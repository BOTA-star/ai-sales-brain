from rag.document_loader import DocumentLoader


def main():
    loader = DocumentLoader(raw_data_dir="data/raw")
    documents = loader.load_all_documents()

    print(f"Loaded documents: {len(documents)}")

    for index, doc in enumerate(documents, start=1):
        print("=" * 80)
        print(f"Document {index}")
        print(f"File name: {doc.file_name}")
        print(f"File type: {doc.file_type}")
        print(f"Page: {doc.page}")
        print(f"Content preview:")
        print(doc.content[:500])

if __name__ == "__main__":
    main()