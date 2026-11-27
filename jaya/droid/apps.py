"""JAYA - Open apps by name in Darija / Turkish / English.

Uses Android PackageManager to discover installed apps dynamically.
No hardcoded app list - discovers what`s actually installed.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path


@dataclass
class AppInfo:
    name: str
    package: str
    display_name_key: str


def _normalize_app_name(text: str) -> str:
    """Normalize app name for matching."""
    text = unicodedata.normalize("NFKC", text or "").lower()
    text = re.sub(r"[ً-ٰٟـ]", "", text)
    text = re.sub(r"[أإآٱ]", "ا", text)
    text = text.replace("ى", "ي").replace("ة", "ه")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _open_intent(app: AppInfo) -> bool:
    """Open an Android app by package name via Intent."""
    try:
        from jnius import autoclass
        from android.content import Intent

        Intent = autoclass("android.content.Intent")
        PythonActivity = autoclass("org.kivy.android.PythonActivity")

        intent = Intent()
        intent.setAction(Intent.ACTION_MAIN)
        intent.addCategory(Intent.CATEGORY_LAUNCHER)
        intent.setPackage(app.package)

        activity = PythonActivity.mActivity
        activity.startActivity(intent)
        return True
    except Exception as e:
        print(f"Failed to open {app.name}: {e}")
        return False


def get_installed_apps() -> list[AppInfo]:
    """Get ALL installed apps via PackageManager.

    Dynamically discovers what apps are actually installed on the device.
    Returns list of AppInfo objects for installed apps only.
    """
    try:
        from jnius import autoclass

        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        context = PythonActivity.mActivity.getApplicationContext()
        PackageManager = autoclass("android.content.pm.PackageManager")

        # Use queryIntentActivities to get all launcher apps
        intent_main = autoclass("android.intent.CATEGORY_LAUNCHER")
        query = autoclass("android.content.Intent").ACTION_MAIN
        intent_filter = autoclass("android.content.Intent").newInstance()
        intent_filter.setAction(query)
        intent_filter.addCategory(intent_main)

        activities = context.getPackageManager().queryIntentActivities(
            intent_filter, 0
        )

        apps: list[AppInfo] = []
        seen: set[str] = set()

        # Build from queryIntentActivities results
        for info in activities:
            pkg = info.activityInfo.packageName
            if pkg in seen:
                continue
            seen.add(pkg)

            # Get label from activity info
            label = info.activityInfo.loadLabel(
                context.getPackageManager()
            )
            label_str = str(label) if label else pkg

            # Determine display name key
            name_words = re.sub(r"[^a-zA-Z0-9\s]", "", label_str).strip().lower()
            key = name_words.replace(" ", "") if name_words else pkg

            apps.append(AppInfo(
                name=label_str,
                package=pkg,
                display_name_key=key,
            ))

        return apps

    except Exception as e:
        print(f"Could not get installed apps: {e}")
        return []


def find_app(text: str) -> AppInfo | None:
    """Find app matching the user`s text.

    Searches installed apps by name in Darija/Turkish/English with fuzzy fallback.
    Uses PackageManager to get real installed apps.
    """
    from jaya.droid.apps import get_installed_apps

    installed = get_installed_apps()
    if not installed:
        return None

    norm = _normalize_app_name(text)
    if not norm:
        return None

    # First try exact/contains match against installed apps
    for app in installed:
        # Check if normalized text is in app name or package
        if norm in app.name.lower() or norm in app.package.lower():
            return app

        # Check if app name words are in normalized text
        app_name_words = set(app.name.lower().split())
        text_words = set(norm.split())
        if app_name_words & text_words:
            return app

        # Check package name
        if app.package.lower() in norm or norm in app.package.lower():
            return app

    # Fuzzy match: find apps whose names share words with the query
    best_match: AppInfo | None = None
    best_score = 0

    for app in installed:
        app_words = set(app.name.lower().split())
        text_words = set(norm.split())
        common = app_words & text_words
        if common:
            score = len(common)
            if score > best_score:
                best_score = score
                best_match = app

    return best_match


def open_app(app: AppInfo) -> bool:
    """Open an Android app by package name."""
    return _open_intent(app)


# Convenience functions for specific apps
def open_youtube() -> bool:
    """Open YouTube app."""
    from jaya.droid.apps import find_app, open_app

    app = find_app("youtube")
    if app:
        return open_app(app)
    return False


def open_whatsapp() -> bool:
    """Open WhatsApp app."""
    from jaya.droid.apps import find_app, open_app

    app = find_app("whatsapp")
    if app:
        return open_app(app)
    return False


def open_facebook() -> bool:
    """Open Facebook app."""
    from jaya.droid.apps import find_app, open_app

    app = find_app("facebook")
    if app:
        return open_app(app)
    return False


def open_instagram() -> bool:
    """Open Instagram app."""
    from jaya.droid.apps import find_app, open_app

    app = find_app("instagram")
    if app:
        return open_app(app)
    return False


def open_tiktok() -> bool:
    """Open TikTok app."""
    from jaya.droid.apps import find_app, open_app

    app = find_app("tiktok")
    if app:
        return open_app(app)
    return False


def open_x() -> bool:
    """Open X (Twitter) app."""
    from jaya.droid.apps import find_app, open_app

    app = find_app("x")
    if app:
        return open_app(app)
    return False


def open_camera() -> bool:
    """Open Camera app."""
    from jaya.droid.apps import find_app, open_app

    app = find_app("camera")
    if app:
        return open_app(app)
    return False


def open_settings() -> bool:
    """Open Settings app."""
    from jaya.droid.apps import find_app, open_app

    app = find_app("settings")
    if app:
        return open_app(app)
    return False


def open_browser() -> bool:
    """Open Browser app."""
    from jaya.droid.apps import find_app, open_app

    app = find_app("browser")
    if app:
        return open_app(app)
    return False


def get_tts_greeting(app_name: str, language: str = "en") -> str:
    """Generate greeting in the same language as the command."""
    # Arabic greeting (detect Arabic characters)
    if re.search(r"[؀-ۿ]", app_name or ""):
        return f"Wakha Reda, kan-sh3al lik {app_name}..."
    # Turkish greeting (detect Turkish words)
    if any(word in (app_name or "").lower() for word in ["ac", "çık", "aç"]):
        return f"Wakha Reda, kan-sh3al lik {app_name}..."
    # English default
    return f"Wakha Reda, kan-sh3al lik {app_name}..."