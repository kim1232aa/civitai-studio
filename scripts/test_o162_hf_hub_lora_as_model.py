#!/usr/bin/env python3
"""o162: HF Hub-LoRA-as-model wiring + Magao Hub loras shape / miss honesty.

Offline only. Never curl /api/generate. Never invent Hub ids.
Stamp: v0822o162-hf-hub-lora-as-model
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from providers import huggingface as hf  # noqa: E402
from providers.hf_catalog_caps import (  # noqa: E402
    mapping_is_hub_lora,
    overlay_huggingface_catalog_item,
)
from providers import modelscope as ms  # noqa: E402
from providers.capabilities import overlay_modelscope_catalog_item  # noqa: E402


GHIBLI_MAP = {
    "fal-ai": {
        "status": "live",
        "providerId": "fal-ai/flux-lora",
        "task": "text-to-image",
        "adapter": "lora",
        "adapterWeightsPath": "flux-chatgpt-ghibli-lora.safetensors",
    },
    "replicate": {
        "status": "live",
        "providerId": "black-forest-labs/flux-dev-lora",
        "task": "text-to-image",
        "adapter": "lora",
        "adapterWeightsPath": "flux-chatgpt-ghibli-lora.safetensors",
    },
}


class O162HfHubLoraAsModel(unittest.TestCase):
    def setUp(self):
        self.enterContext(patch("socket.socket", side_effect=AssertionError("offline only")))
        self.enterContext(patch("socket.getaddrinfo", side_effect=AssertionError("offline only")))
        self.enterContext(patch.object(hf, "hf_keys", return_value=["offline-token"]))
        self.enterContext(patch.object(hf, "hf_key", return_value="offline-token"))
        self.transport = self.enterContext(
            patch.object(hf, "json_call", return_value=(200, {"images": [{"url": "https://example.invalid/o.png"}]}))
        )
        self.enterContext(patch.object(hf, "_save_json_images", return_value=[{"url": "/out/offline.png"}]))
        self.enterContext(patch.object(hf, "load_items", return_value=[]))

    def test_mapping_detects_hub_lora(self):
        self.assertTrue(mapping_is_hub_lora(GHIBLI_MAP))
        self.assertTrue(hf.mapping_is_hub_lora(GHIBLI_MAP))
        self.assertFalse(mapping_is_hub_lora({
            "fal-ai": {"status": "live", "providerId": "fal-ai/flux/schnell", "task": "text-to-image"},
        }))

    def test_catalog_stamp_hub_lora_as_model_official(self):
        row = overlay_huggingface_catalog_item(
            {"id": "openfree/flux-chatgpt-ghibli-lora", "tags": []},
            mapping=GHIBLI_MAP,
        )
        self.assertTrue(row.get("hubLoraAsModel"))
        self.assertTrue(row.get("supportsLora"))
        caps = row["capabilities"]
        self.assertEqual(caps["loraChannel"], "hub-lora-as-model")
        self.assertEqual(caps["loraSource"], "inference-provider-adapter")
        self.assertEqual(caps["loraConfidence"], "official")
        self.assertIn("fal-ai", caps.get("hubLoraProviders") or [])

    def test_fal_ai_star_lora_service_id_still_blocked(self):
        row = overlay_huggingface_catalog_item({"id": "fal-ai/flux-lora"})
        self.assertFalse(row.get("supportsLora"))
        self.assertEqual(row["capabilities"]["loraChannel"], "blocked")

    def test_generate_hub_lora_posts_router_with_hub_mid_adapter(self):
        with patch.object(hf, "inference_mapping", return_value=GHIBLI_MAP), \
                patch("providers.fal.find_model", return_value={
                    "id": "fal-ai/flux-lora",
                    "required": ["prompt"],
                    "optional": ["loras", "image_size", "guidance_scale", "num_inference_steps"],
                }):
            code, data = hf.HuggingFaceProvider().generate({
                "serviceId": "openfree/flux-chatgpt-ghibli-lora",
                "prompt": "ghibli style house",
            })
        self.assertEqual(code, 200, data)
        self.transport.assert_called()
        url = self.transport.call_args.args[0]
        self.assertTrue(url.startswith(hf.ROUTER + "/fal-ai/"), url)
        self.assertIn("fal-ai/flux-lora", url)
        body = self.transport.call_args.kwargs["body"]
        self.assertEqual(
            body["loras"][0]["path"],
            "https://huggingface.co/openfree/flux-chatgpt-ghibli-lora/resolve/main/flux-chatgpt-ghibli-lora.safetensors",
        )
        self.assertNotIn("scale", body["loras"][0])  # IRON §5: no invent scale
        submitted = data.get("submittedInput") or {}
        self.assertTrue(submitted.get("hubLoraAsModel"))
        self.assertEqual(submitted.get("model"), "openfree/flux-chatgpt-ghibli-lora")

    def test_hub_lora_without_fal_ai_is_honest_400(self):
        only_replicate = {
            "replicate": {
                "status": "live",
                "providerId": "black-forest-labs/flux-dev-lora",
                "task": "text-to-image",
                "adapter": "lora",
                "adapterWeightsPath": "x.safetensors",
            },
        }
        with patch.object(hf, "inference_mapping", return_value=only_replicate):
            code, data = hf.HuggingFaceProvider().generate({
                "serviceId": "org/only-replicate-lora",
                "prompt": "x",
            })
        self.assertEqual(code, 400, data)
        err = str(data.get("error") or "")
        self.assertIn("fal-ai", err)
        self.assertTrue(data.get("hubLoraAsModel"))
        self.transport.assert_not_called()

    def test_hf_row_stamps_hub_lora_from_mapping(self):
        row = hf._hf_row(
            "openfree/flux-chatgpt-ghibli-lora",
            "ghibli",
            "text-to-image",
            mapping=GHIBLI_MAP,
        )
        self.assertTrue(row.get("hubLoraAsModel"))
        self.assertIn("hub-lora-as-model", row.get("tags") or [])
        self.assertTrue(row.get("supportsLora"))

    def test_search_adds_filter_lora_url(self):
        calls = []

        def one_page(url):
            calls.append(url)
            return 200, [], None

        with patch.object(hf, "_hf_list_page", side_effect=one_page), \
                patch.object(hf, "json_call", return_value=(404, {})):
            hf._HF_CATALOG_CACHE.update(at=0.0, key=None, items=None, stats={})
            hf.HuggingFaceProvider().catalog("ghibli", "image", "")
        self.assertTrue(any("filter=lora" in u for u in calls), calls)

    def test_stamp_string_in_docs(self):
        doc = (ROOT / "docs" / "api-usage" / "huggingface.md").read_text()
        self.assertIn("v0822o162", doc)
        self.assertIn("Hub-LoRA-as-model", doc)
        self.assertIn("Hub LoRA 当 model", doc)


class O162MagaoHubLoras(unittest.TestCase):
    def test_modelscope_loras_shape_single_string(self):
        self.assertEqual(ms._modelscope_loras({"loras": ["YorickHe/polaroid_lora"]}), "YorickHe/polaroid_lora")
        with self.assertRaises(ValueError):
            ms._modelscope_loras({"loras": [{"path": "https://civitai.com/api/download/models/1"}]})
        with self.assertRaises(ValueError):
            ms._modelscope_loras({"loras": [{"path": "YorickHe/polaroid_lora", "strength": 0.8}]})

    def test_modelscope_loras_multi_sum_one(self):
        out = ms._modelscope_loras({
            "loras": [
                {"path": "owner/a", "weight": 0.4},
                {"path": "owner/b", "weight": 0.6},
            ],
        })
        self.assertEqual(out, {"owner/a": 0.4, "owner/b": 0.6})

    def test_supports_lora_image_not_video(self):
        img = overlay_modelscope_catalog_item({
            "id": "Tongyi-MAI/Z-Image-Turbo",
            "category": "image",
            "task": "text-to-image",
            "tags": ["t2i"],
        })
        self.assertTrue(img.get("supportsLora"))
        vid = overlay_modelscope_catalog_item({
            "id": "krea/krea-realtime-video",
            "category": "video",
            "task": "text-to-video",
            "tags": ["t2v"],
        })
        self.assertFalse(vid.get("supportsLora"))

    def test_cn_krea_keeps_supports_lora(self):
        row = overlay_modelscope_catalog_item({
            "id": "krea/Krea-2-Turbo",
            "category": "image",
            "task": "text-to-image",
            "tags": ["t2i"],
        })
        self.assertTrue(row.get("supportsLora"), "CN krea remains Infer image; AI filters catalog")

    def test_search_loras_exact_miss_is_honest(self):
        with patch.object(ms, "fetch_hub_search", return_value=([], {})):
            code, data = ms.search_loras("NoSuchOwner/no-such-lora-repo-xyz")
        self.assertEqual(code, 200)
        self.assertEqual(data.get("items"), [])
        self.assertTrue(data.get("miss"))
        self.assertIn("不会", data.get("note") or "")


if __name__ == "__main__":
    unittest.main(verbosity=2)
