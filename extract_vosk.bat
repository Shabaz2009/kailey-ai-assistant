@echo off
copy /Y "C:\Users\User\.gemini\antigravity\scratch\Kailey\kailey.py" "C:\Users\User\Downloads\Kailey\"
copy /Y "C:\Users\User\.gemini\antigravity\scratch\Kailey\wake_listener.py" "C:\Users\User\Downloads\Kailey\"
powershell -command "Expand-Archive -Force -Path 'C:\Users\User\Downloads\vosk-model-small-en-in-0.4.zip' -DestinationPath 'C:\Users\User\Downloads\Kailey\models'"
