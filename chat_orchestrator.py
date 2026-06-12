from datetime import datetime
import ast
import re
import logging
import operator
from typing import Any

from config import RECENT_CONTEXT_LIMIT
from conversation_service import get_recent_context
from intent_service import (
    classify_intent,
    extract_math_expression,
    is_memory_recall_question,
    normalize_text,
)

from memory_service import (
    save_memory,
    search_memory,
    format_memory_context,    
)

logger = logging.getLogger(__name__)

_MEMORY_SIGNALS: dict[str, tuple[str, ...]] = {
    "identity": (
        "tôi tên là",
        "mình tên là",
        "em tên là",
        "tui tên là",

        # Không bắt buộc có chữ "là".
        "tôi tên",
        "mình tên",
        "em tên",
        "tui tên",

        "tên tôi là",
        "tên mình là",
        "tên em là",
    ),

    "business": (
        "tôi đang kinh doanh",
        "mình đang kinh doanh",
        "em đang kinh doanh",
        "bên tôi kinh doanh",
        "bên mình kinh doanh",

        "công ty tôi",
        "công ty mình",
        "doanh nghiệp tôi",
        "doanh nghiệp mình",

        "lĩnh vực của tôi",
        "lĩnh vực của mình",
        "ngành của tôi",
        "ngành của mình",

        "tôi làm trong lĩnh vực",
        "mình làm trong lĩnh vực",
        "em làm trong lĩnh vực",

        "tôi làm việc trong lĩnh vực",
        "mình làm việc trong lĩnh vực",

        # Trường hợp câu hiện tại.
        "nhân viên trong lĩnh vực",
        "làm trong lĩnh vực",
        "đang làm trong lĩnh vực",
    ),

    "interest": (
        "tôi quan tâm",
        "mình quan tâm",
        "em quan tâm",
        "bên tôi quan tâm",
        "bên mình quan tâm",

        "tôi đang tìm hiểu",
        "mình đang tìm hiểu",
        "em đang tìm hiểu",
    ),

    "need": (
        "tôi cần",
        "mình cần",
        "em cần",
        "tui cần",

        "tôi đang cần",
        "mình đang cần",
        "em đang cần",

        # Trường hợp chủ ngữ nằm ở đầu câu,
        # phía sau chỉ còn "đang cần".
        "đang cần một chatbot",
        "đang cần chatbot",
        "cần một chatbot",
        "cần chatbot",

        "bên tôi cần",
        "bên mình cần",
        "công ty tôi cần",
        "công ty mình cần",
        "doanh nghiệp tôi cần",
        "doanh nghiệp mình cần",

        "tôi muốn triển khai",
        "mình muốn triển khai",
        "bên tôi muốn triển khai",
        "bên mình muốn triển khai",
        "mình muốn chatbot",
        "tôi muốn chatbot",
        "em muốn chatbot",
        "muốn chatbot tập trung",
        "chatbot tập trung",
        "tập trung hỗ trợ sale",
        "tập trung hỗ trợ bán hàng",
    ),

    "priority": (
        "tôi ưu tiên",
        "mình ưu tiên",
        "em ưu tiên",
        "bên tôi ưu tiên",
        "bên mình ưu tiên",
        "ưu tiên của tôi",
        "ưu tiên của mình",
        "không còn ưu tiên",
        "mình không còn ưu tiên",
        "tôi không còn ưu tiên",
        "ưu tiên hiện tại",
        "chuyển sang ưu tiên",
        "thay đổi ưu tiên",
        "bây giờ mình ưu tiên",
        "bây giờ tôi ưu tiên",
        "hiện tại mình ưu tiên",
        "hiện tại tôi ưu tiên",
        "mình đang ưu tiên",
        "tôi đang ưu tiên",
    ),

    "budget": (
        "ngân sách của tôi",
        "ngân sách của mình",
        "ngân sách bên tôi",
        "ngân sách bên mình",
        "ngân sách dự kiến",
        "ngân sách dự tính",
    ),

    "problem": (
        "đang gặp vấn đề",
        "gặp khó khăn",
        "đang gặp khó khăn",
        "bị chậm",
        "phản hồi chậm",
        "chưa phân loại",
        "không phân loại được",
        "chưa theo dõi được",
    ),

    "goal": (
        "mục tiêu của tôi",
        "mục tiêu của mình",
        "mục tiêu bên tôi",
        "muốn tăng hiệu suất",
        "tăng hiệu suất công việc",
        "muốn cải thiện",
        "muốn tối ưu",
        "muốn tăng tỷ lệ",
    ),
}

_KNOWN_MEMORY_CONCEPTS: tuple[str, ...] = (
    "AI",
    "trí tuệ nhân tạo",

    "chatbot",
    "chatbot AI",
    "chăm sóc khách hàng",
    "chăm sóc học viên",

    "marketing",
    "bán hàng",
    "sale",
    "sales",

    "tăng hiệu suất công việc",
    "tự động hóa",
    "phân loại khách hàng",
    "phân loại người dùng",

    "thẩm mỹ",
    "giáo dục",
    "bất động sản",
    "sản xuất",
)

def _build_memory_candidate(
    user_input: str,
) -> tuple[str, list[str]] | None:
    """
    Kiểm tra tin nhắn có chứa thông tin khách hàng đáng lưu vào long-term memory hay không.

    Lưu các thông tin có giá trị lâu dài:
    - Danh tính.
    - Nghề nghiệp/lĩnh vực.
    - Nhu cầu.
    - Sản phẩm quan tâm.
    - Mục tiêu.
    - Khó khăn hiện tại.
    - Ưu tiên và ngân sách.
    - ...

    Không lưu câu hỏi yêu cầu chatbot nhớ lại.
    """
    clean_input = str(user_input or "").strip()

    if len(clean_input) < 8:
        return None
    
    # Không lưu câu hỏi recall thành fact.
    if is_memory_recall_question(clean_input):
        logger.info(
            "Skip memory because input is a memory recall question. input=%s",
            clean_input,
        )
        return None
    
    normalized_input = (clean_input.casefold())

    matched_categories: list[str] = []

    for category, signals in _MEMORY_SIGNALS.items():
        if any(
            signal in normalized_input
            for signal in signals
        ):
            matched_categories.append(category)

    # Bổ sung nhận dạng bằng regex để không phụ thuộc hoàn toàn vào cụm từ cố định.
    regex_category_patterns: dict[str, tuple[str, ...]] = {
        "identity": (
            r"\b(?:mình|tôi|em|tui)\s+"
            r"tên(?:\s+là)?\s+"
            r"[a-zà-ỹ][a-zà-ỹ\s]{0,40}",
        ),

        "business": (
            r"\b(?:mình|tôi|em|tui)\s+"
            r"(?:đang\s+)?(?:làm|làm việc)\s+"
            r"(?:trong\s+)?lĩnh\s+vực\b",

            r"\bnhân\s+viên\s+"
            r"(?:làm\s+)?(?:trong\s+)?lĩnh\s+vực\b",
        ),

        "need": (
            r"\b(?:mình|tôi|em|tui)\s+"
            r"(?:đang\s+)?cần\b",

            r"\bđang\s+cần\s+"
            r"(?:một\s+)?chatbot\b",
                r"\b(?:mình|tôi|em|tui)\s+"
            r"muốn\s+(?:chatbot|giải\s+pháp)\b",

            r"\bchatbot\s+tập\s+trung\s+"
            r"(?:hỗ\s+trợ\s+)?",
        ),

        "priority": (
            r"\b(?:(?:bây\s+giờ|hiện\s+tại)\s+)?"
            r"(?:mình|tôi|em|tui)\s+"
            r"(?:đang\s+)?ưu\s+tiên\b",

            r"\b(?:mình|tôi|em|tui)\s+"
            r"không\s+còn\s+ưu\s+tiên\b",

            r"\b(?:chuyển\s+sang|thay\s+đổi)\s+"
            r"ưu\s+tiên\b",
        ),

        "goal": (
            r"\b(?:muốn|cần)\s+"
            r"(?:tăng|cải thiện|tối ưu)\b",

            r"\btăng\s+hiệu\s+suất\b",
        ),

        "problem": (
            r"\b(?:đang\s+)?gặp\s+"
            r"(?:vấn\s+đề|khó\s+khăn)\b",

            r"\b(?:bị|đang)\s+chậm\b",

            r"\bchưa\s+"
            r"(?:phân\s+loại|theo\s+dõi|xử\s+lý)\b",
        ),
    }

    for category, patterns in regex_category_patterns.items():
        if category in matched_categories:
            continue

        if any(
            re.search(
                pattern,
                normalized_input,
                flags=re.IGNORECASE,
            )
            for pattern in patterns
        ):
            matched_categories.append(
                category
            )

    if not matched_categories:
        logger.info(
            "Skip memory because no memory signal matched. "
            "input=%s",
            clean_input,
        )
        return None

    concepts = list(matched_categories)

    for concept in _KNOWN_MEMORY_CONCEPTS:
        if concept.casefold() in normalized_input:
            concepts.append(concept)

    # Loại bỏ trùng lặp nhưng giữ nguyên thứ tự.
    concepts = list(
        dict.fromkeys(concepts)
    )

    content = (
        "Khách hàng cho biết: "
        f"{clean_input}"
    )

    return content, concepts

def _save_user_memory_safely(
    customer_id: str,
    user_input: str,
) -> dict[str, Any] | None:
    """
    Tự động lưu thông tin quan trọng của khách hàng.
    Nếu AgentMemory gặp lỗi thì chatbot vẫn tiếp tục xử lý và trả lời bình thường.
    """

    clean_customer_id = str(customer_id or "").strip()

    if not clean_customer_id:
        logger.warning(
            "Skip saving memory because customer_id is empty."
        )
        return None

    memory_candidate = (
        _build_memory_candidate(user_input)
    )

    if memory_candidate is None:
        logger.info(
            "No memory candidate detected. customer_id=%s input=%s",
            clean_customer_id,
            user_input,
        )
        return None

    content, concepts = (memory_candidate)

    logger.info(
        "Saving customer memory. "
        "customer_id=%s concepts=%s content=%s",
        clean_customer_id,
        concepts,
        content,
    )

    print(
        "[MEMORY SAVE REQUEST]",
        {
            "customer_id": clean_customer_id,
            "concepts": concepts,
            "content": content,
        },
    )

    try:
        memory = save_memory(
            customer_id=clean_customer_id,
            content=content,
            memory_type="fact",
            concepts=concepts,
        )

        if memory:
            logger.info(
                "Saved customer memory successfully. "
                "customer_id=%s memory_id=%s",
                clean_customer_id,
                memory.get("id"),
            )

            print(
                "[MEMORY SAVE SUCCESS]",
                {
                    "customer_id": clean_customer_id,
                    "memory_id": memory.get("id"),
                },
            )

        else:
            logger.warning(
                "AgentMemory did not save memory. customer_id=%s",
                clean_customer_id,
            )

            print(
                "[MEMORY SAVE FAILED]",
                {
                    "customer_id": clean_customer_id,
                },
            )

        return memory

    except Exception:
        logger.exception(
            "Failed to save customer memory. "
            "customer_id=%s",
            clean_customer_id,
        )

        return None
    
_ALLOWED_BINARY_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
}

_ALLOWED_UNARY_OPERATORS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}

def _evaluate_math_node(
    node: ast.AST,
) -> int | float:
    """
    Tính biểu thức toán học đơn giản mà không sử dụng eval().
    """
    if isinstance(node, ast.Expression):
        return _evaluate_math_node(node.body)

    if (
        isinstance(node, ast.Constant)
        and isinstance(
            node.value,
            (int, float),
        )
        and not isinstance(
            node.value,
            bool,
        )
    ):
        return node.value

    if (
        isinstance(node, ast.BinOp)
        and type(node.op)
        in _ALLOWED_BINARY_OPERATORS
    ):
        left_value = _evaluate_math_node(node.left)

        right_value = _evaluate_math_node(node.right)

        operation = (
            _ALLOWED_BINARY_OPERATORS[
                type(node.op)
            ]
        )

        return operation(left_value, right_value,)

    if (isinstance(node, ast.UnaryOp) and type(node.op) in _ALLOWED_UNARY_OPERATORS):
        operand_value = (
            _evaluate_math_node(node.operand)
        )

        operation = (
            _ALLOWED_UNARY_OPERATORS[type(node.op)]
        )

        return operation(operand_value)

    raise ValueError(
        "Biểu thức toán học không được hỗ trợ."
    )

def get_source_value(
    source: Any,
    key: str,
    default: Any = "N/A",
) -> Any:
    """
    Lấy giá trị source an toàn.
    Hỗ trợ cả:
    - source.file_name
    - source["file_name"]
    """

    if source is None:
        return default

    if isinstance(source, dict):
        return source.get(key,default,)

    return getattr(source,key,default,)

def format_rag_sources(
    sources: list[Any],
) -> str:
    """
    Format nguồn tham khảo.
    """
    if not sources:
        return ""

    source_lines = ["\n\n---\nNguồn tham khảo:"]

    for index, source in enumerate(sources,start=1):
        file_name = get_source_value(source,"file_name")

        page = get_source_value(source,"page")

        chunk_index = get_source_value(source,"chunk_index")

        source_lines.append(
            f"{index}. File: {file_name} "
            f"| Page: {page} "
            f"| Chunk: {chunk_index}"
        )

    return "\n".join(source_lines)

def answer_simple_math(
    user_input: str,
) -> str:
    """
    Trả lời phép tính đơn giản bằng AST.
    """
    expression_text = (
        extract_math_expression(user_input)
    )

    if not expression_text:
        return ("Mình chưa nhận diện được phép tính trong câu hỏi.")

    try:
        expression = ast.parse(
            expression_text,
            mode="eval",
        )

        result = _evaluate_math_node(expression)

        # Hiển thị 2 thay vì 2.0 nếu kết quả là số nguyên.
        if (isinstance(result, float) and result.is_integer()
        ):
            result = int(result)

        return str(result)

    except ZeroDivisionError:
        return "Không thể chia cho 0."

    except (
        SyntaxError,
        ValueError,
        TypeError,
        OverflowError,
    ):
        return ("Mình chưa xử lý được phép tính này.")

def _extract_customer_name(
    user_input: str,
) -> str:
    """
    Lấy tên khách hàng từ nội dung đã chia sẻ.
    Hỗ trợ:
    - Mình tên T
    - Mình tên là T
    - Hi, mình tên T
    - Tôi là Nguyễn Văn An, ...
    """
    text = str(user_input or "").strip()

    name_patterns = [
        r"\b(?:mình|tôi|em|tui)\s+"
        r"tên(?:\s+là)?\s+"
        r"([A-Za-zÀ-ỹ]+(?:\s+[A-Za-zÀ-ỹ]+){0,3}?)"
        r"(?=\s*(?:,|\.|!|\?|"
        r"và\b|đang\b|nhân\s+viên\b|"
        r"làm\b|$))",

        r"\btên\s+(?:mình|tôi|em|tui)"
        r"(?:\s+là)?\s+"
        r"([A-Za-zÀ-ỹ]+(?:\s+[A-Za-zÀ-ỹ]+){0,3}?)"
        r"(?=\s*(?:,|\.|!|\?|"
        r"và\b|đang\b|nhân\s+viên\b|"
        r"làm\b|$))",

        r"\b(?:mình|tôi|em|tui)\s+là\s+"
        r"([A-Za-zÀ-ỹ]+(?:\s+[A-Za-zÀ-ỹ]+){0,3}?)"
        r"(?=\s*,)",
    ]

    for pattern in name_patterns:
        match = re.search(pattern,text,flags=re.IGNORECASE)

        if match:
            return match.group(1).strip().title()

    return ""

def answer_customer_information(
    user_input: str,
    memory_context: str = "",
) -> str:
    """
    Xác nhận thông tin khách hàng dựa trên:
    - Tin nhắn hiện tại.
    - Memory liên quan đã lưu trước đó.
    Các nhánh cụ thể được ưu tiên trước câu trả lời tổng quát.
    """

    clean_input = str(user_input or "").strip()

    combined_context = normalize_text(f"{memory_context}\n{clean_input}").lower()

    customer_name = _extract_customer_name(clean_input)

    if customer_name:
        opening = (f"Mình hiểu rồi, {customer_name}. ")
    else:
        opening = "Mình hiểu rồi. "
        
    # Phải đặt trước chăm sóc khách hàng vì câu sale cũng có thể chứa từ "khách hàng"
    if (
        "chatbot" in combined_context
        and any(
            keyword in combined_context
            for keyword in [
                "sale",
                "sales",
                "bán hàng",
                "chốt đơn",
                "nhân viên sale",
            ]
        )
    ):
        return (
            opening + "Mình đã ghi nhận bạn cần một chatbot hỗ trợ hoạt động sale. "
            "Chatbot sẽ hỗ trợ tư vấn, thu thập thông tin và phân loại khách hàng, sau đó nhân viên sale "
            "sẽ kiểm tra và quyết định phản hồi cuối cùng. "
            "Bạn muốn ưu tiên xây dựng tiêu chí phân loại khách hàng hay tối ưu tốc độ phản hồi trước?"
        )

    # Chatbot tăng hiệu suất công việc
    if (
        "chatbot" in combined_context
        and any(
            keyword in combined_context
            for keyword in [
                "tăng năng suất",
                "tăng hiệu suất",
                "hiệu suất công việc",
                "năng suất công việc",
                "hỗ trợ công việc",
            ]
        )
    ):
        if any(
            keyword in combined_context
            for keyword in [
                "lĩnh vực ai",
                "trí tuệ nhân tạo",
                "nhân viên trong lĩnh vực ai",
                "làm việc trong lĩnh vực ai",
            ]
        ):
            return (
                opening + "Mình đã ghi nhận bạn đang làm việc trong lĩnh vực AI và cần một chatbot "
                "để tăng năng suất công việc. "
                "Bạn muốn chatbot ưu tiên hỗ trợ phần nào: "
                "tra cứu thông tin, xử lý công việc lặp lại, "
                "hỗ trợ kỹ thuật hay quản lý công việc?"
            )

        return (
            opening + "Mình đã ghi nhận bạn cần một chatbot để tăng năng suất công việc. "
            "Bạn muốn chatbot ưu tiên hỗ trợ công việc nào trước?"
        )

    # Chăm sóc người dùng
    if (
        "chatbot" in combined_context
        and (
            "chăm sóc học viên" in combined_context
            or "học viên" in combined_context
        )
    ):
        return (
            opening
            + "Bạn đang muốn sử dụng chatbot để hỗ trợ chăm sóc học viên. "
            "Bạn muốn chatbot ưu tiên tư vấn khóa học, giải đáp thắc mắc, nhắc lịch hay chăm sóc sau đăng ký?"
        )

    # Chăm sóc khách hàng
    if (
        "chatbot" in combined_context
        and (
            "chăm sóc khách hàng" in combined_context or "hỗ trợ khách hàng" in combined_context
        )
    ):
        return (
            opening + "Bạn đang muốn sử dụng chatbot để hỗ trợ "
            "chăm sóc khách hàng. "
            "Vấn đề cần ưu tiên là tốc độ phản hồi, "
            "xử lý câu hỏi lặp lại, theo dõi khách hàng "
            "hay phân loại khách hàng?"
        )

    # Marketing
    if any(
        keyword in combined_context
        for keyword in [
            "marketing",
            "quảng cáo",
            "tạo nội dung",
        ]
    ):
        return (
            opening + "Bạn đang quan tâm đến hoạt động marketing. "
            "Bạn muốn ưu tiên tạo nội dung, tìm kiếm khách hàng hay tự động hóa quy trình marketing?"
        )

    # Thực tập sinh AI
    if (
        "thực tập sinh" in combined_context
        and any(
            keyword in combined_context
            for keyword in [
                "ai",
                "trí tuệ nhân tạo",
            ]
        )
    ):
        return (
            opening + "Mình đã ghi nhận bạn là thực tập sinh AI và muốn dùng chatbot để hỗ trợ công việc. "
            "Bạn cần ưu tiên đọc và sửa code, xử lý dữ liệu, kiểm thử hệ thống hay viết báo cáo?"
        )

    # Có chatbot nhưng chưa rõ mục đích
    if "chatbot" in combined_context:
        return (
            opening + "Mình đã ghi nhận bạn đang cần một chatbot. "
            "Bạn muốn chatbot hỗ trợ chính cho công việc nội bộ, bán hàng, marketing hay chăm sóc khách hàng?"
        )

    # Fallback
    return (
        opening + "Mình đã ghi nhận thông tin bạn vừa chia sẻ. "
        "Bạn muốn ưu tiên giải quyết vấn đề nào trước?"
    )

def _clean_memory_content(
    memory: dict[str, Any],
) -> str:
    """
    Lấy nội dung memory và bỏ tiền tố kỹ thuật.
    """
    content = str(
        memory.get(
            "content",
            "",
        )
    ).strip()

    prefix = "Khách hàng cho biết:"

    if content.startswith(
        prefix
    ):
        content = content[
            len(prefix):
        ].strip()

    return content

def _get_memory_concepts(
    memory: dict[str, Any],
) -> set[str]:
    """
    Chuẩn hóa concepts của memory.
    """
    raw_concepts = memory.get(
        "concepts",
        [],
    )

    if not isinstance(
        raw_concepts,
        list,
    ):
        return set()

    return {
        str(concept).strip().casefold()
        for concept in raw_concepts
        if str(concept).strip()
    }

def _get_memory_score(
    memory: dict[str, Any],
) -> float:
    """
    Lấy relevance score an toàn.
    """
    try:
        return float(
            memory.get(
                "score",
                0,
            )
            or 0
        )
    except (
        TypeError,
        ValueError,
    ):
        return 0.0

def _get_memory_timestamp(
    memory: dict[str, Any],
) -> float:
    """
    Lấy thời gian memory từ các field phổ biến.

    AgentMemory hiện có thể trả createdAt
    thay vì timestamp.
    """
    timestamp_fields = (
        "updatedAt",
        "createdAt",
        "timestamp",
        "updated_at",
        "created_at",
    )

    for field in timestamp_fields:
        raw_value = str(
            memory.get(field, "",)
            or ""
        ).strip()

        if not raw_value:
            continue

        try:
            return datetime.fromisoformat(
                raw_value.replace(
                    "Z",
                    "+00:00",
                )
            ).timestamp()

        except ValueError:
            continue

    return 0.0

def _detect_recall_targets(
    query: str,
) -> set[str]:
    """
    Xác định trường thông tin người dùng
    đang yêu cầu nhớ lại.
    """
    normalized = normalize_text(query).casefold()

    targets: set[str] = set()

    if any(
        keyword in normalized
        for keyword in [
            "tên",
            "là ai",
        ]
    ):
        targets.add("identity")

    if any(
        keyword in normalized
        for keyword in [
            "lĩnh vực",
            "ngành",
            "nghề",
            "nghề nghiệp",
            "làm việc",
            "đang làm gì",
        ]
    ):
        targets.add("business")

    if any(
        keyword in normalized
        for keyword in [
            "chatbot",
            "nhu cầu",
            "cần gì",
            "cần giải pháp",
            "giải pháp gì",
            "giải pháp",
            "mục tiêu",
            "sản phẩm",
        ]
    ):
        targets.add("need")

    if any(
        keyword in normalized
        for keyword in [
            "nhu cầu hiện tại",
            "cần gì hiện tại",
            "hiện tại cần gì",
        ]
    ):
        targets.add("priority")

    if any(
        keyword in normalized
        for keyword in [
            "vấn đề",
            "khó khăn",
            "trở ngại",
            "bị chậm",
            "phản hồi chậm",
            "phân loại khách hàng",
        ]
    ):
        targets.add("problem")

    if "ưu tiên" in normalized:
        targets.add("priority")

    if "ngân sách" in normalized:
        targets.add("budget")

    # Câu hỏi chung: "Bạn nhớ gì về mình?"
    if not targets:
        targets = {
            "identity",
            "business",
            "need",
            "problem",
        }

    return targets

def _rank_memories(
    memories: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Ưu tiên memory mới nhất.
    Với dữ liệu có thể thay đổi như nhu cầu, mục tiêu, vấn đề và ưu tiên, thông tin mới phải được dùng trước thông tin cũ.
    """
    return sorted(
        memories,
        key=lambda memory: (
            _get_memory_timestamp(memory),
            _get_memory_score(memory),
        ),
        reverse=True,
    )

def _filter_memories_by_target(
    memories: list[dict[str, Any]],
    target: str,
) -> list[dict[str, Any]]:
    """
    Lọc memory dựa trên concepts phù hợp với trường người dùng đang hỏi.
    """
    target_concepts: dict[str, set[str]] = {
        "identity": {
            "identity",
        },
        "business": {
            "business",
            "ai",
            "trí tuệ nhân tạo",
        },
        "need": {
            "need",
            "priority",
            "goal",
            "chatbot",
            "chatbot ai",
            "sale",
            "sales",
            "bán hàng",
            "tăng hiệu suất công việc",
            "phân loại khách hàng",
            "phân loại người dùng",
        },
        "problem": {
            "problem",
            "phân loại khách hàng",
            "phân loại người dùng",
        },
        "priority": {
            "priority",
        },
        "budget": {
            "budget",
        },
    }

    expected_concepts = target_concepts.get(
        target,
        set(),
    )

    matched_memories = [
        memory
        for memory in memories if (
            _get_memory_concepts(memory) & expected_concepts
        )
    ]

    return matched_memories

def _is_invalid_recall_value(
    value: str,
) -> bool:
    """
    Loại bỏ giá trị được trích từ câu hỏi thay vì từ dữ liệu thật.
    """
    normalized = normalize_text(value).casefold().strip(" .?!")

    if not normalized:
        return True

    invalid_values = {
        "gì",
        "nào",
        "là gì",
        "lĩnh vực gì",
        "lĩnh vực nào",
        "ngành gì",
        "ngành nào",
        "giải pháp gì",
        "giải pháp nào",
        "chatbot gì",
        "chatbot nào",
        "nhu cầu gì",
    }

    if normalized in invalid_values:
        return True

    return (
        normalized.endswith(" gì") or normalized.endswith(" nào")
    )

def _extract_business_field(
    content: str,
) -> str:
    """
    Trích xuất lĩnh vực làm việc từ memory.
    """
    patterns = [
        r"\b(?:nhân\s+viên(?:\s+làm\s+việc)?|"
        r"(?:đang\s+)?làm(?:\s+việc)?)\s+"
        r"trong\s+lĩnh\s+vực\s+"
        r"([A-Za-zÀ-ỹ0-9+#./\-\s]+?)"
        r"(?=\s+(?:và|nhưng|đồng\s+thời)\b|"
        r"[,.;!?]|$)",

        r"\blĩnh\s+vực\s+(?:của\s+)?"
        r"(?:tôi|mình|em)\s+là\s+"
        r"([A-Za-zÀ-ỹ0-9+#./\-\s]+?)"
        r"(?=[,.;!?]|$)",
    ]

    for pattern in patterns:
        match = re.search(
            pattern,
            content,
            flags=re.IGNORECASE,
        )

        if match:
            value = match.group(1).strip()

            if not _is_invalid_recall_value(
                value
            ):
                return value

    return ""

def _extract_need(
    content: str,
) -> str:
    """
    Trích xuất nhu cầu hiện tại từ memory.
    Ưu tiên các mẫu cập nhật như:
    - Mình muốn chatbot...
    - Hiện tại mình muốn...
    - Mình cần...
    """
    patterns = [
        # Bây giờ mình ưu tiên...
        # Hiện tại tôi đang ưu tiên...
        r"\b(?:(?:bây\s+giờ|hiện\s+tại)\s+)?"
        r"(?:mình|tôi|em|tui)\s+"
        r"(?:đang\s+)?ưu\s+tiên\s+"
        r"(.+)",

        # Mình chuyển sang ưu tiên...
        r"\b(?:mình|tôi|em|tui)\s+"
        r"(?:chuyển\s+sang|thay\s+đổi)\s+"
        r"ưu\s+tiên\s+(.+)",

        # Các pattern cũ tiếp tục giữ nguyên
        r"\b(?:mình|tôi|em|tui)\s+"
        r"muốn\s+"
        r"(.+)",

        r"\bnhu\s+cầu\s+hiện\s+tại\s+"
        r"(?:của\s+)?(?:mình|tôi|em|tui)"
        r"\s+là\s+(.+)",

        r"\b(?:mình|tôi|em|tui)\s+"
        r"(?:đang\s+)?cần\s+(.+)",

        r"\bđang\s+cần\s+(.+)",

        r"\bnhu\s+cầu\s+(?:của\s+)?"
        r"(?:mình|tôi|em|tui)\s+là\s+(.+)",
    ]

    for pattern in patterns:
        matches = list(
            re.finditer(
                pattern,
                content,
                flags=re.IGNORECASE,
            )
        )

        if not matches:
            continue

        # Nếu một memory có nhiều câu, ưu tiên mẫu xuất hiện sau cùng.
        match = matches[-1]

        value = match.group(1).strip(" .?!")

        if not _is_invalid_recall_value(value):
            return value
    return ""

def _extract_priority(
    content: str,
) -> str:
    """
    Trích xuất ưu tiên hiện tại từ memory.
    """
    patterns = [
        r"\b(?:(?:bây\s+giờ|hiện\s+tại)\s+)?"
        r"(?:mình|tôi|em|tui)\s+"
        r"(?:đang\s+)?ưu\s+tiên\s+"
        r"(.+)",

        r"\bưu\s+tiên\s+hiện\s+tại\s+"
        r"(?:của\s+)?(?:mình|tôi|em|tui)"
        r"\s+là\s+(.+)",

        r"\b(?:mình|tôi|em|tui)\s+"
        r"(?:chuyển\s+sang|thay\s+đổi)\s+"
        r"ưu\s+tiên\s+(.+)",
    ]

    for pattern in patterns:
        matches = list(
            re.finditer(
                pattern,
                content,
                flags=re.IGNORECASE,
            )
        )

        if not matches:
            continue

        value = matches[-1].group(1).strip(" .?!")

        if not _is_invalid_recall_value(value):
            return value

    return ""

def strip_recall_prefix(text: str) -> str:
    return re.sub(
        r"^(?:vậy|thế|còn|cho mình hỏi|cho tôi hỏi)"
        r"\s*[,.:;-]?\s*",
        "",
        text,
        flags=re.IGNORECASE,
    )

def answer_memory_recall(
    customer_id: str,
    query: str,
) -> str:
    """
    Truy xuất đúng trường thông tin người dùng hỏi.
    Không liệt kê toàn bộ top memories.
    Không gọi RAG.
    """
    clean_customer_id = str( customer_id or "").strip()

    clean_query = str(query or "").strip()

    if not clean_customer_id:
        return ("Mình chưa xác định được thông tin khách hàng để kiểm tra bộ nhớ.")

    if not clean_query:
        return ("Bạn muốn mình nhớ lại thông tin nào?")

    try:
        memories = search_memory(
            customer_id=clean_customer_id,
            query=clean_query,
            limit=10,
        )
    except Exception:
        logger.exception(
            "Failed to recall customer memory. "
            "customer_id=%s",
            clean_customer_id,
        )

        return ("Hiện tại mình chưa thể truy xuất thông tin đã ghi nhớ.")

    if not memories:
        return ("Hiện tại mình chưa tìm thấy thông tin bạn đã chia sẻ trước đó.")

    ranked_memories = _rank_memories(memories)

    targets = _detect_recall_targets(clean_query)

    answer_parts: list[str] = []

    # Định danh
    if "identity" in targets:
        identity_memories = (
            _filter_memories_by_target(
                ranked_memories,
                "identity",
            )
        )

        customer_name = ""

        for memory in identity_memories:
            content = _clean_memory_content(memory)

            customer_name = (
                _extract_customer_name(content)
            )

            if customer_name:
                break

        if customer_name:
            answer_parts.append(f"Bạn tên {customer_name}.")

    # Lĩnh vực
    if "business" in targets:
        business_memories = (
            _filter_memories_by_target(
                ranked_memories,
                "business",
            )
        )

        business_field = ""

        for memory in business_memories:
            content = _clean_memory_content(memory)

            business_field = (
                _extract_business_field(content)
            )

            if business_field:
                break

        if business_field:
            answer_parts.append(
                "Bạn làm việc trong lĩnh vực "
                f"{business_field}."
            )

    # Need / chatbot
    if "need" in targets:
        need_memories = (
            _filter_memories_by_target(
                ranked_memories,
                "need",
            )
        )

        customer_need = ""

        for memory in need_memories:
            content = _clean_memory_content(memory)

            customer_need = (
                _extract_need(content)
            )

            if customer_need:
                break

        if customer_need:
            answer_parts.append(f"Bạn cần {customer_need}.")

    if "priority" in targets:
        priority_memories = (
            _filter_memories_by_target(
                ranked_memories,
                "priority",
            )
        )

        current_priority = ""

        for memory in priority_memories:
            content = _clean_memory_content(memory)

            current_priority = (
                _extract_priority(content)
            )

            if current_priority:
                break

        if current_priority:
            answer_parts.append(
                "Ưu tiên hiện tại của bạn là "
                f"{current_priority}."
            )

    # Problem
    if "problem" in targets:
        problem_memories = (
            _filter_memories_by_target(
                ranked_memories,
                "problem",
            )
        )

        if problem_memories:
            problem_content = (
                _clean_memory_content(problem_memories[0])
            )

            if problem_content:
                answer_parts.append(
                    "Vấn đề bạn đang ưu tiên là: "
                    f"{problem_content}."
                )

    if answer_parts:
        return (
            "Có, mình nhớ. "
            + " ".join(
                answer_parts
            )
        )

    # Fallback khi concepts cũ chưa đầy đủ.
    fallback_contents: list[str] = []
    seen_contents: set[str] = set()

    for memory in ranked_memories:
        content = _clean_memory_content(memory)

        if not content:
            continue

        normalized_content = (content.casefold())

        if normalized_content in seen_contents:
            continue

        seen_contents.add(normalized_content)

        fallback_contents.append(content)

        if len(fallback_contents) >= 2:
            break

    if not fallback_contents:
        return (
            "Mình tìm thấy memory nhưng chưa trích xuất được đúng thông tin bạn đang hỏi."
        )

    memory_lines = "\n".join(
        f"- {content}"
        for content in fallback_contents
    )

    return (
        "Mình tìm thấy các thông tin liên quan:\n"
        f"{memory_lines}"
    )

def answer_by_rule(
    intent: str,
    user_input: str = "",
) -> str:
    """
    Các intent không cần RAG được trả lời trực tiếp bằng rule.
    """
    if intent == "empty":
        return (
            "Bạn vui lòng nhập câu hỏi trước nha."
        )

    if intent == "greeting":
        return (
            "Hi bạn 👋 Mình là chatbot RAG demo. "
            "Mình có thể trả lời câu hỏi dựa trên tài liệu đã được nạp vào hệ thống."
        )

    if intent == "thanks":
        return (
            "Không có gì nha 😊 "
            "Bạn cần hỏi thêm gì về tài liệu thì cứ nhắn mình."
        )

    if intent == "upload_info":
        return (
            "Bạn có thể gửi các tài liệu như PDF, DOCX hoặc TXT. "
            "Tuy nhiên hiện tại bản demo đang dùng tài liệu được nạp sẵn trong lúc code. "
            "Bước tiếp theo có thể thêm chức năng upload file để bạn tự nạp tài liệu."
        )

    if intent == "bot_capability":
        return (
            "Hiện tại mình được thiết kế theo chế độ Strict RAG, nên chủ yếu trả lời dựa trên các tài liệu đã được nạp vào hệ thống. "
            "Nếu tài liệu không có thông tin phù hợp, mình sẽ thông báo là chưa tìm thấy thay vì tự dùng kiến thức bên ngoài để trả lời."
        )
    return ""

def _load_recent_context_safely(
    conversation_id: str,
    customer_id: str,
    current_user_message_id: str | None,
) -> list[dict[str, str]]:
    """
    Load short-term context nhưng không để lỗi history làm hỏng toàn bộ lượt trả lời.
    Message user hiện tại được loại khỏi history bằng current_user_message_id.
    """
    clean_conversation_id = str(conversation_id or "").strip()

    clean_customer_id = str(customer_id or "").strip()

    if not clean_conversation_id:
        logger.warning("Cannot load recent context because conversation_id is empty.")
        return []

    if not clean_customer_id:
        logger.warning("Cannot load recent context because customer_id is empty.")
        return []

    try:
        recent_context = get_recent_context(
            conversation_id=clean_conversation_id,
            customer_id=clean_customer_id,
            limit=RECENT_CONTEXT_LIMIT,
            exclude_message_id=(current_user_message_id),
        )

        if not isinstance(
            recent_context,
            list,
        ):
            logger.warning(
                "Recent context is not a list. conversation_id=%s customer_id=%s",
                clean_conversation_id,
                clean_customer_id,
            )
            return []

        return recent_context

    except Exception:
        logger.exception(
            "Failed to load recent chat context. "
            "conversation_id=%s customer_id=%s",
            clean_conversation_id,
            clean_customer_id,
        )

        return []

def _load_memory_context_safely(
    customer_id: str,
    query: str,
    limit: int = 5,
) -> str:
    """
    Truy xuất long-term memory từ AgentMemory.
    AgentMemory lỗi không được làm gián đoạn toàn bộ luồng trả lời của chatbot.
    """
    clean_customer_id = str(customer_id or "").strip()

    clean_query = str(query or "").strip()

    if not clean_customer_id:
        logger.warning("Skip memory search because customer_id is empty.")
        return ""

    if not clean_query:
        return ""

    try:
        memories = search_memory(
            customer_id=clean_customer_id,
            query=clean_query,
            limit=limit,
        )

        if not memories:
            return ""

        memory_context = (
            format_memory_context(memories)
        )

        return str(memory_context or "").strip()

    except Exception:
        logger.exception(
            "Failed to search AgentMemory. "
            "customer_id=%s query=%s",
            clean_customer_id,
            clean_query,
        )

        return ""

def should_use_rag(
    intent: str,
) -> bool:
    """
    Quyết định lượt chat hiện tại có cần truy xuất tài liệu bằng RAG hay không.
    Sau này có thể mở rộng thêm:
    - knowledge-based
    - database-based
    - rule-based
    - API/tool-based
    """
    return intent == "document_question"

def answer_general_conversation(
    user_input: str,
    recent_context: list[dict[str, str]],
    memory_context: str,
) -> str:
    """
    Trả lời hội thoại thông thường mà không gọi RAG.
    Đây là fallback tạm thời cho tới khi hệ thống có General LLM Service riêng.
    Không sử dụng nguồn tài liệu.
    """
    clean_input = normalize_text(user_input)

    normalized = clean_input.lower()

    # Xử lý tình huống chatbot chậm và chưa phân loại được khách hàng.
    if (
        "chatbot" in normalized
        and (
            "chậm" in normalized
            or "phản hồi chậm" in normalized
        )
        and (
            "phân loại" in normalized
            or "nhóm người dùng" in normalized
            or "nhóm khách hàng" in normalized
        )
    ):
        return (
            "Mình hiểu rồi. Hiện chatbot của bạn đang có "
            "hai vấn đề chính: tốc độ phản hồi chậm và chưa "
            "phân loại được khách hàng. Hai vấn đề này nên "
            "được xử lý song song nhưng tách thành hai phần: "
            "tối ưu thời gian xử lý của chatbot và xây dựng "
            "tiêu chí phân nhóm khách hàng dựa trên thông tin "
            "họ cung cấp trong cuộc trò chuyện. "
            "Trước mắt, nên kiểm tra luồng gọi RAG, Memory "
            "và các dịch vụ bên ngoài để xác định bước nào "
            "đang làm phản hồi bị chậm."
        )

    # Một số tín hiệu người dùng đang trình bày khó khăn.
    problem_signals = [
        "đang gặp",
        "gặp vấn đề",
        "khó khăn",
        "bị chậm",
        "chưa thể",
        "chưa phân loại",
        "không hoạt động",
        "không chính xác",
        "chưa tốt",
    ]

    if any(
        signal in normalized
        for signal in problem_signals
    ):
        return (
            "Mình đã ghi nhận vấn đề bạn vừa chia sẻ. "
            "Nội dung này được xem là bối cảnh hiện tại "
            "của bạn, không phải câu hỏi cần tra cứu tài liệu. "
            "Để xử lý đúng, nên tách vấn đề thành nguyên nhân, "
            "ảnh hưởng và phần cần ưu tiên cải thiện trước."
        )

    if memory_context:
        return (
            "Mình hiểu nội dung bạn vừa chia sẻ và đã liên kết "
            "nó với những thông tin trước đó của bạn. "
            "Bạn có thể mô tả thêm kết quả hiện tại hoặc điểm "
            "đang gây khó khăn nhất để mình hỗ trợ đúng trọng tâm."
        )

    if recent_context:
        return (
            "Mình hiểu nội dung bạn vừa chia sẻ. "
            "Mình sẽ tiếp tục dựa trên bối cảnh của cuộc trò chuyện "
            "hiện tại thay vì tự động tra cứu tài liệu."
        )

    return (
        "Mình đã ghi nhận nội dung bạn vừa chia sẻ. "
        "Bạn có thể nói rõ hơn vấn đề hoặc kết quả "
        "mà bạn đang muốn đạt được."
    )

def get_chat_answer(
    user_input: str,
    customer_id: str,
    conversation_id: str,
    rag_pipeline,
    current_user_message_id: str | None = None,
) -> str:
    """
    Điều phối luồng trả lời chatbot.

    Luồng xử lý:

    1. Phân loại intent.
    2. Xử lý các intent đặc biệt.
    3. Lưu thông tin khách hàng nếu cần.
    4. Lấy recent context và AgentMemory.
    5. Chỉ gọi RAG khi intent là document_question.
    6. Các câu thông thường đi qua general conversation.
    7. Chỉ hiển thị nguồn trong nhánh RAG.
    """
    clean_user_input = str(user_input or "").strip()

    intent = classify_intent(clean_user_input)

    print(
        "[ROUTER]",
        {
            "input": clean_user_input,
            "intent": intent,
        },
    )

    use_rag = should_use_rag(intent)

    logger.info(
        "Chat routing. intent=%s use_rag=%s "
        "conversation_id=%s customer_id=%s",
        intent,
        use_rag,
        conversation_id,
        customer_id,
    )

    # 1. Memory recall
    if intent == "memory_recall":
        return answer_memory_recall(
            customer_id=customer_id,
            query=clean_user_input,
        )

    # 2. Lưu thông tin khách hàng    
    memory_save_intents = {
        "customer_information",
        "general_conversation",
    }

    if (
        intent in memory_save_intents
        and not is_memory_recall_question(
            clean_user_input
        )
    ):
        _save_user_memory_safely(
            customer_id=customer_id,
            user_input=clean_user_input,
        )

    # 3. Simple math
    if intent == "simple_math":
        return answer_simple_math(
            clean_user_input
        )

    # 4. Các rule đơn giản
    rule_answer = answer_by_rule(
        intent=intent,
        user_input=clean_user_input,
    )

    if rule_answer:
        return rule_answer

    # 5. Load recent conversation context
    recent_context = (
        _load_recent_context_safely(
            conversation_id=conversation_id,
            customer_id=customer_id,
            current_user_message_id=(
                current_user_message_id
            ),
        )
    )

    # Fallback khi app không truyền current_user_message_id.
    if (
        not current_user_message_id
        and recent_context
    ):
        last_message = recent_context[-1]

        last_role = str(
            last_message.get(
                "role",
                "",
            )
        ).strip().lower()

        last_content = str(
            last_message.get(
                "content",
                "",
            )
        ).strip()

        if (
            last_role == "user"
            and last_content == clean_user_input
        ):
            recent_context = (
                recent_context[:-1]
            )

    # 6. Load AgentMemory context
    memory_context = (
        _load_memory_context_safely(
            customer_id=customer_id,
            query=clean_user_input,
            limit=5,
        )
    )

    if intent == "customer_information":
        return answer_customer_information(
            user_input=clean_user_input,
            memory_context=memory_context,
        )

    # 7. General conversation
    # Không gọi RAG. Không hiển thị nguồn tài liệu.
    if not use_rag:
        return answer_general_conversation(
            user_input=clean_user_input,
            recent_context=recent_context,
            memory_context=memory_context,
        )

    # 8. RAG document question
    # Chỉ chạy khi use_rag=True.
    try:
        rag_response = (
            rag_pipeline.answer(
                question=clean_user_input,
                chat_history=recent_context,
                memory_context=memory_context,
            )
        )

        answer = normalize_text(
            getattr(
                rag_response,
                "answer",
                "",
            )
        )

        sources = getattr(
            rag_response,
            "sources",
            [],
        ) or []

        if not answer:
            return ("Mình chưa nhận được câu trả lời phù hợp từ hệ thống tài liệu.")

        # Bước 5:
        # Chỉ hiện nguồn trong nhánh RAG.
        if not sources:
            return answer

        return (
            answer + format_rag_sources(sources)
        )

    except Exception:
        logger.exception(
            "Failed to generate chatbot answer. "
            "conversation_id=%s customer_id=%s "
            "intent=%s",
            conversation_id,
            customer_id,
            intent,
        )

        return ("Hiện tại hệ thống đang gặp lỗi khi truy xuất tài liệu. Bạn vui lòng thử lại.")