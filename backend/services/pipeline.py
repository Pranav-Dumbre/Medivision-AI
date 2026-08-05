"""
End-to-end pipeline: Upload → OCR → AI Analysis → PDF Generation.
"""
from __future__ import annotations

import os
import shutil
import logging
import uuid
from datetime import datetime
from typing import Optional, Callable

from backend.models.schemas import AnalysisResult
from backend.ocr.ocr_engine import extract_text
from backend.ai.medical_analyzer import analyze_with_llm, check_ollama_available
from backend.ai.fallback_analyzer import analyze_fallback
from backend.pdf.report_generator import generate_pdf
from backend.database.db import save_analysis

logger = logging.getLogger(__name__)

# Paths
PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
UPLOAD_DIR = os.path.join(PROJECT_ROOT, "backend", "uploads")
REPORTS_DIR = os.path.join(PROJECT_ROOT, "reports")

# Allowed file types and max size (20 MB)
ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB


def _validate_file(file_path: str) -> tuple[bool, str]:
    """Validate file type and size."""
    if not os.path.exists(file_path):
        return False, "File not found."

    ext = os.path.splitext(file_path)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return False, (
            f"Unsupported file type: {ext}. "
            f"Supported: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    size = os.path.getsize(file_path)
    if size > MAX_FILE_SIZE:
        return False, (
            f"File too large: {size / (1024*1024):.1f} MB. "
            f"Maximum allowed: {MAX_FILE_SIZE / (1024*1024):.0f} MB."
        )

    if size == 0:
        return False, "File is empty."

    return True, "OK"


def process_report(
    file_path: str,
    progress_callback: Optional[Callable] = None,
    force_fallback: bool = False,
    user_id: Optional[str] = None,
) -> AnalysisResult:
    """
    Process a medical report end-to-end.

    Steps:
    1. Validate the uploaded file
    2. Copy to uploads directory
    3. Extract text via OCR
    4. Analyze with AI (or fallback)
    5. Generate PDF report
    6. Save to database
    7. Return structured result

    Args:
        file_path: Path to the uploaded file.
        progress_callback: Optional callback(progress_float, message_str).
        force_fallback: Force rule-based analysis even if Ollama is available.
        user_id: Optional ID of the user uploading the report.

    Returns:
        AnalysisResult with all fields populated.

    Raises:
        ValueError: If the file is invalid.
    """
    # ── Step 1: Validate ──
    _update_progress(progress_callback, 0.05, "Validating file...")
    valid, message = _validate_file(file_path)
    if not valid:
        raise ValueError(message)

    # ── Step 2: Copy to uploads ──
    _update_progress(progress_callback, 0.10, "Processing upload...")
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    os.makedirs(REPORTS_DIR, exist_ok=True)

    filename = os.path.basename(file_path)
    unique_name = f"{uuid.uuid4().hex[:8]}_{filename}"
    upload_path = os.path.join(UPLOAD_DIR, unique_name)
    shutil.copy2(file_path, upload_path)
    logger.info(f"File saved: {upload_path}")

    # ── Step 3: OCR ──
    _update_progress(progress_callback, 0.15, "Extracting text from report (OCR)...")
    try:
        ocr_text = extract_text(
            upload_path,
            progress_callback=lambda p, m: _update_progress(
                progress_callback, 0.15 + p * 0.30, f"OCR: {m}"
            ),
        )
    except Exception as e:
        logger.error(f"OCR failed: {e}")
        raise ValueError(f"Failed to extract text from the report: {e}")

    if not ocr_text or len(ocr_text.strip()) < 10:
        raise ValueError(
            "Could not extract meaningful text from the report. "
            "Please ensure the image is clear and contains readable text."
        )

    logger.info(f"OCR extracted {len(ocr_text)} characters.")

    # ── Step 4: AI Analysis ──
    _update_progress(progress_callback, 0.50, "Analyzing report with AI...")
    result: Optional[AnalysisResult] = None

    if not force_fallback:
        ollama_ok, model_name = check_ollama_available()
        if ollama_ok:
            try:
                _update_progress(
                    progress_callback, 0.55,
                    f"Analyzing with {model_name} (this may take a minute)...",
                )
                result = analyze_with_llm(ocr_text, model=model_name)
                logger.info("LLM analysis completed successfully.")
            except Exception as e:
                logger.warning(f"LLM analysis failed, falling back: {e}")
                result = None

    if result is None:
        _update_progress(
            progress_callback, 0.60,
            "Using rule-based analysis (Ollama not available)...",
        )
        result = analyze_fallback(ocr_text)
        logger.info("Fallback analysis completed.")

    result.filename = filename
    result.raw_ocr_text = ocr_text

    # Extract Patient Info via structured regex (prevents LLM hallucination)
    from backend.ocr.patient_parser import parse_patient_info
    result.patient_info = parse_patient_info(ocr_text)

    # ── Step 5: Generate PDF ──
    _update_progress(progress_callback, 0.80, "Generating PDF report...")
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    pdf_filename = f"MediVision_AI_Report_{timestamp_str}.pdf"
    pdf_path = os.path.join(REPORTS_DIR, pdf_filename)

    try:
        generate_pdf(result, pdf_path)
        result.pdf_path = pdf_filename
        logger.info(f"PDF generated: {pdf_path}")
    except Exception as e:
        logger.error(f"PDF generation failed: {e}")
        # Non-fatal: analysis still available without PDF

    # ── Step 6: Save to DB ──
    _update_progress(progress_callback, 0.90, "Saving analysis...")
    try:
        if user_id != "guest_user":
            analysis_id = save_analysis(result, user_id=user_id)
            result.id = analysis_id
        else:
            result.id = "guest_analysis_temp"
    except Exception as e:
        logger.warning(f"Failed to save to database: {e}")

    _update_progress(progress_callback, 1.0, "Analysis complete! ✅")
    return result


def _update_progress(
    callback: Optional[Callable],
    progress: float,
    message: str,
) -> None:
    """Safely call the progress callback."""
    if callback:
        try:
            callback(progress, message)
        except Exception:
            pass
