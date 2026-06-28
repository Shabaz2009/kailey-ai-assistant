# Kailey — Personal Voice Command Assistant (Offline + Online)

## Overview
Kailey is a personal voice command assistant with:
- **Wake-word listener**: `wake_listener.py` (runs in background; launches the main app when the wake word is detected).
- **Main UI + STT + TTS + AI**: `kailey.py`
- **Config + command persistence**: `config.json`, `commands.json`

## What was fixed / optimized
### 1) Wake-word debugging visibility
`wake_listener.py` prints wake STT transcripts so you can confirm whether the wake word matching is working:
- `"[WAKE] heard: '...'"` — shows the STT transcript
- `"[WAKE] Wake word detected: '...'"` — confirms wake match

### 2) STT fallback for `recognition_mode=local_whisper`
In `kailey.py`, when `recognition_mode=local_whisper` is selected:
- Faster-Whisper is attempted first.
- If it returns empty / fails, the system falls back to:
  1) **Vosk** (if available)
  2) **Google STT** (online fallback)

This prevents “silent failure” on old/low-end PCs where Faster-Whisper isn’t usable.

### 3) Low-end optimization (very old PCs)
When `low_end_mode=true`:
- STT capture windows are shorter.
- HUD streaming updates are reduced/disabled where expensive.
- **Ollama generation is non-streaming** (saves CPU) and uses a shorter timeout.

### 4) Model selection (GUI + config)
Added GUI inputs and config keys for:
- **Gemini model**: `gemini_model`
- **Custom endpoint model**: `custom_ai_model`

## How to run

### Windows (main UI)
Run:
- `start_kailey.bat`

That launches:
- `venv\Scripts\activate.bat`
- `python kailey.py`

### Wake-word listener (background)
Run:
- `wake_listener.py`
(Optionally through your own scheduler / shortcut.)

## Configuration: `config.json`
Key categories:

### Voice / UI
- `voice_engine`: `edge_tts` or `pyttsx3`
- `edge_voice_id`, `edge_voice_rate`, `edge_voice_pitch`
- `pyttsx3_rate`, `pyttsx3_volume`, `pyttsx3_voice_index`

### STT
- `recognition_mode`:
  - `local_whisper` (Faster-Whisper + fallback)
  - `offline` / `auto` (Vosk offline when available)
  - `online` (Google STT)
- `local_whisper_model`
- `local_whisper_vad`
- `low_end_mode`: boolean

### AI backend
- `ai_mode`:
  - `gemini`, `openai`, `ollama`, `ollama_hybrid`
  - `local_ai` (OpenAI-compatible)
  - `custom` (OpenAI-compatible custom endpoint)
- `openai_model`, `gemini_model`, `ollama_model`
- `local_ai_url`, `local_ai_key`, `local_ai_model`
- `custom_ai_url`, `custom_ai_key`, `custom_ai_model`

## Debug checklist (wake-word not launching)
1. Start `wake_listener.py`
2. Speak the wake phrase clearly
3. Confirm logs show:
   - `"[WAKE] heard: '...'"` (you are getting any transcript)
   - `"[WAKE] Wake word detected: '...'"` (wake matching is successful)
4. If transcript shows but wake match doesn’t:
   - edit the `WAKE_WORDS` list inside `wake_listener.py`

## Troubleshooting
### “Nothing happens after saying Kailey”
- Confirm STT transcript appears in wake listener logs.
- Confirm wake phrase is actually included in `WAKE_WORDS`.

### `recognition_mode=local_whisper` breaks on old PCs
- Install/enable Faster-Whisper if possible.
- Otherwise rely on the fallback (Vosk/Google) implemented in `kailey.py`.

## Files
- `kailey.py`: Main application (HUD + STT + TTS + AI)
- `wake_listener.py`: Lightweight wake word listener
- `config.json`: persistent settings
- `commands.json`: user-defined voice commands
- `models/`: Vosk models
