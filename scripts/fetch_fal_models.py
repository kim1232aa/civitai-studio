#!/usr/bin/env python3
import json, urllib.request, urllib.parse
from pathlib import Path
from collections import Counter
key = Path("/home/box/.config/fal/token").read_text().strip()
headers = {"Authorization": f"Key {key}", "Accept": "application/json", "User-Agent": "Mozilla/5.0"}

def get(url):
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())

all_models = []
url = "https://api.fal.ai/v1/models?limit=100"
seen = set()
for page in range(30):
    data = get(url)
    if isinstance(data, dict):
        items = data.get("models") or data.get("items") or data.get("data") or data.get("endpoints") or []
        if not items and "results" in data:
            items = data["results"]
        nxt = data.get("next") or data.get("next_cursor") or (data.get("pagination") or {}).get("next")
        cursor = data.get("cursor") or data.get("nextCursor")
        keys = list(data.keys())
        if page == 0:
            print("top keys", keys)
            print("n items", len(items) if isinstance(items, list) else type(items))
            if isinstance(items, list) and items:
                print("item0 keys", list(items[0].keys()) if isinstance(items[0], dict) else type(items[0]))
                print(json.dumps(items[0], ensure_ascii=False)[:1200])
        if isinstance(items, list):
            for it in items:
                eid = (it.get("endpoint_id") or it.get("id") or it.get("endpoint") or "") if isinstance(it, dict) else str(it)
                if eid in seen:
                    continue
                seen.add(eid)
                all_models.append(it)
        print(f"page {page} got {len(items) if isinstance(items,list) else '?'} total {len(all_models)} nxt={bool(nxt)} cursor={bool(cursor)}")
        if nxt and isinstance(nxt, str) and nxt.startswith("http"):
            url = nxt
            continue
        if cursor:
            url = f"https://api.fal.ai/v1/models?limit=100&cursor={urllib.parse.quote(str(cursor))}"
            continue
        if nxt:
            url = f"https://api.fal.ai/v1/models?limit=100&cursor={urllib.parse.quote(str(nxt))}"
            continue
        break
    else:
        print("unexpected", type(data), str(data)[:200])
        break

Path("/tmp/fal-models-raw.json").write_text(json.dumps(all_models)[:50] and json.dumps({"count": len(all_models), "models": all_models}, ensure_ascii=False))
print("saved", len(all_models))

cats = Counter()
kinds = Counter()
for it in all_models:
    if not isinstance(it, dict):
        continue
    cat = it.get("category") or it.get("kind") or it.get("type") or (it.get("metadata") or {}).get("category")
    cats[str(cat)] += 1
    tags = it.get("tags") or it.get("categories") or []
    if isinstance(tags, list):
        for t in tags[:3]:
            kinds[str(t)] += 1
print("categories", cats.most_common(20))
print("tags", kinds.most_common(20))
# print some image/video endpoints
n = 0
for it in all_models:
    eid = it.get("endpoint_id") or it.get("id")
    name = it.get("title") or it.get("name") or ""
    cat = it.get("category") or ""
    blob = f"{eid} {name} {cat}".lower()
    if any(x in blob for x in ("flux", "kling", "wan", "minimax", "seedream", "veo", "sora", "hunyuan", "nano", "qwen", "upscale", "video", "image")):
        print(f"{eid:55} {cat:16} {name[:40]}")
        n += 1
        if n > 40:
            break
