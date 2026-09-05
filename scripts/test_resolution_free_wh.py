#!/usr/bin/env python3
"""free_wh 服务的 `720x1280` 必须拆成 width/height。

真 bug 复现：UI 选 9:16 + 720P → buildGraph 只发 resolution="720x1280"，
comfy imageGen 的 cap 里根本没有 resolution 字段，被 allowed 过滤掉，
Civitai 落回 defaults width=1024/height=1024 → 出图恒 1024x1024。

Run: python3 scripts/test_resolution_free_wh.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from providers.civitai import build_workflow
from providers.graph_compile import compile_graph

KREA2 = "image/comfy/krea2/turbo/createImage"


def ok(cond, msg):
    if not cond:
        raise AssertionError(msg)


def t2i_graph(backend="civitai", service=KREA2, params=None):
    p = {"serviceId": service, "resolution": "720x1280"}
    p.update(params or {})
    return {
        "backend": backend,
        "nodes": [
            {"id": "p-shot-1", "op": "prompt", "params": {"text": "a cat"}},
            {"id": "shot-1", "op": "t2i", "params": p},
        ],
        "edges": [{"from": "p-shot-1", "fromPort": "prompt", "to": "shot-1", "toPort": "prompt"}],
    }


def test_compile_splits_wh_for_free_wh():
    r = compile_graph(t2i_graph())
    ok(not r.get("error"), f"compile 失败: {r.get('error')}")
    pl = r.get("payload") or (r.get("stages") or [{}])[0].get("payload")
    ok(pl.get("width") == 720, f"width 应为 720，实际 {pl.get('width')!r}")
    ok(pl.get("height") == 1280, f"height 应为 1280，实际 {pl.get('height')!r}")
    ok("resolution" not in pl, f"free_wh 不该再透传 resolution，实际 {pl.get('resolution')!r}")


def test_compile_keeps_explicit_wh():
    r = compile_graph(t2i_graph(params={"width": 512, "height": 768}))
    pl = r.get("payload") or (r.get("stages") or [{}])[0].get("payload")
    ok(pl.get("width") == 512 and pl.get("height") == 768,
       f"显式 width/height 应优先，实际 {pl.get('width')}x{pl.get('height')}")


def test_compile_catalog_token_backend_untouched():
    r = compile_graph(t2i_graph(backend="nano-gpt", service="image/nano-gpt/flux"))
    pl = (r.get("payload") or (r.get("stages") or [{}])[0].get("payload")) or {}
    ok("width" not in pl and "height" not in pl,
       f"catalog_token 后端不该被塞 width/height，实际 {pl!r}")


def test_build_workflow_splits_wh():
    body = build_workflow({"backend": "civitai", "serviceId": KREA2,
                           "prompt": "a cat", "resolution": "720x1280"})
    inp = body["steps"][0]["input"]
    ok(inp.get("width") == 720, f"width 应为 720，实际 {inp.get('width')!r}")
    ok(inp.get("height") == 1280, f"height 应为 1280，实际 {inp.get('height')!r}")
    ok(inp.get("width") != inp.get("height"), "9:16 不该落成正方形")


def test_build_workflow_1080p_landscape():
    body = build_workflow({"backend": "civitai", "serviceId": KREA2,
                           "prompt": "a cat", "resolution": "1920x1080"})
    inp = body["steps"][0]["input"]
    ok((inp.get("width"), inp.get("height")) == (1920, 1080),
       f"1920x1080 拆错: {inp.get('width')}x{inp.get('height')}")


def test_build_workflow_explicit_wh_wins():
    body = build_workflow({"backend": "civitai", "serviceId": KREA2, "prompt": "a cat",
                           "resolution": "720x1280", "width": 512, "height": 768})
    inp = body["steps"][0]["input"]
    ok((inp.get("width"), inp.get("height")) == (512, 768),
       f"显式 width/height 应优先，实际 {inp.get('width')}x{inp.get('height')}")


def test_video_resolution_token_untouched():
    """wan videoGen 的 resolution 是 catalog 令牌（720p），禁止被拆。"""
    body = build_workflow({"backend": "civitai", "kind": "video",
                           "serviceId": "video/wan/v2.2/i2v",
                           "prompt": "a cat", "resolution": "720p",
                           "sourceImage": "https://example.com/a.jpg"})
    inp = body["steps"][0]["input"]
    ok(inp.get("resolution") == "720p", f"视频 resolution 令牌被改坏: {inp.get('resolution')!r}")


def main():
    fails = []
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"  ok  {name}")
            except AssertionError as e:
                fails.append((name, str(e)))
                print(f"FAIL  {name}: {e}")
            except Exception as e:  # noqa: BLE001
                fails.append((name, f"{type(e).__name__}: {e}"))
                print(f"ERR   {name}: {type(e).__name__}: {e}")
    if fails:
        print(f"\n{len(fails)} failed")
        return 1
    print("\nresolution-free-wh ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
