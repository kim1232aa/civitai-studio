#!/usr/bin/env python3
"""Regression: disconnect-edge must clear lastCompile + outBox and ignore stale ok:true.

Mirrors the graphEpoch / compileSeq guard in static/cloud-nodes.html so an in-flight
compile cannot re-enable Generate after removeEdge / 「断开」 / 「断 prompt 边」.

Also: staged/multiStep compile ok must KEEP Generate disabled (compile ≠ green light).
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "static" / "cloud-nodes.html").read_text(encoding="utf-8")


def assert_source_guards() -> None:
    required = [
        "let graphEpoch = 0",
        "let compileSeq = 0",
        "let lastCompileEpoch = -1",
        "function invalidateCompile(",
        "outBox",
        "box.textContent = ''",
        "epochAtStart !== graphEpoch || seq !== compileSeq",
        "stale compile ignored",
        "invalidateCompile(DISCONNECT_MSG)",
        "DISCONNECT_MSG",
        "lastCompileEpoch === graphEpoch",
        "function syncGenEnabled(",
        "function isStagedCompile(",
        "isStagedCompile(lastCompile)",
        "execute === 'staged'",
        "step runner",
        "className = 'info'",
    ]
    for needle in required:
        assert needle in HTML, f"missing guard in cloud-nodes.html: {needle!r}"
    # All disconnect entry points go through removeEdge → invalidateCompile
    assert "removeEdge(i)" in HTML
    assert "btnBreakPrompt" in HTML
    assert HTML.count("invalidateCompile(") >= 3  # def + removeEdge + backend/serviceId
    assert "EDGE_STORE_KEY" in HTML and "sessionStorage" in HTML
    assert "DISCONNECT_MSG" in HTML
    assert "已断开一条边 · 校验红 · 生成灰" in HTML
    # second break click must reuse DISCONNECT_MSG (not muted "边已不在")
    assert "image 边已不在" not in HTML
    assert "prompt 边已不在" not in HTML
    # syncGenEnabled must not enable on ok alone — staged stays grey
    assert "!isStagedCompile(lastCompile)" in HTML or "&& !isStagedCompile(lastCompile)" in HTML


def is_staged_compile(j: dict | None) -> bool:
    return bool(j and (j.get("multiStep") or j.get("execute") == "staged"))


class FakeUI:
    """Minimal stand-in for the race-relevant UI state."""

    def __init__(self) -> None:
        self.lastCompile = None
        self.graphEpoch = 0
        self.compileSeq = 0
        self.lastCompileEpoch = -1
        self.btnGen_disabled = True
        self.outBox = "prior compile json"
        self.dockMsg = ""
        self.dockClass = "muted"

    def sync_gen_enabled(self) -> None:
        ready = bool(
            self.lastCompile
            and self.lastCompile.get("ok")
            and self.lastCompileEpoch == self.graphEpoch
            and not is_staged_compile(self.lastCompile)
        )
        self.btnGen_disabled = not ready

    def invalidate_compile(self, reason: str = "") -> None:
        self.graphEpoch += 1
        self.lastCompile = None
        self.lastCompileEpoch = -1
        self.btnGen_disabled = True
        self.outBox = ""
        self.dockMsg = reason or "图已变更 · 请重新校验"
        self.dockClass = "warn"

    def apply_compile_response(self, epoch_at_start: int, seq: int, j: dict) -> dict | None:
        if epoch_at_start != self.graphEpoch or seq != self.compileSeq:
            return {"ok": False, "stale": True, "blocked": True, "error": "stale compile ignored"}
        self.lastCompile = j
        self.lastCompileEpoch = epoch_at_start
        self.outBox = str(j)
        if j.get("ok"):
            if is_staged_compile(j):
                n = len(j.get("stages") or [])
                self.dockMsg = f"编译通过 · 多步链 {n} stages · 需 step runner"
                self.dockClass = "info"
            else:
                self.dockClass = "ok"
            self.sync_gen_enabled()
        else:
            self.dockClass = "warn"
            self.btnGen_disabled = True
        return j


def test_stale_ok_after_disconnect() -> None:
    ui = FakeUI()
    # Start validate (in flight)
    epoch_at_start = ui.graphEpoch
    seq = ui.compileSeq = ui.compileSeq + 1
    # User disconnects edge while request is in flight
    ui.invalidate_compile("已断开一条边 · 校验红 · 生成灰")
    assert ui.lastCompile is None
    assert ui.outBox == ""
    assert ui.btnGen_disabled is True
    assert ui.dockClass == "warn"
    epoch_after = ui.graphEpoch
    assert epoch_after == epoch_at_start + 1
    # Stale ok:true arrives — must NOT revive Generate / outBox / lastCompile
    applied = ui.apply_compile_response(epoch_at_start, seq, {"ok": True, "payload": {"x": 1}})
    assert applied and applied.get("stale") is True
    assert ui.lastCompile is None
    assert ui.outBox == ""
    assert ui.btnGen_disabled is True
    assert ui.dockClass == "warn"


def test_fresh_compile_enables() -> None:
    ui = FakeUI()
    ui.invalidate_compile("disconnect")  # blocked
    epoch_at_start = ui.graphEpoch
    seq = ui.compileSeq = ui.compileSeq + 1
    applied = ui.apply_compile_response(epoch_at_start, seq, {"ok": True, "payload": {}, "execute": "single", "multiStep": False})
    assert applied and applied.get("ok") is True
    assert ui.btnGen_disabled is False
    assert ui.lastCompileEpoch == ui.graphEpoch
    assert ui.dockClass == "ok"


def test_staged_compile_keeps_gen_disabled() -> None:
    """Compile ok for staged/multiStep must NOT green-light Generate."""
    ui = FakeUI()
    epoch_at_start = ui.graphEpoch
    seq = ui.compileSeq = ui.compileSeq + 1
    j = {
        "ok": True,
        "execute": "staged",
        "multiStep": True,
        "stages": [{"id": "g"}, {"id": "v"}],
        "payload": {"sourceImage": {"__stageOut__": "g"}},
        "note": "多步链…",
    }
    applied = ui.apply_compile_response(epoch_at_start, seq, j)
    assert applied and applied.get("ok") is True
    assert ui.btnGen_disabled is True, "staged ok must keep Generate disabled"
    assert ui.dockClass == "info", "staged dock must not be green ok"
    assert "step runner" in ui.dockMsg
    # syncGenEnabled alone must not flip to enabled
    ui.sync_gen_enabled()
    assert ui.btnGen_disabled is True


def main() -> int:
    assert_source_guards()
    test_stale_ok_after_disconnect()
    test_fresh_compile_enables()
    test_staged_compile_keeps_gen_disabled()
    print("ok: cloud-nodes disconnect-edge race guards + staged gen gate")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
