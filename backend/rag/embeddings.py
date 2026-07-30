"""
Embedding Model Wrapper for MediVision AI RAG module.
Lazy-loads HuggingFace embeddings (BAAI/bge-small-en-v1.5 or sentence-transformers/all-MiniLM-L6-v2).
"""
from __future__ import annotations

import logging
from typing import Optional, Any
try:
    from langchain_huggingface import HuggingFaceEmbeddings
except ImportError:
    try:
        from langchain_community.embeddings import HuggingFaceEmbeddings
    except ImportError:
        from langchain.embeddings import HuggingFaceEmbeddings

logger = logging.getLogger(__name__)

DEFAULT_EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
FALLBACK_EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


class MedicalEmbeddingManager:
    """
    Singleton manager for local HuggingFace embedding models.
    """

    _instance: Optional[MedicalEmbeddingManager] = None
    _embeddings: Optional[HuggingFaceEmbeddings] = None
    _model_name: str = DEFAULT_EMBEDDING_MODEL

    def __new__(cls, model_name: str = DEFAULT_EMBEDDING_MODEL):
        if cls._instance is None:
            cls._instance = super(MedicalEmbeddingManager, cls).__new__(cls)
            cls._instance._model_name = model_name
        return cls._instance

    def get_embeddings(self) -> HuggingFaceEmbeddings:
        """
        Get or initialize the HuggingFace Embeddings instance.
        Lazy loads the model on first call.
        """
        if self._embeddings is None:
            logger.info(f"Loading local embedding model: {self._model_name}...")
            try:
                model_kwargs = {"device": "cpu"}
                encode_kwargs = {"normalize_embeddings": True}
                self._embeddings = HuggingFaceEmbeddings(
                    model_name=self._model_name,
                    model_kwargs=model_kwargs,
                    encode_kwargs=encode_kwargs,
                )
                logger.info(f"Embedding model '{self._model_name}' loaded successfully.")
            except Exception as e:
                logger.warning(
                    f"Failed to load primary embedding model '{self._model_name}': {e}. "
                    f"Attempting fallback to '{FALLBACK_EMBEDDING_MODEL}'..."
                )
                try:
                    self._model_name = FALLBACK_EMBEDDING_MODEL
                    self._embeddings = HuggingFaceEmbeddings(
                        model_name=FALLBACK_EMBEDDING_MODEL,
                        model_kwargs={"device": "cpu"},
                        encode_kwargs={"normalize_embeddings": True},
                    )
                    logger.info(
                        f"Fallback embedding model '{FALLBACK_EMBEDDING_MODEL}' loaded successfully."
                    )
                except Exception as ex:
                    logger.error(f"Failed to load fallback embedding model: {ex}")
                    raise RuntimeError(f"Could not load any embedding model: {ex}")

        return self._embeddings

    @property
    def model_name(self) -> str:
        return self._model_name


def get_embedding_model(model_name: str = DEFAULT_EMBEDDING_MODEL) -> HuggingFaceEmbeddings:
    """Helper function to obtain lazy-loaded embedding model."""
    manager = MedicalEmbeddingManager(model_name=model_name)
    return manager.get_embeddings()
