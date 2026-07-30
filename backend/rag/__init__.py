"""
RAG (Retrieval-Augmented Generation) package for MediVision AI.
Provides local document ingestion, chunking, embeddings, FAISS vector search, and local LLM chat engine.
"""

from backend.rag.rag_pipeline import RAGPipeline, get_rag_pipeline

__all__ = ["RAGPipeline", "get_rag_pipeline"]
