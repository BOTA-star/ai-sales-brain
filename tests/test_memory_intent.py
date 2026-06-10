import pytest
import chat_orchestrator
from intent_service import classify_intent
from chat_orchestrator import (
    _build_memory_candidate,
    _extract_need,
    _rank_memories,
    answer_memory_recall,
)

@pytest.mark.parametrize(
    ("text", "expected_intent"),
    [
        (
            "Nhu cầu hiện tại của mình là gì?",
            "memory_recall",
        ),
        (
            "Vậy nhu cầu hiện tại mình là gì?",
            "memory_recall",
        ),
        (
            "Thế ưu tiên hiện tại của tôi là gì?",
            "memory_recall",
        ),
        (
            "Bây giờ mình ưu tiên chatbot hỗ trợ sale.",
            "customer_information",
        ),
        (
            "Hiện tại mình ưu tiên phân loại khách hàng.",
            "customer_information",
        ),
        (
            "Vậy bây giờ nhu cầu của mình là gì?",
            "memory_recall",
        ),
        (
            "Bây giờ nhu cầu của tôi là gì?",
            "memory_recall",
        ),
        (
            "Hiện tại nhu cầu của mình là gì?",
            "memory_recall",
        ),
    ],
)
def test_memory_intent(
    text: str,
    expected_intent: str,
):
    assert classify_intent(text) == expected_intent

@pytest.mark.parametrize(
    "text",
    [
        "Nhu cầu hiện tại của mình là gì?",
        "Vậy nhu cầu hiện tại mình là gì?",
        "Thế ưu tiên hiện tại của tôi là gì?",
    ],
)
def test_recall_question_is_not_memory_candidate(
    text: str,
):
    assert _build_memory_candidate(text) is None

@pytest.mark.parametrize(
    ("text", "expected_need"),
    [
        (
            "Bây giờ mình ưu tiên chatbot hỗ trợ sale.",
            "chatbot hỗ trợ sale",
        ),
        (
            "Hiện tại mình ưu tiên phân loại khách hàng.",
            "phân loại khách hàng",
        ),
        (
            (
                "Bây giờ mình ưu tiên 1 chatbot hỗ trợ "
                "bên công tác sale và phân loại khách hàng."
            ),
            (
                "1 chatbot hỗ trợ bên công tác sale "
                "và phân loại khách hàng"
            ),
        ),
    ],
)
def test_extract_need_from_priority(
    text: str,
    expected_need: str,
):
    assert _extract_need(text) == expected_need

def test_latest_memory_is_ranked_first():
    memories = [
        {
            "content": (
                "Khách hàng cho biết: "
                "Mình cần chatbot tăng năng suất làm việc."
            ),
            "createdAt": "2026-06-10T08:00:00Z",
            "score": 0.99,
        },
        {
            "content": (
                "Khách hàng cho biết: "
                "Bây giờ mình ưu tiên chatbot hỗ trợ sale "
                "và phân loại khách hàng."
            ),
            "createdAt": "2026-06-10T09:00:00Z",
            "score": 0.50,
        },
    ]

    ranked_memories = _rank_memories(
        memories
    )

    assert ranked_memories[0]["content"] == (
        "Khách hàng cho biết: "
        "Bây giờ mình ưu tiên chatbot hỗ trợ sale "
        "và phân loại khách hàng."
    )

def test_answer_memory_recall_returns_latest_need(
    monkeypatch,
):
    memories = [
        {
            "content": (
                "Khách hàng cho biết: "
                "Mình cần một chatbot để hỗ trợ "
                "tăng năng suất làm việc."
            ),
            "concepts": [
                "need",
                "chatbot",
                "tăng hiệu suất công việc",
            ],
            "createdAt": "2026-06-10T08:00:00Z",
            "score": 0.99,
        },
        {
            "content": (
                "Khách hàng cho biết: "
                "Bây giờ mình ưu tiên 1 chatbot hỗ trợ "
                "bên công tác sale và phân loại khách hàng."
            ),
            "concepts": [
                "priority",
                "chatbot",
                "sale",
                "phân loại khách hàng",
            ],
            "createdAt": "2026-06-10T09:00:00Z",
            "score": 0.50,
        },
    ]

    def fake_search_memory(
        customer_id: str,
        query: str,
        limit: int,
    ):
        return memories

    monkeypatch.setattr(
        chat_orchestrator,
        "search_memory",
        fake_search_memory,
    )

    answer = answer_memory_recall(
        customer_id="test-customer",
        query="Vậy nhu cầu hiện tại mình là gì?",
    )

    normalized_answer = answer.casefold()

    assert "sale" in normalized_answer
    assert "phân loại khách hàng" in normalized_answer
    assert "tăng năng suất" not in normalized_answer