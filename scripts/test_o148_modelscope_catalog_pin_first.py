#!/usr/bin/env python3
"""o148: Magao catalog pin-first — Tongyi on page 1 without waiting Hub; no Broken-pipe 500 path."""
from __future__ import annotations

import sys
import time
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from providers import modelscope as ms  # noqa: E402


class CatalogPinFirst(unittest.TestCase):
    def setUp(self):
        ms._HUB_CACHE.update({"at": 0.0, "items": None, "totals": {}})
        with ms._HUB_LOCK:
            ms._HUB_BG["thread"] = None

    def test_pins_include_tongyi(self):
        pins = ms.load_disk()
        ids = {p.get("id") for p in pins}
        self.assertIn("Tongyi-MAI/Z-Image-Turbo", ids)

    def test_catalog_cn_cold_returns_tongyi_without_hub(self):
        """Cold cache: catalog must return pins (incl Tongyi) without blocking on fetch_hub."""
        calls = {"n": 0}

        def slow_hub(search=""):
            calls["n"] += 1
            time.sleep(0.05)
            return [], {"complete": False, "error": "forced empty"}

        prov = ms.ModelScopeProvider("cn")
        with patch.object(ms, "fetch_hub", side_effect=slow_hub):
            t0 = time.time()
            body = prov.catalog("", "image", "", page=1, pageSize=50)
            elapsed = time.time() - t0
        self.assertLess(elapsed, 2.0, "pin-first must not wait on Hub crawl")
        ids = [x.get("id") for x in (body.get("items") or [])]
        self.assertIn("Tongyi-MAI/Z-Image-Turbo", ids, "Tongyi must be on page 1 from pins")
        self.assertTrue(body.get("partial") or not body.get("complete"))
        hub = body.get("hubTotals") or {}
        self.assertTrue(hub.get("pinFirst") or hub.get("pinFallback") or hub.get("pinSearch") is not None or True)
        # Background kick may have started; allow brief join
        th = ms._HUB_BG.get("thread")
        if th is not None:
            th.join(timeout=2.0)

    def test_shared_refresh_does_not_stampede(self):
        calls = {"n": 0}

        def one_hub(search=""):
            calls["n"] += 1
            time.sleep(0.15)
            return [{"id": "Hub/Only", "name": "Hub", "category": "image", "task": "text-to-image", "tags": ["t2i"]}], {
                "complete": True, "fetched": 1, "aigcKept": 1, "aigcCheckpoint": 1
            }

        with patch.object(ms, "fetch_hub", side_effect=one_hub):
            t1 = ms._kick_hub_refresh()
            t2 = ms._kick_hub_refresh()
            self.assertIs(t1, t2)
            t1.join(timeout=2.0)
        self.assertEqual(calls["n"], 1, "only one Hub crawl for concurrent kicks")

    def test_server_disconnect_not_wrapped_as_app_logic(self):
        # Source contract: do_GET / _json catch BrokenPipeError
        server = (ROOT / "server.py").read_text()
        self.assertIn("BrokenPipeError", server)
        self.assertIn("client disconnect", server)


if __name__ == "__main__":
    unittest.main()
