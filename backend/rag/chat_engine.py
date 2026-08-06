"""
Local LLM Chat Engine for MediVision AI RAG.
Runs 100% locally via Ollama Python client using medgemma:4b-it-q4_K_M.
Provides thread-safe generation streaming, timeout protection, stop flags, and response cleaning.
"""
from __future__ import annotations

import re
import time
import logging
import threading
from typing import List, Dict, Any, Optional, Generator

import ollama

from backend.rag.prompt import (
    build_chat_messages,
    build_rag_prompt,
    NO_INFO_MESSAGE,
)

logger = logging.getLogger(__name__)

MODEL_NAME = "medgemma:4b-it-q4_K_M"


def clean_response_text(text: str) -> str:
    """
    Post-process LLM response to eliminate duplicated words, sentences, broken formatting, or out-of-order tokens.
    """
    if not text or not text.strip():
        return ""

    # 1. Strip common prompt remnants or leading role tags
    prefixes_to_strip = [
        "Answer:", "assistant:", "Assistant:", "<|assistant|>", "[/INST]", "System:", "User:", "Assistant Answer:"
    ]
    for prefix in prefixes_to_strip:
        if text.startswith(prefix):
            text = text[len(prefix):].strip()

    if "Assistant Answer:" in text:
        text = text.split("Assistant Answer:")[-1].strip()
    elif "Answer:" in text:
        text = text.split("Answer:")[-1].strip()

    # 2. Remove duplicate consecutive words (e.g., "is is" -> "is", "the the" -> "the")
    text = re.sub(r"\b(\w+)(?:\s+\1)+\b", r"\1", text, flags=re.IGNORECASE)

    # 3. Remove duplicate sentences while preserving original order
    sentences = re.split(r"(?<=[.!?])\s+", text)
    seen_sentences = set()
    cleaned_sentences = []
    for s in sentences:
        s_clean = s.strip()
        s_lower = s_clean.lower()
        if s_clean and s_lower not in seen_sentences:
            seen_sentences.add(s_lower)
            cleaned_sentences.append(s_clean)

    text = " ".join(cleaned_sentences)

    # 4. Clean up multiple spaces, repeated punctuation, and extra whitespace
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"([.!?])\1+", r"\1", text)

    return text.strip()


class LocalMedicalLLMEngine:
    """
    Local Medical LLM Engine powered by Ollama and medgemma:4b-it-q4_K_M.
    """

    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or MODEL_NAME
        self._is_loaded = False
        self._lock = threading.Lock()
        self._cancel_requested_event = threading.Event()

    def load_model(self) -> None:
        """
        Verify that the Ollama server is running and the target model is available locally.
        """
        with self._lock:
            if self._is_loaded:
                return

            logger.info(f"Verifying local Ollama server and model '{self.model_name}'...")
            try:
                models_response = ollama.list()
                model_list = []
                if isinstance(models_response, dict):
                    model_list = models_response.get("models", [])
                elif hasattr(models_response, "models"):
                    model_list = models_response.models

                model_names = []
                for m in model_list:
                    if isinstance(m, dict):
                        name = m.get("name", "")
                    else:
                        name = getattr(m, "model", getattr(m, "name", ""))
                    if name:
                        model_names.append(name.lower())

                target_lower = self.model_name.lower()
                target_base = target_lower.split(":")[0]

                is_present = any(target_lower in name or target_base in name for name in model_names)

                if not is_present:
                    logger.error(
                        f"Model '{self.model_name}' not found in local Ollama library. "
                        f"Please run `ollama pull {self.model_name}`."
                    )
                    return

                self._is_loaded = True
                logger.info(f"Ollama server connected; model '{self.model_name}' verified.")
            except Exception as e:
                logger.error(f"Local model server is not running. Please start Ollama and try again. Error: {e}")
                self._is_loaded = False

    def cancel_active_generation(self) -> None:
        """
        Set thread-safe cancellation signal for active stream generation loop.
        Note: CancellableStoppingCriteria was removed (it was HuggingFace-specific).
        Cancellation is now handled via threading.Event in the streaming loop.
        """
        self._cancel_requested_event.set()
        logger.info("Signal sent to stop current generation stream.")

    def stream_generate(
        self,
        question: str,
        context: str,
        chat_history: Optional[List[Dict[str, str]]] = None,
        timeout: float = 12o.0,
    ) -> Generator[str, None, None]:
        """
        Stream generated text token-by-token using the official Ollama Python SDK.

        Yields:
            Token text chunks as generated by Ollama.
        """
        if not context or not context.strip():
            yield NO_INFO_MESSAGE
            return

        if not self._is_loaded:
            self.load_model()

        if not self._is_loaded:
            yield self._rule_based_context_answer(question, context)
            return

        self._cancel_requested_event.clear()
        messages = build_chat_messages(question, context, chat_history)

        start_time = time.time()
        last_chunk_time = time.time()
        token_count = 0

        try:
            stream = ollama.chat(
                model=self.model_name,
                messages=messages,
                stream=True,
            )

            for chunk in stream:
                if self._cancel_requested_event.is_set():
                    logger.info("Streamer loop interrupted by user stop request.")
                    break

                if time.time() - last_chunk_time > timeout:
                    logger.warning(f"Ollama generation timed out after {timeout}s")
                    yield " [Response generation timed out. Please try again.]"
                    break

                token_text = ""
                if isinstance(chunk, dict):
                    token_text = chunk.get("message", {}).get("content", "")
                else:
                    msg = getattr(chunk, "message", None)
                    if msg:
                        token_text = getattr(msg, "content", "") if not isinstance(msg, dict) else msg.get("content", "")

                if token_text:
                    token_count += 1
                    last_chunk_time = time.time()
                    yield token_text

            logger.info(f"Ollama generation completed ({token_count} chunks) in {time.time() - start_time:.2f}s")

        except ollama.ResponseError as e:
            logger.error(f"Ollama model error: {e}")
            yield self._rule_based_context_answer(question, context)
        except ConnectionError:
            logger.error("Ollama connection refused — server not running.")
            yield " [Error: Local model server is not running. Please start Ollama and try again.]"
        except Exception as e:
            logger.error(f"Error during Ollama streaming generation: {e}")
            yield self._rule_based_context_answer(question, context)
        finally:
            self._cancel_requested_event.clear()

    def generate(
        self,
        question: str,
        context: str,
        chat_history: Optional[List[Dict[str, str]]] = None,
    ) -> str:
        """
        Non-streaming generation returning complete response string.
        """
        accumulated = []
        for chunk in self.stream_generate(question, context, chat_history):
            accumulated.append(chunk)
        return clean_response_text("".join(accumulated))

    def _rule_based_context_answer(self, question: str, context: str) -> str:
        """
        Deterministic, local fallback answer synthesizer extracting key info from context.
        """
        question_words = set(question.lower().split()) - {
            "what", "is", "the", "in", "of", "and", "a", "for", "to", "my", "how", "are"
        }

        relevant_sentences = []
        for line in context.split("\n"):
            line_clean = line.strip()
            if not line_clean or line_clean.startswith("[Document:"):
                continue
            line_words = set(line_clean.lower().split())
            if len(question_words.intersection(line_words)) >= 1:
                relevant_sentences.append(line_clean)

        if not relevant_sentences:
            return NO_INFO_MESSAGE

        seen = set()
        sentences = []
        for sentence in relevant_sentences:
            s_lower = sentence.lower()
            if s_lower not in seen and len(sentences) < 4:
                sentences.append(sentence)
                seen.add(s_lower)

        raw_answer = " ".join(sentences)
        return clean_response_text(raw_answer)
