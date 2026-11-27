"""JAYA - local configuration: keys encrypted on the device only."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import secrets
from pathlib import Path

TEST_KEY_12345 = "TEST_KEY_12345"

_KEYS_FILE = "jaya_keys.json"
_SECRET_FILE = "jaya_local.secret"


def _private_dir() -> Path:
    env = os.environ.get("JAYA_DATA_DIR")
    if env:
        base = Path(env)
    else:
        base = None
        try:
            from kivy.app import App

            app = App.get_running_app()
            if app is not None:
                base = Path(app.user_data_dir)
        except Exception:
            base = None
        if base is None:
            base = Path.home() / ".jaya"
    base.mkdir(parents=True, exist_ok=True)
    return base


def _secret() -> str:
    path = _private_dir() / _SECRET_FILE
    if path.exists():
        try:
            value = path.read_text("utf-8").strip()
            if value:
                return value
        except Exception:
            pass
    value = secrets.token_hex(32)
    try:
        path.write_text(value, "utf-8")
        os.chmod(path, 0o600)
    except Exception:
        pass
    return value


def _xor(data: bytes, key: str) -> bytes:
    stream = bytearray()
    counter = 0
    raw = key.encode("utf-8")
    while len(stream) < len(data):
        stream.extend(hashlib.sha256(raw + counter.to_bytes(8, "big")).digest())
        counter += 1
    return bytes(a ^ b for a, b in zip(data, stream))


def mask_key(value: str) -> str:
    return "****" if value else ""


def save_keys(keys: dict[str, str]) -> bool:
    clean = {k: str(v).strip() for k, v in (keys or {}).items() if str(v).strip()}
    try:
        nonce = secrets.token_hex(8)
        payload = json.dumps(clean, ensure_ascii=False, sort_keys=True).encode("utf-8")
        blob = _xor(payload, _secret() + nonce)
        path = _private_dir() / _KEYS_FILE
        path.write_text(
            json.dumps(
                {
                    "v": 1,
                    "nonce": nonce,
                    "data": base64.b64encode(blob).decode("ascii"),
                }
            ),
            "utf-8",
        )
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass
        return True
    except Exception:
        return False


def load_keys() -> dict[str, str]:
    try:
        path = _private_dir() / _KEYS_FILE
        if not path.exists():
            return {}
        data = json.loads(path.read_text("utf-8"))
        blob = base64.b64decode(data["data"])
        plain = _xor(blob, _secret() + str(data.get("nonce", "")))
        values = json.loads(plain.decode("utf-8"))
        return {str(k): str(v) for k, v in values.items() if v}
    except Exception:
        return {}


def delete_keys() -> bool:
    try:
        path = _private_dir() / _KEYS_FILE
        if path.exists():
            path.unlink()
        return True
    except Exception:
        return False


__all__ = ["TEST_KEY_12345", "delete_keys", "load_keys", "mask_key", "save_keys"]
