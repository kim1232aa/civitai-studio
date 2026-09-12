#!/usr/bin/env python3
"""o93: catalog search fan-out. No /api/generate."""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from providers.catalog_search import (  # noqa: E402
    model_search_houses,
    search_models_cross,
    stamp_model_items,
    OP_QUERY,
)


def assert_true(cond, msg):
    if not cond:
        raise AssertionError(msg)


def test_houses():
    h = model_search_houses("fal")
    assert_true(h[0] == "fal", "current first")
    assert_true("civitai" in h and "huggingface" in h, "fan-out houses %s" % h)
    assert_true(len(h) == len(set(h)), "unique")


def test_stamp():
    rows = stamp_model_items([{"name": "a/b"}], "fal")
    assert_true(rows[0]["backend"] == "fal", "stamp backend")
    assert_true(rows[0]["id"] == "a/b", "id from name")


def test_op_query():
    assert_true(OP_QUERY["t2v"] == "text-to-video", "t2v q")
    assert_true(OP_QUERY["i2i"] == "edit", "i2i q")


def test_cross_no_network():
    import providers.catalog_search as cs

    calls = []

    def fake(be, q, category="", op=""):
        calls.append(be)
        return 200, {
            "items": [{"id": be + "/x", "name": be, "backend": be, "source": be}],
            "backend": be,
        }

    orig = cs.search_models_one
    cs.search_models_one = fake
    try:
        code, data = search_models_cross("edit", current="civitai", op="i2i")
    finally:
        cs.search_models_one = orig
    assert_true(code == 200, "200")
    assert_true(data.get("cross") is True, "cross")
    assert_true(data["houses"][0] == "civitai", "current first")
    names = [x["name"] for x in data["items"]]
    assert_true("civitai" in names and "fal" in names, "merged %s" % names)
    assert_true("fal" in calls and "civitai" in calls, "called both")


if __name__ == "__main__":
    test_houses()
    test_stamp()
    test_op_query()
    test_cross_no_network()
    print("PASS o93_catalog_search.py")
