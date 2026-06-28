#!/usr/bin/env python3
"""
+----------------------------------------------------------+
|  Kailey — Personal Voice Command Assistant                |
|  Offline + Online AI | Custom Voice | Wake Word | Low-end |
+----------------------------------------------------------+
"""

import os
import sys
import json
import time
import math
import random
import gc
import threading
import subprocess
import shutil
import webbrowser
import datetime
import platform
import traceback
import asyncio
from pathlib import Path

# ═══════════════════════════════════════════════════════════════
#  GRACEFUL IMPORTS
# ═══════════════════════════════════════════════════════════════

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

try:
    import pyttsx3
    HAS_PYTTSX3 = True
except ImportError:
    HAS_PYTTSX3 = False

try:
    import edge_tts
    HAS_EDGE_TTS = True
except ImportError:
    HAS_EDGE_TTS = False

try:
    import pygame
    HAS_PYGAME = True
except ImportError:
    HAS_PYGAME = False

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

try:
    import pyautogui
    HAS_PYAUTOGUI = True
except ImportError:
    HAS_PYAUTOGUI = False

try:
    from vosk import Model as VoskModel, KaldiRecognizer
    HAS_VOSK = True
except ImportError:
    HAS_VOSK = False

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

try:
    from faster_whisper import WhisperModel
    HAS_FASTER_WHISPER = True
except ImportError:
    HAS_FASTER_WHISPER = False

IS_WINDOWS = platform.system() == "Windows"
if IS_WINDOWS:
    try:
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
        from ctypes import cast, POINTER
        from comtypes import CLSCTX_ALL
        HAS_VOLUME = True
    except Exception:
        HAS_VOLUME = False
    try:
        import screen_brightness_control as sbc
        HAS_BRIGHTNESS = True
    except ImportError:
        HAS_BRIGHTNESS = False
else:
    HAS_VOLUME = False
    HAS_BRIGHTNESS = False

import tkinter as tk
from tkinter import ttk, messagebox, filedialog

# ═══════════════════════════════════════════════════════════════
#  PATHS
# ═══════════════════════════════════════════════════════════════

APP_DIR = Path(__file__).parent
CONFIG_FILE = APP_DIR / "config.json"
COMMANDS_FILE = APP_DIR / "commands.json"
VOSK_MODEL_DIR = APP_DIR / "models" / "vosk-model-small-en-us"
_models_dir = APP_DIR / "models"
if _models_dir.exists():
    for d in _models_dir.iterdir():
        if d.is_dir() and d.name.startswith("vosk-model"):
            VOSK_MODEL_DIR = d
            break
GREETING_DIR = APP_DIR / "greeting_sounds"
GREETING_DIR.mkdir(exist_ok=True)


def open_url_in_app_mode(url):
    if IS_WINDOWS:
        try:
            import urllib.parse
            import win32com.client
            import subprocess
            import shlex

            parsed = urllib.parse.urlparse(url)
            domain = parsed.netloc.lower()
            if domain.startswith('www.'):
                domain = domain[4:]
            
            hints = [p for p in domain.split('.') if len(p) > 2 and p not in ['com', 'org', 'net', 'co']]
            if 'mail' in hints and 'google' in hints:
                hints.append('gmail')

            appdata = os.environ.get('APPDATA', '')
            if appdata and hints:
                dirs_to_check = [
                    os.path.join(appdata, r"Microsoft\Windows\Start Menu\Programs\Brave Apps"),
                    os.path.join(appdata, r"Microsoft\Windows\Start Menu\Programs\Chrome Apps"),
                    os.path.join(appdata, r"Microsoft\Windows\Start Menu\Programs\Edge Apps")
                ]
                
                shell = win32com.client.Dispatch("WScript.Shell")
                candidates = []
                for d in dirs_to_check:
                    if os.path.exists(d):
                        for f in os.listdir(d):
                            if f.lower().endswith('.lnk'):
                                f_base = f.lower().rsplit('.', 1)[0]
                                match_count = 0
                                for hint in hints:
                                    if hint in f_base:
                                        match_count += 1
                                
                                if match_count > 0:
                                    # Exact match bonus
                                    exact_bonus = 1 if any(hint == f_base for hint in hints) else 0
                                    # Score: (-match_count, -exact_bonus, length, path)
                                    candidates.append((-match_count, -exact_bonus, len(f_base), os.path.join(d, f)))
                
                if candidates:
                    candidates.sort()
                    shortcut_path = candidates[0][3]
                    try:
                        sc = shell.CreateShortCut(shortcut_path)
                        target = sc.TargetPath
                        args = sc.Arguments
                        
                        if target and os.path.exists(target):
                            cmd_args = [target] + shlex.split(args, posix=False) + [url]
                            subprocess.Popen(cmd_args)
                            return True
                    except Exception:
                        pass
        except Exception:
            pass
            
    return webbrowser.open(url)

# ═══════════════════════════════════════════════════════════════
#  EVENT BUS
# ═══════════════════════════════════════════════════════════════

class EventBus:
    """Central event mediator for decoupled component communication."""
    CMD_EXECUTE = "cmd.execute"
    AI_REQUEST = "ai.request"
    AI_STREAM = "ai.stream"
    AI_RESPONSE = "ai.response"
    AI_PROVIDER = "ai.provider"
    STT_TEXT = "stt.text"
    ERROR = "error"

    def __init__(self):
        self._listeners = {}

    def on(self, event_name, callback):
        if event_name not in self._listeners:
            self._listeners[event_name] = []
        self._listeners[event_name].append(callback)

    def emit(self, event_name, data=None):
        if event_name in self._listeners:
            for callback in self._listeners[event_name]:
                try:
                    callback(data)
                except Exception as e:
                    print(f"[ERROR] EventBus failed in {event_name}: {e}")

events = EventBus()

# ═══════════════════════════════════════════════════════════════
#  INTELLIGENT VOICE OPTIONS
# ═══════════════════════════════════════════════════════════════

EDGE_VOICE_LIST = [
    {"id": "en-US-JennyNeural",       "name": "Jenny (US) — Signature Kailey",     "gender": "Female", "lang": "en-US"},
    {"id": "en-GB-SoniaNeural",       "name": "Sonia (UK) — British Accent",        "gender": "Female", "lang": "en-GB"},
    {"id": "en-US-AriaNeural",        "name": "Aria (US) — Warm Personality",        "gender": "Female", "lang": "en-US"},
    {"id": "en-GB-MiaNeural",         "name": "Mia (UK) — Young Personality",           "gender": "Female", "lang": "en-GB"},
    {"id": "en-AU-NatashaNeural",     "name": "Natasha (AU) — Australian",          "gender": "Female", "lang": "en-AU"},
    {"id": "en-IN-NeerjaNeural",      "name": "Neerja (IN) — Indian Accent",        "gender": "Female", "lang": "en-IN"},
    {"id": "en-US-MichelleNeural",    "name": "Michelle (US) — Mature Voice",      "gender": "Female", "lang": "en-US"},
    {"id": "en-US-AnaNeural",         "name": "Ana (US) — Soft Spoken",             "gender": "Female", "lang": "en-US"},
    {"id": "en-US-EmmaNeural",        "name": "Emma (US) — Energetic",               "gender": "Female", "lang": "en-US"},
    {"id": "en-GB-LibbyNeural",       "name": "Libby (UK) — High Energy",             "gender": "Female", "lang": "en-GB"},
    {"id": "en-US-GuyNeural",         "name": "Guy (US) — Deep Masculine",               "gender": "Male",   "lang": "en-US"},
    {"id": "en-GB-RyanNeural",        "name": "Ryan (UK) — British Masculine",           "gender": "Male",   "lang": "en-GB"},
    {"id": "en-US-ChristopherNeural", "name": "Christopher (US) — Deep voice",      "gender": "Male",   "lang": "en-US"},
    {"id": "en-US-EricNeural",        "name": "Eric (US) — Clear Male",             "gender": "Male",   "lang": "en-US"},
    {"id": "en-US-RogerNeural",       "name": "Roger (US) — Mature Male",           "gender": "Male",   "lang": "en-US"},
    {"id": "en-US-DavisNeural",       "name": "Davis (US) — Casual Male",           "gender": "Male",   "lang": "en-US"},
    {"id": "en-US-JasonNeural",       "name": "Jason (US) — Confident",             "gender": "Male",   "lang": "en-US"},
    {"id": "en-US-TonyNeural",        "name": "Tony (US) — Friendly",               "gender": "Male",   "lang": "en-US"},
    {"id": "en-AU-WilliamNeural",     "name": "William (AU) — Australian Male",     "gender": "Male",   "lang": "en-AU"},
    {"id": "en-IN-PrabhatNeural",     "name": "Prabhat (IN) — Indian Male",         "gender": "Male",   "lang": "en-IN"},
]

# ═══════════════════════════════════════════════════════════════
#  DEFAULT CONFIG — All Kailey-branded
# ═══════════════════════════════════════════════════════════════

DEFAULT_CONFIG = {
    "assistant_name": "kailey",
    "wake_word": "kailey",
    "voice_engine": "edge_tts",
    "edge_voice_id": "en-US-JennyNeural",
    "edge_voice_rate": "-5%",
    "edge_voice_pitch": "+1Hz",
    "pyttsx3_rate": 175,
    "pyttsx3_volume": 1.0,
    "pyttsx3_voice_index": 1,
    "custom_greeting_file": "",
    "play_greeting_sound": True,
    "recognition_mode": "auto",
    "continuous_listen": False,
    "ai_mode": "gemini",
    "openai_api_key": "",
    "openai_model": "gpt-3.5-turbo",
    "gemini_api_key": "AIzaSyCe_ggRST7Ojthvoa-mLsAlaz2xjQ36nYU",
    "gemini_model": "gemini-flash-latest",
    "ollama_url": "http://localhost:11434",
    "ollama_model": "llama3",
    "ollama_cloud_url": "",
    "ollama_cloud_model": "",
    "ollama_cloud_key": "",
    "local_ai_url": "http://localhost:1234/v1",
    "local_ai_key": "",
    "local_ai_model": "local-model",
    "custom_ai_url": "",
    "custom_ai_key": "",
    "custom_ai_model": "custom-model",
    "language": "en-US",
    "start_listening_on_boot": True,
    "greet_on_start": True,
}

DEFAULT_COMMANDS = {
    "youtube": {"action": "open_url", "target": "https://www.youtube.com", "description": "Open YouTube", "category": "apps"},
    "open youtube": {"action": "open_url", "target": "https://www.youtube.com", "description": "Open YouTube", "category": "apps"},
    "youtube search": {"action": "youtube_search", "target": "", "description": "Search YouTube", "category": "apps"},
    "google": {"action": "open_url", "target": "https://www.google.com", "description": "Open Google", "category": "apps"},
    "search": {"action": "web_search", "target": "", "description": "Google search", "category": "apps"},
    "gmail": {"action": "open_url", "target": "https://mail.google.com", "description": "Open Gmail", "category": "apps"},
    "github": {"action": "open_url", "target": "https://github.com", "description": "Open GitHub", "category": "apps"},
    "whatsapp": {"action": "open_url", "target": "https://web.whatsapp.com", "description": "Open WhatsApp", "category": "apps"},
    "instagram": {"action": "open_url", "target": "https://www.instagram.com", "description": "Open Instagram", "category": "apps"},
    "twitter": {"action": "open_url", "target": "https://twitter.com", "description": "Open Twitter/X", "category": "apps"},
    "spotify": {"action": "open_url", "target": "https://open.spotify.com", "description": "Open Spotify", "category": "apps"},
    "netflix": {"action": "open_url", "target": "https://www.netflix.com", "description": "Open Netflix", "category": "apps"},
    "maps": {"action": "open_url", "target": "https://maps.google.com", "description": "Open Maps", "category": "apps"},
    "translate": {"action": "open_url", "target": "https://translate.google.com", "description": "Open Translate", "category": "apps"},
    "news": {"action": "open_url", "target": "https://news.google.com", "description": "Open News", "category": "apps"},
    "reddit": {"action": "open_url", "target": "https://www.reddit.com", "description": "Open Reddit", "category": "apps"},
    "notepad": {"action": "open_app", "target": "notepad.exe", "description": "Open Notepad", "category": "apps"},
    "calculator": {"action": "open_app", "target": "calc.exe", "description": "Open Calculator", "category": "apps"},
    "file explorer": {"action": "open_app", "target": "explorer.exe", "description": "Open File Explorer", "category": "apps"},
    "task manager": {"action": "open_app", "target": "taskmgr.exe", "description": "Open Task Manager", "category": "apps"},
    "command prompt": {"action": "open_app", "target": "cmd.exe", "description": "Open CMD", "category": "apps"},
    "terminal": {"action": "open_app", "target": "cmd.exe", "description": "Open Terminal", "category": "apps"},
    "chrome": {"action": "open_app", "target": "chrome.exe", "description": "Open Chrome", "category": "apps"},
    "vscode": {"action": "open_app", "target": "code.exe", "description": "Open VS Code", "category": "apps"},
    "paint": {"action": "open_app", "target": "mspaint.exe", "description": "Open Paint", "category": "apps"},
    "settings": {"action": "open_app", "target": "ms-settings:", "description": "Open Settings", "category": "apps"},
    "volume up": {"action": "volume_up", "target": "10", "description": "Volume up 10%", "category": "system"},
    "volume down": {"action": "volume_down", "target": "10", "description": "Volume down 10%", "category": "system"},
    "volume full": {"action": "volume_set", "target": "100", "description": "Volume 100%", "category": "system"},
    "mute": {"action": "volume_mute", "target": "", "description": "Mute", "category": "system"},
    "brightness up": {"action": "brightness_up", "target": "10", "description": "Brightness up 10%", "category": "system"},
    "brightness down": {"action": "brightness_down", "target": "10", "description": "Brightness down 10%", "category": "system"},
    "screenshot": {"action": "screenshot", "target": "", "description": "Take screenshot", "category": "system"},
    "lock": {"action": "lock_screen", "target": "", "description": "Lock screen", "category": "system"},
    "shutdown": {"action": "shutdown", "target": "", "description": "Shutdown PC", "category": "system"},
    "restart": {"action": "restart", "target": "", "description": "Restart PC", "category": "system"},
    "sleep": {"action": "sleep", "target": "", "description": "Sleep PC", "category": "system"},
    "close window": {"action": "key_combo", "target": "alt+f4", "description": "Close window", "category": "system"},
    "minimize": {"action": "key_combo", "target": "win+d", "description": "Minimize all", "category": "system"},
    "switch window": {"action": "key_combo", "target": "alt+tab", "description": "Switch window", "category": "system"},
    "copy": {"action": "key_combo", "target": "ctrl+c", "description": "Copy", "category": "system"},
    "paste": {"action": "key_combo", "target": "ctrl+v", "description": "Paste", "category": "system"},
    "type": {"action": "type_text", "target": "", "description": "Type text", "category": "system"},
    "open": {"action": "open_anything", "target": "", "description": "Open anything", "category": "system"},
    "app launcher": {"action": "app_launcher", "target": "", "description": "Open installed app", "category": "system"},
    "time": {"action": "tell_time", "target": "", "description": "Current time", "category": "info"},
    "date": {"action": "tell_date", "target": "", "description": "Current date", "category": "info"},
    "weather": {"action": "weather", "target": "", "description": "Weather info", "category": "info"},
    "cpu": {"action": "cpu_status", "target": "", "description": "CPU usage", "category": "info"},
    "memory": {"action": "memory_status", "target": "", "description": "RAM usage", "category": "info"},
    "battery": {"action": "battery_status", "target": "", "description": "Battery status", "category": "info"},
    "system info": {"action": "system_info", "target": "", "description": "Full system info", "category": "info"},
    "play music": {"action": "open_url", "target": "https://www.youtube.com/results?search_query=music+lofi", "description": "Play music", "category": "apps"},
    "stop listening": {"action": "stop_listening", "target": "", "description": "Stop voice input", "category": "system"},
    "cancel shutdown": {"action": "cancel_shutdown", "target": "", "description": "Cancel shutdown", "category": "system"},
}


# ═══════════════════════════════════════════════════════════════
#  CONFIG MANAGER
# ═══════════════════════════════════════════════════════════════

class ApplicationConfigurationRegistry:
    """
    Handles the persistent storage and retrieval of application settings and voice commands.
    We separate these into two files to allow for easier synchronization across devices.
    """
    def __init__(self):
        self.active_settings = self._initialize_json_store(CONFIG_FILE, DEFAULT_CONFIG)
        self.action_commands = self._initialize_json_store(COMMANDS_FILE, DEFAULT_COMMANDS)

    @staticmethod
    def _initialize_json_store(file_path, default_fallback):
        """
        Attempts to load a JSON file, creating it from defaults if it does not exist.
        Merging ensures that updates to the software don't fail when new keys are missing.
        """
        try:
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as file_handle:
                    persisted_data = json.load(file_handle)
                return {**default_fallback, **persisted_data}
            
            # Persist defaults if no file exists yet
            with open(file_path, 'w', encoding='utf-8') as file_handle:
                json.dump(default_fallback, file_handle, indent=2)
            return dict(default_fallback)
            
        except json.JSONDecodeError as decode_failure:
            print(f"[CRITICAL] Configuration file {file_path} is corrupt: {decode_failure}")
            return dict(default_fallback)
        except PermissionError as access_failure:
            print(f"[ERROR] Permission denied when accessing {file_path}: {access_failure}")
            return dict(default_fallback)

    def persist_application_settings(self):
        """Saves current global configuration to config.json."""
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as config_handle:
                json.dump(self.active_settings, config_handle, indent=2)
        except IOError as write_error:
            print(f"[ERROR] Failed to save application settings: {write_error}")

    def persist_voice_commands(self):
        """Saves custom user commands to commands.json."""
        try:
            with open(COMMANDS_FILE, 'w', encoding='utf-8') as command_handle:
                json.dump(self.action_commands, command_handle, indent=2)
        except IOError as write_error:
            print(f"[ERROR] Failed to save custom commands: {write_error}")

    def register_new_command(self, trigger_phrase, action_type, target_string, help_text="", label="custom"):
        """Registers a new voice command and persists it immediately."""
        self.action_commands[trigger_phrase.lower().strip()] = {
            "action": action_type, 
            "target": target_string,
            "description": help_text or f"Automated: {trigger_phrase}",
            "category": label
        }
        self.persist_voice_commands()

    def unregister_command(self, trigger_phrase):
        """Removes a command by its trigger phrase."""
        normalized_trigger = trigger_phrase.lower().strip()
        if normalized_trigger in self.action_commands:
            del self.action_commands[normalized_trigger]
            self.persist_voice_commands()
            return True
        return False


# ═══════════════════════════════════════════════════════════════
#  VOICE MANAGER — Kailey's Voice
# ═══════════════════════════════════════════════════════════════

class VoiceSynthesisOrchestrator:
    """
    Coordinates the audible response systems of the application.
    Prioritizes high-quality cloud synthesis via Edge-TTS but falls back to native SAPI5 if offline.
    """
    def __init__(self, system_settings):
        self.settings = system_settings
        self.is_currently_speaking = False
        self._synthesis_lock = threading.Lock()
        
        self.native_engine = self._initialize_native_synthesis()
        self.temporary_audio_cache = APP_DIR / "temp_audio"
        self.temporary_audio_cache.mkdir(exist_ok=True)

        if HAS_PYGAME:
            self._initialize_audio_playback()

    def _initialize_native_synthesis(self):
        """Sets up the offline fallback voice engine (pyttsx3)."""
        if not HAS_PYTTSX3:
            return None
        try:
            native_instance = pyttsx3.init()
            native_instance.setProperty('rate', self.settings.get('pyttsx3_rate', 175))
            native_instance.setProperty('volume', self.settings.get('pyttsx3_volume', 1.0))
            return native_instance
        except Exception as init_failure:
            print(f"[WARN] Native synthesis initialization failed: {init_failure}")
            return None

    def _initialize_audio_playback(self):
        """Prepares the pygame mixer for high-fidelity audio playback."""
        try:
            pygame.mixer.init(frequency=44100, size=-16, channels=1, buffer=2048)
        except Exception as mixer_failure:
            print(f"[ERROR] Audio playback system (Pygame) failed: {mixer_failure}")

    def queue_speech(self, text_payload, completion_callback=None):
        """Asynchronously processes a text-to-speech request to avoid blocking the UI."""
        def _speech_execution_worker():
            with self._synthesis_lock:
                self.is_currently_speaking = True
                try:
                    self._execute_synthesis_logic(text_payload)
                except Exception as synthesis_error:
                    print(f"[CRITICAL] Voice synthesis failure: {synthesis_error}")
                    # Desperate fallback to console if both engines fail
                    print(f"[KAILEY] {text_payload}")
                finally:
                    self.is_currently_speaking = False
                    if completion_callback:
                        completion_callback()

        threading.Thread(target=_speech_execution_worker, daemon=True).start()

    def _execute_synthesis_logic(self, text):
        """Determines the best available engine for the current request."""
        engine_type = self.settings.get('voice_engine', 'edge_tts')
        
        if engine_type == 'edge_tts' and HAS_EDGE_TTS:
            self._generate_and_play_neural_audio(text)
        elif self.native_engine:
            self._play_native_sapi_audio(text)
        else:
            print(f"[Kailey] {text}")

    async def _edge_tts_save_task(self, text, voice, rate, pitch, path):
        communicator = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
        await communicator.save(str(path))

    def _generate_and_play_neural_audio(self, text):
        """Downloads high-quality neural audio from Microsoft and plays it back."""
        voice_identifier = self.settings.get('edge_voice_id', 'en-US-JennyNeural')
        speech_rate = self.settings.get('edge_voice_rate', '-5%')
        speech_pitch = self.settings.get('edge_voice_pitch', '+1Hz')
        
        unique_timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        output_file_path = self.temporary_audio_cache / f"synthesis_{unique_timestamp}.mp3"

        try:
            asyncio.run(self._edge_tts_save_task(text, voice_identifier, speech_rate, speech_pitch, output_file_path))

            if output_file_path.exists():
                self.stream_audio_from_file(str(output_file_path))
                # Cleanup on a slight delay to ensure file handles are released
                threading.Timer(5.0, lambda: self._remove_cached_audio(output_file_path)).start()
        except Exception as network_failure:
            print(f"[ERROR] Edge-TTS service connection lost: {network_failure}")
            self._play_native_sapi_audio(text)

    def _play_native_sapi_audio(self, text):
        """Uses the local OS voice engine to speak text offline."""
        try:
            if IS_WINDOWS:
                try:
                    import win32com.client
                except ImportError:
                    win32com = None
                if win32com:
                    sapi_speaker = win32com.client.Dispatch("SAPI.SpVoice")
                    # Search for a female persona in the system voices
                    available_voices = sapi_speaker.GetVoices()
                    preferred_voice_index = 1
                    for index in range(available_voices.Count):
                        voice_description = available_voices.Item(index).GetDescription().lower()
                        if 'zira' in voice_description or 'female' in voice_description:
                            preferred_voice_index = index
                            break
                    sapi_speaker.Voice = available_voices.Item(preferred_voice_index)
                    sapi_speaker.Speak(text)
                elif self.native_engine:
                    self.native_engine.say(text)
                    self.native_engine.runAndWait()
            elif self.native_engine:
                self.native_engine.say(text)
                self.native_engine.runAndWait()
        except Exception as sapi_failure:
            print(f"[WARN] Local SAPI5 playback failed: {sapi_failure}")

    def stream_audio_from_file(self, file_path):
        """Plays an audio file via the best available low-level library."""
        if HAS_PYGAME:
            try:
                pygame.mixer.music.load(file_path)
                pygame.mixer.music.play()
                while pygame.mixer.music.get_busy():
                    time.sleep(0.05)
                pygame.mixer.music.unload()
                return
            except pygame.error as audio_error:
                print(f"[WARN] Pygame playback error: {audio_error}")

        # Final OS-level fallback if pygame is broken
        self._execute_native_os_audio_player(file_path)

    def _execute_native_os_audio_player(self, file_path):
        """Last resort audio playback using OS commands."""
        try:
            if IS_WINDOWS:
                import ctypes
                mci_alias = f"kailey_stream_{int(time.time()*1000)}"
                ctypes.windll.winmm.mciSendStringW(f'open "{file_path}" alias {mci_alias}', None, 0, None)
                ctypes.windll.winmm.mciSendStringW(f'play {mci_alias} wait', None, 0, None)
                ctypes.windll.winmm.mciSendStringW(f'close {mci_alias}', None, 0, None)
        except Exception:
            pass

    def speak(self, text):
        """High-level alias for queue_speech for cleaner controller logic."""
        self.queue_speech(text)

    def get_pyttsx3_voices(self):
        """Retrieves a list of available system voices for selection in the HUD."""
        if not self.native_engine:
            return []
        try:
            voices = self.native_engine.getProperty('voices')
            return [{'index': i, 'name': v.name, 'id': v.id} for i, v in enumerate(voices)]
        except Exception:
            return []

    def purge_audio_cache(self):
        """Cleans up all temporary speech files from disk."""
        try:
            for cache_file in self.temporary_audio_cache.glob("synthesis_*.mp3"):
                cache_file.unlink(missing_ok=True)
        except OSError as cleanup_failure:
            print(f"[WARN] Could not fully purge audio cache: {cleanup_failure}")

    def _remove_cached_audio(self, path):
        """Deletes a single file with safety checks."""
        try:
            if path.exists():
                path.unlink()
        except Exception:
            pass


# ═══════════════════════════════════════════════════════════════
#  SPEECH RECOGNITION ENGINE
# ═══════════════════════════════════════════════════════════════

class SpeechRecognitionEngine:
    """
    Handles all inbound audio processing, from microphone capture to text transcription.
    Supports multiple recognition tiers: Local (Vosk/Whisper) and Cloud (Google/Groq/OpenAI).
    """
    def __init__(self, system_settings):
        self.settings = system_settings
        self.audio_recognizer = None
        self.microphone_source = None
        self.vosk_model_instance = None
        self.whisper_model_instance = None
        self._initialize_recognition_hardware()

    def _initialize_recognition_hardware(self):
        """Prepares the microphone and speech recognition backend."""
        if not HAS_SR:
            return
        try:
            self.audio_recognizer = sr.Recognizer()
            # Tuned for ambient noise typical in home/office environments
            self.audio_recognizer.energy_threshold = 300
            self.audio_recognizer.dynamic_energy_threshold = True
            self.audio_recognizer.pause_threshold = 0.4
            
            self.microphone_source = sr.Microphone()
            with self.microphone_source as source:
                self.audio_recognizer.adjust_for_ambient_noise(source, duration=1)
        except Exception as hardware_error:
            print(f"[ERROR] Could not initialize microphone hardware: {hardware_error}")
            self.audio_recognizer = None

    def attempt_vosk_model_load(self):
        """Attempts to load the local Vosk model for offline recognition."""
        if not HAS_VOSK:
            return False
        try:
            if VOSK_MODEL_DIR.exists():
                self.vosk_model_instance = VoskModel(str(VOSK_MODEL_DIR))
                return True
        except Exception as model_failure:
            print(f"[WARN] Local Vosk model failed to load: {model_failure}")
        return False

    def capture_and_transcribe(self):
        """
        Listens for a single phrase and attempts to transcribe it using the configured mode.
        If the primary mode fails, it falls back to the most robust available method.
        """
        if not self.audio_recognizer or not self.microphone_source:
            return None

        transcription_mode = self.settings.get('recognition_mode', 'auto').lower()
        is_low_end = self.settings.get('low_end_mode', False)
        phrase_limit = 6 if is_low_end else 10
        listen_timeout = 4 if is_low_end else 5

        try:
            with self.microphone_source as active_source:
                captured_audio = self.audio_recognizer.listen(active_source, timeout=listen_timeout, phrase_time_limit=phrase_limit)

                if transcription_mode == 'openai_whisper':
                    return self._transcribe_via_openai_cloud(captured_audio)
                if transcription_mode == 'groq_whisper':
                    return self._transcribe_via_groq_cloud(captured_audio)
                if transcription_mode == 'local_whisper':
                    local_text = self._transcribe_via_local_whisper(captured_audio)
                    if local_text:
                        return local_text.lower()
                    # Fallback for old PCs where faster-whisper isn't available or fails
                    if self.vosk_model_instance:
                        offline_text = self._transcribe_via_vosk_offline(captured_audio)
                        if offline_text:
                            return offline_text.lower()
                    return self._transcribe_via_google_cloud(captured_audio)

                # Fallback sequence for 'auto' or 'offline'
                if transcription_mode in ('offline', 'auto') and self.vosk_model_instance:
                    offline_text = self._transcribe_via_vosk_offline(captured_audio)
                    if offline_text:
                        return offline_text.lower()

                if transcription_mode in ('online', 'auto'):
                    return self._transcribe_via_google_cloud(captured_audio)

        except sr.WaitTimeoutError:
            return None
        except Exception as general_recognition_error:
            print(f"[ERROR] Speech recognition pipeline failure: {general_recognition_error}")
        return None

    def _transcribe_via_local_whisper(self, audio_data):
        """Runs the Faster-Whisper model locally on the CPU."""
        if not HAS_FASTER_WHISPER:
            print("[WARN] local_whisper requested but faster-whisper is not installed.")
            return None
        try:
            if self.whisper_model_instance is None:
                is_low_end = self.settings.get('low_end_mode', False)
                model_identifier = self.settings.get('local_whisper_model', 'tiny.en' if is_low_end else 'small.en')
                compute_threads = max(1, min(2 if is_low_end else 4, os.cpu_count() or 4))

                print(f"[SYSTEM] Initializing Local Whisper ({model_identifier})...")
                self.whisper_model_instance = WhisperModel(model_identifier, device="cpu", compute_type="int8", cpu_threads=compute_threads)

            import io
            audio_buffer = io.BytesIO(audio_data.get_wav_data())
            vad_enabled = self.settings.get('local_whisper_vad', True)
            beam = 1 if self.settings.get('low_end_mode', False) else 2

            segments, _ = self.whisper_model_instance.transcribe(
                audio_buffer,
                beam_size=beam,
                vad_filter=vad_enabled,
                vad_parameters=dict(min_silence_duration_ms=500) if vad_enabled else None
            )
            return " ".join([segment.text for segment in segments]).strip()
        except Exception as whisper_failure:
            print(f"[ERROR] Local Whisper transcription failed: {whisper_failure}")
            return None

    def _transcribe_via_vosk_offline(self, audio_data):
        """Performs legacy offline recognition using Vosk."""
        try:
            recognizer_engine = KaldiRecognizer(self.vosk_model_instance, 16000)
            raw_wav_data = audio_data.get_wav_data(convert_rate=16000, convert_width=2)
            recognizer_engine.AcceptWaveform(raw_wav_data)
            parsing_result = json.loads(recognizer_engine.FinalResult())
            return parsing_result.get('text', '').strip()
        except Exception:
            return None

    def _transcribe_via_google_cloud(self, audio_data):
        """Free tier Google Cloud recognition."""
        try:
            return self.audio_recognizer.recognize_google(audio_data).lower().strip()
        except (sr.UnknownValueError, sr.RequestError):
            return None

    def _transcribe_via_groq_cloud(self, audio_data):
        """Ultra-fast Whisper transcription via Groq API."""
        api_key = self.settings.get('groq_api_key', '')
        if not api_key: return None
        try:
            api_endpoint = "https://api.groq.com/openai/v1/audio/transcriptions"
            headers = {"Authorization": f"Bearer {api_key}"}
            payload_files = {"file": ("recording.wav", audio_data.get_wav_data(), "audio/wav")}
            request_data = {"model": "whisper-large-v3"}
            response = requests.post(api_endpoint, headers=headers, files=payload_files, data=request_data, timeout=10)
            return response.json().get("text", "").strip()
        except Exception as groq_failure:
            print(f"[ERROR] Groq Whisper API failed: {groq_failure}")
            return None

    def _transcribe_via_openai_cloud(self, audio_data):
        """Standard OpenAI Whisper API transcription."""
        api_key = self.settings.get('openai_api_key', '')
        if not api_key: return None
        try:
            api_endpoint = "https://api.openai.com/v1/audio/transcriptions"
            headers = {"Authorization": f"Bearer {api_key}"}
            payload_files = {"file": ("recording.wav", audio_data.get_wav_data(), "audio/wav")}
            request_data = {"model": "whisper-1"}
            response = requests.post(api_endpoint, headers=headers, files=payload_files, data=request_data, timeout=15)
            return response.json().get("text", "").strip()
        except Exception as openai_failure:
            print(f"[ERROR] OpenAI Whisper API failed: {openai_failure}")
            return None


# ═══════════════════════════════════════════════════════════════
#  AI ENGINE — Kailey's Brain
# ═══════════════════════════════════════════════════════════════

class CognitiveIntelligenceCore:
    """
    The decision-making hub of the application.
    Orchestrates communication with various LLM backends (Ollama, Gemini, OpenAI).
    """
    def __init__(self, system_settings):
        self.settings = system_settings
        self.conversation_history = []

    def generate_response(self, user_prompt):
        """Routes the user prompt to the appropriate AI core based on current settings."""
        operation_mode = self.settings.get('ai_mode', 'auto')

        def _emit_provider(label, model_key=None):
            model_val = ""
            if model_key:
                model_val = self.settings.get(model_key, "") or ""
            events.emit(EventBus.AI_PROVIDER, {"provider": label, "model": model_val})

        if operation_mode in ('auto', 'hybrid'):
            # Start by attempting Gemini; UI/voice should reflect that we are trying Gemini first.
            _emit_provider("Gemini", "gemini_model")
            cloud_reply = self._process_via_google_gemini(user_prompt)
            if "error" not in cloud_reply.lower() and cloud_reply.strip():
                return cloud_reply
            _emit_provider("Ollama", "ollama_model")
            return self._process_via_ollama_local(user_prompt)

        elif operation_mode == 'gemini':
            _emit_provider("Gemini", "gemini_model")
            return self._process_via_google_gemini(user_prompt)
        elif operation_mode == 'openai':
            _emit_provider("OpenAI", "openai_model")
            return self._process_via_openai_cloud(user_prompt)
        elif operation_mode == 'ollama_hybrid':
            _emit_provider("Ollama (Local)", "ollama_model")
            local_reply = self._process_via_ollama_local(user_prompt)
            if "error" not in local_reply.lower() and local_reply.strip():
                return local_reply
            _emit_provider("Ollama (Cloud)", "ollama_cloud_model")
            return self._process_via_ollama_local(user_prompt, use_cloud_endpoint=True)
        elif operation_mode == 'ollama':
            _emit_provider("Ollama (Local)", "ollama_model")
            return self._process_via_ollama_local(user_prompt)
        elif operation_mode == 'local_ai':
            _emit_provider("LocalAI", "local_ai_model")
            return self._process_via_openai_compatible(user_prompt, "local_ai")
        elif operation_mode == 'custom':
            _emit_provider("Custom AI", "custom_ai_model")
            return self._process_via_openai_compatible(user_prompt, "custom")

        return self._generate_static_offline_response(user_prompt)

    def _process_via_google_gemini(self, prompt):
        """Interfaces with Google's Gemini model for high-intelligence tasks."""
        if not HAS_REQUESTS:
            return "System Error: requests library missing."
        api_key = self.settings.get('gemini_api_key', '')
        if not api_key:
            return "Configuration Error: Gemini API key is missing."

        model_id = self.settings.get('gemini_model', 'gemini-flash-latest')
        timeout_s = 6 if self.settings.get('low_end_mode', False) else 15

        try:
            endpoint_url = (
                f"https://generativelanguage.googleapis.com/v1beta/models/"
                f"{model_id}:generateContent?key={api_key}"
            )
            payload = {
                "system_instruction": {
                    "parts": {"text": "You are Kailey, a concise and highly intelligent assistant. No filler words."}
                },
                "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            }
            response = requests.post(
                endpoint_url,
                headers={"Content-Type": "application/json"},
                json=payload,
                timeout=timeout_s
            )
            response_json = response.json()

            if 'candidates' in response_json and response_json['candidates']:
                raw_text = response_json['candidates'][0]['content']['parts'][0]['text']
                return raw_text.replace('*', '').strip()
            return f"Gemini API Error: {response_json.get('error', {}).get('message', 'Unknown failure')}"
        except Exception as connection_failure:
            return f"Gemini Connection Failure: {connection_failure}"

    def _process_via_ollama_local(self, prompt, use_cloud_endpoint=False):
        """Communicates with the local Ollama instance or a private cloud Ollama server."""
        if not HAS_REQUESTS:
            return "System Error: requests library missing."

        config_prefix = "ollama_cloud" if use_cloud_endpoint else "ollama"
        server_url = self.settings.get(f'{config_prefix}_url', 'http://localhost:11434')
        model_name = self.settings.get(f'{config_prefix}_model', 'phi3')
        is_low_end = self.settings.get('low_end_mode', False)
        stream_it = not is_low_end

        try:
            history = self.conversation_history[-2:] if is_low_end else self.conversation_history[-4:]
            chat_payload = {
                "model": model_name,
                "messages": [{"role": "system", "content": "You are Kailey. Mature female assistant. Concise."}] + history,
                "stream": stream_it,
                "options": {
                    "num_ctx": 1024 if is_low_end else 2048,
                    "num_predict": 60 if is_low_end else 100,
                    "temperature": 0.7
                }
            }

            headers = {"Content-Type": "application/json"}
            if self.settings.get(f'{config_prefix}_key'):
                headers["Authorization"] = f"Bearer {self.settings.get(f'{config_prefix}_key')}"

            timeout_s = 25 if is_low_end else 60

            try:
                response = requests.post(
                    f"{server_url}/api/chat",
                    headers=headers,
                    json=chat_payload,
                    timeout=timeout_s,
                    stream=stream_it
                )
            except requests.exceptions.ConnectionError:
                if not use_cloud_endpoint and self._revive_ollama_service():
                    time.sleep(2)
                    response = requests.post(
                        f"{server_url}/api/chat",
                        headers=headers,
                        json=chat_payload,
                        timeout=timeout_s,
                        stream=stream_it
                    )
                else:
                    raise

            accumulated_response = ""

            if stream_it:
                for line_chunk in response.iter_lines():
                    if line_chunk:
                        parsed_chunk = json.loads(line_chunk)
                        if 'message' in parsed_chunk:
                            content_fragment = parsed_chunk['message']['content']
                            accumulated_response += content_fragment
                            # Low-end should not stream UI updates
                            if not is_low_end:
                                events.emit(EventBus.AI_STREAM, {"chunk": content_fragment, "full": accumulated_response})
            else:
                # Non-stream response shape varies slightly by server; handle common one.
                try:
                    response_json = response.json()
                    accumulated_response = (
                        response_json.get("message", {}).get("content", "")
                        or response_json.get("content", "")
                        or ""
                    )
                except Exception:
                    accumulated_response = ""

            final_text = accumulated_response.replace('*', '').strip()
            self.conversation_history.append({"role": "user", "content": prompt})
            self.conversation_history.append({"role": "assistant", "content": final_text})

            if is_low_end and len(self.conversation_history) > 6:
                self.conversation_history = self.conversation_history[-6:]

            return final_text

        except Exception as ollama_failure:
            return f"Ollama Core Failure: {ollama_failure}"

    def _revive_ollama_service(self):
        """Attempts to cold-start the Ollama service if it is found to be offline."""
        if not shutil.which('ollama'): return False
        
        print("[SYSTEM] Attempting to auto-revive Ollama service...")
        try:
            spawn_flags = subprocess.CREATE_NO_WINDOW if IS_WINDOWS else 0
            subprocess.Popen(["ollama", "serve"], creationflags=spawn_flags, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(3)
            return True
        except Exception as boot_failure:
            print(f"[CRITICAL] Failed to revive Ollama: {boot_failure}")
            return False

    def _generate_static_offline_response(self, prompt):
        """Provides hardcoded responses for common queries when all AI backends are unavailable."""
        query = prompt.lower()
        if 'hello' in query: return "Hello! Systems are operational and ready for your command."
        if 'who are you' in query: return "I am Kailey, your personal intelligence interface."
        if 'time' in query: return f"The current system time is {datetime.datetime.now().strftime('%I:%M %p')}."
        return "I am currently disconnected from my neural cores. Please check your internet or local AI server."

    def _process_via_openai_compatible(self, prompt, config_key):
        """
        Generic handler for OpenAI-compatible chat endpoints (LM Studio, LocalAI, Custom).
        Uses:
          - {config_key}_url
          - {config_key}_key (optional)
          - {config_key}_model
        """
        if not HAS_REQUESTS:
            return "System Error: requests library missing."

        base_url = self.settings.get(f'{config_key}_url', '')
        if not base_url:
            return f"Configuration Error: {config_key}_url is missing."

        api_key = self.settings.get(f'{config_key}_key', '') or ''
        model_id = self.settings.get(f'{config_key}_model', 'local-model')

        timeout_s = 6 if self.settings.get('low_end_mode', False) else 15
        stream_it = False  # keep it simple + low-end friendly

        try:
            endpoint = base_url.rstrip('/') + "/chat/completions"
            headers = {"Content-Type": "application/json"}
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"

            payload = {
                "model": model_id,
                "messages": [
                    {"role": "system", "content": "You are Kailey. Mature female assistant. Concise. No filler words."},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.7,
                "stream": stream_it,
            }

            response = requests.post(endpoint, headers=headers, json=payload, timeout=timeout_s)
            response_json = response.json()

            # Compatible formats vary slightly; handle common one.
            content = response_json.get("choices", [{}])[0].get("message", {}).get("content", "")
            return (content or "").replace('*', '').strip() or "Custom AI returned empty response."
        except Exception as e:
            return f"OpenAI-Compatible Connection Failure: {e}"


# ═══════════════════════════════════════════════════════════════
#  COMMAND PROCESSOR — The Action Engine
# ═══════════════════════════════════════════════════════════════

class AutomatedActionProcessor:
    """
    Translates recognized speech commands into system-level actions.
    Separates logic into web, system, and application domains for better maintainability.
    """
    def __init__(self, system_settings, custom_command_registry, controller=None):
        self.settings = system_settings
        self.commands = custom_command_registry
        self.controller = controller

    def process_trigger(self, raw_input):
        """Identifies and executes the correct handler for a given voice command."""
        normalized_input = raw_input.lower().strip()
        
        # Check for registered custom commands first
        if normalized_input in self.commands:
            command_metadata = self.commands[normalized_input]
            return self._execute_metadata_action(command_metadata, normalized_input), True

        # Process hardcoded/native system commands
        return self._evaluate_native_system_commands(normalized_input)

    def _execute_metadata_action(self, metadata, trigger):
        """Dispatches action based on the command type defined in commands.json."""
        action_type = metadata.get('action')
        target_payload = metadata.get('target', '')

        if action_type == 'open_url':
            open_url_in_app_mode(target_payload)
            return f"Opening website: {target_payload}"

        if action_type == 'open_app':
            return self._launch_application(target_payload)

        if action_type == 'key_combo':
            self._execute_keyboard_shortcut(target_payload)
            return f"Simulating shortcut: {target_payload}"

        if action_type == 'tell_time':
            return f"The current time is {datetime.datetime.now().strftime('%I:%M %p')}."

        if action_type == 'tell_date':
            return f"Today is {datetime.datetime.now().strftime('%A, %B %d, %Y')}."

        if action_type == 'weather':
            return self._get_weather()

        if action_type == 'cpu_status':
            return self._get_system_stats('cpu')

        if action_type == 'memory_status':
            return self._get_system_stats('ram')

        if action_type == 'battery_status':
            return self._get_system_stats('battery')

        if action_type == 'system_info':
            return self._get_system_info()

        if action_type == 'screenshot':
            return self._capture_screen()

        if action_type == 'lock_screen':
            if IS_WINDOWS:
                os.system("rundll32.exe user32.dll,LockWorkStation")
            else:
                os.system("xdg-screensaver lock")
            return "Locking system."

        if action_type == 'shutdown':
            if IS_WINDOWS:
                subprocess.run(["shutdown", "/s", "/t", "0"], shell=True)
            else:
                subprocess.run(["systemctl", "poweroff"])
            return "Shutting down."

        if action_type == 'restart':
            if IS_WINDOWS:
                subprocess.run(["shutdown", "/r", "/t", "0"], shell=True)
            else:
                subprocess.run(["systemctl", "reboot"])
            return "Restarting."

        if action_type == 'sleep':
            if IS_WINDOWS:
                subprocess.run(["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"], shell=True)
            else:
                subprocess.run(["systemctl", "suspend"])
            return "Going to sleep."

        if action_type == 'cancel_shutdown':
            if IS_WINDOWS:
                subprocess.run(["shutdown", "/a"], shell=True)
            return "Shutdown cancelled."

        if action_type == 'stop_listening':
            if self.controller:
                self.controller.deactivate_voice_listening()
            return "Voice listening stopped."

        if action_type == 'volume_up':
            delta = int(target_payload) if str(target_payload).isdigit() else 10
            self._apply_volume_scalar(delta)
            return f"Volume increased by {delta}%."

        if action_type == 'volume_down':
            delta = int(target_payload) if str(target_payload).isdigit() else 10
            self._apply_volume_scalar(-delta)
            return f"Volume decreased by {delta}%."

        if action_type == 'volume_set':
            self._set_volume(int(target_payload) if str(target_payload).isdigit() else 50)
            return f"Volume set to {int(target_payload) if str(target_payload).isdigit() else 50}%."

        if action_type == 'volume_mute':
            self._mute_volume()
            return "Volume muted."

        if action_type == 'brightness_up':
            delta = int(target_payload) if str(target_payload).isdigit() else 10
            self._adjust_brightness(delta)
            return "Brightness increased."

        if action_type == 'brightness_down':
            delta = int(target_payload) if str(target_payload).isdigit() else 10
            self._adjust_brightness(-delta)
            return "Brightness decreased."

        if action_type == 'youtube_search':
            query = target_payload or ""
            open_url_in_app_mode(f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}")
            return f"Searching YouTube for {query}"

        if action_type == 'web_search':
            query = target_payload or ""
            open_url_in_app_mode(f"https://www.google.com/search?q={query.replace(' ', '+')}")
            return f"Searching Google for {query}"

        if action_type == 'type_text':
            text = target_payload or ""
            if HAS_PYAUTOGUI:
                try:
                    pyautogui.typewrite(text, interval=0.05)
                except Exception as e:
                    return f"Failed to type text: {e}"
            return f"Typed: {text}"

        if action_type == 'open_anything':
            target = target_payload or ""
            if target.startswith(('http://', 'https://')):
                open_url_in_app_mode(target)
                return f"Opening {target}"
            return self._launch_application(target)

        if action_type == 'app_launcher':
            app_name = target_payload or ""
            return self._launch_application(app_name)

        if action_type == 'shell':
            cmd = target_payload or ""
            return self._run_shell_command(cmd)

        return f"Executing {action_type} for {trigger}"

    def _evaluate_native_system_commands(self, text):
        """Handles built-in logic for system control and info retrieval."""
        if 'search for' in text:
            query = text.split('search for')[-1].strip()
            open_url_in_app_mode(f"https://www.google.com/search?q={query}")
            return f"Searching the web for {query}", True

        if 'volume' in text:
            return self._adjust_audio_volume(text), True

        if 'time' in text:
            current_time = datetime.datetime.now().strftime("%I:%M %p")
            return f"The current time is {current_time}.", True

        if 'screenshot' in text:
            return self._capture_screen(), True

        if 'weather' in text:
            return self._get_weather(), True

        if 'cpu' in text or 'processor' in text:
            return self._get_system_stats('cpu'), True

        if 'memory' in text or 'ram' in text:
            return self._get_system_stats('ram'), True

        if 'lock' in text or 'lock screen' in text:
            os.system("rundll32.exe user32.dll,LockWorkStation" if IS_WINDOWS else "xdg-screensaver lock")
            return "Locking system.", True

        return "Command not recognized.", False

    def _get_weather(self):
        """Fetches a simplified weather report via wttr.in."""
        if not HAS_REQUESTS: return "System Error: requests library missing."
        try:
            response = requests.get("https://wttr.in/?format=3", timeout=5)
            return response.text.strip() if response.ok else "Weather service temporarily unavailable."
        except Exception:
            return "Could not connect to weather service."

    def _get_system_stats(self, stat_type):
        """Retrieves real-time hardware telemetry."""
        if not HAS_PSUTIL:
            return "System Error: psutil library not installed."
        if stat_type == 'cpu':
            return f"Current CPU usage is at {psutil.cpu_percent(interval=0.5)}%."
        if stat_type == 'ram':
            m = psutil.virtual_memory()
            return f"System memory is {m.percent}% utilized ({m.used//(1024**3)}GB used)."
        if stat_type == 'battery':
            b = psutil.sensors_battery()
            if b is None:
                return "Battery information not available."
            plugged = " (plugged in)" if b.power_plugged else ""
            return f"Battery is at {b.percent}%{plugged}."
        return "Unknown stat request."

    def _launch_application(self, executable_name):
        """Attempts to start an external process safely using shell methods."""
        try:
            if IS_WINDOWS:
                os.startfile(executable_name)
            else:
                subprocess.Popen([executable_name])
            return f"Successfully launched {executable_name}"
        except Exception as launch_failure:
            print(f"[ERROR] Failed to launch application {executable_name}: {launch_failure}")
            return f"Could not launch {executable_name}. Is it installed?"

    def _adjust_audio_volume(self, command_text):
        """Calculates and applies volume changes based on descriptive speech."""
        if 'up' in command_text or 'increase' in command_text:
            self._apply_volume_scalar(10)
            return "Increasing volume."
        if 'down' in command_text or 'decrease' in command_text:
            self._apply_volume_scalar(-10)
            return "Decreasing volume."
        return "Volume adjustment failed."

    def _apply_volume_scalar(self, delta):
        """Low-level interface for OS audio controls via pycaw or pyautogui."""
        if IS_WINDOWS and HAS_VOLUME:
            try:
                devices = AudioUtilities.GetSpeakers()
                interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                volume_handle = cast(interface, POINTER(IAudioEndpointVolume))
                current_level = volume_handle.GetMasterVolumeLevelScalar()
                new_level = max(0.0, min(1.0, current_level + (delta / 100.0)))
                volume_handle.SetMasterVolumeLevelScalar(new_level, None)
            except Exception as com_failure:
                print(f"[WARN] Direct volume control failed, falling back to pyautogui: {com_failure}")
                if HAS_PYAUTOGUI:
                    pyautogui.press('volumeup' if delta > 0 else 'volumedown')
        elif HAS_PYAUTOGUI:
            pyautogui.press('volumeup' if delta > 0 else 'volumedown')

    def _capture_screen(self):
        """Saves a timestamped screenshot to the dedicated capture folder."""
        if not HAS_PYAUTOGUI:
            return "Screenshot functionality requires the PyAutoGUI library."
        
        capture_directory = APP_DIR / "screenshots"
        capture_directory.mkdir(exist_ok=True)
        file_name = f"capture_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        file_path = capture_directory / file_name
        
        try:
            pyautogui.screenshot(str(file_path))
            return f"Screenshot captured and saved to {file_name}"
        except Exception as capture_error:
            return f"Failed to capture screen: {capture_error}"

    def _execute_keyboard_shortcut(self, combo_string):
        """Parses a string like 'ctrl+c' and executes the corresponding key events."""
        if not HAS_PYAUTOGUI:
            return
        keys = [k.strip() for k in combo_string.lower().split('+')]
        try:
            pyautogui.hotkey(*keys)
        except Exception as e:
            return f"Failed to simulate shortcut: {e}"

    def _get_system_info(self):
        if not HAS_PSUTIL:
            return "System monitoring unavailable."
        uname = platform.uname()
        m = psutil.virtual_memory()
        return (f"OS: {uname.system} {uname.release}. "
                f"CPU: {uname.processor}. "
                f"RAM: {m.total//(1024**3)}GB total, {m.percent}% used.")

    def _set_volume(self, level_percent):
        level = max(0, min(100, level_percent)) / 100.0
        if IS_WINDOWS and HAS_VOLUME:
            try:
                devices = AudioUtilities.GetSpeakers()
                interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                volume_handle = cast(interface, POINTER(IAudioEndpointVolume))
                volume_handle.SetMasterVolumeLevelScalar(level, None)
                return
            except Exception as com_failure:
                print(f"[WARN] Direct volume set failed: {com_failure}")
        if HAS_PYAUTOGUI:
            pyautogui.press('volumemute')
            for _ in range(50):
                pyautogui.press('volumeup')
            current = self._get_volume_approx()
            if level < current:
                for _ in range(int((current - level) * 50)):
                    pyautogui.press('volumedown')
            elif level > current:
                for _ in range(int((level - current) * 50)):
                    pyautogui.press('volumeup')

    def _mute_volume(self):
        if IS_WINDOWS and HAS_VOLUME:
            try:
                devices = AudioUtilities.GetSpeakers()
                interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                volume_handle = cast(interface, POINTER(IAudioEndpointVolume))
                volume_handle.SetMute(True, None)
                return
            except Exception as com_failure:
                print(f"[WARN] Direct mute failed: {com_failure}")
        if HAS_PYAUTOGUI:
            pyautogui.press('volumemute')

    def _get_volume_approx(self):
        if IS_WINDOWS and HAS_VOLUME:
            try:
                devices = AudioUtilities.GetSpeakers()
                interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                volume_handle = cast(interface, POINTER(IAudioEndpointVolume))
                return volume_handle.GetMasterVolumeLevelScalar()
            except Exception:
                pass
        return 0.5

    def _adjust_brightness(self, delta):
        delta = max(-50, min(50, delta))
        if HAS_BRIGHTNESS:
            try:
                import screen_brightness_control as sbc
                current = sbc.get_brightness()[0]
                target = max(5, min(100, current + delta))
                sbc.set_brightness(target)
                return
            except Exception as bright_failure:
                print(f"[WARN] Brightness control failed: {bright_failure}")
        if IS_WINDOWS and HAS_PYAUTOGUI:
            pyautogui.hotkey('win', 'fn', 'f5')

    def _run_shell_command(self, command):
        if not command:
            return "No command provided."
        try:
            if IS_WINDOWS:
                subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
            else:
                subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
            return f"Executed: {command}"
        except subprocess.CalledProcessError as e:
            return f"Command failed: {e.stderr or str(e)}"
        except Exception as e:
            return f"Command error: {e}"




# ═══════════════════════════════════════════════════════════════
#  GUI — Kailey HUD
# ═══════════════════════════════════════════════════════════════

class UserInterfaceHUD:
    # ── Cyberpunk Colors ──
    BG='#050510'; BG2='#0a002e'; FG='#a8a8c8'; MUTED='#3a4a6c'
    ACCENT='#ff003c'; ACCENT2='#00f3ff'; ACCENT3='#b400ff'; DANGER='#ff003c'
    # Cyberpunk Terminal Brutalism
    KAILEY='#00f3ff'; KAILEY_DIM='#002a2a'
    BORDER='#ff003c'

    def __init__(self, app):
        self.controller = app
        self.root = tk.Tk()
        self.root.title("Kailey — Voice Command System")
        self.root.geometry("960x650")
        self.root.minsize(800, 550)
        self.root.configure(bg=self.BG)

        self.is_listening = False
        self.arc_angle = 0
        self.is_thinking = False
        self._closing = False
        self._display_text = ""
        self._response_text = ""

        self._build_menu()
        self._build_ui()
        self._start_anims()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        # Event Bus Bindings
        events.on(EventBus.AI_STREAM, self._handle_ai_stream)
        events.on(EventBus.AI_RESPONSE, self._handle_ai_response)
        events.on(EventBus.AI_PROVIDER, self._handle_ai_provider)
        events.on(EventBus.ERROR, lambda data: self.append_to_terminal(f"ERROR: {data}", 'err'))

    def _build_menu(self):
        menubar = tk.Menu(self.root, bg=self.BG2, fg=self.FG, activebackground=self.KAILEY, activeforeground=self.BG)
        
        # Options Menu
        opt_menu = tk.Menu(menubar, tearoff=0, bg=self.BG2, fg=self.FG)
        opt_menu.add_command(label="Detailed Configuration", command=self._open_settings)
        opt_menu.add_command(label="Voice Settings", command=self._open_voice_settings)
        opt_menu.add_separator()
        
        # AI Mode Submenu
        ai_menu = tk.Menu(opt_menu, tearoff=0, bg=self.BG2, fg=self.FG)
        for m in ['offline','gemini','openai','ollama','ollama_cloud','ollama_hybrid','local_ai','custom']:
            ai_menu.add_command(label=f"Switch to {m.replace('_',' ').title()}", 
                               command=lambda mode=m: self._quick_switch_ai(mode))
        opt_menu.add_cascade(label="Quick Switch AI Core", menu=ai_menu)
        
        opt_menu.add_separator()
        opt_menu.add_command(label="Exit System", command=self._on_close)
        
        menubar.add_cascade(label="OPTIONS", menu=opt_menu)
        
        # Tools Menu
        tools_menu = tk.Menu(menubar, tearoff=0, bg=self.BG2, fg=self.FG)
        tools_menu.add_command(label="Refresh Command List", command=self._refresh_cmds)
        tools_menu.add_command(label="Clear Terminal", command=lambda: self.term.config(state='normal') or self.term.delete('1.0', 'end') or self.term.config(state='disabled'))
        menubar.add_cascade(label="TOOLS", menu=tools_menu)
        
        self.root.config(menu=menubar)

    def _quick_switch_ai(self, mode):
        cfg = self.controller.registry.active_settings
        self.mode_lbl.config(text=f"AI: {mode.replace('_',' ').title()}")
        self.append_to_terminal(f"AI Intelligence Core switched to: {mode.upper()}", 'sys')
        self.controller.voice_orchestrator.speak(f"AI systems switched to {mode.replace('_',' ')}")

    def _build_ui(self):
        # ═══ TOP BAR ═══
        top = tk.Frame(self.root, bg=self.BG2, height=46)
        top.pack(fill='x'); top.pack_propagate(False)

        # Kailey logo/name
        tk.Label(top, text="KAILEY", font=('Orbitron',12,'bold'), bg=self.BG2, fg=self.KAILEY).pack(side='left', padx=14)

        self.status_lbl = tk.Label(top, text="STANDBY", font=('Orbitron',8,'bold'), bg=self.BG2, fg=self.MUTED)
        self.status_lbl.pack(side='left', padx=18)

        self.voice_lbl = tk.Label(top, text="Voice: Jenny (US)", font=('Rajdhani',8), bg=self.BG2, fg=self.ACCENT2)
        self.voice_lbl.pack(side='left', padx=10)

        self.mode_lbl = tk.Label(top, text="AI: Offline", font=('Rajdhani',8), bg=self.BG2, fg=self.MUTED)
        self.mode_lbl.pack(side='left', padx=10)

        self.clock_lbl = tk.Label(top, text="", font=('Orbitron',9), bg=self.BG2, fg=self.KAILEY)
        self.clock_lbl.pack(side='right', padx=14)

        # ═══ MAIN 3-COLUMN ═══
        main = tk.Frame(self.root, bg=self.BG)
        main.pack(fill='both', expand=True, padx=4, pady=4)

        # ── LEFT: System + Quick cmds ──
        left = tk.Frame(main, bg=self.BG2, width=195)
        left.pack(side='left', fill='y', padx=(0,3)); left.pack_propagate(False)

        tk.Label(left, text="SYSTEM STATUS", font=('Orbitron',7,'bold'), bg=self.BG2, fg=self.MUTED).pack(pady=(8,3), padx=8, anchor='w')
        self.sys_lbls = {}
        for k in ['CPU','RAM','Disk','Battery','Uptime','Net']:
            f = tk.Frame(left, bg=self.BG, highlightthickness=1, highlightbackground=self.BORDER)
            f.pack(fill='x', padx=6, pady=2)
            tk.Label(f, text=k, font=('Rajdhani',8), bg=self.BG, fg=self.MUTED, width=7, anchor='w').pack(side='left', padx=4, pady=2)
            l = tk.Label(f, text="--", font=('Orbitron',7), bg=self.BG, fg=self.ACCENT3, anchor='e')
            l.pack(side='right', padx=4, pady=2)
            self.sys_lbls[k] = l

        tk.Frame(left, bg=self.BORDER, height=1).pack(fill='x', padx=8, pady=6)
        tk.Label(left, text="QUICK COMMANDS", font=('Orbitron',7,'bold'), bg=self.BG2, fg=self.MUTED).pack(pady=(0,3), padx=8, anchor='w')
        for cmd in ['youtube','google','time','screenshot','volume up','volume down','lock','cpu','memory','weather']:
            tk.Button(left, text=f"  {cmd}", font=('Rajdhani',8), bg=self.BG, fg=self.FG, anchor='w', relief='flat', activebackground='#152240', activeforeground=self.KAILEY, cursor='hand2', bd=0, command=lambda c=cmd: self.controller.process_text_command(c)).pack(fill='x', padx=6, pady=1)

        # ── CENTER: Arc Reactor ──
        center = tk.Frame(main, bg=self.BG)
        center.pack(side='left', fill='both', expand=True, padx=3)
        self.canvas = tk.Canvas(center, bg=self.BG, highlightthickness=0)
        self.canvas.pack(fill='both', expand=True)

        # ── RIGHT: Command Editor ──
        right = tk.Frame(main, bg=self.BG2, width=205)
        right.pack(side='right', fill='y', padx=(3,0)); right.pack_propagate(False)

        tk.Label(right, text="COMMAND CENTER", font=('Orbitron',7,'bold'), bg=self.BG2, fg=self.MUTED).pack(pady=(8,3), padx=8, anchor='w')
        form = tk.Frame(right, bg=self.BG, highlightthickness=1, highlightbackground=self.BORDER)
        form.pack(fill='x', padx=6, pady=4)
        tk.Label(form, text="Add Command", font=('Orbitron',7,'bold'), bg=self.BG, fg=self.KAILEY).pack(pady=(5,2))
        self.trig_e = self._entry(form, "Trigger Word:")
        self.act_var = tk.StringVar(value='open_url')
        tk.Label(form, text="Action:", font=('Rajdhani',7), bg=self.BG, fg=self.MUTED).pack(anchor='w', padx=6)
        ttk.Combobox(form, textvariable=self.act_var, width=17, values=[
            'open_url','open_app','key_combo','youtube_search','web_search','shell',
            'type_text','tell_time','tell_date','weather','cpu_status','memory_status',
            'battery_status','system_info','screenshot','lock_screen','shutdown','restart',
            'sleep','cancel_shutdown','stop_listening','volume_up','volume_down',
            'volume_set','volume_mute','brightness_up','brightness_down'
        ], state='readonly', font=('Rajdhani',8)).pack(padx=6, pady=2)
        self.tgt_e = self._entry(form, "Target/URL:")
        self.desc_e = self._entry(form, "Description:")
        tk.Button(form, text="ADD COMMAND", font=('Orbitron',7,'bold'), bg='#0a2a3d', fg=self.KAILEY, relief='flat', cursor='hand2', command=self._add_cmd).pack(fill='x', padx=6, pady=5)

        tk.Label(right, text="SAVED COMMANDS", font=('Orbitron',7,'bold'), bg=self.BG2, fg=self.MUTED).pack(pady=(6,2), padx=8, anchor='w')
        lf = tk.Frame(right, bg=self.BG2)
        lf.pack(fill='both', expand=True, padx=6, pady=(0,3))
        self.cmd_lb = tk.Listbox(lf, bg=self.BG, fg=self.KAILEY, font=('Consolas',7), selectbackground='#152240', selectforeground=self.ACCENT2, relief='flat', highlightthickness=1, highlightbackground=self.BORDER, activestyle='none')
        self.cmd_lb.pack(fill='both', expand=True, side='left')
        sb = tk.Scrollbar(lf, command=self.cmd_lb.yview, bg=self.BG2, troughcolor=self.BG)
        sb.pack(side='right', fill='y'); self.cmd_lb.config(yscrollcommand=sb.set)
        tk.Button(right, text="DELETE SELECTED", font=('Orbitron',7,'bold'), bg='#2d0a14', fg=self.DANGER, relief='flat', cursor='hand2', command=self._del_cmd).pack(fill='x', padx=6, pady=(0,6))
        self._refresh_cmds()

        # ═══ TERMINAL ═══
        tf = tk.Frame(self.root, bg=self.BG2, height=120)
        tf.pack(fill='x', padx=4, pady=(0,3)); tf.pack_propagate(False)
        tk.Label(tf, text="TERMINAL", font=('Orbitron',7,'bold'), bg=self.BG2, fg=self.MUTED).pack(pady=(3,0), padx=8, anchor='w')
        self.term = tk.Text(tf, bg='#080e1c', fg=self.ACCENT3, font=('Consolas',9), height=5, relief='flat', insertbackground=self.ACCENT, wrap='word', state='disabled', highlightthickness=0)
        self.term.pack(fill='both', expand=True, padx=6, pady=(2,5))
        for tag, color in [('cmd',self.KAILEY),('res',self.ACCENT2),('err',self.DANGER),('sys',self.ACCENT3),('muted',self.MUTED)]:
            self.term.tag_configure(tag, foreground=color)

        # ═══ BOTTOM BAR ═══
        bot = tk.Frame(self.root, bg=self.BG2, height=52)
        bot.pack(fill='x', padx=4, pady=(0,4)); bot.pack_propagate(False)
        bf = tk.Frame(bot, bg=self.BG2); bf.pack(expand=True)

        self.listen_btn = tk.Button(bf, text="  START LISTENING", font=('Orbitron',9,'bold'), bg='#0a2a3d', fg=self.KAILEY, relief='flat', cursor='hand2', command=self._toggle_listen)
        self.listen_btn.pack(side='left', padx=5, pady=8)
        tk.Button(bf, text="  ONCE", font=('Orbitron',8,'bold'), bg=self.BG, fg=self.FG, relief='flat', cursor='hand2', command=self.controller.listen_once_async).pack(side='left', padx=5, pady=8)
        self.text_e = tk.Entry(bf, bg=self.BG, fg=self.FG, font=('Rajdhani',10), insertbackground=self.KAILEY, width=22, relief='flat', highlightthickness=1, highlightbackground=self.BORDER, highlightcolor=self.KAILEY)
        self.text_e.pack(side='left', padx=5, pady=8); self.text_e.bind('<Return>', lambda e: self._send())
        tk.Button(bf, text="SEND", font=('Orbitron',8,'bold'), bg=self.BG, fg=self.ACCENT2, relief='flat', cursor='hand2', command=self._send).pack(side='left', padx=5, pady=8)
        tk.Button(bf, text="  VOICE", font=('Orbitron',8,'bold'), bg=self.BG, fg=self.ACCENT2, relief='flat', cursor='hand2', command=self._open_voice_settings).pack(side='right', padx=5, pady=8)
        tk.Button(bf, text="  OPTIONS", font=('Orbitron',8,'bold'), bg=self.BG, fg=self.FG, relief='flat', cursor='hand2', command=self._open_settings).pack(side='right', padx=5, pady=8)

        # Boot messages
        self.append_to_terminal("Kailey Voice Command System Initialized", 'sys')
        cfg = self.controller.registry.active_settings
        self.append_to_terminal(f"Speech Recognition: {'Available' if HAS_SR else 'NOT INSTALLED'}", 'sys' if HAS_SR else 'err')
        self.append_to_terminal(f"Edge-TTS (Natural Voice): {'Available' if HAS_EDGE_TTS else 'pip install edge-tts'}", 'sys' if HAS_EDGE_TTS else 'muted')
        self.append_to_terminal(f"Offline Vosk: {'Available' if HAS_VOSK else 'Not installed'}", 'sys' if HAS_VOSK else 'muted')
        self.append_to_terminal("Say 'Kailey' or click START LISTENING.", 'res')

    def _entry(self, parent, label):
        tk.Label(parent, text=label, font=('Rajdhani',7), bg=self.BG, fg=self.MUTED).pack(anchor='w', padx=6)
        e = tk.Entry(parent, bg='#080e1c', fg=self.FG, font=('Rajdhani',8), insertbackground=self.KAILEY, relief='flat', highlightthickness=1, highlightbackground=self.BORDER, highlightcolor=self.KAILEY)
        e.pack(fill='x', padx=6, pady=2)
        return e

    # ── Animations ──
    def _start_anims(self):
        self._update_clock()
        self._animate_arc()
        self._update_stats()

    def _update_clock(self):
        if self._closing: return
        self.clock_lbl.config(text=datetime.datetime.now().strftime("%H:%M:%S"))
        self.root.after(1000, self._update_clock)

    def _animate_arc(self):
        if self._closing: return
        is_low_end = self.controller.registry.active_settings.get('low_end_mode', False)

        # Skip expensive redraws when idle on low-end
        if is_low_end and not self.is_listening and not self.is_thinking:
            self.root.after(500, self._animate_arc)
            return

        self.canvas.delete('arc')
        w, h = self.canvas.winfo_width(), self.canvas.winfo_height()
        if w < 20: self.root.after(100, self._animate_arc); return
        cx, cy = w//2, h//2 - 20
        br = min(w, h) // 4

        # Slow rotation on low-end
        step = 1 if not is_low_end else 1
        self.arc_angle = (self.arc_angle + step) % 360
        ac = self.KAILEY if not self.is_listening else self.DANGER
        dim = self.KAILEY_DIM if not self.is_listening else '#4d0022'

        if is_low_end:
            # Simple spinner for low-end
            for i in range(4):
                s = self.arc_angle + i*90; r = br
                self.canvas.create_arc(cx-r,cy-r,cx+r,cy+r, start=s, extent=20, style='arc', outline=dim, width=2, tags='arc')
            r = br - 15
            self.canvas.create_oval(cx-r,cy-r,cx+r,cy+r, outline=ac, width=1, fill='', tags='arc')
        else:
            # Fancy animation for powerful devices
            for i in range(6):
                s = self.arc_angle + i*60; r = br + 10
                self.canvas.create_arc(cx-r,cy-r,cx+r,cy+r, start=s, extent=40, style='arc', outline=dim, width=3, tags='arc')
            for i in range(8):
                s = -self.arc_angle*1.5 + i*45; r = br - 15
                self.canvas.create_arc(cx-r,cy-r,cx+r,cy+r, start=s, extent=30, style='arc', outline='#002a22', width=2, tags='arc')
            r = br - 40
            self.canvas.create_oval(cx-r,cy-r,cx+r,cy+r, outline=ac, width=2, fill='', tags='arc')
            r2 = r - 8
            self.canvas.create_oval(cx-r2,cy-r2,cx+r2,cy+r2, outline='', fill=('#002a22' if not self.is_listening else '#331122'), tags='arc')
            for i in range(12):
                a = math.radians(self.arc_angle + i*30)
                rx, ry = cx + (br+10)*math.cos(a), cy - (br+10)*math.sin(a)
                dr = 3 if i%3==0 else 1.5
                self.canvas.create_oval(rx-dr,ry-dr,rx+dr,ry+dr, fill=(ac if i%3==0 else self.MUTED), outline='', tags='arc')

        if self.is_thinking:
            st = "THINKING..."
            sc = self.ACCENT3
        else:
            st = "LISTENING..." if self.is_listening else "STANDBY"
            sc = self.DANGER if self.is_listening else self.MUTED

        self.canvas.create_text(cx, cy-8, text=st, font=('Orbitron',10,'bold'), fill=sc, tags='arc')
        self.canvas.create_text(cx, cy+12, text="KAILEY", font=('Orbitron',7,'bold'), fill=self.KAILEY_DIM, tags='arc')

        if not is_low_end:
            if self._display_text:
                y_pos = cy + br + 25
                self.canvas.create_text(cx, y_pos, text=self._display_text, font=('Rajdhani',11,'bold'), fill=self.KAILEY, tags='arc', width=w-80)
            if self._response_text:
                y_pos = cy + br + 55 if not self._display_text else cy + br + 65
                self.canvas.create_text(cx, y_pos, text=self._response_text, font=('Rajdhani',10,'italic'), fill=self.ACCENT2, tags='arc', width=w-80)

        delay = 100 if is_low_end else 33
        self.root.after(delay, self._animate_arc)

    def _update_stats(self):
        if self._closing: return
        is_low_end = self.controller.registry.active_settings.get('low_end_mode', False)
        if HAS_PSUTIL:
            try:
                c=psutil.cpu_percent(interval=0)
                m=psutil.virtual_memory()
                up=time.time()-psutil.boot_time()
                self.sys_lbls['CPU'].config(text=f"{c}%", fg=self.ACCENT3 if c<50 else self.ACCENT2 if c<80 else self.DANGER)
                self.sys_lbls['RAM'].config(text=f"{m.percent}%", fg=self.ACCENT3 if m.percent<60 else self.ACCENT2 if m.percent<85 else self.DANGER)
                self.sys_lbls['Uptime'].config(text=f"{int(up//3600)}h {int((up%3600)//60)}m")
                if not is_low_end:
                    try:
                        d=psutil.disk_usage('/')
                        self.sys_lbls['Disk'].config(text=f"{d.percent}%")
                    except: pass
                    try:
                        b=psutil.sensors_battery()
                        if b: self.sys_lbls['Battery'].config(text=f"{b.percent}%")
                        else: self.sys_lbls['Battery'].config(text="N/A")
                    except: pass
                    try:
                        import socket; socket.create_connection(("8.8.8.8",53), timeout=1)
                        self.sys_lbls['Net'].config(text="Online", fg=self.ACCENT3)
                    except: self.sys_lbls['Net'].config(text="Offline", fg=self.DANGER)
            except: pass
        delay = 8000 if is_low_end else 3000
        self.root.after(delay, self._update_stats)

    def _handle_ai_stream(self, data):
        """Update the UI with streaming words instantly."""
        full_text = data.get('full', '')
        self._response_text = full_text
        if self.controller.registry.active_settings.get('low_end_mode', False):
            return  # Skip streaming updates on low-end to save CPU
        try:
            self.root.after(0, self._animate_arc)
        except RuntimeError:
            pass

    def _handle_ai_provider(self, data):
        """Show (and optionally speak) which AI provider is currently being used."""
        provider = (data or {}).get('provider', 'AI')
        model = (data or {}).get('model', '')
        line = f"AI Provider: {provider}{f' ({model})' if model else ''}"
        self.append_to_terminal(line, 'sys')
        try:
            self.controller.voice_orchestrator.speak(f"Using {provider}" + (f" {model}" if model else "."))
        except Exception:
            pass

    def _handle_ai_response(self, data):
        """Final AI response cleanup."""
        full_text = data.get('response', '')
        self._response_text = full_text
        try:
            self.root.after(0, self.append_to_terminal, full_text, 'res')
        except RuntimeError:
            self.append_to_terminal(full_text, 'res')

    def append_to_terminal(self, text, tag='sys'):
        try:
            ts = datetime.datetime.now().strftime("%H:%M:%S")
            self.term.config(state='normal')
            self.term.insert('end', f"[{ts}] ", 'muted')
            self.term.insert('end', f"{text}\n", tag)
            self.term.see('end')
            self.term.config(state='disabled')
        except RuntimeError:
            pass

    def show_recognized(self, t):
        self._display_text = t
        try:
            self.append_to_terminal(f'Voice: "{t}"', 'cmd')
        except RuntimeError:
            pass

    def show_response(self, t):
        self._response_text = t
        try:
            self.append_to_terminal(f'Kailey: {t}', 'res')
        except RuntimeError:
            pass

    def update_listening_state(self, v):
        try:
            self.is_listening = v
            if v:
                self.listen_btn.config(text="  STOP LISTENING", bg='#2d0a14', fg=self.DANGER)
                self.status_lbl.config(text="LISTENING", fg=self.DANGER)
            else:
                self.listen_btn.config(text="  START LISTENING", bg='#0a2a3d', fg=self.KAILEY)
                self.status_lbl.config(text="STANDBY", fg=self.KAILEY)
        except RuntimeError:
            pass

    def _toggle_listen(self):
        self.controller.stop_listening() if self.is_listening else self.controller.start_listening()

    def _send(self):
        t = self.text_e.get().strip()
        if t: self.text_e.delete(0,'end'); self.controller.process_text_command(t)

    def _add_cmd(self):
        tr = self.trig_e.get().strip().lower()
        ac = self.act_var.get(); tg = self.tgt_e.get().strip(); de = self.desc_e.get().strip()
        if not tr: messagebox.showwarning("Missing","Enter trigger word"); return
        if not tg and ac not in ('volume_up','volume_down','brightness_up','brightness_down','screenshot','lock_screen'): messagebox.showwarning("Missing","Enter target"); return
        self.controller.registry.register_new_command(tr, ac, tg, de)
        self.append_to_terminal(f"Command added: '{tr}' -> {ac}({tg})", 'sys')
        self.trig_e.delete(0,'end'); self.tgt_e.delete(0,'end'); self.desc_e.delete(0,'end')
        self._refresh_cmds()

    def _del_cmd(self):
        sel = self.cmd_lb.curselection()
        if not sel: return
        tr = self.cmd_lb.get(sel[0]).split(' ->')[0].strip()
        if messagebox.askyesno("Delete", f"Delete '{tr}'?"):
            self.controller.registry.unregister_command(tr)
            self.append_to_terminal(f"Deleted: '{tr}'", 'err')
            self._refresh_cmds()

    def _refresh_cmds(self):
        self.cmd_lb.delete(0,'end')
        for tr, d in sorted(self.controller.registry.action_commands.items()):
            self.cmd_lb.insert('end', f"{tr} -> {d.get('action','')}")

    # ═══════════════════════════════════════════════════════════
    #  VOICE SETTINGS WINDOW
    # ═══════════════════════════════════════════════════════════

    def _open_voice_settings(self):
        win = tk.Toplevel(self.root)
        win.title("Kailey — Voice Settings")
        win.geometry("580x700")
        win.configure(bg=self.BG)
        win.transient(self.root)
        win.grab_set()

        tk.Label(win, text="VOICE CONFIGURATION", font=('Orbitron',12,'bold'), bg=self.BG, fg=self.KAILEY).pack(pady=(12,4))
        tk.Label(win, text="Customize how Kailey sounds", font=('Rajdhani',9), bg=self.BG, fg=self.MUTED).pack(pady=(0,8))

        canvas = tk.Canvas(win, bg=self.BG, highlightthickness=0)
        scrollbar = tk.Scrollbar(win, orient="vertical", command=canvas.yview)
        container = tk.Frame(canvas, bg=self.BG)
        container.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0,0), window=container, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True, padx=16)
        scrollbar.pack(side="right", fill="y")

        # Bind mousewheel
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        cfg = self.controller.registry.active_settings

        # ── Voice Engine Selection ──
        self._section(container, "VOICE ENGINE")
        engine_var = tk.StringVar(value=cfg.get('voice_engine','edge_tts'))
        ef = tk.Frame(container, bg=self.BG)
        ef.pack(fill='x', pady=4)
        for val, label in [('edge_tts','Edge-TTS (Natural Neural Voice — Online)'),('pyttsx3','pyttsx3 (System Voice — Offline)')]:
            tk.Radiobutton(ef, text=label, variable=engine_var, value=val,
                bg=self.BG, fg=self.FG, selectcolor=self.BG2, activebackground=self.BG,
                activeforeground=self.KAILEY, font=('Rajdhani',9), indicatoron=True).pack(anchor='w', padx=8, pady=2)

        # ── Edge-TTS Voice Selection ──
        self._section(container, "EDGE-TTS VOICE (Natural Neural Voices)")
        edge_var = tk.StringVar(value=cfg.get('edge_voice_id','en-US-JennyNeural'))
        edge_frame = tk.Frame(container, bg=self.BG)
        edge_frame.pack(fill='x', pady=4)

        for v in EDGE_VOICE_LIST:
            prefix = "★ " if "Best Kailey" in v['name'] or "British Kailey" in v['name'] or "Warm" in v['name'] else "  "
            tk.Radiobutton(edge_frame, text=f"{prefix}{v['name']}", variable=edge_var, value=v['id'],
                bg=self.BG, fg=(self.ACCENT2 if prefix.strip()=="★" else self.FG),
                selectcolor=self.BG2, activebackground=self.BG, activeforeground=self.KAILEY,
                font=('Rajdhani',9), indicatoron=True).pack(anchor='w', padx=16, pady=0)

        # ── Voice Fine-Tuning ──
        self._section(container, "VOICE FINE-TUNING")
        tune_frame = tk.Frame(container, bg=self.BG)
        tune_frame.pack(fill='x', pady=4)

        rate_var = tk.StringVar(value=cfg.get('edge_voice_rate','-5%'))
        pitch_var = tk.StringVar(value=cfg.get('edge_voice_pitch','+1Hz'))

        tk.Label(tune_frame, text="Speaking Rate:", font=('Rajdhani',9), bg=self.BG, fg=self.FG).pack(anchor='w', padx=8)
        rate_info = tk.Frame(tune_frame, bg=self.BG)
        rate_info.pack(fill='x', padx=8)
        for val, label in [('-20%','Very Slow'),('-10%','Slow'),('-5%','Slightly Slow (Natural)'),
                           ('+0%','Normal'),('+10%','Fast'),('+20%','Very Fast')]:
            tk.Radiobutton(rate_info, text=label, variable=rate_var, value=val,
                bg=self.BG, fg=self.FG, selectcolor=self.BG2, activebackground=self.BG,
                activeforeground=self.KAILEY, font=('Rajdhani',8), indicatoron=True).pack(anchor='w', padx=8)

        tk.Label(tune_frame, text="Voice Pitch:", font=('Rajdhani',9), bg=self.BG, fg=self.FG).pack(anchor='w', padx=8, pady=(8,0))
        pitch_info = tk.Frame(tune_frame, bg=self.BG)
        pitch_info.pack(fill='x', padx=8)
        for val, label in [('-5Hz','Much Deeper'),('-2Hz','Deeper'),
                           ('+0Hz','Normal'),('+1Hz','Slightly Higher (Kailey default)'),('+2Hz','Higher'),('+5Hz','Much Higher')]:
            tk.Radiobutton(pitch_info, text=label, variable=pitch_var, value=val,
                bg=self.BG, fg=self.FG, selectcolor=self.BG2, activebackground=self.BG,
                activeforeground=self.KAILEY, font=('Rajdhani',8), indicatoron=True).pack(anchor='w', padx=8)

        # ── pyttsx3 Settings ──
        self._section(container, "PYTTSX3 OFFLINE VOICE SETTINGS")
        py_frame = tk.Frame(container, bg=self.BG)
        py_frame.pack(fill='x', pady=4)

        pyttsx_rate_var = tk.IntVar(value=cfg.get('pyttsx3_rate',175))
        pyttsx_vol_var = tk.DoubleVar(value=cfg.get('pyttsx3_volume',1.0))
        pyttsx_voice_var = tk.IntVar(value=cfg.get('pyttsx3_voice_index',0))

        tk.Label(py_frame, text="Speech Rate (words/min):", font=('Rajdhani',9), bg=self.BG, fg=self.FG).pack(anchor='w', padx=8)
        tk.Scale(py_frame, from_=100, to=300, orient='horizontal', variable=pyttsx_rate_var,
                bg=self.BG, fg=self.KAILEY, troughcolor=self.BG2, highlightthickness=0, font=('Rajdhani',8)).pack(fill='x', padx=8)
        tk.Label(py_frame, text="Volume:", font=('Rajdhani',9), bg=self.BG, fg=self.FG).pack(anchor='w', padx=8)
        tk.Scale(py_frame, from_=0.0, to=1.0, resolution=0.1, orient='horizontal', variable=pyttsx_vol_var,
                bg=self.BG, fg=self.KAILEY, troughcolor=self.BG2, highlightthickness=0, font=('Rajdhani',8)).pack(fill='x', padx=8)

        pyttsx_voices = self.controller.voice_orchestrator.get_pyttsx3_voices()
        if pyttsx_voices:
            tk.Label(py_frame, text="System Voice:", font=('Rajdhani',9), bg=self.BG, fg=self.FG).pack(anchor='w', padx=8, pady=(4,0))
            for v in pyttsx_voices:
                tk.Radiobutton(py_frame, text=v['name'][:50], variable=pyttsx_voice_var, value=v['index'],
                    bg=self.BG, fg=self.FG, selectcolor=self.BG2, activebackground=self.BG,
                    activeforeground=self.KAILEY, font=('Rajdhani',8), indicatoron=True).pack(anchor='w', padx=16)

        # ── Custom Greeting Sound ──
        self._section(container, "CUSTOM GREETING SOUND")
        greet_frame = tk.Frame(container, bg=self.BG)
        greet_frame.pack(fill='x', pady=4)

        greet_file_var = tk.StringVar(value=cfg.get('custom_greeting_file',''))
        greet_play_var = tk.BooleanVar(value=cfg.get('play_greeting_sound',True))

        tk.Label(greet_frame, text="Play a custom sound when Kailey activates:", font=('Rajdhani',9), bg=self.BG, fg=self.FG).pack(anchor='w', padx=8)
        gf_entry = tk.Entry(greet_frame, textvariable=greet_file_var, bg='#080e1c', fg=self.FG, font=('Rajdhani',8), insertbackground=self.KAILEY, relief='flat', highlightthickness=1, highlightbackground=self.BORDER, width=35)
        gf_entry.pack(fill='x', padx=8, pady=2)
        tk.Label(greet_frame, text="Supports: .mp3, .wav, .ogg", font=('Rajdhani',7), bg=self.BG, fg=self.MUTED).pack(anchor='w', padx=8)

        btn_frame = tk.Frame(greet_frame, bg=self.BG)
        btn_frame.pack(fill='x', padx=8, pady=4)

        def browse_greet():
            fp = filedialog.askopenfilename(filetypes=[("Audio","*.mp3 *.wav *.ogg"),("All","*.*")])
            if fp: greet_file_var.set(fp)

        def record_greeting():
            if not HAS_SR:
                messagebox.showerror("Error", "SpeechRecognition not installed"); return
            messagebox.showinfo("Record", "Click OK, then speak your greeting.\nYou have 5 seconds.")
            try:
                r = sr.Recognizer()
                with sr.Microphone() as source:
                    r.adjust_for_ambient_noise(source, duration=0.5)
                    audio = r.listen(source, timeout=5, phrase_time_limit=5)
                filepath = str(GREETING_DIR / "custom_greeting.wav")
                with open(filepath, 'wb') as f:
                    f.write(audio.get_wav_data())
                greet_file_var.set(filepath)
                messagebox.showinfo("Done", f"Greeting saved to:\n{filepath}")
            except Exception as e:
                messagebox.showerror("Error", f"Recording failed: {e}")

        def test_greet():
            fp = greet_file_var.get()
            if fp and os.path.exists(fp):
                self.controller.voice_orchestrator._play_audio_file(fp)
            else:
                self.controller.voice_orchestrator.speak("Custom greeting not set yet.")

        tk.Button(btn_frame, text="Browse", font=('Rajdhani',8,'bold'), bg=self.BG2, fg=self.KAILEY, relief='flat', cursor='hand2', command=browse_greet).pack(side='left', padx=2)
        tk.Button(btn_frame, text="Record", font=('Rajdhani',8,'bold'), bg=self.BG2, fg=self.ACCENT2, relief='flat', cursor='hand2', command=record_greeting).pack(side='left', padx=2)
        tk.Button(btn_frame, text="Test", font=('Rajdhani',8,'bold'), bg=self.BG2, fg=self.ACCENT3, relief='flat', cursor='hand2', command=test_greet).pack(side='left', padx=2)

        tk.Checkbutton(greet_frame, text="Play greeting sound on activation", variable=greet_play_var,
            bg=self.BG, fg=self.FG, selectcolor=self.BG2, activebackground=self.BG,
            activeforeground=self.KAILEY, font=('Rajdhani',9)).pack(anchor='w', padx=8)

        # ── Test Voice ──
        self._section(container, "TEST VOICE")
        def test_voice():
            cfg['voice_engine'] = engine_var.get()
            cfg['edge_voice_id'] = edge_var.get()
            cfg['edge_voice_rate'] = rate_var.get()
            cfg['edge_voice_pitch'] = pitch_var.get()
            test_text = random.choice([
                "Hey there! I'm Kailey, your personal assistant.",
                "Good to see you! All systems are online and ready.",
                "Hello! Whatever you need, I'm here to help.",
                "Hi! Kailey online and ready for your command.",
                "Hey! I've got everything under control here."
            ])
            self.controller.voice_orchestrator.speak(test_text)

        tk.Button(container, text="  TEST CURRENT VOICE SETTINGS", font=('Orbitron',9,'bold'),
                  bg='#0a2a3d', fg=self.KAILEY, relief='flat', cursor='hand2', command=test_voice).pack(fill='x', padx=8, pady=8)

        def save_voice():
            cfg['voice_engine'] = engine_var.get()
            cfg['edge_voice_id'] = edge_var.get()
            cfg['edge_voice_rate'] = rate_var.get()
            cfg['edge_voice_pitch'] = pitch_var.get()
            cfg['pyttsx3_rate'] = pyttsx_rate_var.get()
            cfg['pyttsx3_volume'] = pyttsx_vol_var.get()
            cfg['pyttsx3_voice_index'] = pyttsx_voice_var.get()
            cfg['custom_greeting_file'] = greet_file_var.get()
            cfg['play_greeting_sound'] = greet_play_var.get()
            self.controller.registry.persist_application_settings()
            self.controller.voice_orchestrator = VoiceSynthesisOrchestrator(cfg)
            vid = cfg.get('edge_voice_id','')
            vname = next((v['name'] for v in EDGE_VOICE_LIST if v['id']==vid), vid)
            self.voice_lbl.config(text=f"Voice: {vname}")
            self.append_to_terminal(f"Voice settings saved: {vname}", 'sys')
            canvas.unbind_all("<MouseWheel>")
            win.destroy()

        tk.Button(container, text="  SAVE VOICE SETTINGS", font=('Orbitron',9,'bold'),
                  bg='#0a3d2a', fg=self.ACCENT3, relief='flat', cursor='hand2', command=save_voice).pack(fill='x', padx=8, pady=4)

    def _section(self, parent, title):
        tk.Frame(parent, bg=self.KAILEY, height=1).pack(fill='x', padx=4, pady=(12,0))
        tk.Label(parent, text=title, font=('Orbitron',8,'bold'), bg=self.BG, fg=self.KAILEY).pack(anchor='w', padx=4, pady=(4,2))

    # ═══════════════════════════════════════════════════════════
    #  SETTINGS WINDOW
    # ═══════════════════════════════════════════════════════════

    def _open_settings(self):
        win = tk.Toplevel(self.root)
        win.title("Kailey — Detailed Configuration")
        win.geometry("640x800")
        win.configure(bg=self.BG)
        win.transient(self.root)
        win.grab_set()

        # Header
        header = tk.Frame(win, bg=self.BG2, height=60)
        header.pack(fill='x')
        header.pack_propagate(False)
        tk.Label(header, text="DETAILED OPTION MENU", font=('Orbitron',14,'bold'), bg=self.BG2, fg=self.KAILEY).pack(pady=10)

        # Scrollable area
        canvas = tk.Canvas(win, bg=self.BG, highlightthickness=0)
        scrollbar = tk.Scrollbar(win, orient="vertical", command=canvas.yview)
        container = tk.Frame(canvas, bg=self.BG)
        container.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0,0), window=container, anchor="nw", width=620)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        scrollbar.pack(side="right", fill="y")

        cfg = self.controller.registry.active_settings
        vs = {}

        def create_card(parent, title, icon="◈"):
            frame = tk.Frame(parent, bg=self.BG2, highlightthickness=1, highlightbackground=self.BORDER)
            frame.pack(fill='x', padx=5, pady=8)
            tk.Label(frame, text=f"{icon} {title}", font=('Orbitron',9,'bold'), bg=self.BG2, fg=self.KAILEY).pack(anchor='w', padx=10, pady=5)
            inner = tk.Frame(frame, bg=self.BG2)
            inner.pack(fill='x', padx=10, pady=(0,10))
            return inner

        # ── GENERAL ──
        gen = create_card(container, "GENERAL SYSTEM SETTINGS", "⚙")
        
        def add_row(parent, label, var, is_bool=False, is_combo=False, vals=None):
            f = tk.Frame(parent, bg=self.BG2)
            f.pack(fill='x', pady=4)
            tk.Label(f, text=label, font=('Rajdhani',10), bg=self.BG2, fg=self.MUTED, width=15, anchor='w').pack(side='left')
            if is_bool:
                tk.Checkbutton(f, variable=var, bg=self.BG2, selectcolor=self.BG, activebackground=self.BG2).pack(side='left')
            elif is_combo:
                ttk.Combobox(f, textvariable=var, values=vals, state='readonly', font=('Rajdhani',9), width=25).pack(side='left', padx=5)
            else:
                tk.Entry(f, textvariable=var, bg='#080e1c', fg=self.FG, font=('Rajdhani',10), insertbackground=self.KAILEY, relief='flat', highlightthickness=1, highlightbackground=self.BORDER, width=30).pack(side='left', padx=5)

        vs['wake_word'] = tk.StringVar(value=cfg.get('wake_word','kailey'))
        add_row(gen, "Wake Word:", vs['wake_word'])
        
        recognition_mode_map = {
            'auto': 'Auto (Online -> Vosk)',
            'online': 'Online (Google)',
            'offline': 'Offline (Vosk)',
            'local_whisper': 'Local Whisper (Slow/High Acc)',
            'groq_whisper': 'Groq Whisper (Fast/Cloud)',
            'openai_whisper': 'OpenAI Whisper (Paid/Cloud)',
        }
        recognition_mode_reverse_map = {label: value for value, label in recognition_mode_map.items()}
        current_mode = cfg.get('recognition_mode', 'auto')
        vs['recognition_mode'] = tk.StringVar(value=recognition_mode_map.get(current_mode, current_mode))
        add_row(gen, "Voice Input:", vs['recognition_mode'], is_combo=True, vals=list(recognition_mode_map.values()))
        
        vs['continuous_listen'] = tk.BooleanVar(value=cfg.get('continuous_listen',False))
        add_row(gen, "Always Listen:", vs['continuous_listen'], is_bool=True)
        
        vs['start_listening_on_boot'] = tk.BooleanVar(value=cfg.get('start_listening_on_boot',True))
        add_row(gen, "Auto-Start:", vs['start_listening_on_boot'], is_bool=True)

        # ── AI BRAIN SELECTION ──
        brain = create_card(container, "AI INTELLIGENCE CORE", "🧠")
        vs['ai_mode'] = tk.StringVar(value=cfg.get('ai_mode','offline'))
        modes = ['offline','gemini','openai','ollama','ollama_cloud','ollama_hybrid','local_ai','custom']
        add_row(brain, "Active Core:", vs['ai_mode'], is_combo=True, vals=modes)

        ai_field_hint = tk.Label(
            brain,
            text="Editing fields: (select ai_mode above)",
            font=('Rajdhani',8,'italic'),
            bg=self.BG2, fg=self.MUTED
        )
        ai_field_hint.pack(anchor='w', pady=(5, 2))

        def _compute_ai_field_hint(mode_value: str):
            m = (mode_value or '').lower().strip()
            if m == 'gemini':
                return "Editing fields: GEMINI card (gemini_api_key + gemini_model)"
            if m == 'openai':
                return "Editing fields: OPENAI card (openai_api_key + openai_model)"
            if m == 'ollama':
                return "Editing fields: OLLAMA (Local) card (ollama_url + ollama_model)"
            if m == 'ollama_cloud' or m == 'ollama_hybrid':
                return "Editing fields: OLLAMA CLOUD card (ollama_cloud_url + ollama_cloud_model + ollama_cloud_key)"
            if m == 'local_ai':
                return "Editing fields: LOCAL AI card (local_ai_url + local_ai_model + local_ai_key)"
            if m == 'custom':
                return "Editing fields: CUSTOM ENDPOINT card (custom_ai_url + custom_ai_model + custom_ai_key)"
            return "Editing fields: No AI provider settings required (offline mode / fallback)"

        # initialize hint based on current config
        ai_field_hint.config(text=_compute_ai_field_hint(cfg.get('ai_mode','offline')))
        # when user changes ai_mode in dropdown, update hint immediately
        vs['ai_mode'].trace_add('write', lambda *args: ai_field_hint.config(
            text=_compute_ai_field_hint(vs['ai_mode'].get())
        ))

        tk.Label(
            brain,
            text="Note: Switching cores may require different API keys or local servers.",
            font=('Rajdhani',8,'italic'),
            bg=self.BG2, fg=self.MUTED
        ).pack(anchor='w', pady=(0,5))

        # ── CLOUD AI (GEMINI) ──
        gem = create_card(container, "GOOGLE GEMINI (Cloud)", "✦")
        tk.Label(gem, text="Use this when: ai_mode = gemini (or auto/hybrid fallback).",
                 font=('Rajdhani',8,'italic'), bg=self.BG2, fg=self.MUTED).pack(anchor='w', pady=(0,6))
        vs['gemini_api_key'] = tk.StringVar(value=cfg.get('gemini_api_key',''))
        add_row(gem, "API Key:", vs['gemini_api_key'])
        vs['gemini_model'] = tk.StringVar(value=cfg.get('gemini_model', 'gemini-flash-latest'))
        add_row(gem, "Model:", vs['gemini_model'])

        # ── CLOUD AI (OPENAI) ──
        oai = create_card(container, "OPENAI GPT (Cloud)", "☁")
        tk.Label(oai, text="Use this when: ai_mode = openai.",
                 font=('Rajdhani',8,'italic'), bg=self.BG2, fg=self.MUTED).pack(anchor='w', pady=(0,6))
        vs['openai_api_key'] = tk.StringVar(value=cfg.get('openai_api_key',''))
        add_row(oai, "API Key:", vs['openai_api_key'])
        vs['openai_model'] = tk.StringVar(value=cfg.get('openai_model','gpt-3.5-turbo'))
        add_row(oai, "Model:", vs['openai_model'])

        # ── LOCAL AI (OLLAMA) ──
        oll = create_card(container, "OLLAMA (Local)", "🦙")
        tk.Label(oll, text="Use this when: ai_mode = ollama.",
                 font=('Rajdhani',8,'italic'), bg=self.BG2, fg=self.MUTED).pack(anchor='w', pady=(0,6))
        vs['ollama_url'] = tk.StringVar(value=cfg.get('ollama_url','http://localhost:11434'))
        add_row(oll, "Server URL:", vs['ollama_url'])
        vs['ollama_model'] = tk.StringVar(value=cfg.get('ollama_model','llama3'))
        add_row(oll, "Model Name:", vs['ollama_model'])

        # ── SERVICES / KEYS ──
        keys = create_card(container, "SERVICE API KEYS", "🔑")
        vs['groq_api_key'] = tk.StringVar(value=cfg.get('groq_api_key',''))
        add_row(keys, "Groq Key:", vs['groq_api_key'])
        vs['openai_api_key'] = tk.StringVar(value=cfg.get('openai_api_key',''))
        add_row(keys, "OpenAI Key:", vs['openai_api_key'])
        vs['gemini_api_key'] = tk.StringVar(value=cfg.get('gemini_api_key',''))
        add_row(keys, "Gemini Key:", vs['gemini_api_key'])

        # ── OLLAMA CLOUD ──
        ollc = create_card(container, "OLLAMA CLOUD / REMOTE", "🌐")
        tk.Label(ollc, text="Use this when: ai_mode = ollama_cloud (or ollama_hybrid cloud fallback).",
                 font=('Rajdhani',8,'italic'), bg=self.BG2, fg=self.MUTED).pack(anchor='w', pady=(0,6))
        vs['ollama_cloud_url'] = tk.StringVar(value=cfg.get('ollama_cloud_url',''))
        add_row(ollc, "Remote URL:", vs['ollama_cloud_url'])
        vs['ollama_cloud_model'] = tk.StringVar(value=cfg.get('ollama_cloud_model',''))
        add_row(ollc, "Model Name:", vs['ollama_cloud_model'])
        vs['ollama_cloud_key'] = tk.StringVar(value=cfg.get('ollama_cloud_key',''))
        add_row(ollc, "Auth Key:", vs['ollama_cloud_key'])

        # ── LOCAL AI (API / LM STUDIO) ──
        lai = create_card(container, "LOCAL AI (OpenAI Compatible)", "💻")
        tk.Label(lai, text="Use this for LM Studio, LocalAI, or any v1-compatible server.",
                 font=('Rajdhani',8), bg=self.BG2, fg=self.MUTED).pack(anchor='w', pady=(0,5))
        tk.Label(lai, text="Use this when: ai_mode = local_ai.",
                 font=('Rajdhani',8,'italic'), bg=self.BG2, fg=self.MUTED).pack(anchor='w', pady=(0,6))
        vs['local_ai_url'] = tk.StringVar(value=cfg.get('local_ai_url','http://localhost:1234/v1'))
        add_row(lai, "Base URL:", vs['local_ai_url'])
        vs['local_ai_model'] = tk.StringVar(value=cfg.get('local_ai_model','local-model'))
        add_row(lai, "Model ID:", vs['local_ai_model'])
        vs['local_ai_key'] = tk.StringVar(value=cfg.get('local_ai_key',''))
        add_row(lai, "Auth (if any):", vs['local_ai_key'])

        # ── CUSTOM API ──
        cust = create_card(container, "CUSTOM ENDPOINT", "⚡")
        tk.Label(cust, text="Use this when: ai_mode = custom.",
                 font=('Rajdhani',8,'italic'), bg=self.BG2, fg=self.MUTED).pack(anchor='w', pady=(0,6))
        vs['custom_ai_url'] = tk.StringVar(value=cfg.get('custom_ai_url',''))
        add_row(cust, "URL:", vs['custom_ai_url'])
        vs['custom_ai_key'] = tk.StringVar(value=cfg.get('custom_ai_key',''))
        add_row(cust, "API Key:", vs['custom_ai_key'])
        vs['custom_ai_model'] = tk.StringVar(value=cfg.get('custom_ai_model','custom-model'))
        add_row(cust, "Model:", vs['custom_ai_model'])

        # Save Button
        def save():
            for k, v in vs.items():
                value = v.get()
                if k == 'recognition_mode':
                    value = recognition_mode_reverse_map.get(value, value)
                cfg[k] = value
            self.controller.registry.persist_application_settings()
            self.mode_lbl.config(text=f"AI: {cfg.get('ai_mode','offline').capitalize()}")
            self.append_to_terminal("Settings saved successfully.", 'sys')
            win.destroy()

        footer = tk.Frame(win, bg=self.BG2, height=70)
        footer.pack(fill='x', side='bottom')
        tk.Button(footer, text="APPLY & SAVE SETTINGS", font=('Orbitron',10,'bold'), 
                  bg='#0a3d2a', fg=self.ACCENT3, relief='flat', cursor='hand2', 
                  padx=20, pady=10, command=save).pack(pady=15)

    # ── Window Close ──
    def _on_close(self):
        self._closing = True
        self.controller.shutdown_system()
        try: self.root.destroy()
        except: pass

    def start_ui_loop(self):
        self.root.update_idletasks()
        sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        self.root.geometry(f"960x650+{(sw-960)//2}+{(sh-650)//2}")
        self.root.mainloop()


# ═══════════════════════════════════════════════════════════════
#  MAIN APP CONTROLLER
# ═══════════════════════════════════════════════════════════════

class MainApplicationController:
    """
    The central coordinator of the application.
    Orchestrates the lifecycle of the UI, AI engines, and voice recognition systems.
    """
    def __init__(self):
        print("\n[SYSTEM] Initializing Main Controller...")
        
        self.registry = ApplicationConfigurationRegistry()
        self.voice_orchestrator = VoiceSynthesisOrchestrator(self.registry.active_settings)
        self.speech_engine = SpeechRecognitionEngine(self.registry.active_settings)
        self.ai_core = CognitiveIntelligenceCore(self.registry.active_settings)

        self._shutdown_event = threading.Event()
        self._execution_lock = threading.Lock()
        
        # Legacy hardware support for Vosk
        if HAS_VOSK:
            self.speech_engine.attempt_vosk_model_load()

        # Give the action processor a back-reference so commands like stop_listening work
        self.action_processor = AutomatedActionProcessor(
            self.registry.active_settings,
            self.registry.action_commands,
            controller=self,
        )

        self.user_interface = UserInterfaceHUD(self)
        self._spoken_text_accumulator = ""
        
        self._startup_sequence()

    def _startup_sequence(self):
        """Executes initialization routines like greetings and auto-start listeners."""
        # Initial status logging
        self.user_interface.append_to_terminal("Kailey Core Online", 'sys')
        
        if self.registry.active_settings.get('start_listening_on_boot', True):
            threading.Timer(2.0, self.activate_voice_listening).start()

    def process_input_request(self, text_command):
        """Central entry point for all user requests (voice or manual)."""
        if not text_command: return
        
        # Dispatch to a background thread to keep the HUD responsive
        threading.Thread(target=self._handle_request_logic, args=(text_command,), daemon=True).start()

    def _handle_request_logic(self, text):
        """Determines whether a command is a system trigger or requires AI reasoning."""
        normalized_text = text.lower().strip()

        # Attempt system action execution
        execution_response, was_handled = self.action_processor.process_trigger(normalized_text)

        if was_handled:
            self.user_interface.root.after(0, self._audible_and_visual_response, execution_response)
        else:
            # Fallback to Cognitive AI Core
            self.user_interface.root.after(0, self.user_interface.append_to_terminal, f"Querying AI: {text}", 'sys')
            ai_reply = self.ai_core.generate_response(text)
            self.user_interface.root.after(0, self._audible_and_visual_response, ai_reply)

    def _audible_and_visual_response(self, response_text):
        """Synchronizes voice output with UI terminal updates."""
        self.user_interface.append_to_terminal(response_text, 'res')
        self.voice_orchestrator.queue_speech(response_text)

    def activate_voice_listening(self):
        """Begins the infinite loop for speech capture."""
        if not HAS_SR: return
        self._shutdown_event.clear()
        try:
            self.user_interface.root.after(0, self.user_interface.update_listening_state, True)
        except RuntimeError:
            try:
                self.user_interface.update_listening_state(True)
            except RuntimeError:
                pass
        threading.Thread(target=self._voice_listener_loop, daemon=True).start()

    def deactivate_voice_listening(self):
        """Signals the listener thread to stop processing."""
        self._shutdown_event.set()
        try:
            self.user_interface.root.after(0, self.user_interface.update_listening_state, False)
        except RuntimeError:
            self.user_interface.update_listening_state(False)

    def _voice_listener_loop(self):
        """Continuous background task for processing ambient audio."""
        wake_phrase = self.registry.active_settings.get('wake_word', 'kailey').lower()

        while not self._shutdown_event.is_set():
            if self.voice_orchestrator.is_currently_speaking:
                time.sleep(0.5)
                continue

            captured_text = self.speech_engine.capture_and_transcribe()
            if captured_text:
                self.user_interface.root.after(0, self.user_interface.append_to_terminal, f"Speech: {captured_text}")

                # Check for wake word or direct command match
                if wake_phrase in captured_text or captured_text in self.registry.action_commands:
                    # Clean the wake word from the prompt
                    prompt = captured_text.replace(wake_phrase, '').strip()
                    self.process_input_request(prompt or captured_text)

            time.sleep(0.1)

    def start_listening(self):
        """UI-friendly alias for voice activation."""
        self.activate_voice_listening()

    def stop_listening(self):
        """UI-friendly alias for voice deactivation."""
        self.deactivate_voice_listening()

    def process_text_command(self, text):
        """UI-friendly alias for handling manual text input."""
        self.process_input_request(text)

    def listen_once_async(self):
        """Captures a single command without entering continuous listening mode."""
        if not HAS_SR: return

        def _capture_and_process_once():
            try:
                self.user_interface.root.after(0, self.user_interface.update_listening_state, True)
                self.user_interface.root.after(0, self.user_interface.append_to_terminal, "Single capture active...", 'sys')
            except RuntimeError:
                self.user_interface.update_listening_state(True)
                self.user_interface.append_to_terminal("Single capture active...", 'sys')
            text = self.speech_engine.capture_and_transcribe()
            try:
                self.user_interface.root.after(0, self.user_interface.update_listening_state, False)
            except RuntimeError:
                self.user_interface.update_listening_state(False)
            if text:
                self.process_input_request(text)
            else:
                try:
                    self.user_interface.root.after(0, self.user_interface.append_to_terminal, "No speech detected.", 'muted')
                except RuntimeError:
                    self.user_interface.append_to_terminal("No speech detected.", 'muted')

        threading.Thread(target=_capture_and_process_once, daemon=True).start()

    def shutdown_system(self):
        """Cleans up resources and persists settings before exit."""
        print("[SYSTEM] Shutting down...")
        self.deactivate_voice_listening()
        self.voice_orchestrator.purge_audio_cache()

def main():
    """Application entry point with global error trapping."""
    # Environment health check
    dependencies = [
        (HAS_SR, "SpeechRecognition"),
        (HAS_PYTTSX3, "pyttsx3"),
        (HAS_EDGE_TTS, "edge-tts"),
        (HAS_PYGAME, "pygame"),
        (HAS_PSUTIL, "psutil")
    ]
    missing = [name for available, name in dependencies if not available]
    if missing:
        print("\n[WARNING] Critical dependencies are missing:")
        for m in missing: print(f"  - {m}")
        print("Please run: pip install SpeechRecognition pyttsx3 edge-tts pygame psutil\n")

    try:
        controller = MainApplicationController()
        controller.user_interface.start_ui_loop()
    except Exception as fatal_error:
        print(f"\n[FATAL SYSTEM ERROR] {fatal_error}\n")
        traceback.print_exc()
        input("Press Enter to terminate...")

if __name__ == '__main__':
    main()
