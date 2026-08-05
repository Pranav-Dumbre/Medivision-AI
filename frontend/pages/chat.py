"""
Streamlit Medical AI Chatbot page for MediVision AI.

Clean end-user interface with official Hugging Face streaming, token-by-token rendering,
'⏹ Stop Generating' control, '🔄 Retry' logic, and full Chat Export (PDF/TXT/Print).
"""
from __future__ import annotations

import logging
import streamlit as st
import streamlit.components.v1 as components

from backend.rag.rag_pipeline import get_rag_pipeline, RAGPipeline
from backend.rag.prompt import NO_INFO_MESSAGE
from frontend.components import render_header
from frontend.chat_export import (
    generate_chat_pdf,
    generate_chat_txt,
    generate_single_response_pdf,
    generate_single_response_txt,
)

logger = logging.getLogger(__name__)


def render_chat_page() -> None:
    """Render the Medical AI Assistant chatbot page."""
    render_header()

    # ── Page Title ─────────────────────────────────────────────────────────
    st.markdown("""
    <div style="
        text-align: center;
        padding: 1.5rem 1rem 0.5rem 1rem;
    " class="no-print">
        <h2 style="
            color: #1565C0;
            font-weight: 800;
            font-size: 1.85rem;
            margin-bottom: 0.4rem;
        ">
            🩺 Medical AI Assistant
        </h2>
        <p style="
            color: #546E7A;
            font-size: 1rem;
            max-width: 680px;
            margin: 0 auto;
            line-height: 1.6;
        ">
            Ask questions related to medical conditions, laboratory tests, diseases,
            medications, nutrition, and the medical knowledge base.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Print-only header
    st.markdown("""
    <div class="print-only-header">
        <h1>Med Scan – Medical AI Chatbot Conversation</h1>
        <p>Official Consultation Export • MediVision AI</p>
        <hr style="border: 1px solid #0D9488; margin: 10px 0;"/>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<br class='no-print'>", unsafe_allow_html=True)

    # ── Initialise RAG pipeline (cached, singleton) ────────────────────────
    @st.cache_resource(show_spinner=False)
    def _get_pipeline() -> RAGPipeline:
        return get_rag_pipeline()

    rag_pipeline = _get_pipeline()

    # ── Session state setup ────────────────────────────────────────────────
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []
    if "chat_feedback" not in st.session_state:
        st.session_state.chat_feedback = {}  # {msg_index: 'like' | 'dislike'}
    if "trigger_print" not in st.session_state:
        st.session_state.trigger_print = False
    if "copy_text" not in st.session_state:
        st.session_state.copy_text = None
    if "pending_retry_query" not in st.session_state:
        st.session_state.pending_retry_query = None
    if "is_generating" not in st.session_state:
        st.session_state.is_generating = False

    # Handle JS print execution
    if st.session_state.trigger_print:
        st.session_state.trigger_print = False
        components.html("<script>window.print();</script>", height=0)

    # Handle JS copy execution
    if st.session_state.copy_text:
        copied_val = st.session_state.copy_text
        st.session_state.copy_text = None
        js_escaped = copied_val.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\r", "")
        components.html(
            f"""<script>
            if (navigator.clipboard) {{
                navigator.clipboard.writeText("{js_escaped}");
            }}
            </script>""",
            height=0,
        )
        st.toast("Copied to clipboard!", icon="📋")

    # ── Action bar (Export Chat & Clear Chat) ──────────────────────────────
    _, export_col, clear_col = st.columns([5, 1.8, 1.2])

    with export_col:
        with st.popover("📄 Export Chat", use_container_width=True):
            st.markdown("#### 📄 Export Options")

            pdf_bytes = generate_chat_pdf(st.session_state.chat_messages)
            st.download_button(
                label="📥 Download Chat as PDF",
                data=pdf_bytes,
                file_name="Med_Scan_Chat_Export.pdf",
                mime="application/pdf",
                use_container_width=True,
                key="export_full_pdf_btn",
            )

            txt_str = generate_chat_txt(st.session_state.chat_messages)
            st.download_button(
                label="📄 Download Chat as TXT",
                data=txt_str,
                file_name="Med_Scan_Chat_Export.txt",
                mime="text/plain",
                use_container_width=True,
                key="export_full_txt_btn",
            )

            if st.button("🖨️ Print Chat", use_container_width=True, key="print_chat_btn"):
                st.session_state.trigger_print = True
                st.rerun()

    with clear_col:
        if st.button(
            "🧹 Clear",
            use_container_width=True,
            type="secondary",
            key="clear_chat_btn",
        ):
            st.session_state.chat_messages = []
            st.session_state.chat_feedback = {}
            st.session_state.pending_retry_query = None
            st.rerun()

    # ── Render Chat History ────────────────────────────────────────────────
    for idx, msg in enumerate(st.session_state.chat_messages):
        avatar = "🧑‍⚕️" if msg["role"] == "assistant" else "👤"
        with st.chat_message(msg["role"], avatar=avatar):
            st.markdown(msg["content"])

            # Render ChatGPT-like action toolbar below assistant responses
            if msg["role"] == "assistant":
                user_question = ""
                if idx > 0 and st.session_state.chat_messages[idx - 1]["role"] == "user":
                    user_question = st.session_state.chat_messages[idx - 1]["content"]

                answer_text = msg["content"]
                current_feedback = st.session_state.chat_feedback.get(idx)

                tb_c1, tb_c2, tb_c3, tb_c4, tb_c5, _ = st.columns([0.07, 0.07, 0.07, 0.18, 0.18, 0.43])

                with tb_c1:
                    like_type = "primary" if current_feedback == "like" else "secondary"
                    if st.button("👍", key=f"like_{idx}", help="Like response", type=like_type):
                        st.session_state.chat_feedback[idx] = "like"
                        st.toast("Thanks for your feedback!", icon="👍")
                        st.rerun()

                with tb_c2:
                    dislike_type = "primary" if current_feedback == "dislike" else "secondary"
                    if st.button("👎", key=f"dislike_{idx}", help="Dislike response", type=dislike_type):
                        st.session_state.chat_feedback[idx] = "dislike"
                        st.toast("Thanks for your feedback!", icon="👎")
                        st.rerun()

                with tb_c3:
                    if st.button("📋", key=f"copy_{idx}", help="Copy response"):
                        st.session_state.copy_text = answer_text
                        st.rerun()

                with tb_c4:
                    with st.popover("📥 Download", use_container_width=True):
                        single_pdf = generate_single_response_pdf(user_question, answer_text)
                        st.download_button(
                            label="PDF Format",
                            data=single_pdf,
                            file_name=f"Med_Scan_Response_{idx}.pdf",
                            mime="application/pdf",
                            use_container_width=True,
                            key=f"dl_single_pdf_{idx}",
                        )

                        single_txt = generate_single_response_txt(user_question, answer_text)
                        st.download_button(
                            label="TXT Format",
                            data=single_txt,
                            file_name=f"Med_Scan_Response_{idx}.txt",
                            mime="text/plain",
                            use_container_width=True,
                            key=f"dl_single_txt_{idx}",
                        )

                with tb_c5:
                    if st.button("🔄 Retry", key=f"retry_{idx}", help="Retry generation for this question"):
                        if user_question:
                            st.session_state.pending_retry_query = user_question
                            # Remove old response turn if retrying
                            st.session_state.chat_messages.pop(idx)
                            st.rerun()

    # ── Check for pending input or pending retry query ────────────────────
    active_prompt = None

    if st.session_state.pending_retry_query:
        active_prompt = st.session_state.pending_retry_query
        st.session_state.pending_retry_query = None
    else:
        user_input = st.chat_input("Type your medical question here…", key="chat_input")
        if user_input:
            active_prompt = user_input
            st.session_state.chat_messages.append({"role": "user", "content": active_prompt})

    # ── Execute Streaming Response Generation ─────────────────────────────
    if active_prompt:
        print("[1] User question received:", active_prompt)
        # Build history context
        history = [
            {"role": m["role"], "content": m["content"]}
            for m in st.session_state.chat_messages[:-1]
        ]
        print("[2] History context built. Length:", len(history))

        # Check knowledge base indexing
        if not rag_pipeline.vector_store_manager.get_indexed_documents():
            st.session_state.chat_messages.append({"role": "assistant", "content": NO_INFO_MESSAGE})
            st.rerun()
            return

        # Retrieve RAG context
        print("[3] Starting RAG Retrieval")
        retrieval = rag_pipeline.retriever.retrieve(active_prompt)
        print("[4] RAG Retrieval Finished")
        context = retrieval.get("context_text", "")
        confidence = retrieval.get("confidence_score", 0.0)
        print(f"[5] Retrieved Context Length: {len(context)}, Confidence: {confidence}")

        if not context or confidence < 15.0:
            st.session_state.chat_messages.append({"role": "assistant", "content": NO_INFO_MESSAGE})
            st.rerun()
            return

        # Prepare assistant streaming UI
        print("[6] Preparing UI for streaming")
        with st.chat_message("assistant", avatar="🧑‍⚕️"):
            message_placeholder = st.empty()

            # Render Stop Generating button container
            stop_col, _ = st.columns([2, 5])
            with stop_col:
                stop_pressed = st.button("⏹ Stop Generating", key="stop_gen_btn", type="secondary")

            accumulated_tokens = []
            st.session_state.is_generating = True

            # Stream tokens using official Hugging Face TextIteratorStreamer
            print("[7] Calling stream_generate")
            try:
                for token in rag_pipeline.chat_engine.stream_generate(
                    question=active_prompt, context=context, chat_history=history, timeout=40.0
                ):
                    if stop_pressed:
                        rag_pipeline.chat_engine.cancel_active_generation()
                        accumulated_tokens.append(" [Generation stopped by user.]")
                        break

                    accumulated_tokens.append(token)
                    full_text = "".join(accumulated_tokens)
                    message_placeholder.markdown(full_text + "▌")

            except Exception as ge:
                logger.error(f"Error during streaming: {ge}")
                print(f"[8-ERROR] Streaming Error: {ge}")
                accumulated_tokens.append(" [An error occurred during generation.]")

            print("[8] Streaming Finished. Returning response.")
            st.session_state.is_generating = False
            final_response = "".join(accumulated_tokens).strip()

            if not final_response:
                final_response = NO_INFO_MESSAGE

            message_placeholder.markdown(final_response)
            print("[9] Streamlit rendering response complete")

        # Persist assistant message and rerun
        st.session_state.chat_messages.append({"role": "assistant", "content": final_response})
        print("[10] Persisting and Rerunning")
        st.rerun()
