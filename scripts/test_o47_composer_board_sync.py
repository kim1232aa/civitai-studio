#!/usr/bin/env python3
"""o47: Composer board sync — Magao maxRefs board + seed clamp hint + adapt stamp."""
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

def main():
    board = (ROOT / "docs/api-usage/composer-field-board.md").read_text()
    assert "天花板 **3**" in board or "天花板 3" in board
    assert "Edit-2509=3" in board
    js = (ROOT / "static/composer-field-adapt.js").read_text()
    assert 'STAMP = "v0821o47-composer-board-sync"' in js
    assert "mod int32" in js
    assert "maxRefs=" in js
    # html stamp may have moved to a newer tip; adapt file stamp is source of truth for o47
    print("PASS o47_composer_board_sync")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
