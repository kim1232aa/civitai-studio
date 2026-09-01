"""Deprecated serve-time UI patch.

Click / hash / storage fixes already live in static/index.html (v0739+).
Keep this module as a no-op identity so run.sh / providers.__init__ still import safely.
"""
from __future__ import annotations


def _patch_v0738(html: str) -> str:
    return html or ""


def _patch_v0739(html: str) -> str:
    return html or ""


def patch_index(html: str) -> str:
    """Identity: do not rewrite HTML at boot."""
    return html or ""


if __name__ == "__main__":
    from pathlib import Path
    target = Path(__file__).resolve().parent / "static" / "index.html"
    raw = target.read_text(encoding="utf-8")
    out = patch_index(raw)
    print("no-op identity", target, "unchanged" if out == raw else "UNEXPECTED CHANGE")
