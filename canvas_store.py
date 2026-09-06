"""Persistent project/canvas storage for the storyboard workspace.

The store is deliberately independent of the HTTP layer so the UI can later
use the same model for project switching, canvas persistence, and asset
bindings without coupling storage to request handling.
"""

from __future__ import annotations

import copy
import json
import os
import tempfile
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = 1
DEFAULT_PROJECT_NAME = "未命名项目"
DEFAULT_CANVAS_NAME = "主画布"
MAX_PROJECT_NAME = 120


class CanvasStoreError(Exception):
    """Base class for expected storage errors."""


class CanvasNotFoundError(CanvasStoreError):
    """Raised when a project id does not exist."""


class CanvasValidationError(CanvasStoreError):
    """Raised when a project payload is invalid."""


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex}"


def _project_name(value: Any, *, default: str = DEFAULT_PROJECT_NAME) -> str:
    if value is None:
        value = default
    if not isinstance(value, str):
        raise CanvasValidationError("项目名称必须是文本")
    name = value.strip()
    if not name:
        raise CanvasValidationError("项目名称不能为空")
    if len(name) > MAX_PROJECT_NAME:
        raise CanvasValidationError(f"项目名称不能超过 {MAX_PROJECT_NAME} 个字符")
    return name


def _new_canvas(name: str = DEFAULT_CANVAS_NAME) -> dict[str, Any]:
    now = _now()
    return {
        "id": _new_id("canvas"),
        "name": name,
        "createdAt": now,
        "updatedAt": now,
        "nodes": [],
        "edges": [],
        "viewport": {"x": 0, "y": 0, "zoom": 1},
        "assetIds": [],
    }


def _normalize_asset(asset: Any, *, generate_id: bool = False) -> dict[str, Any]:
    if not isinstance(asset, dict):
        raise CanvasValidationError("资产必须是对象")
    result = copy.deepcopy(asset)
    asset_id = result.get("id")
    if asset_id is None and generate_id:
        asset_id = _new_id("asset")
    if not isinstance(asset_id, str) or not asset_id:
        raise CanvasValidationError("资产必须包含非空 id")
    result["id"] = asset_id
    return result


def _normalize_canvas(
    canvas: Any, *, generate_id: bool = False, default_name: str = DEFAULT_CANVAS_NAME
) -> dict[str, Any]:
    if not isinstance(canvas, dict):
        raise CanvasValidationError("画布必须是对象")
    result = copy.deepcopy(canvas)
    canvas_id = result.get("id")
    if canvas_id is None and generate_id:
        canvas_id = _new_id("canvas")
    if not isinstance(canvas_id, str) or not canvas_id:
        raise CanvasValidationError("画布必须包含非空 id")
    result["id"] = canvas_id
    result["name"] = _project_name(result.get("name"), default=default_name)
    for key in ("nodes", "edges", "assetIds"):
        if key in result and not isinstance(result[key], list):
            raise CanvasValidationError(f"画布字段 {key} 必须是数组")
    result.setdefault("nodes", [])
    result.setdefault("edges", [])
    asset_ids = result.get("assetIds") or []
    if any(not isinstance(asset_id, str) or not asset_id for asset_id in asset_ids):
        raise CanvasValidationError("画布资产绑定必须是非空 id")
    result["assetIds"] = list(dict.fromkeys(asset_ids))
    viewport = result.get("viewport")
    if viewport is None:
        result["viewport"] = {"x": 0, "y": 0, "zoom": 1}
    elif not isinstance(viewport, dict):
        raise CanvasValidationError("画布 viewport 必须是对象")
    result.setdefault("createdAt", _now())
    result["updatedAt"] = _now()
    return result


def _new_project(name: str) -> dict[str, Any]:
    now = _now()
    canvas = _new_canvas()
    return {
        "id": _new_id("project"),
        "name": name,
        "createdAt": now,
        "updatedAt": now,
        "activeCanvasId": canvas["id"],
        "canvases": [canvas],
        "assets": [],
    }


def _copy_with_new_ids(project: dict[str, Any], name: str) -> dict[str, Any]:
    """Deep-copy a project while keeping duplicated assets internally coherent."""
    duplicate = copy.deepcopy(project)
    now = _now()
    duplicate["id"] = _new_id("project")
    duplicate["name"] = name
    duplicate["createdAt"] = now
    duplicate["updatedAt"] = now

    asset_ids: dict[str, str] = {}
    for asset in duplicate.get("assets") or []:
        if not isinstance(asset, dict) or not asset.get("id"):
            continue
        old_id = str(asset["id"])
        new_id = _new_id("asset")
        asset_ids[old_id] = new_id
        asset["id"] = new_id

    canvas_ids: dict[str, str] = {}
    node_ids: dict[str, str] = {}
    for canvas in duplicate.get("canvases") or []:
        if not isinstance(canvas, dict):
            continue
        old_id = str(canvas.get("id") or "")
        new_id = _new_id("canvas")
        if old_id:
            canvas_ids[old_id] = new_id
        canvas["id"] = new_id
        canvas["createdAt"] = now
        canvas["updatedAt"] = now
        canvas["assetIds"] = [asset_ids.get(str(x), str(x)) for x in canvas.get("assetIds") or []]
        for node in canvas.get("nodes") or []:
            if not isinstance(node, dict) or not node.get("id"):
                continue
            old_node_id = str(node["id"])
            new_node_id = _new_id("node")
            node_ids[old_node_id] = new_node_id
            node["id"] = new_node_id
            for key in ("assetId", "sourceAssetId"):
                if node.get(key) is not None:
                    node[key] = asset_ids.get(str(node[key]), node[key])
            if isinstance(node.get("assetIds"), list):
                node["assetIds"] = [
                    asset_ids.get(str(x), str(x)) for x in node["assetIds"]
                ]
        for edge in canvas.get("edges") or []:
            if not isinstance(edge, dict):
                continue
            for key in (
                "from",
                "to",
                "source",
                "target",
                "fromId",
                "toId",
                "sourceId",
                "targetId",
            ):
                if edge.get(key) is not None:
                    edge[key] = node_ids.get(str(edge[key]), edge[key])

    active = str(project.get("activeCanvasId") or "")
    duplicate["activeCanvasId"] = canvas_ids.get(active) or (
        duplicate.get("canvases") or [{}]
    )[0].get("id")
    return duplicate


class CanvasStore:
    """Thread-safe JSON-backed project store with atomic writes."""

    def __init__(self, path: str | os.PathLike[str]):
        self.path = Path(path)
        self._lock = threading.RLock()

    def _empty_document(self) -> dict[str, Any]:
        return {"version": SCHEMA_VERSION, "projects": []}

    def _read(self) -> dict[str, Any]:
        if not self.path.exists():
            return self._empty_document()
        try:
            document = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise CanvasStoreError(f"项目存储不可读取: {exc}") from exc
        if not isinstance(document, dict) or not isinstance(
            document.get("projects"), list
        ):
            raise CanvasStoreError("项目存储格式无效")
        return document

    def _write(self, document: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(
            prefix=f".{self.path.name}.", suffix=".tmp", dir=self.path.parent
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(document, handle, ensure_ascii=False, indent=2)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp_name, self.path)
        except Exception:
            try:
                os.unlink(tmp_name)
            except OSError:
                pass
            raise

    @staticmethod
    def _find(document: dict[str, Any], project_id: str) -> dict[str, Any]:
        for project in document["projects"]:
            if isinstance(project, dict) and project.get("id") == project_id:
                return project
        raise CanvasNotFoundError("项目不存在")

    def list(self) -> list[dict[str, Any]]:
        with self._lock:
            document = self._read()
            projects = [p for p in document["projects"] if isinstance(p, dict)]
            projects.sort(
                key=lambda item: (str(item.get("updatedAt") or ""), str(item.get("id") or "")),
                reverse=True,
            )
            return copy.deepcopy(projects)

    def get(self, project_id: str) -> dict[str, Any]:
        with self._lock:
            return copy.deepcopy(self._find(self._read(), project_id))

    def create(self, name: Any = None) -> dict[str, Any]:
        project = _new_project(_project_name(name))
        with self._lock:
            document = self._read()
            document["projects"].append(project)
            self._write(document)
            return copy.deepcopy(project)

    def duplicate(self, project_id: str, name: Any = None) -> dict[str, Any]:
        with self._lock:
            document = self._read()
            source = self._find(document, project_id)
            duplicate = _copy_with_new_ids(
                source,
                _project_name(name, default=f"{source.get('name') or DEFAULT_PROJECT_NAME} 副本"),
            )
            document["projects"].append(duplicate)
            self._write(document)
            return copy.deepcopy(duplicate)

    def update_state(self, project_id: str, state: Any) -> dict[str, Any]:
        if not isinstance(state, dict):
            raise CanvasValidationError("项目状态必须是对象")
        with self._lock:
            document = self._read()
            project = self._find(document, project_id)
            updated = copy.deepcopy(project)
            if "assets" in state:
                assets = state["assets"]
                if not isinstance(assets, list):
                    raise CanvasValidationError("项目 assets 必须是数组")
                normalized_assets = [
                    _normalize_asset(asset) for asset in assets
                ]
                asset_ids = [asset["id"] for asset in normalized_assets]
                if len(asset_ids) != len(set(asset_ids)):
                    raise CanvasValidationError("项目不能包含重复资产 id")
                updated["assets"] = normalized_assets
            if "canvases" in state:
                canvases = state["canvases"]
                if not isinstance(canvases, list) or not canvases:
                    raise CanvasValidationError("项目至少需要一个画布")
                normalized_canvases = [_normalize_canvas(canvas) for canvas in canvases]
                canvas_ids = [canvas["id"] for canvas in normalized_canvases]
                if len(canvas_ids) != len(set(canvas_ids)):
                    raise CanvasValidationError("项目不能包含重复画布 id")
                updated["canvases"] = normalized_canvases
            if "activeCanvasId" in state:
                active_id = state["activeCanvasId"]
                if not isinstance(active_id, str) or not active_id:
                    raise CanvasValidationError("activeCanvasId 必须是非空 id")
                updated["activeCanvasId"] = active_id
            if updated.get("activeCanvasId") not in {
                canvas.get("id") for canvas in updated.get("canvases") or []
            }:
                raise CanvasValidationError("activeCanvasId 不属于该项目")
            updated["updatedAt"] = _now()
            project.clear()
            project.update(updated)
            self._write(document)
            return copy.deepcopy(project)

    def create_canvas(self, project_id: str, name: Any = None) -> dict[str, Any]:
        with self._lock:
            document = self._read()
            project = self._find(document, project_id)
            canvas = _new_canvas(_project_name(name, default=DEFAULT_CANVAS_NAME))
            project.setdefault("canvases", []).append(canvas)
            project["activeCanvasId"] = canvas["id"]
            project["updatedAt"] = _now()
            self._write(document)
            return copy.deepcopy(canvas)

    def update_canvas(
        self, project_id: str, canvas_id: str, payload: Any
    ) -> dict[str, Any]:
        if not isinstance(payload, dict):
            raise CanvasValidationError("画布更新内容必须是对象")
        with self._lock:
            project = self._find(self._read(), project_id)
            current = next(
                (
                    canvas
                    for canvas in project.get("canvases") or []
                    if isinstance(canvas, dict) and canvas.get("id") == canvas_id
                ),
                None,
            )
            if current is None:
                raise CanvasNotFoundError("画布不存在")
            candidate = copy.deepcopy(current)
            for key in ("name", "nodes", "edges", "viewport", "assetIds"):
                if key in payload:
                    candidate[key] = payload[key]
            updated = self.update_state(
                project_id,
                {"canvases": [
                    candidate if canvas.get("id") == canvas_id else canvas
                    for canvas in project.get("canvases") or []
                ]},
            )
            return copy.deepcopy(
                next(canvas for canvas in updated["canvases"] if canvas["id"] == canvas_id)
            )

    def delete_canvas(self, project_id: str, canvas_id: str) -> None:
        with self._lock:
            document = self._read()
            project = self._find(document, project_id)
            canvases = project.get("canvases") or []
            if not any(canvas.get("id") == canvas_id for canvas in canvases):
                raise CanvasNotFoundError("画布不存在")
            if len(canvases) <= 1:
                raise CanvasValidationError("项目至少需要一个画布")
            project["canvases"] = [
                canvas for canvas in canvases if canvas.get("id") != canvas_id
            ]
            if project.get("activeCanvasId") == canvas_id:
                project["activeCanvasId"] = project["canvases"][0]["id"]
            project["updatedAt"] = _now()
            self._write(document)

    def add_asset(self, project_id: str, asset: Any) -> dict[str, Any]:
        normalized = _normalize_asset(asset, generate_id=True)
        with self._lock:
            document = self._read()
            project = self._find(document, project_id)
            if any(item.get("id") == normalized["id"] for item in project.get("assets") or []):
                raise CanvasValidationError("资产 id 已存在")
            project.setdefault("assets", []).append(normalized)
            project["updatedAt"] = _now()
            self._write(document)
            return copy.deepcopy(normalized)

    def update_asset(
        self, project_id: str, asset_id: str, payload: Any
    ) -> dict[str, Any]:
        if not isinstance(payload, dict):
            raise CanvasValidationError("资产更新内容必须是对象")
        with self._lock:
            document = self._read()
            project = self._find(document, project_id)
            asset = next(
                (
                    item
                    for item in project.get("assets") or []
                    if item.get("id") == asset_id
                ),
                None,
            )
            if asset is None:
                raise CanvasNotFoundError("资产不存在")
            for key, value in payload.items():
                if key != "id":
                    asset[key] = copy.deepcopy(value)
            project["updatedAt"] = _now()
            self._write(document)
            return copy.deepcopy(asset)

    def delete_asset(self, project_id: str, asset_id: str) -> None:
        with self._lock:
            document = self._read()
            project = self._find(document, project_id)
            assets = project.get("assets") or []
            if not any(asset.get("id") == asset_id for asset in assets):
                raise CanvasNotFoundError("资产不存在")
            project["assets"] = [asset for asset in assets if asset.get("id") != asset_id]
            for canvas in project.get("canvases") or []:
                canvas["assetIds"] = [
                    value for value in canvas.get("assetIds") or [] if value != asset_id
                ]
            project["updatedAt"] = _now()
            self._write(document)

    def rename(self, project_id: str, name: Any) -> dict[str, Any]:
        with self._lock:
            document = self._read()
            project = self._find(document, project_id)
            project["name"] = _project_name(name)
            project["updatedAt"] = _now()
            self._write(document)
            return copy.deepcopy(project)

    def delete(self, project_id: str) -> None:
        with self._lock:
            document = self._read()
            self._find(document, project_id)
            document["projects"] = [
                project
                for project in document["projects"]
                if not isinstance(project, dict) or project.get("id") != project_id
            ]
            self._write(document)
