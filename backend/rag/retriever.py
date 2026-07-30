"""
Retriever Module for MediVision AI RAG pipeline.
Handles query processing, context retrieval, source attribution, and confidence scoring.
"""
from __future__ import annotations

import logging
from typing import List, Dict, Any, Tuple
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
from backend.rag.vector_store import FAISSVectorStoreManager

logger = logging.getLogger(__name__)


class MedicalRetriever:
    """
    Retriever class for fetching relevant medical document chunks and calculating confidence metrics.
    """

    def __init__(self, vector_store_manager: FAISSVectorStoreManager, k: int = 4):
        self.vector_store_manager = vector_store_manager
        self.k = k

    def retrieve(self, query: str) -> Dict[str, Any]:
        """
        Retrieve relevant context for a user query.

        Args:
            query: Question asked by the user.

        Returns:
            Dictionary containing:
            - 'context_text': Formatted string of combined chunks
            - 'documents': List of Document objects
            - 'sources': List of source attribution dictionaries
            - 'confidence_score': Float percentage (0.0 to 100.0)
            - 'document_names': List of unique document names retrieved
        """
        results: List[Tuple[Document, float]] = (
            self.vector_store_manager.similarity_search_with_score(query, k=self.k)
        )

        if not results:
            logger.info("No documents retrieved for query.")
            return {
                "context_text": "",
                "documents": [],
                "sources": [],
                "confidence_score": 0.0,
                "document_names": [],
            }

        documents: List[Document] = []
        sources: List[Dict[str, Any]] = []
        scores: List[float] = []
        context_parts: List[str] = []
        seen_contents = set()
        doc_names_set = set()

        # Sort results by score (most relevant first)
        results = sorted(results, key=lambda x: x[1])

        for doc, score in results:
            content_clean = doc.page_content.strip()
            if not content_clean or content_clean in seen_contents:
                continue
            seen_contents.add(content_clean)

            documents.append(doc)
            scores.append(score)

            file_name = doc.metadata.get("file_name", "Unknown File")
            page_num = doc.metadata.get("page", 1)
            doc_names_set.add(file_name)

            sources.append({
                "file_name": file_name,
                "page": page_num,
                "content_snippet": content_clean[:200] + "...",
                "score": float(score),
            })

            context_parts.append(content_clean)

        # Calculate confidence score percentage
        avg_score = sum(scores) / len(scores) if scores else 2.0
        confidence = max(0.0, min(100.0, (1.0 - (avg_score / 1.8)) * 100))
        confidence = round(confidence, 1)

        combined_context = "\n\n".join(context_parts)

        return {
            "context_text": combined_context,
            "documents": documents,
            "sources": sources,
            "confidence_score": confidence,
            "document_names": sorted(list(doc_names_set)),
        }
