#!/usr/bin/env python3
"""Hard-gate: multi-ref clamp + i2v primary frame."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from providers.ref_images import (  # noqa: E402
    payload_ref_images,
    primary_frame,
    max_refs,
    collect_ref_images,
    enforce_ref_cap,
    declared_max_refs,
    materialize_local_ref,
)
from providers.capabilities import get_provider_capabilities as gc


def main():
    assert max_refs("nano-gpt", gc("nano-gpt")) == 5
    assert max_refs("modelscope-ai", gc("modelscope-ai")) == 1
    assert max_refs("fal", gc("fal")) == 9
    raw = collect_ref_images(
        {
            "firstFrame": "https://ex/1.png",
            "images": [f"https://ex/{i}.png" for i in range(2, 10)],
        }
    )
    assert len(raw) == 9 and raw[0].endswith("/1.png"), raw
    raised_over = False
    try:
        enforce_ref_cap(raw, backend="nano-gpt", caps=gc("nano-gpt"))
    except ValueError as exc:
        raised_over = "超过上限" in str(exc) or "拒绝截断" in str(exc)
    assert raised_over, "nano 9 refs must fail, not slice to 5"
    ok_refs = payload_ref_images(
        {
            "firstFrame": "https://ex/1.png",
            "images": [f"https://ex/{i}.png" for i in range(2, 5)],
        },
        backend="nano-gpt",
        caps=gc("nano-gpt"),
    )
    assert len(ok_refs) == 4 and ok_refs[0].endswith("/1.png"), ok_refs
    assert primary_frame({"sourceImage": "https://ex/ff.png"}) == "https://ex/ff.png"
    # raise blocked via caps
    raised = max_refs("nano-gpt", caps={"maxRefs": 99}, default=5)
    # max_refs takes min(candidates, prov_default) — 99 candidate then min with 5
    assert raised == 5, raised
    from providers import fal as fal_mod
    over_single = False
    try:
        fal_mod.build_fal_input(
            {
                "serviceId": "fal-ai/flux/dev/image-to-image",
                "prompt": "x",
                "firstFrame": "https://ex/a.png",
                "images": ["https://ex/b.png", "https://ex/c.png"],
            }
        )
    except ValueError as exc:
        over_single = "超过上限" in str(exc) or "拒绝截断" in str(exc) or "上限未知" in str(exc)
    assert over_single, "single-slot fal i2i must not silent-drop extra refs"
    fin = fal_mod.build_fal_input(
        {
            "serviceId": "fal-ai/flux/dev/image-to-image",
            "prompt": "x",
            "firstFrame": "https://ex/a.png",
            "images": ["https://ex/a.png"],
        }
    )
    if "image_urls" in fin:
        assert len(fin["image_urls"]) == 1, fin
    elif "image_url" in fin:
        assert fin["image_url"]
    # Canvas packs field names — must not require payload.images
    only_urls = payload_ref_images(
        {"image_urls": ["https://ex/a.png", "https://ex/b.png", "https://ex/c.png"]},
        backend="fal",
        caps=gc("fal"),
    )
    assert only_urls == ["https://ex/a.png", "https://ex/b.png", "https://ex/c.png"], only_urls
    only_refs = payload_ref_images(
        {"input_references": ["https://ex/1.png", "https://ex/2.png"]},
        backend="nano-gpt",
        caps=gc("nano-gpt"),
    )
    assert only_refs == ["https://ex/1.png", "https://ex/2.png"], only_refs
    local_payload = {
        "sourceImage": "/out/upload_20260909150943_1.jpg",
        "images": ["/out/upload_20260909150943_1.jpg", "/out/upload_20260909150949_1.jpg"],
    }
    local_refs = collect_ref_images(local_payload)
    assert local_refs == [
        "/out/upload_20260909150943_1.jpg",
        "/out/upload_20260909150949_1.jpg",
    ], local_refs
    out_file = ROOT / "out" / "upload_20260909150943_1.jpg"
    if out_file.is_file():
        data = materialize_local_ref("/out/upload_20260909150943_1.jpg")
        assert data.startswith("data:image/"), data[:40]
    try:
        materialize_local_ref("/out/does-not-exist-xyz.jpg")
        raise AssertionError("missing /out must raise")
    except ValueError as e:
        assert "无法读取" in str(e), e
    from providers.ref_images import normalize_payload_refs
    raw = {"image_urls": ["https://ex/a.png", "https://ex/b.png"]}
    normalize_payload_refs(raw)
    assert raw["images"] == ["https://ex/a.png", "https://ex/b.png"]
    assert raw["image_urls"] == ["https://ex/a.png", "https://ex/b.png"]  # keep canvas field
    # image_urls-only fal edit endpoint
    fin = fal_mod.build_fal_input(
        {
            "serviceId": "fal-ai/flux-2-pro/edit",
            "prompt": "x",
            "image_urls": ["https://ex/a.png", "https://ex/b.png", "https://ex/c.png"],
        }
    )
    assert fin.get("image_urls") and len(fin["image_urls"]) == 3, fin
    
    # fal single maxRefs
    from providers.fal import overlay_image_fields
    single = overlay_image_fields({"id": "fal-ai/flux/dev/image-to-image", "name": "x"})
    assert single["maxRefs"] == 1 and single["capabilities"]["maxRefs"] == 1, single
    multi = overlay_image_fields({"id": "fal-ai/flux-2-pro/edit", "imageFields": ["image_urls"]})
    assert multi["maxRefs"] == 9, multi
    assert max_refs("fal", gc("fal"), item=single) == 1
    unknown_video = {"id": "fal-ai/mystery-i2v", "category": "video", "name": "mystery"}
    assert declared_max_refs(unknown_video) is None
    assert max_refs("fal", gc("fal"), item=unknown_video) is None, "unknown model cap is not provider 9"
    unknown_raised = False
    try:
        enforce_ref_cap(
            ["https://ex/a.png", "https://ex/b.png"],
            backend="fal",
            caps=gc("fal"),
            item=unknown_video,
        )
    except ValueError as exc:
        unknown_raised = "上限未知" in str(exc)
    assert unknown_raised, "unknown cap must fail, not slice"
    civ_cap = {
        "raw": {"id": "image/comfy/boogu/edit/editImage"},
        "frameFields": ["images"],
        "constraints": {"images": {"type": "array", "minItems": 1, "maxItems": 2}},
    }
    assert declared_max_refs(civ_cap) == 2
    assert max_refs("civitai", gc("civitai"), item=civ_cap) == 2
    
    # Fal t2v must not advertise i2v / first frame
    from providers.fal import overlay_image_fields as _ov
    t2v = _ov({"id": "fal-ai/minimax/video-01", "category": "video", "falCategory": "text-to-video"})
    assert t2v.get("needsFirstFrame") is False and t2v.get("supportsI2v") is False, t2v
    i2v = _ov({"id": "fal-ai/minimax/video-01/image-to-video", "category": "video", "falCategory": "image-to-video"})
    assert i2v.get("needsFirstFrame") is True and i2v.get("supportsI2v") is True, i2v
    print("PASS ref_images")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
