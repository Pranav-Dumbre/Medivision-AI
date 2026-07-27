"""
OCR Engine for MediVision AI.

Extracts text from medical reports in PDF, JPG, JPEG, and PNG formats
using EasyOCR with OpenCV-based preprocessing for improved accuracy.
"""
from __future__ import annotations

import os
import logging
from typing import Optional, Callable

import cv2
import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)

# Lazy-loaded EasyOCR reader (heavy import, load once)
_reader = None


def _get_reader():
    """Lazy-initialize the EasyOCR reader."""
    global _reader
    if _reader is None:
        import easyocr
        logger.info("Initializing EasyOCR reader (first load may download models)...")
        _reader = easyocr.Reader(["en"], gpu=False, verbose=False)
        logger.info("EasyOCR reader ready.")
    return _reader


def preprocess_image(image: np.ndarray) -> np.ndarray:
    """
    Preprocess a medical report image for better OCR accuracy.

    Steps:
    1. Convert to grayscale
    2. Resize if too small
    3. Apply adaptive thresholding
    4. Denoise
    """
    # Convert to grayscale if color
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image.copy()

    # Resize if the image is small (width < 1000px)
    h, w = gray.shape[:2]
    if w < 1000:
        scale = 1500 / w
        gray = cv2.resize(
            gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC
        )

    # Denoise
    denoised = cv2.fastNlMeansDenoising(gray, h=10)

    # Increase contrast using CLAHE
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(denoised)

    # Adaptive thresholding for clean text
    thresh = cv2.adaptiveThreshold(
        enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 15, 8
    )

    return thresh


def extract_text_from_image(
    image_path: str,
    preprocess: bool = True,
) -> str:
    """
    Extract text from a single image file using EasyOCR.

    Args:
        image_path: Path to the image file (JPG, JPEG, PNG).
        preprocess: Whether to apply image preprocessing.

    Returns:
        Extracted text as a single string with lines separated by newlines.
    """
    reader = _get_reader()

    if preprocess:
        # Read with OpenCV and preprocess
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"Cannot read image: {image_path}")
        processed = preprocess_image(img)
        results = reader.readtext(processed, detail=1, paragraph=False)
    else:
        results = reader.readtext(image_path, detail=1, paragraph=False)

    # Sort results by vertical position (top-to-bottom), then horizontal
    results.sort(key=lambda r: (r[0][0][1], r[0][0][0]))

    # Group into lines based on Y-coordinate proximity
    lines = _group_into_lines(results)

    return "\n".join(lines)


def _group_into_lines(
    results: list, y_threshold: float = 15.0
) -> list[str]:
    """
    Group OCR results into logical lines based on Y-coordinate proximity.

    Results that are close vertically are merged into the same line,
    sorted left-to-right within each line.
    """
    if not results:
        return []

    # Each result: (bbox, text, confidence)
    # bbox is [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]
    grouped: list[list] = []
    current_line: list = [results[0]]
    current_y = results[0][0][0][1]  # Top-left Y of first result

    for result in results[1:]:
        top_y = result[0][0][1]
        if abs(top_y - current_y) < y_threshold:
            current_line.append(result)
        else:
            grouped.append(current_line)
            current_line = [result]
            current_y = top_y

    grouped.append(current_line)

    # Sort each line left-to-right and join texts
    lines = []
    for line_items in grouped:
        line_items.sort(key=lambda r: r[0][0][0])  # Sort by X
        line_text = "  ".join(item[1] for item in line_items)
        if line_text.strip():
            lines.append(line_text.strip())

    return lines


def extract_text_from_pdf(
    pdf_path: str,
    progress_callback: Optional[Callable] = None,
) -> str:
    """
    Extract text from a PDF file.

    Strategy:
    1. First attempt direct text extraction (for text-based PDFs).
    2. If no text is found, rasterize pages and run OCR.

    Args:
        pdf_path: Path to the PDF file.
        progress_callback: Optional callback(progress, message) for updates.

    Returns:
        Full extracted text.
    """
    import fitz  # PyMuPDF

    doc = fitz.open(pdf_path)
    total_pages = len(doc)
    all_text_parts: list[str] = []

    # Step 1: Try direct text extraction
    direct_text = ""
    for page in doc:
        direct_text += page.get_text()

    if len(direct_text.strip()) > 50:
        # PDF has embedded text — use it
        logger.info("PDF has embedded text, using direct extraction.")
        doc.close()
        return direct_text.strip()

    # Step 2: Rasterize pages and run OCR
    logger.info(f"PDF appears scanned. Running OCR on {total_pages} page(s)...")
    reader = _get_reader()

    for page_num in range(total_pages):
        if progress_callback:
            progress_callback(
                page_num / total_pages,
                f"Running OCR on page {page_num + 1}/{total_pages}...",
            )

        page = doc[page_num]
        # Render at 300 DPI for good OCR quality
        mat = fitz.Matrix(300 / 72, 300 / 72)
        pix = page.get_pixmap(matrix=mat)

        # Convert pixmap to numpy array
        img_data = pix.tobytes("ppm")
        img_array = np.frombuffer(img_data, dtype=np.uint8)
        # Decode PPM
        nparr = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
            pix.height, pix.width, pix.n
        )
        if pix.n == 4:
            img = cv2.cvtColor(nparr, cv2.COLOR_RGBA2BGR)
        else:
            img = cv2.cvtColor(nparr, cv2.COLOR_RGB2BGR)

        # Preprocess and OCR
        processed = preprocess_image(img)
        results = reader.readtext(processed, detail=1, paragraph=False)
        results.sort(key=lambda r: (r[0][0][1], r[0][0][0]))
        lines = _group_into_lines(results)
        page_text = "\n".join(lines)

        if page_text.strip():
            all_text_parts.append(f"--- Page {page_num + 1} ---\n{page_text}")

    doc.close()
    return "\n\n".join(all_text_parts)


def extract_text(
    file_path: str,
    progress_callback: Optional[Callable] = None,
) -> str:
    """
    Main entry point: extract text from any supported file.

    Args:
        file_path: Path to PDF, JPG, JPEG, or PNG file.
        progress_callback: Optional callback for progress updates.

    Returns:
        Extracted text.

    Raises:
        ValueError: If file type is not supported.
    """
    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".pdf":
        return extract_text_from_pdf(file_path, progress_callback)
    elif ext in (".jpg", ".jpeg", ".png"):
        if progress_callback:
            progress_callback(0.3, "Processing image with OCR...")
        text = extract_text_from_image(file_path)
        if progress_callback:
            progress_callback(1.0, "OCR complete.")
        return text
    else:
        raise ValueError(
            f"Unsupported file type: {ext}. "
            "Supported formats: PDF, JPG, JPEG, PNG."
        )
