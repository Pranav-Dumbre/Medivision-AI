"""
Authentication manager for MediVision AI.

Handles user registration, login, password reset, and session management.
Uses bcrypt for password hashing and SQLite for user storage.
"""
from __future__ import annotations

import hashlib
import logging
import os
import secrets
import sqlite3
import uuid
from datetime import datetime, timedelta
from typing import Optional

import bcrypt

from backend.database.db import _get_connection

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────
# Database Setup
# ──────────────────────────────────────────────────────────────

def initialize_auth_db() -> None:
    """Create the users and password_resets tables if they don't exist."""
    conn = _get_connection()
    cursor = conn.cursor()

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

    conn.commit()
    conn.close()
    logger.info("Auth database tables initialized.")


# ──────────────────────────────────────────────────────────────
# Password Hashing
# ──────────────────────────────────────────────────────────────

def _hash_password(password: str) -> str:
    """Hash a password with bcrypt."""
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def _verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against its bcrypt hash."""
    try:
        return bcrypt.checkpw(
            password.encode("utf-8"),
            password_hash.encode("utf-8"),
        )
    except Exception:
        return False


# ──────────────────────────────────────────────────────────────
# User Registration
# ──────────────────────────────────────────────────────────────

def register_user(
    email: str,
    full_name: str,
    password: str,
) -> tuple[bool, str, Optional[dict]]:
    """
    Register a new user.

    Returns:
        (success, message, user_dict or None)
    """
    email = email.strip().lower()
    full_name = full_name.strip()

    # Validate inputs
    if not email or "@" not in email:
        return False, "Please enter a valid email address.", None

    if not full_name or len(full_name) < 2:
        return False, "Please enter your full name (at least 2 characters).", None

    if len(password) < 6:
        return False, "Password must be at least 6 characters long.", None

    # Check if user already exists
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
    if cursor.fetchone():
        conn.close()
        return False, "An account with this email already exists.", None

    # Create user
    user_id = str(uuid.uuid4())[:12]
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    password_hash = _hash_password(password)

    cursor.execute(
        """
        INSERT INTO users (id, email, full_name, password_hash, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (user_id, email, full_name, password_hash, now, now),
    )
    conn.commit()
    conn.close()

    user = {
        "id": user_id,
        "email": email,
        "full_name": full_name,
        "created_at": now,
        "auth_provider": "local",
    }

    logger.info(f"New user registered: {email} (ID: {user_id})")
    return True, "Account created successfully! You can now log in.", user


# ──────────────────────────────────────────────────────────────
# User Login
# ──────────────────────────────────────────────────────────────

def login_user(email: str, password: str) -> tuple[bool, str, Optional[dict]]:
    """
    Authenticate a user with email and password.

    Returns:
        (success, message, user_dict or None)
    """
    email = email.strip().lower()

    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, email, full_name, password_hash, created_at, auth_provider "
        "FROM users WHERE email = ? AND is_active = 1",
        (email,),
    )
    row = cursor.fetchone()
    conn.close()

    if row is None:
        return False, "No account found with this email address.", None

    if not _verify_password(password, row["password_hash"]):
        return False, "Incorrect password. Please try again.", None

    user = {
        "id": row["id"],
        "email": row["email"],
        "full_name": row["full_name"],
        "created_at": row["created_at"],
        "auth_provider": row["auth_provider"],
    }

    logger.info(f"User logged in: {email}")
    return True, "Login successful!", user


# ──────────────────────────────────────────────────────────────
# Forgot Password / Reset
# ──────────────────────────────────────────────────────────────

def request_password_reset(email: str) -> tuple[bool, str]:
    """
    Generate a password reset token for the given email.
    The token is printed to console (no SMTP configured).

    Returns:
        (success, message)
    """
    email = email.strip().lower()

    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE email = ? AND is_active = 1", (email,))
    row = cursor.fetchone()

    if row is None:
        conn.close()
        # Don't reveal whether the email exists
        return True, "If an account with that email exists, a reset link has been generated. Check the console output."

    user_id = row["id"]
    token = secrets.token_urlsafe(32)
    expires_at = (datetime.now() + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute(
        """
        INSERT INTO password_resets (id, user_id, token, expires_at)
        VALUES (?, ?, ?, ?)
        """,
        (str(uuid.uuid4())[:8], user_id, token, expires_at),
    )
    conn.commit()
    conn.close()

    # In production, this would send an email. For now, print to console.
    print("\n" + "=" * 60)
    print("  PASSWORD RESET TOKEN")
    print("=" * 60)
    print(f"  Email: {email}")
    print(f"  Token: {token}")
    print(f"  Expires: {expires_at}")
    print("=" * 60 + "\n")

    logger.info(f"Password reset token generated for: {email}")
    return True, "If an account with that email exists, a reset link has been generated. Check the console output."


def reset_password(token: str, new_password: str) -> tuple[bool, str]:
    """
    Reset password using a valid token.

    Returns:
        (success, message)
    """
    if len(new_password) < 6:
        return False, "Password must be at least 6 characters long."

    conn = _get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT user_id, expires_at, used
        FROM password_resets
        WHERE token = ?
        """,
        (token,),
    )
    row = cursor.fetchone()

    if row is None:
        conn.close()
        return False, "Invalid reset token."

    if row["used"]:
        conn.close()
        return False, "This reset token has already been used."

    expires_at = datetime.strptime(row["expires_at"], "%Y-%m-%d %H:%M:%S")
    if datetime.now() > expires_at:
        conn.close()
        return False, "This reset token has expired. Please request a new one."

    # Update password
    user_id = row["user_id"]
    password_hash = _hash_password(new_password)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute(
        "UPDATE users SET password_hash = ?, updated_at = ? WHERE id = ?",
        (password_hash, now, user_id),
    )
    cursor.execute(
        "UPDATE password_resets SET used = 1 WHERE token = ?",
        (token,),
    )
    conn.commit()
    conn.close()

    logger.info(f"Password reset completed for user: {user_id}")
    return True, "Password reset successfully! You can now log in with your new password."


# ──────────────────────────────────────────────────────────────
# Profile Management
# ──────────────────────────────────────────────────────────────

def update_profile(user_id: str, full_name: str) -> tuple[bool, str]:
    """Update a user's profile (name)."""
    full_name = full_name.strip()
    if len(full_name) < 2:
        return False, "Name must be at least 2 characters."

    conn = _get_connection()
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        "UPDATE users SET full_name = ?, updated_at = ? WHERE id = ?",
        (full_name, now, user_id),
    )
    updated = cursor.rowcount > 0
    conn.commit()
    conn.close()

    if updated:
        return True, "Profile updated successfully!"
    return False, "Failed to update profile."


def change_password(
    user_id: str, current_password: str, new_password: str
) -> tuple[bool, str]:
    """Change a user's password after verifying the current one."""
    if len(new_password) < 6:
        return False, "New password must be at least 6 characters long."

    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT password_hash FROM users WHERE id = ?",
        (user_id,),
    )
    row = cursor.fetchone()
    conn.close()

    if row is None:
        return False, "User not found."

    if not _verify_password(current_password, row["password_hash"]):
        return False, "Current password is incorrect."

    conn = _get_connection()
    cursor = conn.cursor()
    password_hash = _hash_password(new_password)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        "UPDATE users SET password_hash = ?, updated_at = ? WHERE id = ?",
        (password_hash, now, user_id),
    )
    conn.commit()
    conn.close()

    return True, "Password changed successfully!"


def get_user_by_id(user_id: str) -> Optional[dict]:
    """Fetch a user by their ID."""
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, email, full_name, created_at, auth_provider "
        "FROM users WHERE id = ? AND is_active = 1",
        (user_id,),
    )
    row = cursor.fetchone()
    conn.close()

    if row is None:
        return None

    return dict(row)
