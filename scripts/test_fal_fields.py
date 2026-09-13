#!/usr/bin/env python3
import sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))
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
# lead 裁决(对齐 fail-closed 现行语义): 每端点只喂官方 schema 期望的键, 脏超集会被诚实拒绝
_VALUE_POOL = {
    "prompt": "test",
    "firstFrame": "https://x/a.jpg",
    "lastFrame": "https://x/b.jpg",
    "aspectRatio": "16:9",
    "duration": 5,
    "audioUrl": "https://x/a.mp3",
    "videoUrl": "https://x/v.mp4",
    "images": ["https://x/a.jpg", "https://x/c.jpg"],
}
# fal 出站键 ↔ 入站 payload 键映射
_IN_FOR_OUT = {
    "prompt": "prompt",
    "image_url": "firstFrame",
    "start_image_url": "firstFrame",
    "first_frame_url": "firstFrame",
    "end_image_url": "lastFrame",
    "tail_image_url": "lastFrame",
    "last_frame_url": "lastFrame",
    "image_urls": "images",
    "duration": "duration",
    "aspect_ratio": "aspectRatio",
    "ratio": "aspectRatio",
    "audio_url": "audioUrl",
    "video_url": "videoUrl",
}
for eid, expect in cases.items():
    p = {"serviceId": eid}
    for out_key in expect:
        src = _IN_FOR_OUT.get(out_key)
        if src and src in _VALUE_POOL:
            p[src] = _VALUE_POOL[src]
    try:
        inp = fal_api.build_fal_input(p)
    except ValueError as exc:
        if ("超过上限" in str(exc) or "拒绝截断" in str(exc)) and "images" in p:
            # 端点帽小于 2(如 maxRefs=1): 降到 1 张再验形状
            p["images"] = p["images"][:1]
            inp = fal_api.build_fal_input(p)
        else:
            raise
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
# lead 裁决(fail-closed): 脏超集 payload 会被诚实拒绝, 用干净 payload 验字段映射
rw = fal_api.build_fal_input({"serviceId": "fal-ai/runway-gen3/turbo/image-to-video", "prompt": "test", "firstFrame": "https://x/a.jpg", "aspectRatio": "16:9"})
assert "ratio" in rw and "aspect_ratio" not in rw, rw

# hailuo 2.3 must not send end_image_url
h = fal_api.build_fal_input({"serviceId": "fal-ai/minimax/hailuo-2.3/standard/image-to-video", "prompt": "test", "firstFrame": "https://x/a.jpg", "lastFrame": "https://x/b.jpg"})
assert "end_image_url" not in h, h

# LoRA: /lora endpoints get loras[{path,scale}], AIR is dropped, scale clipped 0-2
# lead 裁决(fail-closed): 干净 payload, 不混脏参考图
lora_pl = {"serviceId": "fal-ai/z-image/turbo/lora", "prompt": "test", "loras": [
    {"path": "https://civitai.com/api/download/models/3184845", "strength": 0.8, "name": "Kroma"},
    {"air": "urn:air:krea2:lora:civitai:2823254@3184845", "strength": 0.8, "name": "AIR only"},
    {"path": "XLabs-AI/flux-lora-collection", "scale": 5},
]}
lz = fal_api.build_fal_input(lora_pl)
assert "loras" in lz, lz
# lead 裁决(对齐 lora_air_resolve 现行正确行为): AIR 解析为下载直链不丢; scale 原样透传不发明 0-2 截断
assert lz["loras"] == [
    {"path": "https://civitai.com/api/download/models/3184845", "scale": 0.8},
    {"path": "https://civitai.com/api/download/models/3184845", "scale": 0.8},
    {"path": "XLabs-AI/flux-lora-collection", "scale": 5.0},
], lz["loras"]
# flux-lora uses optional loras
lf = fal_api.build_fal_input(dict(lora_pl, serviceId="fal-ai/flux-lora"))
assert lf.get("loras") == lz["loras"], lf
# lead 裁决(fail-closed): schnell 不吃 LoRA 时必须硬拒, 不静默丢
try:
    fal_api.build_fal_input(dict(lora_pl, serviceId="fal-ai/flux/schnell"))
    raise SystemExit("schnell with loras must raise, not silently drop")
except ValueError as exc:
    assert "不接受 LoRA" in str(exc), exc
# lead 裁决: AIR-only 现在解析为下载直链(不丢不发明)
air_only = fal_api.build_fal_input({
    "serviceId": "fal-ai/z-image/turbo/lora",
    "prompt": "x",
    "loras": [{"air": "urn:air:sdxl:lora:civitai:1@2", "strength": 1}],
})
assert air_only.get("loras") and air_only["loras"][0]["path"].endswith("/models/2"), air_only

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
