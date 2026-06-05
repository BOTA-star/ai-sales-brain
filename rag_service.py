from config import RAG_COLLECTION_NAME, RAG_PERSIST_DIR, RAG_TOP_K
from rag.llm_client import OpenRouterLLMClient
from rag.rag_pipeline import RAGPipeline
from rag.retrieval import RetrievalOrchestrator


def create_rag_pipeline() -> RAGPipeline:
    retrieval_orchestrator = RetrievalOrchestrator(
        persist_dir=RAG_PERSIST_DIR,
        collection_name=RAG_COLLECTION_NAME,
        top_k=RAG_TOP_K,
    )

    llm_client = OpenRouterLLMClient()

    return RAGPipeline(
        retrieval_orchestrator=retrieval_orchestrator,
        llm_client=llm_client,
    )