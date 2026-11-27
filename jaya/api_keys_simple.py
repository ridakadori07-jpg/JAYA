import json
import os

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
            data = json.load(f)
            return data.get(provider, "")
    except:
        return ""

def get_all_keys():
    if not os.path.exists(KEYS_FILE):
        return {}
    try:
        with open(KEYS_FILE, "r") as f:
            return json.load(f)
    except:
        return {}
