from __future__ import annotations

import json
import math
import re
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from .base import Provider
from .http import collect_urls, extract_error, json_call, parse_job_id, save_media_urls
from . import io_meta

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
TOKEN_PATH = Path.home() / ".config/civitai/token"
ORCH = "https://orchestration.civitai.com"
SITE = "https://civitai.com/api/v1"

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
_CAPS = None
_VERSION_CACHE = {}
_version_lock = threading.Lock()


def token() -> str:
    try:
        return TOKEN_PATH.read_text().strip()
    except Exception:
        return ""


def has_key() -> bool:
    return bool(token())


def civitai(url: str, method="GET", body=None, timeout=90):
    tok = token()
    if not tok:
        return 401, {"error": "没有 API Key"}
    headers = {"Authorization": f"Bearer {tok}"}
    return json_call(url, method=method, headers=headers, body=body, timeout=timeout)


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
        "backend": "civitai",
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


def find_service(service_id: str):
    items, _, _ = catalog_items()
    for it in items:
        if it.get("id") == service_id:
            return it
    return None


def match_service(engine=None, operation=None, ecosystem=None, model=None, category=None):
    items, _, _ = catalog_items()
    scored = []
    want_eco = _catalog_ecosystem(ecosystem) if ecosystem else None
    for it in items:
        if category and it.get("category") != category:
            continue
        # When ecosystem is requested, wrong-eco must not win via available(+2).
        if want_eco and not _ecosystems_compatible(it.get("ecosystem"), want_eco):
            continue
        s = 0
        if engine and it.get("engine") == engine:
            s += 4
        if operation and it.get("operation") == operation:
            s += 3
        if want_eco and _ecosystems_compatible(it.get("ecosystem"), want_eco):
            s += 2
        if model and it.get("model") == model:
            s += 1
        if s:
            if it.get("status") == "available":
                s += 2
            scored.append((s, it))
    scored.sort(key=lambda x: -x[0])
    return scored[0][1] if scored else None


def _norm_name(s) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(s or "").lower())


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


def _constraint(cap, key: str) -> dict:
    cons = ((cap or {}).get("constraints") or {}).get(key)
    return cons if isinstance(cons, dict) else {}


def _check_range(field: str, value, cons: dict):
    if not cons:
        return
    lo, hi = cons.get("min"), cons.get("max")
    if lo is not None and value < lo:
        raise ValueError(f"{field}={value} 超出范围 [{lo}, {hi}]")
    if hi is not None and value > hi:
        raise ValueError(f"{field}={value} 超出范围 [{lo}, {hi}]")
    enum = cons.get("enum")
    if enum is not None and value not in enum:
        raise ValueError(f"{field}={value} 不在允许列表")


def _schema_fields(cap: dict | None) -> set:
    """Official recipe keys only. extraFlags nulls (duration/resolution/turbo) are not fields."""
    fields = {
        "engine", "operation", "ecosystem", "model", "modelVersion",
        "version", "provider", "prompt",
    }
    if not cap:
        fields.update({
            "negativePrompt", "loras", "diffusionModel", "seed", "steps",
            "width", "height", "cfgScale", "quantity", "duration",
            "sampler", "scheduler", "denoise",
        })
        return fields
    for lst in (
        cap.get("required"),
        cap.get("optional"),
        cap.get("frameFields"),
        list((cap.get("constraints") or {}).keys()),
    ):
        if lst:
            fields.update(x for x in lst if x)
    return fields


def _official_field(cap: dict | None, *aliases: str) -> str | None:
    if not aliases:
        return None
    if not cap:
        return aliases[-1]
    schema = _schema_fields(cap)
    for name in aliases:
        if name in schema:
            return name
    return None


def _present(payload: dict, key: str) -> bool:
    if key not in payload:
        return False
    val = payload.get(key)
    if val is None or val == "":
        return False
    if val == [] or val == {}:
        return False
    return True


def _alias_value(payload: dict, *names: str):
    found = [(name, payload[name]) for name in names if _present(payload, name)]
    if not found:
        return None
    first = found[0][1]
    for name, value in found[1:]:
        if value != first:
            raise ValueError(f"{'/'.join(names)} 的值冲突，拒绝覆盖")
    return first


def _unsupported_field(sid: str, field: str) -> ValueError:
    return ValueError(f"{sid} 官方 recipe 不接受 {field}，不会静默丢掉")


def lora_map(payload: dict) -> dict:
    out = {}
    items = payload.get("loras") or []
    if isinstance(items, dict):
        items = [{"air": k, "strength": v} for k, v in items.items()]
    if items and not isinstance(items, list):
        raise ValueError("loras 必须是列表")
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("lora 必须是对象")
        air = (item.get("air") or "").strip()
        if not air:
            path = (item.get("path") or item.get("url") or "").strip()
            raise ValueError(
                "Civitai LoRA 必须提供 air，不能只用 path"
                + (f"（{path}）" if path else "")
            )
        if "strength" in item:
            raw = item.get("strength")
        elif "scale" in item:
            raw = item.get("scale")
        else:
            raw = None
        # Official additionalNetworks.strength is optional. Page 134923572 has
        # strength=null — omit the number, keep the AIR, do not invent 1.0/0.8.
        if raw in (None, ""):
            out[air] = None
            continue
        if isinstance(raw, bool):
            raise ValueError(f"lora strength 必须是数值，收到 {raw!r}")
        try:
            strength = float(raw)
            if not math.isfinite(strength):
                raise ValueError()
        except (TypeError, ValueError, OverflowError):
            raise ValueError(f"lora strength 必须是数值，收到 {raw!r}") from None
        out[air] = strength
    return out


def _set_int(inp, payload, key, lo=None, hi=None, cap=None):
    if payload.get(key) in (None, ""):
        return
    v = _strict_int(payload.get(key), key)
    cons = _constraint(cap, key)
    if lo is None and cons.get("min") is not None:
        lo = cons["min"]
    if hi is None and cons.get("max") is not None:
        hi = cons["max"]
    if lo is not None and v < lo:
        raise ValueError(f"{key}={v} 超出范围 [{lo}, {hi}]")
    if hi is not None and v > hi:
        raise ValueError(f"{key}={v} 超出范围 [{lo}, {hi}]")
    inp[key] = v


def _set_float(inp, payload, key, cap=None, dest=None):
    if payload.get(key) in (None, ""):
        return
    field = dest or key
    v = _strict_float(payload.get(key), field)
    cons = _constraint(cap, field) or _constraint(cap, key)
    _check_range(field, v, cons)
    inp[field] = v


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


def cap_for_service(svc: dict | None, inp: dict | None = None) -> dict | None:
    """Match capability to the catalog service, not the first engine+operation hit.

    Klein 9B/4B share a buggy defaults.modelVersion='4b'; prefer catalog
    parameters.modelVersion plus the capability name.
    """
    inp = inp or {}
    svc = svc or {}
    params = svc.get("parameters") or {}
    engine = inp.get("engine") or svc.get("engine") or params.get("engine")
    operation = inp.get("operation") or svc.get("operation") or params.get("operation")
    ecosystem = inp.get("ecosystem") or svc.get("ecosystem") or params.get("ecosystem")
    model = inp.get("model") or svc.get("model") or params.get("model")
    model_version = (
        inp.get("modelVersion")
        or params.get("modelVersion")
        or inp.get("version")
        or svc.get("version")
        or params.get("version")
    )
    provider = inp.get("provider") or svc.get("provider") or params.get("provider")
    name = svc.get("name") or ""
    name_n = _norm_name(name)
    mvn = _norm_name(model_version)
    svc_id = svc.get("id") or ""
    best, score = None, -1
    for c in load_caps():
        if engine and c.get("engine") and c.get("engine") != engine:
            continue
        s = 0
        raw = c.get("raw") if isinstance(c.get("raw"), dict) else {}
        raw_id = raw.get("id") or ""
        if svc_id and raw_id and svc_id == raw_id:
            s += 100
        cname = c.get("name") or ""
        cn = _norm_name(cname)
        if name and cname == name:
            s += 50
        elif name_n and cn == name_n:
            s += 40
        elif mvn and mvn in cn:
            s += 12
        elif name_n and (name_n in cn or cn in name_n):
            s += 4
        if engine and c.get("engine") == engine:
            s += 20
        if operation:
            if c.get("operation") == operation:
                s += 10
            elif c.get("operation") in (None, "videoGen", "imageGen"):
                s += 1
        d = c.get("defaults") or {}
        if ecosystem and (d.get("ecosystem") == ecosystem or c.get("ecosystem") == ecosystem):
            s += 8
        if model and d.get("model") == model:
            s += 8
        if mvn and mvn in cn:
            s += 15
        elif model_version and d.get("modelVersion") == model_version:
            s += 2
        if provider and c.get("provider") == provider:
            s += 1
        if s > score:
            best, score = c, s
    if best is None:
        return find_cap(engine, operation, inp.get("version") or svc.get("version"), provider)
    return best


def apply_frames(inp: dict, payload: dict, svc: dict | None):
    engine = (inp.get("engine") or (svc or {}).get("engine") or "")
    cap = cap_for_service(svc, inp)
    sid = (svc or {}).get("id") or ""
    for key in ("last_image", "image_url", "image_urls", "end_image", "imageUrl", "imageDataUrl"):
        if payload.get(key) not in (None, "", []):
            raise ValueError(
                f"Civitai 不接受 Fal 字段 {key}，请用官方首尾帧字段，不会静默改名或丢掉"
            )
    frames = list((cap or {}).get("frameFields") or [])
    from .ref_images import payload_ref_images, max_refs, materialize_local_ref, materialize_local_refs
    from .capabilities import get_provider_capabilities
    caps = get_provider_capabilities("civitai")
    first = ""
    for key in ("firstFrame", "sourceImage", "startImage", "sourceImageUrl", "firstFrameImage", "image"):
        val = payload.get(key)
        if isinstance(val, str) and val.strip():
            cur = val.strip()
            if first and first != cur:
                raise ValueError("首帧字段值冲突，拒绝覆盖")
            first = cur
    last = ""
    for key in ("lastFrame", "endImage", "endSourceImage", "lastFrameImage"):
        val = payload.get(key)
        if isinstance(val, str) and val.strip():
            cur = val.strip()
            if last and last != cur:
                raise ValueError("尾帧字段值冲突，拒绝覆盖")
            last = cur
    extra = payload_ref_images(payload, backend="civitai", caps=caps, item=cap if isinstance(cap, dict) else None)
    ref_cap = max_refs(backend="civitai", caps=caps, item=cap if isinstance(cap, dict) else None, payload=payload)
    FIRST_NAMES = {"firstFrame", "sourceImage", "image", "sourceImageUrl", "firstFrameImage"}
    LAST_NAMES = {"lastFrame", "endImage", "endSourceImage", "lastFrameImage"}
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
        if first or last or _present(payload, "images") or _present(payload, "referenceImages"):
            raise _unsupported_field(sid, "首尾帧")
    else:
        has_first = any(name in FIRST_NAMES or name == "startImage" for name in frames)
        has_last = any(name in LAST_NAMES for name in frames)
        if first and not has_first and "images" not in frames and "referenceImages" not in frames:
            raise _unsupported_field(sid, "首帧")
        if last and not has_last:
            raise _unsupported_field(sid, "尾帧")
        if _present(payload, "images") and "images" not in frames:
            raise _unsupported_field(sid, "images")
        if _present(payload, "referenceImages") and "referenceImages" not in frames:
            raise _unsupported_field(sid, "referenceImages")
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
    # o44: Civitai cannot fetch studio /out — materialize to data URLs (same as Fal/Nano).
    # Fail-closed on missing local files; never silent-drop.
    for key in ("images", "referenceImages"):
        if key in inp and isinstance(inp[key], list):
            inp[key] = materialize_local_refs(inp[key])
    for key in (
        "sourceImage", "firstFrame", "startImage", "firstFrameImage", "image", "sourceImageUrl",
        "lastFrame", "endImage", "endSourceImage", "lastFrameImage", "maskImage",
    ):
        if key in inp and isinstance(inp[key], str) and inp[key].strip():
            inp[key] = materialize_local_ref(inp[key])
    schema = _schema_fields(cap)
    if payload.get("turbo") is not None and "turbo" in schema:
        inp["turbo"] = bool(payload.get("turbo"))
    if payload.get("fast") is not None and "fast" in schema:
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


def _assign_int(inp, raw, field, cap=None, aliases=()):
    v = _strict_int(raw, field)
    cons = _constraint(cap, field)
    if not cons:
        for alt in aliases:
            cons = _constraint(cap, alt)
            if cons:
                break
    _check_range(field, v, cons)
    inp[field] = v


def _assign_float(inp, raw, field, cap=None, aliases=()):
    v = _strict_float(raw, field)
    cons = _constraint(cap, field)
    if not cons:
        for alt in aliases:
            cons = _constraint(cap, alt)
            if cons:
                break
    _check_range(field, v, cons)
    inp[field] = v


def _assign_choice(inp, raw, field, cap=None, aliases=()):
    cons = _constraint(cap, field)
    if not cons:
        for alt in aliases:
            cons = _constraint(cap, alt)
            if cons:
                break
    value = raw
    enum = cons.get("enum") if cons else None
    if enum is not None:
        mapped = io_meta.match_allowed_choice(raw, enum)
        if not mapped:
            _check_range(field, raw, cons)  # raises 不在允许列表
            return
        value = mapped
    _check_range(field, value, cons)
    inp[field] = value


def _duration_is_string(cap, field="duration") -> bool:
    cons = _constraint(cap, field)
    if (cons.get("type") or "").lower() == "string":
        return True
    enum = cons.get("enum")
    return bool(enum) and all(isinstance(x, str) for x in enum)


def _assign_by_constraint(inp, raw, field, cap=None, aliases=()):
    cons = _constraint(cap, field)
    if not cons:
        for alt in aliases:
            cons = _constraint(cap, alt)
            if cons:
                break
    typ = (cons.get("type") or "").lower()
    if field == "duration" and _duration_is_string(cap, field):
        if isinstance(raw, bool) or raw is None:
            raise ValueError(f"{field} 必须是官方枚举字符串，收到 {raw!r}")
        value = str(raw).strip()
        _check_range(field, value, cons)
        inp[field] = value
        return
    if field == "seed" or typ == "integer":
        _assign_int(inp, raw, field, cap, aliases)
        return
    if typ == "number":
        _assign_float(inp, raw, field, cap, aliases)
        return
    if typ == "boolean":
        if not isinstance(raw, bool):
            raise ValueError(f"{field} 必须是布尔值，收到 {raw!r}")
        inp[field] = raw
        return
    if typ in ("array", "object"):
        inp[field] = raw
        return
    if cons.get("enum") is not None:
        _assign_choice(inp, raw, field, cap, aliases)
        return
    if isinstance(raw, bool):
        raise ValueError(f"{field} 类型无效，收到 {raw!r}")
    inp[field] = raw


def _lora_row(air: str, strength):
    row = {"air": air}
    if strength is not None:
        row["strength"] = strength
    return row


def _lora_payload(loras: dict, cap: dict | None, engine: str | None):
    """Official Civitai LoRA shapes from constraints.loras.type:
    - object `{air: strength}` (Comfy / sdcpp / Flux2 Klein)
    - array `[{air, strength}]` (Flux2 Dev, Hunyuan, Wan)
    Hunyuan has no type in some dumps; engine==hunyuan still uses the list.

    strength=None (imported sample) omits the number. Object Record<string,number>
    cannot hold null, so a missing strength forces the official array form
    `{air}` without inventing 1.0.
    """
    cons = _constraint(cap, "loras")
    kind = (cons.get("type") or "").lower()
    use_array = kind == "array" or (not kind and engine == "hunyuan")
    missing = [k for k, v in loras.items() if v is None]
    if use_array:
        return [_lora_row(k, v) for k, v in loras.items()]
    # Comfy / sdcpp live recipe: ImmutableDictionary<AIR, double>. Null cannot convert.
    if missing:
        raise ValueError(
            "Civitai 官方 loras 是 {AIR: number}（ImmutableDictionary<AIR,double>），"
            f"导入 strength 为空：{', '.join(missing)}。请填写强度后再生成，不会默认为 1.0"
        )
    return loras


_STUDIO_ALIASES = (
    ("numInferenceSteps", "steps"),
    ("guidanceScale", "cfgScale"),
    ("sampleMethod", "sampler"),
    ("schedule", "scheduler"),
    ("denoiseStrength", "denoise"),
    ("useTurbo", "turbo"),
)

_KNOWN_UI_FIELDS = {
    "prompt", "negativePrompt", "width", "height", "steps", "numInferenceSteps",
    "cfgScale", "guidanceScale", "seed", "sampler", "sampleMethod", "scheduler",
    "schedule", "denoise", "denoiseStrength", "quantity", "diffusionModel",
    "duration", "resolution", "aspectRatio", "creativity", "size",
    "imageStyleReferences", "intensity", "complexity", "movement", "strength",
    "outputFormat", "enablePromptExpansion", "turbo", "useTurbo", "fast",
    "shift", "interpolatorModel", "generateAudio", "frameRate", "clipSkip",
    "vaeModel", "diffuserModel", "mode", "watermark", "imageMetadata",
}

_META_KEYS = {
    "serviceId", "kind", "allowMatureContent", "backend", "recipe", "step",
    "comfyWorkflow", "workflow", "promptEdits", "resources", "whatif", "wait",
    "hideMatureContent", "trace", "comfyImage", "token", "jobId", "id",
    "session", "nodeId", "graph", "customComfy", "checkpointName", "modelName",
    "name", "loras", "engine", "operation", "ecosystem", "model", "version",
    "provider", "modelVersion", "serviceName", "mediaUrl", "mediaType",
    "unmatched", "comfyNodeCount", "importSource", "empty", "paramWarn",
    "dimensionAlign", "sourceWidth", "sourceHeight",
}

_FRAME_KEYS = {
    "firstFrame", "sourceImage", "startImage", "sourceImageUrl", "image",
    "firstFrameImage", "lastFrame", "endImage", "endSourceImage", "lastFrameImage",
    "images", "referenceImages", "sourceVideo", "sourceAudio", "videoUrl",
    "maskImage", "audioUrl", "referenceVideos", "referenceAudios",
    "last_image", "image_url", "image_urls", "end_image", "imageUrl", "imageDataUrl",
    "input_references",
}


_FLUX_BROKEN_DIFFUSIONMODEL_AIR_RE = re.compile(
    r"^urn:air:flux:diffusionmodel:civitai:(\d+)@(\d+)$", re.I
)


def _normalize_sdcpp_flux1_diffuser_air(air: str) -> str:
    """Outbound value for flux1 diffuserModel.

    Prefer REST/model-versions air verbatim. Rewrite only the known-broken
    `_air_from_ids` shape `flux:diffusionmodel` → `flux1:checkpoint` (same mid@version).
    FORBIDDEN: unilaterally rewrite site `checkpoint` → `diffuser`.
    Official `flux1:diffuser` resource AIRs pass through unchanged.
    """
    s = str(air or "").strip()
    m = _FLUX_BROKEN_DIFFUSIONMODEL_AIR_RE.match(s)
    if m:
        return f"urn:air:flux1:checkpoint:civitai:{m.group(1)}@{m.group(2)}"
    return s



def build_workflow(payload: dict) -> dict:
    payload = payload or {}
    sid = (payload.get("serviceId") or "").strip()
    if not sid:
        raise ValueError("缺少 serviceId，不能静默换成默认模型")
    svc = find_service(sid)
    if not svc:
        raise ValueError(f"未知服务 {sid}，不会替换为其他模型")
    kind = payload.get("kind") or svc.get("category") or "image"
    inp = dict(svc.get("parameters") or {})
    for k in ("engine", "operation", "ecosystem", "model", "version", "provider", "modelVersion"):
        if payload.get(k) not in (None, ""):
            inp[k] = payload[k]
    cap = cap_for_service(svc, inp)
    schema = _schema_fields(cap)
    handled = set()
    if payload.get("prompt") is not None:
        inp["prompt"] = payload["prompt"]
        handled.add("prompt")
    seed = payload.get("seed")
    if seed not in (None, "", "random"):
        if "seed" not in schema:
            raise _unsupported_field(sid, "seed")
        _assign_int(inp, seed, "seed", cap)
        handled.add("seed")
    elif seed == "random":
        handled.add("seed")
    for group in _STUDIO_ALIASES:
        if any(_present(payload, name) for name in group):
            value = _alias_value(payload, *group)
            dest = _official_field(cap, *group)
            if not dest:
                raise _unsupported_field(sid, group[-1])
            _assign_by_constraint(inp, value, dest, cap, group)
            handled.update(group)
    raw_loras = payload.get("loras") or []
    if isinstance(raw_loras, dict):
        raw_loras = list(raw_loras.items())
    if raw_loras:
        if "loras" not in schema:
            raise ValueError(
                f"{sid} 官方 recipe 不接受 LoRAs，不会静默丢掉或改打其他模型"
            )
        inp["loras"] = _lora_payload(lora_map(payload), cap, inp.get("engine"))
    handled.add("loras")
    for key, value in list(payload.items()):
        if key in handled or key in _META_KEYS or key in _FRAME_KEYS:
            continue
        if value is None or value == [] or value == {}:
            continue
        dest = _official_field(cap, key)
        if dest:
            _assign_by_constraint(inp, value, dest, cap, (key,))
            continue
        # Outbound checkpoint AIR: prefer official diffuserModel; else model (SDXL precedent).
        # Never silently drop diffusionModel; wrong service stays honest 400.
        if key == "diffusionModel":
            schema = _schema_fields(cap)
            if "diffuserModel" in schema:
                out_val = value
                # o35: sdcpp flux1 only — fix broken flux:diffusionmodel mint; never checkpoint→diffuser
                eco = _catalog_ecosystem(inp.get("ecosystem") or (svc.get("ecosystem") if svc else "") or "")
                sid_l = str(sid or "").lower()
                if eco == "flux1" or "/flux1/" in sid_l:
                    out_val = _normalize_sdcpp_flux1_diffuser_air(value)
                _assign_by_constraint(inp, out_val, "diffuserModel", cap, (key,))
                continue
            if "diffusionModel" not in schema and "model" in schema:
                cur = inp.get("model")
                if cur in (None, "") or _is_recipe_short_model(cur):
                    _assign_by_constraint(inp, value, "model", cap, (key,))
                    continue
        if key in _KNOWN_UI_FIELDS:
            raise _unsupported_field(sid, key)
    cap = apply_frames(inp, payload, svc) or cap
    fill_required(inp, payload, cap)
    if cap and "imageStyleReferences" in (cap.get("required") or []) and "imageStyleReferences" not in inp:
        raise ValueError(f"{sid} 官方必填 imageStyleReferences，不能编造空引用")
    if cap:
        allowed = _schema_fields(cap)
        allowed.update({"modelVersion", "version", "provider"})
        leaked = [k for k in inp if k not in allowed]
        ui_leaked = [k for k in leaked if k in _KNOWN_UI_FIELDS or k in _FRAME_KEYS]
        if ui_leaked:
            raise _unsupported_field(sid, ui_leaked[0])
        inp = {k: v for k, v in inp.items() if k in allowed}
        if isinstance(inp.get("loras"), dict):
            inp["loras"] = _lora_payload(inp["loras"], cap, inp.get("engine"))
    step = svc.get("step") or ("videoGen" if kind == "video" else "imageGen")
    return {
        "allowMatureContent": bool(payload.get("allowMatureContent", True)),
        "steps": [{"$type": step, "input": inp}],
        "_meta": {"serviceId": svc.get("id"), "serviceName": svc.get("name")},
    }


def parse_image_id(raw: str) -> int:
    import re
    s = (raw or "").strip()
    for pat in (r"/images/(\d+)", r"/image/(\d+)", r"[?&]imageId=(\d+)", r"[?&]id=(\d+)", r"^(\d+)$"):
        m = re.search(pat, s, re.I)
        if m:
            return int(m.group(1))
    raise ValueError("请填图片数字 ID 或完整网址")


def _ecosystem_from_blob(*parts) -> str:
    blob = " ".join(str(p or "") for p in parts).lower()
    if "krea" in blob:
        return "krea2"
    if "zimage" in blob or "z-image" in blob or "z_image" in blob:
        return "zImage"
    if "qwen" in blob:
        return "qwen"
    # o35: flux.1 / flux1 before bare flux (AIR eco = flux1; catalog still aliases flux→flux1)
    if "flux.1" in blob or "flux1" in blob:
        return "flux1"
    if "flux" in blob:
        return "flux"
    if "wan" in blob:
        return "wan"
    if "sdxl" in blob or "pony" in blob or "illustrious" in blob:
        return "sdxl"
    return ""


def _catalog_ecosystem(eco) -> str:
    """Map blob/AIR eco labels onto catalog ecosystem ids (flux → flux1)."""
    e = str(eco or "").strip()
    if e == "flux":
        return "flux1"
    return e


def _ecosystems_compatible(a, b) -> bool:
    if not a or not b:
        return False
    return _catalog_ecosystem(a) == _catalog_ecosystem(b)


def _is_recipe_short_model(cur) -> bool:
    """True for recipe distillation slots (turbo/base) — not family ids or AIR URNs."""
    s = str(cur or "").strip()
    if not s or s.lower().startswith("urn:air:"):
        return False
    return s in {"turbo", "base"}


def _air_from_ids(model_id, version_id, typ="", base="", name=""):
    """Mint AIR only when REST `air` is absent.

    o35: never hand-roll `urn:air:flux:diffusionmodel:…`. Flux family → eco=flux1;
    non-LoRA checkpoints use kind=`checkpoint` (REST truth). Prefer model-versions `air` verbatim upstream.
    """
    try:
        mid = int(model_id)
        vid = int(version_id)
    except (TypeError, ValueError):
        return ""
    eco = _catalog_ecosystem(_ecosystem_from_blob(base, name, typ) or "krea2") or "krea2"
    if _is_lora_resource(typ, "", name or ""):
        kind = "lora"
    elif eco == "flux1":
        kind = "checkpoint"
    else:
        kind = "diffusionmodel"
    return f"urn:air:{eco}:{kind}:civitai:{mid}@{vid}"


def _normalize_pair(sampler, scheduler):
    from . import io_meta
    samp, sched = io_meta.split_sampler_scheduler(str(sampler or ""), str(scheduler or ""))
    samp_n = io_meta.normalize_sampler(samp, SAMPLERS) or io_meta.normalize_sampler(samp)
    sched_n = io_meta.normalize_scheduler(sched, SCHEDULERS) or io_meta.normalize_scheduler(sched)
    if samp_n not in SAMPLERS:
        samp_n = DEFAULTS["sampler"]
    if sched_n not in SCHEDULERS:
        sched_n = DEFAULTS["scheduler"]
    return samp_n, sched_n


def _fetch_html(url, timeout=25) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept": "text/html"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def generation_from_page(image_id: int) -> dict:
    """Parse __NEXT_DATA__ from the public image page. No API key."""
    for host in ("https://civitai.com", "https://civitai.red"):
        try:
            html = _fetch_html(f"{host}/images/{int(image_id)}")
        except Exception:
            continue
        m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html)
        if not m:
            continue
        try:
            data = json.loads(m.group(1))
        except Exception:
            continue
        queries = ((((data.get("props") or {}).get("pageProps") or {}).get("trpcState") or {}).get("json") or {}).get("queries") or []
        gen, info = {}, {}
        for q in queries:
            key = q.get("queryKey") or []
            path = ""
            if isinstance(key, list) and key and isinstance(key[0], list):
                path = ".".join(str(x) for x in key[0])
            state = (q.get("state") or {}).get("data") or {}
            if not isinstance(state, dict):
                continue
            if "getGenerationData" in path:
                gen = state
            elif path.endswith(".get") or path == "image.get":
                info = state
        if gen or info:
            return {"gen": gen, "info": info}
    return {}


def public_image_row(image_id: int) -> dict:
    code, data = json_call(f"{SITE}/images?imageId={int(image_id)}&nsfw=X", timeout=25)
    if isinstance(data, dict):
        items = data.get("items") or []
        if items and isinstance(items[0], dict):
            return items[0]
    return {}


def _download_bytes(url: str, timeout=60) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def enrich_local_parse(parsed: dict) -> dict:
    """Best-effort public model match from UNET/checkpoint filename. Never invent a prompt."""
    if not isinstance(parsed, dict):
        return parsed
    name = parsed.get("checkpointName") or parsed.get("Model") or ""
    models = parsed.get("models") or []
    fname = Path(str(models[0])).name if models else ""
    query = name or Path(fname).stem
    query = re.sub(r"[_-]?int[48].*$", "", query, flags=re.I)
    query = re.sub(r"[_-]?(nvfp4|gguf|fp8|fp16).*$", "", query, flags=re.I)
    query = query.replace("_", " ").replace("-", " ").strip()
    query = re.sub(r"\s+", " ", query)
    if not query or len(query) < 4:
        return parsed
    code, data = json_call(f"{SITE}/models?limit=5&query={urllib.parse.quote(query)}", timeout=20)
    items = (data or {}).get("items") if isinstance(data, dict) else []
    if not items:
        return parsed
    pick = None
    for it in items:
        if str(it.get("type") or "").lower() == "checkpoint":
            pick = it
            break
    pick = pick or items[0]
    vers = pick.get("modelVersions") or []
    ver = None
    stem = Path(fname or name).stem.lower()
    for v in vers:
        blob = (str(v.get("name") or "") + " " + str(v.get("baseModel") or "")).lower()
        if "v1.0" in stem and str(v.get("name") or "") == "v1.0":
            ver = v
            break
        if stem and stem[:16] in json.dumps(v, ensure_ascii=False).lower():
            ver = v
            break
    ver = ver or (vers[0] if vers else None)
    if not ver:
        parsed["checkpointName"] = parsed.get("checkpointName") or pick.get("name") or name
        return parsed
    mid, vid = pick.get("id"), ver.get("id")
    air = ver.get("air") or _air_from_ids(mid, vid, pick.get("type"), ver.get("baseModel") or pick.get("baseModel"), pick.get("name"))
    if air and not parsed.get("diffusionModel"):
        parsed["diffusionModel"] = air
    parsed["checkpointName"] = pick.get("name") or parsed.get("checkpointName") or name
    parsed["modelId"] = mid
    parsed["modelVersionId"] = vid
    return parsed


_LORA_TYPES = {
    "LORA", "LORAS", "LOCON", "LOHA", "LOKR", "DORA", "LYCORIS", "TEXTUALINVERSION",
}
_LORA_TAG_RE = re.compile(r"<lora:([^:>]+)(?::([0-9.]+))?>", re.I)


def _is_lora_resource(typ: str, air: str, name: str = "") -> bool:
    t = (typ or "").upper().replace(" ", "").replace("_", "")
    if t in _LORA_TYPES:
        return True
    blob = f"{air} {name}".lower()
    if ":lora:" in blob or "/lora" in blob:
        return True
    return False


def _optional_strength(raw):
    """Parse a LoRA weight. Missing / null / empty / non-numeric → None. Never invent 0.8."""
    if raw is None or raw == "":
        return None
    if isinstance(raw, bool):
        return None
    try:
        strength = float(raw)
    except (TypeError, ValueError, OverflowError):
        return None
    if not math.isfinite(strength):
        return None
    return strength


def _resource_strength_raw(r: dict):
    """Page `strength: null` stays null even if `weight` is present. Missing key may fall back to weight."""
    if not isinstance(r, dict):
        return None
    if "strength" in r:
        return r.get("strength")
    if "weight" in r:
        return r.get("weight")
    return None


def _strength_fields(raw):
    strength = _optional_strength(raw)
    out = {"strength": strength}
    if strength is None:
        out["strengthMissing"] = True
    return out



def _file_stem(name: str) -> str:
    """Basename without weight-extension — for prompt <lora:file:str> ↔ version files dedupe."""
    n = (name or "").strip()
    if not n:
        return ""
    lower = n.lower()
    for ext in (".safetensors", ".pt", ".ckpt", ".bin", ".pth", ".sft"):
        if lower.endswith(ext):
            n = n[: -len(ext)]
            break
    return n.strip().lower()


def _version_file_stems(ver: dict | None) -> set:
    stems = set()
    if not isinstance(ver, dict):
        return stems
    for f in (ver.get("files") or []):
        if not isinstance(f, dict):
            continue
        stem = _file_stem(f.get("name") or "")
        if stem:
            stems.add(stem)
    return stems


def _prompt_lora_tags(prompt: str) -> list:
    out = []
    seen = set()
    for name, weight in _LORA_TAG_RE.findall(prompt or ""):
        key = name.strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        row = {"name": name.strip()}
        row.update(_strength_fields(weight))
        out.append(row)
    return out


def _version_from_cache(vid):
    with _version_lock:
        return _VERSION_CACHE.get(int(vid) if str(vid).isdigit() else vid)


def _store_version(vid, ver):
    key = int(vid) if str(vid).isdigit() else vid
    with _version_lock:
        _VERSION_CACHE[key] = ver
    return ver


def fetch_version_air(vid, timeout=20):
    """Public version endpoint first (no key). Auth mini/full as fallback. Cached."""
    cached = _version_from_cache(vid)
    if cached:
        return cached
    code, ver = json_call(f"{SITE}/model-versions/{vid}", timeout=timeout)
    if not (isinstance(ver, dict) and (ver.get("air") or ver.get("id"))):
        code, ver = civitai(f"{SITE}/model-versions/mini/{vid}", timeout=timeout)
    if not (isinstance(ver, dict) and (ver.get("air") or ver.get("id"))):
        code, ver = civitai(f"{SITE}/model-versions/{vid}", timeout=timeout)
    if isinstance(ver, dict) and (ver.get("air") or ver.get("id")):
        if not ver.get("air"):
            mid = ver.get("modelId")
            base = ver.get("baseModel") or ""
            typ = ((ver.get("model") or {}).get("type") if isinstance(ver.get("model"), dict) else "") or ""
            if mid and vid:
                ver = dict(ver)
                ver["air"] = _air_from_ids(mid, vid, typ, base, (ver.get("model") or {}).get("name") if isinstance(ver.get("model"), dict) else "")
        return _store_version(vid, ver)
    return ver if isinstance(ver, dict) else {}


_AIR_AT_VERSION_RE = re.compile(r"@(\d+)\s*$")
_AIR_CIVITAI_VERSION_RE = re.compile(r"civitai:\d+@(\d+)", re.I)
_CIVITAI_DL_MODELS_RE = re.compile(
    r"(https?://(?:www\.)?civitai\.com/api/download/models/)(\d+)(.*)$",
    re.I,
)


def _as_version_id(raw):
    """Positive digit version id, or None. Rejects bools and non-numeric strings."""
    if raw is None or isinstance(raw, bool):
        return None
    if isinstance(raw, int):
        return raw if raw > 0 else None
    s = str(raw).strip()
    if s.isdigit():
        n = int(s)
        return n if n > 0 else None
    return None


def _version_id_from_air(air: str):
    """Parse `@version` / `civitai:model@version` from an AIR URN."""
    air = (air or "").strip()
    if not air:
        return None
    m = _AIR_AT_VERSION_RE.search(air) or _AIR_CIVITAI_VERSION_RE.search(air)
    return int(m.group(1)) if m else None


def _import_lora_version_id(r: dict):
    """Canonical modelVersionId for import chips.

    Prefer AIR `@version`, then `versionId`, then `modelVersionId`.
    Never let bare `id` (search-hit modelId or sibling version like 2653078)
    beat AIR `@3071582`.
    """
    if not isinstance(r, dict):
        return None
    air_vid = _version_id_from_air(r.get("air") or "")
    if air_vid is not None:
        return air_vid
    for key in ("versionId", "modelVersionId"):
        vid = _as_version_id(r.get(key))
        if vid is not None:
            return vid
    return _as_version_id(r.get("id"))


def _reconcile_civitai_download_path(path: str, vid) -> str:
    """Rewrite stale sibling download URLs to match canonical versionId."""
    if not path or vid is None:
        return path or ""
    m = _CIVITAI_DL_MODELS_RE.match(str(path).strip())
    if m and m.group(2) != str(vid):
        return f"{m.group(1)}{vid}{m.group(3)}"
    return path


def _loras_from_import_sources(resources: list, prompt: str = "", versions: dict | None = None) -> list:
    """Assemble import LoRA chips. Page `strength: null` stays null; never invent 0.8.

    Prompt `<lora:fileStem:w>` often names the version *file* (e.g. hinaSamuraiArmorPony_rev1),
    while resources carry the model display name + AIR. Dedup by file stem so we do not mint a
    second no-air chip that outbound must drop (19201654 → LoRA 出站 1/2).
    """
    loras = []
    seen_lora = set()
    seen_stems = set()
    versions = versions or {}
    for r in resources or []:
        if not isinstance(r, dict):
            continue
        vid = _import_lora_version_id(r)
        ver = versions.get(vid) or _version_from_cache(vid) or {}
        air = (r.get("air") or ver.get("air") or "").strip()
        typ = r.get("modelType") or r.get("type") or (ver.get("model") or {}).get("type") or ""
        name = r.get("modelName") or r.get("name") or (ver.get("model") or {}).get("name") or ver.get("name") or ""
        if not air:
            mid = r.get("modelId") or ver.get("modelId")
            air = _air_from_ids(mid, vid, typ, r.get("baseModel") or ver.get("baseModel"), name)
            # AIR may have been minted above; prefer its @version if id fields were empty.
            if vid is None:
                vid = _version_id_from_air(air)
        if not _is_lora_resource(typ, air, name):
            continue
        key = str(vid or air or name).lower()
        if key in seen_lora:
            continue
        seen_lora.add(key)
        stems = _version_file_stems(ver)
        name_stem = _file_stem(name)
        if name_stem:
            stems.add(name_stem)
        # o23: meta.resources often repeats file-stem LoRA without AIR after js.resources @vid chip.
        if stems and stems.intersection(seen_stems):
            continue
        if not air and vid is None:
            # Filename-only / hash-only rows — do not mint empty-air chips here.
            continue
        seen_stems.update(stems)
        item = {
            "air": air,
            "name": name or "LoRA",
        }
        item.update(_strength_fields(_resource_strength_raw(r)))
        if vid is not None:
            item["versionId"] = vid
        path = ""
        for f in (ver.get("files") or []):
            if isinstance(f, dict) and (f.get("downloadUrl") or f.get("download_url")):
                path = f.get("downloadUrl") or f.get("download_url")
                break
        if not path:
            for k in ("path", "downloadUrl", "download_url", "url"):
                raw = r.get(k)
                if isinstance(raw, str) and raw.strip() and "civitai.com/api/download/models/" in raw:
                    path = raw.strip()
                    break
        if not path and vid is not None:
            path = f"https://civitai.com/api/download/models/{vid}"
        path = _reconcile_civitai_download_path(path, vid)
        if path:
            item["path"] = path
            item["downloadUrl"] = path
        if stems:
            item["fileStems"] = sorted(stems)
        loras.append(item)
    for tag in _prompt_lora_tags(prompt or ""):
        key = tag["name"].lower()
        stem = _file_stem(tag["name"])
        if stem and stem in seen_stems:
            continue
        if any(
            key == str(x.get("name") or "").lower()
            or key in str(x.get("air") or "").lower()
            or stem in { _file_stem(s) for s in (x.get("fileStems") or []) }
            for x in loras
        ):
            continue
        row = {
            "air": "",
            "name": tag["name"],
        }
        row.update(_strength_fields(tag.get("strength")))
        if tag.get("strengthMissing"):
            row["strengthMissing"] = True
        loras.append(row)
    # Final honesty pass: drop empty-air chips whose stem matches an AIR chip (no invent).
    air_stems = set()
    for x in loras:
        if not str((x or {}).get("air") or "").strip():
            continue
        air_stems.add(_file_stem((x or {}).get("name") or ""))
        for s in ((x or {}).get("fileStems") or []):
            air_stems.add(_file_stem(s))
    air_stems.discard("")
    out = []
    for x in loras:
        if str((x or {}).get("air") or "").strip():
            out.append(x)
            continue
        stem = _file_stem((x or {}).get("name") or "")
        if stem and stem in air_stems:
            continue
        out.append(x)
    return out


_COMFY_IMPORT_DIM_MIN = 64
_COMFY_IMPORT_DIM_MAX = 2048


def _clamp_import_comfy_dim(n, field="height"):
    """Keep source pixels. Comfy 64–2048 is a range, not a /16 grid.

    Page 134923572 is 944×1672. 1672 is legal; snapping to 1664 is a bug.
    Returns (value, source, warn_or_none).
    """
    source = int(n)
    value = max(_COMFY_IMPORT_DIM_MIN, min(_COMFY_IMPORT_DIM_MAX, source))
    warn = None
    if value != source:
        warn = (
            f"{field} {source} 超出 Comfy "
            f"{_COMFY_IMPORT_DIM_MIN}–{_COMFY_IMPORT_DIM_MAX}，已截到 {value}"
            "（不是 /16 对齐）"
        )
    return value, source, warn



def fetch_generation_data_rest(image_id: int) -> dict:
    """Official REST generation params (public). Carries resource.strength when trpc null."""
    code, data = json_call(
        f"https://civitai.com/api/generation/data?type=image&id={int(image_id)}",
        timeout=25,
    )
    return data if isinstance(data, dict) else {}


def _resource_version_id_for_strength(r: dict):
    """Match key for REST↔trpc strength merge.

    REST generation/data uses `id` as the model version id; trpc uses modelVersionId/versionId.
    Prefer explicit version fields, then AIR @version, then bare id.
    """
    if not isinstance(r, dict):
        return None
    for key in ("modelVersionId", "versionId"):
        vid = _as_version_id(r.get(key))
        if vid is not None:
            return vid
    air_vid = _version_id_from_air(r.get("air") or "")
    if air_vid is not None:
        return air_vid
    return _as_version_id(r.get("id"))


def _backfill_strength_from_rest(resources: list, rest_resources: list) -> list:
    """When trpc/meta strength is null/missing, copy official REST strength for same versionId.

    NEVER invent 0.8 — only apply a numeric strength present on REST for that version.
    Explicit trpc numeric strength wins; REST null does nothing.
    """
    by_vid = {}
    for r in rest_resources or []:
        if not isinstance(r, dict):
            continue
        vid = _resource_version_id_for_strength(r)
        if vid is None:
            continue
        raw = r.get("strength") if "strength" in r else r.get("weight")
        s = _optional_strength(raw)
        if s is not None:
            by_vid[vid] = s
    if not by_vid:
        return list(resources or [])
    out = []
    for r in resources or []:
        if not isinstance(r, dict):
            out.append(r)
            continue
        row = dict(r)
        if _optional_strength(_resource_strength_raw(row)) is None:
            vid = _resource_version_id_for_strength(row)
            if vid is not None and vid in by_vid:
                row["strength"] = by_vid[vid]
                row.pop("strengthMissing", None)
        out.append(row)
    return out


def import_image(image_id: str) -> dict:
    from . import io_meta

    iid = parse_image_id(image_id)
    q = urllib.parse.quote(json.dumps({"json": {"id": iid}}))
    gen_url = f"https://civitai.com/api/trpc/image.getGenerationData?input={q}"
    info_url = f"https://civitai.com/api/trpc/image.get?input={q}"
    gen_code, gen, info_code, info = 0, {}, 0, {}
    if has_key():
        with ThreadPoolExecutor(max_workers=4) as ex:
            f_gen = ex.submit(civitai, gen_url)
            f_info = ex.submit(civitai, info_url)
            gen_code, gen = f_gen.result()
            info_code, info = f_info.result()
    if not isinstance(gen, dict):
        gen = {}
    if not isinstance(info, dict):
        info = {}
    js = ((gen.get("result") or {}).get("data") or {}).get("json") or {}
    info_js = ((info.get("result") or {}).get("data") or {}).get("json") or {}
    page = {}
    if not (js.get("meta") or js.get("resources") or info_js.get("width")):
        page = generation_from_page(iid)
        if page.get("gen") and not js:
            js = page["gen"]
        if page.get("info") and not info_js:
            info_js = page["info"]
    meta = js.get("meta") or {}
    if not isinstance(meta, dict):
        meta = {}
    public_row = {}
    file_parsed = {}
    if not meta.get("prompt") or not meta.get("sampler"):
        public_row = public_image_row(iid)
        url = (info_js.get("url") or public_row.get("url") or "")
        if isinstance(url, str) and url.startswith("http"):
            try:
                raw = _download_bytes(url)
                file_parsed = io_meta.parse_media_bytes(raw, f"{iid}.png")
            except Exception:
                file_parsed = {}
        if file_parsed and not file_parsed.get("empty"):
            for k, v in file_parsed.items():
                if k in ("empty", "error", "source", "fileName"):
                    continue
                if v not in (None, "", [], {}) and meta.get(k) in (None, "", [], {}):
                    meta[k] = v
    resources = []
    for src in (
        js.get("resources"),
        meta.get("resources"),
        meta.get("civitaiResources"),
        js.get("civitaiResources"),
        (js.get("additionalMeta") or {}).get("resources") if isinstance(js.get("additionalMeta"), dict) else None,
    ):
        if isinstance(src, list):
            resources.extend(x for x in src if isinstance(x, dict))
    # o27: trpc often ships strength=null; official REST /api/generation/data has the real weight.
    # Backfill by versionId only — never invent 0.8 / defaults.
    need_rest_strength = any(
        isinstance(r, dict) and _optional_strength(_resource_strength_raw(r)) is None
        for r in resources
    )
    if need_rest_strength:
        rest = fetch_generation_data_rest(iid)
        rest_resources = rest.get("resources") if isinstance(rest, dict) else None
        if isinstance(rest_resources, list) and rest_resources:
            resources = _backfill_strength_from_rest(resources, rest_resources)
    if not js and not meta and not file_parsed:
        err = gen.get("error") or info.get("error") or ""
        if gen_code == 401 or info_code == 401 or "没有 API Key" in str(err):
            raise ValueError("没有 Civitai API Key，公开页也没读到这张图的提示词 / 底模 / LoRA。把 token 放到 ~/.config/civitai/token，或改上传带 Comfy/A1111 参数的 PNG。")
        raise ValueError(err or f"Civitai 没返回这张图的生成参数（HTTP {gen_code or 404}）")
    media_type = info_js.get("type") or js.get("type") or public_row.get("type") or "image"
    uuid = info_js.get("url") or public_row.get("url") or ""
    name = info_js.get("name") or ""
    media_url = ""
    if isinstance(uuid, str) and uuid.startswith("http"):
        media_url = uuid
    elif uuid:
        ext = "mp4" if str(media_type) == "video" or str(name).endswith(".mp4") else "jpeg"
        media_url = f"https://image.civitai.com/xG1nkqKTMzGDvpLrqFT7WA/{uuid}/original=true/{uuid}.{ext}"
    raw_sampler = meta.get("sampler") or file_parsed.get("sampler") or DEFAULTS["sampler"]
    raw_sched = meta.get("scheduler") or file_parsed.get("scheduler") or ""
    sampler, scheduler = _normalize_pair(raw_sampler, raw_sched)
    need = []
    seen = set()
    for r in resources:
        air = r.get("air")
        vid = r.get("modelVersionId") or r.get("versionId")
        if air:
            continue
        if not vid or vid in seen:
            continue
        seen.add(vid)
        if _version_from_cache(vid):
            continue
        need.append(vid)
    fetched = {}
    if need:
        workers = min(8, len(need))
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futs = {ex.submit(fetch_version_air, vid): vid for vid in need}
            for f in as_completed(futs):
                fetched[futs[f]] = f.result() or {}
    loras = _loras_from_import_sources(resources, meta.get("prompt") or "", fetched)
    checkpoint_air, checkpoint_name = "", ""
    for r in resources:
        vid = r.get("modelVersionId") or r.get("versionId") or r.get("id")
        if vid and not (isinstance(vid, int) or str(vid).isdigit()):
            vid = r.get("modelVersionId") or r.get("versionId")
        ver = fetched.get(vid) or _version_from_cache(vid) or {}
        air = (r.get("air") or ver.get("air") or "").strip()
        typ = r.get("modelType") or r.get("type") or (ver.get("model") or {}).get("type") or ""
        name = r.get("modelName") or r.get("name") or (ver.get("model") or {}).get("name") or ver.get("name") or ""
        if not air:
            mid = r.get("modelId") or ver.get("modelId")
            air = _air_from_ids(mid, vid, typ, r.get("baseModel") or ver.get("baseModel"), name)
        if _is_lora_resource(typ, air, name):
            continue
        if air and (":lora:" in air.lower()):
            continue
        if air or str(typ).upper() in ("CHECKPOINT", "CHECKPOINTTRC", ""):
            if air:
                checkpoint_air = air
                checkpoint_name = name or ""
    if not checkpoint_air:
        guessed = enrich_local_parse({
            "checkpointName": checkpoint_name or meta.get("Model") or meta.get("checkpointName") or "",
            "models": meta.get("models") or file_parsed.get("models") or [],
            "Model": meta.get("Model") or "",
        })
        checkpoint_air = guessed.get("diffusionModel") or ""
        checkpoint_name = guessed.get("checkpointName") or checkpoint_name
    from .io_meta import coerce_int, dims_from_selector, first_int
    selector = None
    for cand in (file_parsed, meta, info_js, public_row):
        if isinstance(cand, dict):
            selector = dims_from_selector(cand) or selector
            for nested in (cand.get("width"), cand.get("inputs"), cand):
                if isinstance(nested, dict) and selector is None:
                    selector = dims_from_selector(nested)
    w = first_int(
        file_parsed.get("width") if isinstance(file_parsed, dict) else None,
        selector[0] if selector else None,
        meta.get("width"),
        info_js.get("width"),
        public_row.get("width"),
        960,
    )
    h = first_int(
        file_parsed.get("height") if isinstance(file_parsed, dict) else None,
        selector[1] if selector else None,
        meta.get("height"),
        info_js.get("height"),
        public_row.get("height"),
        1440,
    )
    w = coerce_int(w, 960) or 960
    h = coerce_int(h, 1440) or 1440
    w, source_w, w_warn = _clamp_import_comfy_dim(w, "width")
    h, source_h, h_warn = _clamp_import_comfy_dim(h, "height")
    dim_warns = [x for x in (w_warn, h_warn) if x]
    kind = "video" if str(media_type) == "video" or "minimax" in (checkpoint_air or "").lower() else "image"
    engine = None
    operation = None
    ecosystem = None
    model = "turbo"
    base_blob = " ".join(str(x or "") for x in (
        checkpoint_air, checkpoint_name, meta.get("engine"), meta.get("Model"),
        public_row.get("baseModel"), info_js.get("baseModel"),
    ))
    if kind == "video":
        engine, operation = "minimax-h3-comfy", "imageToVideo"
    else:
        # Default krea2/turbo only when blob is empty or krea; never keep krea2 for sdxl/pony/flux/…
        engine, operation, ecosystem, model = "comfy", "createImage", "krea2", "turbo"
        eco = _ecosystem_from_blob(base_blob)
        if eco == "krea2" or not eco:
            ecosystem = "krea2"
        elif eco == "sdxl":
            # Stable Diffusion XL / Pony / Illustrious — sdcpp createImage (not krea2 turbo)
            engine, operation, ecosystem, model = "sdcpp", "createImage", "sdxl", None
        elif eco in ("flux", "flux1"):
            # Catalog id is flux1 (blob/AIR often say "flux" / "flux.1"); never leave eco=flux for match_service.
            engine, operation, ecosystem, model = "sdcpp", "createImage", "flux1", None
        elif eco == "wan":
            engine, operation, ecosystem, model = "sdcpp", "createImage", "wan", None
        elif eco == "zImage":
            engine, operation, ecosystem, model = "sdcpp", "createImage", "zImage", None
        elif eco == "qwen":
            engine, operation, ecosystem, model = "sdcpp", "createImage", "qwen", None
        else:
            # Unknown eco from blob — still prefer detected label over silent krea2
            ecosystem = _catalog_ecosystem(eco) or eco
    svc = match_service(engine=engine, operation=operation, ecosystem=ecosystem, model=model, category=kind)
    denoise = meta.get("denoise") if meta.get("denoise") is not None else file_parsed.get("denoise")
    try:
        denoise = float(denoise) if denoise is not None else None
    except (TypeError, ValueError):
        denoise = None
    unmatched = []
    for n in (meta.get("unmatchedNodes") or file_parsed.get("unmatchedNodes") or []):
        unmatched.append(str(n))
    comfy_blob = meta.get("comfy") if isinstance(meta.get("comfy"), dict) else None
    graph = {}
    if isinstance(comfy_blob, dict):
        graph = comfy_blob.get("prompt") or {}
    extra_toks = ("SeedVR2", "Upscale", "ControlNet", "IPAdapter", "InstantID", "PuLID")
    if isinstance(graph, dict):
        for node in graph.values():
            if not isinstance(node, dict):
                continue
            ctype = str(node.get("class_type") or node.get("type") or "")
            if any(tok.lower() in ctype.lower() for tok in extra_toks) and ctype not in unmatched:
                unmatched.append(ctype)
    if meta.get("vaes") or file_parsed.get("vaes"):
        unmatched.append("VAE " + ", ".join((meta.get("vaes") or file_parsed.get("vaes") or [])[:2]))
    node_count = meta.get("comfyNodeCount") or file_parsed.get("comfyNodeCount")
    comfy_blob = meta.get("comfy") if isinstance(meta.get("comfy"), dict) else None
    if comfy_blob and not node_count:
        prompt_graph = comfy_blob.get("prompt") or {}
        if isinstance(prompt_graph, dict):
            node_count = len(prompt_graph)
        wf = comfy_blob.get("workflow") or {}
        if not node_count and isinstance(wf, dict):
            node_count = len(wf.get("nodes") or [])
    sources = []
    if js.get("meta"):
        sources.append("civitai-meta")
    if page.get("gen"):
        sources.append("page")
    if file_parsed and not file_parsed.get("empty"):
        sources.append(file_parsed.get("source") or "png")
    out = {
        "kind": kind,
        "serviceId": (svc or {}).get("id"),
        "serviceName": (svc or {}).get("name"),
        "prompt": meta.get("prompt") or file_parsed.get("prompt") or "",
        "negativePrompt": meta.get("negativePrompt") or file_parsed.get("negativePrompt") or "",
        "width": w,
        "height": h,
        "sourceWidth": source_w,
        "sourceHeight": source_h,
        "steps": int(meta.get("steps") or file_parsed.get("steps") or (20 if kind == "video" else 8)),
        "cfgScale": float(meta.get("cfgScale") if meta.get("cfgScale") is not None else (file_parsed.get("cfgScale") if file_parsed.get("cfgScale") is not None else 1)),
        "sampler": sampler,
        "scheduler": scheduler,
        "seed": meta.get("seed") if meta.get("seed") is not None else file_parsed.get("seed"),
        "denoise": denoise,
        "model": model,
        "engine": engine,
        "operation": operation,
        "ecosystem": ecosystem,
        "diffusionModel": checkpoint_air,
        "checkpointName": checkpoint_name or str(meta.get("Model") or file_parsed.get("checkpointName") or ""),
        "loras": loras,
        "mediaUrl": media_url,
        "mediaType": media_type,
        "duration": 5,
        "firstFrame": "",
        "unmatched": unmatched,
        "comfyNodeCount": node_count,
        "importSource": "+".join(sources) or "partial",
        "empty": not bool(meta.get("prompt") or file_parsed.get("prompt")),
        # Storyboard must land on this backend after import — never leave fal default.
        "backend": "civitai",
    }
    if dim_warns:
        out["paramWarn"] = "；".join(dim_warns)
        out["dimensionAlign"] = True
    return out


def submit(body, whatif=False):
    allow = True if not isinstance(body, dict) else bool(body.get("allowMatureContent", True))
    q = urllib.parse.urlencode({
        "whatif": "true" if whatif else "false",
        "wait": "0",
        "hideMatureContent": "false" if allow else "true",
    })
    return civitai(f"{ORCH}/v2/consumer/workflows?{q}", method="POST", body=body)


def workflow_urls(wf: dict) -> list[str]:
    urls = []
    for step in wf.get("steps") or []:
        out = step.get("output") or {}
        urls.extend(collect_urls(out))
    return urls



def fetch_models(q: str, limit=8, types=None, nsfw=True):
    """GET /api/v1/models. Nested versions have files[].name but no air."""
    qs = {"limit": str(int(limit) or 8), "query": q, "nsfw": "true" if nsfw else "false"}
    if types:
        qs["types"] = types
    return civitai(f"{SITE}/models?" + urllib.parse.urlencode(qs))


def fetch_model_version(vid):
    return civitai(f"{SITE}/model-versions/{vid}")


def fetch_model_version_mini(vid):
    return civitai(f"{SITE}/model-versions/mini/{vid}")


def fetch_model_version_by_hash(h: str):
    return civitai(f"{SITE}/model-versions/by-hash/{urllib.parse.quote(str(h), safe='')}")



def _wait_snapshot(data: dict) -> dict:
    """Flatten real Civitai progress fields. Do not invent percent/ETA."""
    steps = data.get("steps") or []
    step = steps[0] if steps else {}
    jobs = (step.get("jobs") or []) if isinstance(step, dict) else []
    job = jobs[0] if jobs else {}
    q = (job.get("queuePosition") or {}) if isinstance(job, dict) else {}
    prep = (step.get("preparation") or {}) if isinstance(step, dict) else {}
    rate = job.get("estimatedProgressRate")
    if rate is None:
        rate = step.get("estimatedProgressRate")
    if rate is None and prep.get("progress") is not None:
        rate = prep.get("progress")
    eta = prep.get("etaSeconds")
    complete_at = q.get("completeAt")
    if eta is None and complete_at:
        try:
            ts = str(complete_at).replace("Z", "+00:00")
            dt = datetime.fromisoformat(ts)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            sec = (dt - datetime.now(timezone.utc)).total_seconds()
            if sec > 0:
                eta = int(sec)
        except Exception:
            eta = None
    return {
        "progress": rate,
        "precedingJobs": q.get("precedingJobs"),
        "etaSeconds": eta,
        "completeAt": complete_at,
        "log": None,
    }


def _wants_custom_comfy(payload: dict) -> bool:
    """True only when the user is on the workflow tab / sending a graph.

    A Civitai imageGen serviceId like image/comfy/krea2/... is NOT customComfy.
    """
    pld = payload or {}
    if pld.get("recipe") == "workflow":
        return True
    if pld.get("step") == "customComfy":
        return True
    if pld.get("comfyWorkflow") or pld.get("workflow"):
        return True
    return False


def _resource_airs(payload: dict) -> list:
    raw = (payload or {}).get("resources") or []
    out = []
    for x in raw if isinstance(raw, list) else []:
        if isinstance(x, str) and x.strip():
            out.append(x.strip())
        elif isinstance(x, dict):
            air = (x.get("air") or x.get("urn") or "").strip()
            if air:
                out.append(air)
    return out


def _extract_caption(data) -> str:
    if isinstance(data, str) and data.strip():
        return data.strip()
    if not isinstance(data, dict):
        return ""
    for key in ("caption", "text", "prompt", "description"):
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    for step in data.get("steps") or []:
        if not isinstance(step, dict):
            continue
        found = _extract_caption(step.get("output") or step.get("result") or {})
        if found:
            return found
    blobs = data.get("blobs") or data.get("output") or {}
    if isinstance(blobs, dict):
        found = _extract_caption(blobs)
        if found:
            return found
    return ""


def caption_media(media_url: str, model: str = "joy-caption") -> tuple[int, dict]:
    """POST orchestration mediaCaptioning recipe. Real vision caption, never a fixed string."""
    url = (media_url or "").strip()
    if not url:
        return 400, {"error": "缺少 mediaUrl", "code": "missing_url", "backend": "civitai"}
    if not has_key():
        return 401, {"error": "没有 Civitai API Key", "code": "no_key", "backend": "civitai"}
    chosen = (model or "joy-caption").strip() or "joy-caption"
    if chosen not in ("joy-caption", "ideogram4"):
        chosen = "joy-caption"
    body = {"mediaUrl": url, "model": chosen}
    code, data = civitai(
        f"{ORCH}/v2/consumer/recipes/mediaCaptioning?whatif=false",
        method="POST",
        body=body,
        timeout=120,
    )
    if not isinstance(data, dict):
        return 502, {"error": f"Civitai caption 返回无法解析（HTTP {code}）", "backend": "civitai"}
    if code >= 400:
        return code, {
            "error": extract_error(data, data.get("title") or f"Civitai caption HTTP {code}"),
            "code": "caption_failed",
            "backend": "civitai",
        }
    caption = _extract_caption(data)
    if caption:
        return 200, {"caption": caption, "backend": "civitai", "model": chosen}
    wf_id = data.get("id") or data.get("workflowId") or data.get("token")
    if not wf_id:
        return 502, {
            "error": "Civitai caption 未返回描述",
            "backend": "civitai",
            "raw": {k: data.get(k) for k in list(data)[:12]},
        }
    deadline = time.time() + 90
    last = data
    while time.time() < deadline:
        time.sleep(1.5)
        poll, last = civitai(f"{ORCH}/v2/consumer/workflows/{wf_id}")
        if not isinstance(last, dict):
            continue
        caption = _extract_caption(last)
        if caption:
            return 200, {
                "caption": caption,
                "backend": "civitai",
                "model": chosen,
                "workflowId": wf_id,
            }
        st = str(last.get("status") or "").lower()
        if st in ("failed", "canceled", "cancelled", "error"):
            return 502, {
                "error": extract_error(last, f"Civitai caption {st}"),
                "backend": "civitai",
                "workflowId": wf_id,
            }
        if poll >= 400 and st not in ("pending", "processing", "queued"):
            break
    return 504, {
        "error": "Civitai caption 超时，没有拿到描述",
        "backend": "civitai",
        "workflowId": wf_id,
    }



def _civitai_media_ref_audit(inp: dict | None) -> dict:
    """Lengths only — never dump data URL bytes. Used for generate audit / 核."""
    inp = inp if isinstance(inp, dict) else {}
    imgs = inp.get("images")
    if not isinstance(imgs, list):
        imgs = inp.get("referenceImages") if isinstance(inp.get("referenceImages"), list) else []
    n_data = 0
    n_http = 0
    n_out = 0
    lenses: list[int] = []
    for u in imgs:
        if not isinstance(u, str):
            lenses.append(0)
            continue
        lenses.append(len(u))
        if u.startswith("data:"):
            n_data += 1
        elif u.startswith(("http://", "https://")):
            n_http += 1
        elif u.startswith("/out/") or (u and not u.startswith(("http://", "https://", "data:"))):
            n_out += 1
    return {
        "nRefs": len(imgs),
        "nDataUrls": n_data,
        "nHttpUrls": n_http,
        "nOutPaths": n_out,
        "imageUrlLens": lenses,
    }


class CivitaiProvider(Provider):
    id = "civitai"
    label = "Civitai"

    def __init__(self):
        load_catalog_disk()

    def has_key(self) -> bool:
        return has_key()

    def categories(self) -> list:
        items, _, _ = catalog_items()
        return sorted({x.get("category") for x in items if x.get("category")})

    def catalog(self, q, category, status) -> dict:
        warning = None
        try:
            items, fetched, total = catalog_items()
        except Exception:
            load_catalog_disk()
            items, fetched, total = catalog_items()
            warning = "目录读取失败，已用本地缓存"
        if not items:
            load_catalog_disk()
            items, fetched, total = catalog_items()
        out = items
        cat = category or ""
        st = status or ""
        qn = (q or "").lower()
        def _alnum(s):
            return "".join(ch for ch in (s or "").lower() if ch.isalnum())
        if cat:
            out = [x for x in out if x.get("category") == cat]
        if st:
            out = [x for x in out if x.get("status") == st]
        if qn:
            needle = _alnum(qn)
            out = [x for x in out if needle in _alnum(x.get("name")) or needle in _alnum(x.get("id")) or needle in _alnum(x.get("engine")) or needle in _alnum(x.get("ecosystem"))]
        body = {
            "total": total,
            "count": len(out),
            "fetchedAt": fetched,
            "items": out,
            "backend": "civitai",
        }
        if warning:
            body["warning"] = warning
        return body

    def owns_service(self, service_id: str) -> bool:
        sid = (service_id or "").strip()
        if not sid:
            return False
        if find_service(sid):
            return True
        return sid.startswith(("image/", "video/", "audio/", "3d/"))

    def owns_job(self, job_id: str) -> bool:
        pid, _ = parse_job_id(job_id)
        return pid == self.id

    def generate(self, payload: dict):
        if _wants_custom_comfy(payload):
            return self.run_custom_comfy(payload, whatif=False)
        try:
            body = build_workflow(payload or {})
        except ValueError as e:
            return 400, {"error": str(e)}
        meta = body.pop("_meta", {})
        code, data = submit(body, whatif=False)
        if isinstance(data, dict):
            data["service"] = meta
            inp = body["steps"][0]["input"] if body.get("steps") else {}
            submitted = dict(inp)
            submitted["serviceId"] = meta.get("serviceId")
            data["submittedInput"] = submitted
            data["backend"] = "civitai"
            audit = _civitai_media_ref_audit(inp)
            data.update(audit)
            print(
                "[civitai] generate-audit",
                json.dumps({
                    "serviceId": meta.get("serviceId"),
                    **audit,
                }, ensure_ascii=False)[:800],
                flush=True,
            )
            if not data.get("id"):
                data["id"] = data.get("workflowId") or data.get("token")
        return code, data

    def whatif(self, payload: dict):
        if _wants_custom_comfy(payload):
            return self.run_custom_comfy(payload, whatif=True)
        try:
            body = build_workflow(payload or {})
        except ValueError as e:
            return 400, {"error": str(e)}
        meta = body.pop("_meta", {})
        code, data = submit(body, whatif=True)
        if isinstance(data, dict):
            data["service"] = meta
            inp = body["steps"][0]["input"] if body.get("steps") else {}
            submitted = dict(inp)
            submitted["serviceId"] = meta.get("serviceId")
            data["submittedInput"] = submitted
            data["backend"] = "civitai"
            audit = _civitai_media_ref_audit(inp)
            data.update(audit)
        return code, data

    def job_status(self, job_id: str):
        _, opaque = parse_job_id(job_id)
        wf_id = opaque or job_id
        code, data = civitai(f"{ORCH}/v2/consumer/workflows/{wf_id}")
        if isinstance(data, dict):
            st = (data.get("status") or "").lower()
            data["status"] = st
            if not data.get("id"):
                data["id"] = data.get("workflowId") or data.get("token") or wf_id
            data["wait"] = _wait_snapshot(data)
            if st == "succeeded":
                try:
                    data["saved"] = save_media_urls(workflow_urls(data), wf_id)
                except Exception as e:
                    data["saveError"] = str(e)
        return code, data

    def cancel_job(self, job_id: str):
        _, opaque = parse_job_id(job_id)
        wf_id = opaque or job_id
        if not wf_id:
            return 400, {"error": "缺少 Civitai 任务 id"}
        code, data = civitai(f"{ORCH}/v2/consumer/workflows/{wf_id}", method="DELETE")
        if code in (200, 202, 204):
            return 200, {
                "id": wf_id,
                "backend": "civitai",
                "status": "canceled",
            }
        if isinstance(data, dict):
            data.setdefault("error", data.get("message") or data.get("title") or f"Civitai 取消 HTTP {code}")
            return code if code >= 400 else 400, data
        return code if code >= 400 else 400, {"error": f"Civitai 取消 HTTP {code}"}

    def import_image(self, image_id: str) -> dict:
        return import_image(image_id)

    def refresh_catalog(self) -> dict:
        return refresh_catalog()

    def health(self):
        return civitai(f"{ORCH}/health")

    def services(self, limit="50", offset="0"):
        return civitai(f"{ORCH}/v2/services?limit={urllib.parse.quote(str(limit))}&offset={urllib.parse.quote(str(offset))}")

    def list_jobs(self):
        return civitai(f"{ORCH}/v2/consumer/workflows")

    def blobs(self, blob_id: str):
        return civitai(f"{ORCH}/v2/consumer/blobs?blobId={urllib.parse.quote(blob_id)}")

    def search_models(self, q: str, types="LORA", nsfw=True):
        code, data = fetch_models(q, limit=8, types=types or None, nsfw=nsfw)
        items = []
        if isinstance(data, dict):
            for it in (data.get("items") or [])[:8]:
                vers = []
                for v in (it.get("modelVersions") or [])[:6]:
                    files = [{"name": f.get("name"), "id": f.get("id")} for f in (v.get("files") or [])]
                    vers.append({"id": v.get("id"), "name": v.get("name"), "baseModel": v.get("baseModel"), "files": files})
                items.append({"id": it.get("id"), "name": it.get("name"), "type": it.get("type"), "source": "civitai", "versions": vers})
        return code, {"items": items}

    def search_loras(self, q: str, nsfw: bool = True):
        return self.search_models(q, types="LORA", nsfw=nsfw)

    def model_version(self, vid: str):
        code, data = fetch_model_version(vid)
        if isinstance(data, dict):
            return code, {
                "id": data.get("id"),
                "name": data.get("name"),
                "air": data.get("air"),
                "baseModel": data.get("baseModel"),
                "model": (data.get("model") or {}).get("name"),
                "type": (data.get("model") or {}).get("type"),
                "trainedWords": data.get("trainedWords") or [],
            }
        return code, data

    def recipe(self, recipe: str, payload: dict):
        q = urllib.parse.urlencode({
            "whatif": "true" if (payload or {}).get("whatif") else "false",
            "allowMatureContent": "true" if (payload or {}).get("allowMatureContent", True) else "false",
        })
        body = (payload or {}).get("input") or payload
        return civitai(f"{ORCH}/v2/consumer/recipes/{recipe}?{q}", method="POST", body=body)

    def capabilities(self):
        fp = DOCS / "capabilities.json"
        if not fp.exists():
            return 404, {"error": "no capabilities.json"}
        return 200, json.loads(fp.read_text())

    def defaults_payload(self) -> dict:
        items, fetched, total = catalog_items()
        return {
            "defaults": DEFAULTS,
            "samplers": SAMPLERS,
            "schedulers": SCHEDULERS,
            "catalogTotal": total,
            "catalogFetchedAt": fetched,
            "categories": sorted({x.get("category") for x in items if x.get("category")}),
        }

    def lookup_air_file(self, filename: str):
        from . import civitai_workflows as cw
        rec = cw.lookup_filename(filename or "")
        return 200, rec

    def list_workflows(self, q="", username="", limit=30, nsfw=True):
        from .civitai_workflows import MOODY_USER
        qs = {"types": "Workflows", "limit": str(int(limit) or 30), "nsfw": "true" if nsfw else "false"}
        if q:
            qs["query"] = q
        user = username or (MOODY_USER if not q else "")
        if user:
            qs["username"] = user
        url = f"{SITE}/models?" + urllib.parse.urlencode(qs)
        code, data = civitai(url)
        items = []
        if isinstance(data, dict):
            for it in data.get("items") or []:
                vers = it.get("modelVersions") or []
                v = vers[0] if vers else {}
                items.append({
                    "id": it.get("id"),
                    "name": it.get("name"),
                    "type": it.get("type"),
                    "nsfw": it.get("nsfw"),
                    "versionId": v.get("id"),
                    "versionName": v.get("name"),
                    "air": v.get("air"),
                    "url": f"https://civitai.com/models/{it.get('id')}?modelVersionId={v.get('id')}",
                })
        return 200 if code == 200 else code, {"items": items, "username": user, "q": q}

    def import_workflow(self, raw: str, version_id=None):
        from . import civitai_workflows as cw
        ref = cw.parse_workflow_ref(raw)
        vid = version_id or ref.get("versionId")
        mid = ref.get("modelId")
        if not vid and mid:
            code, model = civitai(f"{SITE}/models/{mid}")
            if code != 200 or not isinstance(model, dict):
                return code if code >= 400 else 404, {"error": "找不到这个工作流模型"}
            vers = model.get("modelVersions") or []
            if not vers:
                return 404, {"error": "这个模型没有版本"}
            vid = vers[0].get("id")
            meta_model = model
        else:
            meta_model = None
        code, ver = civitai(f"{SITE}/model-versions/{vid}")
        if code != 200 or not isinstance(ver, dict):
            return code if code >= 400 else 404, {"error": "找不到工作流版本"}
        files = ver.get("files") or []
        cands = cw.pick_workflow_files(files)
        if not cands:
            return 404, {"error": "这个版本没有 JSON / zip 工作流文件"}
        tok = token()

        class _StripAuthRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, req, fp, code, msg, headers, newurl):
                if "civitai.com" not in (urllib.parse.urlparse(newurl).hostname or ""):
                    headers = {k: v for k, v in req.headers.items() if k.lower() != "authorization"}
                    return urllib.request.Request(newurl, headers=headers, method="GET")
                return super().redirect_request(req, fp, code, msg, headers, newurl)

        opener = urllib.request.build_opener(_StripAuthRedirect)
        wf = None
        json_file = None
        last_err = None
        for cand in cands:
            fid = cand.get("id")
            dl = f"https://civitai.com/api/download/models/{vid}" + (f"?fileId={fid}" if fid else "")
            req = urllib.request.Request(dl, headers={"Authorization": f"Bearer {tok}", "User-Agent": "Mozilla/5.0"})
            try:
                with opener.open(req, timeout=90) as r:
                    raw_bytes = r.read()
                wf = cw.parse_workflow_bytes(raw_bytes)
                json_file = cand
                break
            except ValueError as e:
                last_err = e
                continue
            except Exception as e:
                last_err = e
                continue
        if wf is None:
            return 400, {"error": str(last_err or "工作流文件不是合法 JSON")}
        cache = cw.CACHE / f"{vid}.json"
        cache.write_text(json.dumps(wf, ensure_ascii=False), encoding="utf-8")
        api_wf = cw.ui_to_api(wf)
        summary = cw.summarize(wf, meta={
            "modelId": ver.get("modelId") or mid,
            "versionId": vid,
            "name": (ver.get("model") or {}).get("name") or (meta_model or {}).get("name"),
            "versionName": ver.get("name"),
            "file": json_file.get("name"),
            "air": ver.get("air"),
        })
        summary["apiNodes"] = len(api_wf)
        summary["workflowApi"] = api_wf
        mapped = cw.resolve_resources(wf)
        summary["resources"] = mapped.get("resources") or []
        summary["airMap"] = mapped
        n_file_ok = sum(1 for x in (mapped.get("files") or []) if x.get("status") == "matched")
        n_file_miss = len(mapped.get("unmatchedFiles") or [])
        n_node_ok = sum(len(x.get("nodes") or []) for x in (mapped.get("nodepacks") or []) if x.get("status") == "matched")
        n_node_miss = len(mapped.get("unmatchedNodes") or [])
        n_ok = n_file_ok + n_node_ok
        n_miss = n_file_miss + n_node_miss
        summary["warning"] = f"{n_ok} matched / {n_miss} unmatched"
        return 200, summary

    def run_custom_comfy(self, payload, whatif=False):
        from . import civitai_workflows as cw
        api_wf = payload.get("comfyWorkflow") or payload.get("workflow")
        if isinstance(api_wf, dict) and api_wf.get("nodes"):
            api_wf = cw.ui_to_api(api_wf)
        if not api_wf:
            return 400, {"error": "没有工作流图"}
        edits = payload.get("promptEdits") or []
        if edits:
            api_wf = cw.apply_prompt_edits(api_wf, edits)
        resources = [x for x in (payload.get("resources") or []) if isinstance(x, str) and x.strip()]
        mapped = None
        if not resources:
            mapped = cw.resolve_resources(api_wf)
            resources = list(mapped.get("resources") or [])
        if not resources:
            return 400, {
                "error": "customComfy 必须声明 resources（AIR）。这个工作流没有映射到任何权重或节点包。",
                "airMap": mapped,
            }
        bare_packs = [
            a for a in resources
            if isinstance(a, str) and ":nodepack:" in a.lower() and ":nodepacklayer:" not in a.lower()
        ]
        if bare_packs:
            shown = "、".join(bare_packs[:3])
            return 400, {
                "error": (
                    "Civitai customComfy 要求自定义节点用 install-layer AIR"
                    "（urn:air:comfy:nodepacklayer:…），当前映射还是裸 nodepack。"
                    f"这个工作流含：{shown}。先走图片 Tab 出图；没有官方 nodepacklayer 样例前不改 URN。"
                ),
                "resources": resources,
                "bareNodepacks": bare_packs,
            }
        body = {
            "workflow": api_wf,
            "resources": resources,
            "trace": payload.get("trace") or "none",
        }
        ci = payload.get("comfyImage") or ""
        if isinstance(ci, str) and ci.startswith("urn:air:") and "comfyimage" in ci.lower():
            body["comfyImage"] = ci
        # Do not send sessionOwnerApiToken.
        return self.recipe("customComfy", {"input": body, "whatif": whatif, "allowMatureContent": payload.get("allowMatureContent", True)})


from . import register  # noqa: E402

register(CivitaiProvider())
