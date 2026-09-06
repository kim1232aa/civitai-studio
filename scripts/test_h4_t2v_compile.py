#!/usr/bin/env python3
"""H4: OP_SPEC 必须有 t2v；文生视频不得改打 i2v，也不得要首帧。

Run: python3 scripts/test_h4_t2v_compile.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from providers.graph_compile import OP_SPEC, compile_graph  # noqa: E402

fails = []


def check(name, cond, detail=""):
    if cond:
        print(f"  ok   {name}")
    else:
        fails.append(name)
        print(f"  FAIL {name} {detail}")


T2V_CIV = "video/wan/v2.2/fal/text-to-video"
T2V_HF = "tencent/HunyuanVideo"
I2V_CIV = "video/minimax-h3-comfy/imageToVideo"


def t2v_graph(backend="civitai", service=T2V_CIV, params=None, prompt=True, image=False):
    p = {"serviceId": service, "duration": 5, "resolution": "720p"}
    p.update(params or {})
    nodes = []
    edges = []
    if prompt:
        nodes.append({"id": "p1", "op": "prompt", "params": {"text": "a walking cat"}})
        edges.append({"from": "p1", "fromPort": "prompt", "to": "g1", "toPort": "prompt"})
    if image:
        nodes.append({"id": "img", "op": "image", "params": {"url": "https://example.com/a.jpg"}})
        edges.append({"from": "img", "fromPort": "image", "to": "g1", "toPort": "image"})
    nodes.append({"id": "g1", "op": "t2v", "params": p})
    return {"backend": backend, "nodes": nodes, "edges": edges}


spec = OP_SPEC.get("t2v") or {}
check("OP_SPEC 有 t2v", "t2v" in OP_SPEC, str(sorted(OP_SPEC)))
check("t2v outs=video", spec.get("outs") == ["video"], str(spec))
check("t2v required 含 prompt", "prompt" in (spec.get("required") or []), str(spec))
check("t2v required 不含 image", "image" not in (spec.get("required") or []), str(spec))
check("t2v ins 不含 image", "image" not in (spec.get("ins") or []), str(spec))

r = compile_graph(t2v_graph())
pl = r.get("payload") or {}
check("t2v compile ok", r.get("ok") is True, str(r.get("error")))
check("t2v 不改打 i2v", (r.get("stages") or [{}])[0].get("op") == "t2v", str(r.get("stages")))
check("t2v payload.kind=video", pl.get("kind") == "video", str(pl.get("kind")))
check("t2v 无 sourceImage", "sourceImage" not in pl, str(pl.get("sourceImage")))
check("t2v 无 firstFrame", "firstFrame" not in pl, str(pl.get("firstFrame")))
check("t2v 有 prompt", pl.get("prompt") == "a walking cat", str(pl.get("prompt")))
check("t2v duration 透传", pl.get("duration") == 5, str(pl.get("duration")))
check("t2v execute=single", r.get("execute") == "single", str(r.get("execute")))

r_s = compile_graph(t2v_graph(params={"sampler": "euler", "scheduler": "karras"}))
pls = r_s.get("payload") or {}
check("t2v sampler 透传", pls.get("sampler") == "euler", str(pls.get("sampler")))
check("t2v scheduler 透传", pls.get("scheduler") == "karras", str(pls.get("scheduler")))

r_miss = compile_graph(t2v_graph(prompt=False))
check("t2v 缺 prompt 失败", r_miss.get("ok") is False, str(r_miss))
check("t2v 缺 prompt 点名 prompt", "prompt" in str(r_miss.get("error") or ""), str(r_miss.get("error")))

r_img = compile_graph(t2v_graph(image=True))
check("t2v 连 image 口失败", r_img.get("ok") is False, str(r_img))
err_img = str(r_img.get("error") or "")
check("t2v 连 image 不改打 i2v", "i2v" not in err_img.lower() or "禁止改打" in err_img, err_img)
check("t2v 连 image 点名无输入口", "image" in err_img, err_img)

r_bypass = compile_graph(
    t2v_graph(params={"sourceImage": "https://example.com/a.jpg", "firstFrame": "https://example.com/a.jpg"})
)
check("t2v params 塞首帧失败", r_bypass.get("ok") is False, str(r_bypass))
err_b = str(r_bypass.get("error") or "")
check("t2v 首帧旁路禁止改打 i2v", "改打" in err_b or "i2v" in err_b, err_b)
check("t2v 旁路 blocked", r_bypass.get("blocked") is True, str(r_bypass))

r_hf = compile_graph(t2v_graph(backend="huggingface", service=T2V_HF))
check("hf t2v ok（video=True i2v=none）", r_hf.get("ok") is True, str(r_hf.get("error")))
check("hf t2v 无首帧", "sourceImage" not in (r_hf.get("payload") or {}), str(r_hf.get("payload")))

r_novid = compile_graph(t2v_graph(backend="no-such-backend"))
check("无 video 能力后端拒绝 t2v", r_novid.get("ok") is False, str(r_novid))
check("无 video 文案点名文生视频", "文生视频" in str(r_novid.get("error") or "") or "t2v" in str(r_novid.get("error") or ""), str(r_novid.get("error")))

r_i2v = compile_graph(
    {
        "backend": "civitai",
        "nodes": [
            {"id": "p1", "op": "prompt", "params": {"text": "lock"}},
            {"id": "g1", "op": "i2v", "params": {"serviceId": I2V_CIV, "duration": 5}},
        ],
        "edges": [{"from": "p1", "fromPort": "prompt", "to": "g1", "toPort": "prompt"}],
    }
)
check("i2v 无首帧仍失败（回归）", r_i2v.get("ok") is False and r_i2v.get("blocked") is True, str(r_i2v))
check("i2v 无首帧仍点名 image", "image" in str(r_i2v.get("error") or ""), str(r_i2v.get("error")))

print("PASS h4-t2v" if not fails else f"FAIL h4-t2v {len(fails)}: {fails}")
sys.exit(1 if fails else 0)
