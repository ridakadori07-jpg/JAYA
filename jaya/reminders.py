"""JAYA - Local-only reminders in SQLite.

Never sends data to internet. All storage is local encrypted SQLite.
Tables: reminders (id, text, time, done, lang)

Commands:
- Voice: "fkrini f 8" / "remind me at 8" / "saat 8'de hatirlat" / "rappelle-moi à 8h"
  -> save reminder in SQLite, speak confirmation in same language
- "show my reminders" -> list all reminders, ask which to delete
- "delete reminder" -> ask which, wait Yes
- "clear reminders" -> ask Yes twice
- At reminder time: speak reminder + notification + show "Reminder: ..."
"""

from __future__ import annotations

import sqlite3
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any

from jaya.config import TEST_KEY_12345
from jaya.memory import JayaMemory


# Database path within JAYA's local storage
_DB_PATH = Path(__file__).parent.parent / "memory" / "jaya_reminders.db"


def _get_conn():
    """Get or create the reminders SQLite connection."""
    conn = sqlite3.connect(str(_DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT NOT NULL,
            trigger_time TEXT NOT NULL,
            done INTEGER NOT NULL DEFAULT 0,
            lang TEXT NOT NULL DEFAULT 'en',
            created_at REAL NOT NULL
        )
        """
    )
    conn.commit()
    return conn


def save_reminder(text: str, trigger_minutes: int, lang: str = "en") -> int:
    """Save a reminder to trigger in trigger_minutes from now.

    Returns the reminder id.
    """
    conn = _get_conn()
    trigger_time = (datetime.now() + timedelta(minutes=trigger_minutes)).strftime("%Y-%m-%d %H:%M:%S")
    done = 0
    created_at = time.time()

    cur = conn.execute(
        """
        INSERT INTO reminders (text, trigger_time, done, lang, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (text, trigger_time, done, lang, created_at),
    )
    conn.commit()
    reminder_id = int(cur.lastrowid or 0)

    # Speak confirmation in the same language
    from jaya.droid.audio import speak
    speak(f"Reminder saved: {text}", lang)

    return reminder_id


def get_reminders(done: bool | None = None) -> List[Dict[str, Any]]:
    """Get reminders from SQLite.

    If done is None, return all. If True, return only done. If False, return only pending.
    """
    conn = _get_conn()
    if done is None:
        rows = conn.execute(
            "SELECT id, text, trigger_time, done, lang, created_at FROM reminders ORDER BY trigger_time ASC"
        ).fetchall()
    elif done:
        rows = conn.execute(
            "SELECT id, text, trigger_time, done, lang, created_at FROM reminders WHERE done = 1 ORDER BY trigger_time ASC"
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT id, text, trigger_time, done, lang, created_at FROM reminders WHERE done = 0 ORDER BY trigger_time ASC"
        ).fetchall()

    out = []
    for row in rows:
        out.append(
            {
                "id": row[0],
                "text": row[1],
                "trigger_time": row[2],
                "done": bool(row[3]),
                "lang": row[4],
                "created_at": row[5],
            }
        )
    return out


def mark_reminder_done(reminder_id: int) -> bool:
    """Mark a reminder as done."""
    conn = _get_conn()
    cur = conn.execute("UPDATE reminders SET done = 1 WHERE id = ?", (reminder_id,))
    conn.commit()
    return cur.rowcount > 0


def delete_reminder(reminder_id: int) -> bool:
    """Delete a reminder by id."""
    conn = _get_conn()
    cur = conn.execute("DELETE FROM reminders WHERE id = ?", (reminder_id,))
    conn.commit()
    return cur.rowcount > 0


def clear_all_reminders() -> int:
    """Delete all reminders. Returns count deleted."""
    conn = _get_conn()
    cur = conn.execute("DELETE FROM reminders")
    conn.commit()
    return int(cur.rowcount or 0)


def check_pending_reminders() -> List[Dict[str, Any]]:
    """Check for reminders that should trigger now.

    Returns list of reminders whose trigger_time has passed and are not done.
    """
    conn = _get_conn()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    rows = conn.execute(
        "SELECT id, text, trigger_time, lang FROM reminders WHERE done = 0 AND trigger_time <= ?",
        (now_str,),
    ).fetchall()

    out = []
    for row in rows:
        out.append(
            {
                "id": row[0],
                "text": row[1],
                "trigger_time": row[2],
                "lang": row[3],
            }
        )
    return out


def send_reminder_notification(reminder_id: int, text: str, lang: str) -> None:
    """Speak the reminder and show it on screen.

    Called when the trigger time arrives.
    """
    from jaya.droid.audio import speak

    # Speak in the same language
    speak(text, lang)


__all__ = [
    "save_reminder",
    "get_reminders",
    "mark_reminder_done",
    "delete_reminder",
    "clear_all_reminders",
    "check_pending_reminders",
    "send_reminder_notification",
]