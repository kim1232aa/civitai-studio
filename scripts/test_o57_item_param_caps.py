#!/usr/bin/env python3
"""o57: item-level param match contract for 魔搭 + Civitai.

Official schema → supportsLora / loraShape / durationEnum.
Never invent 5/12/16. Never guess LoRA from the word edit.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from providers.capabilities import (  # noqa: E402
    merge_catalog_override,
    overlay_civitai_catalog_item,
    overlay_modelscope_catalog_item,
)


def check(cond, msg):
    if not cond:
        raise AssertionError(msg)


def main():
    qwen = overlay_modelscope_catalog_item({"id": "Qwen/Qwen-Image", "task": "text-to-image", "tags": ["t2i"], "category": "image"})
    check(qwen["supportsLora"] is True, qwen)
    check(qwen["capabilities"]["loraShape"] == "hub_repo", qwen)
    check(qwen["capabilities"]["loraSource"] == "official-aigc-keys", qwen)
    check("durationEnum" not in qwen["capabilities"], "must not invent durationEnum")

    video = overlay_modelscope_catalog_item({"id": "krea/krea-realtime-video", "task": "text-to-video", "tags": ["t2v"], "category": "video"})
    check(video["supportsLora"] is False, video)
    check(video["capabilities"]["loraShape"] == "hub_repo", video)

    unknown = overlay_modelscope_catalog_item({"id": "someone/cool-edit-model"})
    ucaps = unknown.get("capabilities") if isinstance(unknown.get("capabilities"), dict) else {}
    check("supportsLora" not in ucaps, "unknown mid must not invent supportsLora")
    check(unknown.get("supportsLora") is None, "unknown row.supportsLora stays unset")

    comfy = overlay_civitai_catalog_item({
        "id": "image/comfy/krea2/turbo/createImage",
        "engine": "comfy",
        "ecosystem": "krea2",
        "model": "turbo",
    })
    check(comfy["supportsLora"] is True, comfy)
    check(comfy["capabilities"]["loraShape"] == "air", comfy)

    schema = overlay_civitai_catalog_item({
        "id": "image/sdxl/createImage",
        "engine": "other",
        "parameters": {"loras": {}, "engine": "other"},
    })
    check(schema["supportsLora"] is True, schema)
    check(schema["capabilities"]["loraSource"] == "orch-v2-services", schema)

    fal_krea = overlay_civitai_catalog_item({
        "id": "image/fal/krea2/createImage",
        "engine": "fal",
        "model": "krea2",
        "parameters": {"engine": "fal", "model": "krea2"},
    })
    check(fal_krea["supportsLora"] is False, fal_krea)
    check(fal_krea["capabilities"]["loraShape"] == "none", fal_krea)
    check(fal_krea["capabilities"]["loraSource"] == "official-fal-krea-recipe-no-lora", fal_krea)

    no_enum = overlay_civitai_catalog_item({"id": "video/unknown/createVideo", "engine": "other"})
    check("durationEnum" not in (no_enum.get("capabilities") or {}), "no invented 5/12/16")

    with_enum = overlay_civitai_catalog_item({
        "id": "video/kling/createVideo",
        "engine": "other",
        "parameters": {"duration": {"enum": ["5", "10"]}},
    })
    check(with_enum["capabilities"]["durationEnum"] == ["5", "10"], with_enum)

    merged = merge_catalog_override(
        {"lora": "air", "loraConfidence": "official", "maxRefs": 9},
        {"supportsLora": False, "durationEnum": ["5", "10"], "loraShape": "none"},
    )
    check(merged["supportsLora"] is False, merged)
    check(merged["durationEnum"] == ["5", "10"], merged)
    check(merged["loraShape"] == "none", merged)

    print("PASS o57_item_param_caps")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
