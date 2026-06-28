# Project Structure

```
Kailey-AI-Assistant/
├── 📄 Core Application
│   ├── kailey.py                 # Main desktop assistant (GUI + STT + TTS + AI)
│   ├── wake_listener.py          # Background wake-word listener
│   ├── commands.json             # Built-in & custom voice commands
│   ├── config.json               # Runtime settings (gitignored, created on first run)
│   ├── requirements.txt          # Python dependencies
│   └── PROJECT_DETAILS.md        # Technical changelog & debug guide
│
├── 🚀 Windows Launchers
│   ├── start_kailey.bat          # Primary launcher (venv + kailey.py)
│   ├── launch.bat                # Alternative launcher
│   ├── setup.bat                 # First-time setup (venv + deps + models)
│   ├── extract_vosk.bat          # Vosk model extractor
│   ├── install_phi3.bat          # Phi-3 model installer (Ollama)
│   └── copy_to_downloads.bat     # Utility script
│
├── 🧪 Test Scripts
│   ├── test_audio.py             # Microphone + STT verification
│   ├── test_voice.py             # TTS engine verification
│   └── test_gemini.py            # Gemini API verification
│
├── 📁 Runtime Directories (gitignored)
│   ├── venv/                     # Python virtual environment
│   ├── models/                   # Vosk/Whisper models (downloaded separately)
│   ├── greeting_sounds/          # Custom greeting audio files
│   ├── memory/                   # Conversation history & workspace
│   ├── temp_audio/               # TTS cache files
│   ├── screenshots/              # UI screenshots
│   └── scratch/                  # Temporary workspace
│
├── 📄 Documentation
│   ├── README.md                 # Main documentation
│   ├── PROJECT_STRUCTURE.md      # This file
│   └── LICENSE                   # MIT License
│
└── 🔧 Config (gitignored)
    └── config.json               # User settings, API keys, preferences
```

## Key Files Explained

| File | Purpose |
|------|---------|
| `kailey.py` | Monolithic main app: Tkinter HUD, speech recognition, TTS orchestration, AI routing, command execution, system control |
| `wake_listener.py` | Lightweight background process; uses Vosk/Google STT to detect wake words and launch `kailey.py` |
| `commands.json` | Extensible command registry: maps phrases → actions (open_url, open_app, key_combo, system_control, AI query) |
| `requirements.txt` | Pinned dependencies for reproducible installs |
| `start_kailey.bat` | Double-click entry point for non-technical users |

## Ignored by Git (`.gitignore`)

```
venv/
__pycache__/
*.pyc
config.json
temp_audio/
screenshots/
scratch/
memory/
models/
test.mp3
*.log
.DS_Store
```

> **Note:** `config.json` is generated on first run with safe defaults. Users add their own API keys locally.