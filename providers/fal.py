from __future__ import annotations

import json
from pathlib import Path

from .base import Provider
from .http import collect_urls, json_call, parse_job_id, save_media_urls

TOKEN_PATH = Path.home() / ".config/fal/token"
ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
QUEUE = "https://queue.fal.run"
MODELS_API = "https://api.fal.ai/v1/models"

# Endpoint ids that are Fal even when not yet in the local catalog.
FAL_PREFIXES = (
    "fal-ai/",
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


def overlay_image_fields(item: dict) -> dict:
    """Keep catalog imageFields; fill from infer_image_fields when missing."""
    out = dict(item)
    out.setdefault("backend", "fal")
    fields = out.get("imageFields") or infer_image_fields(out.get("id") or "")
    if fields:
        out["imageFields"] = fields
    return out


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
    if not ar_field and "ratio" in list(spec.get("optional") or []) + list(spec.get("required") or []):
        ar_field = "ratio"
    if ar_field and payload.get("aspectRatio"):
        inp[ar_field] = payload["aspectRatio"]
    elif payload.get("aspectRatio") and "kontext" in eid:
        inp["aspect_ratio"] = payload["aspectRatio"]
    if payload.get("width") and payload.get("height") and spec.get("optional") and "image_size" in (spec.get("optional") or []):
        inp["image_size"] = {"width": int(payload["width"]), "height": int(payload["height"])}
    return {k: v for k, v in inp.items() if v not in (None, "", [])}


def submit(payload: dict):
    eid = (payload.get("serviceId") or payload.get("endpoint") or "").strip().lstrip("/")
    if not eid:
        return 400, {"error": "缺少 Fal 模型 id"}
    inp = build_fal_input(payload)
    code, data = fal_call(f"{QUEUE}/{eid}", method="POST", body=inp)
    if isinstance(data, dict):
        rid = data.get("request_id") or data.get("requestId")
        data["id"] = f"fal|{eid}|{rid}" if rid else None
        data["backend"] = "fal"
        data["endpoint"] = eid
        data["submittedInput"] = inp
    return code, data


def job_status(job_id: str):
    # fal|{endpoint}|{request_id}
    parts = job_id.split("|", 2)
    if len(parts) != 3:
        return 400, {"error": "无效 Fal 任务 id"}
    _, eid, rid = parts
    code, data = fal_call(f"{QUEUE}/{eid}/requests/{rid}/status?logs=1")
    if not isinstance(data, dict):
        return code, data
    st = (data.get("status") or "").upper()
    mapped = {
        "IN_QUEUE": "pending",
        "IN_PROGRESS": "processing",
        "COMPLETED": "succeeded",
        "FAILED": "failed",
        "CANCELLED": "canceled",
    }
    data["status"] = mapped.get(st, (data.get("status") or "pending").lower())
    data["backend"] = "fal"
    data["id"] = job_id
    logs = data.get("logs") or []
    last = None
    if logs:
        msg = logs[-1]
        last = msg.get("message") if isinstance(msg, dict) else str(msg)
    ahead = data.get("queue_position") if st == "IN_QUEUE" else None
    data["wait"] = {
        "progress": None,
        "precedingJobs": ahead,
        "etaSeconds": None,
        "completeAt": None,
        "log": last,
    }
    if data["status"] == "succeeded":
        rc, result = fal_call(f"{QUEUE}/{eid}/requests/{rid}")
        if rc == 200 and isinstance(result, dict):
            data["result"] = result
            urls = collect_urls(result)
            try:
                data["saved"] = save_media_urls(urls, job_id)
            except Exception as e:
                data["saveError"] = str(e)
    return code, data


class FalProvider(Provider):
    id = "fal"
    label = "Fal"

    def has_key(self) -> bool:
        return has_key()

    def categories(self) -> list:
        return sorted({x.get("category") for x in load_catalog() if x.get("category")})

    def catalog(self, q, category, status) -> dict:
        q = (q or "").lower()
        items = [overlay_image_fields(x) for x in load_catalog()]
        if category:
            items = [x for x in items if x.get("category") == category]
        if status:
            items = [x for x in items if x.get("status") == status]
        if q:
            items = [
                x for x in items
                if q in (x.get("name") or "").lower() or q in (x.get("id") or "").lower()
            ]
        return {
            "total": len(items),
            "count": len(items),
            "backend": "fal",
            "items": items,
            "hasFal": has_key(),
            "hasKey": has_key(),
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


from . import register  # noqa: E402

register(FalProvider())
