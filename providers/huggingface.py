from __future__ import annotations

import base64
import json
import re
import os
import time
import uuid
import threading
import urllib.error
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import quote

from .base import Provider
from .http import collect_urls, extract_error, json_call, parse_job_id, raw_call, save_bytes, save_media_urls
from .io_meta import looks_like_civitai_service

TOKEN_PATH = Path.home() / ".config/huggingface/token"
ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
ROUTER = "https://router.huggingface.co"
HUB = "https://huggingface.co/api/models"
LEGACY = f"{ROUTER}/hf-inference/models"

# Prefer Fal for FLUX schnell (hf-inference is 410). nscale is also live.
# replicate rejects POST /v1/images/generations ("Not allowed to POST … provider replicate").
_PREF = ("fal-ai", "nscale", "wavespeed", "together", "hf-inference")
_SKIP_OPENAI = {"replicate"}
_MAP_CACHE = {"at": 0.0, "items": {}}
_MAP_TTL = 300
_HUB_LIST_CACHE = {"at": 0.0, "pipes": {}}
_HUB_LIST_LOCK = threading.Lock()
_HUB_PAGE = 100
_HUB_MAX_PAGES = 6
_PIPE_BY_CATEGORY = {
    "image": ("text-to-image", "image-to-image"),
    "video": ("text-to-video", "image-to-video"),
    "upscale": ("image-to-image", "text-to-image"),
}
_ADAPTER_RE = re.compile(r"(lora|lycoris|locon|lokr)", re.I)


def hf_key() -> str:
    try:
        t = TOKEN_PATH.read_text().strip()
        if t:
            return t
    except Exception:
        pass
    return (os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_TOKEN") or "").strip()


def load_items():
    fp = DOCS / "hf-models.json"
    if not fp.exists():
        return []
    try:
        return json.loads(fp.read_text()).get("items") or []
    except Exception:
        return []


def model_id(service_id: str) -> str:
    s = (service_id or "").strip().lstrip("/")
    if s.startswith("hf/"):
        s = s[3:]
    if s.startswith("huggingface/"):
        s = s[len("huggingface/"):]
    return s


def hub_probe(mid: str) -> tuple[int, dict]:
    """One real Hub lookup for the model + its inference provider mapping.

    Returns the HTTP code untouched so callers can separate 404 (no such model)
    from a network failure — whatif needs that difference, inference_mapping()
    does not.
    """
    key = hf_key()
    headers = {"Accept": "application/json"}
    if key:
        headers["Authorization"] = f"Bearer {key}"
    url = f"{HUB}/{quote(mid, safe='/')}?expand[]=inferenceProviderMapping"
    code, data = json_call(url, headers=headers, timeout=20)
    return code, data if isinstance(data, dict) else {"error": str(data)}


def _normalize_mapping(raw) -> dict:
    """Hub `inferenceProviderMapping` is a list of {provider, status, ...} now.

    Older payloads were `{providerName: {status, providerId}}`. generate/whatif
    and the catalog live-filter all need the dict shape.
    """
    if isinstance(raw, dict):
        if not raw:
            return {}
        if all(isinstance(v, dict) for v in raw.values()):
            return raw
        return {}
    if isinstance(raw, list):
        out = {}
        for it in raw:
            if not isinstance(it, dict):
                continue
            name = (it.get("provider") or it.get("name") or "").strip()
            if name:
                out[name] = it
        return out
    return {}


def _has_live_provider(mapping) -> bool:
    for info in _normalize_mapping(mapping).values():
        if isinstance(info, dict) and (info.get("status") or "").lower() == "live":
            return True
    return False


def inference_mapping(mid: str) -> dict:
    now = time.time()
    cached = (_MAP_CACHE.get("items") or {}).get(mid)
    if cached is not None and (now - _MAP_CACHE.get("at") or 0) < _MAP_TTL:
        return cached
    code, data = hub_probe(mid)
    mapping = {}
    if code == 200 and isinstance(data, dict):
        mapping = _normalize_mapping(data.get("inferenceProviderMapping"))
    items = dict(_MAP_CACHE.get("items") or {})
    items[mid] = mapping
    _MAP_CACHE["items"] = items
    _MAP_CACHE["at"] = now
    return mapping


def _style_for(provider: str) -> str:
    if provider == "hf-inference":
        return "bytes"
    if provider in ("fal-ai", "wavespeed"):
        return "fal"
    return "openai"


def _provider_candidates(mapping: dict, mid: str, spec: dict) -> list:
    live = []
    for name, info in (mapping or {}).items():
        if not isinstance(info, dict):
            continue
        st = (info.get("status") or "").lower()
        if st == "error":
            continue
        live.append((name, info.get("providerId") or mid, info))
    live_ok = [(n, p, i) for n, p, i in live if (i.get("status") or "").lower() == "live"]
    if not live_ok:
        live_ok = live
    ordered = []
    seen = set()
    for want in _PREF:
        for name, pid, info in live_ok:
            if name == want and name not in seen:
                ordered.append((name, pid, _style_for(name)))
                seen.add(name)
    for name, pid, info in live_ok:
        if name not in seen:
            ordered.append((name, pid, _style_for(name)))
            seen.add(name)
    if not ordered:
        ordered = [
            ("fal-ai", mid, "fal"),
            ("nscale", mid, "openai"),
            ("hf-inference", mid, "bytes"),
        ]
    return [(n, p, s) for n, p, s in ordered if not (s == "openai" and n in _SKIP_OPENAI)]


def _auth_headers(key: str, extra=None):
    h = {"Authorization": f"Bearer {key}"}
    if extra:
        h.update(extra)
    return h


def _prompt_body(payload: dict) -> dict:
    params = {}
    if payload.get("negativePrompt"):
        params["negative_prompt"] = payload["negativePrompt"]
    if payload.get("steps"):
        try:
            params["num_inference_steps"] = int(payload["steps"])
        except (TypeError, ValueError):
            pass
    if payload.get("cfgScale") not in (None, ""):
        try:
            params["guidance_scale"] = float(payload["cfgScale"])
        except (TypeError, ValueError):
            pass
    if payload.get("width"):
        try:
            params["width"] = int(payload["width"])
        except (TypeError, ValueError):
            pass
    if payload.get("height"):
        try:
            params["height"] = int(payload["height"])
        except (TypeError, ValueError):
            pass
    if payload.get("seed") not in (None, "", "random"):
        try:
            n = int(payload["seed"])
            limit = 2147483647
            if n < -1:
                n = -1
            elif n > limit:
                n = n % limit or limit
            params["seed"] = n
        except (TypeError, ValueError):
            pass
    sched = (payload.get("scheduler") or "").strip()
    if sched:
        params["scheduler"] = sched
    return params


def _save_json_images(data: dict, jid: str, meta=None) -> list:
    saved = []
    for i, item in enumerate(data.get("data") or []):
        if not isinstance(item, dict):
            continue
        stem = jid if i == 0 else f"{jid}_{i}"
        if item.get("b64_json"):
            try:
                raw = base64.b64decode(item["b64_json"])
            except Exception:
                continue
            saved.extend(save_bytes(raw, stem, meta=meta))
        elif item.get("url"):
            saved.extend(save_media_urls([item["url"]], stem, meta=meta))
    urls = collect_urls(data)
    if not saved and urls:
        saved = save_media_urls(urls, jid, meta=meta)
    return saved


def _openai_body(provider_id: str, payload: dict) -> dict:
    body = {
        "model": provider_id,
        "prompt": payload.get("prompt") or "",
        "response_format": "b64_json",
        "n": 1,
    }
    w, h = payload.get("width"), payload.get("height")
    try:
        if w and h:
            body["size"] = f"{int(w)}x{int(h)}"
    except (TypeError, ValueError):
        pass
    return body


def _call_openai(provider: str, provider_id: str, payload: dict, key: str, timeout: int):
    url = f"{ROUTER}/{provider}/v1/images/generations"
    body = _openai_body(provider_id, payload)
    headers = _auth_headers(key)
    code, data = json_call(url, method="POST", headers=headers, body=body, timeout=timeout)
    return code, data if isinstance(data, dict) else {"error": str(data)}, body


def _maybe_lora_pid(pid: str, payload: dict) -> str:
    """Keep the mapped HF providerId. Router does not host Fal `/lora` siblings."""
    return (pid or "").lstrip("/")


def _force_loras(body: dict, payload: dict) -> None:
    if body.get("loras"):
        return
    try:
        from . import fal as fal_mod
    except Exception:
        return
    cleaned = []
    for it in (payload or {}).get("loras") or []:
        if isinstance(it, str) and it.strip().startswith("http"):
            cleaned.append({"path": it.strip(), "scale": 0.8})
            continue
        if not isinstance(it, dict):
            continue
        path = fal_mod._fal_lora_path(it)
        if not path:
            continue
        scale_raw = it.get("scale")
        if scale_raw in (None, ""):
            scale_raw = it.get("strength")
        cleaned.append({"path": path, "scale": fal_mod._clip_lora_scale(scale_raw, 0.8)})
    if cleaned:
        body["loras"] = cleaned[:3]


def fal_style_wants_image(pid: str, payload: dict) -> bool:
    """Router fal/wavespeed style is the only HF path that forwards an input image."""
    blob = ((pid or "") + " " + str((payload or {}).get("task") or "")).lower()
    return any(x in blob for x in ("image-to-image", "kontext", "/edit", "i2i"))


def _fal_body(pid: str, payload: dict) -> dict:
    body = {"prompt": payload.get("prompt") or ""}
    params = _prompt_body(payload)
    if params.get("negative_prompt"):
        body["negative_prompt"] = params["negative_prompt"]
    if params.get("seed") is not None:
        body["seed"] = params["seed"]
    if params.get("num_inference_steps"):
        body["num_inference_steps"] = params["num_inference_steps"]
    if params.get("guidance_scale") is not None:
        body["guidance_scale"] = params["guidance_scale"]
    if params.get("width") and params.get("height"):
        body["image_size"] = {"width": params["width"], "height": params["height"]}
    if params.get("scheduler"):
        body["scheduler"] = params["scheduler"]
    wants_img = fal_style_wants_image(pid, payload)
    img = (payload.get("firstFrame") or payload.get("sourceImage") or payload.get("image_url") or "").strip()
    extra = [x for x in (payload.get("images") or []) if x]
    if img and img not in extra:
        extra = [img] + extra
    if extra and wants_img:
        if len(extra) == 1:
            body["image_url"] = extra[0]
        else:
            body["image_urls"] = extra[:9]
    try:
        from . import fal as fal_mod
        fal_mod.apply_fal_loras(body, payload, fal_mod.find_model(pid) or {"id": pid}, pid)
    except Exception:
        pass
    _force_loras(body, payload or {})
    return body


def _call_fal(provider: str, provider_id: str, payload: dict, key: str, timeout: int):
    pid = _maybe_lora_pid((provider_id or "").lstrip("/"), payload or {})
    url = f"{ROUTER}/{provider}/{pid}"
    body = _fal_body(pid, payload)
    headers = _auth_headers(key)
    code, data = json_call(url, method="POST", headers=headers, body=body, timeout=timeout)
    return code, data if isinstance(data, dict) else {"error": str(data)}, body


def _bytes_body(payload: dict, spec: dict) -> tuple[dict, str]:
    task = spec.get("task") or "text-to-image"
    params = _prompt_body(payload)
    if task == "text-to-video" and payload.get("duration"):
        try:
            params["num_frames"] = max(8, int(payload["duration"]) * 8)
        except (TypeError, ValueError):
            pass
    body = {"inputs": payload.get("prompt") or ""}
    if params:
        body["parameters"] = params
    return body, ("video/mp4" if task == "text-to-video" else "image/png")


def _call_bytes(mid: str, payload: dict, spec: dict, key: str, timeout: int):
    body, accept = _bytes_body(payload, spec)
    headers = _auth_headers(key, {"Content-Type": "application/json", "Accept": accept})
    code, raw, ctype = raw_call(f"{LEGACY}/{mid}", method="POST", headers=headers, body=body, timeout=timeout)
    data = None
    if (ctype or "").startswith("application/json") or (raw[:1] in (b"{", b"[")):
        try:
            data = json.loads(raw.decode("utf-8", "replace"))
        except Exception:
            data = {"error": raw[:500].decode("utf-8", "replace")}
    return code, data, raw, ctype, body


HF_PIPES = {
    "text-to-image": ("image", "text-to-image", ["t2i"], False, False),
    "image-to-image": ("image", "image-to-image", ["i2i"], True, False),
    "text-to-video": ("video", "text-to-video", ["t2v"], False, False),
    "image-to-video": ("video", "image-to-video", ["i2v"], False, True),
}


def _alnum(s):
    return "".join(ch for ch in (s or "").lower() if ch.isalnum())


from .hub_classify import (  # noqa: E402
    _UPSCALE_RE,
    apply_upscale_category as _apply_upscale_category,
    hub_upscale_blob,
)




def _hf_headers():
    h = {"Accept": "application/json"}
    k = hf_key()
    if k:
        h["Authorization"] = f"Bearer {k}"
    return h


def _hf_row(mid, name, pipe):
    spec = HF_PIPES.get(pipe) or ("image", "text-to-image", ["t2i"], False, False)
    cat, task, tags, needs_src, needs_ff = spec
    row = {
        "id": mid,
        "name": name or mid.split("/")[-1],
        "category": cat,
        "backend": "huggingface",
        "status": "available",
        "task": task,
        "tags": list(tags),
        "pipelineTag": pipe,
    }
    if needs_src:
        row["needsSource"] = True
    if needs_ff:
        row["needsFirstFrame"] = True
    return _apply_upscale_category(row)


def search_hf(q, pins=None):
    q = (q or "").strip()
    items, seen = [], set()
    pins = pins or []
    needle = _alnum(q)
    for p in pins:
        pid = p.get("id")
        if pid and (needle in _alnum(p.get("name")) or needle in _alnum(pid)):
            items.append(p)
            seen.add(pid)
    if q.count("/") == 1 and " " not in q and q not in seen:
        code, data = json_call(f"{HUB}/{quote(q, safe='/')}", headers=_hf_headers(), timeout=20)
        if code == 200 and isinstance(data, dict):
            mid = data.get("id") or q
            pipe = data.get("pipeline_tag") or "text-to-image"
            if pipe not in HF_PIPES:
                pipe = "text-to-image"
            row = _hf_row(mid, mid.split("/")[-1], pipe)
            items.insert(0, row)
            seen.add(mid)
    url = f"{HUB}?search={quote(q)}&limit=50"
    code, data = json_call(url, headers=_hf_headers(), timeout=25)
    models = data if isinstance(data, list) else []
    for it in models:
        if not isinstance(it, dict):
            continue
        mid = (it.get("id") or "").strip()
        pipe = it.get("pipeline_tag") or ""
        if not mid or mid in seen or pipe not in HF_PIPES:
            continue
        seen.add(mid)
        items.append(_hf_row(mid, mid.split("/")[-1], pipe))
    return items


def search_loras(q: str, limit: int = 8):
    """Official Hub list: GET /api/models?search=&filter=lora."""
    q = (q or "").strip()
    items = []
    seen = set()
    if q.count("/") == 1 and " " not in q:
        code, data = json_call(f"{HUB}/{quote(q, safe='/')}", headers=_hf_headers(), timeout=20)
        if code == 200 and isinstance(data, dict):
            mid = data.get("id") or q
            items.append({
                "id": mid,
                "name": mid,
                "path": mid,
                "type": "LORA",
                "source": "huggingface",
                "versions": [{"id": mid, "name": data.get("pipeline_tag") or "lora"}],
            })
            seen.add(mid)
    url = f"{HUB}?search={quote(q)}&filter=lora&limit={int(limit)}"
    code, data = json_call(url, headers=_hf_headers(), timeout=25)
    models = data if isinstance(data, list) else []
    for it in models:
        if not isinstance(it, dict):
            continue
        mid = (it.get("id") or "").strip()
        if not mid or mid in seen:
            continue
        seen.add(mid)
        items.append({
            "id": mid,
            "name": mid,
            "path": mid,
            "type": "LORA",
            "source": "huggingface",
            "versions": [{"id": mid, "name": it.get("pipeline_tag") or "lora"}],
        })
        if len(items) >= limit:
            break
    return 200, {"items": items, "backend": "huggingface"}


def _link_next(headers) -> str:
    link = ""
    if isinstance(headers, dict):
        link = headers.get("Link") or headers.get("link") or ""
    for part in (link or "").split(","):
        if 'rel="next"' in part:
            m = re.search(r"<([^>]+)>", part)
            if m:
                return m.group(1)
    return ""


def _is_adapter_id(mid: str) -> bool:
    """LoRA/LyCORIS adapters are not generation services. LoRA search is a separate API."""
    return bool(_ADAPTER_RE.search(mid or ""))


def _hub_get(url: str, timeout: int = 25):
    """Hub list GET that keeps Link headers for cursor pagination."""
    headers = _hf_headers()
    hdrs = {
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0",
    }
    hdrs.update(headers or {})
    req = urllib.request.Request(url, headers=hdrs, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read()
            try:
                parsed = json.loads(raw.decode())
            except json.JSONDecodeError:
                parsed = {"raw": raw[:2000].decode("utf-8", "replace")}
            return r.status, parsed, dict(r.headers)
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            parsed = {"raw": raw[:2000]}
        if isinstance(parsed, dict):
            parsed = dict(parsed)
            parsed.setdefault("error", extract_error(parsed, f"HTTP {e.code}"))
        return e.code, parsed, dict(e.headers)
    except urllib.error.URLError as e:
        return 502, {"error": "网络错误", "detail": str(getattr(e, "reason", e))}, {}
    except Exception as e:
        return 502, {"error": "请求失败", "detail": str(e)}, {}


def _pipes_for_category(category: str) -> tuple:
    from .catalog_ops import canonical_category

    want = canonical_category(category)
    if want in _PIPE_BY_CATEGORY:
        return _PIPE_BY_CATEGORY[want]
    if want:
        return tuple(k for k, spec in HF_PIPES.items() if spec[0] == want)
    return tuple(HF_PIPES)


def fetch_hub_pipe(pipe: str, search: str = ""):
    """One pipeline_tag, inference_provider=all, Link-paginated.

    Keeps models with a live inference provider. Drops LoRA adapters so the
    service picker is not a wall of dead buttons. Pins are applied by the caller.
    """
    q = (search or "").strip()
    url = (
        f"{HUB}?pipeline_tag={quote(pipe)}"
        f"&inference_provider=all&sort=downloads&limit={_HUB_PAGE}"
        f"&expand[]=inferenceProviderMapping"
    )
    if q:
        url += f"&search={quote(q)}"
    items, seen = [], set()
    pages = 0
    has_more = False
    reachable = False
    while url and pages < _HUB_MAX_PAGES:
        code, data, headers = _hub_get(url)
        pages += 1
        if code != 200 or not isinstance(data, list):
            break
        reachable = True
        for it in data:
            if not isinstance(it, dict):
                continue
            mid = (it.get("id") or "").strip()
            row_pipe = it.get("pipeline_tag") or pipe
            if not mid or mid in seen:
                continue
            if row_pipe not in HF_PIPES:
                continue
            if _is_adapter_id(mid):
                continue
            mapping = it.get("inferenceProviderMapping")
            if mapping not in (None, "", [], {}) and not _has_live_provider(mapping):
                continue
            seen.add(mid)
            items.append(_hf_row(mid, mid.split("/")[-1], row_pipe))
        nxt = _link_next(headers)
        if not nxt:
            has_more = False
            url = ""
            break
        has_more = True
        url = nxt
    meta = {
        "pagesFetched": pages,
        "pageSize": _HUB_PAGE,
        "hasMore": bool(has_more),
        "kept": len(items),
        "reachable": reachable,
        "pipe": pipe,
    }
    return items, meta


def fetch_hub_pipe_cached(pipe: str, search: str = ""):
    q = (search or "").strip()
    if q:
        return fetch_hub_pipe(pipe, q)
    now = time.time()
    with _HUB_LIST_LOCK:
        hit = (_HUB_LIST_CACHE.get("pipes") or {}).get(pipe)
        if hit and (now - (_HUB_LIST_CACHE.get("at") or 0)) < _MAP_TTL:
            return list(hit.get("items") or []), dict(hit.get("meta") or {})
    items, meta = fetch_hub_pipe(pipe)
    with _HUB_LIST_LOCK:
        pipes = dict(_HUB_LIST_CACHE.get("pipes") or {})
        pipes[pipe] = {"items": list(items), "meta": dict(meta)}
        _HUB_LIST_CACHE["pipes"] = pipes
        _HUB_LIST_CACHE["at"] = now
    return items, meta


def _cached_hub_items():
    out = []
    seen = set()
    for pack in (_HUB_LIST_CACHE.get("pipes") or {}).values():
        for x in pack.get("items") or []:
            mid = x.get("id")
            if mid and mid not in seen:
                seen.add(mid)
                out.append(x)
    return out


def spec_for(mid: str) -> dict:
    want = (mid or "").strip()
    if not want:
        return {}
    for x in load_items():
        if x.get("id") == want:
            return x
    for x in _cached_hub_items():
        if x.get("id") == want:
            return x
    return {}


def fetch_hf_roster(q: str = "", category: str = ""):
    """Hub list + pins-on-top. Pins are never the entire roster when Hub is up.

    Returns (items, meta). Hub unreachable → items=[] and meta.source=unreachable
    so catalog() can fall back to pins.
    """
    qn = (q or "").strip()
    pipes = _pipes_for_category(category)
    if not pipes:
        return [], {
            "source": "hub",
            "pageSize": _HUB_PAGE,
            "pagesFetched": 0,
            "hasMore": False,
            "pipes": {},
            "hubCount": 0,
        }
    pipe_meta = {}
    hub, seen = [], set()
    reachable = False

    def _one(pipe):
        return pipe, fetch_hub_pipe_cached(pipe, qn)

    if len(pipes) == 1:
        rows = [_one(pipes[0])]
    else:
        rows = []
        with ThreadPoolExecutor(max_workers=min(4, len(pipes))) as pool:
            futs = [pool.submit(_one, p) for p in pipes]
            for fut in futs:
                try:
                    rows.append(fut.result())
                except Exception as e:
                    rows.append((None, ([], {"reachable": False, "error": str(e)})))
    for pipe, pack in rows:
        items, meta = pack if isinstance(pack, tuple) else ([], {})
        if pipe:
            pipe_meta[pipe] = meta
        if meta.get("reachable"):
            reachable = True
        for x in items:
            mid = x.get("id")
            if mid and mid not in seen:
                seen.add(mid)
                hub.append(x)
    if qn and qn.count("/") == 1 and " " not in qn and qn not in seen:
        code, data = json_call(f"{HUB}/{quote(qn, safe='/')}", headers=_hf_headers(), timeout=20)
        if code == 200 and isinstance(data, dict):
            mid = data.get("id") or qn
            pipe = data.get("pipeline_tag") or "text-to-image"
            if pipe not in HF_PIPES:
                pipe = "text-to-image"
            hub.insert(0, _hf_row(mid, mid.split("/")[-1], pipe))
            seen.add(mid)
            reachable = True
    has_more = any((m or {}).get("hasMore") for m in pipe_meta.values())
    pages = sum(int((m or {}).get("pagesFetched") or 0) for m in pipe_meta.values())
    meta = {
        "source": "hub" if reachable else "unreachable",
        "pageSize": _HUB_PAGE,
        "pagesFetched": pages,
        "hasMore": has_more,
        "pipes": pipe_meta,
        "hubCount": len(hub),
    }
    return hub, meta


def _pin_on_top(hub: list, pins: list) -> list:
    """Pins first (category-matching ones), then Hub rows not already pinned."""
    seen = set()
    out = []
    for p in pins:
        pid = p.get("id")
        if pid and pid not in seen:
            row = dict(p)
            row["pinned"] = True
            out.append(row)
            seen.add(pid)
    for x in hub:
        mid = x.get("id")
        if mid and mid not in seen:
            out.append(x)
            seen.add(mid)
    return out


class HuggingFaceProvider(Provider):
    id = "huggingface"
    label = "Hugging Face"

    def has_key(self) -> bool:
        return bool(hf_key())

    def search_loras(self, q: str, nsfw: bool = True):
        return search_loras(q)

    def categories(self) -> list:
        cats = {x.get("category") for x in load_items() if x.get("category")}
        cats.update({"image", "video", "upscale", "utility"})
        for x in _cached_hub_items():
            if x.get("category"):
                cats.add(x.get("category"))
        return sorted(cats)

    def catalog(self, q, category, status) -> dict:
        qn = (q or "").strip()
        pins = list(load_items())
        hub, roster_meta = fetch_hf_roster(qn, category)
        if roster_meta.get("source") == "unreachable":
            items = [dict(p, pinned=True) for p in pins]
            source = "hardcoded_fallback"
        else:
            items = _pin_on_top(hub, pins)
            source = "hub"
        items = [_apply_upscale_category(dict(x)) for x in items]
        unfiltered = list(items)
        if category:
            from .catalog_ops import category_matches

            items = [x for x in items if category_matches(x.get("category"), category)]
        if status:
            items = [x for x in items if x.get("status") == status]
        if qn and source == "hardcoded_fallback":
            needle = _alnum(qn)
            items = [x for x in items if needle in _alnum(x.get("name")) or needle in _alnum(x.get("id"))]
        from .catalog_ops import enrich_catalog_item

        items = [enrich_catalog_item(x, "huggingface") for x in items]
        cat_counts = dict(Counter((x.get("category") or "unknown") for x in unfiltered))
        return {
            "total": len(items),
            "count": len(items),
            "backend": "huggingface",
            "items": items,
            "hasKey": self.has_key(),
            "hub": HUB,
            "categories": cat_counts,
            "pagination": {
                "page": 1,
                "pageSize": roster_meta.get("pageSize") or _HUB_PAGE,
                "pagesFetched": roster_meta.get("pagesFetched") or 0,
                "hasMore": bool(roster_meta.get("hasMore")),
                "source": source,
                "hubCount": roster_meta.get("hubCount") or 0,
            },
            "hubPipes": roster_meta.get("pipes") or {},
        }

    def owns_service(self, service_id: str) -> bool:
        sid = (service_id or "").strip()
        if not sid:
            return False
        if sid.startswith(("hf/", "huggingface/")):
            return True
        ids = {x.get("id") for x in load_items()}
        ids |= {x.get("id") for x in _cached_hub_items()}
        return sid in ids

    def owns_job(self, job_id: str) -> bool:
        pid, _ = parse_job_id(job_id)
        return pid in ("huggingface", "hf") or (job_id or "").startswith("hf|")

    def whatif(self, payload: dict):
        """Dry-run validate against the Hub. No inference call, no charge.

        Three things generate() can fail on are checked for real: the model must
        exist on the Hub, it must have a live inference provider, and the routed
        provider style must actually forward an input image when the model is an
        edit model — the openai/bytes styles drop it silently.
        """
        p = dict(payload or {})
        sid = (p.get("serviceId") or "").strip()
        base = {"backend": "huggingface", "service": {"serviceId": sid}}
        if not sid:
            return 400, {**base, "error": "缺少 Hugging Face 模型 id", "code": "missing_service"}
        if looks_like_civitai_service(sid):
            return 400, {
                **base,
                "error": "当前选中的是 Civitai 服务，不能发给 Hugging Face。请选 FLUX.1-schnell 等 Hub 模型。",
                "code": "wrong_backend",
            }
        if not self.has_key():
            return 401, {**base, "error": f"没有 Hugging Face API Key，放在 {TOKEN_PATH}", "code": "no_key"}
        mid = model_id(sid)
        if not mid or "/" not in mid:
            return 400, {**base, "error": f"不是 Hub 模型 id（应形如 owner/model）：{sid}", "code": "missing_service"}
        base["service"]["serviceId"] = mid

        spec = spec_for(mid) or {}
        code, info = hub_probe(mid)
        if code == 404:
            return 400, {**base, "error": f"Hugging Face Hub 上没有 {mid}", "code": "unknown_service"}
        if code in (401, 403):
            return 401, {
                **base,
                "error": f"Hugging Face 拒绝访问 {mid}（HTTP {code}），可能是私有模型或 token 权限不够",
                "code": "forbidden",
            }
        reachable = code == 200
        mapping = _normalize_mapping((info.get("inferenceProviderMapping") if reachable else None))
        task = spec.get("task") or (info.get("pipeline_tag") if reachable else "") or ""
        if reachable and not mapping:
            return 400, {
                **base,
                "error": f"{mid} 在 Hugging Face 上没有可用推理供应商，发出去必然失败",
                "code": "no_inference_provider",
                "service": {"serviceId": mid, "task": task},
            }

        candidates = _provider_candidates(mapping, mid, spec) if reachable else []
        errors, warnings = [], []
        if not reachable:
            warnings.append({
                "code": "hub_unreachable",
                "message": f"没连上 Hugging Face Hub（HTTP {code}），推理供应商和模型存在性这次没校验",
            })
        if not (p.get("prompt") or "").strip():
            errors.append({"code": "missing_prompt", "message": "prompt 是空的，Hugging Face 三条通道都要 prompt"})

        needs_img = bool(spec.get("needsSource")) or task in ("image-to-image", "image-to-video")
        media = [x for x in (p.get("images") or []) if x]
        first = (p.get("firstFrame") or p.get("sourceImage") or p.get("image_url") or "").strip()
        if first and first not in media:
            media = [first] + media
        provider, pid, style = (candidates[0] if candidates else ("", mid, ""))
        if needs_img and not media:
            errors.append({
                "code": "missing_input_media",
                "message": f"{mid} 是 {task or 'image-to-image'}，必须先接一张图",
            })
        if needs_img and media and style and style != "fal":
            errors.append({
                "code": "input_media_dropped",
                "message": f"{mid} 会走 {provider}（{style} 通道），该通道不带输入图，图会被丢掉当成文生图跑",
            })
        if media and not needs_img:
            warnings.append({
                "code": "input_media_dropped",
                "message": f"{mid} 的 pipeline 是 {task or '未知'}，不吃输入图，接上的图会被丢掉",
            })

        if style == "fal":
            body = _fal_body(_maybe_lora_pid((pid or "").lstrip("/"), p), p)
            if needs_img and media and not (body.get("image_url") or body.get("image_urls")):
                errors.append({
                    "code": "input_media_dropped",
                    "message": f"{pid} 的 id 里没有 edit/i2i 标记，router 不会带上输入图",
                })
        elif style == "bytes":
            body, _accept = _bytes_body(p, spec or {"task": task})
        elif style == "openai":
            body = _openai_body(pid, p)
        else:
            body = {"prompt": p.get("prompt") or ""}

        data = {
            "backend": "huggingface",
            "service": {
                "serviceId": mid,
                "task": task,
                "provider": provider or None,
                "providerId": pid,
                "style": style or None,
            },
            "operation": task or None,
            "submittedInput": body,
            "warnings": warnings,
            "checked": {
                "hubReachable": reachable,
                "hubStatus": code,
                "providers": [n for n, _pid, _s in candidates],
                "catalogSpec": bool(spec),
            },
            "cost": {
                "total": None,
                "usd": None,
                "note": "Hugging Face Inference Providers 按供应商计费，没有预估接口（本次没有提交）",
            },
        }
        if errors:
            data["errors"] = errors
            data["error"] = errors[0]["message"]
            data["code"] = errors[0]["code"]
            return 400, data
        data["ok"] = reachable
        if not reachable:
            data["verified"] = False
        return 200, data

    def generate(self, payload: dict):
        key = hf_key()
        if not key:
            return 401, {"error": "没有 Hugging Face API Key"}
        sid = (payload or {}).get("serviceId") or ""
        if looks_like_civitai_service(sid):
            return 400, {"error": "当前选中的是 Civitai 服务，不能发给 Hugging Face。请选 FLUX.1-schnell 等 Hub 模型。"}
        mid = model_id(sid)
        if not mid:
            return 400, {"error": "缺少 Hugging Face 模型 id"}
        spec = spec_for(mid) or {}
        mapping = inference_mapping(mid)
        candidates = _provider_candidates(mapping, mid, spec)
        last = (502, {"error": "没有可用的 Hugging Face 推理通道"})
        timeout = 300
        for provider, pid, style in candidates:
            if style == "openai" and provider in _SKIP_OPENAI:
                continue
            jid = f"hf|sync|{uuid.uuid4().hex[:12]}"
            submitted = {"model": mid, "provider": provider}
            saved = []
            meta = {
                "backend": "huggingface",
                "serviceId": mid,
                "prompt": (payload or {}).get("prompt"),
                "negativePrompt": (payload or {}).get("negativePrompt"),
                "seed": (payload or {}).get("seed"),
                "jobId": jid,
            }
            try:
                if style == "bytes":
                    code, data, raw, ctype, submitted = _call_bytes(mid, payload or {}, spec, key, timeout)
                    meta["submittedInput"] = submitted
                    if code == 503:
                        last = (503, {"error": "模型正在加载，请稍后再试"})
                        continue
                    if code >= 400:
                        err = data if isinstance(data, dict) else {"error": (raw or b"")[:400].decode("utf-8", "replace")}
                        if isinstance(err, dict):
                            err.setdefault("error", extract_error(err, f"HTTP {code}"))
                        last = (code, err)
                        continue
                    if isinstance(data, dict) and (data.get("error") or data.get("images") or data.get("data")):
                        saved = _save_json_images(data, jid, meta=meta)
                    elif raw and not (ctype or "").startswith("application/json"):
                        saved = save_bytes(raw, jid, meta=meta)
                    elif isinstance(data, dict):
                        saved = _save_json_images(data, jid, meta=meta)
                    elif raw:
                        saved = save_bytes(raw, jid, meta=meta)
                elif style == "fal":
                    code, data, submitted = _call_fal(provider, pid, payload or {}, key, timeout)
                    meta["submittedInput"] = submitted
                    if code >= 400:
                        if isinstance(data, dict):
                            data.setdefault("error", extract_error(data, f"HTTP {code}"))
                        last = (code, data)
                        continue
                    saved = _save_json_images(data, jid, meta=meta)
                else:
                    code, data, submitted = _call_openai(provider, pid, payload or {}, key, timeout)
                    meta["submittedInput"] = submitted
                    err_txt = extract_error(data, f"HTTP {code}") if isinstance(data, dict) else str(data)
                    if code >= 400 or (isinstance(err_txt, str) and "Not allowed to POST" in err_txt):
                        if isinstance(data, dict):
                            data.setdefault("error", err_txt)
                        last = (code if code >= 400 else 400, data if isinstance(data, dict) else {"error": err_txt})
                        continue
                    saved = _save_json_images(data, jid, meta=meta)
            except Exception as e:
                last = (502, {"error": "Hugging Face 请求失败", "detail": str(e), "provider": provider})
                continue
            if saved:
                out = {
                    "id": jid,
                    "status": "succeeded",
                    "backend": "huggingface",
                    "endpoint": mid,
                    "provider": provider,
                    "saved": saved,
                    "submittedInput": submitted,
                }
                # Fake-confidence: body may carry loras[] on mapped turbo; router has no /lora sibling.
                if (payload or {}).get("loras") and isinstance(submitted, dict) and submitted.get("loras"):
                    out["warning"] = (
                        "Hugging Face 已把 loras[] 附在 mapped 端点发出去；"
                        "上游是否加载未证实（路由没有 /lora sibling）"
                    )
                return 200, out
            last = (502, {"error": "Hugging Face 没有返回图片", "provider": provider})
        return last

    def job_status(self, job_id: str):
        return 200, {
            "id": job_id,
            "status": "succeeded",
            "backend": "huggingface",
            "wait": {"progress": 1, "precedingJobs": None, "etaSeconds": None, "completeAt": None, "log": None},
        }


from . import register  # noqa: E402

register(HuggingFaceProvider())
