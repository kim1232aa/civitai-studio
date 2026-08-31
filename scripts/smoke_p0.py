#!/usr/bin/env python3
import json, urllib.request, urllib.error
base="http://127.0.0.1:8765"

def get(path):
    with urllib.request.urlopen(base+path, timeout=30) as r:
        return r.status, json.loads(r.read().decode())

def get_err(path):
    try:
        with urllib.request.urlopen(base+path, timeout=30) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        raw=e.read().decode()
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, raw[:200]

st,d=get("/api/defaults")
print("defaults loras", d.get("defaults",{}).get("loras"), "hasToken", d.get("hasToken"), "total", d.get("catalogTotal"))
st,c=get("/api/catalog")
print("catalog", st, "count", c.get("count"), "warn", c.get("warning"))
st,e=get_err("/api/import-image/notanid")
print("import notanid", st, e)
st,e=get_err("/api/import-image/"+urllib.parse.quote("https://civitai.red/images/140952623", safe=""))
print("import url", st, {k:e.get(k) for k in ("kind","serviceId","prompt","error") if isinstance(e,dict)})
