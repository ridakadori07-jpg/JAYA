[app]

title = JAYA
package.name = jaya
package.domain = org.jaya.assistant

source.dir = .
source.include_exts = py,png,jpg,ttf
source.include_patterns = jaya/fonts/*.ttf,jaya/bidi/*.py
source.exclude_dirs = tests,bin,.git,__pycache__

version = 0.1.0

# Core dependencies (lightweight for Redmi Note 11 Pro 5G)
requirements = python3,kivy==2.3.1,kivymd==1.2.0,sqlite3,pyjnius==1.9.0,requests,certifi,urllib3,idna,chardet,six

orientation = portrait
fullscreen = 0

android.presplash_color = #060B1A
android.allow_backup = False

# Android 13 (API 33) target for HyperOS 1.0.12.0 / Redmi Note 11 Pro 5G (Snapdragon 695 - arm64-v8a)
android.api = 33
android.minapi = 24
android.ndk = 25b
android.archs = arm64-v8a
android.accept_sdk_license = True

# Non-root permissions strictly needed for local voice, BT/Wi-Fi, app launch, and MIUI background survival
android.permissions = INTERNET, RECORD_AUDIO, FOREGROUND_SERVICE, WAKE_LOCK, ACCESS_WIFI_STATE, CHANGE_WIFI_STATE, BLUETOOTH

# Background voice service (uncomment when jaya/service.py is added in next steps)
# services = JayaVoice:jaya/service.py:sticky

[buildozer]
log_level = 2
warn_on_root = 1
p4a.branch = develop
