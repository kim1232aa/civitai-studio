#!/usr/bin/env python3
"""九宫格拼版 ↔ 局部摘取几何必须互逆。与 static/storyboard.js nineCellRect 同公式。

Run: python3 scripts/test_nine_cell_rect.py
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JS = (ROOT / "static" / "storyboard.js").read_text(encoding="utf-8")

GAP = 8


def nine_cell_rect(sheet_w, sheet_h, n, index, gap=GAP):
    n = max(1, int(n or 3))
    i = max(0, int(index or 0))
    cell_w = (sheet_w - (n + 1) * gap) / n
    cell_h = (sheet_h - (n + 1) * gap) / n
    col = i % n
    row = i // n
    return {
        "x": gap + col * (cell_w + gap),
        "y": gap + row * (cell_h + gap),
        "w": cell_w,
        "h": cell_h,
    }


def compose_size(n, cell_w, cell_h, gap=GAP):
    return n * cell_w + (n + 1) * gap, n * cell_h + (n + 1) * gap


def main():
    assert "function nineCellRect" in JS
    assert re.search(r"const NINE_SHEET_GAP = 8", JS)
    assert "已摘取左上格" not in JS
    assert "data-ninecell" in JS
    assert "n.gridFrom" in JS

    w, h = compose_size(3, 640, 360)
    assert w == 3 * 640 + 4 * 8
    assert h == 3 * 360 + 4 * 8
    r0 = nine_cell_rect(w, h, 3, 0)
    assert r0 == {"x": 8, "y": 8, "w": 640.0, "h": 360.0}, r0
    r4 = nine_cell_rect(w, h, 3, 4)
    assert r4["x"] == 8 + 640 + 8
    assert r4["y"] == 8 + 360 + 8
    r8 = nine_cell_rect(w, h, 3, 8)
    assert r8["x"] + r8["w"] + 8 == w
    assert r8["y"] + r8["h"] + 8 == h

    rects = [nine_cell_rect(w, h, 3, i) for i in range(9)]
    for i, a in enumerate(rects):
        for j, b in enumerate(rects):
            if i >= j:
                continue
            overlap_x = min(a["x"] + a["w"], b["x"] + b["w"]) - max(a["x"], b["x"])
            overlap_y = min(a["y"] + a["h"], b["y"] + b["h"]) - max(a["y"], b["y"])
            assert overlap_x <= 0 or overlap_y <= 0, (i, j)

    w2, h2 = compose_size(2, 100, 50)
    r3 = nine_cell_rect(w2, h2, 2, 3)
    assert r3["x"] == 8 + 100 + 8
    assert r3["y"] == 8 + 50 + 8
    assert r3["w"] == 100
    assert r3["h"] == 50

    print("ok nine-cell-rect")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
