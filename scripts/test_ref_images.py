#!/usr/bin/env python3
"""Hard-gate: multi-ref clamp + i2v primary frame."""
from providers.ref_images import payload_ref_images, primary_frame, max_refs
from providers.capabilities import get_provider_capabilities as gc


def main():
    assert max_refs("nano-gpt", gc("nano-gpt")) == 5
    assert max_refs("modelscope-ai", gc("modelscope-ai")) == 1
    assert max_refs("fal", gc("fal")) == 9
    refs = payload_ref_images(
        {
            "firstFrame": "https://ex/1.png",
            "images": [f"https://ex/{i}.png" for i in range(2, 10)],
        },
        backend="nano-gpt",
        caps=gc("nano-gpt"),
    )
    assert len(refs) == 5 and refs[0].endswith("/1.png"), refs
    assert primary_frame({"sourceImage": "https://ex/ff.png"}) == "https://ex/ff.png"
    # raise blocked via caps
    raised = max_refs("nano-gpt", caps={"maxRefs": 99}, default=5)
    # max_refs takes min(candidates, prov_default) — 99 candidate then min with 5
    assert raised == 5, raised
    from providers import fal as fal_mod
    fin = fal_mod.build_fal_input(
        {
            "serviceId": "fal-ai/flux/dev/image-to-image",
            "prompt": "x",
            "firstFrame": "https://ex/a.png",
            "images": ["https://ex/b.png", "https://ex/c.png"],
        }
    )
    if "image_urls" in fin:
        assert len(fin["image_urls"]) >= 2, fin
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
    print("PASS ref_images")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
