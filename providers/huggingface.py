from __future__ import annotations

import base64
import json
import re
import os
import time
import uuid
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


def inference_mapping(mid: str) -> dict:
    now = time.time()
    cached = (_MAP_CACHE.get("items") or {}).get(mid)
    if cached is not None and (now - _MAP_CACHE.get("at") or 0) < _MAP_TTL:
        return cached
    key = hf_key()
    headers = {"Accept": "application/json"}
    if key:
        headers["Authorization"] = f"Bearer {key}"
    url = f"{HUB}/{quote(mid, safe='/')}?expand[]=inferenceProviderMapping"
    code, data = json_call(url, headers=headers, timeout=20)
    mapping = {}
    if code == 200 and isinstance(data, dict):
        mapping = data.get("inferenceProviderMapping") or {}
        if not isinstance(mapping, dict):
            mapping = {}
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


def _call_openai(provider: str, provider_id: str, payload: dict, key: str, timeout: int):
    url = f"{ROUTER}/{provider}/v1/images/generations"
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


def _call_fal(provider: str, provider_id: str, payload: dict, key: str, timeout: int):
    pid = _maybe_lora_pid((provider_id or "").lstrip("/"), payload or {})
    url = f"{ROUTER}/{provider}/{pid}"
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
    blob = (pid + " " + str((payload or {}).get("task") or "")).lower()
    wants_img = any(x in blob for x in ("image-to-image", "kontext", "/edit", "i2i"))
    from .ref_images import payload_ref_images, primary_frame, max_refs
    from .capabilities import get_provider_capabilities
    caps = get_provider_capabilities("huggingface")
    img = primary_frame(payload)
    extra = payload_ref_images(payload, backend="huggingface", caps=caps)
    ref_cap = max_refs(backend="huggingface", caps=caps, payload=payload)
    if extra and wants_img:
        if len(extra) == 1:
            body["image_url"] = extra[0]
        else:
            body["image_urls"] = extra[:ref_cap]
    elif img and wants_img:
        body["image_url"] = img
    try:
        from . import fal as fal_mod
        fal_mod.apply_fal_loras(body, payload, fal_mod.find_model(pid) or {"id": pid}, pid)
    except Exception:
        pass
    _force_loras(body, payload or {})
    headers = _auth_headers(key)
    code, data = json_call(url, method="POST", headers=headers, body=body, timeout=timeout)
    return code, data if isinstance(data, dict) else {"error": str(data)}, body


def _call_bytes(mid: str, payload: dict, spec: dict, key: str, timeout: int):
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
    accept = "video/mp4" if task == "text-to-video" else "image/png"
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
        return sorted(cats)

    def catalog(self, q, category, status) -> dict:
        qn = (q or "").strip()
        pins = list(load_items())
        if qn:
            items = search_hf(qn, pins)
        else:
            items = pins
        items = [_apply_upscale_category(dict(x)) for x in items]
        if category:
            items = [x for x in items if x.get("category") == category]
        if status:
            items = [x for x in items if x.get("status") == status]
        return {
            "total": len(items),
            "count": len(items),
            "backend": "huggingface",
            "items": items,
            "hasKey": self.has_key(),
            "hub": HUB,
        }

    def owns_service(self, service_id: str) -> bool:
        sid = (service_id or "").strip()
        if not sid:
            return False
        if sid.startswith(("hf/", "huggingface/")):
            return True
        ids = {x.get("id") for x in load_items()}
        return sid in ids

    def owns_job(self, job_id: str) -> bool:
        pid, _ = parse_job_id(job_id)
        return pid in ("huggingface", "hf") or (job_id or "").startswith("hf|")

    def whatif(self, payload: dict):
        return 200, {
            "backend": "huggingface",
            "cost": {"total": None, "note": "Hugging Face Inference Providers 按次计费，无黄 Buzz 预估"},
            "service": {"serviceId": (payload or {}).get("serviceId")},
        }

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
        spec = next((x for x in load_items() if x.get("id") == mid), {}) or {}
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
