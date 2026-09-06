#!/usr/bin/env python3
"""compile 必须透传节点 params.sampler/scheduler，禁止丢掉、禁止发明默认值。

后端 civitai.build_workflow 已消费这两字段；画布 compile 白名单漏了就会死 UI。
Run: python3 scripts/test_compile_sampler_passthrough.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from providers.civitai import DEFAULTS, SAMPLERS, SCHEDULERS, build_workflow  # noqa: E402
from providers.graph_compile import compile_graph  # noqa: E402

fails = []


def check(name, cond, detail=""):
    if cond:
        print(f"  ok   {name}")
    else:
        fails.append(name)
        print(f"  FAIL {name} {detail}")


KREA2 = DEFAULTS["serviceId"]
SAMP = "euler"
SCHED = "karras"


def t2i_graph(params=None, backend="civitai"):
    p = {"serviceId": KREA2, "resolution": "960x1440"}
    p.update(params or {})
    return {
        "backend": backend,
        "nodes": [
            {"id": "p1", "op": "prompt", "params": {"text": "a cat"}},
            {"id": "g1", "op": "t2i", "params": p},
        ],
        "edges": [
            {"from": "p1", "fromPort": "prompt", "to": "g1", "toPort": "prompt"},
        ],
    }


def i2i_graph(params=None):
    p = {"serviceId": KREA2, "resolution": "960x1440"}
    p.update(params or {})
    return {
        "backend": "civitai",
        "nodes": [
            {"id": "p1", "op": "prompt", "params": {"text": "a cat"}},
            {"id": "img", "op": "image", "params": {"url": "https://example.com/a.jpg"}},
            {"id": "g1", "op": "i2i", "params": p},
        ],
        "edges": [
            {"from": "p1", "fromPort": "prompt", "to": "g1", "toPort": "prompt"},
            {"from": "img", "fromPort": "image", "to": "g1", "toPort": "image"},
        ],
    }


def i2v_graph(params=None):
    p = {
        "serviceId": "video/minimax-h3-comfy/imageToVideo",
        "duration": 5,
        "resolution": "720p",
    }
    p.update(params or {})
    return {
        "backend": "civitai",
        "nodes": [
            {"id": "p1", "op": "prompt", "params": {"text": "camera locked"}},
            {"id": "img", "op": "image", "params": {"url": "https://example.com/a.jpg"}},
            {"id": "g1", "op": "i2v", "params": p},
        ],
        "edges": [
            {"from": "p1", "fromPort": "prompt", "to": "g1", "toPort": "prompt"},
            {"from": "img", "fromPort": "image", "to": "g1", "toPort": "image"},
        ],
    }


check("SAMPLERS 31", len(SAMPLERS) == 31, str(len(SAMPLERS)))
check("SCHEDULERS 7 含 beta", len(SCHEDULERS) == 7 and "beta" in SCHEDULERS, str(SCHEDULERS))
check("DEFAULTS sampler", DEFAULTS["sampler"] == "er_sde")
check("DEFAULTS scheduler", DEFAULTS["scheduler"] == "sgm_uniform")
check("测试用 sampler 在白名单", SAMP in SAMPLERS)
check("测试用 scheduler 在白名单", SCHED in SCHEDULERS)

r = compile_graph(t2i_graph({"sampler": SAMP, "scheduler": SCHED}))
pl = r.get("payload") or {}
check("t2i compile ok", r.get("ok") is True, str(r.get("error")))
check("t2i payload.sampler 原样", pl.get("sampler") == SAMP, str(pl.get("sampler")))
check("t2i payload.scheduler 原样", pl.get("scheduler") == SCHED, str(pl.get("scheduler")))

r0 = compile_graph(t2i_graph())
pl0 = r0.get("payload") or {}
check("无 params 不发明 sampler", "sampler" not in pl0, str(pl0.get("sampler")))
check("无 params 不发明 scheduler", "scheduler" not in pl0, str(pl0.get("scheduler")))
check("不偷塞 DEFAULTS.er_sde", pl0.get("sampler") != DEFAULTS["sampler"] or "sampler" not in pl0, str(pl0))

r_s = compile_graph(t2i_graph({"sampler": "dpmpp_2m"}))
check(
    "只带 sampler 不发明 scheduler",
    r_s.get("payload", {}).get("sampler") == "dpmpp_2m" and "scheduler" not in (r_s.get("payload") or {}),
    str(r_s.get("payload")),
)

r_i = compile_graph(i2i_graph({"sampler": SAMP, "scheduler": SCHED}))
pli = r_i.get("payload") or {}
check("i2i compile ok", r_i.get("ok") is True, str(r_i.get("error")))
check("i2i payload.sampler 原样", pli.get("sampler") == SAMP, str(pli.get("sampler")))
check("i2i payload.scheduler 原样", pli.get("scheduler") == SCHED, str(pli.get("scheduler")))

r_v = compile_graph(i2v_graph({"sampler": SAMP, "scheduler": SCHED}))
plv = r_v.get("payload") or {}
check("i2v compile ok", r_v.get("ok") is True, str(r_v.get("error")))
check("i2v payload.sampler 原样", plv.get("sampler") == SAMP, str(plv.get("sampler")))
check("i2v payload.scheduler 原样", plv.get("scheduler") == SCHED, str(plv.get("scheduler")))

body = build_workflow(pl)
inp = (body.get("steps") or [{}])[0].get("input") or {}
check("civitai t2i input.sampler", inp.get("sampler") == SAMP, str(inp.get("sampler")))
check("civitai t2i input.scheduler", inp.get("scheduler") == SCHED, str(inp.get("scheduler")))

print("PASS compile-sampler" if not fails else f"FAIL compile-sampler {len(fails)}: {fails}")
sys.exit(1 if fails else 0)
