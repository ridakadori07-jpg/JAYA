from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.clock import Clock
import os, json

# --- المفاتيح: ساهل، بلا تشفير ---
KEYS_FILE = "jaya_keys.json"

def save_key(provider, key):
    data = {}
    if os.path.exists(KEYS_FILE):
        try:
            with open(KEYS_FILE, "r") as f:
                data = json.load(f)
        except:
            data = {}
    data[provider] = key.strip()
    with open(KEYS_FILE, "w") as f:
        json.dump(data, f)
    return True

def get_key(provider):
    if not os.path.exists(KEYS_FILE):
        return ""
    try:
        with open(KEYS_FILE, "r") as f:
            return json.load(f).get(provider, "")
    except:
        return ""

# --- الصوت: ديال Android نيشان ---
try:
    from jnius import autoclass
    ANDROID = True
except:
    ANDROID = False

_tts = None
def speak(text):
    global _tts
    print("JAYA:", text)
    if not ANDROID:
        return
    try:
        from jnius import autoclass
        Locale = autoclass('java.util.Locale')
        TextToSpeech = autoclass('android.speech.tts.TextToSpeech')
        PythonActivity = autoclass('org.kivy.android.PythonActivity')
        activity = PythonActivity.mActivity
        if _tts is None:
            _tts = TextToSpeech(activity, None)
        _tts.setLanguage(Locale("ar", "MA"))
        _tts.speak(text, TextToSpeech.QUEUE_FLUSH, None, "jaya")
    except Exception as e:
        print("TTS ERROR:", e)

# --- الشاشة اللولة ---
class HomeScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation='vertical', padding=20, spacing=20)
        layout.add_widget(Label(text="JAYA", font_size=32, bold=True))
        self.orb = Button(text="●", font_size=120, color=(1, 0.2, 0.6, 1), background_color=(0,0,0,0))
        self.orb.bind(on_press=self.on_orb)
        layout.add_widget(self.orb)
        self.status = Label(text="Hello, I am JAYA\nSay: JAYA", font_size=18)
        layout.add_widget(self.status)
        btn = Button(text="Settings ⚙️", size_hint_y=None, height=50)
        btn.bind(on_press=self.go_settings)
        layout.add_widget(btn)
        self.add_widget(layout)

    def on_orb(self, *args):
        self.status.text = "Listening...\nقول: شحال الوقت"
        speak("نعم رضا، أنا هنا")
        Clock.schedule_once(lambda dt: self.ask(), 1)

    def ask(self):
        self.status.text = "قول ليا: شحال الوقت\nولا: حل يوتيوب"

    def go_settings(self, *args):
        self.manager.current = "settings"

# --- شاشة Settings: فين كتدخل المفاتيح ---
class SettingsScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation='vertical', padding=20, spacing=10)
        layout.add_widget(Label(text="Settings", font_size=28, bold=True))
        layout.add_widget(Label(text="Local-first. No tracking.", font_size=14))
        layout.add_widget(Label(text="Gemini API Key:", font_size=16))
        self.gemini_input = TextInput(text=get_key("Gemini"), multiline=False, password=True)
        layout.add_widget(self.gemini_input)
        layout.add_widget(Label(text="Groq API Key:", font_size=16))
        self.groq_input = TextInput(text=get_key("Groq"), multiline=False, password=True)
        layout.add_widget(self.groq_input)
        self.msg = Label(text="", font_size=16, color=(0,1,0,1))
        layout.add_widget(self.msg)
        save_btn = Button(text="Save Keys", size_hint_y=None, height=50, background_color=(0,0.7,0,1))
        save_btn.bind(on_press=self.save_keys)
        layout.add_widget(save_btn)
        back_btn = Button(text="Back", size_hint_y=None, height=50)
        back_btn.bind(on_press=self.go_home)
        layout.add_widget(back_btn)
        self.add_widget(layout)

    def save_keys(self, *args):
        save_key("Gemini", self.gemini_input.text)
        save_key("Groq", self.groq_input.text)
        self.msg.text = "✅ Saved! المفتاح بقى، ماغاديش يتمسح"
        speak("تم حفظ المفتاح")

    def go_home(self, *args):
        self.manager.current = "home"

class JayaApp(App):
    def build(self):
        sm = ScreenManager()
        sm.add_widget(HomeScreen(name="home"))
        sm.add_widget(SettingsScreen(name="settings"))
        return sm

if __name__ == "__main__":
    JayaApp().run()
