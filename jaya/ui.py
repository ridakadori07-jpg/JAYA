"""JAYA - KivyMD UI: navy background with a glowing pink sphere."""

from __future__ import annotations

import threading

from kivy.animation import Animation
from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, Ellipse
from kivy.lang import Builder
from kivy.metrics import dp
from kivy.properties import BooleanProperty, NumericProperty, StringProperty
from kivy.uix.button import Button
from kivy.uix.widget import Widget
from kivy.utils import platform
from kivymd.app import MDApp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDIconButton
from kivymd.uix.label import MDLabel
from kivymd.uix.screen import MDScreen
from kivymd.uix.screenmanager import MDScreenManager
from kivymd.uix.textfield import MDTextField

from jaya import config
from jaya.brain import LOCAL_PROVIDER, PROVIDERS, privacy_label, resolve_provider
from jaya.config import load_keys
from jaya.memory import JayaMemory
from jaya.guard import is_guard_enabled, set_guard_enabled
from jaya.notes import get_notes, clear_all_notes, get_notes_count
from jaya.reminders import get_reminders, clear_all_reminders
from jaya.voice_lock import is_enrolled, get_guest_status

FONT = "Roboto"

NAVY = (0.024, 0.043, 0.102, 1.0)  # #060B1A
PINK = (1.0, 0.28, 0.58)
IDLE_TEXT = "Hello, I am JAYA"
LISTEN_TEXT = "Listening..."

PROVIDER_SLOTS = (
    ("groq", "Groq"),
    ("gemini", "Gemini"),
    ("grok", "Grok"),
    ("openrouter", "OpenRouter"),
    ("nvidia", "NVIDIA"),
    ("zai", "Z.ai"),
)

KV = """
<JayaHomeScreen>:
    md_bg_color: 0.024, 0.043, 0.102, 1

    MDBoxLayout:
        orientation: "vertical"
        padding: dp(20), dp(16), dp(20), dp(26)

        MDBoxLayout:
            size_hint_y: None
            height: dp(48)

            MDLabel:
                text: "JAYA"
                font_name: app.font_name
                font_size: "18sp"
                bold: True
                theme_text_color: "Custom"
                text_color: 0.85, 0.88, 0.96, 0.9

            MDIconButton:
                icon: "cog-outline"
                font_name: app.font_name
                theme_icon_color: "Custom"
                icon_color: 0.85, 0.88, 0.96, 0.85
                on_release: app.open_settings_screen()

        AnchorLayout:
            anchor_x: "center"
            anchor_y: "center"
            size_hint_y: 0.52

            GlowingOrb:
                id: orb
                size_hint: None, None
                size: dp(220), dp(220)
                on_touch_down:
                    if self.collide_point(*args[1].pos): app.on_orb_tapped()

        MDLabel:
            text: app.say_text
            font_name: app.font_name
            halign: "center"
            size_hint_y: None
            height: dp(22)
            theme_text_color: "Custom"
            text_color: 0.72, 0.78, 0.90, 1

        MDLabel:
            text: app.provider_text
            font_name: app.font_name
            halign: "center"
            size_hint_y: None
            height: dp(22)
            theme_text_color: "Custom"
            text_color: 0.72, 0.78, 0.90, 1

        MDLabel:
            text: app.brain_text
            font_name: app.font_name
            halign: "center"
            size_hint_y: None
            height: dp(22)
            theme_text_color: "Custom"
            text_color: 0.72, 0.78, 0.90, 1

        MDLabel:
            text: app.privacy_text
            font_name: app.font_name
            halign: "center"
            size_hint_y: None
            height: dp(22)
            theme_text_color: "Custom"
            text_color: 0.72, 0.78, 0.90, 1

        MDLabel:
            text: app.memory_text
            font_name: app.font_name
            halign: "center"
            size_hint_y: None
            height: dp(22)
            theme_text_color: "Custom"
            text_color: 0.72, 0.78, 0.90, 1

        MDLabel:
            text: app.reminder_text
            font_name: app.font_name
            halign: "center"
            size_hint_y: None
            height: dp(22)
            theme_text_color: "Custom"
            text_color: 0.72, 0.78, 0.90, 1

        MDLabel:
            text: app.note_text
            font_name: app.font_name
            halign: "center"
            size_hint_y: None
            height: dp(22)
            theme_text_color: "Custom"
            text_color: 0.72, 0.78, 0.90, 1

        MDLabel:
            text: app.status_text
            font_name: app.font_name
            halign: "center"
            size_hint_y: None
            height: dp(44)
            theme_text_color: "Custom"
            text_color: 0.88, 0.90, 0.98, 0.88


<JayaSettingsScreen>:
    md_bg_color: 0.024, 0.043, 0.102, 1

    MDBoxLayout:
        orientation: "vertical"
        padding: dp(20), dp(16)
        spacing: dp(12)

        MDBoxLayout:
            size_hint_y: None
            height: dp(48)

            MDIconButton:
                icon: "arrow-left"
                font_name: app.font_name
                theme_icon_color: "Custom"
                icon_color: 0.9, 0.92, 0.98, 1
                on_release: app.open_home_screen()

            MDLabel:
                text: "Settings"
                font_name: app.font_name
                font_size: "20sp"
                bold: True
                theme_text_color: "Custom"
                text_color: 0.92, 0.94, 0.99, 1

        MDLabel:
            text: "Test mode enabled locally"
            font_name: app.font_name
            halign: "center"
            theme_text_color: "Custom"
            text_color: 0.72, 0.78, 0.90, 1

        # Guest mode status bar
        MDCard:
            size_hint_y: None
            height: dp(40)
            padding: dp(8)
            elevation: 2
            md_bg_color: 0.8, 0.1, 0.2, 0.2
            radius: [8]
            MDLabel:
                text: app.guest_status_text
                font_name: app.font_name
                halign: "center"
                theme_text_color: "Custom"
                text_color: 0.9, 0.2, 0.3, 1

        # Settings action buttons row
        MDBoxLayout:
            size_hint_y: None
            height: dp(48)
            spacing: dp(8)
            MDRaisedButton:
                text: "Retrain My Voice"
                font_name: app.font_name
                on_release: app.retrain_voice()
                style: "outlined"
            MDRaisedButton:
                text: "Guard: ON" if is_guard_enabled() else "Guard: OFF"
                font_name: app.font_name
                on_release: app.toggle_guard()
                style: "outlined"

        ScrollView:
            ApiKeysPanel:
                size_hint_y: None
                height: self.minimum_height
"""


def load_provider() -> str:
    try:
        with JayaMemory() as memory:
            value = memory.recall("settings.provider", LOCAL_PROVIDER)
    except Exception:
        value = LOCAL_PROVIDER
    return value if value in PROVIDERS else LOCAL_PROVIDER


def refresh_labels(app) -> None:
    resolved = resolve_provider(load_provider(), load_keys())
    app.provider_text = f"Provider: {resolved}"
    app.privacy_text = privacy_label(resolved)
    try:
        with JayaMemory() as memory:
            count = memory.count_chats()
    except Exception:
        count = 0
    app.memory_text = f"Memory: {count} chats - Local only"
    try:
        reminders = get_reminders(done=False)
        app.reminder_text = f"Reminders: {len(reminders)}"
    except Exception:
        app.reminder_text = "Reminders: 0"
    try:
        notes = get_notes()
        app.note_text = f"Notes: {len(notes)}"
    except Exception:
        app.note_text = "Notes: 0"


class GlowingOrb(Widget):
    """Glowing pink sphere. No eyes, no mouth."""

    pulse_scale = NumericProperty(1.0)
    is_listening = BooleanProperty(False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._anim = None
        with self.canvas:
            Color(*PINK, 0.18)
            self._glow = Ellipse()
            Color(*PINK, 0.95)
            self._core = Ellipse()
        self.bind(pos=self._redraw, size=self._redraw, pulse_scale=self._redraw)
        self._idle_pulse()

    def _idle_pulse(self) -> None:
        if self._anim:
            self._anim.cancel(self)
        self._anim = (
            Animation(pulse_scale=1.06, duration=1.8, t="in_out_sine")
            + Animation(pulse_scale=0.96, duration=1.8, t="in_out_sine")
        )
        self._anim.repeat = True
        self._anim.start(self)

    def set_listening(self, listening: bool) -> None:
        self.is_listening = bool(listening)
        if self._anim:
            self._anim.cancel(self)
        if self.is_listening:
            self._anim = (
                Animation(pulse_scale=1.13, duration=0.6, t="in_out_sine")
                + Animation(pulse_scale=0.94, duration=0.6, t="in_out_sine")
            )
            self._anim.repeat = True
            self._anim.start(self)
        else:
            self._idle_pulse()

    def _redraw(self, *_args) -> None:
        cx, cy = self.center
        base = min(self.width, self.height) * 0.34 * self.pulse_scale
        r = base * 1.3
        self._glow.pos = (cx - r, cy - r)
        self._glow.size = (2 * r, 2 * r)
        self._core.pos = (cx - base, cy - base)
        self._core.size = (2 * base, 2 * base)


class ApiKeysPanel(MDBoxLayout):
    """Five API key slots, kept only in the encrypted local SQLite memory."""

    def __init__(self, **kwargs):
        kwargs.setdefault("orientation", "vertical")
        kwargs.setdefault("size_hint_y", None)
        kwargs.setdefault("adaptive_height", True)
        kwargs.setdefault("spacing", dp(8))
        super().__init__(**kwargs)

        self.provider = load_provider()
        self.fields: dict[str, MDTextField] = {}

        self.add_widget(self._title("Provider (default: Local only)"))
        self.provider_label = MDLabel(
            text=f"Provider: {self.provider}",
            font_name=FONT,
            size_hint_y=None,
            height=dp(28),
            theme_text_color="Custom",
            text_color=(0.85, 0.88, 0.96, 0.95),
        )
        self.add_widget(self.provider_label)
        for name in PROVIDERS:
            button = Button(
                text=name,
                font_name=FONT,
                size_hint_y=None,
                height=dp(34),
                background_color=(0.12, 0.16, 0.28, 1),
                color=(0.85, 0.88, 0.96, 1),
            )
            button.bind(on_release=lambda _btn, n=name: self.set_provider(n))
            self.add_widget(button)

        self.add_widget(self._title("API Keys (encrypted locally)"))
        stored = load_keys()
        for slug, label in PROVIDER_SLOTS:
            field = MDTextField(
                hint_text=f"{label} — {'saved' if slug in stored else 'key'}",
                password=True,
                write_tab=False,
                size_hint_y=None,
                height=dp(64),
            )
            self.fields[slug] = field
            self.add_widget(field)

        self.add_widget(
            self._action_row("Save Keys", "content-save-outline", self.save)
        )
        self.add_widget(self._action_row("Clear Memory", "delete", self.clear_memory))
        self.add_widget(
            self._action_row("Clear Reminders", "delete", self.clear_reminders)
        )
        self.add_widget(
            self._action_row("Clear Notes", "delete", self.clear_notes)
        )
        self.add_widget(
            self._action_row("Delete All Keys", "delete-forever", self.delete_all_keys)
        )

        self.status = MDLabel(
            text="",
            font_name=FONT,
            size_hint_y=None,
            height=dp(32),
            halign="center",
            theme_text_color="Custom",
            text_color=(0.72, 0.78, 0.90, 1),
        )
        self.add_widget(self.status)

    def _title(self, text: str) -> MDLabel:
        return MDLabel(
            text=text,
            font_name=FONT,
            size_hint_y=None,
            height=dp(30),
            bold=True,
            theme_text_color="Custom",
            text_color=(0.85, 0.88, 0.96, 0.95),
        )

    def _action_row(self, label: str, icon: str, callback) -> MDBoxLayout:
        row = MDBoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(48),
            spacing=dp(8),
        )
        row.add_widget(
            MDLabel(
                text=label,
                font_name=FONT,
                theme_text_color="Custom",
                text_color=(0.85, 0.88, 0.96, 0.9),
            )
        )
        button = MDIconButton(icon=icon, font_name=FONT)
        button.bind(on_release=lambda *_: callback())
        row.add_widget(button)
        return row

    def set_provider(self, name: str) -> None:
        if name not in PROVIDERS:
            return
        self.provider = name
        self.provider_label.text = f"Provider: {name}"
        try:
            with JayaMemory() as memory:
                memory.remember("settings.provider", name, tags=("settings",))
        except Exception:
            pass
        self._refresh_app()

    def save(self) -> bool:
        values = {
            slug: field.text.strip()
            for slug, field in self.fields.items()
            if field.text.strip()
        }
        if not values:
            self.status.text = "No keys"
            return False
        merged = load_keys()
        merged.update(values)
        if not config.save_keys(merged):
            self.status.text = "Save error"
            return False
        # Keep fields filled - do NOT clear them
        self.status.text = "Saved locally (encrypted)"
        self._refresh_app()
        return True

    def clear_memory(self) -> bool:
        try:
            with JayaMemory() as memory:
                memory.clear_history()
        except Exception:
            self.status.text = "Clear error"
            return False
        self.set_provider(LOCAL_PROVIDER)
        self.status.text = "Memory cleared"
        self._refresh_app()
        return True

    def delete_all_keys(self) -> bool:
        ok = config.delete_keys()
        for field in self.fields.values():
            field.text = ""
        self.status.text = "Keys deleted" if ok else "Delete error"
        self._refresh_app()
        return ok

    def _refresh_app(self) -> None:
        app = App.get_running_app()
        if app is not None and hasattr(app, "refresh_privacy"):
            try:
                app.refresh_privacy()
            except Exception:
                pass

    def clear_reminders(self) -> None:
        from jaya.reminders import clear_all_reminders
        clear_all_reminders()
        parent = self.parent
        if parent is not None and hasattr(parent, "refresh_labels"):
            parent.refresh_labels()
        self.status.text = "Reminders cleared"

    def clear_notes(self) -> None:
        from jaya.notes import clear_all_notes
        clear_all_notes()
        self.status.text = "Notes cleared"


class JayaHomeScreen(MDScreen):
    pass


class JayaSettingsScreen(MDScreen):
    pass


def listen_and_respond(app, on_result) -> None:
    """Local ASR -> local intent or opt-in provider -> local TTS."""

    def status(text: str) -> None:
        Clock.schedule_once(lambda *_: setattr(app, "status_text", text), 0)

    def worker() -> None:
        from jaya.brain import handle
        from jaya.droid.audio import listen, speak

        status("Listening...")
        text = ""
        try:
            text = listen(5.0) or ""
        except Exception:
            text = ""
        if not text:
            status("No speech detected")
            Clock.schedule_once(lambda *_: on_result("No speech detected"), 0)
            return

        status("Thinking...")
        result = handle(text, load_provider(), load_keys())
        reply = str(result.get("reply") or "")
        lang = str(result.get("lang") or "en")
        try:
            with JayaMemory() as memory:
                memory.save_chat(text, reply, lang)
                memory.save_routine(text)
        except Exception:
            pass

        status("Speaking...")
        try:
            speak(reply, lang)
        except Exception:
            pass

        def finish(*_args) -> None:
            on_result(reply)
            try:
                app.refresh_privacy()
            except Exception:
                pass

        Clock.schedule_once(finish, 0)

    threading.Thread(target=worker, daemon=True).start()


def build_root() -> MDScreenManager:
    """Build the screen manager for the JAYA UI."""
    Builder.load_string(KV)
    manager = MDScreenManager()
    manager.add_widget(JayaHomeScreen(name="home"))
    manager.add_widget(JayaSettingsScreen(name="settings"))
    return manager


class JayaUIApp(MDApp):
    status_text = StringProperty(IDLE_TEXT)
    font_name = StringProperty(FONT)
    say_text = StringProperty("Say: JAYA")
    provider_text = StringProperty(f"Provider: {LOCAL_PROVIDER}")
    privacy_text = StringProperty("Privacy: Local only")
    memory_text = StringProperty("Memory: 0 chats - Local only")
    reminder_text = StringProperty("Reminders: 0")
    note_text = StringProperty("Notes: 0")
    brain_text = StringProperty("Brain: Local")
    guest_status_text = StringProperty("Voice not enrolled")
    _busy = False

    def build(self):
        self.title = "JAYA"
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "Pink"
        if platform != "android":
            Window.size = (390, 844)
        Window.clearcolor = NAVY
        self.refresh_privacy()
        return build_root()

    def refresh_privacy(self) -> None:
        refresh_labels(self)

    def on_start(self) -> None:
        self.refresh_privacy()
        try:
            from jaya.droid.audio import start_wake_listener

            if start_wake_listener(self._on_wake):
                self.status_text = "Listening for JAYA..."
        except Exception:
            pass

    def _on_wake(self, _heard: str = "") -> None:
        Clock.schedule_once(lambda *_: setattr(self, "status_text", "Yes?"), 0)

    def on_stop(self) -> None:
        try:
            from jaya.droid.audio import stop_wake_listener

            stop_wake_listener()
        except Exception:
            pass

    def retrain_voice(self) -> None:
        """Retrain the voice lock by re-enrolling Reda's voice."""
        from jaya.voice_lock import enroll_voice
        success = enroll_voice()
        if success:
            self.guest_status_text = "Voice re-trained - Reda enrolled"
        else:
            self.guest_status_text = "Voice re-training failed"

    def toggle_guard(self) -> None:
        """Toggle the guard system ON/OFF."""
        from jaya.guard import is_guard_enabled, set_guard_enabled
        current = is_guard_enabled()
        set_guard_enabled(not current)
        self.guest_status_text = f"Guard {'enabled' if not current else 'disabled'}"

    def on_orb_tapped(self) -> None:
        if self._busy:
            return
        orb: GlowingOrb = self.root.get_screen("home").ids.orb
        self._busy = True
        orb.set_listening(True)
        self.status_text = LISTEN_TEXT

        def done(text: str) -> None:
            self._busy = False
            orb.set_listening(False)
            self.status_text = text or IDLE_TEXT

        listen_and_respond(self, done)

    def open_settings_screen(self) -> None:
        self.root.current = "settings"

    def open_home_screen(self) -> None:
        self.root.current = "home"


if __name__ == "__main__":
    JayaUIApp().run()
