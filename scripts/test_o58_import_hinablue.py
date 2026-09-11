#!/usr/bin/env python3
"""o58 T8: hinablue generation-data keeps full prompt / LoRA / null strength.

Does not POST /api/generate. Does not treat 134923572 as the only post.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from providers.hinablue_meta import parse_civitai_generation_meta  # noqa: E402

FIXTURE = ROOT / "scripts" / "fixtures" / "hinablue_142373903.json"
FORBIDDEN_ONLY = 134923572


def check(cond, msg):
    if not cond:
        raise AssertionError(msg)


def main() -> int:
    raw = json.loads(FIXTURE.read_text(encoding="utf-8"))
    check(raw.get("id") != FORBIDDEN_ONLY, "must not use fixture 134923572 as the only post")
    parsed = parse_civitai_generation_meta(raw)
    check(parsed["backend"] == "civitai", parsed)
    check(parsed["prompt"] == raw["prompt"], "prompt must not be shortened")
    check(len(parsed["prompt"]) > 400, f"prompt too short {len(parsed['prompt'])}")
    check("SFW" not in parsed["prompt"][:20], "no SFW substitute prefix")
    check(str(parsed["seed"]) == "243138068893831", parsed["seed"])
    check(parsed["width"] == 960 and parsed["height"] == 1440, parsed)
    check(parsed["loras"], "LoRA chips missing")
    chip = parsed["loras"][0]
    check(chip["name"] == "Purple_Graphics_KR2", chip)
    check(chip["strength"] == 1.0, chip)

    null_strength = dict(raw)
    null_strength["resources"] = [{"type": "lora", "name": "Purple_Graphics_KR2", "weight": None}]
    null_strength["prompt"] = raw["prompt"].replace("<lora:Purple_Graphics_KR2:1>", "<lora:Purple_Graphics_KR2>")
    parsed_null = parse_civitai_generation_meta(null_strength)
    check(parsed_null["loras"][0]["strength"] is None, "null strength must stay null, not 1.0")

    tag_only = {
        "id": 142373894,
        "sourceUrl": "https://civitai.red/images/142373894",
        "prompt": "another unused hinablue post <lora:SomeLora>",
        "seed": 1,
        "Size": "512x768",
    }
    tagged = parse_civitai_generation_meta(tag_only)
    check(tagged["sourceId"] != FORBIDDEN_ONLY, tagged)
    check(tagged["width"] == 512 and tagged["height"] == 768, tagged)
    check(tagged["loras"][0]["name"] == "SomeLora", tagged)
    check(tagged["loras"][0]["strength"] is None, "tag without weight stays null")

    print("PASS o58_import_hinablue")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
