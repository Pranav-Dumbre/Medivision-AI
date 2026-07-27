"""
Backend initialization for MediVision AI.

Sets up directories, database, logging, and checks Ollama availability.
"""
from __future__ import annotations

import os
import logging
import sys

# Setup logging safely for Windows console
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def initialize_app() -> None:
    """Initialize the MediVision AI backend services."""
    logger.info("Initializing MediVision AI backend...")

    # Create required directories
    dirs = [
        os.path.join(PROJECT_ROOT, "backend", "uploads"),
        os.path.join(PROJECT_ROOT, "reports"),
        os.path.join(PROJECT_ROOT, "data"),
        os.path.join(PROJECT_ROOT, "static"),
    ]
    for d in dirs:
        os.makedirs(d, exist_ok=True)
        logger.info(f"  Directory ready: {d}")

    # Initialize database
    from backend.database.db import initialize_db
    initialize_db()

    # Check Ollama
    from backend.ai.medical_analyzer import check_ollama_available
    available, model = check_ollama_available()
    if available:
        logger.info(f"  [+] Ollama available — model: {model}")
    else:
        logger.warning(
            "  [!] Ollama not available. Will use rule-based fallback analysis.\n"
            "     To enable AI analysis:\n"
            "     1. Install Ollama: https://ollama.com\n"
            "     2. Pull a medical model: ollama pull medgemma\n"
            "     3. Start Ollama: ollama serve"
        )

    logger.info("Backend initialization complete.\n")
