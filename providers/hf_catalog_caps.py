"""HF catalog row LoRA / channel caps (o57 matching + official API wiring).

Official source: Hub inferenceProviderMapping + adapter channel wiring.
Hub LoRA-as-model (huggingface_hub v0.31+): live mapping with adapter=lora /
adapterWeightsPath → select Hub mid as model= via fal-ai (or replicate in SDK).
Not official: Inference Providers marketing sentence alone, Hub filter=lora tag
alone, fal-ai/*lora as a Hugging Face serviceId (o33: Router does not host it).

Does not raise i2i/i2v. Closed-loop still 0.
"""
from __future__ import annotations

from typing import Any

_FAL_STYLE = {"fal", "fal-ai", "wavespeed"}
_BLOCKED_STYLE = {"openai", "bytes", "nscale", "together", "hf-inference"}
# Official Hub LoRA Inference Providers (huggingface_hub v0.31 release notes).
_HUB_LORA_PROVIDERS = frozenset({"fal-ai", "replicate", "wavespeed"})


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
    order = ("fal-ai", "nscale", "together", "hf-inference", "wavespeed", "replicate")
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


def _mapping_as_dict(raw) -> dict:
    if isinstance(raw, dict):
        return {k: v for k, v in raw.items() if isinstance(v, dict)}
    if not isinstance(raw, list):
        return {}
    out = {}
    for info in raw:
        if not isinstance(info, dict):
            continue
        name = info.get("provider") or info.get("providerName")
        if name:
            out[str(name)] = info
    return out


def mapping_is_hub_lora(mapping: dict | None) -> bool:
    """True when Hub inferenceProviderMapping marks this mid as a LoRA adapter model."""
    for name, info in _mapping_as_dict(mapping).items():
        if not isinstance(info, dict):
            continue
        st = str(info.get("status") or "").lower()
        if st and st != "live":
            continue
        adapter = str(info.get("adapter") or "").lower()
        path = info.get("adapterWeightsPath") or info.get("adapter_weights_path")
        if adapter == "lora" or (isinstance(path, str) and path.strip()):
            # Prefer known Hub-LoRA providers; still true if only those fields exist.
            if name in _HUB_LORA_PROVIDERS or adapter == "lora" or path:
                return True
    return False


def hub_lora_providers(mapping: dict | None) -> list[str]:
    out = []
    for name, info in _mapping_as_dict(mapping).items():
        if not isinstance(info, dict):
            continue
        st = str(info.get("status") or "").lower()
        if st and st != "live":
            continue
        adapter = str(info.get("adapter") or "").lower()
        path = info.get("adapterWeightsPath") or info.get("adapter_weights_path")
        if adapter == "lora" or (isinstance(path, str) and path.strip()):
            out.append(str(name))
    # Official preference: fal-ai then replicate.
    pref = ("fal-ai", "replicate", "wavespeed")
    ordered = [p for p in pref if p in out]
    ordered.extend(p for p in out if p not in ordered)
    return ordered


def _row_mapping(row: dict | None) -> dict:
    row = row or {}
    if isinstance(row.get("inferenceProviderMapping"), (dict, list)):
        return _mapping_as_dict(row.get("inferenceProviderMapping"))
    raw = row.get("hubLoraMapping")
    if isinstance(raw, dict):
        return _mapping_as_dict(raw)
    return {}


def overlay_huggingface_catalog_item(
    row: dict | None,
    mapping: dict | None = None,
    mapped_style_name: str | None = None,
) -> dict:
    """Stamp LoRA box metadata on one HF catalog row.

    - fal-ai/*lora serviceId → supportsLora=False (Router does not host)
    - Hub LoRA-as-model (adapter / adapterWeightsPath) → hubLoraAsModel=True;
      selectable as serviceId; official path via fal-ai/replicate Router mapping
    - mapped fal style (base) → supportsLora=True, loraConfidence=unverified
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
        caps["hubLoraAsModel"] = False
        row["capabilities"] = caps
        row["supportsLora"] = False
        row["hubLoraAsModel"] = False
        return row

    mapping = _mapping_as_dict(mapping) if mapping else _row_mapping(row)
    is_hub_lora = bool(row.get("hubLoraAsModel")) or mapping_is_hub_lora(mapping)

    style = mapped_style_name if mapped_style_name is not None else mapped_style(mapping)
    style = style_for_provider(style) if style else ""

    tags = [str(t).lower() for t in (row.get("tags") or []) if t]
    hub_lora_tag = any("lora" in t for t in tags)

    if is_hub_lora:
        # Official: Hub mid is the model= (v0.31 InferenceClient + fal-ai/replicate).
        # Extra chip attach on the mapped /lora endpoint is schema-dependent → unverified.
        providers = hub_lora_providers(mapping) or ["fal-ai"]
        caps["hubLoraAsModel"] = True
        caps["supportsLora"] = True
        caps["loraConfidence"] = "official"
        caps["loraChannel"] = "hub-lora-as-model"
        caps["loraSource"] = "inference-provider-adapter"
        caps["hubLoraProviders"] = providers
        row["hubLoraAsModel"] = True
        row["supportsLora"] = True
    elif style in _FAL_STYLE:
        caps["supportsLora"] = True
        caps["loraConfidence"] = "unverified"
        caps["loraChannel"] = "fal"
        caps["loraSource"] = "adapter-fal-channel"
        caps["hubLoraAsModel"] = False
    elif style in _BLOCKED_STYLE:
        caps["supportsLora"] = False
        caps["loraConfidence"] = "none"
        caps["loraChannel"] = style
        caps["loraSource"] = "adapter-unwired"
        caps["hubLoraAsModel"] = False
    else:
        caps.setdefault("loraConfidence", "unverified")
        caps.setdefault("loraChannel", "")
        caps["loraSource"] = "hub-tag-not-schema" if hub_lora_tag else "unknown-mapping"
        caps.setdefault("hubLoraAsModel", False)

    row["capabilities"] = caps
    if "supportsLora" in caps:
        row["supportsLora"] = caps["supportsLora"]
    if "hubLoraAsModel" in caps:
        row["hubLoraAsModel"] = caps["hubLoraAsModel"]
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
