"""JAYA - Android TTS and microphone capture."""

from __future__ import annotations

import math
import threading
import time
from array import array
from pathlib import Path

SAMPLE_RATE = 8000
CHUNK_MS = 40
SPEECH_RMS = 1200
POLL_S = 0.18


def is_android() -> bool:
    try:
        from kivy.utils import platform
        return platform == "android"
    except Exception:
        return False


class LightMic:
    """Energy-gated mic. Records only small PCM chunks in RAM."""

    def __init__(self, sample_rate: int = SAMPLE_RATE, chunk_ms: int = CHUNK_MS):
        self.sample_rate = int(sample_rate)
        self.chunk_ms = int(chunk_ms)
        self.chunk_bytes = int(self.sample_rate * self.chunk_ms / 1000) * 2
        self.available = False
        self._rec = None
        self._lock = threading.Lock()
        if is_android():
            self._open()

    def _open(self) -> None:
        try:
            from jnius import autoclass
            AudioRecord = autoclass("android.media.AudioRecord")
            AudioFormat = autoclass("android.media.AudioFormat")
            Source = autoclass("android.media.MediaRecorder$AudioSource")
            min_buf = AudioRecord.getMinBufferSize(
                self.sample_rate,
                AudioFormat.CHANNEL_IN_MONO,
                AudioFormat.ENCODING_PCM_16BIT,
            )
            buf_size = max(int(min_buf), self.chunk_bytes * 4)
            rec = AudioRecord(
                Source.MIC,
                self.sample_rate,
                AudioFormat.CHANNEL_IN_MONO,
                AudioFormat.ENCODING_PCM_16BIT,
                buf_size,
            )
            if rec.getState() != AudioRecord.STATE_INITIALIZED:
                rec.release()
                return
            rec.startRecording()
            self._rec = rec
            self.available = True
        except Exception:
            self._rec = None
            self.available = False

    def pause(self) -> None:
        with self._lock:
            if self._rec is None:
                return
            try:
                self._rec.stop()
            except Exception:
                pass
            try:
                self._rec.release()
            except Exception:
                pass
            self._rec = None
            self.available = False

    def resume(self) -> bool:
        if self.available:
            return True
        self._open()
        return self.available

    def read_rms(self) -> float:
        with self._lock:
            if not self.available or self._rec is None:
                return 0.0
            buf = bytearray(self.chunk_bytes)
            try:
                read = int(self._rec.read(buf, 0, len(buf)))
            except Exception:
                return 0.0
            if read < 2:
                return 0.0
            read -= read % 2
            pcm = array("h")
            pcm.frombytes(bytes(buf[:read]))
            if not pcm:
                return 0.0
            total = 0
            for sample in pcm:
                total += sample * sample
            return math.sqrt(total / len(pcm))

    def wait_for_speech(
        self,
        stop_event: threading.Event,
        timeout: float | None = None,
        threshold: int = SPEECH_RMS,
        poll: float = POLL_S,
    ) -> bool:
        deadline = None if timeout is None else time.monotonic() + timeout
        while not stop_event.is_set():
            if deadline is not None and time.monotonic() >= deadline:
                return False
            if self.read_rms() >= threshold:
                return True
            stop_event.wait(poll)
        return False

    def record_wav(
        self,
        path: str | Path,
        max_seconds: float = 6.0,
        stop_event: threading.Event | None = None,
        threshold: int = SPEECH_RMS,
        silence_s: float = 0.8,
    ) -> Path | None:
        if not self.available:
            return None
        stop_event = stop_event or threading.Event()
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        started = time.monotonic()
        silent_for = 0.0
        spoke = False
        with wave.open(str(out), "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(self.sample_rate)
            while not stop_event.is_set():
                if time.monotonic() - started >= max_seconds:
                    break
                with self._lock:
                    if self._rec is None:
                        break
                    buf = bytearray(self.chunk_bytes)
                    try:
                        read = int(self._rec.read(buf, 0, len(buf)))
                    except Exception:
                        break
                if read < 2:
                    time.sleep(0.02)
                    continue
                read -= read % 2
                pcm = bytes(buf[:read])
                wav.writeframes(pcm)
                level = math.sqrt(
                    sum(s * s for s in array("h", pcm)) / max(1, read // 2)
                )
                if level >= threshold:
                    spoke = True
                    silent_for = 0.0
                elif spoke:
                    silent_for += read / (2.0 * self.sample_rate)
                    if silent_for >= silence_s:
                        break
        return out if out.exists() and out.stat().st_size > 44 else None

    def close(self) -> None:
        self.pause()


def speak(text: str, lang: str = "en") -> None:
    """Speak text with Android TTS. Falls back to print on desktop."""
    text = (text or "").strip()
    if not text:
        return
    if is_android():
        try:
            from jnius import autoclass, PythonJavaClass, java_method
            from android.runnable import run_on_ui_thread
        except Exception:
            return

        TextToSpeech = autoclass("android.speech.tts.TextToSpeech")
        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        Locale = autoclass("java.util.Locale")
        locale = _LOCALES.get(lang, "en-US")

        class _Init(PythonJavaClass):
            __javainterfaces__ = ["android/speech/tts/TextToSpeech$OnInitListener"]
            __javacontext__ = "app"

            @java_method("(I)V")
            def onInit(self, status):
                pass

        @run_on_ui_thread
        def _run():
            try:
                tts = _TTS_STATE.get("tts")
                if tts is None:
                    tts = TextToSpeech(PythonActivity.mActivity, _Init())
                    _TTS_STATE["tts"] = tts
                tts.setLanguage(Locale(locale))
                tts.speak(text, TextToSpeech.QUEUE_FLUSH, None, "jaya")
            except Exception:
                pass

        _run()
    else:
        # Desktop fallback: print what would be spoken
        print(f"[TTS] Would speak ({lang}): {text}")


_LOCALES = {"ar": "ar-MA", "fr": "fr-FR", "tr": "tr-TR", "en": "en-US"}