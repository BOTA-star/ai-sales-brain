import os
from dotenv import load_dotenv

load_dotenv()

USE_MOCK = os.getenv("USE_MOCK", "false").lower() == "true"
MODEL_NAME = os.getenv("MODEL", "qwen2.5:3b")
DATABASE_URL = os.getenv("DATABASE_URL")

DEFAULT_CUSTOMER_NAME = "Khách demo AI Sales Brain"
WELCOME_MESSAGE = "Chào bạn, mình là chatbot AI demo. Bạn muốn hỏi gì?"

APP_HEIGHT = 500
CHAT_FRAME_HEIGHT = 520
HISTORY_BOX_HEIGHT = 360

RAG_PERSIST_DIR = os.getenv("RAG_PERSIST_DIR", "storage/vector_db")
RAG_COLLECTION_NAME = os.getenv("RAG_COLLECTION_NAME", "rag_documents")
RAG_TOP_K = int(os.getenv("RAG_TOP_K", "4"))
RAG_SIMILARITY_THRESHOLD = float(os.getenv("RAG_SIMILARITY_THRESHOLD", "0.35"))