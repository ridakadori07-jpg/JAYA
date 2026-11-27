"""JAYA - simple Darija intents: wifi, bluetooth, whatsapp."""

from __future__ import annotations

import re
import time
import unicodedata
from dataclasses import dataclass

WIFI_WORDS = ("واي فاي", "واي-فاي", "وايفاي", "ويفي", "wifi", "wi-fi")
BLUETOOTH_WORDS = ("بلوتوث", "بلوتوس", "bluetooth", "blutooth")
WHATSAPP_WORDS = ("واتساب", "واتس اب", "واتسآب", "whatsapp", "whats app")
OPEN_WORDS = ("فتح", "افتح", "حل", "شعل", "open", "launch")
TIME_WORDS = ("what time", "current time", "time is it", "الساعة", "وقت")
HELLO_WORDS = ("hello", "hi", "hey", "salam", "سلام")
ON_WORDS = ("turn on", "enable", "on", "شعل")
OFF_WORDS = ("turn off", "disable", "off", "طفي", "اطفي")

WHATSAPP_PACKAGE = "com.whatsapp"


@dataclass(frozen=True)
class IntentResult:
    ok: bool
    action: str
    message: str = ""


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text or "").lower()
    text = re.sub(r"[\u064b-\u065f\u0670\u0640]", "", text)
    text = re.sub(r"[أإآٱ]", "ا", text)
    text = text.replace("ى", "ي").replace("ة", "ه")
    return re.sub(r"\s+", " ", text).strip()


def _has_word(norm: str, word: str) -> bool:
    pattern = r"(?<!\w)" + re.escape(normalize(word)) + r"(?!\w)"
    return re.search(pattern, norm) is not None


def detect(text: str) -> str | None:
    norm = normalize(text)
    if not norm:
        return None
    if any(_has_word(norm, word) for word in HELLO_WORDS):
        return "hello"
    if any(normalize(word) in norm for word in TIME_WORDS):
        return "time"
    off = any(_has_word(norm, word) for word in OFF_WORDS)
    if any(normalize(word) in norm for word in WIFI_WORDS):
        return "wifi_off" if off else "wifi"
    if any(normalize(word) in norm for word in BLUETOOTH_WORDS):
        return "bluetooth_off" if off else "bluetooth"
    if any(normalize(word) in norm for word in WHATSAPP_WORDS):
        return "whatsapp"
    return None


def _android() -> bool:
    try:
        from kivy.utils import platform

        return platform == "android"
    except Exception:
        return False


def _activity():
    from jnius import autoclass

    return autoclass("org.kivy.android.PythonActivity").mActivity


def _launch(intent) -> None:
    from jnius import autoclass

    Intent = autoclass("android.content.Intent")
    intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
    _activity().startActivity(intent)


def open_wifi() -> IntentResult:
    if not _android():
        return IntentResult(False, "wifi", "Not available on desktop")
    try:
        from jnius import autoclass

        Intent = autoclass("android.content.Intent")
        Settings = autoclass("android.provider.Settings")
        _launch(Intent(Settings.ACTION_WIFI_SETTINGS))
        return IntentResult(True, "wifi", "WiFi settings opened")
    except Exception as exc:
        return IntentResult(False, "wifi", str(exc))


def open_bluetooth() -> IntentResult:
    if not _android():
        return IntentResult(False, "bluetooth", "Not available on desktop")
    try:
        from jnius import autoclass

        Intent = autoclass("android.content.Intent")
        Settings = autoclass("android.provider.Settings")
        _launch(Intent(Settings.ACTION_BLUETOOTH_SETTINGS))
        return IntentResult(True, "bluetooth", "Bluetooth settings opened")
    except Exception as exc:
        return IntentResult(False, "bluetooth", str(exc))


def open_whatsapp() -> IntentResult:
    if not _android():
        return IntentResult(False, "whatsapp", "Not available on desktop")
    try:
        from jnius import autoclass

        Intent = autoclass("android.content.Intent")
        Uri = autoclass("android.net.Uri")
        intent = _activity().getPackageManager().getLaunchIntentForPackage(
            WHATSAPP_PACKAGE
        )
        if intent is None:
            intent = Intent(
                Intent.ACTION_VIEW,
                Uri.parse("market://details?id=" + WHATSAPP_PACKAGE),
            )
        _launch(intent)
        return IntentResult(True, "whatsapp", "WhatsApp opened")
    except Exception as exc:
        return IntentResult(False, "whatsapp", str(exc))


def tell_time() -> IntentResult:
    return IntentResult(True, "time", time.strftime("%H:%M"))


def say_hello() -> IntentResult:
    return IntentResult(True, "hello", "Hello, I am JAYA")


ACTIONS = {
    "wifi": open_wifi,
    "wifi_off": open_wifi,
    "bluetooth": open_bluetooth,
    "bluetooth_off": open_bluetooth,
    "whatsapp": open_whatsapp,
    "time": tell_time,
    "hello": say_hello,
}


def execute(text: str) -> IntentResult:
    action = detect(text)
    if action is None:
        return IntentResult(False, "unknown", "Unknown command")
    return ACTIONS[action]()


__all__ = [
    "IntentResult",
    "detect",
    "execute",
    "open_bluetooth",
    "open_wifi",
    "open_whatsapp",
    "say_hello",
    "tell_time",
]
