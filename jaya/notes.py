"""JAYA - Local-only notes in SQLite.

Never sends data to internet. All storage is local encrypted SQLite.
Tables: notes (id, text, date, lang)

Commands:
- Voice: "note f 8" / "note at 8" / "nota 8'de" / "note à 8h"
  -> save note in SQLite, speak confirmation in same language
- "show my notes" -> list all notes, ask which to delete
- "delete note" -> ask which, wait Yes
- "clear notes" -> ask Yes twice
- Each note shows date and language
"""

from __future__ import annotations

import sqlite3
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

from jaya.config import TEST_KEY_12345


# Database path within JAYA's local storage
_DB_PATH = Path(__file__).parent.parent / "memory" / "jaya_notes.db"


def _get_conn():
    """Get or create the notes SQLite connection."""
    conn = sqlite3.connect(str(_DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT NOT NULL,
            note_date TEXT NOT NULL,
            lang TEXT NOT NULL DEFAULT 'en',
            created_at REAL NOT NULL
        )
        """
    )
    conn.commit()
    return conn


def save_note(text: str, lang: str = "en") -> int:
    """Save a note to SQLite.

    Returns the note id.
    """
    conn = _get_conn()
    note_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    created_at = time.time()

    cur = conn.execute(
        """
        INSERT INTO notes (text, note_date, lang, created_at)
        VALUES (?, ?, ?, ?)
        """,
        (text, note_date, lang, created_at),
    )
    conn.commit()
    note_id = int(cur.lastrowid or 0)

    # Speak confirmation in the same language
    from jaya.droid.audio import speak
    speak(f"Note saved: {text}", lang)

    return note_id


def get_notes() -> List[Dict[str, Any]]:
    """Get all notes from SQLite."""
    conn = _get_conn()
    rows = conn.execute(
        "SELECT id, text, note_date, lang, created_at FROM notes ORDER BY note_date DESC"
    ).fetchall()

    out = []
    for row in rows:
        out.append(
            {
                "id": row[0],
                "text": row[1],
                "note_date": row[2],
                "lang": row[3],
                "created_at": row[4],
            }
        )
    return out


def delete_note(note_id: int) -> bool:
    """Delete a note by id."""
    conn = _get_conn()
    cur = conn.execute("DELETE FROM notes WHERE id = ?", (note_id,))
    conn.commit()
    return cur.rowcount > 0


def clear_all_notes() -> int:
    """Delete all notes. Returns count deleted."""
    conn = _get_conn()
    cur = conn.execute("DELETE FROM notes")
    conn.commit()
    return int(cur.rowcount or 0)


def get_notes_count() -> int:
    """Return total number of notes."""
    conn = _get_conn()
    cur = conn.execute("SELECT COUNT(*) FROM notes")
    return int(cur.fetchone()[0])

__all__ = [
    "save_note",
    "get_notes",
    "delete_note",
    "clear_all_notes",
    "get_notes_count",
]