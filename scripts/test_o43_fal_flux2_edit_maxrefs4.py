"""o43: fal-ai/flux-2/edit maxRefs=4 from official OpenAPI (not provider 9).

Fal OpenAPI for flux-2/edit (and siblings whose schema/desc says max 4):
  image_urls — A maximum of 4 images are allowed
Runtime 422 when N>4 (job 01a08be3…). Catalog must tighten to 4; UI/gate read model cap.
Do not invent lower than official; leave */edit rows without openapi ≤N alone (e.g. flux-2-pro/edit).
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from providers.fal import (  # noqa: E402
    FAL_OPENAPI_MAX_REFS,
    build_fal_input,
    overlay_image_fields,
)
from providers.ref_images import max_refs  # noqa: E402
from providers.capabilities import get_provider_capabilities  # noqa: E402


def check(cond, msg=""):
    if not cond:
        raise AssertionError(msg or "check failed")


def main() -> int:
    caps = get_provider_capabilities("fal")
    check(int(caps.get("maxRefs") or 0) == 9, "provider ceiling stays 9")

    edit = overlay_image_fields({"id": "fal-ai/flux-2/edit", "imageFields": ["image_urls"]})
    check(edit["maxRefs"] == 4, edit)
    check(edit["capabilities"]["maxRefs"] == 4, edit["capabilities"])
    check(edit.get("maxImages") == 4, edit)
    check(max_refs("fal", caps, item=edit) == 4, "max_refs on overlay item")

    for eid in (
        "fal-ai/flux-2/flash/edit",
        "fal-ai/flux-2/turbo/edit",
        "fal-ai/flux-2/lora/edit",
        "fal-ai/flux-2/klein/4b/edit",
        "fal-ai/flux-2/klein/4b/edit/lora",
        "fal-ai/flux-2/klein/4b/base/edit",
        "fal-ai/flux-2/klein/9b/edit",
        "fal-ai/flux-2/klein/9b/edit/lora",
        "fal-ai/flux-2/klein/9b/base/edit",
    ):
        ov = overlay_image_fields({"id": eid, "imageFields": ["image_urls"]})
        check(ov["maxRefs"] == 4, f"{eid} -> {ov.get('maxRefs')}")

    for eid in (
        "fal-ai/flux-2-pro/edit",
        "fal-ai/flux-2-max/edit",
        "fal-ai/flux-2-flex/edit",
        "fal-ai/nano-banana/edit",
    ):
        ov = overlay_image_fields({"id": eid, "imageFields": ["image_urls"]})
        check(ov["maxRefs"] == 9, f"{eid} must stay 9 (no invent lower): {ov.get('maxRefs')}")

    urls = [f"https://ex/{i}.png" for i in range(9)]
    # lead 裁决(对齐 fail-closed 现行语义): 4 帽端点塞 9 张必须诚实拒绝, 不静默截断到 4
    raised = False
    try:
        build_fal_input(
            {
                "serviceId": "fal-ai/flux-2/edit",
                "prompt": "edit",
                "image_urls": urls,
            }
        )
    except ValueError as exc:
        raised = "超过上限" in str(exc) or "拒绝截断" in str(exc)
    check(raised, "flux-2/edit 9 refs must fail-closed, not slice to 4")
    # 4 张以内正常通过
    fin = build_fal_input(
        {
            "serviceId": "fal-ai/flux-2/edit",
            "prompt": "edit",
            "image_urls": urls[:4],
        }
    )
    check(len(fin.get("image_urls") or []) == 4, fin)

    fin_pro = build_fal_input(
        {
            "serviceId": "fal-ai/flux-2-pro/edit",
            "prompt": "edit",
            "image_urls": urls,
        }
    )
    check(len(fin_pro.get("image_urls") or []) == 9, fin_pro)

    for eid, n in FAL_OPENAPI_MAX_REFS.items():
        check(1 <= int(n) <= 9, f"policy bad {eid}={n}")
        check(int(n) <= 4, f"o43 policy must be ≤4 tighten-only: {eid}={n}")

    print("PASS o43 fal flux-2/edit maxRefs=4")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
