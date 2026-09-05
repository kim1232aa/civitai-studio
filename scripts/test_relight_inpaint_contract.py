#!/usr/bin/env python3
"""前后端契约交叉测试：消除笔 params.maskUrl、打光方向大小写 / 色温 / 亮度 / 12 预设。

三测里的结构断言测不到这两处 —— 它们是「前端写 A、后端读 B」的错口。
Run: python3 scripts/test_relight_inpaint_contract.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from providers.graph_compile import compile_graph
from providers.fal import LIGHT_PRESETS, build_fal_input, build_iclight_lighting

FAILED: list[str] = []


def ok(name, cond, detail=""):
    if cond:
        print(f"ok {name}")
    else:
        FAILED.append(name)
        print(f"FAIL {name} {detail}")


def edit_graph(op, params, image_url="/out/bot.jpg", service="fal-ai/iclight-v2"):
    p = dict(params)
    p["serviceId"] = service
    return {
        "backend": "fal",
        "nodes": [
            {"id": "a-bot", "op": "image", "params": {"url": image_url}},
            {"id": "n1", "op": op, "params": p},
        ],
        "edges": [{"from": "a-bot", "fromPort": "image", "to": "n1", "toPort": "image"}],
    }


# --- 消除笔：单节点 + params.maskUrl（拍板契约） ---------------------------
MASK_URL = "/out/mask-1.png"
DATA_MASK = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUg=="

r = compile_graph(edit_graph("inpaint", {"maskUrl": MASK_URL}, service="fal-ai/object-removal/mask"))
ok("inpaint_single_node_maskUrl_compiles", r.get("ok") is True, r)
ok("inpaint_payload_carries_maskUrl", (r.get("payload") or {}).get("maskUrl") == MASK_URL, r.get("payload"))

r = compile_graph(edit_graph("inpaint", {"maskUrl": DATA_MASK}, service="fal-ai/object-removal/mask"))
ok("inpaint_dataurl_mask_compiles", r.get("ok") is True, r)
ok("inpaint_dataurl_passthrough", (r.get("payload") or {}).get("maskUrl") == DATA_MASK, r.get("payload"))

r = compile_graph(edit_graph("inpaint", {}, service="fal-ai/object-removal/mask"))
ok("inpaint_no_mask_blocked", r.get("ok") is False and r.get("blocked") is True, r)
ok("inpaint_no_mask_names_maskUrl", "maskUrl" in str(r.get("error", "")), r.get("error"))

# 旧 op:mask 图仍能编译（回退口，不是主路径）
legacy = {
    "backend": "fal",
    "nodes": [
        {"id": "a-bot", "op": "image", "params": {"url": "/out/bot.jpg"}},
        {"id": "m1", "op": "mask", "params": {"url": MASK_URL}},
        {"id": "n1", "op": "inpaint", "params": {"serviceId": "fal-ai/object-removal/mask"}},
    ],
    "edges": [
        {"from": "a-bot", "fromPort": "image", "to": "n1", "toPort": "image"},
        {"from": "m1", "fromPort": "mask", "to": "n1", "toPort": "mask"},
    ],
}
r = compile_graph(legacy)
ok("inpaint_legacy_mask_node_still_compiles", r.get("ok") is True, r)


# --- 打光：方向大小写 / front-back 不静默近似 -------------------------------
r = compile_graph(edit_graph("relight", {"lightDirection": "left", "brightness": 50, "colorTemperature": 5000}))
ok("relight_compiles", r.get("ok") is True, r)
pl = r.get("payload") or {}
ok("relight_keeps_colorTemperature", pl.get("colorTemperature") == 5000, pl)
ok("relight_keeps_brightness", pl.get("brightness") == 50, pl)

inp = build_fal_input({**pl, "sourceImage": "/out/bot.jpg"})
ok("relight_lowercase_left_becomes_Left", inp.get("initial_latent") == "Left", inp)
ok("relight_kelvin_lands_in_prompt", "5000K" in inp.get("prompt", ""), inp.get("prompt"))
ok("relight_brightness_lands_in_prompt", "brightness 50%" in inp.get("prompt", ""), inp.get("prompt"))

for d, enum in (("right", "Right"), ("top", "Top"), ("bottom", "Bottom")):
    lat, _ = build_iclight_lighting({"lightDirection": d})
    ok(f"relight_dir_{d}_maps_{enum}", lat == enum, lat)

for d, word in (("front", "front"), ("back", "behind")):
    payload = {"lightDirection": d}
    lat, prompt = build_iclight_lighting(payload)
    ok(f"relight_{d}_no_fake_latent", lat is None, lat)
    ok(f"relight_{d}_described_in_prompt", word in prompt, prompt)
    ok(f"relight_{d}_marked_unsupported", any(d in u for u in payload.get("_unsupported", [])), payload)

# 空描述不得再送 "" 给 iclight
inp = build_fal_input({"serviceId": "fal-ai/iclight-v2", "sourceImage": "/out/bot.jpg", "lightDirection": "top"})
ok("relight_empty_desc_has_prompt", bool(inp.get("prompt", "").strip()), inp)

# --- 12 预设逐字 ------------------------------------------------------------
EXPECTED = [
    "伦勃朗光", "黄金时刻", "蓝调时刻", "暖调光斑", "过曝胶片", "教父暗影",
    "布达佩斯大饭店", "沙丘救赎", "商业蝴蝶光", "产品聚光", "香槟金高光", "光学焦散",
]
ok("light_presets_count_12", len(LIGHT_PRESETS) == 12, len(LIGHT_PRESETS))
ok("light_presets_exact_order", list(LIGHT_PRESETS) == EXPECTED, list(LIGHT_PRESETS))
lat, prompt = build_iclight_lighting({"lightPreset": "伦勃朗光", "lightDirection": "left"})
ok("light_preset_lands_in_prompt", "Rembrandt" in prompt, prompt)

print(f"result {'FAILED: ' + ', '.join(FAILED) if FAILED else 'all green'}")
sys.exit(1 if FAILED else 0)
