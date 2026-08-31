#!/usr/bin/env python3
import json
from pathlib import Path

raw = json.loads(Path("/tmp/civitai-probe/services.json").read_text())
items = raw.get("items") or []
print("count", len(items), "totalCount", raw.get("totalCount"))
print("item0 keys", sorted(items[0].keys()) if items else None)
print("--- first item dump (truncated) ---")
print(json.dumps(items[0], ensure_ascii=False, indent=2)[:3000])

def find_eng(o, found):
    if isinstance(o, dict):
        for k in ("engine", "operation", "ecosystem", "model", "version", "provider"):
            if k in o and o[k] and k not in found:
                found[k] = o[k]
        for v in o.values():
            find_eng(v, found)
    elif isinstance(o, list):
        for x in o:
            find_eng(x, found)

print("\n===== ALL SERVICES =====")
keysets = set()
for it in items:
    keysets.add(tuple(sorted(it.keys())))
    found = {}
    find_eng(it, found)
    name = it.get("name") or it.get("id") or it.get("key") or it.get("service")
    status = it.get("status") or it.get("availability") or it.get("state") or it.get("health") or it.get("serviceStatus")
    typ = it.get("type") or it.get("recipe") or it.get("category") or it.get("kind")
    print(f"{str(name)[:48]:48} st={str(status):14} type={str(typ):14} {found}")

print("\nunique keysets:")
for ks in sorted(keysets):
    print(ks)
