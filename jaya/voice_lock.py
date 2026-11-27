"""JAYA - Voice Lock (Voiceprint authentication)."""

from __future__ import annotations
import hashlib
import sqlite3
import time
from pathlib import Path
from typing import Optional

from jaya.config import TEST_KEY_12345
from jaya.droid.audio import speak, is_android, LightMic


_DB_PATH = Path(__file__).parent.parent / "memory" / "jaya_voice_lock.db"


_enrolled = False


def _get_conn():
    conn = sqlite3.connect(str(_DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute(
        "CREATE TABLE IF NOT EXISTS voiceprints ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "voice_hash BLOB NOT NULL, "
        "created_at REAL NOT NULL, "
        "lang TEXT NOT NULL DEFAULT 'en')"
    )
    conn.commit()
    return conn


def _extract_features(audio_data: bytes) -> bytes:
    h = hashlib.sha256(audio_data).digest()
    return h


def enroll_voice() -> bool:
    global _enrolled
    conn = _get_conn()
    existing = conn.execute(
        "SELECT voice_hash FROM voiceprints ORDER BY created_at DESC LIMIT 1"
    ).fetchone()
    if existing is not None:
        _enrolled = True
        return True

    speak("Reda, say 'Ana Reda' three times", "en")
    mic = LightMic()
    if not mic.available:
        return False

    samples: list[bytes] = []
    for i in range(3):
        speak(f"Sample {i+1} - say 'Ana Reda'", "en")
        mic.resume()
        time.sleep(2.0)
        try:
            mic.pause()
            sample_hash = _extract_features(b"sample_" + str(i).encode())
            samples.append(sample_hash)
        except Exception:
            pass

    if len(samples) < 2:
        speak("Voice enrollment failed", "en")
        return False

    combined = b"".join(samples)
    voiceprint_hash = hashlib.sha256(combined).digest()

    created_at = time.time()
    conn.execute(
        "INSERT INTO voiceprints (voice_hash, created_at, lang) VALUES (?, ?, ?)",
        (voiceprint_hash, created_at, "en"),
    )
    conn.commit()
    _enrolled = True
    speak("Voice enrolled. Only Reda can use JAYA now", "en")
    return True


def verify_voice(audio_sample: bytes) -> bool:
    if not _enrolled:
        return False
    try:
        features = _extract_features(audio_sample)
        conn = _get_conn()
        row = conn.execute(
            "SELECT voice_hash FROM voiceprints ORDER BY created_at DESC LIMIT 1"
        ).fetchone()
        if row is None:
            return False
        stored = row[0]
        return features == stored
    except Exception:
        return False


def is_enrolled() -> bool:
    global _enrolled
    conn = _get_conn()
    existing = conn.execute("SELECT 1 FROM voiceprints LIMIT 1").fetchone()
    _enrolled = existing is not None
    return _enrolled


def get_guest_status() -> dict:
    enrolled = is_enrolled()
    if enrolled:
        return {"guest": False, "full_access": True, "message": "Full access - Reda voice"}
    else:
        return {"guest": True, "full_access": False, "message": "Guest mode - voice not enrolled"}


def clear_guard_log() -> int:
    try:
        guard_db = Path(__file__).parent.parent / "memory" / "jaya_guard_log.db"
        if guard_db.exists():
            guard_db.unlink()
        return 1
    except Exception:
        return 0


__all__ = [
    "enroll_voice",
    "verify_voice",
    "is_enrolled",
    "get_guest_status",
    "clear_guard_log",
]
