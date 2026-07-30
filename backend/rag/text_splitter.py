"""
Medical Text Splitter for MediVision AI RAG module.
Splits medical documents into semantic chunks while retaining full document metadata.
"""
from __future__ import annotations

import logging
from typing import List, Optional

try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
except ImportError:
    try:
        from langchain.text_splitter import RecursiveCharacterTextSplitter
    except ImportError:
        try:
            from langchain_community.text_splitter import RecursiveCharacterTextSplitter
        except ImportError:
            RecursiveCharacterTextSplitter = None

try:
    from langchain_core.documents import Document
except ImportError:
    try:
        from langchain.schema import Document
    except ImportError:
        from dataclasses import dataclass, field
        @dataclass
        class Document:
            page_content: str
            metadata: dict = field(default_factory=dict)

logger = logging.getLogger(__name__)


class _FallbackTextSplitter:
    """Fallback text splitter when LangChain text splitter is unavailable."""

    def __init__(self, chunk_size: int = 800, chunk_overlap: int = 150):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def split_documents(self, documents: List[Document]) -> List[Document]:
        chunks: List[Document] = []
        for doc in documents:
            text = doc.page_content
            if not text:
                continue
            start = 0
            while start < len(text):
                end = start + self.chunk_size
                chunk_text = text[start:end]
                new_doc = Document(
                    page_content=chunk_text,
                    metadata=dict(doc.metadata),
                )
                chunks.append(new_doc)
                start += self.chunk_size - self.chunk_overlap
                if start >= len(text):
                    break
        return chunks


class MedicalTextSplitter:
    """
    Splits document text into manageable chunks suitable for embeddings & retrieval.
    """

    def __init__(
        self,
        chunk_size: int = 750,
        chunk_overlap: int = 125,
        separators: Optional[List[str]] = None,
    ):
        if separators is None:
            separators = ["\n\n", "\n", ". ", "; ", ", ", " ", ""]
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

        if RecursiveCharacterTextSplitter is not None:
            self.splitter = RecursiveCharacterTextSplitter(
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap,
                separators=separators,
                length_function=len,
                is_separator_regex=False,
            )
        else:
            self.splitter = _FallbackTextSplitter(
                chunk_size=self.chunk_size, chunk_overlap=self.chunk_overlap
            )

    def split_documents(self, documents: List[Document]) -> List[Document]:
        """
        Split a list of Document objects into smaller chunks.

        Args:
            documents: List of input Document objects.

        Returns:
            List of chunked Document objects.
        """
        if not documents:
            return []

        chunks = self.splitter.split_documents(documents)
        # Assign unique chunk metadata
        for idx, chunk in enumerate(chunks):
            chunk.metadata["chunk_id"] = idx
            if "file_name" in chunk.metadata:
                chunk.metadata["chunk_key"] = (
                    f"{chunk.metadata['file_name']}_p{chunk.metadata.get('page', 1)}_c{idx}"
                )

        logger.info(
            f"Split {len(documents)} document pages into {len(chunks)} text chunks "
            f"(chunk_size={self.chunk_size}, overlap={self.chunk_overlap})."
        )
        return chunks
