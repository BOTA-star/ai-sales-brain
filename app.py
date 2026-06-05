import streamlit as st

from chat_orchestrator import get_chat_answer
from config import CHAT_FRAME_HEIGHT, WELCOME_MESSAGE, HISTORY_BOX_HEIGHT
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
from ui_components import build_chat_html, get_global_css


@st.cache_resource
def get_rag_pipeline():
    return create_rag_pipeline()


def shorten_title(title: str, max_length: int = 32) -> str:
    if not title:
        return "Cuộc trò chuyện mới"

    title = title.strip()

    if len(title) <= max_length:
        return title

    return title[:max_length] + "..."


st.set_page_config(
    page_title="AI Chatbot Demo",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown(get_global_css(), unsafe_allow_html=True)

if "messages" not in st.session_state:
    init_chat_session(st.session_state)

left_col, right_col = st.columns([1, 4], gap="large")

with left_col:
    customer_id = create_customer_if_needed(st.session_state)
    conversations = load_conversations(customer_id)

    st.markdown(
        f"""
        <div class="left-title">Lịch sử</div>
        <div class="left-subtitle">{len(conversations)} phiên chat</div>
        """,
        unsafe_allow_html=True
    )

    if st.button("➕ Chat mới", use_container_width=True, key="new_chat_button"):
        st.session_state["conversation_id"] = None
        st.session_state["messages"] = [
            {
                "role": "assistant",
                "content": WELCOME_MESSAGE
            }
        ]

        st.rerun()

    st.markdown(
        """
        <div class="history-list-title">Danh sách chat</div>
        """,
        unsafe_allow_html=True
    )

    history_box = st.container(height=HISTORY_BOX_HEIGHT, border=True)

    with history_box:
        if not conversations:
            st.caption("Chưa có cuộc trò chuyện nào.")
        else:
            for index, conversation in enumerate(conversations):
                conversation_id = str(conversation["id"])
                title = conversation["title"] or f"Cuộc trò chuyện {index + 1}"
                display_title = shorten_title(title)

                is_current = conversation_id == st.session_state.get("conversation_id")
                button_label = f"● {display_title}" if is_current else display_title

                if st.button(
                    button_label,
                    key=f"conversation_{conversation_id}",
                    use_container_width=True
                ):
                    st.session_state["conversation_id"] = conversation_id
                    st.session_state["messages"] = load_messages(conversation_id)

                    st.rerun()

with right_col:
    st.iframe(
        build_chat_html(st.session_state["messages"]),
        height=CHAT_FRAME_HEIGHT,
        width="stretch"
    )

    with st.form("chat_form", clear_on_submit=True):
        input_col, button_col = st.columns([8, 1])

        with input_col:
            user_input = st.text_input(
                "Nhập câu hỏi",
                placeholder="Nhập câu hỏi của bạn...",
                label_visibility="collapsed"
            )

        with button_col:
            submitted = st.form_submit_button("Gửi", use_container_width=True)

    clean_user_input = (user_input or "").strip()

    if submitted and clean_user_input:
        conversation_id = st.session_state.get("conversation_id")

        if not conversation_id:
            conversation_id = create_conversation(customer_id)
            st.session_state["conversation_id"] = conversation_id

            save_message(conversation_id, "assistant", WELCOME_MESSAGE)

        st.session_state["messages"].append({
            "role": "user",
            "content": clean_user_input
        })

        save_message(conversation_id, "user", clean_user_input)
        update_conversation_title_if_needed(conversation_id, clean_user_input)

        rag_pipeline = get_rag_pipeline()

        answer = get_chat_answer(
            user_input=clean_user_input,
            conversation_id=conversation_id,
            rag_pipeline=rag_pipeline
        )

        st.session_state["messages"].append({
            "role": "assistant",
            "content": answer
        })

        save_message(conversation_id, "assistant", answer)

        st.rerun()