#!/usr/bin/env python3
import json
from pathlib import Path
raw = json.loads(Path("/tmp/civitai-probe/services.json").read_text())
want = ("krea2", "minimax", "wan", "happyHorse", "hunyuan", "seedream", "qwen")
for it in raw["items"]:
    blob = json.dumps(it)
    if any(w.lower() in blob.lower() for w in ("Krea 2 Turbo", "Minimax-h3-comfy Image To Video", "Wan v2.2 · Image to Video")):
        print("="*60)
        print(it.get("id"), it.get("name"), it.get("status"), it.get("step"), it.get("submit"))
        print("params keys", list((it.get("parameters") or {}).keys())[:40])
        print(json.dumps(it.get("parameters"), ensure_ascii=False)[:2500])
        print()
