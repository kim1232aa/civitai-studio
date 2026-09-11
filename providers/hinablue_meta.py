"""Map a Civitai / hinablue generation-data object onto Composer fields.

Used by import tests and as the contract import_image must honor.
Does not invent strength 1.0. Does not shorten prompts. No HTTP.
"""
from __future__ import annotations

import re
from typing import Any

LORA_TAG = re.compile(r"<lora:([^:>]+)(?::([^>]*))?>", re.I)
SIZE_RE = re.compile(r"(\d+)\s*[x×]\s*(\d+)", re.I)


def _as_int(val: Any) -> int | None:
    if val is None or val is False:
        return None
    if isinstance(val, bool):
        return None
    if isinstance(val, int):
        return val
    if isinstance(val, float):
        return int(val)
    if isinstance(val, str) and val.strip():
        try:
            return int(val.strip(), 10)
        except ValueError:
            try:
                return int(float(val.strip()))
            except ValueError:
                return None
    return None


def _as_float_or_null(val: Any) -> float | None:
    if val is None or val == "":
        return None
    if isinstance(val, bool):
        return None
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, str) and val.strip():
        try:
            return float(val.strip())
        except ValueError:
            return None
    return None


def _dims(meta: dict[str, Any]) -> tuple[int | None, int | None]:
    w = _as_int(meta.get("width") or meta.get("Width"))
    h = _as_int(meta.get("height") or meta.get("Height"))
    if w and h:
        return w, h
    size = meta.get("Size") or meta.get("size") or ""
    m = SIZE_RE.search(str(size))
    if m:
        return int(m.group(1)), int(m.group(2))
    return w, h


def _chip_from_resource(res: Any) -> dict[str, Any] | None:
    if not isinstance(res, dict):
        return None
    kind = str(res.get("type") or res.get("modelType") or "").lower()
    name = str(res.get("name") or res.get("modelName") or "").strip()
    if "lora" not in kind and "lora" not in name.lower() and not res.get("air"):
        if kind in ("checkpoint", "model", "embed", "embedding", "vae"):
            return None
        if not name:
            return None
        return None
    strength = res.get("weight")
    if strength is None:
        strength = res.get("strength")
    if strength is None:
        strength = res.get("multiplier")
    chip = {
        "name": name or str(res.get("air") or ""),
        "air": res.get("air") or res.get("modelAir") or "",
        "strength": _as_float_or_null(strength),
    }
    if res.get("versionId") is not None:
        chip["versionId"] = res.get("versionId")
    if res.get("modelId") is not None:
        chip["modelId"] = res.get("modelId")
    return chip


def _chips_from_prompt_tags(prompt: str) -> list[dict[str, Any]]:
    out = []
    for m in LORA_TAG.finditer(prompt or ""):
        name = m.group(1).strip()
        raw = m.group(2)
        strength = _as_float_or_null(raw if raw is not None and raw != "" else None)
        out.append({"name": name, "air": "", "strength": strength})
    return out


def parse_civitai_generation_meta(meta: dict[str, Any] | None) -> dict[str, Any]:
    """Return Composer-facing fields from a generation-data / image.meta object."""
    src = dict(meta or {})
    prompt = src.get("prompt") or src.get("Prompt") or ""
    if not isinstance(prompt, str):
        prompt = str(prompt or "")
    negative = src.get("negativePrompt") or src.get("Negative prompt") or src.get("negative") or ""
    if not isinstance(negative, str):
        negative = str(negative or "")
    w, h = _dims(src)
    seed = src.get("seed")
    if seed is None:
        seed = src.get("Seed")
    chips: list[dict[str, Any]] = []
    resources = src.get("resources") or src.get("Resources") or []
    if isinstance(resources, list):
        for res in resources:
            chip = _chip_from_resource(res)
            if chip:
                chips.append(chip)
    if not chips:
        chips = _chips_from_prompt_tags(prompt)
    seen = set()
    uniq = []
    for chip in chips:
        key = (chip.get("air") or "", chip.get("name") or "")
        if key in seen:
            continue
        seen.add(key)
        uniq.append(chip)
    return {
        "backend": "civitai",
        "prompt": prompt,
        "negativePrompt": negative,
        "seed": seed,
        "width": w,
        "height": h,
        "steps": _as_int(src.get("steps") or src.get("Steps")),
        "cfgScale": _as_float_or_null(src.get("cfgScale") or src.get("CFG scale") or src.get("cfg")),
        "sampler": src.get("sampler") or src.get("Sampler") or "",
        "scheduler": src.get("scheduler") or src.get("Schedule type") or src.get("Schedule") or "",
        "checkpointName": src.get("Model") or src.get("checkpointName") or src.get("model") or "",
        "loras": uniq,
        "sourceId": src.get("id") or src.get("imageId") or src.get("postId"),
    }
