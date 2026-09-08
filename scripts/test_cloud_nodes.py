#!/usr/bin/env python3
"""Contract tests for cloud-node compile. Run: python3 scripts/test_cloud_nodes.py"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from providers.graph_compile import compile_graph  # noqa: E402


def g(**kw):
    return compile_graph(kw)


def assert_true(cond, msg):
    if not cond:
        raise AssertionError(msg)


def test_missing_image_blocked():
    r = g(
        backend="fal",
        nodes=[{"id": "v", "op": "i2v", "params": {"serviceId": "fal-ai/minimax/video-01"}}],
        edges=[],
    )
    assert_true(r.get("ok") is False, r)
    assert_true(r.get("blocked") is True, r)
    assert_true("image" in (r.get("error") or ""), r)


def test_single_i2v_payload():
    r = g(
        backend="nano-gpt",
        nodes=[
            {"id": "img", "op": "image", "params": {"url": "/out/x.jpg"}},
            {"id": "p", "op": "prompt", "params": {"text": "pan"}},
            {"id": "v", "op": "i2v", "params": {"serviceId": "vidu-q2-pro", "duration": 5}},
        ],
        edges=[
            {"from": "img", "fromPort": "image", "to": "v", "toPort": "image"},
            {"from": "p", "fromPort": "prompt", "to": "v", "toPort": "prompt"},
        ],
    )
    assert_true(r.get("ok") is True, r)
    assert_true(r.get("execute") == "single", r)
    assert_true(r.get("payload", {}).get("serviceId") == "vidu-q2-pro", r)
    assert_true(r["payload"].get("prompt") == "pan", r)
    assert_true(r["payload"].get("sourceImage") == "/out/x.jpg", r)


def test_chain_is_staged():
    r = g(
        backend="nano-gpt",
        nodes=[
            {"id": "p", "op": "prompt", "params": {"text": "x"}},
            {"id": "g", "op": "t2i", "params": {"serviceId": "flux"}},
            {"id": "v", "op": "i2v", "params": {"serviceId": "vidu-q2-pro"}},
        ],
        edges=[
            {"from": "p", "fromPort": "prompt", "to": "g", "toPort": "prompt"},
            {"from": "g", "fromPort": "image", "to": "v", "toPort": "image"},
        ],
    )
    assert_true(r.get("ok") is True, r)
    assert_true(r.get("multiStep") is True, r)
    assert_true(r.get("execute") == "staged", r)
    assert_true(len(r.get("stages") or []) == 2, r)
    img = r["payload"].get("sourceImage")
    assert_true(isinstance(img, dict) and img.get("__stageOut__") == "g", img)


def test_hf_i2v_blocked():
    r = g(
        backend="huggingface",
        nodes=[
            {"id": "img", "op": "image", "params": {"url": "/out/x.jpg"}},
            {"id": "v", "op": "i2v", "params": {"serviceId": "x"}},
        ],
        edges=[{"from": "img", "fromPort": "image", "to": "v", "toPort": "image"}],
    )
    assert_true(r.get("ok") is False, r)
    assert_true(r.get("blocked") is True, r)


def test_seed_bypass_blocked():
    r = g(
        backend="fal",
        nodes=[
            {"id": "p", "op": "prompt", "params": {"text": "x"}},
            {"id": "t", "op": "t2i", "params": {"serviceId": "flux", "seed": 1}},
        ],
        edges=[{"from": "p", "fromPort": "prompt", "to": "t", "toPort": "prompt"}],
    )
    assert_true(r.get("ok") is False, r)
    assert_true("seed" in (r.get("error") or ""), r)


def test_unknown_op():
    r = g(
        backend="fal",
        nodes=[{"id": "c", "op": "CheckpointLoader", "params": {}}],
        edges=[],
    )
    assert_true(r.get("ok") is False, r)
    assert_true("未知 op" in (r.get("error") or ""), r)


def test_i2v_empty_prompt_allowed():
    """v0821i: i2v prompt node may be empty string (optional)."""
    r = g(
        backend="fal",
        nodes=[
            {"id": "img", "op": "image", "params": {"url": "/out/x.jpg"}},
            {"id": "p", "op": "prompt", "params": {"text": ""}},
            {"id": "v", "op": "i2v", "params": {"serviceId": "fal-ai/minimax/video-01/image-to-video", "duration": 5}},
        ],
        edges=[
            {"from": "img", "fromPort": "image", "to": "v", "toPort": "image"},
            {"from": "p", "fromPort": "prompt", "to": "v", "toPort": "prompt"},
        ],
    )
    assert_true(r.get("ok") is True, r)
    assert_true((r.get("payload") or {}).get("prompt") == "", r)
    assert_true("缺少文本" not in (r.get("error") or ""), r)


def main():
    tests = [
        test_missing_image_blocked,
        test_single_i2v_payload,
        test_chain_is_staged,
        test_hf_i2v_blocked,
        test_seed_bypass_blocked,
        test_unknown_op,
        test_i2v_empty_prompt_allowed,
    ]
    failed = 0
    for fn in tests:
        try:
            fn()
            print("ok", fn.__name__)
        except Exception as e:
            failed += 1
            print("FAIL", fn.__name__, e)
    print("result", len(tests) - failed, "/", len(tests))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
