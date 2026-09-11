#!/usr/bin/env python3
"""o57: Provider.catalog HTTP rows get official overlay stamps."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from providers.capabilities import overlay_civitai_catalog_item  # noqa: E402
from providers.catalog_stamp import (  # noqa: E402
    install_catalog_stamps,
    overlay_provider_catalog,
)
from providers.hf_catalog_caps import overlay_huggingface_catalog_item  # noqa: E402


def check(cond, msg):
    if not cond:
        raise AssertionError(msg)


class _Fake:
    def __init__(self, pid, body):
        self.id = pid
        self._body = body

    def catalog(self, q="", category="", status="", page=1, pageSize=50):
        return dict(self._body)


def main():
    comfy_body = {
        "items": [{
            "id": "image/comfy/krea2/turbo/createImage",
            "engine": "comfy",
            "model": "turbo",
        }]
    }
    stamped = overlay_provider_catalog("civitai", comfy_body)
    check(stamped["items"][0]["supportsLora"] is True, stamped)
    check(stamped["items"][0]["capabilities"]["loraShape"] == "air", stamped)

    fal_krea = overlay_provider_catalog("civitai", {
        "items": [{
            "id": "image/fal/krea2/createImage",
            "engine": "fal",
            "model": "krea2",
            "parameters": {"engine": "fal", "model": "krea2"},
        }]
    })
    check(fal_krea["items"][0]["supportsLora"] is False, fal_krea)

    ms = overlay_provider_catalog("modelscope-cn", {
        "items": [{"id": "Qwen/Qwen-Image", "task": "text-to-image", "tags": ["t2i"], "category": "image"}]
    })
    check(ms["items"][0]["supportsLora"] is True, ms)
    check(ms["items"][0]["capabilities"]["loraShape"] == "hub_repo", ms)

    hf_blocked = overlay_huggingface_catalog_item({
        "id": "fal-ai/flux-lora",
        "tags": ["lora"],
    })
    check(hf_blocked["supportsLora"] is False, hf_blocked)
    check(hf_blocked["capabilities"]["loraChannel"] == "blocked", hf_blocked)

    hf_fal = overlay_huggingface_catalog_item(
        {"id": "black-forest-labs/FLUX.1-dev"},
        mapped_style_name="fal",
    )
    check(hf_fal["supportsLora"] is True, hf_fal)
    check(hf_fal["capabilities"]["loraConfidence"] == "unverified", hf_fal)
    check(hf_fal["capabilities"]["loraChannel"] == "fal", hf_fal)

    fake = _Fake("civitai", comfy_body)
    install_catalog_stamps({"civitai": fake})
    out = fake.catalog("", "", "")
    check(out["items"][0]["supportsLora"] is True, out)
    check(getattr(fake, "_o57_stamped") is True, "idempotent flag")
    install_catalog_stamps({"civitai": fake})
    out2 = fake.catalog("", "", "")
    check(out2["items"][0]["supportsLora"] is True, out2)

    row = overlay_civitai_catalog_item({
        "id": "video/unknown/createVideo",
        "engine": "other",
    })
    check("durationEnum" not in (row.get("capabilities") or {}), "no invented 5/12/16")

    print("PASS o57_catalog_http_stamp")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
