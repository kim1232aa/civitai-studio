#!/usr/bin/env python3
"""Pure-Python mirrors of LiteGraph step-runner helpers (no live API).

Mirrors static/cloud-nodes.html: nextRunnableStage + fillStageRefs deep-walk.
Run: python3 scripts/test_step_runner.py
"""
from __future__ import annotations

import copy
from typing import Any


def fill_stage_refs(payload: Any, stage_urls: dict) -> Any:
    """Deep-walk nested dict/list; replace {__stageOut__: id} only when URL exists."""

    def walk(v: Any) -> Any:
        if isinstance(v, list):
            return [walk(x) for x in v]
        if isinstance(v, dict):
            if "__stageOut__" in v:
                u = stage_urls.get(str(v["__stageOut__"]))
                return u if u else v
            return {k: walk(val) for k, val in v.items()}
        return v

    return walk(copy.deepcopy(payload if payload is not None else {}))


def next_runnable_stage(plan: dict | None, stage_urls: dict) -> dict | None:
    stages = (plan or {}).get("stages") or []
    for s in stages:
        if stage_urls.get(str(s.get("id"))):
            continue
        needs = s.get("needs") or []
        if all(stage_urls.get(str(i)) for i in needs):
            return s
    return None


def has_unresolved_stage_out(obj: Any) -> bool:
    if isinstance(obj, list):
        return any(has_unresolved_stage_out(x) for x in obj)
    if isinstance(obj, dict):
        if "__stageOut__" in obj:
            return True
        return any(has_unresolved_stage_out(v) for v in obj.values())
    return False


def assert_true(cond, msg):
    if not cond:
        raise AssertionError(msg)


def test_needs_gating():
    """Downstream needs upstream stage URL before it is runnable."""
    plan = {
        "stages": [
            {"id": "a", "op": "t2i", "needs": [], "payload": {"prompt": "x"}},
            {
                "id": "b",
                "op": "i2v",
                "needs": ["a"],
                "payload": {"sourceImage": {"__stageOut__": "a"}},
            },
        ]
    }
    urls: dict = {}
    nxt = next_runnable_stage(plan, urls)
    assert_true(nxt is not None and nxt["id"] == "a", nxt)
    # b must wait for needs
    assert_true(
        next_runnable_stage({"stages": [plan["stages"][1]]}, urls) is None,
        "b runnable without a",
    )
    urls["a"] = "https://cdn.example/a.jpg"
    nxt = next_runnable_stage(plan, urls)
    assert_true(nxt is not None and nxt["id"] == "b", nxt)


def test_skip_completed_stages():
    plan = {
        "stages": [
            {"id": "a", "op": "t2i", "needs": []},
            {"id": "b", "op": "i2v", "needs": ["a"]},
        ]
    }
    urls = {"a": "https://cdn.example/a.jpg"}
    nxt = next_runnable_stage(plan, urls)
    assert_true(nxt is not None and nxt["id"] == "b", nxt)
    urls["b"] = "https://cdn.example/b.mp4"
    assert_true(next_runnable_stage(plan, urls) is None, "all done should be None")


def test_refuse_unresolved_stage_out():
    payload = {"sourceImage": {"__stageOut__": "g"}, "prompt": "go"}
    filled = fill_stage_refs(payload, {})
    assert_true(has_unresolved_stage_out(filled), filled)
    assert_true(
        isinstance(filled["sourceImage"], dict)
        and filled["sourceImage"].get("__stageOut__") == "g",
        filled,
    )
    filled_ok = fill_stage_refs(payload, {"g": "https://cdn.example/g.jpg"})
    assert_true(not has_unresolved_stage_out(filled_ok), filled_ok)
    assert_true(filled_ok["sourceImage"] == "https://cdn.example/g.jpg", filled_ok)


def test_nested_first_frame_source_image():
    """Deep-walk must reach nested firstFrame / sourceImage, not only top-level keys."""
    payload = {
        "sourceImage": {"__stageOut__": "g"},
        "params": {
            "firstFrame": {"__stageOut__": "g"},
            "extra": [{"sourceImage": {"__stageOut__": "g"}}],
        },
    }
    filled = fill_stage_refs(payload, {"g": "/out/g.jpg"})
    assert_true(filled["sourceImage"] == "/out/g.jpg", filled)
    assert_true(filled["params"]["firstFrame"] == "/out/g.jpg", filled)
    assert_true(filled["params"]["extra"][0]["sourceImage"] == "/out/g.jpg", filled)
    # only replace when URL exists — leave marker otherwise
    partial = fill_stage_refs(payload, {})
    assert_true(partial["params"]["firstFrame"]["__stageOut__"] == "g", partial)
    assert_true(has_unresolved_stage_out(partial), partial)


def test_fill_only_when_url_exists_mixed():
    payload = {
        "a": {"__stageOut__": "done"},
        "b": {"__stageOut__": "pending"},
    }
    filled = fill_stage_refs(payload, {"done": "/out/done.jpg"})
    assert_true(filled["a"] == "/out/done.jpg", filled)
    assert_true(filled["b"]["__stageOut__"] == "pending", filled)


def main():
    tests = [
        test_needs_gating,
        test_skip_completed_stages,
        test_refuse_unresolved_stage_out,
        test_nested_first_frame_source_image,
        test_fill_only_when_url_exists_mixed,
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
