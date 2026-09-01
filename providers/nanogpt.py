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
GEN_IMAGES = API + "/images"
GEN_IMAGES_OAI = BASE + "/v1/images/generations"
GEN_VIDEO = BASE + "/api/generate-video"
VIDEO_STATUS = BASE + "/api/video/status"

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
    res = pick_resolution(spec, w, h, preferred=(payload or {}).get("resolution"))
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
        res = pick_resolution(spec, payload.get("width"), payload.get("height"), preferred=(payload or {}).get("resolution"))
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
        meta = {
            "backend": self.id,
            "serviceId": mid,
            "prompt": (payload or {}).get("prompt"),
            "negativePrompt": (payload or {}).get("negativePrompt"),
            "seed": full.get("seed"),
            "jobId": jid,
            "submittedInput": persist_body,
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
                    "submittedInput": sanitize_submitted_for_persist(body, lora_meta),
                    "cost": data.get("cost"),
                }
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
                return 200, {"id": jid, "status": "succeeded", "backend": self.id, "saved": saved, "submittedInput": persist_body}
            return 502, {"error": "NanoGPT 视频没返回任务 id", "raw": json.dumps(data)[:400]}
        jid = f"nano-gpt|vid|{run}"
        return 200, {
            "id": jid,
            "status": (data.get("status") or "pending").lower(),
            "backend": self.id,
            "endpoint": mid,
            "submittedInput": persist_body,
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
