import html

from config import CHAT_FRAME_HEIGHT


def get_global_css() -> str:
    return """
<style>
.block-container {
    padding-top: 4.2rem !important;
    padding-bottom: 0.75rem !important;
    padding-left: 1.5rem !important;
    padding-right: 1.5rem !important;
    max-width: 100% !important;
    min-height: 100vh !important;
}

.stApp {
    background: linear-gradient(135deg, #EAF8FB 0%, #F7FCFD 100%);
    min-height: 100vh;
}

html, body {
    overflow: auto;
}

/* Không được hidden, nếu không sẽ mất ô nhập */
section.main {
    height: auto !important;
    min-height: 100vh !important;
    overflow-y: auto !important;
}

.main .block-container {
    max-width: 100vw !important;
}

div[data-testid="stHorizontalBlock"] {
    gap: 1.2rem !important;
}

div[data-testid="column"] {
    min-width: 0 !important;
}

/* Header cột trái */
.left-title {
    font-size: 24px;
    font-weight: 800;
    color: #102D33;
    line-height: 1.2;
    margin-bottom: 4px;
}

.left-subtitle {
    font-size: 14px;
    color: #6A8085;
    margin-bottom: 12px;
}

.history-list-title {
    font-size: 18px;
    font-weight: 800;
    color: #102D33;
    margin-top: 18px;
    margin-bottom: 8px;
}

/* Button chung */
.stButton button {
    width: 100%;
    border-radius: 12px;
    background: rgba(65, 157, 165, 0.92);
    color: white;
    border: none;

    min-height: 52px;
    max-height: 52px;

    font-size: 14px;
    font-weight: 600;
    line-height: 1.2;

    padding: 8px 16px;
    margin-bottom: 10px;

    display: flex !important;
    align-items: center !important;
    justify-content: flex-start !important;

    overflow: hidden !important;
    box-sizing: border-box !important;
}

.stButton button:hover {
    background: rgba(48, 127, 135, 0.98);
    color: white;
    border: none;
}

/* Streamlit thường bọc text của button trong markdown container */
.stButton button div[data-testid="stMarkdownContainer"] {
    width: 100% !important;
    display: block !important;
    overflow: hidden !important;
}

/* Chữ trong button nằm bên trái */
.stButton button div[data-testid="stMarkdownContainer"] p {
    width: 100% !important;
    margin: 0 !important;

    text-align: left !important;
    white-space: nowrap !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
}

/* Fallback nếu Streamlit render thẳng thẻ p */
.stButton button p {
    width: 100% !important;
    margin: 0 !important;

    text-align: left !important;
    white-space: nowrap !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
}

/* Khung danh sách chat có scroll nội bộ */
div[data-testid="stVerticalBlockBorderWrapper"] {
    border: none !important;
    background: transparent !important;
    overflow-y: auto !important;
}

div[data-testid="stVerticalBlockBorderWrapper"]::-webkit-scrollbar {
    width: 6px;
}

div[data-testid="stVerticalBlockBorderWrapper"]::-webkit-scrollbar-track {
    background: transparent;
}

div[data-testid="stVerticalBlockBorderWrapper"]::-webkit-scrollbar-thumb {
    background: rgba(65, 157, 165, 0.35);
    border-radius: 20px;
}

/* Form nhập tin nhắn */
div[data-testid="stForm"] {
    min-height: 76px;
    background: rgba(255, 255, 255, 0.78);
    border-left: 1px solid rgba(65, 157, 165, 0.25);
    border-right: 1px solid rgba(65, 157, 165, 0.25);
    border-bottom: 1px solid rgba(65, 157, 165, 0.25);
    border-top: none;
    border-radius: 0 0 22px 22px;
    padding: 12px 18px 10px 18px;
    box-shadow: 0 10px 28px rgba(65, 157, 165, 0.08);
    box-sizing: border-box;

    position: sticky;
    bottom: 0;
    z-index: 20;
}

div[data-testid="stTextInput"] input {
    border-radius: 16px;
    border: 1px solid rgba(65, 157, 165, 0.32);
    background: rgba(255, 255, 255, 0.95);
    height: 40px;
    color: #102D33;
    padding-left: 14px;
}

/* Riêng nút gửi thì căn giữa */
div[data-testid="stFormSubmitButton"] button {
    border-radius: 16px;
    background: rgba(65, 157, 165, 0.92);
    color: white;
    border: none;
    height: 40px;
    min-height: 40px;
    max-height: 40px;
    font-weight: 700;

    justify-content: center !important;
    text-align: center !important;
}

div[data-testid="stFormSubmitButton"] button div[data-testid="stMarkdownContainer"] p,
div[data-testid="stFormSubmitButton"] button p {
    text-align: center !important;
}

div[data-testid="stFormSubmitButton"] button:hover {
    background: rgba(48, 127, 135, 0.98);
    color: white;
    border: none;
}

iframe {
    display: block;
    border: none !important;
}
</style>
"""


def render_messages(messages) -> str:
    html_messages = ""

    for message in messages:
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


def build_chat_html(messages) -> str:
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
        height: 76px;
        padding: 14px 24px 10px 24px;
        box-sizing: border-box;
    }}

    .chat-title {{
        font-size: 28px;
        font-weight: 800;
        color: #102D33;
        margin-bottom: 4px;
        line-height: 1.15;
    }}

    .chat-subtitle {{
        color: #4B6B70;
        font-size: 15px;
        line-height: 1.3;
    }}

    .chat-scroll {{
        height: calc(100% - 76px);
        overflow-y: auto;
        padding: 16px 24px;
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
        background: rgba(255, 255, 255, 0.82);
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
                {render_messages(messages)}
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