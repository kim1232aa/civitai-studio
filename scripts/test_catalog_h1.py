#!/usr/bin/env python3
"""H1/H2/H3/H8 catalog + providers contract. Disk only for civitai/fal/hf."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from providers.catalog_ops import (  # noqa: E402
    canonical_category,
    category_matches,
    enrich_catalog_item,
)
from providers.civitai import CivitaiProvider  # noqa: E402
from providers.fal import FalProvider  # noqa: E402
from providers.huggingface import HuggingFaceProvider  # noqa: E402
from providers.capabilities import REQUIRED_KEYS, get_provider_capabilities  # noqa: E402

fails = []


def check(name, cond, detail=""):
    if cond:
        print(f"  ok   {name}")
    else:
        fails.append(name)
        print(f"  FAIL {name} {detail}")


REQUIRED_ITEM = (
    "id",
    "operation",
    "supportedOperations",
    "needsSource",
    "resolutions",
    "maxResolution",
    "whRange",
    "aspectRatios",
    "referenceLimit",
    "resolutionMode",
)


def _has_fields(item):
    return all(k in item for k in REQUIRED_ITEM)


print("civitai")
civ = CivitaiProvider()
body = civ.catalog("", "image", "")
items = body.get("items") or []
check("image n>0", len(items) > 0, str(len(items)))
check("每条有 H1 字段", all(_has_fields(x) for x in items), str(items[0].keys() if items else None))
check("每条有 operation", all(x.get("operation") for x in items), str([x.get("id") for x in items if not x.get("operation")][:5]))
convert = next((x for x in items if x.get("id") == "image/convertImage"), None)
check("convertImage=transcode", convert and convert.get("operation") == "transcode", str(convert))
krea = next((x for x in items if x.get("id") == "image/comfy/krea2/turbo/createImage"), None)
check("krea2 turbo=t2i", krea and krea.get("operation") == "t2i" and krea.get("needsSource") is False, str(krea))
deprecated = next((x for x in items if x.get("id") == "image/textToImage"), None)
check("textToImage=deprecated", not deprecated or deprecated.get("operation") == "deprecated", str(deprecated))
edit = next((x for x in items if x.get("nativeOperation") == "editImage"), None)
check("editImage=i2i needsSource", edit and edit.get("operation") == "i2i" and edit.get("needsSource") is True, str(edit))

vid = civ.catalog("", "video", "")
vitems = vid.get("items") or []
trans = next((x for x in vitems if x.get("id") == "video/transcode"), None)
check("video/transcode=transcode", trans and trans.get("operation") == "transcode", str(trans))
check("video 每条有 operation", all(x.get("operation") for x in vitems), str(len(vitems)))

print("fal")
fal = FalProvider()
fbody = fal.catalog("", "image", "")
fitems = fbody.get("items") or []
check("fal/image n=671", len(fitems) == 671, str(len(fitems)))
check("fal 报分类实数", isinstance(fbody.get("categories"), dict) and (fbody.get("categories") or {}).get("image") == 671, str(fbody.get("categories")))
check("fal 报分页实数", (fbody.get("pagination") or {}).get("hasMore") is False and (fbody.get("pagination") or {}).get("sourceTotal") == fbody.get("unfilteredTotal"), str(fbody.get("pagination")))
check("fal/image 每条有 operation", all(x.get("operation") for x in fitems), str([x.get("id") for x in fitems if not x.get("operation")][:5]))
first = fitems[0] if fitems else {}
check(
    "fal/image 第一项 nano-banana-2/edit 是 i2i+needsSource",
    first.get("id") == "fal-ai/nano-banana-2/edit"
    and first.get("operation") == "i2i"
    and first.get("needsSource") is True,
    str((first.get("id"), first.get("operation"), first.get("needsSource"))),
)
edit_row = next((x for x in fitems if x.get("id") == "fal-ai/nano-banana-2/edit"), None)
check("edit 项 i2i", edit_row and edit_row.get("operation") == "i2i" and edit_row.get("needsSource"), str(edit_row))
schnell = next((x for x in fitems if x.get("id") == "fal-ai/flux/schnell"), None)
check("schnell t2i", schnell and schnell.get("operation") == "t2i" and not schnell.get("needsSource"), str(schnell))

cam_a = fal.catalog("", "camera-angle", "")
cam_b = fal.catalog("", "cameraAngle", "")
check("camera-angle n=4", cam_a.get("count") == 4, str(cam_a.get("count")))
check("cameraAngle 别名同 4 条", cam_b.get("count") == 4, str(cam_b.get("count")))
check("camera-angle operation", all(x.get("operation") == "camera-angle" for x in (cam_a.get("items") or [])), str(cam_a.get("items")))

print("huggingface")
from providers import huggingface as hf_mod

# H1 is the field contract. Live Hub roster is scripts/test_w3_roster.py — do not
# hang this disk-only test on huggingface.co.
_orig_roster = hf_mod.fetch_hf_roster
hf_mod.fetch_hf_roster = lambda q="", category="": (list(hf_mod.load_items()), {"source": "hub", "pageSize": 100, "pagesFetched": 0, "hasMore": False, "hubCount": 0, "pipes": {}})
try:
    hf = HuggingFaceProvider()
    hbody = hf.catalog("", "image", "")
    hitems = hbody.get("items") or []
    check("hf image n>0", len(hitems) > 0, str(len(hitems)))
    check("hf 图全 t2i", all(x.get("operation") == "t2i" for x in hitems), str([(x.get("id"), x.get("operation")) for x in hitems]))
    check("hf i2i=none 不进 supportedOperations", all("i2i" not in (x.get("supportedOperations") or []) for x in hitems), str(hitems[0].get("supportedOperations") if hitems else None))
    check("hf catalog 带 categories/pagination", isinstance(hbody.get("categories"), dict) and isinstance(hbody.get("pagination"), dict), str(hbody.keys()))
finally:
    hf_mod.fetch_hf_roster = _orig_roster

print("H8")
caps = get_provider_capabilities("civitai")
check("PROVIDER_CAPS 有必填键", all(k in caps for k in REQUIRED_KEYS), str(sorted(caps)))
from providers import list_public
from providers import nanogpt as nano_mod
from providers import modelscope as ms_mod

nano_mod.fetch_catalog = lambda force=False: [{"id": "x", "category": "image"}]
nano_mod.fetch_text_catalog = lambda force=False: [{"id": "y", "category": "text"}]
ms_mod.fetch_hub = lambda search="": ([], {})

try:
    pubs = list_public()
except Exception as e:
    pubs = []
    check("list_public 可调用", False, str(e))
else:
    check("list_public 非空", len(pubs) >= 4, str([x.get("id") for x in pubs]))
    check("每家带 capabilities", all(isinstance(x.get("capabilities"), dict) and "lora" in x["capabilities"] for x in pubs), str(pubs[0].keys() if pubs else None))

print("aliases")
check("canonical cameraAngle", canonical_category("cameraAngle") == "camera-angle")
check("match cameraAngle vs camera-angle", category_matches("camera-angle", "cameraAngle"))

print("synthetic")
ms_edit = enrich_catalog_item(
    {"id": "MusePublic/Qwen-Image-Edit", "name": "Qwen Image Edit", "category": "image", "needsSource": True, "task": "image-to-image"},
    "modelscope-ai",
)
check("魔搭 edit=i2i", ms_edit.get("operation") == "i2i" and ms_edit.get("needsSource") is True, str(ms_edit))
nano_i2i = enrich_catalog_item(
    {
        "id": "edit-only",
        "category": "image",
        "task": "image-to-image",
        "capabilities": {"image_to_image": True, "image_generation": False},
        "supported_parameters": {"resolutions": ["square_hd"]},
    },
    "nano-gpt",
)
check("nano i2i token 原样", nano_i2i.get("operation") == "i2i" and nano_i2i.get("resolutions") == ["square_hd"] and nano_i2i.get("resolutionMode") == "catalog_token", str(nano_i2i))

print("PASS catalog-h1" if not fails else f"FAIL catalog-h1 {len(fails)}: {fails}")
sys.exit(1 if fails else 0)
