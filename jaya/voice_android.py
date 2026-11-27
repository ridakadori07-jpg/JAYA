try:
    from jnius import autoclass
    ANDROID = True
except:
    ANDROID = False

_tts = None

def speak(text):
    global _tts
    if not ANDROID:
        print("SPEAK:", text)
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

def listen_once():
    if not ANDROID:
        return ""
    try:
        from jnius import autoclass
        Intent = autoclass('android.content.Intent')
        RecognizerIntent = autoclass('android.speech.RecognizerIntent')
        PythonActivity = autoclass('org.kivy.android.PythonActivity')
        activity = PythonActivity.mActivity
        intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH)
        intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
        intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE, "ar-MA")
        activity.startActivityForResult(intent, 1001)
        return "LISTENING"
    except Exception as e:
        print("STT ERROR:", e)
        return ""
