from config import MODEL_NAME, USE_MOCK
from conversation_service import get_recent_context


def get_bot_answer(user_input: str, conversation_id: str) -> str:
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