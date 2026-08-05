"""
Home page for MediVision AI.

Hero section with features, supported reports, and call-to-action.
"""
from __future__ import annotations

import streamlit as st

from frontend.components import render_header


def render_home_page():
    """Render the Home page."""

    render_header()

    # ─── Welcome Section ───
    st.markdown("""
    <div class="fade-in-up" style="text-align:center; margin-bottom:2rem;">
        <h2 style="color:#1565C0; font-weight:700; font-size:1.6rem;">
            Understand Your Medical Reports Instantly
        </h2>
        <p style="color:#78909C; font-size:1.05rem; max-width:600px; margin:0 auto;">
            Upload your blood test, CBC, lipid profile, or any lab report and get an
            AI-powered analysis with clear explanations, risk assessment, and health recommendations.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # ─── Feature Cards ───
    cols = st.columns(4)

    features = [
        ("🔬", "Smart OCR", "Advanced text extraction from PDF and image reports with high accuracy"),
        ("🤖", "AI Analysis", "Powered by MedGemma/BioMistral for intelligent medical interpretation"),
        ("📊", "Visual Dashboard", "Color-coded stats, risk badges, and detailed parameter breakdowns"),
        ("🔒", "100% Private", "All processing happens locally — your data never leaves your machine"),
    ]

    for col, (icon, title, desc) in zip(cols, features):
        with col:
            st.markdown(f"""
            <div class="feature-card">
                <div class="feature-icon">{icon}</div>
                <h3>{title}</h3>
                <p>{desc}</p>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)



    # ─── Call to Action ───
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("""
        <div style="text-align:center; padding:2rem; background: linear-gradient(135deg, #E3F2FD, #E8F5E9);
                    border-radius:16px; border:1px solid rgba(30,136,229,0.15);">
            <h3 style="color:#1565C0; margin-bottom:0.5rem;">Ready to Analyze Your Report?</h3>
            <p style="color:#78909C; margin-bottom:1rem;">
                Upload a PDF, JPG, or PNG file — supports files up to 20 MB
            </p>
        </div>
        """, unsafe_allow_html=True)

        if st.button("📤 Go to Upload Page", use_container_width=True, type="primary"):
            st.session_state.current_page = "Upload"
            st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    # ─── How It Works ───
    st.markdown("""
    <div style="text-align:center; margin:1rem 0 1rem;">
        <h3 style="color:#1565C0; font-weight:700;">⚡ How It Works</h3>
    </div>
    """, unsafe_allow_html=True)

    steps = st.columns(4)
    step_data = [
        ("1️⃣", "Upload", "Upload your medical report in PDF or image format"),
        ("2️⃣", "Extract", "OCR extracts text from your report with high accuracy"),
        ("3️⃣", "Analyze", "AI interprets parameters against medical reference ranges"),
        ("4️⃣", "Results", "View your dashboard with explanations and recommendations"),
    ]

    for col, (num, title, desc) in zip(steps, step_data):
        with col:
            st.markdown(f"""
            <div style="text-align:center; padding:1.25rem;">
                <div style="font-size:2rem; margin-bottom:0.5rem;">{num}</div>
                <div style="font-weight:700; color:#1565C0; margin-bottom:0.25rem;">{title}</div>
                <div style="color:#90A4AE; font-size:0.85rem;">{desc}</div>
            </div>
            """, unsafe_allow_html=True)
