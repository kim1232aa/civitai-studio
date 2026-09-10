"""Shared outbound reference-image collection + cap enforce.

Studio / storyboard inbound (any of these — union, not only images):
  - firstFrame / sourceImage / startImage / image_url / imageUrl / …
  - images[] / referenceImages[]
  - image_urls[]   (Fal canvas pack)
  - input_references[]  (Nano canvas pack)

Providers map to official outbound fields (Fal image_urls, Nano
input_references, Civitai images, ModelScope image_url).

maxRefs comes from one place: providers/capabilities.py (provider ceiling)
plus the catalog/capability row (may only tighten). A model row with no
declared cap is unknown — callers must fail, never silent-slice to the
generic provider ceiling.
"""
from __future__ import annotations

from typing import Any

# Fallback field names only. Numeric ceilings live in capabilities.PROVIDER_CAPS.
REF_IMAGES_FIELD: dict[str, str] = {
    "civitai": "images",
    "fal": "image_urls",
    "nano-gpt": "input_references",
    "modelscope-ai": "image_url",
    "modelscope-cn": "image_url",
    "huggingface": "image_urls",
}

_MULTI_REF_FIELDS = ("image_urls", "images", "input_references", "referenceImages")
_SINGULAR_FIRST_FIELDS = ("image_url", "start_image_url", "first_frame_url", "image")
_CIVITAI_MULTI_FRAMES = ("images", "referenceImages")
_CIVITAI_SINGULAR_FRAMES = (
    "firstFrame", "sourceImage", "startImage", "lastFrame", "endImage",
    "sourceImageUrl", "firstFrameImage", "lastFrameImage", "endSourceImage",
    "image",
)


def _positive_int(raw: Any, default: int | None = None) -> int | None:
    try:
        n = int(raw)
    except (TypeError, ValueError):
        return default
    if n <= 0 or n >= 99:
        return default
    return n


def _provider_ceiling(backend: str | None, caps: dict | None = None, default: int | None = None) -> int:
    if default is not None:
        n = _positive_int(default)
        if n is not None:
            return n
    if isinstance(caps, dict):
        for key in ("maxRefs", "maxImages", "maxRefImages"):
            n = _positive_int(caps.get(key))
            if n is not None:
                return n
    try:
        from .capabilities import get_provider_capabilities
        row = get_provider_capabilities((backend or "").strip())
        for key in ("maxRefs", "maxImages"):
            n = _positive_int(row.get(key))
            if n is not None:
                return n
    except Exception:
        pass
    return 9


def _constraint_max_items(src: dict) -> int | None:
    """Civitai capabilities.json: constraints[field].maxItems on frameFields."""
    best: int | None = None

    def consider(rule: Any) -> None:
        nonlocal best
        if not isinstance(rule, dict):
            return
        if rule.get("type") not in (None, "array"):
            return
        n = _positive_int(rule.get("maxItems") if rule.get("maxItems") is not None else rule.get("maxLength"))
        if n is None:
            return
        best = n if best is None else max(best, n)

    cons = src.get("constraints") if isinstance(src.get("constraints"), dict) else {}
    fields = src.get("frameFields") if isinstance(src.get("frameFields"), list) else []
    for name in list(fields) + ["images", "image_urls", "input_references", "referenceImages"]:
        consider(cons.get(name))
    for rule in cons.values():
        consider(rule)
    extra = src.get("extraFlags") if isinstance(src.get("extraFlags"), dict) else {}
    consider(extra.get("images") or extra.get("referenceImages"))
    return best


def _explicit_max_from_dict(src: dict | None) -> int | None:
    if not isinstance(src, dict):
        return None
    nested = src.get("capabilities") if isinstance(src.get("capabilities"), dict) else {}
    sp = src.get("supported_parameters") if isinstance(src.get("supported_parameters"), dict) else {}
    for bag in (src, nested, sp):
        if not isinstance(bag, dict):
            continue
        for key in ("maxRefs", "maxImages", "maxRefImages", "referenceLimit", "max_input_images", "max_images"):
            n = _positive_int(bag.get(key))
            if n is not None:
                return n
    n = _constraint_max_items(src)
    if n is not None:
        return n
    cap = src.get("capability") if isinstance(src.get("capability"), dict) else None
    if cap:
        n = _positive_int(cap.get("referenceLimit"))
        if n is not None:
            return n
        n = _constraint_max_items(cap)
        if n is not None:
            return n
    return None


def _looks_video_row(item: dict | None) -> bool:
    if not isinstance(item, dict):
        return False
    blob = " ".join(
        str(item.get(k) or "")
        for k in ("id", "name", "category", "kind", "falCategory", "task", "operation")
    ).lower()
    return "video" in blob or "image-to-video" in blob or "/i2v" in blob


def _image_fields(item: dict | None) -> list[str]:
    if not isinstance(item, dict):
        return []
    caps = item.get("capabilities") if isinstance(item.get("capabilities"), dict) else {}
    raw = caps.get("imageFields") or item.get("imageFields") or []
    if isinstance(raw, list):
        return [str(x) for x in raw if x]
    return []


def _infer_max_from_image_fields(item: dict | None) -> int | None:
    fields = _image_fields(item)
    if fields:
        has_multi = any(f in _MULTI_REF_FIELDS for f in fields)
        has_singular = any(f in _SINGULAR_FIRST_FIELDS for f in fields)
        if not has_multi and (has_singular or fields):
            return 1
    if not isinstance(item, dict):
        return None
    frames = item.get("frameFields") if isinstance(item.get("frameFields"), list) else []
    cap = item.get("capability") if isinstance(item.get("capability"), dict) else {}
    if not frames and isinstance(cap, dict) and isinstance(cap.get("frameFields"), list):
        frames = cap.get("frameFields") or []
    names = [str(x) for x in frames]
    if not names:
        return None
    if any(n in _CIVITAI_MULTI_FRAMES for n in names):
        return None
    if any(n in _CIVITAI_SINGULAR_FRAMES for n in names):
        return 1
    return None


def declared_max_refs(item: dict | None = None, payload: dict | None = None) -> int | None:
    """Model/catalog declared cap only. None = this row did not declare a cap."""
    n = _explicit_max_from_dict(item)
    if n is None:
        n = _infer_max_from_image_fields(item)
    if n is None:
        n = _explicit_max_from_dict(payload)
    return n


def max_refs(
    backend: str | None = None,
    caps: dict | None = None,
    item: dict | None = None,
    payload: dict | None = None,
    default: int | None = None,
) -> int | None:
    """Resolve max reference images from provider + catalog.

    Returns None when the model row exists but declares no cap (unknown).
    Catalog may only tighten the provider ceiling. Never raise a weaker limit.
    """
    ceil = _provider_ceiling(backend, caps, default)
    declared = declared_max_refs(item, payload)
    if declared is not None:
        return min(declared, ceil)
    fields = _image_fields(item)
    frames = []
    if isinstance(item, dict):
        frames = item.get("frameFields") if isinstance(item.get("frameFields"), list) else []
        cap = item.get("capability") if isinstance(item.get("capability"), dict) else {}
        if not frames and isinstance(cap.get("frameFields"), list):
            frames = cap.get("frameFields") or []
    if any(f in _MULTI_REF_FIELDS for f in fields) or any(str(n) in _CIVITAI_MULTI_FRAMES for n in frames):
        # Schema says multi-ref but no number — provider ceiling, not unknown.
        return ceil
    if isinstance(item, dict) and item and _looks_video_row(item) and not fields and not frames:
        # Video/i2v row with no schema at all — do not silent-slice to the image ceiling.
        return None
    return ceil

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


def enforce_ref_cap(
    images: list[str] | None,
    *,
    backend: str | None = None,
    caps: dict | None = None,
    item: dict | None = None,
    payload: dict | None = None,
    default: int | None = None,
) -> list[str]:
    """Return all refs, or raise. Never silent-slice."""
    imgs = [x for x in (images or []) if x]
    if not imgs:
        return imgs
    n = max_refs(backend=backend, caps=caps, item=item, payload=payload, default=default)
    if n is None:
        raise ValueError("当前模型参考图上限未知，拒绝按通用上限截断")
    if len(imgs) > n:
        raise ValueError(f"参考图 {len(imgs)}/{n} · 超过上限，拒绝截断")
    return imgs


def clamp_ref_images(
    images: list[str] | None,
    *,
    backend: str | None = None,
    caps: dict | None = None,
    item: dict | None = None,
    payload: dict | None = None,
    default: int | None = None,
) -> list[str]:
    # Name kept for callers. Behavior is fail-closed, not slice.
    return enforce_ref_cap(
        images, backend=backend, caps=caps, item=item, payload=payload, default=default
    )


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
    enforce: bool = True,
) -> list[str]:
    raw = collect_ref_images(payload, include_primary=include_primary)
    if not enforce:
        return raw
    return enforce_ref_cap(
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
