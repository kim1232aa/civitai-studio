from __future__ import annotations

import base64
import json
import os
import time
import uuid
from pathlib import Path
from urllib.parse import quote

from .base import Provider
from .http import collect_urls, extract_error, json_call, parse_job_id, raw_call, save_bytes, save_media_urls

TOKEN_PATH = Path.home() / ".config/huggingface/token"
ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
ROUTER = "https://router.huggingface.co"
HUB = "https://huggingface.co/api/models"
LEGACY = f"{ROUTER}/hf-inference/models"

# Prefer providers that still host FLUX / Qwen / SDXL after hf-inference 410.
_PREF = ("nscale", "fal-ai", "wavespeed", "replicate", "together", "hf-inference")
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


def _provider_candidates(mapping: dict, mid: str, spec: dict) -> list:
    """Ordered (provider, providerId, style) for live Inference Providers."""
    live = []
    for name, info in (mapping or {}).items():
        if not isinstance(info, dict):
            continue
        if (info.get("status") or "").lower() not in ("live", "staging", ""):
            if (info.get("status") or "").lower() == "error":
                continue
        if (info.get("status") or "").lower() == "error":
            continue
        live.append((name, info.get("providerId") or mid, info))
    live_ok = []
    for name, pid, info in live:
        st = (info.get("status") or "").lower()
        if st == "live":
            live_ok.append((name, pid, info))
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
            ("nscale", mid, "openai"),
            ("fal-ai", mid, "fal"),
            ("hf-inference", mid, "bytes"),
        ]
    return ordered


def _style_for(provider: str) -> str:
    if provider in ("nscale", "together"):
        return "openai"
    if provider == "hf-inference":
        return "bytes"
    if provider in ("fal-ai", "wavespeed"):
        return "fal"
    if provider == "replicate":
        return "openai"
    return "openai"


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
            params["seed"] = int(payload["seed"])
        except (TypeError, ValueError):
            pass
    return params


def _save_json_images(data: dict, jid: str) -> list:
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
            saved.extend(save_bytes(raw, stem))
        elif item.get("url"):
            saved.extend(save_media_urls([item["url"]], stem))
    urls = collect_urls(data)
    if not saved and urls:
        saved = save_media_urls(urls, jid)
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


def _call_fal(provider: str, provider_id: str, payload: dict, key: str, timeout: int):
    pid = (provider_id or "").lstrip("/")
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
    img = (payload.get("firstFrame") or payload.get("sourceImage") or payload.get("image_url") or "").strip()
    extra = [x for x in (payload.get("images") or []) if x]
    if img and img not in extra:
        extra = [img] + extra
    if extra:
        if len(extra) == 1:
            body["image_url"] = extra[0]
        else:
            body["image_urls"] = extra[:9]
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


class HuggingFaceProvider(Provider):
    id = "huggingface"
    label = "Hugging Face"

    def has_key(self) -> bool:
        return bool(hf_key())

    def categories(self) -> list:
        return sorted({x.get("category") for x in load_items() if x.get("category")})

    def catalog(self, q, category, status) -> dict:
        qn = (q or "").lower()
        items = list(load_items())
        if category:
            items = [x for x in items if x.get("category") == category]
        if status:
            items = [x for x in items if x.get("status") == status]
        if qn:
            items = [x for x in items if qn in (x.get("name") or "").lower() or qn in (x.get("id") or "").lower()]
        return {
            "total": len(items),
            "count": len(items),
            "backend": "huggingface",
            "items": items,
            "hasKey": self.has_key(),
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
        mid = model_id((payload or {}).get("serviceId") or "")
        if not mid:
            return 400, {"error": "缺少 Hugging Face 模型 id"}
        spec = next((x for x in load_items() if x.get("id") == mid), {}) or {}
        mapping = inference_mapping(mid)
        candidates = _provider_candidates(mapping, mid, spec)
        last = (502, {"error": "没有可用的 Hugging Face 推理通道"})
        timeout = 180
        for provider, pid, style in candidates:
            jid = f"hf|sync|{uuid.uuid4().hex[:12]}"
            submitted = {"model": mid, "provider": provider}
            saved = []
            try:
                if style == "bytes":
                    code, data, raw, ctype, submitted = _call_bytes(mid, payload or {}, spec, key, timeout)
                    if code == 503:
                        return 503, {"error": "模型正在加载，请稍后再试"}
                    if code >= 400:
                        err = data if isinstance(data, dict) else {"error": (raw or b"")[:400].decode("utf-8", "replace")}
                        if isinstance(err, dict):
                            err.setdefault("error", extract_error(err, f"HTTP {code}"))
                        last = (code, err)
                        continue
                    if isinstance(data, dict):
                        saved = _save_json_images(data, jid)
                    elif raw:
                        saved = save_bytes(raw, jid)
                elif style == "fal":
                    code, data, submitted = _call_fal(provider, pid, payload or {}, key, timeout)
                    if code >= 400:
                        if isinstance(data, dict):
                            data.setdefault("error", extract_error(data, f"HTTP {code}"))
                        last = (code, data)
                        continue
                    saved = _save_json_images(data, jid)
                else:
                    code, data, submitted = _call_openai(provider, pid, payload or {}, key, timeout)
                    if code >= 400:
                        if isinstance(data, dict):
                            data.setdefault("error", extract_error(data, f"HTTP {code}"))
                        last = (code, data)
                        continue
                    saved = _save_json_images(data, jid)
            except Exception as e:
                last = (502, {"error": "Hugging Face 请求失败", "detail": str(e), "provider": provider})
                continue
            if saved:
                return 200, {
                    "id": jid,
                    "status": "succeeded",
                    "backend": "huggingface",
                    "endpoint": mid,
                    "provider": provider,
                    "saved": saved,
                    "submittedInput": {k: v for k, v in (submitted or {}).items() if k != "parameters" or True},
                }
            last = (502, {"error": "Hugging Face 没有返回图片", "provider": provider})
        return last

    def job_status(self, job_id: str):
        # sync jobs finish in generate(); nothing to poll
        return 200, {
            "id": job_id,
            "status": "succeeded",
            "backend": "huggingface",
            "wait": {"progress": 1, "precedingJobs": None, "etaSeconds": None, "completeAt": None, "log": None},
        }


from . import register  # noqa: E402

register(HuggingFaceProvider())
