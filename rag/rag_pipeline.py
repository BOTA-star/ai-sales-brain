from dataclasses import dataclass
from typing import Optional

from rag.llm_client import LLMClient
from rag.retrieval import (
    RetrievalOrchestrator,
    RetrievedContext,
)


@dataclass
class RAGResponse:
    answer: str
    sources: list[RetrievedContext]
    context: str
    grounded: bool=False

class RAGPipeline:
    """
    Luồng xử lý RAG:

    1. Nhận câu hỏi.
    2. Truy vấn tài liệu liên quan.
    3. Xây dựng context.
    4. Gửi context, lịch sử chat và câu hỏi tới LLM.
    5. Trả về câu trả lời và nguồn tham khảo.
    """
    def __init__(
        self,
        retrieval_orchestrator: RetrievalOrchestrator,
        llm_client: LLMClient,
    ) -> None:
        self.retrieval_orchestrator = (
            retrieval_orchestrator
        )
        self.llm_client = llm_client

    def answer(
        self,
        question: str,
        chat_history: Optional[
            list[dict[str, str]]
        ] = None,
    ) -> RAGResponse:
        clean_question = (
            question or ""
        ).strip()

        if not clean_question:
            return RAGResponse(
                answer=(
                    "Bạn vui lòng nhập câu hỏi."
                ),
                sources=[],
                context="",
            )

        # Giữ lại để test RAGPipeline trực tiếp.
        # Khi chạy qua chat_orchestrator, phần greeting
        # thường đã được xử lý trước.
        if self._is_small_talk(
            clean_question
        ):
            return RAGResponse(
                answer=(
                    "Hi bạn 👋 Mình đang là chatbot RAG, "
                    "có thể trả lời dựa trên tài liệu đã "
                    "được nạp vào hệ thống. Bạn muốn hỏi "
                    "gì về tài liệu?"
                ),
                sources=[],
                context="",
            )

        safe_history = self._sanitize_history(
            chat_history or []
        )

        retrieval_query = (
            self._build_retrieval_query(
                question=clean_question,
                chat_history=safe_history,
            )
        )

        retrieved_items = (
            self.retrieval_orchestrator.retrieve(
                retrieval_query
            )
        )

        if not retrieved_items:
            return RAGResponse(
                answer=(
                    "Mình chưa tìm thấy thông tin phù hợp "
                    "trong tài liệu để trả lời câu hỏi này."
                ),
                sources=[],
                context="",
            )

        context = (
            self._build_context_from_items(
                retrieved_items
            )
        )

        messages = self._build_messages(
            question=clean_question,
            context=context,
            chat_history=safe_history,
        )

        answer = self.llm_client.generate(
            messages=messages,
            max_tokens=1000,
            temperature=0.1,
        )

        clean_answer = (
            answer or ""
        ).strip()

        if not clean_answer:
            return RAGResponse(
                answer=(
                    "Mình chưa nhận được câu trả lời "
                    "phù hợp từ mô hình."
                ),
                sources=[],
                context=context,
            )

        if self._is_insufficient_answer(
            clean_answer
        ):
            return RAGResponse(
                answer=(
                    "Mình chưa tìm thấy thông tin phù hợp "
                    "trong tài liệu để trả lời câu hỏi này."
                ),
                sources=[],
                context=context,
                grounded=False
            )

        return RAGResponse(
            answer=clean_answer,
            sources=retrieved_items,
            context=context,
            grounded=True,
        )

    def _build_messages(
        self,
        question: str,
        context: str,
        chat_history: list[
            dict[str, str]
        ],
    ) -> list[dict[str, str]]:
        """
        Xây dựng messages gửi tới Ollama hoặc OpenRouter.

        Lịch sử chat chỉ giúp hiểu câu hỏi nối tiếp.
        Context từ tài liệu mới là nguồn thông tin chính.
        """

        system_prompt = (
            "Bạn là trợ lý RAG. "
            "Chỉ trả lời dựa trên nội dung trong phần "
            "TÀI LIỆU THAM KHẢO. "
            "Lịch sử hội thoại chỉ dùng để hiểu câu hỏi nối tiếp, "
            "không được xem là nguồn dữ liệu xác thực. "
            "Nếu tài liệu không trực tiếp chứa thông tin cần thiết "
            "để trả lời câu hỏi, chỉ trả về chính xác chuỗi sau: "
            "__INSUFFICIENT_CONTEXT__. "
            "Không thêm giải thích, không đoán và không dùng "
            "kiến thức bên ngoài tài liệu. "
            "Nếu đủ thông tin, hãy trả lời bằng cùng ngôn ngữ "
            "với người dùng, rõ ràng và ngắn gọn."
        )

        messages: list[
            dict[str, str]
        ] = [
            {
                "role": "system",
                "content": system_prompt,
            }
        ]

        messages.extend(chat_history)

        user_prompt = (
            "TÀI LIỆU THAM KHẢO:\n"
            f"{context}\n\n"
            "CÂU HỎI HIỆN TẠI:\n"
            f"{question}"
        )

        messages.append(
            {
                "role": "user",
                "content": user_prompt,
            }
        )

        return messages

    def _build_retrieval_query(
        self,
        question: str,
        chat_history: list[
            dict[str, str]
        ],
    ) -> str:
        """
        Thêm tối đa hai câu hỏi trước vào truy vấn tìm kiếm.

        Hữu ích với câu nối tiếp như:
        - Còn giá thì sao?
        - Ưu điểm của nó là gì?
        """

        previous_user_messages = [
            message["content"]
            for message in chat_history
            if (
                message.get("role") == "user"
                and message.get("content")
            )
        ][-2:]

        if not previous_user_messages:
            return question

        previous_context = "\n".join(
            previous_user_messages
        )

        return (
            "Các câu hỏi trước:\n"
            f"{previous_context}\n\n"
            "Câu hỏi hiện tại:\n"
            f"{question}"
        )

    def _sanitize_history(
        self,
        chat_history: list[
            dict[str, str]
        ],
    ) -> list[dict[str, str]]:
        """
        Chỉ giữ user và assistant.

        System message cũ không được đưa lại vào prompt
        để tránh ghi đè system prompt của RAG.
        """

        safe_history: list[
            dict[str, str]
        ] = []

        for message in chat_history:
            if not isinstance(
                message,
                dict,
            ):
                continue

            role = str(
                message.get(
                    "role",
                    "",
                )
            ).strip().lower()

            content = str(
                message.get(
                    "content",
                    "",
                )
            ).strip()

            if role not in {
                "user",
                "assistant",
            }:
                continue

            if not content:
                continue

            safe_history.append(
                {
                    "role": role,
                    "content": content,
                }
            )

        # Giới hạn lịch sử để tránh prompt quá dài.
        return safe_history[-8:]

    def _build_context_from_items(
        self,
        items: list[RetrievedContext],
    ) -> str:
        context_parts: list[str] = []

        for index, item in enumerate(
            items,
            start=1,
        ):
            context_parts.append(
                f"[Context {index}]\n"
                f"File: {item.file_name}\n"
                f"Page: {item.page}\n"
                f"Chunk index: "
                f"{item.chunk_index}\n"
                f"Content:\n"
                f"{item.content}"
            )

        return "\n\n".join(
            context_parts
        )

    def _is_small_talk(
        self,
        question: str,
    ) -> bool:
        normalized_question = (
            question.lower().strip()
        )

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

        if (
            normalized_question
            in small_talk_keywords
        ):
            return True

        return normalized_question.startswith(
            tuple(
                keyword + " "
                for keyword
                in small_talk_keywords
            )
        )

    def _is_insufficient_answer(
        self,
        answer: str,
    ) -> bool:
        normalized_answer = (
            answer or ""
        ).strip().lower()

        insufficient_phrases = [
            "__insufficient_context__",
            "does not provide enough information",
            "not provide enough information",
            "not enough information",
            "không đủ thông tin",
            "chưa đủ thông tin",
            "chưa tìm thấy thông tin",
            "không tìm thấy thông tin",
            "chưa cung cấp đủ thông tin",
            "tài liệu không cung cấp",
            "không được nêu rõ trong tài liệu",
            "không được đề cập trong tài liệu",
            "không thể trả lời chính xác",
            "thông tin có sẵn không đủ",
        ]

        return any(
            phrase in normalized_answer
            for phrase in insufficient_phrases
        )