from dataclasses import dataclass
from typing import List

from rag.llm_client import OpenRouterLLMClient
from rag.retrieval import RetrievalOrchestrator, RetrievedContext


@dataclass
class RAGResponse:
    answer: str
    sources: List[RetrievedContext]
    context: str


class RAGPipeline:
    def __init__(
        self,
        retrieval_orchestrator: RetrievalOrchestrator,
        llm_client: OpenRouterLLMClient,
    ):
        self.retrieval_orchestrator = retrieval_orchestrator
        self.llm_client = llm_client

    def answer(self, question: str) -> RAGResponse:
        question = question.strip()

        if self._is_small_talk(question):
            return RAGResponse(
                answer=(
                    "Hi bạn 👋 Mình đang là chatbot RAG, có thể trả lời dựa trên "
                    "tài liệu đã được nạp vào hệ thống. Bạn muốn hỏi gì về tài liệu?"
                ),
                sources=[],
                context="",
            )

        retrieved_items = self.retrieval_orchestrator.retrieve(question)

        if not retrieved_items:
            return RAGResponse(
                answer="Mình chưa tìm thấy thông tin phù hợp trong tài liệu để trả lời câu hỏi này.",
                sources=[],
                context="",
            )

        context = self._build_context_from_items(retrieved_items)

        system_prompt = (
            "You are a RAG assistant. "
            "Answer the user's question using only the provided context. "
            "If the context does not contain enough information, say that the document does not provide enough information. "
            "Do not invent facts. "
            "Answer clearly and concisely."
        )

        user_prompt = f"""
Context:
{context}

Question:
{question}

Answer:
"""

        answer = self.llm_client.generate(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=1000,
            temperature=0.1,
        )

        if self._is_insufficient_answer(answer):
            return RAGResponse(
                answer="Mình chưa tìm thấy thông tin phù hợp trong tài liệu để trả lời câu hỏi này.",
                sources=[],
                context=context,
            )

        return RAGResponse(
            answer=answer,
            sources=retrieved_items,
            context=context,
        )

    def _build_context_from_items(self, items: List[RetrievedContext]) -> str:
        context_parts = []

        for index, item in enumerate(items, start=1):
            context_parts.append(
                f"[Context {index}]\n"
                f"File: {item.file_name}\n"
                f"Page: {item.page}\n"
                f"Chunk index: {item.chunk_index}\n"
                f"Content:\n{item.content}"
            )

        return "\n\n".join(context_parts)

    def _is_small_talk(self, question: str) -> bool:
        normalized_question = question.lower().strip()

        small_talk_keywords = [
            "hi",
            "hello",
            "hey",
            "chào",
            "xin chào",
            "alo",
            "yo",
            "good morning",
            "good afternoon",
            "good evening",
        ]

        return normalized_question in small_talk_keywords or normalized_question.startswith(
            tuple(keyword + " " for keyword in small_talk_keywords)
        )

    def _is_insufficient_answer(self, answer: str) -> bool:
        normalized_answer = answer.lower()

        insufficient_phrases = [
            "does not provide enough information",
            "not provide enough information",
            "not enough information",
            "không đủ thông tin",
            "chưa tìm thấy thông tin",
            "không tìm thấy thông tin",
        ]

        return any(phrase in normalized_answer for phrase in insufficient_phrases)