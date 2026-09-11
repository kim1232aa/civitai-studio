#!/usr/bin/env python3
"""Official Civitai LoRA payload shape by recipe."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from providers.civitai_lora_shape import (  # noqa: E402
    lora_shape_for_recipe,
    official_lora_payload,
    reshape_workflow_loras,
)

AIR = "urn:air:krea2:lora:civitai:2323765@3071582"
MAP = {AIR: 0.8}


def check(cond, msg):
    if not cond:
        raise AssertionError(msg)


def main():
    check(lora_shape_for_recipe("comfy", "turbo", "krea2", "createImage") == "map", "comfy-krea2")
    check(lora_shape_for_recipe("flux2", "klein") == "map", "flux2 klein")
    check(lora_shape_for_recipe("flux2", "dev") == "array", "flux2 dev")
    check(lora_shape_for_recipe("flux2", "flex") == "none", "flux2 flex")
    check(lora_shape_for_recipe("fal", "krea2") == "none", "fal-krea")
    check(lora_shape_for_recipe("wan", "v2.2", "wan") == "array", "wan image")
    check(lora_shape_for_recipe("ltx2.3", "22b-distilled") == "map", "ltx2 map")
    check(lora_shape_for_recipe("hunyuan", "imageToVideo") == "array", "hunyuan")

    comfy = official_lora_payload(MAP, engine="comfy", model="turbo", ecosystem="krea2")
    check(comfy == MAP, comfy)

    dev = official_lora_payload(MAP, engine="flux2", model="dev")
    check(dev == [{"air": AIR, "strength": 0.8}], dev)

    hunyuan = official_lora_payload([{"air": AIR, "strength": 0.5}], engine="hunyuan")
    check(hunyuan == [{"air": AIR, "strength": 0.5}], hunyuan)

    try:
        official_lora_payload(MAP, engine="fal", model="krea2")
        raise AssertionError("fal-krea must reject LoRA")
    except ValueError as e:
        check("不接 LoRA" in str(e), e)

    wf = reshape_workflow_loras({
        "steps": [{
            "$type": "imageGen",
            "input": {
                "engine": "flux2",
                "model": "dev",
                "loras": MAP,
            },
        }]
    })
    check(wf["steps"][0]["input"]["loras"] == [{"air": AIR, "strength": 0.8}], wf)

    comfy_wf = reshape_workflow_loras({
        "steps": [{
            "$type": "imageGen",
            "input": {
                "engine": "comfy",
                "ecosystem": "krea2",
                "model": "turbo",
                "loras": MAP,
            },
        }]
    })
    check(comfy_wf["steps"][0]["input"]["loras"] == MAP, comfy_wf)

    print("PASS o57_civitai_lora_shape")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
