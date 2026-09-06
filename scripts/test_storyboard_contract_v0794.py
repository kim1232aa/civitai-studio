#!/usr/bin/env python3
"""Static checks for real, non-demo storyboard contracts."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JS = ROOT / "static" / "storyboard.js"
REQ = ROOT / "dalao_original_requirements.md"
SRC = JS.read_text(encoding="utf-8")


def ok(cond, msg):
    if not cond:
        raise AssertionError(msg)


def main() -> int:
    # A-0 authenticity contract: deleted robot/demo wiring must stay deleted.
    for token in ("CHAR_LIB", "DEMO_BOT", "fallbackRealThumb", "loadDemo"):
        ok(token not in SRC, f"forbidden production token remains: {token}")
    ok(
        not re.search(
            r"[\"'](?:/static/)?(?:demo-(?:bot|work|bed|bath)|light-preset-\d+)\.jpg",
            SRC,
        ),
        "production code must not reference frozen demo/preset jpg assets",
    )
    ok("LIGHT_PRESET_THUMBS" not in SRC, "obsolete preset thumbnail table remains")

    # Prompt/story contracts must reach the real graph and model paths.
    for token in (
        'const STORE = "nl-storyboard-v0794"',
        "function promptOf",
        "async function reverseFromImage",
        "function describePrompt",
        "async function generateFromText",
        "function syncPrompt",
        "function moveCardEl",
        "function selectDefaultBackendForCategory",
        "dedupeCatalogItems",
        "data-textact",
        "buildStoryGraph",
        "generateStoryFrames",
        "buildStoryFrameGraph",
        "runCompiledGenerate(",
    ):
        ok(token in SRC, f"real storyboard path missing: {token}")
    ok('fetch("/api/story"' not in SRC, "story must not bypass compiled generation")
    ok(REQ.exists(), "original requirements file is present")

    # Lighting is runtime current-image + filter/swatch preview, not fake files.
    light = SRC[SRC.index("const LIGHT_PRESETS") : SRC.index("const NINE_TYPES")]
    ok(len(re.findall(r"\blabel:\s*\"", light)) == 12, "lighting preset count is not 12")
    for token in (
        "data-light-thumb",
        "data-light-swatch",
        "示意",
        "实际光影由生成模型输出决定",
        "selectedShotImage()",
        "syncLightControls",
        "applyLightPreset",
    ):
        ok(token in SRC, f"runtime lighting contract missing: {token}")

    print("ok v0794-contract")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
