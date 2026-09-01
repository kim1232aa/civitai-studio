from __future__ import annotations

import json
import os
import time
import uuid
from pathlib import Path
from urllib.parse import quote

from .base import Provider
from .http import collect_urls, extract_error, json_call, parse_job_id, save_bytes, save_media_urls
from .io_meta import looks_like_civitai_service

TOKEN_PATH = Path.home() / ".config/nano-gpt/token"
ROOT = Path(__file__).resolve().parent.parent
BASE = "https://nano-gpt.com"
API = BASE + "/api/v1"
IMG_MODELS = API + "/images/models"
VID_MODELS = API + "/video-models"
GEN_IMAGES = API + "/images"
GEN_IMAGES_OAI = BASE + "/v1/images/generations"
GEN_VIDEO = BASE + "/api/generate-video"
VIDEO_STATUS = BASE + "/api/video/status"

_CACHE = {"at": 0.0, "items": None}
_TTL = 300

_ASPECTS = (
    (1, 1, "1:1"),
    (4, 3, "4:3"),
    (3, 4, "3:4"),
    (3, 2, "3:2"),
    (2, 3, "2:3"),
    (16, 9, "16:9"),
    (9, 16, "9:16"),
    (2, 1, "2:1"),
    (1, 2, "1:2"),
    (4, 5, "4:5"),
    (5, 4, "5:4"),
    (21, 9, "21:9"),
    (235, 100, "2.35:1"),
)
_FAL_SIZE = {
    "1:1": "square_hd",
    "4:3": "landscape_4_3",
    "3:4": "portrait_4_3",
    "16:9": "landscape_16_9",
    "9:16": "portrait_16_9",
}


def nano_key() -> str:
    try:
        t = TOKEN_PATH.read_text().strip()
        if t:
            return t
    except Exception:
        pass
    return (os.environ.get("NANO_GPT_API_KEY") or os.environ.get("NANOGPT_API_KEY") or "").strip()


def _auth():
    key = nano_key()
    if not key:
        return {}
    return {"Authorization": "Bearer " + key, "x-api-key": key}


def _alnum(s):
    return "".join(ch for ch in (s or "").lower() if ch.isalnum())


def _clamp_seed(raw):
    if raw in (None, "", "random"):
        return None
    try:
        n = int(raw)
    except (TypeError, ValueError):
        return None
    if n < -1:
        return -1
    limit = 2147483647
    if n > limit:
        n = n % limit or limit
    return n


def closest_aspect(w, h) -> str:
    try:
        w = int(w)
        h = int(h)
    except (TypeError, ValueError):
        return "1:1"
    if w <= 0 or h <= 0:
        return "1:1"
    r = w / h
    best, best_d = "1:1", 99.0
    for a, b, name in _ASPECTS:
        d = abs(r - (a / b))
        if d < best_d:
            best, best_d = name, d
    return best


def pick_resolution(spec, w=None, h=None):
    """Pick a catalog resolution token the model actually lists."""
    sp = (spec or {}).get("supported_parameters") or {}
    res = [str(x) for x in (sp.get("resolutions") or []) if x not in (None, "")]
    if not res:
        try:
            if w and h:
                return f"{int(w)}x{int(h)}"
        except (TypeError, ValueError):
            pass
        return None

    def norm(s):
        return str(s).lower().replace("×", "x").replace("*", "x").replace(" ", "")

    low = {norm(x): x for x in res}
    try:
        wi = int(w) if w not in (None, "") else 0
        hi = int(h) if h not in (None, "") else 0
    except (TypeError, ValueError):
        wi = hi = 0
    if wi and hi:
        hit = low.get(f"{wi}x{hi}")
        if hit:
            return hit
    if "1k" in low or "2k" in low:
        mx = max(wi, hi)
        if mx >= 1536 and "2k" in low:
            return low["2k"]
        if "1k" in low:
            return low["1k"]
    ar = closest_aspect(wi or 1024, hi or 1024)
    if ar.lower() in low:
        return low[ar.lower()]
    token = _FAL_SIZE.get(ar)
    if token and token.lower() in low:
        return low[token.lower()]
    parsed = []
    for r in res:
        n = norm(r)
        if "x" not in n:
            continue
        a, _, b = n.partition("x")
        try:
            pw, ph = int(a), int(b)
        except ValueError:
            continue
        if pw > 0 and ph > 0:
            parsed.append((pw, ph, r))
    if parsed and wi and hi:
        def score(t):
            pw, ph, _ = t
            aspect_d = abs((pw / ph) - (wi / hi))
            area_d = abs(pw * ph - wi * hi) / max(wi * hi, 1)
            return (aspect_d, area_d)

        parsed.sort(key=score)
        return parsed[0][2]
    if wi and hi and wi == hi:
        for t in ("square_hd", "square", "1024x1024", "1:1"):
            if t in low:
                return low[t]
    if "auto" in low:
        return low["auto"]
    if parsed:
        parsed.sort(key=lambda t: -(t[0] * t[1]))
        return parsed[0][2]
    return res[0]


def _loras(payload: dict) -> list:
    out = []
    raw = (payload or {}).get("loras") or []
    if isinstance(raw, dict):
        raw = [raw]
    for it in raw if isinstance(raw, list) else []:
        if isinstance(it, str):
            path = it.strip()
            scale = 1.0
            name = path
        elif isinstance(it, dict):
            path = (it.get("path") or it.get("downloadUrl") or it.get("url") or it.get("air") or "").strip()
            name = it.get("name") or path
            try:
                raw_s = it.get("scale")
                if raw_s is None:
                    raw_s = it.get("strength")
                scale = float(raw_s) if raw_s not in (None, "") else 1.0
            except (TypeError, ValueError):
                scale = 1.0
            if (not path or path.lower().startswith("urn:")) and str(it.get("versionId") or "").isdigit():
                path = "https://civitai.com/api/download/models/" + str(it.get("versionId"))
        else:
            continue
        if not path or path.lower().startswith("urn:"):
            continue
        out.append({"path": path, "scale": max(0.0, min(4.0, scale)), "name": name})
        if len(out) >= 3:
            break
    return out


def _source_images(payload: dict) -> list:
    seen, out = set(), []

    def add(u):
        s = (u or "").strip()
        if not s or s in seen:
            return
        if not (s.startswith("http") or s.startswith("data:image")):
            return
        seen.add(s)
        out.append(s)

    add((payload or {}).get("sourceImage"))
    add((payload or {}).get("firstFrame"))
    add((payload or {}).get("image_url"))
    add((payload or {}).get("imageUrl"))
    add((payload or {}).get("imageDataUrl"))
    for u in (payload or {}).get("images") or []:
        add(u)
    return out


def _row_image(it: dict) -> dict:
    mid = (it.get("id") or "").strip()
    name = (it.get("name") or mid.split("/")[-1] or mid).strip()
    caps = it.get("capabilities") or {}
    tags = [str(t).lower() for t in (it.get("tags") or []) if t]
    blob = (mid + " " + name + " " + " ".join(tags)).lower()
    cat = "image"
    if any(x in blob for x in ("upscale", "upscaler")):
        cat = "upscale"
    elif "background" in blob or "bg-removal" in blob or "bg removal" in blob:
        cat = "bg"
    elif "3d" in blob or "3-d" in blob:
        cat = "3d"
    i2i = bool(caps.get("image_to_image") or caps.get("inpainting"))
    t2i = bool(caps.get("image_generation", True))
    lora = ("lora" in blob) or any("lora" in t for t in tags)
    row = {
        "id": mid,
        "name": name,
        "category": cat,
        "backend": "nano-gpt",
        "status": "available",
        "task": "image-to-image" if (i2i and not t2i) else "text-to-image",
        "tags": tags or (["lora"] if lora else []),
        "supportsLora": lora,
        "pricing": it.get("pricing") or {},
        "supported_parameters": it.get("supported_parameters") or {},
        "capabilities": caps,
        "description": it.get("description") or "",
    }
    if i2i and not t2i:
        row["needsSource"] = True
    if lora:
        row["supportsLora"] = True
        if "lora" not in row["tags"]:
            row["tags"] = list(row["tags"]) + ["lora"]
    return row


def _row_video(it: dict) -> dict:
    mid = (it.get("id") or "").strip()
    name = (it.get("name") or mid.split("/")[-1] or mid).strip()
    caps = it.get("capabilities") or {}
    tags = [str(t).lower() for t in (it.get("tags") or []) if t]
    blob = (mid + " " + name).lower()
    i2v = bool(caps.get("image_to_video"))
    t2v = bool(caps.get("text_to_video") or caps.get("video_generation", True))
    row = {
        "id": mid,
        "name": name,
        "category": "video",
        "backend": "nano-gpt",
        "status": "available",
        "task": "image-to-video" if (i2v and not t2v) else "text-to-video",
        "tags": tags,
        "pricing": it.get("pricing") or {},
        "supported_parameters": it.get("supported_parameters") or {},
        "capabilities": caps,
        "description": it.get("description") or "",
    }
    if i2v and not t2v:
        row["needsFirstFrame"] = True
    if "upscale" in blob:
        row["category"] = "upscale"
    return row


def fetch_catalog(force=False) -> list:
    now = time.time()
    if not force and _CACHE.get("items") is not None and (now - (_CACHE.get("at") or 0)) < _TTL:
        return list(_CACHE["items"])
    items, seen = [], set()
    headers = {"Accept": "application/json"}
    headers.update(_auth())
    code, data = json_call(IMG_MODELS, headers=headers, timeout=30)
    block = (data or {}).get("data") if isinstance(data, dict) else None
    if code == 200 and isinstance(block, list):
        for it in block:
            if not isinstance(it, dict) or not it.get("id"):
                continue
            row = _row_image(it)
            if row["id"] in seen:
                continue
            seen.add(row["id"])
            items.append(row)
    code, data = json_call(VID_MODELS, headers=headers, timeout=30)
    block = (data or {}).get("data") if isinstance(data, dict) else None
    if code == 200 and isinstance(block, list):
        for it in block:
            if not isinstance(it, dict) or not it.get("id"):
                continue
            row = _row_video(it)
            if row["id"] in seen:
                continue
            seen.add(row["id"])
            items.append(row)
    _CACHE["items"] = items
    _CACHE["at"] = now
    return list(items)


def find_spec(mid: str) -> dict:
    mid = (mid or "").strip()
    for it in fetch_catalog():
        if it.get("id") == mid:
            return it
    return {"id": mid, "supported_parameters": {}, "capabilities": {}}


def model_id(service_id: str) -> str:
    s = (service_id or "").strip().lstrip("/")
    for pfx in ("nano-gpt/", "nanogpt/", "nano/"):
        if s.lower().startswith(pfx):
            s = s[len(pfx):]
    return s


def _image_body(payload: dict, spec: dict) -> dict:
    w = payload.get("width")
    h = payload.get("height")
    try:
        n = int(payload.get("quantity") or payload.get("n") or 1)
    except (TypeError, ValueError):
        n = 1
    n = max(1, min(4, n))
    body = {
        "model": model_id(payload.get("serviceId") or spec.get("id") or ""),
        "prompt": payload.get("prompt") or "",
        "n": n,
        "nImages": n,
        "response_format": "url",
    }
    neg = (payload.get("negativePrompt") or "").strip()
    if neg:
        body["negative_prompt"] = neg
        body["negativePrompt"] = neg
    res = pick_resolution(spec, w, h)
    if res:
        body["resolution"] = res
        body["size"] = res
    ar = closest_aspect(w or 1024, h or 1024)
    if ar:
        body["aspect_ratio"] = ar
    try:
        if w:
            body["width"] = int(w)
        if h:
            body["height"] = int(h)
    except (TypeError, ValueError):
        pass
    seed = _clamp_seed(payload.get("seed"))
    if seed is not None:
        body["seed"] = seed
    imgs = _source_images(payload)
    if imgs:
        # NanoGPT rejects mixing input_references with image / imageDataUrl / image_url.
        body["input_references"] = imgs
        denoise = payload.get("denoise")
        if denoise in (None, ""):
            denoise = payload.get("strength")
        try:
            body["strength"] = float(denoise) if denoise not in (None, "") else 0.65
        except (TypeError, ValueError):
            body["strength"] = 0.65
    steps = payload.get("steps")
    try:
        if steps:
            body["num_inference_steps"] = int(steps)
            body["steps"] = int(steps)
    except (TypeError, ValueError):
        pass
    cfg = payload.get("cfgScale")
    try:
        if cfg not in (None, ""):
            body["guidance_scale"] = float(cfg)
    except (TypeError, ValueError):
        pass
    loras = _loras(payload)
    if loras:
        body["loras"] = [{"path": x["path"], "scale": x["scale"]} for x in loras]
        for i, item in enumerate(loras, 1):
            body[f"lora_{i}_url"] = item["path"]
            body[f"lora_{i}_scale"] = item["scale"]
    if payload.get("allowMatureContent"):
        body["enable_safety_checker"] = False
    return body


def _core_image_body(full: dict) -> dict:
    keep = (
        "model", "prompt", "n", "nImages", "resolution", "size", "aspect_ratio",
        "seed", "negative_prompt", "input_references", "imageDataUrl", "imageUrl",
        "image", "strength", "loras", "guidance_scale", "num_inference_steps",
        "response_format", "width", "height",
    )
    return {k: full[k] for k in keep if k in full}


def _save_result(data, jid, meta) -> list:
    saved = []
    if isinstance(data, dict):
        for i, item in enumerate(data.get("data") or []):
            if not isinstance(item, dict):
                continue
            stem = jid if i == 0 else f"{jid}_{i}"
            if item.get("b64_json"):
                import base64
                try:
                    raw = base64.b64decode(item["b64_json"])
                except Exception:
                    continue
                saved.extend(save_bytes(raw, stem, meta=meta if i == 0 else None))
            elif item.get("url"):
                saved.extend(save_media_urls([item["url"]], stem, meta=meta if i == 0 else None))
        if not saved:
            urls = collect_urls(data)
            if urls:
                saved = save_media_urls(urls, jid, meta=meta)
    return saved


def _video_body(payload: dict, spec: dict) -> dict:
    mid = model_id(payload.get("serviceId") or spec.get("id") or "")
    body = {"model": mid, "prompt": payload.get("prompt") or ""}
    neg = (payload.get("negativePrompt") or "").strip()
    if neg:
        body["negative_prompt"] = neg
    dur = payload.get("duration")
    if dur not in (None, ""):
        body["duration"] = str(int(dur) if str(dur).isdigit() else dur)
    w, h = payload.get("width"), payload.get("height")
    ar = closest_aspect(w or 1280, h or 720)
    body["aspect_ratio"] = ar
    res = pick_resolution(spec, w, h)
    if res:
        body["resolution"] = res
        body["size"] = res
    seed = _clamp_seed(payload.get("seed"))
    if seed is not None:
        body["seed"] = seed
    imgs = _source_images(payload)
    ff = (payload or {}).get("firstFrame") or (imgs[0] if imgs else "")
    if ff:
        if str(ff).startswith("data:"):
            body["imageDataUrl"] = ff
        else:
            body["imageUrl"] = ff
            body["image_url"] = ff
        body["mode"] = "image-to-video"
    else:
        body["mode"] = "text-to-video"
    last = (payload or {}).get("lastFrame")
    if last:
        body["lastFrame"] = last
    return body


class NanoGptProvider(Provider):
    id = "nano-gpt"
    label = "NanoGPT"

    def has_key(self) -> bool:
        return bool(nano_key())

    def categories(self) -> list:
        return sorted({x.get("category") for x in fetch_catalog() if x.get("category")})

    def catalog(self, q, category, status) -> dict:
        items = fetch_catalog()
        qn = _alnum(q)
        if qn:
            items = [x for x in items if qn in _alnum((x.get("name") or "") + " " + (x.get("id") or "") + " " + " ".join(x.get("tags") or []))]
        if category:
            items = [x for x in items if x.get("category") == category]
        if status:
            items = [x for x in items if x.get("status") == status]
        return {
            "total": len(items),
            "count": len(items),
            "backend": self.id,
            "items": items,
            "hasKey": self.has_key(),
        }

    def owns_service(self, service_id: str) -> bool:
        sid = (service_id or "").strip()
        if not sid:
            return False
        if sid.startswith(("nano-gpt/", "nanogpt/", "nano/")):
            return True
        ids = {x.get("id") for x in fetch_catalog()}
        return sid in ids

    def owns_job(self, job_id: str) -> bool:
        pid, _ = parse_job_id(job_id)
        return pid in ("nano-gpt", "nanogpt", "nano") or (job_id or "").startswith("nano-gpt|")

    def whatif(self, payload: dict):
        mid = model_id((payload or {}).get("serviceId") or "")
        spec = find_spec(mid)
        pricing = (spec.get("pricing") or {}).get("per_image") or {}
        res = pick_resolution(spec, payload.get("width"), payload.get("height"))
        price = None
        if isinstance(pricing, dict) and pricing:
            key = res if res in pricing else ("auto" if "auto" in pricing else next(iter(pricing)))
            try:
                price = float(pricing[key])
            except (TypeError, ValueError, KeyError):
                price = None
        try:
            n = max(1, int(payload.get("quantity") or 1))
        except (TypeError, ValueError):
            n = 1
        note = "NanoGPT 按次美元计费，无黄 Buzz"
        if price is not None:
            note = f"约 ${price * n:.4f} USD · {note}"
        return 200, {
            "backend": self.id,
            "cost": {"total": None, "usd": price, "note": note},
            "service": {"serviceId": mid, "resolution": res},
        }

    def generate(self, payload: dict):
        key = nano_key()
        if not key:
            return 401, {"error": "没有 NanoGPT API Key"}
        sid = (payload or {}).get("serviceId") or ""
        if looks_like_civitai_service(sid):
            return 400, {"error": "当前选中的是 Civitai 服务，不能发给 NanoGPT。请选 Krea 2 Turbo LoRA 等。"}
        mid = model_id(sid)
        if not mid:
            return 400, {"error": "缺少 NanoGPT 模型 id"}
        spec = find_spec(mid)
        cat = (spec.get("category") or payload.get("kind") or payload.get("recipe") or "image").lower()
        if cat == "video" or (spec.get("task") or "").find("video") >= 0:
            return self._generate_video(payload, spec, mid)
        return self._generate_image(payload, spec, mid)

    def _generate_image(self, payload, spec, mid):
        full = _image_body(payload or {}, spec)
        jid = f"nano-gpt|img|{uuid.uuid4().hex[:12]}"
        meta = {
            "backend": self.id,
            "serviceId": mid,
            "prompt": (payload or {}).get("prompt"),
            "negativePrompt": (payload or {}).get("negativePrompt"),
            "seed": full.get("seed"),
            "jobId": jid,
            "submittedInput": full,
        }
        headers = _auth()
        last = (502, {"error": "NanoGPT 出图失败"})
        for url, body in (
            (GEN_IMAGES, full),
            (GEN_IMAGES_OAI, _core_image_body(full)),
        ):
            code, data = json_call(url, method="POST", headers=headers, body=body, timeout=180)
            if not isinstance(data, dict):
                last = (code if code >= 400 else 502, {"error": str(data)})
                continue
            if code >= 400:
                data.setdefault("error", extract_error(data, f"HTTP {code}"))
                last = (code, data)
                continue
            saved = _save_result(data, jid, meta)
            if saved:
                return 200, {
                    "id": jid,
                    "status": "succeeded",
                    "backend": self.id,
                    "endpoint": mid,
                    "saved": saved,
                    "submittedInput": body,
                    "cost": data.get("cost"),
                }
            last = (502, {"error": "NanoGPT 没有返回图片", "raw": json.dumps(data)[:400]})
        return last

    def _generate_video(self, payload, spec, mid):
        body = _video_body(payload or {}, spec)
        code, data = json_call(GEN_VIDEO, method="POST", headers=_auth(), body=body, timeout=90)
        if not isinstance(data, dict) or code >= 400:
            if isinstance(data, dict):
                data.setdefault("error", extract_error(data, f"HTTP {code}"))
                return code if code >= 400 else 502, data
            return code if code >= 400 else 502, {"error": str(data)}
        run = data.get("runId") or data.get("id") or data.get("requestId") or ""
        if not run:
            saved = _save_result(data, f"nano-gpt|vid|{uuid.uuid4().hex[:12]}", {"backend": self.id, "serviceId": mid})
            if saved:
                jid = f"nano-gpt|vid|{uuid.uuid4().hex[:12]}"
                return 200, {"id": jid, "status": "succeeded", "backend": self.id, "saved": saved, "submittedInput": body}
            return 502, {"error": "NanoGPT 视频没返回任务 id", "raw": json.dumps(data)[:400]}
        jid = f"nano-gpt|vid|{run}"
        return 200, {
            "id": jid,
            "status": (data.get("status") or "pending").lower(),
            "backend": self.id,
            "endpoint": mid,
            "submittedInput": body,
            "wait": {"progress": None, "precedingJobs": None, "etaSeconds": None, "completeAt": None, "log": None},
        }

    def job_status(self, job_id: str):
        pid, rest = parse_job_id(job_id)
        kind, _, opaque = rest.partition("|")
        if kind == "img" or rest.startswith("img|"):
            return 200, {
                "id": job_id,
                "status": "succeeded",
                "backend": self.id,
                "wait": {"progress": 1, "precedingJobs": None, "etaSeconds": None, "completeAt": None, "log": None},
            }
        run = opaque or rest
        if run.startswith("vid|"):
            run = run.split("|", 1)[-1]
        url = VIDEO_STATUS + "?requestId=" + quote(run, safe="")
        code, data = json_call(url, headers=_auth(), timeout=30)
        if not isinstance(data, dict):
            return 502, {"error": "NanoGPT 状态无效", "id": job_id, "backend": self.id, "status": "failed"}
        st = (data.get("status") or data.get("state") or "").lower()
        mapped = {
            "pending": "pending",
            "queued": "pending",
            "processing": "processing",
            "running": "processing",
            "in_progress": "processing",
            "succeeded": "succeeded",
            "completed": "succeeded",
            "complete": "succeeded",
            "success": "succeeded",
            "failed": "failed",
            "error": "failed",
            "canceled": "canceled",
            "cancelled": "canceled",
        }.get(st, st or "pending")
        out = {
            "id": job_id,
            "backend": self.id,
            "status": mapped,
            "wait": {
                "progress": data.get("progress"),
                "precedingJobs": None,
                "etaSeconds": data.get("etaSeconds") or data.get("eta"),
                "completeAt": None,
                "log": (data.get("message") or data.get("error") or "")[:120] or None,
            },
        }
        if mapped == "succeeded":
            saved = _save_result(data, job_id, {"backend": self.id, "jobId": job_id})
            if saved:
                out["saved"] = saved
            else:
                out["status"] = "failed"
                out["error"] = "成功但没拿到文件"
        if mapped == "failed":
            out["error"] = extract_error(data, data.get("error") or "NanoGPT 视频失败")
        if code >= 400 and mapped not in ("succeeded", "failed"):
            out["status"] = "failed"
            out["error"] = extract_error(data, f"HTTP {code}")
        return 200, out


from . import register  # noqa: E402

register(NanoGptProvider())
