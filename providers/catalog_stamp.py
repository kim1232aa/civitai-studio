"""o57: stamp GET /api/catalog rows with official item-level match caps.

All six backends. Overlays only translate official schema; they do not invent
duration 5/12/16, Nano promptMax=1200, or raise HF loraConfidence to official.
"""
from __future__ import annotations

from typing import Any, Callable


def overlay_provider_catalog(backend: str | None, body: dict | None) -> dict:
    be = str(backend or "").strip()
    if not isinstance(body, dict):
        return {}
    if be == "civitai":
        from .capabilities import overlay_civitai_catalog
        return overlay_civitai_catalog(body)
    if be in ("modelscope-ai", "modelscope-cn", "modelscope"):
        from .capabilities import overlay_modelscope_catalog
        return overlay_modelscope_catalog(body)
    if be in ("huggingface", "hf"):
        from .hf_catalog_caps import overlay_huggingface_catalog
        return overlay_huggingface_catalog(body)
    if be == "fal":
        from .six_catalog_caps import overlay_fal_catalog
        return overlay_fal_catalog(body)
    if be in ("nano-gpt", "nanogpt", "nano"):
        from .six_catalog_caps import overlay_nano_catalog
        return overlay_nano_catalog(body)
    return dict(body)


def _wrap_catalog(provider: Any, overlay_fn: Callable[[dict | None], dict]) -> None:
    if not provider or getattr(provider, "_o57_stamped", False):
        return
    orig = provider.catalog

    def catalog(*args, **kwargs):
        body = orig(*args, **kwargs)
        return overlay_fn(body) if isinstance(body, dict) else body

    provider.catalog = catalog
    provider._o57_stamped = True


def install_catalog_stamps(providers_map: dict | None) -> None:
    """Wrap live Provider.catalog + civitai.slim_item. Idempotent. All six houses."""
    from .capabilities import (
        overlay_civitai_catalog,
        overlay_civitai_catalog_item,
        overlay_modelscope_catalog,
    )
    from .hf_catalog_caps import overlay_huggingface_catalog
    from .six_catalog_caps import overlay_fal_catalog, overlay_nano_catalog

    mapping = providers_map or {}
    _wrap_catalog(mapping.get("civitai"), overlay_civitai_catalog)
    _wrap_catalog(mapping.get("modelscope-ai"), overlay_modelscope_catalog)
    _wrap_catalog(mapping.get("modelscope-cn"), overlay_modelscope_catalog)
    _wrap_catalog(mapping.get("huggingface"), overlay_huggingface_catalog)
    _wrap_catalog(mapping.get("fal"), overlay_fal_catalog)
    _wrap_catalog(mapping.get("nano-gpt"), overlay_nano_catalog)

    from . import civitai as civitai_mod
    if not getattr(civitai_mod, "_o57_slim_stamped", False):
        orig_slim = civitai_mod.slim_item

        def slim_item(it):
            row = orig_slim(it)
            return overlay_civitai_catalog_item(row) if isinstance(row, dict) else row

        civitai_mod.slim_item = slim_item
        orig_items = civitai_mod.catalog_items

        def catalog_items():
            items, fetched, total = orig_items()
            stamped = [
                overlay_civitai_catalog_item(x) if isinstance(x, dict) else x
                for x in (items or [])
            ]
            return stamped, fetched, total

        civitai_mod.catalog_items = catalog_items
        civitai_mod._o57_slim_stamped = True

    try:
        from .civitai_lora_shape import install_civitai_lora_shape
        install_civitai_lora_shape()
    except Exception as e:
        print("[civitai] o57 lora shape skip", e, flush=True)
