# Kailey AI Assistant

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-blue?logo=python&logoColor=white" alt="Python Version">
  <img src="https://img.shields.io/badge/Platform-Windows-0078D6?logo=windows&logoColor=white" alt="Platform">
  <img src="https://img.shields.io/badge/License-MIT-green" alt="License">
  <img src="https://img.shields.io/badge/Status-Active-brightgreen" alt="Status">
  <img src="https://img.shields.io/github/last-commit/Shabaz2009/kailey-ai-assistant" alt="Last Commit">
  <img src="https://img.shields.io/github/stars/Shabaz2009/kailey-ai-assistant?style=social" alt="Stars">
</p>

<p align="center">
  <strong>A Windows-native Python voice assistant with wake-word detection, speech recognition, text-to-speech, app automation, and AI backends.</strong>
</p>

---

## ✨ Features

| Category | Capabilities |
|----------|--------------|
| **🎤 Voice Interface** | Wake-word listener (`wake_listener.py`), real-time STT, multiple TTS engines |
| **🤖 AI Backends** | Ollama (local), Gemini, OpenAI-compatible, Custom endpoints, LocalAI/LM Studio |
| **🎯 Speech Recognition** | Faster-Whisper (local), Vosk (offline), Google STT (online), auto-fallback |
| **🔊 Text-to-Speech** | Edge TTS (neural voices), pyttsx3 (offline SAPI5), Windows SAPI fallback |
| **⚡ Automation** | App launching, web actions, system controls (volume, brightness, power), hotkeys |
| **💻 Low-End Support** | Optimized modes for older hardware, reduced CPU/RAM usage |
| **🔧 Extensible** | Custom commands via `commands.json`, persistent settings in `config.json` |
| **🖥️ Desktop UI** | Tkinter-based HUD with live transcript, command log, and settings panel |

---

## 📁 Project Structure

```
Kailey/
├── kailey.py              # Main desktop assistant application
├── wake_listener.py       # Lightweight background wake-word listener
├── commands.json          # Built-in + custom voice command mappings
├── config.json            # Runtime settings (auto-generated, gitignored)
├── requirements.txt       # Python dependencies
├── PROJECT_DETAILS.md     # Technical documentation & changelog
├── LICENSE                # MIT License
├── README.md              # This file
│
├── 📁 Launch Scripts (Windows)
│   ├── start_kailey.bat   # Primary launcher (venv + app)
│   ├── launch.bat         # Alternative launcher
│   └── setup.bat          # First-time setup helper
│
├── 📁 Utility Scripts
│   ├── extract_vosk.bat   # Vosk model extractor
│   ├── install_phi3.bat   # Phi-3 model installer
│   └── copy_to_downloads.bat
│
├── 📁 Test Scripts
│   ├── test_audio.py      # Microphone/STT test
│   ├── test_gemini.py     # Gemini API test
│   └── test_voice.py      # TTS engine test
│
└── 📁 Assets (gitignored)
    ├── models/            # Vosk/Whisper models
    ├── greeting_sounds/   # Custom greeting audio
    ├── temp_audio/        # TTS cache
    ├── memory/            # Conversation history
    └── screenshots/       # UI captures
```

---

## 🚀 Quick Start

### Prerequisites
- **Windows 10/11** (primary target)
- **Python 3.10+**
- Microphone access

### 1. Clone & Setup

```bash
git clone https://github.com/Shabaz2009/kailey-ai-assistant.git
cd kailey-ai-assistant

# Create virtual environment
python -m venv venv
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

> **Windows users:** Run `setup.bat` for automated setup.

### 2. Configure (Optional)

On first run, `config.json` is created with safe defaults. Edit it to add API keys:

```json
{
  "gemini_api_key": "YOUR_KEY_HERE",
  "openai_api_key": "YOUR_KEY_HERE",
  "ollama_url": "http://localhost:11434",
  "recognition_mode": "local_whisper",
  "voice_engine": "edge_tts",
  "low_end_mode": true
}
```

### 3. Run the Assistant

```bash
# Main app
python kailey.py

# Or use the Windows launcher
start_kailey.bat
```

### 4. Run Wake-Word Listener (Background)

```bash
python wake_listener.py
```

Say **"Kailey"** (or variants: *kali, kaylee, kelly, kylie, hailey, daily, clearly*) to activate.

---

## ⚙️ Configuration Guide

### Speech Recognition (`recognition_mode`)

| Mode | Engine | Offline | Best For |
|------|--------|---------|----------|
| `local_whisper` | Faster-Whisper + fallback | ✅ | Accuracy + offline |
| `offline` / `auto` | Vosk | ✅ | Fully offline, low resources |
| `online` | Google STT | ❌ | Maximum accuracy, requires internet |

### AI Backends (`ai_mode`)

| Mode | Description | Config Keys |
|------|-------------|-------------|
| `ollama` | Local Ollama server | `ollama_url`, `ollama_model` |
| `ollama_hybrid` | Local + cloud fallback | `ollama_*` + `ollama_cloud_*` |
| `gemini` | Google Gemini API | `gemini_api_key`, `gemini_model` |
| `openai` | OpenAI API | `openai_api_key`, `openai_model` |
| `local_ai` | OpenAI-compatible (LM Studio, LocalAI) | `local_ai_url`, `local_ai_key`, `local_ai_model` |
| `custom` | Custom OpenAI-compatible endpoint | `custom_ai_url`, `custom_ai_key`, `custom_ai_model` |

### Voice Settings

```json
{
  "voice_engine": "edge_tts",
  "edge_voice_id": "en-US-JennyNeural",
  "edge_voice_rate": "-5%",
  "edge_voice_pitch": "+1Hz",
  "pyttsx3_rate": 175,
  "pyttsx3_volume": 1.0
}
```

### Low-End Mode

Enable `low_end_mode: true` for:
- Shorter STT capture windows
- Non-streaming Ollama responses
- Reduced UI update frequency
- Lower Whisper model (`small.en`)

---

## 🎮 Built-in Commands

| Category | Examples |
|----------|----------|
| **Apps** | `youtube`, `github`, `spotify`, `notepad`, `calculator`, `vscode`, `chrome` |
| **System** | `volume up/down`, `brightness up/down`, `screenshot`, `lock`, `shutdown`, `restart` |
| **Web** | `google`, `search <query>`, `youtube search <query>`, `gmail`, `maps` |
| **Info** | `time`, `date`, `weather`, `cpu`, `memory`, `battery`, `system info` |
| **Control** | `stop listening`, `cancel shutdown` |

> Add your own in `commands.json` or via the Settings UI.

---

## 🛠️ Development

### Run Tests

```bash
python test_audio.py      # Microphone + STT
python test_voice.py      # TTS engines
python test_gemini.py     # Gemini API
```

### Code Style

```bash
# Type checking (optional)
pip install mypy
mypy kailey.py wake_listener.py
```

---

## 📦 Dependencies

| Package | Purpose |
|---------|---------|
| `speechrecognition` | STT abstraction |
| `pyaudiowpatch` | Audio capture (Windows loopback) |
| `faster-whisper` | Local Whisper inference |
| `vosk` | Offline STT |
| `edge-tts` | Neural TTS |
| `pyttsx3` | Offline TTS fallback |
| `pygame` | Audio playback |
| `pycaw` | Windows volume control |
| `screen-brightness-control` | Windows brightness |
| `psutil` | System stats |
| `pyautogui` | Hotkey automation |
| `requests` | HTTP for AI APIs |
| `wikipedia` | Wiki search |

---

## 🐛 Troubleshooting

| Issue | Solution |
|-------|----------|
| Wake word not detected | Check `wake_listener.py` logs; ensure mic works; try `offline` mode |
| STT returns empty | Try `recognition_mode: "online"`; check microphone permissions |
| TTS silent | Verify `voice_engine`; install `edge-tts` or check `pyttsx3` voices |
| Ollama connection failed | Ensure `ollama serve` runs; check `ollama_url` in config |
| High CPU on old PC | Enable `low_end_mode: true`; use `vosk` model; reduce Whisper model size |

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

Copyright (c) 2026 Shabaz2009

---

## 🙏 Thanks

This project builds on some great open-source tools:

- [Faster-Whisper](https://github.com/SYSTRAN/faster-whisper) for local speech recognition
- [Vosk](https://alphacephei.com/vosk/) for offline speech recognition  
- [Edge-TTS](https://github.com/rany2/edge-tts) for natural-sounding voices
- [Ollama](https://ollama.ai/) for running AI models locally
- [pycaw](https://github.com/AndreMiras/pycaw) for Windows audio control

---

<p align="center">
  <strong>Made by Shabaz</strong>
</p>