"""HF catalog row LoRA / channel caps (o57 matching + official API wiring).

Official source: Hub inferenceProviderMapping + adapter channel wiring.
Not official: Inference Providers marketing sentence, Hub filter=lora,
fal-ai/*lora as a Hugging Face serviceId (o33: Router does not host it).

Does not raise i2i/i2v. Closed-loop still 0.
"""
from __future__ import annotations

from typing import Any

_FAL_STYLE = {"fal", "fal-ai", "wavespeed"}
_BLOCKED_STYLE = {"openai", "bytes", "nscale", "together", "hf-inference"}


def _mid(row: dict | None) -> str:
    raw = (row or {}).get("id") or (row or {}).get("model") or ""
    s = str(raw).strip().lstrip("/")
    for pfx in ("huggingface/", "hf/"):
        if s.startswith(pfx):
            s = s[len(pfx):]
    return s


def style_for_provider(provider: str) -> str:
    name = str(provider or "").strip().lower()
    if name == "hf-inference":
        return "bytes"
    if name in ("fal-ai", "wavespeed"):
        return "fal"
    if name in ("nscale", "together"):
        return "openai"
    return name or ""


def mapped_style(mapping: dict | None, prefer: str | None = None) -> str:
    if prefer:
        return style_for_provider(prefer)
    if not isinstance(mapping, dict) or not mapping:
        return ""
    order = ("fal-ai", "nscale", "together", "hf-inference", "wavespeed")
    for want in order:
        info = mapping.get(want)
        if not isinstance(info, dict):
            continue
        st = str(info.get("status") or "").lower()
        if st and st != "live":
            continue
        return style_for_provider(want)
    for name, info in mapping.items():
        if isinstance(info, dict):
            return style_for_provider(name)
    return ""


def overlay_huggingface_catalog_item(
    row: dict | None,
    mapping: dict | None = None,
    mapped_style_name: str | None = None,
) -> dict:
    """Stamp LoRA box metadata on one HF catalog row.

    - fal-ai/*lora serviceId → supportsLora=False (Router does not host)
    - mapped fal style → supportsLora=True, loraConfidence=unverified
    - mapped openai/bytes → supportsLora=False (adapter rejects loras)
    - no mapping → do not invent supportsLora=True
    - Hub tags containing 'lora' must not become official/true alone
    """
    row = dict(row or {})
    mid = _mid(row)
    if mid and not row.get("id"):
        row["id"] = mid
    caps: dict[str, Any] = dict(row["capabilities"]) if isinstance(row.get("capabilities"), dict) else {}
    caps.setdefault("loraShape", "path")

    if mid.startswith("fal-ai/") and "lora" in mid.lower():
        caps["supportsLora"] = False
        caps["loraConfidence"] = "none"
        caps["loraChannel"] = "blocked"
        caps["loraSource"] = "router-ban"
        row["capabilities"] = caps
        row["supportsLora"] = False
        return row

    style = mapped_style_name if mapped_style_name is not None else mapped_style(mapping)
    style = style_for_provider(style) if style else ""

    tags = [str(t).lower() for t in (row.get("tags") or []) if t]
    hub_lora_tag = any("lora" in t for t in tags)

    if style in _FAL_STYLE:
        caps["supportsLora"] = True
        caps["loraConfidence"] = "unverified"
        caps["loraChannel"] = "fal"
        caps["loraSource"] = "adapter-fal-channel"
    elif style in _BLOCKED_STYLE:
        caps["supportsLora"] = False
        caps["loraConfidence"] = "none"
        caps["loraChannel"] = style
        caps["loraSource"] = "adapter-unwired"
    else:
        caps.setdefault("loraConfidence", "unverified")
        caps.setdefault("loraChannel", "")
        caps["loraSource"] = "hub-tag-not-schema" if hub_lora_tag else "unknown-mapping"

    row["capabilities"] = caps
    if "supportsLora" in caps:
        row["supportsLora"] = caps["supportsLora"]
    return row


def overlay_huggingface_catalog(body: dict | None, mapping_by_id: dict | None = None) -> dict:
    if not isinstance(body, dict):
        return {}
    out = dict(body)
    items = out.get("items")
    if not isinstance(items, list):
        return out
    maps = mapping_by_id if isinstance(mapping_by_id, dict) else {}
    stamped = []
    for it in items:
        if not isinstance(it, dict):
            stamped.append(it)
            continue
        stamped.append(overlay_huggingface_catalog_item(it, mapping=maps.get(_mid(it))))
    out["items"] = stamped
    return out
