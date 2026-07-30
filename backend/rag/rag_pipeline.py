"""
RAG Pipeline Orchestrator for MediVision AI.

Developer Knowledge Base:
    Place PDF files in backend/rag/documents/
    The pipeline auto-scans, indexes, and serves those documents.
    End users never interact with the knowledge base directly.

On startup:
    1. Check if FAISS index already exists in backend/rag/vector_db/
    2. If yes → load it (fast path).
    3. If no → scan backend/rag/documents/, embed all PDFs, build & save index.
    4. Rebuild automatically if the set of PDF files has changed.
"""
from __future__ import annotations

import os
import hashlib
import json
import logging
from typing import List, Dict, Any, Optional

from backend.rag.document_loader import DocumentBatchLoader
from backend.rag.text_splitter import MedicalTextSplitter
from backend.rag.vector_store import FAISSVectorStoreManager
from backend.rag.retriever import MedicalRetriever
from backend.rag.chat_engine import LocalMedicalLLMEngine
from backend.rag.prompt import NO_INFO_MESSAGE

logger = logging.getLogger(__name__)

# ── Path constants ───────────────────────────────────────────────────────────
_RAG_DIR = os.path.dirname(os.path.abspath(__file__))
DOCUMENTS_DIR = os.path.join(_RAG_DIR, "documents")
VECTOR_DB_DIR = os.path.join(_RAG_DIR, "vector_db")
INDEX_MANIFEST = os.path.join(VECTOR_DB_DIR, "manifest.json")

# Message when knowledge base has no relevant answer
KB_NO_INFO_MESSAGE = "I couldn't find this information in the medical knowledge base."


def _collect_pdf_paths(directory: str) -> List[str]:
    """Return sorted list of all .pdf files inside directory (non-recursive top-level)."""
    if not os.path.isdir(directory):
        return []
    return sorted(
        os.path.join(directory, f)
        for f in os.listdir(directory)
        if f.lower().endswith(".pdf") and os.path.isfile(os.path.join(directory, f))
    )


def _compute_manifest(pdf_paths: List[str]) -> Dict[str, str]:
    """
    Compute a lightweight fingerprint dict for each PDF:
    {filename: "<size>-<mtime>"} — used to detect changes without hashing file content.
    """
    manifest: Dict[str, str] = {}
    for path in pdf_paths:
        try:
            stat = os.stat(path)
            manifest[os.path.basename(path)] = f"{stat.st_size}-{stat.st_mtime:.0f}"
        except OSError:
            pass
    return manifest


def _load_manifest() -> Dict[str, str]:
    """Load the saved manifest from disk, or return empty dict."""
    if os.path.exists(INDEX_MANIFEST):
        try:
            with open(INDEX_MANIFEST, "r", encoding="utf-8") as fh:
                return json.load(fh)
        except Exception:
            pass
    return {}


def _save_manifest(manifest: Dict[str, str]) -> None:
    """Persist the manifest to disk."""
    os.makedirs(VECTOR_DB_DIR, exist_ok=True)
    with open(INDEX_MANIFEST, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2)


def _index_exists() -> bool:
    """True if a usable FAISS index file is present."""
    return os.path.isfile(os.path.join(VECTOR_DB_DIR, "index.faiss"))


class RAGPipeline:
    """
    Complete end-to-end Retrieval Augmented Generation Pipeline.
    The knowledge base is managed by the developer via backend/rag/documents/.
    End users interact only with the chat interface.
    """

    _instance: Optional[RAGPipeline] = None

    def __init__(self):
        logger.info("Initializing RAG Pipeline...")
        self.loader = DocumentBatchLoader()
        self.splitter = MedicalTextSplitter(chunk_size=750, chunk_overlap=125)
        self.vector_store_manager = FAISSVectorStoreManager(index_dir=VECTOR_DB_DIR)
        self.retriever = MedicalRetriever(self.vector_store_manager, k=4)
        self.chat_engine = LocalMedicalLLMEngine()

        # Auto-build / reuse knowledge base index
        self._auto_initialize_knowledge_base()
        logger.info("RAG Pipeline initialized successfully.")

    @classmethod
    def get_instance(cls) -> RAGPipeline:
        """Singleton accessor for RAGPipeline."""
        if cls._instance is None:
            cls._instance = RAGPipeline()
        return cls._instance

    # ── Developer-only knowledge base management ─────────────────────────────

    def _auto_initialize_knowledge_base(self) -> None:
        """
        Automatically scan backend/rag/documents/ and build or reuse the FAISS index.

        Logic:
        - If index exists AND manifest matches current PDFs → reuse (fast).
        - If index exists BUT PDFs have changed → rebuild.
        - If no index → build from scratch.
        - If no PDFs and no index → log a warning, chatbot operates in fallback mode.
        """
        os.makedirs(DOCUMENTS_DIR, exist_ok=True)
        os.makedirs(VECTOR_DB_DIR, exist_ok=True)

        pdf_paths = _collect_pdf_paths(DOCUMENTS_DIR)
        current_manifest = _compute_manifest(pdf_paths)
        saved_manifest = _load_manifest()

        if not pdf_paths:
            logger.warning(
                "No PDF documents found in backend/rag/documents/. "
                "The chatbot will respond with a fallback message. "
                "Add PDFs to that directory and restart the application to enable RAG."
            )
            return

        if _index_exists() and current_manifest == saved_manifest:
            logger.info(
                f"FAISS index is up-to-date. Loaded {len(pdf_paths)} PDF(s) from knowledge base."
            )
            return  # vector_store already loaded by FAISSVectorStoreManager.__init__

        # Need to (re)build the index
        reason = "initial build" if not _index_exists() else "PDFs changed"
        logger.info(f"Building FAISS knowledge base index ({reason}) from {len(pdf_paths)} PDF(s)...")

        # Clear stale index so we build fresh
        self.vector_store_manager.clear()

        docs = self.loader.load_documents(pdf_paths)
        if not docs:
            logger.error("Failed to extract text from any PDF in backend/rag/documents/.")
            return

        chunks = self.splitter.split_documents(docs)
        if not chunks:
            logger.error("Text splitting produced no chunks.")
            return

        self.vector_store_manager.add_documents(chunks)
        _save_manifest(current_manifest)
        logger.info(
            f"Knowledge base indexed: {len(pdf_paths)} file(s), "
            f"{len(docs)} pages, {len(chunks)} chunks."
        )

    def rebuild_knowledge_base(self) -> Dict[str, Any]:
        """
        Force a full rebuild of the knowledge base index.
        Called programmatically by the developer; not exposed in the UI.
        """
        pdf_paths = _collect_pdf_paths(DOCUMENTS_DIR)
        if not pdf_paths:
            return {"status": "error", "message": "No PDFs found in backend/rag/documents/"}

        self.vector_store_manager.clear()
        docs = self.loader.load_documents(pdf_paths)
        if not docs:
            return {"status": "error", "message": "Could not extract text from PDFs."}

        chunks = self.splitter.split_documents(docs)
        self.vector_store_manager.add_documents(chunks)
        _save_manifest(_compute_manifest(pdf_paths))

        return {
            "status": "success",
            "files": len(pdf_paths),
            "pages": len(docs),
            "chunks": len(chunks),
        }

    # ── Chat interface (user-facing) ──────────────────────────────────────────

    def ask(
        self,
        query: str,
        chat_history: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        """
        Answer a medical question using the developer knowledge base.

        Args:
            query:        The user's question.
            chat_history: Optional list of past turns [{'role': ..., 'content': ...}].

        Returns:
            {'answer': str}  — intentionally lean; sources are not exposed to the UI.
        """
        if not query or not query.strip():
            return {"answer": "Please enter a valid question."}

        # No documents indexed yet
        if not self.vector_store_manager.get_indexed_documents():
            return {"answer": KB_NO_INFO_MESSAGE}

        # Retrieve
        retrieval_result = self.retriever.retrieve(query)
        context = retrieval_result["context_text"]
        confidence = retrieval_result["confidence_score"]

        if not context or confidence < 15.0:
            return {"answer": KB_NO_INFO_MESSAGE}

        # Generate
        answer = self.chat_engine.generate(
            question=query,
            context=context,
            chat_history=chat_history,
        )

        return {"answer": answer}


def get_rag_pipeline() -> RAGPipeline:
    """Return the global singleton RAGPipeline."""
    return RAGPipeline.get_instance()
