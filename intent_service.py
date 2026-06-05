import re


def normalize_text(value: str) -> str:
    """
    Chuẩn hóa text đầu vào.
    Tránh lỗi NoneType.strip().
    """
    if value is None:
        return ""

    return str(value).strip()


def is_simple_math_question(text: str) -> bool:
    """
    Nhận diện phép tính đơn giản như:
    1+1
    123*321
    123 / 321
    """
    text = normalize_text(text)

    if not text:
        return False

    return bool(
        re.fullmatch(
            r"[0-9\s\+\-\*\/\.\(\)]+",
            text
        )
    )


def classify_intent(user_input: str) -> str:
    """
    Phân loại câu hỏi trước khi quyết định có gọi RAG hay không.

    Các intent hiện tại:
    - empty
    - greeting
    - thanks
    - upload_info
    - bot_capability
    - simple_math
    - document_question
    """
    text = normalize_text(user_input)

    if not text:
        return "empty"

    lower_text = text.lower()

    greetings = [
        "hi",
        "hello",
        "hey",
        "xin chào",
        "chào",
        "chào bạn",
        "hi bạn",
        "alo",
        "alo bạn"
    ]

    thanks = [
        "cảm ơn",
        "cám ơn",
        "thanks",
        "thank you",
        "ok cảm ơn",
        "ok cám ơn"
    ]

    upload_keywords = [
        "upload",
        "up file",
        "tải file",
        "tải tài liệu",
        "gửi file",
        "gửi tài liệu",
        "đưa tài liệu",
        "nạp tài liệu",
        "loại tài liệu",
        "file gì",
        "file nào",
        "pdf",
        "docx",
        "txt"
    ]

    capability_keywords = [
        "bạn làm được gì",
        "bạn có thể làm gì",
        "chatbot làm được gì",
        "chức năng của bạn",
        "chức năng gì",
        "hỗ trợ gì",
        "giúp gì"
    ]

    if lower_text in greetings or any(lower_text.startswith(item) for item in greetings):
        return "greeting"

    if any(item in lower_text for item in thanks):
        return "thanks"

    if any(item in lower_text for item in upload_keywords):
        return "upload_info"

    if any(item in lower_text for item in capability_keywords):
        return "bot_capability"

    if is_simple_math_question(lower_text):
        return "simple_math"

    return "document_question"