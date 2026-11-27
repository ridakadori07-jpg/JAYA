"""JAYA - KivyMD entry point."""

from __future__ import annotations

from kivy.clock import Clock
from kivy.core.window import Window
from kivy.lang import Builder
from kivy.properties import StringProperty
from kivy.utils import platform
from kivymd.app import MDApp
from kivymd.uix.screenmanager import MDScreenManager

from jaya import __app_name__
from jaya.memory import JayaMemory
from jaya.ui import (
    ApiKeysPanel,
    FONT,
    GlowingOrb,
    JayaHomeScreen,
    JayaSettingsScreen,
    listen_and_respond,
    refresh_labels,
)

NAVY_BG = (0.024, 0.043, 0.102, 1.0)  # #060B1A

KV = """
<JayaHomeScreen>:
    md_bg_color: 0.024, 0.043, 0.102, 1

    MDBoxLayout:
        orientation: "vertical"
        padding: dp(20), dp(16), dp(20), dp(28)

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

        Widget:
            size_hint_y: 0.12

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
            id: status_label
            text: app.status_text
            font_name: app.font_name
            halign: "center"
            size_hint_y: None
            height: dp(44)
            theme_text_color: "Custom"
            text_color: 0.88, 0.90, 0.98, 0.88

        Widget:
            size_hint_y: 0.10


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
            text: "Local-first mode. No tracking."
            font_name: app.font_name
            halign: "center"
            theme_text_color: "Custom"
            text_color: 0.72, 0.78, 0.90, 1

        ScrollView:
            ApiKeysPanel:
                size_hint_y: None
                height: self.minimum_height
"""


class JayaApp(MDApp):
    status_text = StringProperty("Hello, I am JAYA")
    font_name = StringProperty(FONT)
    say_text = StringProperty("Say: JAYA")
    provider_text = StringProperty("Provider: Local only")
    privacy_text = StringProperty("Privacy: Local only")
    memory_text = StringProperty("Memory: 0 chats - Local only")
    brain_text = StringProperty("Brain: Local")
    reminder_text = StringProperty("Reminders: 0")
    note_text = StringProperty("Notes: 0")
    _busy = False
    memory: JayaMemory | None = None

    def build(self):
        try:
            self.title = __app_name__
            self.theme_cls.theme_style = "Dark"
            self.theme_cls.primary_palette = "Pink"

            if platform != "android":
                Window.size = (390, 844)
            Window.clearcolor = NAVY_BG

            Builder.load_string(KV)
            self.refresh_privacy()
            sm = MDScreenManager()
            sm.add_widget(JayaHomeScreen(name="home"))
            sm.add_widget(JayaSettingsScreen(name="settings"))
            return sm
        except Exception as exc:
            from kivymd.uix.screen import MDScreen
            from kivymd.uix.label import MDLabel

            error_screen = MDScreen()
            error_screen.add_widget(
                MDLabel(
                    text=f"JAYA - Application error:\n{exc}",
                    halign="center",
                    theme_text_color="Custom",
                    text_color=(0.85, 0.88, 0.96, 0.95),
                )
            )
            return error_screen

    def refresh_privacy(self) -> None:
        refresh_labels(self)

    def on_start(self) -> None:
        try:
            self.memory = JayaMemory()
        except Exception:
            self.memory = None
        self.refresh_privacy()
        if platform == "android":
            self._request_runtime_permissions()
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
        if self.memory is not None:
            self.memory.close()
            self.memory = None

    def on_pause(self) -> bool:
        return True

    def on_resume(self) -> None:
        pass

    def _request_runtime_permissions(self) -> None:
        from android.permissions import Permission, request_permissions

        request_permissions([Permission.RECORD_AUDIO])

    def on_orb_tapped(self) -> None:
        if self._busy:
            return
        home = self.root.get_screen("home")
        orb: GlowingOrb = home.ids.orb
        self._busy = True
        orb.set_listening(True)
        self.status_text = "Listening..."

        def done(text: str) -> None:
            self._busy = False
            orb.set_listening(False)
            self.status_text = text or "Hello, I am JAYA"

        listen_and_respond(self, done)

    def open_settings_screen(self) -> None:
        self.root.current = "settings"

    def open_home_screen(self) -> None:
        self.root.current = "home"


if __name__ == "__main__":
    JayaApp().run()
