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
    "modelscope-ai": 3,
    "modelscope-cn": 3,
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
    item_caps = None
    if isinstance(item, dict) and isinstance(item.get("capabilities"), dict):
        item_caps = item["capabilities"]
    for src in (item_caps, item, payload, caps):
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
    # Fal (and friends): single image_url schema cannot take N refs —
    # unless catalog already advertises maxRefs>1 (Magao Edit-2509: image_url list 1–3).
    if isinstance(item, dict):
        fields = (
            item.get("imageFields")
            or (item_caps.get("imageFields") if isinstance(item_caps, dict) else None)
            or []
        )
        item_cap = None
        for key in ("maxRefs", "maxImages", "maxRefImages"):
            for src in (item_caps, item):
                n = _positive_int(src.get(key)) if isinstance(src, dict) else None
                if n is not None:
                    item_cap = n
                    break
            if item_cap is not None:
                break
        if fields and "image_urls" not in fields and "input_references" not in fields and "images" not in fields:
            if item_cap is None or item_cap <= 1:
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
            # Studio uploads land as /out/<file>. Fal/HF/魔搭 materialize them later;
            # dropping here made Nano POST 0 images while the canvas still showed refs.
            if not s.startswith("data:") and not s.startswith("/out/"):
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


def materialize_local_ref(url: str) -> str:
    """Keep http(s)/data URLs; turn studio `/out/<file>` into a data URL.

    Remote providers cannot fetch 127.0.0.1. Missing local files raise — never drop.
    """
    if not isinstance(url, str):
        raise ValueError("参考图必须是文本 URL")
    s = url.strip()
    if not s:
        raise ValueError("参考图 URL 为空")
    if s.startswith(("http://", "https://", "data:")):
        return s
    if s.startswith("/out/"):
        from .fal import local_out_to_data_url
        data = local_out_to_data_url(s)
        if not data:
            raise ValueError(f"无法读取本地参考图 {s}（文件不存在或不可读）")
        return data
    raise ValueError("参考图必须是 HTTP(S)、data URL 或已上传的 /out 文件")


def materialize_local_refs(urls: list[str] | None) -> list[str]:
    return [materialize_local_ref(u) for u in (urls or [])]


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
