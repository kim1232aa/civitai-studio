#!/usr/bin/env python3
"""Offline request contracts, NOT real generation/HTTP/UI acceptance.

python3 -B scripts/test_nanogpt_media_contract.py
Discovery-shaped examples follow public video-models?detailed=true and
images/models. All transport and credential access is replaced.
"""
import copy
import socket
import sys
import urllib.request
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from providers import nanogpt as nano

VIDEO = {
    "id": "bytedance-seedance-2-0",
    "category": "video",
    "capabilities": {"video_generation": True, "text_to_video": True, "image_to_video": True},
    "supported_parameters": {"parameters": {
        "resolution": {"type": "select", "options": [{"value": "720p"}, {"value": "1080p"}]},
        "duration": {"type": "select", "options": [{"value": "5"}, {"value": "10"}, {"value": "15"}]},
        "aspect_ratio": {"type": "select", "options": [{"value": "16:9"}, {"value": "9:16"}]},
        "last_image": {"type": "text", "label": "Last Frame URL (I2V)"},
    }},
}
FRAME = "https://example.invalid/first.png"
TAIL = "https://example.invalid/last.png"
BASE = {"serviceId": VIDEO["id"], "prompt": "pan", "resolution": "720p"}
checks = 0


def check(condition):
    global checks
    assert condition
    checks += 1


def rejects(fn, *args):
    try:
        fn(*args)
    except ValueError:
        check(True)
    else:
        raise AssertionError("expected ValueError")


def main():
    calls = []

    def transport(url, method="GET", **kwargs):
        calls.append({"url": url, "method": method, "body": kwargs.get("body")})
        return 422, {"error": "OFFLINE transport sentinel"}

    no_net = AssertionError("offline check attempted external I/O")
    with patch.object(socket, "socket", side_effect=no_net), \
         patch.object(urllib.request, "urlopen", side_effect=no_net), \
         patch.object(nano, "nano_key", side_effect=no_net), \
         patch.object(nano, "civitai_api_token", side_effect=no_net), \
         patch.object(nano, "_auth", return_value={}), \
         patch.object(nano, "fetch_catalog", return_value=[]), \
         patch.object(nano, "json_call", side_effect=transport):
        check(nano.VID_MODELS.endswith("?detailed=true"))
        original = copy.deepcopy(VIDEO)
        row = nano._row_video(VIDEO)
        check(row["task"] == "text-to-video")
        check(row["supported_parameters"]["resolutions"] == ["720p", "1080p"])
        check(VIDEO == original)  # no mutation of discovery data
        i2v = copy.deepcopy(VIDEO)
        i2v["capabilities"]["text_to_video"] = False
        check(nano._row_video(i2v)["needsFirstFrame"] is True)
        check(nano._row_video(i2v)["task"] == "image-to-video")
        unknown = {**VIDEO, "capabilities": {"video_generation": True}}
        check(nano._row_video(unknown)["task"] == "video")
        rejects(nano._video_body, BASE, unknown)
        rejects(nano._video_body, BASE, i2v)

        t2v = nano._video_body({**BASE, "mode": "text-to-video", "duration": 5}, VIDEO)
        check(t2v == {"model": VIDEO["id"], "prompt": "pan", "mode": "text-to-video",
                      "duration": "5", "resolution": "720p"})
        body = nano._video_body({**BASE, "firstFrame": FRAME, "lastFrame": TAIL}, VIDEO)
        check(body["mode"] == "image-to-video" and body["imageUrl"] == FRAME)
        check(body["last_image"] == TAIL)
        check(not {"lastFrame", "last_frame_url", "image_url", "size"} & body.keys())
        data_frame = "data:image/png;base64,AA=="
        body = nano._video_body({**BASE, "firstFrame": data_frame}, VIDEO)
        check(body["imageDataUrl"] == data_frame and "imageUrl" not in body)
        for extra in (
            {"mode": "text-to-video", "firstFrame": FRAME},
            {"mode": "image-to-video"}, {"mode": "t2v", "op": "i2v"},
            {"mode": []}, {"mode": "video-edit"}, {"videoUrl": FRAME},
            {"prompt": []}, {"negativePrompt": []}, {"prompt": " "}, {"script": "unsupported"},
            {"firstFrame": "/out/unconverted.png"}, {"firstFrame": [FRAME]}, {"images": [{}]},
            {"firstFrame": FRAME, "images": [FRAME, TAIL]},
            {"lastFrame": TAIL}, {"last_frame_url": TAIL}, {"end_image_url": TAIL},
            {"firstFrame": FRAME, "lastFrame": TAIL, "last_image": FRAME},
            {"firstFrame": FRAME, "lastFrame": data_frame},
            {"duration": "999"}, {"aspectRatio": "1:99"},
            {"aspectRatio": "9:16", "aspect_ratio": "16:9"},
            {"resolution": "1280x720"}, {"resolution": ""}, {"resolution": 720},
            {"quantity": 2},
        ):
            rejects(nano._video_body, {**BASE, **extra}, VIDEO)
        no_tail = copy.deepcopy(VIDEO)
        no_tail["supported_parameters"]["parameters"].pop("last_image")
        rejects(nano._video_body, {**BASE, "firstFrame": FRAME, "lastFrame": TAIL}, no_tail)
        # Some official video rows have fixed resolution: no selector, no invented token.
        fixed = copy.deepcopy(VIDEO)
        fixed["supported_parameters"]["parameters"].pop("resolution")
        body = nano._video_body({"prompt": "pan"}, fixed)
        check("resolution" not in body and "size" not in body and "aspect_ratio" not in body)

        image = {"id": "image-contract", "supported_parameters": {
            "resolutions": ["1k"], "max_output_images": 8, "max_images": 1}}
        for n in (1, 4, 8):
            body = nano._image_body({"quantity": n, "resolution": "1k"}, image)
            check(body["n"] == n and body["nImages"] == n)
        check(nano._image_count({"n": 1, "nImages": 8}, image) == 8)
        for raw in (0, -1, 9, 1.5, True, None, "", "x", float("inf"), []):
            rejects(nano._image_count, {"quantity": raw}, image)
        rejects(nano._image_count, {"quantity": 1, "n": 2}, image)
        rejects(nano._image_count, {"quantity": 2}, {})
        range_spec = {"supported_parameters": {"n": {"min": 2, "max": 6}}}
        check(nano._image_count({"n": 6}, range_spec) == 6)
        rejects(nano._image_count, {"n": 1}, range_spec)

        flare = {
            "id": "openai/gpt-image-2.5/flare/edit",
            "name": "GPT Image 2.5 Flare Edit",
            "supported_parameters": {
                "resolutions": ["1024x1024"],
                "max_output_images": 4,
                "max_input_images": 16,
            },
            "capabilities": {"image_generation": True, "image_to_image": True},
        }
        check(nano._row_image({
            "id": flare["id"], "name": flare["name"],
            "capabilities": flare["capabilities"],
            "supported_parameters": flare["supported_parameters"],
        }).get("needsSource") is True)
        rejects(nano._image_body, {"prompt": "淘宝主图", "resolution": "1024x1024"}, flare)
        local = "/out/upload_20260909150943_1.jpg"
        packed = nano._image_body({
            "prompt": "淘宝主图",
            "resolution": "1024x1024",
            "sourceImage": local,
            "images": [local, "/out/upload_20260909150949_1.jpg"],
            "serviceId": flare["id"],
        }, flare)
        check(isinstance(packed.get("input_references"), list) and len(packed["input_references"]) >= 1)
        check(all(str(u).startswith("data:image/") for u in packed["input_references"]))

        flare_t2i = {
            "id": "openai/gpt-image-2.5/flare/text-to-image",
            "name": "GPT Image 2.5 Flare",
            "supported_parameters": {
                "resolutions": ["1024x1024"],
                "max_output_images": 4,
            },
            "capabilities": {"image_generation": True, "image_to_image": False},
        }
        check(nano._image_eats_refs(flare_t2i) is False)
        check(nano._image_eats_refs(flare) is True)
        t2i_ok = nano._image_body({"prompt": "淘宝主图", "resolution": "1024x1024"}, flare_t2i)
        check("input_references" not in t2i_ok)
        rejects(nano._image_body, {
            "prompt": "淘宝主图",
            "resolution": "1024x1024",
            "sourceImage": "https://example.invalid/ref.png",
            "images": ["https://example.invalid/ref.png"],
            "serviceId": flare_t2i["id"],
        }, flare_t2i)

        ref = "https://example.invalid/ref.png"
        i2i_spec = {
            "id": "image-i2i",
            "supported_parameters": {"resolutions": ["1k"], "max_output_images": 4},
            "capabilities": {"image_generation": True, "image_to_image": True},
        }
        no_str = nano._image_body({
            "prompt": "x", "resolution": "1k", "sourceImage": ref, "images": [ref],
        }, i2i_spec)
        check("strength" not in no_str)
        check(no_str.get("strength") != 0.65)
        check(no_str.get("input_references") == [ref])
        with_str = nano._image_body({
            "prompt": "x", "resolution": "1k", "sourceImage": ref, "images": [ref],
            "denoise": 0.4,
        }, i2i_spec)
        check(with_str["strength"] == 0.4)
        user_065 = nano._image_body({
            "prompt": "x", "resolution": "1k", "sourceImage": ref, "images": [ref],
            "strength": 0.65,
        }, i2i_spec)
        check(user_065["strength"] == 0.65)
        for extra in (
            {"strength": None},
            {"denoise": None},
            {"strength": "oops"},
            {"strength": True},
            {"strength": float("inf")},
            {"denoise": 0.3, "strength": 0.9},
        ):
            rejects(nano._image_body, {
                "prompt": "x", "resolution": "1k", "sourceImage": ref, "images": [ref], **extra,
            }, i2i_spec)
        packed_no_default = nano._image_body({
            "prompt": "淘宝主图",
            "resolution": "1024x1024",
            "sourceImage": "https://example.invalid/ref.png",
            "images": ["https://example.invalid/ref.png"],
            "serviceId": flare["id"],
        }, flare)
        check("strength" not in packed_no_default)

        stepped = nano._image_body(
            {"quantity": 1, "resolution": "1k", "steps": 20, "cfgScale": 7.5, "seed": 42}, image
        )
        check(stepped["steps"] == 20 and stepped["num_inference_steps"] == 20)
        check(stepped["guidance_scale"] == 7.5 and stepped["seed"] == 42)
        bare = nano._image_body({"quantity": 1, "resolution": "1k"}, image)
        check("steps" not in bare and "guidance_scale" not in bare and "seed" not in bare)
        for extra in (
            {"steps": "many"}, {"steps": True}, {"steps": 1.5}, {"steps": []},
            {"cfgScale": "high"}, {"cfgScale": True}, {"cfgScale": float("nan")},
            {"seed": 891104780613135}, {"seed": -2}, {"seed": "abc"}, {"seed": True},
        ):
            rejects(nano._image_body, {"quantity": 1, "resolution": "1k", **extra}, image)
        rejects(nano._video_body, {**BASE, "mode": "text-to-video", "seed": 891104780613135}, VIDEO)

        provider = nano.NanoGptProvider()
        code, data = provider._generate_video({**BASE, "mode": "text-to-video"}, VIDEO, VIDEO["id"])
        check(code == 422 and data["error"] == "OFFLINE transport sentinel")
        check(len(calls) == 1 and calls[0]["url"] == nano.GEN_VIDEO)
        check(calls[0]["body"]["mode"] == "text-to-video" and "imageUrl" not in calls[0]["body"])
        calls.clear()
        for payload in ({**BASE, "mode": "text-to-video", "firstFrame": FRAME},
                        {**BASE, "lastFrame": TAIL}):
            code, _ = provider._generate_video(payload, VIDEO, VIDEO["id"])
            check(code == 400)
        code, _ = provider._generate_image({"quantity": 9}, image, image["id"])
        check(code == 400 and not calls)
        code, _ = provider._generate_image({"quantity": 8, "resolution": "1k"}, image, image["id"])
        check(code == 422 and all(call["body"]["nImages"] == 8 for call in calls))
        n_calls = len(calls)
        code, data = provider._generate_image(
            {"quantity": 1, "resolution": "1k", "seed": 891104780613135}, image, image["id"]
        )
        check(code == 400 and "种子" in data["error"] and "seedClamped" not in data)
        check(len(calls) == n_calls)
        code, data = provider._generate_image(
            {"quantity": 1, "resolution": "1k", "steps": "many"}, image, image["id"]
        )
        check(code == 400 and "steps" in data["error"] and len(calls) == n_calls)
        code, data = provider._generate_image({
            "quantity": 1, "resolution": "1k",
            "sourceImage": ref, "images": [ref], "strength": "oops",
        }, i2i_spec, i2i_spec["id"])
        check(code == 400 and "strength" in data["error"] and len(calls) == n_calls)
        code, data = provider._generate_image({
            "quantity": 1, "resolution": "1k",
            "sourceImage": ref, "images": [ref], "strength": None,
        }, i2i_spec, i2i_spec["id"])
        check(code == 400 and "0.65" in data["error"] and len(calls) == n_calls)
        with patch.object(nano, "find_spec", return_value=image):
            code, _ = provider.whatif({"quantity": 9})
            check(code == 400)
    print(f"PASS {checks} offline Nano media assertions; no real generation, HTTP, or UI acceptance")


if __name__ == "__main__":
    main()
