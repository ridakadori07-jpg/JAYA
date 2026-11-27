"""JAYA - wake word "jaya": hears the mic, answers "Naam Reda, ana hna"."""

from __future__ import annotations

import threading
import time
from collections.abc import Callable

from jaya.droid.audio import LightMic, speak

WAKE_WORDS = ("jaya",)
REPLY = "Naam Reda, ana hna"
COOLDOWN_S = 1.2
LISTEN_TIMEOUT_S = 10.0


def normalize(text: str) -> str:
    """Normalize text for wake word matching: NFKC, lower, strip diacritics."""
    import unicodedata
    import re

    text = unicodedata.normalize("NFKC", text or "").lower()
    text = re.sub(r"[ً-ٰٟـ]", "", text)
    text = re.sub(r"[أإآٱ]", "ا", text)
    text = text.replace("ى", "ي").replace("ة", "ه")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def contains_wake(text: str) -> bool:
    """Check if normalized text contains any wake word."""
    norm = normalize(text)
    return bool(norm) and any(normalize(word) in norm for word in WAKE_WORDS)


def listen_for_response(timeout: float = LISTEN_TIMEOUT_S) -> str:
    """Listen for user response after wake word, with timeout."""
    from jaya.droid.audio import listen

    text = listen(timeout=timeout) or ""
    return text


class WakeWordListener:
    """Wake word loop.

    On wake: speak "Naam Reda, ana hna" + listen 10s for response + answer + back to wake.
    After 10s silence, back to sleep.
    """

    def __init__(
        self,
        on_wake: Callable[[str], None] | None = None,
        language: str = "en-MA",
        cooldown: float = COOLDOWN_S,
        mic: LightMic | None = None,
    ):
        self.on_wake = on_wake
        self.language = language
        self.cooldown = cooldown
        self._mic = mic or LightMic()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> bool:
        if self.running:
            return True
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._loop, name="jaya-wake", daemon=True
        )
        self._thread.start()
        return True

    def stop(self, timeout: float = 2.0) -> None:
        self._stop.set()
        thread = self._thread
        if thread is not None:
            thread.join(timeout=timeout)
        self._thread = None
        self._mic.close()
        self._mic = None

    def _loop(self) -> None:
        mic = self._mic
        if not mic.available:
            return
        while not self._stop.is_set():
            # Energy-gated listen for wake word
            if not mic.wait_for_speech(self._stop, timeout=LISTEN_TIMEOUT_S):
                continue

            # Wake detected: speak reply
            speak("Naam Reda, ana hna")

            # Listen for 10s for user response
            heard_text = listen_for_response(self.language)

            # Process the heard text
            if self.on_wake is not None:
                try:
                    self.on_wake(heard_text)
                except Exception:
                    pass

            # Cooldown before next listen
            self._stop.wait(self.cooldown)