"""
Professional PDF Report Generator for MediVision AI.

Uses ReportLab Platypus to create a branded, multi-page PDF report
containing patient info, AI summary, risk badge, parameter table,
recommendations, and disclaimer.
"""
from __future__ import annotations

import os
import logging
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch, mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
    HRFlowable,
    KeepTogether,
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from backend.models.schemas import AnalysisResult, ParameterStatus, RiskLevel

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────
# Brand Colors
# ──────────────────────────────────────────────────────────────
BRAND_PRIMARY = colors.HexColor("#0F766E")    # Teal
BRAND_DARK = colors.HexColor("#134E4A")       # Dark Teal
BRAND_LIGHT = colors.HexColor("#CCFBF1")      # Light Teal
BRAND_ACCENT = colors.HexColor("#2563EB")     # Blue
COLOR_NORMAL = colors.HexColor("#16A34A")     # Green
COLOR_LOW = colors.HexColor("#F59E0B")        # Amber
COLOR_HIGH = colors.HexColor("#EF4444")       # Red
COLOR_CRITICAL = colors.HexColor("#991B1B")   # Dark Red
COLOR_BG_ALT = colors.HexColor("#F8FAFC")     # Slate-50
COLOR_BORDER = colors.HexColor("#E2E8F0")     # Slate-200
WHITE = colors.white
BLACK = colors.HexColor("#1E293B")            # Slate-800


# ──────────────────────────────────────────────────────────────
# Custom Styles
# ──────────────────────────────────────────────────────────────
def _build_styles():
    """Create custom paragraph styles for the PDF."""
    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        name="BrandTitle",
        fontSize=24,
        fontName="Helvetica-Bold",
        textColor=BRAND_DARK,
        alignment=TA_CENTER,
        spaceAfter=6,
    ))

    styles.add(ParagraphStyle(
        name="BrandSubtitle",
        fontSize=10,
        fontName="Helvetica",
        textColor=BRAND_PRIMARY,
        alignment=TA_CENTER,
        spaceAfter=16,
    ))

    styles.add(ParagraphStyle(
        name="SectionHeading",
        fontSize=14,
        fontName="Helvetica-Bold",
        textColor=BRAND_DARK,
        spaceAbove=16,
        spaceAfter=8,
        borderWidth=0,
        borderPadding=4,
    ))

    styles.add(ParagraphStyle(
        name="BodyText_Custom",
        fontSize=10,
        fontName="Helvetica",
        textColor=BLACK,
        alignment=TA_JUSTIFY,
        leading=14,
        spaceAfter=6,
    ))

    styles.add(ParagraphStyle(
        name="SmallText",
        fontSize=8,
        fontName="Helvetica",
        textColor=colors.HexColor("#64748B"),
        leading=10,
    ))

    styles.add(ParagraphStyle(
        name="DisclaimerText",
        fontSize=8,
        fontName="Helvetica-Oblique",
        textColor=colors.HexColor("#DC2626"),
        alignment=TA_CENTER,
        leading=11,
        spaceBefore=12,
    ))

    styles.add(ParagraphStyle(
        name="RiskBadge",
        fontSize=16,
        fontName="Helvetica-Bold",
        alignment=TA_CENTER,
        spaceAfter=4,
    ))

    styles.add(ParagraphStyle(
        name="KeyFinding",
        fontSize=10,
        fontName="Helvetica",
        textColor=BLACK,
        leading=14,
        leftIndent=12,
        spaceAfter=3,
    ))

    styles.add(ParagraphStyle(
        name="Recommendation",
        fontSize=10,
        fontName="Helvetica",
        textColor=BLACK,
        leading=14,
        leftIndent=12,
        bulletIndent=0,
        spaceAfter=3,
    ))

    return styles


# ──────────────────────────────────────────────────────────────
# Header / Footer
# ──────────────────────────────────────────────────────────────
def _header_footer(canvas, doc):
    """Draw header and footer on each page."""
    canvas.saveState()

    # Header bar
    canvas.setFillColor(BRAND_DARK)
    canvas.rect(0, A4[1] - 28, A4[0], 28, fill=True, stroke=False)
    canvas.setFillColor(WHITE)
    canvas.setFont("Helvetica-Bold", 9)
    canvas.drawString(20, A4[1] - 20, "MediVision AI — AI-Powered Medical Report Analysis")
    canvas.drawRightString(
        A4[0] - 20, A4[1] - 20,
        datetime.now().strftime("%B %d, %Y"),
    )

    # Footer
    canvas.setFillColor(COLOR_BORDER)
    canvas.rect(0, 0, A4[0], 30, fill=True, stroke=False)
    canvas.setFillColor(colors.HexColor("#64748B"))
    canvas.setFont("Helvetica", 7)
    canvas.drawCentredString(
        A4[0] / 2, 12,
        "This report is for informational purposes only. Not a medical diagnosis. "
        "Consult a healthcare professional.",
    )
    canvas.drawRightString(A4[0] - 20, 12, f"Page {doc.page}")

    canvas.restoreState()


# ──────────────────────────────────────────────────────────────
# Status helpers
# ──────────────────────────────────────────────────────────────
def _status_color(status: ParameterStatus) -> colors.Color:
    """Return color for a parameter status."""
    mapping = {
        ParameterStatus.NORMAL: COLOR_NORMAL,
        ParameterStatus.LOW: COLOR_LOW,
        ParameterStatus.HIGH: COLOR_HIGH,
        ParameterStatus.CRITICAL_LOW: COLOR_CRITICAL,
        ParameterStatus.CRITICAL_HIGH: COLOR_CRITICAL,
    }
    return mapping.get(status, BLACK)


def _risk_color(risk: RiskLevel) -> colors.Color:
    """Return color for a risk level."""
    mapping = {
        RiskLevel.LOW: COLOR_NORMAL,
        RiskLevel.MODERATE: COLOR_LOW,
        RiskLevel.HIGH: COLOR_HIGH,
    }
    return mapping.get(risk, colors.HexColor("#64748B"))


# ──────────────────────────────────────────────────────────────
# Main Generator
# ──────────────────────────────────────────────────────────────
def generate_pdf(analysis: AnalysisResult, output_path: str) -> str:
    """
    Generate a professional PDF report from an AnalysisResult.

    Args:
        analysis: The analysis result to render.
        output_path: Full path for the output PDF file.

    Returns:
        The output_path on success.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    styles = _build_styles()

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        topMargin=40,
        bottomMargin=40,
        leftMargin=30,
        rightMargin=30,
    )

    story = []

    # ─── Title ───
    story.append(Spacer(1, 12))
    story.append(Paragraph("🩺 MediVision AI Report", styles["BrandTitle"]))
    story.append(
        Paragraph(
            "AI-Powered Medical Report Analysis",
            styles["BrandSubtitle"],
        )
    )
    story.append(HRFlowable(
        width="100%", thickness=2, color=BRAND_PRIMARY,
        spaceBefore=4, spaceAfter=12,
    ))

    # ─── Patient Information ───
    pi = analysis.patient_info
    story.append(Paragraph("Patient Information", styles["SectionHeading"]))

    patient_data = [
        ["Name", pi.name, "Age", pi.age],
        ["Gender", pi.gender, "Report Date", pi.report_date],
        ["Lab Name", pi.lab_name, "Ref. Number", pi.ref_number],
    ]
    patient_table = Table(patient_data, colWidths=[80, 175, 80, 175])
    patient_table.setStyle(TableStyle([
        ("FONT", (0, 0), (0, -1), "Helvetica-Bold", 9),
        ("FONT", (2, 0), (2, -1), "Helvetica-Bold", 9),
        ("FONT", (1, 0), (1, -1), "Helvetica", 9),
        ("FONT", (3, 0), (3, -1), "Helvetica", 9),
        ("TEXTCOLOR", (0, 0), (0, -1), BRAND_DARK),
        ("TEXTCOLOR", (2, 0), (2, -1), BRAND_DARK),
        ("TEXTCOLOR", (1, 0), (1, -1), BLACK),
        ("TEXTCOLOR", (3, 0), (3, -1), BLACK),
        ("BACKGROUND", (0, 0), (-1, -1), BRAND_LIGHT),
        ("GRID", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(patient_table)
    story.append(Spacer(1, 12))

    # ─── Risk Level Badge ───
    story.append(Paragraph("Overall Risk Assessment", styles["SectionHeading"]))
    risk_color = _risk_color(analysis.risk_level)
    risk_icon = {
        RiskLevel.LOW: "🟢",
        RiskLevel.MODERATE: "🟡",
        RiskLevel.HIGH: "🔴",
        RiskLevel.UNKNOWN: "⚪",
    }.get(analysis.risk_level, "⚪")

    risk_style = ParagraphStyle(
        "RiskBadgeInline",
        parent=styles["RiskBadge"],
        textColor=risk_color,
    )
    story.append(
        Paragraph(f"{risk_icon}  {analysis.risk_level.value}", risk_style)
    )
    story.append(Spacer(1, 4))

    # Stats row
    stats_data = [[
        f"Total: {analysis.total_params}",
        f"Normal: {analysis.normal_count}",
        f"High: {analysis.high_count}",
        f"Low: {analysis.low_count}",
        f"Critical: {analysis.critical_count}",
    ]]
    stats_table = Table(stats_data, colWidths=[100] * 5)
    stats_table.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, -1), "Helvetica-Bold", 9),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("TEXTCOLOR", (0, 0), (0, 0), BLACK),
        ("TEXTCOLOR", (1, 0), (1, 0), COLOR_NORMAL),
        ("TEXTCOLOR", (2, 0), (2, 0), COLOR_HIGH),
        ("TEXTCOLOR", (3, 0), (3, 0), COLOR_LOW),
        ("TEXTCOLOR", (4, 0), (4, 0), COLOR_CRITICAL),
        ("BACKGROUND", (0, 0), (-1, -1), COLOR_BG_ALT),
        ("BOX", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(stats_table)
    story.append(Spacer(1, 12))

    # ─── AI Summary ───
    story.append(Paragraph("AI Summary", styles["SectionHeading"]))
    summary_text = analysis.summary.replace("\n", "<br/>")
    story.append(Paragraph(summary_text, styles["BodyText_Custom"]))
    story.append(Spacer(1, 8))

    # ─── Key Findings ───
    if analysis.key_findings:
        story.append(Paragraph("Key Findings", styles["SectionHeading"]))
        for finding in analysis.key_findings:
            story.append(Paragraph(f"• {finding}", styles["KeyFinding"]))
        story.append(Spacer(1, 8))

    # ─── Parameter Table ───
    story.append(Paragraph("Complete Parameter Analysis", styles["SectionHeading"]))

    # Table header
    header = ["#", "Test Name", "Value", "Normal Range", "Status"]
    table_data = [header]

    for i, param in enumerate(analysis.parameters, 1):
        status_text = param.status.value
        table_data.append([
            str(i),
            param.test_name,
            f"{param.patient_value} {param.unit}".strip(),
            param.normal_range,
            status_text,
        ])

    param_table = Table(
        table_data,
        colWidths=[25, 150, 100, 120, 80],
        repeatRows=1,
    )

    # Base table style
    table_style_cmds = [
        # Header
        ("BACKGROUND", (0, 0), (-1, 0), BRAND_DARK),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 9),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        # Body
        ("FONT", (0, 1), (-1, -1), "Helvetica", 8),
        ("ALIGN", (0, 1), (0, -1), "CENTER"),
        ("ALIGN", (4, 1), (4, -1), "CENTER"),
        # Grid
        ("GRID", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]

    # Alternating row colors and status coloring
    for i, param in enumerate(analysis.parameters, 1):
        # Alternate row background
        if i % 2 == 0:
            table_style_cmds.append(
                ("BACKGROUND", (0, i), (-1, i), COLOR_BG_ALT)
            )

        # Color the status cell
        sc = _status_color(param.status)
        table_style_cmds.append(("TEXTCOLOR", (4, i), (4, i), sc))
        table_style_cmds.append(("FONT", (4, i), (4, i), "Helvetica-Bold", 8))

    param_table.setStyle(TableStyle(table_style_cmds))
    story.append(param_table)
    story.append(Spacer(1, 12))

    # ─── Detailed Explanations (for abnormal values) ───
    abnormal = [
        p for p in analysis.parameters
        if p.status not in (ParameterStatus.NORMAL, ParameterStatus.UNKNOWN)
    ]
    if abnormal:
        story.append(PageBreak())
        story.append(Paragraph("Detailed Explanations", styles["SectionHeading"]))

        for param in abnormal:
            block = []
            sc = _status_color(param.status)

            title_style = ParagraphStyle(
                f"ParamTitle_{param.test_name}",
                parent=styles["BodyText_Custom"],
                fontSize=11,
                fontName="Helvetica-Bold",
                textColor=sc,
                spaceAfter=2,
            )
            block.append(
                Paragraph(
                    f"{param.test_name}  —  {param.status.value}",
                    title_style,
                )
            )
            block.append(
                Paragraph(
                    f"<b>Value:</b> {param.patient_value} {param.unit}  |  "
                    f"<b>Normal Range:</b> {param.normal_range}",
                    styles["BodyText_Custom"],
                )
            )
            if param.explanation:
                block.append(
                    Paragraph(param.explanation, styles["BodyText_Custom"])
                )
            if param.possible_causes:
                causes = ", ".join(param.possible_causes)
                block.append(
                    Paragraph(
                        f"<b>Possible Causes:</b> {causes}",
                        styles["BodyText_Custom"],
                    )
                )
            if param.health_implications:
                imps = ", ".join(param.health_implications)
                block.append(
                    Paragraph(
                        f"<b>Health Implications:</b> {imps}",
                        styles["BodyText_Custom"],
                    )
                )
            block.append(Spacer(1, 6))
            block.append(HRFlowable(
                width="100%", thickness=0.5, color=COLOR_BORDER,
                spaceAfter=6,
            ))
            story.append(KeepTogether(block))

    # ─── Recommendations ───
    story.append(Paragraph("Recommendations", styles["SectionHeading"]))
    for i, rec in enumerate(analysis.recommendations, 1):
        story.append(
            Paragraph(f"{i}. {rec}", styles["Recommendation"])
        )
    story.append(Spacer(1, 16))

    # ─── Disclaimer ───
    story.append(HRFlowable(
        width="100%", thickness=1, color=COLOR_HIGH,
        spaceBefore=8, spaceAfter=4,
    ))
    story.append(Paragraph(analysis.disclaimer, styles["DisclaimerText"]))

    # ─── Analysis Metadata ───
    story.append(Spacer(1, 12))
    meta_text = (
        f"Analysis Mode: {analysis.analysis_mode.upper()} | "
        f"Generated: {analysis.timestamp} | "
        f"File: {analysis.filename}"
    )
    story.append(Paragraph(meta_text, styles["SmallText"]))

    # Build PDF
    doc.build(story, onFirstPage=_header_footer, onLaterPages=_header_footer)
    logger.info(f"PDF report generated: {output_path}")

    return output_path
