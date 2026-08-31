#!/usr/bin/env python3
import urllib.request
from pathlib import Path
token = Path("/home/box/.config/civitai/token").read_text().strip()
for name in ("imageGen", "videoGen", "imageUpscaler", "videoUpscaler", "convertImage"):
    url = f"https://orchestration.civitai.com/v2/consumer/recipes/{name}/openapi.yaml"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}", "User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            body = r.read()
        Path(f"/tmp/civitai-probe/{name}.openapi.yaml").write_bytes(body)
        print(name, "ok", len(body))
    except Exception as e:
        print(name, "fail", e)
