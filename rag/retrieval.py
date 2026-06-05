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


class RetrievalOrchestrator:
    def __init__(
        self,
        persist_dir: str = "storage/vector_db",
        collection_name: str = "rag_documents",
        embedding_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        top_k: int = 4,
    ):
        self.top_k = top_k

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

    def retrieve(self, query: str) -> List[RetrievedContext]:
        if not query or not query.strip():
            return []

        docs = self.retriever.invoke(query.strip())

        results: List[RetrievedContext] = []

        for doc in docs:
            metadata = doc.metadata or {}

            results.append(
                RetrievedContext(
                    content=doc.page_content,
                    file_name=metadata.get("file_name", ""),
                    file_type=metadata.get("file_type", ""),
                    page=int(metadata.get("page", -1)),
                    chunk_index=int(metadata.get("chunk_index", -1)),
                    source=metadata.get("source", ""),
                )
            )

        return results

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