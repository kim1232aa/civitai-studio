#!/usr/bin/env python3
from __future__ import annotations

import inspect
import json
import re
import mimetypes
import os
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import providers
from providers import civitai as civitai_prov

ROOT = Path(__file__).resolve().parent
STATIC = ROOT / "static"
DOCS = ROOT / "docs"
OUT = ROOT / "out"
TOKEN_PATH = Path.home() / ".config/civitai/token"
ORCH = "https://orchestration.civitai.com"
SITE = "https://civitai.com/api/v1"
PORT = int(os.environ.get("PORT", "8765"))
OUT.mkdir(parents=True, exist_ok=True)
DOCS.mkdir(parents=True, exist_ok=True)

SAMPLERS = [
    "er_sde", "euler", "euler_ancestral", "euler_cfg_pp", "euler_ancestral_cfg_pp",
    "heun", "heunpp2", "dpm_2", "dpm_2_ancestral", "lms", "dpm_fast", "dpm_adaptive",
    "dpmpp_2s_ancestral", "dpmpp_2s_ancestral_cfg_pp", "dpmpp_sde", "dpmpp_sde_gpu",
    "dpmpp_2m", "dpmpp_2m_cfg_pp", "dpmpp_2m_sde", "dpmpp_2m_sde_gpu",
    "dpmpp_3m_sde", "dpmpp_3m_sde_gpu", "ddpm", "lcm", "ipndm", "ipndm_v",
    "deis", "ddim", "uni_pc", "uni_pc_bh2", "res_multistep",
]
SCHEDULERS = ["sgm_uniform", "simple", "normal", "karras", "exponential", "ddim_uniform", "beta"]

DEFAULTS = {
    "serviceId": "image/comfy/krea2/turbo/createImage",
    "videoServiceId": "video/minimax-h3-comfy/imageToVideo",
    "engine": "comfy",
    "ecosystem": "krea2",
    "model": "turbo",
    "operation": "createImage",
    "width": 960,
    "height": 1440,
    "steps": 8,
    "cfgScale": 1,
    "sampler": "er_sde",
    "scheduler": "sgm_uniform",
    "quantity": 1,
    "diffusionModel": "urn:air:krea2:diffusionmodel:civitai:2782456@3146785",
    "loras": [],
    "allowMatureContent": True,
    "checkpointName": "1125 Krea2 Asian Utopian v2.0",
}

_catalog_lock = threading.Lock()
_catalog = {"total": 0, "items": [], "fetchedAt": None}


def token() -> str:
    try:
        return TOKEN_PATH.read_text().strip()
    except Exception:
        return ""


def civitai(url: str, method="GET", body=None, timeout=90):
    tok = token()
    if not tok:
        return 401, {"error": "没有 API Key"}
    headers = {
        "Authorization": f"Bearer {tok}",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0",
    }
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read()
            try:
                parsed = json.loads(raw.decode())
            except json.JSONDecodeError:
                parsed = {"raw": raw[:2000].decode("utf-8", "replace")}
            return r.status, parsed
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            parsed = {"raw": raw[:2000]}
        if isinstance(parsed, dict) and "error" not in parsed:
            parsed = dict(parsed)
            parsed.setdefault("error", parsed.get("title") or f"HTTP {e.code}")
        return e.code, parsed
    except urllib.error.URLError as e:
        return 502, {"error": "网络错误", "detail": str(getattr(e, "reason", e))}
    except Exception as e:
        return 502, {"error": "请求失败", "detail": str(e)}


def slim_item(it: dict) -> dict:
    params = it.get("parameters") or {}
    return {
        "id": it.get("id"),
        "name": it.get("name"),
        "description": it.get("description") or "",
        "category": it.get("category"),
        "status": it.get("status"),
        "step": it.get("step"),
        "submit": it.get("submit"),
        "estimate": it.get("estimate"),
        "tags": it.get("tags") or [],
        "modalities": it.get("modalities") or {},
        "engine": params.get("engine"),
        "operation": params.get("operation"),
        "ecosystem": params.get("ecosystem"),
        "model": params.get("model"),
        "version": params.get("version"),
        "provider": params.get("provider"),
        "parameters": params,
    }


def load_catalog_disk():
    fp = DOCS / "catalog.json"
    if not fp.exists():
        return
    try:
        data = json.loads(fp.read_text())
        with _catalog_lock:
            _catalog["items"] = data.get("items") or []
            _catalog["total"] = data.get("total") or len(_catalog["items"])
            _catalog["fetchedAt"] = data.get("fetchedAt")
    except Exception as e:
        print("catalog load", e, flush=True)


def refresh_catalog() -> dict:
    items = []
    offset = 0
    total = None
    while True:
        code, data = civitai(f"{ORCH}/v2/services?limit=200&offset={offset}")
        if code != 200 or not isinstance(data, dict):
            raise RuntimeError(f"catalog fetch {code} {data}")
        batch = data.get("items") or []
        total = data.get("totalCount")
        items.extend(slim_item(x) for x in batch)
        if not batch or (total is not None and len(items) >= total):
            break
        offset += 200
    payload = {"total": len(items), "items": items, "fetchedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    (DOCS / "catalog.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    with _catalog_lock:
        _catalog.update(payload)
    return payload


def catalog_items():
    with _catalog_lock:
        if not _catalog["items"]:
            load_catalog_disk()
        return list(_catalog["items"]), _catalog.get("fetchedAt"), _catalog.get("total") or 0


_CATALOG_PAGE_DEFAULT = 1
_CATALOG_PAGE_SIZE_DEFAULT = 50
_CATALOG_PAGE_SIZE_MAX = 100


def _catalog_qs_one(qs, name):
    vals = qs.get(name) if isinstance(qs, dict) else None
    if not vals:
        return None
    if isinstance(vals, list):
        return vals[0]
    return vals


def _catalog_int(raw, default, lo, hi=None):
    if raw is None or raw == "":
        return default
    try:
        n = int(str(raw).strip())
    except (TypeError, ValueError):
        return default
    if n < lo:
        return lo
    if hi is not None and n > hi:
        return hi
    return n


def catalog_paging_requested(qs) -> bool:
    """Slice only when the client sent page, pageSize, or limit.

    One-shot callers (Civitai/Fal storyboard loadCatalog) omit these and must
    still receive the full filtered roster. HuggingFace/ModelScope send page.
    """
    for name in ("page", "pageSize", "limit"):
        raw = _catalog_qs_one(qs, name)
        if raw not in (None, ""):
            return True
    return False


def parse_catalog_page(qs, default_page=_CATALOG_PAGE_DEFAULT, default_size=_CATALOG_PAGE_SIZE_DEFAULT, max_size=_CATALOG_PAGE_SIZE_MAX):
    """page default 1; pageSize/limit default 50, cap 100."""
    page = _catalog_int(_catalog_qs_one(qs, "page"), default_page, 1)
    size_raw = _catalog_qs_one(qs, "pageSize")
    if size_raw is None or size_raw == "":
        size_raw = _catalog_qs_one(qs, "limit")
    page_size = _catalog_int(size_raw, default_size, 1, max_size)
    return page, page_size


def slice_catalog_items(items, page, page_size):
    """Page window over a fully held filtered list. total is that list's length."""
    items = list(items or [])
    total = len(items)
    start = (max(1, int(page)) - 1) * int(page_size)
    if start < 0:
        start = 0
    sliced = items[start:start + int(page_size)]
    has_more = start + len(sliced) < total
    return {
        "items": sliced,
        "count": len(sliced),
        "total": total,
        "page": int(page),
        "pageSize": int(page_size),
        "hasMore": has_more,
        "nextPage": (int(page) + 1) if has_more else None,
    }


def apply_catalog_paging(body, page, page_size, already_paged=False):
    """Always emit paging keys. Re-slice only when the provider returned the full list."""
    body = dict(body or {})
    items = list(body["items"]) if isinstance(body.get("items"), list) else []
    provider_total = body.get("total")
    looks_paged = (
        already_paged
        and isinstance(provider_total, int)
        and len(items) <= page_size
        and (body.get("page") in (None, page))
        and (body.get("pageSize") in (None, page_size))
    )
    if looks_paged:
        total = provider_total
        sliced = items
        has_more = body.get("hasMore")
        if not isinstance(has_more, bool):
            has_more = (page * page_size) < total
        next_page = body.get("nextPage")
        if has_more:
            next_page = next_page if isinstance(next_page, int) else page + 1
        else:
            next_page = None
    else:
        window = slice_catalog_items(items, page, page_size)
        sliced = window["items"]
        total = window["total"]
        has_more = window["hasMore"]
        next_page = window["nextPage"]
    body["items"] = sliced
    body["count"] = len(sliced)
    body["total"] = total
    body["page"] = page
    body["pageSize"] = page_size
    body["hasMore"] = bool(has_more)
    body["nextPage"] = next_page if body["hasMore"] else None
    if body.get("complete") is None:
        hub = body.get("hubTotals") if isinstance(body.get("hubTotals"), dict) else {}
        if isinstance(hub.get("complete"), bool):
            body["complete"] = hub["complete"]
        else:
            body["complete"] = True
    else:
        body["complete"] = bool(body.get("complete"))
    if body.get("partial") is None:
        body["partial"] = not body["complete"]
    else:
        body["partial"] = bool(body.get("partial"))
    return body


def catalog_accepts_paging(prov) -> bool:
    try:
        params = inspect.signature(prov.catalog).parameters
    except (TypeError, ValueError):
        return False
    if any(p.kind is inspect.Parameter.VAR_KEYWORD for p in params.values()):
        return True
    return "page" in params and ("pageSize" in params or "page_size" in params or "limit" in params)


def invoke_provider_catalog(prov, q, category, status, page, page_size):
    kwargs = {}
    already = False
    pass_page = page is not None and page_size is not None
    try:
        params = inspect.signature(prov.catalog).parameters
        names = set(params)
        var_kw = any(p.kind is inspect.Parameter.VAR_KEYWORD for p in params.values())
        if pass_page and (var_kw or "page" in names):
            kwargs["page"] = page
            already = True
        if pass_page and (var_kw or "pageSize" in names):
            kwargs["pageSize"] = page_size
            already = True
        elif pass_page and "page_size" in names:
            kwargs["page_size"] = page_size
            already = True
        if pass_page and "limit" in names:
            kwargs["limit"] = page_size
            already = True
    except (TypeError, ValueError):
        kwargs = {}
        already = False
    try:
        if kwargs:
            body = prov.catalog(q, category, status, **kwargs)
        else:
            body = prov.catalog(q, category, status)
            already = False
    except TypeError:
        body = prov.catalog(q, category, status)
        already = False
    if not isinstance(body, dict):
        body = {"items": [], "error": "catalog 返回值不是对象"}
    return body, already


def build_catalog_response(prov, q, category, status, page, page_size, backend="", paging_requested=True):
    if paging_requested:
        body, already = invoke_provider_catalog(prov, q, category, status, page, page_size)
    else:
        body, already = invoke_provider_catalog(prov, q, category, status, None, None)
        items = list(body["items"]) if isinstance(body.get("items"), list) else []
        native = body.get("hasMore") is not None and body.get("page") is not None
        if native:
            page = int(body.get("page") or 1)
            page_size = int(body.get("pageSize") or max(len(items), 1))
            already = True
        else:
            page = 1
            page_size = max(len(items), 1)
            already = False
    if backend in ("modelscope-ai", "modelscope-cn", "modelscope"):
        from providers.capabilities import overlay_modelscope_catalog
        body = overlay_modelscope_catalog(body)
    return apply_catalog_paging(body, page, page_size, already_paged=already)


def find_service(service_id: str):
    items, _, _ = catalog_items()
    for it in items:
        if it.get("id") == service_id:
            return it
    return None


def match_service(engine=None, operation=None, ecosystem=None, model=None, category=None):
    items, _, _ = catalog_items()
    scored = []
    for it in items:
        if category and it.get("category") != category:
            continue
        s = 0
        if engine and it.get("engine") == engine:
            s += 4
        if operation and it.get("operation") == operation:
            s += 3
        if ecosystem and it.get("ecosystem") == ecosystem:
            s += 2
        if model and it.get("model") == model:
            s += 1
        if s:
            if it.get("status") == "available":
                s += 2
            scored.append((s, it))
    scored.sort(key=lambda x: -x[0])
    return scored[0][1] if scored else None


def lora_map(payload: dict) -> dict:
    out = {}
    for item in payload.get("loras") or []:
        air = (item.get("air") or "").strip()
        if not air:
            continue
        try:
            out[air] = float(item.get("strength", 1))
        except (TypeError, ValueError):
            out[air] = 1.0
    return out


def _set_int(inp, payload, key, lo=None, hi=None):
    if payload.get(key) in (None, ""):
        return
    try:
        v = int(payload[key])
    except (TypeError, ValueError):
        return
    if lo is not None:
        v = max(lo, v)
    if hi is not None:
        v = min(hi, v)
    inp[key] = v


def _set_float(inp, payload, key):
    if payload.get(key) in (None, ""):
        return
    try:
        inp[key] = float(payload[key])
    except (TypeError, ValueError):
        pass


_CAPS = None


def load_caps():
    global _CAPS
    if _CAPS is not None:
        return _CAPS
    fp = DOCS / "capabilities.json"
    if not fp.exists():
        _CAPS = []
        return _CAPS
    try:
        _CAPS = (json.loads(fp.read_text()).get("capabilities") or [])
    except Exception:
        _CAPS = []
    return _CAPS


def find_cap(engine=None, operation=None, version=None, provider=None):
    best, score = None, -1
    for c in load_caps():
        s = 0
        if engine and c.get("engine") == engine:
            s += 5
        elif engine:
            continue
        if operation:
            if c.get("operation") == operation:
                s += 3
            elif c.get("operation") in (None, "videoGen", "imageGen"):
                s += 1
        if version and c.get("version") == version:
            s += 2
        if provider and c.get("provider") == provider:
            s += 1
        if s > score:
            best, score = c, s
    return best


def apply_frames(inp: dict, payload: dict, svc: dict | None):
    engine = (inp.get("engine") or (svc or {}).get("engine") or "")
    op = (inp.get("operation") or (svc or {}).get("operation") or "")
    cap = find_cap(engine, op, inp.get("version") or (svc or {}).get("version"), inp.get("provider") or (svc or {}).get("provider"))
    frames = list((cap or {}).get("frameFields") or [])
    from providers.ref_images import payload_ref_images, primary_frame, max_refs
    from providers.capabilities import get_provider_capabilities
    caps = get_provider_capabilities("civitai")
    first = primary_frame(payload) or (payload.get("startImage") or "").strip()
    last = (payload.get("lastFrame") or payload.get("endImage") or payload.get("endSourceImage") or "").strip()
    extra = payload_ref_images(payload, backend="civitai", caps=caps, item=cap if isinstance(cap, dict) else None)
    ref_cap = max_refs(backend="civitai", caps=caps, item=cap if isinstance(cap, dict) else None, payload=payload)
    FIRST_NAMES = {"firstFrame", "sourceImage", "image", "sourceImageUrl"}
    LAST_NAMES = {"lastFrame", "endImage", "endSourceImage"}
    ver = str(inp.get("version") or (svc or {}).get("version") or "")
    if engine == "wan":
        # v2.2 / v2.5 / v2.6: sourceImage + images; do NOT send startImage
        if ver in ("v2.2", "v2.5", "v2.6"):
            frames = [f for f in frames if f not in ("startImage", "endImage")]
            if "sourceImage" not in frames:
                frames.append("sourceImage")
            if "images" not in frames:
                frames.append("images")
        elif ver == "v2.7":
            frames = [f for f in frames if f != "images"]
        # v3.0 keeps sourceImage + startImage + endImage from schema
    elif "sourceImage" in frames and "startImage" in frames:
        frames = [f for f in frames if f != "startImage"]
    if "firstFrame" in frames and "endImage" in frames and "lastFrame" in frames:
        frames = [f for f in frames if f != "endImage"]
    if not frames:
        if extra and ("edit" in str(op).lower() or "variant" in str(op).lower()):
            frames = ["images"]
        elif first:
            frames = ["firstFrame", "image"]
    for name in frames:
        if name in FIRST_NAMES and first:
            inp[name] = first
        elif name in LAST_NAMES and last:
            inp[name] = last
        elif name == "startImage" and first:
            inp[name] = first
        elif name == "images" and extra:
            inp[name] = extra[:ref_cap]
        elif name == "referenceImages" and extra:
            inp[name] = extra[:ref_cap]
        elif name == "sourceVideo" and payload.get("sourceVideo"):
            inp[name] = payload["sourceVideo"]
        elif name == "sourceAudio" and payload.get("sourceAudio"):
            inp[name] = payload["sourceAudio"]
        elif name == "videoUrl" and payload.get("videoUrl"):
            inp[name] = payload["videoUrl"]
        elif name == "maskImage" and payload.get("maskImage"):
            inp[name] = payload["maskImage"]
    flags = (cap or {}).get("extraFlags") or {}
    if flags.get("turbo") is not None or engine == "minimax-h3-comfy":
        if payload.get("turbo") is not None:
            inp["turbo"] = bool(payload.get("turbo"))
    if flags.get("fast") is not None or engine == "minimax-h3-comfy":
        if payload.get("fast") is not None:
            inp["fast"] = bool(payload.get("fast"))
    if engine == "wan":
        if ver == "v2.2":
            if payload.get("turbo"):
                inp["useTurbo"] = True
            if payload.get("shift") not in (None, ""):
                inp["shift"] = payload["shift"]
            if payload.get("interpolatorModel"):
                inp["interpolatorModel"] = payload["interpolatorModel"]
            inp.setdefault("enablePromptExpansion", False)
        elif ver == "v2.5":
            inp.pop("useTurbo", None)
            inp.setdefault("enablePromptExpansion", True)
        if payload.get("enablePromptExpansion") is not None:
            inp["enablePromptExpansion"] = bool(payload.get("enablePromptExpansion"))
        if ver == "v2.6" and payload.get("audioUrl"):
            inp["audioUrl"] = payload["audioUrl"]
        if ver == "v2.7":
            if payload.get("videoUrl"):
                inp["videoUrl"] = payload["videoUrl"]
            if payload.get("audioUrl"):
                inp["audioUrl"] = payload["audioUrl"]
    return cap


def fill_required(inp: dict, payload: dict, cap: dict | None):
    if not cap:
        return
    req = cap.get("required") or []
    engine = inp.get("engine") or ""
    if "cfgScale" in req and "cfgScale" not in inp:
        inp["cfgScale"] = 4.0 if engine == "wan" else 1.0
    if "width" in req and "width" not in inp:
        inp["width"] = int(payload.get("width") or 864)
    if "height" in req and "height" not in inp:
        inp["height"] = int(payload.get("height") or 480)
    if "generateAudio" in req and "generateAudio" not in inp:
        inp["generateAudio"] = bool(payload.get("generateAudio"))
    if "duration" in req and "duration" in inp and engine in ("kling", "kling-v3"):
        inp["duration"] = str(inp["duration"])
    if "aspectRatio" in req and "aspectRatio" not in inp:
        inp["aspectRatio"] = payload.get("aspectRatio") or "9:16"
    if "frameRate" in req and "frameRate" not in inp:
        try:
            inp["frameRate"] = int(payload.get("frameRate") or 24)
        except (TypeError, ValueError):
            inp["frameRate"] = 24
    if "resolution" in req and "resolution" not in inp:
        ver = str(inp.get("version") or "")
        if engine == "wan" and ver == "v2.5":
            inp["resolution"] = payload.get("resolution") or "1080p"
        else:
            inp["resolution"] = payload.get("resolution") or "720p"


def build_workflow(payload: dict) -> dict:
    svc = None
    sid = (payload.get("serviceId") or "").strip()
    if sid:
        svc = find_service(sid)
    kind = payload.get("kind") or (svc or {}).get("category") or "image"
    if not svc:
        if kind == "video":
            svc = match_service(
                engine=payload.get("engine"),
                operation=payload.get("operation"),
                category="video",
            ) or find_service(DEFAULTS["videoServiceId"])
        else:
            svc = match_service(
                engine=payload.get("engine") or "comfy",
                operation=payload.get("operation") or "createImage",
                ecosystem=payload.get("ecosystem") or "krea2",
                model=payload.get("model"),
                category="image",
            ) or find_service(DEFAULTS["serviceId"])
    inp = dict((svc or {}).get("parameters") or {})
    for k in ("engine", "operation", "ecosystem", "model", "version", "provider"):
        if payload.get(k):
            inp[k] = payload[k]
    if payload.get("prompt"):
        inp["prompt"] = payload["prompt"]
    if payload.get("negativePrompt"):
        inp["negativePrompt"] = payload["negativePrompt"]
    _set_int(inp, payload, "width", 16, 2048)
    _set_int(inp, payload, "height", 16, 2048)
    _set_int(inp, payload, "steps", 1, 150)
    _set_int(inp, payload, "quantity", 1, 12)
    _set_int(inp, payload, "duration", 1, 30)
    _set_float(inp, payload, "cfgScale")
    if payload.get("sampler"):
        inp["sampler"] = payload["sampler"]
    if payload.get("scheduler"):
        inp["scheduler"] = payload["scheduler"]
    if payload.get("denoise") not in (None, ""):
        try:
            inp["denoise"] = float(payload["denoise"])
        except (TypeError, ValueError):
            pass
    if payload.get("resolution"):
        inp["resolution"] = payload["resolution"]
    if payload.get("aspectRatio"):
        inp["aspectRatio"] = payload["aspectRatio"]
    if payload.get("outputFormat") in ("jpeg", "png", "webP"):
        inp["outputFormat"] = payload["outputFormat"]
    seed = payload.get("seed")
    if seed not in (None, "", "random"):
        try:
            inp["seed"] = int(seed)
        except (TypeError, ValueError):
            pass
    dm = (payload.get("diffusionModel") or "").strip()
    if dm:
        inp["diffusionModel"] = dm
    loras = lora_map(payload)
    if loras:
        inp["loras"] = loras
    cap = apply_frames(inp, payload, svc)
    fill_required(inp, payload, cap)
    if cap:
        allowed = {"engine", "operation", "ecosystem", "model", "version", "provider",
                   "prompt", "negativePrompt", "loras", "diffusionModel", "seed",
                   "steps", "width", "height", "cfgScale", "quantity", "duration",
                   "sampler", "scheduler", "denoise"}
        for lst in (cap.get("required"), cap.get("optional"), cap.get("frameFields"), list((cap.get("constraints") or {}).keys()), list((cap.get("extraFlags") or {}).keys())):
            if lst:
                allowed.update(lst)
        inp = {k: v for k, v in inp.items() if k in allowed}
        if inp.get("engine") == "hunyuan" and isinstance(inp.get("loras"), dict):
            inp["loras"] = [{"air": k, "strength": v} for k, v in inp["loras"].items()]
    step = (svc or {}).get("step") or ("videoGen" if kind == "video" else "imageGen")
    return {
        "allowMatureContent": bool(payload.get("allowMatureContent", True)),
        "steps": [{"$type": step, "input": inp}],
        "_meta": {"serviceId": (svc or {}).get("id"), "serviceName": (svc or {}).get("name")},
    }


def parse_image_id(raw: str) -> int:
    import re
    s = (raw or "").strip()
    for pat in (r"/images/(\d+)", r"/image/(\d+)", r"[?&]imageId=(\d+)", r"[?&]id=(\d+)", r"^(\d+)$"):
        m = re.search(pat, s, re.I)
        if m:
            return int(m.group(1))
    raise ValueError("请填图片数字 ID 或完整网址")


def import_image(image_id: str) -> dict:
    return civitai_prov.import_image(image_id)


def _alias_backend(bid: str) -> str:
    aliases = {
        "hf": "huggingface",
        "ms": "modelscope-ai",
        "modelscope": "modelscope-ai",
        "魔搭": "modelscope-ai",
        "魔搭ai": "modelscope-ai",
        "魔搭cn": "modelscope-cn",
        "nano": "nano-gpt",
        "nanogpt": "nano-gpt",
        "nano_gpt": "nano-gpt",
    }
    bid = (bid or "civitai").strip()
    return aliases.get(bid, bid)


def _looks_civitai_import(q: str) -> bool:
    s = (q or "").strip()
    low = s.lower()
    if "civitai.com" in low or "civitai.red" in low:
        return True
    if re.search(r"/images/\d+", s, re.I):
        return True
    if re.fullmatch(r"\d+", s):
        return True
    return False


def handle_import(backend="civitai", q="", file_bytes=None, filename="", endpoint=None):
    """Provider-aware import. Never triggers generate."""
    import base64
    from providers import io_meta
    from providers import fal as fal_prov

    backend = _alias_backend(backend)
    filename = Path(filename or "").name
    if file_bytes:
        parsed = io_meta.parse_media_bytes(file_bytes, filename)
        side = io_meta.read_sidecar(filename) if filename else None
        if not side and q:
            side = io_meta.read_sidecar(q)
        if parsed and not parsed.get("empty"):
            try:
                from providers import civitai as civitai_mod
                parsed = civitai_mod.enrich_local_parse(parsed)
                samp, sched = civitai_mod._normalize_pair(parsed.get("sampler"), parsed.get("scheduler"))
                parsed["sampler"] = samp
                parsed["scheduler"] = sched
                if parsed.get("diffusionModel") or parsed.get("checkpointName"):
                    eco = civitai_mod._ecosystem_from_blob(parsed.get("diffusionModel"), parsed.get("checkpointName"), parsed.get("engine"))
                    engine, operation, model = "comfy", "createImage", "turbo"
                    ecosystem = eco or "krea2"
                    if ecosystem == "zImage":
                        engine, ecosystem = "sdcpp", "zImage"
                    elif ecosystem == "qwen":
                        engine, ecosystem = "sdcpp", "qwen"
                    svc = civitai_mod.match_service(engine=engine, operation=operation, ecosystem=ecosystem, model=model, category="image")
                    parsed.setdefault("kind", "image")
                    parsed.setdefault("engine", engine)
                    parsed.setdefault("operation", operation)
                    parsed.setdefault("ecosystem", ecosystem)
                    parsed.setdefault("model", model)
                    if svc:
                        parsed.setdefault("serviceId", svc.get("id"))
                        parsed.setdefault("serviceName", svc.get("name"))
            except Exception:
                pass
        if side:
            merged = io_meta.sidecar_to_import(side)
            for k, v in parsed.items():
                if k in ("empty", "error", "source"):
                    continue
                if v not in (None, "", []):
                    merged[k] = v
            merged["fileName"] = filename
            if parsed.get("prompt") or merged.get("prompt") or merged.get("serviceId"):
                merged["empty"] = False
                merged.pop("error", None)
            return 200, merged
        return 200, parsed
    q = (q or "").strip()
    if not q:
        return 400, {"error": "请填导入内容"}
    if _looks_civitai_import(q):
        try:
            return 200, import_image(q)
        except Exception as e:
            return 400, {"error": str(e)}
    side = io_meta.read_sidecar(q)
    if side:
        return 200, io_meta.sidecar_to_import(side)
    if backend == "fal":
        return fal_prov.import_request(q, endpoint=endpoint)
    if backend in ("huggingface", "modelscope", "modelscope-ai", "modelscope-cn", "nano-gpt", "nanogpt"):
        return 200, {
            "empty": True,
            "backend": backend,
            "prompt": "",
            "error": "Hugging Face / 魔搭没有云端按图反查。Civitai 图请贴 civitai 链接或数字 id；或上传带 parameters 的 PNG。",
        }
    try:
        return 200, import_image(q)
    except Exception as e:
        return 400, {"error": str(e)}


def submit(body, whatif=False):
    allow = True if not isinstance(body, dict) else bool(body.get("allowMatureContent", True))
    q = urllib.parse.urlencode({
        "whatif": "true" if whatif else "false",
        "wait": "0",
        "hideMatureContent": "false" if allow else "true",
    })
    return civitai(f"{ORCH}/v2/consumer/workflows?{q}", method="POST", body=body)


def save_blobs(wf: dict) -> list[dict]:
    saved = []
    wf_id = wf.get("id") or "wf"
    for step in wf.get("steps") or []:
        out = step.get("output") or {}
        items = []
        for key in ("images", "videos", "blobs"):
            items.extend(out.get(key) or [])
        for i, item in enumerate(items):
            url = item.get("url")
            if not url or item.get("available") is False:
                continue
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=120) as r:
                raw = r.read()
            if raw[:8] == b"\x89PNG\r\n\x1a\n":
                ext = ".png"
            elif raw[:3] == b"\xff\xd8\xff":
                ext = ".jpg"
            elif raw[4:8] == b"ftyp" or b"ftyp" in raw[:12]:
                ext = ".mp4"
            else:
                ext = ".bin"
            name = f"{wf_id}_{i}{ext}"
            (OUT / name).write_bytes(raw)
            saved.append({"file": name, "url": f"/out/{name}", "bytes": len(raw), "kind": "video" if ext == ".mp4" else "image"})
    return saved


def save_fal_result(data: dict) -> list[dict]:
    result = data.get("result") or {}
    urls = []
    for key in ("images", "image", "video", "videos", "audio", "audios"):
        val = result.get(key)
        if isinstance(val, str) and val.startswith("http"):
            urls.append(val)
        elif isinstance(val, dict) and val.get("url"):
            urls.append(val["url"])
        elif isinstance(val, list):
            for item in val:
                if isinstance(item, str) and item.startswith("http"):
                    urls.append(item)
                elif isinstance(item, dict) and item.get("url"):
                    urls.append(item["url"])
    saved = []
    job_id = (data.get("id") or "fal").replace("|", "_").replace("/", "_")
    for i, url in enumerate(urls):
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=120) as r:
            raw = r.read()
        if raw[:8] == b"\x89PNG\r\n\x1a\n":
            ext = ".png"
        elif raw[:3] == b"\xff\xd8\xff":
            ext = ".jpg"
        elif b"ftyp" in raw[:12]:
            ext = ".mp4"
        elif raw[:4] == b"RIFF":
            ext = ".webp"
        else:
            ext = ".bin"
        name = f"{job_id}_{i}{ext}"
        (OUT / name).write_bytes(raw)
        kind = "video" if ext == ".mp4" else ("audio" if ext in (".wav", ".mp3") else "image")
        saved.append({"file": name, "url": f"/out/{name}", "bytes": len(raw), "kind": kind})
    return saved



def save_upload_out(data_url: str, filename: str = "") -> dict:
    """Persist a browser data URL under /out and return a studio-relative url.

    Used by storyboard local upload (POST /api/upload-out). Relative /out paths
    are later materialized to data URLs before Fal submit.
    """
    import base64
    import re
    import time
    s = (data_url or "").strip()
    if not s.startswith("data:"):
        raise ValueError("需要 dataUrl")
    m = re.match(r"^data:([^;]+);base64,(.+)$", s, re.S)
    if not m:
        raise ValueError("dataUrl 不是合法 base64 data URI")
    ctype = (m.group(1) or "application/octet-stream").split(";")[0].strip().lower()
    try:
        raw = base64.b64decode(m.group(2), validate=False)
    except Exception as e:
        raise ValueError(f"base64 解码失败: {e}") from e
    if not raw:
        raise ValueError("空文件")
    ext = {
        "image/png": ".png",
        "image/jpeg": ".jpg",
        "image/jpg": ".jpg",
        "image/webp": ".webp",
        "image/gif": ".gif",
        "video/mp4": ".mp4",
        "video/webm": ".webm",
    }.get(ctype)
    if not ext:
        name = (filename or "").lower()
        for e in (".png", ".jpg", ".jpeg", ".webp", ".gif", ".mp4", ".webm"):
            if name.endswith(e):
                ext = ".jpg" if e == ".jpeg" else e
                break
        else:
            ext = ".bin"
    safe = re.sub(r"[^a-zA-Z0-9._-]+", "_", (filename or "upload").rsplit("/", 1)[-1])[:60] or "upload"
    if "." in safe:
        safe = safe.rsplit(".", 1)[0]
    stamp = time.strftime("%Y%m%d%H%M%S")
    out_name = f"upload_{stamp}_{safe}{ext}"
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / out_name).write_bytes(raw)
    kind = "video" if ext in (".mp4", ".webm") else "image"
    return {"file": out_name, "url": f"/out/{out_name}", "bytes": len(raw), "kind": kind, "contentType": ctype}


class Handler(BaseHTTPRequestHandler):
    server_version = "CivitaiStudio/2.0"

    def log_message(self, fmt, *args):
        print("[web]", self.address_string(), fmt % args, flush=True)

    def _json(self, code, obj):
        data = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _bytes(self, code, data, ctype):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        if "html" in (ctype or "") or "javascript" in (ctype or ""):
            self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
            self.send_header("Pragma", "no-cache")
        self.end_headers()
        self.wfile.write(data)

    def _read_json(self):
        n = int(self.headers.get("Content-Length") or 0)
        if n <= 0:
            return {}
        return json.loads(self.rfile.read(n).decode())

    def _cancel_job(self, path):
        rest = urllib.parse.unquote(path.split("/api/jobs/", 1)[1])
        job_id = rest[:-7] if rest.endswith("/cancel") else rest
        job_id = job_id.strip("/")
        if not job_id:
            return self._json(400, {"error": "缺少任务 id"})
        prov = providers.resolve_from_job(job_id)
        code, data = prov.cancel_job(job_id)
        return self._json(code, data)

    def do_GET(self):
        try:
            return self._handle_get()
        except Exception as e:
            print("[web] GET", e, flush=True)
            try:
                return self._json(500, {"error": "服务器出错"})
            except Exception:
                return

    def _handle_get(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        qs = urllib.parse.parse_qs(parsed.query)
        if path in ("/", "/index.html"):
            return self._bytes(200, (STATIC / "index.html").read_bytes(), "text/html; charset=utf-8")
        # Seko storyboard canvas (PLAN-v0789): /storyboard + /cloud-nodes share one shell.
        if path in ("/storyboard.html", "/storyboard", "/cloud-nodes.html", "/cloud-nodes"):
            fp = STATIC / "storyboard.html"
            if not fp.exists():
                return self._json(404, {"error": "storyboard.html missing"})
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(fp.stat().st_size))
            self.end_headers()
            self.wfile.write(fp.read_bytes())
            return
        # LiteGraph legacy shell (top-bar link /litegraph)
        if path in ("/litegraph.html", "/litegraph"):
            fp = STATIC / "cloud-nodes.html"
            if not fp.exists():
                return self._json(404, {"error": "cloud-nodes.html missing"})
            return self._bytes(200, fp.read_bytes(), "text/html; charset=utf-8")
        # Cache-bust: old chain demo lived on LiteGraph shell
        if path in ("/cloud-nodes-chain.html", "/cloud-nodes-chain"):
            self.send_response(302)
            self.send_header("Location", "/litegraph?demo=chain&v=0780")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            return
        if path.startswith("/static/"):
            name = Path(path.split("/static/", 1)[1]).name
            fp = STATIC / name
            if not fp.exists():
                return self._json(404, {"error": "not found"})
            ctype = mimetypes.guess_type(str(fp))[0] or "application/octet-stream"
            return self._bytes(200, fp.read_bytes(), ctype)
        if path == "/api/providers":
            return self._json(200, {"items": providers.list_public()})
        if path == "/api/workflows":
            civ = providers.get("civitai")
            q = (qs.get("q") or [""])[0]
            user = (qs.get("username") or [""])[0]
            nsfw_raw = (qs.get("nsfw") or ["true"])[0]
            nsfw = str(nsfw_raw).lower() in ("1", "true", "yes")
            code, data = civ.list_workflows(q=q, username=user, nsfw=nsfw)
            return self._json(code, data)
        if path == "/api/workflows/air":
            civ = providers.get("civitai")
            filename = (qs.get("filename") or qs.get("q") or [""])[0]
            if not filename:
                return self._json(400, {"error": "filename required"})
            try:
                code, data = civ.lookup_air_file(filename)
            except Exception as e:
                return self._json(502, {"error": str(e)})
            return self._json(code, data)
        if path == "/api/workflows/import":
            civ = providers.get("civitai")
            raw = (qs.get("url") or qs.get("q") or [""])[0]
            try:
                code, data = civ.import_workflow(raw)
            except ValueError as e:
                return self._json(400, {"error": str(e)})
            except Exception as e:
                return self._json(502, {"error": str(e)})
            return self._json(code, data)
        if path == "/api/catalog":
            backend = (qs.get("backend") or ["civitai"])[0]
            prov = providers.get(backend) or providers.get("civitai")
            if backend != "civitai" and (qs.get("refresh") or ["0"])[0] in ("1", "true"):
                pass
            elif backend == "civitai" and (qs.get("refresh") or ["0"])[0] in ("1", "true"):
                try:
                    prov.refresh_catalog()
                except Exception as e:
                    print("catalog refresh", e, flush=True)
            paging_requested = catalog_paging_requested(qs)
            page, page_size = parse_catalog_page(qs)
            body = build_catalog_response(
                prov,
                (qs.get("q") or [""])[0],
                (qs.get("category") or [""])[0],
                (qs.get("status") or [""])[0],
                page,
                page_size,
                backend=backend,
                paging_requested=paging_requested,
            )
            return self._json(200, body)
        if path == "/api/defaults":
            civ = providers.get("civitai")
            extra = civ.defaults_payload() if civ else {}
            keys = {p.id: p.has_key() for p in providers.all_providers()}
            extra.update({
                "hasToken": keys.get("civitai", False),
                "hasFal": keys.get("fal", False),
                "hasKeys": keys,
                "providers": providers.list_public(),
            })
            return self._json(200, extra)
        if path == "/api/capabilities":
            fp = DOCS / "capabilities.json"
            if not fp.exists():
                return self._json(404, {"error": "no capabilities.json"})
            return self._json(200, json.loads(fp.read_text()))
        if path == "/api/services":
            limit = (qs.get("limit") or ["50"])[0]
            offset = (qs.get("offset") or ["0"])[0]
            code, data = civitai(f"{ORCH}/v2/services?limit={urllib.parse.quote(str(limit))}&offset={urllib.parse.quote(str(offset))}")
            return self._json(code, data)
        if path == "/api/outs":
            items = []
            for fp in sorted(OUT.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
                if not fp.is_file():
                    continue
                ext = fp.suffix.lower()
                if ext not in (".jpg", ".jpeg", ".png", ".webp", ".gif", ".mp4", ".webm", ".wav", ".mp3"):
                    continue
                items.append({
                    "file": fp.name,
                    "url": f"/out/{fp.name}",
                    "bytes": fp.stat().st_size,
                    "kind": "video" if ext in (".mp4", ".webm") else ("audio" if ext in (".wav", ".mp3") else "image"),
                })
            return self._json(200, {"items": items[:60]})
        if path == "/api/jobs":
            code, data = civitai(f"{ORCH}/v2/consumer/workflows")
            return self._json(code, data)
        if path == "/api/blobs":
            blob = (qs.get("blobId") or [""])[0]
            if not blob:
                return self._json(400, {"error": "blobId required"})
            code, data = civitai(f"{ORCH}/v2/consumer/blobs?blobId={urllib.parse.quote(blob)}")
            return self._json(code, data)
        if path == "/api/go":
            print("[web] GO_CLICK", flush=True)
            return self._json(200, {"ok": True})
        if path == "/api/health":
            code, data = civitai(f"{ORCH}/health")
            return self._json(code, data if isinstance(data, dict) else {"status": data})
        if path.startswith("/api/jobs/"):
            wf_id = urllib.parse.unquote(path.split("/api/jobs/", 1)[1])
            prov = providers.resolve_from_job(wf_id)
            code, data = prov.job_status(wf_id)
            return self._json(code, data)
        if path == "/api/import":
            backend = (qs.get("backend") or ["civitai"])[0]
            q = (qs.get("q") or qs.get("query") or [""])[0]
            endpoint = (qs.get("endpoint") or qs.get("serviceId") or [""])[0]
            code, data = handle_import(backend, q, endpoint=endpoint or None)
            return self._json(code, data)
        if path.startswith("/api/import-image/"):
            image_id = urllib.parse.unquote(path.split("/api/import-image/", 1)[1]).strip()
            try:
                return self._json(200, import_image(image_id))
            except Exception as e:
                return self._json(400, {"error": str(e)})
        if path.startswith("/api/model-version/"):
            vid = urllib.parse.unquote(path.split("/api/model-version/", 1)[1])
            code, data = civitai(f"{SITE}/model-versions/{vid}")
            if isinstance(data, dict):
                files = []
                for f in (data.get("files") or []):
                    if not isinstance(f, dict):
                        continue
                    files.append({
                        "id": f.get("id"),
                        "name": f.get("name"),
                        "type": f.get("type"),
                        "downloadUrl": f.get("downloadUrl") or f.get("download_url"),
                    })
                download = next((x.get("downloadUrl") for x in files if x.get("downloadUrl")), None)
                vid = data.get("id")
                if not download and vid:
                    download = f"https://civitai.com/api/download/models/{vid}"
                return self._json(code, {
                    "id": data.get("id"),
                    "name": data.get("name"),
                    "air": data.get("air"),
                    "baseModel": data.get("baseModel"),
                    "model": (data.get("model") or {}).get("name"),
                    "type": (data.get("model") or {}).get("type"),
                    "trainedWords": data.get("trainedWords") or [],
                    "files": files,
                    "downloadUrl": download,
                })
            return self._json(code, data)
        if path == "/api/search":
            q = (qs.get("q") or [""])[0]
            types = (qs.get("type") or ["LORA"])[0]
            nsfw_raw = (qs.get("nsfw") or ["true"])[0]
            nsfw = str(nsfw_raw).lower() in ("1", "true", "yes")
            backend = _alias_backend((qs.get("backend") or ["civitai"])[0])
            prov = providers.get(backend) or providers.get("civitai")
            if backend != "civitai" and hasattr(prov, "search_loras"):
                code, data = prov.search_loras(q, nsfw=nsfw)
                if isinstance(data, dict):
                    data.setdefault("backend", backend)
                    data.setdefault("nsfw", nsfw)
                return self._json(code, data if isinstance(data, dict) else {"items": []})
            url = (
                f"{SITE}/models?limit=8&query={urllib.parse.quote(q)}"
                f"&types={urllib.parse.quote(types)}&nsfw={'true' if nsfw else 'false'}"
            )
            code, data = civitai(url)
            items = []
            if isinstance(data, dict):
                for it in (data.get("items") or [])[:8]:
                    vers = [{"id": v.get("id"), "name": v.get("name"), "baseModel": v.get("baseModel")} for v in (it.get("modelVersions") or [])[:6]]
                    items.append({"id": it.get("id"), "name": it.get("name"), "type": it.get("type"), "source": "civitai", "nsfw": it.get("nsfw"), "versions": vers})
            return self._json(code, {"items": items, "nsfw": nsfw, "backend": "civitai"})
        if path.startswith("/out/"):
            name = Path(path.split("/out/", 1)[1]).name
            fp = OUT / name
            if not fp.exists():
                return self._json(404, {"error": "not found"})
            ctype = mimetypes.guess_type(str(fp))[0] or "application/octet-stream"
            return self._bytes(200, fp.read_bytes(), ctype)
        self._json(404, {"error": "not found"})

    def do_POST(self):
        try:
            return self._handle_post()
        except Exception as e:
            print("[web] POST", e, flush=True)
            try:
                return self._json(500, {"error": "服务器出错"})
            except Exception:
                return

    def _handle_post(self):
        path = urllib.parse.urlparse(self.path).path
        try:
            payload = self._read_json()
        except Exception:
            return self._json(400, {"error": "invalid json"})
        if path == "/api/import":
            raw = None
            b64 = payload.get("fileB64") or payload.get("file")
            if b64:
                import base64
                if isinstance(b64, str) and "," in b64:
                    b64 = b64.split(",", 1)[1]
                try:
                    raw = base64.b64decode(b64)
                except Exception:
                    return self._json(400, {"error": "文件不是合法 base64"})
            code, data = handle_import(
                payload.get("backend") or "civitai",
                payload.get("q") or payload.get("query") or "",
                file_bytes=raw,
                filename=payload.get("fileName") or payload.get("filename") or "",
                endpoint=payload.get("endpoint") or payload.get("serviceId"),
            )
            return self._json(code, data)
        if path == "/api/upload-out":
            try:
                data_url = payload.get("dataUrl") or payload.get("data_url") or ""
                filename = payload.get("filename") or payload.get("fileName") or "upload"
                info = save_upload_out(data_url, filename)
                return self._json(200, info)
            except ValueError as e:
                return self._json(400, {"error": str(e)})
            except Exception as e:
                print("[web] upload-out", e, flush=True)
                return self._json(500, {"error": "上传失败"})
        if path == "/api/graph/compile":
            from providers.graph_compile import compile_graph
            result = compile_graph(payload.get("graph") if isinstance(payload.get("graph"), dict) else payload)
            code = 200 if result.get("ok") else 400
            return self._json(code, result)
        if path in ("/api/generate", "/api/whatif"):
            if path == "/api/generate":
                from providers.graph_compile import reject_staged_generate
                blocked = reject_staged_generate(payload)
                if blocked:
                    return self._json(400, blocked)
            # Canvas may pack image_urls / input_references; mirror to images.
            from providers.ref_images import normalize_payload_refs, collect_ref_images
            normalize_payload_refs(payload)
            prov = providers.resolve_from_payload(payload)
            if path == "/api/generate" and prov and prov.id in ("modelscope-ai", "modelscope-cn"):
                from providers.capabilities import modelscope_t2i_refs_error
                n_refs = len(collect_ref_images(payload, include_primary=True))
                t2i_err = modelscope_t2i_refs_error(payload.get("serviceId"), n_refs)
                if t2i_err:
                    return self._json(400, {"error": t2i_err, "backend": prov.id})
            if path == "/api/whatif":
                code, data = prov.whatif(payload)
            else:
                code, data = prov.generate(payload)
            return self._json(code, data)
        if path == "/api/catalog/refresh":
            try:
                return self._json(200, refresh_catalog())
            except Exception as e:
                return self._json(502, {"error": str(e)})
        if path.startswith("/api/recipes/"):
            recipe = urllib.parse.unquote(path.split("/api/recipes/", 1)[1]).strip("/")
            q = urllib.parse.urlencode({
                "whatif": "true" if payload.get("whatif") else "false",
                "allowMatureContent": "true" if payload.get("allowMatureContent", True) else "false",
            })
            body = payload.get("input") or payload
            code, data = civitai(f"{ORCH}/v2/consumer/recipes/{recipe}?{q}", method="POST", body=body)
            return self._json(code, data)
        if path.startswith("/api/jobs/") and path.rstrip("/").endswith("/cancel"):
            return self._cancel_job(path)
        self._json(404, {"error": "not found"})

    def do_DELETE(self):
        try:
            path = urllib.parse.urlparse(self.path).path
            if path.startswith("/api/jobs/") and path.rstrip("/").endswith("/cancel"):
                return self._cancel_job(path)
            return self._json(404, {"error": "not found"})
        except Exception as e:
            print("[web] DELETE", e, flush=True)
            try:
                return self._json(500, {"error": "服务器出错"})
            except Exception:
                return


def main():
    civ = providers.get("civitai")
    n = 0
    if civ:
        try:
            n = civ.defaults_payload().get("catalogTotal") or 0
        except Exception:
            n = 0
    httpd = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"Civitai Studio http://127.0.0.1:{PORT} providers={','.join(p.id for p in providers.all_providers())} catalog={n}", flush=True)
    httpd.serve_forever()


if __name__ == "__main__":
    main()
