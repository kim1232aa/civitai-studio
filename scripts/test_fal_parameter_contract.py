#!/usr/bin/env python3
"""Offline Fal contracts: python3 scripts/test_fal_parameter_contract.py.

Per-endpoint schema from docs/fal-models.json + docs/fal-openapi-models.json.
All transport is replaced; never POSTs queue.fal.run.
"""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from providers import fal as fal


FLUX_LORA = "fal-ai/flux-lora"
SCHNELL = "fal-ai/flux/schnell"
Z_LORA = "fal-ai/z-image/turbo/lora"
Z_TURBO = "fal-ai/z-image/turbo"
NANO = "fal-ai/nano-banana-2"
KREA_TURBO = "fal-ai/krea-2/turbo"
KREA_LORA = "fal-ai/krea-2/turbo/lora"
TRAINER = "fal-ai/krea-2-trainer"
KLING = "fal-ai/kling-video/v2.5-turbo/pro/image-to-video"
PROMPT = "keep this prompt intact, including  punctuation "
LORA_PATH = "https://civitai.com/api/download/models/3184845"
LORA_PATH_2 = "XLabs-AI/flux-lora-collection"


def flux_lora_payload(**extra):
    body = {
        "serviceId": FLUX_LORA,
        "prompt": PROMPT,
        "width": 960,
        "height": 1440,
        "steps": 28,
        "cfgScale": 3.5,
        "seed": 475720515768790,
        "quantity": 3,
        "loras": [
            {"path": LORA_PATH, "strength": 0.8, "name": "Kroma"},
            {"path": LORA_PATH_2, "scale": 1.2},
        ],
    }
    body.update(extra)
    return body


class FalContract(unittest.TestCase):
    def setUp(self):
        self.enterContext(patch("socket.socket", side_effect=AssertionError("offline only")))
        self.enterContext(patch("socket.getaddrinfo", side_effect=AssertionError("offline only")))
        self.enterContext(patch.object(fal, "fal_key", return_value="offline-token"))
        self.transport = self.enterContext(
            patch.object(fal, "fal_call", return_value=(200, {"request_id": "offline-rid"}))
        )
        self.enterContext(patch.object(fal, "json_call", side_effect=AssertionError("unexpected json_call")))

    def _posted(self):
        self.assertTrue(self.transport.called, "expected Fal queue POST")
        args, kwargs = self.transport.call_args
        url = args[0]
        method = kwargs.get("method") or (args[1] if len(args) > 1 else None)
        body = kwargs.get("body") if "body" in kwargs else (args[2] if len(args) > 2 else None)
        self.assertEqual(method, "POST")
        self.assertTrue(url.startswith("https://queue.fal.run/"), url)
        return url, body

    def test_flux_lora_originals_round_trip_through_generate(self):
        code, data = fal.FalProvider().generate(flux_lora_payload())
        self.assertEqual(code, 200, data)
        url, body = self._posted()
        self.assertTrue(url.endswith("/" + FLUX_LORA), url)
        submitted = data["submittedInput"]
        for blob in (body, submitted):
            self.assertEqual(blob["prompt"], PROMPT)
            self.assertEqual(blob["num_inference_steps"], 28)
            self.assertEqual(blob["guidance_scale"], 3.5)
            self.assertEqual(blob["seed"], 475720515768790)
            self.assertEqual(blob["num_images"], 3)
            self.assertEqual(blob["image_size"], {"width": 960, "height": 1440})
            self.assertEqual(blob["loras"], [
                {"path": LORA_PATH, "scale": 0.8},
                {"path": LORA_PATH_2, "scale": 1.2},
            ])
            self.assertNotIn("cfgScale", blob)
            self.assertNotIn("steps", blob)
            self.assertNotIn("quantity", blob)
        self.assertEqual(submitted, body)
        self.assertEqual(data.get("endpoint"), FLUX_LORA)

    def test_schnell_loras_are_rejected_not_swapped_to_flux_lora(self):
        payload = flux_lora_payload(serviceId=SCHNELL)
        self.transport.reset_mock()
        with self.assertRaises(ValueError) as raised:
            fal.build_fal_input(payload)
        msg = str(raised.exception)
        self.assertTrue("lora" in msg.lower() or "LoRA" in msg)
        self.assertNotIn("flux-lora", msg)

        code, data = fal.FalProvider().generate(payload)
        self.assertEqual(code, 400, data)
        self.assertIn("error", data)
        self.transport.assert_not_called()
        self.assertNotEqual(data.get("endpoint"), "fal-ai/flux-lora")

    def test_sibling_helper_still_reports_catalog_lora_endpoint(self):
        self.assertEqual(fal.fal_lora_sibling("fal-ai/krea-2/turbo"), "fal-ai/krea-2/turbo/lora")
        self.assertEqual(fal.fal_lora_sibling("fal-ai/z-image/turbo"), "fal-ai/z-image/turbo/lora")
        self.assertEqual(fal.fal_lora_sibling("fal-ai/flux/schnell"), "fal-ai/flux-lora")
        self.assertEqual(fal.fal_lora_sibling("fal-ai/flux-lora"), "fal-ai/flux-lora")

    def test_trainer_is_not_posted_as_generate(self):
        for eid in (TRAINER, "fal-ai/flux-lora-fast-training", "fal-ai/z-image-turbo-trainer-v2"):
            with self.subTest(eid=eid):
                self.transport.reset_mock()
                payload = {"serviceId": eid, "prompt": "train me", "quantity": 1}
                code, data = fal.FalProvider().generate(payload)
                self.assertEqual(code, 400, data)
                err = (data.get("error") or "").lower()
                self.assertTrue("train" in err or "训练" in (data.get("error") or ""))
                self.transport.assert_not_called()

    def test_nano_banana_2_sends_aspect_and_quantity_not_image_size(self):
        payload = {
            "serviceId": NANO,
            "prompt": PROMPT,
            "aspectRatio": "3:2",
            "quantity": 3,
            "width": 960,
            "height": 1440,
            "seed": 91,
            "resolution": "2K",
        }
        inp = fal.build_fal_input(payload)
        self.assertEqual(inp["prompt"], PROMPT)
        self.assertEqual(inp["aspect_ratio"], "3:2")
        self.assertEqual(inp["num_images"], 3)
        self.assertEqual(inp["seed"], 91)
        self.assertEqual(inp["resolution"], "2K")
        self.assertNotIn("image_size", inp)
        self.assertNotIn("width", inp)
        self.assertNotIn("height", inp)

        code, data = fal.FalProvider().generate(payload)
        self.assertEqual(code, 200, data)
        url, body = self._posted()
        self.assertTrue(url.endswith("/" + NANO), url)
        self.assertEqual(body["aspect_ratio"], "3:2")
        self.assertEqual(body["num_images"], 3)
        self.assertEqual(body["resolution"], "2K")
        self.assertNotIn("image_size", body)
        self.assertEqual(data["submittedInput"], body)

    def test_num_images_oor_is_rejected_not_clamped(self):
        self.transport.reset_mock()
        with self.assertRaises(ValueError) as raised:
            fal.build_fal_input(flux_lora_payload(quantity=0))
        self.assertIn("0", str(raised.exception))
        code, data = fal.FalProvider().generate(flux_lora_payload(quantity=0))
        self.assertEqual(code, 400, data)
        self.assertIn("0", data["error"])
        self.transport.assert_not_called()

        inp = fal.build_fal_input(flux_lora_payload(quantity=13))
        self.assertEqual(inp["num_images"], 13)
        self.assertNotEqual(inp["num_images"], 12)

    def test_lora_scale_is_not_silently_clipped(self):
        payload = flux_lora_payload(loras=[
            {"path": LORA_PATH, "scale": 5},
            {"path": LORA_PATH_2, "scale": -0.25},
        ])
        inp = fal.build_fal_input(payload)
        self.assertEqual(inp["loras"], [
            {"path": LORA_PATH, "scale": 5},
            {"path": LORA_PATH_2, "scale": -0.25},
        ])
        z = fal.build_fal_input(dict(payload, serviceId=Z_LORA))
        self.assertEqual(z["loras"], inp["loras"])

    def test_air_only_lora_is_not_silently_dropped(self):
        # AIR without @version still cannot invent a download URL.
        payload = flux_lora_payload(loras=[
            {"air": "urn:air:krea2:lora:civitai:2823254", "strength": 0.8},
        ])
        self.transport.reset_mock()
        with self.assertRaises(ValueError) as raised:
            fal.build_fal_input(payload)
        msg = str(raised.exception).lower()
        self.assertTrue("air" in msg or "path" in msg or "lora" in msg)
        code, data = fal.FalProvider().generate(payload)
        self.assertEqual(code, 400, data)
        self.transport.assert_not_called()

    def test_air_at_version_builds_download_path(self):
        payload = flux_lora_payload(loras=[
            {"air": "urn:air:krea2:lora:civitai:2823254@3184845", "strength": 0.8},
        ])
        inp = fal.build_fal_input(payload)
        self.assertEqual(
            inp["loras"],
            [{"path": "https://civitai.com/api/download/models/3184845", "scale": 0.8}],
        )

    def test_fixture_134923572_fal_pack_uses_3071582_not_2653078(self):
        """Sample post LoRA AIR @3071582 must win over sibling path/id 2653078."""
        air = "urn:air:krea2:lora:civitai:2323765@3071582"
        cases = [
            {"air": air, "strength": None},
            {"air": air, "versionId": 3071582, "id": 2653078, "strength": None},
            {
                "air": air,
                "versionId": 3071582,
                "path": "https://civitai.com/api/download/models/2653078",
                "strength": None,
            },
            {
                "air": air,
                "path": "https://civitai.com/api/download/models/2653078?fileId=1",
                "downloadUrl": "https://civitai.com/api/download/models/2653078?fileId=1",
                "strength": None,
            },
            {"air": air, "id": 2653078, "strength": None},
            {"air": air, "versionId": 2653078, "strength": None},
            {"air": air, "modelVersionId": 2653078, "id": 2653078, "strength": None},
        ]
        for row in cases:
            with self.subTest(row=row):
                path = fal._fal_lora_path(row)
                self.assertIn("3071582", path, path)
                self.assertNotIn("2653078", path, path)
                payload = {
                    "serviceId": KREA_LORA,
                    "prompt": PROMPT,
                    "loras": [row],
                }
                inp = fal.build_fal_input(payload)
                self.assertEqual(len(inp["loras"]), 1)
                self.assertIn("3071582", inp["loras"][0]["path"])
                self.assertNotIn("2653078", inp["loras"][0]["path"])
                self.assertNotIn("scale", inp["loras"][0])  # strength=null → omit, no invent 1.0

    def test_invalid_lora_scale_is_not_defaulted(self):
        for scale in ("oops", True, float("nan")):
            payload = flux_lora_payload(loras=[{"path": LORA_PATH, "scale": scale}])
            with self.subTest(scale=scale):
                self.transport.reset_mock()
                with self.assertRaises(ValueError):
                    fal.build_fal_input(payload)
                code, data = fal.FalProvider().generate(payload)
                self.assertEqual(code, 400, data)
                self.transport.assert_not_called()

    def test_invalid_numeric_types_are_not_dropped_or_truncated(self):
        cases = (
            ("seed", True),
            ("seed", 1.5),
            ("steps", "abc"),
            ("width", 1024.5),
            ("cfgScale", float("nan")),
            ("quantity", True),
        )
        for field, value in cases:
            with self.subTest(field=field, value=value):
                self.transport.reset_mock()
                with self.assertRaises(ValueError):
                    fal.build_fal_input(flux_lora_payload(**{field: value}))
                code, data = fal.FalProvider().generate(flux_lora_payload(**{field: value}))
                self.assertEqual(code, 400, data)
                self.transport.assert_not_called()

    def test_empty_schema_lora_endpoint_still_sends_loras(self):
        payload = {
            "serviceId": Z_LORA,
            "prompt": PROMPT,
            "seed": 11,
            "steps": 8,
            "cfgScale": 1,
            "width": 960,
            "height": 1440,
            "quantity": 2,
            "loras": [{"path": LORA_PATH, "strength": 0.8}],
        }
        inp = fal.build_fal_input(payload)
        self.assertEqual(inp["prompt"], PROMPT)
        self.assertEqual(inp["seed"], 11)
        self.assertEqual(inp["num_inference_steps"], 8)
        self.assertEqual(inp["guidance_scale"], 1)
        self.assertEqual(inp["image_size"], {"width": 960, "height": 1440})
        self.assertEqual(inp["num_images"], 2)
        self.assertEqual(inp["loras"], [{"path": LORA_PATH, "scale": 0.8}])

        # o155: krea-2/turbo/lora now has official schema — CFG/steps must reject, not open-schema invent
        with self.assertRaises(ValueError):
            fal.build_fal_input(dict(payload, serviceId=KREA_LORA))
        krea_ok = {
            "serviceId": KREA_LORA,
            "prompt": PROMPT,
            "seed": 11,
            "width": 960,
            "height": 1440,
            "quantity": 2,
            "loras": [{"path": LORA_PATH, "strength": 0.8}],
        }
        krea = fal.build_fal_input(krea_ok)
        self.assertEqual(krea["loras"], [{"path": LORA_PATH, "scale": 0.8}])
        self.assertNotIn("guidance_scale", krea)
        self.assertNotIn("num_inference_steps", krea)

    def test_krea_turbo_loras_are_not_rewritten_to_lora_sibling(self):
        payload = flux_lora_payload(serviceId=KREA_TURBO)
        self.transport.reset_mock()
        with self.assertRaises(ValueError):
            fal.build_fal_input(payload)
        code, data = fal.FalProvider().generate(payload)
        self.assertEqual(code, 400, data)
        self.transport.assert_not_called()
        if data.get("endpoint"):
            self.assertEqual(data["endpoint"], KREA_TURBO)

        ok = {"serviceId": KREA_TURBO, "prompt": PROMPT, "seed": 7, "width": 960, "height": 1440}
        code, data = fal.FalProvider().generate(ok)
        self.assertEqual(code, 200, data)
        url, body = self._posted()
        self.assertTrue(url.endswith("/" + KREA_TURBO), url)
        self.assertEqual(body["prompt"], PROMPT)
        self.assertEqual(body["seed"], 7)
        self.assertNotIn("loras", body)

    def test_kling_keeps_duration_and_does_not_broadcast_image_size(self):
        payload = {
            "serviceId": KLING,
            "prompt": "a running horse",
            "firstFrame": "https://example.invalid/a.jpg",
            "lastFrame": "https://example.invalid/b.jpg",
            "duration": 5,
            "width": 960,
            "height": 1440,
            "cfgScale": 0.5,
        }
        inp = fal.build_fal_input(payload)
        self.assertEqual(inp["prompt"], "a running horse")
        self.assertEqual(inp["image_url"], "https://example.invalid/a.jpg")
        self.assertEqual(inp["tail_image_url"], "https://example.invalid/b.jpg")
        self.assertEqual(inp["duration"], "5")
        self.assertEqual(inp["cfg_scale"] if "cfg_scale" in inp else inp.get("guidance_scale"), 0.5)
        self.assertNotIn("image_size", inp)

    def test_z_turbo_without_lora_does_not_grow_loras_or_swap(self):
        payload = {
            "serviceId": Z_TURBO,
            "prompt": PROMPT,
            "seed": 3,
            "steps": 8,
            "cfgScale": 0,
            "width": 768,
            "height": 1024,
            "quantity": 2,
        }
        inp = fal.build_fal_input(payload)
        self.assertEqual(inp["prompt"], PROMPT)
        self.assertEqual(inp["seed"], 3)
        self.assertEqual(inp["num_inference_steps"], 8)
        self.assertEqual(inp["guidance_scale"], 0)
        self.assertEqual(inp["image_size"], {"width": 768, "height": 1024})
        self.assertEqual(inp["num_images"], 2)
        self.assertNotIn("loras", inp)
        code, data = fal.FalProvider().generate(payload)
        self.assertEqual(code, 200, data)
        url, _ = self._posted()
        self.assertTrue(url.endswith("/" + Z_TURBO), url)

    def test_krea_turbo_lora_sample_keeps_endpoint_and_sends_loras(self):
        # o155: official OpenAPI has no guidance_scale / num_inference_steps
        payload = {
            "serviceId": KREA_LORA,
            "prompt": PROMPT,
            "width": 944,
            "height": 1672,
            "seed": 467475143677094,
            "quantity": 1,
            "loras": [{"path": LORA_PATH, "strength": 0.8}],
        }
        inp = fal.build_fal_input(payload)
        self.assertEqual(inp["prompt"], PROMPT)
        self.assertEqual(inp["image_size"], {"width": 944, "height": 1672})
        self.assertNotIn("num_inference_steps", inp)
        self.assertNotIn("guidance_scale", inp)
        self.assertEqual(inp["seed"], 467475143677094)
        self.assertEqual(inp["num_images"], 1)
        self.assertEqual(inp["loras"], [{"path": LORA_PATH, "scale": 0.8}])
        code, data = fal.FalProvider().generate(payload)
        self.assertEqual(code, 200, data)
        url, body = self._posted()
        self.assertTrue(url.endswith("/" + KREA_LORA), url)
        self.assertEqual(body["loras"], [{"path": LORA_PATH, "scale": 0.8}])
        self.assertEqual(body["image_size"], {"width": 944, "height": 1672})
        self.assertNotIn("guidance_scale", body)
        self.assertNotIn("num_inference_steps", body)
        self.assertEqual(data.get("endpoint"), KREA_LORA)
        self.assertNotIn("z-image", url)
        self.assertNotIn("trainer", url)

        with self.assertRaises(ValueError):
            fal.build_fal_input(dict(payload, steps=8, cfgScale=1))

        null_scale = dict(payload, loras=[{"path": LORA_PATH, "scale": None}])
        self.transport.reset_mock()
        inp = fal.build_fal_input(null_scale)
        self.assertEqual(inp["loras"], [{"path": LORA_PATH}])
        self.assertNotIn("scale", inp["loras"][0])
        code, data = fal.FalProvider().generate(null_scale)
        self.assertEqual(code, 200, data)
        _, body = self._posted()
        self.assertEqual(body["loras"], [{"path": LORA_PATH}])
        self.assertNotEqual(body["loras"][0].get("scale"), 1.0)

        missing_scale = dict(payload, loras=[{"path": LORA_PATH}])
        self.transport.reset_mock()
        inp = fal.build_fal_input(missing_scale)
        self.assertEqual(inp["loras"], [{"path": LORA_PATH}])
        code, data = fal.FalProvider().generate(missing_scale)
        self.assertEqual(code, 200, data)
        _, body = self._posted()
        self.assertEqual(body["loras"], [{"path": LORA_PATH}])
        self.assertNotIn("scale", body["loras"][0])

        with_aspect = dict(payload, aspectRatio="9:16")
        with self.assertRaises(ValueError) as raised:
            fal.build_fal_input(with_aspect)
        self.assertIn("aspect_ratio", str(raised.exception))

    def test_imagen4_unverified_does_not_invent_fields(self):
        eid = "fal-ai/imagen4/preview"
        extras = {
            "serviceId": eid,
            "prompt": "hello",
            "negativePrompt": "blur",
            "seed": 1,
            "steps": 28,
            "cfgScale": 3.5,
            "aspectRatio": "16:9",
            "width": 1024,
            "height": 1024,
            "quantity": 2,
        }
        self.transport.reset_mock()
        with self.assertRaises(ValueError) as raised:
            fal.build_fal_input(extras)
        msg = str(raised.exception)
        self.assertTrue("未验证" in msg or "404" in msg or "编" in msg)
        self.assertTrue("width" in msg or "steps" in msg or "seed" in msg)
        code, data = fal.FalProvider().generate(extras)
        self.assertEqual(code, 400, data)
        err = data.get("error") or ""
        self.assertTrue("未验证" in err or "404" in err or "编" in err)
        self.transport.assert_not_called()

        prompt_only = {"serviceId": eid, "prompt": "hello"}
        inp = fal.build_fal_input(prompt_only)
        self.assertEqual(inp, {"prompt": "hello"})
        self.assertNotIn("image_size", inp)
        self.assertNotIn("num_images", inp)
        self.assertNotIn("guidance_scale", inp)
        self.assertNotIn("num_inference_steps", inp)
        self.assertNotIn("aspect_ratio", inp)
        code, data = fal.FalProvider().generate(prompt_only)
        self.assertEqual(code, 200, data)
        url, body = self._posted()
        self.assertTrue(url.endswith("/" + eid), url)
        self.assertEqual(body, {"prompt": "hello"})

        for sibling in ("fal-ai/imagen4/preview/fast", "fal-ai/imagen4/preview/ultra"):
            with self.subTest(eid=sibling):
                self.transport.reset_mock()
                code, data = fal.FalProvider().generate({
                    "serviceId": sibling,
                    "prompt": "hello",
                    "width": 1024,
                    "height": 1024,
                })
                self.assertEqual(code, 400, data)
                self.transport.assert_not_called()

    def test_aspect_ratio_rejected_when_schema_has_neither_field(self):
        payload = flux_lora_payload(aspectRatio="16:9")
        self.transport.reset_mock()
        with self.assertRaises(ValueError) as raised:
            fal.build_fal_input(payload)
        msg = str(raised.exception)
        self.assertIn("aspect_ratio", msg)
        self.assertIn("aspectRatio", msg)
        self.assertTrue("静默" in msg or "丢弃" in msg)
        code, data = fal.FalProvider().generate(payload)
        self.assertEqual(code, 400, data)
        self.assertIn("aspect", (data.get("error") or "").lower())
        self.transport.assert_not_called()

    def test_runway_maps_aspect_ratio_to_ratio_not_aspect_ratio(self):
        payload = {
            "serviceId": "fal-ai/runway-gen3/turbo/image-to-video",
            "prompt": "a running horse",
            "firstFrame": "https://example.invalid/a.jpg",
            "lastFrame": "https://example.invalid/b.jpg",
            "aspectRatio": "16:9",
            "duration": 5,
        }
        inp = fal.build_fal_input(payload)
        self.assertEqual(inp["ratio"], "16:9")
        self.assertNotIn("aspect_ratio", inp)
        self.assertEqual(inp["image_url"], "https://example.invalid/a.jpg")
        self.assertEqual(inp["end_image_url"], "https://example.invalid/b.jpg")
        self.assertEqual(inp["duration"], 5)

    def test_quantity_not_one_rejected_when_schema_has_no_num_images(self):
        payload = {
            "serviceId": KLING,
            "prompt": "a running horse",
            "firstFrame": "https://example.invalid/a.jpg",
            "duration": 5,
            "quantity": 2,
        }
        self.transport.reset_mock()
        with self.assertRaises(ValueError) as raised:
            fal.build_fal_input(payload)
        msg = str(raised.exception)
        self.assertIn("num_images", msg)
        self.assertIn("2", msg)
        code, data = fal.FalProvider().generate(payload)
        self.assertEqual(code, 400, data)
        self.transport.assert_not_called()

        ok = dict(payload, quantity=1)
        inp = fal.build_fal_input(ok)
        self.assertNotIn("num_images", inp)
        self.assertEqual(inp["duration"], "5")

    def test_qty_alias_maps_to_num_images(self):
        payload = flux_lora_payload()
        payload.pop("quantity")
        payload["qty"] = 4
        inp = fal.build_fal_input(payload)
        self.assertEqual(inp["num_images"], 4)
        self.assertNotIn("qty", inp)
        self.assertNotIn("quantity", inp)

    def test_incomplete_width_height_is_rejected(self):
        payload = flux_lora_payload()
        payload.pop("height")
        self.transport.reset_mock()
        with self.assertRaises(ValueError) as raised:
            fal.build_fal_input(payload)
        self.assertIn("height", str(raised.exception).lower())
        code, data = fal.FalProvider().generate(payload)
        self.assertEqual(code, 400, data)
        self.transport.assert_not_called()

    def test_unsupported_negative_prompt_is_rejected_not_dropped(self):
        payload = flux_lora_payload(negativePrompt="blur, watermark")
        self.transport.reset_mock()
        with self.assertRaises(ValueError) as raised:
            fal.build_fal_input(payload)
        msg = str(raised.exception)
        self.assertIn("negative", msg.lower())
        code, data = fal.FalProvider().generate(payload)
        self.assertEqual(code, 400, data)
        self.transport.assert_not_called()

    def test_minimax_i2v_keeps_empty_prompt_key(self):
        payload = {
            "serviceId": "fal-ai/minimax/hailuo-02/standard/image-to-video",
            "prompt": "",
            "firstFrame": "https://example.invalid/a.jpg",
            "duration": 6,
        }
        inp = fal.build_fal_input(payload)
        self.assertIn("prompt", inp)
        self.assertEqual(inp["prompt"], "")
        self.assertEqual(inp["image_url"], "https://example.invalid/a.jpg")
        self.assertEqual(inp["duration"], 6)

    def test_zero_real_upstream_on_success_uses_fake_transport_only(self):
        fal.FalProvider().generate(flux_lora_payload())
        url, _ = self._posted()
        self.assertTrue(url.startswith("https://queue.fal.run/"))
        self.assertEqual(self.transport.call_count, 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
