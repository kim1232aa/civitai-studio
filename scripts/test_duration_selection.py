#!/usr/bin/env python3
"""Duration select must repair an invalid selection even when options are unchanged."""
from pathlib import Path

SRC = (Path(__file__).resolve().parents[1] / "static" / "storyboard.js").read_text()

# The old implementation guarded repair only with `if (!same)`, so an empty
# selected value with an otherwise identical option list stayed selectedIndex=-1.
assert "if (!same || !inRange(now))" in SRC, (
    "duration repair must cover unchanged options + invalid current value"
)
assert "durSel.value = opts[0]" in SRC
print("duration-selection contract ok")
