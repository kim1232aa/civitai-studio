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

    from providers.modelscope import hub_upscale_blob as ms_up, _hub_row, _apply_upscale_category as ms_apply
    from providers.huggingface import hub_upscale_blob as hf_up, _hf_row, _apply_upscale_category as hf_apply
    fake_apisr = {"id": "org/APISR-generator-onnx", "name": "APISR ONNX", "chinese_name": "APISR"}
    assert ms_up(fake_apisr), "APISR-like id must classify as upscale blob"
    row = _hub_row(fake_apisr, "image", "text-to-image", ["t2i"], False, False)
    assert row["category"] == "upscale", row
    assert row["task"] == "upscale"
    z = _hub_row(
        {"id": "Tongyi-MAI/Z-Image-Turbo", "name": "Z-Image Turbo", "chinese_name": "Z-Image Turbo"},
        "image", "text-to-image", ["t2i"], False, False,
    )
    assert z["category"] == "image" and not ms_up(z), z
    edit = _hub_row(
        {"id": "Qwen/Qwen-Image-Edit", "name": "Qwen Image Edit"},
        "image", "image-to-image", ["i2i"], True, False,
    )
    assert edit["category"] == "image" and edit.get("needsSource") is True, edit
    assert ms_apply({"id": "x/realesrgan", "name": "RealESRGAN", "category": "image"})["category"] == "upscale"
    assert hf_up({"id": "foo/apisr-onnx", "name": "APISR"})
    hf_row = _hf_row("foo/APISR-ONNX", "APISR", "text-to-image")
    assert hf_row["category"] == "upscale", hf_row
    assert _hf_row("Tongyi-MAI/Z-Image-Turbo", "Z-Image-Turbo", "text-to-image")["category"] == "image"
    assert hf_apply({"id": "a/super-resolution", "name": "SR", "category": "image"})["category"] == "upscale"

    # v0758: widen Nomos / 4x family upscale classifier (not bare 4x / Z-Image)
    nomos = {"id": "muse/4xNomos8kSCHAT-L", "name": "4xNomos8kSCHAT-L"}
    assert ms_up(nomos) and hf_up(nomos), nomos
    assert ms_apply(dict(nomos, category="image"))["category"] == "upscale"
    assert hf_apply(dict(nomos, category="image"))["category"] == "upscale"
    assert _hub_row(nomos, "image", "text-to-image", ["t2i"], False, False)["category"] == "upscale"
    assert _hf_row("muse/4xNomos8kSCHAT-L", "4xNomos8kSCHAT-L", "text-to-image")["category"] == "upscale"

    apisr_x = {"id": "Xenova/4x_APISR_GRL_GAN_generator-onnx", "name": "4x_APISR_GRL_GAN_generator-onnx"}
    assert ms_up(apisr_x) and hf_up(apisr_x), apisr_x
    assert _hf_row(apisr_x["id"], apisr_x["name"], "text-to-image")["category"] == "upscale"

    zimg = {"id": "Tongyi-MAI/Z-Image-Turbo", "name": "Z-Image-Turbo"}
    assert not ms_up(zimg) and not hf_up(zimg), zimg
    assert ms_apply(dict(zimg, category="image"))["category"] == "image"
    assert hf_apply(dict(zimg, category="image"))["category"] == "image"
    assert _hf_row("Tongyi-MAI/Z-Image-Turbo", "Z-Image-Turbo", "text-to-image")["category"] == "image"
    # bare 4x / flux / turbo must NOT flip to upscale
    assert not ms_up({"id": "org/some-4x-model", "name": "some 4x model"})
    assert not hf_up({"id": "black-forest-labs/FLUX.1-schnell", "name": "FLUX.1 schnell"})

    # v0759: NMKD / VAE / ControlNet / GGUF / LoRA out of image; Z-Image stays image
    from providers.hub_classify import apply_hub_category, hub_utility_blob
    nmkd = {"id": "org/NMKD_Siax_200k_x4", "name": "NMKD_Siax_200k_x4", "category": "image"}
    assert ms_up(nmkd) and hf_up(nmkd), nmkd
    assert ms_apply(dict(nmkd))["category"] == "upscale"
    assert hf_apply(dict(nmkd))["category"] == "upscale"
    assert _hub_row(nmkd, "image", "text-to-image", ["t2i"], False, False)["category"] == "upscale"
    assert apply_hub_category(dict(nomos, category="image"))["category"] == "upscale"

    nmkd2 = {"id": "org/NMKDSuperscale15000G8x", "name": "NMKDSuperscale15000G8x", "category": "image"}
    assert apply_hub_category(dict(nmkd2))["category"] == "upscale"

    cnet = {"id": "lllyasviel/sd-controlnet-canny", "name": "ControlNet Canny", "category": "image"}
    assert hub_utility_blob(cnet)
    assert apply_hub_category(dict(cnet))["category"] == "utility"
    assert ms_apply(dict(cnet))["category"] != "image"
    assert hf_apply(dict(cnet))["category"] != "image"

    fvae = {"id": "black-forest-labs/flux_vae", "name": "flux_vae", "category": "image"}
    assert hub_utility_blob(fvae)
    assert apply_hub_category(dict(fvae))["category"] == "utility"
    assert ms_apply(dict(fvae))["category"] != "image"

    gguf = {"id": "org/weights-gguf", "name": "model.gguf", "category": "image"}
    assert apply_hub_category(dict(gguf))["category"] == "utility"

    lora = {"id": "user/cool-style_lora", "name": "cool-style_lora", "category": "image"}
    assert apply_hub_category(dict(lora))["category"] == "utility"

    assert apply_hub_category({"id": "Tongyi-MAI/Z-Image-Turbo", "name": "Z-Image-Turbo", "category": "image"})["category"] == "image"
    assert _hub_row(
        {"id": "Tongyi-MAI/Z-Image-Turbo", "name": "Z-Image-Turbo"},
        "image", "text-to-image", ["t2i"], False, False,
    )["category"] == "image"
    assert _hf_row("Qwen/Qwen-Image", "Qwen-Image", "text-to-image")["category"] == "image"
    assert _hf_row("black-forest-labs/FLUX.1-schnell", "FLUX.1 schnell", "text-to-image")["category"] == "image"

    # v0760: sticky VAE names; bare nmkd/ org not upscale; ip-composition-adapter utility
    from providers.hub_classify import hub_upscale_blob as hub_up
    sticky = [
        {"id": "org/BeautyFool_v1.2VAE_pruned", "name": "BeautyFool_v1.2VAE_pruned", "category": "image"},
        {"id": "org/qwen_image_vae", "name": "qwen_image_vae", "category": "image"},
        {"id": "org/ya3_VAE", "name": "ya3_VAE", "category": "image"},
    ]
    for row in sticky:
        assert hub_utility_blob(row), row
        assert apply_hub_category(dict(row))["category"] == "utility", row
        assert not hub_up(row), row
    assert not hub_utility_blob({"id": "Tongyi-MAI/Z-Image-Turbo", "name": "Z-Image-Turbo"})
    assert apply_hub_category({"id": "Tongyi-MAI/Z-Image-Turbo", "name": "Z-Image-Turbo", "category": "image"})["category"] == "image"

    bare_nmkd = {"id": "nmkd/some-diffusion", "name": "some-diffusion", "category": "image"}
    assert not hub_up(bare_nmkd) and not ms_up(bare_nmkd) and not hf_up(bare_nmkd), bare_nmkd
    assert apply_hub_category(dict(bare_nmkd))["category"] == "image"

    ipcomp = {"id": "x/ip-composition-adapter", "name": "ip-composition-adapter", "category": "image"}
    assert hub_utility_blob(ipcomp)
    assert apply_hub_category(dict(ipcomp))["category"] == "utility"

    bare_nomos = {"id": "muse/nomos", "name": "nomos", "category": "image"}
    assert hub_up(bare_nomos) and ms_up(bare_nomos) and hf_up(bare_nomos), bare_nomos

    # v0761: video-tagged VAE / wan_2.1_vae → utility; categories include utility
    wan_vae = {"id": "Wan-AI/wan_2.1_vae", "name": "wan_2.1_vae", "category": "video", "tags": ["t2v"]}
    assert hub_utility_blob(wan_vae), wan_vae
    assert apply_hub_category(dict(wan_vae))["category"] == "utility", wan_vae
    assert apply_hub_category(dict(wan_vae))["category"] != "video"
    vid_vae = {"id": "org/some_video_vae", "name": "video_vae", "category": "video"}
    assert apply_hub_category(dict(vid_vae))["category"] == "utility"
    # leave real video models alone
    real_vid = {"id": "tencent/HunyuanVideo", "name": "HunyuanVideo", "category": "video", "task": "text-to-video"}
    assert apply_hub_category(dict(real_vid))["category"] == "video"
    ms = ModelScopeProvider("ai")
    assert "utility" in ms.categories()
    from providers.huggingface import HuggingFaceProvider
    assert "utility" in HuggingFaceProvider().categories()

    # v0762: video GGUF / video LoRA stay video; pure VAE still utility; image GGUF still utility
    wan_gguf = {"id": "Wan-AI/Wan2.1-T2V-14B-GGUF", "name": "Wan2.1 GGUF", "category": "video", "pipeline_tag": "text-to-video"}
    assert not hub_utility_blob(wan_gguf), wan_gguf
    assert apply_hub_category(dict(wan_gguf))["category"] == "video", apply_hub_category(dict(wan_gguf))
    city_gguf = {"id": "city96/Wan2.1-GGUF", "name": "Wan2.1-GGUF", "category": "video", "pipeline_tag": "text-to-video"}
    assert apply_hub_category(dict(city_gguf))["category"] == "video"
    vid_lora = {"id": "someone/wan-video-lora", "name": "wan video lora", "category": "video", "tags": ["text-to-video", "lora"]}
    assert not hub_utility_blob(vid_lora), vid_lora
    assert apply_hub_category(dict(vid_lora))["category"] == "video"
    allegro = {"id": "rhymes-ai/Allegro", "name": "Allegro", "category": "video", "tags": ["text-to-video"]}
    assert apply_hub_category(dict(allegro))["category"] == "video"
    assert apply_hub_category(dict(wan_vae))["category"] == "utility"  # still hide VAE
    img_gguf = {"id": "org/weights-gguf", "name": "model.gguf", "category": "image"}
    assert apply_hub_category(dict(img_gguf))["category"] == "utility"

    # v0762: umt5 / text-encoder → utility (out of image); Qwen-Image stays image
    umt5 = {"id": "Wan-AI/umt5-xxl", "name": "umt5-xxl", "category": "image"}
    assert hub_utility_blob(umt5), umt5
    assert apply_hub_category(dict(umt5))["category"] == "utility"
    wan_umt5 = {"id": "Wan-AI/wan2.1-umt5", "name": "wan2.1-umt5", "category": "image"}
    assert hub_utility_blob(wan_umt5), wan_umt5
    assert apply_hub_category(dict(wan_umt5))["category"] == "utility"
    t5enc = {"id": "org/t5-encoder-weights", "name": "T5 encoder", "category": "image"}
    assert apply_hub_category(dict(t5enc))["category"] == "utility"
    te = {"id": "org/wan-text-encoder", "name": "text-encoder", "category": "image"}
    assert apply_hub_category(dict(te))["category"] == "utility"
    te2 = {"id": "org/clip-text_encoder", "name": "CLIP text_encoder", "category": "video"}
    assert apply_hub_category(dict(te2))["category"] == "utility"
    assert apply_hub_category({"id": "Qwen/Qwen-Image", "name": "Qwen Image", "category": "image"})["category"] == "image"

    # v0762: catalogIdMatchesWant exact-only (no Qwen-Image → Qwen-Image-2512 cousin)
    html = (Path(__file__).resolve().parent.parent / "static" / "index.html").read_text()
    assert "function catalogIdMatchesWant" in html
    assert "Exact string equality ONLY" in html
    # Extract and eval JS helper via node
    import subprocess, textwrap, tempfile, os
    js = r"""
function catalogIdMatchesWant(itOrId, want) {
  if (want == null || want === '') return false;
  const w = String(want);
  let id = '';
  if (itOrId != null && typeof itOrId === 'object') id = String(itOrId.id || itOrId.serviceId || '');
  else id = String(itOrId == null ? '' : itOrId);
  if (!id) return false;
  return id === w;
}
const assert = (c, m) => { if (!c) { console.error(m); process.exit(1); } };
assert(catalogIdMatchesWant('Qwen/Qwen-Image','Qwen/Qwen-Image-2512') === false, 'cousin must be false');
assert(catalogIdMatchesWant('Qwen/Qwen-Image','Qwen/Qwen-Image') === true, 'exact must be true');
assert(catalogIdMatchesWant({id:'Qwen/Qwen-Image'},'Qwen/Qwen-Image') === true, 'obj exact');
assert(catalogIdMatchesWant({id:'Qwen/Qwen-Image'},'Qwen/Qwen-Image-2512') === false, 'obj cousin');
assert(catalogIdMatchesWant('Qwen/Qwen-Image-2512','Qwen/Qwen-Image') === false, 'reverse cousin');
console.log('PASS catalogIdMatchesWant');
"""
    # Prefer the live function body from index.html when present
    import re
    m = re.search(r"function catalogIdMatchesWant\(itOrId, want\) \{[\s\S]*?\n\}", html)
    if m:
        live = m.group(0)
        js = live + """
const assert = (c, m) => { if (!c) { console.error(m); process.exit(1); } };
assert(catalogIdMatchesWant('Qwen/Qwen-Image','Qwen/Qwen-Image-2512') === false, 'cousin must be false');
assert(catalogIdMatchesWant('Qwen/Qwen-Image','Qwen/Qwen-Image') === true, 'exact must be true');
assert(catalogIdMatchesWant({id:'Qwen/Qwen-Image'},'Qwen/Qwen-Image') === true, 'obj exact');
assert(catalogIdMatchesWant({id:'Qwen/Qwen-Image'},'Qwen/Qwen-Image-2512') === false, 'obj cousin');
console.log('PASS catalogIdMatchesWant');
"""
    r = subprocess.run(["node", "-e", js], capture_output=True, text=True)
    assert r.returncode == 0, (r.stdout, r.stderr)
    assert "PASS catalogIdMatchesWant" in (r.stdout or "")

    # frozenPickId wiring markers in runGenerate
    assert "frozenPickId" in html and "Hard-lock" in html
    assert "pl.serviceId = frozenPick" in html
    assert "ignored during goBusy" in html
    assert "allowRecipeSwitch" in html

    print("PASS p0 wiring")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
