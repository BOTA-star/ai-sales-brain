import os

from dotenv import load_dotenv

load_dotenv()

def _get_int(name: str, default: int) -> int:
    value = os.getenv(name)

    if value is None or not value.strip():
        return default

    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer.") from exc

def _get_float(name: str, default: float) -> float:
    value = os.getenv(name)

    if value is None or not value.strip():
        return default

    try:
        return float(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be a number.") from exc

# Application
USE_MOCK = os.getenv("USE_MOCK", "false").lower() == "true"

DEFAULT_CUSTOMER_NAME = "Khách AI Sales Brain"

WELCOME_MESSAGE = (
    "Chào bạn, mình là chatbot AI demo. Bạn muốn hỏi gì?"
)

CHAT_FRAME_HEIGHT = _get_int(
    "CHAT_FRAME_HEIGHT",
    520,
)

HISTORY_BOX_HEIGHT = _get_int(
    "HISTORY_BOX_HEIGHT",
    360,
)

RECENT_CONTEXT_LIMIT = _get_int(
    "RECENT_CONTEXT_LIMIT",
    8,
)

# PostgreSQL
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "",
).strip()

DB_CONNECT_TIMEOUT = _get_int(
    "DB_CONNECT_TIMEOUT",
    10,
)

# LLM Provider
# ollama | openrouter
LLM_PROVIDER = os.getenv(
    "LLM_PROVIDER",
    "ollama",
).strip().lower()

# Ollama local
OLLAMA_HOST = os.getenv(
    "OLLAMA_HOST",
    "http://localhost:11434",
).strip().rstrip("/")

OLLAMA_MODEL = os.getenv(
    "OLLAMA_MODEL",
    "qwen2.5:3b",
).strip()

OLLAMA_TIMEOUT = _get_int(
    "OLLAMA_TIMEOUT",
    120,
)

OLLAMA_TEMPERATURE = _get_float(
    "OLLAMA_TEMPERATURE",
    0.1,
)

OLLAMA_MAX_TOKENS = _get_int(
    "OLLAMA_MAX_TOKENS",
    1000,
)

# OpenRouter
# Dùng sau khi deploy công ty
OPENROUTER_BASE_URL = os.getenv(
    "OPENROUTER_BASE_URL",
    "https://openrouter.ai/api/v1",
).rstrip("/")

OPENROUTER_API_KEY = os.getenv(
    "OPENROUTER_API_KEY",
    "",
).strip()

OPENROUTER_MODEL = os.getenv(
    "OPENROUTER_MODEL",
    "",
).strip()

OPENROUTER_TIMEOUT = _get_int(
    "OPENROUTER_TIMEOUT",
    90,
)

# RAG
RAG_PERSIST_DIR = os.getenv(
    "RAG_PERSIST_DIR",
    "storage/vector_db",
)

RAG_COLLECTION_NAME = os.getenv(
    "RAG_COLLECTION_NAME",
    "rag_documents",
)

RAG_EMBEDDING_MODEL = os.getenv(
    "RAG_EMBEDDING_MODEL",
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
)

RAG_TOP_K = _get_int(
    "RAG_TOP_K",
    4,
)

RAG_SIMILARITY_THRESHOLD = _get_float(
    "RAG_SIMILARITY_THRESHOLD",
    0.45,
)