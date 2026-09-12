#!/usr/bin/env python3
"""o90: cross-house LoRA search fan-out. No live Hub calls, no /api/generate."""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from providers.lora_search import (  # noqa: E402
    alias_backend,
    lora_search_houses,
    search_loras_cross,
    stamp_lora_items,
)
from providers.base import Provider  # noqa: E402
from providers.nanogpt import NanoGptProvider  # noqa: E402


def assert_true(cond, msg):
    if not cond:
        raise AssertionError(msg)


def test_houses():
    assert_true(lora_search_houses("fal") == ["fal", "civitai", "modelscope-ai"], "fal houses")
    assert_true("huggingface" not in lora_search_houses("fal"), "fal already searches HF")
    assert_true(lora_search_houses("nano-gpt") == ["nano-gpt", "civitai", "modelscope-ai"], "nano houses")
    assert_true(lora_search_houses("civitai") == ["civitai", "huggingface", "modelscope-ai"], "civitai houses")
    assert_true(lora_search_houses("huggingface") == ["huggingface", "civitai", "modelscope-ai"], "hf houses")
    assert_true(lora_search_houses("modelscope-cn") == ["modelscope-cn", "civitai", "huggingface"], "ms-cn houses")
    assert_true(lora_search_houses("nano")[0] == "nano-gpt", "alias nano")


def test_stamp():
    rows = stamp_lora_items([{"id": "a/b", "path": "a/b"}], "fal")
    assert_true(rows[0]["backend"] == "fal", "stamp backend")
    assert_true(rows[0]["source"] == "fal", "stamp source")


def test_nano_overrides_base():
    assert_true(NanoGptProvider.search_loras is not Provider.search_loras, "nano search_loras not base empty")


def test_cross_merge_no_network(monkey=None):
    import providers.lora_search as ls

    calls = []

    def fake(be, q, nsfw=True, types="LORA"):
        calls.append(be)
        return 200, {
            "items": [{
                "id": be + "-1",
                "name": be,
                "path": be + "/x",
                "backend": be,
                "source": be,
                "versions": [],
            }],
            "backend": be,
        }

    orig = ls.search_loras_one
    ls.search_loras_one = fake
    try:
        code, data = search_loras_cross("flux", current="fal")
    finally:
        ls.search_loras_one = orig
    assert_true(code == 200, "cross 200")
    assert_true(data.get("cross") is True, "cross flag")
    assert_true(data["houses"][0] == "fal", "current first")
    assert_true("civitai" in data["houses"], "civitai fan-out")
    names = [x["name"] for x in data["items"]]
    assert_true("fal" in names and "civitai" in names, "merged items %s" % names)
    assert_true(calls[0] == "fal" or "fal" in calls, "called fal")


def test_alias():
    assert_true(alias_backend("hf") == "huggingface", "hf alias")
    assert_true(alias_backend("nanogpt") == "nano-gpt", "nano alias")


if __name__ == "__main__":
    test_houses()
    test_stamp()
    test_nano_overrides_base()
    test_cross_merge_no_network()
    test_alias()
    print("PASS o90_cross_lora_search")
