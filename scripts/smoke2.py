#!/usr/bin/env python3
import json, urllib.request
base="http://127.0.0.1:8765"

def get(path):
    with urllib.request.urlopen(base+path, timeout=30) as r:
        raw=r.read()
        try:
            return r.status, json.loads(raw.decode())
        except Exception:
            return r.status, raw[:120]

def post(path, body):
    req=urllib.request.Request(base+path, data=json.dumps(body).encode(), headers={"Content-Type":"application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())

import urllib.error
print("health", get("/api/health")[0], get("/api/health")[1] if False else None)
st, h = get("/api/health")
print("health", st, h)
st, c = get("/api/capabilities")
print("caps", st, "n", len(c.get("capabilities") or []), "keys", list(c.keys())[:6])
st, d = get("/api/defaults")
print("defaults", st, d.get("catalogTotal"))
# whatif wan i2v — estimate only, does not enqueue
st, w = post("/api/whatif", {
    "serviceId": "video/wan/v2.2/fal/image-to-video",
    "kind": "video",
    "prompt": "test",
    "cfgScale": 4,
    "firstFrame": "https://example.com/a.jpg",
    "allowMatureContent": True,
})
print("wan whatif", st, "input", w.get("submittedInput"), "svc", w.get("service"), "err", str(w)[:240] if st>=400 else "")
st, m = post("/api/whatif", {
    "serviceId": "video/minimax-h3-comfy/imageToVideo",
    "kind": "video",
    "prompt": "zxtp_c1ub",
    "firstFrame": "https://example.com/a.jpg",
    "allowMatureContent": True,
})
print("minimax whatif", st, "input", m.get("submittedInput"))
st, l = post("/api/whatif", {
    "serviceId": "video/ltx2.5/firstLastFrameToVideo",
    "kind": "video",
    "prompt": "test",
    "firstFrame": "https://example.com/a.jpg",
    "lastFrame": "https://example.com/b.jpg",
    "allowMatureContent": True,
})
print("ltx whatif", st, "input", l.get("submittedInput"))
