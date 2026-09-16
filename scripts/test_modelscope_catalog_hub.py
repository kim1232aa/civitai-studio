#!/usr/bin/env python3
"""魔搭 catalog: Checkpoint 全量翻页 + AIGC 底模；禁止 OpenAPI page_size=100。"""
from __future__ import annotations

import sys
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from providers import modelscope as ms  # noqa: E402


def _openapi_list(models, total, page_size=50):
    return 200, {"data": {"models": models, "total_count": total, "page_size": page_size}}


class CatalogHub(unittest.TestCase):
    def setUp(self):
        ms._HUB_CACHE.update({"at": 0.0, "items": None, "totals": {}})

    def test_openapi_page_size_is_50_not_100(self):
        self.assertEqual(ms._HUB_PAGE, 50)
        self.assertLessEqual(ms._HUB_PAGE, 50)
        self.assertEqual(ms._HUB_PUT_PAGE, 100)
        self.assertNotEqual(ms._HUB_PAGE, 100)

    def test_put_checkpoint_paginates_all_pages_and_skips_vae(self):
        calls = []

        def fake(url, method="GET", headers=None, body=None, timeout=90):
            calls.append((method, url, body))
            if method == "PUT":
                page = int(body["PageNumber"])
                tag = body["Criterion"][0]["values"][0]
                self.assertEqual(tag, "Checkpoint")
                self.assertEqual(body["PageSize"], 100)
                if page == 1:
                    models = [
                        {
                            "Path": "MAILAND", "Name": "majicflus_v1", "AigcType": "Checkpoint",
                            "SupportInference": "txt2img", "SupportExperience": 1,
                            "ChineseName": "麦橘",
                            "Tasks": [{"Name": "text-to-image-synthesis"}],
                        },
                        {
                            "Path": "skip", "Name": "vae", "AigcType": "VAE",
                            "SupportInference": "txt2img", "SupportExperience": 1,
                            "Tasks": [{"Name": "text-to-image-synthesis"}],
                        },
                    ]
                    return 200, {"Code": 200, "Data": {"Models": models, "TotalCount": 101}}
                if page == 2:
                    models = [
                        {
                            "Path": "Qwen", "Name": "Qwen-Image-Edit", "AigcType": "Checkpoint",
                            "SupportInference": "img2img", "SupportExperience": 1,
                            "ChineseName": "Qwen Edit",
                            "Tasks": [{"Name": "image-to-image"}],
                        },
                    ]
                    return 200, {"Code": 200, "Data": {"Models": models, "TotalCount": 101}}
                self.fail(f"unexpected PUT page {page}")
            if "/muse/predict/unauth/defaultTemplateV2" in url:
                return 200, {"Code": 200, "Data": {"data": {
                    "IMAGE": {"supportSDVersionList": [
                        {
                            "label": "Krea-2",
                            "modelUrl": "modelscope://krea/Krea-2-Turbo?revision=master",
                            "model_id": {"path": "krea/Krea-2-Turbo", "Name": "Krea-2-Turbo"},
                        }
                    ]},
                    "VIDEO": {"supportSDVersionList": []},
                }}}
            if "openapi/v1/models?" in url and "filter.task=" in url:
                task = parse_qs(urlsplit(url).query)["filter.task"][0]
                size = parse_qs(urlsplit(url).query)["page_size"][0]
                self.assertEqual(size, "1")
                totals = {
                    "text-to-image-synthesis": 95181,
                    "image-to-image": 836,
                    "text-to-video-synthesis": 3090,
                    "image-to-video": 567,
                }
                return _openapi_list([], totals[task], page_size=1)
            self.fail(f"unexpected {method} {url}")

        with patch.object(ms, "json_call", side_effect=fake):
            rows, totals = ms.fetch_hub()
        ids = {row["id"] for row in rows}
        self.assertIn("MAILAND/majicflus_v1", ids)
        self.assertIn("Qwen/Qwen-Image-Edit", ids)
        self.assertIn("krea/Krea-2-Turbo", ids)
        self.assertNotIn("skip/vae", ids)
        self.assertEqual(totals["aigcCheckpoint"], 101)
        self.assertTrue(totals["complete"])
        self.assertEqual(totals["pageSizeOpenAPI"], 50)
        put_pages = sorted(body["PageNumber"] for method, url, body in calls if method == "PUT")
        self.assertEqual(put_pages, [1, 2])
        edit = next(row for row in rows if row["id"] == "Qwen/Qwen-Image-Edit")
        self.assertEqual(edit["task"], "image-to-image")
        self.assertTrue(edit["needsSource"])
        self.assertEqual(edit["callability"], "generatable")
        t2i = next(row for row in rows if row["id"] == "MAILAND/majicflus_v1")
        self.assertEqual(t2i["task"], "text-to-image")
        self.assertEqual(t2i["callability"], "generatable")

    def test_search_uses_openapi_page_size_50_and_stops_at_three_pages(self):
        calls = []

        def fake(url, method="GET", headers=None, body=None, timeout=90):
            calls.append(url)
            if method != "GET":
                self.fail(method)
            query = parse_qs(urlsplit(url).query)
            if "page_size" in query:
                self.assertEqual(query["page_size"][0], "50")
                page = int(query["page_number"][0])
                return _openapi_list(
                    [{"id": f"org/m{page}", "tasks": ["text-to-image-synthesis"]}],
                    400,
                    page_size=50,
                )
            return 200, {"data": {}}

        with patch.object(ms, "json_call", side_effect=fake):
            rows, totals = ms.fetch_hub_search("krea")
        self.assertEqual(len(rows), 3)
        self.assertEqual(totals["searchPages"], 3)
        self.assertEqual(totals["search"], 400)
        self.assertTrue(all("page_size=50" in url for url in calls if "page_size=" in url))
        self.assertFalse(any("page_size=100" in url for url in calls))

    def test_put_failure_marks_incomplete_not_silent_success(self):
        def fake(url, method="GET", headers=None, body=None, timeout=90):
            if method == "PUT":
                return 400, {"Code": 400, "Message": "invalid page_size parameter, cannot exceed 50", "error": "bad"}
            if "/muse/predict/" in url:
                return 200, {"Code": 200, "Data": {"data": {"IMAGE": {"supportSDVersionList": []}, "VIDEO": {"supportSDVersionList": []}}}}
            if "filter.task=" in url:
                return _openapi_list([], 95181, page_size=1)
            return 200, {"data": {}}

        with patch.object(ms, "json_call", side_effect=fake):
            rows, totals = ms.fetch_hub()
        self.assertFalse(totals["complete"])
        self.assertTrue(totals.get("aigcCheckpointError"))
        self.assertEqual(rows, [])

    def test_catalog_pin_fallback_sets_error_when_hub_empty(self):
        def fake(*args, **kwargs):
            return 400, {"error": "down"}

        with patch.object(ms, "json_call", side_effect=fake):
            with patch.object(ms, "load_disk", return_value=[
                {"id": "krea/Krea-2-Raw", "name": "Krea", "category": "image", "task": "text-to-image", "tags": ["t2i"]},
            ]):
                body = ms.ModelScopeProvider("cn").catalog("", "image", "")
        self.assertEqual(body["count"], 1)
        self.assertEqual(body["items"][0]["id"], "krea/Krea-2-Raw")
        self.assertTrue(body["hubTotals"]["pinFallback"])
        self.assertFalse(body["hubTotals"]["complete"])
        self.assertIn("pin", body["hubTotals"]["error"])
        self.assertIs(body["items"][0]["capabilities"]["image_to_image"], False)

    def test_catalog_promotes_disk_pins_to_front(self):
        hub_rows = [
            {"id": "org/other", "name": "Other", "category": "image", "task": "text-to-image", "tags": ["t2i"]},
            {"id": "krea/Krea-2-Turbo", "name": "Buried Turbo", "category": "image", "task": "text-to-image", "tags": ["t2i"]},
        ]
        with patch.object(ms, "fetch_hub", return_value=(hub_rows, {"complete": True})):
            with patch.object(ms, "load_disk", return_value=[
                {"id": "krea/Krea-2-Turbo", "name": "Krea 2 Turbo", "category": "image", "task": "text-to-image", "tags": ["t2i"]},
                {"id": "MusePublic/Qwen-Image-Edit", "name": "Qwen Edit", "category": "image", "task": "image-to-image", "tags": ["i2i"], "needsSource": True},
                {"id": "Wan-AI/Wan2.1-I2V-14B-720P", "name": "Wan I2V", "category": "video", "task": "image-to-video", "tags": ["i2v"], "needsFirstFrame": True},
            ]):
                body = ms.ModelScopeProvider("cn").catalog("", "image", "", page=1, pageSize=50)
                video = ms.ModelScopeProvider("cn").catalog("", "video", "", page=1, pageSize=50)
        ids = [x["id"] for x in body["items"]]
        self.assertEqual(ids[0], "krea/Krea-2-Turbo")
        self.assertIn("MusePublic/Qwen-Image-Edit", ids[:2])
        # i2v=none: Hub video pins must not appear as sendable catalog rows
        self.assertEqual(video["items"], [])
        self.assertNotIn("Wan-AI/Wan2.1-I2V-14B-720P", ids)

    def test_catalog_filters_video_when_i2v_none(self):
        """ms-video-honest: Magao catalog must not advertise sendable i2v/t2v."""
        hub_rows = [
            {"id": "krea/krea-realtime-video", "name": "Krea RT", "category": "video", "task": "text-to-video", "tags": ["t2v"]},
            {"id": "Wan-AI/Wan2.1-I2V-14B-720P", "name": "Wan I2V", "category": "video", "task": "image-to-video", "tags": ["i2v"]},
            {"id": "Tongyi-MAI/Z-Image-Turbo", "name": "Z Turbo", "category": "image", "task": "text-to-image", "tags": ["t2i"]},
        ]
        with patch.object(ms, "fetch_hub", return_value=(hub_rows, {"complete": True})):
            with patch.object(ms, "load_disk", return_value=[]):
                all_body = ms.ModelScopeProvider("ai").catalog("", "", "", page=1, pageSize=50)
                vid_body = ms.ModelScopeProvider("ai").catalog("", "video", "", page=1, pageSize=50)
        ids = [x["id"] for x in all_body["items"]]
        self.assertIn("Tongyi-MAI/Z-Image-Turbo", ids)
        self.assertNotIn("krea/krea-realtime-video", ids)
        self.assertNotIn("Wan-AI/Wan2.1-I2V-14B-720P", ids)
        self.assertEqual(vid_body["items"], [])
        self.assertEqual(vid_body["total"], 0)
        cats = ms.ModelScopeProvider("ai").categories()
        self.assertNotIn("video", cats)
        # overlay must not stamp supportsI2v=True (fake sendable)
        from providers.capabilities import overlay_modelscope_catalog_item
        stamped = overlay_modelscope_catalog_item({
            "id": "Wan-AI/Wan2.1-I2V-14B-720P",
            "task": "image-to-video",
            "tags": ["i2v"],
            "category": "video",
        })
        self.assertIs(stamped.get("supportsI2v"), False)
        self.assertTrue(stamped.get("unsendable"))
        self.assertEqual(stamped.get("unsendableLabel"), "不可发")

    def test_catalog_search_uses_warm_cache_not_hub(self):
        ms._HUB_CACHE.update({
            "at": time.time(),
            "items": [
                {"id": "krea/Krea-2-Turbo", "name": "Krea", "category": "image", "task": "text-to-image", "tags": ["t2i"]},
                {"id": "org/other", "name": "Other", "category": "image", "task": "text-to-image", "tags": ["t2i"]},
            ],
            "totals": {"complete": True},
        })
        with patch.object(ms, "fetch_hub", side_effect=AssertionError("must not search hub when cache is warm")):
            body = ms.ModelScopeProvider("cn").catalog("krea/Krea-2-Turbo", "image", "")
        self.assertEqual(body["items"][0]["id"], "krea/Krea-2-Turbo")


if __name__ == "__main__":
    unittest.main(verbosity=2)
