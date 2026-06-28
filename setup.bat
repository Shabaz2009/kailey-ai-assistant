@echo off
title Kailey Setup
color 0B

echo ============================================
echo    Kailey - Voice Assistant Setup
echo ============================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found! Install Python 3.8+
    echo Check "Add Python to PATH" during install.
    pause & exit
)

echo [1/5] Creating virtual environment...
python -m venv venv
call venv\Scripts\activate.bat

echo [2/5] Installing core voice packages...
pip install SpeechRecognition pyaudiowpatch pyttsx3 edge-tts
pip install pygame 2>nul

echo [3/5] Installing system control packages...
pip install psutil pyautogui requests

echo [4/5] Installing offline voice engine (Vosk)...
pip install vosk

echo [5/5] Installing Windows-specific packages...
pip install pycaw screen_brightness_control 2>nul

echo.
echo ============================================
echo    SETUP COMPLETE!
echo ============================================
echo.
echo NEXT STEPS:
echo   1. Download Vosk model for OFFLINE voice:
echo      https://alphacephei.com/vosk/models
echo      Get: vosk-model-small-en-us-0.15 (40MB)
echo      Extract to: models\vosk-model-small-en-us\
echo.
echo   2. Run: start_kailey.bat
echo      OR:  python kailey.py
echo.
echo VOICE CUSTOMIZATION:
echo   - Open Settings inside Kailey
echo   - Choose from 50+ natural voices
echo   - Default: Jenny (US) - natural female voice
echo.
pause
