from rag.document_loader import DocumentLoader
from rag.text_splitter import TextSplitter


def main():
    loader = DocumentLoader(raw_data_dir="data/raw")
    documents = loader.load_all_documents()

    splitter = TextSplitter(
        chunk_size=800,
        chunk_overlap=120
    )

    chunks = splitter.split_documents(documents)

    print(f"Loaded documents: {len(documents)}")
    print(f"Generated chunks: {len(chunks)}")

    for index, chunk in enumerate(chunks[:10], start=1):
        print("=" * 80)
        print(f"Chunk {index}")
        print(f"File name: {chunk.file_name}")
        print(f"File type: {chunk.file_type}")
        print(f"Page: {chunk.page}")
        print(f"Chunk index: {chunk.chunk_index}")
        print(f"Start char: {chunk.start_char}")
        print(f"End char: {chunk.end_char}")
        print("Content preview:")
        print(chunk.content[:500])


if __name__ == "__main__":
    main()