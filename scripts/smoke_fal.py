#!/usr/bin/env python3
import json, urllib.request
base="http://127.0.0.1:8765"
def get(path):
    with urllib.request.urlopen(base+path, timeout=30) as r:
        return json.loads(r.read().decode())
d=get("/api/defaults")
print("hasToken", d.get("hasToken"), "hasFal", d.get("hasFal"))
c=get("/api/catalog?backend=fal")
print("fal count", c.get("count"), "backend", c.get("backend"), "first", (c.get("items") or [{}])[0].get("id"), (c.get("items") or [{}])[0].get("name"))
from collections import Counter
print(Counter(x.get("category") for x in c.get("items") or []))
cv=get("/api/catalog")
print("civitai count", cv.get("count"))
