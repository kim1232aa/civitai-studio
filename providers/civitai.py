from __future__ import annotations

import json
import re
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from .base import Provider
from .capabilities import get_provider_capabilities
from .http import collect_urls, json_call, parse_job_id, save_media_urls

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
    for it in items:
        if category and it.get("category") != category:
            continue
        s = 0
        if engine and it.get("engine") == engine:
            s += 4
        if operation and it.get("operation") == operation:
            s += 3
        if ecosystem and it.get("ecosystem") == ecosystem:
            s += 2
        if model and it.get("model") == model:
            s += 1
        if s:
            if it.get("status") == "available":
                s += 2
            scored.append((s, it))
    scored.sort(key=lambda x: -x[0])
    return scored[0][1] if scored else None


def lora_map(payload: dict) -> dict:
    out = {}
    for item in payload.get("loras") or []:
        air = (item.get("air") or "").strip()
        if not air:
            continue
        try:
            out[air] = float(item.get("strength", 1))
        except (TypeError, ValueError):
            out[air] = 1.0
    return out


def _set_int(inp, payload, key, lo=None, hi=None):
    if payload.get(key) in (None, ""):
        return
    from .io_meta import coerce_int
    v = coerce_int(payload.get(key), None)
    if v is None:
        return
    if lo is not None:
        v = max(lo, v)
    if hi is not None:
        v = min(hi, v)
    inp[key] = v


def _set_float(inp, payload, key):
    if payload.get(key) in (None, ""):
        return
    try:
        inp[key] = float(payload[key])
    except (TypeError, ValueError):
        pass


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


def _cap_meta(c: dict, key: str):
    """capabilities.json 的 version / provider 只存在 defaults 里，顶层恒为 None。"""
    v = c.get(key)
    if v in (None, ""):
        v = (c.get("defaults") or {}).get(key)
    return v


def find_cap(engine=None, operation=None, version=None, provider=None, model=None):
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
        if version and _cap_meta(c, "version") == version:
            s += 4
        if model and _cap_meta(c, "model") == model:
            s += 4
        if provider and _cap_meta(c, "provider") == provider:
            s += 1
        if s > score:
            best, score = c, s
    return best


def apply_frames(inp: dict, payload: dict, svc: dict | None):
    engine = (inp.get("engine") or (svc or {}).get("engine") or "")
    op = (inp.get("operation") or (svc or {}).get("operation") or "")
    cap = find_cap(engine, op,
                   inp.get("version") or (svc or {}).get("version"),
                   inp.get("provider") or (svc or {}).get("provider"),
                   inp.get("model") or (svc or {}).get("model"))
    frames = list((cap or {}).get("frameFields") or [])
    first = (payload.get("firstFrame") or payload.get("sourceImage") or payload.get("startImage") or payload.get("image") or "").strip()
    last = (payload.get("lastFrame") or payload.get("endImage") or payload.get("endSourceImage") or "").strip()
    extra = [x for x in (payload.get("images") or payload.get("referenceImages") or []) if x]
    if first and first not in extra:
        extra = [first] + extra
    FIRST_NAMES = {"firstFrame", "sourceImage", "image", "sourceImageUrl"}
    LAST_NAMES = {"lastFrame", "endImage", "endSourceImage"}
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
        if extra and ("edit" in str(op).lower() or "variant" in str(op).lower()):
            frames = ["images"]
        elif first:
            frames = ["firstFrame", "image"]
    for name in frames:
        if name in FIRST_NAMES and first:
            inp[name] = first
        elif name in LAST_NAMES and last:
            inp[name] = last
        elif name == "startImage" and first:
            inp[name] = first
        elif name == "images" and extra:
            inp[name] = extra[:9]
        elif name == "referenceImages" and extra:
            inp[name] = extra[:9]
        elif name == "sourceVideo" and payload.get("sourceVideo"):
            inp[name] = payload["sourceVideo"]
        elif name == "sourceAudio" and payload.get("sourceAudio"):
            inp[name] = payload["sourceAudio"]
        elif name == "videoUrl" and payload.get("videoUrl"):
            inp[name] = payload["videoUrl"]
        elif name == "maskImage" and payload.get("maskImage"):
            inp[name] = payload["maskImage"]
    flags = (cap or {}).get("extraFlags") or {}
    if flags.get("turbo") is not None or engine == "minimax-h3-comfy":
        if payload.get("turbo") is not None:
            inp["turbo"] = bool(payload.get("turbo"))
    if flags.get("fast") is not None or engine == "minimax-h3-comfy":
        if payload.get("fast") is not None:
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


_WH_TOKEN = re.compile(r"^\s*(\d{2,5})\s*[x\u00d7*]\s*(\d{2,5})\s*$", re.I)


def _split_free_wh(inp: dict, payload: dict, cap: dict | None) -> None:
    """把 `720x1280` 拆成 width/height；显式 width/height 优先。"""
    m = _WH_TOKEN.match(str(payload.get("resolution") or ""))
    if not m:
        return
    fields = set((cap or {}).get("required") or []) | set((cap or {}).get("optional") or [])
    if "resolution" in fields:
        return  # 服务本身收 resolution 令牌，别动
    if payload.get("width") in (None, "") and payload.get("height") in (None, ""):
        inp["width"] = max(16, min(2048, int(m.group(1))))
        inp["height"] = max(16, min(2048, int(m.group(2))))
    inp.pop("resolution", None)


_RES_TOKEN = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*([pkPK])?\s*$")


def _token_pixels(tok) -> int | None:
    """把 `720p` / `1080p` / `2K` / 整数 720 折成可比的短边像素数。"""
    if isinstance(tok, bool):
        return None
    if isinstance(tok, (int, float)):
        return int(tok)
    m = _RES_TOKEN.match(str(tok))
    if not m:
        return None
    n = float(m.group(1))
    return int(n * 1024) if (m.group(2) or "p").lower() == "k" else int(n)


def _aspect_of(w: int, h: int) -> str:
    from math import gcd

    g = gcd(w, h) or 1
    return f"{w // g}:{h // g}"


def _cap_fields(cap: dict | None) -> set:
    cap = cap or {}
    return (set(cap.get("required") or []) | set(cap.get("optional") or [])
            | set((cap.get("constraints") or {}).keys()))


def _snap_enum_resolution(inp: dict, payload: dict, cap: dict | None) -> bool:
    """枚举令牌家族（视频 wan/seedance/sora…、图片 nano-banana/grok）只认 `720p`/`1K`。

    UI 一律发 `720x1280`（WxH），落到这类服务上是非法枚举值，云端打回或按默认档渲染，
    而且竖屏意图整个丢掉 —— 这些服务的朝向靠 aspectRatio，不靠 WxH。
    返回 True 表示该服务归令牌家族（调用方就别再走 free_wh 拆分了）。
    """
    cons = ((cap or {}).get("constraints") or {}).get("resolution") or {}
    enum = cons.get("enum")
    if not enum:
        return False
    m = _WH_TOKEN.match(str(payload.get("resolution") or ""))
    if not m:
        return True  # 已经是令牌（或没给），不动
    w, h = int(m.group(1)), int(m.group(2))
    usable = [(v, _token_pixels(v)) for v in enum]
    usable = [(v, px) for v, px in usable if px]
    if usable:
        tier = min(w, h)
        fit = [t for t in usable if t[1] <= tier]
        inp["resolution"] = (max(fit, key=lambda t: t[1]) if fit else min(usable, key=lambda t: t[1]))[0]
    else:
        dv = ((cap or {}).get("defaults") or {}).get("resolution")
        inp["resolution"] = dv if dv in enum else enum[0]
    fields = _cap_fields(cap)
    if "aspectRatio" in fields and not payload.get("aspectRatio"):
        ar = _aspect_of(w, h)
        ar_enum = ((cap or {}).get("constraints") or {}).get("aspectRatio", {}).get("enum")
        if not ar_enum or ar in ar_enum:
            inp["aspectRatio"] = ar
    if "width" not in fields and "height" not in fields:
        inp.pop("width", None)
        inp.pop("height", None)
    return True


def _provider_id(payload: dict) -> str:
    return "civitai"


def build_workflow(payload: dict) -> dict:
    svc = None
    sid = (payload.get("serviceId") or "").strip()
    if sid:
        svc = find_service(sid)
    kind = payload.get("kind") or (svc or {}).get("category") or "image"
    if not svc:
        if kind == "video":
            svc = match_service(
                engine=payload.get("engine"),
                operation=payload.get("operation"),
                category="video",
            ) or find_service(DEFAULTS["videoServiceId"])
        else:
            svc = match_service(
                engine=payload.get("engine") or "comfy",
                operation=payload.get("operation") or "createImage",
                ecosystem=payload.get("ecosystem") or "krea2",
                model=payload.get("model"),
                category="image",
            ) or find_service(DEFAULTS["serviceId"])
    inp = dict((svc or {}).get("parameters") or {})
    for k in ("engine", "operation", "ecosystem", "model", "version", "provider"):
        if payload.get(k):
            inp[k] = payload[k]
    if payload.get("prompt"):
        inp["prompt"] = payload["prompt"]
    if payload.get("negativePrompt"):
        inp["negativePrompt"] = payload["negativePrompt"]
    _set_int(inp, payload, "width", 16, 2048)
    _set_int(inp, payload, "height", 16, 2048)
    _set_int(inp, payload, "steps", 1, 150)
    _set_int(inp, payload, "quantity", 1, 12)
    _set_int(inp, payload, "duration", 1, 30)
    _set_float(inp, payload, "cfgScale")
    if payload.get("sampler"):
        inp["sampler"] = payload["sampler"]
    if payload.get("scheduler"):
        inp["scheduler"] = payload["scheduler"]
    if payload.get("denoise") not in (None, ""):
        try:
            inp["denoise"] = float(payload["denoise"])
        except (TypeError, ValueError):
            pass
    if payload.get("resolution"):
        inp["resolution"] = payload["resolution"]
    if payload.get("aspectRatio"):
        inp["aspectRatio"] = payload["aspectRatio"]
    if payload.get("outputFormat") in ("jpeg", "png", "webP"):
        inp["outputFormat"] = payload["outputFormat"]
    seed = payload.get("seed")
    if seed not in (None, "", "random"):
        try:
            inp["seed"] = int(seed)
        except (TypeError, ValueError):
            pass
    dm = (payload.get("diffusionModel") or "").strip()
    if dm:
        inp["diffusionModel"] = dm
    loras = lora_map(payload)
    if loras:
        inp["loras"] = loras
    cap = apply_frames(inp, payload, svc)
    fill_required(inp, payload, cap)
    # free_wh 服务只认 width/height。`720x1280` 原样透传会被下面的 allowed 过滤掉，
    # Civitai 回落到 catalog defaults 1024x1024（真扣费复现过）。
    # 只拆 WxH；视频的 `720p`/`1080p` 是 catalog 令牌，cap 里声明了 resolution 的一律不动。
    if not _snap_enum_resolution(inp, payload, cap):
        if get_provider_capabilities(_provider_id(payload)).get("resolution") == "free_wh":
            _split_free_wh(inp, payload, cap)
    if cap:
        allowed = {"engine", "operation", "ecosystem", "model", "version", "provider",
                   "prompt", "negativePrompt", "loras", "diffusionModel", "seed",
                   "steps", "width", "height", "cfgScale", "quantity", "duration",
                   "sampler", "scheduler", "denoise"}
        for lst in (cap.get("required"), cap.get("optional"), cap.get("frameFields"), list((cap.get("constraints") or {}).keys()), list((cap.get("extraFlags") or {}).keys())):
            if lst:
                allowed.update(lst)
        inp = {k: v for k, v in inp.items() if k in allowed}
        if inp.get("engine") == "hunyuan" and isinstance(inp.get("loras"), dict):
            inp["loras"] = [{"air": k, "strength": v} for k, v in inp["loras"].items()]
    step = (svc or {}).get("step") or ("videoGen" if kind == "video" else "imageGen")
    return {
        "allowMatureContent": bool(payload.get("allowMatureContent", True)),
        "steps": [{"$type": step, "input": inp}],
        "_meta": {"serviceId": (svc or {}).get("id"), "serviceName": (svc or {}).get("name")},
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
    if "flux" in blob:
        return "flux"
    if "wan" in blob:
        return "wan"
    if "sdxl" in blob or "pony" in blob or "illustrious" in blob:
        return "sdxl"
    return ""


def _air_from_ids(model_id, version_id, typ="", base="", name=""):
    try:
        mid = int(model_id)
        vid = int(version_id)
    except (TypeError, ValueError):
        return ""
    eco = _ecosystem_from_blob(base, name, typ) or "krea2"
    kind = "lora" if _is_lora_resource(typ, "", name or "") else "diffusionmodel"
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


def _prompt_lora_tags(prompt: str) -> list:
    out = []
    seen = set()
    for name, weight in _LORA_TAG_RE.findall(prompt or ""):
        key = name.strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        try:
            strength = float(weight) if weight else 0.8
        except (TypeError, ValueError):
            strength = 0.8
        out.append({"name": name.strip(), "strength": strength})
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
    loras, checkpoint_air, checkpoint_name = [], "", ""
    seen_lora = set()
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
        strength_raw = r.get("strength") if r.get("strength") is not None else r.get("weight")
        try:
            strength = float(strength_raw) if strength_raw is not None else 0.8
        except (TypeError, ValueError):
            strength = 0.8
        if _is_lora_resource(typ, air, name):
            key = str(vid or air or name).lower()
            if key in seen_lora:
                continue
            seen_lora.add(key)
            item = {
                "air": air,
                "strength": strength,
                "name": name or "LoRA",
            }
            if vid:
                item["versionId"] = vid
            path = ""
            for f in (ver.get("files") or []):
                if isinstance(f, dict) and (f.get("downloadUrl") or f.get("download_url")):
                    path = f.get("downloadUrl") or f.get("download_url")
                    break
            if not path and vid:
                path = f"https://civitai.com/api/download/models/{vid}"
            if path:
                item["path"] = path
                item["downloadUrl"] = path
            loras.append(item)
        elif air or str(typ).upper() in ("CHECKPOINT", "CHECKPOINTTRC", ""):
            if air and (":lora:" in air.lower()):
                continue
            if air:
                checkpoint_air = air
                checkpoint_name = name or ""
    for tag in _prompt_lora_tags(meta.get("prompt") or ""):
        key = tag["name"].lower()
        if any(key == str(x.get("name") or "").lower() or key in str(x.get("air") or "").lower() for x in loras):
            continue
        loras.append({
            "air": "",
            "strength": tag["strength"],
            "name": tag["name"],
        })
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
    w = max(64, min(2048, (w // 16) * 16 or 16))
    h = max(64, min(2048, (h // 16) * 16 or 16))
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
        engine, operation, ecosystem, model = "comfy", "createImage", "krea2", "turbo"
        eco = _ecosystem_from_blob(base_blob)
        if eco == "krea2":
            ecosystem = "krea2"
        elif eco == "zImage":
            engine, ecosystem = "sdcpp", "zImage"
        elif eco == "qwen":
            engine, ecosystem = "sdcpp", "qwen"
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
    }
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
        body = build_workflow(payload or {})
        meta = body.pop("_meta", {})
        code, data = submit(body, whatif=False)
        if isinstance(data, dict):
            data["service"] = meta
            data["submittedInput"] = {"serviceId": meta.get("serviceId")}
            data["backend"] = "civitai"
            if not data.get("id"):
                data["id"] = data.get("workflowId") or data.get("token")
        return code, data

    def whatif(self, payload: dict):
        if _wants_custom_comfy(payload):
            return self.run_custom_comfy(payload, whatif=True)
        body = build_workflow(payload or {})
        meta = body.pop("_meta", {})
        code, data = submit(body, whatif=True)
        if isinstance(data, dict):
            data["service"] = meta
            data["submittedInput"] = body["steps"][0]["input"] if body.get("steps") else {"serviceId": meta.get("serviceId")}
            data["backend"] = "civitai"
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
