"""
SQLite database for storing analysis history.
"""
from __future__ import annotations

import json
import os
import sqlite3
import logging
import uuid
from typing import Optional

from backend.models.schemas import AnalysisResult

logger = logging.getLogger(__name__)

DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data",
    "medivision_ai.db",
)


def _get_connection() -> sqlite3.Connection:
    """Get a database connection, creating the DB file if needed."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def initialize_db() -> None:
    """Create the database tables if they don't exist."""
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS analyses (
            id TEXT PRIMARY KEY,
            filename TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            risk_level TEXT NOT NULL,
            summary TEXT,
            total_params INTEGER DEFAULT 0,
            normal_count INTEGER DEFAULT 0,
            abnormal_count INTEGER DEFAULT 0,
            analysis_mode TEXT DEFAULT 'fallback',
            result_json TEXT NOT NULL,
            pdf_path TEXT
        )
    """)
    conn.commit()
    conn.close()
    logger.info(f"Database initialized at: {DB_PATH}")


def save_analysis(result: AnalysisResult) -> str:
    """
    Save an analysis result to the database.

    Returns:
        The analysis ID.
    """
    if not result.id:
        result.id = str(uuid.uuid4())[:8]

    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT OR REPLACE INTO analyses
        (id, filename, timestamp, risk_level, summary, total_params,
         normal_count, abnormal_count, analysis_mode, result_json, pdf_path)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            result.id,
            result.filename,
            result.timestamp,
            result.risk_level.value,
            result.summary,
            result.total_params,
            result.normal_count,
            result.abnormal_count,
            result.analysis_mode,
            result.model_dump_json(),
            result.pdf_path,
        ),
    )
    conn.commit()
    conn.close()
    logger.info(f"Analysis saved: {result.id}")
    return result.id


def get_history(limit: int = 50) -> list[dict]:
    """
    Get analysis history, most recent first.

    Returns:
        List of dicts with id, filename, timestamp, risk_level, summary.
    """
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, filename, timestamp, risk_level, summary,
               total_params, normal_count, abnormal_count, analysis_mode
        FROM analyses
        ORDER BY timestamp DESC
        LIMIT ?
        """,
        (limit,),
    )
    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def get_analysis_by_id(analysis_id: str) -> Optional[AnalysisResult]:
    """Load a full analysis result by ID."""
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT result_json FROM analyses WHERE id = ?",
        (analysis_id,),
    )
    row = cursor.fetchone()
    conn.close()

    if row is None:
        return None

    return AnalysisResult.model_validate_json(row["result_json"])


def delete_analysis(analysis_id: str) -> bool:
    """Delete an analysis by ID."""
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM analyses WHERE id = ?", (analysis_id,))
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return deleted
