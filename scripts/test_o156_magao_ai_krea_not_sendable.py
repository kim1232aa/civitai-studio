#!/usr/bin/env python3
"""o156: Magao AI must not advertise/send krea Turbo/Raw — AI Infer rejects (Model not exists).

CN keeps them. Never silent-swap AI→CN. Mirror video-filter honesty.
"""
from __future__ import annotations

import sys
import time
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from providers import modelscope as ms  # noqa: E402


KREA_TURBO = "krea/Krea-2-Turbo"
KREA_RAW = "krea/Krea-2-Raw"
KREA_VIDEO = "krea/krea-realtime-video"
TONGYI = "Tongyi-MAI/Z-Image-Turbo"


class O156MagaoAiKreaNotSendable(unittest.TestCase):
    def setUp(self):
        ms._HUB_CACHE.update({"at": 0.0, "items": None, "totals": {}})
        with ms._HUB_LOCK:
            ms._HUB_BG["thread"] = None

    def tearDown(self):
        th = ms._HUB_BG.get("thread")
        if th is not None:
            th.join(timeout=2.0)

    def test_helpers_classify_krea_image_not_video(self):
        self.assertTrue(ms._is_ai_unsendable_krea_image_mid(KREA_TURBO))
        self.assertTrue(ms._is_ai_unsendable_krea_image_mid(KREA_RAW))
        self.assertFalse(ms._is_ai_unsendable_krea_image_mid(KREA_VIDEO))
        self.assertFalse(ms._is_ai_unsendable_krea_image_mid(TONGYI))
        self.assertTrue(
            ms._is_ai_unsendable_krea_image_row(
                {"id": KREA_TURBO, "category": "image", "task": "text-to-image", "tags": ["t2i"]}
            )
        )
        self.assertFalse(
            ms._is_ai_unsendable_krea_image_row(
                {"id": KREA_VIDEO, "category": "video", "task": "text-to-video", "tags": ["t2v"]}
            )
        )

    def test_filter_only_when_modelscope_ai(self):
        rows = [
            {"id": KREA_TURBO, "name": "Turbo", "category": "image", "task": "text-to-image", "tags": ["t2i"]},
            {"id": KREA_RAW, "name": "Raw", "category": "image", "task": "text-to-image", "tags": ["t2i"]},
            {"id": TONGYI, "name": "Z", "category": "image", "task": "text-to-image", "tags": ["t2i"]},
        ]
        ai = ms._filter_unsendable_ai_krea(rows, "modelscope-ai")
        cn = ms._filter_unsendable_ai_krea(rows, "modelscope-cn")
        self.assertEqual([x["id"] for x in ai], [TONGYI])
        self.assertEqual([x["id"] for x in cn], [KREA_TURBO, KREA_RAW, TONGYI])

    def test_catalog_ai_drops_krea_cn_keeps(self):
        hub_rows = [
            {"id": KREA_TURBO, "name": "Turbo", "category": "image", "task": "text-to-image", "tags": ["t2i"]},
            {"id": KREA_RAW, "name": "Raw", "category": "image", "task": "text-to-image", "tags": ["t2i"]},
            {"id": TONGYI, "name": "Z", "category": "image", "task": "text-to-image", "tags": ["t2i"]},
        ]
        pins = [
            {"id": KREA_TURBO, "name": "Krea 2 Turbo", "category": "image", "task": "text-to-image", "tags": ["t2i"]},
            {"id": KREA_RAW, "name": "Krea 2 Raw", "category": "image", "task": "text-to-image", "tags": ["t2i"]},
            {"id": TONGYI, "name": "Z-Image Turbo", "category": "image", "task": "text-to-image", "tags": ["t2i"]},
        ]
        ms._HUB_CACHE.update({"at": time.time(), "items": hub_rows, "totals": {"complete": True}})
        with patch.object(ms, "fetch_hub", side_effect=AssertionError("warm cache")):
            with patch.object(ms, "load_disk", return_value=pins):
                ai_body = ms.ModelScopeProvider("ai").catalog("", "image", "", page=1, pageSize=50)
                cn_body = ms.ModelScopeProvider("cn").catalog("", "image", "", page=1, pageSize=50)
        ai_ids = [x["id"] for x in ai_body["items"]]
        cn_ids = [x["id"] for x in cn_body["items"]]
        self.assertNotIn(KREA_TURBO, ai_ids)
        self.assertNotIn(KREA_RAW, ai_ids)
        self.assertIn(TONGYI, ai_ids)
        self.assertIn(KREA_TURBO, cn_ids)
        self.assertIn(KREA_RAW, cn_ids)
        self.assertIn(TONGYI, cn_ids)

    def test_generate_ai_rejects_krea_clear_message(self):
        prov = ms.ModelScopeProvider("ai")
        with patch.object(prov, "_reach_error", return_value=None), patch.object(prov, "_key", return_value="tok"):
            code, data = prov.generate({
                "serviceId": KREA_TURBO,
                "prompt": "a film still",
            })
        self.assertEqual(code, 400)
        err = str((data or {}).get("error") or "")
        self.assertIn(KREA_TURBO, err)
        self.assertTrue(
            "Model not exists" in err or "不支持" in err,
            f"clear reject message missing: {err!r}",
        )
        self.assertIn("不会改走", err)
        self.assertEqual(data.get("backend"), "modelscope-ai")
        # Must not invent a substitute model or rewrite house
        self.assertNotIn("submittedInput", data or {})
        self.assertIsNone((data or {}).get("id"))

    def test_generate_ai_rejects_krea_raw(self):
        prov = ms.ModelScopeProvider("ai")
        with patch.object(prov, "_reach_error", return_value=None), patch.object(prov, "_key", return_value="tok"):
            code, data = prov.generate({"serviceId": KREA_RAW, "prompt": "x"})
        self.assertEqual(code, 400)
        self.assertIn(KREA_RAW, str(data.get("error") or ""))

    def test_generate_cn_does_not_preempt_krea(self):
        """CN path must not hit the AI-only krea gate (mock json_call so no network)."""
        prov = ms.ModelScopeProvider("cn")
        called = {"n": 0}

        def fake_json_call(url, method="GET", headers=None, body=None, timeout=60):
            called["n"] += 1
            return 200, {"task_id": "cn-krea-task", "data": {"task_id": "cn-krea-task"}}

        with patch.object(prov, "_reach_error", return_value=None), patch.object(prov, "_key", return_value="tok"):
            with patch.object(ms, "json_call", side_effect=fake_json_call):
                code, data = prov.generate({"serviceId": KREA_TURBO, "prompt": "cn ok"})
        self.assertEqual(called["n"], 1, "CN must reach Infer, not pre-reject like AI")
        self.assertLess(code, 400)
        self.assertIn("modelscope-cn|", str(data.get("id") or ""))

    def test_stamp_present(self):
        html = (ROOT / "static" / "storyboard.html").read_text()
        js = (ROOT / "static" / "storyboard.js").read_text()
        self.assertIn("v0822o156-magao-ai-krea-not-sendable", html)
        self.assertIn("storyboard.js?v=o156magaoaikrea", html)
        self.assertIn("v0822o156-magao-ai-krea-not-sendable", js)


if __name__ == "__main__":
    unittest.main(verbosity=2)
