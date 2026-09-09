#!/usr/bin/env python3
"""Offline NanoGPT parameter contracts."""
from __future__ import annotations

import ast
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from providers import nanogpt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SRC = (ROOT / "providers" / "nanogpt.py").read_text(encoding="utf-8")


def _pick_resolution_source() -> str:
    tree = ast.parse(SRC)
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "pick_resolution":
            return ast.get_source_segment(SRC, node) or ""
    raise AssertionError("pick_resolution not found")


def main() -> int:
    src = _pick_resolution_source()
    for banned in (
        'if "1k" in low or "2k" in low',
        "closest_aspect",
        "_FAL_SIZE",
        "parsed.sort(key=score)",
        'if "auto" in low',
        "return res[0]",
        "return parsed[0][2]",
        "square_hd",
        "area_d",
        "aspect_d",
        '"1k"',
        '"2k"',
        '"auto"',
    ):
        assert banned not in src, f"approximation remnant: {banned}"

    spec = {"supported_parameters": {"resolutions": ["1k", "1024*1536"]}}
    assert nanogpt.pick_resolution(spec, preferred="1k") == "1k"
    assert nanogpt.pick_resolution(spec, preferred="not-a-token") is None
    assert nanogpt.pick_resolution(spec, 1024, 1536) == "1024*1536"
    assert nanogpt.pick_resolution(spec, preferred="1024x1536") == "1024*1536"
    # 944×1672 is the sample size — not a catalog token and not exact WxH.
    assert nanogpt.pick_resolution(spec, 944, 1672) is None
    assert nanogpt.pick_resolution(spec, 1024, 1024) is None
    assert nanogpt.pick_resolution(spec, 2048, 2048) is None

    k_spec = {"supported_parameters": {"resolutions": ["1k", "2k"]}}
    assert nanogpt.pick_resolution(k_spec, 1024, 1024) is None
    assert nanogpt.pick_resolution(k_spec, 2048, 2048) is None
    assert nanogpt.pick_resolution(k_spec, preferred="2k") == "2k"
    assert nanogpt.pick_resolution(k_spec, 1024, 1024, preferred="1k") == "1k"

    ar_spec = {"supported_parameters": {"resolutions": ["1:1", "4:3", "2:3", "9:16"]}}
    assert nanogpt.pick_resolution(ar_spec, 960, 1440) is None
    assert nanogpt.pick_resolution(ar_spec, 1024, 1024) is None
    assert nanogpt.pick_resolution(ar_spec, preferred="2:3") == "2:3"

    zspec = {
        "supported_parameters": {
            "resolutions": [
                "256*256",
                "512*512",
                "768*768",
                "1024*1024",
                "1280*720",
                "720*1280",
                "1536*1024",
                "1024*1536",
                "1536*1536",
            ]
        }
    }
    assert nanogpt.pick_resolution(zspec, 960, 1440) is None
    assert nanogpt.pick_resolution(zspec, 1024, 1024) == "1024*1024"
    assert nanogpt.pick_resolution({"supported_parameters": {"resolutions": []}}, 1024, 1024) is None
    assert nanogpt.pick_resolution({}, 256, 256) is None
    assert nanogpt.pick_resolution(zspec, 944, 1672) is None
    assert nanogpt.pick_resolution(zspec) is None
    invented = nanogpt.pick_resolution({}, 944, 1672)
    assert invented is None
    assert invented != "944x1672"

    fal_spec = {
        "supported_parameters": {
            "resolutions": ["square_hd", "landscape_16_9", "portrait_16_9", "auto"]
        }
    }
    assert nanogpt.pick_resolution(fal_spec, 1024, 1024) is None
    assert nanogpt.pick_resolution(fal_spec, 1920, 1080) is None
    assert nanogpt.pick_resolution(fal_spec, preferred="square_hd") == "square_hd"
    assert nanogpt.pick_resolution(fal_spec, preferred="auto") == "auto"

    video_spec = {
        "id": "video-model",
        "category": "video",
        "task": "text-to-video",
        "supported_parameters": {},
    }
    with patch.object(nanogpt, "nano_key", return_value="offline-key"), patch.object(
        nanogpt, "find_spec", return_value=video_spec
    ), patch.object(
        nanogpt, "json_call", side_effect=AssertionError("video POST must be blocked")
    ):
        code, body = nanogpt.NanoGptProvider().generate(
            {"serviceId": "video-model", "prompt": "x", "kind": "video"}
        )
    assert code == 400, (code, body)
    assert "resolutions" in body["error"], body

    img_spec = {
        "id": "wavespeed-ai/krea-v2/turbo-lora",
        "category": "image",
        "task": "text-to-image",
        "supported_parameters": {"resolutions": ["1k", "2k"]},
    }
    with patch.object(nanogpt, "nano_key", return_value="offline-key"), patch.object(
        nanogpt, "find_spec", return_value=img_spec
    ), patch.object(
        nanogpt, "json_call", side_effect=AssertionError("image POST must be blocked")
    ):
        code, body = nanogpt.NanoGptProvider().generate(
            {
                "serviceId": "wavespeed-ai/krea-v2/turbo-lora",
                "prompt": "x",
                "width": 944,
                "height": 1672,
            }
        )
    assert code == 400, (code, body)
    assert "resolution" in body["error"].lower() or "分辨率" in body["error"], body

    with patch.object(nanogpt, "nano_key", return_value="offline-key"), patch.object(
        nanogpt, "find_spec", return_value=img_spec
    ), patch.object(
        nanogpt, "json_call", side_effect=AssertionError("image POST must be blocked")
    ):
        code, body = nanogpt.NanoGptProvider().generate(
            {
                "serviceId": "wavespeed-ai/krea-v2/turbo-lora",
                "prompt": "x",
                "width": 1024,
                "height": 1024,
            }
        )
    assert code == 400, (code, body)
    assert "resolution" in body["error"].lower() or "分辨率" in body["error"], body

    print("OK nanogpt-parameters")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
