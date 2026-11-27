"""JAYA - local encrypted SQLite memory."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import time
from pathlib import Path
from typing import Any, Iterable

try:  # optional, preferred backend
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
except Exception:  # pragma: no cover - Android fallback
    AESGCM = None

from jaya.config import TEST_KEY_12345

PBKDF2_ROUNDS = 200_000
MAGIC_AES = b"JAYA2"
MAGIC_FALLBACK = b"JAYA1"

# Reminders and notes table constants (kept in sync with reminders.py/notes.py)
REMINDERS_TABLE = "reminders"
NOTES_TABLE = "notes"


def _default_dir() -> Path:
    env = os.environ.get("JAYA_DATA_DIR")
    if env:
        return Path(env)
    try:
        from kivy.app import App

        app = App.get_running_app()
        if app is not None:
            return Path(app.user_data_dir)
    except Exception:
        pass
    return Path.home() / ".jaya"


class _Vault:
    """AES-GCM when available, HMAC-SHA256 keystream fallback otherwise."""

    def __init__(self, key_path: Path, passphrase: str):
        self.key_path = Path(key_path)
        self._enc, self._mac = self._load_or_create(passphrase)

    def _load_or_create(self, passphrase: str) -> tuple[bytes, bytes]:
        data: dict[str, Any] | None = None
        if self.key_path.exists():
            try:
                data = json.loads(self.key_path.read_text("utf-8"))
            except Exception:
                data = None
        if not data or "salt" not in data:
            data = {"v": 1, "salt": secrets.token_hex(16)}
            self.key_path.parent.mkdir(parents=True, exist_ok=True)
            self.key_path.write_text(json.dumps(data), "utf-8")
            try:
                os.chmod(self.key_path, 0o600)
            except OSError:
                pass

        salt = bytes.fromhex(data["salt"])
        master = hashlib.pbkdf2_hmac(
            "sha256", passphrase.encode("utf-8"), salt, PBKDF2_ROUNDS, 32
        )
        enc = hmac.new(master, b"jaya-enc", hashlib.sha256).digest()
        mac = hmac.new(master, b"jaya-mac", hashlib.sha256).digest()
        return enc, mac

    def encrypt(self, plain: bytes) -> bytes:
        if AESGCM is not None:
            nonce = secrets.token_bytes(12)
            return MAGIC_AES + nonce + AESGCM(self._enc).encrypt(nonce, plain, None)
        nonce = secrets.token_bytes(16)
        cipher = self._xor(plain, nonce)
        tag = hmac.new(self._mac, nonce + cipher, hashlib.sha256).digest()[:16]
        return MAGIC_FALLBACK + nonce + tag + cipher

    def decrypt(self, blob: bytes) -> bytes:
        if blob.startswith(MAGIC_AES):
            if AESGCM is None:
                raise RuntimeError("AES-GCM backend unavailable")
            nonce, payload = blob[5:17], blob[17:]
            return AESGCM(self._enc).decrypt(nonce, payload, None)
        if blob.startswith(MAGIC_FALLBACK):
            nonce, tag, cipher = blob[5:21], blob[21:37], blob[37:]
            expected = hmac.new(self._mac, nonce + cipher, hashlib.sha256).digest()[:16]
            if not hmac.compare_digest(tag, expected):
                raise ValueError("memory integrity check failed")
            return self._xor(cipher, nonce)
        raise ValueError("unknown memory format")

    def _xor(self, data: bytes, nonce: bytes) -> bytes:
        stream = bytearray()
        counter = 0
        while len(stream) < len(data):
            block = hashlib.sha256(
                self._enc + nonce + counter.to_bytes(8, "big")
            ).digest()
            stream.extend(block)
            counter += 1
        return bytes(a ^ b for a, b in zip(data, stream))


class JayaMemory:
    """Encrypted key/value store backed by a local SQLite file."""

    def __init__(
        self,
        db_path: str | Path | None = None,
        key_path: str | Path | None = None,
        passphrase: str | None = None,
    ):
        base = _default_dir()
        base.mkdir(parents=True, exist_ok=True)
        self.db_path = Path(db_path) if db_path else base / "jaya_memory.db"
        self.key_path = Path(key_path) if key_path else base / "jaya_memory.key"
        self._vault = _Vault(
            self.key_path,
            passphrase or os.environ.get("JAYA_PASSPHRASE") or TEST_KEY_12345,
        )
        try:
            self._db = sqlite3.connect(str(self.db_path))
        except Exception:
            self._db = sqlite3.connect(":memory:")
        self._db.execute("PRAGMA journal_mode=WAL")
        self._db.execute(
            """
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT NOT NULL UNIQUE,
                cipher BLOB NOT NULL,
                tags TEXT NOT NULL DEFAULT '',
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            )
            """
        )
        self._db.commit()

    def _dump(self, value: Any) -> bytes:
        return json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8")

    def _load(self, blob: bytes) -> Any:
        return json.loads(self._vault.decrypt(bytes(blob)).decode("utf-8"))

    def remember(self, key: str, value: Any, tags: Iterable[str] = ()) -> int:
        now = time.time()
        blob = self._vault.encrypt(self._dump(value))
        joined = ",".join(str(tag) for tag in tags)
        cur = self._db.execute(
            """
            INSERT INTO memories (key, cipher, tags, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET
                cipher = excluded.cipher,
                tags = excluded.tags,
                updated_at = excluded.updated_at
            """,
            (key, blob, joined, now, now),
        )
        self._db.commit()
        return int(cur.lastrowid or 0)

    def recall(self, key: str, default: Any = None) -> Any:
        row = self._db.execute(
            "SELECT cipher FROM memories WHERE key = ?", (key,)
        ).fetchone()
        return default if row is None else self._load(row[0])

    def has(self, key: str) -> bool:
        row = self._db.execute(
            "SELECT 1 FROM memories WHERE key = ?", (key,)
        ).fetchone()
        return row is not None

    def forget(self, key: str) -> bool:
        cur = self._db.execute("DELETE FROM memories WHERE key = ?", (key,))
        self._db.commit()
        return cur.rowcount > 0

    def entries(self, limit: int = 50) -> list[dict[str, Any]]:
        rows = self._db.execute(
            "SELECT key, cipher, tags, updated_at FROM memories "
            "ORDER BY updated_at DESC LIMIT ?",
            (int(limit),),
        ).fetchall()
        out = []
        for key, cipher, tags, updated in rows:
            out.append(
                {
                    "key": key,
                    "value": self._load(cipher),
                    "tags": [t for t in tags.split(",") if t],
                    "updated_at": updated,
                }
            )
        return out

    def search(self, query: str, limit: int = 20) -> list[dict[str, Any]]:
        needle = query.strip().lower()
        if not needle:
            return []
        hits = []
        for entry in self.entries(limit=10_000):
            haystack = " ".join(
                [entry["key"], " ".join(entry["tags"]), json.dumps(entry["value"], ensure_ascii=False)]
            ).lower()
            if needle in haystack:
                hits.append(entry)
                if len(hits) >= limit:
                    break
        return hits

    def count(self) -> int:
        return int(self._db.execute("SELECT COUNT(*) FROM memories").fetchone()[0])

    @staticmethod
    def _today_key() -> str:
        return "routine." + time.strftime("%Y-%m-%d")

    def save_routine(self, text: str) -> bool:
        """Append one routine entry for today, encrypted, local only."""
        text = (text or "").strip()
        if not text:
            return False
        key = self._today_key()
        items = self.recall(key, default=[])
        if not isinstance(items, list):
            items = []
        items.append({"text": text, "at": time.time()})
        self.remember(key, items, tags=("routine", "today"))
        return True

    def get_today(self) -> list[dict[str, Any]]:
        items = self.recall(self._today_key(), default=[])
        return items if isinstance(items, list) else []

    def save_chat(self, user: str, jaya: str, lang: str = "en") -> bool:
        """Store one local chat turn. Never leaves the device."""
        user = (user or "").strip()
        jaya = (jaya or "").strip()
        if not user and not jaya:
            return False
        key = f"chat.{time.time():.6f}.{secrets.token_hex(4)}"
        self.remember(
            key,
            {"user": user, "jaya": jaya, "lang": lang, "at": time.time()},
            tags=("chat", lang),
        )
        return True

    def get_history(self, limit: int = 5) -> list[dict[str, Any]]:
        rows = self._db.execute(
            "SELECT cipher FROM memories WHERE key LIKE 'chat.%' "
            "ORDER BY updated_at DESC LIMIT ?",
            (int(limit),),
        ).fetchall()
        history: list[dict[str, Any]] = []
        for (cipher,) in reversed(rows):
            try:
                history.append(self._load(cipher))
            except Exception:
                continue
        return history

    def count_chats(self) -> int:
        return int(
            self._db.execute(
                "SELECT COUNT(*) FROM memories WHERE key LIKE 'chat.%'"
            ).fetchone()[0]
        )

    def clear_history(self) -> int:
        """Wipe every stored memory entry: chats, routines, settings."""
        cur = self._db.execute("DELETE FROM memories")
        self._db.commit()
        return int(cur.rowcount or 0)

    def close(self) -> None:
        self._db.close()

    def __enter__(self) -> "JayaMemory":
        return self

    def __exit__(self, *_exc) -> None:
        self.close()


def save_reminder_to_memory(text: str, trigger_minutes: int, lang: str = "en") -> int:
    """Save a reminder using JayaMemory (deprecated - use reminders.py instead)."""
    from jaya.reminders import save_reminder as _save
    return _save(text, trigger_minutes, lang)


def get_reminders_from_memory(done: bool | None = None) -> List[Dict[str, Any]]:
    """Get reminders using JayaMemory (deprecated - use reminders.py instead)."""
    from jaya.reminders import get_reminders as _get
    return _get(done)


def mark_reminder_done_in_memory(reminder_id: int) -> bool:
    """Mark a reminder as done using JayaMemory (deprecated - use reminders.py instead)."""
    from jaya.reminders import mark_reminder_done as _mark
    return _mark(reminder_id)


def delete_reminder_in_memory(reminder_id: int) -> bool:
    """Delete a reminder using JayaMemory (deprecated - use reminders.py instead)."""
    from jaya.reminders import delete_reminder as _delete
    return _delete(reminder_id)


def clear_all_reminders_in_memory() -> int:
    """Delete all reminders using JayaMemory (deprecated - use reminders.py instead)."""
    from jaya.reminders import clear_all_reminders as _clear
    return _clear()


def save_note_to_memory(text: str, lang: str = "en") -> int:
    """Save a note using JayaMemory (deprecated - use notes.py instead)."""
    from jaya.notes import save_note as _save
    return _save(text, lang)


def get_notes_from_memory() -> List[Dict[str, Any]]:
    """Get all notes using JayaMemory (deprecated - use notes.py instead)."""
    from jaya.notes import get_notes as _get
    return _get()


def delete_note_in_memory(note_id: int) -> bool:
    """Delete a note using JayaMemory (deprecated - use notes.py instead)."""
    from jaya.notes import delete_note as _delete
    return _delete(note_id)


def clear_all_notes_in_memory() -> int:
    """Delete all notes using JayaMemory (deprecated - use notes.py instead)."""
    from jaya.notes import clear_all_notes as _clear
    return _clear()


def get_notes_count_from_memory() -> int:
    """Get notes count using JayaMemory (deprecated - use notes.py instead)."""
    from jaya.notes import get_notes_count as _count
    return _count()


__all__ = ["JayaMemory", "save_reminder_to_memory", "get_reminders_from_memory", "mark_reminder_done_in_memory",
           "delete_reminder_in_memory", "clear_all_reminders_in_memory", "save_note_to_memory", "get_notes_from_memory",
           "delete_note_in_memory", "clear_all_notes_in_memory", "get_notes_count_from_memory"]