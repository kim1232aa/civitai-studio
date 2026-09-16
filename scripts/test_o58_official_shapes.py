#!/usr/bin/env python3
"""o58: official outbound shapes for six houses.

Does not POST /api/generate. Does not claim page-up Pass.
Sources: docs/api-usage/OFFICIAL-SOURCES.md
"""
from __future__ import annotations

import os
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


class CivitaiRecipeLoRA(unittest.TestCase):
    def test_klein_comfy_map(self):
        from providers.civitai_lora_shape import official_lora_payload, lora_shape_for_recipe

        self.assertEqual(lora_shape_for_recipe("comfy", "krea2", "krea2", "createImage"), "map")
        payload = official_lora_payload(
            [{"air": "urn:air:krea2:lora:civitai:1@2", "strength": 0.8}],
            engine="comfy",
            model="krea2",
            ecosystem="krea2",
        )
        self.assertEqual(payload, {"urn:air:krea2:lora:civitai:1@2": 0.8})

    def test_dev_wan_hunyuan_array(self):
        from providers.civitai_lora_shape import official_lora_payload

        dev = official_lora_payload(
            [{"air": "urn:air:flux2:lora:civitai:1@2", "strength": 0.5}],
            engine="flux2",
            model="dev",
        )
        self.assertEqual(dev, [{"air": "urn:air:flux2:lora:civitai:1@2", "strength": 0.5}])
        wan = official_lora_payload(
            [{"air": "urn:air:wan:lora:civitai:3@4", "strength": 0.7}],
            engine="wan",
            operation="createImage",
        )
        self.assertIsInstance(wan, list)
        hun = official_lora_payload(
            [{"air": "urn:air:hy:lora:civitai:5@6", "strength": 0.3}],
            engine="hunyuan",
        )
        self.assertIsInstance(hun, list)

    def test_fal_krea_rejects(self):
        from providers.civitai_lora_shape import official_lora_payload

        with self.assertRaises(ValueError):
            official_lora_payload(
                [{"air": "urn:air:krea2:lora:civitai:1@2", "strength": 0.8}],
                engine="fal",
                model="krea2",
            )


class ModelScopeSeed(unittest.TestCase):
    def test_omit_minus_one(self):
        from providers.modelscope_seed import official_seed_outbound, strip_unofficial_seed

        self.assertIsNone(official_seed_outbound(-1))
        self.assertIsNone(official_seed_outbound("random"))
        self.assertEqual(official_seed_outbound(42), 42)
        self.assertNotIn("seed", strip_unofficial_seed({"prompt": "a", "seed": -1}))

    def test_omit_over_int32_no_wrap(self):
        # o149: over-int32 omits (official Magao), never wraps / never invents
        from providers.modelscope_seed import official_seed_outbound, strip_unofficial_seed

        self.assertIsNone(official_seed_outbound(2147483648))
        self.assertIsNone(official_seed_outbound(4294967295))
        self.assertEqual(official_seed_outbound(2147483647), 2147483647)
        self.assertNotIn("seed", strip_unofficial_seed({"prompt": "a", "seed": 2147483648}))
        with self.assertRaises(ValueError):
            official_seed_outbound(-2)


class FalNanoCatalogNoInventedGates(unittest.TestCase):
    def test_fal_no_default_duration(self):
        from providers.six_catalog_caps import overlay_fal_catalog_item

        row = overlay_fal_catalog_item({"id": "fal-ai/flux/schnell"})
        caps = row.get("capabilities") or {}
        self.assertNotIn("durationEnum", caps)

    def test_nano_no_prompt_max(self):
        from providers.six_catalog_caps import overlay_nano_catalog_item

        row = overlay_nano_catalog_item({"id": "flux-lora", "tags": ["lora"]})
        caps = row.get("capabilities") or {}
        self.assertNotIn("promptMax", caps)
        self.assertNotEqual(caps.get("promptMax"), 1200)


class HuggingFaceCatalogBan(unittest.TestCase):
    def test_fal_ai_lora_not_hf_service(self):
        from providers.hf_catalog_caps import overlay_huggingface_catalog_item

        row = overlay_huggingface_catalog_item({"id": "fal-ai/flux-lora"})
        self.assertFalse(row.get("supportsLora"))
        self.assertEqual((row.get("capabilities") or {}).get("loraChannel"), "blocked")


if __name__ == "__main__":
    unittest.main()
