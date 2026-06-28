# Kailey AI Assistant

Kailey is a Windows-focused Python voice assistant that combines wake-word detection, speech recognition, text-to-speech, app automation, and optional AI backends in a desktop interface.

## Features

- Wake-word listener that can launch the main app in the background
- Desktop assistant UI for voice input, command execution, and AI responses
- Offline and online speech recognition support
- Multiple text-to-speech options, including Edge TTS and pyttsx3
- Voice command automation for apps, web actions, and system controls
- Support for local and cloud AI backends such as Ollama, Gemini, OpenAI-compatible servers, and custom endpoints
- Low-end mode options for older or slower Windows PCs
- Persistent custom commands and settings

## Project Structure

- `kailey.py` - main desktop assistant application
- `wake_listener.py` - lightweight wake-word listener
- `commands.json` - built-in and custom command mappings
- `config.json` - local runtime settings generated on first run
- `requirements.txt` - Python dependencies
- `start_kailey.bat`, `launch.bat`, `setup.bat` - Windows launch and setup helpers
- `models/` - optional local speech recognition models
- `greeting_sounds/` - optional greeting audio assets

## Quick Start

### 1. Install dependencies

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Run the assistant

```bash
python kailey.py
```

Or on Windows, use:

```bat
start_kailey.bat
```

### 3. Run the wake-word listener

```bash
python wake_listener.py
```

## Configuration

Kailey loads its settings from `config.json`. If the file does not exist, the app creates it from safe defaults on first launch.

Recommended local setup:

- Keep API keys and personal settings in your local `config.json`
- Use `low_end_mode=true` on older hardware
- Set `recognition_mode` based on your preferred speech engine

## Notes

- This repository is designed for Windows
- Large generated files, local models, and personal runtime data are excluded from version control
- The repository uses the MIT License

## License

MIT License. See the [LICENSE](LICENSE) file for details.