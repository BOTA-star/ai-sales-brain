from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import requests
from ollama import Client

from config import (
    LLM_PROVIDER,
    OLLAMA_HOST,
    OLLAMA_MAX_TOKENS,
    OLLAMA_MODEL,
    OLLAMA_TEMPERATURE,
    OLLAMA_TIMEOUT,
    OPENROUTER_API_KEY,
    OPENROUTER_BASE_URL,
    OPENROUTER_MODEL,
    OPENROUTER_TIMEOUT,
    USE_MOCK,
)


ChatMessage = dict[str, str]

VALID_MESSAGE_ROLES = {
    "system",
    "user",
    "assistant",
}


def sanitize_messages(
    messages: list[ChatMessage],
) -> list[ChatMessage]:
    """
    Chuẩn hóa danh sách message trước khi gửi cho LLM.

    Chỉ giữ các role hợp lệ và nội dung không rỗng.
    """

    safe_messages: list[ChatMessage] = []

    for message in messages:
        if not isinstance(message, dict):
            continue

        role = str(
            message.get("role", "")
        ).strip().lower()

        content = str(
            message.get("content", "")
        ).strip()

        if role not in VALID_MESSAGE_ROLES:
            continue

        if not content:
            continue

        safe_messages.append(
            {
                "role": role,
                "content": content,
            }
        )

    return safe_messages


def validate_generation_options(
    max_tokens: int,
    temperature: float,
) -> None:
    """
    Kiểm tra các tham số sinh nội dung.
    """

    if max_tokens <= 0:
        raise ValueError(
            "max_tokens phải lớn hơn 0."
        )

    if not 0 <= temperature <= 2:
        raise ValueError(
            "temperature phải nằm trong khoảng từ 0 đến 2."
        )


class LLMClient(ABC):
    """
    Interface chung cho các LLM provider.

    RAGPipeline chỉ phụ thuộc vào interface này,
    không phụ thuộc trực tiếp vào Ollama hoặc OpenRouter.
    """

    @abstractmethod
    def generate(
        self,
        messages: list[ChatMessage],
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> str:
        raise NotImplementedError


class MockLLMClient(LLMClient):
    """
    LLM giả lập.

    Được sử dụng khi USE_MOCK=true.
    Không gọi Ollama hoặc OpenRouter.
    """

    def generate(
        self,
        messages: list[ChatMessage],
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> str:
        del max_tokens
        del temperature

        safe_messages = sanitize_messages(
            messages
        )

        if not safe_messages:
            return "Đây là phản hồi mock."

        last_message = safe_messages[-1][
            "content"
        ]

        return (
            "Đây là phản hồi mock cho nội dung:\n"
            f"{last_message[:500]}"
        )


class OllamaLLMClient(LLMClient):
    """
    Gọi model đang chạy local bằng Ollama.
    """

    def __init__(
        self,
        host: str = OLLAMA_HOST,
        model: str = OLLAMA_MODEL,
        timeout: int = OLLAMA_TIMEOUT,
    ) -> None:
        clean_host = (
            host or ""
        ).strip().rstrip("/")

        clean_model = (
            model or ""
        ).strip()

        if not clean_host:
            raise ValueError(
                "Thiếu OLLAMA_HOST trong file .env."
            )

        if not clean_model:
            raise ValueError(
                "Thiếu OLLAMA_MODEL trong file .env."
            )

        self.host = clean_host
        self.model = clean_model

        self.client = Client(
            host=self.host,
            timeout=timeout,
        )

    def generate(
        self,
        messages: list[ChatMessage],
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> str:
        safe_messages = sanitize_messages(
            messages
        )

        if not safe_messages:
            raise ValueError(
                "Danh sách messages không được để trống."
            )

        selected_max_tokens = (
            max_tokens
            if max_tokens is not None
            else OLLAMA_MAX_TOKENS
        )

        selected_temperature = (
            temperature
            if temperature is not None
            else OLLAMA_TEMPERATURE
        )

        validate_generation_options(
            max_tokens=selected_max_tokens,
            temperature=selected_temperature,
        )

        try:
            response = self.client.chat(
                model=self.model,
                messages=safe_messages,
                stream=False,
                options={
                    "temperature": (
                        selected_temperature
                    ),
                    "num_predict": (
                        selected_max_tokens
                    ),
                },
            )

        except Exception as exc:
            raise RuntimeError(
                "Không thể kết nối hoặc nhận phản hồi "
                "từ Ollama. Hãy kiểm tra Ollama đang chạy "
                f"tại {self.host} và model "
                f"'{self.model}' đã được tải."
            ) from exc

        content = self._extract_content(
            response
        )

        if not content:
            raise RuntimeError(
                "Ollama trả về nội dung rỗng."
            )

        return content

    @staticmethod
    def _extract_content(
        response: Any,
    ) -> str:
        """
        Hỗ trợ response dạng object và dictionary.
        """

        if response is None:
            return ""

        if hasattr(response, "message"):
            message = response.message

            if hasattr(message, "content"):
                return str(
                    message.content or ""
                ).strip()

            if isinstance(message, dict):
                return str(
                    message.get(
                        "content",
                        "",
                    )
                ).strip()

        if isinstance(response, dict):
            message = response.get(
                "message",
                {},
            )

            if isinstance(message, dict):
                return str(
                    message.get(
                        "content",
                        "",
                    )
                ).strip()

        return ""


class OpenRouterLLMClient(LLMClient):
    """
    Gọi LLM thông qua OpenRouter.

    Provider này được chuẩn bị cho giai đoạn
    deploy hoặc sử dụng tại công ty.
    """

    def __init__(
        self,
        api_key: str = OPENROUTER_API_KEY,
        base_url: str = OPENROUTER_BASE_URL,
        model: str = OPENROUTER_MODEL,
        timeout: int = OPENROUTER_TIMEOUT,
    ) -> None:
        clean_api_key = (
            api_key or ""
        ).strip()

        clean_base_url = (
            base_url or ""
        ).strip().rstrip("/")

        clean_model = (
            model or ""
        ).strip()

        if not clean_api_key:
            raise ValueError(
                "Thiếu OPENROUTER_API_KEY "
                "trong file .env."
            )

        if not clean_base_url:
            raise ValueError(
                "Thiếu OPENROUTER_BASE_URL "
                "trong file .env."
            )

        if not clean_model:
            raise ValueError(
                "Thiếu OPENROUTER_MODEL "
                "trong file .env."
            )

        self.api_key = clean_api_key
        self.base_url = clean_base_url
        self.model = clean_model
        self.timeout = timeout

    def generate(
        self,
        messages: list[ChatMessage],
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> str:
        safe_messages = sanitize_messages(
            messages
        )

        if not safe_messages:
            raise ValueError(
                "Danh sách messages không được để trống."
            )

        selected_max_tokens = (
            max_tokens
            if max_tokens is not None
            else OLLAMA_MAX_TOKENS
        )

        selected_temperature = (
            temperature
            if temperature is not None
            else OLLAMA_TEMPERATURE
        )

        validate_generation_options(
            max_tokens=selected_max_tokens,
            temperature=selected_temperature,
        )

        try:
            response = requests.post(
                (
                    f"{self.base_url}"
                    "/chat/completions"
                ),
                headers={
                    "Authorization": (
                        f"Bearer {self.api_key}"
                    ),
                    "Content-Type": (
                        "application/json"
                    ),
                    "HTTP-Referer": (
                        "http://localhost:8501"
                    ),
                    "X-Title": "AI Sales Brain",
                },
                json={
                    "model": self.model,
                    "messages": safe_messages,
                    "max_tokens": (
                        selected_max_tokens
                    ),
                    "temperature": (
                        selected_temperature
                    ),
                },
                timeout=self.timeout,
            )

        except requests.Timeout as exc:
            raise RuntimeError(
                "OpenRouter phản hồi quá thời gian "
                "cho phép."
            ) from exc

        except requests.RequestException as exc:
            raise RuntimeError(
                "Không thể kết nối tới OpenRouter."
            ) from exc

        try:
            response_data = response.json()

        except ValueError as exc:
            raise RuntimeError(
                "OpenRouter trả về dữ liệu không phải "
                "JSON hợp lệ. "
                f"HTTP status: {response.status_code}"
            ) from exc

        if not response.ok:
            error_message: Any = response_data

            if isinstance(response_data, dict):
                error_message = (
                    response_data.get(
                        "error",
                        response_data,
                    )
                )

            raise RuntimeError(
                "OpenRouter API gặp lỗi. "
                f"HTTP {response.status_code}: "
                f"{error_message}"
            )

        try:
            content = (
                response_data["choices"][0]
                ["message"]["content"]
            )

        except (
            KeyError,
            IndexError,
            TypeError,
        ) as exc:
            raise RuntimeError(
                "Cấu trúc phản hồi từ OpenRouter "
                "không hợp lệ."
            ) from exc

        clean_content = str(
            content or ""
        ).strip()

        if not clean_content:
            raise RuntimeError(
                "OpenRouter trả về nội dung rỗng."
            )

        return clean_content


def create_llm_client(
    provider: str | None = None,
) -> LLMClient:
    """
    Khởi tạo LLM client theo cấu hình.

    Local:
        LLM_PROVIDER=ollama

    Công ty hoặc server:
        LLM_PROVIDER=openrouter
    """

    if USE_MOCK:
        return MockLLMClient()

    selected_provider = (
        provider or LLM_PROVIDER
    ).strip().lower()

    if selected_provider == "ollama":
        return OllamaLLMClient()

    if selected_provider == "openrouter":
        return OpenRouterLLMClient()

    raise ValueError(
        "LLM_PROVIDER không được hỗ trợ. "
        "Chỉ sử dụng 'ollama' hoặc 'openrouter'."
    )