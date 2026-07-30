"""
FAISS Vector Store Manager for MediVision AI RAG module.
Manages vector index persistence, document additions, document deletions, and vector search.
"""
from __future__ import annotations

import os
import shutil
import logging
from typing import List, Tuple, Optional, Set
try:
    from langchain_community.vectorstores import FAISS
except ImportError:
    from langchain.vectorstores import FAISS

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
from backend.rag.embeddings import get_embedding_model

logger = logging.getLogger(__name__)

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
DEFAULT_FAISS_DIR = os.path.join(PROJECT_ROOT, "backend", "rag", "vector_db")


class FAISSVectorStoreManager:
    """
    Manages local FAISS vector store with persistence and CRUD operations on documents.
    """

    def __init__(self, index_dir: str = DEFAULT_FAISS_DIR):
        self.index_dir = index_dir
        self.embedding_model = get_embedding_model()
        self.vector_store: Optional[FAISS] = None
        self._load_or_initialize()

    def _load_or_initialize(self) -> None:
        """Load existing index from disk if available."""
        if os.path.exists(self.index_dir) and os.path.exists(
            os.path.join(self.index_dir, "index.faiss")
        ):
            try:
                self.vector_store = FAISS.load_local(
                    folder_path=self.index_dir,
                    embeddings=self.embedding_model,
                    allow_dangerous_deserialization=True,
                )
                logger.info(f"Loaded existing FAISS vector store from '{self.index_dir}'.")
            except Exception as e:
                logger.warning(f"Could not load FAISS store from '{self.index_dir}': {e}")
                self.vector_store = None
        else:
            self.vector_store = None

    def save(self) -> None:
        """Persist FAISS vector store to disk."""
        if self.vector_store is not None:
            os.makedirs(self.index_dir, exist_ok=True)
            self.vector_store.save_local(self.index_dir)
            logger.info(f"Saved FAISS index to '{self.index_dir}'.")

    def add_documents(self, documents: List[Document]) -> None:
        """
        Add new document chunks to the FAISS store and persist.

        Args:
            documents: List of Document objects to index.
        """
        if not documents:
            logger.warning("No documents provided to add to vector store.")
            return

        if self.vector_store is None:
            self.vector_store = FAISS.from_documents(
                documents=documents, embedding=self.embedding_model
            )
        else:
            self.vector_store.add_documents(documents)

        self.save()
        logger.info(f"Added {len(documents)} document chunks to FAISS store.")

    def delete_document(self, file_name: str) -> bool:
        """
        Remove all chunks associated with a specific document filename.

        Args:
            file_name: Name of the file to remove (e.g. 'report.pdf').

        Returns:
            True if document was found and removed, False otherwise.
        """
        if self.vector_store is None:
            return False

        # Extract all existing documents except ones matching file_name
        doc_dict = self.vector_store.docstore._dict
        remaining_docs: List[Document] = []
        found = False

        for doc_id, doc in doc_dict.items():
            doc_filename = doc.metadata.get("file_name", "")
            doc_source = doc.metadata.get("source", "")
            if doc_filename == file_name or os.path.basename(doc_source) == file_name:
                found = True
            else:
                remaining_docs.append(doc)

        if not found:
            logger.info(f"Document '{file_name}' not found in vector store.")
            return False

        # Re-build index with remaining documents or clear if empty
        if remaining_docs:
            self.vector_store = FAISS.from_documents(
                documents=remaining_docs, embedding=self.embedding_model
            )
            self.save()
        else:
            self.clear()

        logger.info(f"Successfully deleted document '{file_name}' from vector store.")
        return True

    def clear(self) -> None:
        """Clear the vector store completely."""
        self.vector_store = None
        if os.path.exists(self.index_dir):
            try:
                shutil.rmtree(self.index_dir)
                logger.info(f"Removed FAISS index directory: {self.index_dir}")
            except Exception as e:
                logger.error(f"Error deleting index directory: {e}")

    def get_indexed_documents(self) -> List[str]:
        """
        Return a list of unique document filenames currently indexed in the vector store.
        """
        if self.vector_store is None:
            return []

        doc_names: Set[str] = set()
        doc_dict = self.vector_store.docstore._dict
        for _, doc in doc_dict.items():
            name = doc.metadata.get("file_name") or os.path.basename(doc.metadata.get("source", ""))
            if name:
                doc_names.add(name)

        return sorted(list(doc_names))

    def similarity_search_with_score(
        self, query: str, k: int = 4
    ) -> List[Tuple[Document, float]]:
        """
        Perform similarity search with distance scores.

        Args:
            query: User search query.
            k: Number of top chunks to retrieve.

        Returns:
            List of (Document, float_distance) tuples.
        """
        if self.vector_store is None:
            return []
        try:
            return self.vector_store.similarity_search_with_score(query, k=k)
        except Exception as e:
            logger.error(f"Error during FAISS search: {e}")
            return []
