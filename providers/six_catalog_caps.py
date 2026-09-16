"""Fal + Nano catalog row stamps from official schema only.

Six-house match: Civitai/魔搭 live in capabilities.py, HF in hf_catalog_caps.py,
Fal/Nano here. Do not invent duration 5/12/16 or promptMax=1200.
"""
from __future__ import annotations

import re
from typing import Any


def _caps(row: dict) -> dict[str, Any]:
    return dict(row["capabilities"]) if isinstance(row.get("capabilities"), dict) else {}


def _params(row: dict) -> dict[str, Any]:
    for key in ("parameters", "supported_parameters", "supportedParameters", "openapi"):
        raw = row.get(key)
        if isinstance(raw, dict):
            return raw
    return {}


def _enum_of(blob: Any) -> list[str] | None:
    if isinstance(blob, list) and blob:
        return [str(x) for x in blob]
    if isinstance(blob, dict):
        vals = blob.get("enum") or blob.get("values") or blob.get("options")
        if isinstance(vals, list) and vals:
            return [str(x) for x in vals]
    return None


def _duration_enum(row: dict, params: dict) -> list[str] | None:
    caps = _caps(row)
    for blob in (
        caps.get("durationEnum"),
        row.get("durationEnum"),
        params.get("duration"),
        params.get("durations"),
        params.get("video_duration"),
    ):
        got = _enum_of(blob)
        if got:
            return got
    return None



_PROMPT_MAX_KEYS = ("promptMax", "prompt_max", "max_chars", "maxLength", "max_length")


def _positive_int(v):
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)) and int(v) > 0:
        return int(v)
    if isinstance(v, str) and v.strip().isdigit():
        n = int(v.strip())
        return n if n > 0 else None
    return None


def nano_prompt_max_from_row(row: dict | None) -> int | None:
    """Official catalog metadata only. Never invent 1200 (or any other number).

    Live GET /api/v1/images/models (2026-09-16) has no promptMax/max_chars field.
    Some descriptions state a limit ("Prompts are limited to 512 characters").
    Measured fail-closed fallback lives in nanogpt.NANO_PROMPT_MAX (400), not here.
    """
    if not isinstance(row, dict):
        return None
    caps = row.get("capabilities") if isinstance(row.get("capabilities"), dict) else {}
    params = _params(row)
    for blob in (row, caps, params):
        if not isinstance(blob, dict):
            continue
        for k in _PROMPT_MAX_KEYS:
            got = _positive_int(blob.get(k))
            if got:
                return got
        prompt = blob.get("prompt")
        if isinstance(prompt, dict):
            for k in ("max", "maxLength", "max_chars", "max_length"):
                got = _positive_int(prompt.get(k))
                if got:
                    return got
    desc = str(row.get("description") or caps.get("description") or "")
    m = re.search(r"limited to\s+([\d,]+)\s+characters", desc, re.I)
    if m:
        n = int(m.group(1).replace(",", ""))
        if n > 0:
            return n
    return None

def _sid_has_lora_token(sid: str) -> bool:
    """Token-level 'lora' in endpoint id (fal-ai/flux-lora, krea-2/turbo/lora).

    Substring match would false-positive on ids like 'floral'; official Fal
    LoRA endpoints carry a real lora path segment or -lora suffix.
    """
    return "lora" in re.split(r"[^a-z0-9]+", sid.lower())


def overlay_fal_catalog_item(row: dict | None) -> dict:
    """Stamp one Fal row from OpenAPI / catalog overlay fields. Never invent 5/12/16."""
    row = dict(row or {})
    caps = _caps(row)
    params = _params(row)
    caps.setdefault("loraShape", "path")
    caps.setdefault("loraConfidence", "official")

    sid = str(row.get("id") or row.get("endpoint") or "").strip()
    if "supportsLora" in row:
        caps["supportsLora"] = bool(row["supportsLora"])
        caps.setdefault("loraSource", "fal-catalog-overlay")
    elif "supportsLora" in caps:
        row["supportsLora"] = bool(caps["supportsLora"])
        caps.setdefault("loraSource", "fal-catalog-overlay")
    elif isinstance(params.get("loras"), (dict, list)) or _sid_has_lora_token(sid):
        caps["supportsLora"] = True
        caps["loraSource"] = "openapi-loras-or-sibling"
        row["supportsLora"] = True

    dur = _duration_enum(row, params)
    if dur:
        caps["durationEnum"] = dur

    fields = row.get("imageFields") or caps.get("imageFields")
    if isinstance(fields, list):
        caps["imageFields"] = fields

    row["capabilities"] = caps
    if "supportsLora" in caps:
        row["supportsLora"] = caps["supportsLora"]
    return row


def overlay_fal_catalog(body: dict | None) -> dict:
    if not isinstance(body, dict):
        return {}
    out = dict(body)
    items = out.get("items")
    if not isinstance(items, list):
        return out
    out["items"] = [overlay_fal_catalog_item(x) if isinstance(x, dict) else x for x in items]
    return out


def overlay_nano_catalog_item(row: dict | None) -> dict:
    """Stamp one Nano row from GET /images/models supported_parameters.

    LoRA flag on *-lora ids is a local heuristic (official Image API has no
    loras key). Mark loraSource=heuristic. Never invent promptMax=1200.
    """
    row = dict(row or {})
    caps = _caps(row)
    params = _params(row)
    caps.setdefault("loraShape", "path")
    sid = str(row.get("id") or row.get("model") or "").lower()
    tags = [str(t).lower() for t in (row.get("tags") or []) if t]

    if "supportsLora" in row:
        caps["supportsLora"] = bool(row["supportsLora"])
        caps.setdefault("loraSource", "nano-catalog")
    elif "supportsLora" in caps:
        row["supportsLora"] = bool(caps["supportsLora"])
    elif "lora" in sid or any("lora" in t for t in tags):
        if any(tok in sid for tok in ("upscale", "bg-removal", "background", "utility")):
            caps["supportsLora"] = False
            caps["loraSource"] = "nano-utility-not-lora"
            row["supportsLora"] = False
        else:
            caps["supportsLora"] = True
            caps["loraSource"] = "heuristic"
            caps["loraConfidence"] = "heuristic"
            row["supportsLora"] = True

    caps.setdefault("loraConfidence", "official" if caps.get("loraSource") != "heuristic" else "heuristic")

    res = params.get("resolutions") or caps.get("resolutionTokens") or row.get("resolutionTokens")
    if isinstance(res, list) and res:
        caps["resolutionTokens"] = [str(x) for x in res]
        caps.setdefault("resolution", "catalog_token")

    dur = _duration_enum(row, params)
    if dur:
        caps["durationEnum"] = dur

    task = str(row.get("task") or "").strip().lower()
    tags_l = tags
    sid_l = sid
    if (
        row.get("needsFirstFrame")
        or task == "image-to-video"
        or "i2v" in tags_l
        or "image-to-video" in sid_l
        or "imagetovideo" in sid_l.replace("-", "")
    ):
        row.setdefault("needsFirstFrame", True)
        row["supportsI2v"] = True
        caps.setdefault("supportsI2v", True)
        caps.setdefault("maxRefs", 1)
        caps.setdefault("maxImages", 1)
        caps.setdefault("refImagesField", "image_url")
        if not caps.get("imageFields"):
            caps["imageFields"] = ["image_url"]
    elif row.get("needsSource") or task == "image-to-image" or "i2i" in tags_l or "/edit" in sid_l or sid_l.endswith("-edit"):
        caps.setdefault("image_to_image", True)
        caps.setdefault("maxRefs", 1)
        caps.setdefault("maxImages", 1)
    elif task in ("text-to-image", "text-to-video") or "t2i" in tags_l or "t2v" in tags_l:
        caps.setdefault("image_to_image", False)
        caps.setdefault("maxRefs", 1)

    got_max = nano_prompt_max_from_row(row)
    if got_max:
        caps["promptMax"] = got_max
        caps.setdefault("promptMaxSource", "catalog-metadata")

    row["capabilities"] = caps
    if "supportsLora" in caps:
        row["supportsLora"] = caps["supportsLora"]
    return row


def overlay_nano_catalog(body: dict | None) -> dict:
    if not isinstance(body, dict):
        return {}
    out = dict(body)
    items = out.get("items")
    if not isinstance(items, list):
        return out
    out["items"] = [overlay_nano_catalog_item(x) if isinstance(x, dict) else x for x in items]
    return out
