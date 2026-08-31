from __future__ import annotations

import json
import os
import socket
from pathlib import Path
import time
from urllib.parse import urlparse, quote

from .base import Provider
from .http import collect_urls, json_call, parse_job_id, save_media_urls

TOKEN_PATH = Path.home() / ".config/modelscope/token"
BASE_PATH = Path.home() / ".config/modelscope/base_url"
ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
PREFERRED = "https://api.modelscope.ai/v1"
FALLBACK = "https://api-inference.modelscope.cn/v1"


def ms_key() -> str:
    try:
        t = TOKEN_PATH.read_text().strip()
        if t:
            return t
    except Exception:
        pass
    return (os.environ.get("MODELSCOPE_API_TOKEN") or os.environ.get("MODELSCOPE_SDK_TOKEN") or os.environ.get("MODELSCOPE_API_KEY") or "").strip()


def _host_ok(url: str) -> bool:
    try:
        host = urlparse(url).hostname
        if not host:
            return False
        socket.getaddrinfo(host, 443)
        return True
    except Exception:
        return False


def base_url() -> str:
    preferred = PREFERRED
    try:
        t = BASE_PATH.read_text().strip().rstrip("/")
        if t:
            preferred = t
    except Exception:
        pass
    if _host_ok(preferred):
        return preferred
    return FALLBACK


def auth_headers(extra=None):
    key = ms_key()
    h = {"Authorization": f"Bearer {key}"}
    if extra:
        h.update(extra)
    return h


def load_disk():
    fp = DOCS / "ms-models.json"
    if not fp.exists():
        return []
    try:
        return json.loads(fp.read_text()).get("items") or []
    except Exception:
        return []


def model_id(service_id: str) -> str:
    s = (service_id or "").strip().lstrip("/")
    for pfx in ("ms/", "modelscope/", "魔搭/"):
        if s.startswith(pfx):
            s = s[len(pfx):]
    return s



HUB = "https://www.modelscope.cn/openapi/v1/models"
# Hub slug, studio category, task, tags, needsSource, needsFirstFrame
HUB_TASKS = (
    ("text-to-image-synthesis", "image", "text-to-image", ["t2i"], False, False),
    ("image-to-image", "image", "image-to-image", ["i2i"], True, False),
    ("text-to-video-synthesis", "video", "text-to-video", ["t2v"], False, False),
    ("image-to-video", "video", "image-to-video", ["i2v"], False, True),
)
_HUB_CACHE = {"at": 0.0, "items": None, "totals": {}}
_HUB_TTL = 300
_HUB_PAGE = 50
_HUB_PAGES = 2


def fetch_hub(search=""):
    items = []
    seen = set()
    totals = {}
    for hub_task, cat, task, tags, needs_src, needs_ff in HUB_TASKS:
        total = 0
        for page in range(1, _HUB_PAGES + 1):
            qs = (
                f"filter.task={quote(hub_task, safe='')}&sort=downloads"
                f"&page_size={_HUB_PAGE}&page_number={page}"
            )
            if search:
                qs += f"&search={quote(search)}"
            code, data = json_call(f"{HUB}?{qs}", headers=auth_headers(), timeout=30)
            block = data.get("data") if isinstance(data, dict) else None
            if code != 200 or not isinstance(block, dict):
                break
            models = block.get("models") or []
            try:
                total = int(block.get("total_count") or 0)
            except (TypeError, ValueError):
                total = 0
            totals[hub_task] = total
            for it in models:
                if not isinstance(it, dict):
                    continue
                mid = (it.get("id") or it.get("name") or "").strip()
                if not mid or mid in seen:
                    continue
                seen.add(mid)
                name = (it.get("chinese_name") or it.get("name") or mid.split("/")[-1]).strip()
                row = {
                    "id": mid,
                    "name": name or mid.split("/")[-1],
                    "category": cat,
                    "backend": "modelscope",
                    "status": "available",
                    "task": task,
                    "tags": list(tags),
                    "downloads": it.get("downloads"),
                    "hubTask": hub_task,
                }
                if needs_src:
                    row["needsSource"] = True
                if needs_ff:
                    row["needsFirstFrame"] = True
                items.append(row)
            if not models or page * _HUB_PAGE >= total:
                break
    return items, totals


def is_edit(mid: str) -> bool:
    low = (mid or "").lower()
    return "image-edit" in low or "image-to-image" in low or "/edit" in low


class ModelScopeProvider(Provider):
    id = "modelscope"
    label = "魔搭"

    def has_key(self) -> bool:
        return bool(ms_key())

    def categories(self) -> list:
        return ["image", "video"]

    def catalog(self, q, category, status) -> dict:
        qn = (q or "").strip()
        now = time.time()
        totals = {}
        if (not qn) and _HUB_CACHE["items"] is not None and (now - _HUB_CACHE["at"]) < _HUB_TTL:
            items = list(_HUB_CACHE["items"])
            totals = dict(_HUB_CACHE.get("totals") or {})
        else:
            hub, totals = fetch_hub(search=qn)
            pins = load_disk()
            seen = {x.get("id") for x in hub}
            items = list(hub)
            for pin in reversed(pins):
                pid = pin.get("id")
                if pid and pid not in seen:
                    items.insert(0, pin)
                    seen.add(pid)
            if not hub:
                items = list(pins)
            if not qn:
                _HUB_CACHE["items"] = list(items)
                _HUB_CACHE["at"] = now
                _HUB_CACHE["totals"] = totals
        qnl = qn.lower()
        if category:
            items = [x for x in items if x.get("category") == category]
        if status:
            items = [x for x in items if x.get("status") == status]
        if qnl:
            items = [x for x in items if qnl in (x.get("name") or "").lower() or qnl in (x.get("id") or "").lower()]
        return {
            "total": len(items),
            "count": len(items),
            "backend": "modelscope",
            "items": items,
            "hasKey": self.has_key(),
            "baseUrl": base_url(),
            "hub": HUB,
            "hubTotals": totals,
        }

    def owns_service(self, service_id: str) -> bool:
        sid = (service_id or "").strip()
        if not sid:
            return False
        if sid.startswith(("ms/", "modelscope/")):
            return True
        ids = {x.get("id") for x in load_disk()}
        if _HUB_CACHE.get("items"):
            ids |= {x.get("id") for x in _HUB_CACHE["items"]}
        return sid in ids

    def owns_job(self, job_id: str) -> bool:
        pid, _ = parse_job_id(job_id)
        return pid in ("modelscope", "ms") or (job_id or "").startswith("ms|")

    def whatif(self, payload: dict):
        return 200, {
            "backend": "modelscope",
            "cost": {"total": None, "note": "魔搭按次计费，无黄 Buzz 预估"},
            "service": {"serviceId": (payload or {}).get("serviceId")},
        }

    def generate(self, payload: dict):
        key = ms_key()
        if not key:
            return 401, {"error": "没有魔搭 API Key"}
        mid = model_id((payload or {}).get("serviceId") or "")
        if not mid:
            return 400, {"error": "缺少魔搭模型 id"}
        body = {"model": mid, "prompt": payload.get("prompt") or ""}
        if payload.get("negativePrompt"):
            body["negative_prompt"] = payload["negativePrompt"]
        if payload.get("seed") not in (None, "", "random"):
            try:
                body["seed"] = int(payload["seed"])
            except (TypeError, ValueError):
                pass
        if payload.get("steps"):
            try:
                body["steps"] = int(payload["steps"])
            except (TypeError, ValueError):
                pass
        if payload.get("cfgScale") not in (None, ""):
            try:
                body["guidance"] = float(payload["cfgScale"])
            except (TypeError, ValueError):
                pass
        if payload.get("width") and payload.get("height"):
            try:
                body["size"] = f"{int(payload['width'])}x{int(payload['height'])}"
            except (TypeError, ValueError):
                pass
        img = (payload.get("firstFrame") or payload.get("sourceImage") or payload.get("image_url") or "").strip()
        extra = [x for x in (payload.get("images") or []) if x]
        if img and img not in extra:
            extra = [img] + extra
        if is_edit(mid) and extra:
            body["image_url"] = extra[:9]
        headers = auth_headers({"X-ModelScope-Async-Mode": "true"})
        code, data = json_call(f"{base_url()}/images/generations", method="POST", headers=headers, body=body, timeout=90)
        if not isinstance(data, dict):
            return code, {"error": "魔搭响应无效"}
        tid = data.get("task_id") or data.get("taskId") or data.get("id")
        if not tid:
            data.setdefault("error", data.get("message") or data.get("errors") or "魔搭未返回 task_id")
            return code if code >= 400 else 502, data
        data["id"] = f"ms|{tid}"
        data["status"] = "pending"
        data["backend"] = "modelscope"
        data["endpoint"] = mid
        data["submittedInput"] = body
        return code if code < 400 else code, data

    def job_status(self, job_id: str):
        _, tid = parse_job_id(job_id)
        if not tid:
            return 400, {"error": "无效魔搭任务 id"}
        headers = auth_headers({"X-ModelScope-Task-Type": "image_generation"})
        code, data = json_call(f"{base_url()}/tasks/{tid}", headers=headers, timeout=60)
        if not isinstance(data, dict):
            return code, data
        st = str(data.get("task_status") or data.get("status") or "").upper()
        mapped = {
            "SUCCEED": "succeeded", "SUCCEEDED": "succeeded", "SUCCESS": "succeeded",
            "FAILED": "failed", "FAIL": "failed",
            "PENDING": "pending", "RUNNING": "processing", "QUEUED": "pending",
        }
        data["status"] = mapped.get(st, (data.get("status") or "pending").lower())
        data["backend"] = "modelscope"
        data["id"] = job_id
        data["wait"] = {"progress": None, "precedingJobs": None, "etaSeconds": None, "completeAt": None, "log": None}
        if data["status"] == "succeeded":
            urls = collect_urls(data) + collect_urls(data.get("output") or {})
            for u in data.get("output_images") or []:
                if isinstance(u, str) and u.startswith("http"):
                    urls.append(u)
                elif isinstance(u, dict) and u.get("url"):
                    urls.append(u["url"])
            # unique
            seen = []
            for u in urls:
                if u not in seen:
                    seen.append(u)
            try:
                data["saved"] = save_media_urls(seen, job_id)
            except Exception as e:
                data["saveError"] = str(e)
        return code, data


from . import register  # noqa: E402

register(ModelScopeProvider())
