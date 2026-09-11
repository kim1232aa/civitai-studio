#!/usr/bin/env python3
"""魔搭 catalog ref policy: t2i does not eat refs; Edit is 1; 2509 official 3 is recorded.

Do NOT copy Nano's maxRefs=5 onto modelscope-cn.
Do NOT guess i2i from the word edit in an unknown model id (o56 / REQUIREMENTS 3.5).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from providers.capabilities import (  # noqa: E402
    MODELSCOPE_REF_POLICY,
    get_provider_capabilities,
    modelscope_t2i_refs_error,
    overlay_modelscope_catalog,
    overlay_modelscope_catalog_item,
)
from providers.ref_images import max_refs  # noqa: E402


def check(cond, msg):
    if not cond:
        raise AssertionError(msg)


def main():
    check(get_provider_capabilities("modelscope-cn")["maxRefs"] == 3, "provider ceiling 3 (Edit-2509 official)")
    check(get_provider_capabilities("modelscope-ai")["maxRefs"] == 3, "AI ceiling 3")
    check(max_refs("modelscope-cn", get_provider_capabilities("modelscope-cn")) == 3, "max_refs default 3")

    krea = overlay_modelscope_catalog_item({"id": "krea/Krea-2-Raw", "task": "text-to-image", "tags": ["t2i"]})
    check(krea["capabilities"]["image_to_image"] is False, krea)
    check(modelscope_t2i_refs_error("krea/Krea-2-Raw", 5, krea), "Krea t2i + 5 refs must 400")
    check("文生图" in modelscope_t2i_refs_error("krea/Krea-2-Raw", 5, krea), "Chinese unused-ref copy")
    check(modelscope_t2i_refs_error("krea/Krea-2-Raw", 0, krea) is None, "no refs → no error")

    edit = overlay_modelscope_catalog_item({"id": "Qwen/Qwen-Image-Edit", "task": "image-to-image", "needsSource": True})
    check(edit["capabilities"]["image_to_image"] is True, edit)
    check(edit["capabilities"]["maxRefs"] == 1, edit)
    check(modelscope_t2i_refs_error("Qwen/Qwen-Image-Edit", 5, edit) is None, "Edit eats refs; over-cap is max_refs")
    check(max_refs("modelscope-cn", get_provider_capabilities("modelscope-cn"), item=edit) == 1, "Edit clamped to 1")

    multi = overlay_modelscope_catalog_item({"id": "Qwen/Qwen-Image-Edit-2509"})
    check(multi["capabilities"]["image_to_image"] is True, multi)
    check(multi["capabilities"]["maxRefs"] == 3, "official 2509 is 1–3 on the item")
    # Provider ceiling 3 + catalog 3 → resolve 3 (no longer clamped to 1).
    check(max_refs("modelscope-cn", get_provider_capabilities("modelscope-cn"), item=multi) == 3,
          "2509 resolves to official 3")

    hub_t2i = overlay_modelscope_catalog_item({"id": "someone/unknown-t2i", "task": "text-to-image", "tags": ["t2i"]})
    check(hub_t2i["capabilities"]["image_to_image"] is False, hub_t2i)
    hub_i2i = overlay_modelscope_catalog_item({"id": "someone/unknown-edit", "task": "image-to-image", "tags": ["i2i"]})
    check(hub_i2i["capabilities"]["image_to_image"] is True and hub_i2i["needsSource"] is True, hub_i2i)

    # o56: name containing "edit" without policy/task/tags must not invent i2i.
    guessed = overlay_modelscope_catalog_item({"id": "someone/cool-edit-model"})
    guessed_caps = guessed.get("capabilities") if isinstance(guessed.get("capabilities"), dict) else {}
    check(guessed_caps.get("image_to_image") is not True, "must not guess i2i from edit in id")
    check(guessed_caps.get("maxRefs") is None, "unknown row must not invent maxRefs=1")
    check(modelscope_t2i_refs_error("someone/cool-edit-model", 2, guessed) is None,
          "unknown edit-named mid is not a t2i hard-block")

    pins = json.loads((ROOT / "docs" / "ms-models.json").read_text())["items"]
    body = overlay_modelscope_catalog({"backend": "modelscope-cn", "items": pins})
    by_id = {x["id"]: x for x in body["items"]}
    check(by_id["krea/Krea-2-Raw"]["capabilities"]["image_to_image"] is False, "pin overlay")
    check(by_id["Qwen/Qwen-Image-Edit"]["capabilities"]["image_to_image"] is True, "edit pin overlay")
    check("Qwen/Qwen-Image-Edit-2509" in MODELSCOPE_REF_POLICY, "2509 policy recorded")

    print("PASS modelscope_catalog_refs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
