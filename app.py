import streamlit as st
import streamlit.components.v1 as components

from bot_service import get_bot_answer
from config import CHAT_FRAME_HEIGHT, WELCOME_MESSAGE
from conversation_service import (
    create_conversation,
    create_customer_if_needed,
    init_chat_session,
    save_message,
)
from ui_components import build_chat_html, get_global_css


st.set_page_config(
    page_title="AI Chatbot Demo",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown(get_global_css(), unsafe_allow_html=True)


if "messages" not in st.session_state:
    init_chat_session(st.session_state)

if "chat_history" not in st.session_state:
    st.session_state.chat_history = ["Cuộc trò chuyện hiện tại"]


left_col, right_col = st.columns([1, 4], gap="large")


with left_col:
    st.markdown("""
    <div class="history-panel">
        <div class="history-title">Lịch sử</div>
        <div class="history-item">Cuộc trò chuyện hiện tại</div>
    </div>
    """, unsafe_allow_html=True)

    if st.button("➕ Chat mới", use_container_width=True):
        customer_id = create_customer_if_needed(st.session_state)
        conversation_id = create_conversation(customer_id)

        st.session_state["conversation_id"] = conversation_id

        st.session_state["messages"] = [
            {
                "role": "assistant",
                "content": WELCOME_MESSAGE
            }
        ]

        save_message(conversation_id, "assistant", WELCOME_MESSAGE)

        st.rerun()


with right_col:
    components.html(
        build_chat_html(st.session_state["messages"]),
        height=CHAT_FRAME_HEIGHT,
        scrolling=False
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

    if submitted and user_input.strip():
        user_input = user_input.strip()

        conversation_id = st.session_state["conversation_id"]

        st.session_state["messages"].append({
            "role": "user",
            "content": user_input
        })

        save_message(conversation_id, "user", user_input)

        answer = get_bot_answer(user_input, conversation_id)

        st.session_state["messages"].append({
            "role": "assistant",
            "content": answer
        })

        save_message(conversation_id, "assistant", answer)

        st.rerun()