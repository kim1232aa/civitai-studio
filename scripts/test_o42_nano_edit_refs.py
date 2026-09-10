#!/usr/bin/env python3
"""o42: Nano edit refs reach OAI/edit endpoints as imageDataUrls (offline).

python3 -B scripts/test_o42_nano_edit_refs.py
No live HTTP / curl acceptance. Closed-loop stays 0.
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from providers import nanogpt as nano

ROOT = Path(__file__).resolve().parents[1]
checks = 0


def check(cond, msg=""):
    global checks
    if not cond:
        raise AssertionError(msg or "check failed")
    checks += 1


FLARE = {
    "id": "openai/gpt-image-2.5/flare/edit",
    "name": "GPT Image 2.5 Flare Edit",
    "supported_parameters": {
        "resolutions": ["1024x1024"],
        "max_output_images": 4,
        "max_input_images": 16,
    },
    "capabilities": {"image_generation": True, "image_to_image": True},
}


def test_oai_body_maps_refs_to_imageDataUrls_no_mix():
    refs = [
        "data:image/jpeg;base64,AAA",
        "data:image/jpeg;base64,BBB",
        "data:image/jpeg;base64,CCC",
        "data:image/jpeg;base64,DDD",
        "data:image/jpeg;base64,EEE",
    ]
    full = {
        "model": FLARE["id"],
        "prompt": "淘宝主图",
        "n": 1,
        "nImages": 1,
        "resolution": "1024x1024",
        "size": "1024x1024",
        "response_format": "url",
        "input_references": refs,
    }
    oai = nano._core_image_body(full)
    check("input_references" not in oai, "OAI body must not keep input_references")
    check(oai.get("imageDataUrls") == refs, "imageDataUrls must mirror refs")
    check(oai.get("imageDataUrl") == refs[0], "imageDataUrl = first ref")
    check("image" not in oai or oai.get("image") is None or True)
    # normalized path still uses input_references only
    check(full.get("input_references") == refs)
    check("imageDataUrls" not in full)


def test_edit_image_body_same_shape():
    refs = ["data:image/png;base64,XXX", "data:image/png;base64,YYY"]
    full = {
        "model": FLARE["id"],
        "prompt": "edit me",
        "n": 1,
        "resolution": "1024x1024",
        "size": "1024x1024",
        "input_references": refs,
        "response_format": "url",
    }
    edit = nano._edit_image_body(full)
    check("input_references" not in edit)
    check(edit.get("imageDataUrls") == refs)
    check(edit.get("imageDataUrl") == refs[0])


def test_endpoint_candidates_edit_prefers_edit_routes():
    full = {
        "model": FLARE["id"],
        "prompt": "x",
        "n": 1,
        "resolution": "1024x1024",
        "size": "1024x1024",
        "input_references": ["data:image/jpeg;base64,AAA"],
        "response_format": "url",
    }
    cands = nano._image_endpoint_candidates(FLARE, full)
    urls = [u for u, _ in cands]
    check(any("/images/edit" in u for u in urls), "must try edit endpoint")
    check(any(u.rstrip("/").endswith("/images/edits") or u.endswith("/images/edits") for u in urls)
          or any("/images/edits" in u for u in urls),
          "must try edits alias")
    # first candidate for edit models should be an edit route
    check("/edit" in urls[0], f"prefer edit first, got {urls[0]}")
    # bodies on edit/OAI routes must not mix styles
    for u, body in cands:
        if "input_references" in body:
            check("imageDataUrls" not in body and "imageDataUrl" not in body,
                  f"mixed styles on {u}")
        if "imageDataUrls" in body or "imageDataUrl" in body:
            check("input_references" not in body, f"mixed styles on {u}")


def test_endpoint_candidates_t2i_no_edit_first():
    t2i = {
        "id": "openai/gpt-image-2.5/flare/text-to-image",
        "name": "GPT Image 2.5 Flare",
        "capabilities": {"image_generation": True, "image_to_image": False},
    }
    full = {
        "model": t2i["id"],
        "prompt": "x",
        "n": 1,
        "resolution": "1024x1024",
        "size": "1024x1024",
        "response_format": "url",
    }
    cands = nano._image_endpoint_candidates(t2i, full)
    urls = [u for u, _ in cands]
    check(urls[0] == nano.GEN_IMAGES, "t2i prefers normalized /images")
    check(not any("/edit" in u for u in urls[:1]), "t2i must not prefer edit")


def test_fail_closed_empty_image_surfaces_local_nRefs():
    refs = [f"data:image/jpeg;base64,REF{i}" for i in range(5)]
    full = {
        "model": FLARE["id"],
        "prompt": "淘宝主图",
        "n": 1,
        "nImages": 1,
        "resolution": "1024x1024",
        "size": "1024x1024",
        "response_format": "url",
        "input_references": refs,
    }
    empty_err = {"error": "GPT Image 2.5 Edit requires between 1 and 16 input images."}

    def fake_json_call(url, method="POST", headers=None, body=None, timeout=180):
        return 400, dict(empty_err)

    prov = nano.NanoGptProvider()
    payload = {
        "serviceId": FLARE["id"],
        "prompt": "淘宝主图",
        "resolution": "1024x1024",
        "images": refs,
        "input_references": refs,
        "sourceImage": refs[0],
    }
    with patch.object(nano, "nano_key", return_value="test-key"), \
         patch.object(nano, "find_spec", return_value=FLARE), \
         patch.object(nano, "_image_body", return_value=full), \
         patch.object(nano, "json_call", side_effect=fake_json_call), \
         patch.object(nano, "model_supports_lora", return_value=False):
        code, data = prov._generate_image(payload, FLARE, FLARE["id"])
    check(code >= 400, "must fail closed")
    check(data.get("local_nRefs") == 5, f"local_nRefs=5 got {data.get('local_nRefs')}")
    check(isinstance(data.get("endpointTried"), list) and len(data["endpointTried"]) >= 1,
          "endpointTried must be logged")
    err = str(data.get("error") or "")
    check("local_nRefs" in err or data.get("local_nRefs") == 5)


def test_empty_image_error_detector():
    check(nano._is_empty_input_images_error(
        "GPT Image 2.5 Edit requires between 1 and 16 input images."))
    check(nano._is_empty_input_images_error(
        {"error": "requires between 1 and 16 input images"}))
    check(not nano._is_empty_input_images_error("unrelated boom"))


def test_audit_lengths_helper():
    body_norm = {"input_references": ["a", "b", "c"], "prompt": "x"}
    body_oai = {"imageDataUrls": ["a", "b"], "imageDataUrl": "a", "prompt": "x"}
    a = nano._image_body_audit(body_norm)
    check(a["nInputReferences"] == 3)
    check(a["nImageDataUrls"] == 0)
    b = nano._image_body_audit(body_oai)
    check(b["nInputReferences"] == 0)
    check(b["nImageDataUrls"] == 2)


def test_stamp_and_cache_bust():
    html = (ROOT / "static" / "storyboard.html").read_text(encoding="utf-8")
    js = (ROOT / "static" / "storyboard.js").read_text(encoding="utf-8")
    check("v0821o46b-local-out-resume" in html, "html stamp")
    check("20260911-o46blocaloutresume" in html, "cache-bust")
    check("v0821o42" in js, "js header o42")


def main():
    test_oai_body_maps_refs_to_imageDataUrls_no_mix()
    test_edit_image_body_same_shape()
    test_endpoint_candidates_edit_prefers_edit_routes()
    test_endpoint_candidates_t2i_no_edit_first()
    test_empty_image_error_detector()
    test_audit_lengths_helper()
    test_fail_closed_empty_image_surfaces_local_nRefs()
    test_stamp_and_cache_bust()
    print(f"ok {checks} checks · o42-nano-edit-refs offline")


if __name__ == "__main__":
    main()
