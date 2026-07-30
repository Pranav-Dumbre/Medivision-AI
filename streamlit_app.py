"""
MediVision AI — Main Streamlit Application Entry Point.
Enforces Authentication as the mandatory first page.
"""
from __future__ import annotations

import os
import sys
import streamlit as st

# Add project root to sys.path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.main import initialize_app
from frontend.pages.auth import render_auth_page
from frontend.pages.home import render_home_page
from frontend.pages.upload import render_upload_page
from frontend.pages.analysis import render_analysis_page
from frontend.pages.chat import render_chat_page

# ─── Streamlit Page Config ───────────────────────────────────────────────────
st.set_page_config(
    page_title="MediVision AI — Medical Report Analyzer",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Load Custom CSS ─────────────────────────────────────────────────────────
css_path = os.path.join(PROJECT_ROOT, "frontend", "style.css")
if os.path.exists(css_path):
    with open(css_path, "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# ─── Backend + RAG Initialization (runs once, cached) ───────────────────────
@st.cache_resource(show_spinner=False)
def _init_backend_and_rag():
    """Initialize the app backend and pre-build the RAG knowledge base index."""
    initialize_app()
    # Trigger RAG pipeline singleton → auto-scans backend/rag/documents/ and
    # builds / reuses the FAISS index without any user interaction.
    from backend.rag.rag_pipeline import get_rag_pipeline
    get_rag_pipeline()

_init_backend_and_rag()

# ─── Session State Setup ──────────────────────────────────────────────────────
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "user" not in st.session_state:
    st.session_state.user = None
if "current_page" not in st.session_state:
    st.session_state.current_page = "Auth"

# ─── Mandatory Authentication Gatekeeper ─────────────────────────────────────
if not st.session_state.authenticated:
    st.session_state.current_page = "Auth"
    render_auth_page()
else:
    # ── Sidebar Navigation ────────────────────────────────────────────────
    with st.sidebar:
        st.markdown("## 🩺 MediVision AI")
        user_info = st.session_state.get("user") or {}
        user_name = user_info.get("full_name") or user_info.get("email") or "User"
        user_email = user_info.get("email") or ""

        st.markdown(f"""
        <div class="user-profile-card">
            <div class="profile-label">Logged in as</div>
            <div class="profile-name">👤 {user_name}</div>
            {f'<div class="profile-email">{user_email}</div>' if user_email and user_email != user_name else ''}
        </div>
        """, unsafe_allow_html=True)
        st.markdown("---")

        nav_options = {
            "🏠 Home":              "Home",
            "📤 Upload Report":     "Upload",
            "📊 Report Analysis":   "Analysis",
            "💬 Medical Chatbot":   "Chat",
        }

        current_page = st.session_state.get("current_page", "Home")
        page_values = list(nav_options.values())
        default_index = (
            page_values.index(current_page) if current_page in page_values else 0
        )

        selected_label = st.radio(
            "Navigation",
            options=list(nav_options.keys()),
            index=default_index,
            key="nav_radio",
        )

        st.session_state.current_page = nav_options[selected_label]

        st.markdown("---")
        if st.button("🚪 Log Out", use_container_width=True, key="logout_btn"):
            st.session_state.authenticated = False
            st.session_state.user = None
            st.session_state.current_page = "Auth"
            st.session_state.analysis_result = None
            st.rerun()

    # ── Page Router ───────────────────────────────────────────────────────
    active_page = st.session_state.get("current_page", "Home")
    if active_page == "Home":
        render_home_page()
    elif active_page == "Upload":
        render_upload_page()
    elif active_page == "Analysis":
        render_analysis_page()
    elif active_page == "Chat":
        render_chat_page()
    else:
        render_home_page()
