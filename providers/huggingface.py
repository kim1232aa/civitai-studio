from __future__ import annotations

import base64
import inspect
import json
import math
import re
import os
import time
import uuid
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import parse_qs, quote, urlsplit

from .base import Provider
from .http import collect_urls, extract_error, json_call, parse_job_id, raw_call, save_bytes, save_media_urls
from .io_meta import looks_like_civitai_service, remember_job, job_meta

TOKEN_PATH = Path.home() / ".config/huggingface/token"
ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
ROUTER = "https://router.huggingface.co"
HUB = "https://huggingface.co/api/models"
LEGACY = f"{ROUTER}/hf-inference/models"

# Prefer Fal for FLUX schnell (hf-inference is 410). nscale is also live.
# replicate rejects POST /v1/images/generations ("Not allowed to POST … provider replicate").
_PREF = ("fal-ai", "nscale", "together", "hf-inference")
_SKIP_OPENAI = {"replicate"}
_MAP_CACHE = {"at": 0.0, "items": {}}
_MAP_TTL = 300
# Official HF text-to-image `seed` is integer with no documented max.
# Fal-as-HF-provider already accepted seeds > int32 (live 1055482629632456).
# Never modulo or clip; reject only non-integers / seed < -1.
_HF_SEED_MIN = -1


def _mapping_as_dict(raw):
    """Hub model info returns a provider-keyed dict; list endpoints return a list."""
    if isinstance(raw, dict):
        return {key: info for key, info in raw.items() if isinstance(info, dict)}
    if not isinstance(raw, list):
        return {}
    out = {}
    for info in raw:
        if not isinstance(info, dict):
            continue
        name = info.get("provider") or info.get("providerName")
        if name:
            out[str(name)] = info
    return out


def hf_key() -> str:
    try:
        t = TOKEN_PATH.read_text().strip()
        if t:
            return t
    except Exception:
        pass
    return (os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_TOKEN") or "").strip()


_KREA_PIN = {
    "id": "krea/Krea-2-Turbo",
    "name": "Krea 2 Turbo",
    "category": "image",
    "backend": "huggingface",
    "status": "available",
    "task": "text-to-image",
    "tags": ["t2i"],
}

_I2I_PIN = {
    "id": "Qwen/Qwen-Image-Edit",
    "name": "Qwen Image Edit",
    "category": "image",
    "backend": "huggingface",
    "status": "available",
    "task": "image-to-image",
    "tags": ["i2i"],
    "needsSource": True,
    "pipelineTag": "image-to-image",
}


def load_items():
    fp = DOCS / "hf-models.json"
    items = []
    if fp.exists():
        try:
            raw = json.loads(fp.read_text()).get("items") or []
            if isinstance(raw, list):
                items = [x for x in raw if isinstance(x, dict)]
        except Exception:
            items = []
    extra = []
    ids = {x.get("id") for x in items}
    if "krea/Krea-2-Turbo" not in ids:
        extra.append(dict(_KREA_PIN))
    if "Qwen/Qwen-Image-Edit" not in ids:
        extra.append(dict(_I2I_PIN))
    return extra + items


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
        mapping = _mapping_as_dict(data.get("inferenceProviderMapping"))
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


def _is_zimage_turbo(mid: str, mapping=None) -> bool:
    blob = (mid or "").lower()
    if "z-image-turbo" in blob or "z_image_turbo" in blob:
        return True
    compact = "".join(ch for ch in blob if ch.isalnum())
    if "zimageturbo" in compact:
        return True
    for info in (mapping or {}).values():
        if not isinstance(info, dict):
            continue
        pid = str(info.get("providerId") or "").lower()
        if "z-image/turbo" in pid or "z-image-turbo" in pid:
            return True
    return False


def _is_krea_turbo(mid: str, mapping=None) -> bool:
    blob = (mid or "").lower()
    compact = "".join(ch for ch in blob if ch.isalnum())
    if "krea2turbo" in compact or "kreav2turbo" in compact:
        return True
    if any(tok in blob for tok in ("krea-2-turbo", "krea-2/turbo", "krea-v2/turbo", "krea2/turbo")):
        return True
    for info in (mapping or {}).values():
        if not isinstance(info, dict):
            continue
        pid = str(info.get("providerId") or "").lower()
        if any(tok in pid for tok in ("krea-2/turbo", "krea-v2/turbo", "krea2/turbo", "krea-2-turbo")):
            return True
    return False


def _skip_wavespeed(mid: str, mapping=None) -> bool:
    # wavespeed does not support Krea / Z-Image turbo; must not cover a fal-ai error.
    return _is_zimage_turbo(mid, mapping) or _is_krea_turbo(mid, mapping)


def _has_loras(payload) -> bool:
    loras = (payload or {}).get("loras")
    return isinstance(loras, list) and len(loras) > 0


def _provider_candidates(mapping: dict, mid: str, spec: dict, payload=None) -> list:
    live = []
    task = _task(payload or {}, spec)
    for name, info in (mapping or {}).items():
        if not isinstance(info, dict):
            continue
        st = (info.get("status") or "").lower()
        if st != "live" or (info.get("task") and info["task"] != task):
            continue
        if info.get("providerId"):
            live.append((name, info["providerId"], info))
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
    out = [(n, p, s) for n, p, s in ordered if not (s == "openai" and n in _SKIP_OPENAI)]
    # v0821o5: Krea / Z-Image turbo — pin fal-ai; wavespeed does not support
    # these models (and must not cover a fal-ai LoRA error).
    if _skip_wavespeed(mid, mapping):
        out = [(n, p, s) for n, p, s in out if n != "wavespeed"]
        fal = [x for x in out if x[0] == "fal-ai"]
        rest = [x for x in out if x[0] != "fal-ai"]
        if fal:
            out = fal + rest
    return out


def _fal_ai_error_is_final(provider: str, mid: str, mapping=None) -> bool:
    return provider == "fal-ai" and _skip_wavespeed(mid, mapping)


def _auth_headers(key: str, extra=None):
    h = {"Authorization": f"Bearer {key}"}
    if extra:
        h.update(extra)
    return h


def _number(raw, field, *, integer=False, minimum=None, maximum=None):
    """Validate before encoding; never truncate, wrap or silently drop input."""
    try:
        if isinstance(raw, bool):
            raise ValueError()
        if integer:
            value = int(raw)
            if not isinstance(raw, str) and value != raw:
                raise ValueError()
        else:
            value = float(raw)
        if not math.isfinite(value) or (minimum is not None and value < minimum) or (
                maximum is not None and value > maximum):
            raise ValueError()
    except (TypeError, ValueError, OverflowError):
        if minimum is not None and maximum is not None:
            bounds = f"（{minimum} ≤ 原值 ≤ {maximum}）"
        elif minimum is not None:
            bounds = f"，且 ≥ {minimum}"
        elif maximum is not None:
            bounds = f"，且 ≤ {maximum}"
        else:
            bounds = ""
        extra = "，拒绝静默改值" if maximum is not None else ""
        raise ValueError(
            f"{field} 必须是{'整数' if integer else '有限数值'}{bounds}{extra}"
        ) from None
    return value


def _value(payload, *names):
    values = [(key, payload[key]) for key in names if payload.get(key) not in (None, "")]
    if values and any(value != values[0][1] for _, value in values[1:]):
        raise ValueError(f"{'/'.join(names)} 的值冲突，拒绝覆盖")
    return values[0][1] if values else None


def _task(payload, spec):
    if payload.get("task") or spec.get("task"):
        return payload.get("task") or spec["task"]
    has_image = any(payload.get(k) for k in ("sourceImage", "firstFrame", "images", "image_url", "image_urls"))
    if payload.get("kind") == "video" or payload.get("recipe") == "video":
        return "image-to-video" if has_image else "text-to-video"
    return "image-to-image" if has_image else "text-to-image"


def _references(payload):
    from .fal import materialize_fal_media
    values = []
    for field in ("firstFrame", "sourceImage", "startImage", "image_url", "imageUrl", "imageDataUrl",
                  "image", "images", "referenceImages", "input_references", "image_urls"):
        value = payload.get(field)
        if value not in (None, ""):
            values.extend(value if isinstance(value, list) else [value])
    refs = materialize_fal_media({"image_urls": values})["image_urls"]
    if any(not isinstance(value, str) or not value.startswith(("https://", "http://", "data:")) for value in refs):
        raise ValueError("参考图必须是有效 URL、data URL 或可读取的 /out 文件，拒绝跳过")
    return list(dict.fromkeys(refs))


def _prompt_body(payload: dict) -> dict:
    if payload.get("prompt") is not None and not isinstance(payload["prompt"], str):
        raise ValueError("prompt 必须是文本")
    params = {}
    for names, integer, minimum in (
        (("num_inference_steps", "steps"), True, 1),
        (("guidance_scale", "cfgScale", "cfg"), False, None),
        (("width",), True, 1), (("height",), True, 1),
        (("seed",), True, -1),
    ):
        value = _value(payload, *names)
        if value is not None and not (names[0] == "seed" and value == "random"):
            if names[0] == "seed":
                params["seed"] = _number(
                    value, "seed", integer=True, minimum=_HF_SEED_MIN,
                )
            else:
                params[names[0]] = _number(value, names[0], integer=integer, minimum=minimum)
    for names in (("negative_prompt", "negativePrompt"), ("scheduler",)):
        value = _value(payload, *names)
        if value is not None:
            if not isinstance(value, str):
                raise ValueError(f"{names[0]} 必须是文本")
            params[names[0]] = value
    resolution = _value(payload, "resolution", "size")
    match = re.fullmatch(r"(\d+)\s*[x×*]\s*(\d+)", resolution.strip()) if isinstance(resolution, str) else None
    if match:
        for field, value in zip(("width", "height"), match.groups()):
            value = _number(value, field, integer=True, minimum=1)
            if field in params and params[field] != value:
                raise ValueError(f"resolution/size 与 {field} 冲突")
            params[field] = value
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
    # Queue/status URLs are not generated media.
    urls = []
    for field in ("images", "image", "video", "audio", "output", "outputs"):
        urls.extend(collect_urls(data.get(field) or {}))
    if not saved and urls:
        saved = save_media_urls(urls, jid, meta=meta)
    return saved


def _call_openai(provider: str, provider_id: str, payload: dict, key: str, timeout: int):
    # HF's official nscale and together helpers do NOT share an image payload.
    # huggingface_hub/inference/_providers/{nscale,together}.py
    if provider not in ("nscale", "together"):
        raise ValueError(f"HF {provider} 图片参数尚未接入；不会猜测 OpenAI 通道")
    params = _prompt_body(payload)
    unsupported = {"scheduler"} | ({"num_inference_steps", "guidance_scale"} if provider == "nscale" else set())
    supplied = sorted(unsupported.intersection(params))
    for field in ("loras", "sampler", "duration", "aspectRatio", "aspect_ratio", "denoise", "strength"):
        if payload.get(field) not in (None, "", []):
            supplied.append(field)
    resolution = _value(payload, "resolution", "size")
    if resolution is not None and not (isinstance(resolution, str) and re.fullmatch(r"\d+\s*[x×*]\s*\d+", resolution.strip())):
        supplied.append("resolution/size")
    if _references(payload):
        supplied.append("参考图")
    if supplied:
        raise ValueError(f"HF {provider} 当前适配器未接入这些参数：{', '.join(supplied)}；拒绝丢参生成")
    if ("width" in params) != ("height" in params):
        raise ValueError("width/height 必须一起填写")
    if provider == "together":
        if "num_inference_steps" in params:
            params["steps"] = params.pop("num_inference_steps")
    elif "width" in params:
        params["size"] = f"{params.pop('width')}x{params.pop('height')}"
    url = f"{ROUTER}/{provider}/v1/images/generations"
    quantity = _value(payload, "quantity", "qty", "n", "num_images")
    body = {
        "model": provider_id,
        "prompt": payload.get("prompt") or "",
        "response_format": "base64" if provider == "together" else "b64_json",
        **params,
        "n": _number(1 if quantity is None else quantity, "quantity", integer=True, minimum=1),
    }
    headers = _auth_headers(key)
    code, data = json_call(url, method="POST", headers=headers, body=body, timeout=timeout)
    return code, data if isinstance(data, dict) else {"error": str(data)}, body


def _maybe_lora_pid(pid: str, payload: dict) -> str:
    """Keep the mapped HF providerId. Router does not host Fal `/lora` siblings."""
    return (pid or "").lstrip("/")


def _force_loras(body: dict, payload: dict) -> None:
    raw = payload.get("loras")
    if raw in (None, []):
        return
    if not isinstance(raw, list):
        raise ValueError("HF LoRA 必须是数组")
    from .fal import _fal_lora_path
    cleaned = []
    for it in raw:
        if isinstance(it, str):
            it = {"path": it}
        if not isinstance(it, dict):
            raise ValueError("HF LoRA 条目必须包含下载路径和权重")
        path = _fal_lora_path(it)
        if not path or not (re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", path)
                            or re.match(r"^https?://[^/\s]+/\S+$", path)):
            raise ValueError("HF LoRA 缺少有效下载地址或 Hub owner/repo；拒绝跳过")
        scale = _value(it, "scale", "strength", "weight")
        row = {"path": path}
        # Official Fal LoraWeight.scale is optional (vendor default 1). Omit when
        # the imported sample has strength=null — do not invent 1.0 here.
        if scale is not None:
            row["scale"] = _number(scale, "LoRA scale")
        cleaned.append(row)
    body["loras"] = cleaned


def _call_fal(provider: str, provider_id: str, payload: dict, key: str, timeout: int, *, mapping_task=None):
    from . import fal as fal_mod
    from .ref_images import max_refs
    from .capabilities import get_provider_capabilities
    pid = _maybe_lora_pid((provider_id or "").lstrip("/"), payload or {})
    spec = fal_mod.find_model(pid) or {}
    fields = set(spec.get("required") or []) | set(spec.get("optional") or [])
    url = f"{ROUTER}/{provider}/{pid}"
    if provider == "fal-ai" and (mapping_task or _task(payload, spec)) in ("image-to-image", "text-to-video", "image-to-video"):
        # HF official FalAIQueueTask routes async tasks via the queue subdomain.
        url += "?_subdomain=queue"
    body = {"prompt": payload.get("prompt") or ""}
    if payload.get("model_name"):
        body["model_name"] = payload["model_name"]
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
    if ("width" in params) != ("height" in params):
        raise ValueError("width/height 必须一起填写")
    for names, integer in ((("num_images", "quantity", "qty", "n"), True),
                           (("duration",), False), (("strength", "denoise"), False)):
        value = _value(payload, *names)
        if value is not None:
            body[names[0]] = _number(value, names[0], integer=integer, minimum=1 if integer else None)
    for names in (("aspect_ratio", "aspectRatio"), ("resolution",), ("sampler",)):
        value = _value(payload, *names)
        if value is not None:
            if names[0] == "resolution" and isinstance(value, str) and re.fullmatch(r"\d+\s*[x×*]\s*\d+", value.strip()):
                continue  # Exact numeric resolution is already encoded as image_size.
            body[names[0]] = value
    # A client/inferred task does not add reference support to the mapped endpoint.
    blob = pid.lower()
    wants_img = mapping_task in ("image-to-image", "image-to-video") or any(
        x in blob for x in ("image-to-image", "image-to-video", "kontext", "/edit", "i2i", "i2v"))
    caps = get_provider_capabilities("huggingface")
    refs = _references(payload)
    ref_cap = max_refs(backend="huggingface", caps=caps, item=spec, payload=payload)
    if refs:
        if not wants_img and not fields.intersection({"image_url", "image_urls"}):
            raise ValueError(f"HF {pid} 当前未接参考图，拒绝丢图生成")
        if len(refs) > ref_cap or (fields and "image_urls" not in fields and len(refs) > 1):
            raise ValueError(f"HF {pid} 当前参考图接线不能接收 {len(refs)} 张，拒绝截断")
        if "image_urls" in fields or (not fields and len(refs) > 1):
            body["image_urls"] = refs
        else:
            body["image_url"] = refs[0]
        if mapping_task == "image-to-image" and not fields:
            body["image_url"] = refs[0]
            body["image_urls"] = refs
    if (payload or {}).get("loras") not in (None, [], {}):
        # Same official LoRA rules as Fal: omit null scale, refuse non-LoRA endpoints
        # (including mapped fal-ai/krea-2/turbo). Never invent /lora sibling.
        fal_mod.apply_fal_loras(body, payload or {}, spec, pid)
    # Pass endpoint-specific input fields through; never silently discard a supplied field.
    for field in fields.intersection(payload):
        if payload[field] not in (None, "") and field not in ("loras", "prompt"):
            if field in body and body[field] != payload[field]:
                raise ValueError(f"{field} 与统一参数冲突，拒绝覆盖")
            body[field] = payload[field]
    if fields:
        missing = set(body) - fields
        if missing:
            raise ValueError(f"HF {pid} 的端点字段表未声明：{', '.join(sorted(missing))}；拒绝丢参生成")
    body = fal_mod.materialize_fal_media(body)
    headers = _auth_headers(key)
    code, data = json_call(url, method="POST", headers=headers, body=body, timeout=timeout)
    return code, data if isinstance(data, dict) else {"error": str(data)}, body


def _call_bytes(mid: str, payload: dict, spec: dict, key: str, timeout: int):
    task = spec.get("task") or "text-to-image"
    if task != "text-to-image":
        raise ValueError(f"HF bytes 的 {task} 参数尚未接入；不能用秒数猜测帧数")
    for field in ("loras", "duration", "sampler", "aspectRatio", "aspect_ratio", "denoise", "strength"):
        if payload.get(field) not in (None, "", []):
            raise ValueError(f"HF bytes 当前适配器未接入 {field}；拒绝丢参生成")
    quantity = _value(payload, "quantity", "qty", "n", "num_images")
    if quantity is not None and _number(quantity, "quantity", integer=True, minimum=1) != 1:
        raise ValueError("HF bytes 当前适配器未接入 quantity 多图")
    if _references(payload):
        raise ValueError("HF bytes text-to-image 不能接参考图")
    params = _prompt_body(payload)
    resolution = _value(payload, "resolution", "size")
    if resolution is not None and not (isinstance(resolution, str) and re.fullmatch(r"\d+\s*[x×*]\s*\d+", resolution.strip())):
        raise ValueError("HF bytes 当前只接明确宽高，不能忽略 resolution/size")
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


def _queue_url(value):
    """Re-route only official Fal queue paths; never send the HF key elsewhere.

    HF official FalAiQueueTask builds status/result as
    `https://router.huggingface.co/fal-ai` + response_url.pathname.
    queue.fal.run pathnames already start with `/fal-ai/`, so the router
    URL is `/fal-ai/fal-ai/...`. Do not collapse that prefix.
    """
    parsed = urlsplit(value) if isinstance(value, str) else None
    if not parsed or parsed.scheme != "https" or parsed.netloc not in ("queue.fal.run", "fal.run", "router.huggingface.co"):
        raise ValueError("HF 队列响应包含无效地址")
    path = parsed.path
    if parsed.netloc == "router.huggingface.co":
        if not path.startswith("/fal-ai/"):
            raise ValueError("HF 队列地址不是 Fal 路由")
        if path.startswith("/fal-ai/fal-ai/"):
            path = path[len("/fal-ai"):]
    if not path.startswith("/fal-ai/") or "/requests/" not in path or ".." in path.split("/"):
        raise ValueError("HF 队列响应缺少合法请求路径")
    return f"{ROUTER}/fal-ai{path}?_subdomain=queue"


HF_PIPES = {
    "text-to-image": ("image", "text-to-image", ["t2i"], False, False),
    "image-to-image": ("image", "image-to-image", ["i2i"], True, False),
    "text-to-video": ("video", "text-to-video", ["t2v"], False, False),
    "image-to-video": ("video", "image-to-video", ["i2v"], False, True),
}
_HF_PAGE_SIZE = 50
_HF_LIST_TIMEOUT = 8
_HF_CATALOG_TTL = 300
_HF_CATALOG_CACHE = {"at": 0.0, "key": None, "items": None, "stats": {}}
_HF_NEXT_BY_KEY = {}


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


def _parameter_capabilities(mid, task, *, channel=None, route=None):
    task_fields = {
        "text-to-image": ("prompt",),
        "image-to-image": ("prompt", "reference image"),
        "text-to-video": ("prompt",),
        "image-to-video": ("prompt", "reference image"),
    }
    unknown = (
        "negative_prompt", "seed", "steps", "guidance_scale",
        "width", "height", "quantity", "loras", "scheduler",
    )
    return {
        "model": mid,
        "task": task,
        "channel": channel,
        "route": route,
        "callability": "unknown",
        "source": "Hugging Face Hub metadata; a live inference mapping is required",
        "supported": list(task_fields.get(task, ("prompt",))),
        "unknown": list(unknown),
    }


def _hf_row(mid, name, pipe, *, raw=None, mapping=None):
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
        "callability": "unknown",
        "parameterCapabilities": {
            "model": mid,
            "task": task,
            "channels": {"unknown": _parameter_capabilities(mid, task)},
            "source": "Hub pipeline_tag identifies the task, not provider availability or model schema",
        },
    }
    if isinstance(raw, dict) and raw.get("downloads") is not None:
        row["downloads"] = raw["downloads"]
    channels = _mapping_as_dict(mapping if mapping is not None else (raw or {}).get("inferenceProviderMapping"))
    if channels:
        row["parameterCapabilities"]["channels"] = {}
        for channel, info in channels.items():
            row["parameterCapabilities"]["channels"][channel] = _parameter_capabilities(
                mid, task, channel=channel, route=info.get("providerId")
            ) | {"status": info.get("status") or "unknown"}
        if not row["parameterCapabilities"]["channels"]:
            row["parameterCapabilities"]["channels"] = {"unknown": _parameter_capabilities(mid, task)}
    if needs_src:
        row["needsSource"] = True
    if needs_ff:
        row["needsFirstFrame"] = True
    if cat == "image":
        eats = bool(needs_src)
        row["capabilities"] = {
            "image_to_image": eats,
            "maxRefs": 1,
            "maxImages": 1,
            "refImagesField": "image_url",
            "imageFields": ["image_url"] if eats else [],
        }
        if eats:
            row["supported_parameters"] = {"max_input_images": 1}
    return _apply_upscale_category(row)


def _next_link(value):
    if not isinstance(value, str):
        return None
    for part in value.split(","):
        if 'rel="next"' not in part:
            continue
        match = re.search(r"<([^>]+)>", part)
        return match.group(1) if match else None
    return None


def _hf_list_page(url):
    """GET one Hub page and return its RFC 5988 next URL.

    The shared json_call intentionally discards response headers; Hub cursor
    pagination lives in Link, so catalog reads use this small GET-only helper.
    """
    req = urllib.request.Request(url, headers=_hf_headers(), method="GET")
    try:
        with urllib.request.urlopen(req, timeout=_HF_LIST_TIMEOUT) as response:
            raw = response.read()
            try:
                data = json.loads(raw.decode("utf-8"))
            except json.JSONDecodeError:
                data = {"error": raw[:500].decode("utf-8", "replace")}
            return response.status, data, _next_link(response.headers.get("Link"))
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", "replace")
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            data = {"error": raw[:500]}
        return exc.code, data, None
    except Exception as exc:
        return 502, {"error": "网络错误", "detail": str(exc)}, None


def _trusted_hub_list_url(url):
    parsed = urlsplit(url) if isinstance(url, str) else None
    if not parsed or parsed.scheme != "https" or parsed.netloc != "huggingface.co" or parsed.path != "/api/models":
        return None
    return url


def _cursor_from_url(url):
    trusted = _trusted_hub_list_url(url)
    if not trusted:
        return None
    values = parse_qs(urlsplit(trusted).query).get("cursor") or []
    return values[0] if values else None


def _normalize_page(page, page_size):
    if page is None:
        page = 1
    if page_size is None:
        page_size = _HF_PAGE_SIZE
    if isinstance(page, bool) or isinstance(page_size, bool):
        raise ValueError("page/pageSize 必须是整数，拒绝静默改值")
    try:
        page_i = int(page)
        size_i = int(page_size)
    except (TypeError, ValueError):
        raise ValueError("page/pageSize 必须是整数，拒绝静默改值") from None
    if page_i != page or size_i != page_size:
        raise ValueError("page/pageSize 必须是整数，拒绝静默改值")
    if page_i < 1 or size_i < 1 or size_i > _HF_PAGE_SIZE:
        raise ValueError(f"page 必须 ≥ 1，pageSize 必须在 1～{_HF_PAGE_SIZE}，拒绝静默改值")
    return page_i, size_i


def _pipeline_for_category(category):
    cat = (category or "").strip().lower()
    if cat == "video":
        return "text-to-video"
    if cat in HF_PIPES:
        return cat
    return "text-to-image"


def _pipelines_for_category(category, q=""):
    """Official Hub filters for one Studio catalog request.

    Search keeps a single untagged Hub page. Image browse is t2i + i2i,
    one page each (limit≤50), not a Hub crawl.
    """
    if (q or "").strip():
        return [None]
    cat = (category or "").strip().lower()
    if cat == "video":
        return ["text-to-video"]
    if cat in HF_PIPES:
        return [cat]
    return ["text-to-image", "image-to-image"]


def _hub_browse_url(q="", category="", page_size=_HF_PAGE_SIZE, pipeline=None):
    """One official Hub list page. Filters: inference_provider=all, optional pipeline_tag/search.

    Docs: https://huggingface.co/docs/inference-providers/hub-api
    Live: GET /api/models?inference_provider=all&pipeline_tag=text-to-image&limit=50
    """
    parts = [
        "inference_provider=all",
        f"limit={int(page_size)}",
        "expand[]=inferenceProviderMapping",
        "expand[]=pipeline_tag",
    ]
    qn = (q or "").strip()
    if qn:
        parts.insert(0, f"search={quote(qn)}")
    else:
        pipe = pipeline or _pipeline_for_category(category)
        parts.insert(0, f"pipeline_tag={quote(pipe)}")
    return f"{HUB}?{'&'.join(parts)}"


def _catalog_key(q, category, page, page_size):
    return ((q or "").strip(), (category or "").strip().lower(), int(page), int(page_size))


def _store_next(key, urls):
    if isinstance(urls, str):
        urls = [urls]
    trusted = []
    for url in urls or []:
        item = _trusted_hub_list_url(url)
        if item:
            trusted.append(item)
    if trusted:
        _HF_NEXT_BY_KEY[key] = {"at": time.time(), "urls": trusted, "url": trusted[0]}


def _load_next(q, category, page, page_size):
    hit = _HF_NEXT_BY_KEY.get(_catalog_key(q, category, page, page_size))
    if not hit or (time.time() - (hit.get("at") or 0)) >= _HF_CATALOG_TTL:
        return []
    raw = hit.get("urls")
    if not raw and hit.get("url"):
        raw = [hit["url"]]
    out = []
    for url in raw or []:
        item = _trusted_hub_list_url(url)
        if item:
            out.append(item)
    return out


def _pipe_from_item(it):
    if not isinstance(it, dict):
        return ""
    pipe = it.get("pipeline_tag") or it.get("pipelineTag") or ""
    if pipe in HF_PIPES:
        return pipe
    for info in _mapping_as_dict(it.get("inferenceProviderMapping")).values():
        task = (info or {}).get("task") or ""
        if task in HF_PIPES:
            return task
    return pipe


def _ingest_hub_row(items, seen, it):
    if not isinstance(it, dict):
        return False
    mid = (it.get("id") or "").strip()
    pipe = _pipe_from_item(it)
    if not mid or mid in seen or pipe not in HF_PIPES:
        return False
    seen.add(mid)
    items.append(_hf_row(
        mid, mid.split("/")[-1], pipe, raw=it,
        mapping=it.get("inferenceProviderMapping"),
    ))
    return True


def _pin_row(pin):
    pid = (pin.get("id") or "").strip()
    pipe = pin.get("pipelineTag") or pin.get("task") or "text-to-image"
    if pipe not in HF_PIPES:
        pipe = "text-to-image"
    return _hf_row(pid, pin.get("name") or pid, pipe, raw=pin)


def _fetch_hf_catalog(q="", pins=None, *, page=1, page_size=_HF_PAGE_SIZE, category="", cursor=None):
    """Pins plus one Hub page per official pipeline. Never follows Link rel=next on this call.

    Image browse hits text-to-image and image-to-image (limit≤50 each). Search is
    still a single untagged Hub page.
    """
    q = (q or "").strip()
    page, page_size = _normalize_page(page, page_size)
    items, seen = [], set()
    pins = pins or []
    needle = _alnum(q)
    for p in pins:
        pid = p.get("id")
        if pid and (needle in _alnum(p.get("name")) or needle in _alnum(pid)):
            items.append(_pin_row(p))
            seen.add(pid)
    stats = {
        "pages": 0,
        "hubFetched": 0,
        "pinned": len(items),
        "complete": False,
        "hasMore": False,
        "nextPage": None,
        "page": page,
        "pageSize": page_size,
        "errors": [],
        "filter": "inference_provider=all",
        "pagination": "Hub RFC 5988 Link rel=next cursor; Studio exposes integer nextPage",
        "pipelines": [p for p in _pipelines_for_category(category, q) if p],
        "hubUrls": [],
    }
    if q.count("/") == 1 and " " not in q and q not in seen:
        code, data = json_call(
            f"{HUB}/{quote(q, safe='/')}?expand[]=inferenceProviderMapping&expand[]=pipeline_tag",
            headers=_hf_headers(), timeout=_HF_LIST_TIMEOUT,
        )
        if code == 200 and isinstance(data, dict):
            _ingest_hub_row(items, seen, data)
        elif code != 200:
            stats["errors"].append({"url": f"{HUB}/{q}", "status": code})
    urls = []
    if cursor:
        url = _trusted_hub_list_url(cursor)
        if not url:
            stats["errors"].append({"url": cursor, "error": "分页地址不是 Hub /api/models"})
        else:
            urls = [url]
    elif page > 1:
        urls = _load_next(q, category, page - 1, page_size)
        if not urls:
            stats["errors"].append({
                "page": page,
                "error": "没有上一页的 Hub cursor，拒绝盲走下一页",
            })
            stats["retryPage"] = page
            stats["unique"] = len(items)
            stats["coverage"] = "partial"
            return items, stats
    else:
        pipes = _pipelines_for_category(category, q)
        each = page_size if pipes == [None] or len(pipes) <= 1 else max(1, page_size // len(pipes))
        stats["pageSizeEach"] = each
        for pipe in pipes:
            urls.append(_hub_browse_url(q=q, category=category, page_size=each, pipeline=pipe))
    next_urls = []
    for url in urls:
        code, data, next_url = _hf_list_page(url)
        stats["pages"] += 1
        stats["hubUrl"] = url
        stats["hubUrls"].append(url)
        if code != 200 or not isinstance(data, list):
            stats["errors"].append({"url": url, "status": code})
            continue
        added = 0
        for it in data:
            if _ingest_hub_row(items, seen, it):
                added += 1
        stats["hubFetched"] = stats.get("hubFetched", 0) + added
        next_url = _trusted_hub_list_url(next_url)
        if next_url:
            next_urls.append(next_url)
    if next_urls:
        stats["hasMore"] = True
        stats["nextPage"] = page + 1
        stats["nextCursor"] = _cursor_from_url(next_urls[0])
        _store_next(_catalog_key(q, category, page, page_size), next_urls)
    else:
        stats["complete"] = not stats["errors"]
    stats["unique"] = len(items)
    stats["coverage"] = "Hub list complete for this filter" if stats["complete"] else "partial"
    return items, stats


def search_hf(q, pins=None):
    return _fetch_hf_catalog(q, pins)[0]


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

    def catalog(self, q, category, status, page=1, pageSize=None, page_size=None, cursor=None) -> dict:
        qn = (q or "").strip()
        size = _HF_PAGE_SIZE if pageSize is None and page_size is None else (
            pageSize if pageSize is not None else page_size
        )
        page, size = _normalize_page(page, size)
        pins = list(load_items())
        cache_key = _catalog_key(qn, category, page, size)
        now = time.time()
        cached = (
            not qn and page == 1 and cursor is None
            and _HF_CATALOG_CACHE["items"] is not None
            and _HF_CATALOG_CACHE.get("key") == cache_key
            and now - (_HF_CATALOG_CACHE.get("at") or 0) < _HF_CATALOG_TTL
        )
        if cached:
            items = list(_HF_CATALOG_CACHE["items"])
            stats = dict(_HF_CATALOG_CACHE["stats"])
        else:
            items, stats = _fetch_hf_catalog(
                qn, pins, page=page, page_size=size, category=category, cursor=cursor,
            )
            if not qn and page == 1 and cursor is None and not stats.get("errors"):
                _HF_CATALOG_CACHE.update(
                    items=list(items), stats=dict(stats), at=now, key=cache_key,
                )
        items = [_apply_upscale_category(dict(x)) for x in items]
        if category:
            items = [x for x in items if x.get("category") == category]
        if status:
            items = [x for x in items if x.get("status") == status]
        complete = bool(stats.get("complete")) and not stats.get("errors")
        has_more = bool(stats.get("hasMore"))
        return {
            "total": len(items),
            "count": len(items),
            "backend": "huggingface",
            "items": items,
            "hasKey": self.has_key(),
            "hub": HUB,
            "hubCoverage": stats,
            "page": stats.get("page") or page,
            "pageSize": stats.get("pageSize") or size,
            "hasMore": has_more,
            "nextPage": stats.get("nextPage") if has_more else None,
            "complete": complete,
            "partial": not complete,
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
        if not isinstance(payload, dict) or not isinstance(payload.get("serviceId", ""), str):
            return 400, {"error": "请求必须是对象，serviceId 必须是文本", "backend": self.id}
        key = hf_key()
        if not key:
            return 401, {"error": "没有 Hugging Face API Key"}
        sid = (payload or {}).get("serviceId") or ""
        if looks_like_civitai_service(sid):
            return 400, {"error": "当前选中的是 Civitai 服务，不能发给 Hugging Face。请选 FLUX.1-schnell 等 Hub 模型。"}
        if (sid or "").startswith(("fal-ai/", "fal.ai/")):
            return 400, {"error": "当前选中的是 Fal 服务，不能发给 Hugging Face。请选 krea/Krea-2-Turbo。"}
        mid = model_id(sid)
        if not mid:
            return 400, {"error": "缺少 Hugging Face 模型 id"}
        spec = next((x for x in load_items() if x.get("id") == mid), {}) or {}
        mapping = inference_mapping(mid)
        candidates = _provider_candidates(mapping, mid, spec, payload)
        last = (502, {"error": "没有可用的 Hugging Face 推理通道"})
        timeout = 300
        # One click authorizes one route, not a sequence of billable fallback POSTs.
        for provider, pid, style in candidates[:1]:
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
                routed_payload = dict(payload, task=_task(payload, spec))
                adapter_path = (mapping.get(provider) or {}).get("adapterWeightsPath")
                if adapter_path is not None:
                    if provider != "fal-ai" or not isinstance(adapter_path, str) or not adapter_path or adapter_path.startswith("/") or ".." in adapter_path.split("/"):
                        raise ValueError("HF 映射的 adapterWeightsPath 无法接入，拒绝只生成底模")
                    loras = payload.get("loras") or []
                    if not isinstance(loras, list):
                        raise ValueError("HF LoRA 必须是数组")
                    routed_payload["loras"] = [{
                        "path": f"https://huggingface.co/{quote(mid, safe='/')}/resolve/main/{quote(adapter_path, safe='/')}",
                        "scale": 1.0,
                    }, *loras]
                    if pid == "fal-ai/lora":
                        # The HF official Fal helper specifies this base for SDXL adapters.
                        routed_payload["model_name"] = "stabilityai/stable-diffusion-xl-base-1.0"
                if style == "bytes":
                    code, data, raw, ctype, submitted = _call_bytes(mid, payload or {}, spec, key, timeout)
                    meta["submittedInput"] = submitted
                    if code == 503:
                        last = (503, {"error": "模型正在加载，请稍后再试"})
                        continue
                    if code >= 400 or (isinstance(data, dict) and data.get("error")):
                        err = data if isinstance(data, dict) else {"error": (raw or b"")[:400].decode("utf-8", "replace")}
                        if isinstance(err, dict):
                            err.setdefault("error", extract_error(err, f"HTTP {code}"))
                        last = (code if code >= 400 else 502, err)
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
                    # o5 fake_call is 5-arg; do not TypeError mapping_task into a fake fal-ai error.
                    extra = {}
                    mapping_task = (mapping.get(provider) or {}).get("task")
                    try:
                        inspect.signature(_call_fal).bind(
                            provider, pid, routed_payload, key, timeout,
                            mapping_task=mapping_task,
                        )
                    except TypeError:
                        pass
                    else:
                        extra["mapping_task"] = mapping_task
                    code, data, submitted = _call_fal(
                        provider, pid, routed_payload, key, timeout, **extra
                    )
                    meta["submittedInput"] = submitted
                    if code >= 400 or data.get("error"):
                        if isinstance(data, dict):
                            data.setdefault("error", extract_error(data, f"HTTP {code}"))
                        last = (code if code >= 400 else 502, data)
                        # v0821o5: do not continue to wavespeed and overwrite the fal-ai error
                        if _fal_ai_error_is_final(provider, mid, mapping):
                            return last
                        continue
                    if data.get("request_id"):
                        try:
                            result_url = _queue_url(data.get("response_url"))
                            status_url = _queue_url(data["status_url"]) if data.get("status_url") else result_url.replace("?_subdomain=queue", "/status?_subdomain=queue")
                        except ValueError as exc:
                            return 502, {"error": str(exc), "backend": self.id, "provider": provider}
                        jid = jid.replace("|sync|", "|queue|")
                        meta.update(jobId=jid, queueResultUrl=result_url, queueStatusUrl=status_url, provider=provider)
                        remember_job(jid, meta)
                        return 200, {
                            "id": jid, "status": "pending", "backend": self.id, "endpoint": mid,
                            "provider": provider, "submittedInput": submitted,
                        }
                    saved = _save_json_images(data, jid, meta=meta)
                else:
                    code, data, submitted = _call_openai(provider, pid, payload or {}, key, timeout)
                    meta["submittedInput"] = submitted
                    err_txt = extract_error(data, f"HTTP {code}") if isinstance(data, dict) else str(data)
                    if code >= 400 or data.get("error") or (isinstance(err_txt, str) and "Not allowed to POST" in err_txt):
                        if isinstance(data, dict):
                            data.setdefault("error", err_txt)
                        last = (code if code >= 400 else 400, data if isinstance(data, dict) else {"error": err_txt})
                        continue
                    saved = _save_json_images(data, jid, meta=meta)
            except ValueError as e:
                return 400, {"error": str(e), "backend": self.id, "provider": provider}
            except Exception as e:
                last = (502, {"error": "Hugging Face 请求失败", "detail": str(e), "provider": provider})
                if _fal_ai_error_is_final(provider, mid, mapping):
                    return last
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
                remember_job(jid, {**meta, "result": out})
                return 200, out
            last = (502, {"error": "Hugging Face 没有返回图片", "provider": provider})
            if _fal_ai_error_is_final(provider, mid, mapping):
                return last
        return last

    def job_status(self, job_id: str):
        meta = job_meta(job_id)
        if not meta or meta.get("backend") != self.id:
            return 404, {"id": job_id, "error": "没有此 HF 任务记录，不能推断成功", "backend": self.id}
        if meta.get("result"):
            return 200, meta["result"]
        if not meta.get("queueStatusUrl"):
            return 502, {"id": job_id, "error": "HF 任务缺少查询地址", "backend": self.id}
        key = hf_key()
        if not key:
            return 401, {"error": "没有 Hugging Face API Key", "backend": self.id}
        headers = _auth_headers(key)
        code, data = json_call(meta["queueStatusUrl"], headers=headers, timeout=60)
        if code >= 400 or not isinstance(data, dict):
            return code if code >= 400 else 502, {"id": job_id, "error": extract_error(data), "backend": self.id}
        state = str(data.get("status") or "").upper()
        out = {
            "id": job_id, "backend": self.id, "endpoint": meta.get("serviceId"),
            "provider": meta.get("provider"), "submittedInput": meta.get("submittedInput"),
        }
        if state in ("IN_QUEUE", "IN_PROGRESS"):
            return 200, {**out, "status": "pending" if state == "IN_QUEUE" else "processing"}
        if state != "COMPLETED" or data.get("error"):
            return 200, {**out, "status": "failed", "error": extract_error(data, f"HF 队列状态异常：{state}")}
        code, result = json_call(meta["queueResultUrl"], headers=headers, timeout=60)
        if code >= 400 or not isinstance(result, dict) or result.get("error"):
            return 200, {
                **out,
                "status": "failed",
                "error": extract_error(result, "HF 获取结果失败"),
            }
        try:
            saved = _save_json_images(result, job_id, meta=meta)
        except Exception as exc:
            return 502, {**out, "error": f"HF 媒体保存失败：{exc}"}
        if not saved:
            return 502, {**out, "error": "HF 队列已完成，但没有获得媒体文件"}
        out.update(status="succeeded", saved=saved)
        remember_job(job_id, {**meta, "result": out})
        return 200, out


from . import register  # noqa: E402

register(HuggingFaceProvider())
