"""Shared Hub category classifier for ModelScope + Hugging Face catalog rows.

Widen carefully: Nomos/NMKD/4x family upscalers → category=upscale; VAE /
ControlNet / IP-Adapter / umt5+text-encoder / (non-video) GGUF / pure LoRA → utility;
video-family GGUF / video LoRA / Wan checkpoints stay video; plain t2i
(Z-Image-Turbo, FLUX.1-schnell, Qwen-Image, …) stay image.
Bare ``4x`` alone is not enough for upscale — require known family tokens.
"""
from __future__ import annotations

import re

# Explicit upscale tokens (existing + pipeline/task "upscal*")
_UPSCALE_EXPLICIT = re.compile(
    r"onnx|upscal|apisr|realesr|esrgan|super.?res|generator-onnx",
    re.I,
)

# Known upscaler family names (match without requiring a scale factor)
# Bare org ``nmkd/`` alone is NOT upscale — need siax/superscale/scale tokens.
_UPSCALE_FAMILY_TOKENS = re.compile(
    r"\b(?:"
    r"siax|superscale|remacri|ultrasharp|animevig|ldsr|swinir|"
    r"hat-l|dat-2|span|nomos|apisr|esrgan|realesr(?:gan)?|cugan|"
    r"animesharp|schat|compact|latent.?upscaler"
    r")\b"
    r"|nmkd[_-]?siax|nmkd[_-]?superscale|nmkdsuperscale|"
    r"4xnomos|8xnomos|\bnomos\d|nomos8k",
    re.I,
)

# Scale factor glued to known upscaler family (Nomos, APISR, ESRGAN, NMKD, …)
_FAMILY = (
    r"nomos|esrgan|apisr|realesr(?:gan)?|cugan|ultrasharp|remacri|"
    r"swinir|hat(?:-?l)?|dat(?:-?2)?|span|animesharp|animevig|schat|compact|"
    r"latent.?upscaler|lds?r|upscaler?|"
    r"nmkd|siax|superscale"
)
_SCALE_FAMILY = re.compile(rf"\d+x[_-]?(?:{_FAMILY})", re.I)

# Compact Nomos ids: nomos8k, nomos4, 4xnomos, …
_NOMOS = re.compile(r"\bnomos\d|nomos8k|4xnomos|8xnomos|\d+x[_-]?nomos", re.I)

# ``4x`` within ~20 chars of a family token (covers 4x-Foo-Nomos / NMKD_Siax_x4)
_SCALE_NEAR = re.compile(
    rf"\d+x.{{0,20}}(?:{_FAMILY})|(?:{_FAMILY}).{{0,20}}\d+x",
    re.I,
)

# Explicit ``Nx`` + (siax|superscale|nmkd) even when glued oddly
_NMKD_SCALE = re.compile(r"\d+x.{0,24}(?:siax|superscale|nmkd)|(?:siax|superscale|nmkd).{0,24}\d+x", re.I)

# Back-compat alias used by older imports / tests that poke at the regex
_UPSCALE_RE = re.compile(
    rf"(?:onnx|upscal|apisr|realesr|esrgan|super.?res|generator-onnx|"
    rf"\d+x[_-]?(?:{_FAMILY})|\bnomos\d|nomos8k|4xnomos|8xnomos|"
    rf"siax|superscale|nmkd[_-]?siax|nmkd[_-]?superscale|nmkdsuperscale)",
    re.I,
)

# --- non-t2i adapters / weight dumps → utility ---
# Sticky VAE: _vae / 12VAE_pruned / v1.2VAE — not bare "wave". CamelCase VAE is case-sensitive.
_VAE = re.compile(
    r"(?i:(?:^|[\W_\d])vae(?:$|[\W_\d]))|"
    r"(?i:flux[_-]vae)|ae\.safetensors|"
    r"(?i:vae(?:_pruned|_ft|\d))|"
    r"[a-z0-9]VAE(?:[A-Z_]|_|$)|_VAE_"
)
_IP_ADAPTER = re.compile(
    r"ip-adapter|ip_adapter|ipadapter|ip-composition-adapter|ip_composition_adapter",
    re.I,
)
_CONTROLNET = re.compile(r"controlnet|control_net|control-lora|control_lora", re.I)
# Text encoders (UMT5 / T5 / CLIP text-encoder dumps) — not t2i checkpoints.
# Before video-family GGUF exception: never video even if name has wan (wan2.1-umt5).
_TEXT_ENCODER = re.compile(
    # umt5_xxl_encoder: allow _ after mt5 (\b fails because _ is a word char)
    # v0766: sd35_t5xxl / sd35_clip_l — same \b hole; allow [_-] / non-word prefix
    r"\bu[_-]?mt5(?:\b|[_-]|$)|wan2\.1[_-]?u[_-]?mt5|umt5[_-]|"
    r"(?:^|[\W_])t5[_-]?xxl(?:\b|[_-]|$)|(?:^|[\W_])t5[_-](?:xl|base|small|large)(?:\b|[_-]|$)|"
    r"(?:^|[\W_])t5\s*encoder\b|t5[_-]encoder|"
    r"text[_-]?encoder|text-encoding|text_encoding|"
    r"(?:^|[\W_])clip[_-]l(?:\b|[_-]|$)",
    re.I,
)
_GGUF = re.compile(r"\.gguf\b|\bgguf\b", re.I)
# Pure LoRA weight repos: tokenized lora or ends with _lora / -lora
_LORA_TOKEN = re.compile(r"(^|[_/-])loras?($|[_/-])", re.I)
_LORA_SUFFIX = re.compile(r"[_-]loras?$", re.I)
# Keep full t2i checkpoints that happen to mention lora-ish base names
_T2I_BASE = re.compile(
    r"z-image-turbo|z_image_turbo|flux\.1|flux-1|sd3|stable.?diffusion.?3|"
    r"qwen-image|tongyi-mai",
    re.I,
)
# Video diffusion families — GGUF/LoRA of these stay video, not utility.
_VIDEO_FAMILY = re.compile(
    r"\b(?:"
    r"wan|hunyuan\s*video|hunyuanvideo|ltx|allegro|cogvideo|mochi|"
    r"open-?sora|opensora|animatediff|animate.?diff|"
    r"i2v|t2v|text-to-video|image-to-video|vid2vid"
    r")\b|\bvideo\b",
    re.I,
)


def _hub_blob_parts(it) -> list[str]:
    if not isinstance(it, dict):
        return []
    parts = [
        it.get("id") or "",
        it.get("name") or "",
        it.get("chinese_name") or "",
        it.get("task") or "",
        it.get("hubTask") or "",
        it.get("pipelineTag") or "",
        it.get("pipeline_tag") or "",
        " ".join(str(t) for t in (it.get("tags") or []) if t),
    ]
    tasks = it.get("tasks") or it.get("Tasks") or []
    if isinstance(tasks, str):
        parts.append(tasks)
    elif isinstance(tasks, (list, tuple)):
        parts.append(" ".join(str(t) for t in tasks))
    return parts


def blob_is_upscale(blob: str) -> bool:
    s = blob or ""
    if not s.strip():
        return False
    if _UPSCALE_EXPLICIT.search(s):
        return True
    if _NOMOS.search(s):
        return True
    if _UPSCALE_FAMILY_TOKENS.search(s):
        return True
    if _SCALE_FAMILY.search(s):
        return True
    if _SCALE_NEAR.search(s):
        return True
    if _NMKD_SCALE.search(s):
        return True
    return False


def hub_upscale_blob(it) -> bool:
    """True when Hub id/name/task/tags look like an upscaler (not Z-Image-Turbo)."""
    if not isinstance(it, dict):
        return False
    return blob_is_upscale(" ".join(_hub_blob_parts(it)))


def _id_name_blob(it) -> str:
    if not isinstance(it, dict):
        return ""
    return f"{it.get('id') or ''} {it.get('name') or ''}"


def _is_video_family(blob: str, it=None) -> bool:
    if it and isinstance(it, dict) and (it.get("category") or "") == "video":
        return True
    return bool(_VIDEO_FAMILY.search(blob or ""))


def blob_is_utility(blob: str, *, id_name: str = "", it=None) -> bool:
    """Non-t2i adapter / VAE / ControlNet / (non-video) GGUF / pure LoRA weight dump.

    Video-family GGUF / video LoRA / Wan checkpoints are NOT utility.
    Pure VAE (wan_2.1_vae, *_vae) and umt5 / text-encoder / T5 encoder still utility.
    """
    s = blob or ""
    if not s.strip():
        return False
    if _VAE.search(s):
        return True
    if _IP_ADAPTER.search(s):
        return True
    if _CONTROLNET.search(s):
        return True
    if _TEXT_ENCODER.search(s):
        return True
    videoish = _is_video_family(s, it)
    if _GGUF.search(s):
        return not videoish
    # LoRA: inspect id/name. Clear ``something-lora`` / ``*_lora`` adapters → utility
    # even when the base name mentions flux.1 / qwen-image / z-image-turbo.
    # Video LoRA packages stay video.
    ln = id_name or s
    mid = (ln.split() or [""])[0]
    name = ln[len(mid) :].strip() if " " in ln else ""
    leaf = mid.rsplit("/", 1)[-1] if mid else ""
    lora_hit = False
    for piece in (mid, leaf, name, ln):
        if not piece:
            continue
        if _LORA_SUFFIX.search(piece) or _LORA_TOKEN.search(piece):
            lora_hit = True
            break
    if not lora_hit:
        return False
    if videoish:
        return False
    # Borderline: full t2i checkpoint id that only mentions lora loosely — keep image.
    # Clear adapter leaf (ends with _lora / -lora or tokenized lora) always utility.
    for piece in (leaf, name):
        if piece and (_LORA_SUFFIX.search(piece) or _LORA_TOKEN.search(piece)):
            return True
    if _T2I_BASE.search(ln):
        return False
    return True


def hub_utility_blob(it) -> bool:
    if not isinstance(it, dict):
        return False
    blob = " ".join(_hub_blob_parts(it))
    return blob_is_utility(blob, id_name=_id_name_blob(it), it=it)


def apply_hub_category(row: dict) -> dict:
    """upscale → category upscale; adapter/vae/controlnet/(non-video) gguf/lora → utility; else leave.

    Always reclassify upscale/utility blobs even when Hub already tagged category
    as video (or other non-image) — otherwise wan_2.1_vae slips into the video tab.
    """
    if not isinstance(row, dict):
        return row
    if hub_upscale_blob(row):
        row = dict(row)
        row["category"] = "upscale"
        row["task"] = "upscale"
        tags = list(row.get("tags") or [])
        if "upscale" not in tags:
            tags = ["upscale"] + tags
        row["tags"] = tags
        row.pop("needsSource", None)
        return row
    if hub_utility_blob(row):
        row = dict(row)
        row["category"] = "utility"
        tags = list(row.get("tags") or [])
        if "utility" not in tags:
            tags = ["utility"] + tags
        row["tags"] = tags
        row.pop("needsSource", None)
        return row
    return row


# Back-compat: modelscope / huggingface still import apply_upscale_category
apply_upscale_category = apply_hub_category
_apply_hub_category = apply_hub_category
