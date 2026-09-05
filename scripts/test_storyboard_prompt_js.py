#!/usr/bin/env python3
"""Static checks that storyboard.js actually implements the prompt contract."""
from pathlib import Path

JS = Path(__file__).resolve().parents[1] / "static" / "storyboard.js"
src = JS.read_text(encoding="utf-8")


def ok(cond, msg):
    if not cond:
        raise AssertionError(msg)


def main():
    ok('STORE = "nl-storyboard-v0794"' in src, "STORE must be v0794")
    ok("async function reverseFromImage" in src, "reverseFromImage must exist")
    ok("function describePrompt" in src, "describePrompt must exist")
    ok("function generateFromText" in src, "generateFromText must exist")
    ok("function promptOf" in src, "promptOf must exist")
    ok("textarea" in src and "data-text" in src, "text card must be a live textarea")
    ok("look:" in src and "outfit:" in src and "negative:" in src, "CHAR_LIB bible fields")
    ok("captionFromAsset" in src, "caption path")
    ok("syncPrompt" in src, "text/shot prompt sync")
    ok("moveCardEl" in src, "drag must not wipe textarea")
    ok("fal_fal-ai_flux_schnell_01a05be2" in src, "apple restore reject")
    for title in ("家用机器人", "大白-居家装", "大白-职场装", "扫地机器人", "温馨现代卧室", "现代感洗手间"):
        ok(title in src, title)
    ok(src.count("demo-bot.jpg") >= 1, "distinct demo urls")
    ok("demo-bath.jpg" in src and "demo-work.jpg" in src, "all demo thumbs")
    ok("kind === \"text\"" in src or 'kind === "text"' in src, "text kind")
    print("ok prompt-js-contract")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
