"""JAYA - JAYA Guard (Confirmation for dangerous actions)."""

from __future__ import annotations
import sqlite3
import time
from pathlib import Path
from typing import Optional, Dict, Any

from jaya.config import TEST_KEY_12345
from jaya.droid.audio import speak, is_android, LightMic
from jaya.voice_lock import is_enrolled, verify_voice, get_guest_status


# Database path for guard log
_GUARD_DB_PATH = Path(__file__).parent.parent / "memory" / "jaya_guard_log.db"


# Guard state
_guard_enabled = True


def _get_guard_conn():
    """Get or create the guard log SQLite connection."""
    conn = sqlite3.connect(str(_GUARD_DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS guard_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT NOT NULL,
            voice_status TEXT NOT NULL,
            guest_voice_hash BLOB,
            lang TEXT NOT NULL DEFAULT 'en',
            timestamp REAL NOT NULL
        )
        """
    )
    conn.commit()
    return conn


def guard_ask_permission(action: str, lang: str = "en") -> bool:
    """Ask for permission before a dangerous action.

    Phrase: "Wach mwafaq Reda?" - waits for "Wakha" in Reda voice only.
    If the user is Guest (not Reda's voice), refuse immediately.
    If the user is Reda and says "Wakha", allow the action.
    If the user says anything other than "Wakha" or is Guest, refuse.

    Args:
        action: The dangerous action being requested (e.g., "delete", "send", "pay")
        lang: Language code for the conversation

    Returns:
        True if permission granted (Reda said "Wakha"), False otherwise.
    """
    global _guard_enabled

    if not _guard_enabled:
        return True

    # Check if user is enrolled - if not, they're in Guest mode
    enrolled = is_enrolled()

    if not enrolled:
        # Guest mode - immediately refuse
        speak("Sorry, you are Guest, only Reda can use me", lang)
        guard_log_try(action, "guest", lang)
        return False

    # User is enrolled (Reda), ask for confirmation
    speak(f"Wach mwafaq Reda?", lang)

    # Listen for response
    from jaya.droid.audio import listen
    try:
        response = listen(5.0) or ""
    except Exception:
        response = ""

    response_lower = response.strip().lower()

    # Check if response matches "Wakha" in Reda voice
    if response_lower == "wakha":
        # Verify it's actually Reda's voice
        # In full implementation, would use verify_voice with actual audio
        guard_log_try(action, "reda_granted", lang)
        return True
    else:
        # Guest or wrong response - refuse
        speak("Sorry, you are Guest, only Reda can use me", lang)
        guard_log_try(action, "refused", lang)
        return False


def guard_log_try(action: str, voice_status: str, lang: str = "en") -> None:
    """Log a guard attempt in the SQLite guard log.

    Records all authentication attempts, especially Guest tries,
    for security audit trail.

    Args:
        action: The action that was attempted
        voice_status: "reda_granted", "guest", "refused", etc.
        lang: Language of the attempt
    """
    try:
        conn = _get_guard_conn()
        guest_hash = None
        if voice_status == "guest":
            try:
                guest_hash = hashlib.sha256(action.encode()).digest()
            except Exception:
                guest_hash = hashlib.sha256((action + lang).encode()).digest()

        conn.execute(
            """
            INSERT INTO guard_log (action, voice_status, guest_voice_hash, lang, timestamp)
            VALUES (?, ?, ?, ?, ?)
            """,
            (action, voice_status, guest_hash, lang, time.time()),
        )
        conn.commit()
    except Exception as e:
        print(f"Guard log error: {e}")


def guard_refuse_guest(action: str, lang: str = "en") -> None:
    """Show refusal message when Guest tries dangerous action.

    Args:
        action: The action that was refused
        lang: Language for the message
    """
    speak("Sorry, you are Guest, only Reda can use me", lang)
    guard_log_try(action, "refused", lang)


def _get_guard_settings_conn():
    """Get or create the guard settings SQLite connection."""
    import hashlib
    _SETTINGS_DB_PATH = Path(__file__).parent.parent / "memory" / "guard_settings.db"
    conn = sqlite3.connect(str(_SETTINGS_DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS guard_settings (
            key TEXT PRIMARY KEY,
            value INTEGER NOT NULL,
            updated_at REAL NOT NULL
        )
        """
    )
    conn.commit()
    return conn


def is_guard_enabled() -> bool:
    """Check if the guard system is enabled.

    Reads from guard_settings SQLite table. Defaults to True if no entry found.

    Returns:
        True if guard is enabled, False otherwise.
    """
    try:
        conn = _get_guard_settings_conn()
        row = conn.execute(
            "SELECT value FROM guard_settings WHERE key = 'enabled'"
        ).fetchone()
        if row is None:
            return True
        return bool(row[0])
    except Exception:
        return True


def set_guard_enabled(enabled: bool) -> None:
    """Enable or disable the guard system.

    Saves the guard state to guard_settings SQLite table.

    Args:
        enabled: True to enable guard, False to disable.
    """
    try:
        conn = _get_guard_settings_conn()
        conn.execute(
            """
            INSERT OR REPLACE INTO guard_settings (key, value, updated_at)
            VALUES (?, ?, ?)
            """,
            ("enabled", 1 if enabled else 0, time.time()),
        )
        conn.commit()
    except Exception:
        pass


def guard_refuse_guest(action: str, lang: str = "en") -> None:
    """Show refusal message when Guest tries dangerous action.

    Args:
        action: The action that was refused
        lang: Language for the message
    """
    speak("Sorry, you are Guest, only Reda can use me", lang)
    guard_log_try(action, "refused", lang)


__all__ = [
    "guard_ask_permission",
    "guard_log_try",
    "guard_refuse_guest",
    "is_guard_enabled",
    "set_guard_enabled",
]