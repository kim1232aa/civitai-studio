#!/usr/bin/env python3
import json
from pathlib import Path
raw = json.loads(Path("/tmp/fal-models-raw.json").read_text())
models = raw.get("models") or raw
out = []
for it in models:
    md = it.get("metadata") or {}
    eid = it.get("endpoint_id") or ""
    fcat = md.get("category") or ""
    blob = (eid + " " + fcat + " " + (md.get("display_name") or "")).lower()
    if "upscale" in blob or "upscaler" in blob:
        recipe, step = "upscale", "upscale"
    elif "background" in blob or "bria/background" in blob:
        recipe, step = "bg", "bg"
    elif "3d" in fcat or "3d" in blob:
        recipe, step = "3d", "3d"
    elif "audio" in fcat or "speech" in fcat or fcat in ("text-to-audio", "text-to-speech", "audio-to-audio"):
        recipe, step = "audio", "audio"
    elif "video" in fcat:
        recipe, step = "video", "videoGen"
    elif fcat in ("text-to-image", "image-to-image") or "image" in fcat:
        recipe, step = "image", "imageGen"
    else:
        recipe, step = "other", fcat or "other"
    st = md.get("status") or "unknown"
    status = "available" if st == "active" else ("degraded" if st in ("deprecated",) else st)
    out.append({
        "id": eid,
        "name": md.get("display_name") or eid,
        "description": (md.get("description") or "").strip(),
        "category": recipe if recipe != "other" else "image",
        "falCategory": fcat,
        "status": status if status in ("available", "degraded", "unavailable") else "unknown",
        "step": step,
        "backend": "fal",
        "tags": md.get("tags") or [],
        "needsSource": fcat in ("image-to-image", "image-to-video", "image-to-3d", "video-to-video") or "edit" in eid or "image-to-video" in eid,
        "needsFirstFrame": "image-to-video" in fcat or "image-to-video" in eid,
    })
Path("/workspace/civitai-studio/docs/fal-models.json").write_text(json.dumps({"total": len(out), "items": out}, ensure_ascii=False))
from collections import Counter
print("total", len(out), Counter(x["category"] for x in out), Counter(x["status"] for x in out))
