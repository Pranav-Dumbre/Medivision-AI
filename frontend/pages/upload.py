"""
Upload page for MediVision AI.

Handles file upload, validation, and triggering the analysis pipeline.
"""
from __future__ import annotations

import os
import tempfile
import logging

import streamlit as st

from backend.services.pipeline import process_report
from frontend.components import render_header

logger = logging.getLogger(__name__)


def render_upload_page():
    """Render the Upload & Analyze page."""

    render_header()

    st.markdown("""
    <h2 style="color:#1565C0; font-weight:700; text-align:center;">
        📤 Upload Your Medical Report
    </h2>
    <p style="color:#78909C; text-align:center; margin-bottom:1.5rem;">
        Upload a blood test, CBC, lipid profile, KFT, LFT, thyroid, diabetes, or vitamin report
    </p>
    """, unsafe_allow_html=True)

    # ─── Layout ───
    col_upload, col_info = st.columns([3, 2])

    with col_upload:
        st.markdown("""
        <div class="info-box">
            📂 <strong>Supported formats:</strong> PDF, JPG, JPEG, PNG — Max size: 20 MB
        </div>
        """, unsafe_allow_html=True)

        uploaded_file = st.file_uploader(
            "Drop your report here or click to upload",
            type=["pdf", "jpg", "jpeg", "png"],
            accept_multiple_files=False,
            key="report_uploader",
        )

        if uploaded_file is not None:
            # Show file info
            file_size_mb = uploaded_file.size / (1024 * 1024)
            st.markdown(f"""
            <div class="success-box">
                ✅ <strong>File ready:</strong> {uploaded_file.name}
                ({file_size_mb:.1f} MB)
            </div>
            """, unsafe_allow_html=True)

            # Analyze button
            if st.button("🔬 Analyze Report", use_container_width=True, type="primary"):
                _run_analysis(uploaded_file)

        else:
            st.markdown("""
            <div style="text-align:center; padding:3rem; border:2px dashed #90CAF9;
                        border-radius:16px; background:rgba(30,136,229,0.02); margin-top:1rem;">
                <div style="font-size:3rem; margin-bottom:0.75rem;">📄</div>
                <p style="color:#90A4AE; font-size:1rem;">
                    Drag and drop a file above or click to browse
                </p>
            </div>
            """, unsafe_allow_html=True)

    with col_info:
        st.markdown("""
        <div class="param-card" style="margin-top:0;">
            <h4 style="color:#1565C0;">📋 Supported Reports</h4>
            <table style="width:100%; font-size:0.9rem;">
                <tr><td>🩸 Complete Blood Count (CBC)</td><td style="color:#43A047;">✅</td></tr>
                <tr><td>🫀 Lipid Profile</td><td style="color:#43A047;">✅</td></tr>
                <tr><td>🫘 Kidney Function Test (KFT)</td><td style="color:#43A047;">✅</td></tr>
                <tr><td>🫁 Liver Function Test (LFT)</td><td style="color:#43A047;">✅</td></tr>
                <tr><td>🦋 Thyroid Panel</td><td style="color:#43A047;">✅</td></tr>
                <tr><td>🍬 Diabetes (HbA1c, FBS)</td><td style="color:#43A047;">✅</td></tr>
                <tr><td>💊 Vitamin Reports (D, B12)</td><td style="color:#43A047;">✅</td></tr>
                <tr><td>⚡ Electrolytes</td><td style="color:#43A047;">✅</td></tr>
            </table>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div class="info-box" style="margin-top:1rem;">
            <strong>💡 Tips for best results:</strong><br>
            • Use clear, high-resolution images<br>
            • Ensure text is readable and not blurred<br>
            • Crop out unnecessary borders if possible<br>
            • PDF reports with embedded text work best
        </div>
        """, unsafe_allow_html=True)


def _run_analysis(uploaded_file):
    """Run the analysis pipeline with progress feedback."""
    progress_bar = st.progress(0, text="Starting analysis...")
    status_placeholder = st.empty()

    try:
        # Save uploaded file to a temp location
        suffix = os.path.splitext(uploaded_file.name)[1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(uploaded_file.getbuffer())
            tmp_path = tmp.name

        def progress_callback(p, msg):
            progress_bar.progress(min(p, 1.0), text=msg)

        # Run the pipeline
        user_id = st.session_state.get("user", {}).get("id")
        result = process_report(
            file_path=tmp_path,
            progress_callback=progress_callback,
            user_id=user_id,
        )

        # Clean up temp file
        try:
            os.unlink(tmp_path)
        except Exception:
            pass

        # Store result in session and navigate
        st.session_state.analysis_result = result
        progress_bar.progress(1.0, text="Analysis complete! ✅")

        status_placeholder.markdown("""
        <div class="success-box">
            ✅ <strong>Analysis complete!</strong> Redirecting to results...
        </div>
        """, unsafe_allow_html=True)

        st.session_state.current_page = "Analysis"
        st.rerun()

    except ValueError as e:
        progress_bar.empty()
        status_placeholder.error(f"❌ {str(e)}")

    except Exception as e:
        progress_bar.empty()
        logger.error(f"Analysis failed: {e}", exc_info=True)
        status_placeholder.error(f"❌ An unexpected error occurred: {str(e)}")
