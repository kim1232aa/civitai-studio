#!/usr/bin/env python3
"""o45: Magao Edit-2509 maxRefs=3 (provider ceiling raised; catalog tightens)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from providers.capabilities import (  # noqa: E402
    get_provider_capabilities,
    overlay_modelscope_catalog_item,
)
from providers.ref_images import max_refs  # noqa: E402


def check(cond, msg):
    if not cond:
        raise AssertionError(msg)


def main():
    for pid in ("modelscope-ai", "modelscope-cn"):
        caps = get_provider_capabilities(pid)
        check(caps["maxRefs"] == 3, f"{pid} ceiling maxRefs==3")
        check(caps["maxImages"] == 3, f"{pid} ceiling maxImages==3")

    edit = overlay_modelscope_catalog_item({"id": "Qwen/Qwen-Image-Edit"})
    check(edit["capabilities"]["maxRefs"] == 1, "non-2509 Edit stays 1 on item")
    check(max_refs("modelscope-ai", get_provider_capabilities("modelscope-ai"), item=edit) == 1,
          "non-2509 Edit resolve 1")

    e2509 = overlay_modelscope_catalog_item({"id": "Qwen/Qwen-Image-Edit-2509"})
    check(e2509["capabilities"]["maxRefs"] == 3, "2509 item maxRefs 3")
    check(max_refs("modelscope-ai", get_provider_capabilities("modelscope-ai"), item=e2509) == 3,
          "2509 resolve 3 (not singular-forced to 1)")

    t2i = overlay_modelscope_catalog_item({"id": "krea/Krea-2-Raw", "task": "text-to-image"})
    check(t2i["capabilities"].get("image_to_image") is False, "t2i no i2i")

    html = (ROOT / "static" / "storyboard.html").read_text()
    js = (ROOT / "static" / "storyboard.js").read_text()
    check("v0821o49b-hydrate-fresh-empty-url" in html, "html stamp")
    check("20260911-o49bhydratefreshemptyurl" in html, "cache-bust")
    check('"modelscope-ai": { maxRefs: 3' in js or '"modelscope-ai": { maxRefs: 3,' in js, "UI PROVIDER_REF_CAPS ai=3")
    check("catalogAllowsList" in js, "resolveRefCaps list escape for 2509")

    print("PASS o45_magao_edit2509_maxrefs3")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
