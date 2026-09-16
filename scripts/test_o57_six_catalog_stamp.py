#!/usr/bin/env python3
"""o57: all six backends stamp catalog rows from official schema only."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from providers.catalog_stamp import overlay_provider_catalog  # noqa: E402
from providers.six_catalog_caps import (  # noqa: E402
    overlay_fal_catalog_item,
    overlay_nano_catalog_item,
)


def check(cond, msg):
    if not cond:
        raise AssertionError(msg)


def main():
    comfy = overlay_provider_catalog("civitai", {
        "items": [{"id": "image/comfy/krea2/turbo/createImage", "engine": "comfy", "model": "turbo"}]
    })
    check(comfy["items"][0]["supportsLora"] is True, comfy)
    check(comfy["items"][0]["capabilities"]["loraShape"] == "air", comfy)

    fal_krea = overlay_provider_catalog("civitai", {
        "items": [{
            "id": "image/fal/krea2/createImage",
            "engine": "fal",
            "model": "krea2",
            "parameters": {"engine": "fal", "model": "krea2"},
        }]
    })
    check(fal_krea["items"][0]["supportsLora"] is False, fal_krea)

    ms = overlay_provider_catalog("modelscope-ai", {
        "items": [{"id": "Qwen/Qwen-Image", "task": "text-to-image", "tags": ["t2i"], "category": "image"}]
    })
    check(ms["items"][0]["supportsLora"] is True, ms)
    check(ms["items"][0]["capabilities"]["loraShape"] == "hub_repo", ms)

    video_ms = overlay_provider_catalog("modelscope-cn", {
        "items": [{"id": "krea/krea-realtime-video", "task": "text-to-video", "tags": ["t2v"], "category": "video"}]
    })
    check(video_ms["items"][0]["supportsLora"] is False, video_ms)

    hf = overlay_provider_catalog("huggingface", {"items": [{"id": "black-forest-labs/FLUX.1-dev"}]})
    check(hf["items"][0].get("supportsLora") is None, "HF without mapping must not invent true")
    check(hf["items"][0]["capabilities"]["loraConfidence"] == "unverified", hf)

    fal_lora = overlay_fal_catalog_item({"id": "fal-ai/flux-lora", "supportsLora": True})
    check(fal_lora["supportsLora"] is True, fal_lora)
    check(fal_lora["capabilities"]["loraShape"] == "path", fal_lora)

    fal_enum = overlay_fal_catalog_item({
        "id": "fal-ai/kling-video",
        "parameters": {"duration": {"enum": ["5", "10"]}},
    })
    check(fal_enum["capabilities"]["durationEnum"] == ["5", "10"], fal_enum)

    fal_plain = overlay_fal_catalog_item({"id": "fal-ai/flux/dev"})
    check("durationEnum" not in (fal_plain.get("capabilities") or {}), "no invented 5/12/16")
    check(fal_plain.get("supportsLora") is None, "plain flux/dev must not invent supportsLora")

    nano_lora = overlay_nano_catalog_item({"id": "z-image-turbo-lora", "tags": ["lora"]})
    check(nano_lora["supportsLora"] is True, nano_lora)
    check(nano_lora["capabilities"]["loraSource"] == "heuristic", nano_lora)

    nano_res = overlay_nano_catalog_item({
        "id": "hidream",
        "supported_parameters": {"resolutions": ["1024x1024", "1376x768"]},
    })
    check(nano_res["capabilities"]["resolutionTokens"] == ["1024x1024", "1376x768"], nano_res)
    check(nano_res.get("supportsLora") is None, "hidream must not invent LoRA")
    check("promptMax" not in (nano_res.get("capabilities") or {}), "no invented 1200")

    nano_meta = overlay_nano_catalog_item({
        "id": "step-image-edit-2",
        "description": "Prompts are limited to 512 characters; negative prompts have the same limit.",
        "supported_parameters": {"resolutions": ["1024x1024"]},
    })
    check(nano_meta["capabilities"].get("promptMax") == 512, nano_meta)
    nano_chars = overlay_nano_catalog_item({
        "id": "qwen-image-3",
        "supported_parameters": {"max_chars": 800, "resolutions": ["1024x1024"]},
    })
    check(nano_chars["capabilities"].get("promptMax") == 800, nano_chars)

    nano_util = overlay_nano_catalog_item({"id": "image-upscale-lora-fix"})
    check(nano_util["supportsLora"] is False, nano_util)

    stamped = overlay_provider_catalog("nano-gpt", {"items": [{"id": "flux-lora"}]})
    check(stamped["items"][0]["supportsLora"] is True, stamped)

    stamped_fal = overlay_provider_catalog("fal", {"items": [{"id": "fal-ai/flux-lora"}]})
    check(stamped_fal["items"][0]["supportsLora"] is True, stamped_fal)

    print("PASS o57_six_catalog_stamp")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
