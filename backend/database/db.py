"""
SQLite database for storing analysis history and user data.
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

    # Users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            full_name TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            is_active INTEGER DEFAULT 1,
            profile_picture TEXT DEFAULT NULL,
            auth_provider TEXT DEFAULT 'local'
        )
    """)

    # Password resets table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS password_resets (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            token TEXT UNIQUE NOT NULL,
            expires_at TEXT NOT NULL,
            used INTEGER DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    # Analyses table (with optional user_id)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS analyses (
            id TEXT PRIMARY KEY,
            user_id TEXT DEFAULT NULL,
            filename TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            risk_level TEXT NOT NULL,
            summary TEXT,
            total_params INTEGER DEFAULT 0,
            normal_count INTEGER DEFAULT 0,
            abnormal_count INTEGER DEFAULT 0,
            analysis_mode TEXT DEFAULT 'fallback',
            result_json TEXT NOT NULL,
            pdf_path TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    # Migrate: add user_id column if table exists without it
    try:
        cursor.execute("SELECT user_id FROM analyses LIMIT 1")
    except sqlite3.OperationalError:
        cursor.execute("ALTER TABLE analyses ADD COLUMN user_id TEXT DEFAULT NULL")
        logger.info("Migrated analyses table: added user_id column.")

    conn.commit()
    conn.close()
    logger.info(f"Database initialized at: {DB_PATH}")


def save_analysis(result: AnalysisResult, user_id: Optional[str] = None) -> str:
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
        (id, user_id, filename, timestamp, risk_level, summary, total_params,
         normal_count, abnormal_count, analysis_mode, result_json, pdf_path)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            result.id,
            user_id,
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
    logger.info(f"Analysis saved: {result.id} (user: {user_id})")
    return result.id


def get_history(limit: int = 50, user_id: Optional[str] = None) -> list[dict]:
    """
    Get analysis history, most recent first.
    If user_id is provided, only return that user's analyses.

    Returns:
        List of dicts with id, filename, timestamp, risk_level, summary.
    """
    conn = _get_connection()
    cursor = conn.cursor()

    if user_id:
        cursor.execute(
            """
            SELECT id, filename, timestamp, risk_level, summary,
                   total_params, normal_count, abnormal_count, analysis_mode
            FROM analyses
            WHERE user_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (user_id, limit),
        )
    else:
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
