#!/usr/bin/env python3
"""Regression tests for the canvas NanoGPT text-generation path.

Run directly: python3 scripts/test_nanogpt_text_generation.py
No paid or external requests: the NanoGPT transport is replaced by a tiny
response fixture, while the real graph compiler and provider code execute.
"""
from __future__ import annotations

import json
import sys
import threading
import time
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from providers.graph_compile import compile_graph  # noqa: E402
from providers import nanogpt as nano  # noqa: E402
from providers.nanogpt import CHAT_COMPLETIONS, NanoGptProvider  # noqa: E402

JS = (ROOT / "static" / "storyboard.js").read_text(encoding="utf-8")


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def text_graph(service="chat/gpt-4o-mini", prompt="请写三句镜头旁白"):
    return {
        "backend": "nano-gpt",
        "nodes": [
            {"id": "p1", "op": "prompt", "params": {"text": prompt}},
            {"id": "t1", "op": "text", "params": {"serviceId": service}},
        ],
        "edges": [
            {"from": "p1", "fromPort": "prompt", "to": "t1", "toPort": "prompt"},
        ],
    }


def test_canvas_text_compiles_without_resolution():
    result = compile_graph(text_graph())
    check(result.get("ok") is True, result)
    check(result.get("execute") == "single", result)
    payload = result.get("payload") or {}
    check(payload.get("kind") == "text", payload)
    check(payload.get("recipe") == "text", payload)
    check(payload.get("serviceId") == "chat/gpt-4o-mini", payload)
    check(payload.get("prompt") == "请写三句镜头旁白", payload)
    check("resolution" not in payload, payload)
    check((result.get("stages") or [{}])[0].get("produces") == "text", result)


def test_canvas_text_calls_chat_and_returns_text():
    calls = []
    originals = {
        "nano_key": nano.nano_key,
        "find_spec": nano.find_spec,
        "json_call": nano.json_call,
    }
    nano.nano_key = lambda: "fixture-key"
    nano.find_spec = lambda mid: {
        "id": mid,
        "category": "text",
        "task": "text-generation",
        "supported_parameters": {},
    }

    def fake_json_call(url, method="GET", headers=None, body=None, timeout=90):
        calls.append({"url": url, "method": method, "body": body})
        return 200, {
            "choices": [{"message": {"content": "夜色落下，镜头慢慢推近。"}}],
        }

    nano.json_call = fake_json_call
    try:
        payload = compile_graph(text_graph())["payload"]
        code, result = NanoGptProvider().generate(payload)
    finally:
        nano.nano_key = originals["nano_key"]
        nano.find_spec = originals["find_spec"]
        nano.json_call = originals["json_call"]

    check(code == 200, (code, result))
    check(result.get("ok") is True, result)
    check(result.get("status") == "succeeded", result)
    check(result.get("text") == "夜色落下，镜头慢慢推近。", result)
    check("没有 resolutions" not in str(result), result)
    check(len(calls) == 1, calls)
    check(calls[0]["url"] == CHAT_COMPLETIONS, calls)
    check(calls[0]["method"] == "POST", calls)
    body = calls[0]["body"]
    check(body.get("model") == "gpt-4o-mini", body)
    check(body.get("messages") == [{"role": "user", "content": "请写三句镜头旁白"}], body)
    check("resolution" not in body, body)
    check("input_references" not in body, body)


def test_text_payload_without_catalog_spec_still_chats():
    calls = []
    originals = {
        "nano_key": nano.nano_key,
        "find_spec": nano.find_spec,
        "json_call": nano.json_call,
    }
    nano.nano_key = lambda: "fixture-key"
    nano.find_spec = lambda mid: {"id": mid, "supported_parameters": {}, "capabilities": {}}

    def fake_json_call(url, method="GET", headers=None, body=None, timeout=90):
        calls.append(url)
        return 200, {"choices": [{"message": {"content": "旁白一行。"}}]}

    nano.json_call = fake_json_call
    try:
        code, result = NanoGptProvider().generate(
            {
                "backend": "nano-gpt",
                "serviceId": "z-ai/glm-5.3-flash",
                "kind": "text",
                "recipe": "text",
                "prompt": "写一句旁白",
            }
        )
    finally:
        nano.nano_key = originals["nano_key"]
        nano.find_spec = originals["find_spec"]
        nano.json_call = originals["json_call"]

    check(code == 200, (code, result))
    check(result.get("text") == "旁白一行。", result)
    check(calls == [CHAT_COMPLETIONS], calls)
    check("没有 resolutions" not in str(result), result)


def test_non_chat_provider_is_blocked_at_compile():
    graph = text_graph()
    graph["backend"] = "fal"
    result = compile_graph(graph)
    check(result.get("ok") is False, result)
    check(result.get("blocked") is True, result)
    check("不支持文本生成" in result.get("error", ""), result)


def test_text_node_rejects_image_wire():
    graph = text_graph()
    graph["nodes"].append({"id": "img", "op": "image", "params": {"url": "https://example.com/a.jpg"}})
    graph["edges"].append({"from": "img", "fromPort": "image", "to": "t1", "toPort": "image"})
    result = compile_graph(graph)
    check(result.get("ok") is False, result)
    check("无输入口" in result.get("error", ""), result)


def test_owns_service_includes_text_catalog():
    originals = {
        "fetch_catalog": nano.fetch_catalog,
        "fetch_text_catalog": nano.fetch_text_catalog,
    }
    nano.fetch_catalog = lambda force=False: []
    nano.fetch_text_catalog = lambda force=False: [
        {"id": "z-ai/glm-5.3-flash", "category": "text"}
    ]
    try:
        check(NanoGptProvider().owns_service("z-ai/glm-5.3-flash"), "text catalog id not owned")
        check(not NanoGptProvider().owns_service("ghost/not-a-nano-model"), "ghost id owned")
    finally:
        nano.fetch_catalog = originals["fetch_catalog"]
        nano.fetch_text_catalog = originals["fetch_text_catalog"]


def _http(base, method, path, body=None):
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(
        base + path,
        data=data,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    last_error = None
    for attempt in range(80):
        try:
            with urllib.request.urlopen(req, timeout=5) as response:
                raw = response.read()
                return response.status, json.loads(raw.decode()) if raw else None
        except urllib.error.HTTPError as exc:
            raw = exc.read()
            try:
                payload = json.loads(raw.decode())
            except json.JSONDecodeError:
                payload = {"raw": raw.decode("utf-8", "replace")}
            return exc.code, payload
        except urllib.error.URLError as exc:
            last_error = exc
            if attempt == 79:
                raise
            time.sleep(0.05)
    raise AssertionError(f"in-process server never accepted: {last_error}")


def test_http_compile_and_generate_return_text():
    import server  # noqa: WPS433 — in-process Handler, same pattern as other scripts

    calls = []
    originals = {
        "nano_key": nano.nano_key,
        "find_spec": nano.find_spec,
        "json_call": nano.json_call,
    }
    nano.nano_key = lambda: "fixture-key"
    nano.find_spec = lambda mid: {
        "id": mid,
        "category": "text",
        "task": "text-generation",
        "supported_parameters": {},
    }

    def fake_json_call(url, method="GET", headers=None, body=None, timeout=90):
        calls.append({"url": url, "body": body})
        return 200, {"choices": [{"message": {"content": "HTTP 文本生成结果。"}}]}

    nano.json_call = fake_json_call
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{httpd.server_address[1]}"
    try:
        code, compiled = _http(base, "POST", "/api/graph/compile", text_graph())
        check(code == 200, (code, compiled))
        check(compiled.get("ok") is True, compiled)
        payload = compiled.get("payload") or {}
        check(payload.get("kind") == "text", payload)
        check("resolution" not in payload, payload)
        code, result = _http(base, "POST", "/api/generate", payload)
        check(code == 200, (code, result))
        check(result.get("text") == "HTTP 文本生成结果。", result)
        check("没有 resolutions" not in str(result), result)
        check(calls and calls[0]["url"] == CHAT_COMPLETIONS, calls)
        check(calls[0]["body"].get("model") == "gpt-4o-mini", calls[0]["body"])
    finally:
        httpd.shutdown()
        thread.join(timeout=5)
        httpd.server_close()
        nano.nano_key = originals["nano_key"]
        nano.find_spec = originals["find_spec"]
        nano.json_call = originals["json_call"]


def test_js_text_mode_does_not_build_image_graph():
    check("async function generateText" in JS, "generateText missing")
    check('if (state.mode === "text") op = "text"' in JS, "buildGraph does not emit op=text")
    check("payload.kind !== \"text\"" in JS, "generateText must refuse non-text compile payload")
    check('op === "text"' in JS and "resolution" in JS, JS)
    check(
        'op !== "text"' in JS,
        "buildGraph still wires image/seed/lora onto text nodes",
    )
    check("const PH_TEXT" in JS, "text-mode placeholder missing")
    check("输入要生成的文本" in JS, "text-mode prompt copy missing")
    check("PH_STORY" in JS, "story placeholder must stay on story dock")


if __name__ == "__main__":
    tests = [
        test_canvas_text_compiles_without_resolution,
        test_canvas_text_calls_chat_and_returns_text,
        test_text_payload_without_catalog_spec_still_chats,
        test_non_chat_provider_is_blocked_at_compile,
        test_text_node_rejects_image_wire,
        test_owns_service_includes_text_catalog,
        test_http_compile_and_generate_return_text,
        test_js_text_mode_does_not_build_image_graph,
    ]
    failures = []
    for test in tests:
        try:
            test()
            print(f"ok {test.__name__}")
        except Exception as exc:  # keep direct-run output actionable
            failures.append((test.__name__, str(exc)))
            print(f"FAIL {test.__name__}: {exc}")
    if failures:
        raise SystemExit(1)
    print("PASS nanogpt-text-canvas 8/8")
