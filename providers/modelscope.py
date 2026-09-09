from __future__ import annotations

import json
import math
import re
import os
import socket
from pathlib import Path
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
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
    for pfx in ("modelscope-ai/", "modelscope-cn/", "ms/", "modelscope/", "魔搭/"):
        if s.startswith(pfx):
            s = s[len(pfx):]
    return s


def _number(raw, field, *, integer=False, minimum=None, maximum=None):
    try:
        if isinstance(raw, bool):
            raise ValueError()
        value = int(raw) if integer else float(raw)
        if integer and not isinstance(raw, str) and value != raw:
            raise ValueError()
        if not math.isfinite(value) or (minimum is not None and value < minimum) or (maximum is not None and value > maximum):
            raise ValueError()
    except (TypeError, ValueError, OverflowError):
        bounds = f"（{minimum} ≤ 原值 ≤ {maximum}）" if maximum is not None else (
            f"（原值 ≥ {minimum}）" if minimum is not None else "")
        raise ValueError(f"{field} 必须是{'整数' if integer else '有限数值'}{bounds}，拒绝静默改值") from None
    return value


def _clamp_seed(raw):
    """Historical name retained for callers; now rejects, never wraps int32."""
    return _number(raw, "seed", integer=True, minimum=-1, maximum=2147483647)


def _value(payload, *names):
    values = [payload[key] for key in names if payload.get(key) not in (None, "")]
    if values and any(value != values[0] for value in values[1:]):
        raise ValueError(f"{'/'.join(names)} 的值冲突，拒绝覆盖")
    return values[0] if values else None


_HUB_LORA_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


def _hub_lora_repo(raw):
    if not isinstance(raw, str):
        return None
    repo = raw.strip()
    return repo if _HUB_LORA_RE.fullmatch(repo) else None


def _modelscope_loras(payload: dict):
    """Official API-Inference LoRA wire shape (2026-09-09 live + docs).

    https://www.modelscope.cn/docs/model-service/API-Inference/intro
      - one LoRA:  string \"owner/repo\"
      - many:      {\"owner/repo\": weight, ...} and weights must sum to 1.0

    Live Krea 400: `loras[0] is not a string` when we sent [{model, weight}].
    Live CN 500: `{repo: 0.8}` for one LoRA → 模型不存在. Single with weight is
    not remapped to a dict and the weight is not dropped.
    Civitai download / AIR is not remapped; refuse rather than drop or invent Hub id.
    Missing weight is not defaulted to 1.0.
    """
    raw = payload.get("loras")
    if raw in (None, [], {}):
        return None
    items = []
    if isinstance(raw, str):
        items = [(raw, None)]
    elif isinstance(raw, dict):
        items = list(raw.items())
    elif isinstance(raw, list):
        for item in raw:
            if isinstance(item, str):
                items.append((item, None))
            elif isinstance(item, dict):
                repo = (
                    item.get("model") or item.get("path") or item.get("url")
                    or item.get("downloadUrl") or item.get("download_url")
                    or item.get("name") or item.get("id")
                )
                items.append((repo, _value(item, "weight", "scale", "strength")))
            else:
                raise ValueError("魔搭 LoRA 条目必须是 Hub owner/repo")
    else:
        raise ValueError("魔搭 LoRA 必须是 Hub owner/repo 字符串、{repo:weight} 或数组")
    parsed = []
    for repo, weight in items:
        hub = _hub_lora_repo(repo)
        if not hub:
            raise ValueError("魔搭 LoRA 必须是 Hub owner/repo，不能跳过下载链或 AIR 后只生成底模")
        parsed.append((hub, weight))
    if not parsed:
        return None
    if len(parsed) == 1:
        repo, weight = parsed[0]
        if weight is not None:
            raise ValueError(
                "魔搭单条 LoRA 官方字段是 owner/repo 字符串，没有 weight；"
                "不会改成 {repo:weight}（CN 实测 500 模型不存在），也不会丢权重"
            )
        return repo
    out = {}
    for repo, weight in parsed:
        if weight is None:
            raise ValueError("魔搭多 LoRA 必须每条都有 weight/scale/strength，拒绝默认 1.0")
        if repo in out:
            raise ValueError(f"魔搭 LoRA 重复: {repo}")
        out[repo] = _number(weight, "LoRA weight")
    total = sum(out.values())
    if abs(total - 1.0) > 1e-6:
        raise ValueError(f"魔搭多 LoRA 官方要求 weight 之和为 1.0，收到 {total}；拒绝缩放")
    return out


def _image_body(payload, mid, backend):
    if payload.get("prompt") is not None and not isinstance(payload["prompt"], str):
        raise ValueError("prompt 必须是文本")
    body = {"model": mid, "prompt": payload.get("prompt") or ""}
    negative = _value(payload, "negativePrompt", "negative_prompt")
    if negative is not None:
        if not isinstance(negative, str):
            raise ValueError("negativePrompt 必须是文本")
        body["negative_prompt"] = negative
    seed = _value(payload, "seed")
    if seed is not None and seed != "random":
        body["seed"] = _clamp_seed(seed)
    for names, field, integer in (
        (("steps", "num_inference_steps"), "steps", True),
        (("cfgScale", "guidance", "guidance_scale", "cfg"), "guidance", False),
    ):
        value = _value(payload, *names)
        if value is not None:
            body[field] = _number(value, "/".join(names), integer=integer, minimum=1 if integer else None)
    width, height = _value(payload, "width"), _value(payload, "height")
    if (width is None) != (height is None):
        raise ValueError("width/height 必须一起填写")
    if width is not None:
        width = _number(width, "width", integer=True, minimum=1)
        height = _number(height, "height", integer=True, minimum=1)
        body["size"] = f"{width}x{height}"
    size = _value(payload, "resolution", "size")
    if size is not None:
        match = re.fullmatch(r"(\d+)\s*[x×*]\s*(\d+)", size.strip()) if isinstance(size, str) else None
        if not match:
            raise ValueError("resolution/size 必须是明确的宽x高；拒绝近似尺寸")
        w = _number(match[1], "width", integer=True, minimum=1)
        h = _number(match[2], "height", integer=True, minimum=1)
        if "size" in body and body["size"] != f"{w}x{h}":
            raise ValueError("resolution/size 与 width/height 冲突")
        body["size"] = f"{w}x{h}"
    for field in ("sampler", "scheduler", "duration", "aspectRatio", "aspect_ratio",
                  "denoise", "strength", "lastFrame", "end_image_url"):
        if payload.get(field) not in (None, ""):
            raise ValueError(f"{backend} 当前图片适配器未接入 {field}；拒绝丢参生成，不能据此认定 API 不支持")
    quantity = _value(payload, "quantity", "qty", "n", "num_images")
    if quantity is not None and _number(quantity, "quantity", integer=True, minimum=1) != 1:
        raise ValueError(f"{backend} 当前适配器未接入 quantity 多图；不会只生成一张")
    loras = _modelscope_loras(payload)
    if loras is not None:
        body["loras"] = loras
    from .ref_images import max_refs
    from .capabilities import get_provider_capabilities
    from .fal import materialize_fal_media
    # Reuse local-media materialization, not Fal's parameter mapper or transport.
    values = []
    for field in ("firstFrame", "sourceImage", "startImage", "image_url", "imageUrl", "imageDataUrl",
                  "image", "images", "referenceImages", "input_references", "image_urls"):
        value = payload.get(field)
        if value not in (None, ""):
            values.extend(value if isinstance(value, list) else [value])
    refs = materialize_fal_media({"image_urls": values})["image_urls"]
    if any(not isinstance(value, str) or not value.startswith(("https://", "http://", "data:")) for value in refs):
        raise ValueError("参考图必须是有效 URL、data URL 或可读取的 /out 文件，拒绝跳过")
    refs = list(dict.fromkeys(refs))
    from .capabilities import modelscope_t2i_refs_error, overlay_modelscope_catalog_item
    item = overlay_modelscope_catalog_item({"id": mid})
    t2i_err = modelscope_t2i_refs_error(mid, len(refs), item)
    if t2i_err:
        raise ValueError(t2i_err)
    limit = max_refs(backend=backend, caps=get_provider_capabilities(backend), item=item, payload=payload)
    if refs and limit is None:
        raise ValueError(f"{backend} 当前模型参考图上限未知，拒绝按通用上限截断")
    if limit is not None and len(refs) > limit:
        raise ValueError(f"{backend} 当前参考图接线最多 {limit} 张，收到 {len(refs)} 张；拒绝截断")
    if refs:
        body["image_url"] = refs[0] if len(refs) == 1 else refs
    return body


HUB = "https://www.modelscope.cn/openapi/v1/models"
# Website catalog (PUT). OpenAPI GET has no working inference_type filter.
MODELS_PUT = "https://www.modelscope.cn/api/v1/models"
AIGC_TEMPLATE = "https://www.modelscope.cn/api/v1/muse/predict/unauth/defaultTemplateV2"
# Hub slug, studio category, task, tags, needsSource, needsFirstFrame
HUB_TASKS = (
    ("text-to-image-synthesis", "image", "text-to-image", ["t2i"], False, False),
    ("image-to-image", "image", "image-to-image", ["i2i"], True, False),
    ("text-to-video-synthesis", "video", "text-to-video", ["t2v"], False, False),
    ("image-to-video", "video", "image-to-video", ["i2v"], False, True),
)
_HUB_CACHE = {"at": 0.0, "items": None, "totals": {}}
_HUB_TTL = 300
# Official OpenAPI: page_size maximum 50; page_number * page_size <= 3000.
_HUB_PAGE = 50
_HUB_OPENAPI_OFFSET_MAX = 3000
_HUB_SEARCH_PAGES = 3
# PUT /api/v1/models allows PageSize 200; 100 keeps payloads smaller.
_HUB_PUT_PAGE = 100
_HUB_WORKERS = 8
# Website filter=inference_type is not on OpenAPI. PUT tags=Checkpoint is the
# generatable AIGC base-model slice (SupportInference txt2img/img2img).
# LoRA tag is ~88k adapters — those stay on search_loras, not the model dropdown.
_AIGC_LIST_TAGS = ("Checkpoint",)
_AIGC_SKIP_TYPES = {"VAE", "TextualInversion"}
_INFER_CLASS = {
    "txt2img": ("image", "text-to-image", ["t2i"], False, False),
    "img2img": ("image", "image-to-image", ["i2i"], True, False),
    "txt2vid": ("video", "text-to-video", ["t2v"], False, False),
    "img2vid": ("video", "image-to-video", ["i2v"], False, True),
}


def _parameter_capabilities(mid, task, *, channel):
    endpoint_fields = {
        "prompt", "negative_prompt", "size", "seed", "steps",
        "guidance", "image_url", "loras",
    }
    if task not in ("image-to-image", "image-to-video"):
        endpoint_fields.discard("image_url")
    return {
        "model": mid,
        "task": task,
        "channel": channel,
        "callability": "unknown",
        "source": "ModelScope Hub task metadata; Hub inclusion does not prove inference availability",
        "supported": ["prompt"],
        "unknown": sorted(endpoint_fields - {"prompt"}),
        "endpointFields": sorted(endpoint_fields),
    }


def _alnum(s):
    return "".join(ch for ch in (s or "").lower() if ch.isalnum())


from .hub_classify import (  # noqa: E402
    _UPSCALE_RE,
    apply_upscale_category as _apply_upscale_category,
    hub_upscale_blob,
)




def _hub_row(it, cat, task, tags, needs_src, needs_ff, *, callability="unknown", source=None):
    mid = (it.get("id") or it.get("name") or "").strip()
    name = (it.get("chinese_name") or it.get("ChineseName") or it.get("name") or (mid.split("/")[-1] if mid else "")).strip()
    cap_source = source or (
        "Hub task metadata identifies a task, not AI/CN inference availability or model schema"
    )
    channels = {
        "modelscope-ai": _parameter_capabilities(mid, task, channel="modelscope-ai"),
        "modelscope-cn": _parameter_capabilities(mid, task, channel="modelscope-cn"),
    }
    for caps in channels.values():
        caps["callability"] = callability
        caps["source"] = cap_source
    row = {
        "id": mid,
        "name": name or (mid.split("/")[-1] if mid else mid),
        "category": cat,
        "backend": "modelscope",
        "status": "available",
        "task": task,
        "tags": list(tags),
        "downloads": it.get("downloads") or it.get("Downloads"),
        "hubTask": task,
        "callability": callability,
        "parameterCapabilities": {
            "model": mid,
            "task": task,
            "channels": channels,
            "source": cap_source,
        },
    }
    if needs_src:
        row["needsSource"] = True
    if needs_ff:
        row["needsFirstFrame"] = True
    return _apply_upscale_category(row)


def _task_name_list(it):
    raw = it.get("tasks") or it.get("Tasks") or []
    if isinstance(raw, str):
        raw = [raw]
    names = []
    for item in raw:
        if isinstance(item, str) and item.strip():
            names.append(item.strip())
        elif isinstance(item, dict):
            name = item.get("Name") or item.get("name") or item.get("task")
            if isinstance(name, str) and name.strip():
                names.append(name.strip())
    return names


def _classify_hub(it):
    tasks = _task_name_list(it)
    for hub_task, cat, task, tags, needs_src, needs_ff in HUB_TASKS:
        if hub_task in tasks:
            return cat, task, tags, needs_src, needs_ff
    return None


def _classify_hub_all(it):
    tasks = _task_name_list(it)
    return [
        (cat, task, tags, needs_src, needs_ff)
        for hub_task, cat, task, tags, needs_src, needs_ff in HUB_TASKS
        if hub_task in tasks
    ]


def _classes_for_item(it):
    classes = _classify_hub_all(it)
    if classes:
        return classes
    infer = str(it.get("SupportInference") or it.get("supportInference") or "").strip().lower()
    mapped = _INFER_CLASS.get(infer)
    return [mapped] if mapped else []


def _put_mid(it):
    path = str(it.get("Path") or "").strip().strip("/")
    name = str(it.get("Name") or "").strip()
    if path and name:
        return f"{path}/{name}"
    mid = it.get("id") or it.get("Id") or ""
    if isinstance(mid, str) and mid.count("/") == 1:
        return mid.strip()
    return ""


def _mid_from_modelscope_url(url):
    text = str(url or "").strip()
    if "modelscope://" in text:
        text = text.split("modelscope://", 1)[1]
    text = text.split("?", 1)[0].strip().strip("/")
    if text.count("/") == 1:
        return text
    return ""


def _append_row(items, seen, it, cls, *, callability, source, extra=None):
    row = _hub_row(it, *cls, callability=callability, source=source)
    if extra:
        row.update(extra)
    key = (row["id"], row["task"])
    if not row["id"] or key in seen:
        return False
    seen.add(key)
    items.append(row)
    return True


def _openapi_max_page():
    return max(1, _HUB_OPENAPI_OFFSET_MAX // _HUB_PAGE)


def fetch_hub_search(search):
    """OpenAPI search. page_size max 50. Typeahead stops at 3 pages."""
    items, seen, totals = [], set(), {}
    q = (search or "").strip()
    if not q:
        return items, totals
    if q.count("/") == 1 and " " not in q:
        code, data = json_call(f"{HUB}/{quote(q, safe='')}", headers=auth_headers(), timeout=20)
        block = data.get("data") or data.get("Data") if isinstance(data, dict) else None
        if code == 200 and isinstance(block, dict):
            block.setdefault("id", q)
            classes = _classify_hub_all(block) or [("image", "text-to-image", ["t2i"], False, False)]
            for cls in classes:
                _append_row(items, seen, block, cls, callability="unknown", source="OpenAPI model detail")
    last_allowed = min(_HUB_SEARCH_PAGES, _openapi_max_page())
    page = 1
    pages_fetched = 0
    while page <= last_allowed:
        qs = f"search={quote(q)}&sort=downloads&page_size={_HUB_PAGE}&page_number={page}"
        code, data = json_call(f"{HUB}?{qs}", headers=auth_headers(), timeout=30)
        block = data.get("data") if isinstance(data, dict) else None
        models = (block.get("models") or []) if isinstance(block, dict) else []
        if code != 200 or not isinstance(block, dict):
            totals["searchComplete"] = False
            totals["searchHttp"] = code
            break
        pages_fetched += 1
        try:
            totals["search"] = int(block.get("total_count") or 0)
        except (TypeError, ValueError):
            totals["search"] = 0
        for it in models:
            if not isinstance(it, dict):
                continue
            classes = _classify_hub_all(it)
            if not classes:
                continue
            for cls in classes:
                _append_row(items, seen, it, cls, callability="unknown", source="OpenAPI search")
        covered = page * _HUB_PAGE
        if not models or (totals.get("search") and covered >= totals["search"]):
            break
        page += 1
    totals["searchPages"] = pages_fetched
    totals["searchFetched"] = len(items)
    totals["pageSize"] = _HUB_PAGE
    totals.setdefault(
        "searchComplete",
        bool(totals.get("search") and pages_fetched * _HUB_PAGE >= int(totals["search"])),
    )
    return items, totals


def _openapi_task_total(hub_task):
    qs = f"filter.task={quote(hub_task, safe='')}&sort=downloads&page_size=1&page_number=1"
    code, data = json_call(f"{HUB}?{qs}", headers=auth_headers(), timeout=20)
    block = data.get("data") if isinstance(data, dict) else None
    total = 0
    if code == 200 and isinstance(block, dict):
        try:
            total = int(block.get("total_count") or 0)
        except (TypeError, ValueError):
            total = 0
    return code, total, None if code == 200 else (
        (data.get("error") if isinstance(data, dict) else None) or f"HTTP {code}"
    )


def _put_models_page(tag, page, page_size=_HUB_PUT_PAGE):
    body = {
        "PageNumber": int(page),
        "PageSize": int(page_size),
        "Criterion": [{"category": "tags", "predicate": "contains", "values": [tag]}],
    }
    code, data = json_call(MODELS_PUT, method="PUT", headers=auth_headers(), body=body, timeout=30)
    block = data.get("Data") if isinstance(data, dict) and isinstance(data.get("Data"), dict) else None
    if code != 200 or not block:
        err = None
        if isinstance(data, dict):
            err = data.get("Message") or data.get("error") or data.get("message")
        return code, None, err or f"HTTP {code}"
    return code, block, None


def _ingest_put_models(models, items, seen, totals):
    kept = 0
    skipped = 0
    source = "PUT /api/v1/models tags=Checkpoint (AIGC generatable, not Hub weights)"
    for it in models or []:
        if not isinstance(it, dict):
            continue
        aigc_type = str(it.get("AigcType") or "").strip()
        if aigc_type in _AIGC_SKIP_TYPES:
            skipped += 1
            continue
        infer = str(it.get("SupportInference") or "").strip().lower()
        if infer not in _INFER_CLASS and not it.get("SupportExperience"):
            skipped += 1
            continue
        mid = _put_mid(it)
        if not mid:
            skipped += 1
            continue
        payload = {
            "id": mid,
            "name": it.get("ChineseName") or it.get("Name") or mid.split("/")[-1],
            "chinese_name": it.get("ChineseName") or it.get("Name"),
            "downloads": it.get("Downloads"),
            "Tasks": it.get("Tasks") or [],
            "SupportInference": infer,
        }
        classes = _classes_for_item(payload)
        if not classes:
            skipped += 1
            continue
        extra = {
            "aigcType": aigc_type or None,
            "supportInference": infer or None,
            "supportExperience": bool(it.get("SupportExperience")),
        }
        added = False
        for cls in classes:
            if _append_row(items, seen, payload, cls, callability="generatable", source=source, extra=extra):
                added = True
        if added:
            kept += 1
        else:
            skipped += 1
    totals["aigcKept"] = int(totals.get("aigcKept") or 0) + kept
    totals["aigcSkipped"] = int(totals.get("aigcSkipped") or 0) + skipped
    return kept


def _ingest_aigc_template(items, seen, totals):
    # This endpoint 401s with Bearer ("用户未登录") and 200s anonymously.
    code, data = json_call(AIGC_TEMPLATE, timeout=25)
    totals["aigcTemplateHttp"] = code
    inner = None
    if isinstance(data, dict):
        block = data.get("Data") if isinstance(data.get("Data"), dict) else data.get("data")
        if isinstance(block, dict):
            inner = block.get("data") if isinstance(block.get("data"), dict) else block
            if isinstance(inner, dict) and "IMAGE" not in inner and isinstance(inner.get("data"), dict):
                inner = inner["data"]
    if code != 200 or not isinstance(inner, dict):
        totals["aigcTemplateError"] = (
            (data.get("Message") if isinstance(data, dict) else None)
            or (data.get("error") if isinstance(data, dict) else None)
            or f"HTTP {code}"
        )
        totals["aigcTemplateAdded"] = 0
        return 0
    added = 0
    source = "GET /api/v1/muse/predict/unauth/defaultTemplateV2 supportSDVersionList"
    buckets = []
    for key in ("IMAGE", "VIDEO", "AUDIO"):
        bucket = inner.get(key)
        if isinstance(bucket, dict):
            buckets.append((key, bucket))
    for key, bucket in buckets:
        for item in bucket.get("supportSDVersionList") or []:
            if not isinstance(item, dict):
                continue
            mid = ""
            model_id = item.get("model_id")
            if isinstance(model_id, dict):
                mid = str(model_id.get("path") or "").strip()
            if not mid:
                mid = _mid_from_modelscope_url(item.get("modelUrl") or item.get("model_url"))
            if not mid:
                continue
            label = item.get("label") or item.get("sub_label") or mid.split("/")[-1]
            chinese = ""
            if isinstance(model_id, dict):
                chinese = model_id.get("ChineseName") or model_id.get("Name") or ""
            support_types = item.get("supportType") or []
            if not isinstance(support_types, list):
                support_types = [support_types] if support_types else []
            gen_type = str(item.get("gen_type") or "").upper()
            is_video = str(item.get("is_video_model") or "").lower() == "true" or key == "VIDEO"
            classes = []
            type_blob = " ".join(str(x) for x in support_types) + " " + gen_type
            if is_video:
                if "TXT_2_VIDEO" in type_blob or gen_type == "T2V":
                    classes.append(("video", "text-to-video", ["t2v"], False, False))
                if "IMG_2_VIDEO" in type_blob or "FLF_2_VIDEO" in type_blob or gen_type in ("I2V", "IT2V", "FLF2V"):
                    classes.append(("video", "image-to-video", ["i2v"], False, True))
                if not classes:
                    classes.append(("video", "text-to-video", ["t2v"], False, False))
            else:
                low = (mid + " " + str(label)).lower()
                if "edit" in low or "kontext" in low:
                    classes.append(("image", "image-to-image", ["i2i"], True, False))
                else:
                    classes.append(("image", "text-to-image", ["t2i"], False, False))
            payload = {"id": mid, "name": chinese or label, "chinese_name": chinese or label}
            extra = {"aigcType": "Checkpoint", "supportInference": "template", "supportExperience": True}
            for cls in classes:
                if _append_row(items, seen, payload, cls, callability="generatable", source=source, extra=extra):
                    added += 1
        for field in ("qwenImageEditModelUrl", "fluxHighResModelUrl", "fluxKontextModelUrl"):
            raw = bucket.get(field)
            values = raw if isinstance(raw, list) else ([raw] if raw else [])
            for url in values:
                mid = _mid_from_modelscope_url(url)
                if not mid:
                    continue
                payload = {"id": mid, "name": mid.split("/")[-1]}
                cls = ("image", "image-to-image", ["i2i"], True, False) if "edit" in mid.lower() or "kontext" in mid.lower() else (
                    "image", "text-to-image", ["t2i"], False, False
                )
                extra = {"aigcType": "Checkpoint", "supportInference": "template", "supportExperience": True}
                if _append_row(items, seen, payload, cls, callability="generatable", source=source, extra=extra):
                    added += 1
    extra_list = inner.get("qwenImageEditModelUrlList") or []
    if isinstance(extra_list, list):
        for url in extra_list:
            mid = _mid_from_modelscope_url(url)
            if not mid:
                continue
            payload = {"id": mid, "name": mid.split("/")[-1]}
            cls = ("image", "image-to-image", ["i2i"], True, False)
            extra = {"aigcType": "Checkpoint", "supportInference": "template", "supportExperience": True}
            if _append_row(items, seen, payload, cls, callability="generatable", source=source, extra=extra):
                added += 1
    totals["aigcTemplateAdded"] = added
    return added


def fetch_hub(search=""):
    if (search or "").strip():
        return fetch_hub_search(search)
    items = []
    seen = set()
    totals = {
        "source": "PUT /api/v1/models tags=Checkpoint + AIGC template",
        "filter": "generatable AIGC (SupportInference txt2img/img2img), not Hub weight dump",
        "pageSizeOpenAPI": _HUB_PAGE,
        "pageSizePut": _HUB_PUT_PAGE,
        "loraInCatalog": 0,
        "loraHubNote": "AIGC LoRA (~88k) stays on search_loras; model dropdown is Checkpoints + official bases + pins",
    }
    for hub_task, *_rest in HUB_TASKS:
        code, total, err = _openapi_task_total(hub_task)
        totals[hub_task] = total
        totals[f"{hub_task}Http"] = code
        if err:
            totals[f"{hub_task}Error"] = err
    reachable = False
    pages_fetched = 0
    for tag in _AIGC_LIST_TAGS:
        code, block, err = _put_models_page(tag, 1)
        pages_fetched += 1
        if code != 200 or not block:
            totals["aigcCheckpointError"] = err or f"HTTP {code}"
            totals["complete"] = False
            continue
        reachable = True
        try:
            tag_total = int(block.get("TotalCount") or 0)
        except (TypeError, ValueError):
            tag_total = len(block.get("Models") or [])
        totals["aigcCheckpoint"] = tag_total
        _ingest_put_models(block.get("Models") or [], items, seen, totals)
        last_page = max(1, (tag_total + _HUB_PUT_PAGE - 1) // _HUB_PUT_PAGE) if tag_total else 1
        if last_page > 1:
            with ThreadPoolExecutor(max_workers=_HUB_WORKERS) as pool:
                futs = {
                    pool.submit(_put_models_page, tag, page): page
                    for page in range(2, last_page + 1)
                }
                for fut in as_completed(futs):
                    pages_fetched += 1
                    try:
                        pcode, pblock, perr = fut.result()
                    except Exception as exc:
                        totals.setdefault("aigcPageErrors", []).append(str(exc))
                        continue
                    if pcode != 200 or not pblock:
                        totals.setdefault("aigcPageErrors", []).append(perr or f"HTTP {pcode}")
                        continue
                    _ingest_put_models(pblock.get("Models") or [], items, seen, totals)
    _ingest_aigc_template(items, seen, totals)
    totals["_pagesFetched"] = pages_fetched
    totals["_reachable"] = reachable
    totals["unique"] = len(seen)
    totals["fetched"] = len(items)
    totals["complete"] = bool(
        reachable
        and totals.get("aigcCheckpoint")
        and not totals.get("aigcCheckpointError")
        and int(totals.get("aigcKept") or 0) > 0
    )
    return items, totals


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


def is_edit(mid: str) -> bool:
    low = (mid or "").lower()
    return "image-edit" in low or "image-to-image" in low or "/edit" in low


def _catalog_page_args(page=1, pageSize=50, max_size=100):
    """View paging over the already-fetched AIGC Checkpoint list. Does not change fetch_hub."""
    try:
        page = int(page)
    except (TypeError, ValueError):
        page = 1
    if page < 1:
        page = 1
    try:
        size = int(pageSize)
    except (TypeError, ValueError):
        size = 50
    if size < 1:
        size = 1
    if size > max_size:
        size = max_size
    return page, size


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

    def catalog(self, q, category, status, page=1, pageSize=50) -> dict:
        qn = (q or "").strip()
        now = time.time()
        totals = {}
        cache_key = self.id
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
                totals = dict(totals or {})
                totals["pinFallback"] = True
                totals["complete"] = False
                totals.setdefault(
                    "error",
                    "AIGC Checkpoint 目录拉取失败，已回退 pin 短名单；不是官网只有这些",
                )
            if not qn:
                _HUB_CACHE["items"] = list(items)
                _HUB_CACHE["at"] = now
                _HUB_CACHE["totals"] = totals
        qnl = qn.lower()
        items = [_apply_upscale_category(dict(x)) for x in items]
        if category:
            items = [x for x in items if x.get("category") == category]
        if status:
            items = [x for x in items if x.get("status") == status]
        if qnl:
            needle = _alnum(qnl)
            items = [x for x in items if needle in _alnum(x.get("name")) or needle in _alnum(x.get("id"))]
        tagged = []
        from .capabilities import overlay_modelscope_catalog_item
        for x in items:
            row = dict(x)
            row["backend"] = self.id
            tagged.append(overlay_modelscope_catalog_item(row))
        page, page_size = _catalog_page_args(page, pageSize)
        total = len(tagged)
        start = (page - 1) * page_size
        sliced = tagged[start:start + page_size]
        has_more = start + len(sliced) < total
        hub_complete = bool((totals or {}).get("complete"))
        partial = (not hub_complete) or bool((totals or {}).get("pinFallback"))
        body = {
            "total": total,
            "count": len(sliced),
            "backend": self.id,
            "items": sliced,
            "hasKey": self.has_key(),
            "baseUrl": self._base,
            "hub": HUB,
            "hubTotals": totals,
            "hubCoverage": {
                "source": (totals or {}).get("source") or "ModelScope AIGC Checkpoint + template + pins",
                "channel": self.id,
                "callability": "generatable" if hub_complete else "unknown",
                "fetchedUnique": len({x.get("id") for x in tagged}),
                "hubTotals": totals,
            },
            "page": page,
            "pageSize": page_size,
            "hasMore": has_more,
            "nextPage": (page + 1) if has_more else None,
            "complete": hub_complete,
            "partial": partial,
        }
        warning = None
        if isinstance(totals, dict):
            warning = totals.get("error") or totals.get("aigcCheckpointError")
        if warning:
            body["warning"] = warning
        return body

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
        return 200, {
            "backend": self.id,
            "cost": {"total": None, "note": f"{self.label} 按次计费，无黄 Buzz 预估"},
            "service": {"serviceId": (payload or {}).get("serviceId")},
            "baseUrl": self._base,
        }

    def generate(self, payload: dict):
        if not isinstance(payload, dict) or not isinstance(payload.get("serviceId", ""), str):
            return 400, {"error": "请求必须是对象，serviceId 必须是文本", "backend": self.id}
        err = self._reach_error()
        if err:
            return 502, {"error": err, "backend": self.id, "baseUrl": self._base}
        key = self._key()
        if not key:
            return 401, {"error": f"没有{self.label} API Key，放在 {self._token_path}", "backend": self.id}
        sid = (payload or {}).get("serviceId") or ""
        other = "modelscope-ai/" if self.flavor == "cn" else "modelscope-cn/"
        if sid.startswith(other):
            return 400, {"error": "模型前缀与所选魔搭 AI/CN 不一致，拒绝跨家发送", "backend": self.id}
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
        try:
            body = _image_body(payload, mid, self.id)
        except ValueError as exc:
            return 400, {"error": str(exc), "backend": self.id}
        headers = self._auth({"X-ModelScope-Async-Mode": "true"})
        url = f"{self._base}/images/generations"
        code, data = json_call(url, method="POST", headers=headers, body=body, timeout=90)
        if not isinstance(data, dict):
            return code if code >= 400 else 502, {"error": f"{self.label} 响应无效", "backend": self.id, "baseUrl": self._base}
        if code >= 400 or data.get("error"):
            data.setdefault("error", extract_error(data, f"HTTP {code}"))
            data["backend"] = self.id
            data["baseUrl"] = self._base
            return code if code >= 400 else 502, data
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
