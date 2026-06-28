@echo off
title Installing Offline AI Engine (Phi-3)
color 0A

echo ========================================================
echo   Kailey AI - Offline Engine Setup
echo ========================================================
echo.
echo Make sure you have installed OllamaSetup.exe first!
echo.
echo Press any key to start downloading the Phi-3 model...
pause >nul

echo.
echo [1/1] Downloading Phi-3 AI Model (2.3GB)...
echo This may take a few minutes depending on your internet.
echo You can close this window once it finishes!
echo.

ollama run phi3

pause
