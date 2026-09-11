"""Fal + Nano catalog row stamps from official schema only.

Six-house match: Civitai/魔搭 live in capabilities.py, HF in hf_catalog_caps.py,
Fal/Nano here. Do not invent duration 5/12/16 or promptMax=1200.
"""
from __future__ import annotations

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
    elif isinstance(params.get("loras"), (dict, list)) or "/lora" in sid.lower():
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
