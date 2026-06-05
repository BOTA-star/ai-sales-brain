from rag_service import create_rag_pipeline


def main():
    rag_pipeline = create_rag_pipeline()

    question = "What is TransReID?"
    response = rag_pipeline.answer(question)

    print("=" * 80)
    print("Question:")
    print(question)

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