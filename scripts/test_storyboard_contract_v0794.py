#!/usr/bin/env python3
"""Static checks for v0794 non-shell UI contracts."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JS = ROOT / "static" / "storyboard.js"
REQ = ROOT / "dalao_original_requirements.md"
SRC = JS.read_text(encoding="utf-8")


def ok(cond, msg):
    if not cond:
        raise AssertionError(msg)


def main() -> int:
    # C8: no flat demo placeholders left in shipped demo assets.
    for name in ("demo-bot.jpg", "demo-work.jpg", "demo-bed.jpg", "demo-bath.jpg"):
        fp = ROOT / "static" / name
        ok(fp.exists() and fp.stat().st_size > 20_000, f"{name} still placeholder-sized")
    ok("LIGHT_PRESET_THUMBS = []" not in SRC, "lighting presets must not render color swatches only")
    ok("fallbackRealThumb" in SRC, "relight/camera orb needs selected image fallback")
    ok('class="sw"' not in SRC, "lighting preset swatches must be replaced by real thumbnails")

    # C3/C9: node class drives model category and UI, first render must land on text backend.
    ok("function selectDefaultBackendForCategory" in SRC, "category-specific backend selector missing")
    ok('selectDefaultBackendForCategory("text")' in SRC, "initial text backend not forced")
    ok("dedupeCatalogItems" in SRC, "model catalog dedupe missing")
    ok('cls.kind === "text"' in SRC and 'setTextDockRefs' in SRC, "text node refs path missing")
    ok("data-textact" in SRC and "生图" not in SRC.split("function setTextDockRefs", 1)[1].split("function", 1)[0], "text dock refs still生图/反推")

    # C6: story推演 has source-like controls and real graph/generate path, not /api/story only.
    for token in ("向后推演", "向前推演", "专业模型", "通用模型", "生成 ◆10"):
        ok(token in SRC, f"story UI missing {token}")
    ok("buildStoryGraph" in SRC, "story graph builder missing")
    ok("generateStoryFrames" in SRC, "story frame generator missing")
    ok("buildGraph → compile → generate → poll" in SRC, "story path must document true pipeline")
    ok('fetch("/api/story"' not in SRC, "story send still calls /api/story directly")
    ok("runCompiledGenerate(" in SRC and "buildStoryFrameGraph" in SRC, "story frames not using compiled generate")

    ok(REQ.exists(), "dalao_original_requirements.md not migrated into repo")
    print("ok v0794-contract")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
