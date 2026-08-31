#!/usr/bin/env python3
import json, urllib.request
base="http://127.0.0.1:8765"
with urllib.request.urlopen(base+"/api/defaults", timeout=20) as r:
    d=json.loads(r.read().decode())
print("defaults", r.status if False else 200, "total", d.get("catalogTotal"), "token", d.get("hasToken"), "sid", d.get("defaults",{}).get("serviceId"))
with urllib.request.urlopen(base+"/api/catalog?category=video&status=available", timeout=20) as r:
    c=json.loads(r.read().decode())
print("video available", c.get("count"), [x["id"] for x in c.get("items",[])[:8]])
with urllib.request.urlopen(base+"/api/import-image/140952623", timeout=60) as r:
    j=json.loads(r.read().decode())
print("import", {k:j.get(k) for k in ("kind","serviceId","serviceName","prompt","engine","operation","checkpointName","width","height")})
