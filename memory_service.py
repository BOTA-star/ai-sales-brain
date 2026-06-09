from __future__ import annotations

import logging
import os
import re
from typing import Any

import requests
from requests import Session
from requests.exceptions import RequestException


logger = logging.getLogger(__name__)


class MemoryService:
    """
    Module trung gian dùng để giao tiếp với AgentMemory REST API.

    Memory được phân tách theo customer_id bằng project:

        chatbot-rag/customer/{customer_id}
    """

    def __init__(
        self,
        base_url: str | None = None,
        timeout_seconds: float | None = None,
        session: Session | None = None,
    ) -> None:
        self.base_url = (
            base_url
            or os.getenv(
                "AGENTMEMORY_BASE_URL",
                "http://127.0.0.1:3111/agentmemory",
            )
        ).rstrip("/")

        timeout_value = timeout_seconds or os.getenv(
            "AGENTMEMORY_TIMEOUT_SECONDS",
            "10",
        )

        try:
            self.timeout_seconds = float(timeout_value)
        except (TypeError, ValueError):
            self.timeout_seconds = 10.0

        self.session = session or requests.Session()
        self.session.headers.update(
            {
                "Accept": "application/json",
                "Content-Type": "application/json; charset=utf-8",
            }
        )

    @staticmethod
    def build_project(customer_id: str | int) -> str:
        """
        Tạo project riêng cho từng khách hàng.

        Ví dụ:
            customer_id = 10001
            project = chatbot-rag/customer/10001
        """
        normalized_customer_id = str(customer_id).strip()

        if not normalized_customer_id:
            raise ValueError("customer_id không được để trống.")

        # Chỉ cho phép ký tự an toàn xuất hiện trong project key.
        safe_customer_id = re.sub(
            r"[^a-zA-Z0-9._-]",
            "_",
            normalized_customer_id,
        )

        return f"chatbot-rag/customer/{safe_customer_id}"

    def health_check(self) -> bool:
        """
        Kiểm tra AgentMemory có đang hoạt động hay không.

        Trả về:
            True: AgentMemory healthy.
            False: AgentMemory không thể kết nối hoặc không healthy.
        """
        try:
            response = self.session.get(
                f"{self.base_url}/health",
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()

            data = response.json()

            root_status = str(data.get("status", "")).lower()
            health_status = str(
                data.get("health", {}).get("status", "")
            ).lower()

            return (
                root_status == "healthy"
                or health_status == "healthy"
            )

        except (RequestException, ValueError, TypeError) as exc:
            logger.warning(
                "Không thể kiểm tra AgentMemory health: %s",
                exc,
            )
            return False

    def save_memory(
        self,
        customer_id: str | int,
        content: str,
        memory_type: str = "fact",
        concepts: list[str] | None = None,
    ) -> dict[str, Any] | None:
        """
        Lưu một Memory cho khách hàng.

        Trả về thông tin Memory khi thành công.
        Trả về None nếu AgentMemory không khả dụng hoặc lưu thất bại.
        """
        normalized_content = content.strip()

        if not normalized_content:
            raise ValueError("content không được để trống.")

        project = self.build_project(customer_id)

        payload = {
            "project": project,
            "content": normalized_content,
            "type": memory_type,
            "concepts": concepts or [],
        }

        try:
            response = self.session.post(
                f"{self.base_url}/remember",
                json=payload,
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()

            data = response.json()

            if not data.get("success"):
                logger.warning(
                    "AgentMemory không xác nhận lưu thành công: %s",
                    data,
                )
                return None

            memory = data.get("memory")

            if not isinstance(memory, dict):
                logger.warning(
                    "AgentMemory trả về memory không hợp lệ: %s",
                    data,
                )
                return None

            return memory

        except (RequestException, ValueError, TypeError) as exc:
            logger.warning(
                "Không thể lưu AgentMemory cho customer_id=%s: %s",
                customer_id,
                exc,
            )
            return None

    def search_memory(
        self,
        customer_id: str | int,
        query: str,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """
        Tìm Memory liên quan của một khách hàng.

        Sử dụng endpoint /search thay vì /smart-search để bảo đảm
        dữ liệu được lọc đúng theo project của customer_id.
        """
        normalized_query = query.strip()

        if not normalized_query:
            raise ValueError("query không được để trống.")

        project = self.build_project(customer_id)
        safe_limit = max(1, min(int(limit), 20))

        payload = {
            "project": project,
            "query": normalized_query,
            "limit": safe_limit,
            "format": "full",
        }

        try:
            response = self.session.post(
                f"{self.base_url}/search",
                json=payload,
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()

            data = response.json()
            raw_results = data.get("results", [])

            if not isinstance(raw_results, list):
                return []

            return [
                self._normalize_search_result(item)
                for item in raw_results
                if isinstance(item, dict)
            ]

        except (RequestException, ValueError, TypeError) as exc:
            logger.warning(
                "Không thể truy vấn AgentMemory cho customer_id=%s: %s",
                customer_id,
                exc,
            )
            return []

    @staticmethod
    def _normalize_search_result(
        item: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Chuẩn hóa response từ AgentMemory thành cấu trúc dễ sử dụng.
        """
        observation = item.get("observation", {})

        if not isinstance(observation, dict):
            observation = {}

        facts = observation.get("facts", [])

        if not isinstance(facts, list):
            facts = []

        narrative = str(observation.get("narrative", "")).strip()
        title = str(observation.get("title", "")).strip()

        if narrative:
            content = narrative
        elif facts:
            content = "\n".join(str(fact) for fact in facts)
        else:
            content = title

        return {
            "id": observation.get("id"),
            "content": content,
            "title": title,
            "facts": facts,
            "concepts": observation.get("concepts", []),
            "score": item.get("score", 0),
            "timestamp": observation.get("timestamp"),
            "type": observation.get("type"),
            "project_session": item.get("sessionId"),
            "raw": item,
        }

    def format_memory_context(
        self,
        memories: list[dict[str, Any]],
    ) -> str:
        """
        Chuyển kết quả tìm kiếm thành đoạn context để đưa vào prompt.
        """
        context_parts: list[str] = []

        for index, memory in enumerate(memories, start=1):
            content = str(memory.get("content", "")).strip()

            if not content:
                continue

            context_parts.append(
                f"[Memory {index}]\n{content}"
            )

        return "\n\n".join(context_parts)


_default_memory_service = MemoryService()


def check_memory_health() -> bool:
    return _default_memory_service.health_check()


def save_memory(
    customer_id: str | int,
    content: str,
    memory_type: str = "fact",
    concepts: list[str] | None = None,
) -> dict[str, Any] | None:
    return _default_memory_service.save_memory(
        customer_id=customer_id,
        content=content,
        memory_type=memory_type,
        concepts=concepts,
    )


def search_memory(
    customer_id: str | int,
    query: str,
    limit: int = 5,
) -> list[dict[str, Any]]:
    return _default_memory_service.search_memory(
        customer_id=customer_id,
        query=query,
        limit=limit,
    )


def format_memory_context(
    memories: list[dict[str, Any]],
) -> str:
    return _default_memory_service.format_memory_context(memories)