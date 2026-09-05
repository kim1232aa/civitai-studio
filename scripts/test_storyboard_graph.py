#!/usr/bin/env python3
"""Storyboard buildGraph contract: t2i / i2i / i2v. Run: python3 scripts/test_storyboard_graph.py"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from providers.graph_compile import compile_graph
from providers.modelscope import wants_source_image


def compile(graph):
    return compile_graph(graph)


def assert_true(cond, msg):
    if not cond:
        raise AssertionError(msg)


def shot_graph(op, prompt, image_url=None, service=None):
    nodes = [{"id": "p-shot-1", "op": "prompt", "params": {"text": prompt}}]
    edges = [{"from": "p-shot-1", "fromPort": "prompt", "to": "shot-1", "toPort": "prompt"}]
    if image_url:
        nodes.append({"id": "a-bot", "op": "image", "params": {"url": image_url}})
        edges.append({"from": "a-bot", "fromPort": "image", "to": "shot-1", "toPort": "image"})
    nodes.append({
        "id": "shot-1",
        "op": op,
        "params": {
            "serviceId": service or ("fal-ai/minimax/video-01" if op == "i2v" else "fal-ai/flux/schnell"),
            "resolution": "1280x720",
            "duration": 5,
        },
    })
    return {"backend": "fal", "nodes": nodes, "edges": edges}


def test_t2i_no_ref():
    """Picture mode, no connected asset → t2i. Dangling @ stays text."""
    r = compile(shot_graph("t2i", "【镜头1】场景：@温馨现代卧室\n画面：室内。", image_url=None))
    assert_true(r.get("ok") is True, r)
    assert_true(r.get("execute") == "single", r)
    assert_true("sourceImage" not in (r.get("payload") or {}), r)
    assert_true("@温馨现代卧室" in r["payload"]["prompt"], r["payload"])
    assert_true(r["payload"]["serviceId"] == "fal-ai/flux/schnell", r["payload"])


def test_i2i_with_ref():
    r = compile(shot_graph("i2i", "同一位 @家用机器人 站在窗边", image_url="/out/bot.jpg", service="fal-ai/flux/dev"))
    assert_true(r.get("ok") is True, r)
    assert_true(r["payload"].get("sourceImage") == "/out/bot.jpg", r)
    assert_true(r["payload"].get("prompt", "").startswith("同一位"), r)


def test_i2v_with_first_frame():
    r = compile(shot_graph("i2v", "固定镜头，机器人轻微转动", image_url="/out/bot.jpg"))
    assert_true(r.get("ok") is True, r)
    p = r["payload"]
    assert_true(p.get("sourceImage") == "/out/bot.jpg", p)
    assert_true(p.get("firstFrame") == "/out/bot.jpg", p)
    assert_true(p.get("duration") == 5, p)


def test_i2v_missing_frame_blocked():
    r = compile(shot_graph("i2v", "固定镜头", image_url=None))
    assert_true(r.get("ok") is False, r)
    assert_true(r.get("blocked") is True, r)
    err = r.get("error") or ""
    assert_true("image" in err and "偷" in err, err)


def test_mention_without_edge_is_not_i2i():
    """@ in prompt alone must not invent an image wire."""
    r = compile(shot_graph("t2i", "@家用机器人 在卧室", image_url=None))
    assert_true(r.get("ok") is True, r)
    assert_true("sourceImage" not in r["payload"], r)


def normalize_prompt(text, linked_titles):
    """Payload-only: linked @中文名 → @图片N. Unlinked @ stays."""
    out = text or ""
    for i, title in enumerate(linked_titles, 1):
        tag = "@" + title
        if tag in out:
            out = out.replace(tag, "@图片%d" % i)
    return out


def test_payload_normalize_linked_only():
    text = "场景：@温馨现代卧室 画面：@家用机器人 和 @没连上的角色"
    got = normalize_prompt(text, ["温馨现代卧室", "家用机器人"])
    assert_true("@图片1" in got and "@图片2" in got, got)
    assert_true("@没连上的角色" in got, got)
    assert_true("@温馨现代卧室" not in got, got)


def test_i2v_first_frame_pick_second_ref():
    """Two linked images; compile image port is the chosen first-frame, not always [0]."""
    g = {
        "backend": "fal",
        "nodes": [
            {"id": "p-shot-1", "op": "prompt", "params": {"text": "固定镜头"}},
            {"id": "a-bot", "op": "image", "params": {"url": "/out/bot.jpg"}},
            {"id": "a-bed", "op": "image", "params": {"url": "/out/bed.jpg"}},
            {"id": "shot-1", "op": "i2v", "params": {"serviceId": "fal-ai/minimax/video-01", "duration": 5}},
        ],
        "edges": [
            {"from": "p-shot-1", "fromPort": "prompt", "to": "shot-1", "toPort": "prompt"},
            {"from": "a-bed", "fromPort": "image", "to": "shot-1", "toPort": "image"},
        ],
    }
    r = compile(g)
    assert_true(r.get("ok") is True, r)
    assert_true(r["payload"].get("sourceImage") == "/out/bed.jpg", r["payload"])
    assert_true(r["payload"].get("firstFrame") == "/out/bed.jpg", r["payload"])


def test_shot_result_as_image_node():
    """Finished shot.url can be an image node for the next shot (t2i → i2i)."""
    g = {
        "backend": "fal",
        "nodes": [
            {"id": "p-2", "op": "prompt", "params": {"text": "同一场景继续"}},
            {"id": "shot-1", "op": "image", "params": {"url": "/out/shot1.jpg"}},
            {"id": "shot-2", "op": "i2i", "params": {"serviceId": "fal-ai/flux/dev", "resolution": "1280x720"}},
        ],
        "edges": [
            {"from": "p-2", "fromPort": "prompt", "to": "shot-2", "toPort": "prompt"},
            {"from": "shot-1", "fromPort": "image", "to": "shot-2", "toPort": "image"},
        ],
    }
    r = compile(g)
    assert_true(r.get("ok") is True, r)
    assert_true(r["payload"].get("sourceImage") == "/out/shot1.jpg", r["payload"])


def test_first_frame_from_promoted_asset():
    """i2v first frame can be a promoted shot result, not only a library character."""
    g = {
        "backend": "fal",
        "nodes": [
            {"id": "p-v", "op": "prompt", "params": {"text": "固定镜头轻微转动"}},
            {"id": "shot-1", "op": "image", "params": {"url": "/out/shot1.jpg"}},
            {"id": "shot-3", "op": "i2v", "params": {"serviceId": "fal-ai/minimax/video-01", "duration": 5}},
        ],
        "edges": [
            {"from": "p-v", "fromPort": "prompt", "to": "shot-3", "toPort": "prompt"},
            {"from": "shot-1", "fromPort": "image", "to": "shot-3", "toPort": "image"},
        ],
    }
    r = compile(g)
    assert_true(r.get("ok") is True, r)
    assert_true(r["payload"].get("firstFrame") == "/out/shot1.jpg", r["payload"])
    assert_true(r["payload"].get("sourceImage") == "/out/shot1.jpg", r["payload"])


def test_rail_history_not_in_compile():
    """/api/outs history stays in the rail; compile only sees wired image nodes."""
    r = compile(shot_graph("t2i", "空镜", image_url=None))
    assert_true(r.get("ok") is True, r)
    assert_true("sourceImage" not in (r.get("payload") or {}), r)


def upscale_graph(backend, image_url="/out/shot1.jpg"):
    return {
        "backend": backend,
        "nodes": [
            {"id": "a-src", "op": "image", "params": {"url": image_url}},
            {"id": "shot-up", "op": "upscale", "params": {"serviceId": "fal-ai/clarity-upscaler"}},
        ],
        "edges": [
            {"from": "a-src", "fromPort": "image", "to": "shot-up", "toPort": "image"},
        ],
    }


def test_upscale_on_fal():
    """图片超清：fal 的 catalog 驱动 imageFields 通用支持 upscale 类目模型。"""
    r = compile(upscale_graph("fal"))
    assert_true(r.get("ok") is True, r)
    assert_true(r["payload"].get("sourceImage") == "/out/shot1.jpg", r)
    assert_true("prompt" not in r["payload"], r["payload"])


def test_upscale_blocked_on_huggingface():
    """huggingface 的 _call_bytes 目前完全不带图，禁止静默降级成纯文生图。"""
    r = compile(upscale_graph("huggingface"))
    assert_true(r.get("ok") is False, r)
    assert_true(r.get("blocked") is True, r)
    assert_true("超清" in (r.get("error") or ""), r)


def test_upscale_missing_image_blocked():
    g = upscale_graph("fal")
    g["nodes"] = [n for n in g["nodes"] if n["id"] != "a-src"]
    g["edges"] = []
    r = compile(g)
    assert_true(r.get("ok") is False, r)
    assert_true(r.get("blocked") is True, r)


def test_upscale_on_modelscope_ai():
    """图片超清：修复 is_edit(mid) 漏判后，muse/NMKDSuperscale15000G8x 等真实超清模型可用。"""
    r = compile({**upscale_graph("modelscope-ai"), "nodes": [
        {"id": "a-src", "op": "image", "params": {"url": "/out/shot1.jpg"}},
        {"id": "shot-up", "op": "upscale", "params": {"serviceId": "muse/NMKDSuperscale15000G8x"}},
    ]})
    assert_true(r.get("ok") is True, r)
    assert_true(r["payload"].get("sourceImage") == "/out/shot1.jpg", r)


def test_upscale_on_modelscope_cn():
    r = compile({**upscale_graph("modelscope-cn"), "nodes": [
        {"id": "a-src", "op": "image", "params": {"url": "/out/shot1.jpg"}},
        {"id": "shot-up", "op": "upscale", "params": {"serviceId": "muse/NMKDSuperscale15000G8x"}},
    ]})
    assert_true(r.get("ok") is True, r)
    assert_true(r["payload"].get("sourceImage") == "/out/shot1.jpg", r)


def test_modelscope_wants_source_image_covers_real_upscale_ids():
    """/api/catalog?backend=modelscope-ai&category=upscale 里真实的 8 个模型 id 都要命中，
    否则会静默退化成纯文生图（这就是原来的 bug）。"""
    real_ids = [
        "muse/NMKDSuperscale15000G8x",
        "muse/4xNomos8kSCHAT-L",
        "muse/Ultrasharp4x",
        "muse/NMKD_Siax_200k_x4",
        "jasperai/Flux.1-dev-Controlnet-Upscaler",
        "AI-ModelScope/Flux.1-dev-Controlnet-Upscaler",
        "Xenova/4x_APISR_GRL_GAN_generator-onnx",
        "Xenova/2x_APISR_RRDB_GAN_generator-onnx",
    ]
    for mid in real_ids:
        assert_true(wants_source_image(mid), f"{mid} should attach sourceImage")
    assert_true(not wants_source_image("Tongyi-MAI/Z-Image-Turbo"), "plain t2i model must stay text-only")


def main():
    tests = [
        test_t2i_no_ref,
        test_i2i_with_ref,
        test_i2v_with_first_frame,
        test_i2v_missing_frame_blocked,
        test_mention_without_edge_is_not_i2i,
        test_payload_normalize_linked_only,
        test_i2v_first_frame_pick_second_ref,
        test_shot_result_as_image_node,
        test_first_frame_from_promoted_asset,
        test_rail_history_not_in_compile,
        test_upscale_on_fal,
        test_upscale_blocked_on_huggingface,
        test_upscale_missing_image_blocked,
        test_upscale_on_modelscope_ai,
        test_upscale_on_modelscope_cn,
        test_modelscope_wants_source_image_covers_real_upscale_ids,
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
