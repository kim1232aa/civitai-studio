#!/usr/bin/env python3
"""九宫格拆解契约: catalog 无 grid 模型 -> 拆 N 条子提示词再拼版。

Run: python3 scripts/test_grid_plan.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from providers.nanogpt import GRID_KINDS, _parse_prompt_list, plan_grid

FAILED: list[str] = []


def ok(name, cond, detail=""):
    if cond:
        print(f"ok {name}")
    else:
        FAILED.append(name)
        print(f"FAIL {name} {detail}")


# --- catalog 里确实没有 grid 分类 / 多联出图模型 ---------------------------
cat = json.loads((ROOT / "docs/catalog.json").read_text())
items = cat if isinstance(cat, list) else (cat.get("items") or [])
cats = {it.get("category") for it in items if isinstance(it, dict)}
ok("catalog_has_no_grid_category", "grid" not in cats, sorted(c for c in cats if c))
ok("catalog_size_304", len(items) == 304, len(items))

# --- 四种类型逐字（源站「选择类型」）--------------------------------------
ok("grid_kinds_exact", list(GRID_KINDS) == ["灵感风暴", "故事叙述", "武打分镜", "全景机位"], list(GRID_KINDS))

# --- 参数校验先于 key，错误必须显式 --------------------------------------
ok("grid_requires_model", plan_grid({})[1].get("error", "").find("模型 id") >= 0, plan_grid({}))
ok("grid_requires_text", plan_grid({"model": "chat/x"})[1].get("error", "").find("提示词") >= 0, plan_grid({"model": "chat/x"}))
c, d = plan_grid({"model": "chat/x", "text": "古装女侠", "kind": "不存在"})
ok("grid_rejects_unknown_kind", c == 400 and d.get("allowed") == list(GRID_KINDS), d)
c, d = plan_grid({"model": "chat/x", "text": "x", "count": 99})
ok("grid_rejects_bad_count", c == 400, d)
c, d = plan_grid({"model": "chat/x", "text": "x", "count": 1})
ok("grid_rejects_count_1", c == 400, d)

# --- 子提示词解析：JSON / 围栏 / 编号行 -----------------------------------
p = _parse_prompt_list('```json\n["shot one wide","shot two close","shot three ots"]\n```', 9)
ok("parse_fenced_json", p == ["shot one wide", "shot two close", "shot three ots"], p)
p = _parse_prompt_list('1. first shot wide\n2. second shot close\n3. third shot ots', 2)
ok("parse_numbered_lines_truncates", p == ["first shot wide", "second shot close"], p)
ok("parse_empty_returns_empty", _parse_prompt_list("", 9) == [], _parse_prompt_list("", 9))
p = _parse_prompt_list('["only one"]', 9)
ok("parse_short_does_not_pad", p == ["only one"], p)

# --- 路由已挂 --------------------------------------------------------------
src = (ROOT / "server.py").read_text()
ok("route_api_grid_plan_registered", '"/api/grid/plan"' in src, "")
ok("route_calls_plan_grid", re.search(r"from providers\.nanogpt import plan_grid", src) is not None, "")

print(f"result {'FAILED: ' + ', '.join(FAILED) if FAILED else 'all green'}")
sys.exit(1 if FAILED else 0)
