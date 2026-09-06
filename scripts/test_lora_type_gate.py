#!/usr/bin/env python3
"""E 门 B1/B2 回归：换模型后 dock 显隐要刷新；撞号的非 LoRA 资源不许入列。
Run: python3 scripts/test_lora_type_gate.py

B1：#service 的 change 只调 applyServiceConstraints，而 loraToggle/paramChrome/seedChrome
    的 hidden 只在 syncParamChrome 里改 —— 换到声明 loras 的模型后开关仍旧不出现。
B2：/api/model-version/<id> 对撞号的裸数字会回 Checkpoint（实测 122359 → Gap_mix），
    前端没有类型校验，checkpoint 会被当 LoRA 发进生成链。
前端白名单必须和 providers/civitai.py 的 _LORA_TYPES 逐字一致，否则 UI 放行、服务端丢弃。
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
    """取出 `  function <name>(` 起、到同缩进 `  }` 为止的整段函数体。"""
    head = "\n  function %s(" % name
    if head not in JS:
        head = "\n  async function %s(" % name
    start = JS.index(head) + 1
    end = JS.index("\n  }\n", start) + 3
    return JS[start:end]


# ---------- B1：换模型的那条链真的会刷 dock 显隐 ----------
body = fn_body("applyServiceConstraints")
ok("syncParamChrome()" in body, "B1 applyServiceConstraints 里调了 syncParamChrome")

sync = fn_body("syncParamChrome")
ok("toggle.hidden = !loraEnabled(n)" in sync, "loraToggle 的显隐仍由 syncParamChrome 负责")
ok("applyModelParamRules()" in sync, "syncParamChrome 仍会刷模型级参数规则（不丢 W2 门控）")

# #service 的 change 回调 → applyServiceConstraints → syncParamChrome，链子接上了
change = JS[JS.index('$("service").dataset.capabilityBound = "1";'):]
change = change[: change.index("\n    });\n") + 8]
ok("applyServiceConstraints()" in change, "#service change 仍调 applyServiceConstraints")

# ---------- B2：类型白名单和服务端逐字一致 ----------
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
ok("loraTypeUsable(draft.type)" in add, "addLora 入列前按 type 拦")
ok(
    add.index("loraTypeUsable") < add.index("resolveLoraAir"),
    "类型校验在 resolveLoraAir 之前，撞号的 checkpoint 不会先去换 air",
)
norm = fn_body("normalizeLoraRow")
ok("type: type," in norm, "normalizeLoraRow 把 /api/model-version/ 的 type 带出来")

# ---------- 谓词真跑一遍，不只是 grep ----------
block = JS[JS.index("  const LORA_TYPES = new Set(["): JS.index("\n  function normalizeLoraRow(")]
cases = [
    ["LORA", True],
    ["LoCon", True],
    ["lycoris", True],
    ["Textual Inversion", True],
    ["DO_RA", True],
    ["", True],           # 拿不到 type 的行（URL / 裸 air）不拦
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

# ---------- 服务端口径复核：122359 这个撞号 id 的真身确实不是 LoRA ----------
ok(not civ._is_lora_resource("Checkpoint", "urn:air:sd1:checkpoint:civitai:96429@122359"), 
   "服务端也认为 122359 的真身 Checkpoint 不是 LoRA 资源")

print("\nall ok")
