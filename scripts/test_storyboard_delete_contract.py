#!/usr/bin/env python3
"""Regression contract checks for storyboard edge and group deletion."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JS = (ROOT / "static" / "storyboard.js").read_text(encoding="utf-8")
HTML = (ROOT / "static" / "storyboard.html").read_text(encoding="utf-8")


def require(text: str, needle: str, message: str) -> None:
    if needle not in text:
        raise AssertionError(message)


def main() -> int:
    require(HTML, "svg.wires path.wire-hit", "wire hit target CSS is missing")
    require(HTML, "pointer-events:stroke", "wire hit target must receive pointer events")
    require(JS, "selectedEdge: null", "edge selection state is missing")
    require(JS, 'class=\"wire-hit\"', "drawWires must render edge hit targets")
    require(JS, 'data-edge-from=\"', "wire hit targets need a stable source id")
    require(JS, 'data-edge-to=\"', "wire hit targets need a stable destination id")
    require(JS, "function selectEdge(from, to)", "wire selection handler is missing")
    require(JS, "function deleteEdge(from, to)", "single-edge deletion handler is missing")
    require(JS, "deleteEdge(state.selectedEdge.from, state.selectedEdge.to)", "Delete must remove a selected edge")
    require(JS, "targetEdge: targetEdge", "context menu must retain the selected edge")
    require(JS, "deleteEdge(point.targetEdge.from, point.targetEdge.to)", "context menu must delete a selected edge")
    require(JS, 'if (node.kind !== "group" || !Array.isArray(node.memberIds)) continue;', "group deletion must traverse members")
    require(JS, "removedIds.add(member.id)", "group deletion must include member nodes")
    require(JS, "!removedIds.has(n.id)", "group deletion must remove all selected member nodes")
    require(JS, "function ungroup()", "users need the separate keep-members ungroup action")
    print("ok storyboard-delete-contract")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
