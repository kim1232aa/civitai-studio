"""Provider capability declarations (docs/capability-schema.md).

Single source for GET /api/providers[].capabilities.
Catalog overrides may narrow / specialize, never raise a weaker provider limit.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any

# Formal enums — missing key in tests = fail (never silent full-support).
LORA = ("air", "path", "hub_repo", "none")
LORA_PATH = ("http", "civitai_download", "hub_owner_repo", "none")
LORA_CONF = ("official", "unverified", "none")
RESOLUTION = ("free_wh", "catalog_token", "aspect", "none")
PROGRESS = ("rate", "queue", "status_only", "none")
ESTIMATE = ("buzz", "pricing_api", "catalog_price", "none")
I2I = ("source", "first_frame", "input_references", "none")
I2V = ("sourceImage", "image_url", "first_frame", "fal_endpoint", "none")
SEED_CLAMP = ("reject", "mod", "none")

_WEAK_LORA_RANK = {"none": 0, "hub_repo": 1, "path": 2, "air": 3}
_WEAK_RES_RANK = {"none": 0, "aspect": 1, "catalog_token": 2, "free_wh": 3}
_WEAK_I2V_RANK = {"none": 0, "first_frame": 1, "image_url": 2, "sourceImage": 2, "fal_endpoint": 2}


def _seed(min_v=None, max_v=None, clamp="none"):
    return {"min": min_v, "max": max_v, "clamp": clamp}


# Six backends — explicit none everywhere unknown.
PROVIDER_CAPS: dict[str, dict[str, Any]] = {
    "civitai": {
        "lora": "air",
        "loraPath": "none",
        "loraConfidence": "official",
        "resolution": "free_wh",
        "seed": _seed(clamp="none"),
        "promptMax": None,
        "negative": True,
        "progress": "rate",
        "cancel": True,
        "estimate": "buzz",
        "sampler": True,
        "i2i": "source",
        "video": True,
        "i2v": "sourceImage",
        "videoDuration": True,
        "videoAspect": True,
        "upscale": False,  # only reachable via ComfyUI workflow builder, not a plain serviceId call
    },
    "fal": {
        "lora": "path",
        "loraPath": "http",
        "loraConfidence": "official",
        "resolution": "free_wh",
        "seed": _seed(clamp="none"),
        "promptMax": None,
        "negative": True,
        "progress": "queue",
        "cancel": True,
        "estimate": "pricing_api",
        "sampler": False,
        "i2i": "first_frame",
        "video": True,
        "i2v": "fal_endpoint",
        "videoDuration": True,
        "videoAspect": True,
        "upscale": True,  # build_fal_input maps sourceImage generically off catalog imageFields
    },
    "huggingface": {
        "lora": "path",
        "loraPath": "http",
        "loraConfidence": "unverified",  # routed path ≠ official /lora
        "resolution": "free_wh",
        "seed": _seed(min_v=-1, max_v=2147483647, clamp="mod"),
        "promptMax": None,
        "negative": True,
        "progress": "none",
        "cancel": False,
        "estimate": "none",
        "sampler": False,
        "i2i": "none",
        "video": True,
        "i2v": "none",
        "videoDuration": False,
        "videoAspect": False,
        "upscale": False,  # _call_bytes never sends an image field at all today
    },
    "modelscope-ai": {
        "lora": "hub_repo",
        "loraPath": "hub_owner_repo",
        "loraConfidence": "official",
        "resolution": "free_wh",
        "seed": _seed(min_v=-1, max_v=2147483647, clamp="mod"),
        "promptMax": None,
        "negative": True,
        "progress": "status_only",
        "cancel": False,
        "estimate": "none",
        "sampler": False,
        "i2i": "source",
        "video": True,
        "i2v": "image_url",
        "videoDuration": False,
        "videoAspect": True,
        "upscale": True,  # generate() now uses wants_source_image(mid) = is_edit(mid) or hub_upscale_blob(mid); 8 real upscale models confirmed via /api/catalog
    },
    "modelscope-cn": {
        "lora": "hub_repo",
        "loraPath": "hub_owner_repo",
        "loraConfidence": "official",
        "resolution": "free_wh",
        "seed": _seed(min_v=-1, max_v=2147483647, clamp="mod"),
        "promptMax": None,
        "negative": True,
        "progress": "status_only",
        "cancel": False,
        "estimate": "none",
        "sampler": False,
        "i2i": "source",
        "video": True,
        "i2v": "image_url",
        "videoDuration": False,
        "videoAspect": True,
        "upscale": True,  # same fix, same 8 models (AI/CN share one Hub catalog)
    },
    "nano-gpt": {
        "lora": "path",
        "loraPath": "civitai_download",
        "loraConfidence": "official",
        "resolution": "catalog_token",
        "seed": _seed(min_v=-1, max_v=2147483647, clamp="mod"),
        "promptMax": 1200,
        "negative": True,
        "progress": "none",
        "cancel": False,
        "estimate": "catalog_price",
        "sampler": False,
        "i2i": "input_references",
        "video": True,
        "i2v": "image_url",
        "videoDuration": "string_seconds",
        "videoAspect": True,
        "upscale": True,  # _source_images() attaches sourceImage unconditionally, no model-id gate
    },
}

REQUIRED_KEYS = (
    "lora",
    "loraPath",
    "loraConfidence",
    "resolution",
    "seed",
    "promptMax",
    "negative",
    "progress",
    "cancel",
    "estimate",
    "sampler",
    "i2i",
    "video",
    "i2v",
    "videoDuration",
    "videoAspect",
    "upscale",
)


def get_provider_capabilities(provider_id: str) -> dict[str, Any]:
    base = PROVIDER_CAPS.get(provider_id)
    if not base:
        # Unknown provider: explicit none everywhere (never silent full-support).
        return {
            "lora": "none",
            "loraPath": "none",
            "loraConfidence": "none",
            "resolution": "none",
            "seed": _seed(clamp="none"),
            "promptMax": None,
            "negative": False,
            "progress": "none",
            "cancel": False,
            "estimate": "none",
            "sampler": False,
            "i2i": "none",
            "video": False,
            "i2v": "none",
            "videoDuration": False,
            "videoAspect": False,
            "upscale": False,
        }
    return deepcopy(base)


def merge_catalog_override(provider_caps: dict, override: dict | None) -> dict:
    """Catalog may specialize / narrow; must never raise a weaker provider limit.

    Raise examples that must be rejected:
    - loraConfidence: unverified → official
    - progress: none → rate|queue|status_only
    - promptMax: 1200 → None (unlimited is weaker constraint / raise)
    - lora: none → path|air|hub_repo
    - supportsLora True when provider lora is none
    """
    out = deepcopy(provider_caps or {})
    if not override:
        return out
    o = dict(override)

    # --- lora ---
    if "lora" in o:
        p, c = out.get("lora", "none"), o["lora"]
        if _WEAK_LORA_RANK.get(c, -1) <= _WEAK_LORA_RANK.get(p, 0):
            out["lora"] = c
            if c == "none":
                out["loraConfidence"] = "none"
        # else reject raise

    if "supportsLora" in o:
        want = bool(o["supportsLora"])
        if out.get("lora") == "none" and want:
            want = False
        out["supportsLora"] = want

    # --- loraConfidence: official > unverified > none; only allow equal or weaker ---
    _CONF_RANK = {"none": 0, "unverified": 1, "official": 2}
    if "loraConfidence" in o:
        if out.get("lora") == "none":
            out["loraConfidence"] = "none"
        else:
            p = out.get("loraConfidence", "none")
            c = o["loraConfidence"]
            if _CONF_RANK.get(c, -1) <= _CONF_RANK.get(p, 0):
                out["loraConfidence"] = c
            # else reject raise (keep provider)

    # --- progress: none is weakest; cannot raise to rate/queue/status_only ---
    _PROG_RANK = {"none": 0, "status_only": 1, "queue": 2, "rate": 3}
    if "progress" in o:
        p = out.get("progress", "none")
        c = o["progress"]
        if _PROG_RANK.get(c, -1) <= _PROG_RANK.get(p, 0):
            out["progress"] = c

    # --- promptMax: smaller is stricter; None means unlimited = raise if provider had a finite max ---
    if "promptMax" in o:
        p = out.get("promptMax", None)
        c = o["promptMax"]
        if p is None:
            # provider unlimited: catalog may set a finite max (narrow) or stay None
            out["promptMax"] = c
        elif c is None:
            # reject raise to unlimited
            pass
        else:
            try:
                if int(c) <= int(p):
                    out["promptMax"] = int(c)
            except (TypeError, ValueError):
                pass

    # --- resolution: allow specialize free_wh → catalog_token; none is weakest ---
    if "resolution" in o:
        p, c = out.get("resolution", "none"), o["resolution"]
        if c == "none" or _WEAK_RES_RANK.get(c, 0) <= _WEAK_RES_RANK.get(p, 0) or (
            p == "free_wh" and c == "catalog_token"
        ):
            out["resolution"] = c

    # --- i2v: none weakest; catalog cannot invent i2v if provider has none ---
    if "i2v" in o:
        p0, c = out.get("i2v", "none"), o["i2v"]
        if p0 == "none":
            out["i2v"] = "none"
        elif c == "none" or c == p0:
            out["i2v"] = c
        # else reject raise / swap to invented shape

    if "videoDuration" in o:
        p = out.get("videoDuration", False)
        c = o["videoDuration"]
        if p in (False, 0, None):
            out["videoDuration"] = False
        else:
            out["videoDuration"] = c

    if "videoAspect" in o:
        if not out.get("videoAspect"):
            out["videoAspect"] = False
        else:
            out["videoAspect"] = bool(o["videoAspect"])

    if "upscale" in o:
        if not out.get("upscale"):
            out["upscale"] = False
        else:
            out["upscale"] = bool(o["upscale"])

    for k in (
        "resolutionTokens",
        "imageFields",
        "aspectRatioField",
        "durationField",
        "promptField",
        "loraShape",
    ):
        if k in o:
            out[k] = o[k]

    return out
