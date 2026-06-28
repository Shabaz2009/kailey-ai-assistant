import ctypes
import os

filepath = r"C:\Windows\Media\tada.wav"
if os.path.exists(filepath):
    alias = "myaudio"
    print("Playing sound silently...")
    ctypes.windll.winmm.mciSendStringW(f'open "{filepath}" alias {alias}', None, 0, None)
    ctypes.windll.winmm.mciSendStringW(f'play {alias} wait', None, 0, None)
    ctypes.windll.winmm.mciSendStringW(f'close {alias}', None, 0, None)
    print("Done")
else:
    print("File not found.")
