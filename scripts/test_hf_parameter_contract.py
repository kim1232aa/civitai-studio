#!/usr/bin/env python3
"""Offline HF contracts: python3 scripts/test_hf_parameter_contract.py.

Mapping reference: huggingface/huggingface_hub, inference/_providers/{fal_ai,
nscale,together}.py and inference/_generated/types/text_to_image.py.
All transport, credentials and media writes are replaced; never submits upstream.
"""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from providers import huggingface as hf


class HFContract(unittest.TestCase):
    def setUp(self):
        self.enterContext(patch("socket.socket", side_effect=AssertionError("offline only")))
        self.enterContext(patch("socket.getaddrinfo", side_effect=AssertionError("offline only")))
        self.enterContext(patch.object(hf, "hf_keys", return_value=["offline-token"]))
        self.enterContext(patch.object(hf, "hf_key", return_value="offline-token"))
        self.transport = self.enterContext(patch.object(hf, "json_call", return_value=(200, {"images": []})))
        self.enterContext(patch.object(hf, "raw_call", side_effect=AssertionError("unexpected bytes call")))
        self.save_images = self.enterContext(patch.object(hf, "_save_json_images", return_value=[{"url": "/out/offline.png"}]))
        self.enterContext(patch.object(hf, "save_bytes", side_effect=AssertionError("unexpected media write")))
        self.enterContext(patch.object(hf, "load_items", return_value=[]))

    def test_seed_and_zero_guidance_are_not_rewritten(self):
        params = hf._prompt_body({"seed": 2147483647, "cfgScale": 0, "steps": "8"})
        self.assertEqual(params, {"seed": 2147483647, "guidance_scale": 0, "num_inference_steps": 8})
        self.assertEqual(hf._prompt_body({"seed": -1})["seed"], -1)
        # Official HF seed is integer with no max; sample 134923572 must pass through.
        self.assertEqual(hf._prompt_body({"seed": 467475143677094})["seed"], 467475143677094)
        self.assertEqual(hf._prompt_body({"seed": 475720515768790})["seed"], 475720515768790)
        with self.assertRaises(ValueError):
            hf._prompt_body({"seed": -2})

    def test_bad_numeric_input_is_not_dropped_or_truncated(self):
        for field, value in (("seed", True), ("seed", 1.5), ("steps", "abc"),
                             ("width", 1024.5), ("height", 0), ("cfgScale", float("nan"))):
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                hf._prompt_body({field: value})

    def test_no_invented_route_and_no_turbo_wavespeed(self):
        self.assertEqual(hf._provider_candidates({}, "org/model", {}), [])
        self.assertNotIn("wavespeed", hf._PREF)
        mapping = {"wavespeed": {"status": "live", "providerId": "wavespeed-ai/z-image/turbo"}}
        self.assertEqual(hf._provider_candidates(mapping, "Tongyi-MAI/Z-Image-Turbo", {}), [])

    def test_nonlive_or_wrong_task_routes_are_not_candidates(self):
        mapping = {
            "fal-ai": {"status": "staging", "providerId": "fal-ai/flux/dev"},
            "nscale": {"status": "live", "providerId": "org/chat", "task": "conversational"},
        }
        self.assertEqual(hf._provider_candidates(mapping, "org/model", {"task": "text-to-image"}), [])

    def test_fal_failure_never_submits_to_a_second_route(self):
        mapping = {
            "fal-ai": {"status": "live", "providerId": "fal-ai/flux/dev"},
            "nscale": {"status": "live", "providerId": "org/flux"},
        }
        self.transport.return_value = (422, {"error": "original rejection"})
        with patch.object(hf, "inference_mapping", return_value=mapping):
            code, data = hf.HuggingFaceProvider().generate({"serviceId": "org/flux", "prompt": "x"})
        self.assertEqual(code, 422)
        self.assertEqual(data["error"], "original rejection")
        self.assertEqual(self.transport.call_count, 1)

    def test_402_retries_next_hf_key_not_another_route(self):
        mapping = {
            "fal-ai": {"status": "live", "providerId": "fal-ai/flux/dev", "task": "text-to-image"},
            "nscale": {"status": "live", "providerId": "org/flux"},
        }

        def transport(url, method="GET", headers=None, body=None, timeout=90):
            auth = (headers or {}).get("Authorization") or ""
            if "key-dead" in auth:
                return 402, {"error": "You have depleted your monthly included credits."}
            return 200, {"images": [{"url": "https://example.invalid/ok.png"}]}

        self.transport.side_effect = transport
        with patch.object(hf, "hf_keys", return_value=["key-dead", "key-live"]), \
                patch.object(hf, "inference_mapping", return_value=mapping):
            code, data = hf.HuggingFaceProvider().generate({"serviceId": "org/flux", "prompt": "x"})
        self.assertEqual(code, 200, data)
        self.assertEqual(data.get("status"), "succeeded")
        self.assertEqual(self.transport.call_count, 2)
        auths = [c.kwargs.get("headers", {}).get("Authorization") for c in self.transport.call_args_list]
        self.assertEqual(auths, ["Bearer key-dead", "Bearer key-live"])

    def test_422_does_not_burn_a_second_hf_key(self):
        mapping = {"fal-ai": {"status": "live", "providerId": "fal-ai/flux/dev", "task": "text-to-image"}}
        self.transport.return_value = (422, {"error": "HTTP 422"})
        with patch.object(hf, "hf_keys", return_value=["key-a", "key-b"]), \
                patch.object(hf, "inference_mapping", return_value=mapping):
            code, data = hf.HuggingFaceProvider().generate({"serviceId": "org/flux", "prompt": "x"})
        self.assertEqual(code, 422, data)
        self.assertEqual(self.transport.call_count, 1)

    def test_lora_weights_and_all_entries_preserved(self):
        loras = [{"path": f"https://example.invalid/{n}.safetensors", "scale": -0.25}
                 for n in range(4)]
        body = {}
        hf._force_loras(body, {"loras": loras})
        self.assertEqual(body["loras"], loras)

    def test_invalid_lora_is_not_silently_removed(self):
        for rows in ([{"air": "urn:air:unresolved"}],
                     [{"path": "https://example.invalid/a", "scale": "oops"}],
                     [{"path": "https://example.invalid/a", "scale": True}],
                     "https://example.invalid/a"):
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                hf._force_loras({}, {"loras": rows})

    def test_missing_lora_scale_is_omitted_not_defaulted(self):
        for rows in (
            [{"path": "org/lora"}],
            [{"path": "https://example.invalid/a.safetensors", "scale": None}],
            [{"path": "org/lora", "strength": None, "weight": None}],
            ["org/lora"],
        ):
            with self.subTest(rows=rows):
                body = {}
                hf._force_loras(body, {"loras": rows})
                self.assertTrue(body.get("loras"))
                for item in body["loras"]:
                    self.assertNotIn("scale", item)
                    self.assertNotEqual(item.get("scale"), 1.0)

    def test_together_uses_its_image_schema_not_nscale_size(self):
        _, _, body = hf._call_openai("together", "org/model", {
            "prompt": " keep spaces ", "seed": 91, "negativePrompt": "blur",
            "width": 960, "height": 1440, "steps": 28, "cfgScale": 3.5, "quantity": 2,
        }, "offline-token", 1)
        self.assertEqual(body, {
            "model": "org/model", "prompt": " keep spaces ", "response_format": "base64",
            "seed": 91, "negative_prompt": "blur", "width": 960, "height": 1440,
            "steps": 28, "guidance_scale": 3.5, "n": 2,
        })

    def test_nscale_keeps_seed_and_rejects_unwired_parameters_before_post(self):
        _, _, body = hf._call_openai("nscale", "org/model", {
            "prompt": "x", "seed": 91, "width": 960, "height": 1440, "quantity": 2,
        }, "offline-token", 1)
        self.assertEqual(body["seed"], 91)
        self.assertEqual(body["n"], 2)
        self.assertEqual(body["size"], "960x1440")
        self.transport.reset_mock()
        with self.assertRaises(ValueError):
            hf._call_openai("nscale", "org/model", {
                "prompt": "x", "steps": 8, "loras": [{"path": "org/lora"}],
            }, "offline-token", 1)
        self.transport.assert_not_called()

    def test_fal_extra_fields_preserved_without_lora_clipping(self):
        with patch("providers.fal.find_model", return_value={}):
            _, _, body = hf._call_fal("fal-ai", "fal-ai/krea-2/turbo/lora", {
                "prompt": "x", "quantity": 2, "aspectRatio": "3:2", "resolution": "1080p",
                "duration": 5, "denoise": 0.375,
                "loras": [{"path": "org/lora", "scale": -0.25}],
            }, "offline-token", 1)
        self.assertEqual(body["num_images"], 2)
        self.assertEqual(body["aspect_ratio"], "3:2")
        self.assertEqual(body["resolution"], "1080p")
        self.assertEqual(body["duration"], 5)
        self.assertEqual(body["strength"], 0.375)
        self.assertEqual(body["loras"], [{"path": "org/lora", "scale": -0.25}])

    def test_bytes_does_not_ignore_loras_or_invent_video_frames(self):
        for payload, spec in (({"loras": [{"path": "org/lora"}]}, {}),
                              ({"duration": 5}, {"task": "text-to-video"})):
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                hf._call_bytes("org/model", payload, spec, "offline-token", 1)

    def test_fal_references_never_silently_disappear(self):
        for pid, payload in (
            ("fal-ai/text-to-image", {"sourceImage": "https://example.invalid/a.png"}),
            ("fal-ai/model/edit", {"images": [f"https://example.invalid/{n}.png" for n in range(10)]}),
            ("fal-ai/model/edit", {"image_url": "not-a-url"}),
        ):
            with self.subTest(pid=pid, payload=payload), patch("providers.fal.find_model", return_value={}), self.assertRaises(ValueError):
                hf._call_fal("fal-ai", pid, payload, "offline-token", 1)
        self.transport.assert_not_called()

    def test_generate_cannot_invent_reference_support_from_the_payload_task(self):
        # Exercise generate(), not just _call_fal(): generate injects inferred task.
        mapping = {"fal-ai": {"status": "live", "providerId": "fal-ai/text-to-image"}}
        for extra in ({"sourceImage": "https://example.invalid/a.png"},
                      {"task": "image-to-image", "sourceImage": "https://example.invalid/a.png"}):
            with self.subTest(extra=extra), patch.object(hf, "inference_mapping", return_value=mapping), \
                    patch("providers.fal.find_model", return_value={}):
                code, data = hf.HuggingFaceProvider().generate({
                    "serviceId": "org/model", "prompt": "x", **extra,
                })
            self.assertEqual(code, 400, data)
            self.transport.assert_not_called()
            self.save_images.assert_not_called()

    def test_mapping_adapter_weights_are_part_of_the_selected_hub_model(self):
        mapping = {"fal-ai": {
            "status": "live", "providerId": "fal-ai/flux-lora", "task": "text-to-image",
            "adapterWeightsPath": "weights/adapter.safetensors",
        }}
        with patch.object(hf, "inference_mapping", return_value=mapping):
            code, data = hf.HuggingFaceProvider().generate({"serviceId": "org/adapter", "prompt": "x"})
        self.assertEqual(code, 200, data)
        self.assertEqual(data["submittedInput"]["loras"], [{
            "path": "https://huggingface.co/org/adapter/resolve/main/weights/adapter.safetensors",
        }])  # mapped adapter omits scale — never invent 1.0

    def test_trusted_mapping_keeps_reference_support_for_an_opaque_endpoint(self):
        mapping = {"fal-ai": {
            "status": "live", "providerId": "fal-ai/opaque-endpoint", "task": "image-to-image",
        }}
        with patch.object(hf, "inference_mapping", return_value=mapping), \
                patch("providers.fal.find_model", return_value={}):
            code, data = hf.HuggingFaceProvider().generate({
                "serviceId": "org/model", "prompt": "x", "sourceImage": "https://example.invalid/a.png",
            })
        self.assertEqual(code, 200, data)
        self.transport.assert_called_once()
        self.assertEqual(self.transport.call_args.kwargs["body"]["image_url"], "https://example.invalid/a.png")
        self.assertEqual(data["submittedInput"], self.transport.call_args.kwargs["body"])

    def test_numeric_resolution_is_encoded_and_not_overwritten(self):
        params = hf._prompt_body({"resolution": "960x1440"})
        self.assertEqual(params, {"width": 960, "height": 1440})
        with self.assertRaises(ValueError):
            hf._prompt_body({"resolution": "960x1440", "width": 1024, "height": 1024})

    def test_resolution_and_mapping_lora_are_in_actual_post_and_submitted_input(self):
        mapping = {"fal-ai": {
            "status": "live", "providerId": "fal-ai/flux-lora", "task": "text-to-image",
            "adapterWeightsPath": "weights/adapter.safetensors",
        }}
        with patch.object(hf, "inference_mapping", return_value=mapping), \
                patch("providers.fal.find_model", return_value={
                    "required": ["prompt"], "optional": ["image_size", "loras", "guidance_scale"],
                }):
            code, data = hf.HuggingFaceProvider().generate({
                "serviceId": "org/adapter", "prompt": " keep spaces ", "resolution": "960x1440",
                "cfgScale": 0, "loras": [{"path": "https://example.invalid/extra.safetensors", "scale": -0.25}],
            })
        self.assertEqual(code, 200, data)
        self.transport.assert_called_once()
        sent = self.transport.call_args.kwargs["body"]
        self.assertEqual(sent, {
            "prompt": " keep spaces ", "image_size": {"width": 960, "height": 1440}, "guidance_scale": 0,
            "loras": [
                {"path": "https://huggingface.co/org/adapter/resolve/main/weights/adapter.safetensors"},
                {"path": "https://example.invalid/extra.safetensors", "scale": -0.25},
            ],
        })
        self.assertEqual(data["submittedInput"], sent)

    def test_upstream_json_error_is_not_a_success(self):
        for route in ("fal-ai", "nscale", "together", "hf-inference"):
            self.transport.reset_mock()
            self.transport.return_value = (200, {"error": "generation failed"})
            mapping = {route: {"status": "live", "providerId": "org/model", "task": "text-to-image"}}
            with self.subTest(route=route), patch.object(hf, "inference_mapping", return_value=mapping), \
                    patch("providers.fal.find_model", return_value={}), \
                    patch.object(hf, "raw_call", return_value=(
                        200, b'{"error":"generation failed"}', "application/json",
                    )) as raw:
                code, data = hf.HuggingFaceProvider().generate({"serviceId": "org/model", "prompt": "x"})
                self.assertGreaterEqual(code, 400, data)
                self.assertEqual(data["error"], "generation failed")
                self.assertEqual(self.transport.call_count + raw.call_count, 1)
                self.save_images.assert_not_called()

    def test_hub_search_does_not_follow_next_links(self):
        calls = []
        next_url = "https://huggingface.co/api/models?search=krea&inference_provider=all&limit=50&cursor=next"

        def one_page(url):
            calls.append(url)
            if "cursor=" in url:
                raise AssertionError("catalog must not follow Link rel=next")
            return (200, [
                {"id": "org/a", "pipeline_tag": "text-to-image"},
                {"id": "org/skip", "pipeline_tag": "text-classification"},
                {"id": "org/b", "pipeline_tag": "image-to-image",
                 "inferenceProviderMapping": [
                     {"provider": "fal-ai", "status": "live", "providerId": "fal-ai/x", "task": "image-to-image"},
                 ]},
            ], next_url)

        with patch.object(hf, "_hf_list_page", side_effect=one_page):
            items, stats = hf._fetch_hf_catalog("krea")
        self.assertEqual(len(calls), 1)
        self.assertIn("search=krea", calls[0])
        self.assertIn("inference_provider=all", calls[0])
        self.assertIn("limit=50", calls[0])
        self.assertNotIn("limit=1000", calls[0])
        self.assertEqual([x["id"] for x in items], ["org/a", "org/b"])
        self.assertEqual(stats["pages"], 1)
        self.assertTrue(stats["hasMore"])
        self.assertEqual(stats["nextPage"], 2)
        self.assertFalse(stats["complete"])

    def test_model_capability_is_task_and_route_scoped_unknown_is_not_support(self):
        row = hf._hf_row(
            "org/model", "model", "text-to-image",
            mapping={"nscale": {"status": "live", "providerId": "org/model"}},
        )
        caps = row["parameterCapabilities"]
        self.assertEqual(caps["task"], "text-to-image")
        self.assertIn("nscale", caps["channels"])
        self.assertEqual(caps["channels"]["nscale"]["callability"], "unknown")
        self.assertNotIn("loras", caps["channels"]["nscale"]["supported"])

    def test_queue_submission_and_polling_do_not_masquerade_as_saved_media(self):
        mapping = {"fal-ai": {"status": "live", "providerId": "fal-ai/model/image-to-video", "task": "image-to-video"}}
        responses = [
            (200, {"request_id": "offline-queue", "status": "IN_QUEUE",
                   "response_url": "https://queue.fal.run/fal-ai/model/requests/offline-queue",
                   "status_url": "https://queue.fal.run/fal-ai/model/requests/offline-queue/status"}),
            (200, {"status": "IN_PROGRESS"}),
            (200, {"status": "COMPLETED"}),
            (200, {"video": {"url": "https://example.invalid/result.mp4"}}),
        ]
        self.transport.side_effect = responses
        with patch.object(hf, "inference_mapping", return_value=mapping), patch("providers.fal.find_model", return_value={}):
            code, data = hf.HuggingFaceProvider().generate({
                "serviceId": "org/video", "kind": "video", "firstFrame": "https://example.invalid/frame.png",
            })
        self.assertEqual(code, 200, data)
        self.assertEqual(data["status"], "pending")
        self.assertNotIn("saved", data)
        self.assertTrue(self.transport.call_args.args[0].endswith("?_subdomain=queue"))
        _, running = hf.HuggingFaceProvider().job_status(data["id"])
        self.assertEqual(running["status"], "processing")
        _, complete = hf.HuggingFaceProvider().job_status(data["id"])
        self.assertEqual(complete["status"], "succeeded")
        self.assertTrue(complete["saved"])
        self.assertEqual([c.kwargs.get("method", "GET") for c in self.transport.call_args_list],
                         ["POST", "GET", "GET", "GET"])
        self.assertTrue(all(c.args[0].startswith(hf.ROUTER + "/fal-ai/") for c in self.transport.call_args_list))
        poll_urls = [c.args[0] for c in self.transport.call_args_list if c.kwargs.get("method", "GET") == "GET"]
        self.assertTrue(poll_urls)
        self.assertTrue(all("/fal-ai/fal-ai/model/requests/offline-queue" in u for u in poll_urls), poll_urls)

    def test_queue_url_matches_official_router_fal_ai_prefix(self):
        got = hf._queue_url("https://queue.fal.run/fal-ai/qwen-image-edit/requests/abc")
        self.assertEqual(got, hf.ROUTER + "/fal-ai/fal-ai/qwen-image-edit/requests/abc?_subdomain=queue")
        got = hf._queue_url("https://router.huggingface.co/fal-ai/fal-ai/qwen-image-edit/requests/abc")
        self.assertEqual(got, hf.ROUTER + "/fal-ai/fal-ai/qwen-image-edit/requests/abc?_subdomain=queue")

    def test_unknown_job_is_not_reported_succeeded(self):
        code, data = hf.HuggingFaceProvider().job_status("hf|sync|never-submitted")
        self.assertEqual(code, 404, data)

    def test_queue_cannot_redirect_hf_token_to_arbitrary_host(self):
        self.transport.return_value = (200, {"request_id": "bad",
            "response_url": "https://example.invalid/steal", "status_url": "https://example.invalid/steal"})
        mapping = {"fal-ai": {"status": "live", "providerId": "fal-ai/model", "task": "text-to-image"}}
        with patch.object(hf, "inference_mapping", return_value=mapping):
            code, data = hf.HuggingFaceProvider().generate({"serviceId": "org/model", "prompt": "x"})
        self.assertGreaterEqual(code, 400, data)
        self.transport.assert_called_once()


if __name__ == "__main__":
    unittest.main(verbosity=2)
