"""JAYA - local-first brain. Nothing leaves the device unless the user picks a provider."""

from __future__ import annotations

import re

from jaya.config import TEST_KEY_12345
from jaya.memory import JayaMemory

PRIVACY_MODE = True

LOCAL_PROVIDER = "Local only"
PROVIDERS = (
    "Local only",
    "Auto",
    "Groq",
    "Gemini",
    "Grok",
    "OpenRouter",
    "NVIDIA",
    "Z.ai",
)

PROVIDER_SLUGS = {
    "Groq": "groq",
    "Gemini": "gemini",
    "Grok": "grok",
    "OpenRouter": "openrouter",
    "NVIDIA": "nvidia",
    "Z.ai": "zai",
}

SYSTEM_PROMPTS = {
    "ar": "You are JAYA, a private local assistant. Reply briefly in Moroccan Darija.",
    "en": "You are JAYA, a private local assistant. Reply briefly in English.",
    "fr": "You are JAYA, a private local assistant. Reply briefly in French.",
    "tr": "You are JAYA, a private local assistant. Reply briefly in Turkish.",
}

_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
_PHONE_RE = re.compile(r"\+?\d[\d\s().-]{6,}\d")
_URL_RE = re.compile(r"https?://\S+")


def detect_language(text: str) -> str:
    raw = text or ""
    low = raw.lower()
    if not low.strip():
        return "en"
    if re.search(r"[\u0600-\u06ff]", raw):
        return "ar"
    if re.search(r"[çğıöşü]", low) or any(
        word in low for word in ("merhaba", "nasilsin", "saat", "aç", "kapat")
    ):
        return "tr"
    if re.search(r"[àâçéèêëîïôùûüœ]", low) or any(
        word in low
        for word in ("bonjour", "salut", "merci", "heure", "ouvre", "ferme")
    ):
        return "fr"
    return "en"


def sanitize(text: str) -> str:
    """Strip obvious personal data before any optional network call."""
    clean = _URL_RE.sub("[url]", text or "")
    clean = _EMAIL_RE.sub("[email]", clean)
    clean = _PHONE_RE.sub("[number]", clean)
    return re.sub(r"\s+", " ", clean).strip()[:500]


def resolve_provider(provider: str, keys: dict[str, str] | None = None) -> str:
    provider = provider if provider in PROVIDERS else LOCAL_PROVIDER
    keys = keys or {}
    if provider != "Auto":
        return provider
    # Auto mode: only use external if key is present AND not the test key
    for name, slug in PROVIDER_SLUGS.items():
        value = keys.get(slug, "")
        # Skip if key is empty, test key, or placeholder
        if not value or value == TEST_KEY_12345 or value.startswith("test") or value.startswith("fake"):
            continue
        # Only use if key looks real (long enough, has letters+numbers)
        if len(value) < 10:
            continue
        return name
    return LOCAL_PROVIDER


def privacy_label(resolved: str) -> str:
    if resolved == LOCAL_PROVIDER:
        return "Privacy: Local only"
    return f"Privacy: Sending only question to {resolved}"


def _local_reply(text: str) -> tuple[bool, str]:
    low = (text or "").strip().lower()
    if any(word in low for word in ("what did i do", "my routine", "today")):
        try:
            from jaya.memory import JayaMemory
            with JayaMemory() as memory:
                items = memory.get_today()
            return True, f"You saved {len(items)} routine entries today."
        except Exception:
            return True, "Memory is unavailable."
    # Greetings
    if any(word in low for word in ("hello", "hi", "hey", "salam", "سلام")):
        return True, "Hello! I am JAYA, your local assistant."
    # Time
    if any(word in low for word in ("what time", "current time", "time is it", "sاعة", "وقت")):
        from jaya.intents import tell_time
        result = tell_time()
        return True, result.message or time.strftime("%H:%M")
    # App opening commands
    if any(word in low for word in ("open", "launch", "شعل", "افتح")):
        from jaya.intents import execute
        from jaya.droid.apps import find_app, open_app

        result = execute(text)
        if result.action != "unknown":
            return True, result.message or "Opening app..."

        # Try to find and open app
        app = find_app(text)
        if app:
            if open_app(app):
                return True, f"Opening {app.name}"
            return True, f"Could not open {app.name}"
        return True, "Unknown app. Try: YouTube, WhatsApp, Facebook, Instagram, TikTok, X, Camera, Settings, Browser"
    # System commands
    if any(word in low for word in ("wifi", "bluetooth", "flash", "time", "date", "call")):
        return True, "System command detected. Ask me to specify."
    # Default local reply
    return True, "I understand. I'm running locally."


def ask_ai(question: str, provider: str, keys: dict[str, str]) -> str:
    slug = PROVIDER_SLUGS.get(provider)
    if not slug:
        return ""
    key = (keys or {}).get(slug, "")
    if not key or key == TEST_KEY_12345:
        return ""
    try:
        import requests
    except Exception:
        return ""

    question = sanitize(question)
    if not question:
        return ""
    system = SYSTEM_PROMPTS[detect_language(question)]

    try:
        if slug == "gemini":
            response = requests.post(
                "https://generativelanguage.googleapis.com/v1beta/models/"
                "gemini-1.5-flash:generateContent",
                params={"key": key},
                json={
                    "contents": [
                        {"parts": [{"text": system + "\n\n" + question}]}
                    ]
                },
                timeout=20,
            )
            data = response.json()
            return str(
                data["candidates"][0]["content"]["parts"][0]["text"]
            ).strip()

        endpoints = {
            "groq": (
                "https://api.groq.com/openai/v1/chat/completions",
                "llama-3.1-8b-instant",
            ),
            "grok": ("https://api.x.ai/v1/chat/completions", "grok-2-latest"),
            "openrouter": (
                "https://openrouter.ai/api/v1/chat/completions",
                "openai/gpt-4o-mini",
            ),
            "nvidia": (
                "https://integrate.api.nvidia.com/v1/chat/completions",
                "meta/llama-3.1-8b-instruct",
            ),
            "zai": (
                "https://api.z.ai/api/paas/v4/chat/completions",
                "glm-4-flash",
            ),
        }
        url, model = endpoints[slug]
        response = requests.post(
            url,
            headers={"Authorization": f"Bearer {key}"},
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": question},
                ],
                "max_tokens": 300,
            },
            timeout=20,
        )
        data = response.json()
        return str(data["choices"][0]["message"]["content"]).strip()
    except Exception:
        return ""


def handle(text: str, provider: str = LOCAL_PROVIDER, keys: dict[str, str] | None = None) -> dict:
    text = (text or "").strip()
    keys = keys or {}
    lang = detect_language(text)
    if not text:
        return {"reply": "", "lang": lang, "used": "local", "local": True}

    handled, reply = _local_reply(text)
    if handled:
        return {"reply": reply, "lang": lang, "used": "local", "local": True}

    resolved = resolve_provider(provider, keys)
    if resolved == LOCAL_PROVIDER:
        return {
            "reply": "Local only. I can handle WiFi, Bluetooth, WhatsApp, time and memory.",
            "lang": lang,
            "used": "local",
            "local": True,
        }

    answer = ask_ai(text, resolved, keys)
    return {
        "reply": answer or "No answer from the provider.",
        "lang": lang,
        "used": resolved,
        "local": False,
    }


def clear_history() -> int:
    with JayaMemory() as memory:
        return memory.clear_history()


__all__ = [
    "PRIVACY_MODE",
    "PROVIDERS",
    "PROVIDER_SLUGS",
    "SYSTEM_PROMPTS",
    "ask_ai",
    "clear_history",
    "detect_language",
    "handle",
    "privacy_label",
    "resolve_provider",
    "sanitize",
]
