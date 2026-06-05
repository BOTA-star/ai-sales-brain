from rag.llm_client import OpenRouterLLMClient
from rag.rag_pipeline import RAGPipeline
from rag.retrieval import RetrievalOrchestrator


def main():
    retrieval_orchestrator = RetrievalOrchestrator(
        persist_dir="storage/vector_db",
        collection_name="rag_documents",
        top_k=4,
    )

    llm_client = OpenRouterLLMClient()

    rag_pipeline = RAGPipeline(
        retrieval_orchestrator=retrieval_orchestrator,
        llm_client=llm_client,
    )

    question = "What is TransReID?"

    response = rag_pipeline.answer(question)

    print("=" * 80)
    print(f"Question: {question}")
    print("=" * 80)
    print("Answer:")
    print(response.answer)

    print("=" * 80)
    print("Sources:")

    for index, source in enumerate(response.sources, start=1):
        print(
            f"{index}. File: {source.file_name} | "
            f"Page: {source.page} | "
            f"Chunk: {source.chunk_index}"
        )

if __name__ == "__main__":
    main()