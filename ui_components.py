import html

from config import CHAT_FRAME_HEIGHT


def get_global_css() -> str:
    return """
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