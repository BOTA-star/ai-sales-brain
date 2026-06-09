from dataclasses import dataclass
from typing import List

from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

@dataclass
class RetrievedContext:
    content: str
    file_name: str
    file_type: str
    page: int
    chunk_index: int
    source: str
    relevance_score: float | None=None

class RetrievalOrchestrator:
    def __init__(
        self,
        persist_dir: str = "storage/vector_db",
        collection_name: str = "rag_documents",
        embedding_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        top_k: int = 4,
        similarity_threshold: float = 0.45,
    ):
        self.top_k = top_k
        self.similarity_threshold = (
            similarity_threshold
        )

        self.embedding_function = HuggingFaceEmbeddings(
            model_name=embedding_model,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )

        self.vector_store = Chroma(
            collection_name=collection_name,
            persist_directory=persist_dir,
            embedding_function=self.embedding_function,
        )

        self.retriever = self.vector_store.as_retriever(
            search_kwargs={"k": self.top_k}
        )

    def retrieve(
        self,
        query: str,
    ) -> list[RetrievedContext]:
        clean_query = (
            query or ""
        ).strip()

        if not clean_query:
            return []

        docs_with_scores = (
            self.vector_store
            .similarity_search_with_relevance_scores(
                clean_query,
                k=self.top_k,
            )
        )

        results: list[RetrievedContext] = []

        for document, score in docs_with_scores:
            relevance_score = float(score)

            if (
                relevance_score
                < self.similarity_threshold
            ):
                continue

            metadata = document.metadata or {}

            results.append(
                RetrievedContext(
                    content=document.page_content,
                    file_name=str(
                        metadata.get(
                            "file_name",
                            "",
                        )
                    ),
                    file_type=str(
                        metadata.get(
                            "file_type",
                            "",
                        )
                    ),
                    page=self._safe_int(
                        metadata.get("page"),
                        -1,
                    ),
                    chunk_index=self._safe_int(
                        metadata.get(
                            "chunk_index"
                        ),
                        -1,
                    ),
                    source=str(
                        metadata.get(
                            "source",
                            "",
                        )
                    ),
                    relevance_score=(
                        relevance_score
                    ),
                )
            )

        return results
    
    @staticmethod
    def _safe_int(
        value,
        default: int,
    ) -> int:
        try:
            return int(value)
        except (
            TypeError,
            ValueError,
        ):
            return default

    def build_context(self, query: str) -> str:
        retrieved_items = self.retrieve(query)

        if not retrieved_items:
            return ""

        context_parts = []

        for index, item in enumerate(retrieved_items, start=1):
            context_parts.append(
                f"[Context {index}]\n"
                f"File: {item.file_name}\n"
                f"Page: {item.page}\n"
                f"Chunk index: {item.chunk_index}\n"
                f"Content:\n{item.content}"
            )

        return "\n\n".join(context_parts)