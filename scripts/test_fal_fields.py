#!/usr/bin/env python3
import sys
sys.path.insert(0, "/workspace/civitai-studio")
import fal_api

payload = {
    "prompt": "test",
    "firstFrame": "https://x/a.jpg",
    "lastFrame": "https://x/b.jpg",
    "aspectRatio": "16:9",
    "duration": 5,
    "audioUrl": "https://x/a.mp3",
    "videoUrl": "https://x/v.mp4",
    "images": ["https://x/a.jpg", "https://x/c.jpg"],
}

cases = {
    "fal-ai/flux/schnell": {"prompt"},
    "fal-ai/flux/dev/image-to-image": {"prompt", "image_url"},
    "fal-ai/flux-2/edit": {"prompt", "image_urls"},
    "fal-ai/kling-video/v3/pro/image-to-video": {"prompt", "start_image_url", "end_image_url", "duration"},
    "fal-ai/kling-video/v2.5-turbo/pro/image-to-video": {"prompt", "image_url", "tail_image_url", "duration"},
    "fal-ai/kling-video/v2.5-turbo/standard/image-to-video": {"prompt", "image_url", "duration"},
    "fal-ai/kling-video/v2.1/pro/image-to-video": {"prompt", "image_url", "tail_image_url", "duration"},
    "fal-ai/kling-video/v3/turbo/pro/image-to-video": {"prompt", "image_url", "duration"},
    "minimax/h3/image-to-video": {"prompt", "image_url", "end_image_url", "duration"},
    "fal-ai/wan/v2.2-a14b/image-to-video": {"prompt", "image_url", "end_image_url", "aspect_ratio"},
    "alibaba/wan-3.0/image-to-video": {"prompt", "start_image_url", "end_image_url", "duration", "aspect_ratio"},
    "fal-ai/veo3.1/first-last-frame-to-video": {"prompt", "first_frame_url", "last_frame_url", "duration", "aspect_ratio"},
    "fal-ai/sora-2/image-to-video": {"prompt", "image_url", "duration", "aspect_ratio"},
    "fal-ai/kling-video/o3/standard/image-to-video": {"prompt", "image_url", "end_image_url", "duration"},
    "fal-ai/kling-video/o3/pro/reference-to-video": {"prompt", "start_image_url", "end_image_url", "image_urls", "duration", "aspect_ratio"},
    "fal-ai/kling-video/o3/4k/image-to-video": {"prompt", "image_url", "end_image_url", "duration"},
    "fal-ai/minimax/hailuo-02/standard/image-to-video": {"prompt", "image_url", "end_image_url", "duration"},
    "fal-ai/minimax/hailuo-2.3/standard/image-to-video": {"prompt", "image_url", "duration"},
    "fal-ai/minimax/hailuo-2.3-fast/standard/image-to-video": {"prompt", "image_url", "duration"},
    "fal-ai/minimax/hailuo-02-fast/image-to-video": {"prompt", "image_url", "duration"},
    "fal-ai/kling-video/v3/4k/image-to-video": {"prompt", "start_image_url", "end_image_url", "duration"},
    "fal-ai/kling-video/v3/turbo/standard/image-to-video": {"prompt", "image_url", "duration"},
    "fal-ai/kling-video/o3/4k/reference-to-video": {"prompt", "start_image_url", "end_image_url", "image_urls", "duration", "aspect_ratio"},
    "fal-ai/minimax/hailuo-2.3-fast/pro/image-to-video": {"prompt", "image_url"},
    "lightricks/ltx-2.5/image-to-video/fast": {"prompt", "image_url", "end_image_url", "duration", "aspect_ratio"},
    "lightricks/ltx-2.5/audio-to-video/fast": {"prompt", "image_url", "audio_url", "aspect_ratio"},
    "fal-ai/veo3.1/lite/image-to-video": {"prompt", "image_url", "duration", "aspect_ratio"},
    "fal-ai/veo3.1/lite/first-last-frame-to-video": {"prompt", "first_frame_url", "last_frame_url", "duration", "aspect_ratio"},
    "fal-ai/veo3.1/reference-to-video": {"prompt", "image_urls", "duration", "aspect_ratio"},
    "fal-ai/runway-gen3/turbo/image-to-video": {"prompt", "image_url", "end_image_url", "duration", "ratio"},
    "fal-ai/runway-gen3/turbo/text-to-video": {"prompt"},
    "fal-ai/imagen4/preview": {"prompt"},
    "fal-ai/imagen4/preview/fast": {"prompt"},
    "fal-ai/imagen4/preview/ultra": {"prompt"},
}

fail = 0
for eid, expect in cases.items():
    p = dict(payload, serviceId=eid)
    inp = fal_api.build_fal_input(p)
    keys = set(inp)
    extra = keys - expect
    missing = expect - keys
    # imagen4 / runway T2V must not invent image fields
    if "imagen4" in eid or eid.endswith("text-to-video"):
        img_keys = {k for k in keys if "image" in k or k in ("first_frame_url", "last_frame_url")}
        if img_keys:
            print("FAIL invented", eid, img_keys)
            fail += 1
            continue
    if extra or missing:
        print("FAIL", eid, "got", {k: inp[k] for k in inp if k != "prompt"}, "missing", missing, "extra", extra)
        fail += 1
    else:
        print("ok", eid, "=>", sorted(k for k in keys if k != "prompt"))

# ratio vs aspect_ratio on runway
rw = fal_api.build_fal_input(dict(payload, serviceId="fal-ai/runway-gen3/turbo/image-to-video"))
assert "ratio" in rw and "aspect_ratio" not in rw, rw

# hailuo 2.3 must not send end_image_url
h = fal_api.build_fal_input(dict(payload, serviceId="fal-ai/minimax/hailuo-2.3/standard/image-to-video"))
assert "end_image_url" not in h, h

# LoRA: /lora endpoints get loras[{path,scale}], AIR is dropped, scale clipped 0-2
lora_pl = dict(payload, serviceId="fal-ai/z-image/turbo/lora", loras=[
    {"path": "https://civitai.com/api/download/models/3184845", "strength": 0.8, "name": "Kroma"},
    {"air": "urn:air:krea2:lora:civitai:2823254@3184845", "strength": 0.8, "name": "AIR only"},
    {"path": "XLabs-AI/flux-lora-collection", "scale": 5},
])
lz = fal_api.build_fal_input(lora_pl)
assert "loras" in lz, lz
assert lz["loras"] == [
    {"path": "https://civitai.com/api/download/models/3184845", "scale": 0.8},
    {"path": "XLabs-AI/flux-lora-collection", "scale": 2.0},
], lz["loras"]
# flux-lora uses optional loras
lf = fal_api.build_fal_input(dict(lora_pl, serviceId="fal-ai/flux-lora"))
assert lf.get("loras") == lz["loras"], lf
# schnell must not grow a loras field from leftover payload
ls = fal_api.build_fal_input(dict(lora_pl, serviceId="fal-ai/flux/schnell"))
assert "loras" not in ls, ls
# AIR-only must not become path
air_only = fal_api.build_fal_input({
    "serviceId": "fal-ai/z-image/turbo/lora",
    "prompt": "x",
    "loras": [{"air": "urn:air:sdxl:lora:civitai:1@2", "strength": 1}],
})
assert "loras" not in air_only, air_only

from providers.fal import overlay_image_fields, infer_image_fields
ov = overlay_image_fields({"id": "fal-ai/kling-video/v3/pro/image-to-video", "category": "video", "falCategory": "image-to-video"})
assert ov.get("needsSource") is False, ov
assert ov.get("needsFirstFrame") is True, ov
assert "end_image_url" in (ov.get("imageFields") or []), ov
ov2 = overlay_image_fields({"id": "fal-ai/kling-video/o3/pro/reference-to-video", "category": "video", "falCategory": "reference-to-video"})
assert ov2.get("needsSource") is False, ov2
assert "image_urls" in (ov2.get("imageFields") or []), ov2
assert "end_image_url" in (ov2.get("imageFields") or []), ov2
ov3 = overlay_image_fields({"id": "fal-ai/z-image/turbo/lora", "category": "image", "falCategory": "text-to-image", "tags": ["lora"]})
assert ov3.get("supportsLora") is True, ov3
assert ov3.get("needsSource") in (False, None) or ov3.get("needsSource") is False
ov4 = overlay_image_fields({"id": "fal-ai/flux-2/edit", "category": "image", "falCategory": "image-to-image"})
assert "image_urls" in (ov4.get("imageFields") or infer_image_fields("fal-ai/flux-2/edit")), ov4
assert ov4.get("needsSource") is False, ov4

print("catalog", len(fal_api.load_catalog()))
print("FAIL" if fail else "PASS", fail)
sys.exit(1 if fail else 0)
