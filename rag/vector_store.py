from pathlib import Path
from typing import List, Dict, Any

import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

from rag.text_splitter import DocumentChunk

class VectorStore:
    def __init__(
        self,
        persist_dir: str = "storage/vector_db",
        collection_name: str = "rag_documents",
    ):
        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)

        # 100% local embedding model, không dùng API trả phí
        self.embedding_function = SentenceTransformerEmbeddingFunction(
            model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
            device="cpu",
            normalize_embeddings=True,
        )

        self.client = chromadb.PersistentClient(path=str(self.persist_dir))

        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            embedding_function=self.embedding_function,
        )

    def add_chunks(self, chunks: List[DocumentChunk]) -> int:
        if not chunks:
            return 0

        ids = []
        documents = []
        metadatas: List[Dict[str, Any]] = []

        for chunk in chunks:
            chunk_id = self._build_chunk_id(chunk)

            ids.append(chunk_id)
            documents.append(chunk.content)
            metadatas.append(
                {
                    "source": chunk.source,
                    "file_name": chunk.file_name,
                    "file_type": chunk.file_type,
                    "page": chunk.page if chunk.page is not None else -1,
                    "chunk_index": chunk.chunk_index,
                    "start_char": chunk.start_char if chunk.start_char is not None else -1,
                    "end_char": chunk.end_char if chunk.end_char is not None else -1,
                }
            )

        self.collection.upsert(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
        )

        return len(chunks)

    def search(self, query: str, top_k: int = 4) -> List[Dict[str, Any]]:
        results = self.collection.query(
            query_texts=[query],
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )

        output = []

        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        for document, metadata, distance in zip(documents, metadatas, distances):
            output.append(
                {
                    "content": document,
                    "metadata": metadata,
                    "distance": distance,
                }
            )

        return output

    def count(self) -> int:
        return self.collection.count()

    def _build_chunk_id(self, chunk: DocumentChunk) -> str:
        page = chunk.page if chunk.page is not None else 0
        return f"{chunk.file_name}_page_{page}_chunk_{chunk.chunk_index}"