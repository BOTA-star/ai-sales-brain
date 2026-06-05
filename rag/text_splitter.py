from dataclasses import dataclass
from typing import List, Optional

from rag.document_loader import LoadedDocument


@dataclass
class DocumentChunk:
    content: str
    source: str
    file_name: str
    file_type: str
    chunk_index: int
    page: Optional[int] = None
    start_char: Optional[int] = None
    end_char: Optional[int] = None


class TextSplitter:
    def __init__(self, chunk_size: int = 800, chunk_overlap: int = 120):
        if chunk_size <= 0:
            raise ValueError("chunk_size must be greater than 0")

        if chunk_overlap < 0:
            raise ValueError("chunk_overlap must be greater than or equal to 0")

        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be smaller than chunk_size")

        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def split_documents(self, documents: List[LoadedDocument]) -> List[DocumentChunk]:
        chunks: List[DocumentChunk] = []
        global_chunk_index = 0

        for document in documents:
            text_chunks = self._split_text(document.content)

            for chunk_text, start_char, end_char in text_chunks:
                chunks.append(
                    DocumentChunk(
                        content=chunk_text,
                        source=document.source,
                        file_name=document.file_name,
                        file_type=document.file_type,
                        page=document.page,
                        chunk_index=global_chunk_index,
                        start_char=start_char,
                        end_char=end_char,
                    )
                )

                global_chunk_index += 1

        return chunks

    def _split_text(self, text: str) -> List[tuple[str, int, int]]:
        text = text.strip()

        if not text:
            return []

        chunks: List[tuple[str, int, int]] = []
        text_length = len(text)

        start = 0

        while start < text_length:
            end = min(start + self.chunk_size, text_length)

            if end < text_length:
                end = self._find_best_split_position(text, start, end)

            chunk_text = text[start:end].strip()

            if chunk_text:
                chunks.append((chunk_text, start, end))

            if end >= text_length:
                break

            next_start = end - self.chunk_overlap

            if next_start <= start:
                next_start = end

            start = max(next_start, 0)

        return chunks

    def _find_best_split_position(self, text: str, start: int, end: int) -> int:
        newline_position = text.rfind("\n", start, end)

        if newline_position != -1 and newline_position > start + self.chunk_size * 0.5:
            return newline_position

        space_position = text.rfind(" ", start, end)

        if space_position != -1 and space_position > start:
            return space_position

        return end