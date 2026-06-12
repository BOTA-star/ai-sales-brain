import re

# Math patterns
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

# Text normalization
def normalize_text(
    value: str | None,
) -> str:
    """
    Chuẩn hóa text đầu vào.
    - Không lỗi khi value là None.
    - Xóa khoảng trắng đầu và cuối.
    - Gom nhiều khoảng trắng thành một khoảng trắng.
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
    Chỉ chuyển x hoặc × thành phép nhân khi ký tự nằm giữa hai chữ số.
    Ví dụ:
    - 123x321  -> 123 * 321
    - 10 × 2   -> 10 * 2
    - xin chào -> giữ nguyên
    """
    text = normalize_text(value).lower()

    text = (
        text.replace("÷", "/")
        .replace("–", "-")
        .replace("—", "-")
    )

    # Chỉ xem x hoặc × là phép nhân khi nằm giữa hai chữ số.
    text = re.sub(
        r"(?<=\d)\s*[x×]\s*(?=\d)",
        " * ",
        text,
    )

    text = re.sub(
        r"\s+",
        " ",
        text,
    ).strip()

    return text

def strip_recall_prefix(
    text: str,
) -> str:
    """
    Loại bỏ các từ dẫn đầu không ảnh hưởng tới ý nghĩa của câu hỏi recall.
    """
    previous_text = ""

    while previous_text != text:
        previous_text = text

        text = re.sub(
            r"^(?:vậy|thế|còn|"
            r"bây\s+giờ|hiện\s+tại|"
            r"cho\s+mình\s+hỏi|"
            r"cho\s+tôi\s+hỏi)"
            r"\s*[,.:;\-]?\s*",
            "",
            text,
            flags=re.IGNORECASE,
        ).strip()

    return text

def contains_phrase(
    text: str,
    phrases: list[str],
) -> bool:
    """
    Kiểm tra text có chứa ít nhất một cụm từ trong danh sách.
    """
    return any(
        phrase in text
        for phrase in phrases
    )

# Simple math
def extract_math_expression(
    text: str | None,
) -> str | None:
    """
    Tách biểu thức toán từ câu tự nhiên.
    Ví dụ:
    - "1+1 bằng mấy?"         -> "1+1"
    - "tính 123 * 321"        -> "123 * 321"
    - "123x321 là bao nhiêu"  -> "123 * 321"
    - "kết quả 10 / 2 là?"    -> "10 / 2"
    """
    normalized = normalize_for_intent(text)

    if not normalized:
        return None

    if MATH_ONLY_PATTERN.fullmatch(
        normalized
    ):
        return normalized.strip()

    match = MATH_EXPRESSION_PATTERN.search(normalized)

    if not match:
        return None

    return match.group(0).strip()

def is_simple_math_question(
    text: str | None,
) -> bool:
    """
    Nhận diện phép tính đơn giản trong câu tự nhiên.
    """
    expression = extract_math_expression(text)

    if not expression:
        return False

    normalized = normalize_for_intent(text)

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

    if contains_phrase(
        normalized,
        math_question_keywords,
    ):
        return True

    return normalized.endswith("?")

# Memory recall
def is_memory_recall_question(
    text: str,
) -> bool:
    """
    Nhận diện câu hỏi yêu cầu nhớ lại thông tin
    người dùng đã cung cấp trước đó.
    Hỗ trợ:
    - Bạn nhớ gì về mình?
    - Mình tên gì?
    - Mình làm việc trong lĩnh vực nào?
    - Mình đang cần giải pháp gì?
    - Nhu cầu của mình?
    """
    normalized = normalize_for_intent(text)

    normalized = strip_recall_prefix(normalized)

    if not normalized:
        return False

    explicit_recall_patterns = [
        # Bạn nhớ / bạn có nhớ / bạn còn nhớ...
        r"\b(?:bạn|bot|chatbot)\s+"
        r"(?:(?:có|còn)\s+)?nhớ\b",

        # Bạn biết gì về mình...
        r"\b(?:bạn|bot|chatbot)\s+"
        r"biết\s+gì\s+về\s+"
        r"(?:mình|tôi|em|tui)\b",

        # Tôi đã chia sẻ gì...
        r"\b(?:mình|tôi|em|tui)\s+đã\s+"
        r"(?:nói|chia sẻ|cho biết|cung cấp)\s+gì\b",

        # Nhớ lại...
        r"\bnhớ\s+lại\b",
    ]

    if any(
        re.search(
            pattern,
            normalized,
        )
        for pattern in explicit_recall_patterns
    ):
        return True

    field_recall_patterns = [
        # Mình tên gì?
        r"\b(?:mình|tôi|em|tui)\s+"
        r"tên\s+(?:là\s+)?gì\b",

        # Tên của mình? / Tên mình là gì?
        r"^tên\s+(?:của\s+)?"
        r"(?:mình|tôi|em|tui)"
        r"(?:\s+là\s+gì|\s+gì)?\s*\??$",

        # Mình làm việc trong lĩnh vực nào?
        r"\b(?:mình|tôi|em|tui)\s+"
        r"(?:đang\s+)?làm(?:\s+việc)?\s+"
        r"trong\s+lĩnh\s+vực\s+"
        r"(?:gì|nào)\b",

        # Lĩnh vực của mình? / Ngành của tôi?
        r"^(?:lĩnh\s+vực|ngành|nghề(?:\s+nghiệp)?)\s+"
        r"(?:của\s+)?(?:mình|tôi|em|tui)"
        r"(?:\s+là\s+gì|\s+gì|\s+nào)?\s*\??$",

        # Mình đang cần giải pháp gì?
        r"\b(?:mình|tôi|em|tui)\s+"
        r"(?:đang\s+)?cần"
        r"(?:\s+(?:giải\s+pháp|chatbot|sản\s+phẩm))?"
        r"\s+(?:gì|nào)\b",

        # Nhu cầu của mình? / Mục tiêu của tôi?
        r"^(?:nhu\s+cầu|mục\s+tiêu|"
        r"giải\s+pháp|chatbot|ưu\s+tiên|ngân\s+sách)\s+"
        r"(?:của\s+)?(?:mình|tôi|em|tui)"
        r"(?:\s+là\s+gì|\s+gì|\s+nào|\s+bao\s+nhiêu)?"
        r"\s*\??$",

        # Tôi cần gì?
        r"\b(?:mình|tôi|em|tui)\s+"
        r"(?:đang\s+)?cần\s+gì\b",

        r"^(?:nhu\s+cầu|mục\s+tiêu|ưu\s+tiên|"
        r"giải\s+pháp|chatbot)"
        r"(?:\s+hiện\s+tại)?\s+"
        r"(?:của\s+)?(?:mình|tôi|em|tui)"
        r"(?:\s+là\s+(?:gì|nào)|"
        r"\s+(?:gì|nào))?\s*\??$",

        r"^(?:nhu\s+cầu|mục\s+tiêu|ưu\s+tiên|"
        r"giải\s+pháp|chatbot|ngân\s+sách)"
        r"(?:\s+hiện\s+tại)?\s+"
        r"(?:của\s+)?(?:mình|tôi|em|tui)"
        r"\s+(?:là\s+)?"
        r"(?:gì|nào|bao\s+nhiêu)"
        r"\s*\??$",
    ]

    return any(
        re.search(
            pattern,
            normalized,
        )
        for pattern in field_recall_patterns
    )

# Thông tin người dùng
def is_customer_information(
    text: str,
) -> bool:
    """
    Nhận diện khách hàng đang cung cấp
    thông tin mới về:
    - Danh tính.
    - Nghề nghiệp hoặc lĩnh vực.
    - Doanh nghiệp.
    - Nhu cầu.
    - Sản phẩm quan tâm.
    - Mục tiêu triển khai.
    - Nhu cầu sale / lead / đội kinh doanh.
    """
    normalized = normalize_for_intent(text)

    if not normalized:
        return False

    # Câu hỏi yêu cầu nhớ lại không phải thông tin mới cần lưu.
    if is_memory_recall_question(
        normalized
    ):
        return False

    customer_information_phrases = [
        # Danh tính
        "tôi tên là",
        "mình tên là",
        "em tên là",
        "tui tên là",
        "tôi tên",
        "mình tên",
        "em tên",
        "tui tên",
        "tên tôi là",
        "tên mình là",
        "tên em là",

        # Nghề nghiệp và lĩnh vực
        "tôi làm trong lĩnh vực",
        "mình làm trong lĩnh vực",
        "em làm trong lĩnh vực",
        "tôi đang làm trong lĩnh vực",
        "mình đang làm trong lĩnh vực",
        "em đang làm trong lĩnh vực",
        "tôi làm việc trong lĩnh vực",
        "mình làm việc trong lĩnh vực",
        "nhân viên trong lĩnh vực",
        "tôi là nhân viên",
        "mình là nhân viên",
        "em là nhân viên",
        "tôi đang là nhân viên",
        "mình đang là nhân viên",

        # Kinh doanh và doanh nghiệp
        "tôi đang kinh doanh",
        "mình đang kinh doanh",
        "em đang kinh doanh",
        "bên tôi kinh doanh",
        "bên mình kinh doanh",
        "công ty tôi",
        "công ty mình",
        "doanh nghiệp tôi",
        "doanh nghiệp mình",

        # Nhu cầu
        "tôi cần",
        "mình cần",
        "em cần",
        "tui cần",
        "tôi đang cần",
        "mình đang cần",
        "em đang cần",
        "đang cần một chatbot",
        "đang cần chatbot",
        "bên tôi cần",
        "bên mình cần",
        "công ty tôi cần",
        "doanh nghiệp tôi cần",
        "cần sự hỗ trợ",
        "cần chatbot hỗ trợ",

        # Quan tâm và triển khai
        "tôi quan tâm",
        "mình quan tâm",
        "em quan tâm",
        "bên tôi quan tâm",
        "bên mình quan tâm",
        "tôi đang tìm hiểu",
        "mình đang tìm hiểu",
        "tôi muốn triển khai",
        "mình muốn triển khai",
        "em muốn triển khai",
        "bên tôi muốn triển khai",
        "bên mình muốn triển khai",

        # Mục tiêu và ưu tiên
        "mục tiêu của tôi",
        "mục tiêu của mình",
        "tôi muốn cải thiện",
        "mình muốn cải thiện",
        "tôi ưu tiên",
        "mình ưu tiên",
        "bên tôi ưu tiên",

        # Ngân sách
        "ngân sách của tôi",
        "ngân sách của mình",
        "ngân sách bên tôi",
        "ngân sách bên mình",
        "ngân sách dự kiến",

        # Cập nhật hoặc thay đổi nhu cầu
        "không còn ưu tiên",
        "mình không còn ưu tiên",
        "tôi không còn ưu tiên",
        "hiện tại mình muốn",
        "hiện tại tôi muốn",
        "mình muốn chatbot",
        "tôi muốn chatbot",
        "bên mình muốn chatbot",
        "bên tôi muốn chatbot",
        "chatbot tập trung",
        "muốn chatbot tập trung",
        "chuyển sang ưu tiên",
        "thay đổi ưu tiên",

        "hiện tại mình ưu tiên",
        "hiện tại tôi ưu tiên",
        "bây giờ mình ưu tiên",
        "bây giờ tôi ưu tiên",
        "mình đang ưu tiên",
        "tôi đang ưu tiên",

        # Sale / lead / đội kinh doanh
        "tôi muốn hệ thống",
        "mình muốn hệ thống",
        "em muốn hệ thống",
        "bên tôi muốn hệ thống",
        "bên mình muốn hệ thống",

        "tôi muốn công cụ",
        "mình muốn công cụ",
        "bên tôi muốn công cụ",
        "bên mình muốn công cụ",

        "cần hệ thống",
        "cần công cụ",
        "hệ thống hỗ trợ",
        "công cụ hỗ trợ",
        "giải pháp hỗ trợ",

        "hỗ trợ đội kinh doanh",
        "hỗ trợ đội sale",
        "hỗ trợ sale",
        "hỗ trợ sales",
        "hỗ trợ nhân viên sale",
        "hỗ trợ nhân viên kinh doanh",

        "xử lý lead",
        "quản lý lead",
        "phân loại lead",
        "chăm sóc lead",
        "theo dõi lead",
        "tăng tốc xử lý lead",

        "quản lý khách tiềm năng",
        "phân loại khách tiềm năng",
        "chăm sóc khách tiềm năng",
        "theo dõi khách tiềm năng",

        "đội kinh doanh xử lý",
        "đội sale xử lý",
        "sale xử lý",
        "sales xử lý",

        "tăng tỷ lệ chốt",
        "tăng tỉ lệ chốt",
        "tối ưu quy trình sale",
        "tối ưu quy trình sales",
        "tối ưu quy trình bán hàng",
    ]

    if contains_phrase(
        normalized,
        customer_information_phrases,
    ):
        return True

    introduction_patterns = [
        # Mình tên T / Mình tên là T
        r"\b(?:mình|tôi|em|tui)\s+"
        r"tên(?:\s+là)?\s+"
        r"[a-zà-ỹ][a-zà-ỹ\s]{0,50}",

        # Mình là T, ...
        r"\b(?:mình|tôi|em|tui)\s+là\s+"
        r"[^?]{1,120}",

        # Mình đang là nhân viên...
        r"\b(?:mình|tôi|em|tui)\s+"
        r"đang\s+là\s+[^?]{1,120}",

        # Mình đang làm...
        r"\b(?:mình|tôi|em|tui)\s+"
        r"đang\s+làm\s+[^?]{1,120}",

        # Mình làm việc...
        r"\b(?:mình|tôi|em|tui)\s+"
        r"làm\s+việc\s+[^?]{1,120}",

        # Mình đang cần...
        r"\b(?:mình|tôi|em|tui)\s+"
        r"đang\s+cần\s+[^?]{1,150}",

        # Bên tôi đang...
        r"\b(?:bên\s+tôi|bên\s+mình|"
        r"công\s+ty\s+tôi|doanh\s+nghiệp\s+tôi)\s+"
        r"(?:đang\s+)?(?:cần|muốn|gặp|kinh doanh)\s+"
        r"[^?]{1,150}",

        # Mình muốn chatbot / giải pháp / hệ thống / công cụ...
        r"\b(?:mình|tôi|em|tui)\s+"
        r"muốn\s+"
        r"(?:chatbot|giải\s+pháp|hệ\s+thống|công\s+cụ|ai)\s+"
        r"[^?]{1,180}",

        # Mình cần hệ thống/công cụ/giải pháp liên quan sale hoặc lead
        r"\b(?:mình|tôi|em|tui)\s+"
        r"(?:đang\s+)?cần\s+"
        r"(?:(?:hệ\s+thống|công\s+cụ|giải\s+pháp|chatbot|ai)\s+)?"
        r"[^?]{0,80}"
        r"(?:lead|khách\s+tiềm\s+năng|đội\s+kinh\s+doanh|"
        r"đội\s+sale|sale|sales|bán\s+hàng)"
        r"[^?]{0,120}",

        # Hệ thống hỗ trợ đội kinh doanh / lead
        r"\b(?:hệ\s+thống|công\s+cụ|giải\s+pháp|chatbot|ai)\s+"
        r"hỗ\s+trợ\s+"
        r"[^?]{0,80}"
        r"(?:lead|khách\s+tiềm\s+năng|đội\s+kinh\s+doanh|"
        r"đội\s+sale|sale|sales|bán\s+hàng)"
        r"[^?]{0,120}",

        # Xử lý / quản lý / phân loại lead
        r"\b(?:xử\s+lý|quản\s+lý|phân\s+loại|"
        r"theo\s+dõi|chăm\s+sóc)\s+"
        r"(?:lead|khách\s+tiềm\s+năng)"
        r"[^?]{0,120}",

        # Tăng / tối ưu / cải thiện sale, lead, tỷ lệ chốt
        r"\b(?:tăng|tối\s+ưu|cải\s+thiện)\s+"
        r"[^?]{0,80}"
        r"(?:tỷ\s+lệ\s+chốt|tỉ\s+lệ\s+chốt|"
        r"lead|sale|sales|bán\s+hàng)"
        r"[^?]{0,120}",

        # Không còn ưu tiên...
        r"\b(?:mình|tôi|em|tui)\s+"
        r"không\s+còn\s+ưu\s+tiên\s+[^?]{1,180}",
    ]

    return any(
        re.search(
            pattern,
            normalized,
        )
        for pattern in introduction_patterns
    )

# Greeting
def is_greeting(
    text: str,
) -> bool:
    """
    Chỉ nhận diện lời chào đơn thuần.
    Được nhận diện:
    - hi
    - hi bạn
    - xin chào
    - chào bạn nha
    Không được nhận diện là greeting:
    - hi bạn, mình tên T
    - xin chào, bên tôi cần chatbot
    """

    normalized = normalize_for_intent(text)

    if not normalized:
        return False

    greeting_patterns = [
        r"^(?:hi|hello|hey|alo|yo)"
        r"(?:\s+(?:bạn|bạn nha|bạn nhé|mọi người))?"
        r"[!,.?]*$",

        r"^xin\s+chào"
        r"(?:\s+(?:bạn|bạn nha|bạn nhé|mọi người))?"
        r"[!,.?]*$",

        r"^chào"
        r"(?:\s+(?:bạn|bạn nha|bạn nhé|mọi người))?"
        r"[!,.?]*$",
    ]

    return any(
        re.fullmatch(
            pattern,
            normalized,
        )
        for pattern in greeting_patterns
    )

# Document / RAG question
def is_document_question(
    text: str,
) -> bool:
    """
    Chỉ nhận diện RAG khi người dùng có dấu hiệu rõ ràng đang hỏi về tài liệu hoặc file đã nạp.
    Không mặc định mọi câu chưa nhận diện được là document_question.
    """
    normalized = normalize_for_intent(text)

    if not normalized:
        return False

    document_keywords = [
        # Tài liệu
        "trong tài liệu",
        "theo tài liệu",
        "dựa trên tài liệu",
        "tài liệu nói gì",
        "tài liệu có đề cập",
        "tài liệu đề cập",
        "nội dung tài liệu",
        "tóm tắt tài liệu",

        # File
        "trong file",
        "theo file",
        "dựa trên file",
        "file nói gì",
        "file có đề cập",
        "file đề cập",
        "nội dung file",
        "tóm tắt file",

        # Định dạng
        "trong pdf",
        "theo pdf",
        "trong docx",
        "theo docx",
        "trong txt",
        "theo txt",

        # Trang và đoạn
        "ở trang nào",
        "trang bao nhiêu",
        "đoạn nào trong tài liệu",
        "phần nào trong tài liệu",
        "chương nào trong tài liệu",

        # Tên file
        ".pdf",
        ".docx",
        ".txt",
    ]

    return contains_phrase(
        normalized,
        document_keywords,
    )

# Intent classifier
def classify_intent(
    user_input: str | None,
) -> str:
    """
    Phân loại mục đích chính của tin nhắn.
    Thứ tự ưu tiên:
    1. empty
    2. memory_recall
    3. simple_math
    4. customer_information
    5. greeting
    6. thanks
    7. upload_info
    8. bot_capability
    9. document_question
    10. general_conversation

    Lưu ý:
    - customer_information phải đứng trước greeting.
    - document_question không được làm fallback mặc định.
    """

    text = normalize_for_intent(user_input)

    if not text:
        return "empty"

    # Phải đứng trước customer_information để tránh: "Bạn còn nhớ chatbot tôi cần không?" bị hiểu nhầm là cung cấp nhu cầu mới.
    if is_memory_recall_question(text):
        return "memory_recall"

    if is_simple_math_question(text):
        return "simple_math"

    # Phải đứng trước greeting để câu:
    # "Hi bạn, mình tên T..." vẫn được lưu thành customer information.
    if is_customer_information(text):
        return "customer_information"

    if is_greeting(text):
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

    if is_document_question(text):
        return "document_question"

    return "general_conversation"