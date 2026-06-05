from rag.document_loader import DocumentLoader
from rag.text_splitter import TextSplitter
from rag.vector_store import VectorStore


def main():
    loader = DocumentLoader(raw_data_dir="data/raw")
    documents = loader.load_all_documents()

    splitter = TextSplitter(
        chunk_size=800,
        chunk_overlap=120,
    )

    chunks = splitter.split_documents(documents)

    vector_store = VectorStore(
        persist_dir="storage/vector_db",
        collection_name="rag_documents",
    )

    inserted_count = vector_store.add_chunks(chunks)

    print(f"Loaded documents: {len(documents)}")
    print(f"Generated chunks: {len(chunks)}")
    print(f"Inserted chunks: {inserted_count}")
    print(f"Total chunks in Vector DB: {vector_store.count()}")

    query = "What is TransReID?"
    results = vector_store.search(query=query, top_k=3)

    print("=" * 80)
    print(f"Search query: {query}")
    print(f"Top results: {len(results)}")

    for index, result in enumerate(results, start=1):
        metadata = result["metadata"]

        print("=" * 80)
        print(f"Result {index}")
        print(f"Distance: {result['distance']}")
        print(f"File name: {metadata.get('file_name')}")
        print(f"Page: {metadata.get('page')}")
        print(f"Chunk index: {metadata.get('chunk_index')}")
        print("Content preview:")
        print(result["content"][:700])

if __name__ == "__main__":
    main()