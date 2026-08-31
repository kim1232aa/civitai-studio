#!/usr/bin/env python3
import json
from pathlib import Path
from collections import defaultdict

p = Path("/tmp/civitai-probe/services.json")
raw = json.loads(p.read_text())
print("top keys", list(raw.keys())[:20] if isinstance(raw, dict) else type(raw).__name__)
items = raw
if isinstance(raw, dict):
    for k in ("items", "data", "services", "result"):
        if k in raw:
            items = raw[k]
            print("using", k, type(items).__name__)
            break
if isinstance(items, dict) and "items" in items:
    items = items["items"]

def walk(obj, acc):
    if isinstance(obj, dict):
        eng = obj.get("engine") or obj.get("Engine")
        op = obj.get("operation") or obj.get("Operation") or obj.get("name")
        st = obj.get("status") or obj.get("availability") or obj.get("state")
        typ = obj.get("type") or obj.get("recipe") or obj.get("kind")
        if eng:
            acc.append({
                "engine": eng,
                "operation": op,
                "status": st,
                "type": typ,
                "keys": sorted(obj.keys())[:30],
            })
        for v in obj.values():
            walk(v, acc)
    elif isinstance(obj, list):
        for v in obj:
            walk(v, acc)

acc = []
walk(raw, acc)
print("engine hits", len(acc))
seen = set()
for a in acc:
    key = (a["engine"], a["operation"], a["status"], a["type"])
    if key in seen:
        continue
    seen.add(key)
    print(f"{a['engine']:24} op={a['operation']!s:28} st={a['status']!s:14} type={a['type']}")
print("--- sample keys of first ---")
if acc:
    print(acc[0]["keys"])
