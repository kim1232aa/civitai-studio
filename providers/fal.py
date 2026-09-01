from __future__ import annotations

import json
from pathlib import Path

from .base import Provider
import re
from urllib.parse import quote

from .http import collect_urls, json_call, parse_job_id, save_media_urls
from .io_meta import looks_like_civitai_service, remember_job as remember_studio_job, job_meta

TOKEN_PATH = Path.home() / ".config/fal/token"
ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
QUEUE = "https://queue.fal.run"
MODELS_API = "https://api.fal.ai/v1/models"

# Endpoint ids that are Fal even when not yet in the local catalog.
FAL_PREFIXES = (
    "fal-ai/",
    "krea/",
    "minimax/",
    "bytedance/",
    "openai/",
    "google/",
    "xai/",
    "wan/",
    "kling/",
    "alibaba/",
    "lightricks/",
)


def fal_key() -> str:
    try:
        return TOKEN_PATH.read_text().strip()
    except Exception:
        return ""


def has_key() -> bool:
    return bool(fal_key())


def fal_call(url: str, method="GET", body=None, timeout=90):
    key = fal_key()
    if not key:
        return 401, {"error": "没有 Fal API Key"}
    headers = {"Authorization": f"Key {key}"}
    return json_call(url, method=method, headers=headers, body=body, timeout=timeout)


def load_catalog():
    fp = DOCS / "fal-models.json"
    if not fp.exists():
        return []
    try:
        data = json.loads(fp.read_text())
        return data.get("items") or data.get("models") or []
    except Exception:
        return []


def load_openapi_overlay():
    fp = DOCS / "fal-openapi-models.json"
    if not fp.exists():
        return []
    try:
        data = json.loads(fp.read_text())
        return data.get("models") or data.get("items") or []
    except Exception:
        return []


def find_model(endpoint_id: str):
    for it in load_catalog():
        if it.get("id") == endpoint_id:
            return it
    for it in load_openapi_overlay():
        if it.get("id") == endpoint_id:
            return it
    return None


def infer_image_fields(eid: str) -> list:
    e = eid or ""
    # Imagen4 preview/fast/ultra OpenAPI 404 (deprecated). Do not invent fields.
    if "imagen4" in e:
        return []
    if "video-to-video" in e and "/edit" in e:
        return ["video_url", "image_urls"]
    if "/edit" in e or "image-to-image" in e:
        if any(x in e for x in ("flux-2", "gpt-image", "nano-banana")):
            return ["image_urls"]
        return ["image_url"]
    if "first-last-frame" in e or "first_last" in e:
        return ["first_frame_url", "last_frame_url"]
    if "reference-to-video" in e:
        if "kling-video/o3" in e:
            return ["start_image_url", "end_image_url", "image_urls"]
        return ["image_urls"]
    if "audio-to-video" in e:
        return ["image_url"]
    if e.rstrip("/") == "fal-ai/runway-gen3" or e.startswith("fal-ai/runway-gen3/"):
        if "text-to-video" in e:
            return []
        return ["image_url", "end_image_url"]
    if "image-to-video" in e or "start-end-to-video" in e:
        if "kling-video/v2.5-turbo/pro" in e or "kling-video/v2.1/pro" in e:
            return ["image_url", "tail_image_url"]
        if "kling-video/v2.5" in e or "kling-video/v2.1" in e or "kling-video/v3/turbo" in e:
            return ["image_url"]
        if "kling-video/v3" in e or "kling-video/v2.6" in e or "wan-3.0" in e:
            return ["start_image_url", "end_image_url"]
        if (
            "sora" in e
            or "hunyuan-video" in e
            or "hailuo-2.3" in e
            or "hailuo-02-fast" in e
            or "veo" in e
            or e.endswith("video-01/image-to-video")
            or "/wan/v2.6/" in e
            or e.startswith("wan/v2.6/")
        ):
            return ["image_url"]
        if "kling-video/o3" in e:
            return ["image_url", "end_image_url"]
        return ["image_url", "end_image_url"]
    return []


FIRST_IMAGE_FIELDS = {"image_url", "start_image_url", "first_frame_url", "image"}
LAST_IMAGE_FIELDS = {"end_image_url", "tail_image_url", "last_frame_url"}
LORA_INPUT_KEYS = ("loras", "lora", "lora_url", "lora_path")


def fal_supports_lora(item) -> bool:
    """True when this Fal endpoint actually takes user LoRAs."""
    if isinstance(item, str):
        item = {"id": item}
    item = item or {}
    eid = (item.get("id") or "").lower()
    name = (item.get("name") or "").lower()
    fcat = (item.get("falCategory") or "").lower()
    tags = [str(t).lower() for t in (item.get("tags") or [])]
    fields = [str(x).lower() for x in list(item.get("required") or []) + list(item.get("optional") or [])]
    if "lora" in eid or "lora" in name:
        return True
    if any(k in fields for k in LORA_INPUT_KEYS):
        return True
    if "lora" in fcat or any("lora" in t for t in tags):
        return True
    return False


def overlay_image_fields(item: dict) -> dict:
    """Keep catalog imageFields; fill from infer_image_fields when missing.

    Fal i2v uses first-frame slots, never the image source slot.
    """
    out = dict(item)
    out.setdefault("backend", "fal")
    eid = out.get("id") or ""
    fields = list(out.get("imageFields") or infer_image_fields(eid))
    if fields:
        out["imageFields"] = fields
    recipe = (out.get("category") or "").lower()
    fcat = (out.get("falCategory") or "").lower()
    blob = f"{eid} {fcat} {recipe}".lower()
    is_video = (
        recipe == "video"
        or "video" in fcat
        or "image-to-video" in blob
        or "first-last" in blob
        or "reference-to-video" in blob
        or "start-end-to-video" in blob
    )
    has_first = any(f in FIRST_IMAGE_FIELDS for f in fields)
    has_many = "image_urls" in fields
    if is_video:
        out["needsSource"] = False
        out["needsFirstFrame"] = bool(
            has_first or "image-to-video" in blob or "first-last" in blob or "reference-to-video" in blob
        )
    elif has_many and not has_first:
        out["needsSource"] = False
    elif has_first:
        out["needsSource"] = True
        out["needsFirstFrame"] = False
    if fal_supports_lora(out):
        out["supportsLora"] = True
    return out


def _is_civitai_air(s: str) -> bool:
    t = (s or "").strip()
    if not t:
        return True
    low = t.lower()
    if low.startswith("urn:air:") or low.startswith("urn:"):
        return True
    if ":lora:" in low and "civitai" in low:
        return True
    return False


def _fal_lora_path(item: dict) -> str:
    if not isinstance(item, dict):
        return ""
    for k in ("path", "url", "downloadUrl", "download_url"):
        v = item.get(k)
        if isinstance(v, str):
            v = v.strip()
            if v and not _is_civitai_air(v):
                return v
    vid = item.get("versionId") or item.get("modelVersionId") or item.get("id")
    if vid and (isinstance(vid, int) or str(vid).isdigit()):
        return f"https://civitai.com/api/download/models/{vid}"
    return ""


def _clip_lora_scale(v, default=1.0) -> float:
    try:
        x = float(v)
    except (TypeError, ValueError):
        x = default
    return max(0.0, min(4.0, x))


def _lora_field_shape(spec: dict, eid: str):
    req_opt = [str(x).lower() for x in list(spec.get("required") or []) + list(spec.get("optional") or [])]
    if "loras" in req_opt:
        return "loras"
    if "lora_url" in req_opt:
        return "lora_url"
    if "lora_path" in req_opt:
        return "lora_path"
    if "lora" in req_opt:
        return "lora"
    e = (eid or "").lower()
    if "/lora" in e or "lora" in e:
        return "loras"
    return None


def _norm_eid(s: str) -> str:
    return (s or "").strip().lstrip("/").lower().replace("_", "-")


def fal_lora_sibling(eid: str) -> str:
    """Pick an upstream Fal endpoint that actually documents LoRA.

    No model-name presets. Order:
    1. current id already supports loras
    2. `{id}/lora` exists in the local Fal catalog
    3. catalog row whose id starts with `{id}/` and fal_supports_lora
    4. hyphen-normalized prefix match (flux/krea → flux-krea-lora)
    """
    e = (eid or "").strip().lstrip("/")
    if not e:
        return ""
    if fal_supports_lora({"id": e}):
        return e
    items = [it for it in load_catalog() if it.get("id")]
    ids = {it.get("id") for it in items}
    direct = e + "/lora"
    if direct in ids:
        return direct
    if e.endswith("/text-to-image"):
        swapped = e[: -len("/text-to-image")] + "/lora"
        if swapped in ids:
            return swapped
    prefixed = []
    for it in items:
        iid = it.get("id") or ""
        if iid == e or not fal_supports_lora(it):
            continue
        if iid.startswith(e + "/") and "lora" in iid.lower():
            prefixed.append(iid)
    if prefixed:
        prefixed.sort(key=lambda x: (x.count("/"), len(x)))
        return prefixed[0]
    needle = _norm_eid(e).replace("/", "-")
    parts = [p for p in needle.split("-") if p]
    stem = "-".join(parts[:-1]) if len(parts) > 2 else needle
    fuzzy = []
    for it in items:
        iid = it.get("id") or ""
        if iid == e or not fal_supports_lora(it):
            continue
        nid = _norm_eid(iid).replace("/", "-")
        if "lora" not in nid:
            continue
        if nid == needle + "-lora" or nid.startswith(needle + "-"):
            fuzzy.append(iid)
        elif stem and (nid == stem + "-lora" or nid.startswith(stem + "-") and nid.endswith("lora")):
            fuzzy.append(iid)
    if fuzzy:
        src_tok = set(parts)

        def _score(iid: str):
            nid = _norm_eid(iid).replace("/", "-")
            hit = set(p for p in nid.split("-") if p)
            return (-len(src_tok & hit), nid.count("-"), len(nid))

        fuzzy.sort(key=_score)
        return fuzzy[0]
    return ""


def apply_fal_loras(inp: dict, payload: dict, spec: dict, eid: str) -> None:
    shape = _lora_field_shape(spec, eid)
    if not shape:
        return
    cleaned = []
    for it in payload.get("loras") or []:
        if not isinstance(it, dict):
            continue
        path = _fal_lora_path(it)
        if not path:
            continue
        scale_raw = it.get("scale")
        if scale_raw in (None, ""):
            scale_raw = it.get("strength")
        cleaned.append({"path": path, "scale": _clip_lora_scale(scale_raw, 1.0)})
    if not cleaned:
        return
    if shape == "loras":
        inp["loras"] = cleaned
    elif shape == "lora_url":
        inp["lora_url"] = cleaned[0]["path"]
        inp["lora_scale"] = cleaned[0]["scale"]
    elif shape == "lora_path":
        inp["lora_path"] = cleaned[0]["path"]
        inp["lora_scale"] = cleaned[0]["scale"]
    elif shape == "lora":
        inp["lora"] = cleaned[0]["path"]
        if "lora_scale" in [str(x).lower() for x in list(spec.get("required") or []) + list(spec.get("optional") or [])]:
            inp["lora_scale"] = cleaned[0]["scale"]


def build_fal_input(payload: dict) -> dict:
    eid = (payload.get("serviceId") or payload.get("endpoint") or "").strip()
    spec = find_model(eid) or {}
    fields = list(spec.get("imageFields") or infer_image_fields(eid))
    prompt_key = spec.get("promptField") or "prompt"
    inp = {}
    prompt = payload.get("prompt") or ""
    if prompt_key:
        inp[prompt_key] = prompt
    img = (payload.get("firstFrame") or payload.get("sourceImage") or payload.get("image_url") or payload.get("image") or "").strip()
    last = (payload.get("lastFrame") or payload.get("endImage") or "").strip()
    extra = [x for x in (payload.get("images") or []) if x]
    if img and img not in extra:
        extra = [img] + extra
    FIRST = {"image_url", "start_image_url", "first_frame_url", "image"}
    LAST = {"end_image_url", "tail_image_url", "last_frame_url"}
    if not fields:
        for k in list(spec.get("required") or []) + list(spec.get("optional") or []):
            if k in FIRST or k in LAST or k in ("image_urls", "video_url"):
                fields.append(k)
    vid = (payload.get("videoUrl") or payload.get("video_url") or payload.get("sourceVideo") or "").strip()
    audio = (payload.get("audioUrl") or payload.get("audio_url") or "").strip()
    for name in fields:
        if name == "image_urls":
            if extra:
                inp["image_urls"] = extra[:9]
        elif name == "video_url" and vid:
            inp["video_url"] = vid
        elif name in FIRST and img:
            inp[name] = img
        elif name in LAST and last:
            inp[name] = last
    req_opt = list(spec.get("required") or []) + list(spec.get("optional") or [])
    if audio and (not spec.get("id") or "audio_url" in req_opt or "audio-to-video" in eid):
        inp["audio_url"] = audio
    if payload.get("negativePrompt") and (not spec.get("optional") or "negative_prompt" in (spec.get("optional") or [])):
        inp["negative_prompt"] = payload["negativePrompt"]
    elif payload.get("negativePrompt") and not spec.get("optional"):
        inp["negative_prompt"] = payload["negativePrompt"]
    if payload.get("seed") not in (None, "", "random"):
        try:
            inp["seed"] = int(payload["seed"])
        except (TypeError, ValueError):
            pass
    if payload.get("steps") and (not spec.get("optional") or "num_inference_steps" in (spec.get("optional") or [])):
        try:
            inp["num_inference_steps"] = int(payload["steps"])
        except (TypeError, ValueError):
            pass
    if payload.get("cfgScale") not in (None, "") and (not spec.get("optional") or "guidance_scale" in (spec.get("optional") or [])):
        try:
            inp["guidance_scale"] = float(payload["cfgScale"])
        except (TypeError, ValueError):
            pass
    if payload.get("duration") not in (None, "") and (spec.get("durationField") or not spec.get("id")):
        try:
            dur = int(payload["duration"])
            inp["duration"] = str(dur) if "kling" in eid else dur
        except (TypeError, ValueError):
            pass
    ar_field = spec.get("aspectRatioField")
    req_opt_ar = list(spec.get("optional") or []) + list(spec.get("required") or [])
    if not ar_field and "ratio" in req_opt_ar:
        ar_field = "ratio"
    if not ar_field and "aspect_ratio" in req_opt_ar:
        ar_field = "aspect_ratio"
    if ar_field and payload.get("aspectRatio"):
        inp[ar_field] = payload["aspectRatio"]
    elif payload.get("aspectRatio") and ("kontext" in eid or not req_opt_ar):
        # kontext / unschematized endpoints: official field is aspect_ratio
        inp["aspect_ratio"] = payload["aspectRatio"]
    size_keys = set(req_opt) | set(fields)
    if payload.get("width") and payload.get("height") and (
        not size_keys or "image_size" in size_keys or spec.get("category") != "video"
    ):
        try:
            inp["image_size"] = {"width": int(payload["width"]), "height": int(payload["height"])}
        except (TypeError, ValueError):
            pass
    if payload.get("scheduler") and (not req_opt or "scheduler" in req_opt):
        inp["scheduler"] = payload["scheduler"]
    # qty / quantity → num_images when the endpoint lists that field
    if "num_images" in size_keys or "num_images" in set(req_opt):
        raw_q = payload.get("quantity")
        if raw_q in (None, ""):
            raw_q = payload.get("qty")
        if raw_q in (None, ""):
            raw_q = payload.get("num_images")
        try:
            n = int(raw_q)
            if n > 0:
                inp["num_images"] = max(1, min(12, n))
        except (TypeError, ValueError):
            pass
    apply_fal_loras(inp, payload, spec, eid)
    return {k: v for k, v in inp.items() if v not in (None, "", [])}


# rid -> {endpoint, status_url, response_url}. Submit response is source of truth:
# nested endpoints like fal-ai/flux/schnell status under fal-ai/flux (first two segments).
_FAL_JOBS = {}
_FAL_JOBS_MAX = 200


def queue_app(endpoint_id: str) -> str:
    parts = [p for p in (endpoint_id or "").strip("/").split("/") if p]
    if len(parts) >= 2:
        return "/".join(parts[:2])
    return "/".join(parts)


def queue_bases(endpoint_id: str) -> list[str]:
    parts = [p for p in (endpoint_id or "").strip("/").split("/") if p]
    out = []
    if len(parts) >= 2:
        out.append("/".join(parts[:2]))
    if len(parts) >= 3:
        out.append("/".join(parts[:3]))
    if parts:
        out.append("/".join(parts))
    seen = []
    for x in out:
        if x and x not in seen:
            seen.append(x)
    return seen


def _remember_job(rid: str, meta: dict):
    if not rid:
        return
    _FAL_JOBS[rid] = meta
    extra = len(_FAL_JOBS) - _FAL_JOBS_MAX
    if extra > 0:
        for k in list(_FAL_JOBS.keys())[:extra]:
            _FAL_JOBS.pop(k, None)


def _with_logs(url: str) -> str:
    u = (url or "").strip()
    if not u:
        return u
    if "logs=" in u:
        return u
    return u + ("&" if "?" in u else "?") + "logs=1"


def _unique(seq):
    seen = []
    for x in seq:
        if x and x not in seen:
            seen.append(x)
    return seen


def status_urls(eid: str, rid: str, meta=None):
    out = []
    if meta and meta.get("status_url"):
        out.append(_with_logs(meta["status_url"]))
    for base in queue_bases(eid):
        out.append(f"{QUEUE}/{base}/requests/{rid}/status?logs=1")
    return _unique(out)


def result_urls(eid: str, rid: str, meta=None, status_data=None):
    out = []
    for src in (status_data, meta):
        if not src:
            continue
        for key in ("response_url", "result_url"):
            if src.get(key):
                u = str(src[key]).rstrip("/")
                out.append(u)
                if not u.endswith("/response"):
                    out.append(u + "/response")
    for base in queue_bases(eid):
        out.append(f"{QUEUE}/{base}/requests/{rid}")
        out.append(f"{QUEUE}/{base}/requests/{rid}/response")
    return _unique(out)


def cancel_urls(eid: str, rid: str, meta=None):
    out = []
    if meta and meta.get("cancel_url"):
        out.append(str(meta["cancel_url"]).rstrip("/"))
    for base in queue_bases(eid):
        out.append(f"{QUEUE}/{base}/requests/{rid}/cancel")
    return _unique(out)


def _try_get(urls, need_media=False):
    last_code, last_data = 502, {"error": "Fal 状态请求失败"}
    for url in urls:
        code, data = fal_call(url)
        last_code, last_data = code, data
        if code == 200 and isinstance(data, dict) and data.get("raw") != "":
            if data.get("error") and not (data.get("status") or data.get("images") or data.get("image") or data.get("request_id")):
                continue
            if need_media and not collect_urls(data):
                continue
            return code, data
        if code in (404, 405, 422):
            continue
        if isinstance(data, dict) and data.get("status") and not need_media:
            return code, data
    return last_code, last_data


def submit(payload: dict):
    eid = (payload.get("serviceId") or payload.get("endpoint") or "").strip().lstrip("/")
    if looks_like_civitai_service(eid):
        return 400, {"error": "当前选中的是 Civitai 服务，不能发给 Fal。请在 Fal 目录里选一个模型（例如 fal-ai/flux/schnell）。"}
    if not eid:
        return 400, {"error": "缺少 Fal 模型 id"}
    if payload.get("loras") and not fal_supports_lora({"id": eid}):
        sib = fal_lora_sibling(eid)
        if sib:
            eid = sib
            payload = dict(payload)
            payload["serviceId"] = eid
            payload["endpoint"] = eid
    inp = build_fal_input(payload)
    code, data = fal_call(f"{QUEUE}/{eid}", method="POST", body=inp)
    if isinstance(data, dict):
        rid = data.get("request_id") or data.get("requestId")
        jid = f"fal|{eid}|{rid}" if rid else None
        data["id"] = jid
        data["backend"] = "fal"
        data["endpoint"] = eid
        data["submittedInput"] = inp
        if rid:
            _remember_job(rid, {
                "endpoint": eid,
                "status_url": data.get("status_url"),
                "response_url": data.get("response_url"),
                "cancel_url": data.get("cancel_url"),
                "submittedInput": inp,
                "prompt": payload.get("prompt"),
            })
            remember_studio_job(jid, {
                "backend": "fal",
                "serviceId": eid,
                "submittedInput": inp,
                "prompt": payload.get("prompt"),
                "negativePrompt": payload.get("negativePrompt"),
                "seed": payload.get("seed"),
                "jobId": jid,
                "cancel_url": data.get("cancel_url"),
                "status_url": data.get("status_url"),
                "response_url": data.get("response_url"),
            })
        # Some endpoints return the image on the queue POST itself.
        urls = collect_urls(data)
        if urls and jid:
            try:
                data["saved"] = save_media_urls(urls, jid, meta=job_meta(jid))
                if data.get("saved"):
                    data["status"] = "succeeded"
            except Exception as e:
                data["saveError"] = str(e)
    return code, data



UUID_RE = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")
SIZE_ENUM = {
    "square_hd": (1024, 1024),
    "square": (512, 512),
    "portrait_4_3": (768, 1024),
    "portrait_16_9": (576, 1024),
    "landscape_4_3": (1024, 768),
    "landscape_16_9": (1024, 576),
}


def platform_payloads(eid: str, rid: str):
    url = (
        f"{MODELS_API}/requests/by-endpoint"
        f"?endpoint_id={quote(eid or '', safe='')}&request_id={quote(rid or '')}&expand=payloads"
    )
    return fal_call(url, timeout=60)


def _save_fal(result, job_id):
    urls = collect_urls(result)
    meta = job_meta(job_id) or {}
    if not meta.get("serviceId") and "|" in (job_id or ""):
        parts = job_id.split("|", 2)
        if len(parts) == 3:
            meta.setdefault("backend", "fal")
            meta.setdefault("serviceId", parts[1])
            meta.setdefault("jobId", job_id)
    if not urls:
        return []
    return save_media_urls(urls, job_id, meta=meta)


def parse_fal_ref(q, endpoint=None):
    q = (q or "").strip()
    if q.startswith("fal|"):
        parts = q.split("|", 2)
        if len(parts) == 3:
            return parts[1].strip(), parts[2].strip()
    m = UUID_RE.search(q)
    rid = m.group(0) if m else None
    eid = (endpoint or "").strip()
    if m:
        rest = (q[:m.start()] + " " + q[m.end():]).strip()
        rest = re.sub(r"(endpoint_id|endpoint|request_id)\s*=", " ", rest, flags=re.I)
        rest = rest.strip(" /|?,&\t")
        if rest and "/" in rest:
            token = rest.split()[0].strip(" /|")
            if "/" in token:
                eid = token
    return (eid or None), rid


def map_fal_json_input(inp, endpoint_id):
    inp = inp or {}
    if not isinstance(inp, dict):
        inp = {}
    out = {
        "backend": "fal",
        "serviceId": endpoint_id,
        "prompt": inp.get("prompt") or "",
        "source": "fal-job",
        "empty": not bool(inp.get("prompt")),
    }
    if inp.get("negative_prompt"):
        out["negativePrompt"] = inp["negative_prompt"]
    if inp.get("num_inference_steps") not in (None, ""):
        try:
            out["steps"] = int(inp["num_inference_steps"])
        except (TypeError, ValueError):
            pass
    if inp.get("guidance_scale") not in (None, ""):
        try:
            out["cfgScale"] = float(inp["guidance_scale"])
        except (TypeError, ValueError):
            pass
    if inp.get("seed") not in (None, ""):
        try:
            out["seed"] = int(inp["seed"])
        except (TypeError, ValueError):
            pass
    sz = inp.get("image_size")
    if isinstance(sz, dict):
        try:
            if sz.get("width"):
                out["width"] = int(sz["width"])
            if sz.get("height"):
                out["height"] = int(sz["height"])
        except (TypeError, ValueError):
            pass
    elif isinstance(sz, str):
        if sz in SIZE_ENUM:
            out["width"], out["height"] = SIZE_ENUM[sz]
        elif "x" in sz.lower():
            try:
                a, b = sz.lower().split("x", 1)
                out["width"], out["height"] = int(a), int(b)
            except (TypeError, ValueError):
                pass
    img = inp.get("image_url")
    if isinstance(img, list) and img:
        img = img[0]
    if img:
        out["firstFrame"] = img
        out["sourceImage"] = img
    return out


def import_request(q, endpoint=None):
    eid, rid = parse_fal_ref(q, endpoint)
    if not rid:
        return 400, {"error": "请贴 Fal request id（uuid），或 fal|endpoint|uuid，或 endpoint + request_id"}
    if not eid:
        return 400, {"error": "还需要 Fal endpoint id（例如 fal-ai/flux/schnell），或整段 fal|endpoint|uuid"}
    code, data = platform_payloads(eid, rid)
    if not isinstance(data, dict):
        return code if code >= 400 else 502, {"error": "Fal 回放失败"}
    items = data.get("items") or data.get("requests") or []
    item = items[0] if items else data
    if code >= 400 or not isinstance(item, dict):
        if isinstance(data, dict):
            data.setdefault("error", data.get("message") or f"HTTP {code}")
        return code if code >= 400 else 404, data
    inp = item.get("json_input") or item.get("input") or {}
    mapped = map_fal_json_input(inp, eid)
    mapped["jobId"] = f"fal|{eid}|{rid}"
    mapped["submittedInput"] = inp
    if not mapped.get("prompt") and not inp:
        mapped["empty"] = True
        mapped["error"] = "Fal 没存下这次请求的 payload（可能开了 X-Fal-Store-IO 或已过期）。"
    return 200, mapped


def job_status(job_id: str):
    # fal|{endpoint}|{request_id}
    parts = job_id.split("|", 2)
    if len(parts) != 3:
        return 400, {"error": "无效 Fal 任务 id"}
    _, eid, rid = parts
    stored = job_meta(job_id) or {}
    meta = dict(stored)
    meta.update(_FAL_JOBS.get(rid) or {})
    code, data = _try_get(status_urls(eid, rid, meta))
    if not isinstance(data, dict):
        return 502, {"error": "Fal 状态响应无效", "id": job_id, "backend": "fal", "status": "failed"}
    # Queue GET may 405 after expiry; platform API still has the payload/result.
    if code in (404, 405) or (code >= 400 and not data.get("status")):
        pc, plat = platform_payloads(eid, rid)
        item = None
        if pc == 200 and isinstance(plat, dict):
            items = plat.get("items") or []
            item = items[0] if items else None
        if isinstance(item, dict):
            outp = item.get("json_output") or item.get("output") or {}
            saved = []
            try:
                saved = _save_fal(outp, job_id) if outp else []
            except Exception as e:
                saved = []
                plat_err = str(e)
            if saved:
                return 200, {
                    "id": job_id,
                    "backend": "fal",
                    "status": "succeeded",
                    "saved": saved,
                    "result": outp,
                    "wait": {"progress": 1, "precedingJobs": None, "etaSeconds": None, "completeAt": None, "log": None},
                }
        return 200, {
            "id": job_id,
            "backend": "fal",
            "status": "processing" if code in (404, 405) else "failed",
            "error": data.get("error") or f"Fal 状态 HTTP {code}",
            "wait": {"progress": None, "precedingJobs": None, "etaSeconds": None, "completeAt": None, "log": None},
        }
    st = (data.get("status") or "").upper()
    mapped = {
        "IN_QUEUE": "pending",
        "IN_PROGRESS": "processing",
        "COMPLETED": "succeeded",
        "FAILED": "failed",
        "CANCELLED": "canceled",
        "CANCELED": "canceled",
    }
    data["status"] = mapped.get(st, (data.get("status") or "pending").lower())
    data["backend"] = "fal"
    data["id"] = job_id
    logs = data.get("logs") or []
    last = None
    log_blob = ""
    if logs:
        parts = []
        for msg in logs:
            if isinstance(msg, dict):
                parts.append(str(msg.get("message") or msg.get("error") or ""))
            else:
                parts.append(str(msg))
        last = parts[-1] if parts else None
        log_blob = " ".join(parts)
    extra_err = data.get("error") or data.get("detail") or data.get("message") or ""
    log_blob = f"{log_blob} {extra_err} {json.dumps(data, default=str)[:1200]}"
    ahead = data.get("queue_position") if st == "IN_QUEUE" else None
    data["wait"] = {
        "progress": None,
        "precedingJobs": ahead,
        "etaSeconds": None,
        "completeAt": None,
        "log": last,
    }
    if data["status"] not in ("succeeded", "canceled", "cancelled") and (
        code == 422 or " 422" in log_blob or "HTTP 422" in log_blob or '"status": 422' in log_blob
        or "Unprocessable" in log_blob
    ):
        data["status"] = "failed"
        data["error"] = data.get("error") or last or "Fal 422：请求不被接受（字段/模型不匹配）"
    if data["status"] == "succeeded":
        rc, result = _try_get(result_urls(eid, rid, meta, data), need_media=True)
        if rc in (404, 405) or not (rc == 200 and isinstance(result, dict) and collect_urls(result)):
            pc, plat = platform_payloads(eid, rid)
            if pc == 200 and isinstance(plat, dict):
                items = plat.get("items") or []
                item = items[0] if items else None
                if isinstance(item, dict) and (item.get("json_output") or item.get("output")):
                    result = item.get("json_output") or item.get("output")
                    rc = 200
        if rc == 200 and isinstance(result, dict) and collect_urls(result):
            data["result"] = {k: result[k] for k in result if k != "raw"}
            try:
                data["saved"] = _save_fal(result, job_id)
            except Exception as e:
                data["saveError"] = str(e)
        if not data.get("saved"):
            # COMPLETED on the queue is not "got the file". Keep polling.
            data["status"] = "processing"
            data["wait"] = data.get("wait") or {}
            data["wait"]["log"] = data.get("saveError") or "Fal 已完成，正在取媒体 URL"
            data.pop("saveError", None)
    # Always 200 so the browser poll does not throw on provider 405 leftovers.
    return 200, data



from urllib.parse import quote as _quote


def _alnum(s):
    return "".join(ch for ch in (s or "").lower() if ch.isalnum())


def fal_recipe(eid, fcat, name):
    blob = f"{eid} {fcat} {name}".lower()
    if "upscale" in blob:
        return "upscale", "upscale"
    if "background" in blob:
        return "bg", "bg"
    if "audio" in fcat or "speech" in fcat:
        return "audio", "audio"
    if "3d" in fcat or ("/3d" in blob and "video" not in fcat):
        return "3d", "3d"
    if "video" in fcat:
        return "video", "videoGen"
    return "image", "imageGen"


def row_from_fal_api(it):
    md = it.get("metadata") or {}
    eid = (it.get("endpoint_id") or it.get("id") or "").strip()
    local = find_model(eid)
    if local:
        return overlay_image_fields(local)
    name = md.get("display_name") or eid
    fcat = md.get("category") or ""
    recipe, step = fal_recipe(eid, fcat, name)
    fields = infer_image_fields(eid)
    st = md.get("status") or "active"
    return overlay_image_fields({
        "id": eid,
        "name": name,
        "description": (md.get("description") or "").strip(),
        "category": recipe,
        "falCategory": fcat,
        "status": "available" if st == "active" else st,
        "step": step,
        "backend": "fal",
        "tags": md.get("tags") or [],
        "needsSource": recipe in ("image", "bg", "upscale", "3d") and (
            fcat in ("image-to-image", "image-to-3d") or "/edit" in eid
        ),
        "needsFirstFrame": "image-to-video" in fcat or "image-to-video" in eid or "first-last" in eid,
        "imageFields": fields,
        "promptField": "prompt",
    })


def search_loras(q: str, limit: int = 8):
    """Fal LoRA `path` is a download URL or HF owner/repo. Search HF Hub filter=lora."""
    from . import huggingface as hf
    code, payload = hf.search_loras(q, limit=limit)
    items = []
    for it in payload.get("items") or []:
        row = dict(it)
        row["source"] = "fal"
        items.append(row)
    return code, {"items": items, "backend": "fal"}


def search_fal(q):
    q = (q or "").strip()
    if not q:
        return []
    url = f"{MODELS_API}?q={_quote(q)}&limit=50"
    key = fal_key()
    headers = {"Authorization": f"Key {key}"} if key else None
    code, data = json_call(url, headers=headers, timeout=25)
    models = data.get("models") if isinstance(data, dict) else None
    if code != 200 or not isinstance(models, list):
        return []
    out, seen = [], set()
    for it in models:
        if not isinstance(it, dict):
            continue
        row = row_from_fal_api(it)
        eid = row.get("id")
        if not eid or eid in seen:
            continue
        seen.add(eid)
        out.append(row)
    return out


class FalProvider(Provider):
    id = "fal"
    label = "Fal"

    def has_key(self) -> bool:
        return has_key()

    def categories(self) -> list:
        return sorted({x.get("category") for x in load_catalog() if x.get("category")})

    def catalog(self, q, category, status) -> dict:
        qn = (q or "").strip()
        items = [overlay_image_fields(x) for x in load_catalog()]
        unfiltered = len(items)
        # Keep the full local catalog. Live search only ADDS extra ids.
        # UI filters leftover text client-side; sending q must not collapse ~1492 to 1.
        if qn:
            live = search_fal(qn)
            by = {x.get("id"): x for x in items if x.get("id")}
            for x in live:
                eid = x.get("id")
                if eid and eid not in by:
                    items.append(x)
                    by[eid] = x
        if category:
            items = [x for x in items if x.get("category") == category]
        if status:
            items = [x for x in items if x.get("status") == status]
        return {
            "total": unfiltered,
            "count": len(items),
            "backend": "fal",
            "items": items,
            "hasFal": has_key(),
            "hasKey": has_key(),
            "unfilteredTotal": unfiltered,
        }

    def owns_service(self, service_id: str) -> bool:
        sid = (service_id or "").strip().lstrip("/")
        if not sid:
            return False
        if find_model(sid):
            return True
        if "/" in sid and sid.startswith(FAL_PREFIXES):
            return True
        return False

    def owns_job(self, job_id: str) -> bool:
        pid, _ = parse_job_id(job_id)
        return pid == self.id or (job_id or "").startswith("fal|")

    def search_loras(self, q: str, nsfw: bool = True):
        return search_loras(q)

    def generate(self, payload: dict):
        return submit(payload)

    def whatif(self, payload: dict):
        return 200, {
            "backend": "fal",
            "cost": {"total": None, "note": "Fal 按次计费，无黄 Buzz 预估"},
            "service": {"serviceId": (payload or {}).get("serviceId")},
        }

    def job_status(self, job_id: str):
        return job_status(job_id)

    def cancel_job(self, job_id: str):
        parts = (job_id or "").split("|", 2)
        if len(parts) != 3:
            return 400, {"error": "无效 Fal 任务 id"}
        _, eid, rid = parts
        stored = job_meta(job_id) or {}
        meta = dict(stored)
        meta.update(_FAL_JOBS.get(rid) or {})
        last_code, last_data = 400, {"error": "Fal 取消失败"}
        for url in cancel_urls(eid, rid, meta):
            code, data = fal_call(url, method="PUT")
            last_code, last_data = code, data if isinstance(data, dict) else {"error": str(data)}
            if code in (200, 202):
                st = ""
                if isinstance(data, dict):
                    st = str(data.get("status") or "")
                return 200, {
                    "id": job_id,
                    "backend": "fal",
                    "status": "canceled" if st.upper() in ("CANCELLATION_REQUESTED", "CANCELLED", "CANCELED") else "canceled",
                    "vendorStatus": st or "CANCELLATION_REQUESTED",
                }
            if code == 400:
                msg = ""
                if isinstance(data, dict):
                    msg = str(data.get("status") or data.get("error") or "")
                if "ALREADY_COMPLETED" in msg.upper() or "already" in msg.lower():
                    return 400, {"error": "Fal 任务已经开始或完成，取消不了", "vendorStatus": msg}
            if code in (404, 405):
                continue
        if isinstance(last_data, dict):
            last_data.setdefault("error", last_data.get("message") or f"Fal 取消 HTTP {last_code}")
        return last_code if last_code >= 400 else 400, last_data if isinstance(last_data, dict) else {"error": str(last_data)}


from . import register  # noqa: E402

register(FalProvider())
