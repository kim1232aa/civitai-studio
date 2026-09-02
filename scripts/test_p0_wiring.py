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
    # v0774: proven UI import seed → Nano int32 modulo
    assert _clamp_seed(891104780613135) == 2146323191
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
    assert "width" not in body and "height" not in body
    from providers.nanogpt import sanitize_submitted_for_persist
    persisted = sanitize_submitted_for_persist({**body, "width": 960, "height": 1440})
    assert "width" not in persisted and "height" not in persisted
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

    # v0763: umt5 / u-mt5 / t5xxl / clip_l / text-encoder → utility (out of image); Qwen-Image stays image
    umt5 = {"id": "Wan-AI/umt5-xxl", "name": "umt5-xxl", "category": "image"}
    assert hub_utility_blob(umt5), umt5
    assert apply_hub_category(dict(umt5))["category"] == "utility"
    wan_umt5 = {"id": "Wan-AI/wan2.1-umt5", "name": "wan2.1-umt5", "category": "image"}
    assert hub_utility_blob(wan_umt5), wan_umt5
    assert apply_hub_category(dict(wan_umt5))["category"] == "utility"
    assert hub_utility_blob({"id": "org/u-mt5", "name": "u-mt5", "category": "image"})
    assert hub_utility_blob({"id": "org/t5xxl", "name": "t5xxl", "category": "image"})
    assert hub_utility_blob({"id": "org/clip_l", "name": "clip_l", "category": "image"})
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

    # v0764: umt5_xxl_encoder (underscore after mt5) → utility
    umt5_xxl = {"id": "org/umt5_xxl_encoder", "name": "umt5_xxl_encoder", "category": "image"}
    assert hub_utility_blob(umt5_xxl), umt5_xxl
    assert apply_hub_category(dict(umt5_xxl))["category"] == "utility"
    umt5_fp8 = {"id": "org/umt5_xxl_fp8_e4m3fn_scaled.safetensors", "name": "umt5_xxl_fp8", "category": "image"}
    assert hub_utility_blob(umt5_fp8), umt5_fp8

    # v0764: cousin false for Qwen-Image vs 2512 and vs MusePublic/Qwen-image
    assert "function isForbiddenHubRemap" in html
    assert "拒绝写入不同 model" in html
    assert "MusePublic/Qwen-Image-Edit']" not in html  # banned from want list
    assert "want = ['Qwen/Qwen-Image-Edit']" in html
    m2 = re.search(r"function isForbiddenHubRemap\(frozen, candidate\) \{[\s\S]*?\n\}", html)
    assert m2, "isForbiddenHubRemap missing"
    m3 = re.search(r"function hubIdLeaf\(id\) \{[\s\S]*?\n\}", html)
    assert m3, "hubIdLeaf missing"
    js2 = m3.group(0) + "\n" + m2.group(0) + """
const assert = (c, m) => { if (!c) { console.error(m); process.exit(1); } };
assert(isForbiddenHubRemap('Qwen/Qwen-Image','Qwen/Qwen-Image-2512') === true, '2512 cousin');
assert(isForbiddenHubRemap('Qwen/Qwen-Image','MusePublic/Qwen-image') === true, 'MusePublic cousin');
assert(isForbiddenHubRemap('Qwen/Qwen-Image','MusePublic/Qwen-Image') === true, 'MusePublic same leaf');
assert(isForbiddenHubRemap('Qwen/Qwen-Image','Qwen/Qwen-Image') === false, 'exact ok');
assert(isForbiddenHubRemap('Qwen/Qwen-Image-Edit','MusePublic/Qwen-Image-Edit') === true, 'Edit MusePublic');
console.log('PASS isForbiddenHubRemap');
"""
    r2 = subprocess.run(["node", "-e", js2], capture_output=True, text=True)
    assert r2.returncode == 0, (r2.stdout, r2.stderr)
    assert "PASS isForbiddenHubRemap" in (r2.stdout or "")

    # payload builder refuse mismatched serviceId markers + single-flight
    assert "拒绝写入不同 model" in html
    assert "early single-flight" in html
    assert "only html onclick=__studioGo" in html
    assert "go.addEventListener" not in html
    assert "v0767" in html

    # server refuse mismatched model
    ms = (Path(__file__).resolve().parent.parent / "providers" / "modelscope.py").read_text()
    assert "模型 id 不一致" in ms


    # v0765: applyImport must not invoke pickForBackend (exact Hub freeze only)
    import re as _re
    m_ai = _re.search(r"function applyImport\(j\) \{", html)
    assert m_ai, "applyImport missing"
    _i = m_ai.end() - 1
    _depth = 0
    _end = None
    for _j in range(_i, len(html)):
        if html[_j] == "{":
            _depth += 1
        elif html[_j] == "}":
            _depth -= 1
            if _depth == 0:
                _end = _j + 1
                break
    assert _end, "applyImport brace match failed"
    ai_body = html[m_ai.start():_end]
    assert "pickForBackend(" not in ai_body, "applyImport must not call pickForBackend"
    assert "resolveExactHubFromImport" in ai_body
    assert "function resolveExactHubFromImport" in html
    assert "function exactRepoNamedIn" in html
    assert "请先点选确切模型" in html
    # unit exactRepoNamedIn + resolveExactHubFromImport via node
    m_ex = _re.search(r"function exactRepoNamedIn\(text, repo\) \{[\s\S]*?\n\}", html)
    m_re = _re.search(r"function resolveExactHubFromImport\(j\) \{[\s\S]*?\n\}", html)
    assert m_ex and m_re
    # stub findCatalogItem / looksCivitaiId for unit
    js3 = m_ex.group(0) + """
const catalog = [
  {id:'Qwen/Qwen-Image'},
  {id:'Qwen/Qwen-Image-2512'},
  {id:'MusePublic/Qwen-image'},
  {id:'Tongyi-MAI/Z-Image-Turbo'},
];
function findCatalogItem(id) {
  id = String(id == null ? '' : id);
  if (!id) return null;
  return catalog.find(x => String(x.id) === id) || null;
}
function looksCivitaiId(s) {
  s = String(s || '');
  return /^(image|video|audio|3d|utility)\\//.test(s) || /\\/comfy\\//.test(s);
}
""" + m_re.group(0) + """
const assert = (c, m) => { if (!c) { console.error(m); process.exit(1); } };
assert(exactRepoNamedIn('Qwen/Qwen-Image', 'Qwen/Qwen-Image') === true, 'exact');
assert(exactRepoNamedIn('foo Qwen/Qwen-Image-2512 bar', 'Qwen/Qwen-Image') === false, '2512 must not match Qwen-Image');
assert(exactRepoNamedIn('MusePublic/Qwen-image', 'Qwen/Qwen-Image') === false, 'MusePublic');
assert(exactRepoNamedIn('use Qwen/Qwen-Image please', 'Qwen/Qwen-Image') === true, 'token');
let hit = resolveExactHubFromImport({checkpointName:'Qwen/Qwen-Image'});
assert(hit && hit.id === 'Qwen/Qwen-Image', 'checkpoint exact');
hit = resolveExactHubFromImport({checkpointName:'Qwen/Qwen-Image-2512'});
assert(!hit || hit.id !== 'Qwen/Qwen-Image', '2512 must not resolve to Qwen-Image');
hit = resolveExactHubFromImport({hubModel:'Tongyi-MAI/Z-Image-Turbo'});
assert(hit && hit.id === 'Tongyi-MAI/Z-Image-Turbo', 'hubModel');
hit = resolveExactHubFromImport({checkpointName:'some random civitai ckpt'});
assert(hit === null, 'unknown null');
hit = resolveExactHubFromImport({serviceId:'MusePublic/Qwen-image'});
assert(hit && hit.id === 'MusePublic/Qwen-image', 'exact MusePublic id ok if literally imported');
console.log('PASS resolveExactHubFromImport');
"""
    r3 = subprocess.run(["node", "-e", js3], capture_output=True, text=True)
    assert r3.returncode == 0, (r3.stdout, r3.stderr)
    assert "PASS resolveExactHubFromImport" in (r3.stdout or "")


    # v0766: generateLockId hard lock; full id chip; sd35_t5xxl/clip utility; no MusePublic steal
    assert "generateLockId" in html
    assert "lockId = String(userPickedId" in html or "const lockId = String(userPickedId" in html
    assert "banned during goBusy/lock" in html
    assert "owner/leaf" in html or "owner + '/' + leaf" in html
    assert "hubVideoListNoise" in html
    assert "MusePublic/" in html  # still mentioned as ban
    assert "want = (want || []).filter(id => !String(id || '').startsWith('MusePublic/'))" in html
    sd35 = {"id": "org/sd35_t5xxl", "name": "sd35_t5xxl", "category": "image"}
    assert hub_utility_blob(sd35), sd35
    assert apply_hub_category(dict(sd35))["category"] == "utility"
    sd35c = {"id": "org/sd35_clip_l", "name": "sd35_clip_l", "category": "image"}
    assert hub_utility_blob(sd35c), sd35c
    assert apply_hub_category(dict(sd35c))["category"] == "utility"
    # FE hubUtilityBlob must also catch sd35_* via node extract
    m_fe = _re.search(r"function hubUtilityBlob\(it\) \{[\s\S]*?\n\}", html)
    assert m_fe, "hubUtilityBlob missing"
    # Also hubVideoFamilyBlob needed by hubUtilityBlob
    m_vf = _re.search(r"function hubVideoFamilyBlob\(it\) \{[\s\S]*?\n\}", html)
    assert m_vf, "hubVideoFamilyBlob missing"
    js_fe = m_vf.group(0) + "\n" + m_fe.group(0) + """
const assert = (c, m) => { if (!c) { console.error(m); process.exit(1); } };
assert(hubUtilityBlob({id:'org/sd35_t5xxl', name:'sd35_t5xxl'}) === true, 'sd35_t5xxl');
assert(hubUtilityBlob({id:'org/sd35_clip_l', name:'sd35_clip_l'}) === true, 'sd35_clip_l');
assert(hubUtilityBlob({id:'Qwen/Qwen-Image', name:'Qwen-Image'}) === false, 'Qwen-Image');
console.log('PASS hubUtilityBlob sd35');
"""
    r_fe = subprocess.run(["node", "-e", js_fe], capture_output=True, text=True)
    assert r_fe.returncode == 0, (r_fe.stdout, r_fe.stderr)


    # v0767/v0768: recipe/tab switch clears svcFilter and reloads catalog
    m_sr = _re.search(r"function setRecipe\(r\) \{[\s\S]*?\n\}", html)
    assert m_sr, "setRecipe missing"
    sr = m_sr.group(0)
    assert "svcFilter" in sr and ".value = ''" in sr
    assert "loadCatalog" in sr
    assert "window.loadCatalog = loadCatalog" in html
    assert "当前配方无匹配模型，请搜索或切换供应商" in html
    assert 'title="v0776"' in html
    assert 'aria-label="生成"' in html
    assert 'aria-label="v0772"' not in html
    # v0768: setRecipe locked during goBusy/generateLockId
    assert "生成中不能切换配方" in sr
    assert "goBusy || generateLockId" in sr
    # v0768: MusePublic/Qwen-image ban
    assert "isMusePublicQwenImageCousin" in html
    assert "禁止手选 MusePublic/Qwen-image" in html
    assert "禁止提交 MusePublic/Qwen-image" in html
    # v0768: sd35_clip_g utility FE+PY
    sd35g = {"id": "muse/sd35_clip_g", "name": "sd35_clip_g", "category": "image"}
    assert hub_utility_blob(sd35g), sd35g
    assert apply_hub_category(dict(sd35g))["category"] == "utility"
    js_fe2 = m_vf.group(0) + "\n" + m_fe.group(0) + """
const assert = (c, m) => { if (!c) { console.error(m); process.exit(1); } };
assert(hubUtilityBlob({id:'muse/sd35_clip_g', name:'sd35_clip_g'}) === true, 'sd35_clip_g');
assert(hubUtilityBlob({id:'muse/sd35_large', name:'sd35_large'}) === false, 'sd35_large');
console.log('PASS hubUtilityBlob sd35_clip_g');
"""
    r_fe2 = subprocess.run(["node", "-e", js_fe2], capture_output=True, text=True)
    assert r_fe2.returncode == 0, (r_fe2.stdout, r_fe2.stderr)
    # v0768: hubVideoListNoise drops Comfy/LoRA/safetensors; keeps real wan t2v/gguf
    m_noise = _re.search(r"function hubVideoListNoise\(it\) \{[\s\S]*?\n\}", html)
    assert m_noise, "hubVideoListNoise missing"
    # Need hubUtilityBlob + hubVideoFamilyBlob deps
    js_vn = m_vf.group(0) + "\n" + m_fe.group(0) + "\n" + m_noise.group(0) + """
const assert = (c, m) => { if (!c) { console.error('FAIL', m); process.exit(1); } };
assert(hubVideoListNoise({id:'Comfy-Org/Wan_2.2_ComfyUI_Repackaged', name:'Wan_2.2_ComfyUI_Repackaged', category:'video'}) === true, 'comfyui repack');
assert(hubVideoListNoise({id:'Kijai/WanVideo_comfy', name:'WanVideo_comfy', category:'video'}) === true, 'WanVideo_comfy');
assert(hubVideoListNoise({id:'lightx2v/Wan2.2-Distill-Loras', name:'Wan2.2-Distill-Loras', category:'video'}) === true, 'Distill-Loras');
assert(hubVideoListNoise({id:'acevsok/wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors', name:'wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors', category:'video'}) === true, 'safetensors dump');
assert(hubVideoListNoise({id:'Wan-AI/Wan2.1-T2V-14B', name:'Wan2.1-T2V-14B', category:'video'}) === false, 'real T2V');
assert(hubVideoListNoise({id:'Wan-AI/Wan2.1-I2V-14B-480P', name:'Wan2.1-I2V-14B-480P', category:'video'}) === false, 'real I2V');
assert(hubVideoListNoise({id:'city96/Wan2.1-T2V-14B-gguf', name:'Wan2.1-T2V-14B-gguf', category:'video'}) === false, 'real GGUF');
console.log('PASS hubVideoListNoise v0768');
"""
    r_vn = subprocess.run(["node", "-e", js_vn], capture_output=True, text=True)
    assert r_vn.returncode == 0, (r_vn.stdout, r_vn.stderr)
    # MusePublic cousin helper via node
    m_mp = _re.search(r"function isMusePublicQwenImageCousin\(it\) \{[\s\S]*?\n\}", html)
    assert m_mp, "isMusePublicQwenImageCousin missing"
    js_mp = m_mp.group(0) + """
const assert = (c, m) => { if (!c) { console.error(m); process.exit(1); } };
assert(isMusePublicQwenImageCousin({id:'MusePublic/Qwen-image'}) === true, 'MP Qwen-image');
assert(isMusePublicQwenImageCousin({id:'MusePublic/Qwen-Image-Edit'}) === true, 'MP Edit');
assert(isMusePublicQwenImageCousin({id:'MusePublic/Qwen-image-fp8'}) === true, 'MP fp8');
assert(isMusePublicQwenImageCousin({id:'Qwen/Qwen-Image'}) === false, 'real Qwen');
assert(isMusePublicQwenImageCousin({id:'MusePublic/Something-Else'}) === false, 'other MP');
console.log('PASS isMusePublicQwenImageCousin');
"""
    r_mp = subprocess.run(["node", "-e", js_mp], capture_output=True, text=True)
    assert r_mp.returncode == 0, (r_mp.stdout, r_mp.stderr)


    # v0770: always re-resolve Civitai LoRA B2 at Nano generate; stale B2 alone fails
    assert 'title="v0776"' in html
    assert '无直链' in html
    assert 'loraHasDirectPath' in html
    assert 'lora-miss-chip' in html
    assert 'lora_no_direct_url' in html or 'LoRA 无直链' in html
    from providers.nanogpt import (
        resolve_civitai_b2_url,
        resolve_nano_loras,
        sanitize_submitted_for_persist,
        persist_safe_lora_path,
        model_supports_lora,
        civitai_api_token,
        _strip_token_query,
        is_signed_b2_url,
    )
    assert model_supports_lora({"supportsLora": True}, "z-image-turbo")
    assert model_supports_lora({}, "z-image-turbo-lora")
    assert not model_supports_lora({}, "z-image-turbo")
    # strip ?token= never keep API key query
    assert "token=" not in _strip_token_query(
        "https://civitai.com/api/download/models/3231694?token=SECRET&fileId=1"
    ).lower()
    assert "fileId=1" in _strip_token_query(
        "https://civitai.com/api/download/models/3231694?token=SECRET&fileId=1"
    )
    # Mock resolve: inject Location without network when possible — prefer live if token/public works,
    # else unittest.mock.
    import unittest.mock as mock
    fake_b2 = (
        "https://b2.civitai.com/file/civitai-modelfiles/model/1/x.safetensors"
        "?Authorization=fake_sig&b2ContentDisposition=attachment"
    )
    with mock.patch("providers.nanogpt._head_redirect_location", return_value=fake_b2):
        got = resolve_civitai_b2_url("https://civitai.com/api/download/models/3231694")
        assert got == fake_b2
        assert "token=" not in got.split("?")[0]
        out, err = resolve_nano_loras({
            "loras": [{"versionId": 3231694, "name": "Asian Mix", "scale": 0.8}]
        })
        assert err is None and out and out[0]["path"] == fake_b2
        assert out[0]["versionId"] == "3231694"
        safe = sanitize_submitted_for_persist(
            {"loras": [{"path": fake_b2, "scale": 0.8}], "lora_1_url": fake_b2},
            out,
        )
        assert safe["loras"][0]["path"] == "https://civitai.com/api/download/models/3231694"
        assert "Authorization=" not in safe["loras"][0]["path"]
        assert safe["lora_1_url"] == "https://civitai.com/api/download/models/3231694"
    # Fail closed: AIR-only
    out2, err2 = resolve_nano_loras({"loras": [{"air": "urn:air:x:lora:civitai:1@1", "name": "NoUrl"}]})
    assert out2 is None and err2 and err2.get("code") == "lora_no_direct_url"
    assert "无直链" in err2["error"]
    # Fail closed: >3
    out3, err3 = resolve_nano_loras({
        "loras": [{"path": "https://civitai.com/api/download/models/%d" % i, "name": "L%d" % i} for i in range(4)]
    })
    assert err3 and err3.get("code") == "lora_too_many"
    # v0770: stale B2 alone (no versionId / download API) → FAIL closed — never passthrough
    out_stale, err_stale = resolve_nano_loras({
        "loras": [{"path": fake_b2, "name": "StaleB2", "scale": 1.0}]
    })
    assert out_stale is None and err_stale and err_stale.get("code") == "lora_no_direct_url"
    assert any(
        "B2" in (f.get("error") or "") or "刷新" in (f.get("error") or "") or "无直链" in (f.get("error") or "")
        for f in (err_stale.get("failed") or [])
    ) or ("B2" in err_stale.get("error", "") or "刷新" in err_stale.get("error", "") or "无直链" in err_stale.get("error", ""))
    # v0770: versionId + stale B2 path → still re-resolves via download API (not passthrough)
    with mock.patch("providers.nanogpt._head_redirect_location", return_value=fake_b2) as m_head:
        out_re, err_re = resolve_nano_loras({
            "loras": [{"path": fake_b2, "versionId": 3231694, "name": "ReResolve", "scale": 0.7}]
        })
        assert err_re is None and out_re and out_re[0]["path"] == fake_b2
        assert m_head.called, "must re-resolve via HEAD/GET, not trust stale B2"
        # Called with download API URL, not the stale B2
        call_url = m_head.call_args[0][0]
        assert "civitai.com/api/download/models/3231694" in call_url
        assert "Authorization=" not in call_url
    # resolve_civitai_b2_url rejects B2 as entry
    try:
        resolve_civitai_b2_url(fake_b2)
        raise AssertionError("should refuse B2 as resolve entry")
    except ValueError as e:
        assert "B2" in str(e) or "versionId" in str(e) or "download" in str(e).lower()
    # Refuse key leak in Location
    tok = civitai_api_token() or "TEST_CIVITAI_KEY_LEAK"
    with mock.patch("providers.nanogpt.civitai_api_token", return_value=tok):
        with mock.patch(
            "providers.nanogpt._head_redirect_location",
            return_value="https://evil.example/x?token=" + tok,
        ):
            try:
                resolve_civitai_b2_url("https://civitai.com/api/download/models/1")
                raise AssertionError("should have refused key leak")
            except ValueError as e:
                assert "token" in str(e).lower() or "Key" in str(e) or "泄露" in str(e) or "拒绝" in str(e)
    # persist_safe: with versionId → download API; without → empty (no bare b2)
    assert persist_safe_lora_path(fake_b2, "3231694") == "https://civitai.com/api/download/models/3231694"
    assert "Authorization=" not in persist_safe_lora_path(fake_b2, "3231694")
    assert persist_safe_lora_path(fake_b2, None) == ""
    assert persist_safe_lora_path(fake_b2, "") == ""
    assert is_signed_b2_url(fake_b2)
    # _generate_image + _generate_video wire resolve (source markers)
    nano_src = (Path(__file__).resolve().parent.parent / "providers" / "nanogpt.py").read_text()
    assert "resolve_nano_loras" in nano_src
    assert "sanitize_submitted_for_persist" in nano_src
    assert "model_supports_lora" in nano_src
    assert "CIVITAI_TOKEN_PATH" in nano_src
    assert 'code": "lora_model_unsupported"' in nano_src or "lora_model_unsupported" in nano_src
    assert "elif is_signed_b2_url(path_hint):" not in nano_src  # old passthrough removed
    assert "def _generate_video" in nano_src
    assert nano_src.count("resolve_nano_loras") >= 2  # image + video
    assert "video path also runs resolve_nano_loras" in nano_src

    # v0772: Nano prompt length precheck (server + FE) — do not waste a generate
    from providers.nanogpt import prompt_length_error, NANO_PROMPT_MAX, NanoGptProvider
    assert NANO_PROMPT_MAX == 1200
    assert prompt_length_error("x" * 1200) is None
    assert prompt_length_error("ok") is None
    assert prompt_length_error("") is None
    assert prompt_length_error(None) is None
    err_long = prompt_length_error("y" * 1408)
    assert err_long and err_long.get("code") == "prompt_too_long"
    assert err_long["length"] == 1408 and err_long["max"] == 1200 and err_long["limit"] == 1200
    assert "1408/1200" in err_long["error"]
    assert "提示词过长" in err_long["error"]
    # Provider generate path returns 400 before Nano API when overlong
    prov = NanoGptProvider()
    # Patch nano_key so we get past auth; prompt gate runs in _generate_image/_video
    import unittest.mock as mock
    with mock.patch("providers.nanogpt.nano_key", return_value="test-key"):
        with mock.patch("providers.nanogpt.find_spec", return_value={
            "id": "wavespeed-ai/krea-v2/turbo",
            "category": "image",
            "supported_parameters": {"resolutions": ["1024x1024"]},
            "capabilities": {},
        }):
            with mock.patch("providers.nanogpt.json_call") as jc:
                code, body = prov.generate({
                    "serviceId": "wavespeed-ai/krea-v2/turbo",
                    "prompt": "z" * 1408,
                    "width": 1024,
                    "height": 1024,
                })
                assert code == 400, (code, body)
                assert body.get("code") == "prompt_too_long"
                assert body.get("length") == 1408 and body.get("max") == 1200
                assert not jc.called, "must not call Nano API when prompt_too_long"
    # FE: constant + precheck + truncate + import/switch warn
    assert "NANO_PROMPT_MAX = 1200" in html
    assert "提示词过长" in html
    assert "nPrompt > NANO_PROMPT_MAX" in html
    assert "截断到 1200" in html
    assert "truncateNanoPrompt" in html
    assert "syncNanoPromptHint" in html
    assert "nanoPromptHint" in html
    assert 'title="v0776"' in html
    assert "prompt_length_error" in nano_src
    assert "NANO_PROMPT_MAX = 1200" in nano_src


    # v0773: seed sync after generate; fixed-seed warn; Nano prefers response seed
    # v0774: FE clampSeedInt32 write-back; server seedOriginal/seedClamped
    assert "syncSeedAfterGenerate" in html
    assert "warnFixedSeedIfNeeded" in html
    assert "clampSeedInt32" in html
    assert "applyNanoSeedClampIfNeeded" in html
    assert "种子超出范围，已取模为" in html
    assert "已用种子" in html
    assert "随机种子" in html
    assert "固定种子会复现同一张图；要新图请清空种子" in html
    assert "seedRaw === '' ? null" in html or "seedRaw === \'\' ? null" in html
    assert "seedHint" in html
    assert 'title="v0776"' in html
    from providers.nanogpt import _response_seed, _clamp_seed as _ns, _seed_clamp_meta
    assert _ns(891104780613135) == 2146323191
    assert _seed_clamp_meta(891104780613135) == {"seedOriginal": 891104780613135, "seedClamped": True}
    assert _seed_clamp_meta(42) == {}
    assert _response_seed({"seed": 42}) == 42
    assert _response_seed({"data": [{"seed": 99, "url": "x"}]}) == 99
    assert _response_seed({"data": [{"url": "x"}]}) is None
    assert _response_seed({"meta": {"seed": 7}}) == 7
    # generate path stores response seed over submitted
    import unittest.mock as mock
    from providers.nanogpt import NanoGptProvider
    prov = NanoGptProvider()
    with mock.patch("providers.nanogpt.nano_key", return_value="test-key"):
        with mock.patch("providers.nanogpt.find_spec", return_value={
            "id": "z-image-turbo",
            "category": "image",
            "supported_parameters": {"resolutions": ["1024x1024"]},
            "capabilities": {},
        }):
            with mock.patch("providers.nanogpt.json_call") as jc:
                with mock.patch("providers.nanogpt._save_result", return_value=[{"url": "/out/x.jpg", "file": "x.jpg"}]):
                    jc.return_value = (200, {"data": [{"url": "https://example.com/a.png", "seed": 555}], "cost": 0.01})
                    code, body = prov.generate({
                        "serviceId": "z-image-turbo",
                        "prompt": "hi",
                        "width": 1024,
                        "height": 1024,
                        "seed": 111,
                    })
                    assert code == 200, (code, body)
                    assert body.get("seed") == 555, body
                    # fallback to submitted when response has no seed
                    jc.return_value = (200, {"data": [{"url": "https://example.com/b.png"}]})
                    code2, body2 = prov.generate({
                        "serviceId": "z-image-turbo",
                        "prompt": "hi",
                        "width": 1024,
                        "height": 1024,
                        "seed": 222,
                    })
                    assert code2 == 200 and body2.get("seed") == 222, body2
                    # v0774: oversized seed → seedOriginal + seedClamped; seed stays response/clamped
                    jc.return_value = (200, {"data": [{"url": "https://example.com/c.png"}]})
                    code3, body3 = prov.generate({
                        "serviceId": "z-image-turbo",
                        "prompt": "hi",
                        "width": 1024,
                        "height": 1024,
                        "seed": 891104780613135,
                    })
                    assert code3 == 200, body3
                    assert body3.get("seed") == 2146323191, body3
                    assert body3.get("seedClamped") is True, body3
                    assert body3.get("seedOriginal") == 891104780613135, body3



    # --- v0777-branch: provider capabilities on /api/providers ---
    from providers.capabilities import (
        PROVIDER_CAPS,
        REQUIRED_KEYS,
        get_provider_capabilities,
        merge_catalog_override,
    )
    import providers as prov_mod
    prov_mod.load()
    pub = {x["id"]: x for x in prov_mod.list_public()}
    for pid in ("civitai", "fal", "huggingface", "modelscope-ai", "modelscope-cn", "nano-gpt"):
        assert pid in pub, pid
        caps = pub[pid].get("capabilities")
        assert isinstance(caps, dict), pid
        for k in REQUIRED_KEYS:
            assert k in caps, f"{pid} missing capabilities.{k}"
        # never silent full-support for unknown
        assert caps["lora"] in ("air", "path", "hub_repo", "none")
        assert caps["loraConfidence"] in ("official", "unverified", "none")
        assert caps["progress"] in ("rate", "queue", "status_only", "none")
    assert pub["huggingface"]["capabilities"]["loraConfidence"] == "unverified"
    assert pub["nano-gpt"]["capabilities"]["resolution"] == "catalog_token"
    assert pub["nano-gpt"]["capabilities"]["promptMax"] == 1200
    # override must not raise: provider lora=none cannot get supportsLora true
    weak = get_provider_capabilities("huggingface")
    # simulate a none provider
    none_caps = get_provider_capabilities("___missing___")
    assert none_caps["lora"] == "none"
    merged = merge_catalog_override(none_caps, {"supportsLora": True, "lora": "path"})
    assert merged["supportsLora"] is False
    assert merged["lora"] == "none"
    # path provider can set supportsLora false (narrow)
    merged2 = merge_catalog_override(get_provider_capabilities("fal"), {"supportsLora": False})
    assert merged2["supportsLora"] is False
    # P0: must not raise confidence / progress / promptMax
    hf = get_provider_capabilities("huggingface")
    assert hf["loraConfidence"] == "unverified"
    bad_conf = merge_catalog_override(hf, {"loraConfidence": "official"})
    assert bad_conf["loraConfidence"] == "unverified", bad_conf
    nano = get_provider_capabilities("nano-gpt")
    assert nano["promptMax"] == 1200 and nano["progress"] == "none"
    bad_prog = merge_catalog_override(nano, {"progress": "rate"})
    assert bad_prog["progress"] == "none", bad_prog
    bad_max = merge_catalog_override(nano, {"promptMax": None})
    assert bad_max["promptMax"] == 1200, bad_max
    # narrowing still ok
    ok_max = merge_catalog_override(nano, {"promptMax": 800})
    assert ok_max["promptMax"] == 800



    # --- graph_compile linear real-edges ---
    from providers.graph_compile import compile_graph, OP_SPEC
    g = {
        "backend": "nano-gpt",
        "nodes": [
            {"id": "p", "op": "prompt", "params": {"text": "hello"}},
            {"id": "g", "op": "t2i", "params": {"serviceId": "z-image-turbo-lora", "width": 1, "height": 2, "resolution": "1024*1536"}},
        ],
        "edges": [{"from": "p", "fromPort": "prompt", "to": "g", "toPort": "prompt"}],
    }
    cg = compile_graph(g)
    assert cg.get("ok"), cg
    assert cg["payload"]["prompt"] == "hello"
    assert "width" not in cg["payload"] and "height" not in cg["payload"]
    steal = compile_graph({
        "backend": "nano-gpt",
        "nodes": [{"id": "g", "op": "t2i", "params": {"serviceId": "z", "prompt": "steal-me"}}],
        "edges": [],
    })
    assert not steal.get("ok") and steal.get("blocked")
    assert "未连线" in steal.get("error", "")

    # P1: params.seed must NOT bypass missing seed edge
    seed_bypass = compile_graph({
        "backend": "nano-gpt",
        "nodes": [
            {"id": "p", "op": "prompt", "params": {"text": "hi"}},
            {"id": "g", "op": "t2i", "params": {"serviceId": "z", "seed": 999}},
        ],
        "edges": [{"from": "p", "fromPort": "prompt", "to": "g", "toPort": "prompt"}],
    })
    assert not seed_bypass.get("ok") and seed_bypass.get("blocked"), seed_bypass
    assert "params.seed" in seed_bypass.get("error", "") or "只认连线" in seed_bypass.get("error", "")

    # wired seed still works
    seed_ok = compile_graph({
        "backend": "nano-gpt",
        "nodes": [
            {"id": "p", "op": "prompt", "params": {"text": "hi"}},
            {"id": "s", "op": "seed", "params": {"value": 42}},
            {"id": "g", "op": "t2i", "params": {"serviceId": "z"}},
        ],
        "edges": [
            {"from": "p", "fromPort": "prompt", "to": "g", "toPort": "prompt"},
            {"from": "s", "fromPort": "seed", "to": "g", "toPort": "seed"},
        ],
    })
    assert seed_ok.get("ok") and seed_ok["payload"]["seed"] == 42

    # P1: lora_apply must merge into sink loras
    lora_g = compile_graph({
        "backend": "civitai",
        "nodes": [
            {"id": "p", "op": "prompt", "params": {"text": "hi"}},
            {"id": "l", "op": "lora_apply", "params": {"loras": [{"air": "urn:air:x", "strength": 0.8}]}},
            {"id": "g", "op": "t2i", "params": {"serviceId": "ckpt"}},
        ],
        "edges": [
            {"from": "p", "fromPort": "prompt", "to": "g", "toPort": "prompt"},
            {"from": "l", "fromPort": "loras", "to": "g", "toPort": "loras"},
        ],
    })
    assert lora_g.get("ok"), lora_g
    assert lora_g["payload"].get("loras") and lora_g["payload"]["loras"][0]["air"] == "urn:air:x"

    # P1: multi-sink must block (no silent last-wins)
    multi = compile_graph({
        "backend": "nano-gpt",
        "nodes": [
            {"id": "p", "op": "prompt", "params": {"text": "hi"}},
            {"id": "g1", "op": "t2i", "params": {"serviceId": "a"}},
            {"id": "g2", "op": "t2i", "params": {"serviceId": "b"}},
        ],
        "edges": [
            {"from": "p", "fromPort": "prompt", "to": "g1", "toPort": "prompt"},
            {"from": "p", "fromPort": "prompt", "to": "g2", "toPort": "prompt"},
        ],
    })
    assert not multi.get("ok") and multi.get("blocked")
    assert "一个生成汇点" in multi.get("error", "")

    # P1: must not mutate caller graph
    g2 = {
        "backend": "nano-gpt",
        "nodes": [
            {"id": "p", "op": "prompt", "params": {"text": "hello"}},
            {"id": "g", "op": "t2i", "params": {"serviceId": "z", "resolution": "1024*1536"}},
        ],
        "edges": [{"from": "p", "fromPort": "prompt", "to": "g", "toPort": "prompt"}],
    }
    keys_before = set(g2.keys())
    assert compile_graph(g2).get("ok")
    assert set(g2.keys()) == keys_before
    assert "_last_payload" not in g2 and "_last_sink" not in g2


    # --- graph_compile: image source, orphan lora, wire-only neg/loras ---
    from providers.graph_compile import compile_graph as _cg
    _i2i = _cg({
        "backend": "nano-gpt",
        "nodes": [
            {"id": "p", "op": "prompt", "params": {"text": "hi"}},
            {"id": "img", "op": "image", "params": {"url": "https://ex/a.png"}},
            {"id": "g", "op": "i2i", "params": {"serviceId": "z-image-turbo-lora"}},
        ],
        "edges": [
            {"from": "p", "fromPort": "prompt", "to": "g", "toPort": "prompt"},
            {"from": "img", "fromPort": "image", "to": "g", "toPort": "image"},
        ],
    })
    assert _i2i.get("ok"), _i2i
    assert _i2i["payload"].get("sourceImage")
    _orphan = _cg({
        "backend": "nano-gpt",
        "nodes": [
            {"id": "p", "op": "prompt", "params": {"text": "hi"}},
            {"id": "l", "op": "lora_apply", "params": {"loras": [{"path": "a", "scale": 1}]}},
            {"id": "g", "op": "t2i", "params": {"serviceId": "z"}},
        ],
        "edges": [{"from": "p", "fromPort": "prompt", "to": "g", "toPort": "prompt"}],
    })
    assert not _orphan.get("ok") and "静默无效" in _orphan.get("error", "")
    _bypass = _cg({
        "backend": "nano-gpt",
        "nodes": [
            {"id": "p", "op": "prompt", "params": {"text": "hi"}},
            {"id": "g", "op": "t2i", "params": {"serviceId": "z", "loras": [{"path": "a"}], "negativePrompt": "n"}},
        ],
        "edges": [{"from": "p", "fromPort": "prompt", "to": "g", "toPort": "prompt"}],
    })
    assert not _bypass.get("ok") and _bypass.get("blocked")

    # --- i2v: image→video main path ---
    assert pub["civitai"]["capabilities"]["i2v"] == "sourceImage"
    assert pub["fal"]["capabilities"]["i2v"] == "fal_endpoint"
    assert pub["huggingface"]["capabilities"]["i2v"] == "none"
    assert pub["nano-gpt"]["capabilities"]["i2v"] == "image_url"
    # cannot raise i2v from none
    bad_i2v = merge_catalog_override(get_provider_capabilities("huggingface"), {"i2v": "image_url"})
    assert bad_i2v["i2v"] == "none", bad_i2v

    i2v_ok = compile_graph({
        "backend": "civitai",
        "nodes": [
            {"id": "img", "op": "image", "params": {"url": "https://ex/frame.png"}},
            {"id": "p", "op": "prompt", "params": {"text": "pan left"}},
            {"id": "v", "op": "i2v", "params": {"serviceId": "video/minimax-h3-comfy/imageToVideo", "duration": 5}},
        ],
        "edges": [
            {"from": "img", "fromPort": "image", "to": "v", "toPort": "image"},
            {"from": "p", "fromPort": "prompt", "to": "v", "toPort": "prompt"},
        ],
    })
    assert i2v_ok.get("ok"), i2v_ok
    pl = i2v_ok["payload"]
    assert pl.get("kind") == "video" and pl.get("recipe") == "video"
    assert pl.get("sourceImage") == "https://ex/frame.png"
    assert pl.get("firstFrame") == "https://ex/frame.png"
    assert pl.get("prompt") == "pan left"
    assert pl.get("duration") == 5

    # missing image edge → blocked, no gallery steal
    i2v_steal = compile_graph({
        "backend": "civitai",
        "nodes": [{"id": "v", "op": "i2v", "params": {"serviceId": "video/x"}}],
        "edges": [],
    })
    assert not i2v_steal.get("ok") and i2v_steal.get("blocked")
    assert "未连线" in i2v_steal.get("error", "")

    # HF i2v=none → blocked
    i2v_hf = compile_graph({
        "backend": "huggingface",
        "nodes": [
            {"id": "img", "op": "image", "params": {"url": "https://ex/a.png"}},
            {"id": "v", "op": "i2v", "params": {"serviceId": "x"}},
        ],
        "edges": [{"from": "img", "fromPort": "image", "to": "v", "toPort": "image"}],
    })
    assert not i2v_hf.get("ok") and i2v_hf.get("blocked")
    assert "不支持图生视频" in i2v_hf.get("error", "")

    # fake chain t2i→i2v in one compile → blocked
    fake_chain = compile_graph({
        "backend": "nano-gpt",
        "nodes": [
            {"id": "p", "op": "prompt", "params": {"text": "hi"}},
            {"id": "g", "op": "t2i", "params": {"serviceId": "z"}},
            {"id": "v", "op": "i2v", "params": {"serviceId": "vid"}},
        ],
        "edges": [
            {"from": "p", "fromPort": "prompt", "to": "g", "toPort": "prompt"},
            {"from": "g", "fromPort": "image", "to": "v", "toPort": "image"},
        ],
    })
    assert not fake_chain.get("ok") and fake_chain.get("blocked")
    # either intermediate sink block or pending chain block
    assert ("不支持把" in fake_chain.get("error", "") or "第二刀" in fake_chain.get("error", "") or "链式" in fake_chain.get("error", ""))

    # Nano i2v strips WxH when catalog_token + imageUrl/mode
    i2v_nano = compile_graph({
        "backend": "nano-gpt",
        "nodes": [
            {"id": "img", "op": "image", "params": {"url": "https://ex/a.png"}},
            {"id": "v", "op": "i2v", "params": {"serviceId": "vid", "width": 1, "height": 2, "resolution": "1280x720"}},
        ],
        "edges": [{"from": "img", "fromPort": "image", "to": "v", "toPort": "image"}],
    })
    assert i2v_nano.get("ok"), i2v_nano
    assert "width" not in i2v_nano["payload"] and "height" not in i2v_nano["payload"]
    assert i2v_nano["payload"].get("resolution") == "1280x720"
    assert i2v_nano["payload"].get("imageUrl") == "https://ex/a.png"
    assert i2v_nano["payload"].get("image_url") == "https://ex/a.png"
    assert i2v_nano["payload"].get("mode") == "image-to-video"
    assert i2v_nano.get("wiring", {}).get("out", {}).get("mode") == "image-to-video"

    # Fal i2v maps endpoint first-frame field (not silent source steal)
    i2v_fal = compile_graph({
        "backend": "fal",
        "nodes": [
            {"id": "img", "op": "image", "params": {"url": "https://ex/f.png"}},
            {"id": "v", "op": "i2v", "params": {"serviceId": "fal-ai/kling-video/v2.5-turbo/standard/image-to-video"}},
        ],
        "edges": [{"from": "img", "fromPort": "image", "to": "v", "toPort": "image"}],
    })
    assert i2v_fal.get("ok"), i2v_fal
    assert i2v_fal["payload"].get("image_url") == "https://ex/f.png"
    assert i2v_fal["payload"].get("firstFrame") == "https://ex/f.png"
    assert "image_url" in (i2v_fal.get("wiring") or {}).get("out", {})

    # Modelscope i2v → image_url
    i2v_ms = compile_graph({
        "backend": "modelscope-ai",
        "nodes": [
            {"id": "img", "op": "image", "params": {"url": "https://ex/m.png"}},
            {"id": "v", "op": "i2v", "params": {"serviceId": "Wan-AI/Wan2.1-I2V-14B-480P"}},
        ],
        "edges": [{"from": "img", "fromPort": "image", "to": "v", "toPort": "image"}],
    })
    assert i2v_ms.get("ok"), i2v_ms
    assert i2v_ms["payload"].get("image_url") == "https://ex/m.png"
    assert i2v_ms.get("wiring", {}).get("out", {}).get("image_url") == "https://ex/m.png"

    # Civitai keeps sourceImage (no Nano mode, no fal invent)
    assert i2v_ok["payload"].get("sourceImage") and "mode" not in i2v_ok["payload"]
    assert pub["modelscope-cn"]["capabilities"]["i2v"] == "image_url"
    assert "videoDuration" in pub["nano-gpt"]["capabilities"]
    assert pub["nano-gpt"]["capabilities"]["videoDuration"] == "string_seconds"
    assert pub["huggingface"]["capabilities"]["videoAspect"] is False

    # no image edge must not invent image fields on payload
    assert "sourceImage" not in (i2v_steal.get("payload") or {})
    assert "imageUrl" not in (i2v_steal.get("payload") or {})

    # UI demo markers for image→i2v
    cn_html = (Path(__file__).resolve().parent.parent / "static" / "cloud-nodes.html").read_text()
    assert "op:'i2v'" in cn_html
    assert "btnBreakImage" in cn_html
    assert "image→i2v" in cn_html
    assert "toPort:'image'" in cn_html
    # Cold-start: serviceId must match default backend family (not fal SID on nano-gpt)
    assert "syncColdStartServiceId" in cn_html
    assert 'value="vidu-q2-pro"' in cn_html
    assert "i2v" in OP_SPEC, "server must register i2v or UI shows 未知 op: i2v"
    # Default demo graph (image→i2v + prompt/seed) must compile green on nano-gpt
    demo = compile_graph({
        "backend": "nano-gpt",
        "nodes": [
            {"id": "img", "op": "image", "params": {"url": "https://example.com/frame.png"}},
            {"id": "p", "op": "prompt", "params": {"text": "camera slowly pans left, cinematic"}},
            {"id": "s", "op": "seed", "params": {"value": 4924112}},
            {"id": "v", "op": "i2v", "params": {"serviceId": "vidu-q2-pro", "duration": 5, "resolution": "1280x720"}},
        ],
        "edges": [
            {"from": "img", "fromPort": "image", "to": "v", "toPort": "image"},
            {"from": "p", "fromPort": "prompt", "to": "v", "toPort": "prompt"},
            {"from": "s", "fromPort": "seed", "to": "v", "toPort": "seed"},
        ],
    })
    assert demo.get("ok"), demo
    assert "未知 op" not in (demo.get("error") or "")

    print("PASS p0 wiring")


    return 0


if __name__ == "__main__":
    raise SystemExit(main())
