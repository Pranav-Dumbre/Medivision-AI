"""
Analysis / Dashboard page for MediVision AI.

Displays full analysis results: stats, risk, patient info,
parameters, findings, recommendations, and PDF download.
"""
from __future__ import annotations

import os

import streamlit as st

from backend.models.schemas import AnalysisResult
from frontend.components import (
    render_header,
    render_footer,
    render_stats_row,
    render_risk_badge,
    render_patient_info,
    render_summary,
    render_param_card,
    render_findings,
    render_recommendations,
)


def render_analysis_page():
    """Render the Analysis/Dashboard page."""

    render_header()

    result: AnalysisResult = st.session_state.get("analysis_result")

    if result is None:
        st.markdown("""
        <div style="text-align:center; padding:4rem 2rem;">
            <div style="font-size:4rem; margin-bottom:1rem;">📊</div>
            <h3 style="color:#1565C0;">No Analysis Available</h3>
            <p style="color:#78909C;">
                Upload and analyze a medical report to see results here.
            </p>
        </div>
        """, unsafe_allow_html=True)

        if st.button("📤 Go to Upload", use_container_width=True, type="primary"):
            st.session_state.current_page = "Upload"
            st.rerun()
        return

    # ─── Dashboard Header ───
    st.markdown("""
    <h2 style="color:#1565C0; font-weight:700; text-align:center; margin-bottom:0.5rem;">
        📊 Analysis Dashboard
    </h2>
    """, unsafe_allow_html=True)

    # ─── Stats Row ───
    render_stats_row(result)

    st.markdown("<br>", unsafe_allow_html=True)

    # ─── Tabs for sections ───
    tabs = st.tabs([
        "📋 Summary",
        "🔬 Detailed Analysis",
        "💡 Recommendations",
        "📥 Download",
    ])

    # ═══ Summary Tab ═══
    with tabs[0]:
        render_summary(result)

        st.markdown("<br>", unsafe_allow_html=True)

        # Patient Info
        render_patient_info(result)

        st.markdown("<br>", unsafe_allow_html=True)

        # Key Findings
        st.markdown("""
        <h3 style="color:#1565C0; font-weight:700;">🔍 Key Findings</h3>
        """, unsafe_allow_html=True)
        render_findings(result)

        render_footer()

    # ═══ Detailed Analysis Tab ═══
    with tabs[1]:
        st.markdown("""
        <h3 style="color:#1565C0; font-weight:700;">🔬 Parameter-by-Parameter Analysis</h3>
        """, unsafe_allow_html=True)

        if not result.parameters:
            st.info("No parameters were extracted from this report.")
        else:
            # Filter options
            filter_col1, filter_col2 = st.columns([2, 1])
            with filter_col2:
                status_filter = st.selectbox(
                    "Filter by status:",
                    ["All", "Normal", "High", "Low", "Critical"],
                    key="param_filter",
                )

            filtered_params = result.parameters
            if status_filter != "All":
                filtered_params = [
                    p for p in result.parameters
                    if status_filter.lower() in p.status.value.lower()
                ]

            st.markdown(f"<p style='color:#78909C;'>Showing {len(filtered_params)} of {len(result.parameters)} parameters</p>",
                         unsafe_allow_html=True)

            for param in filtered_params:
                render_param_card(param)

        render_footer()

    # ═══ Recommendations Tab ═══
    with tabs[2]:
        st.markdown("""
        <h3 style="color:#1565C0; font-weight:700;">💡 Health Recommendations</h3>
        <p style="color:#78909C; margin-bottom:1rem;">
            Based on your report analysis, here are some general health recommendations.
        </p>
        """, unsafe_allow_html=True)

        render_recommendations(result)

        st.markdown("""
        <div class="disclaimer" style="margin-top:2rem;">
            ⚕️ <strong>Note:</strong> These are general wellness suggestions, not medical prescriptions.
            Always consult your healthcare provider before making changes to your health routine.
        </div>
        """, unsafe_allow_html=True)

    # ═══ Download Tab ═══
    with tabs[3]:
        st.markdown("""
        <h3 style="color:#1565C0; font-weight:700;">📥 Download Report</h3>
        """, unsafe_allow_html=True)

        if result.pdf_path and os.path.exists(result.pdf_path):
            st.markdown(f"""
            <div class="success-box">
                ✅ <strong>PDF report generated successfully!</strong><br>
                📄 File: {result.filename}<br>
                🕐 Analyzed: {result.timestamp}<br>
                📊 Risk Level: {result.risk_level.value}<br>
                📋 Parameters Found: {result.total_params}
            </div>
            """, unsafe_allow_html=True)

            with open(result.pdf_path, "rb") as pdf_file:
                st.download_button(
                    label="📥 Download PDF Report",
                    data=pdf_file.read(),
                    file_name=os.path.basename(result.pdf_path),
                    mime="application/pdf",
                    use_container_width=True,
                    type="primary",
                )
        else:
            st.warning("PDF report is not available for this analysis.")

        # Raw OCR text
        if result.raw_ocr_text:
            with st.expander("📝 View Extracted OCR Text (Raw)"):
                st.text_area(
                    "Raw OCR Output",
                    value=result.raw_ocr_text,
                    height=300,
                    disabled=True,
                )
