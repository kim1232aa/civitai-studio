#!/usr/bin/env python3
"""Regression: disconnect-edge must clear lastCompile and ignore stale ok:true.

Mirrors the epoch / lastEpoch guard in static/cloud-nodes.html so an in-flight
compile cannot re-enable the run button after the graph changes (edge removed,
node removed, params edited, undo, clear, backend switch).

Also: staged/multiStep compile ok runs through the step runner
(nextRunnableStage + hasUnresolvedStageOut) — never a blind whole-chain go.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "static" / "cloud-nodes.html").read_text(encoding="utf-8")


def assert_source_guards() -> None:
    required = [
        # invalidation core: bump epoch, drop lastCompile, grey the run button
        "function invalidate(reason)",
        "epoch += 1",
        "lastCompile = null",
        "lastEpoch = -1",
        'setGenState(true, "运行此步")',
        # litegraph fires onConnectionChange on edge removal → invalidate
        'graph.onConnectionChange = () => { snapshot(); invalidate("连线已变"); }',
        'graph.onNodeRemoved = () => { snapshot(); invalidate("已删节点"); }',
        # stale compile response can never drive generate()
        "lastEpoch !== epoch",
        # staged chains go through the step runner with an upstream-media gate
        "nextRunnableStage",
        "hasUnresolvedStageOut",
        "不能偷配方台图",
        # run button copy distinguishes whole-run vs next-step
        "运行下一步 · ",
        # edge/ui state persistence survives reload
        "sessionStorage",
    ]
    for needle in required:
        assert needle in HTML, f"missing guard in cloud-nodes.html: {needle!r}"
    # Every mutation entry point invalidates the compile
    assert HTML.count("invalidate(") >= 6  # def + connection/node/param/undo/clear/backend
    # generate() hard-gates on a FRESH successful compile
    assert "if (!lastCompile || !lastCompile.ok || lastEpoch !== epoch) return;" in HTML


def is_staged_compile(j: dict | None) -> bool:
    return bool(j and (j.get("multiStep") or j.get("execute") == "staged"))


class FakeUI:
    """Minimal stand-in for the race-relevant UI state (current epoch design)."""

    def __init__(self) -> None:
        self.lastCompile = None
        self.epoch = 0
        self.lastEpoch = -1
        self.btn_disabled = True
        self.btn_text = "运行此步"
        self.dockMsg = ""
        self.dockClass = "muted"

    def invalidate(self, reason: str = "") -> None:
        self.epoch += 1
        self.lastCompile = None
        self.lastEpoch = -1
        self.btn_disabled = True
        self.btn_text = "运行此步"
        self.dockMsg = reason or "图已变更 · 请重新校验"
        self.dockClass = "warn"

    def apply_compile_response(self, epoch_at_start: int, j: dict) -> dict | None:
        # stale guard mirrors generate(): response from an old epoch is dropped
        if epoch_at_start != self.epoch:
            return {"ok": False, "stale": True, "blocked": True, "error": "stale compile ignored"}
        self.lastCompile = j
        self.lastEpoch = epoch_at_start
        if not j.get("ok"):
            self.dockClass = "warn"
            self.btn_disabled = True
            return j
        if is_staged_compile(j):
            # staged ok → step runner owns execution; button runs NEXT step only
            self.btn_disabled = False
            self.btn_text = "运行下一步"
            self.dockClass = "info"
        else:
            self.btn_disabled = False
            self.btn_text = "运行此步"
            self.dockClass = "ok"
        return j

    def generate(self) -> dict | None:
        # hard gate, mirrors cloud-nodes.html generate()
        if not self.lastCompile or not self.lastCompile.get("ok") or self.lastEpoch != self.epoch:
            return None
        return self.lastCompile


def test_stale_ok_after_disconnect() -> None:
    ui = FakeUI()
    # Start validate (in flight)
    epoch_at_start = ui.epoch
    # User disconnects edge while request is in flight
    ui.invalidate("连线已变")
    assert ui.lastCompile is None
    assert ui.btn_disabled is True
    assert ui.dockClass == "warn"
    assert ui.epoch == epoch_at_start + 1
    # Stale ok:true arrives — must NOT revive the run button / lastCompile
    applied = ui.apply_compile_response(epoch_at_start, {"ok": True, "payload": {"x": 1}})
    assert applied and applied.get("stale") is True
    assert ui.lastCompile is None
    assert ui.btn_disabled is True
    assert ui.dockClass == "warn"
    assert ui.generate() is None


def test_fresh_compile_enables() -> None:
    ui = FakeUI()
    ui.invalidate("连线已变")  # blocked
    epoch_at_start = ui.epoch
    applied = ui.apply_compile_response(epoch_at_start, {"ok": True, "payload": {}, "execute": "single", "multiStep": False})
    assert applied and applied.get("ok") is True
    assert ui.btn_disabled is False
    assert ui.btn_text == "运行此步"
    assert ui.lastEpoch == ui.epoch
    assert ui.dockClass == "ok"
    assert ui.generate() is not None


def test_staged_compile_runs_via_step_runner() -> None:
    """Staged/multiStep compile ok must route through the step runner, not whole-chain go."""
    ui = FakeUI()
    epoch_at_start = ui.epoch
    j = {
        "ok": True,
        "execute": "staged",
        "multiStep": True,
        "stages": [{"id": "g"}, {"id": "v"}],
        "payload": {"sourceImage": {"__stageOut__": "g"}},
        "note": "多步链…",
    }
    applied = ui.apply_compile_response(epoch_at_start, j)
    assert applied and applied.get("ok") is True
    assert ui.btn_disabled is False
    assert ui.btn_text == "运行下一步", "staged ok runs next step only (step runner)"
    assert ui.dockClass == "info", "staged dock must not be green ok"
    # source-level: staged execution is gated on upstream stage media
    assert "hasUnresolvedStageOut" in HTML
    assert "nextRunnableStage" in HTML


def main() -> int:
    assert_source_guards()
    test_stale_ok_after_disconnect()
    test_fresh_compile_enables()
    test_staged_compile_runs_via_step_runner()
    print("ok: cloud-nodes disconnect-edge race guards + staged step-runner gate")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
