import re


MATH_ONLY_PATTERN = re.compile(
    r"^[0-9\s+\-*/().]+$"
)

MATH_EXPRESSION_PATTERN = re.compile(
    r"(?<![\w.])"
    r"[-+]?"
    r"(?:\d+(?:\.\d+)?|\.\d+)"
    r"(?:\s*[+\-*/]\s*"
    r"[-+]?(?:\d+(?:\.\d+)?|\.\d+))+"
)


def normalize_text(
    value: str | None,
) -> str:
    """
    Chuẩn hóa text đầu vào.

    Tránh lỗi NoneType.strip() và gom
    nhiều khoảng trắng thành một khoảng trắng.
    """

    if value is None:
        return ""

    normalized = str(value).strip()

    normalized = re.sub(
        r"\s+",
        " ",
        normalized,
    )

    return normalized


def normalize_for_intent(
    value: str | None,
) -> str:
    """
    Chuẩn hóa text phục vụ phân loại intent.

    Chỉ chuyển x hoặc × thành phép nhân khi ký tự đó
    nằm giữa hai chữ số.

    Ví dụ:
    - 123x321  -> 123 * 321
    - 10 × 2   -> 10 * 2
    - xin chào -> giữ nguyên
    """

    text = normalize_text(
        value
    ).lower()

    # Chuẩn hóa ký hiệu chia và dấu trừ.
    text = (
        text.replace("÷", "/")
        .replace("–", "-")
        .replace("—", "-")
    )

    # Chỉ coi x hoặc × là phép nhân khi nằm giữa các số.
    text = re.sub(
        r"(?<=\d)\s*[x×]\s*(?=\d)",
        " * ",
        text,
    )

    # Gom lại khoảng trắng có thể phát sinh
    # sau quá trình thay thế.
    text = re.sub(
        r"\s+",
        " ",
        text,
    ).strip()

    return text


def extract_math_expression(
    text: str | None,
) -> str | None:
    """
    Tách biểu thức toán từ câu tự nhiên.

    Ví dụ:
    - "1+1 bằng mấy?"       -> "1+1"
    - "tính 123 * 321"      -> "123 * 321"
    - "123x321 là bao nhiêu" -> "123 * 321"
    - "kết quả 10 / 2 là?"  -> "10 / 2"
    """

    normalized = normalize_for_intent(
        text
    )

    if not normalized:
        return None

    # Trường hợp input chỉ chứa biểu thức.
    if MATH_ONLY_PATTERN.fullmatch(
        normalized
    ):
        return normalized.strip()

    match = MATH_EXPRESSION_PATTERN.search(
        normalized
    )

    if not match:
        return None

    return match.group(0).strip()


def is_simple_math_question(
    text: str | None,
) -> bool:
    """
    Nhận diện phép tính đơn giản trong câu tự nhiên.
    """

    expression = extract_math_expression(
        text
    )

    if not expression:
        return False

    normalized = normalize_for_intent(
        text
    )

    # Input chỉ là phép tính.
    if MATH_ONLY_PATTERN.fullmatch(
        normalized
    ):
        return True

    math_question_keywords = [
        "bằng mấy",
        "bằng bao nhiêu",
        "là bao nhiêu",
        "kết quả",
        "tính giúp",
        "tính dùm",
        "tính hộ",
        "tính",
    ]

    if any(
        keyword in normalized
        for keyword in math_question_keywords
    ):
        return True

    # Có biểu thức và kết thúc bằng dấu hỏi.
    return normalized.endswith("?")


def contains_phrase(
    text: str,
    phrases: list[str],
) -> bool:
    """
    Kiểm tra text có chứa ít nhất một cụm từ.
    """

    return any(
        phrase in text
        for phrase in phrases
    )


def is_greeting(
    text: str,
) -> bool:
    """
    Nhận diện lời chào nhưng tránh nhầm
    từ 'hiện tại' thành lời chào 'hi'.
    """

    greeting_patterns = [
        r"^hi(?:\s|$|[!,.?])",
        r"^hello(?:\s|$|[!,.?])",
        r"^hey(?:\s|$|[!,.?])",
        r"^alo(?:\s|$|[!,.?])",
        r"^yo(?:\s|$|[!,.?])",
        r"^xin chào(?:\s|$|[!,.?])",
        r"^chào(?:\s|$|[!,.?])",
    ]

    return any(
        re.search(
            pattern,
            text,
        )
        for pattern in greeting_patterns
    )


def classify_intent(
    user_input: str | None,
) -> str:
    """
    Phân loại câu hỏi trước khi quyết định gọi RAG.

    Các intent:
    - empty
    - greeting
    - thanks
    - upload_info
    - bot_capability
    - simple_math
    - document_question
    """

    text = normalize_for_intent(
        user_input
    )

    if not text:
        return "empty"

    # Kiểm tra toán trước các intent chung.
    if is_simple_math_question(
        text
    ):
        return "simple_math"

    if is_greeting(
        text
    ):
        return "greeting"

    thanks_keywords = [
        "cảm ơn",
        "cám ơn",
        "thank you",
        "thanks",
        "thank",
    ]

    if contains_phrase(
        text,
        thanks_keywords,
    ):
        return "thanks"

    upload_keywords = [
        "upload file",
        "upload tài liệu",
        "up file",
        "tải file",
        "tải tài liệu",
        "gửi file",
        "gửi tài liệu",
        "đưa tài liệu",
        "nạp tài liệu",
        "nhập tài liệu",
        "loại tài liệu",
        "loại file",
        "file gì",
        "file nào",
        "định dạng file",
        "đọc được pdf",
        "đọc file pdf",
        "đọc được docx",
        "đọc được txt",
    ]

    if contains_phrase(
        text,
        upload_keywords,
    ):
        return "upload_info"

    capability_keywords = [
        "bạn làm được gì",
        "bạn có thể làm gì",
        "chatbot làm được gì",
        "chức năng của bạn",
        "chức năng gì",
        "bạn hỗ trợ gì",
        "hỗ trợ được gì",
        "bạn giúp được gì",
        "có thể trả lời ngoài tài liệu",
        "trả lời câu hỏi ngoài tài liệu",
        "trả lời ngoài tài liệu",
        "chỉ trả lời trong tài liệu",
        "chỉ trả lời theo tài liệu",
        "có dùng kiến thức bên ngoài",
        "có kiến thức ngoài tài liệu",
        "phạm vi trả lời",
        "giới hạn của bạn",
    ]

    if contains_phrase(
        text,
        capability_keywords,
    ):
        return "bot_capability"

    return "document_question"