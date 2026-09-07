"""Shared outbound reference-image collection + clamp.

Studio / storyboard inbound (any of these — union, not only images):
  - firstFrame / sourceImage / startImage / image_url / imageUrl / …
  - images[] / referenceImages[]
  - image_urls[]   (Fal canvas pack)
  - input_references[]  (Nano canvas pack)

Providers map to official outbound fields (Fal image_urls, Nano
input_references, Civitai images, ModelScope image_url).

maxRefs / maxImages come from provider capabilities or catalog item;
never invent higher than the provider default below.
"""
from __future__ import annotations

from typing import Any

# Provider defaults = existing hard clamps / documented ceilings (not higher).
# Catalog / caps.maxRefs may only narrow (callers use min()).
PROVIDER_MAX_REFS: dict[str, int] = {
    # Keep in sync with providers/capabilities.py PROVIDER_CAPS[].maxRefs
    "civitai": 9,
    "fal": 9,
    "nano-gpt": 5,
    "modelscope-ai": 1,
    "modelscope-cn": 1,
    "huggingface": 9,
}

REF_IMAGES_FIELD: dict[str, str] = {
    "civitai": "images",
    "fal": "image_urls",
    "nano-gpt": "input_references",
    "modelscope-ai": "image_url",
    "modelscope-cn": "image_url",
    "huggingface": "image_urls",
}


def _positive_int(raw: Any, default: int | None = None) -> int | None:
    try:
        n = int(raw)
    except (TypeError, ValueError):
        return default
    if n <= 0 or n >= 99:
        return default
    return n


def max_refs(
    backend: str | None = None,
    caps: dict | None = None,
    item: dict | None = None,
    payload: dict | None = None,
    default: int | None = None,
) -> int:
    """Resolve max reference images: item → payload → caps → provider default.

    Prefer smaller (stricter) when several sources disagree.
    """
    candidates: list[int] = []
    for src in (item, payload, caps):
        if not isinstance(src, dict):
            continue
        for key in ("maxRefs", "maxImages", "maxRefImages"):
            n = _positive_int(src.get(key))
            if n is not None:
                candidates.append(n)
                break
    prov_default = PROVIDER_MAX_REFS.get((backend or "").strip(), 9)
    if default is not None:
        prov_default = int(default)
    # Fal (and friends): single image_url schema cannot take N refs
    if isinstance(item, dict):
        fields = item.get("imageFields") or []
        if fields and "image_urls" not in fields and "input_references" not in fields:
            # only singular official slots → ceiling 1
            prov_default = min(prov_default, 1)
            candidates = [min(c, 1) for c in candidates] or [1]
    if not candidates:
        return prov_default
    return min(min(candidates), prov_default)


def ref_images_field(backend: str | None = None, caps: dict | None = None) -> str:
    if isinstance(caps, dict):
        for key in ("refImagesField", "refField"):
            v = caps.get(key)
            if isinstance(v, str) and v.strip():
                return v.strip()
    return REF_IMAGES_FIELD.get((backend or "").strip(), "images")


def collect_ref_images(payload: dict | None, *, include_primary: bool = True) -> list[str]:
    """Deduped list of http/data image URLs from Studio payload."""
    payload = payload or {}
    seen: set[str] = set()
    out: list[str] = []

    def add(u: Any):
        if not isinstance(u, str):
            return
        s = u.strip()
        if not s or s in seen:
            return
        if not (s.startswith("http") or s.startswith("data:image") or s.startswith("data:application")):
            # allow plain data: for some providers; still skip stage-out dicts
            if not s.startswith("data:"):
                return
        seen.add(s)
        out.append(s)

    if include_primary:
        for key in (
            "firstFrame",
            "sourceImage",
            "startImage",
            "image_url",
            "imageUrl",
            "imageDataUrl",
            "image",
        ):
            add(payload.get(key))

    for key in ("images", "referenceImages", "input_references", "image_urls"):
        bag = payload.get(key)
        if isinstance(bag, str):
            add(bag)
        elif isinstance(bag, list):
            for u in bag:
                add(u)

    return out


def clamp_ref_images(
    images: list[str] | None,
    *,
    backend: str | None = None,
    caps: dict | None = None,
    item: dict | None = None,
    payload: dict | None = None,
    default: int | None = None,
) -> list[str]:
    imgs = [x for x in (images or []) if x]
    n = max_refs(backend=backend, caps=caps, item=item, payload=payload, default=default)
    return imgs[:n]


def normalize_payload_refs(payload: dict | None) -> dict:
    """Mirror canvas field names onto payload.images for legacy readers.

    Storyboard packs refs onto capabilities.refImagesField (often
    image_urls / input_references). Call this at /api/generate so any
    leftover images-only path still sees the full list. Idempotent.
    """
    if not isinstance(payload, dict):
        return {}
    refs = collect_ref_images(payload, include_primary=True)
    if not refs:
        return payload
    existing = payload.get("images")
    if not isinstance(existing, list) or len(existing) < len(refs):
        payload["images"] = list(refs)
    # Keep canvas fields intact; do not delete image_urls / input_references.
    return payload


def payload_ref_images(
    payload: dict | None,
    *,
    backend: str | None = None,
    caps: dict | None = None,
    item: dict | None = None,
    include_primary: bool = True,
    default: int | None = None,
) -> list[str]:
    raw = collect_ref_images(payload, include_primary=include_primary)
    return clamp_ref_images(
        raw,
        backend=backend,
        caps=caps,
        item=item,
        payload=payload,
        default=default,
    )


def primary_frame(payload: dict | None) -> str:
    """First-frame / source image for i2v (string URL or data URL)."""
    payload = payload or {}
    for key in ("firstFrame", "sourceImage", "startImage", "image_url", "imageUrl", "imageDataUrl", "image"):
        v = payload.get(key)
        if isinstance(v, str) and v.strip():
            return v.strip()
    imgs = collect_ref_images(payload, include_primary=False)
    return imgs[0] if imgs else ""
