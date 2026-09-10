from __future__ import annotations

import json
import math
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


def _strict_int(raw, field: str) -> int:
    if isinstance(raw, bool) or raw in (None, ""):
        raise ValueError(f"{field} 必须是整数，收到 {raw!r}")
    try:
        value = int(raw)
        if not isinstance(raw, str) and value != raw:
            raise ValueError()
    except (TypeError, ValueError, OverflowError):
        raise ValueError(f"{field} 必须是整数，收到 {raw!r}") from None
    return value


def _strict_float(raw, field: str) -> float:
    if isinstance(raw, bool) or raw in (None, ""):
        raise ValueError(f"{field} 必须是有限数值，收到 {raw!r}")
    try:
        value = float(raw)
        if not math.isfinite(value):
            raise ValueError()
    except (TypeError, ValueError, OverflowError):
        raise ValueError(f"{field} 必须是有限数值，收到 {raw!r}") from None
    return value


def _schema_keys(spec: dict) -> list[str]:
    return [str(x) for x in list((spec or {}).get("required") or []) + list((spec or {}).get("optional") or [])]


def _is_imagen4_unverified(eid: str) -> bool:
    """fal-ai/imagen4/preview* OpenAPI 404. Do not invent fields."""
    return "imagen4" in (eid or "").lower()


def _unschematized(spec: dict) -> bool:
    eid = (spec or {}).get("id") or ""
    if _is_imagen4_unverified(eid):
        return False
    return not eid or not _schema_keys(spec)


def _is_fal_trainer(eid: str, spec: dict | None = None) -> bool:
    spec = spec if spec is not None else (find_model(eid) or {})
    fcat = (spec.get("falCategory") or "").lower()
    if fcat == "training":
        return True
    e = (eid or "").lower()
    if "trainer" in e or "-training" in e or e.endswith("training") or "/training" in e or e.endswith("/train"):
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
    has_last = any(f in LAST_IMAGE_FIELDS for f in fields)
    is_t2v = (
        "text-to-video" in fcat
        or "/t2v" in eid.lower()
        or eid.rstrip("/").endswith("video-01")  # classic MiniMax t2v (no image fields)
        or ("text-to-video" in blob and "image-to-video" not in blob)
    )
    is_i2v = (
        has_first
        or "image-to-video" in blob
        or "first-last" in blob
        or "reference-to-video" in blob
        or "start-end-to-video" in blob
    ) and not is_t2v
    # Pure t2v: never advertise first-frame / i2v
    if is_video and is_t2v and not has_first:
        out["needsSource"] = False
        out["needsFirstFrame"] = False
        out["supportsI2v"] = False
        if not fields:
            out["imageFields"] = []
    elif is_video:
        out["needsSource"] = False
        out["needsFirstFrame"] = bool(is_i2v or has_first)
        out["supportsI2v"] = bool(out["needsFirstFrame"])
    elif has_many and not has_first:
        out["needsSource"] = False
    elif has_first:
        out["needsSource"] = True
        out["needsFirstFrame"] = False
    # P0: single-image endpoints must not advertise maxRefs=9
    if has_many:
        out["maxRefs"] = int(out.get("maxRefs") or 9)
        out["maxImages"] = int(out.get("maxImages") or out["maxRefs"])
        out["refImagesField"] = "image_urls"
    else:
        # image_url / start_image_url / first_frame_url only — one primary (last is separate port)
        out["maxRefs"] = 1
        out["maxImages"] = 1
        out["refImagesField"] = "image_url" if (has_first or fields) else out.get("refImagesField") or "image_url"
    # expose under capabilities for storyboard resolveRefCaps
    caps = dict(out.get("capabilities") or {})
    caps["maxRefs"] = out["maxRefs"]
    caps["maxImages"] = out["maxImages"]
    caps["refImagesField"] = out.get("refImagesField") or caps.get("refImagesField")
    if "supportsI2v" in out:
        caps["supportsI2v"] = bool(out["supportsI2v"])
    elif is_video:
        caps["supportsI2v"] = bool(out.get("needsFirstFrame"))
    out["capabilities"] = caps
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


_CIVITAI_DL_RE = re.compile(
    r"(https?://(?:www\.)?civitai\.com/api/download/models/)(\d+)(.*)$",
    re.I,
)


def _fal_lora_version_id(item: dict) -> str:
    """Canonical Civitai modelVersionId for Fal download URLs.

    Prefer AIR `@version`, then versionId / modelVersionId.
    Never let a bare `id` or stale sibling versionId (2653078) beat AIR
    `@3071582` — model 2323765 ships both Krea2 and z_image_turbo siblings.
    """
    if not isinstance(item, dict):
        return ""

    def _as_vid(raw):
        if raw is None:
            return ""
        s = str(raw).strip()
        return s if s.isdigit() else ""

    air = (item.get("air") or "").strip()
    if air:
        m = re.search(r"@(\d+)\s*$", air) or re.search(r"civitai:\d+@(\d+)", air, re.I)
        if m:
            return m.group(1)
    for key in ("versionId", "modelVersionId"):
        vid = _as_vid(item.get(key))
        if vid:
            return vid
    return _as_vid(item.get("id"))


def _fal_lora_path(item: dict) -> str:
    if not isinstance(item, dict):
        return ""
    vid = _fal_lora_version_id(item)
    for k in ("path", "url", "downloadUrl", "download_url"):
        v = item.get(k)
        if isinstance(v, str):
            v = v.strip()
            if v and not _is_civitai_air(v):
                m = _CIVITAI_DL_RE.match(v)
                # Stale sibling path (2653078) must not beat AIR/versionId (3071582).
                if m and vid and m.group(2) != vid:
                    return f"{m.group(1)}{vid}{m.group(3)}"
                return v
    if vid:
        return f"https://civitai.com/api/download/models/{vid}"
    return ""


def _clip_lora_scale(v, default=1.0) -> float:
    """Keep the name for leftover callers. No silent clip and no default 1.0."""
    if v in (None, ""):
        raise ValueError(f"lora scale 必须是有限数值，收到 {v!r}，不能缺省为 {default}")
    return _strict_float(v, "lora scale")


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
    raw = payload.get("loras")
    if raw in (None, [], {}):
        return
    if not isinstance(raw, list):
        raise ValueError("Fal LoRA 必须是列表")
    shape = _lora_field_shape(spec, eid)
    if not shape:
        raise ValueError(f"端点 {eid} 不接受 LoRA，不能静默换到其他 endpoint")
    cleaned = []
    for it in raw:
        if not isinstance(it, dict):
            raise ValueError(f"lora 必须是对象，收到 {it!r}")
        path = _fal_lora_path(it)
        if not path:
            air = (it.get("air") or "").strip()
            raise ValueError(
                "Fal LoRA 必须提供可下载 path/url，不能只用 air"
                + (f"（{air}）" if air else "")
            )
        if "scale" in it:
            scale_raw = it.get("scale")
        elif "strength" in it:
            scale_raw = it.get("strength")
        else:
            scale_raw = None
        row = {"path": path}
        # Official Fal LoraWeight: path required, scale optional default 1.
        # Imported sample 134923572 has strength=null — omit scale, do not invent 1.0.
        # Invalid non-numeric values still 400.
        if scale_raw not in (None, ""):
            row["scale"] = _strict_float(scale_raw, "lora scale")
        cleaned.append(row)
    if not cleaned:
        return
    if shape == "loras":
        inp["loras"] = cleaned
    elif shape == "lora_url":
        inp["lora_url"] = cleaned[0]["path"]
        if "scale" in cleaned[0]:
            inp["lora_scale"] = cleaned[0]["scale"]
    elif shape == "lora_path":
        inp["lora_path"] = cleaned[0]["path"]
        if "scale" in cleaned[0]:
            inp["lora_scale"] = cleaned[0]["scale"]
    elif shape == "lora":
        inp["lora"] = cleaned[0]["path"]
        if "scale" in cleaned[0] and "lora_scale" in [str(x).lower() for x in _schema_keys(spec)]:
            inp["lora_scale"] = cleaned[0]["scale"]


MIME_BY_EXT = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".gif": "image/gif",
    ".mp4": "video/mp4",
    ".webm": "video/webm",
    ".wav": "audio/wav",
    ".mp3": "audio/mpeg",
}

MEDIA_URL_KEYS = (
    "image_url", "start_image_url", "first_frame_url", "image",
    "end_image_url", "tail_image_url", "last_frame_url",
    "image_urls", "video_url", "audio_url",
)


def local_out_to_data_url(url: str) -> str | None:
    """Turn studio-local /out/<file> into a data URL fal can fetch. None if not local."""
    if not isinstance(url, str):
        return None
    s = url.strip()
    if not s.startswith("/out/"):
        return None
    name = Path(s.split("?", 1)[0]).name
    if not name or name in (".", "..") or "/" in name or "\\" in name:
        return None
    fp = ROOT / "out" / name
    if not fp.is_file():
        return None
    import base64
    raw = fp.read_bytes()
    mime = MIME_BY_EXT.get(fp.suffix.lower(), "application/octet-stream")
    return f"data:{mime};base64,{base64.b64encode(raw).decode('ascii')}"


def materialize_fal_media(inp: dict) -> dict:
    """Rewrite local /out paths in fal outbound fields to data URLs.

    Relative /out/... is unreachable from fal workers (file_download_error).
    http(s) and existing data: URLs are left alone. Missing local files raise.
    """
    if not isinstance(inp, dict):
        return inp
    out = dict(inp)

    def one(val, key):
        if isinstance(val, list):
            return [one(v, key) for v in val]
        if not isinstance(val, str) or not val.strip():
            return val
        s = val.strip()
        if s.startswith("http://") or s.startswith("https://") or s.startswith("data:"):
            return s
        if s.startswith("/out/"):
            data = local_out_to_data_url(s)
            if not data:
                raise ValueError(f"Fal 无法读取本地首帧/参考图 {s}（文件不存在或不可读）")
            return data
        return s

    for key in MEDIA_URL_KEYS:
        if key not in out:
            continue
        out[key] = one(out[key], key)
    return out


def fal_output_error(obj) -> str | None:
    """Extract fal 422 / validation error text from result or platform json_output."""
    if not isinstance(obj, dict):
        return None
    detail = obj.get("detail")
    if isinstance(detail, list) and detail:
        msgs = []
        for it in detail:
            if isinstance(it, dict):
                m = it.get("msg") or it.get("message") or it.get("type")
                loc = it.get("loc")
                if m:
                    msgs.append(f"{'.'.join(str(x) for x in loc)}: {m}" if isinstance(loc, list) else str(m))
            elif it:
                msgs.append(str(it))
        if msgs:
            return "; ".join(msgs)
    if isinstance(detail, str) and detail.strip():
        return detail.strip()
    for k in ("error", "message", "msg"):
        v = obj.get(k)
        if isinstance(v, str) and v.strip() and v.strip() not in ("HTTP 405", "HTTP 404"):
            return v.strip()
        if isinstance(v, dict) and v.get("message"):
            return str(v.get("message"))
    return None


def _imagen4_invented_keys(payload: dict) -> list[str]:
    extras = []
    for k in (
        "width", "height", "steps", "cfgScale", "quantity", "qty", "num_images",
        "aspectRatio", "negativePrompt", "loras", "scheduler", "resolution",
        "duration", "seed", "guidanceScale", "numInferenceSteps",
        "firstFrame", "lastFrame", "image",
    ):
        if payload.get(k) not in (None, "", [], {}):
            extras.append(k)
    return extras


def build_fal_input(payload: dict) -> dict:
    eid = (payload.get("serviceId") or payload.get("endpoint") or "").strip()
    if _is_imagen4_unverified(eid):
        extras = _imagen4_invented_keys(payload or {})
        if extras:
            raise ValueError(
                f"端点 {eid} OpenAPI 未验证（404），不能编接口字段：{', '.join(extras)}"
            )
    spec = find_model(eid) or {}
    fields = list(spec.get("imageFields") or infer_image_fields(eid))
    prompt_key = spec.get("promptField") or "prompt"
    inp = {}
    prompt = payload.get("prompt") or ""
    if prompt_key:
        inp[prompt_key] = prompt
    from .ref_images import payload_ref_images, primary_frame, max_refs
    from .capabilities import get_provider_capabilities
    caps = get_provider_capabilities("fal")
    # catalog item may narrow maxRefs for single-image endpoints
    img = primary_frame(payload)
    last = (payload.get("lastFrame") or payload.get("endImage") or "").strip()
    extra = payload_ref_images(payload, backend="fal", caps=caps, item=spec)
    ref_cap = max_refs(backend="fal", caps=caps, item=spec, payload=payload)
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
                inp["image_urls"] = extra[:ref_cap]
        elif name == "video_url" and vid:
            inp["video_url"] = vid
        elif name in FIRST and img:
            inp[name] = img
        elif name in LAST and last:
            inp[name] = last
    req_opt = _schema_keys(spec)
    open_schema = _unschematized(spec)
    is_video = (
        (spec.get("category") or "").lower() == "video"
        or "video" in (spec.get("falCategory") or "").lower()
    )

    def has_field(*names):
        if open_schema:
            return True
        return any(n in req_opt for n in names)

    def reject_drop(studio_key: str, official: str):
        raise ValueError(
            f"端点 {eid} 官方 schema 没有 {official}，不能静默丢弃 {studio_key}"
        )

    if audio and (open_schema or "audio_url" in req_opt or "audio-to-video" in eid):
        inp["audio_url"] = audio
    if payload.get("negativePrompt"):
        if has_field("negative_prompt"):
            inp["negative_prompt"] = payload["negativePrompt"]
        else:
            reject_drop("negativePrompt", "negative_prompt")
    if payload.get("seed") not in (None, "", "random"):
        if has_field("seed"):
            inp["seed"] = _strict_int(payload["seed"], "seed")
        else:
            reject_drop("seed", "seed")
    if payload.get("steps") not in (None, ""):
        if has_field("num_inference_steps"):
            inp["num_inference_steps"] = _strict_int(payload["steps"], "steps")
        else:
            reject_drop("steps", "num_inference_steps")
    if payload.get("cfgScale") not in (None, ""):
        if "cfg_scale" in req_opt and "guidance_scale" not in req_opt:
            inp["cfg_scale"] = _strict_float(payload["cfgScale"], "cfgScale")
        elif has_field("guidance_scale"):
            inp["guidance_scale"] = _strict_float(payload["cfgScale"], "cfgScale")
        elif "cfg_scale" in req_opt:
            inp["cfg_scale"] = _strict_float(payload["cfgScale"], "cfgScale")
        else:
            reject_drop("cfgScale", "guidance_scale/cfg_scale")
    dur_field = spec.get("durationField")
    if not dur_field and (open_schema or "duration" in req_opt):
        dur_field = "duration"
    if payload.get("duration") not in (None, ""):
        if dur_field:
            dur = _strict_int(payload["duration"], "duration")
            inp[dur_field] = str(dur) if "kling" in eid else dur
        else:
            reject_drop("duration", "duration")
    ar_field = spec.get("aspectRatioField")
    if not ar_field and "ratio" in req_opt:
        ar_field = "ratio"
    if not ar_field and "aspect_ratio" in req_opt:
        ar_field = "aspect_ratio"
    if payload.get("aspectRatio"):
        if ar_field:
            inp[ar_field] = payload["aspectRatio"]
        elif "kontext" in eid or open_schema:
            inp["aspect_ratio"] = payload["aspectRatio"]
        else:
            raise ValueError(
                f"端点 {eid} 官方 schema 没有 aspect_ratio/ratio，"
                f"不能静默丢弃 aspectRatio={payload.get('aspectRatio')!r}"
            )
    w_raw, h_raw = payload.get("width"), payload.get("height")
    w_set = w_raw not in (None, "")
    h_set = h_raw not in (None, "")
    if w_set or h_set:
        if not (w_set and h_set):
            raise ValueError("width 和 height 必须同时提供，不能只给其中一个")
        size = {"width": _strict_int(w_raw, "width"), "height": _strict_int(h_raw, "height")}
        if "image_size" in req_opt or (open_schema and not is_video):
            inp["image_size"] = size
    if payload.get("scheduler"):
        if has_field("scheduler"):
            inp["scheduler"] = payload["scheduler"]
        else:
            reject_drop("scheduler", "scheduler")
    if payload.get("resolution") not in (None, ""):
        if has_field("resolution"):
            inp["resolution"] = payload["resolution"]
        else:
            reject_drop("resolution", "resolution")
    raw_q = payload.get("quantity")
    if raw_q in (None, ""):
        raw_q = payload.get("qty")
    if raw_q in (None, ""):
        raw_q = payload.get("num_images")
    if raw_q not in (None, ""):
        n = _strict_int(raw_q, "num_images")
        if n < 1:
            raise ValueError(f"num_images={n} 超出范围")
        if "num_images" in req_opt or (open_schema and not is_video):
            inp["num_images"] = n
        elif n != 1:
            raise ValueError(
                f"端点 {eid} 官方 schema 没有 num_images，quantity={n} 不能静默丢弃"
                "（仅 quantity=1 可省略）"
            )
    apply_fal_loras(inp, payload, spec, eid)
    # Keep empty-string prompt: Fal minimax i2v 422s with "body.prompt: Field required"
    # if the key is omitted (v0821k / job 01a07e75). Other empty strings still drop.
    out = {}
    for k, v in inp.items():
        if v is None or v == []:
            continue
        if v == "" and k not in ("prompt", "negative_prompt"):
            continue
        out[k] = v
    return out


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
    spec = find_model(eid) or {}
    if _is_fal_trainer(eid, spec):
        return 400, {"error": f"端点 {eid} 是训练器，不能当作生成", "backend": "fal", "endpoint": eid}
    try:
        inp = build_fal_input(payload)
        outbound = materialize_fal_media(inp)
    except ValueError as e:
        return 400, {"error": str(e), "backend": "fal", "endpoint": eid}
    # v0821k: optional provider reject when catalog requires prompt and outbound is empty
    # (client gates first; this stops silent Fal 422 Field required for API callers)
    spec = find_model(eid) or {}
    prompt_key = spec.get("promptField") or "prompt"
    req = list(spec.get("required") or [])
    if prompt_key in req or "prompt" in req:
        pv = outbound.get(prompt_key) if isinstance(outbound, dict) else None
        if pv is None or (isinstance(pv, str) and not pv.strip()):
            return 400, {
                "error": "此模型需要提示词",
                "backend": "fal",
                "endpoint": eid,
                "submittedInput": outbound,
            }
    code, data = fal_call(f"{QUEUE}/{eid}", method="POST", body=outbound)
    if isinstance(data, dict):
        rid = data.get("request_id") or data.get("requestId")
        jid = f"fal|{eid}|{rid}" if rid else None
        data["id"] = jid
        data["backend"] = "fal"
        data["endpoint"] = eid
        # v0821i P1: persist what Fal actually received (post-materialize), not pre-/out snapshot
        data["submittedInput"] = outbound
        if rid:
            _remember_job(rid, {
                "endpoint": eid,
                "status_url": data.get("status_url"),
                "response_url": data.get("response_url"),
                "cancel_url": data.get("cancel_url"),
                "submittedInput": outbound,
                "prompt": payload.get("prompt"),
            })
            remember_studio_job(jid, {
                "backend": "fal",
                "serviceId": eid,
                "submittedInput": outbound,
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
            # COMPLETED with no media: either still fetching, or fal 422/validation
            # (e.g. file_download_error on relative /out paths). Surface as failed.
            err = fal_output_error(result) if isinstance(result, dict) else None
            if not err and isinstance(data.get("result"), dict):
                err = fal_output_error(data.get("result"))
            if not err:
                pc2, plat2 = platform_payloads(eid, rid)
                if pc2 == 200 and isinstance(plat2, dict):
                    items2 = plat2.get("items") or []
                    item2 = items2[0] if items2 else None
                    if isinstance(item2, dict):
                        err = fal_output_error(item2.get("json_output") or item2.get("output") or {})
                        if not err and item2.get("status_code") and int(item2.get("status_code") or 0) >= 400:
                            err = f"Fal HTTP {item2.get('status_code')}"
            if err:
                data["status"] = "failed"
                data["error"] = err
                data["wait"] = data.get("wait") or {}
                data["wait"]["log"] = err
                data.pop("saveError", None)
            else:
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
