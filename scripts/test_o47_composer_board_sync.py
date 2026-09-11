#!/usr/bin/env python3
"""o47/o56: Composer board — Magao maxRefs 3 + official seed gates."""
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

def main():
    board = (ROOT / "docs/api-usage/composer-field-board.md").read_text()
    assert "天花板 **3**" in board or "天花板 3" in board
    assert "Edit-2509=3" in board
    js = (ROOT / "static/composer-field-adapt.js").read_text()
    assert 'STAMP = "v0821o56-gate-honesty"' in js
    assert "禁止 mod int32" in js
    assert "reject[-1,2147483647]" in js
    assert "_hasI2vInput" in js
    assert "maxRefs=" in js
    assert "needsClamp" not in js
    print("PASS o47_composer_board_sync")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
