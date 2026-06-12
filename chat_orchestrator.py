import logging
from typing import Any

from config import RECENT_CONTEXT_LIMIT
from conversation_service import get_recent_context
from intent_service import (
    classify_intent,
    is_memory_recall_question,
)
from memory_service import (
    save_memory,
    search_memory,
    format_memory_context,
)
from rule_response_service import (
    answer_by_rule,
    answer_customer_information,
    answer_general_conversation,
    answer_memory_recall,
    answer_simple_math,
    build_memory_candidate,
    format_rag_sources,
    should_use_rag,
    strip_recall_prefix,
)

logger = logging.getLogger(__name__)

ROUTE_RULE = "rule"
ROUTE_MEMORY_RECALL = "memory_recall"
ROUTE_CUSTOMER_INFO = "customer_information"
ROUTE_RAG = "rag"
ROUTE_GENERAL = "general_conversation"
ROUTE_AGENT = "agent"

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

    memory_candidate = build_memory_candidate(user_input)

    if memory_candidate is None:
        logger.info(
            "No memory candidate detected. customer_id=%s input=%s",
            clean_customer_id,
            user_input,
        )
        return None

    content, concepts = memory_candidate

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
            exclude_message_id=current_user_message_id,
        )

        if not isinstance(recent_context, list):
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

        memory_context = format_memory_context(memories)

        return str(memory_context or "").strip()

    except Exception:
        logger.exception(
            "Failed to search AgentMemory. "
            "customer_id=%s query=%s",
            clean_customer_id,
            clean_query,
        )

        return ""

def decide_route(
    intent: str,
    user_input: str,
) -> str:
    """
    Quyết định yêu cầu hiện tại nên đi theo luồng xử lý nào.
    Hàm này chỉ quyết định route, không tạo câu trả lời.
    """
    clean_input = str(user_input or "").strip()

    if intent in [
        "empty",
        "greeting",
        "thanks",
        "upload_info",
        "bot_capability",
        "simple_math",
    ]:
        return ROUTE_RULE

    if is_memory_recall_question(clean_input):
        return ROUTE_MEMORY_RECALL

    if intent == "customer_information":
        return ROUTE_CUSTOMER_INFO

    if should_use_rag(intent):
        return ROUTE_RAG

    # Chưa triển khai tool calling/agent ở bước này.
    # Để sẵn route để sau này mở rộng.
    if intent in [
        "tool_action",
        "agent_action",
    ]:
        return ROUTE_AGENT

    return ROUTE_GENERAL

def execute_route(
    route: str,
    intent: str,
    user_input: str,
    customer_id: str,
    rag_pipeline,
    recent_context: list[dict[str, str]],
    memory_context: str,
) -> str:
    """
    Thực thi route đã được quyết định.
    Orchestrator chỉ gọi đúng handler, không ôm logic rule chi tiết.
    """
    if route == ROUTE_RULE:
        if intent == "simple_math":
            return answer_simple_math(user_input)

        rule_answer = answer_by_rule(
            intent=intent,
            user_input=user_input,
        )

        if rule_answer:
            return rule_answer

        return answer_general_conversation(
            user_input=user_input,
            recent_context=recent_context,
            memory_context=memory_context,
        )

    if route == ROUTE_MEMORY_RECALL:
        return answer_memory_recall(
            customer_id=customer_id,
            query=strip_recall_prefix(user_input),
        )

    if route == ROUTE_CUSTOMER_INFO:
        return answer_customer_information(
            user_input=user_input,
            memory_context=memory_context,
        )

    if route == ROUTE_RAG:
        rag_response = rag_pipeline.answer(
            question=user_input,
            chat_history=recent_context,
            memory_context=memory_context,
        )

        answer = rag_response.answer

        if rag_response.sources:
            answer += format_rag_sources(rag_response.sources)

        return answer

    if route == ROUTE_AGENT:
        return ("Mình đã nhận được yêu cầu thao tác, nhưng phần gọi công cụ/Agentic AI hiện chưa được bật trong bản MVP này.")

    return answer_general_conversation(
        user_input=user_input,
        recent_context=recent_context,
        memory_context=memory_context,
    )

def get_chat_answer(
    user_input: str,
    conversation_id: str,
    customer_id: str,
    rag_pipeline,
    current_user_message_id: str | None = None,
) -> str:
    """
    Luồng điều phối chính của chatbot.
    Vai trò:
    - Nhận input từ app.py.
    - Phân loại intent.
    - Load recent context.
    - Load memory context.
    - Lưu memory nếu có thông tin quan trọng.
    - Quyết định route.
    - Gọi đúng handler xử lý.
    """
    clean_input = str(user_input or "").strip()
    intent = classify_intent(clean_input)

    recent_context = _load_recent_context_safely(
        conversation_id=conversation_id,
        customer_id=customer_id,
        current_user_message_id=current_user_message_id,
    )

    memory_context = _load_memory_context_safely(
        customer_id=customer_id,
        query=clean_input,
        limit=5,
    )

    # Lưu memory trước khi trả lời, nhưng không để lỗi memory làm hỏng chatbot.
    _save_user_memory_safely(
        customer_id=customer_id,
        user_input=clean_input,
    )

    route = decide_route(
        intent=intent,
        user_input=clean_input,
    )

    print(
        "[ORCHESTRATOR]",
        {
            "input": clean_input,
            "intent": intent,
            "route": route,
            "conversation_id": conversation_id,
            "customer_id": customer_id,
        },
    )

    return execute_route(
        route=route,
        intent=intent,
        user_input=clean_input,
        customer_id=customer_id,
        rag_pipeline=rag_pipeline,
        recent_context=recent_context,
        memory_context=memory_context,
    )