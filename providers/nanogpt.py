from __future__ import annotations

import copy
import json
import math
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
VID_MODELS = API + "/video-models?detailed=true"
GEN_IMAGES = API + "/images"
GEN_IMAGES_OAI = BASE + "/v1/images/generations"
GEN_IMAGES_EDIT = API + "/images/edit"
GEN_IMAGES_EDITS = API + "/images/edits"
GEN_VIDEO = BASE + "/api/generate-video"
VIDEO_STATUS = BASE + "/api/video/status"
TEXT_MODELS = API + "/models?detailed=true"
CHAT_COMPLETIONS = BASE + "/v1/chat/completions"

_CACHE = {"at": 0.0, "items": None}
_TTL = 300

# Live 2026-09-10: POST https://nano-gpt.com/api/v1/images accepted a 1311-char
# SFW prompt (HTTP 200, billed). Docs still publish no prompt max. The old
# local 1200 ceiling (historical 400 "1408 > 1200") is not an official limit
# and must not invent one. Upstream prompt_too_long still surfaces as 400.
NANO_PROMPT_MAX = None


def prompt_length_error(prompt) -> dict | None:
    """Local precheck only when an official max is known. None = pass through."""
    if NANO_PROMPT_MAX is None:
        return None
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



def _finite_number(raw, field, *, integer=False, minimum=None, maximum=None):
    """Validate before encoding; never truncate, wrap, default, or drop."""
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
            bounds = f"（原值 ≥ {minimum}）"
        elif maximum is not None:
            bounds = f"（原值 ≤ {maximum}）"
        else:
            bounds = ""
        raise ValueError(
            f"NanoGPT {field} 必须是{'整数' if integer else '有限数值'}{bounds}，拒绝静默改值"
        ) from None
    return value


def _response_seed_value(raw):
    """Parse a vendor-echoed seed. Never modulo; never fail the whole job."""
    try:
        return _clamp_seed(raw)
    except ValueError:
        return None


def _response_seed(data):
    """Prefer seed echoed by Nano API response (truth); None if absent."""
    if not isinstance(data, dict):
        return None
    for key in ("seed", "noise_seed", "noiseSeed"):
        if data.get(key) not in (None, ""):
            return _response_seed_value(data.get(key))
    for nest_key in ("data", "result", "output", "images", "meta", "metadata"):
        nest = data.get(nest_key)
        if isinstance(nest, list) and nest:
            item = nest[0]
            if isinstance(item, dict):
                for key in ("seed", "noise_seed", "noiseSeed"):
                    if item.get(key) not in (None, ""):
                        return _response_seed_value(item.get(key))
        elif isinstance(nest, dict):
            for key in ("seed", "noise_seed", "noiseSeed"):
                if nest.get(key) not in (None, ""):
                    return _response_seed_value(nest.get(key))
    return None


def _clamp_seed(raw):
    """Parse Nano seed as integer. Never modulo, clip, drop, or invent an int32 max.

    Official WaveSpeed krea-v2/turbo-lora: seed is integer, Range "-", -1 = random.
    Official NanoGPT Image API: seed is optional integer, no min/max in the schema.
    None/''/'random' → omit. Non-int or < -1 → ValueError 中文.
    """
    if raw in (None, "", "random"):
        return None
    try:
        return _finite_number(raw, "seed", integer=True, minimum=-1)
    except ValueError:
        raise ValueError(
            f"NanoGPT 种子必须是整数（≥ -1），收到 {raw!r}，拒绝静默取模"
        ) from None


def _seed_clamp_meta(raw):
    """No silent int32 wrap. Valid/omitted seed never sets seedClamped; invalid raises."""
    if raw in (None, "", "random"):
        return {}
    _clamp_seed(raw)
    return {}


def _i2i_strength(payload):
    """Map denoise/strength for input_references. Never invent 0.65.

    Both omitted → None (omit key, official default). Explicit null or
    non-finite/non-numeric → ValueError. Conflicting denoise vs strength → ValueError.
    """
    payload = payload or {}
    found = []
    for key in ("denoise", "strength"):
        if key not in payload:
            continue
        val = payload.get(key)
        if val == "":
            continue
        found.append((key, val))
    if not found:
        return None
    non_null = [(k, v) for k, v in found if v is not None]
    if not non_null:
        raise ValueError("NanoGPT 图生图 strength 为 null，拒绝默认 0.65")
    values = [_finite_number(v, "strength") for _, v in non_null]
    if any(x != values[0] for x in values[1:]):
        raise ValueError("denoise 与 strength 冲突，拒绝覆盖")
    return values[0]


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


def _parameter_options(spec, name):
    sp = (spec or {}).get("supported_parameters") or {}
    param = (sp.get("parameters") or sp).get(name) or {}
    if isinstance(param, list):
        return param
    if not isinstance(param, dict):
        return []
    values = param.get("options") or param.get("values") or []
    return [x.get("value") if isinstance(x, dict) else x for x in values]


def _resolutions(spec):
    sp = (spec or {}).get("supported_parameters") or {}
    return [str(x) for x in (sp.get("resolutions") or _parameter_options(spec, "resolution"))
            if x not in (None, "")]


def pick_resolution(spec, w=None, h=None, preferred=None):
    """Pick a catalog resolution token the model actually lists.

    Empty catalog resolutions → None (caller must 400). Never invent `{w}x{h}`.
    preferred miss → None. No preferred and no exact catalog WxH → None.
    No size-tier, aspect, Fal-name, nearest-pixel, auto, or first-token fallback.
    """
    res = _resolutions(spec)
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
        # A user/model-selected token is a contract, not a hint. Do not
        # silently replace it with an aspect/area-nearest catalog value.
        return None
    try:
        wi = int(w) if w not in (None, "") else 0
        hi = int(h) if h not in (None, "") else 0
    except (TypeError, ValueError):
        wi = hi = 0
    if wi and hi:
        hit = low.get(f"{wi}x{hi}")
        if hit:
            return hit
    return None



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
            row = {"path": path}
            if it.get("scale") not in (None, ""):
                row["scale"] = it.get("scale")
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


def _nano_lora_scale_field(it) -> float | None:
    """Fal-aligned: null/missing strength → omit scale (never invent 1.0).

    Plain string LoRA entries omit scale. Invalid non-numeric → ValueError.
    Clip only when a real numeric scale is provided.
    """
    if isinstance(it, str):
        return None
    if not isinstance(it, dict):
        return None
    if "scale" in it:
        raw_s = it.get("scale")
    elif "strength" in it:
        raw_s = it.get("strength")
    else:
        return None
    if raw_s in (None, ""):
        return None
    try:
        if isinstance(raw_s, bool):
            raise ValueError()
        scale = float(raw_s)
        if not math.isfinite(scale):
            raise ValueError()
    except (TypeError, ValueError, OverflowError):
        raise ValueError(f"lora scale 必须是有限数值，收到 {raw_s!r}，不能缺省为 1.0") from None
    return max(0.0, min(4.0, scale))


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
        scale = None
        if isinstance(it, str):
            name = it.strip() or "LoRA"
            # o50: plain string → omit scale (do not invent 1.0)
            try:
                scale = _nano_lora_scale_field(it)
            except ValueError as e:
                failed.append({"name": name, "error": str(e)})
                continue
            vid = civitai_version_id(it)
            dl = civitai_download_api_url(it)
            path_hint = it.strip()
        elif isinstance(it, dict):
            name = str(it.get("name") or it.get("path") or it.get("air") or "LoRA")
            try:
                scale = _nano_lora_scale_field(it)
            except ValueError as e:
                failed.append({"name": name, "error": str(e)})
                continue
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
            row = {
                "path": resolved,
                "name": name,
                "versionId": vid or "",
                "downloadUrl": dl or (f"https://civitai.com/api/download/models/{vid}" if vid else ""),
            }
            if scale is not None:
                row["scale"] = scale
            out.append(row)
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
            name = path
            scale = _nano_lora_scale_field(it)  # None → omit
        elif isinstance(it, dict):
            path = (it.get("path") or it.get("downloadUrl") or it.get("url") or it.get("air") or "").strip()
            name = it.get("name") or path
            scale = _nano_lora_scale_field(it)  # ValueError fail-closed; None omit
            if (not path or path.lower().startswith("urn:")) and str(it.get("versionId") or "").isdigit():
                path = "https://civitai.com/api/download/models/" + str(it.get("versionId"))
        else:
            continue
        if not path or path.lower().startswith("urn:"):
            continue
        row = {"path": path, "name": name}
        if scale is not None:
            row["scale"] = scale
        out.append(row)
        if len(out) >= 3:
            break
    return out


_EDIT_ID_RE = re.compile(r"(?:^|[/_\-])edit(?:/|$)", re.I)
_EDIT_NAME_RE = re.compile(r"(?:^|[\s\-])edit(?:\s|$)", re.I)


def _looks_like_required_edit(mid: str, name: str = "") -> bool:
    """Catalog ids like openai/.../flare/edit or names ending in Edit require ≥1 input image."""
    if _EDIT_ID_RE.search((mid or "").strip()):
        return True
    if _EDIT_NAME_RE.search((name or "").strip()):
        return True
    return False


def _min_input_images(spec: dict | None) -> int:
    spec = spec or {}
    if spec.get("needsSource"):
        return 1
    if _looks_like_required_edit(spec.get("id") or "", spec.get("name") or ""):
        return 1
    return 0


def _image_eats_refs(spec: dict | None) -> bool:
    """False only when catalog explicitly says this row is not image-to-image.

    Flare/Sunburst text-to-image advertise image_generation and image_to_image=false.
    Attaching input_references there makes Nano ignore the product photos and still
    return 200 — the canvas then writes a green success that is not the connected refs.
    """
    spec = spec or {}
    if spec.get("needsSource"):
        return True
    if _looks_like_required_edit(spec.get("id") or "", spec.get("name") or ""):
        return True
    caps = spec.get("capabilities") or {}
    if caps.get("image_to_image") is True or caps.get("inpainting") is True:
        return True
    if caps.get("image_to_image") is False:
        return False
    return True


def _source_images(payload: dict, spec: dict | None = None) -> list:
    """Collect refs for Nano input_references. Over-cap / unknown cap fail, never slice."""
    from .ref_images import payload_ref_images, materialize_local_refs
    from .capabilities import get_provider_capabilities
    caps = get_provider_capabilities("nano-gpt")
    item = spec if isinstance(spec, dict) and spec else None
    if item is None:
        try:
            mid = model_id((payload or {}).get("serviceId") or "")
            item = find_spec(mid) if mid else None
        except Exception:
            item = None
    raw = payload_ref_images(payload, backend="nano-gpt", caps=caps, item=item or {})
    return materialize_local_refs(raw)


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
    elif i2i and _looks_like_required_edit(mid, name):
        # Flare/Sunburst Edit etc. also advertise image_generation, so the
        # i2i-and-not-t2i branch never fired — Nano then 400'd "requires 1..N".
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
    i2v = caps.get("image_to_video") is True
    t2v = caps.get("text_to_video") is True
    row = {
        "id": mid,
        "name": name,
        "category": "video",
        "backend": "nano-gpt",
        "status": "available",
        "task": "text-to-video" if t2v else ("image-to-video" if i2v else "video"),
        "tags": tags,
        "pricing": it.get("pricing") or {},
        "supported_parameters": dict(it.get("supported_parameters") or {}),
        "capabilities": caps,
        "description": it.get("description") or "",
    }
    if i2v and not t2v:
        row["needsFirstFrame"] = True
    # Detailed video discovery nests selectors under parameters, unlike images.
    # Keep the official schema and expose its exact tokens to the existing UI.
    if _resolutions(it):
        row["supported_parameters"]["resolutions"] = _resolutions(it)
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


def _image_count(payload, spec):
    # Nano's documented alias precedence; quantity is Studio's input name.
    raw = payload.get("nImages", payload.get("n", payload.get("quantity", 1)))
    try:
        if isinstance(raw, bool) or not re.fullmatch(r"[0-9]+", str(raw)):
            raise ValueError()
        n = int(raw)
        if n < 1:
            raise ValueError()
    except (TypeError, ValueError, OverflowError):
        raise ValueError("NanoGPT 图片数量必须是正整数，拒绝静默改值") from None
    if "quantity" in payload and (isinstance(payload["quantity"], bool) or
                                  not re.fullmatch(r"[0-9]+", str(payload["quantity"])) or
                                  int(payload["quantity"]) != n):
        raise ValueError("quantity 与 n/nImages 冲突，拒绝覆盖")
    sp = (spec or {}).get("supported_parameters") or {}
    count_spec = sp.get("n") or {}
    low = count_spec.get("min", 1) if isinstance(count_spec, dict) else 1
    high = count_spec.get("max") if isinstance(count_spec, dict) else None
    if high is None:
        high = sp.get("max_output_images")
    if high is None and n > 1:
        raise ValueError("NanoGPT 当前模型目录未声明多图数量上限，拒绝猜测")
    if n < low or (high is not None and n > high):
        raise ValueError(f"NanoGPT 当前模型图片数量范围为 {low}–{high}，拒绝截断")
    return n


def _image_body(payload: dict, spec: dict) -> dict:
    w = payload.get("width")
    h = payload.get("height")
    n = _image_count(payload, spec)
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
    imgs = _source_images(payload, spec)
    min_in = _min_input_images(spec)
    if min_in and len(imgs) < min_in:
        max_in = ((spec or {}).get("supported_parameters") or {}).get("max_input_images")
        rng = f"{min_in}–{max_in}" if max_in else str(min_in)
        raise ValueError(
            f"当前模型需要 {rng} 张参考图，请求里是 {len(imgs)} 张。请先把图片连到分镜，不能静默发 0 张"
        )
    if imgs and not _image_eats_refs(spec):
        raise ValueError(
            f"当前模型是文生图，不吃参考图（已连 {len(imgs)} 张）。请改选 Edit 模型或断开参考连线，不能静默忽略"
        )
    if imgs:
        # NanoGPT rejects mixing input_references with image / imageDataUrl / image_url.
        body["input_references"] = imgs
        strength = _i2i_strength(payload)
        if strength is not None:
            body["strength"] = strength
    steps = payload.get("steps")
    if steps not in (None, ""):
        n_steps = _finite_number(steps, "steps", integer=True)
        body["num_inference_steps"] = n_steps
        body["steps"] = n_steps
    cfg = payload.get("cfgScale")
    if cfg not in (None, ""):
        body["guidance_scale"] = _finite_number(cfg, "cfgScale")
    loras = _loras(payload)
    if loras:
        packed = []
        for x in loras:
            row = {"path": x["path"]}
            if "scale" in x:
                row["scale"] = x["scale"]
            packed.append(row)
        body["loras"] = packed
        for i, item in enumerate(loras, 1):
            body[f"lora_{i}_url"] = item["path"]
            if "scale" in item:
                body[f"lora_{i}_scale"] = item["scale"]
    if payload.get("allowMatureContent"):
        body["enable_safety_checker"] = False
    return body


def _core_image_body(full: dict) -> dict:
    """OAI / generations + edit JSON body: imageDataUrl(s) only — never mix input_references.

    Normalized POST /api/v1/images keeps input_references on `full`. This helper is for
    OpenAI-compatible routes that expect imageDataUrl / imageDataUrls instead.
    """
    keep = (
        "model", "prompt", "n", "nImages", "resolution", "size", "aspect_ratio",
        "seed", "negative_prompt", "strength", "loras", "guidance_scale",
        "num_inference_steps", "response_format",
    )
    body = {k: full[k] for k in keep if k in full}
    refs = full.get("input_references")
    if isinstance(refs, list) and refs:
        body["imageDataUrls"] = list(refs)
        body["imageDataUrl"] = refs[0]
    else:
        # Pass through explicit OAI fields only when no input_references bag.
        for k in ("imageDataUrls", "imageDataUrl", "imageUrl", "image"):
            if k in full:
                body[k] = full[k]
    return body


def _edit_image_body(full: dict) -> dict:
    """Edit endpoint JSON: same imageDataUrl(s) shape as OAI, never input_references."""
    return _core_image_body(full)


def _is_empty_input_images_error(err) -> bool:
    """True for upstream 'requires between 1 and N input images' (refs never arrived)."""
    if isinstance(err, dict):
        msg = str(err.get("error") or err.get("message") or err)
    else:
        msg = str(err or "")
    low = msg.lower()
    if "input image" not in low and "input_image" not in low:
        return False
    return ("requires between" in low) or ("between 1 and" in low) or ("at least 1" in low)


def _image_body_audit(body: dict | None) -> dict:
    """Lengths only — never dump data URLs."""
    body = body if isinstance(body, dict) else {}
    refs = body.get("input_references")
    urls = body.get("imageDataUrls")
    n_refs = len(refs) if isinstance(refs, list) else 0
    n_urls = len(urls) if isinstance(urls, list) else (1 if body.get("imageDataUrl") else 0)
    return {
        "nInputReferences": n_refs,
        "nImageDataUrls": n_urls,
        "hasImageDataUrl": bool(body.get("imageDataUrl")),
    }


def _image_endpoint_candidates(spec: dict | None, full: dict) -> list:
    """Ordered (url, body) attempts. Edit models prefer /images/edit(s) + imageDataUrls."""
    norm = dict(full)  # keeps input_references only style from _image_body
    oai = _core_image_body(full)
    edit = _edit_image_body(full)
    if _looks_like_required_edit((spec or {}).get("id") or "", (spec or {}).get("name") or ""):
        return [
            (GEN_IMAGES_EDITS, edit),
            (GEN_IMAGES_EDIT, edit),
            (GEN_IMAGES, norm),
            (GEN_IMAGES_OAI, oai),
        ]
    return [
        (GEN_IMAGES, norm),
        (GEN_IMAGES_OAI, oai),
    ]



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
    from .ref_images import collect_ref_images, materialize_local_refs

    for field in ("prompt", "negativePrompt", "resolution", "lastFrame", "last_image"):
        if payload.get(field) is not None and not isinstance(payload[field], str):
            raise ValueError(f"{field} 必须是文本")
    sp = spec.get("supported_parameters") or {}
    params = sp.get("parameters") or sp
    caps = spec.get("capabilities") or {}
    # Do not let invalid/local media disappear in the shared URL collector and
    # accidentally turn an intended I2V request into a billable T2V request.
    for field in ("firstFrame", "sourceImage", "startImage", "image_url", "imageUrl",
                  "imageDataUrl", "image", "images", "referenceImages", "input_references", "image_urls"):
        value = payload.get(field)
        if value in (None, "", []):
            continue
        if isinstance(value, list) and field not in ("images", "referenceImages", "input_references", "image_urls"):
            raise ValueError(f"{field} 必须是单张图片")
        for image in value if isinstance(value, list) else [value]:
            if not isinstance(image, str) or not image.startswith(("http://", "https://", "data:image/", "/out/")):
                raise ValueError(f"{field} 必须是 HTTP(S) 图片 URL、图片 data URL 或已上传的 /out 文件")
    imgs = materialize_local_refs(collect_ref_images(payload))
    modes = {"t2v": "text-to-video", "i2v": "image-to-video"}
    requested = []
    for key in ("mode", "op", "operation"):
        value = payload.get(key)
        if value in (None, "", "auto", "video", "image"):
            continue
        if not isinstance(value, str):
            raise ValueError(f"{key} 必须是文本")
        mode = modes.get(value, value)
        if mode not in ("text-to-video", "image-to-video"):
            raise ValueError(f"NanoGPT 当前视频适配器未接入 {key}={value}")
        requested.append(mode)
    if len(set(requested)) > 1:
        raise ValueError("视频 mode/op/operation 冲突，拒绝换模式")
    mode = requested[0] if requested else ("image-to-video" if imgs else "text-to-video")
    _image_count(payload, {"supported_parameters": {"max_output_images": 1}})
    last = payload.get("lastFrame") or payload.get("last_image")
    if payload.get("lastFrame") and payload.get("last_image") and payload["lastFrame"] != payload["last_image"]:
        raise ValueError("lastFrame 与 last_image 冲突")
    for field in ("last_frame_url", "end_image_url", "tail_image_url", "endImage",
                  "videoUrl", "videoDataUrl", "video", "audioUrl", "audioDataUrl", "audio", "script"):
        if payload.get(field) not in (None, "", []):
            raise ValueError(f"NanoGPT 当前 T2V/I2V 适配器未接入 {field}，拒绝丢参")
    if mode == "text-to-video" and (imgs or last):
        raise ValueError("纯文生视频不能带首帧、尾帧或参考图；不会自动改成图生视频")
    if mode == "text-to-video" and not (payload.get("prompt") or "").strip():
        raise ValueError("纯文生视频需要非空 prompt")
    capability = mode.replace("-", "_")
    if caps.get(capability) is not True:
        raise ValueError(f"NanoGPT 当前模型官方目录未声明支持 {mode}")
    if mode == "image-to-video" and len(imgs) != 1:
        raise ValueError("NanoGPT 图生视频需要恰好一张首帧，不能丢弃多余参考图")
    if last:
        # Public GET /video-models?detailed=true declares this exact key only
        # for some models. Never infer last_frame_url/lastFrame from the name.
        if not isinstance(params.get("last_image"), dict):
            raise ValueError("NanoGPT 当前模型官方目录未声明尾帧字段 last_image")
        if not isinstance(last, str) or not last.startswith(("https://", "http://")):
            raise ValueError("NanoGPT last_image 需要公开 HTTP(S) 图片 URL")
    mid = model_id(payload.get("serviceId") or spec.get("id") or "")
    body = {"model": mid, "prompt": payload.get("prompt") or "", "mode": mode}
    neg = (payload.get("negativePrompt") or "").strip()
    if neg:
        body["negative_prompt"] = neg
    dur = payload.get("duration")
    if dur not in (None, ""):
        options = _parameter_options(spec, "duration")
        if not options or str(dur) not in [str(x) for x in options]:
            raise ValueError("duration 必须是当前视频模型目录中的原始选项")
        body["duration"] = str(dur)
    w, h = payload.get("width"), payload.get("height")
    ar = payload.get("aspect_ratio") or payload.get("aspectRatio")
    if payload.get("aspect_ratio") and payload.get("aspectRatio") and payload["aspect_ratio"] != payload["aspectRatio"]:
        raise ValueError("aspectRatio 与 aspect_ratio 冲突")
    if ar:
        if ar not in _parameter_options(spec, "aspect_ratio"):
            raise ValueError("aspect_ratio 必须是当前视频模型目录中的原始选项")
        body["aspect_ratio"] = ar
    res = pick_resolution(spec, w, h, preferred=(payload or {}).get("resolution"))
    if res:
        body["resolution"] = res
    elif payload.get("resolution") or w not in (None, "") or h not in (None, ""):
        raise ValueError("无法从当前视频模型目录选中 resolution token，拒绝近似尺寸")
    elif _resolutions(spec):
        raise ValueError("请在构图里选一个目录视频 resolution token")
    seed = _clamp_seed(payload.get("seed"))
    if seed is not None:
        body["seed"] = seed
    if imgs:
        body["imageDataUrl" if imgs[0].startswith("data:") else "imageUrl"] = imgs[0]
    if last:
        body["last_image"] = last
    loras = _loras(payload)
    if loras:
        packed = []
        for x in loras:
            row = {"path": x["path"]}
            if "scale" in x:
                row["scale"] = x["scale"]
            packed.append(row)
        body["loras"] = packed
        for i, item in enumerate(loras, 1):
            body[f"lora_{i}_url"] = item["path"]
            if "scale" in item:
                body[f"lora_{i}_scale"] = item["scale"]
    return body


class NanoGptProvider(Provider):
    id = "nano-gpt"
    label = "NanoGPT"

    def has_key(self) -> bool:
        return bool(nano_key())

    def search_loras(self, q: str, nsfw: bool = True):
        # Nano LoRA path is Hub owner/repo or a download URL — same index Fal uses.
        from . import huggingface as hf
        code, payload = hf.search_loras(q)
        items = []
        for it in (payload.get("items") if isinstance(payload, dict) else None) or []:
            if not isinstance(it, dict):
                continue
            row = dict(it)
            row["source"] = "nano-gpt"
            row["backend"] = "nano-gpt"
            items.append(row)
        return code, {"items": items, "backend": "nano-gpt"}

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
            n = _image_count(payload, spec)
        except ValueError as exc:
            return 400, {"error": str(exc), "serviceId": mid}
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
        try:
            _image_count(payload, spec)
        except ValueError as exc:
            return 400, {"error": str(exc), "serviceId": mid}
        if not _resolutions(spec):
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
        try:
            full = _image_body(pl, spec)
        except ValueError as exc:
            return 400, {"error": str(exc), "serviceId": mid}
        if not full.get("resolution") and not full.get("size"):
            return 400, {
                "error": "无法从目录选中 resolution token，请在构图里选一个目录分辨率",
                "serviceId": mid,
            }
        # Persist download API URL / versionId — never long-lived B2 signed query.
        persist_body = sanitize_submitted_for_persist(full, lora_meta)
        jid = f"nano-gpt|img|{uuid.uuid4().hex[:12]}"
        # Seed is fail-closed in _image_body (no int32 modulo). meta.seed prefers
        # API response seed; fallback submitted.
        submitted_seed = full.get("seed")
        meta = {
            "backend": self.id,
            "serviceId": mid,
            "prompt": (payload or {}).get("prompt"),
            "negativePrompt": (payload or {}).get("negativePrompt"),
            "seed": submitted_seed,
            "jobId": jid,
            "submittedInput": persist_body,
        }
        headers = _auth()
        last = (502, {"error": "NanoGPT 出图失败"})
        local_refs = full.get("input_references") if isinstance(full.get("input_references"), list) else []
        local_n_refs = len(local_refs)
        endpoint_tried: list = []
        saw_empty_image = False
        for url, body in _image_endpoint_candidates(spec, full):
            audit = _image_body_audit(body)
            endpoint_tried.append({
                "url": url,
                "nInputReferences": audit["nInputReferences"],
                "nImageDataUrls": audit["nImageDataUrls"],
            })
            print(
                "[nano] image-attempt",
                json.dumps({
                    "serviceId": mid,
                    "nRefs": local_n_refs,
                    "endpointTried": url,
                    **audit,
                }, ensure_ascii=False)[:800],
                flush=True,
            )
            code, data = json_call(url, method="POST", headers=headers, body=body, timeout=180)
            if not isinstance(data, dict):
                last = (code if code >= 400 else 502, {"error": str(data)})
                continue
            if code >= 400:
                data.setdefault("error", extract_error(data, f"HTTP {code}"))
                if _is_empty_input_images_error(data):
                    saw_empty_image = True
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
                    "nRefs": local_n_refs,
                    "endpointTried": [e["url"] for e in endpoint_tried],
                }
                return 200, out
            last = (502, {"error": "NanoGPT 没有返回图片", "raw": json.dumps(data)[:400]})
        # Fail-closed: local bag had refs but every path claimed 0 input images.
        if saw_empty_image and local_n_refs >= 1:
            code, data = last
            if not isinstance(data, dict):
                data = {"error": str(data)}
            else:
                data = dict(data)
            upstream = data.get("error") or "upstream rejected input images"
            tried_urls = [e["url"] for e in endpoint_tried]
            data["error"] = (
                f"{upstream} · local_nRefs={local_n_refs} but upstream saw 0 "
                f"(endpoints={tried_urls})"
            )
            data["local_nRefs"] = local_n_refs
            data["endpointTried"] = tried_urls
            data["nRefs"] = local_n_refs
            data["refAudit"] = endpoint_tried
            return (code if code >= 400 else 400), data
        if isinstance(last[1], dict):
            last[1].setdefault("nRefs", local_n_refs)
            last[1].setdefault("endpointTried", [e["url"] for e in endpoint_tried])
        return last

    def _generate_video(self, payload, spec, mid):
        too = prompt_length_error((payload or {}).get("prompt"))
        if too:
            return 400, too
        sp = (spec or {}).get("supported_parameters") or {}
        if not sp:
            return 400, {
                "error": "当前 NanoGPT 视频模型目录没有 supported_parameters/resolutions，不能猜测参数",
                "serviceId": mid,
            }
        try:
            body = _video_body(payload, spec)
        except ValueError as exc:
            return 400, {"error": str(exc), "serviceId": mid}
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
        if raw_loras:
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


def _row_text(it: dict) -> dict:
    """Normalize official GET /api/v1/models rows for vision/chat selectors."""
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
    """Fetch official NanoGPT text model IDs. Empty failure raises; never invents a model id."""
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


from . import register  # noqa: E402

register(NanoGptProvider())
