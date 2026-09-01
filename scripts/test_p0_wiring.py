#!/usr/bin/env python3
"""Smoke the P0 wiring: Fal LoRA sibling, HF skip replicate, nodepack guard."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from providers.fal import (  # noqa: E402
    _fal_lora_path,
    apply_fal_loras,
    fal_lora_sibling,
    fal_supports_lora,
)
from providers.huggingface import _SKIP_OPENAI  # noqa: E402


def main() -> int:
    assert fal_supports_lora({"id": "fal-ai/krea-2/turbo/lora"})
    assert fal_supports_lora({"id": "fal-ai/flux-lora"})
    assert fal_lora_sibling("fal-ai/krea-2/turbo") == "fal-ai/krea-2/turbo/lora"
    assert fal_lora_sibling("fal-ai/z-image/turbo") == "fal-ai/z-image/turbo/lora"
    sib = fal_lora_sibling("fal-ai/flux/schnell")
    assert sib == "fal-ai/flux-lora", sib
    assert _fal_lora_path({"air": "urn:air:krea2:lora:civitai:1@3184845", "versionId": 3184845}) == (
        "https://civitai.com/api/download/models/3184845"
    )
    inp = {}
    apply_fal_loras(
        inp,
        {"loras": [{"path": "https://civitai.com/api/download/models/1", "scale": 1.2}]},
        {"id": "fal-ai/krea-2/turbo/lora"},
        "fal-ai/krea-2/turbo/lora",
    )
    assert inp.get("loras") and inp["loras"][0]["path"].startswith("https://")
    assert "replicate" in _SKIP_OPENAI
    from providers.fal import build_fal_input, find_model
    fin = build_fal_input({
        "serviceId": "fal-ai/nano-banana-2",
        "prompt": "x",
        "aspectRatio": "16:9",
        "quantity": 3,
    })
    assert fin.get("aspect_ratio") == "16:9", fin
    spec = find_model("fal-ai/nano-banana-2") or {}
    opt = set(spec.get("optional") or []) | set(spec.get("required") or [])
    if "num_images" in opt:
        assert fin.get("num_images") == 3, fin
    from providers.huggingface import _prompt_body, _maybe_lora_pid, _force_loras
    pb = _prompt_body({"steps": 8, "cfgScale": 1, "scheduler": "sgm_uniform", "seed": 3, "width": 960, "height": 1440})
    assert pb["num_inference_steps"] == 8
    assert pb["guidance_scale"] == 1
    assert pb["scheduler"] == "sgm_uniform"
    assert _maybe_lora_pid("fal-ai/z-image/turbo", {"loras": [{"path": "https://civitai.com/api/download/models/3231694"}]}) == "fal-ai/z-image/turbo"
    assert _maybe_lora_pid("fal-ai/z-image/turbo", {}) == "fal-ai/z-image/turbo"
    forced = {}
    _force_loras(forced, {"loras": [{"path": "https://civitai.com/api/download/models/3231694", "scale": 0.8}]})
    assert forced["loras"][0]["path"].startswith("https://")
    assert _prompt_body({"seed": 1074720209731743})["seed"] <= 2147483647
    from providers.modelscope import (
        _modelscope_loras, _clamp_seed, AI_BASE, CN_BASE,
        AI_TOKEN_PATH, CN_TOKEN_PATH, ModelScopeProvider,
    )
    assert "modelscope.ai" in AI_BASE and "modelscope.cn" not in AI_BASE
    assert "modelscope.cn" in CN_BASE
    assert AI_BASE != CN_BASE
    # Regression: AI / CN must not share token path or base (no cross-fallback).
    assert AI_TOKEN_PATH != CN_TOKEN_PATH
    assert str(AI_TOKEN_PATH).endswith("modelscope/token")
    assert str(CN_TOKEN_PATH).endswith("modelscope-cn/token")
    ai = ModelScopeProvider("ai")
    cn = ModelScopeProvider("cn")
    assert ai._base == AI_BASE and cn._base == CN_BASE
    assert ai._token_path == AI_TOKEN_PATH and cn._token_path == CN_TOKEN_PATH
    assert ai.id == "modelscope-ai" and cn.id == "modelscope-cn"
    assert _modelscope_loras({"loras": [{"name": "Qwen/foo", "scale": 1}]}) == "Qwen/foo"
    assert _modelscope_loras({"loras": [{"path": "https://civitai.com/api/download/models/3231694", "scale": 0.8}]}) is None
    assert _modelscope_loras({"loras": [{
        "name": "[Z Image Turbo] Asian Mix Lora - EOL",
        "path": "https://civitai.com/api/download/models/3231694?fileId=3114056",
        "scale": 0.8,
    }]}) is None
    assert _clamp_seed(475720515768790) <= 2147483647
    assert _clamp_seed(475720515768790) > 0
    assert _clamp_seed(-3) == -1
    from providers.io_meta import coerce_int, dims_from_selector, first_int, parse_comfy
    node = {
        "class_type": "ResolutionSelector",
        "inputs": {"multiple": 32, "megapixels": 2, "aspect_ratio": "2:3 (Portrait Photo)"},
    }
    assert coerce_int(node) is not None
    wh = dims_from_selector(node)
    assert wh and wh[0] >= 64 and wh[1] > wh[0]
    assert first_int(node, 2368) == coerce_int(node) or first_int({"width": 2368}) == 2368
    parsed = parse_comfy(json.dumps({"1": node, "2": {"class_type": "CLIPTextEncode", "inputs": {"text": "hi"}}}))
    assert parsed.get("width") and parsed.get("height")
    from providers.civitai import _wants_custom_comfy
    assert _wants_custom_comfy({"recipe": "workflow", "prompt": "x"})
    assert _wants_custom_comfy({"step": "customComfy"})
    assert not _wants_custom_comfy({"prompt": "x", "serviceId": "image/comfy/krea2/turbo/createImage"})
    from providers.nanogpt import closest_aspect, pick_resolution, _loras, _clamp_seed as nano_seed, _image_body
    assert closest_aspect(960, 1440) in ("2:3", "4:5")
    spec = {"supported_parameters": {"resolutions": ["1k", "2k"]}}
    assert pick_resolution(spec, 1024, 1024) == "1k"
    assert pick_resolution(spec, 2048, 2048) == "2k"
    spec2 = {"supported_parameters": {"resolutions": ["1:1", "4:3", "2:3", "9:16"]}}
    assert pick_resolution(spec2, 960, 1440) == "2:3"
    zspec = {"supported_parameters": {"resolutions": [
        "256*256", "512*512", "768*768", "1024*1024", "1280*720", "720*1280",
        "1536*1024", "1024*1536", "1536*1536",
    ]}}
    assert pick_resolution(zspec, 960, 1440) == "1024*1536"
    assert pick_resolution(zspec, 1024, 1024) == "1024*1024"
    assert pick_resolution({"supported_parameters": {"resolutions": []}}, 1024, 1024) is None
    assert pick_resolution({}, 256, 256) is None
    assert pick_resolution(spec, 1024, 1024, preferred="2k") == "2k"
    ls = _loras({"loras": [{"path": "https://civitai.com/api/download/models/1", "scale": 0.8}]})
    assert ls and ls[0]["path"].startswith("https://")
    assert nano_seed(475720515768790) <= 2147483647
    body = _image_body({"serviceId": "wavespeed-ai/krea-v2/turbo-lora", "prompt": "x", "width": 1024, "height": 1024, "quantity": 1, "loras": [{"path": "https://civitai.com/api/download/models/1", "scale": 1}]}, spec)
    assert body["model"] == "wavespeed-ai/krea-v2/turbo-lora"
    assert body["loras"][0]["path"].startswith("https://")
    assert body["resolution"] == "1k"
    i2i = _image_body({
        "serviceId": "wavespeed-ai/krea-v2/turbo-lora",
        "prompt": "x",
        "width": 960,
        "height": 1440,
        "sourceImage": "https://example.com/a.jpg",
        "denoise": 0.4,
    }, spec)
    assert i2i["input_references"] == ["https://example.com/a.jpg"]
    assert i2i["strength"] == 0.4
    assert "image" not in i2i and "imageUrl" not in i2i and "imageDataUrl" not in i2i and "image_url" not in i2i
    print("PASS p0 wiring")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
