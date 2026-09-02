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
SEED_CLAMP = ("reject", "mod", "none")

_WEAK_LORA_RANK = {"none": 0, "hub_repo": 1, "path": 2, "air": 3}
_WEAK_RES_RANK = {"none": 0, "aspect": 1, "catalog_token": 2, "free_wh": 3}


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
        "video": False,
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
        "video": False,
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
        }
    return deepcopy(base)


def merge_catalog_override(provider_caps: dict, override: dict | None) -> dict:
    """Catalog may specialize; must not raise weaker provider limits."""
    out = deepcopy(provider_caps or {})
    if not override:
        return out
    o = dict(override)

    # lora: only allow equal or weaker rank
    if "lora" in o:
        p, c = out.get("lora", "none"), o["lora"]
        if _WEAK_LORA_RANK.get(c, -1) > _WEAK_LORA_RANK.get(p, 0):
            o.pop("lora", None)  # reject raise
        else:
            out["lora"] = c
            if c == "none":
                out["loraConfidence"] = "none"

    if "supportsLora" in o:
        # supportsLora true forbidden when provider lora is none
        if out.get("lora") == "none" and o["supportsLora"] is True:
            o["supportsLora"] = False
        out["supportsLora"] = bool(o["supportsLora"])

    if "loraConfidence" in o:
        # unverified/none can downgrade official; cannot upgrade none→official via catalog alone if provider none
        conf = o["loraConfidence"]
        if out.get("lora") == "none":
            out["loraConfidence"] = "none"
        else:
            out["loraConfidence"] = conf

    if "resolution" in o:
        p, c = out.get("resolution", "none"), o["resolution"]
        # catalog_token is not "higher" than free_wh — treat as specialize; allow if provider is free_wh or catalog_token
        if c == "none" or _WEAK_RES_RANK.get(c, 0) <= _WEAK_RES_RANK.get(p, 0) or (
            p == "free_wh" and c == "catalog_token"
        ):
            out["resolution"] = c

    for k in (
        "resolutionTokens",
        "imageFields",
        "aspectRatioField",
        "durationField",
        "promptField",
        "progress",
        "loraShape",
        "promptMax",
    ):
        if k in o:
            out[k] = o[k]

    return out
