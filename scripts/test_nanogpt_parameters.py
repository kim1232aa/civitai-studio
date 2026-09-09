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


def _fn_source(name: str) -> str:
    tree = ast.parse(SRC)
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return ast.get_source_segment(SRC, node) or ""
    raise AssertionError(f"{name} not found")


def _raises_zh(fn, *args, must=(), **kwargs):
    try:
        fn(*args, **kwargs)
    except ValueError as exc:
        msg = str(exc)
        for token in must:
            assert token in msg, (token, msg)
        return msg
    raise AssertionError(f"expected ValueError from {fn.__name__} args={args!r}")


def main() -> int:
    n = 0

    def check(cond):
        nonlocal n
        assert cond
        n += 1

    src = _fn_source("pick_resolution")
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

    # --- seed: official WaveSpeed/NanoGPT have no int32 max; fail-closed, never modulo ---
    clamp_src = _fn_source("_clamp_seed")
    check("%" not in clamp_src)
    check("2147483647" not in clamp_src)
    check("n % " not in SRC)
    meta_src = _fn_source("_seed_clamp_meta")
    check("seedOriginal" not in meta_src)
    check("True" not in meta_src)

    check(nanogpt._clamp_seed(None) is None)
    check(nanogpt._clamp_seed("") is None)
    check(nanogpt._clamp_seed("random") is None)
    check(nanogpt._clamp_seed(-1) == -1)
    check(nanogpt._clamp_seed(0) == 0)
    check(nanogpt._clamp_seed(42) == 42)
    check(nanogpt._clamp_seed("7") == 7)
    check(nanogpt._clamp_seed(2147483647) == 2147483647)
    check(nanogpt._clamp_seed(2147483648) == 2147483648)
    check(nanogpt._clamp_seed(467475143677094) == 467475143677094)
    check(nanogpt._seed_clamp_meta(42) == {})
    check(nanogpt._seed_clamp_meta(None) == {})
    check(nanogpt._seed_clamp_meta(-1) == {})
    check(nanogpt._seed_clamp_meta(467475143677094) == {})
    for bad in (-2, -3, 1.5, True, False, "abc", [], {}, 4.2):
        msg = _raises_zh(nanogpt._clamp_seed, bad, must=("种子", "静默"))
        check("取模" in msg or "改值" in msg)
    check(nanogpt._response_seed({"seed": 42}) == 42)
    check(nanogpt._response_seed({"data": [{"seed": 99, "url": "x"}]}) == 99)
    check(nanogpt._response_seed({"seed": 467475143677094}) == 467475143677094)

    img_seed_spec = {
        "id": "z-image-turbo",
        "category": "image",
        "supported_parameters": {"resolutions": ["1024x1024"], "max_output_images": 4},
        "capabilities": {},
    }
    captured = {}

    def _capture_seed_post(url, method="GET", headers=None, body=None, timeout=None):
        captured["url"] = url
        captured["body"] = body
        return 200, {"data": [{"url": "https://example.invalid/x.png", "seed": (body or {}).get("seed")}]}

    with patch.object(nanogpt, "nano_key", return_value="offline-key"), patch.object(
        nanogpt, "find_spec", return_value=img_seed_spec
    ), patch.object(nanogpt, "json_call", side_effect=_capture_seed_post), patch.object(
        nanogpt, "_save_result", return_value="/tmp/nano-seed-probe.png"
    ):
        code, body = nanogpt.NanoGptProvider().generate({
            "serviceId": "z-image-turbo",
            "prompt": "hi",
            "resolution": "1024x1024",
            "seed": 467475143677094,
        })
    check(code == 200)
    check(captured["body"]["seed"] == 467475143677094)
    check("seedClamped" not in (body or {}))
    check(body.get("seedOriginal") is None)

    with patch.object(nanogpt, "nano_key", return_value="offline-key"), patch.object(
        nanogpt, "find_spec", return_value=img_seed_spec
    ), patch.object(
        nanogpt, "json_call", side_effect=AssertionError("non-int seed must not POST")
    ):
        code, body = nanogpt.NanoGptProvider().generate({
            "serviceId": "z-image-turbo",
            "prompt": "hi",
            "resolution": "1024x1024",
            "seed": "abc",
        })
    check(code == 400)
    check("种子" in body["error"])

    # --- strength: omit official default; never invent 0.65 ---
    body_src = _fn_source("_image_body")
    check("0.65" not in body_src)
    check("except (TypeError, ValueError):\n        pass" not in body_src)
    i2i_spec = {
        "id": "edit-model",
        "supported_parameters": {"resolutions": ["1k"], "max_output_images": 4},
        "capabilities": {"image_generation": True, "image_to_image": True},
    }
    ref = "https://example.invalid/ref.png"
    omitted = nanogpt._image_body({
        "prompt": "x", "resolution": "1k", "sourceImage": ref, "images": [ref],
    }, i2i_spec)
    check("strength" not in omitted)
    check(omitted.get("input_references") == [ref])
    explicit = nanogpt._image_body({
        "prompt": "x", "resolution": "1k", "sourceImage": ref, "images": [ref],
        "denoise": 0.4,
    }, i2i_spec)
    check(explicit["strength"] == 0.4)
    user_065 = nanogpt._image_body({
        "prompt": "x", "resolution": "1k", "sourceImage": ref, "images": [ref],
        "strength": 0.65,
    }, i2i_spec)
    check(user_065["strength"] == 0.65)
    msg = _raises_zh(
        nanogpt._image_body,
        {"prompt": "x", "resolution": "1k", "sourceImage": ref, "images": [ref], "strength": None},
        i2i_spec,
        must=("0.65",),
    )
    check("null" in msg or "strength" in msg)
    _raises_zh(
        nanogpt._image_body,
        {"prompt": "x", "resolution": "1k", "sourceImage": ref, "images": [ref], "strength": "oops"},
        i2i_spec,
        must=("strength",),
    )
    _raises_zh(
        nanogpt._image_body,
        {"prompt": "x", "resolution": "1k", "sourceImage": ref, "images": [ref], "strength": True},
        i2i_spec,
        must=("strength",),
    )
    _raises_zh(
        nanogpt._image_body,
        {"prompt": "x", "resolution": "1k", "sourceImage": ref, "images": [ref], "denoise": 0.3, "strength": 0.9},
        i2i_spec,
        must=("冲突",),
    )

    # --- steps / cfgScale: invalid supplied values raise, not omit ---
    t2i = {"id": "t2i", "supported_parameters": {"resolutions": ["1k"], "max_output_images": 4}}
    stepped = nanogpt._image_body({"prompt": "x", "resolution": "1k", "steps": 20, "cfgScale": 7.5}, t2i)
    check(stepped["steps"] == 20 and stepped["num_inference_steps"] == 20)
    check(stepped["guidance_scale"] == 7.5)
    bare = nanogpt._image_body({"prompt": "x", "resolution": "1k"}, t2i)
    check("steps" not in bare and "num_inference_steps" not in bare and "guidance_scale" not in bare)
    for raw in ("many", True, 1.5, [], {}):
        _raises_zh(nanogpt._image_body, {"prompt": "x", "resolution": "1k", "steps": raw}, t2i, must=("steps",))
    for raw in ("high", True, float("inf"), float("nan"), []):
        _raises_zh(nanogpt._image_body, {"prompt": "x", "resolution": "1k", "cfgScale": raw}, t2i, must=("cfgScale",))

    print(f"OK nanogpt-parameters {n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
