import streamlit as st

from chat_orchestrator import get_chat_answer
from config import (
    CHAT_FRAME_HEIGHT,
    HISTORY_BOX_HEIGHT,
    WELCOME_MESSAGE,
)
from conversation_service import (
    create_conversation,
    create_customer_if_needed,
    init_chat_session,
    load_conversations,
    load_messages,
    save_message,
    update_conversation_title_if_needed,
)
from rag_service import create_rag_pipeline
from session_service import get_or_create_client_id
from ui_components import (
    build_chat_html,
    get_global_css,
)


# ==================================================
# Streamlit configuration
# ==================================================

st.set_page_config(
    page_title="AI Chatbot Demo",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ==================================================
# Cached resources
# ==================================================

@st.cache_resource
def get_rag_pipeline():
    """
    Chỉ khởi tạo embedding model, vector store
    và LLM client một lần trong vòng đời ứng dụng.
    """

    return create_rag_pipeline()


# ==================================================
# Helper functions
# ==================================================

def shorten_title(
    title: str | None,
    max_length: int = 32,
) -> str:
    """
    Rút gọn tiêu đề conversation để hiển thị
    trong danh sách lịch sử.
    """

    clean_title = str(
        title or ""
    ).strip()

    if not clean_title:
        return "Cuộc trò chuyện mới"

    if len(clean_title) <= max_length:
        return clean_title

    return (
        clean_title[:max_length]
        + "..."
    )


def reset_current_chat() -> None:
    """
    Reset giao diện về một cuộc trò chuyện mới.

    Chưa tạo conversation trong database.
    Conversation chỉ được tạo khi user gửi
    câu hỏi đầu tiên.
    """

    st.session_state[
        "conversation_id"
    ] = None

    st.session_state[
        "messages"
    ] = [
        {
            "role": "assistant",
            "content": WELCOME_MESSAGE,
        }
    ]


def select_conversation(
    conversation_id: str,
    customer_id: str,
) -> None:
    """
    Chọn một conversation và load lại toàn bộ
    messages thuộc đúng customer hiện tại.
    """

    st.session_state[
        "conversation_id"
    ] = conversation_id

    st.session_state[
        "messages"
    ] = load_messages(
        conversation_id=conversation_id,
        customer_id=customer_id,
    )


# ==================================================
# Global UI
# ==================================================

st.markdown(
    get_global_css(),
    unsafe_allow_html=True,
)


# ==================================================
# Initialize browser user and chat session
# ==================================================

# Mỗi trình duyệt có một client_id riêng.
client_id = get_or_create_client_id(
    st.session_state
)

# Khởi tạo messages và customer
# cho lần truy cập đầu tiên.
if "messages" not in st.session_state:
    init_chat_session(
        session_state=st.session_state,
        external_id=client_id,
    )

# Lấy customer_id gắn với
# trình duyệt hiện tại.
customer_id = create_customer_if_needed(
    session_state=st.session_state,
    external_id=client_id,
)

# Đảm bảo session luôn có conversation_id.
st.session_state.setdefault(
    "conversation_id",
    None,
)


# ==================================================
# Main layout
# ==================================================

left_col, right_col = st.columns(
    [1, 4],
    gap="large",
)


# ==================================================
# Left column: conversation history
# ==================================================

with left_col:
    conversations = load_conversations(
        customer_id=customer_id
    )

    st.markdown(
        f"""
        <div class="left-title">
            Lịch sử
        </div>

        <div class="left-subtitle">
            {len(conversations)} phiên chat
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.button(
        "➕ Chat mới",
        use_container_width=True,
        key="new_chat_button",
    ):
        reset_current_chat()
        st.rerun()

    st.markdown(
        """
        <div class="history-list-title">
            Danh sách chat
        </div>
        """,
        unsafe_allow_html=True,
    )

    history_box = st.container(
        height=HISTORY_BOX_HEIGHT,
        border=True,
    )

    with history_box:
        if not conversations:
            st.caption(
                "Chưa có cuộc trò chuyện nào."
            )

        else:
            current_conversation_id = (
                st.session_state.get(
                    "conversation_id"
                )
            )

            for index, conversation in enumerate(
                conversations
            ):
                history_conversation_id = str(
                    conversation["id"]
                )

                conversation_title = (
                    conversation.get(
                        "title"
                    )
                    or (
                        "Cuộc trò chuyện "
                        f"{index + 1}"
                    )
                )

                display_title = shorten_title(
                    conversation_title
                )

                is_current = (
                    history_conversation_id
                    == current_conversation_id
                )

                button_label = (
                    f"● {display_title}"
                    if is_current
                    else display_title
                )

                if st.button(
                    button_label,
                    key=(
                        "conversation_"
                        f"{history_conversation_id}"
                    ),
                    use_container_width=True,
                ):
                    select_conversation(
                        conversation_id=(
                            history_conversation_id
                        ),
                        customer_id=customer_id,
                    )

                    st.rerun()


# ==================================================
# Right column: chat content and input
# ==================================================

with right_col:
    st.iframe(
        build_chat_html(
            st.session_state[
                "messages"
            ]
        ),
        height=CHAT_FRAME_HEIGHT,
        width="stretch",
    )

    with st.form(
        "chat_form",
        clear_on_submit=True,
    ):
        input_col, button_col = st.columns(
            [8, 1]
        )

        with input_col:
            user_input = st.text_input(
                "Nhập câu hỏi",
                placeholder=(
                    "Nhập câu hỏi của bạn..."
                ),
                label_visibility="collapsed",
            )

        with button_col:
            submitted = (
                st.form_submit_button(
                    "Gửi",
                    use_container_width=True,
                )
            )


# ==================================================
# Handle submitted message
# ==================================================

clean_user_input = str(
    user_input or ""
).strip()


if submitted and clean_user_input:
    active_conversation_id = (
        st.session_state.get(
            "conversation_id"
        )
    )

    # Chỉ tạo conversation khi user
    # gửi câu đầu tiên.
    if not active_conversation_id:
        active_conversation_id = (
            create_conversation(
                customer_id=customer_id
            )
        )

        st.session_state[
            "conversation_id"
        ] = active_conversation_id

        # Giữ nguyên chức năng hiện tại:
        # lưu welcome message vào conversation mới.
        save_message(
            conversation_id=(
                active_conversation_id
            ),
            customer_id=customer_id,
            sender="assistant",
            content=WELCOME_MESSAGE,
        )

    # Hiển thị message user trên UI.
    st.session_state[
        "messages"
    ].append(
        {
            "role": "user",
            "content": clean_user_input,
        }
    )

    # Lưu message user vào database
    # và lấy ID của message vừa tạo.
    current_user_message_id = save_message(
        conversation_id=(
            active_conversation_id
        ),
        customer_id=customer_id,
        sender="user",
        content=clean_user_input,
    )

    # Dùng câu hỏi đầu tiên làm
    # tiêu đề conversation.
    update_conversation_title_if_needed(
        conversation_id=(
            active_conversation_id
        ),
        customer_id=customer_id,
        user_input=clean_user_input,
    )

    # Gọi chatbot.
    #
    # current_user_message_id được truyền vào
    # để orchestrator loại câu hỏi hiện tại
    # khỏi recent context.
    answer = get_chat_answer(
        user_input=clean_user_input,
        conversation_id=(
            active_conversation_id
        ),
        customer_id=customer_id,
        rag_pipeline=get_rag_pipeline(),
        current_user_message_id=(
            current_user_message_id
        ),
    )

    # Hiển thị câu trả lời trên UI.
    st.session_state[
        "messages"
    ].append(
        {
            "role": "assistant",
            "content": answer,
        }
    )

    # Lưu câu trả lời vào database.
    save_message(
        conversation_id=(
            active_conversation_id
        ),
        customer_id=customer_id,
        sender="assistant",
        content=answer,
    )

    # Chạy lại để cập nhật chat và sidebar.
    st.rerun()


elif submitted:
    st.warning(
        "Bạn vui lòng nhập nội dung "
        "trước khi gửi."
    )