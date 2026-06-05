import os
import html
import psycopg2
from psycopg2.extras import RealDictCursor
import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv

load_dotenv()

USE_MOCK = os.getenv("USE_MOCK", "false").lower() == "true"
MODEL_NAME = os.getenv("MODEL", "qwen2.5:3b")
DATABASE_URL = os.getenv("DATABASE_URL")
DEFAULT_CUSTOMER_NAME = "Khách demo AI Sales Brain"

# Chỉnh kích thước tổng ở đây
APP_HEIGHT = 550
CHAT_FRAME_HEIGHT = 550

st.set_page_config(
    page_title="AI Chatbot Demo",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
.block-container {
    padding-top: 1rem !important;
    padding-bottom: 1rem !important;
    padding-left: 2.5rem !important;
    padding-right: 2.5rem !important;
    max-width: 100% !important;
}

.stApp {
    background: linear-gradient(135deg, #EAF8FB 0%, #F7FCFD 100%);
}

/* Giảm scroll toàn trang */
html, body {
    overflow: hidden;
}

/* Cột lịch sử */
.history-panel {
    height: 610px;
    background: rgba(255, 255, 255, 0.60);
    border: 1px solid rgba(65, 157, 165, 0.25);
    border-radius: 22px;
    padding: 18px;
    box-shadow: 0 10px 28px rgba(65, 157, 165, 0.08);
    box-sizing: border-box;
}

.history-title {
    font-size: 20px;
    font-weight: 700;
    color: #163B40;
    margin-bottom: 16px;
}

.history-item {
    padding: 12px 14px;
    margin-bottom: 10px;
    border-radius: 14px;
    background: rgba(65, 157, 165, 0.13);
    color: #24474B;
    font-size: 14px;
}

/* Form nhập tin nhắn - layer trước */
div[data-testid="stForm"] {
    height: 86px;
    background: rgba(255, 255, 255, 0.72);
    border-left: 1px solid rgba(65, 157, 165, 0.25);
    border-right: 1px solid rgba(65, 157, 165, 0.25);
    border-bottom: 1px solid rgba(65, 157, 165, 0.25);
    border-top: none;
    border-radius: 0 0 22px 22px;
    padding: 16px 18px 12px 18px;
    box-shadow: 0 10px 28px rgba(65, 157, 165, 0.08);
    box-sizing: border-box;
}

/* Ô nhập */
div[data-testid="stTextInput"] input {
    border-radius: 16px;
    border: 1px solid rgba(65, 157, 165, 0.32);
    background: rgba(255, 255, 255, 0.95);
    height: 42px;
    color: #102D33;
}

/* Nút gửi */
div[data-testid="stFormSubmitButton"] button {
    border-radius: 16px;
    background: rgba(65, 157, 165, 0.92);
    color: white;
    border: none;
    height: 42px;
    font-weight: 600;
}

div[data-testid="stFormSubmitButton"] button:hover {
    background: rgba(48, 127, 135, 0.98);
    color: white;
    border: none;
}

.stButton button {
    border-radius: 14px;
    background: rgba(65, 157, 165, 0.90);
    color: white;
    border: none;
}

.stButton button:hover {
    background: rgba(48, 127, 135, 0.98);
    color: white;
    border: none;
}

/* Giảm khoảng trắng iframe */
iframe {
    display: block;
}
</style>
""", unsafe_allow_html=True)

def get_db_connection():
    if not DATABASE_URL:
        raise Exception("Missing DATABASE_URL in .env")

    return psycopg2.connect(DATABASE_URL)


def create_customer_if_needed():
    """
    MVP hiện tại chưa có đăng nhập/customer thật,
    nên tạo 1 khách demo để gắn hội thoại.
    """
    if "customer_id" in st.session_state:
        return st.session_state.customer_id

    conn = get_db_connection()

    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO customers (full_name, source, note)
                    VALUES (%s, %s, %s)
                    RETURNING id;
                    """,
                    (
                        DEFAULT_CUSTOMER_NAME,
                        "web",
                        "Khách demo tạo từ Streamlit chatbot"
                    )
                )

                customer_id = cur.fetchone()[0]
                st.session_state.customer_id = str(customer_id)
                return st.session_state.customer_id

    finally:
        conn.close()


def create_conversation(customer_id: str):
    conn = get_db_connection()

    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO conversations (customer_id, channel, status)
                    VALUES (%s, %s, %s)
                    RETURNING id;
                    """,
                    (customer_id, "web", "active")
                )

                conversation_id = cur.fetchone()[0]
                return str(conversation_id)

    finally:
        conn.close()


def save_message(conversation_id: str, sender: str, content: str):
    conn = get_db_connection()

    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO messages (conversation_id, sender, content)
                    VALUES (%s, %s, %s);
                    """,
                    (conversation_id, sender, content)
                )

    finally:
        conn.close()


def load_messages(conversation_id: str):
    conn = get_db_connection()

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT sender, content
                FROM messages
                WHERE conversation_id = %s
                ORDER BY message_order ASC;
                """,
                (conversation_id,)
            )

            rows = cur.fetchall()

            messages = []
            for row in rows:
                messages.append({
                    "role": row["sender"],
                    "content": row["content"]
                })

            return messages

    finally:
        conn.close()

def get_recent_context(conversation_id: str, limit: int = 8):
    conn = get_db_connection()

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT sender, content
                FROM messages
                WHERE conversation_id = %s
                ORDER BY message_order DESC
                LIMIT %s;
                """,
                (conversation_id, limit)
            )

            rows = cur.fetchall()
            rows.reverse()

            context_messages = []

            for row in rows:
                context_messages.append({
                    "role": row["sender"],
                    "content": row["content"]
                })

            return context_messages

    finally:
        conn.close()

def init_chat_session():
    customer_id = create_customer_if_needed()

    if "conversation_id" not in st.session_state:
        conversation_id = create_conversation(customer_id)
        st.session_state.conversation_id = conversation_id

        welcome_message = "Chào bạn, mình là chatbot AI demo. Bạn muốn hỏi gì?"
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": welcome_message
            }
        ]

        save_message(conversation_id, "assistant", welcome_message)

    else:
        db_messages = load_messages(st.session_state.conversation_id)

        if db_messages:
            st.session_state.messages = db_messages

if "messages" not in st.session_state:
    init_chat_session()

if "chat_history" not in st.session_state:
    st.session_state.chat_history = ["Cuộc trò chuyện hiện tại"]


def get_bot_answer(user_input: str) -> str:
    if USE_MOCK:
        return f"Đây là câu trả lời demo. Bạn vừa hỏi: {user_input}"

    try:
        import ollama

        system_prompt = {
            "role": "system",
            "content": (
                "You are a basic local AI chatbot demo. "
                "Answer in the same language as the user. "
                "Be concise, clear, and honest. "
                "Do not invent facts, numbers, sources, links, or real-time information. "
                "If you are not sure, say you do not have enough information."
            )
        }

        conversation_id = st.session_state.get("conversation_id")
        recent_context = get_recent_context(conversation_id, limit=8)
        messages = [system_prompt] + recent_context

        response = ollama.chat(
            model=MODEL_NAME,
            messages=messages,
            options={
                "temperature": 0.2,
                "top_p": 0.8
            }
        )

        if hasattr(response, "message"):
            return response.message.content

        return response["message"]["content"]

    except Exception as e:
        return (
            "Không gọi được Ollama. Bạn kiểm tra lại:\n\n"
            "1. Ollama đã chạy chưa.\n"
            "2. Đã pull model chưa.\n"
            "3. Tên model trong file .env có đúng không.\n\n"
            f"Chi tiết lỗi: {e}"
        )


def render_messages() -> str:
    html_messages = ""

    for message in st.session_state.messages:
        role = message.get("role", "assistant")
        content = html.escape(message.get("content", ""))

        if role == "user":
            html_messages += f"""
            <div class="message-row user-row">
                <div class="message-bubble user-bubble">{content}</div>
            </div>
            """
        else:
            html_messages += f"""
            <div class="message-row assistant-row">
                <div class="message-bubble assistant-bubble">{content}</div>
            </div>
            """

    return html_messages


def build_chat_html() -> str:
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
    <style>
    body {{
        margin: 0;
        font-family: Arial, sans-serif;
        background: transparent;
        overflow: hidden;
    }}

    .chat-panel {{
        height: {CHAT_FRAME_HEIGHT}px;
        background: rgba(255, 255, 255, 0.60);
        border: 1px solid rgba(65, 157, 165, 0.25);
        border-radius: 22px 22px 0 0;
        box-shadow: 0 10px 28px rgba(65, 157, 165, 0.08);
        overflow: hidden;
        box-sizing: border-box;
    }}

    .chat-header {{
        height: 86px;
        padding: 18px 26px 12px 26px;
        border-bottom: 1px solid rgba(65, 157, 165, 0.15);
        background: rgba(255, 255, 255, 0.30);
        box-sizing: border-box;
    }}

    .chat-title {{
        font-size: 28px;
        font-weight: 800;
        color: #102D33;
        margin-bottom: 4px;
    }}

    .chat-subtitle {{
        color: #4B6B70;
        font-size: 15px;
    }}

    /* Layer sau: vùng chat có scroll */
    .chat-scroll {{
        height: {CHAT_FRAME_HEIGHT - 86}px;
        overflow-y: auto;
        padding: 20px 26px;
        box-sizing: border-box;
        scroll-behavior: smooth;
        background: rgba(240, 251, 253, 0.35);
    }}

    .chat-scroll::-webkit-scrollbar {{
        width: 8px;
    }}

    .chat-scroll::-webkit-scrollbar-track {{
        background: transparent;
    }}

    .chat-scroll::-webkit-scrollbar-thumb {{
        background: rgba(65, 157, 165, 0.35);
        border-radius: 20px;
    }}

    .message-row {{
        display: flex;
        margin-bottom: 14px;
    }}

    .user-row {{
        justify-content: flex-end;
    }}

    .assistant-row {{
        justify-content: flex-start;
    }}

    .message-bubble {{
        max-width: 72%;
        padding: 12px 16px;
        border-radius: 18px;
        line-height: 1.55;
        font-size: 15px;
        word-wrap: break-word;
        white-space: pre-wrap;
        box-sizing: border-box;
    }}

    .user-bubble {{
        background: rgba(65, 157, 165, 0.34);
        border: 1px solid rgba(65, 157, 165, 0.42);
        color: #102D33;
        border-bottom-right-radius: 6px;
    }}

    .assistant-bubble {{
        background: rgba(255, 255, 255, 0.78);
        border: 1px solid rgba(65, 157, 165, 0.22);
        color: #183A40;
        border-bottom-left-radius: 6px;
    }}
    </style>
    </head>

    <body>
        <div class="chat-panel">
            <div class="chat-header">
                <div class="chat-title">AI Chatbot Demo</div>
                <div class="chat-subtitle">Bản demo chatbot cơ bản chạy local</div>
            </div>

            <div class="chat-scroll" id="chat-scroll">
                {render_messages()}
            </div>
        </div>

        <script>
            const chatScroll = document.getElementById("chat-scroll");
            if (chatScroll) {{
                chatScroll.scrollTop = chatScroll.scrollHeight;
            }}
        </script>
    </body>
    </html>
    """


left_col, right_col = st.columns([1, 4], gap="large")

with left_col:
    st.markdown("""
    <div class="history-panel">
        <div class="history-title">Lịch sử</div>
        <div class="history-item">Cuộc trò chuyện hiện tại</div>
    </div>
    """, unsafe_allow_html=True)

    if st.button("➕ Chat mới", use_container_width=True):
        customer_id = create_customer_if_needed()
        conversation_id = create_conversation(customer_id)

        st.session_state.conversation_id = conversation_id

        welcome_message = "Chào bạn, mình là chatbot AI demo. Bạn muốn hỏi gì?"
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": welcome_message
            }
        ]

        save_message(conversation_id, "assistant", welcome_message)

        st.rerun()

with right_col:
    components.html(
        build_chat_html(),
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

        conversation_id = st.session_state.conversation_id

        st.session_state.messages.append({
            "role": "user",
            "content": user_input
        })

        save_message(conversation_id, "user", user_input)

        answer = get_bot_answer(user_input)

        st.session_state.messages.append({
            "role": "assistant",
            "content": answer
        })

        save_message(conversation_id, "assistant", answer)

        st.rerun()