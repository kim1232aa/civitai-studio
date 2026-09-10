#!/usr/bin/env python3
"""Offline Civitai contracts: python3 scripts/test_civitai_parameter_contract.py.

Per-model schema from docs/capabilities.json + docs/catalog.json.
All transport is replaced; never POSTs orchestration.civitai.com.
"""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from providers import civitai as civ


KREA_SID = "image/comfy/krea2/turbo/createImage"
KLEA_AIR = "urn:air:krea2:lora:civitai:2823254@3184845"
CKPT_AIR = "urn:air:krea2:diffusionmodel:civitai:2782456@3146785"
KLEA_PROMPT = "keep this prompt intact, including  punctuation "


def krea_payload(**extra):
    body = {
        "serviceId": KREA_SID,
        "prompt": KLEA_PROMPT,
        "negativePrompt": "blur, watermark",
        "width": 960,
        "height": 1440,
        "steps": 8,
        "cfgScale": 1,
        "seed": 475720515768790,
        "sampler": "er_sde",
        "scheduler": "sgm_uniform",
        "quantity": 3,
        "diffusionModel": CKPT_AIR,
        "loras": [
            {"air": KLEA_AIR, "strength": 0.8, "name": "Kroma"},
            {"air": "urn:air:krea2:lora:civitai:1@2", "strength": 1.2},
        ],
    }
    body.update(extra)
    return body


def step_input(wf):
    return wf["steps"][0]["input"]


class CivitaiContract(unittest.TestCase):
    def setUp(self):
        self.enterContext(patch("socket.socket", side_effect=AssertionError("offline only")))
        self.transport = self.enterContext(
            patch.object(civ, "civitai", return_value=(200, {"id": "wf-offline", "token": "tok"}))
        )
        self.enterContext(patch.object(civ, "json_call", side_effect=AssertionError("unexpected json_call")))
        self.enterContext(patch.object(civ, "token", return_value="offline-token"))

    def _posted_body(self):
        self.assertTrue(self.transport.called, "expected orchestration POST")
        args, kwargs = self.transport.call_args
        self.assertEqual(kwargs.get("method") or (args[1] if len(args) > 1 else None), "POST")
        url = args[0]
        self.assertIn("orchestration.civitai.com", url)
        self.assertIn("/v2/consumer/workflows", url)
        return kwargs.get("body") if "body" in kwargs else (args[2] if len(args) > 2 else None)

    def test_krea_turbo_originals_round_trip_through_generate(self):
        code, data = civ.CivitaiProvider().generate(krea_payload())
        self.assertEqual(code, 200)
        posted = self._posted_body()
        inp = posted["steps"][0]["input"]
        submitted = data["submittedInput"]
        for blob in (inp, submitted):
            self.assertEqual(blob["prompt"], KLEA_PROMPT)
            self.assertEqual(blob["negativePrompt"], "blur, watermark")
            self.assertEqual(blob["width"], 960)
            self.assertEqual(blob["height"], 1440)
            self.assertEqual(blob["steps"], 8)
            self.assertEqual(blob["cfgScale"], 1)
            self.assertEqual(blob["seed"], 475720515768790)
            self.assertEqual(blob["sampler"], "er_sde")
            self.assertEqual(blob["scheduler"], "sgm_uniform")
            self.assertEqual(blob["quantity"], 3)
            self.assertEqual(blob["diffusionModel"], CKPT_AIR)
            self.assertEqual(blob["engine"], "comfy")
            self.assertEqual(blob["ecosystem"], "krea2")
            self.assertEqual(blob["model"], "turbo")
            self.assertEqual(blob["loras"], {KLEA_AIR: 0.8, "urn:air:krea2:lora:civitai:1@2": 1.2})
        self.assertEqual(submitted.get("serviceId") or data.get("service", {}).get("serviceId"), KREA_SID)
        self.assertNotEqual(submitted, {"serviceId": KREA_SID})

    def test_krea_oor_is_rejected_not_clamped(self):
        cases = (
            ("width", 32),
            ("width", 3000),
            ("height", 32),
            ("steps", 0),
            ("steps", 200),
            ("quantity", 0),
            ("quantity", 13),
            ("cfgScale", -1),
            ("cfgScale", 31),
        )
        for field, value in cases:
            with self.subTest(field=field, value=value):
                self.transport.reset_mock()
                with self.assertRaises(ValueError) as raised:
                    civ.build_workflow(krea_payload(**{field: value}))
                msg = str(raised.exception)
                self.assertTrue(
                    "超出" in msg or "范围" in msg or field in msg,
                    msg,
                )
                self.assertIn(str(value), msg)
                code, data = civ.CivitaiProvider().generate(krea_payload(**{field: value}))
                self.assertEqual(code, 400)
                self.assertIn("error", data)
                self.assertIn(str(value), data["error"])
                self.transport.assert_not_called()

    def test_unknown_or_missing_service_is_not_silently_swapped(self):
        self.transport.reset_mock()
        with self.assertRaises(ValueError):
            civ.build_workflow(krea_payload(serviceId="image/comfy/does-not-exist/createImage"))
        code, data = civ.CivitaiProvider().generate(
            krea_payload(serviceId="image/comfy/does-not-exist/createImage")
        )
        self.assertEqual(code, 400)
        self.assertIn("error", data)
        self.assertNotIn("krea2/turbo", data["error"])
        self.transport.assert_not_called()

        self.transport.reset_mock()
        payload = krea_payload()
        payload.pop("serviceId")
        with self.assertRaises(ValueError):
            civ.build_workflow(payload)
        code, data = civ.CivitaiProvider().generate(payload)
        self.assertEqual(code, 400)
        self.transport.assert_not_called()

    def test_unknown_sampler_scheduler_are_not_rewritten_to_defaults(self):
        for field, value in (("sampler", "not_a_sampler"), ("scheduler", "not_a_scheduler")):
            with self.subTest(field=field, value=value):
                self.transport.reset_mock()
                with self.assertRaises(ValueError) as raised:
                    civ.build_workflow(krea_payload(**{field: value}))
                self.assertIn(value, str(raised.exception))
                code, data = civ.CivitaiProvider().generate(krea_payload(**{field: value}))
                self.assertEqual(code, 400)
                self.assertIn(value, data["error"])
                self.transport.assert_not_called()

    def test_invalid_numeric_types_are_not_dropped_or_truncated(self):
        for field, value in (
            ("seed", True),
            ("seed", 1.5),
            ("steps", "abc"),
            ("width", 1024.5),
            ("cfgScale", float("nan")),
        ):
            with self.subTest(field=field, value=value):
                self.transport.reset_mock()
                with self.assertRaises(ValueError):
                    civ.build_workflow(krea_payload(**{field: value}))
                self.transport.assert_not_called()

    def test_path_only_lora_is_not_invented_or_silently_dropped(self):
        payload = krea_payload(loras=[
            {"path": "https://civitai.com/api/download/models/3184845", "strength": 0.8},
        ])
        self.transport.reset_mock()
        with self.assertRaises(ValueError) as raised:
            civ.build_workflow(payload)
        msg = str(raised.exception).lower()
        self.assertTrue("air" in msg or "lora" in msg)
        code, data = civ.CivitaiProvider().generate(payload)
        self.assertEqual(code, 400)
        self.transport.assert_not_called()

    def test_invalid_lora_strength_is_not_defaulted(self):
        for strength in ("oops", True):
            payload = krea_payload(loras=[{"air": KLEA_AIR, "strength": strength}])
            with self.subTest(strength=strength):
                self.transport.reset_mock()
                with self.assertRaises(ValueError) as raised:
                    civ.build_workflow(payload)
                self.assertNotIn("1.0", str(raised.exception))
                code, data = civ.CivitaiProvider().generate(payload)
                self.assertEqual(code, 400, data)
                self.transport.assert_not_called()

    def test_null_lora_strength_is_omitted_not_defaulted(self):
        for loras in (
            [{"air": KLEA_AIR, "strength": None}],
            [{"air": KLEA_AIR, "strength": ""}],
            [{"air": KLEA_AIR}],
        ):
            payload = krea_payload(loras=loras)
            with self.subTest(loras=loras):
                self.transport.reset_mock()
                with self.assertRaises(ValueError) as raised:
                    civ.build_workflow(payload)
                msg = str(raised.exception)
                self.assertIn("ImmutableDictionary", msg)
                self.assertIn("不会默认为 1.0", msg)
                code, data = civ.CivitaiProvider().generate(payload)
                self.assertEqual(code, 400, data)
                self.transport.assert_not_called()

    def test_hunyuan_keeps_array_loras_and_original_duration_steps(self):
        air = "urn:air:hunyuan:lora:civitai:9@9"
        payload = {
            "serviceId": "video/hunyuan",
            "prompt": "a running horse",
            "width": 864,
            "height": 480,
            "cfgScale": 7.5,
            "duration": 8,
            "steps": 20,
            "seed": 99,
            "loras": [{"air": air, "strength": 0.65}],
        }
        wf = civ.build_workflow(payload)
        inp = step_input(wf)
        self.assertEqual(inp["engine"], "hunyuan")
        self.assertEqual(inp["duration"], 8)
        self.assertEqual(inp["steps"], 20)
        self.assertEqual(inp["cfgScale"], 7.5)
        self.assertEqual(inp["width"], 864)
        self.assertEqual(inp["height"], 480)
        self.assertEqual(inp["loras"], [{"air": air, "strength": 0.65}])
        self.assertIsInstance(inp["loras"], list)

        self.transport.reset_mock()
        with self.assertRaises(ValueError):
            civ.build_workflow(dict(payload, steps=5))
        with self.assertRaises(ValueError):
            civ.build_workflow(dict(payload, duration=31))
        code, data = civ.CivitaiProvider().generate(dict(payload, steps=5))
        self.assertEqual(code, 400)
        self.transport.assert_not_called()

    def test_flux2_klein_9b_uses_klein_schema_not_dev(self):
        air = "urn:air:flux2:lora:civitai:3@4"
        payload = {
            "serviceId": "image/flux2/klein/createImage/9b",
            "prompt": "klein original",
            "negativePrompt": "low quality",
            "width": 1024,
            "height": 768,
            "quantity": 3,
            "steps": 20,
            "cfgScale": 5,
            "seed": 11,
            "sampler": "er_sde",
            "scheduler": "sgm_uniform",
            "loras": [{"air": air, "strength": 0.9}],
        }
        wf = civ.build_workflow(payload)
        inp = step_input(wf)
        self.assertEqual(inp["engine"], "flux2")
        self.assertEqual(inp["model"], "klein")
        self.assertEqual(inp.get("modelVersion") or "9b", "9b")
        self.assertEqual(inp["width"], 1024)
        self.assertEqual(inp["height"], 768)
        self.assertEqual(inp["quantity"], 3)
        self.assertEqual(inp["steps"], 20)
        self.assertEqual(inp["cfgScale"], 5)
        self.assertEqual(inp.get("negativePrompt"), "low quality")
        self.assertNotIn("guidanceScale", inp)
        self.assertNotIn("numInferenceSteps", inp)
        loras = inp["loras"]
        if isinstance(loras, dict):
            self.assertEqual(loras[air], 0.9)
        else:
            self.assertEqual(loras, [{"air": air, "strength": 0.9}])

        self.transport.reset_mock()
        with self.assertRaises(ValueError):
            civ.build_workflow(dict(payload, quantity=5))
        with self.assertRaises(ValueError):
            civ.build_workflow(dict(payload, width=256))
        with self.assertRaises(ValueError):
            civ.build_workflow(dict(payload, steps=3))
        code, data = civ.CivitaiProvider().generate(dict(payload, quantity=5))
        self.assertEqual(code, 400)
        self.transport.assert_not_called()

    def test_flux2_dev_keeps_official_field_names_and_array_loras(self):
        air = "urn:air:flux2:lora:civitai:8@8"
        payload = {
            "serviceId": "image/flux2/dev/createImage",
            "prompt": "dev original",
            "width": 1024,
            "height": 1024,
            "quantity": 2,
            "steps": 28,
            "cfgScale": 3.5,
            "seed": 4,
            "loras": [{"air": air, "strength": 0.4}],
        }
        inp = step_input(civ.build_workflow(payload))
        self.assertEqual(inp["guidanceScale"], 3.5)
        self.assertEqual(inp["numInferenceSteps"], 28)
        self.assertNotIn("cfgScale", inp)
        self.assertNotIn("steps", inp)
        self.assertEqual(inp["quantity"], 2)
        self.assertEqual(inp["loras"], [{"air": air, "strength": 0.4}])

    def test_sd15_rejects_width_above_1024(self):
        payload = {
            "serviceId": "image/comfy/sd1/createImage",
            "prompt": "sd15",
            "width": 1280,
            "height": 768,
            "steps": 30,
            "cfgScale": 7,
            "sampler": "euler",
            "scheduler": "karras",
        }
        self.transport.reset_mock()
        with self.assertRaises(ValueError) as raised:
            civ.build_workflow(payload)
        self.assertIn("1280", str(raised.exception))
        code, data = civ.CivitaiProvider().generate(payload)
        self.assertEqual(code, 400)
        self.transport.assert_not_called()

        ok = dict(payload, width=768)
        inp = step_input(civ.build_workflow(ok))
        self.assertEqual(inp["width"], 768)
        self.assertEqual(inp["height"], 768)
        self.assertEqual(inp["ecosystem"], "sd1")

    def test_krea_raw_is_not_replaced_by_turbo_defaults(self):
        payload = krea_payload(
            serviceId="image/comfy/krea2/raw/createImage",
            steps=20,
            cfgScale=4,
        )
        inp = step_input(civ.build_workflow(payload))
        self.assertEqual(inp["model"], "raw")
        self.assertEqual(inp["steps"], 20)
        self.assertEqual(inp["cfgScale"], 4)
        self.assertEqual(inp["width"], 960)
        self.assertEqual(inp["loras"][KLEA_AIR], 0.8)

    def test_sdcpp_zimage_turbo_maps_sample_method_and_schedule(self):
        air = "urn:air:zImage:lora:civitai:1@2"
        payload = {
            "serviceId": "image/sdcpp/zImage/turbo/createImage",
            "prompt": "z turbo",
            "width": 768,
            "height": 1024,
            "steps": 9,
            "cfgScale": 1,
            "seed": 42,
            "sampler": "euler",
            "scheduler": "simple",
            "loras": [{"air": air, "strength": 0.8}],
        }
        inp = step_input(civ.build_workflow(payload))
        self.assertEqual(inp["engine"], "sdcpp")
        self.assertEqual(inp["ecosystem"], "zImage")
        self.assertEqual(inp["model"], "turbo")
        self.assertEqual(inp["sampleMethod"], "euler")
        self.assertEqual(inp["schedule"], "simple")
        self.assertNotIn("sampler", inp)
        self.assertNotIn("scheduler", inp)
        self.assertEqual(inp["steps"], 9)
        self.assertEqual(inp["cfgScale"], 1)
        self.assertEqual(inp["loras"], {air: 0.8})
        code, data = civ.CivitaiProvider().generate(payload)
        self.assertEqual(code, 200, data)
        posted = self._posted_body()["steps"][0]["input"]
        self.assertEqual(posted["sampleMethod"], "euler")
        self.assertEqual(posted["schedule"], "simple")
        self.assertNotIn("sampler", posted)
        self.assertEqual(data["submittedInput"]["sampleMethod"], "euler")
        self.transport.reset_mock()
        with self.assertRaises(ValueError) as raised:
            civ.build_workflow(dict(payload, width=32))
        self.assertIn("32", str(raised.exception))
        code, data = civ.CivitaiProvider().generate(dict(payload, width=32))
        self.assertEqual(code, 400, data)
        self.transport.assert_not_called()


    def test_sdcpp_sdxl_maps_dpmpp_2m_karras_from_import(self):
        """19201654 import: dpmpp_2m/karras → sdcpp sampleMethod dpm++2m + schedule karras.

        Locked mapping (api对接助手): dpmpp_2m MUST outbound as exact enum dpm++2m.
        Checkpoint AIR maps to official sdcpp `model` (OpenAPI), not Comfy diffusionModel.
        """
        air = "urn:air:sdxl:lycoris:civitai:518563@633865"
        ckpt = "urn:air:sdxl:checkpoint:civitai:317902@593760"
        payload = {
            "serviceId": "image/sdcpp/sdxl/createImage",
            "prompt": "score_9, holding sliver sword",
            "negativePrompt": "score_6, blurry",
            "width": 1728,
            "height": 2048,
            "steps": 30,
            "cfgScale": 7.0,
            "seed": 3436905144,
            "sampler": "dpmpp_2m",
            "scheduler": "karras",
            "diffusionModel": ckpt,
            "loras": [{"air": air, "strength": 0.7}],
        }
        inp = step_input(civ.build_workflow(payload))
        self.assertEqual(inp["engine"], "sdcpp")
        self.assertEqual(inp["ecosystem"], "sdxl")
        self.assertEqual(inp["sampleMethod"], "dpm++2m")
        self.assertEqual(inp["schedule"], "karras")
        self.assertEqual(inp["model"], ckpt)
        self.assertNotIn("sampler", inp)
        self.assertNotIn("scheduler", inp)
        self.assertNotIn("diffusionModel", inp)
        self.assertEqual(inp["loras"], {air: 0.7})
        self.assertEqual(inp["steps"], 30)
        self.assertEqual(inp["cfgScale"], 7.0)
        self.assertEqual(inp["width"], 1728)
        self.assertEqual(inp["height"], 2048)
        # unknown sampler still rejected (no silent invent)
        with self.assertRaises(ValueError) as raised:
            civ.build_workflow(dict(payload, sampler="not_a_real_sampler"))
        self.assertIn("不在允许列表", str(raised.exception))

    def test_fal_engine_krea2_rejects_loras_and_sends_official_fields(self):
        sid = "image/fal/krea2/createImage"
        refs = [{"url": "https://example.invalid/style.jpg", "strength": 1.0}]
        with_lora = {
            "serviceId": sid,
            "prompt": "fal krea",
            "quantity": 1,
            "aspectRatio": "9:16",
            "creativity": "raw",
            "size": "large",
            "imageStyleReferences": refs,
            "loras": [{"air": KLEA_AIR, "strength": 0.8}],
        }
        self.transport.reset_mock()
        with self.assertRaises(ValueError) as raised:
            civ.build_workflow(with_lora)
        msg = str(raised.exception)
        self.assertTrue("LoRA" in msg or "lora" in msg.lower())
        self.assertNotIn("turbo", msg.lower())
        code, data = civ.CivitaiProvider().generate(with_lora)
        self.assertEqual(code, 400, data)
        self.transport.assert_not_called()
        self.assertNotIn("krea2/turbo", (data.get("error") or "").lower())

        ok = {
            "serviceId": sid,
            "prompt": "fal krea",
            "quantity": 2,
            "aspectRatio": "9:16",
            "creativity": "raw",
            "size": "large",
            "seed": 7,
            "imageStyleReferences": refs,
        }
        inp = step_input(civ.build_workflow(ok))
        self.assertEqual(inp["engine"], "fal")
        self.assertEqual(inp["model"], "krea2")
        self.assertEqual(inp["creativity"], "raw")
        self.assertEqual(inp["size"], "large")
        self.assertEqual(inp["aspectRatio"], "9:16")
        self.assertEqual(inp["quantity"], 2)
        self.assertEqual(inp["seed"], 7)
        self.assertEqual(inp["imageStyleReferences"], refs)
        self.assertNotIn("loras", inp)
        self.assertNotIn("sampler", inp)
        self.assertNotIn("width", inp)
        code, data = civ.CivitaiProvider().generate(ok)
        self.assertEqual(code, 200, data)
        posted = self._posted_body()["steps"][0]["input"]
        self.assertEqual(posted["creativity"], "raw")
        self.assertEqual(posted["size"], "large")
        self.assertEqual(posted["aspectRatio"], "9:16")
        self.assertNotIn("loras", posted)

        self.transport.reset_mock()
        with self.assertRaises(ValueError) as raised:
            civ.build_workflow(dict(ok, creativity="turbo"))
        self.assertIn("turbo", str(raised.exception))
        code, data = civ.CivitaiProvider().generate(dict(ok, creativity="turbo"))
        self.assertEqual(code, 400, data)
        self.transport.assert_not_called()

        self.transport.reset_mock()
        missing_refs = dict(ok)
        missing_refs.pop("imageStyleReferences")
        with self.assertRaises(ValueError) as raised:
            civ.build_workflow(missing_refs)
        self.assertIn("imageStyleReferences", str(raised.exception))
        code, data = civ.CivitaiProvider().generate(missing_refs)
        self.assertEqual(code, 400, data)
        self.transport.assert_not_called()

    def test_krea_engine_large_keeps_catalog_model_and_rejects_loras(self):
        sid = "image/krea/createImage/krea2-large"
        refs = [{"url": "https://example.invalid/style.jpg", "strength": 0.5}]
        with_lora = {
            "serviceId": sid,
            "prompt": "krea engine",
            "aspectRatio": "16:9",
            "creativity": "high",
            "imageStyleReferences": refs,
            "loras": [{"air": KLEA_AIR, "strength": 0.8}],
        }
        self.transport.reset_mock()
        with self.assertRaises(ValueError) as raised:
            civ.build_workflow(with_lora)
        self.assertTrue("LoRA" in str(raised.exception) or "lora" in str(raised.exception).lower())
        code, data = civ.CivitaiProvider().generate(with_lora)
        self.assertEqual(code, 400, data)
        self.transport.assert_not_called()

        ok = {
            "serviceId": sid,
            "prompt": "krea engine",
            "aspectRatio": "16:9",
            "creativity": "high",
            "quantity": 2,
            "imageStyleReferences": refs,
            "intensity": 20,
        }
        inp = step_input(civ.build_workflow(ok))
        self.assertEqual(inp["engine"], "krea")
        self.assertEqual(inp["model"], "krea2-large")
        self.assertNotEqual(inp["model"], "krea2-medium")
        self.assertEqual(inp["creativity"], "high")
        self.assertEqual(inp["aspectRatio"], "16:9")
        self.assertEqual(inp["intensity"], 20)
        self.assertNotIn("loras", inp)
        self.assertNotIn("size", inp)
        self.transport.reset_mock()
        with self.assertRaises(ValueError) as raised:
            civ.build_workflow(dict(ok, intensity=0.2))
        self.assertIn("0.2", str(raised.exception))
        self.assertNotIn("截", str(raised.exception))
        code, data = civ.CivitaiProvider().generate(dict(ok, intensity=0.2))
        self.assertEqual(code, 400, data)
        self.transport.assert_not_called()

    def test_zero_real_upstream_on_success_uses_fake_transport_only(self):
        civ.CivitaiProvider().generate(krea_payload())
        url = self.transport.call_args[0][0]
        self.assertTrue(url.startswith("https://orchestration.civitai.com/v2/consumer/workflows"))
        self.assertEqual(self.transport.call_count, 1)

    def test_import_null_strength_is_preserved_not_defaulted_to_0_8(self):
        """Page 134923572: strength=null must stay visible. Import must not invent 0.8."""
        air = "urn:air:krea2:lora:civitai:2323765@3071582"
        resources = [{
            "air": air,
            "modelType": "LORA",
            "modelName": "Radiance Chrome Voluptuous",
            "modelId": 2323765,
            "modelVersionId": 3071582,
            "strength": None,
        }]
        loras = civ._loras_from_import_sources(resources)
        self.assertEqual(len(loras), 1)
        row = loras[0]
        self.assertEqual(row["air"], air)
        self.assertIsNone(row["strength"])
        self.assertTrue(row.get("strengthMissing"))
        self.assertNotEqual(row["strength"], 0.8)
        self.assertEqual(row["versionId"], 3071582)

        explicit = civ._loras_from_import_sources([{
            "air": air,
            "modelType": "LORA",
            "modelName": "Radiance Chrome Voluptuous",
            "strength": 0.65,
        }])
        self.assertEqual(explicit[0]["strength"], 0.65)
        self.assertNotIn("strengthMissing", explicit[0])

        weight_only = civ._loras_from_import_sources([{
            "air": air,
            "modelType": "LORA",
            "modelName": "Radiance Chrome Voluptuous",
            "weight": 1.1,
        }])
        self.assertEqual(weight_only[0]["strength"], 1.1)

        null_beats_weight = civ._loras_from_import_sources([{
            "air": air,
            "modelType": "LORA",
            "modelName": "Radiance Chrome Voluptuous",
            "strength": None,
            "weight": 0.8,
        }])
        self.assertIsNone(null_beats_weight[0]["strength"])
        self.assertTrue(null_beats_weight[0].get("strengthMissing"))

        missing_keys = civ._loras_from_import_sources([{
            "air": air,
            "modelType": "LORA",
            "modelName": "Radiance Chrome Voluptuous",
        }])
        self.assertIsNone(missing_keys[0]["strength"])
        self.assertTrue(missing_keys[0].get("strengthMissing"))

        self.transport.reset_mock()
        payload = krea_payload(loras=[{"air": air, "strength": loras[0]["strength"]}])
        with self.assertRaises(ValueError) as raised:
            civ.build_workflow(payload)
        self.assertIn("ImmutableDictionary", str(raised.exception))
        code, data = civ.CivitaiProvider().generate(payload)
        self.assertEqual(code, 400, data)
        self.transport.assert_not_called()

    def test_import_air_at_version_beats_sibling_id_path_2653078(self):
        """Fixture 134923572: AIR @3071582 must land on chips, not sibling 2653078."""
        air = "urn:air:krea2:lora:civitai:2323765@3071582"
        cases = [
            {"air": air, "modelType": "LORA", "modelName": "Radiance Chrome Voluptuous",
             "id": 2653078, "strength": None},
            {"air": air, "modelType": "LORA", "modelName": "Radiance Chrome Voluptuous",
             "versionId": 2653078, "strength": None},
            {"air": air, "modelType": "LORA", "modelName": "Radiance Chrome Voluptuous",
             "modelVersionId": 2653078, "strength": None},
            {"air": air, "modelType": "LORA", "modelName": "Radiance Chrome Voluptuous",
             "id": 2653078,
             "path": "https://civitai.com/api/download/models/2653078",
             "downloadUrl": "https://civitai.com/api/download/models/2653078",
             "strength": None},
            {"air": air, "modelType": "LORA", "modelName": "Radiance Chrome Voluptuous",
             "modelVersionId": 3071582, "id": 2653078, "strength": None},
        ]
        for resources in ([[c] for c in cases]):
            with self.subTest(resources=resources):
                loras = civ._loras_from_import_sources(resources)
                self.assertEqual(len(loras), 1)
                row = loras[0]
                self.assertEqual(row["air"], air)
                self.assertEqual(row["versionId"], 3071582)
                self.assertIn("3071582", row.get("path") or "")
                self.assertNotIn("2653078", row.get("path") or "")
                self.assertNotIn("2653078", row.get("downloadUrl") or "")
                self.assertEqual(row["versionId"], civ._version_id_from_air(air))

        # No AIR @version: explicit versionId still wins over bare id.
        no_air = civ._loras_from_import_sources([{
            "modelType": "LORA",
            "modelName": "X",
            "versionId": 3071582,
            "id": 2653078,
            "strength": 0.8,
        }])
        self.assertEqual(no_air[0]["versionId"], 3071582)
        self.assertIn("3071582", no_air[0]["path"])


    def test_o27_rest_backfill_strength_28533344(self):
        """Image 28533344: trpc strength=null, REST strength=0.7 for version 823089.

        Official REST /api/generation/data is the original param — never invent 0.8.
        """
        trpc = [{
            "modelVersionId": 823089,
            "versionId": 823089,
            "modelType": "LORA",
            "modelName": "Kolors style Asian face for Flux1 dev",
            "strength": None,
        }]
        rest = [{
            "id": 823089,
            "name": "v0.3",
            "air": "urn:air:flux1:lora:civitai:730162@823089",
            "strength": 0.7,
        }]
        merged = civ._backfill_strength_from_rest(trpc, rest)
        self.assertEqual(merged[0]["strength"], 0.7)
        loras = civ._loras_from_import_sources(merged)
        self.assertEqual(len(loras), 1)
        self.assertEqual(loras[0]["strength"], 0.7)
        self.assertNotIn("strengthMissing", loras[0])
        self.assertEqual(loras[0]["versionId"], 823089)
        self.assertNotEqual(loras[0]["strength"], 0.8)

        # REST null / missing → still strengthMissing (no invent)
        still = civ._backfill_strength_from_rest(trpc, [{"id": 823089, "strength": None}])
        self.assertIsNone(still[0]["strength"])
        missing = civ._loras_from_import_sources(still)
        self.assertTrue(missing[0].get("strengthMissing"))

        # Explicit trpc numeric wins over REST
        explicit = civ._backfill_strength_from_rest(
            [{"modelVersionId": 823089, "modelType": "LORA", "modelName": "X", "strength": 0.55}],
            rest,
        )
        self.assertEqual(explicit[0]["strength"], 0.55)

        # Full import_image path with mocked trpc + REST (offline)
        def fake_civitai(url, method="GET", body=None, timeout=90):
            if "image.getGenerationData" in url:
                return 200, {"result": {"data": {"json": {
                    "meta": {"prompt": "o27 fixture", "steps": 20, "cfgScale": 1,
                             "sampler": "euler", "width": 832, "height": 1216},
                    "resources": trpc,
                }}}}
            if "image.get" in url:
                return 200, {"result": {"data": {"json": {"type": "image", "url": "https://example.invalid/x", "width": 832, "height": 1216}}}}
            return 200, {}

        def fake_json_call(url, method="GET", headers=None, body=None, timeout=90):
            if "/api/generation/data" in url and "28533344" in url:
                return 200, {"type": "image", "resources": rest, "params": {}}
            raise AssertionError(f"unexpected json_call {url}")

        with patch.object(civ, "civitai", side_effect=fake_civitai), \
             patch.object(civ, "json_call", side_effect=fake_json_call), \
             patch.object(civ, "has_key", return_value=True), \
             patch.object(civ, "generation_from_page", return_value={}), \
             patch.object(civ, "public_image_row", return_value={}), \
             patch.object(civ, "fetch_version_air", return_value={
                 "id": 823089,
                 "air": "urn:air:flux1:lora:civitai:730162@823089",
                 "modelId": 730162,
                 "model": {"name": "Kolors style Asian face for Flux1 dev", "type": "LORA"},
                 "files": [{"downloadUrl": "https://civitai.com/api/download/models/823089"}],
             }), \
             patch.object(civ, "match_service", return_value={"id": "image/sdcpp/flux/createImage", "name": "flux"}):
            imported = civ.import_image("28533344")
        self.assertEqual(imported["loras"][0]["strength"], 0.7)
        self.assertNotIn("strengthMissing", imported["loras"][0])
        self.assertEqual(imported["loras"][0]["versionId"], 823089)

    def test_prompt_lora_tag_without_weight_is_not_defaulted_to_0_8(self):
        tagged = civ._prompt_lora_tags("<lora:RadianceChrome>")
        self.assertEqual(len(tagged), 1)
        self.assertIsNone(tagged[0]["strength"])
        self.assertTrue(tagged[0].get("strengthMissing"))

        weighted = civ._prompt_lora_tags("<lora:RadianceChrome:0.65>")
        self.assertEqual(weighted[0]["strength"], 0.65)
        self.assertNotIn("strengthMissing", weighted[0])

        imported = civ._loras_from_import_sources([], prompt="<lora:RadianceChrome>")
        self.assertEqual(len(imported), 1)
        self.assertEqual(imported[0]["name"], "RadianceChrome")
        self.assertIsNone(imported[0]["strength"])
        self.assertTrue(imported[0].get("strengthMissing"))
        self.assertNotEqual(imported[0]["strength"], 0.8)

    def test_schema_fields_are_rejected_not_silently_omitted(self):
        cases = (
            (krea_payload(duration=8), "duration", "8"),
            (krea_payload(resolution="1080p"), "resolution", "1080p"),
            (krea_payload(denoise=0.5), "denoise", "0.5"),
            ({
                "serviceId": "image/fal/krea2/createImage",
                "prompt": "fal krea",
                "quantity": 1,
                "aspectRatio": "9:16",
                "creativity": "raw",
                "size": "large",
                "imageStyleReferences": [{"url": "https://example.invalid/style.jpg", "strength": 1.0}],
                "width": 960,
            }, "width", "960"),
            ({
                "serviceId": "image/fal/krea2/createImage",
                "prompt": "fal krea",
                "quantity": 1,
                "aspectRatio": "9:16",
                "creativity": "raw",
                "size": "large",
                "imageStyleReferences": [{"url": "https://example.invalid/style.jpg", "strength": 1.0}],
                "negativePrompt": "blur",
            }, "negativePrompt", "blur"),
        )
        for payload, field, _shown in cases:
            with self.subTest(field=field, serviceId=payload.get("serviceId")):
                self.transport.reset_mock()
                with self.assertRaises(ValueError) as raised:
                    civ.build_workflow(payload)
                msg = str(raised.exception)
                self.assertTrue(field in msg or "不接受" in msg, msg)
                self.assertIn("不接受", msg)
                code, data = civ.CivitaiProvider().generate(payload)
                self.assertEqual(code, 400, data)
                self.assertIn("error", data)
                self.transport.assert_not_called()
                wf_keys = []
                try:
                    wf_keys = list(step_input(civ.build_workflow({k: v for k, v in payload.items() if k != field})).keys())
                except Exception:
                    pass
                self.assertNotIn(field, wf_keys)

    def test_dict_lora_form_is_accepted_without_default_strength(self):
        air = "urn:air:krea2:lora:civitai:2823254@3184845"
        payload = krea_payload(loras={air: 0.55, "urn:air:krea2:lora:civitai:1@2": 1.2})
        inp = step_input(civ.build_workflow(payload))
        self.assertEqual(inp["loras"], {air: 0.55, "urn:air:krea2:lora:civitai:1@2": 1.2})
        code, data = civ.CivitaiProvider().generate(payload)
        self.assertEqual(code, 200, data)
        self.assertEqual(data["submittedInput"]["loras"][air], 0.55)

    def test_empty_service_id_is_hard_error(self):
        for sid in ("", "   "):
            payload = krea_payload()
            payload["serviceId"] = sid
            self.transport.reset_mock()
            with self.assertRaises(ValueError) as raised:
                civ.build_workflow(payload)
            self.assertIn("serviceId", str(raised.exception))
            self.assertNotIn("krea2/turbo", str(raised.exception))
            code, data = civ.CivitaiProvider().generate(payload)
            self.assertEqual(code, 400, data)
            self.transport.assert_not_called()

    def test_video_fal_keys_are_not_copied(self):
        hunyuan = {
            "serviceId": "video/hunyuan",
            "prompt": "a running horse",
            "width": 864,
            "height": 480,
            "cfgScale": 7.5,
            "duration": 8,
            "steps": 20,
        }
        for key in ("last_image", "image_url"):
            payload = dict(hunyuan, **{key: "https://example.invalid/frame.jpg"})
            self.transport.reset_mock()
            with self.assertRaises(ValueError) as raised:
                civ.build_workflow(payload)
            msg = str(raised.exception)
            self.assertIn(key, msg)
            self.assertTrue("Fal" in msg or "官方" in msg)
            code, data = civ.CivitaiProvider().generate(payload)
            self.assertEqual(code, 400, data)
            self.transport.assert_not_called()
        with self.assertRaises(ValueError) as raised:
            civ.build_workflow(dict(hunyuan, lastFrame="https://example.invalid/last.jpg"))
        self.assertTrue("尾帧" in str(raised.exception) or "lastFrame" in str(raised.exception) or "不接受" in str(raised.exception))

        ok = dict(hunyuan)
        inp = step_input(civ.build_workflow(ok))
        self.assertEqual(inp["duration"], 8)
        self.assertNotIn("last_image", inp)
        self.assertNotIn("image_url", inp)
        self.assertNotIn("resolution", inp)

    def test_minimax_official_first_last_frame_fields(self):
        payload = {
            "serviceId": "video/minimax-h3-comfy/imageToVideo",
            "prompt": "walk",
            "duration": 5,
            "firstFrame": "https://example.invalid/first.jpg",
            "lastFrame": "https://example.invalid/last.jpg",
            "seed": 9,
        }
        inp = step_input(civ.build_workflow(payload))
        self.assertEqual(inp["engine"], "minimax-h3-comfy")
        self.assertEqual(inp["firstFrame"], "https://example.invalid/first.jpg")
        self.assertEqual(inp["lastFrame"], "https://example.invalid/last.jpg")
        self.assertEqual(inp["duration"], 5)
        self.assertNotIn("last_image", inp)
        self.assertNotIn("image_url", inp)
        self.transport.reset_mock()
        with self.assertRaises(ValueError):
            civ.build_workflow(dict(payload, last_image="https://example.invalid/fal.jpg"))
        code, data = civ.CivitaiProvider().generate(dict(payload, image_url="https://example.invalid/fal.jpg"))
        self.assertEqual(code, 400, data)
        self.transport.assert_not_called()

    def test_wan_v22_uses_official_resolution_and_source_image(self):
        payload = {
            "serviceId": "video/wan/v2.2/fal/image-to-video",
            "prompt": "wan i2v",
            "cfgScale": 4,
            "duration": 5,
            "steps": 20,
            "resolution": "720p",
            "firstFrame": "https://example.invalid/first.jpg",
        }
        inp = step_input(civ.build_workflow(payload))
        self.assertEqual(inp["engine"], "wan")
        self.assertEqual(inp["version"], "v2.2")
        self.assertEqual(inp["resolution"], "720p")
        self.assertEqual(inp["sourceImage"], "https://example.invalid/first.jpg")
        self.assertNotIn("startImage", inp)
        self.assertNotIn("endImage", inp)
        self.assertNotIn("last_image", inp)
        self.assertNotIn("image_url", inp)
        self.transport.reset_mock()
        with self.assertRaises(ValueError) as raised:
            civ.build_workflow(dict(payload, resolution="1080p"))
        self.assertIn("1080p", str(raised.exception))
        code, data = civ.CivitaiProvider().generate(dict(payload, last_image="https://example.invalid/last.jpg"))
        self.assertEqual(code, 400, data)
        self.transport.assert_not_called()

    def test_kling_duration_uses_official_string_enum(self):
        payload = {
            "serviceId": "video/kling",
            "prompt": "kling",
            "cfgScale": 0.5,
            "duration": 5,
        }
        inp = step_input(civ.build_workflow(payload))
        self.assertEqual(inp["duration"], "5")
        self.assertIsInstance(inp["duration"], str)
        inp10 = step_input(civ.build_workflow(dict(payload, duration="10")))
        self.assertEqual(inp10["duration"], "10")
        self.transport.reset_mock()
        with self.assertRaises(ValueError) as raised:
            civ.build_workflow(dict(payload, duration=8))
        self.assertIn("8", str(raised.exception))
        code, data = civ.CivitaiProvider().generate(dict(payload, duration=8))
        self.assertEqual(code, 400, data)
        self.transport.assert_not_called()

    def test_denoise_maps_to_official_denoiseStrength_on_variant(self):
        payload = {
            "serviceId": "image/comfy/anima/createVariant",
            "prompt": "variant",
            "firstFrame": "https://example.invalid/src.jpg",
            "denoise": 0.4,
            "width": 1024,
            "height": 768,
            "steps": 30,
            "cfgScale": 4,
        }
        inp = step_input(civ.build_workflow(payload))
        self.assertEqual(inp["denoiseStrength"], 0.4)
        self.assertNotIn("denoise", inp)
        self.assertEqual(inp["image"], "https://example.invalid/src.jpg")
        self.transport.reset_mock()
        with self.assertRaises(ValueError):
            civ.build_workflow(dict(payload, denoise=1.5))
        code, data = civ.CivitaiProvider().generate(dict(payload, denoise=1.5))
        self.assertEqual(code, 400, data)
        self.transport.assert_not_called()

    def test_klein_9b_is_not_the_4b_capability(self):
        nine = {
            "serviceId": "image/flux2/klein/createImage/9b",
            "prompt": "klein 9b",
            "width": 1024,
            "height": 768,
            "quantity": 3,
            "steps": 20,
            "cfgScale": 5,
        }
        inp9 = step_input(civ.build_workflow(nine))
        self.assertEqual(inp9.get("modelVersion"), "9b")
        self.assertEqual(inp9["model"], "klein")
        four = {
            "serviceId": "image/flux2/klein/createImage/4b",
            "prompt": "klein 4b",
            "width": 1024,
            "height": 768,
            "quantity": 3,
            "steps": 20,
            "cfgScale": 5,
        }
        inp4 = step_input(civ.build_workflow(four))
        self.assertEqual(inp4.get("modelVersion"), "4b")
        self.assertNotEqual(inp9.get("modelVersion"), inp4.get("modelVersion"))

    def test_whatif_cancel_and_status_keep_orchestration_contract(self):
        code, data = civ.CivitaiProvider().whatif(krea_payload())
        self.assertEqual(code, 200, data)
        args, kwargs = self.transport.call_args
        url = args[0]
        method = kwargs.get("method") or (args[1] if len(args) > 1 else None)
        body = kwargs.get("body") if "body" in kwargs else (args[2] if len(args) > 2 else None)
        self.assertEqual(method, "POST")
        self.assertIn("orchestration.civitai.com", url)
        self.assertIn("/v2/consumer/workflows", url)
        self.assertIn("whatif=true", url)
        self.assertEqual(body["steps"][0]["input"]["seed"], 475720515768790)
        self.assertEqual(data["submittedInput"]["seed"], 475720515768790)
        self.assertEqual(data["submittedInput"]["loras"][KLEA_AIR], 0.8)

        self.transport.reset_mock()
        with self.assertRaises(ValueError):
            civ.build_workflow(krea_payload(width=32))
        code, data = civ.CivitaiProvider().whatif(krea_payload(width=32))
        self.assertEqual(code, 400, data)
        self.transport.assert_not_called()

        self.transport.reset_mock()
        code, data = civ.CivitaiProvider().job_status("civitai|wf-offline")
        self.assertEqual(code, 200, data)
        args, kwargs = self.transport.call_args
        self.assertIn("/v2/consumer/workflows/wf-offline", args[0])
        method = kwargs.get("method") or (args[1] if len(args) > 1 else "GET")
        self.assertEqual(method, "GET")

        self.transport.reset_mock()
        code, data = civ.CivitaiProvider().cancel_job("civitai|wf-offline")
        self.assertEqual(code, 200, data)
        self.assertEqual(data.get("status"), "canceled")
        self.assertEqual(data.get("backend"), "civitai")
        args, kwargs = self.transport.call_args
        self.assertIn("/v2/consumer/workflows/wf-offline", args[0])
        self.assertEqual(kwargs.get("method") or args[1], "DELETE")


if __name__ == "__main__":
    unittest.main(verbosity=2)
