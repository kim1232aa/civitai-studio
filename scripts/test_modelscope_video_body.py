#!/usr/bin/env python3
"""魔搭图生视频 body：官方仍走 /images/generations + image_url；无 duration；有 size 时忽略 aspect_ratio。"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from providers import modelscope as ms  # noqa: E402


def check(cond, msg):
    if not cond:
        raise AssertionError(msg)


def main():
    payload = {
        "kind": "video",
        "task": "image-to-video",
        "serviceId": "Wan-AI/Wan2.1-I2V-14B-720P",
        "prompt": "slow pan",
        "width": 720,
        "height": 1280,
        "aspectRatio": "9:16",
        "image_url": "https://example.invalid/frame.jpg",
    }
    with patch("providers.fal.materialize_fal_media", return_value={"image_urls": ["https://example.invalid/frame.jpg"]}):
        body = ms._image_body(payload, "Wan-AI/Wan2.1-I2V-14B-720P", "modelscope-ai", video=True)
    check(body["model"] == "Wan-AI/Wan2.1-I2V-14B-720P", body)
    check(body["prompt"] == "slow pan", body)
    check(body["size"] == "720x1280", body)
    check("duration" not in body, body)
    check("aspect_ratio" not in body and "aspectRatio" not in body, body)
    check(body["image_url"] == "https://example.invalid/frame.jpg", body)
    check(ms._wants_video(payload, "Wan-AI/Wan2.1-I2V-14B-720P"), "wants video")

    try:
        with patch("providers.fal.materialize_fal_media", return_value={"image_urls": []}):
            ms._image_body({"prompt": "x", "kind": "video"}, "Wan-AI/Wan2.1-I2V-14B-720P", "modelscope-ai", video=True)
        raise AssertionError("i2v without frame must 400")
    except ValueError as exc:
        check("首帧" in str(exc), exc)

    try:
        with patch("providers.fal.materialize_fal_media", return_value={"image_urls": ["https://example.invalid/f.jpg"]}):
            ms._image_body({
                "prompt": "x", "duration": 5, "image_url": "https://example.invalid/f.jpg",
            }, "Wan-AI/Wan2.1-I2V-14B-720P", "modelscope-ai", video=True)
        raise AssertionError("duration must 400")
    except ValueError as exc:
        check("duration" in str(exc), exc)

    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
