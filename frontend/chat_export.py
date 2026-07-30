"""
Chat Export Utilities for MediVision AI Medical Chatbot.
Generates PDF (using ReportLab) and TXT formats for full conversation and individual responses.
"""
from __future__ import annotations

import io
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
    KeepTogether,
)

logger = logging.getLogger(__name__)

# Brand Colors
BRAND_PRIMARY = colors.HexColor("#0D9488")    # Teal
BRAND_DARK = colors.HexColor("#0F172A")       # Slate 900
BRAND_CARD = colors.HexColor("#1E293B")       # Slate 800
COLOR_TEXT = colors.HexColor("#1E293B")       # Dark text for PDF background
COLOR_MUTED = colors.HexColor("#64748B")      # Muted text
COLOR_USER_BG = colors.HexColor("#F0FDFA")    # Light teal for user question box
COLOR_BORDER = colors.HexColor("#E2E8F0")     # Light border
WHITE = colors.white

def _build_styles():
    """Create paragraph styles for chat exports."""
    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        name="ChatTitle",
        fontSize=20,
        fontName="Helvetica-Bold",
        textColor=BRAND_DARK,
        alignment=TA_CENTER,
        spaceAfter=4,
    ))

    styles.add(ParagraphStyle(
        name="ChatSubtitle",
        fontSize=10,
        fontName="Helvetica",
        textColor=BRAND_PRIMARY,
        alignment=TA_CENTER,
        spaceAfter=14,
    ))

    styles.add(ParagraphStyle(
        name="UserRole",
        fontSize=10,
        fontName="Helvetica-Bold",
        textColor=BRAND_PRIMARY,
        spaceAfter=4,
    ))

    styles.add(ParagraphStyle(
        name="AssistantRole",
        fontSize=10,
        fontName="Helvetica-Bold",
        textColor=colors.HexColor("#1565C0"),
        spaceAfter=4,
    ))

    styles.add(ParagraphStyle(
        name="MessageText",
        fontSize=9.5,
        fontName="Helvetica",
        textColor=COLOR_TEXT,
        alignment=TA_LEFT,
        leading=14,
        spaceAfter=4,
    ))

    styles.add(ParagraphStyle(
        name="MetaText",
        fontSize=8,
        fontName="Helvetica",
        textColor=COLOR_MUTED,
        alignment=TA_CENTER,
        spaceBefore=10,
    ))

    return styles

def _header_footer(canvas, doc):
    """Draw page header and footer."""
    canvas.saveState()
    # Header bar
    canvas.setFillColor(BRAND_DARK)
    canvas.rect(0, A4[1] - 26, A4[0], 26, fill=True, stroke=False)
    canvas.setFillColor(WHITE)
    canvas.setFont("Helvetica-Bold", 9)
    canvas.drawString(20, A4[1] - 18, "Med Scan — Medical AI Chatbot Conversation")
    canvas.drawRightString(
        A4[0] - 20, A4[1] - 18,
        datetime.now().strftime("%d-%b-%Y %I:%M %p")
    )

    # Footer
    canvas.setFillColor(COLOR_BORDER)
    canvas.rect(0, 0, A4[0], 24, fill=True, stroke=False)
    canvas.setFillColor(COLOR_MUTED)
    canvas.setFont("Helvetica", 8)
    canvas.drawCentredString(
        A4[0] / 2, 8,
        "Confidential Medical Consultation Log • MediVision AI System"
    )
    canvas.drawRightString(A4[0] - 20, 8, f"Page {doc.page}")
    canvas.restoreState()

def generate_chat_pdf(messages: List[Dict[str, str]]) -> bytes:
    """
    Generate a formatted PDF document containing full chat history.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=36,
        bottomMargin=36,
        leftMargin=36,
        rightMargin=36,
    )

    styles = _build_styles()
    story = []

    story.append(Spacer(1, 10))
    story.append(Paragraph("🩺 Med Scan – Medical AI Chatbot Conversation", styles["ChatTitle"]))
    story.append(Paragraph(f"Exported on: {datetime.now().strftime('%d-%b-%Y at %I:%M %p')}", styles["ChatSubtitle"]))
    story.append(HRFlowable(width="100%", thickness=1.5, color=BRAND_PRIMARY, spaceBefore=2, spaceAfter=14))

    if not messages:
        story.append(Paragraph("No messages in chat history.", styles["MessageText"]))
    else:
        for idx, msg in enumerate(messages):
            role = msg.get("role", "user")
            content = msg.get("content", "").replace("\n", "<br/>")

            block = []
            if role == "user":
                block.append(Paragraph("👤 User Question:", styles["UserRole"]))
                # Styled box for question
                p = Paragraph(content, styles["MessageText"])
                t = Table([[p]], colWidths=[A4[0] - 72])
                t.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, -1), COLOR_USER_BG),
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#99F6E4")),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ("LEFTPADDING", (0, 0), (-1, -1), 10),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ]))
                block.append(t)
            else:
                block.append(Paragraph("🧑‍⚕️ Assistant Response:", styles["AssistantRole"]))
                p = Paragraph(content, styles["MessageText"])
                t = Table([[p]], colWidths=[A4[0] - 72])
                t.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
                    ("BOX", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                    ("LEFTPADDING", (0, 0), (-1, -1), 10),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ]))
                block.append(t)

            block.append(Spacer(1, 10))
            story.append(KeepTogether(block))

    story.append(HRFlowable(width="100%", thickness=0.5, color=COLOR_BORDER, spaceBefore=10, spaceAfter=10))
    story.append(Paragraph("End of conversation export • MediVision AI", styles["MetaText"]))

    doc.build(story, onFirstPage=_header_footer, onLaterPages=_header_footer)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes

def generate_single_response_pdf(question: str, answer: str) -> bytes:
    """
    Generate PDF for an individual Q&A turn.
    """
    messages = []
    if question:
        messages.append({"role": "user", "content": question})
    messages.append({"role": "assistant", "content": answer})
    return generate_chat_pdf(messages)

def generate_chat_txt(messages: List[Dict[str, str]]) -> str:
    """
    Generate plain text export for full chat.
    """
    lines = [
        "------------------------------------------------",
        "Med Scan Medical AI Chat Export",
        f"Generated: {datetime.now().strftime('%d-%b-%Y %I:%M %p')}",
        "------------------------------------------------",
        ""
    ]

    for msg in messages:
        role = "User" if msg.get("role") == "user" else "Assistant"
        lines.append(f"{role}:")
        lines.append(msg.get("content", "").strip())
        lines.append("")
        lines.append("------------------------------------------------")
        lines.append("")

    return "\n".join(lines)

def generate_single_response_txt(question: str, answer: str) -> str:
    """
    Generate plain text export for a single AI response.
    """
    lines = [
        "------------------------------------------------",
        "Med Scan AI Response",
        f"Generated: {datetime.now().strftime('%d-%b-%Y %I:%M %p')}",
        "------------------------------------------------",
        ""
    ]
    if question:
        lines.append("Question:")
        lines.append(question.strip())
        lines.append("")
    lines.append("Answer:")
    lines.append(answer.strip())
    lines.append("")
    lines.append("------------------------------------------------")

    return "\n".join(lines)
