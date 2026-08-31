#!/usr/bin/env python3
import json, urllib.request, urllib.error
from pathlib import Path
key = Path("/home/box/.config/fal/token").read_text().strip()
headers = {"Authorization": f"Key {key}", "User-Agent": "Mozilla/5.0", "Accept": "application/json"}

def hit(url):
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read()
            print("OK", r.status, url, "bytes", len(raw))
            try:
                return r.status, json.loads(raw.decode())
            except Exception:
                print(raw[:400])
                return r.status, raw[:400]
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        print("ERR", e.code, url, raw[:400])
        return e.code, raw
    except Exception as e:
        print("FAIL", url, e)
        return 0, str(e)

urls = [
    "https://api.fal.ai/v1/models",
    "https://fal.ai/api/models",
    "https://rest.alpha.fal.ai/models",
    "https://api.fal.ai/models",
    "https://queue.fal.run/fal-ai/flux/dev",
]
for u in urls:
    hit(u)
