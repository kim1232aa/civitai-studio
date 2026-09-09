#!/usr/bin/env python3
"""E 门 B1/B2 回归：换模型后 dock 显隐要刷新；撞号的非 LoRA 资源不许入列。
Run: python3 scripts/test_lora_type_gate.py

B1：#service / #backend 切换必须再跑 syncParamChrome，不能等用户再点一次节点卡。
B2：/api/model-version/<id> 对撞号裸数字会回 Checkpoint（实测 122359 → Gap_mix），
    前端必须按 type 拦，checkpoint 不能进 LoRA 列表。
前端白名单必须和 providers/civitai.py 的 _LORA_TYPES 逐字一致。
全离线，不打网络。
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from providers import civitai as civ  # noqa: E402

JS = (ROOT / "static" / "storyboard.js").read_text(encoding="utf-8")


def ok(cond, msg):
    if not cond:
        raise AssertionError(msg)
    print("ok  -", msg)


def fn_body(name):
    head = "\n  function %s(" % name
    if head not in JS:
        head = "\n  async function %s(" % name
    start = JS.index(head) + 1
    end = JS.index("\n  }\n", start) + 3
    return JS[start:end]


body = fn_body("applyServiceConstraints")
ok("syncParamChrome()" in body, "B1 applyServiceConstraints 里调了 syncParamChrome")

sync = fn_body("syncParamChrome")
ok("syncLoraUi()" in sync, "syncParamChrome 刷新 LoRA 开关")
ok("revalidateLorasForService()" in sync, "换模后重跑 LoRA capability 校验")
ok("syncParamSurface()" in sync, "syncParamChrome 仍会刷参数面")
ok("function catalogItemSupportsLora" in JS, "catalogItemSupportsLora")
ok("function revalidateLorasForService" in JS, "revalidateLorasForService")
ok("当前模型不支持 LoRA" in JS, "unsupported-model LoRA 红字")

ok('applyServiceConstraints();' in JS, "#service/#backend change 调 applyServiceConstraints")
ok("loadCatalog().then(function () { applyServiceConstraints(); })" in JS,
   "目录异步完成后再次 syncParamChrome，不要求用户再点节点")

raw = re.search(r"const LORA_TYPES = new Set\(\[(.*?)\]\);", JS, re.S)
ok(raw is not None, "前端有 LORA_TYPES 白名单")
js_types = set(re.findall(r'"([A-Z]+)"', raw.group(1)))
ok(
    js_types == civ._LORA_TYPES,
    "前端 LORA_TYPES 与 providers/civitai.py _LORA_TYPES 一致："
    "前端多 %s，服务端多 %s" % (sorted(js_types - civ._LORA_TYPES), sorted(civ._LORA_TYPES - js_types)),
)
ok("CHECKPOINT" not in js_types, "Checkpoint 不在白名单里")

add = fn_body("addLora")
ok("loraTypeUsable(draft.type, draft.air)" in add, "addLora 入列前按 type+air 拦")
ok(
    add.index("loraTypeUsable") < add.index("resolveLoraAir"),
    "类型校验在 resolveLoraAir 之前，撞号的 checkpoint 不会先去换 air",
)
ok("function airKind(" in JS, "前端从 AIR 解 kind，缺 type 不 fail-open")
norm = fn_body("normalizeLora")
ok("type: type," in norm, "normalizeLora 把 /api/model-version/ 的 type 带出来")
ok("modelId: modelId," in norm, "normalizeLora 带 modelId 给服务端交叉校验")

block = JS[JS.index("  const LORA_TYPES = new Set(["): JS.index("\n  function loraDisplayName(")]
cases = [
    ["LORA", True],
    ["LoCon", True],
    ["lycoris", True],
    ["Textual Inversion", True],
    ["DO_RA", True],
    ["", True],
    ["Checkpoint", False],
    ["Controlnet", False],
    ["VAE", False],
    ["Upscaler", False],
]
prog = block + "\nconsole.log(JSON.stringify(%s.map(function(c){return loraTypeUsable(c[0])===c[1];})));" % json.dumps(cases)
out = subprocess.run(
    ["node", "-e", prog], capture_output=True, text=True, cwd=str(ROOT)
)
ok(out.returncode == 0, "loraTypeUsable 能在 node 里独立跑：%s" % out.stderr.strip()[-300:])
got = json.loads(out.stdout.strip().splitlines()[-1])
for (value, want), passed in zip(cases, got):
    ok(passed, "loraTypeUsable(%r) == %s" % (value, want))

air_cases = [
    ["", "urn:air:sd1:checkpoint:civitai:96429@122359", False],
    ["", "urn:air:sdxl:lora:civitai:1@2", True],
    ["LORA", "urn:air:sd1:checkpoint:civitai:96429@122359", False],
    ["Checkpoint", "urn:air:sdxl:lora:civitai:1@2", False],
    ["", "", True],
    ["", "https://civitai.com/api/download/models/1", True],
]
prog2 = block + "\nconsole.log(JSON.stringify(%s.map(function(c){return loraTypeUsable(c[0], c[1])===c[2];})));" % json.dumps(air_cases)
out2 = subprocess.run(
    ["node", "-e", prog2], capture_output=True, text=True, cwd=str(ROOT)
)
ok(out2.returncode == 0, "loraTypeUsable(type, air) 能在 node 里独立跑：%s" % out2.stderr.strip()[-300:])
got2 = json.loads(out2.stdout.strip().splitlines()[-1])
for (typ, air, want), passed in zip(air_cases, got2):
    ok(passed, "loraTypeUsable(%r, %r) == %s" % (typ, air, want))

ok(
    not civ._is_lora_resource("Checkpoint", "urn:air:sd1:checkpoint:civitai:96429@122359"),
    "服务端也认为 122359 的真身 Checkpoint 不是 LoRA 资源",
)
ok(
    not civ._is_lora_resource("", "urn:air:sd1:checkpoint:civitai:96429@122359"),
    "缺 type 时 Checkpoint AIR 仍拒绝",
)
ok(
    not civ._is_lora_resource("LORA", "urn:air:sd1:checkpoint:civitai:96429@122359"),
    "Checkpoint AIR 不因 type=LORA 伪装而放行",
)
ok(
    civ._is_lora_resource("", "urn:air:sdxl:lora:civitai:1@2"),
    "缺 type 的 LoRA AIR 仍可走",
)

print("\nall ok")
