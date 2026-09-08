#!/usr/bin/env python3
"""Offline NanoGPT parameter contracts."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from providers import nanogpt  # noqa: E402


def main() -> int:
    spec = {"supported_parameters": {"resolutions": ["1k", "1024*1536"]}}
    assert nanogpt.pick_resolution(spec, preferred="1k") == "1k"
    assert nanogpt.pick_resolution(spec, preferred="not-a-token") is None

    video_spec = {
        "id": "video-model",
        "category": "video",
        "task": "text-to-video",
        "supported_parameters": {},
    }
    with patch.object(nanogpt, "nano_key", return_value="offline-key"), patch.object(
        nanogpt, "find_spec", return_value=video_spec
    ), patch.object(
        nanogpt, "json_call", side_effect=AssertionError("video POST must be blocked")
    ):
        code, body = nanogpt.NanoGptProvider().generate(
            {"serviceId": "video-model", "prompt": "x", "kind": "video"}
        )
    assert code == 400, (code, body)
    assert "resolutions" in body["error"], body
    print("OK nanogpt-parameters")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
