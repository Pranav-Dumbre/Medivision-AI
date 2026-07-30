"""
Document Loader for MediVision AI RAG pipeline.
Handles loading and sanitizing batch PDF documents.
"""
from __future__ import annotations

import os
import re
import logging
from typing import List, Union, Sequence
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
from backend.rag.pdf_loader import PDFLoader

logger = logging.getLogger(__name__)


def clean_text(text: str) -> str:
    """Clean and normalize raw extracted document text."""
    if not text:
        return ""
    # Replace multiple newlines or tabs with normalized spaces while preserving paragraph breaks
    text = re.sub(r"\r\n|\r", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


class DocumentBatchLoader:
    """
    Batch Document Loader for ingesting multiple medical documents.
    """

    def __init__(self):
        self.pdf_loader = PDFLoader()

    def load_documents(self, sources: Sequence[str]) -> List[Document]:
        """
        Load a list of PDF file paths or a directory path.

        Args:
            sources: List of file paths or directory containing PDFs.

        Returns:
            List of cleaned LangChain Document objects.
        """
        all_docs: List[Document] = []
        target_files: List[str] = []

        for source in sources:
            if os.path.isdir(source):
                for root, _, files in os.walk(source):
                    for file in files:
                        if file.lower().endswith(".pdf"):
                            target_files.append(os.path.join(root, file))
            elif os.path.isfile(source) and source.lower().endswith(".pdf"):
                target_files.append(source)
            else:
                logger.warning(f"Skipping non-PDF or non-existent path: {source}")

        for file_path in target_files:
            try:
                docs = self.pdf_loader.load_pdf(file_path)
                for doc in docs:
                    doc.page_content = clean_text(doc.page_content)
                    if len(doc.page_content) >= 10:  # Ignore empty or near-empty pages
                        all_docs.append(doc)
            except Exception as e:
                logger.error(f"Error loading {file_path}: {e}")

        logger.info(f"Successfully loaded {len(all_docs)} total document pages from {len(target_files)} files.")
        return all_docs
