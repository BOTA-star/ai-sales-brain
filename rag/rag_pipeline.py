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
    grounded: bool = False


class RAGPipeline:
    """
    Luồng xử lý RAG kết hợp AgentMemory:

    1. Nhận câu hỏi hiện tại.
    2. Chuẩn hóa lịch sử hội thoại.
    3. Nhận customer memory từ AgentMemory.
    4. Truy vấn tài liệu liên quan.
    5. Xây dựng prompt gồm:
       - System instruction
       - Customer memory
       - Recent conversation
       - Knowledge base
       - Current question
    6. Gửi messages tới LLM.
    7. Trả về câu trả lời và nguồn tham khảo.
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
        memory_context: str = "",
    ) -> RAGResponse:
        """
        Trả lời câu hỏi dựa trên:

        - Customer memory từ AgentMemory.
        - Lịch sử hội thoại gần nhất.
        - Tài liệu được truy xuất từ RAG.
        """

        clean_question = (
            question or ""
        ).strip()

        if not clean_question:
            return RAGResponse(
                answer="Bạn vui lòng nhập câu hỏi.",
                sources=[],
                context="",
                grounded=False,
            )

        # Giữ lại để kiểm thử RAGPipeline trực tiếp.
        # Khi chạy qua chat_orchestrator,
        # greeting thường được xử lý trước.
        if self._is_small_talk(
            clean_question
        ):
            return RAGResponse(
                answer=(
                    "Hi bạn 👋 Mình đang là chatbot RAG, "
                    "có thể hỗ trợ dựa trên tài liệu đã "
                    "được nạp và những thông tin đã ghi nhớ "
                    "trong quá trình trao đổi. "
                    "Bạn muốn hỏi gì?"
                ),
                sources=[],
                context="",
                grounded=False,
            )

        safe_history = self._sanitize_history(
            chat_history or []
        )

        safe_memory_context = (
            self._sanitize_memory_context(
                memory_context
            )
        )

        retrieval_query = (
            self._build_retrieval_query(
                question=clean_question,
                chat_history=safe_history,
            )
        )

        retrieved_items: list[
            RetrievedContext
        ] = []

        try:
            retrieved_items = (
                self.retrieval_orchestrator.retrieve(
                    retrieval_query
                )
                or []
            )
        except Exception as error:
            # Retrieval tài liệu lỗi nhưng vẫn có thể
            # trả lời bằng memory và lịch sử chat.
            print(
                "[RAG warning] Không thể truy xuất "
                f"tài liệu: {error}"
            )

        context = ""

        if retrieved_items:
            context = (
                self._build_context_from_items(
                    retrieved_items
                )
            )

        # Nếu không có cả tài liệu lẫn memory,
        # không cần gọi LLM để tránh hallucination.
        if (
            not retrieved_items
            and not safe_memory_context
        ):
            return RAGResponse(
                answer=(
                    "Mình chưa tìm thấy thông tin phù hợp "
                    "trong tài liệu hoặc dữ liệu đã ghi nhớ "
                    "để trả lời câu hỏi này."
                ),
                sources=[],
                context="",
                grounded=False,
            )

        messages = self._build_messages(
            question=clean_question,
            context=context,
            chat_history=safe_history,
            memory_context=safe_memory_context,
        )

        try:
            answer = self.llm_client.generate(
                messages=messages,
                max_tokens=1000,
                temperature=0.1,
            )
        except Exception as error:
            print(
                "[LLM error] Không thể sinh "
                f"câu trả lời: {error}"
            )

            return RAGResponse(
                answer=(
                    "Hiện tại mình chưa thể xử lý "
                    "câu hỏi này. Bạn vui lòng thử lại."
                ),
                sources=[],
                context=context,
                grounded=False,
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
                grounded=False,
            )

        if self._is_insufficient_answer(
            clean_answer
        ):
            return RAGResponse(
                answer=(
                    "Mình chưa tìm thấy đủ thông tin "
                    "trong tài liệu hoặc dữ liệu đã ghi nhớ "
                    "để trả lời chính xác câu hỏi này."
                ),
                sources=[],
                context=context,
                grounded=False,
            )

        return RAGResponse(
            answer=clean_answer,
            sources=retrieved_items,
            context=context,
            grounded=bool(
                retrieved_items
                or safe_memory_context
            ),
        )

    def _build_messages(
        self,
        question: str,
        context: str,
        chat_history: list[
            dict[str, str]
        ],
        memory_context: str = "",
    ) -> list[dict[str, str]]:
        """
        Xây dựng messages gửi tới Ollama hoặc OpenRouter.

        Thứ tự context:

        1. System instruction.
        2. Customer memory.
        3. Recent conversation.
        4. Knowledge base.
        5. Current question.
        """

        safe_history = (
            chat_history or []
        )

        clean_memory_context = (
            memory_context or ""
        ).strip()

        clean_document_context = (
            context or ""
        ).strip()

        system_prompt = """
Bạn là trợ lý AI hỗ trợ bán hàng và chăm sóc khách hàng.

Bạn có thể sử dụng ba nguồn ngữ cảnh:

1. Customer memory:
Thông tin dài hạn đã được ghi nhớ về khách hàng từ những lần trao đổi trước.

2. Recent conversation:
Các tin nhắn gần nhất trong cuộc hội thoại hiện tại.

3. Knowledge base:
Thông tin được truy xuất từ tài liệu của doanh nghiệp.

Quy tắc trả lời:

- Chỉ sử dụng những thông tin có trong customer memory,
  recent conversation hoặc knowledge base.
- Không tự suy đoán hoặc tạo thêm thông tin không có căn cứ.
- Không nhắc đến AgentMemory, hệ thống memory, vector database,
  project ID, memory ID hoặc metadata nội bộ.
- Không nói rằng bạn đang đọc memory của khách hàng.
- Hãy sử dụng thông tin đã ghi nhớ một cách tự nhiên,
  giống như tiếp tục một cuộc trò chuyện trước đó.
- Customer memory được dùng để hiểu nhu cầu, sở thích,
  bối cảnh và thông tin dài hạn của khách hàng.
- Knowledge base là nguồn chính để trả lời về sản phẩm,
  dịch vụ, giá, chính sách và thông tin doanh nghiệp.
- Recent conversation được dùng để hiểu các câu hỏi nối tiếp,
  đại từ hoặc nội dung đang được nhắc tới.
- Nếu customer memory và recent conversation mâu thuẫn,
  ưu tiên thông tin mới hơn trong recent conversation.
- Nếu customer memory mâu thuẫn với knowledge base về
  sản phẩm hoặc chính sách, ưu tiên knowledge base.
- Không biến một nhận định hoặc suy đoán của trợ lý trước đó
  thành sự thật về khách hàng.
- Nếu không đủ thông tin để trả lời chính xác,
  hãy nói rõ rằng chưa đủ thông tin.
- Trả lời bằng tiếng Việt tự nhiên, rõ ràng và đúng trọng tâm,
  trừ khi người dùng yêu cầu ngôn ngữ khác.
        """

        messages: list[
            dict[str, str]
        ] = [
            {
                "role": "system",
                "content": system_prompt.strip(),
            }
        ]

        if clean_memory_context:
            messages.append(
                {
                    "role": "system",
                    "content": (
                        "CUSTOMER MEMORY:\n"
                        "Dưới đây là thông tin dài hạn "
                        "đã được xác nhận hoặc ghi nhận "
                        "về khách hàng:\n\n"
                        f"{clean_memory_context}"
                    ),
                }
            )

        # Lịch sử hội thoại nằm sau memory để LLM
        # ưu tiên thông tin mới trong phiên hiện tại.
        messages.extend(
            safe_history
        )

        if clean_document_context:
            document_section = (
                "KNOWLEDGE BASE:\n"
                f"{clean_document_context}"
            )
        else:
            document_section = (
                "KNOWLEDGE BASE:\n"
                "Không tìm thấy tài liệu phù hợp "
                "cho câu hỏi hiện tại."
            )

        user_prompt = (
            f"{document_section}\n\n"
            "CURRENT QUESTION:\n"
            f"{question}\n\n"
            "Hãy trả lời câu hỏi hiện tại bằng cách "
            "kết hợp hợp lý customer memory, "
            "recent conversation và knowledge base. "
            "Không hiển thị tên các nguồn ngữ cảnh "
            "hoặc thông tin kỹ thuật nội bộ."
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
        - Giải pháp đó triển khai bao lâu?
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
        Chỉ giữ message có role user hoặc assistant.

        System message cũ không được đưa lại vào prompt
        để tránh ghi đè system prompt của RAGPipeline.
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

            raw_content = message.get(
                "content",
                "",
            )

            if raw_content is None:
                continue

            content = str(
                raw_content
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

        # Giới hạn 8 message gần nhất
        # để tránh prompt quá dài.
        return safe_history[-8:]

    def _sanitize_memory_context(
        self,
        memory_context: str,
    ) -> str:
        """
        Chuẩn hóa memory context trước khi đưa vào prompt.

        Giới hạn độ dài để tránh memory quá lớn
        chiếm toàn bộ context window của LLM.
        """

        if memory_context is None:
            return ""

        clean_memory = str(
            memory_context
        ).strip()

        if not clean_memory:
            return ""

        max_memory_characters = 6000

        if (
            len(clean_memory)
            > max_memory_characters
        ):
            clean_memory = (
                clean_memory[
                    :max_memory_characters
                ].rstrip()
                + "\n[Memory đã được rút gọn]"
            )

        return clean_memory

    def _build_context_from_items(
        self,
        items: list[
            RetrievedContext
        ],
    ) -> str:
        """
        Chuyển danh sách tài liệu truy xuất được
        thành context có cấu trúc rõ ràng cho LLM.
        """

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