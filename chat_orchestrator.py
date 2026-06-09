import ast
import logging
import operator
from typing import Any

from config import RECENT_CONTEXT_LIMIT
from conversation_service import get_recent_context
from intent_service import (
    classify_intent,
    extract_math_expression,
    normalize_text,
)


logger = logging.getLogger(__name__)


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
    Tính biểu thức toán học đơn giản
    mà không sử dụng eval().
    """

    if isinstance(node, ast.Expression):
        return _evaluate_math_node(
            node.body
        )

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
        left_value = _evaluate_math_node(
            node.left
        )

        right_value = _evaluate_math_node(
            node.right
        )

        operation = (
            _ALLOWED_BINARY_OPERATORS[
                type(node.op)
            ]
        )

        return operation(
            left_value,
            right_value,
        )

    if (
        isinstance(node, ast.UnaryOp)
        and type(node.op)
        in _ALLOWED_UNARY_OPERATORS
    ):
        operand_value = (
            _evaluate_math_node(
                node.operand
            )
        )

        operation = (
            _ALLOWED_UNARY_OPERATORS[
                type(node.op)
            ]
        )

        return operation(
            operand_value
        )

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
        return source.get(
            key,
            default,
        )

    return getattr(
        source,
        key,
        default,
    )


def format_rag_sources(
    sources: list[Any],
) -> str:
    """
    Format nguồn tham khảo.
    """

    if not sources:
        return ""

    source_lines = [
        "\n\n---\nNguồn tham khảo:"
    ]

    for index, source in enumerate(
        sources,
        start=1,
    ):
        file_name = get_source_value(
            source,
            "file_name",
        )

        page = get_source_value(
            source,
            "page",
        )

        chunk_index = get_source_value(
            source,
            "chunk_index",
        )

        source_lines.append(
            f"{index}. File: {file_name} "
            f"| Page: {page} "
            f"| Chunk: {chunk_index}"
        )

    return "\n".join(
        source_lines
    )


def answer_simple_math(
    user_input: str,
) -> str:
    """
    Trả lời phép tính đơn giản bằng AST.
    """

    expression_text = (
        extract_math_expression(
            user_input
        )
    )

    if not expression_text:
        return (
            "Mình chưa nhận diện được "
            "phép tính trong câu hỏi."
        )

    try:
        expression = ast.parse(
            expression_text,
            mode="eval",
        )

        result = _evaluate_math_node(
            expression
        )

        # Hiển thị 2 thay vì 2.0
        # nếu kết quả là số nguyên.
        if (
            isinstance(result, float)
            and result.is_integer()
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
        return (
            "Mình chưa xử lý được "
            "phép tính này."
        )


def answer_by_rule(
    intent: str,
) -> str:
    """
    Các intent không cần RAG
    được trả lời trực tiếp bằng rule.
    """

    if intent == "empty":
        return (
            "Bạn vui lòng nhập câu hỏi "
            "trước nha."
        )

    if intent == "greeting":
        return (
            "Hi bạn 👋 Mình là chatbot RAG demo. "
            "Mình có thể trả lời câu hỏi dựa trên "
            "tài liệu đã được nạp vào hệ thống."
        )

    if intent == "thanks":
        return (
            "Không có gì nha 😊 "
            "Bạn cần hỏi thêm gì về tài liệu "
            "thì cứ nhắn mình."
        )

    if intent == "upload_info":
        return (
            "Bạn có thể gửi các tài liệu như "
            "PDF, DOCX hoặc TXT. "
            "Tuy nhiên hiện tại bản demo đang "
            "dùng tài liệu được nạp sẵn trong lúc code. "
            "Bước tiếp theo có thể thêm chức năng "
            "upload file để bạn tự nạp tài liệu."
        )

    if intent == "bot_capability":
        return (
            "Hiện tại mình được thiết kế theo chế độ "
            "Strict RAG, nên chủ yếu trả lời dựa trên "
            "các tài liệu đã được nạp vào hệ thống. "
            "Nếu tài liệu không có thông tin phù hợp, "
            "mình sẽ thông báo là chưa tìm thấy thay vì "
            "tự dùng kiến thức bên ngoài để trả lời."
        )

    return ""


def _load_recent_context_safely(
    conversation_id: str,
    customer_id: str,
    current_user_message_id: str | None,
) -> list[dict[str, str]]:
    """
    Load short-term context nhưng không để lỗi history
    làm hỏng toàn bộ lượt trả lời.

    Message user hiện tại được loại khỏi history
    bằng current_user_message_id.
    """

    try:
        return get_recent_context(
            conversation_id=conversation_id,
            customer_id=customer_id,
            limit=RECENT_CONTEXT_LIMIT,
            exclude_message_id=(
                current_user_message_id
            ),
        )

    except Exception:
        logger.exception(
            "Failed to load recent chat context. "
            "conversation_id=%s customer_id=%s",
            conversation_id,
            customer_id,
        )

        return []


def get_chat_answer(
    user_input: str,
    conversation_id: str,
    customer_id: str,
    rag_pipeline: Any,
    current_user_message_id: str | None = None,
) -> str:
    """
    Hàm điều phối chính:

    1. Phân loại intent.
    2. Intent đơn giản được trả lời bằng rule.
    3. Câu hỏi tài liệu mới load short-term context.
    4. Gọi RAG với lịch sử hội thoại.
    5. Chỉ hiển thị nguồn khi kết quả grounded.
    """

    clean_user_input = normalize_text(
        user_input
    )

    intent = classify_intent(
        clean_user_input
    )

    if intent == "simple_math":
        return answer_simple_math(
            clean_user_input
        )

    if intent != "document_question":
        return answer_by_rule(
            intent
        )

    recent_context = (
        _load_recent_context_safely(
            conversation_id=conversation_id,
            customer_id=customer_id,
            current_user_message_id=(
                current_user_message_id
            ),
        )
    )

    try:
        rag_response = (
            rag_pipeline.answer(
                question=clean_user_input,
                chat_history=recent_context,
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

        grounded = bool(
            getattr(
                rag_response,
                "grounded",
                False,
            )
        )

        if not answer:
            return (
                "Tài liệu chưa cung cấp đủ "
                "thông tin để trả lời câu hỏi này."
            )

        if (
            not grounded
            or not sources
        ):
            return answer

        return (
            answer
            + format_rag_sources(
                sources
            )
        )

    except Exception:
        logger.exception(
            "RAG processing failed. "
            "conversation_id=%s customer_id=%s",
            conversation_id,
            customer_id,
        )

        return (
            "Hiện tại hệ thống đang gặp lỗi "
            "trong quá trình xử lý. "
            "Bạn vui lòng thử lại sau."
        )