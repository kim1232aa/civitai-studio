#!/usr/bin/env python3
"""Offline HF catalog boundary regressions; no Hub or inference traffic."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from providers import huggingface as hf

NEXT = (
    "https://huggingface.co/api/models?inference_provider=all"
    "&pipeline_tag=text-to-image&limit=50&cursor=page2"
)
HUB_ROW = {
    "id": "org/hub-one",
    "pipeline_tag": "text-to-image",
    "inferenceProviderMapping": [
        {"provider": "fal-ai", "status": "live", "providerId": "fal-ai/x", "task": "text-to-image"},
    ],
}


def _reset_cache():
    hf._HF_CATALOG_CACHE.update(at=0.0, key=None, items=None, stats={})
    hf._HF_NEXT_BY_KEY.clear()


class HFCatalogTests(unittest.TestCase):
    def setUp(self):
        _reset_cache()
        self.enterContext(patch("socket.socket", side_effect=AssertionError("offline only")))
        self.enterContext(patch("socket.getaddrinfo", side_effect=AssertionError("offline only")))
        self.enterContext(patch.object(hf, "json_call", side_effect=AssertionError("unexpected json_call")))
        self.calls = []

        def one_page(url):
            self.calls.append(url)
            if "cursor=" in url:
                raise AssertionError("request-path catalog must not follow Link rel=next")
            return 200, [dict(HUB_ROW)], NEXT

        self.list_page = self.enterContext(patch.object(hf, "_hf_list_page", side_effect=one_page))

    def test_empty_catalog_is_one_hub_page_with_krea_pin(self):
        body = hf.HuggingFaceProvider().catalog("", "image", "")
        self.assertEqual(len(self.calls), 1)
        query = parse_qs(urlsplit(self.calls[0]).query)
        self.assertEqual(query.get("inference_provider"), ["all"])
        self.assertEqual(query.get("pipeline_tag"), ["text-to-image"])
        self.assertEqual(query.get("limit"), ["50"])
        self.assertNotEqual(query.get("limit"), ["1000"])
        ids = [x["id"] for x in body["items"]]
        self.assertIn("krea/Krea-2-Turbo", ids)
        self.assertIn("org/hub-one", ids)
        self.assertLessEqual(len(body["items"]), 50 + 20)
        self.assertTrue(body["hasMore"])
        self.assertEqual(body["nextPage"], 2)
        self.assertFalse(body["complete"])
        self.assertTrue(body["partial"])
        self.assertEqual(body["page"], 1)
        self.assertEqual(body["pageSize"], 50)
        self.assertEqual(body["backend"], "huggingface")
        self.assertIn("hasKey", body)
        self.assertEqual(body["count"], len(body["items"]))
        self.assertEqual(body["total"], len(body["items"]))
        self.assertTrue(all(x.get("category") == "image" for x in body["items"]))

    def test_empty_catalog_uses_ttl_cache(self):
        hf.HuggingFaceProvider().catalog("", "image", "")
        hf.HuggingFaceProvider().catalog("", "image", "")
        self.assertEqual(len(self.calls), 1)

    def test_video_category_requests_official_t2v_filter(self):
        hf.HuggingFaceProvider().catalog("", "video", "")
        self.assertEqual(len(self.calls), 1)
        query = parse_qs(urlsplit(self.calls[0]).query)
        self.assertEqual(query.get("pipeline_tag"), ["text-to-video"])
        self.assertEqual(query.get("inference_provider"), ["all"])

    def test_search_is_one_page_plus_pins(self):
        body = hf.HuggingFaceProvider().catalog("krea", "image", "")
        self.assertEqual(len(self.calls), 1)
        query = parse_qs(urlsplit(self.calls[0]).query)
        self.assertEqual(query.get("search"), ["krea"])
        self.assertEqual(query.get("inference_provider"), ["all"])
        self.assertEqual(query.get("limit"), ["50"])
        self.assertNotIn("pipeline_tag", query)
        ids = [x["id"] for x in body["items"]]
        self.assertIn("krea/Krea-2-Turbo", ids)
        self.assertTrue(body["hasMore"])
        self.assertEqual(body["nextPage"], 2)

    def test_page_two_uses_stored_cursor_not_a_walk(self):
        hf.HuggingFaceProvider().catalog("", "image", "")
        self.assertEqual(len(self.calls), 1)

        def page_two(url):
            self.calls.append(url)
            self.assertIn("cursor=page2", url)
            return 200, [{
                "id": "org/hub-two",
                "pipeline_tag": "text-to-image",
                "inferenceProviderMapping": [
                    {"provider": "nscale", "status": "live", "providerId": "org/two", "task": "text-to-image"},
                ],
            }], None

        self.list_page.side_effect = page_two
        body = hf.HuggingFaceProvider().catalog("", "image", "", page=2)
        self.assertEqual(len(self.calls), 2)
        ids = [x["id"] for x in body["items"]]
        self.assertIn("krea/Krea-2-Turbo", ids)
        self.assertIn("org/hub-two", ids)
        self.assertNotIn("org/hub-one", ids)
        self.assertFalse(body["hasMore"])
        self.assertIsNone(body["nextPage"])
        self.assertTrue(body["complete"])
        self.assertFalse(body["partial"])

    def test_page_two_without_cursor_does_not_walk_hub(self):
        body = hf.HuggingFaceProvider().catalog("", "image", "", page=2)
        self.assertEqual(self.calls, [])
        self.assertIn("krea/Krea-2-Turbo", [x["id"] for x in body["items"]])
        self.assertTrue(body["partial"])
        self.assertFalse(body["complete"])
        self.assertEqual(body["hubCoverage"].get("retryPage"), 2)

    def test_page_validation_rejects_without_network(self):
        for page in (0, -1, True, "x", 1.5):
            with self.subTest(page=page):
                with self.assertRaises(ValueError):
                    hf.HuggingFaceProvider().catalog("", "image", "", page=page)
                self.assertEqual(self.calls, [])
        with self.assertRaises(ValueError):
            hf.HuggingFaceProvider().catalog("", "image", "", pageSize=51)
        self.assertEqual(self.calls, [])

    def test_list_mapping_array_does_not_crash_and_keeps_channels(self):
        row = hf._hf_row("org/hub-one", "hub-one", "text-to-image", raw=HUB_ROW)
        self.assertIn("fal-ai", row["parameterCapabilities"]["channels"])
        self.assertEqual(row["parameterCapabilities"]["channels"]["fal-ai"]["status"], "live")

    def test_hub_failure_keeps_pins_and_is_partial(self):
        def fail(url):
            self.calls.append(url)
            return 503, {"error": "temporary"}, None

        self.list_page.side_effect = fail
        body = hf.HuggingFaceProvider().catalog("", "image", "")
        self.assertTrue(body["items"])
        self.assertIn("krea/Krea-2-Turbo", [x["id"] for x in body["items"]])
        self.assertTrue(body["partial"])
        self.assertFalse(body["complete"])
        self.assertTrue(body["hubCoverage"]["errors"])
        hf.HuggingFaceProvider().catalog("", "image", "")
        self.assertEqual(len(self.calls), 2, "failed first page must not be cached as success")


if __name__ == "__main__":
    unittest.main(verbosity=2)
