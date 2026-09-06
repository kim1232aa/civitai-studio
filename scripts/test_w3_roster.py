#!/usr/bin/env python3
"""W3 backend roster: HF Hub list, ModelScope hub-only, fal/nano category+page facts.

No generate POSTs. Hub HTTP is mocked.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from providers import fal as fal_mod  # noqa: E402
from providers import huggingface as hf_mod  # noqa: E402
from providers import modelscope as ms_mod  # noqa: E402
from providers import nanogpt as nano_mod  # noqa: E402
from providers.fal import FalProvider  # noqa: E402
from providers.huggingface import HuggingFaceProvider  # noqa: E402
from providers.modelscope import ModelScopeProvider  # noqa: E402
from providers.nanogpt import NanoGptProvider  # noqa: E402

fails = []


def check(name, cond, detail=""):
    if cond:
        print(f"  ok   {name}")
    else:
        fails.append(name)
        print(f"  FAIL {name} {detail}")


def _hf_model(mid, pipe="text-to-image", live="fal-ai", extra=None):
    mapping = []
    if live:
        mapping.append({"provider": live, "status": "live", "providerId": mid, "task": pipe})
    if extra:
        mapping.extend(extra)
    return {"id": mid, "pipeline_tag": pipe, "inferenceProviderMapping": mapping}


def test_hf_hub_not_pins_only():
    print("hf roster")
    pages = {
        "text-to-image": [
            _hf_model("black-forest-labs/FLUX.1-schnell"),
            _hf_model("playgroundai/playground-v2.5-1024px-aesthetic"),
            _hf_model("nphSi/Z-Image-Lora"),  # adapter — drop
            _hf_model("someone/dead-model", live=None, extra=[{"provider": "nscale", "status": "error", "providerId": "x", "task": "text-to-image"}]),
        ],
        "image-to-image": [
            _hf_model("Qwen/Qwen-Image-Edit", pipe="image-to-image"),
        ],
    }

    def fake_get(url, timeout=25):
        pipe = "text-to-image"
        if "pipeline_tag=image-to-image" in url:
            pipe = "image-to-image"
        elif "pipeline_tag=text-to-video" in url:
            pipe = "text-to-video"
        elif "pipeline_tag=image-to-video" in url:
            pipe = "image-to-video"
        data = pages.get(pipe, [])
        return 200, data, {}

    orig_get = hf_mod._hub_get
    orig_cache = dict(hf_mod._HUB_LIST_CACHE)
    hf_mod._HUB_LIST_CACHE["at"] = 0.0
    hf_mod._HUB_LIST_CACHE["pipes"] = {}
    hf_mod._hub_get = fake_get
    try:
        hub, meta = hf_mod.fetch_hf_roster("", "image")
        ids = [x.get("id") for x in hub]
        check("hf hub 不止 8 条 pin", "playgroundai/playground-v2.5-1024px-aesthetic" in ids, str(ids))
        check("hf 丢掉 LoRA adapter", "nphSi/Z-Image-Lora" not in ids, str(ids))
        check("hf 丢掉无 live provider", "someone/dead-model" not in ids, str(ids))
        check("hf 收下 i2i", "Qwen/Qwen-Image-Edit" in ids, str(ids))
        check("hf source=hub", meta.get("source") == "hub", str(meta))

        prov = HuggingFaceProvider()
        body = prov.catalog("", "image", "")
        items = body.get("items") or []
        item_ids = [x.get("id") for x in items]
        check("hf catalog pin 置顶", item_ids and item_ids[0] in {p.get("id") for p in hf_mod.load_items()}, str(item_ids[:3]))
        check("hf catalog 含 hub 模型", "playgroundai/playground-v2.5-1024px-aesthetic" in item_ids, str(item_ids))
        check("hf 报分类", isinstance(body.get("categories"), dict) and body["categories"].get("image", 0) > 0, str(body.get("categories")))
        check("hf 报分页", isinstance(body.get("pagination"), dict) and body["pagination"].get("source") == "hub", str(body.get("pagination")))
        pin_n = len([x for x in hf_mod.load_items() if x.get("category") == "image"])
        check("hf 不是 pin 全集", len(items) > pin_n, f"n={len(items)} pins={pin_n}")
    finally:
        hf_mod._hub_get = orig_get
        hf_mod._HUB_LIST_CACHE.clear()
        hf_mod._HUB_LIST_CACHE.update(orig_cache)


def test_hf_hub_down_uses_pins():
    print("hf fallback")

    def dead_get(url, timeout=25):
        return 502, {"error": "网络错误"}, {}

    orig_get = hf_mod._hub_get
    orig_cache = dict(hf_mod._HUB_LIST_CACHE)
    hf_mod._HUB_LIST_CACHE["at"] = 0.0
    hf_mod._HUB_LIST_CACHE["pipes"] = {}
    hf_mod._hub_get = dead_get
    try:
        hub, meta = hf_mod.fetch_hf_roster("", "image")
        check("hf unreachable 空 hub", hub == [] and meta.get("source") == "unreachable", str(meta))
        body = HuggingFaceProvider().catalog("", "image", "")
        check("hf hub 挂了才用 pin", body.get("pagination", {}).get("source") == "hardcoded_fallback", str(body.get("pagination")))
        check("hf fallback 仍有 pin", len(body.get("items") or []) > 0, str(len(body.get("items") or [])))
    finally:
        hf_mod._hub_get = orig_get
        hf_mod._HUB_LIST_CACHE.clear()
        hf_mod._HUB_LIST_CACHE.update(orig_cache)


def test_hf_mapping_list():
    print("hf mapping")
    raw = [
        {"provider": "fal-ai", "status": "live", "providerId": "fal-ai/fast-sdxl"},
        {"provider": "nscale", "status": "error", "providerId": "x"},
    ]
    m = hf_mod._normalize_mapping(raw)
    check("list mapping → dict", set(m) == {"fal-ai", "nscale"}, str(m.keys()))
    check("live provider 识别", hf_mod._has_live_provider(raw) is True)
    check("全 error 不算 live", hf_mod._has_live_provider([{"provider": "nscale", "status": "error"}]) is False)
    check("adapter id", hf_mod._is_adapter_id("nphSi/Z-Image-Lora") and not hf_mod._is_adapter_id("Qwen/Qwen-Image"))


def test_ms_hub_not_inject_pins():
    print("ms roster")
    orig_call = ms_mod.json_call
    orig_cache = dict(ms_mod._HUB_CACHE)
    ms_mod._HUB_CACHE["at"] = 0.0
    ms_mod._HUB_CACHE["items"] = None
    ms_mod._HUB_CACHE["totals"] = {}
    ms_mod._HUB_CACHE["by_key"] = {}

    def fake_call(url, method="GET", headers=None, body=None, timeout=90):
        if "filter.task=text-to-image-synthesis" in url and "page_number=1" in url:
            return 200, {
                "data": {
                    "models": [
                        {"id": "Qwen/Qwen-Image", "name": "Qwen Image", "tasks": ["text-to-image-synthesis"], "downloads": 9},
                        {"id": "hub-only/NotInPins", "name": "Hub Only", "tasks": ["text-to-image-synthesis"], "downloads": 8},
                    ],
                    "total_count": 2,
                    "page_number": 1,
                    "page_size": 50,
                }
            }
        if "filter.task=" in url:
            task = "image-to-image"
            if "text-to-video" in url:
                task = "text-to-video-synthesis"
            elif "image-to-video" in url:
                task = "image-to-video"
            return 200, {"data": {"models": [], "total_count": 0, "page_number": 1, "page_size": 50, "tasks": [task]}}
        return 502, {"error": "nope"}

    ms_mod.json_call = fake_call
    try:
        hub, totals = ms_mod.fetch_hub(search="", category="image")
        ids = [x.get("id") for x in hub]
        check("ms hub 拉到 Hub only", "hub-only/NotInPins" in ids, str(ids))
        check("ms reachable", totals.get("_reachable") is True, str(totals))
        check("ms 报 t2i total_count", totals.get("text-to-image-synthesis") == 2, str(totals))

        body = ModelScopeProvider("ai").catalog("", "image", "")
        item_ids = [x.get("id") for x in (body.get("items") or [])]
        pin_ids = {p.get("id") for p in ms_mod.load_disk()}
        extra_pins = [p for p in pin_ids if p not in set(ids) and p in item_ids]
        # Qwen-Image is both pin and hub — allowed. Krea pins must NOT be injected.
        check("ms hub 成功不灌缺失 pin", "krea/Krea-2-Turbo" not in item_ids, str(item_ids))
        check("ms 含 hub-only", "hub-only/NotInPins" in item_ids, str(item_ids))
        check("ms source=hub", (body.get("pagination") or {}).get("source") == "hub", str(body.get("pagination")))
        check("ms 报分类", isinstance(body.get("categories"), dict), str(body.get("categories")))
        check("ms 报分页 pageSize=50", (body.get("pagination") or {}).get("pageSize") == 50, str(body.get("pagination")))
        check("ms extra pins 未灌", extra_pins == [] or extra_pins == ["Qwen/Qwen-Image"], str(extra_pins))
        cn = ModelScopeProvider("cn").catalog("", "image", "")
        check("ms cn 同源 hub", "hub-only/NotInPins" in [x.get("id") for x in (cn.get("items") or [])], str(len(cn.get("items") or [])))
    finally:
        ms_mod.json_call = orig_call
        ms_mod._HUB_CACHE.clear()
        ms_mod._HUB_CACHE.update(orig_cache)


def test_ms_hub_down_uses_pins():
    print("ms fallback")
    orig_call = ms_mod.json_call
    orig_cache = dict(ms_mod._HUB_CACHE)
    ms_mod._HUB_CACHE["at"] = 0.0
    ms_mod._HUB_CACHE["items"] = None
    ms_mod._HUB_CACHE["totals"] = {}
    ms_mod._HUB_CACHE["by_key"] = {}
    ms_mod.json_call = lambda *a, **k: (502, {"error": "down"})
    try:
        hub, totals = ms_mod.fetch_hub(search="", category="image")
        check("ms down 空 hub", hub == [] and not totals.get("_reachable"), str(totals))
        body = ModelScopeProvider("ai").catalog("", "image", "")
        check("ms hub 挂了才用 hardcoded", (body.get("pagination") or {}).get("source") == "hardcoded_fallback", str(body.get("pagination")))
        pin_ids = {p.get("id") for p in ms_mod.load_disk() if p.get("category") == "image"}
        got = {x.get("id") for x in (body.get("items") or [])}
        check("ms fallback = disk pins", pin_ids <= got, str(got))
    finally:
        ms_mod.json_call = orig_call
        ms_mod._HUB_CACHE.clear()
        ms_mod._HUB_CACHE.update(orig_cache)


def test_fal_category_pagination():
    print("fal facts")
    body = FalProvider().catalog("", "image", "")
    cats = body.get("categories") or {}
    pag = body.get("pagination") or {}
    check("fal categories 是 dict", isinstance(cats, dict) and cats.get("image") == body.get("count"), str(cats))
    check("fal 全部分类合计=unfiltered", sum(cats.values()) == body.get("unfilteredTotal"), f"{sum(cats.values())} vs {body.get('unfilteredTotal')}")
    check("fal 一页全量", pag.get("hasMore") is False and pag.get("pages") == 1, str(pag))
    check("fal source=json", pag.get("source") == "docs/fal-models.json", str(pag))
    check("fal sourceTotal", pag.get("sourceTotal") == body.get("unfilteredTotal"), str(pag))
    vid = FalProvider().catalog("", "video", "")
    check("fal video 分类数对得上", (vid.get("categories") or {}).get("video") == vid.get("count"), str(vid.get("categories")))


def test_nano_category_pagination():
    print("nano facts")
    orig_img = nano_mod.fetch_catalog
    orig_text = nano_mod.fetch_text_catalog
    nano_mod.fetch_catalog = lambda force=False: [
        {"id": "img-a", "name": "A", "category": "image", "status": "available", "tags": []},
        {"id": "vid-a", "name": "V", "category": "video", "status": "available", "tags": [], "task": "text-to-video"},
    ]
    nano_mod.fetch_text_catalog = lambda force=False: [
        {"id": "txt-a", "name": "T", "category": "text", "status": "available", "tags": []},
    ]
    try:
        img = NanoGptProvider().catalog("", "image", "")
        txt = NanoGptProvider().catalog("", "text", "")
        check("nano image count=1", img.get("count") == 1, str(img.get("count")))
        check("nano 报三类实数", img.get("categories") == {"image": 1, "video": 1, "text": 1}, str(img.get("categories")))
        check("nano image 分页无截断", (img.get("pagination") or {}).get("hasMore") is False, str(img.get("pagination")))
        check("nano text count=1", txt.get("count") == 1, str(txt.get("count")))
        check("nano text 同源 categories", txt.get("categories") == {"image": 1, "video": 1, "text": 1}, str(txt.get("categories")))
        check("nano text source 指向 models", "models" in str((txt.get("pagination") or {}).get("source")), str(txt.get("pagination")))
    finally:
        nano_mod.fetch_catalog = orig_img
        nano_mod.fetch_text_catalog = orig_text


def main():
    test_hf_mapping_list()
    test_hf_hub_not_pins_only()
    test_hf_hub_down_uses_pins()
    test_ms_hub_not_inject_pins()
    test_ms_hub_down_uses_pins()
    test_fal_category_pagination()
    test_nano_category_pagination()
    print("PASS w3-roster" if not fails else f"FAIL w3-roster {len(fails)}: {fails}")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
