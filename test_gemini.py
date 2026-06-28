import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent))
import kailey

mgr = kailey.ApplicationConfigurationRegistry()
cfg = dict(mgr.active_settings)
cfg['ai_mode'] = 'gemini'
engine = kailey.CognitiveIntelligenceCore(cfg)
print("Using mode:", cfg.get('ai_mode'))
key = cfg.get('gemini_api_key', '')
print("Key:", f"{key[:6]}..." if key else "(missing)")
reply = engine.generate_response("Hello, who are you?")
print("Response:", reply)
