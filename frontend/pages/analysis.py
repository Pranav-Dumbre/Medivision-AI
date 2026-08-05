"""
Analysis / Dashboard page for MediVision AI.

Displays full analysis results: stats, risk, patient info,
parameters, findings, recommendations, and PDF download.
"""
from __future__ import annotations

import os

import streamlit as st

from backend.models.schemas import AnalysisResult
from backend.database.db import get_history, get_analysis_by_id
from backend.services.pipeline import REPORTS_DIR
from frontend.components import (
    render_header,
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
    
    selected_report_id = st.session_state.get("selected_report_id")
    if selected_report_id and selected_report_id != "guest_analysis_temp":
        loaded_result = get_analysis_by_id(selected_report_id)
        if loaded_result:
            st.session_state.analysis_result = loaded_result
            # Clear selected_report_id so we don't keep hitting the DB on every interaction
            # Or keep it to know which one is active? 
            # We can keep it so it's consistent.

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
            
        _render_analysis_history()
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

    # ═══ Recommendations Tab ═══
    with tabs[2]:
        st.markdown("""
        <h3 style="color:#1565C0; font-weight:700;">💡 Health Recommendations</h3>
        <p style="color:#78909C; margin-bottom:1rem;">
            Based on your report analysis, here are some general health recommendations.
        </p>
        """, unsafe_allow_html=True)

        render_recommendations(result)

    # ═══ Download Tab ═══
    with tabs[3]:
        st.markdown("""
        <h3 style="color:#1565C0; font-weight:700;">📥 Download Report</h3>
        """, unsafe_allow_html=True)

        actual_pdf_path = None
        if result.pdf_path:
            # If it's already an absolute path (from old DB records), use it. Otherwise, build it.
            if os.path.isabs(result.pdf_path):
                actual_pdf_path = result.pdf_path
            else:
                actual_pdf_path = os.path.join(REPORTS_DIR, result.pdf_path)

        if actual_pdf_path and os.path.exists(actual_pdf_path):
            st.markdown(f"""
            <div class="success-box">
                ✅ <strong>PDF report generated successfully!</strong><br>
                📄 File: {result.filename}<br>
                🕐 Analyzed: {result.timestamp}<br>
                📊 Risk Level: {result.risk_level.value}<br>
                📋 Parameters Found: {result.total_params}
            </div>
            """, unsafe_allow_html=True)

            try:
                with open(actual_pdf_path, "rb") as pdf_file:
                    st.download_button(
                        label="📥 Download PDF Report",
                        data=pdf_file.read(),
                        file_name=os.path.basename(actual_pdf_path),
                        mime="application/pdf",
                        use_container_width=True,
                        type="primary",
                    )
            except Exception as e:
                st.error(f"Unable to read PDF file for download: {e}")
        else:
            st.warning("PDF report is not available for this analysis.")


    st.markdown("<br><br>", unsafe_allow_html=True)
    _render_analysis_history()


def _render_analysis_history():
    user = st.session_state.get("user")
    if not user or user.get("is_guest", False):
        return
        
    history = get_history(limit=10, user_id=user.get("id"))
    if not history:
        return
        
    st.markdown("""
    <h3 style="color:#1565C0; font-weight:700;">
        📂 Analysis History
    </h3>
    <hr style="margin-top: 0; margin-bottom: 1rem;">
    """, unsafe_allow_html=True)
    
    for row in history:
        with st.container():
            col1, col2, col3, col4 = st.columns([3, 2, 2, 2])
            with col1:
                st.markdown(f"**📄 {row['filename']}**")
            with col2:
                # Add Risk Level Badge with appropriate color if possible, or just text
                risk = row.get('risk_level', 'Unknown')
                color = "#43A047" if "low" in risk.lower() else "#F57C00" if "moderate" in risk.lower() else "#E53935" if "high" in risk.lower() else "#78909C"
                st.markdown(f"**Risk:** <span style='color:{color};'>{risk}</span>", unsafe_allow_html=True)
            with col3:
                # The timestamp in db is like "2026-08-05 22:35:00"
                # The prompt asks for "Analysis Date: 05 Aug 2026" but just timestamp is fine
                st.markdown(f"**Analysis Date:**<br>{row['timestamp'].split(' ')[0]}", unsafe_allow_html=True)
            with col4:
                if st.button("Open Analysis", key=f"open_{row['id']}", use_container_width=True):
                    st.session_state.selected_report_id = row['id']
                    st.rerun()
            st.markdown("<hr style='margin: 0.5rem 0;'>", unsafe_allow_html=True)
