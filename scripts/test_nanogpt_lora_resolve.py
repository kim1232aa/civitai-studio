#!/usr/bin/env python3
"""Offline NanoGPT LoRA resolve contracts.

Run: python3 scripts/test_nanogpt_lora_resolve.py

Fail-closed cases (E1):
  >3 LoRAs → lora_too_many
  no direct URL / AIR-only → lora_no_direct_url
  stale B2 without versionId → lora_no_direct_url
Success: each resolved row and outbound body use {path, scale}.
Transport: every socket / urllib / json_call / catalog fetch is replaced.
Never hits Civitai, B2, or nano-gpt.com (the previous live 402 path).
"""
from __future__ import annotations

import socket
import sys
import unittest
import urllib.request
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from providers import nanogpt as nano  # noqa: E402

FAKE_B2 = (
    "https://b2.civitai.com/file/civitai-modelfiles/model/1/x.safetensors"
    "?Authorization=fake_sig&b2ContentDisposition=attachment"
)
DL_API = "https://civitai.com/api/download/models/3231694"
OFFLINE_CIVITAI = "OFFLINE_CIVITAI_TOKEN_DO_NOT_SEND"
OFFLINE_NANO = "OFFLINE_NANO_KEY_DO_NOT_SEND"
LORA_SPEC = {
    "id": "z-image-turbo-lora",
    "supportsLora": True,
    "category": "image",
    "supported_parameters": {"resolutions": ["1k", "1024x1024"]},
}
NO_LORA_SPEC = {
    "id": "z-image-turbo",
    "supportsLora": False,
    "category": "image",
    "supported_parameters": {"resolutions": ["1k"]},
}
VIDEO_LORA_SPEC = {
    "id": "some-video-lora",
    "supportsLora": True,
    "category": "video",
    "task": "text-to-video",
    "capabilities": {"text_to_video": True},
    "supported_parameters": {"resolutions": ["720p"]},
}


def _net_blocked(*_a, **_k):
    raise AssertionError("offline only: refused real upstream")


class NanoLoraResolveOffline(unittest.TestCase):
    def setUp(self):
        self.enterContext(patch.object(socket, "socket", side_effect=_net_blocked))
        self.enterContext(patch.object(urllib.request, "urlopen", side_effect=_net_blocked))
        self.enterContext(patch.object(urllib.request, "build_opener", side_effect=_net_blocked))
        self.head = self.enterContext(
            patch.object(nano, "_head_redirect_location", side_effect=_net_blocked)
        )
        self.json_call = self.enterContext(
            patch.object(nano, "json_call", side_effect=_net_blocked)
        )
        self.enterContext(patch.object(nano, "fetch_catalog", return_value=[]))
        self.enterContext(patch.object(nano, "civitai_api_token", return_value=OFFLINE_CIVITAI))
        self.enterContext(patch.object(nano, "nano_key", return_value=OFFLINE_NANO))
        self.enterContext(patch.object(nano, "save_bytes", side_effect=_net_blocked))
        self.enterContext(patch.object(nano, "save_media_urls", side_effect=_net_blocked))

    def _allow_b2_head(self, location=FAKE_B2):
        self.head.side_effect = None
        self.head.return_value = location
        return self.head

    # --- reject: >3 ---

    def test_more_than_three_loras_rejected_without_head(self):
        rows = [
            {"path": f"https://civitai.com/api/download/models/{i}", "name": f"L{i}"}
            for i in range(4)
        ]
        out, err = nano.resolve_nano_loras({"loras": rows})
        self.assertIsNone(out)
        self.assertEqual(err["code"], "lora_too_many")
        self.assertIn("4", err["error"])
        self.assertEqual(len(err["failed"]), 1)
        self.assertEqual(err["failed"][0]["error"], "超过 3 条")
        self.head.assert_not_called()
        self.json_call.assert_not_called()

    def test_five_loras_also_too_many(self):
        out, err = nano.resolve_nano_loras({
            "loras": [{"name": f"L{i}", "versionId": 1000 + i} for i in range(5)],
        })
        self.assertIsNone(out)
        self.assertEqual(err["code"], "lora_too_many")
        self.assertEqual(len(err["failed"]), 2)
        self.head.assert_not_called()

    def test_generate_more_than_three_never_posts_nano(self):
        with patch.object(nano, "find_spec", return_value=LORA_SPEC):
            code, data = nano.NanoGptProvider().generate({
                "serviceId": "z-image-turbo-lora",
                "prompt": "x",
                "resolution": "1k",
                "loras": [{"versionId": i, "name": f"L{i}"} for i in range(4)],
            })
        self.assertEqual(code, 400)
        self.assertEqual(data["code"], "lora_too_many")
        self.json_call.assert_not_called()

    # --- reject: no direct url ---

    def test_air_only_no_direct_url(self):
        out, err = nano.resolve_nano_loras({
            "loras": [{"air": "urn:air:x:lora:civitai:1@1", "name": "NoUrl"}],
        })
        self.assertIsNone(out)
        self.assertEqual(err["code"], "lora_no_direct_url")
        self.assertIn("无直链", err["error"])
        self.assertEqual(err["failed"][0]["name"], "NoUrl")
        self.head.assert_not_called()

    def test_urn_path_without_version_id_rejected(self):
        out, err = nano.resolve_nano_loras({
            "loras": [{"path": "urn:air:sdxl:lora:civitai:99@99", "name": "UrnOnly"}],
        })
        self.assertIsNone(out)
        self.assertEqual(err["code"], "lora_no_direct_url")
        self.head.assert_not_called()

    def test_empty_path_no_version_rejected(self):
        out, err = nano.resolve_nano_loras({"loras": [{"name": "Blank", "scale": 1}]})
        self.assertIsNone(out)
        self.assertEqual(err["code"], "lora_no_direct_url")
        self.head.assert_not_called()

    def test_invalid_entry_type_rejected(self):
        out, err = nano.resolve_nano_loras({"loras": [12345]})
        self.assertIsNone(out)
        self.assertEqual(err["code"], "lora_no_direct_url")
        self.assertIn("格式无效", err["failed"][0]["error"])
        self.head.assert_not_called()

    def test_mixed_batch_one_bad_fails_all_no_partial(self):
        self._allow_b2_head()
        out, err = nano.resolve_nano_loras({
            "loras": [
                {"versionId": 3231694, "name": "Good", "scale": 0.8},
                {"air": "urn:air:x:lora:civitai:2@2", "name": "Bad"},
            ],
        })
        self.assertIsNone(out)
        self.assertEqual(err["code"], "lora_no_direct_url")
        self.assertIn("Bad", err["error"])
        self.assertTrue(any(f.get("name") == "Bad" for f in err["failed"]))

    def test_head_empty_same_as_civitai_402_fail_closed(self):
        """Live Civitai 402 used to leak out of tests. Empty Location is fail-closed."""
        self._allow_b2_head(location="")
        out, err = nano.resolve_nano_loras({
            "loras": [{"versionId": 3231694, "name": "Paywalled"}],
        })
        self.assertIsNone(out)
        self.assertEqual(err["code"], "lora_no_direct_url")
        self.assertTrue(
            any(
                "B2" in (f.get("error") or "") or "直链" in (f.get("error") or "")
                for f in err["failed"]
            )
        )

    def test_head_returns_download_api_not_b2_fail_closed(self):
        self._allow_b2_head(location=DL_API)
        out, err = nano.resolve_nano_loras({
            "loras": [{"versionId": 3231694, "name": "StillApi"}],
        })
        self.assertIsNone(out)
        self.assertEqual(err["code"], "lora_no_direct_url")
        self.assertTrue(any("未拿到 B2" in (f.get("error") or "") for f in err["failed"]))

    # --- reject: stale B2 missing versionId ---

    def test_stale_b2_without_version_id_rejected(self):
        out, err = nano.resolve_nano_loras({
            "loras": [{"path": FAKE_B2, "name": "StaleB2", "scale": 1.0}],
        })
        self.assertIsNone(out)
        self.assertEqual(err["code"], "lora_no_direct_url")
        blob = err["error"] + " " + " ".join(f.get("error") or "" for f in err["failed"])
        self.assertTrue("B2" in blob or "刷新" in blob or "无直链" in blob, blob)
        self.head.assert_not_called()

    def test_stale_b2_as_downloadurl_without_version_id_rejected(self):
        out, err = nano.resolve_nano_loras({
            "loras": [{"downloadUrl": FAKE_B2, "name": "StaleDl"}],
        })
        self.assertIsNone(out)
        self.assertEqual(err["code"], "lora_no_direct_url")
        self.head.assert_not_called()

    def test_resolve_civitai_b2_url_refuses_b2_entry(self):
        with self.assertRaises(ValueError) as ctx:
            nano.resolve_civitai_b2_url(FAKE_B2)
        self.assertTrue(
            "B2" in str(ctx.exception) or "versionId" in str(ctx.exception),
            ctx.exception,
        )
        self.head.assert_not_called()

    def test_generate_stale_b2_never_posts_nano(self):
        with patch.object(nano, "find_spec", return_value=LORA_SPEC):
            code, data = nano.NanoGptProvider().generate({
                "serviceId": "z-image-turbo-lora",
                "prompt": "x",
                "resolution": "1k",
                "loras": [{"path": FAKE_B2, "name": "StaleB2"}],
            })
        self.assertEqual(code, 400)
        self.assertEqual(data["code"], "lora_no_direct_url")
        self.json_call.assert_not_called()

    # --- success shape {path, scale} ---

    def _assert_success_row(self, row, *, scale, name=None):
        self.assertIsInstance(row, dict)
        self.assertEqual(set(row) >= {"path", "scale"}, True)
        self.assertEqual(row["path"], FAKE_B2)
        self.assertEqual(row["scale"], scale)
        self.assertIn("Authorization=", row["path"])
        if name is not None:
            self.assertEqual(row["name"], name)

    def test_version_id_resolves_to_path_scale(self):
        self._allow_b2_head()
        out, err = nano.resolve_nano_loras({
            "loras": [{"versionId": 3231694, "name": "Asian Mix", "scale": 0.8}],
        })
        self.assertIsNone(err)
        self.assertEqual(len(out), 1)
        self._assert_success_row(out[0], scale=0.8, name="Asian Mix")
        self.assertEqual(out[0]["versionId"], "3231694")
        head_url = self.head.call_args[0][0]
        self.assertIn("civitai.com/api/download/models/3231694", head_url)
        self.assertNotIn("Authorization=", head_url)
        self.assertNotIn(OFFLINE_CIVITAI, head_url)

    def test_exactly_three_all_succeed_with_path_scale(self):
        self._allow_b2_head()
        out, err = nano.resolve_nano_loras({
            "loras": [
                {"versionId": 111, "name": "A", "scale": 0.5},
                {"versionId": 222, "name": "B", "strength": 1.25},
                {"path": DL_API.replace("3231694", "333"), "name": "C"},
            ],
        })
        self.assertIsNone(err)
        self.assertEqual(len(out), 3)
        self.assertEqual([r["scale"] for r in out], [0.5, 1.25, 1.0])
        for row in out:
            self.assertEqual(set(row) >= {"path", "scale"}, True)
            self.assertEqual(row["path"], FAKE_B2)

    def test_stale_b2_with_version_id_reresolves_via_download_api(self):
        self._allow_b2_head()
        out, err = nano.resolve_nano_loras({
            "loras": [{"path": FAKE_B2, "versionId": 3231694, "name": "ReResolve", "scale": 0.7}],
        })
        self.assertIsNone(err)
        self._assert_success_row(out[0], scale=0.7, name="ReResolve")
        self.assertTrue(self.head.called)
        head_url = self.head.call_args[0][0]
        self.assertIn("civitai.com/api/download/models/3231694", head_url)
        self.assertNotIn("Authorization=", head_url)
        self.assertNotIn("b2.civitai.com", head_url)

    def test_hf_owner_repo_is_path_without_head(self):
        out, err = nano.resolve_nano_loras({
            "loras": [{"path": "owner/my-lora", "scale": 0.4, "name": "Hub"}],
        })
        self.assertIsNone(err)
        self.assertEqual(out[0]["path"], "owner/my-lora")
        self.assertEqual(out[0]["scale"], 0.4)
        self.head.assert_not_called()

    def test_direct_non_civitai_http_passthrough_without_head(self):
        url = "https://huggingface.co/owner/my-lora/resolve/main/x.safetensors"
        out, err = nano.resolve_nano_loras({"loras": [{"path": url, "scale": 1.0}]})
        self.assertIsNone(err)
        self.assertEqual(out[0]["path"], url)
        self.assertEqual(out[0]["scale"], 1.0)
        self.head.assert_not_called()

    def test_single_dict_payload_not_list(self):
        self._allow_b2_head()
        out, err = nano.resolve_nano_loras({
            "loras": {"versionId": "3231694", "name": "One", "scale": 1.1},
        })
        self.assertIsNone(err)
        self.assertEqual(len(out), 1)
        self._assert_success_row(out[0], scale=1.1, name="One")

    def test_empty_loras_is_empty_success(self):
        out, err = nano.resolve_nano_loras({"loras": []})
        self.assertEqual(out, [])
        self.assertIsNone(err)
        self.head.assert_not_called()

    def test_image_body_outbound_is_only_path_and_scale(self):
        self._allow_b2_head()
        resolved, err = nano.resolve_nano_loras({
            "loras": [{"versionId": 3231694, "name": "Asian Mix", "scale": 0.8}],
        })
        self.assertIsNone(err)
        body = nano._image_body(
            {"serviceId": "z-image-turbo-lora", "prompt": "x", "loras": resolved, "resolution": "1k"},
            LORA_SPEC,
        )
        self.assertEqual(body["loras"], [{"path": FAKE_B2, "scale": 0.8}])
        self.assertEqual(set(body["loras"][0]), {"path", "scale"})
        self.assertEqual(body["lora_1_url"], FAKE_B2)
        self.assertEqual(body["lora_1_scale"], 0.8)
        self.assertNotIn("lora_2_url", body)

    def test_video_body_outbound_is_only_path_and_scale(self):
        self._allow_b2_head()
        resolved, err = nano.resolve_nano_loras({
            "loras": [{"versionId": 3231694, "scale": 0.55, "name": "V"}],
        })
        self.assertIsNone(err)
        body = nano._video_body(
            {"serviceId": "some-video-lora", "prompt": "pan", "loras": resolved, "resolution": "720p"},
            VIDEO_LORA_SPEC,
        )
        self.assertEqual(body["loras"], [{"path": FAKE_B2, "scale": 0.55}])
        self.assertEqual(set(body["loras"][0]), {"path", "scale"})
        self.assertEqual(body["lora_1_url"], FAKE_B2)
        self.assertEqual(body["lora_1_scale"], 0.55)

    def test_persist_never_keeps_signed_b2(self):
        self._allow_b2_head()
        resolved, err = nano.resolve_nano_loras({
            "loras": [{"versionId": 3231694, "name": "Asian Mix", "scale": 0.8}],
        })
        self.assertIsNone(err)
        safe = nano.sanitize_submitted_for_persist(
            {"loras": [{"path": FAKE_B2, "scale": 0.8}], "lora_1_url": FAKE_B2, "width": 1024},
            resolved,
        )
        self.assertEqual(safe["loras"][0]["path"], DL_API)
        self.assertEqual(safe["lora_1_url"], DL_API)
        self.assertNotIn("Authorization=", safe["loras"][0]["path"])
        self.assertNotIn("width", safe)

    # --- generate wiring, still fake transport ---

    def test_generate_image_posts_path_scale_to_nano_only(self):
        captured = []

        def fake_json(url, method="GET", headers=None, body=None, timeout=None):
            captured.append({"url": url, "method": method, "body": body, "headers": headers})
            return 200, {"data": [{"url": "https://example.invalid/img.png"}]}

        self._allow_b2_head()
        self.json_call.side_effect = fake_json
        with patch.object(nano, "find_spec", return_value=LORA_SPEC), patch.object(
            nano, "_save_result", return_value=[{"url": "/out/x.jpg", "file": "x.jpg"}]
        ):
            code, data = nano.NanoGptProvider().generate({
                "serviceId": "z-image-turbo-lora",
                "prompt": "a cat",
                "resolution": "1k",
                "loras": [{"versionId": 3231694, "name": "Asian Mix", "scale": 0.8}],
            })
        self.assertEqual(code, 200)
        self.assertTrue(captured)
        posted = captured[0]["body"]
        self.assertEqual(posted["loras"], [{"path": FAKE_B2, "scale": 0.8}])
        self.assertEqual(set(posted["loras"][0]), {"path", "scale"})
        self.assertEqual(posted["lora_1_url"], FAKE_B2)
        persist = data["submittedInput"]["loras"][0]["path"]
        self.assertEqual(persist, DL_API)
        self.assertNotIn("Authorization=", persist)
        for call in captured:
            self.assertIn("nano-gpt.com", call["url"])
            self.assertNotIn("civitai.com", call["url"])
            hdrs = call["headers"] or {}
            blob = " ".join(str(v) for v in hdrs.values())
            self.assertNotIn(OFFLINE_CIVITAI, blob)
            self.assertNotIn(OFFLINE_CIVITAI, str(call["body"]))

    def test_generate_video_also_resolves_and_sends_path_scale(self):
        captured = []

        def fake_json(url, method="GET", headers=None, body=None, timeout=None):
            captured.append({"url": url, "body": body})
            return 200, {"requestId": "vid-offline-1", "status": "pending"}

        self._allow_b2_head()
        self.json_call.side_effect = fake_json
        with patch.object(nano, "find_spec", return_value=VIDEO_LORA_SPEC):
            code, data = nano.NanoGptProvider().generate({
                "serviceId": "some-video-lora",
                "prompt": "pan",
                "kind": "video",
                "resolution": "720p",
                "loras": [{"versionId": 3231694, "name": "V", "scale": 0.9}],
            })
        self.assertEqual(code, 200)
        self.assertEqual(captured[0]["body"]["loras"], [{"path": FAKE_B2, "scale": 0.9}])
        self.assertEqual(set(captured[0]["body"]["loras"][0]), {"path", "scale"})
        self.assertIn("nano-gpt.com", captured[0]["url"])
        self.assertNotIn("civitai.com", captured[0]["url"])
        self.assertEqual(data["submittedInput"]["loras"][0]["path"], DL_API)

    def test_generate_unsupported_model_does_not_post(self):
        with patch.object(nano, "find_spec", return_value=NO_LORA_SPEC):
            code, data = nano.NanoGptProvider().generate({
                "serviceId": "z-image-turbo",
                "prompt": "x",
                "resolution": "1k",
                "loras": [{"versionId": 3231694, "name": "X"}],
            })
        self.assertEqual(code, 400)
        self.assertEqual(data["code"], "lora_model_unsupported")
        self.json_call.assert_not_called()
        self.head.assert_not_called()

    def test_key_leak_in_location_fail_closed(self):
        self._allow_b2_head(location="https://evil.example/x?token=" + OFFLINE_CIVITAI)
        with self.assertRaises(ValueError) as ctx:
            nano.resolve_civitai_b2_url(DL_API)
        msg = str(ctx.exception)
        self.assertTrue("token" in msg.lower() or "Key" in msg or "泄露" in msg or "拒绝" in msg)

    def test_question_token_without_b2_auth_fail_closed(self):
        self._allow_b2_head(location="https://cdn.example/file?token=abc")
        with self.assertRaises(ValueError) as ctx:
            nano.resolve_civitai_b2_url(DL_API)
        self.assertIn("token", str(ctx.exception).lower())

    def test_no_real_socket_or_opener_on_success_path(self):
        self._allow_b2_head()
        nano.resolve_nano_loras({"loras": [{"versionId": 3231694, "name": "X"}]})
        # If the production HEAD helper were invoked, setUp's build_opener would raise.
        self.assertTrue(self.head.called)


if __name__ == "__main__":
    r = unittest.main(verbosity=2, exit=False)
    if r.result.wasSuccessful():
        print("OK nanogpt-lora-resolve")
        sys.exit(0)
    sys.exit(1)
