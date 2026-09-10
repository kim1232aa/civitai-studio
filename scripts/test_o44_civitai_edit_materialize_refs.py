#!/usr/bin/env python3
"""o44: Civitai editImage materializes /out refs to data URLs before POST.

python3 -B scripts/test_o44_civitai_edit_materialize_refs.py
No live HTTP / curl acceptance. Closed-loop stays 0.
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from providers import civitai as civ  # noqa: E402
from providers.ref_images import materialize_local_refs  # noqa: E402

checks = 0


def check(cond, msg=""):
    global checks
    if not cond:
        raise AssertionError(msg or "check failed")
    checks += 1


def _out_urls(n: int) -> list[str]:
    return [f"/out/fill-cap-{i}.jpg" for i in range(1, n + 1)]


def test_build_workflow_editimage_materializes_out_paths():
    civ.load_catalog_disk()
    urls = _out_urls(9)
    for u in urls:
        check((ROOT / "out" / Path(u).name).is_file(), f"fixture missing {u}")
    wf = civ.build_workflow(
        {
            "serviceId": "image/sdcpp/flux1/editImage",
            "prompt": "淘宝主图 edit",
            "images": urls,
        }
    )
    inp = wf["steps"][0]["input"]
    imgs = inp.get("images") or []
    check(len(imgs) == 9, f"keep official maxRefs=9, got {len(imgs)}")
    for i, u in enumerate(imgs):
        check(isinstance(u, str) and u.startswith("data:"), f"img[{i}] not data: {u[:60]!r}")
        check("/out/" not in u[:80], f"img[{i}] still /out")
        check(len(u) > 100, f"img[{i}] too short len={len(u)}")


def test_fail_closed_missing_local():
    civ.load_catalog_disk()
    try:
        civ.build_workflow(
            {
                "serviceId": "image/sdcpp/flux1/editImage",
                "prompt": "x",
                "images": ["/out/does-not-exist-o44.jpg", "/out/fill-cap-1.jpg"],
            }
        )
        raise AssertionError("missing local must raise")
    except ValueError as e:
        check("无法读取" in str(e) or "不存在" in str(e), str(e))


def test_http_refs_untouched_and_clamp_not_invented_lower():
    civ.load_catalog_disk()
    urls = [f"https://example.invalid/r{i}.jpg" for i in range(9)]
    wf = civ.build_workflow(
        {
            "serviceId": "image/sdcpp/flux1/editImage",
            "prompt": "x",
            "images": urls,
        }
    )
    imgs = wf["steps"][0]["input"].get("images") or []
    check(len(imgs) == 9, f"do not invent lower than official 9: {len(imgs)}")
    check(imgs == urls, imgs)


def test_source_image_materialize():
    civ.load_catalog_disk()
    # Some caps use sourceImage; force via apply_frames path when frameFields has it.
    # editImage frameFields=['images'] — also cover sourceImage if present in payload
    # by building a wan-like path is heavy; unit the helper path instead.
    out = materialize_local_refs(["/out/fill-cap-1.jpg"])
    check(len(out) == 1 and out[0].startswith("data:image/"), out[0][:40])


def test_generate_audit_nrefs_data_lengths_only():
    civ.load_catalog_disk()
    urls = _out_urls(3)
    captured = {}

    def fake_submit(body, whatif=False):
        inp = body["steps"][0]["input"]
        captured["inp"] = inp
        return 200, {"id": "wf-test", "status": "pending"}

    prov = civ.CivitaiProvider()
    with patch.object(civ, "submit", side_effect=fake_submit):
        code, data = prov.generate(
            {
                "serviceId": "image/sdcpp/flux1/editImage",
                "prompt": "audit",
                "images": urls,
            }
        )
    check(code == 200, code)
    check(data.get("nRefs") == 3, data.get("nRefs"))
    check(int(data.get("nDataUrls") or 0) == 3, data.get("nDataUrls"))
    check(int(data.get("nOutPaths") or 0) == 0, data.get("nOutPaths"))
    lenses = data.get("imageUrlLens")
    check(isinstance(lenses, list) and len(lenses) == 3, lenses)
    check(all(isinstance(n, int) and n > 100 for n in lenses), lenses)
    # submitted images must be data URLs (not /out)
    sub = (data.get("submittedInput") or {}).get("images") or []
    check(len(sub) == 3 and all(str(u).startswith("data:") for u in sub), [str(u)[:40] for u in sub])
    check(all(str(u).startswith("data:") for u in (captured.get("inp") or {}).get("images") or []))


def test_stamp_and_cache_bust():
    html = (ROOT / "static" / "storyboard.html").read_text(encoding="utf-8")
    js = (ROOT / "static" / "storyboard.js").read_text(encoding="utf-8")
    check("v0821o49b-hydrate-fresh-empty-url" in html, "html stamp")
    check("20260911-o49bhydratefreshemptyurl" in html, "cache-bust")
    check("v0821o44" in js, "js header o44")


def main() -> int:
    test_build_workflow_editimage_materializes_out_paths()
    test_fail_closed_missing_local()
    test_http_refs_untouched_and_clamp_not_invented_lower()
    test_source_image_materialize()
    test_generate_audit_nrefs_data_lengths_only()
    test_stamp_and_cache_bust()
    print(f"ok {checks} checks · o44-civitai-edit-materialize-refs offline")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
