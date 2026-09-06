#!/usr/bin/env python3
"""Static checks that storyboard.js implements the real prompt/tool contract."""
from __future__ import annotations

import re
from pathlib import Path

SRC = (Path(__file__).resolve().parents[1] / "static" / "storyboard.js").read_text(
    encoding="utf-8"
)


def ok(cond, msg):
    if not cond:
        raise AssertionError(msg)


def main() -> int:
    # Keep the test aligned with the A-0 removal decision: no fake seed/fallback path.
    for token in ("CHAR_LIB", "DEMO_BOT", "fallbackRealThumb", "loadDemo"):
        ok(token not in SRC, f"forbidden production token remains: {token}")
    ok(
        not re.search(
            r"[\"'](?:/static/)?(?:demo-(?:bot|work|bed|bath)|light-preset-\d+)\.jpg",
            SRC,
        ),
        "prompt surface must not reference frozen jpg assets",
    )
    ok("LIGHT_PRESET_THUMBS" not in SRC, "obsolete preset thumbnail table remains")

    for token in (
        'const STORE = "nl-storyboard-v0794"',
        "async function reverseFromImage",
        "function describePrompt",
        "async function generateFromText",
        "function promptOf",
        "function syncPrompt",
        "function moveCardEl",
        "captionFromAsset",
        "textarea",
        "data-text",
        "kind === \"text\"",
        "function mapSekoYawToFal",
        "function mapSekoPitchToFal",
        "function mapSekoZoomToFal",
        "category=cameraAngle",
        'op: "camera-angle"',
        "function applyLightPreset",
        "function syncLightControls",
        "function selectedShotImage",
        "data-light-thumb",
        "data-light-swatch",
        "打光效果",
        "STORY_PLAN_ENDPOINT",
        "buildStoryFrameGraph",
        "planNineGridPrompts",
        "composeNineGridSheet",
        "buildNineCellGraph",
        "function deleteNode",
        "localStorage.setItem(",
        "localStorage.getItem(STORE)",
    ):
        ok(token in SRC, f"prompt/tool contract missing: {token}")

    for label in ("鱼眼镜头", "反打镜头", "荷兰角镜头"):
        ok(label in SRC, f"camera preset missing: {label}")
    for label in ("四宫格", "九宫格", "十六宫格", "二十五宫格"):
        ok(label in SRC, f"split option missing: {label}")
    for label in ("伦勃朗光", "光学焦散", "布达佩斯大饭店"):
        ok(label in SRC, f"lighting preset missing: {label}")

    light = SRC[SRC.index("const LIGHT_PRESETS") : SRC.index("const NINE_TYPES")]
    ok(len(re.findall(r"\blabel:\s*\"", light)) == 12, "lighting preset count is not 12")
    for token in ("示意", "实际光影由生成模型输出决定", "selectedShotImage()"):
        ok(token in SRC, f"lighting preview authenticity contract missing: {token}")

    ok("category=text" in SRC, "story catalog must use text models")
    ok("无可用模型" in SRC, "empty catalog must be explicit")
    ok("不会用默认假值生成" in SRC, "blank service must be rejected")
    ok("生图必须显式选择图片模型" in SRC, "image generation must require a real model")
    ok('option value="">默认模型' not in SRC, "fake default model option remains")
    ok('serviceId = "fal-ai/iclight-v2"' not in SRC, "hardcoded relight id remains")
    ok("function rejectVideoTool" in SRC, "unsupported video tools need explicit refusal")
    ok("function isNineGridNode" in SRC, "nine-grid classifier missing")
    ok("function extractNineGridCell" in SRC, "nine-grid extraction missing")
    ok("不足不静默补空" in SRC, "planner must not silently pad empty prompts")

    print("ok prompt-js-contract")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
