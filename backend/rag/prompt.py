"""
Prompt Template Manager for MediVision AI RAG Chatbot.
Enforces clean instruction formatting, document grounding, and concise responses.
"""
from __future__ import annotations

from typing import List, Dict, Any

NO_INFO_MESSAGE = "I couldn't find this information in the medical knowledge base."

SYSTEM_INSTRUCTION = """You are Med Scan AI, a professional AI Medical Assistant.

Instructions:
1. Answer ONLY using the retrieved medical context provided below.
2. If the required information is unavailable in the context, reply EXACTLY with:
   "I couldn't find this information in the medical knowledge base."
3. Write natural, fluent, and grammatically correct English.
4. Never repeat words, phrases, or sentences.
5. Never copy the prompt, context headings, or prompt tokens into your answer.
6. Provide concise, clear, and complete medical explanations."""


def build_chat_messages(
    question: str, context: str, chat_history: List[Dict[str, str]] = None
) -> List[Dict[str, str]]:
    """
    Build structured message dictionary list for HuggingFace apply_chat_template.

    Args:
        question: Current user query.
        context: Retrieved medical context text.
        chat_history: Optional list of past messages [{'role': 'user'|'assistant', 'content': str}].

    Returns:
        List of message dicts formatted for chat templates.
    """
    system_content = f"{SYSTEM_INSTRUCTION}\n\nMedical Context:\n{context.strip()}"
    messages = [{"role": "system", "content": system_content}]

    if chat_history:
        for msg in chat_history[-6:]:  # Keep last 3 turns
            role = msg.get("role", "user")
            content = msg.get("content", "").strip()
            if content and role in ("user", "assistant"):
                messages.append({"role": role, "content": content})

    messages.append({"role": "user", "content": question.strip()})
    return messages


def build_rag_prompt(
    question: str, context: str, chat_history_str: str = ""
) -> str:
    """
    Fallback plain string prompt formatter for models without chat templates.

    Args:
        question: User query.
        context: Retrieved text chunks from vector store.
        chat_history_str: Optional string representation of prior turns.

    Returns:
        Formatted text prompt string.
    """
    if not context or not context.strip():
        return NO_INFO_MESSAGE

    prompt_parts = [SYSTEM_INSTRUCTION, "\nMedical Context:", context.strip()]

    if chat_history_str and chat_history_str.strip():
        prompt_parts.extend(["\nPrevious Conversation:", chat_history_str.strip()])

    prompt_parts.extend([f"\nUser Question: {question.strip()}", "\nAssistant Answer:"])
    return "\n\n".join(prompt_parts)
