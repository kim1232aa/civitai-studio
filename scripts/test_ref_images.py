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
    print("PASS ref_images")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
