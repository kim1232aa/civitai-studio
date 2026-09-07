#!/usr/bin/env python3
"""Contract tests for the canvas project persistence/API slice."""

from __future__ import annotations

import json
import sys
import threading
import time
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import server  # noqa: E402
from canvas_store import CanvasStore  # noqa: E402


def request(base: str, method: str, path: str, body=None):
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(
        base + path,
        data=data,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    # ThreadingHTTPServer 线程启动存在竞态：窗口拉长到 ~4s，
    # 避免慢启动被误报为 ConnectionRefused（偶发 flake 会砸 D 门 exit 0）。
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
        except urllib.error.URLError:
            if attempt == 79:
                raise
            time.sleep(0.05)


def test_store_persists_project_canvas_shape():
    with TemporaryDirectory(dir=ROOT / ".test-tmp") as tmp:
        path = Path(tmp) / "projects.json"
        store = CanvasStore(path)
        project = store.create("分镜项目")
        assert project["name"] == "分镜项目"
        assert project["id"]
        assert project["activeCanvasId"]
        assert len(project["canvases"]) == 1
        canvas = project["canvases"][0]
        assert canvas["id"] == project["activeCanvasId"]
        assert canvas["nodes"] == []
        assert canvas["edges"] == []
        assert canvas["assetIds"] == []

        reloaded = CanvasStore(path)
        assert reloaded.get(project["id"]) == project


def test_http_crud_list_create_duplicate_rename_delete():
    with TemporaryDirectory(dir=ROOT / ".test-tmp") as tmp:
        server.canvas_store = CanvasStore(Path(tmp) / "projects.json")
        httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{httpd.server_address[1]}"
        try:
            status, payload = request(base, "GET", "/api/canvas-projects")
            assert status == 200
            assert payload == {"items": []}

            status, payload = request(
                base,
                "POST",
                "/api/canvas-projects",
                {"name": "镜头规划"},
            )
            assert status == 201
            original = payload["project"]
            project_id = original["id"]
            assert original["name"] == "镜头规划"

            status, payload = request(
                base,
                "PATCH",
                f"/api/canvas-projects/{project_id}",
                {"name": "镜头规划（第一版）"},
            )
            assert status == 200
            assert payload["project"]["name"] == "镜头规划（第一版）"

            status, payload = request(
                base,
                "POST",
                f"/api/canvas-projects/{project_id}/duplicate",
                {"name": "镜头规划副本"},
            )
            assert status == 201
            duplicate = payload["project"]
            assert duplicate["id"] != project_id
            assert duplicate["name"] == "镜头规划副本"
            assert duplicate["canvases"][0]["id"] != original["canvases"][0]["id"]

            status, payload = request(
                base, "DELETE", f"/api/canvas-projects/{project_id}"
            )
            assert status == 200
            assert payload == {"deleted": project_id}

            status, payload = request(base, "GET", "/api/canvas-projects")
            assert status == 200
            assert [item["id"] for item in payload["items"]] == [duplicate["id"]]
        finally:
            httpd.shutdown()
            thread.join(timeout=5)


def test_store_updates_empty_canvas_and_asset_binding():
    with TemporaryDirectory(dir=ROOT / ".test-tmp") as tmp:
        path = Path(tmp) / "projects.json"
        store = CanvasStore(path)
        project = store.create()
        canvas_id = project["activeCanvasId"]
        asset = {
            "id": "asset-imported-1",
            "kind": "image",
            "title": "相册资产",
            "url": "/out/imported-1.jpg",
            "sourceUrl": "https://civitai.red/user/AIImageStudio/images/141669899",
        }
        state = store.update_state(
            project["id"],
            {
                "activeCanvasId": canvas_id,
                "assets": [asset],
                "canvases": [
                    {
                        **project["canvases"][0],
                        "nodes": [{"id": "node-1", "kind": "asset", "assetId": asset["id"]}],
                        "assetIds": [asset["id"]],
                    }
                ],
                "script": {
                    "script": "一场雨夜追逐",
                    "scenes": "旧城区",
                    "characters": "林默",
                    "shots": "远景→近景",
                },
                "editor": {"content": "可编辑稿件"},
            },
        )
        assert state["assets"] == [asset]
        assert state["canvases"][0]["assetIds"] == [asset["id"]]
        assert state["canvases"][0]["nodes"][0]["assetId"] == asset["id"]
        assert state["script"]["scenes"] == "旧城区"
        assert state["editor"]["content"] == "可编辑稿件"
        assert CanvasStore(path).get(project["id"]) == state


def test_store_new_canvas_is_empty():
    with TemporaryDirectory(dir=ROOT / ".test-tmp") as tmp:
        store = CanvasStore(Path(tmp) / "projects.json")
        project = store.create("空白工作区")
        canvas = store.create_canvas(project["id"], "第二画布")
        assert canvas["name"] == "第二画布"
        assert canvas["nodes"] == []
        assert canvas["edges"] == []
        assert canvas["assetIds"] == []
        assert store.get(project["id"])["activeCanvasId"] == canvas["id"]


def test_http_persists_canvas_state_and_assets():
    with TemporaryDirectory(dir=ROOT / ".test-tmp") as tmp:
        server.canvas_store = CanvasStore(Path(tmp) / "projects.json")
        httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{httpd.server_address[1]}"
        try:
            status, payload = request(base, "POST", "/api/canvas-projects", {"name": "资产绑定"})
            assert status == 201
            project = payload["project"]
            project_id = project["id"]
            canvas_id = project["activeCanvasId"]
            asset = {
                "id": "asset-imported-2",
                "kind": "image",
                "title": "导入图像",
                "url": "/out/imported-2.jpg",
                "sourceUrl": "https://civitai.red/user/AIImageStudio/images/141669890",
            }
            status, payload = request(
                base,
                "PUT",
                f"/api/canvas-projects/{project_id}/state",
                {
                    "assets": [asset],
                    "canvases": [
                        {
                            **project["canvases"][0],
                            "nodes": [{"id": "node-2", "assetId": asset["id"]}],
                            "assetIds": [asset["id"]],
                        }
                    ],
                    "activeCanvasId": canvas_id,
                    "script": {"script": "", "scenes": "", "characters": "", "shots": ""},
                    "editor": {"content": ""},
                },
            )
            assert status == 200
            assert payload["project"]["assets"] == [asset]

            status, payload = request(
                base, "GET", f"/api/canvas-projects/{project_id}"
            )
            assert status == 200
            assert payload["project"]["canvases"][0]["assetIds"] == [asset["id"]]
        finally:
            httpd.shutdown()
            thread.join(timeout=5)


def test_http_put_replaces_whole_state_patch_merges():
    with TemporaryDirectory(dir=ROOT / ".test-tmp") as tmp:
        server.canvas_store = CanvasStore(Path(tmp) / "projects.json")
        httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{httpd.server_address[1]}"
        try:
            status, payload = request(base, "POST", "/api/canvas-projects", {"name": "PUT 语义"})
            assert status == 201
            project = payload["project"]
            project_id = project["id"]
            canvas_id = project["activeCanvasId"]
            canvas_two = {
                **project["canvases"][0],
                "id": "canvas-put-2",
                "name": "第二画布",
                "nodes": [],
                "edges": [],
                "assetIds": [],
            }
            asset = {
                "id": "asset-put-1",
                "kind": "image",
                "title": "资产一",
                "url": "/out/put-1.jpg",
                "sourceUrl": "https://civitai.red/user/AIImageStudio/images/141669901",
            }

            # PUT = 整状态替换：完整五件套写入
            status, payload = request(
                base,
                "PUT",
                f"/api/canvas-projects/{project_id}/state",
                {"assets": [asset], "canvases": [project["canvases"][0]], "activeCanvasId": canvas_id,
                 "script": {"script": "", "scenes": "", "characters": "", "shots": ""}, "editor": {"content": ""}},
            )
            assert status == 200
            assert payload["project"]["assets"] == [asset]

            # PATCH = 合并：未提交 assets 时旧资产必须保留
            status, payload = request(
                base,
                "PATCH",
                f"/api/canvas-projects/{project_id}/state",
                {"canvases": [canvas_two], "activeCanvasId": canvas_two["id"]},
            )
            assert status == 200
            assert payload["project"]["assets"] == [asset], "PATCH 合并不应清空未提交字段"

            # PUT 缺字段 = 400，不许静默合并；裸项目路径 = 400
            status, payload = request(
                base,
                "PUT",
                f"/api/canvas-projects/{project_id}/state",
                {"canvases": [canvas_two], "activeCanvasId": canvas_two["id"]},
            )
            assert status == 400
            status, payload = request(
                base,
                "PUT",
                f"/api/canvas-projects/{project_id}",
                {"assets": [asset], "canvases": [canvas_two], "activeCanvasId": canvas_two["id"]},
            )
            assert status == 400

            # PUT 显式清空 assets：整替换生效（与上面的 PATCH 保留形成对照）
            status, payload = request(
                base,
                "PUT",
                f"/api/canvas-projects/{project_id}/state",
                {"assets": [], "canvases": [canvas_two], "activeCanvasId": canvas_two["id"],
                 "script": {"script": "", "scenes": "", "characters": "", "shots": ""}, "editor": {"content": ""}},
            )
            assert status == 200
            assert payload["project"]["assets"] == []
            assert [c["id"] for c in payload["project"]["canvases"]] == ["canvas-put-2"]

            status, payload = request(base, "GET", f"/api/canvas-projects/{project_id}")
            assert status == 200
            assert payload["project"]["assets"] == []
        finally:
            httpd.shutdown()
            thread.join(timeout=5)


def test_http_rejects_invalid_project_operations():
    with TemporaryDirectory(dir=ROOT / ".test-tmp") as tmp:
        server.canvas_store = CanvasStore(Path(tmp) / "projects.json")
        httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{httpd.server_address[1]}"
        try:
            status, payload = request(
                base, "POST", "/api/canvas-projects", {"name": "   "}
            )
            assert status == 400
            assert "error" in payload

            status, payload = request(
                base,
                "PATCH",
                "/api/canvas-projects/not-found",
                {"name": "新名称"},
            )
            assert status == 404
            assert "error" in payload
        finally:
            httpd.shutdown()
            thread.join(timeout=5)


if __name__ == "__main__":
    base = ROOT / ".test-tmp"
    base.mkdir(exist_ok=True)
    tests = [
        test_store_persists_project_canvas_shape,
        test_store_updates_empty_canvas_and_asset_binding,
        test_store_new_canvas_is_empty,
        test_http_crud_list_create_duplicate_rename_delete,
        test_http_persists_canvas_state_and_assets,
        test_http_put_replaces_whole_state_patch_merges,
        test_http_rejects_invalid_project_operations,
    ]
    for test in tests:
        test()
        print(f"ok {test.__name__}")
    print(f"result {len(tests)} / {len(tests)}")
