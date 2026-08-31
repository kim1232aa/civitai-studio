#!/usr/bin/env python3
import json, urllib.request
from pathlib import Path

token = Path("/home/box/.config/civitai/token").read_text().strip()
base = "https://orchestration.civitai.com/v2/services"
all_items = []
offset = 0
limit = 200
total = None
while True:
    url = f"{base}?limit={limit}&offset={offset}"
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {token}",
        "User-Agent": "Mozilla/5.0",
    })
    with urllib.request.urlopen(req, timeout=60) as r:
        data = json.loads(r.read().decode())
    items = data.get("items") or []
    total = data.get("totalCount")
    all_items.extend(items)
    print(f"offset={offset} got={len(items)} total_so_far={len(all_items)} totalCount={total}", flush=True)
    if not items or len(all_items) >= (total or 0):
        break
    offset += limit

out = {"totalCount": total, "count": len(all_items), "items": all_items}
Path("/tmp/civitai-probe/services_all.json").write_text(json.dumps(out))
# slim catalog for the app
slim = []
for it in all_items:
    params = it.get("parameters") or {}
    slim.append({
        "id": it.get("id"),
        "name": it.get("name"),
        "description": it.get("description") or "",
        "category": it.get("category"),
        "status": it.get("status"),
        "step": it.get("step"),
        "submit": it.get("submit"),
        "estimate": it.get("estimate"),
        "tags": it.get("tags") or [],
        "modalities": it.get("modalities") or {},
        "engine": params.get("engine"),
        "operation": params.get("operation"),
        "ecosystem": params.get("ecosystem"),
        "model": params.get("model"),
        "version": params.get("version"),
        "provider": params.get("provider"),
        "parameters": params,
    })
Path("/workspace/civitai-studio/docs/catalog.json").write_text(json.dumps({
    "total": len(slim), "items": slim
}, ensure_ascii=False, indent=2))
from collections import Counter
print("by category", Counter(x["category"] for x in slim))
print("by status", Counter(x["status"] for x in slim))
print("gen steps", Counter(x["step"] for x in slim if x.get("step") in ("imageGen","videoGen","audioGen") or (x.get("category") in ("image","video") and x.get("step"))))
# list image+video available
print("\nAVAILABLE IMAGE/VIDEO:")
for x in slim:
    if x["category"] in ("image","video") and x["status"]=="available" and x.get("step") in ("imageGen","videoGen"):
        print(f"  [{x['category']}] {x['status']:12} {x['id']:55} {x['name']}")
