"""
MediVision AI — Gradio Blocks Application.

Full-featured medical report analyzer UI with 6 tabs:
1. Upload & Analyze
2. Dashboard
3. Detailed Analysis
4. Recommendations
5. Download
6. History
"""
from __future__ import annotations

import os
import logging
from datetime import datetime
from typing import Optional

import gradio as gr

from frontend.theme import get_theme
from backend.services.pipeline import process_report
from backend.database.db import get_history, get_analysis_by_id
from backend.models.schemas import AnalysisResult, ParameterStatus, RiskLevel

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────
# CSS for premium styling
# ──────────────────────────────────────────────────────────────
CUSTOM_CSS = """
/* ── Global ── */
.gradio-container {
    max-width: 1200px !important;
    margin: 0 auto !important;
}

/* ── Header ── */
.app-header {
    text-align: center;
    padding: 24px 16px;
    background: linear-gradient(135deg, rgba(13,148,136,0.15), rgba(8,145,178,0.15));
    border-radius: 16px;
    border: 1px solid rgba(13,148,136,0.3);
    margin-bottom: 16px;
}
.app-header h1 {
    font-size: 2.2em;
    background: linear-gradient(135deg, #14b8a6, #06b6d4);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin: 0;
    font-weight: 800;
}
.app-header p {
    color: #94a3b8;
    margin: 4px 0 0 0;
    font-size: 1em;
}

/* ── Stats Cards ── */
.stat-card {
    text-align: center;
    padding: 20px 12px;
    border-radius: 14px;
    border: 1px solid #334155;
    background: #1e293b;
    transition: transform 0.2s ease, box-shadow 0.2s ease;
}
.stat-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 24px rgba(0,0,0,0.3);
}
.stat-card .stat-value {
    font-size: 2.4em;
    font-weight: 800;
    line-height: 1.2;
}
.stat-card .stat-label {
    font-size: 0.85em;
    color: #94a3b8;
    margin-top: 4px;
}
.stat-total .stat-value { color: #60a5fa; }
.stat-normal .stat-value { color: #34d399; }
.stat-abnormal .stat-value { color: #f87171; }
.stat-high .stat-value { color: #ef4444; }
.stat-low .stat-value { color: #fbbf24; }

/* ── Risk Badge ── */
.risk-badge {
    text-align: center;
    padding: 16px;
    border-radius: 14px;
    font-size: 1.3em;
    font-weight: 700;
    margin: 8px 0;
}
.risk-low {
    background: linear-gradient(135deg, rgba(34,197,94,0.2), rgba(34,197,94,0.05));
    border: 1px solid rgba(34,197,94,0.4);
    color: #4ade80;
}
.risk-moderate {
    background: linear-gradient(135deg, rgba(245,158,11,0.2), rgba(245,158,11,0.05));
    border: 1px solid rgba(245,158,11,0.4);
    color: #fbbf24;
}
.risk-high {
    background: linear-gradient(135deg, rgba(239,68,68,0.2), rgba(239,68,68,0.05));
    border: 1px solid rgba(239,68,68,0.4);
    color: #f87171;
}
.risk-unknown {
    background: linear-gradient(135deg, rgba(100,116,139,0.2), rgba(100,116,139,0.05));
    border: 1px solid rgba(100,116,139,0.4);
    color: #94a3b8;
}

/* ── Parameter Cards ── */
.param-card {
    padding: 16px 20px;
    border-radius: 12px;
    border: 1px solid #334155;
    background: #1e293b;
    margin-bottom: 10px;
}
.param-card h3 {
    margin: 0 0 8px 0;
}
.param-normal h3 { color: #34d399; }
.param-high h3 { color: #ef4444; }
.param-low h3 { color: #fbbf24; }
.param-critical h3 { color: #fca5a5; }

/* ── Summary Box ── */
.summary-box {
    padding: 20px;
    border-radius: 14px;
    background: linear-gradient(135deg, rgba(13,148,136,0.1), rgba(8,145,178,0.1));
    border: 1px solid rgba(13,148,136,0.3);
    line-height: 1.7;
    font-size: 1.05em;
}

/* ── Disclaimer ── */
.disclaimer {
    padding: 14px 20px;
    border-radius: 12px;
    background: rgba(239,68,68,0.1);
    border: 1px solid rgba(239,68,68,0.3);
    color: #fca5a5;
    font-size: 0.9em;
    text-align: center;
    margin-top: 12px;
}

/* ── Upload Area ── */
.upload-area {
    border: 2px dashed #475569 !important;
    border-radius: 16px !important;
    transition: border-color 0.3s ease, background 0.3s ease;
}
.upload-area:hover {
    border-color: #0d9488 !important;
    background: rgba(13,148,136,0.05) !important;
}

/* ── History Table ── */
.history-table {
    border-radius: 12px;
    overflow: hidden;
}

/* ── Tab Badges ── */
.tab-nav button {
    font-weight: 600 !important;
    transition: all 0.2s ease !important;
}
.tab-nav button.selected {
    background: linear-gradient(135deg, #0d9488, #0891b2) !important;
    color: white !important;
}

/* ── Animations ── */
@keyframes fadeIn {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
}
.fade-in {
    animation: fadeIn 0.5s ease forwards;
}

@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.6; }
}
.pulse {
    animation: pulse 2s ease-in-out infinite;
}
"""


# ──────────────────────────────────────────────────────────────
# Helper Functions
# ──────────────────────────────────────────────────────────────

def _stat_card_html(value: int | str, label: str, css_class: str) -> str:
    """Generate HTML for a stat card."""
    return f"""
    <div class="stat-card {css_class}">
        <div class="stat-value">{value}</div>
        <div class="stat-label">{label}</div>
    </div>
    """


def _risk_badge_html(risk: RiskLevel) -> str:
    """Generate HTML for the risk level badge."""
    icon = {
        RiskLevel.LOW: "🟢",
        RiskLevel.MODERATE: "🟡",
        RiskLevel.HIGH: "🔴",
        RiskLevel.UNKNOWN: "⚪",
    }.get(risk, "⚪")

    css = {
        RiskLevel.LOW: "risk-low",
        RiskLevel.MODERATE: "risk-moderate",
        RiskLevel.HIGH: "risk-high",
        RiskLevel.UNKNOWN: "risk-unknown",
    }.get(risk, "risk-unknown")

    return f"""
    <div class="risk-badge {css}">
        {icon} {risk.value}
    </div>
    """


def _param_detail_html(param) -> str:
    """Generate detailed HTML for a single parameter."""
    status_icon = {
        ParameterStatus.NORMAL: "✅",
        ParameterStatus.LOW: "⬇️",
        ParameterStatus.HIGH: "⬆️",
        ParameterStatus.CRITICAL_LOW: "🔻",
        ParameterStatus.CRITICAL_HIGH: "🔺",
    }.get(param.status, "❓")

    status_css = {
        ParameterStatus.NORMAL: "param-normal",
        ParameterStatus.LOW: "param-low",
        ParameterStatus.HIGH: "param-high",
        ParameterStatus.CRITICAL_LOW: "param-critical",
        ParameterStatus.CRITICAL_HIGH: "param-critical",
    }.get(param.status, "")

    causes_html = ""
    if param.possible_causes:
        causes_list = "".join(f"<li>{c}</li>" for c in param.possible_causes)
        causes_html = f"<p><strong>Possible Causes:</strong></p><ul>{causes_list}</ul>"

    implications_html = ""
    if param.health_implications:
        imp_list = "".join(f"<li>{i}</li>" for i in param.health_implications)
        implications_html = f"<p><strong>Health Implications:</strong></p><ul>{imp_list}</ul>"

    return f"""
    <div class="param-card {status_css}">
        <h3>{status_icon} {param.test_name}</h3>
        <table style="width:100%; margin: 8px 0;">
            <tr>
                <td><strong>Patient Value:</strong> {param.patient_value} {param.unit}</td>
                <td><strong>Normal Range:</strong> {param.normal_range}</td>
                <td><strong>Status:</strong> {param.status.value}</td>
            </tr>
        </table>
        <p style="color: #cbd5e1;">{param.explanation}</p>
        {causes_html}
        {implications_html}
    </div>
    """


def _build_dashboard_html(result: AnalysisResult) -> str:
    """Build the full dashboard HTML."""
    return f"""
    <div style="display:grid; grid-template-columns: repeat(5, 1fr); gap:12px; margin-bottom:16px;">
        {_stat_card_html(result.total_params, "Total Parameters", "stat-total")}
        {_stat_card_html(result.normal_count, "Normal", "stat-normal")}
        {_stat_card_html(result.abnormal_count, "Abnormal", "stat-abnormal")}
        {_stat_card_html(result.high_count, "High Values", "stat-high")}
        {_stat_card_html(result.low_count, "Low Values", "stat-low")}
    </div>
    """


def _build_summary_html(result: AnalysisResult) -> str:
    """Build the summary section HTML."""
    mode_label = "🤖 AI Analysis" if result.analysis_mode == "ai" else "📐 Rule-Based Analysis"
    return f"""
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
        <span style="color:#94a3b8; font-size:0.9em;">{mode_label}</span>
        <span style="color:#94a3b8; font-size:0.9em;">📄 {result.filename} · {result.timestamp}</span>
    </div>
    {_risk_badge_html(result.risk_level)}
    <div class="summary-box" style="margin-top:12px;">
        {result.summary}
    </div>
    """


def _build_findings_html(result: AnalysisResult) -> str:
    """Build key findings HTML."""
    if not result.key_findings:
        return "<p style='color:#94a3b8;'>No significant findings to highlight.</p>"

    items = "".join(
        f"<li style='margin-bottom:6px;'>{f}</li>"
        for f in result.key_findings
    )
    return f"<ul style='line-height:1.8;'>{items}</ul>"


def _build_params_html(result: AnalysisResult) -> str:
    """Build detailed parameters HTML."""
    if not result.parameters:
        return "<p style='color:#94a3b8;'>No parameters were extracted from this report.</p>"

    html_parts = []
    for param in result.parameters:
        html_parts.append(_param_detail_html(param))
    return "\n".join(html_parts)


def _build_recommendations_html(result: AnalysisResult) -> str:
    """Build recommendations HTML."""
    if not result.recommendations:
        return "<p style='color:#94a3b8;'>No recommendations available.</p>"

    items = ""
    icons = ["💧", "🥗", "🏃", "😴", "🧂", "🚭", "🏥", "💊", "🧘", "📋"]
    for i, rec in enumerate(result.recommendations):
        icon = icons[i] if i < len(icons) else "✅"
        items += f"""
        <div style="padding:10px 16px; margin:6px 0; border-radius:10px;
                     background:rgba(13,148,136,0.08); border:1px solid rgba(13,148,136,0.2);">
            {icon} {rec}
        </div>
        """
    return items


def _build_patient_info_html(result: AnalysisResult) -> str:
    """Build patient info HTML."""
    pi = result.patient_info
    return f"""
    <div style="display:grid; grid-template-columns: repeat(3, 1fr); gap:10px;">
        <div><strong>👤 Name:</strong> {pi.name}</div>
        <div><strong>📅 Age:</strong> {pi.age}</div>
        <div><strong>⚧ Gender:</strong> {pi.gender}</div>
        <div><strong>📋 Report Date:</strong> {pi.report_date}</div>
        <div><strong>🏥 Lab:</strong> {pi.lab_name}</div>
        <div><strong>🔢 Ref #:</strong> {pi.ref_number}</div>
    </div>
    """


# ──────────────────────────────────────────────────────────────
# Global state
# ──────────────────────────────────────────────────────────────
_current_result: Optional[AnalysisResult] = None


# ──────────────────────────────────────────────────────────────
# Application Builder
# ──────────────────────────────────────────────────────────────

def create_app() -> gr.Blocks:
    """Create and return the complete Gradio Blocks application."""

    with gr.Blocks(
        title="MediVision AI — AI Medical Report Analyzer",
    ) as app:

        # ─── Hidden state ───
        analysis_state = gr.State(None)

        # ─── Header ───
        gr.HTML("""
        <div class="app-header">
            <h1>🩺 MediVision AI</h1>
            <p>AI-Powered Medical Report Analyzer — Understand your health reports with ease</p>
        </div>
        """)

        # ─── Tabs ───
        with gr.Tabs() as tabs:

            # ═══════════════════════════════════════════
            # TAB 1: Upload & Analyze
            # ═══════════════════════════════════════════
            with gr.Tab("📤 Upload & Analyze", id="upload"):
                with gr.Row():
                    with gr.Column(scale=2):
                        gr.Markdown("### Upload Your Medical Report")
                        gr.Markdown(
                            "Upload a blood test, CBC, lipid profile, KFT, LFT, thyroid, "
                            "diabetes, or vitamin report in **PDF**, **JPG**, **JPEG**, or **PNG** format."
                        )

                        upload_file = gr.File(
                            label="Drop your report here or click to upload",
                            file_types=[".pdf", ".jpg", ".jpeg", ".png"],
                            file_count="single",
                            elem_classes=["upload-area"],
                        )

                        with gr.Row():
                            analyze_btn = gr.Button(
                                "🔬 Analyze Report",
                                variant="primary",
                                size="lg",
                                interactive=False,
                            )
                            clear_btn = gr.Button(
                                "🗑️ Clear",
                                variant="secondary",
                                size="lg",
                            )

                        status_text = gr.Markdown(
                            value="",
                            elem_classes=["fade-in"],
                        )

                    with gr.Column(scale=1):
                        gr.Markdown("### Supported Reports")
                        gr.Markdown("""
| Report Type | Status |
|:---|:---|
| 🩸 Complete Blood Count (CBC) | ✅ Supported |
| 🫀 Lipid Profile | ✅ Supported |
| 🫘 Kidney Function Test (KFT) | ✅ Supported |
| 🫁 Liver Function Test (LFT) | ✅ Supported |
| 🦋 Thyroid Panel | ✅ Supported |
| 🍬 Diabetes (HbA1c, FBS) | ✅ Supported |
| 💊 Vitamin Reports (D, B12) | ✅ Supported |
| ⚡ Electrolytes | ✅ Supported |
                        """)

                        gr.Markdown("""
> **File Requirements:**
> - Formats: PDF, JPG, JPEG, PNG
> - Max size: 20 MB
> - Clear, readable text
                        """)

            # ═══════════════════════════════════════════
            # TAB 2: Dashboard
            # ═══════════════════════════════════════════
            with gr.Tab("📊 Dashboard", id="dashboard"):
                dashboard_html = gr.HTML(
                    value="<p style='text-align:center; color:#94a3b8; padding:40px;'>"
                    "📤 Upload and analyze a report to see the dashboard.</p>",
                )
                patient_info_html = gr.HTML(value="")
                summary_html = gr.HTML(value="")
                findings_html = gr.HTML(value="")
                disclaimer_md = gr.Markdown(value="")

            # ═══════════════════════════════════════════
            # TAB 3: Detailed Analysis
            # ═══════════════════════════════════════════
            with gr.Tab("🔬 Detailed Analysis", id="details"):
                details_html = gr.HTML(
                    value="<p style='text-align:center; color:#94a3b8; padding:40px;'>"
                    "📤 Upload and analyze a report to see detailed analysis.</p>",
                )

            # ═══════════════════════════════════════════
            # TAB 4: Recommendations
            # ═══════════════════════════════════════════
            with gr.Tab("💡 Recommendations", id="recommendations"):
                recs_html = gr.HTML(
                    value="<p style='text-align:center; color:#94a3b8; padding:40px;'>"
                    "📤 Upload and analyze a report to see recommendations.</p>",
                )
                recs_disclaimer = gr.HTML(value="")

            # ═══════════════════════════════════════════
            # TAB 5: Download
            # ═══════════════════════════════════════════
            with gr.Tab("📥 Download", id="download"):
                gr.Markdown("### Download Your Analysis Report")
                download_info = gr.Markdown(
                    "Upload and analyze a report first to generate a downloadable PDF."
                )
                download_file = gr.File(
                    label="PDF Report",
                    interactive=False,
                    visible=False,
                )
                download_btn = gr.Button(
                    "📥 Download PDF Report",
                    variant="primary",
                    visible=False,
                )
                ocr_text_box = gr.Textbox(
                    label="📝 Extracted OCR Text (Raw)",
                    lines=10,
                    interactive=False,
                    visible=False,
                )

            # ═══════════════════════════════════════════
            # TAB 6: History
            # ═══════════════════════════════════════════
            with gr.Tab("📚 History", id="history"):
                gr.Markdown("### Analysis History")
                refresh_history_btn = gr.Button(
                    "🔄 Refresh", variant="secondary", size="sm"
                )
                history_table = gr.Dataframe(
                    headers=["ID", "File", "Date", "Risk", "Summary"],
                    column_count=(5, "fixed"),
                    interactive=False,
                    elem_classes=["history-table"],
                )

        # ─── Footer Disclaimer ───
        gr.HTML("""
        <div class="disclaimer">
            ⚕️ <strong>DISCLAIMER:</strong> This analysis is generated by an AI system
            for informational and educational purposes only. It is NOT a medical diagnosis.
            Always consult a qualified healthcare provider for proper evaluation and guidance.
        </div>
        """)

        # ──────────────────────────────────────────
        # Event Handlers
        # ──────────────────────────────────────────

        def on_file_upload(file):
            """Enable analyze button when a file is uploaded."""
            if file is not None:
                return gr.update(interactive=True), ""
            return gr.update(interactive=False), ""

        upload_file.change(
            fn=on_file_upload,
            inputs=[upload_file],
            outputs=[analyze_btn, status_text],
        )

        def on_clear():
            """Clear all state."""
            return (
                None,                   # upload_file
                gr.update(interactive=False),  # analyze_btn
                "",                     # status_text
                None,                   # analysis_state
                # Dashboard
                "<p style='text-align:center; color:#94a3b8; padding:40px;'>📤 Upload and analyze a report to see the dashboard.</p>",
                "",
                "",
                "",
                "",
                # Details
                "<p style='text-align:center; color:#94a3b8; padding:40px;'>📤 Upload and analyze a report to see detailed analysis.</p>",
                # Recommendations
                "<p style='text-align:center; color:#94a3b8; padding:40px;'>📤 Upload and analyze a report to see recommendations.</p>",
                "",
                # Download
                "Upload and analyze a report first to generate a downloadable PDF.",
                gr.update(visible=False),
                gr.update(visible=False),
                gr.update(visible=False),
            )

        clear_btn.click(
            fn=on_clear,
            outputs=[
                upload_file, analyze_btn, status_text, analysis_state,
                dashboard_html, patient_info_html, summary_html, findings_html, disclaimer_md,
                details_html,
                recs_html, recs_disclaimer,
                download_info, download_file, download_btn, ocr_text_box,
            ],
        )

        def on_analyze(file, progress=gr.Progress()):
            """Run the full analysis pipeline."""
            if file is None:
                return _analysis_error("No file uploaded.")

            try:
                progress(0.05, desc="Starting analysis...")

                def progress_cb(p, msg):
                    progress(p, desc=msg)

                result = process_report(
                    file_path=file,
                    progress_callback=progress_cb,
                )

                return _analysis_success(result)

            except ValueError as e:
                return _analysis_error(str(e))
            except Exception as e:
                logger.error(f"Analysis failed: {e}", exc_info=True)
                return _analysis_error(f"An unexpected error occurred: {e}")

        def _analysis_error(message: str):
            """Return error state for all outputs."""
            error_html = f"""
            <div style="text-align:center; padding:30px; color:#f87171;">
                <h3>❌ Analysis Failed</h3>
                <p>{message}</p>
            </div>
            """
            return (
                f"❌ **Error:** {message}",     # status_text
                None,                           # analysis_state
                error_html,                     # dashboard_html
                "",                             # patient_info_html
                "",                             # summary_html
                "",                             # findings_html
                "",                             # disclaimer_md
                error_html,                     # details_html
                error_html,                     # recs_html
                "",                             # recs_disclaimer
                f"❌ {message}",                 # download_info
                gr.update(visible=False),       # download_file
                gr.update(visible=False),       # download_btn
                gr.update(visible=False),       # ocr_text_box
            )

        def _analysis_success(result: AnalysisResult):
            """Return success state for all outputs."""
            global _current_result
            _current_result = result

            # Dashboard
            dash = _build_dashboard_html(result)
            patient = _build_patient_info_html(result)
            summary = _build_summary_html(result)
            findings = _build_findings_html(result)
            disclaimer = f'<div class="disclaimer">{result.disclaimer}</div>'

            # Details
            details = _build_params_html(result)

            # Recommendations
            recs = _build_recommendations_html(result)
            recs_disc = f'<div class="disclaimer">{result.disclaimer}</div>'

            # Download
            pdf_available = result.pdf_path and os.path.exists(result.pdf_path)
            dl_info = (
                f"✅ **Report generated successfully!**\n\n"
                f"📄 File: {result.filename}\n\n"
                f"🕐 Analyzed: {result.timestamp}\n\n"
                f"📊 Risk Level: {result.risk_level.value}\n\n"
                f"📋 Parameters Found: {result.total_params}"
            )

            return (
                "✅ **Analysis complete!** Switch to the **Dashboard** tab to view results.",
                result,                                              # analysis_state
                dash,                                                # dashboard_html
                patient,                                             # patient_info_html
                summary,                                             # summary_html
                findings,                                            # findings_html
                disclaimer,                                          # disclaimer_md
                details,                                             # details_html
                recs,                                                # recs_html
                recs_disc,                                           # recs_disclaimer
                dl_info,                                             # download_info
                gr.update(value=result.pdf_path, visible=pdf_available),  # download_file
                gr.update(visible=pdf_available),                    # download_btn
                gr.update(value=result.raw_ocr_text, visible=True), # ocr_text_box
            )

        analyze_btn.click(
            fn=on_analyze,
            inputs=[upload_file],
            outputs=[
                status_text, analysis_state,
                dashboard_html, patient_info_html, summary_html, findings_html, disclaimer_md,
                details_html,
                recs_html, recs_disclaimer,
                download_info, download_file, download_btn, ocr_text_box,
            ],
        )

        def on_download(state):
            """Provide the PDF for download."""
            if state and state.pdf_path and os.path.exists(state.pdf_path):
                return gr.update(value=state.pdf_path, visible=True)
            return gr.update(visible=False)

        download_btn.click(
            fn=on_download,
            inputs=[analysis_state],
            outputs=[download_file],
        )

        def on_refresh_history():
            """Refresh the history table."""
            rows = get_history(limit=25)
            if not rows:
                return []
            return [
                [
                    r["id"],
                    r["filename"],
                    r["timestamp"],
                    r["risk_level"],
                    (r["summary"] or "")[:80] + "...",
                ]
                for r in rows
            ]

        refresh_history_btn.click(
            fn=on_refresh_history,
            outputs=[history_table],
        )

        # Load history on app start
        app.load(fn=on_refresh_history, outputs=[history_table])

    return app
