"""
Local LLM Chat Engine for MediVision AI RAG.
Runs 100% locally using AutoTokenizer, AutoModelForCausalLM, and official HuggingFace TextIteratorStreamer.
Provides thread-safe generation streaming, timeout protection, CancellableStoppingCriteria, and post-processing.
"""
from __future__ import annotations

import re
import time
import logging
from threading import Thread
from typing import List, Dict, Any, Optional, Generator
import torch

try:
    from transformers import (
        AutoModelForCausalLM,
        AutoTokenizer,
        TextIteratorStreamer,
        StoppingCriteria,
        StoppingCriteriaList,
    )
    import queue
except ImportError:
    AutoModelForCausalLM = None
    AutoTokenizer = None
    TextIteratorStreamer = None
    StoppingCriteria = object
    StoppingCriteriaList = None

from backend.rag.prompt import (
    build_chat_messages,
    build_rag_prompt,
    NO_INFO_MESSAGE,
)

logger = logging.getLogger(__name__)

# Preferred local model identifiers
PREFERRED_MODELS = [
    "BioMistral/BioMistral-7B",
    "google/gemma-2b-it",
    "TinyLlama/TinyLlama-1.1B-Chat-v1.0",
]


class CancellableStoppingCriteria(StoppingCriteria):
    """
    Thread-safe stopping criteria to halt model.generate() on command or timeout.
    """

    def __init__(self):
        super().__init__()
        self.stopped = False

    def stop(self) -> None:
        self.stopped = True

    def __call__(self, input_ids: torch.LongTensor, scores: torch.FloatTensor, **kwargs) -> bool:
        return self.stopped


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
    Local HuggingFace LLM Engine with AutoModelForCausalLM + AutoTokenizer + TextIteratorStreamer.
    """

    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or PREFERRED_MODELS[-1]
        self.tokenizer = None
        self.model = None
        self._is_loaded = False
        self._active_stopping_criteria: Optional[CancellableStoppingCriteria] = None

    def load_model(self) -> None:
        """Lazy load AutoTokenizer and AutoModelForCausalLM locally."""
        if self._is_loaded and self.model is not None and self.tokenizer is not None:
            return

        logger.info(f"Initializing local LLM engine with model: {self.model_name}...")
        try:
            device = "cuda" if torch.cuda.is_available() else "cpu"
            logger.info(f"Using device for local LLM inference: {device}")

            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_name, trust_remote_code=True
            )

            # Configure padding and pad_token_id
            if self.tokenizer.pad_token_id is None:
                self.tokenizer.pad_token_id = self.tokenizer.eos_token_id or 0
            self.tokenizer.padding_side = "left"

            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                torch_dtype=torch.float16 if device == "cuda" else torch.float32,
                device_map="auto" if device == "cuda" else None,
                trust_remote_code=True,
                low_cpu_mem_usage=True,
            )
            self.model.eval()
            self._is_loaded = True
            logger.info(f"Local LLM engine loaded successfully on {device}.")

        except Exception as e:
            logger.warning(f"Could not load local LLM model '{self.model_name}': {e}")
            if self.model_name != PREFERRED_MODELS[-1]:
                logger.info(f"Attempting fallback to lightweight local model: {PREFERRED_MODELS[-1]}")
                self.model_name = PREFERRED_MODELS[-1]
                self.load_model()
            else:
                logger.error("Failed to initialize HuggingFace model. Rule-based prompt responder active.")
                self.model = None
                self.tokenizer = None
                self._is_loaded = False

    def cancel_active_generation(self) -> None:
        """Cancel current model.generate() execution immediately."""
        if self._active_stopping_criteria is not None:
            self._active_stopping_criteria.stop()
            logger.info("Signal sent to stop current generation thread.")

    def stream_generate(
        self,
        question: str,
        context: str,
        chat_history: List[Dict[str, str]] = None,
        timeout: float = 40.0,
    ) -> Generator[str, None, None]:
        """
        Stream generated text token-by-token using Hugging Face TextIteratorStreamer in a background thread.

        Yields:
            Token text chunks as generated.
        """
        if not context or not context.strip():
            yield NO_INFO_MESSAGE
            return

        if not self._is_loaded:
            import psutil
            import torch
            
            # Determine required memory based on model size
            required_gb = 0.0
            if "7b" in self.model_name.lower():
                required_gb = 14.0 if not torch.cuda.is_available() else 8.0
            elif "2b" in self.model_name.lower():
                required_gb = 5.0 if not torch.cuda.is_available() else 3.0
            elif "1.1b" in self.model_name.lower():
                required_gb = 2.5 if not torch.cuda.is_available() else 1.5

            if torch.cuda.is_available():
                # Check VRAM
                available_vram_gb = torch.cuda.get_device_properties(0).total_memory / (1024**3)
                if required_gb > 0 and available_vram_gb < required_gb:
                    error_msg = f" [Error: Insufficient VRAM. '{self.model_name}' requires at least {required_gb:.1f}GB of VRAM, but only {available_vram_gb:.1f}GB is available. The chatbot cannot start.]"
                    logger.error(error_msg)
                    yield error_msg
                    return
            else:
                # Check System RAM
                ram_info = psutil.virtual_memory()
                available_ram_gb = ram_info.available / (1024 ** 3)
                if required_gb > 0 and available_ram_gb < required_gb:
                    error_msg = f" [Error: Insufficient System RAM. '{self.model_name}' requires at least {required_gb:.1f}GB of available RAM, but only {available_ram_gb:.1f}GB is available. This prevents severe system freezing.]"
                    logger.error(error_msg)
                    yield error_msg
                    return
            
            self.load_model()

        if self.model is None or self.tokenizer is None or TextIteratorStreamer is None:
            # Fallback to rule-based answer generator if model is unavailable
            yield self._rule_based_context_answer(question, context)
            return

        try:
            # Format prompt using chat template if available
            formatted_prompt = ""
            if hasattr(self.tokenizer, "apply_chat_template") and callable(self.tokenizer.apply_chat_template):
                try:
                    messages = build_chat_messages(question, context, chat_history)
                    formatted_prompt = self.tokenizer.apply_chat_template(
                        messages, tokenize=False, add_generation_prompt=True
                    )
                except Exception as te:
                    logger.warning(f"Failed to apply chat template: {te}")

            if not formatted_prompt:
                history_str = ""
                if chat_history:
                    history_lines = [
                        f"{'User' if m.get('role') == 'user' else 'Assistant'}: {m.get('content', '')}"
                        for m in chat_history[-6:]
                    ]
                    history_str = "\n".join(history_lines)
                formatted_prompt = build_rag_prompt(question, context, history_str)

            device = "cuda" if torch.cuda.is_available() else "cpu"
            inputs = self.tokenizer(
                formatted_prompt, return_tensors="pt", truncation=True, max_length=2048
            ).to(device)

            # Official TextIteratorStreamer setup
            streamer = TextIteratorStreamer(
                self.tokenizer, skip_prompt=True, skip_special_tokens=True, timeout=timeout
            )
            stopping_criteria = CancellableStoppingCriteria()
            self._active_stopping_criteria = stopping_criteria

            generation_kwargs = dict(
                **inputs,
                streamer=streamer,
                stopping_criteria=StoppingCriteriaList([stopping_criteria]),
                max_new_tokens=512,
                temperature=0.2,
                top_p=0.9,
                top_k=40,
                repetition_penalty=1.15,
                no_repeat_ngram_size=3,
                do_sample=True,
                pad_token_id=self.tokenizer.pad_token_id,
                eos_token_id=self.tokenizer.eos_token_id,
                use_cache=True,
            )

            # Run generate() in background daemon thread
            thread = Thread(target=self.model.generate, kwargs=generation_kwargs)
            thread.daemon = True
            thread.start()

            full_accumulated = []

            try:
                for token_text in streamer:
                    if stopping_criteria.stopped:
                        logger.info("Streamer loop interrupted by user stop request.")
                        break

                    if token_text:
                        full_accumulated.append(token_text)
                        yield token_text
            except queue.Empty:
                logger.warning(f"Generation timeout of {timeout}s reached. Terminating stream.")
                stopping_criteria.stop()
                yield " [Response generation timed out. Please try again.]"

            self._active_stopping_criteria = None


        except Exception as e:
            logger.error(f"Error during streaming generation: {e}")
            yield self._rule_based_context_answer(question, context)

    def generate(
        self, question: str, context: str, chat_history: List[Dict[str, str]] = None
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
