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
    assert 'title="v0768"' in html
    assert 'aria-label="生成"' in html
    assert 'aria-label="v0768"' not in html
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

    print("PASS p0 wiring")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
