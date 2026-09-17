#!/usr/bin/env python3
"""o164: closed-loop hard-gate tests.

verify.sh exit 0 is a pack-declaration gate, NOT product Pass.
GOAL.md still records closed-loop = 0. No curl /api/generate.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GOAL = ROOT / ".cursor" / "loops" / "hard-gate-closed-loop" / "GOAL.md"
VERIFY = ROOT / ".cursor" / "loops" / "hard-gate-closed-loop" / "verify.sh"
BASE = ROOT / "docs" / "review-shots" / "closed-loop"


def check(cond, msg):
    if not cond:
        raise AssertionError(msg)


def main() -> int:
    goal = GOAL.read_text(encoding="utf-8")
    check("still **0**" in goal, "GOAL.md must keep product closed-loop = 0")
    check("no curl generate" in goal.lower() or "禁止 curl" in goal, "GOAL forbids curl generate")
    check("No invent Pass" in goal, "GOAL forbids inventing Pass")
    check("HANDOFF" in goal and "≠" in goal, "HANDOFF green ≠ 验收")

    check(VERIFY.is_file(), "verify.sh exists")
    check(BASE.is_dir(), "closed-loop packs dir")

    proc = subprocess.run(
        ["bash", str(VERIFY)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=120,
    )
    out = (proc.stdout or "") + (proc.stderr or "")
    check(proc.returncode == 0, "verify.sh must exit 0 when ≥1 honest pack exists\n" + out[-2000:])
    check("PASS pack:" in out, "verify.sh must print PASS pack")
    check("OK: §3 closed loop" in out, "verify.sh mechanical OK line")

    # Mechanical green is not product Pass.
    check("still **0**" in goal, "product scoreboard remains 0 after verify.sh green")
    check("≠产品验收" in goal or "≠ 验收" in goal or "≠ Pass" in goal, "tip/verify ≠ product Pass")

    # At least one pack must declare the iron gates (not invent yes on seko if no).
    manifests = list(BASE.glob("*/MANIFEST.md"))
    check(manifests, "at least one MANIFEST.md")
    honest_gap = 0
    for m in manifests:
        text = m.read_text(encoding="utf-8", errors="replace")
        if "seko_paired_contrast: no" in text.lower() or "seko_paired_contrast: no" in text:
            honest_gap += 1
        if "Pass=False" in text or "Pass 宣称 | **False**" in text or "判定：Pass=False" in text or "**判定：Pass=False**" in text:
            honest_gap += 1
    # Not required to find one — just must not rewrite GOAL to Pass.
    check("产品 验收 / 闭环 still **0**" in goal or "闭环 still **0**" in goal,
          "do not rewrite GOAL closed-loop to non-zero")

    print("PASS o164_hard_gate_not_product_pass")
    print("note: verify.sh exit 0 ≠ product closed-loop Pass (still 0)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
