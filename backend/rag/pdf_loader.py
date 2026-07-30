"""
PDF Document Loader for MediVision AI RAG module.
Extracts text and page-level metadata from medical PDF documents.
"""
from __future__ import annotations

import os
import logging
from typing import List, Optional
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


class PDFLoader:
    """
    Robust PDF Loader supporting PyPDF, PyPDF2, and pdfplumber backends.
    """

    def __init__(self, prefer_pdfplumber: bool = True):
        self.prefer_pdfplumber = prefer_pdfplumber

    def load_pdf(self, file_path: str) -> List[Document]:
        """
        Load a single PDF document and split into LangChain Document objects by page.

        Args:
            file_path: Absolute or relative path to the PDF file.

        Returns:
            List of Document objects containing page content and metadata.
        """
        if not os.path.exists(file_path):
            logger.error(f"PDF file not found: {file_path}")
            raise FileNotFoundError(f"File not found: {file_path}")

        file_name = os.path.basename(file_path)
        documents: List[Document] = []

        # Attempt 1: pdfplumber if available
        if self.prefer_pdfplumber:
            try:
                import pdfplumber

                with pdfplumber.open(file_path) as pdf:
                    total_pages = len(pdf.pages)
                    for i, page in enumerate(pdf.pages):
                        text = page.extract_text() or ""
                        text = text.strip()
                        if text:
                            doc = Document(
                                page_content=text,
                                metadata={
                                    "source": file_path,
                                    "file_name": file_name,
                                    "page": i + 1,
                                    "total_pages": total_pages,
                                },
                            )
                            documents.append(doc)
                if documents:
                    logger.info(
                        f"Loaded {len(documents)} pages from '{file_name}' using pdfplumber."
                    )
                    return documents
            except Exception as e:
                logger.warning(
                    f"pdfplumber extraction failed for {file_name}, falling back to PyPDF/PyPDF2: {e}"
                )

        # Attempt 2: pypdf / PyPDF2 fallback
        try:
            try:
                from pypdf import PdfReader
            except ImportError:
                from PyPDF2 import PdfReader

            reader = PdfReader(file_path)
            total_pages = len(reader.pages)
            for i, page in enumerate(reader.pages):
                text = page.extract_text() or ""
                text = text.strip()
                if text:
                    doc = Document(
                        page_content=text,
                        metadata={
                            "source": file_path,
                            "file_name": file_name,
                            "page": i + 1,
                            "total_pages": total_pages,
                        },
                    )
                    documents.append(doc)
            logger.info(
                f"Loaded {len(documents)} pages from '{file_name}' using PyPDF."
            )
        except Exception as e:
            logger.error(f"Failed to extract text from PDF '{file_name}': {e}")
            raise ValueError(f"Could not read PDF '{file_name}': {e}")

        return documents


def load_single_pdf(file_path: str) -> List[Document]:
    """Helper function to load a single PDF."""
    loader = PDFLoader()
    return loader.load_pdf(file_path)
