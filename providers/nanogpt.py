from __future__ import annotations

import copy
import json
import os
import re
import time
import uuid
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import parse_qsl, quote, urlencode, urljoin, urlparse, urlunparse

from .base import Provider
from .http import collect_urls, extract_error, json_call, parse_job_id, save_bytes, save_media_urls
from .io_meta import looks_like_civitai_service

TOKEN_PATH = Path.home() / ".config/nano-gpt/token"
CIVITAI_TOKEN_PATH = Path.home() / ".config/civitai/token"
ROOT = Path(__file__).resolve().parent.parent
_CIVITAI_DL_RE = re.compile(
    r"^https?://(?:www\.)?civitai\.com/api/download/models/(\d+)(?:\?.*)?$",
    re.I,
)
_HF_REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
BASE = "https://nano-gpt.com"
API = BASE + "/api/v1"
IMG_MODELS = API + "/images/models"
VID_MODELS = API + "/video-models"
TEXT_MODELS = API + "/models?detailed=true"
GEN_IMAGES = API + "/images"
GEN_IMAGES_OAI = BASE + "/v1/images/generations"
GEN_VIDEO = BASE + "/api/generate-video"
VIDEO_STATUS = BASE + "/api/video/status"
CHAT_COMPLETIONS = BASE + "/v1/chat/completions"

STORY_DIRECTOR_SYSTEM = (
    "你是一位专业的故事导演（story director）。"
    "根据用户给出的主体、场景或设定，推演出一段适合分镜创作的故事梗概："
    "包含起承转合、关键场景节拍、每个节拍的画面感（构图/情绪/光线线索），"
    "以及可直接复用到下一步生图/生视频提示词的具体描述。"
    "输出用中文，分点列出节拍，不要写成小说体大段散文。"
)

_CACHE = {"at": 0.0, "items": None}
_TTL = 300

# Nano Image API rejects prompts over this many characters with HTTP 400
# code prompt_too_long (observed: "1408 > 1200"). Keep FE/server in sync.
NANO_PROMPT_MAX = 1200


def prompt_length_error(prompt) -> dict | None:
    """Return 400 body if prompt exceeds NANO_PROMPT_MAX; else None."""
    text = prompt if isinstance(prompt, str) else ("" if prompt is None else str(prompt))
    n = len(text)
    if n <= NANO_PROMPT_MAX:
        return None
    return {
        "error": f"提示词过长 {n}/{NANO_PROMPT_MAX}",
        "code": "prompt_too_long",
        "length": n,
        "max": NANO_PROMPT_MAX,
        "limit": NANO_PROMPT_MAX,
    }


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



def _response_seed(data):
    """Prefer seed echoed by Nano API response (truth); None if absent."""
    if not isinstance(data, dict):
        return None
    for key in ("seed", "noise_seed", "noiseSeed"):
        if data.get(key) not in (None, ""):
            return _clamp_seed(data.get(key))
    for nest_key in ("data", "result", "output", "images", "meta", "metadata"):
        nest = data.get(nest_key)
        if isinstance(nest, list) and nest:
            item = nest[0]
            if isinstance(item, dict):
                for key in ("seed", "noise_seed", "noiseSeed"):
                    if item.get(key) not in (None, ""):
                        return _clamp_seed(item.get(key))
        elif isinstance(nest, dict):
            for key in ("seed", "noise_seed", "noiseSeed"):
                if nest.get(key) not in (None, ""):
                    return _clamp_seed(nest.get(key))
    return None


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


def _seed_clamp_meta(raw):
    """Return dict with seedOriginal/seedClamped when _clamp_seed changes the value."""
    clamped = _clamp_seed(raw)
    if clamped is None:
        return {}
    try:
        if raw in (None, "", "random"):
            return {}
        orig = int(raw)
    except (TypeError, ValueError):
        return {}
    if orig != clamped:
        return {"seedOriginal": orig, "seedClamped": True}
    return {}


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


def pick_resolution(spec, w=None, h=None, preferred=None):
    """Pick a catalog resolution token the model actually lists.

    Empty catalog resolutions → None (caller must 400). Never invent `{w}x{h}`.
    """
    sp = (spec or {}).get("supported_parameters") or {}
    res = [str(x) for x in (sp.get("resolutions") or []) if x not in (None, "")]
    if not res:
        return None

    def norm(s):
        return str(s).lower().replace("×", "x").replace("*", "x").replace(" ", "")

    low = {norm(x): x for x in res}
    pref = (preferred or "").strip()
    if pref:
        hit = low.get(norm(pref))
        if hit:
            return hit
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



def civitai_api_token() -> str:
    """Local Civitai API key only — never sent to Nano, never appended as ?token=."""
    try:
        t = CIVITAI_TOKEN_PATH.read_text().strip()
        if t:
            return t
    except Exception:
        pass
    return (
        os.environ.get("CIVITAI_API_TOKEN")
        or os.environ.get("CIVITAI_TOKEN")
        or ""
    ).strip()


def is_signed_b2_url(url: str) -> bool:
    u = (url or "").strip().lower()
    return "b2.civitai.com" in u and "authorization=" in u


def _strip_token_query(url: str) -> str:
    """Drop ?token= / api key query leaks; keep fileId etc."""
    p = urlparse((url or "").strip())
    if not p.scheme:
        return (url or "").strip()
    q = [(k, v) for k, v in parse_qsl(p.query, keep_blank_values=True) if k.lower() != "token"]
    return urlunparse((p.scheme, p.netloc, p.path, p.params, urlencode(q), ""))


def civitai_version_id(item) -> str:
    if isinstance(item, dict):
        for k in ("versionId", "modelVersionId", "id"):
            v = item.get(k)
            if v is not None and str(v).isdigit():
                return str(v)
        for k in ("path", "downloadUrl", "url"):
            m = _CIVITAI_DL_RE.match(_strip_token_query(str(item.get(k) or "")))
            if m:
                return m.group(1)
    elif isinstance(item, str):
        m = _CIVITAI_DL_RE.match(_strip_token_query(item))
        if m:
            return m.group(1)
    return ""


def civitai_download_api_url(item_or_url) -> str:
    if isinstance(item_or_url, dict):
        for k in ("downloadUrl", "path", "url"):
            raw = (item_or_url.get(k) or "").strip()
            if not raw or raw.lower().startswith("urn:"):
                continue
            cleaned = _strip_token_query(raw)
            if _CIVITAI_DL_RE.match(cleaned.split("#")[0]) or "civitai.com/api/download/models/" in cleaned.lower():
                return cleaned.split("#")[0]
        vid = civitai_version_id(item_or_url)
        if vid:
            return "https://civitai.com/api/download/models/" + vid
        return ""
    s = _strip_token_query(str(item_or_url or ""))
    if _CIVITAI_DL_RE.match(s.split("#")[0]) or "civitai.com/api/download/models/" in s.lower():
        return s.split("#")[0]
    if str(item_or_url).isdigit():
        return "https://civitai.com/api/download/models/" + str(item_or_url)
    return ""


def _head_redirect_location(url: str, headers: dict, timeout: float = 30) -> str:
    class _NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: A002
            return None

    opener = urllib.request.build_opener(_NoRedirect)
    base_headers = {
        "User-Agent": "civitai-studio/nanogpt",
        "Accept": "*/*",
    }
    base_headers.update(headers or {})
    for method in ("HEAD", "GET"):
        hdrs = dict(base_headers)
        if method == "GET":
            hdrs["Range"] = "bytes=0-0"
        req = urllib.request.Request(url, method=method, headers=hdrs)
        try:
            with opener.open(req, timeout=timeout) as resp:
                final = resp.geturl()
                if final and final.rstrip("/") != url.rstrip("/"):
                    return final
                return ""
        except urllib.error.HTTPError as e:
            if e.code in (301, 302, 303, 307, 308):
                loc = (e.headers.get("Location") or "").strip()
                if loc.startswith("/"):
                    loc = urljoin(url, loc)
                return loc
            continue
        except Exception:
            continue
    return ""


def resolve_civitai_b2_url(url: str, *, timeout: float = 30) -> str:
    """At generate-time: civitai download URL → B2 signed Location.

    Uses local ~/.config/civitai/token as Bearer only on the Civitai HEAD/GET.
    Never appends ?token=. Never returns a URL that embeds the Civitai API key.
    Public (unauth) 307 is OK when it already yields b2…Authorization=…
    """
    url = _strip_token_query((url or "").strip())
    if not url:
        raise ValueError("空 LoRA URL")
    # Never accept an existing B2 signed/bare URL as the resolve entry — caller must
    # supply versionId / download API URL so we can mint a fresh 307 Location.
    if is_signed_b2_url(url) or "b2.civitai.com" in url.lower():
        raise ValueError("不可用过期 B2 直链作解析入口；请用 download API / versionId")
    if _HF_REPO_RE.match(url):
        return url
    if url.startswith("http") and "civitai.com/api/download/models/" not in url.lower():
        # Already a direct non-Civitai URL (HF file, CDN, …)
        return url
    if not url.startswith("http"):
        if _HF_REPO_RE.match(url):
            return url
        raise ValueError("LoRA 需要 http(s) 下载链或 versionId")

    token = civitai_api_token()
    attempts = []
    if token:
        attempts.append({"Authorization": "Bearer " + token})
    attempts.append({})  # public / unauth fallback

    last = ""
    for hdrs in attempts:
        loc = _head_redirect_location(url, hdrs, timeout=timeout)
        last = loc or last
        if not loc:
            continue
        loc = loc.strip()
        # Refuse leaking Civitai API key via ?token=
        if token and token in loc:
            raise ValueError("拒绝把 Civitai API Key 写进 LoRA URL")
        low = loc.lower()
        if "token=" in low and "authorization=" not in low and "b2.civitai.com" not in low:
            # civitai sometimes redirects with ?token= — strip and fail closed
            raise ValueError("直链含 ?token=，拒绝发给 Nano")
        if loc.startswith("http"):
            return loc
    raise ValueError("无法解析 B2 直链" + (f"（{last[:80]}）" if last else ""))


def persist_safe_lora_path(path: str, version_id: str | None = None) -> str:
    """Sidecar / remember: store download API URL or versionId — never long-lived B2 signed query."""
    vid = str(version_id or "").strip()
    if vid.isdigit():
        return "https://civitai.com/api/download/models/" + vid
    raw = (path or "").strip()
    if not raw:
        return ""
    if is_signed_b2_url(raw) or "b2.civitai.com" in raw.lower():
        # No versionId (handled above) — do not leave bare b2 path after stripping query
        return ""
    cleaned = _strip_token_query(raw)
    m = _CIVITAI_DL_RE.match(cleaned.split("#")[0])
    if m:
        # keep fileId if present (not a signed secret)
        return cleaned.split("#")[0]
    return cleaned


def sanitize_submitted_for_persist(body: dict, lora_meta: list | None = None) -> dict:
    out = copy.deepcopy(body or {})
    meta = list(lora_meta or [])
    loras = out.get("loras")
    if isinstance(loras, list):
        safe = []
        for i, it in enumerate(loras):
            if not isinstance(it, dict):
                continue
            m = meta[i] if i < len(meta) and isinstance(meta[i], dict) else {}
            vid = m.get("versionId") or civitai_version_id(it) or civitai_version_id(m)
            path = persist_safe_lora_path(it.get("path") or "", vid)
            row = {"path": path, "scale": it.get("scale")}
            if m.get("name"):
                row["name"] = m.get("name")
            if vid:
                row["versionId"] = str(vid)
            dl = m.get("downloadUrl") or (path if "civitai.com/api/download" in path else "")
            if dl:
                row["downloadUrl"] = persist_safe_lora_path(dl, vid)
            safe.append(row)
        out["loras"] = safe
    for i in range(1, 4):
        k = f"lora_{i}_url"
        if k in out:
            m = meta[i - 1] if i - 1 < len(meta) and isinstance(meta[i - 1], dict) else {}
            vid = m.get("versionId") or ""
            out[k] = persist_safe_lora_path(out.get(k) or "", vid)
    # Never persist free WxH alongside catalog resolution tokens.
    out.pop("width", None)
    out.pop("height", None)
    return out


def model_supports_lora(spec: dict | None, mid: str = "") -> bool:
    sp = spec or {}
    if sp.get("supportsLora"):
        # Explicit flag wins — but never for upscale/utility/bg categories (false positive guard).
        cat = str(sp.get("category") or "").lower()
        if cat in ("upscale", "utility", "bg"):
            return False
        return True
    cat = str(sp.get("category") or "").lower()
    if cat in ("upscale", "utility", "bg"):
        # Don't infer supportsLora from bare 'lora' substring on upscalers / utility.
        return False
    blob = " ".join(
        [
            str(mid or ""),
            str(sp.get("id") or ""),
            str(sp.get("name") or ""),
            " ".join(str(t) for t in (sp.get("tags") or [])),
        ]
    ).lower()
    return "lora" in blob


def resolve_nano_loras(payload: dict, *, timeout: float = 30):
    """Resolve ≤3 LoRAs to clean B2 signed paths at generate time. Fail closed.

    Returns (resolved_list, None) or (None, error_dict).
    Partial failure → error (never silently drop while UI still shows the name).
    """
    raw = (payload or {}).get("loras") or []
    if isinstance(raw, dict):
        raw = [raw]
    if not isinstance(raw, list):
        raw = []
    if not raw:
        return [], None
    if len(raw) > 3:
        names = []
        for it in raw:
            if isinstance(it, dict):
                names.append(str(it.get("name") or it.get("path") or it.get("versionId") or "LoRA"))
            else:
                names.append(str(it)[:60] or "LoRA")
        return None, {
            "error": f"NanoGPT 最多 3 条 LoRA（已选 {len(raw)}）",
            "failed": [{"name": n, "error": "超过 3 条"} for n in names[3:]],
            "code": "lora_too_many",
        }

    failed = []
    out = []
    for it in raw:
        if isinstance(it, str):
            name = it.strip() or "LoRA"
            scale = 1.0
            vid = civitai_version_id(it)
            dl = civitai_download_api_url(it)
            path_hint = it.strip()
        elif isinstance(it, dict):
            name = str(it.get("name") or it.get("path") or it.get("air") or "LoRA")
            try:
                raw_s = it.get("scale")
                if raw_s is None:
                    raw_s = it.get("strength")
                scale = float(raw_s) if raw_s not in (None, "") else 1.0
            except (TypeError, ValueError):
                scale = 1.0
            vid = civitai_version_id(it)
            dl = civitai_download_api_url(it)
            path_hint = (
                (it.get("path") or it.get("downloadUrl") or it.get("url") or "").strip()
            )
            if (not path_hint or path_hint.lower().startswith("urn:")) and vid:
                path_hint = "https://civitai.com/api/download/models/" + vid
                dl = dl or path_hint
        else:
            failed.append({"name": "LoRA", "error": "条目格式无效"})
            continue

        scale = max(0.0, min(4.0, scale))
        try:
            if not path_hint or path_hint.lower().startswith("urn:"):
                raise ValueError("无下载链 / versionId（无直链）")
            if _HF_REPO_RE.match(path_hint):
                resolved = path_hint
            else:
                # v0770: NEVER trust existing b2…Authorization= as final path.
                # Always re-resolve from stable identity (versionId / download API).
                b2ish = is_signed_b2_url(path_hint) or "b2.civitai.com" in path_hint.lower()
                target = (dl or "").strip()
                if not target and vid:
                    target = "https://civitai.com/api/download/models/" + vid
                if (
                    not target
                    and path_hint
                    and "civitai.com/api/download/models/" in path_hint.lower()
                ):
                    target = path_hint
                if b2ish and not target:
                    raise ValueError(
                        "过期 B2 直链无法刷新（缺 versionId / download API URL）"
                    )
                if target:
                    if not target.startswith("http") and vid:
                        target = "https://civitai.com/api/download/models/" + vid
                    # Strip any prior signed Location — resolve from download API only
                    if is_signed_b2_url(target) or "b2.civitai.com" in target.lower():
                        if not vid:
                            raise ValueError(
                                "过期 B2 直链无法刷新（缺 versionId / download API URL）"
                            )
                        target = "https://civitai.com/api/download/models/" + vid
                    resolved = resolve_civitai_b2_url(target, timeout=timeout)
                elif path_hint.startswith("http") and not b2ish:
                    resolved = resolve_civitai_b2_url(path_hint, timeout=timeout)
                else:
                    raise ValueError("无直链")
            if not resolved or resolved.lower().startswith("urn:"):
                raise ValueError("无直链")
            # Final guard: never send Civitai API key to Nano
            tok = civitai_api_token()
            if tok and tok in resolved:
                raise ValueError("拒绝泄露 Civitai API Key")
            if "civitai.com/api/download" in resolved.lower() and "authorization=" not in resolved.lower():
                # Still the API URL — Nano may not follow with our key; fail closed
                raise ValueError("未拿到 B2 直链")
            out.append({
                "path": resolved,
                "scale": scale,
                "name": name,
                "versionId": vid or "",
                "downloadUrl": dl or (f"https://civitai.com/api/download/models/{vid}" if vid else ""),
            })
        except Exception as e:
            failed.append({
                "name": name,
                "versionId": vid or "",
                "error": str(e) or "无直链",
            })

    if failed:
        label = "、".join(f.get("name") or "?" for f in failed)
        return None, {
            "error": f"LoRA 无直链：{label}",
            "failed": failed,
            "code": "lora_no_direct_url",
        }
    return out, None


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
    # v0771: do not mark upscale/bg/utility as supportsLora from bare 'lora' substring.
    lora = False if cat in ("upscale", "bg", "utility") else (("lora" in blob) or any("lora" in t for t in tags))
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


def _row_text(it: dict) -> dict:
    """Normalize official GET /api/v1/models rows for model selectors."""
    mid = str(it.get("id") or "").strip()
    name = str(it.get("name") or mid.rsplit("/", 1)[-1] or mid).strip()
    caps = it.get("capabilities") or {}
    tags = [str(t).lower() for t in (it.get("tags") or []) if t]
    return {
        "id": mid,
        "name": name,
        "category": "text",
        "backend": "nano-gpt",
        "status": "available",
        "task": "text-generation",
        "tags": tags,
        "pricing": it.get("pricing") or {},
        "supported_parameters": it.get("supported_parameters") or {},
        "capabilities": caps,
        "description": it.get("description") or "",
        "owned_by": it.get("owned_by") or "",
    }


class CatalogFetchError(RuntimeError):
    def __init__(self, message, code="catalog_fetch_failed"):
        super().__init__(message)
        self.code = code


def fetch_text_catalog(force=False) -> list:
    """Fetch official NanoGPT text model IDs; never infer chat models from image/video rows.

    A failed fetch must not overwrite a good cache with []. Empty failure raises.
    """
    now = time.time()
    cache = _CACHE.setdefault("text", {"at": 0.0, "items": None})
    if not force and cache.get("items") is not None and now - (cache.get("at") or 0) < _TTL:
        return list(cache["items"])
    code, data = json_call(TEXT_MODELS, headers={"Accept": "application/json", **_auth()}, timeout=30)
    rows = data.get("data") if isinstance(data, dict) else None
    items, seen = [], set()
    if code == 200 and isinstance(rows, list):
        for it in rows:
            if not isinstance(it, dict) or not it.get("id"):
                continue
            row = _row_text(it)
            if row["id"] not in seen:
                seen.add(row["id"])
                items.append(row)
        cache["items"], cache["at"] = items, now
        cache["error"] = None
        return list(items)
    if cache.get("items"):
        cache["stale"] = True
        return list(cache["items"])
    raise CatalogFetchError(f"NanoGPT 文本目录 HTTP {code}，没有可用缓存")


def fetch_catalog(force=False) -> list:
    now = time.time()
    if not force and _CACHE.get("items") is not None and (now - (_CACHE.get("at") or 0)) < _TTL:
        return list(_CACHE["items"])
    items, seen = [], set()
    headers = {"Accept": "application/json"}
    headers.update(_auth())
    img_code, data = json_call(IMG_MODELS, headers=headers, timeout=30)
    block = (data or {}).get("data") if isinstance(data, dict) else None
    if img_code == 200 and isinstance(block, list):
        for it in block:
            if not isinstance(it, dict) or not it.get("id"):
                continue
            row = _row_image(it)
            if row["id"] in seen:
                continue
            seen.add(row["id"])
            items.append(row)
    vid_code, data = json_call(VID_MODELS, headers=headers, timeout=30)
    block = (data or {}).get("data") if isinstance(data, dict) else None
    if vid_code == 200 and isinstance(block, list):
        for it in block:
            if not isinstance(it, dict) or not it.get("id"):
                continue
            row = _row_video(it)
            if row["id"] in seen:
                continue
            seen.add(row["id"])
            items.append(row)
    if items:
        _CACHE["items"] = items
        _CACHE["at"] = now
        return list(items)
    prev = _CACHE.get("items")
    if prev:
        return list(prev)
    raise CatalogFetchError(f"NanoGPT 图/视频目录为空（image HTTP {img_code}, video HTTP {vid_code}）")


def find_spec(mid: str) -> dict:
    mid = (mid or "").strip()
    try:
        pool = list(fetch_catalog())
    except CatalogFetchError:
        pool = []
    try:
        pool.extend(fetch_text_catalog())
    except CatalogFetchError:
        pass
    for it in pool:
        if it.get("id") == mid:
            return it
    return {"id": mid, "supported_parameters": {}, "capabilities": {}}


def known_nano_model(mid: str) -> bool:
    mid = (mid or "").strip()
    if not mid:
        return False
    spec = find_spec(mid)
    return bool(spec.get("category") or spec.get("supported_parameters") or spec.get("capabilities"))


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
    res = pick_resolution(spec, w, h, preferred=(payload or {}).get("resolution"))
    if res:
        body["resolution"] = res
        body["size"] = res
    # width/height are only for picking the catalog token / aspect — never POST or persist them
    # (FE hint: 导入尺寸仅参考，不进 POST).
    ar = closest_aspect(w or 1024, h or 1024)
    if ar:
        body["aspect_ratio"] = ar
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
        "response_format",
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
    res = pick_resolution(spec, w, h, preferred=(payload or {}).get("resolution"))
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
    loras = _loras(payload)
    if loras:
        body["loras"] = [{"path": x["path"], "scale": x["scale"]} for x in loras]
        for i, item in enumerate(loras, 1):
            body[f"lora_{i}_url"] = item["path"]
            body[f"lora_{i}_scale"] = item["scale"]
    return body


class NanoGptProvider(Provider):
    id = "nano-gpt"
    label = "NanoGPT"

    def has_key(self) -> bool:
        return bool(nano_key())

    def categories(self) -> list:
        cats = set()
        try:
            cats |= {x.get("category") for x in fetch_catalog() if x.get("category")}
        except CatalogFetchError:
            cats.update({"image", "video"})
        try:
            cats |= {x.get("category") for x in fetch_text_catalog() if x.get("category")}
        except CatalogFetchError:
            cats.add("text")
        return sorted(cats) or ["image", "video", "text"]

    def catalog(self, q, category, status) -> dict:
        from collections import Counter
        from .catalog_ops import category_matches, enrich_catalog_item

        error = None
        err_code = None
        imgvid, text = [], []
        try:
            imgvid = fetch_catalog()
        except CatalogFetchError as e:
            if category not in ("chat", "text"):
                error = str(e)
                err_code = e.code
        try:
            text = fetch_text_catalog()
        except CatalogFetchError as e:
            if category in ("chat", "text"):
                error = str(e)
                err_code = e.code
        if category in ("chat", "text"):
            items = list(text)
            page_source = TEXT_MODELS
        else:
            items = list(imgvid)
            page_source = f"{IMG_MODELS} + {VID_MODELS}"
        cat_counts = Counter()
        for x in list(imgvid) + list(text):
            cat_counts[x.get("category") or "unknown"] += 1
        qn = _alnum(q)
        if qn:
            items = [x for x in items if qn in _alnum((x.get("name") or "") + " " + (x.get("id") or "") + " " + " ".join(x.get("tags") or []))]
        if category:
            items = [x for x in items if category_matches(x.get("category"), category)]
        if status:
            items = [x for x in items if x.get("status") == status]
        items = [enrich_catalog_item(x, "nano-gpt") for x in items]
        body = {
            "total": len(items),
            "count": len(items),
            "backend": self.id,
            "items": items,
            "hasKey": self.has_key(),
            "categories": dict(cat_counts),
            "pagination": {
                "page": 1,
                "pageSize": len(items),
                "pagesFetched": 1,
                "pages": 1,
                "hasMore": False,
                "source": page_source,
                "sourceTotal": (len(text) if category in ("chat", "text") else len(imgvid)),
                "limit": None,
            },
        }
        if error:
            body["error"] = error
            body["code"] = err_code
        return body

    def owns_service(self, service_id: str) -> bool:
        sid = (service_id or "").strip()
        if not sid:
            return False
        if sid.startswith(("nano-gpt/", "nanogpt/", "nano/")):
            return True
        ids = {x.get("id") for x in fetch_catalog()}
        if sid in ids:
            return True
        try:
            ids |= {x.get("id") for x in fetch_text_catalog()}
        except CatalogFetchError:
            pass
        return sid in ids

    def owns_job(self, job_id: str) -> bool:
        pid, _ = parse_job_id(job_id)
        return pid in ("nano-gpt", "nanogpt", "nano") or (job_id or "").startswith("nano-gpt|")

    def whatif(self, payload: dict):
        """Dry-run the same gates generate() hits. Never POST image/video endpoints."""
        p = dict(payload or {})
        sid = (p.get("serviceId") or "").strip()
        mid = model_id(sid)
        base = {"backend": self.id, "service": {"serviceId": mid or sid}}
        if not sid:
            return 400, {**base, "error": "缺少 NanoGPT 模型 id", "code": "missing_service"}
        if looks_like_civitai_service(sid):
            return 400, {
                **base,
                "error": "当前选中的是 Civitai 服务，不能发给 NanoGPT。请选 NanoGPT 目录里的模型。",
                "code": "wrong_backend",
            }
        if not self.has_key():
            return 401, {**base, "error": "没有 NanoGPT API Key", "code": "no_key"}
        spec = find_spec(mid)
        if not known_nano_model(mid):
            return 400, {**base, "error": f"NanoGPT 目录里没有 {mid}", "code": "unknown_service"}
        errors, warnings = [], []
        too = prompt_length_error(p.get("prompt"))
        if too:
            return 400, {**base, **too}
        cat = (spec.get("category") or p.get("kind") or p.get("recipe") or "image").lower()
        kind = str(p.get("kind") or p.get("recipe") or "").lower()
        task = spec.get("task") or ""
        is_video = cat == "video" or "video" in task
        is_text = kind in ("text", "chat") or cat in ("text", "chat")
        if not is_text and not (p.get("prompt") or "").strip():
            errors.append({"code": "missing_prompt", "message": "prompt 是空的，NanoGPT 会直接打回"})
        media = _source_images(p)
        needs_img = bool(spec.get("needsSource")) or task == "image-to-image" or (
            (spec.get("capabilities") or {}).get("image_to_image")
            and not (spec.get("capabilities") or {}).get("image_generation", True)
        )
        needs_first = bool(spec.get("needsFirstFrame")) or task == "image-to-video"
        if needs_img and not media:
            errors.append({"code": "missing_input_media", "message": f"{mid} 是图生图，必须先接一张图"})
        if is_video and needs_first and not media:
            errors.append({"code": "missing_input_media", "message": f"{mid} 是图生视频，必须先接首帧"})
        if is_video:
            body = _video_body(p, spec)
        elif is_text:
            body = {"model": mid, "prompt": p.get("prompt") or ""}
        else:
            sp = spec.get("supported_parameters") or {}
            if not [x for x in (sp.get("resolutions") or []) if x not in (None, "")]:
                errors.append({
                    "code": "missing_resolution",
                    "message": "当前 NanoGPT 模型目录没有 resolutions，请换一个带分辨率列表的目录模型",
                })
            body = _image_body(p, spec)
            if not body.get("resolution") and not body.get("size") and not any(e["code"] == "missing_resolution" for e in errors):
                errors.append({
                    "code": "missing_resolution",
                    "message": "无法从目录选中 resolution token，请在构图里选一个目录分辨率",
                })
        pricing = (spec.get("pricing") or {}).get("per_image") or {}
        res = pick_resolution(spec, p.get("width"), p.get("height"), preferred=p.get("resolution"))
        price = None
        if isinstance(pricing, dict) and pricing:
            key = res if res in pricing else ("auto" if "auto" in pricing else next(iter(pricing)))
            try:
                price = float(pricing[key])
            except (TypeError, ValueError, KeyError):
                price = None
        try:
            n = max(1, int(p.get("quantity") or 1))
        except (TypeError, ValueError):
            n = 1
        note = "NanoGPT 按次美元计费，无黄 Buzz"
        if price is not None:
            note = f"约 ${price * n:.4f} USD · {note}"
        data = {
            **base,
            "operation": task or cat,
            "submittedInput": body,
            "warnings": warnings,
            "checked": {"catalogSpec": True, "category": cat},
            "cost": {"total": None, "usd": price, "note": note},
            "service": {"serviceId": mid, "resolution": res, "category": cat},
        }
        if errors:
            data["errors"] = errors
            data["error"] = errors[0]["message"]
            data["code"] = errors[0]["code"]
            return 400, data
        data["ok"] = True
        return 200, data

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
        kind = str((payload or {}).get("kind") or (payload or {}).get("recipe") or "").lower()
        cat = (spec.get("category") or kind or "image").lower()
        if kind in ("text", "chat") or cat in ("text", "chat"):
            return self._generate_text(payload, spec, mid)
        if cat == "video" or (spec.get("task") or "").find("video") >= 0:
            return self._generate_video(payload, spec, mid)
        return self._generate_image(payload, spec, mid)

    def _generate_text(self, payload, spec, mid):
        too = prompt_length_error((payload or {}).get("prompt"))
        if too:
            return 400, too
        prompt = str((payload or {}).get("prompt") or "").strip()
        if not prompt:
            return 400, {"error": "文本生成需要提示词", "serviceId": mid, "code": "missing_prompt"}
        model = str(mid or "").strip()
        if model.startswith("chat/"):
            model = model[len("chat/"):]
        if not model:
            return 400, {"error": "缺少 NanoGPT 模型 id", "code": "missing_service"}
        body = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
        }
        temperature = (payload or {}).get("temperature")
        if temperature not in (None, ""):
            try:
                body["temperature"] = float(temperature)
            except (TypeError, ValueError):
                return 400, {"error": "temperature 必须是数字", "serviceId": mid, "code": "invalid_temperature"}
        code, data = json_call(
            CHAT_COMPLETIONS,
            method="POST",
            headers=_auth(),
            body=body,
            timeout=90,
        )
        if code >= 400 or not isinstance(data, dict):
            return (
                code if code >= 400 else 502,
                {
                    "error": extract_error(data, f"NanoGPT chat HTTP {code}"),
                    "code": "text_generation_failed",
                    "backend": self.id,
                    "model": mid,
                },
            )
        choices = data.get("choices") or []
        content = ""
        if choices and isinstance(choices[0], dict):
            message = choices[0].get("message") or {}
            content = message.get("content") or choices[0].get("text") or ""
        if isinstance(content, list):
            content = "".join(
                str(part.get("text") or "") if isinstance(part, dict) else str(part)
                for part in content
            )
        content = str(content).strip()
        if not content:
            return 502, {
                "error": "NanoGPT 文本接口未返回内容",
                "code": "empty_text_generation",
                "backend": self.id,
                "model": mid,
            }
        jid = f"nano-gpt|text|{uuid.uuid4().hex[:12]}"
        return 200, {
            "ok": True,
            "id": jid,
            "status": "succeeded",
            "backend": self.id,
            "endpoint": mid,
            "model": mid,
            "text": content,
            "content": content,
            "submittedInput": body,
            "cost": data.get("cost"),
        }

    def _generate_image(self, payload, spec, mid):
        too = prompt_length_error((payload or {}).get("prompt"))
        if too:
            return 400, too
        sp = (spec or {}).get("supported_parameters") or {}
        if not [x for x in (sp.get("resolutions") or []) if x not in (None, "")]:
            return 400, {
                "error": "当前 NanoGPT 模型目录没有 resolutions，请换一个带分辨率列表的目录模型（勿自拼 WxH）",
                "serviceId": mid,
            }
        # v0770: always re-resolve Civitai→fresh B2 at generate (never trust stale signed URL).
        pl = dict(payload or {})
        raw_loras = pl.get("loras") or []
        if isinstance(raw_loras, dict):
            raw_loras = [raw_loras]
        lora_meta: list = []
        if raw_loras:
            if not model_supports_lora(spec, mid):
                return 400, {
                    "error": f"当前 Nano 模型不支持 LoRA，请改选 *-lora 模型（当前：{mid}）",
                    "serviceId": mid,
                    "code": "lora_model_unsupported",
                }
            resolved, err = resolve_nano_loras(pl)
            if err:
                return 400, err
            pl["loras"] = resolved
            lora_meta = list(resolved or [])
        full = _image_body(pl, spec)
        if not full.get("resolution") and not full.get("size"):
            return 400, {
                "error": "无法从目录选中 resolution token，请在构图里选一个目录分辨率",
                "serviceId": mid,
            }
        # Persist download API URL / versionId — never long-lived B2 signed query.
        persist_body = sanitize_submitted_for_persist(full, lora_meta)
        jid = f"nano-gpt|img|{uuid.uuid4().hex[:12]}"
        # v0774: when int32 clamp changes seed, expose seedOriginal + seedClamped.
        # v0773: meta.seed prefers API response seed; fallback submitted.
        submitted_seed = full.get("seed")
        seed_extra = _seed_clamp_meta((payload or {}).get("seed"))
        meta = {
            "backend": self.id,
            "serviceId": mid,
            "prompt": (payload or {}).get("prompt"),
            "negativePrompt": (payload or {}).get("negativePrompt"),
            "seed": submitted_seed,
            "jobId": jid,
            "submittedInput": persist_body,
        }
        if seed_extra:
            meta.update(seed_extra)
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
            resp_seed = _response_seed(data)
            used_seed = resp_seed if resp_seed is not None else submitted_seed
            meta["seed"] = used_seed
            saved = _save_result(data, jid, meta)
            if saved:
                out = {
                    "id": jid,
                    "status": "succeeded",
                    "backend": self.id,
                    "endpoint": mid,
                    "saved": saved,
                    "submittedInput": sanitize_submitted_for_persist(body, lora_meta),
                    "seed": used_seed,
                    "cost": data.get("cost"),
                }
                if seed_extra:
                    out.update(seed_extra)
                return 200, out
            last = (502, {"error": "NanoGPT 没有返回图片", "raw": json.dumps(data)[:400]})
        return last

    def _generate_video(self, payload, spec, mid):
        too = prompt_length_error((payload or {}).get("prompt"))
        if too:
            return 400, too
        # v0770: video path also runs resolve_nano_loras (same fail-closed rules).
        pl = dict(payload or {})
        raw_loras = pl.get("loras") or []
        if isinstance(raw_loras, dict):
            raw_loras = [raw_loras]
        lora_meta: list = []
        if raw_loras:
            if not model_supports_lora(spec, mid):
                return 400, {
                    "error": f"当前 Nano 模型不支持 LoRA，请改选 *-lora 模型（当前：{mid}）",
                    "serviceId": mid,
                    "code": "lora_model_unsupported",
                }
            resolved, err = resolve_nano_loras(pl)
            if err:
                return 400, err
            pl["loras"] = resolved
            lora_meta = list(resolved or [])
        body = _video_body(pl, spec)
        persist_body = sanitize_submitted_for_persist(body, lora_meta)
        seed_extra = _seed_clamp_meta((payload or {}).get("seed"))
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
                resp_seed = _response_seed(data)
                used_seed = resp_seed if resp_seed is not None else body.get("seed")
                out = {
                    "id": jid,
                    "status": "succeeded",
                    "backend": self.id,
                    "saved": saved,
                    "submittedInput": persist_body,
                    "seed": used_seed,
                }
                if seed_extra:
                    out.update(seed_extra)
                return 200, out
            return 502, {"error": "NanoGPT 视频没返回任务 id", "raw": json.dumps(data)[:400]}
        jid = f"nano-gpt|vid|{run}"
        resp_seed = _response_seed(data)
        used_seed = resp_seed if resp_seed is not None else body.get("seed")
        out = {
            "id": jid,
            "status": (data.get("status") or "pending").lower(),
            "backend": self.id,
            "endpoint": mid,
            "submittedInput": persist_body,
            "seed": used_seed,
            "wait": {"progress": None, "precedingJobs": None, "etaSeconds": None, "completeAt": None, "log": None},
        }
        if seed_extra:
            out.update(seed_extra)
        return 200, out

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


GRID_KINDS = {
    "灵感风暴": "从不同创意方向发散同一主题, 每格换一种视觉概念/材质/情绪, 不要重复构图",
    "故事叙述": "按时间顺序推进的连续叙事, 每格是下一个瞬间, 保持角色与场景一致",
    "武打分镜": "一段打斗的连续分镜, 每格换动作节点与机位(全景/中景/特写/过肩), 强调动势",
    "全景机位": "同一场景同一主体, 每格换机位与焦段(广角/中景/特写/俯拍/仰拍/侧面), 主体一致",
}

GRID_PLANNER_SYSTEM = (
    "你是分镜策划。把用户的一句提示词拆成 N 条互不重复的子提示词, 用于并行出 N 张图再拼成宫格。\n"
    "硬性要求:\n"
    "1. 只输出 JSON 数组, 形如 [\"子提示词1\", \"子提示词2\", ...], 不要任何解释、编号或代码块围栏。\n"
    "2. 数组长度必须严格等于要求的条数。\n"
    "3. 每条都是可独立喂给文生图模型的完整画面描述, 自带主体、场景、光线、镜头。\n"
    "4. 同一宫格内主体形象/服装/画风必须一致, 变化只发生在该宫格类型指定的维度上。"
)


def plan_grid(payload: dict):
    """九宫格: 把 1 条提示词拆成 N 条子提示词。

    catalog 304 项 + fal-models 1492 项里没有任何一次出多联/网格图的模型
    (核查于 2026-09-06)。所以九宫格不是「找个 grid 模型」, 而是拆 N 次子提示词
    -> N 次 t2i -> 前端 canvas 拼成一张卡。这个接口只负责「拆」。
    """
    payload = payload or {}
    model = (payload.get("model") or "").strip()
    if model.startswith("chat/"):
        model = model[len("chat/"):]
    if not model:
        return 400, {"error": "缺少九宫格拆解模型 id"}
    text = (payload.get("text") or payload.get("prompt") or "").strip()
    if not text:
        return 400, {"error": "缺少九宫格生成提示词"}
    kind = (payload.get("kind") or payload.get("gridKind") or "").strip()
    if kind and kind not in GRID_KINDS:
        return 400, {"error": f"未知九宫格类型 {kind}", "allowed": list(GRID_KINDS)}
    try:
        count = int(payload.get("count") or 9)
    except (TypeError, ValueError):
        return 400, {"error": "count 必须是整数"}
    if count < 2 or count > 25:
        return 400, {"error": "count 超出范围 (2..25)"}
    key = nano_key()
    if not key:
        return 401, {"error": "没有 NanoGPT API Key"}

    rule = GRID_KINDS.get(kind, "")
    user = f"主提示词: {text}\n条数: {count}"
    if rule:
        user += f"\n宫格类型: {kind} —— {rule}"
    code, data = json_call(
        CHAT_COMPLETIONS,
        method="POST",
        headers=_auth(),
        body={
            "model": model,
            "messages": [
                {"role": "system", "content": GRID_PLANNER_SYSTEM},
                {"role": "user", "content": user},
            ],
        },
        timeout=60,
    )
    if code >= 400 or not isinstance(data, dict):
        return code if code >= 400 else 502, {
            "error": extract_error(data, f"NanoGPT chat HTTP {code}"),
            "backend": "nano-gpt",
        }
    choices = data.get("choices") or []
    content = ""
    if choices and isinstance(choices[0], dict):
        content = ((choices[0].get("message") or {}).get("content") or "").strip()
    prompts = _parse_prompt_list(content, count)
    if not prompts:
        return 502, {"error": "九宫格拆解未返回可用子提示词", "backend": "nano-gpt", "raw": content[:400]}
    return 200, {
        "ok": True,
        "backend": "nano-gpt",
        "model": model,
        "kind": kind,
        "count": len(prompts),
        "prompts": prompts,
    }


def _parse_prompt_list(content: str, count: int) -> list:
    """LLM 回的 JSON 数组; 允许被 ```json 围栏包住; 兜底按行拆。"""
    import json as _json
    import re as _re

    raw = (content or "").strip()
    if raw.startswith("```"):
        raw = _re.sub(r"^```[a-zA-Z]*\s*", "", raw)
        raw = _re.sub(r"\s*```$", "", raw).strip()
    items = None
    m = _re.search(r"\[.*\]", raw, _re.S)
    if m:
        try:
            parsed = _json.loads(m.group(0))
            if isinstance(parsed, list):
                items = [str(x).strip() for x in parsed if str(x).strip()]
        except ValueError:
            items = None
    if not items:
        lines = [_re.sub(r"^\s*[-*\d.)、]+\s*", "", ln).strip() for ln in raw.splitlines()]
        items = [ln for ln in lines if len(ln) > 4]
    if not items:
        return []
    # 不足就报少, 不静默补空; 多了截断到 count。
    return items[:count]


def pick_vision_model(explicit: str = "") -> str:
    chosen = (explicit or "").strip()
    if chosen.startswith("chat/"):
        chosen = chosen[len("chat/"):]
    if chosen:
        return chosen
    try:
        items = fetch_text_catalog()
    except CatalogFetchError as e:
        raise CatalogFetchError(f"无法选择视觉模型：{e}", code=e.code) from e
    ranked = []
    for it in items:
        mid = str(it.get("id") or "")
        blob = " ".join(
            [
                mid,
                str(it.get("name") or ""),
                " ".join(str(t) for t in (it.get("tags") or [])),
            ]
        ).lower()
        caps = it.get("capabilities") or {}
        if caps.get("vision") or "vl" in blob or "vision" in blob:
            score = 0
            if "instruct" in blob:
                score += 2
            if "vl" in blob:
                score += 3
            ranked.append((score, mid))
    ranked.sort(reverse=True)
    if not ranked:
        raise CatalogFetchError("NanoGPT 文本目录里没有视觉（vl/vision）模型")
    return ranked[0][1]


def caption_image(image_url: str, model: str = "") -> tuple[int, dict]:
    """Vision chat completion. Caption text comes from the model, never a fixed string."""
    key = nano_key()
    if not key:
        return 401, {"error": "没有 NanoGPT API Key", "code": "no_key", "backend": "nano-gpt"}
    url = (image_url or "").strip()
    if not url:
        return 400, {"error": "缺少图片 url", "code": "missing_url", "backend": "nano-gpt"}
    try:
        mid = pick_vision_model(model)
    except CatalogFetchError as e:
        return 503, {"error": str(e), "code": e.code, "backend": "nano-gpt"}
    prompt = (
        "Describe this image so it can be reused as an image-generation prompt. "
        "Be specific about subject, appearance, clothing, pose, setting, lighting, and camera. "
        "Do not invent a backstory. Output only the description."
    )

    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": url}},
            ],
        }
    ]
    body = {"model": mid, "messages": messages, "max_tokens": 400}
    code, data = json_call(CHAT_COMPLETIONS, method="POST", headers=_auth(), body=body, timeout=90)
    if code >= 400 or not isinstance(data, dict):
        return (
            code if code >= 400 else 502,
            {
                "error": extract_error(data, f"NanoGPT vision HTTP {code}"),
                "code": "caption_failed",
                "backend": "nano-gpt",
                "model": mid,
            },
        )
    choices = data.get("choices") or []
    content = ""
    if choices and isinstance(choices[0], dict):
        content = ((choices[0].get("message") or {}).get("content") or "").strip()
    if not content:
        return 502, {
            "error": "NanoGPT vision 未返回描述",
            "code": "empty_caption",
            "backend": "nano-gpt",
            "model": mid,
        }
    return 200, {"caption": content, "backend": "nano-gpt", "model": mid}


def chat_story(payload: dict):
    """故事推演: plain chat completion, not part of the image/video graph pipeline.

    NanoGPT is the only one of the six backends with a real chat/completions surface
    (verified: BASE + /v1/chat/completions, OpenAI-compatible, mirrors GEN_IMAGES_OAI).
    Model must be picked explicitly by the caller — no hardcoded fallback model id.
    """
    key = nano_key()
    if not key:
        return 401, {"error": "没有 NanoGPT API Key"}
    payload = payload or {}
    model = (payload.get("model") or "").strip()
    if model.startswith("chat/"):
        model = model[len("chat/"):]
    if not model:
        return 400, {"error": "缺少故事推演模型 id"}
    text = (payload.get("text") or payload.get("prompt") or "").strip()
    if not text:
        return 400, {"error": "缺少故事/场景/角色设定文本"}
    messages = [
        {"role": "system", "content": STORY_DIRECTOR_SYSTEM},
        {"role": "user", "content": text},
    ]
    body = {"model": model, "messages": messages}
    if payload.get("temperature") not in (None, ""):
        try:
            body["temperature"] = float(payload["temperature"])
        except (TypeError, ValueError):
            pass
    code, data = json_call(CHAT_COMPLETIONS, method="POST", headers=_auth(), body=body, timeout=60)
    if code >= 400 or not isinstance(data, dict):
        return code if code >= 400 else 502, {"error": extract_error(data, f"NanoGPT chat HTTP {code}"), "backend": "nano-gpt"}
    choices = data.get("choices") or []
    content = ""
    if choices and isinstance(choices[0], dict):
        content = ((choices[0].get("message") or {}).get("content") or "").strip()
    if not content:
        return 502, {"error": "NanoGPT chat 未返回内容", "backend": "nano-gpt", "raw": data}
    return 200, {"ok": True, "backend": "nano-gpt", "model": model, "text": content}


from . import register  # noqa: E402

register(NanoGptProvider())
