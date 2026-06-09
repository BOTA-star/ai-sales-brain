from config import (
    RAG_COLLECTION_NAME,
    RAG_PERSIST_DIR,
    RAG_SIMILARITY_THRESHOLD,
    RAG_TOP_K,
)
from rag.llm_client import create_llm_client
from rag.rag_pipeline import RAGPipeline
from rag.retrieval import RetrievalOrchestrator

def create_rag_pipeline() -> RAGPipeline:
    """
    Khởi tạo đầy đủ RAG pipeline.

    LLM provider được chọn thông qua biến:
        LLM_PROVIDER=ollama
        hoặc
        LLM_PROVIDER=openrouter
    """
    retrieval_orchestrator = RetrievalOrchestrator(
        persist_dir=RAG_PERSIST_DIR,
        collection_name=RAG_COLLECTION_NAME,
        top_k=RAG_TOP_K,
        similarity_threshold=(RAG_SIMILARITY_THRESHOLD),
    )

    llm_client = create_llm_client()

    return RAGPipeline(
        retrieval_orchestrator=retrieval_orchestrator,
        llm_client=llm_client,
    )