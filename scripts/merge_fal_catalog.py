#!/usr/bin/env python3
import json
from pathlib import Path
from collections import Counter

raw = json.loads(Path("/tmp/fal-models-raw.json").read_text())
src = raw.get("models") or raw
spec = json.loads(Path("/workspace/civitai-studio/docs/fal-models.json").read_text())
by_id = {m["id"]: m for m in (spec.get("models") or [])}

def recipe_of(eid, fcat, name):
    blob = (eid + " " + fcat + " " + name).lower()
    if "upscale" in blob:
        return "upscale", "upscale"
    if "background" in blob:
        return "bg", "bg"
    if "3d" in fcat or "/3d" in blob or "3d" in blob and "video" not in fcat:
        if "video" in fcat:
            return "video", "videoGen"
        return "3d", "3d"
    if "audio" in fcat or "speech" in fcat:
        return "audio", "audio"
    if "video" in fcat:
        return "video", "videoGen"
    if "image" in fcat:
        return "image", "imageGen"
    return "image", "imageGen"

items = []
for it in src:
    md = it.get("metadata") or {}
    eid = it.get("endpoint_id") or ""
    name = md.get("display_name") or eid
    fcat = md.get("category") or ""
    recipe, step = recipe_of(eid, fcat, name)
    spec_m = by_id.get(eid) or {}
    image_fields = spec_m.get("imageFields") or []
    needs_src = bool(image_fields) or fcat in ("image-to-image", "image-to-video", "image-to-3d", "video-to-video") or "/edit" in eid
    needs_ff = "image-to-video" in fcat or "image-to-video" in eid or "first-last" in eid
    items.append({
        "id": eid,
        "name": spec_m.get("title") or name,
        "description": (md.get("description") or spec_m.get("notes") or "").strip(),
        "category": recipe,
        "falCategory": fcat,
        "status": "available" if (md.get("status") or "active") == "active" else (md.get("status") or "unknown"),
        "step": step,
        "backend": "fal",
        "tags": md.get("tags") or [],
        "needsSource": needs_src and recipe in ("image", "bg", "upscale", "3d"),
        "needsFirstFrame": needs_ff,
        "imageFields": image_fields,
        "promptField": spec_m.get("promptField") or "prompt",
        "durationField": spec_m.get("durationField"),
        "aspectRatioField": spec_m.get("aspectRatioField"),
        "required": spec_m.get("required") or [],
        "optional": spec_m.get("optional") or [],
    })

out = {"total": len(items), "items": items, "openapiModels": len(by_id)}
Path("/workspace/civitai-studio/docs/fal-models.json").write_text(json.dumps(out, ensure_ascii=False))
# keep openapi spec aside
Path("/workspace/civitai-studio/docs/fal-openapi-models.json").write_text(json.dumps(spec, ensure_ascii=False))
print("items", len(items), "with fields", sum(1 for x in items if x["imageFields"]), Counter(x["category"] for x in items))
