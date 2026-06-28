#!/usr/bin/env python3
"""
Background Wake Word Listener for Kailey.
Lightweight process that listens for "Kailey" and launches the main app.
Optimized for low-end PCs — uses minimal CPU.
"""

import os
import sys
import time
import subprocess
import json
import re

# ─── Import checks ───
try:
    import pyaudiowpatch as pyaudio
    import sys
    sys.modules['pyaudio'] = pyaudio
except ImportError:
    pass

try:
    import speech_recognition as sr
    HAS_SR = True
except ImportError:
    HAS_SR = False
    print("[WAKE] speech_recognition not installed. Wake word disabled.")

try:
    from vosk import Model as VoskModel, KaldiRecognizer
    HAS_VOSK = True
except ImportError:
    HAS_VOSK = False

# ─── Config ───
WAKE_WORDS = ["kailey", "hey kailey", "kailey are you there", "wake up kailey", "kali", "kaylee", "kelly", "kylie", "hailey", "daily", "clearly", "hey kelly", "hey kali", "hey", "hello", "hi", "listen"]
VOSK_MODEL_PATH = os.path.join(os.path.dirname(__file__), "models", "vosk-model-small-en-us")
_models_dir = os.path.join(os.path.dirname(__file__), "models")
if os.path.exists(_models_dir):
    for d in os.listdir(_models_dir):
        if d.startswith("vosk-model"):
            VOSK_MODEL_PATH = os.path.join(_models_dir, d)
            break
KAILEY_SCRIPT = os.path.join(os.path.dirname(__file__), "kailey.py")
LISTEN_TIMEOUT = 5
PHRASE_LIMIT = 4
COOLDOWN = 12
KAILEY_RUNNING_SLEEP = 3


def normalize_transcript(text):
    if not text:
        return ""
    t = text.lower().strip()
    t = re.sub(r"[^a-z0-9\s]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    replacements = {
        "kayley": "kailey",
        "kay lee": "kailey",
        "kay li": "kailey",
        "kali": "kailey",
        "kaylee": "kailey",
        "kelly": "kailey",
        "kylie": "kailey",
        "hailey": "kailey",
        "daily": "kailey",
        "clearly": "kailey",
    }
    for wrong, correct in replacements.items():
        t = re.sub(rf"\b{re.escape(wrong)}\b", correct, t)
    return t


def list_microphone_names():
    try:
        return list(sr.Microphone.list_microphone_names())
    except Exception:
        return []


def select_microphone_index(config_index=-1):
    names = list_microphone_names()
    if isinstance(config_index, int) and 0 <= config_index < len(names):
        return config_index
    if names:
        return 0
    return None


def is_kailey_running():
    """Check if main Kailey app is already running."""
    try:
        import psutil
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = proc.info.get('cmdline') or []
                if any('kailey.py' in str(c) for c in cmdline):
                    if proc.info['pid'] != os.getpid():
                        return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    except ImportError:
        pass
    return False


def launch_kailey():
    """Launch the main Kailey application."""
    if is_kailey_running():
        print("[WAKE] Kailey is already running.")
        return
    print("[WAKE] Launching Kailey...")
    try:
        if sys.platform == 'win32':
            subprocess.Popen(
                [sys.executable, KAILEY_SCRIPT],
                creationflags=subprocess.CREATE_NEW_CONSOLE
            )
        else:
            subprocess.Popen([sys.executable, KAILEY_SCRIPT])
        print("[WAKE] Kailey launched!")
    except Exception as e:
        print(f"[WAKE] Launch error: {e}")


global_vosk_model = None

def listen_with_vosk(recognizer, device_index):
    """Listen using Vosk offline model — lightweight, zero extra RAM."""
    global global_vosk_model
    try:
        with sr.Microphone(device_index=device_index) as source:
            audio = recognizer.listen(source, timeout=LISTEN_TIMEOUT, phrase_time_limit=PHRASE_LIMIT)
        if HAS_VOSK and os.path.exists(VOSK_MODEL_PATH):
            if global_vosk_model is None:
                global_vosk_model = VoskModel(VOSK_MODEL_PATH)
            rec = KaldiRecognizer(global_vosk_model, 16000)
            wav_data = audio.get_wav_data(convert_rate=16000, convert_width=2)
            rec.AcceptWaveform(wav_data)
            result = json.loads(rec.FinalResult())
            return normalize_transcript(result.get('text', '').strip())
        return normalize_transcript(recognizer.recognize_google(audio))
    except sr.WaitTimeoutError:
        return ""
    except sr.UnknownValueError:
        return ""
    except Exception:
        return ""


def listen_with_google(recognizer, device_index):
    """Listen using Google Speech Recognition."""
    try:
        with sr.Microphone(device_index=device_index) as source:
            audio = recognizer.listen(source, timeout=LISTEN_TIMEOUT, phrase_time_limit=PHRASE_LIMIT)
        return normalize_transcript(recognizer.recognize_google(audio))
    except (sr.WaitTimeoutError, sr.UnknownValueError, sr.RequestError):
        return ""
    except Exception:
        return ""


def main():
    if not HAS_SR:
        print("[WAKE] Cannot start — SpeechRecognition not installed.")
        return

    print("\n  +--------------------------------------------+")
    print("  |  Kailey Wake Word Listener                 |")
    print("  |  Say 'Kailey' to activate                  |")
    print("  +--------------------------------------------+\n")

    recognizer = sr.Recognizer()
    recognizer.energy_threshold = 220
    recognizer.dynamic_energy_threshold = True
    recognizer.dynamic_energy_adjustment_damping = 0.2
    recognizer.dynamic_energy_ratio = 1.5
    recognizer.pause_threshold = 0.6
    recognizer.non_speaking_duration = 0.35

    cfg_path = os.path.join(os.path.dirname(__file__), "config.json")
    mode = 'auto'
    input_device_index = -1
    try:
        if os.path.exists(cfg_path):
            with open(cfg_path, 'r', encoding='utf-8') as f:
                cfg = json.load(f)
                mode = cfg.get('recognition_mode', 'auto')
                input_device_index = cfg.get('input_device_index', -1)
    except: pass

    device_index = select_microphone_index(input_device_index)
    if device_index is None:
        print("[WAKE] Microphone error: no usable input device found.")
        return

    try:
        with sr.Microphone(device_index=device_index) as source:
            print("[WAKE] Calibrating microphone...")
            recognizer.adjust_for_ambient_noise(source, duration=1.5)
    except Exception as e:
        print(f"[WAKE] Microphone error: {e}")
        return

    # Vosk is only enabled for truly offline modes.
    # When recognition_mode is local_whisper, the wake listener should NOT switch to Vosk.
    use_vosk = HAS_VOSK and os.path.exists(VOSK_MODEL_PATH) and mode in ('offline', 'auto')
    listen_fn = listen_with_vosk if use_vosk else listen_with_google
    print(f"[WAKE] Config mode: {mode} | Listening engine: {'Vosk (Offline)' if use_vosk else 'Google (Online)'}")
    print(f"[WAKE] Wake words: {', '.join(WAKE_WORDS)}")
    print("[WAKE] Listening in background...\n")

    while True:
        try:
            if is_kailey_running():
                time.sleep(KAILEY_RUNNING_SLEEP)
                continue

            text = listen_fn(recognizer, device_index)
            if not text:
                time.sleep(0.2)
                continue

            # Debug: show what STT produced so we can verify wake detection.
            print(f"[WAKE] heard: '{text}'")

            for wake in WAKE_WORDS:
                if wake in text:
                    print(f"[WAKE] Wake word detected: '{text}'")
                    launch_kailey()
                    print(f"[WAKE] Cooling down for {COOLDOWN} seconds...\n")
                    time.sleep(COOLDOWN)
                    break
        except KeyboardInterrupt:
            print("\n[WAKE] Wake listener stopped.")
            break
        except Exception as e:
            print(f"[WAKE] Error: {e}")
            time.sleep(2)


if __name__ == '__main__':
    main()
