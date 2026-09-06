from __future__ import annotations

import json
import re
import os
import socket
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import time
from urllib.parse import urlparse, quote

from .base import Provider
from .http import collect_urls, extract_error, json_call, parse_job_id, save_media_urls
from .io_meta import looks_like_civitai_service, remember_job, job_meta

AI_TOKEN_PATH = Path.home() / ".config/modelscope/token"
CN_TOKEN_PATH = Path.home() / ".config/modelscope-cn/token"
ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
# AI and CN are separate products. Never fall back to the other base/token on failure.
AI_BASE = "https://api-inference.modelscope.ai/v1"
CN_BASE = "https://api-inference.modelscope.cn/v1"


def _read_token(path: Path) -> str:
    try:
        t = path.read_text().strip()
        return t or ""
    except Exception:
        return ""


def _host_ok(url: str) -> bool:
    try:
        host = urlparse(url).hostname
        if not host:
            return False
        socket.getaddrinfo(host, 443)
        return True
    except Exception:
        return False


def hub_headers():
    key = _read_token(AI_TOKEN_PATH) or _read_token(CN_TOKEN_PATH)
    if not key:
        key = (os.environ.get("MODELSCOPE_API_TOKEN") or os.environ.get("MODELSCOPE_CN_API_TOKEN") or "").strip()
    h = {}
    if key:
        h["Authorization"] = f"Bearer {key}"
    return h


def auth_headers(extra=None):
    h = hub_headers()
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


def _clamp_seed(raw):
    """ModelScope AIGC: seed in [-1, 2147483647]. Huge Civitai seeds wrap, not drop."""
    try:
        n = int(raw)
    except (TypeError, ValueError):
        return None
    if n < -1:
        return -1
    limit = 2147483647
    if n > limit:
        n = n % limit
        if n == 0:
            n = limit
    return n


def _modelscope_loras(payload: dict):
    """Official AIGC field: Hub `owner/repo` or `{repo: weight}`. Civitai http paths are skipped (+ warning)."""
    raw = payload.get("loras") or []
    if isinstance(raw, str) and raw.strip() and "/" in raw and not raw.startswith("http"):
        return raw.strip()
    if isinstance(raw, dict):
        return raw
    pairs = {}
    for it in raw if isinstance(raw, list) else []:
        repo = ""
        weight = 1.0
        if isinstance(it, str):
            repo = it.strip()
        elif isinstance(it, dict):
            path = (it.get("path") or it.get("url") or it.get("downloadUrl") or it.get("download_url") or "").strip()
            name = (it.get("name") or it.get("id") or "").strip()
            if path.startswith("http"):
                repo = path
            elif name.count("/") == 1 and not name.lower().startswith("urn:"):
                repo = name
            elif path.count("/") == 1:
                repo = path
            else:
                repo = path or name
            try:
                raw_w = it.get("scale")
                if raw_w is None:
                    raw_w = it.get("strength")
                weight = float(raw_w) if raw_w not in (None, "") else 1.0
            except (TypeError, ValueError):
                weight = 1.0
        else:
            continue
        if not repo or repo.lower().startswith("urn:"):
            continue
        if repo.startswith("http"):
            # AIGC wants Hub owner/repo; Civitai download URLs 500 with 空 modelName.
            continue
        if repo.count("/") != 1:
            continue
        pairs[repo] = max(0.0, weight)
    if not pairs:
        return None
    if len(pairs) == 1:
        return next(iter(pairs.keys()))
    total = sum(pairs.values()) or 1.0
    return {k: (v / total) for k, v in pairs.items()}


HUB = "https://www.modelscope.cn/openapi/v1/models"
# Hub slug, studio category, task, tags, needsSource, needsFirstFrame
HUB_TASKS = (
    ("text-to-image-synthesis", "image", "text-to-image", ["t2i"], False, False),
    ("image-to-image", "image", "image-to-image", ["i2i"], True, False),
    ("text-to-video-synthesis", "video", "text-to-video", ["t2v"], False, False),
    ("image-to-video", "video", "image-to-video", ["i2v"], False, True),
)
_HUB_CACHE = {"at": 0.0, "items": None, "totals": {}, "by_key": {}}
_HUB_TTL = 300
_HUB_PAGE = 50
# page_size max 50. 20 pages = 1000 / task. Smaller tasks (i2i 830, i2v 561) exhaust.
_HUB_PAGES = 20
_HUB_WORKERS = 8


def _alnum(s):
    return "".join(ch for ch in (s or "").lower() if ch.isalnum())


from .hub_classify import (  # noqa: E402
    _UPSCALE_RE,
    apply_upscale_category as _apply_upscale_category,
    hub_upscale_blob,
)




def _hub_row(it, cat, task, tags, needs_src, needs_ff):
    mid = (it.get("id") or it.get("name") or "").strip()
    name = (it.get("chinese_name") or it.get("name") or (mid.split("/")[-1] if mid else "")).strip()
    row = {
        "id": mid,
        "name": name or (mid.split("/")[-1] if mid else mid),
        "category": cat,
        "backend": "modelscope",
        "status": "available",
        "task": task,
        "tags": list(tags),
        "downloads": it.get("downloads"),
        "hubTask": task,
    }
    if needs_src:
        row["needsSource"] = True
    if needs_ff:
        row["needsFirstFrame"] = True
    return _apply_upscale_category(row)


def _classify_hub(it):
    tasks = it.get("tasks") or it.get("Tasks") or []
    if isinstance(tasks, str):
        tasks = [tasks]
    for hub_task, cat, task, tags, needs_src, needs_ff in HUB_TASKS:
        if hub_task in tasks:
            return cat, task, tags, needs_src, needs_ff
    return None


def fetch_hub_search(search):
    """Hub search=. Paginate until total_count or 3 pages — typeahead must stay fast."""
    items, seen, totals = [], set(), {}
    q = (search or "").strip()
    if not q:
        return items, totals
    if q.count("/") == 1 and " " not in q:
        code, data = json_call(f"{HUB}/{quote(q, safe='')}", headers=auth_headers(), timeout=20)
        block = data.get("data") or data.get("Data") if isinstance(data, dict) else None
        if code == 200 and isinstance(block, dict):
            block.setdefault("id", q)
            cls = _classify_hub(block) or ("image", "text-to-image", ["t2i"], False, False)
            row = _hub_row(block, *cls)
            if row["id"] and row["id"] not in seen:
                seen.add(row["id"])
                items.append(row)
    total = 0
    search_pages = 3
    reachable = False
    for page in range(1, search_pages + 1):
        qs = f"search={quote(q)}&sort=downloads&page_size={_HUB_PAGE}&page_number={page}"
        code, data = json_call(f"{HUB}?{qs}", headers=auth_headers(), timeout=25)
        block = data.get("data") if isinstance(data, dict) else None
        if code != 200 or not isinstance(block, dict):
            break
        reachable = True
        models = block.get("models") or []
        try:
            total = int(block.get("total_count") or 0)
        except (TypeError, ValueError):
            total = max(total, len(models))
        for it in models:
            if not isinstance(it, dict):
                continue
            cls = _classify_hub(it)
            if not cls:
                continue
            row = _hub_row(it, *cls)
            if not row["id"] or row["id"] in seen:
                continue
            seen.add(row["id"])
            items.append(row)
        if not models or page * _HUB_PAGE >= total:
            break
    totals["search"] = total
    totals["_reachable"] = reachable
    totals["_pagesFetched"] = min(search_pages, max(1, (total + _HUB_PAGE - 1) // _HUB_PAGE if total else 1))
    totals["_hasMore"] = bool(total and len(items) < total)
    totals["_pageSize"] = _HUB_PAGE
    return items, totals


def _hub_tasks_for_category(category: str):
    from .catalog_ops import canonical_category

    want = canonical_category(category)
    if want == "upscale":
        return tuple(t for t in HUB_TASKS if t[1] == "image")
    if want in ("image", "video"):
        return tuple(t for t in HUB_TASKS if t[1] == want)
    if want:
        return tuple(t for t in HUB_TASKS if t[1] == want)
    return HUB_TASKS


def _fetch_task_page(hub_task, page, search=""):
    qs = (
        f"filter.task={quote(hub_task, safe='')}&sort=downloads"
        f"&page_size={_HUB_PAGE}&page_number={page}"
    )
    if search:
        qs += f"&search={quote(search)}"
    code, data = json_call(f"{HUB}?{qs}", headers=auth_headers(), timeout=30)
    block = data.get("data") if isinstance(data, dict) else None
    return code, block if isinstance(block, dict) else None


def _rows_from_block(block, hub_task, cat, task, tags, needs_src, needs_ff, seen):
    rows = []
    models = (block or {}).get("models") or []
    for it in models:
        if not isinstance(it, dict):
            continue
        row = _hub_row(it, cat, task, tags, needs_src, needs_ff)
        row["hubTask"] = hub_task
        if not row["id"] or row["id"] in seen:
            continue
        seen.add(row["id"])
        rows.append(row)
    return rows


def fetch_hub(search="", category=""):
    if (search or "").strip():
        return fetch_hub_search(search)
    items = []
    seen = set()
    totals = {}
    pages_fetched = 0
    has_more = False
    reachable = False
    tasks = _hub_tasks_for_category(category)
    for hub_task, cat, task, tags, needs_src, needs_ff in tasks:
        code, block = _fetch_task_page(hub_task, 1)
        pages_fetched += 1
        if code != 200 or not isinstance(block, dict):
            totals[hub_task] = 0
            continue
        reachable = True
        try:
            total = int(block.get("total_count") or 0)
        except (TypeError, ValueError):
            total = len(block.get("models") or [])
        totals[hub_task] = total
        items.extend(_rows_from_block(block, hub_task, cat, task, tags, needs_src, needs_ff, seen))
        last_page = min(_HUB_PAGES, max(1, (total + _HUB_PAGE - 1) // _HUB_PAGE if total else 1))
        if total and last_page * _HUB_PAGE < total:
            has_more = True
        if last_page <= 1:
            continue
        with ThreadPoolExecutor(max_workers=_HUB_WORKERS) as pool:
            futs = {
                pool.submit(_fetch_task_page, hub_task, page): page
                for page in range(2, last_page + 1)
            }
            for fut in as_completed(futs):
                pages_fetched += 1
                try:
                    pcode, pblock = fut.result()
                except Exception:
                    continue
                if pcode != 200 or not isinstance(pblock, dict):
                    continue
                items.extend(_rows_from_block(pblock, hub_task, cat, task, tags, needs_src, needs_ff, seen))
    if canonical_category_safe(category) == "upscale":
        extra, extra_tot = fetch_hub_search("upscale")
        for row in extra:
            mid = row.get("id")
            if mid and mid not in seen:
                seen.add(mid)
                items.append(row)
        if extra_tot.get("_reachable"):
            reachable = True
    totals["_reachable"] = reachable
    totals["_pagesFetched"] = pages_fetched
    totals["_hasMore"] = has_more
    totals["_pageSize"] = _HUB_PAGE
    return items, totals


def canonical_category_safe(category: str) -> str:
    try:
        from .catalog_ops import canonical_category
        return canonical_category(category)
    except Exception:
        return (category or "").strip()


def search_loras(q: str, limit: int = 8):
    """ModelScope Hub search. Official loras field wants owner/repo."""
    q = (q or "").strip()
    items, seen = [], set()
    if not q:
        return 200, {"items": [], "backend": "modelscope"}
    rows, _ = fetch_hub_search(q)
    extra, _ = fetch_hub_search(q + " lora")
    for row in list(rows) + list(extra):
        mid = (row.get("id") or "").strip()
        if not mid or mid in seen or mid.count("/") != 1:
            continue
        seen.add(mid)
        items.append({
            "id": mid,
            "name": row.get("name") or mid,
            "path": mid,
            "type": "LORA",
            "source": "modelscope",
            "versions": [{"id": mid, "name": row.get("task") or "lora"}],
        })
        if len(items) >= limit:
            break
    return 200, {"items": items, "backend": "modelscope"}


def hub_model_probe(mid: str) -> tuple[int, dict]:
    """One real Hub lookup for a single model id.

    Returns the HTTP code untouched: whatif has to tell "no such model" (404)
    apart from "Hub unreachable", and fetch_hub_search() swallows both.
    """
    q = (mid or "").strip()
    if not q or q.count("/") != 1:
        return 400, {}
    code, data = json_call(f"{HUB}/{quote(q, safe='')}", headers=hub_headers(), timeout=20)
    block = None
    if isinstance(data, dict):
        block = data.get("data") or data.get("Data")
    return code, block if isinstance(block, dict) else {}


def is_edit(mid: str) -> bool:
    low = (mid or "").lower()
    return "image-edit" in low or "image-to-image" in low or "/edit" in low


def wants_source_image(mid: str) -> bool:
    """True when the model needs an input image: edit models, or upscale models.

    Upscale models (NMKDSuperscale, Ultrasharp, APISR, Controlnet-Upscaler, ...)
    rarely have "image-edit"/"image-to-image" in their id, so is_edit() alone
    missed them — the request would silently go out as plain text-to-image with
    no source image attached. hub_upscale_blob() is the same id/name/tag
    classifier the catalog already uses to put these models in the "upscale"
    category, so this stays consistent with what the UI shows the user.
    """
    return is_edit(mid) or hub_upscale_blob({"id": mid})


OFFICIAL_FIELDS = {
    "model", "prompt", "negative_prompt", "size", "seed", "steps", "guidance", "image_url", "loras",
}


def build_ms_body(payload: dict, mid: str) -> tuple[dict, str | None]:
    """Exact request body generate() posts. whatif() checks this same body."""
    payload = payload or {}
    body = {"model": mid, "prompt": payload.get("prompt") or ""}
    if payload.get("negativePrompt"):
        body["negative_prompt"] = payload["negativePrompt"]
    if payload.get("seed") not in (None, "", "random"):
        seed = _clamp_seed(payload.get("seed"))
        if seed is not None:
            body["seed"] = seed
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
    ms_loras = _modelscope_loras(payload)
    lora_skip = None
    if ms_loras is not None:
        body["loras"] = ms_loras
    elif payload.get("loras"):
        lora_skip = "魔搭 LoRA 只要 Hub 的 owner/repo，Civitai 下载链不能用"
    img = (payload.get("firstFrame") or payload.get("sourceImage") or payload.get("image_url") or "").strip()
    extra = [x for x in (payload.get("images") or []) if x]
    if img and img not in extra:
        extra = [img] + extra
    if wants_source_image(mid) and extra:
        body["image_url"] = extra[:9]
    return body, lora_skip


class ModelScopeProvider(Provider):
    def __init__(self, flavor: str):
        flavor = "cn" if flavor == "cn" else "ai"
        self.flavor = flavor
        if flavor == "cn":
            self.id = "modelscope-cn"
            self.label = "魔搭 CN"
            self._base = CN_BASE
            self._token_path = CN_TOKEN_PATH
            self._job_ids = ("modelscope-cn", "mscn")
        else:
            self.id = "modelscope-ai"
            self.label = "魔搭 AI"
            self._base = AI_BASE
            self._token_path = AI_TOKEN_PATH
            self._job_ids = ("modelscope-ai", "modelscope", "ms")

    def _key(self) -> str:
        t = _read_token(self._token_path)
        if t:
            return t
        if self.flavor == "cn":
            return (os.environ.get("MODELSCOPE_CN_API_TOKEN") or "").strip()
        return (os.environ.get("MODELSCOPE_API_TOKEN") or os.environ.get("MODELSCOPE_SDK_TOKEN") or os.environ.get("MODELSCOPE_API_KEY") or "").strip()

    def has_key(self) -> bool:
        return bool(self._key())

    def search_loras(self, q: str, nsfw: bool = True):
        return search_loras(q)

    def _auth(self, extra=None):
        h = {"Authorization": f"Bearer {self._key()}"}
        if extra:
            h.update(extra)
        return h

    def _reach_error(self):
        if _host_ok(self._base):
            return None
        return f"{self.label} 地址 {self._base} 连不上。AI 和 CN 是两套接口，不会改走另一边。"

    def categories(self) -> list:
        return ["image", "video", "upscale", "utility"]

    def catalog(self, q, category, status) -> dict:
        qn = (q or "").strip()
        now = time.time()
        totals = {}
        from .catalog_ops import canonical_category, category_matches, enrich_catalog_item

        cat_key = canonical_category(category) or ""
        cache_key = (qn, cat_key)
        pack = (_HUB_CACHE.get("by_key") or {}).get(cache_key)
        if (not qn) and pack and (now - pack.get("at", 0)) < _HUB_TTL:
            items = list(pack.get("items") or [])
            totals = dict(pack.get("totals") or {})
            source = pack.get("source") or "hub"
        else:
            hub, totals = fetch_hub(search=qn, category=category)
            reachable = bool(totals.get("_reachable"))
            pins = load_disk()
            if reachable:
                # Hub is the roster. Pins that landed in Hub go to the front;
                # missing pins are NOT injected — that was the 4-id fake roster.
                by_id = {x.get("id"): x for x in hub if x.get("id")}
                pinned, rest, seen = [], [], set()
                for pin in pins:
                    pid = pin.get("id")
                    if pid and pid in by_id and pid not in seen:
                        row = dict(by_id[pid])
                        row["pinned"] = True
                        pinned.append(row)
                        seen.add(pid)
                for x in hub:
                    mid = x.get("id")
                    if mid and mid not in seen:
                        rest.append(x)
                        seen.add(mid)
                items = pinned + rest
                source = "hub"
            else:
                items = list(pins)
                source = "hardcoded_fallback"
            if not qn:
                by_key = dict(_HUB_CACHE.get("by_key") or {})
                by_key[cache_key] = {
                    "at": now,
                    "items": list(items),
                    "totals": dict(totals),
                    "source": source,
                }
                _HUB_CACHE["by_key"] = by_key
                union = list(_HUB_CACHE.get("items") or [])
                seen_u = {x.get("id") for x in union}
                for x in items:
                    if x.get("id") and x.get("id") not in seen_u:
                        union.append(x)
                        seen_u.add(x.get("id"))
                _HUB_CACHE["items"] = union
                _HUB_CACHE["at"] = now
                merged = dict(_HUB_CACHE.get("totals") or {})
                merged.update(totals)
                _HUB_CACHE["totals"] = merged
        qnl = qn.lower()
        items = [_apply_upscale_category(dict(x)) for x in items]
        unfiltered = list(items)
        if category:
            items = [x for x in items if category_matches(x.get("category"), category)]
        if status:
            items = [x for x in items if x.get("status") == status]
        if qnl:
            needle = _alnum(qnl)
            items = [x for x in items if needle in _alnum(x.get("name")) or needle in _alnum(x.get("id"))]
        tagged = []
        for x in items:
            row = dict(x)
            row["backend"] = self.id
            tagged.append(enrich_catalog_item(row, self.id))
        hub_totals = {k: v for k, v in (totals or {}).items() if not str(k).startswith("_")}
        return {
            "total": len(tagged),
            "count": len(tagged),
            "backend": self.id,
            "items": tagged,
            "hasKey": self.has_key(),
            "baseUrl": self._base,
            "hub": HUB,
            "hubTotals": hub_totals,
            "categories": dict(Counter((x.get("category") or "unknown") for x in unfiltered)),
            "pagination": {
                "page": 1,
                "pageSize": totals.get("_pageSize") or _HUB_PAGE,
                "pagesFetched": totals.get("_pagesFetched") or 0,
                "hasMore": bool(totals.get("_hasMore")),
                "source": source,
            },
        }

    def owns_service(self, service_id: str) -> bool:
        sid = (service_id or "").strip()
        if not sid:
            return False
        prefixes = (self.id + "/", "ms/", "modelscope/", "魔搭/")
        if sid.startswith(prefixes):
            return True
        ids = {x.get("id") for x in load_disk()}
        if _HUB_CACHE.get("items"):
            ids |= {x.get("id") for x in _HUB_CACHE["items"]}
        return sid in ids

    def owns_job(self, job_id: str) -> bool:
        pid, _ = parse_job_id(job_id)
        return pid in self._job_ids or (job_id or "").startswith(self.id + "|")

    def whatif(self, payload: dict):
        """Dry-run validate against the same gates generate() hits. No submit.

        魔搭 has no estimate endpoint, so this checks reachability, key, model
        identity (one real Hub lookup), the exact request body, and whether an
        edit/upscale model was handed a source image — the case that used to go
        out silently as plain text-to-image.
        """
        p = dict(payload or {})
        sid = (p.get("serviceId") or "").strip()
        base = {"backend": self.id, "baseUrl": self._base, "service": {"serviceId": sid}}
        err = self._reach_error()
        if err:
            return 502, {**base, "error": err, "code": "unreachable"}
        if not self._key():
            return 401, {
                **base,
                "error": f"没有{self.label} API Key，放在 {self._token_path}",
                "code": "no_key",
            }
        if looks_like_civitai_service(sid):
            return 400, {
                **base,
                "error": f"当前选中的是 Civitai 服务，不能发给{self.label}。请选 Tongyi-MAI/Z-Image-Turbo 或 Qwen/Qwen-Image。",
                "code": "wrong_backend",
            }
        mid = model_id(sid)
        if not mid:
            return 400, {**base, "error": f"缺少{self.label} 模型 id", "code": "missing_service"}
        raw_model = p.get("model")
        if isinstance(raw_model, str) and "/" in raw_model.strip():
            want_m = model_id(raw_model.strip())
            if want_m and want_m != mid:
                return 400, {
                    **base,
                    "error": f"模型 id 不一致：serviceId={mid} model={want_m}（拒绝 remap）",
                    "code": "model_mismatch",
                }
        base["service"]["serviceId"] = mid

        known_ids = {x.get("id") for x in load_disk()}
        if _HUB_CACHE.get("items"):
            known_ids |= {x.get("id") for x in _HUB_CACHE["items"]}
        errors, warnings = [], []
        hub_code = None
        if mid in known_ids:
            source = "catalog"
        else:
            hub_code, block = hub_model_probe(mid)
            if hub_code == 404:
                return 400, {
                    **base,
                    "error": f"{self.label} Hub 上没有 {mid}",
                    "code": "unknown_service",
                }
            if hub_code in (401, 403):
                return 401, {
                    **base,
                    "error": f"{self.label} Hub 拒绝访问 {mid}（HTTP {hub_code}），无法确认模型存在，拒绝放行",
                    "code": "forbidden",
                }
            if hub_code == 200 and block:
                source = "hub"
            else:
                return 400, {
                    **base,
                    "error": f"没连上{self.label} Hub（HTTP {hub_code}），且目录里没有 {mid}，拒绝放行未知模型",
                    "code": "unknown_service",
                    "checked": {"hubStatus": hub_code, "modelSource": None},
                }

        body, lora_skip = build_ms_body(p, mid)
        if lora_skip:
            warnings.append({"code": "lora_dropped", "message": lora_skip})
        if not (body.get("prompt") or "").strip():
            errors.append({"code": "missing_prompt", "message": f"prompt 是空的，{self.label} 会直接打回"})
        needs_img = wants_source_image(mid)
        if needs_img and not body.get("image_url"):
            errors.append({
                "code": "missing_input_media",
                "message": f"{mid} 是编辑/放大模型，必须先接一张图，否则会被当成文生图跑",
            })
        if body.get("image_url") and not needs_img:
            warnings.append({
                "code": "input_media_dropped",
                "message": f"{mid} 不是编辑模型，接上的图不会被带上",
            })
        if p.get("width") and p.get("height") and not body.get("size"):
            warnings.append({
                "code": "bad_size",
                "message": f"宽高不是整数，size 没能拼出来：{p.get('width')}x{p.get('height')}",
            })
        unknown = sorted(set(body) - OFFICIAL_FIELDS)
        if unknown:
            warnings.append({
                "code": "unknown_fields",
                "fields": unknown,
                "message": f"{self.label} 官方字段表里没有：{'、'.join(unknown)}",
            })

        data = {
            **base,
            "operation": "image-to-image" if needs_img else "text-to-image",
            "submittedInput": body,
            "warnings": warnings,
            "checked": {
                "reachable": True,
                "modelSource": source,
                "hubStatus": hub_code,
                "endpoint": f"{self._base}/images/generations",
            },
            "cost": {
                "total": None,
                "usd": None,
                "note": f"{self.label} 按次计费，没有预估接口（本次没有提交）",
            },
        }
        data["service"]["serviceId"] = mid
        if errors:
            data["errors"] = errors
            data["error"] = errors[0]["message"]
            data["code"] = errors[0]["code"]
            return 400, data
        data["ok"] = source is not None
        if source is None:
            data["verified"] = False
        return 200, data

    def generate(self, payload: dict):
        err = self._reach_error()
        if err:
            return 502, {"error": err, "backend": self.id, "baseUrl": self._base}
        key = self._key()
        if not key:
            return 401, {"error": f"没有{self.label} API Key，放在 {self._token_path}", "backend": self.id}
        sid = (payload or {}).get("serviceId") or ""
        if looks_like_civitai_service(sid):
            return 400, {"error": f"当前选中的是 Civitai 服务，不能发给{self.label}。请选 Tongyi-MAI/Z-Image-Turbo 或 Qwen/Qwen-Image。"}
        mid = model_id(sid)
        if not mid:
            return 400, {"error": f"缺少{self.label} 模型 id"}
        # v0764: refuse client model field that disagrees with serviceId (no MusePublic/2512 remap).
        raw_model = (payload or {}).get("model")
        if isinstance(raw_model, str) and "/" in raw_model.strip():
            want_m = model_id(raw_model.strip())
            if want_m and want_m != mid:
                return 400, {
                    "error": f"模型 id 不一致：serviceId={mid} model={want_m}（拒绝 remap）",
                    "backend": self.id,
                }
        body, lora_skip = build_ms_body(payload, mid)
        headers = self._auth({"X-ModelScope-Async-Mode": "true"})
        url = f"{self._base}/images/generations"
        code, data = json_call(url, method="POST", headers=headers, body=body, timeout=90)
        extra_keys = set(body) - OFFICIAL_FIELDS
        if code >= 400 and extra_keys:
            slim = {k: v for k, v in body.items() if k in OFFICIAL_FIELDS}
            code, data = json_call(url, method="POST", headers=headers, body=slim, timeout=90)
            body = slim
        if not isinstance(data, dict):
            return code, {"error": f"{self.label} 响应无效", "backend": self.id, "baseUrl": self._base}
        if code >= 400:
            data.setdefault("error", extract_error(data, f"HTTP {code}"))
            data["backend"] = self.id
            data["baseUrl"] = self._base
            return code, data
        nested = data.get("data") if isinstance(data.get("data"), dict) else {}
        tid = data.get("task_id") or data.get("taskId") or nested.get("task_id") or data.get("id")
        if not tid:
            data.setdefault("error", extract_error(data, f"{self.label} 未返回 task_id"))
            data["backend"] = self.id
            return code if code >= 400 else 502, data
        jid = f"{self.id}|{tid}"
        data["id"] = jid
        data["status"] = "pending"
        data["backend"] = self.id
        data["endpoint"] = mid
        data["submittedInput"] = body
        if lora_skip:
            data["warning"] = lora_skip
        remember_job(jid, {
            "backend": self.id,
            "serviceId": mid,
            "submittedInput": body,
            "prompt": payload.get("prompt"),
            "negativePrompt": payload.get("negativePrompt"),
            "seed": payload.get("seed"),
            "jobId": jid,
        })
        return code if code < 400 else code, data

    def job_status(self, job_id: str):
        err = self._reach_error()
        if err:
            return 502, {"error": err, "backend": self.id, "id": job_id}
        _, tid = parse_job_id(job_id)
        if not tid:
            return 400, {"error": f"无效{self.label} 任务 id"}
        headers = self._auth({"X-ModelScope-Task-Type": "image_generation"})
        code, data = json_call(f"{self._base}/tasks/{tid}", headers=headers, timeout=60)
        if not isinstance(data, dict):
            return code, data
        st = str(data.get("task_status") or data.get("status") or "").upper()
        mapped = {
            "SUCCEED": "succeeded", "SUCCEEDED": "succeeded", "SUCCESS": "succeeded",
            "FAILED": "failed", "FAIL": "failed",
            "PENDING": "pending", "RUNNING": "processing", "QUEUED": "pending",
        }
        data["status"] = mapped.get(st, (data.get("status") or "pending").lower())
        data["backend"] = self.id
        data["id"] = job_id
        err_txt = extract_error(data, "")
        data["wait"] = {
            "progress": None,
            "precedingJobs": None,
            "etaSeconds": None,
            "completeAt": None,
            "log": (err_txt or "")[:120] or None,
        }
        if data["status"] == "failed":
            data["error"] = err_txt or f"{self.label} 生成失败"
        if data["status"] == "succeeded":
            nested = data.get("data") if isinstance(data.get("data"), dict) else {}
            urls = collect_urls(data) + collect_urls(data.get("output") or {}) + collect_urls(data.get("outputs") or {}) + collect_urls(nested)
            for u in data.get("output_images") or []:
                if isinstance(u, str) and u.startswith("http"):
                    urls.append(u)
                elif isinstance(u, dict) and u.get("url"):
                    urls.append(u["url"])
            seen = []
            for u in urls:
                if u not in seen:
                    seen.append(u)
            try:
                data["saved"] = save_media_urls(seen, job_id, meta=job_meta(job_id) or {"backend": self.id, "jobId": job_id})
            except Exception as e:
                data["saveError"] = str(e)
            if not data.get("saved"):
                data["status"] = "failed"
                data["error"] = data.get("saveError") or f"{self.label} 成功但没拿到文件"
        return 200 if code in (200, 202) else code, data


from . import register  # noqa: E402

register(ModelScopeProvider("ai"))
register(ModelScopeProvider("cn"))
