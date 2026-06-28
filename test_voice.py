import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent))
import kailey

mgr = kailey.ApplicationConfigurationRegistry()
vm = kailey.VoiceSynthesisOrchestrator(mgr.active_settings)

if vm.native_engine:
    voice_id = vm.native_engine.getProperty('voice')
    voices = vm.native_engine.getProperty('voices')
    voice_name = next((v.name for v in voices if v.id == voice_id), "Unknown")
    print(f"Selected offline voice: {voice_name}")
else:
    print("pyttsx3 failed to initialize")
