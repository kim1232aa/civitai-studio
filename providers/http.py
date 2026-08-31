from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path

DEFAULT_OUT = Path(__file__).resolve().parent.parent / "out"


def json_call(url: str, method="GET", headers=None, body=None, timeout=90):
    """Shared JSON HTTP. Callers pass Authorization; this helper never adds it."""
    hdrs = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0",
    }
    if headers:
        hdrs.update(headers)
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, headers=hdrs, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read()
            try:
                parsed = json.loads(raw.decode())
            except json.JSONDecodeError:
                parsed = {"raw": raw[:2000].decode("utf-8", "replace")}
            return r.status, parsed
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            parsed = {"raw": raw[:2000]}
        if isinstance(parsed, dict):
            parsed = dict(parsed)
            parsed.setdefault(
                "error",
                parsed.get("title") or parsed.get("detail") or parsed.get("msg") or f"HTTP {e.code}",
            )
        return e.code, parsed
    except urllib.error.URLError as e:
        return 502, {"error": "网络错误", "detail": str(getattr(e, "reason", e))}
    except Exception as e:
        return 502, {"error": "请求失败", "detail": str(e)}


def sniff_media(raw: bytes) -> tuple[str, str]:
    if raw[:8] == b"\x89PNG\r\n\x1a\n":
        return ".png", "image"
    if raw[:3] == b"\xff\xd8\xff":
        return ".jpg", "image"
    if b"ftyp" in raw[:12]:
        return ".mp4", "video"
    if raw[:4] == b"RIFF":
        kind4 = raw[8:12] if len(raw) >= 12 else b""
        if kind4 == b"WEBP":
            return ".webp", "image"
        if kind4 == b"WAVE":
            return ".wav", "audio"
        return ".webp", "image"
    return ".bin", "image"


def save_media_urls(urls, stem, out_dir=None):
    """Download URLs, sniff png/jpg/mp4/webp/riff, write out_dir, return [{file,url,bytes,kind}]."""
    out = Path(out_dir or DEFAULT_OUT)
    out.mkdir(parents=True, exist_ok=True)
    saved = []
    stem = str(stem or "media").replace("|", "_").replace("/", "_")
    for i, url in enumerate(urls or []):
        if not url or not isinstance(url, str):
            continue
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=120) as r:
            raw = r.read()
        ext, kind = sniff_media(raw)
        name = f"{stem}_{i}{ext}"
        (out / name).write_bytes(raw)
        saved.append({"file": name, "url": f"/out/{name}", "bytes": len(raw), "kind": kind})
    return saved


def parse_job_id(job_id: str) -> tuple[str, str]:
    """Return (provider_id, opaque). New jobs use `{provider}|rest`. Bare UUIDs default to civitai.
    Fal keeps `fal|{endpoint}|{request_id}` so opaque is `{endpoint}|{request_id}`."""
    s = job_id or ""
    if "|" in s:
        pid, rest = s.split("|", 1)
        if pid:
            return pid, rest
    return "civitai", s


def collect_urls(obj) -> list[str]:
    """Pull http(s) URLs out of typical image/video result blobs."""
    urls = []

    def add(val):
        if isinstance(val, str) and val.startswith("http"):
            urls.append(val)
        elif isinstance(val, dict) and val.get("url"):
            if val.get("available") is False:
                return
            u = val.get("url")
            if isinstance(u, str) and u.startswith("http"):
                urls.append(u)
        elif isinstance(val, list):
            for item in val:
                add(item)

    if isinstance(obj, dict):
        for key in ("images", "image", "videos", "video", "blobs", "audio", "audios"):
            if key in obj:
                add(obj.get(key))
    elif isinstance(obj, list):
        add(obj)
    return urls


def raw_call(url: str, method="POST", headers=None, body=None, timeout=120):
    """HTTP that may return bytes. Does not force JSON Accept. No auth added."""
    hdrs = {"User-Agent": "Mozilla/5.0"}
    if headers:
        hdrs.update(headers)
    data = None
    if body is not None:
        if isinstance(body, (bytes, bytearray)):
            data = bytes(body)
        else:
            data = json.dumps(body).encode()
            hdrs.setdefault("Content-Type", "application/json")
    req = urllib.request.Request(url, data=data, headers=hdrs, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read()
            ctype = r.headers.get("Content-Type") or ""
            return r.status, raw, ctype
    except urllib.error.HTTPError as e:
        raw = e.read()
        ctype = e.headers.get("Content-Type") if e.headers else ""
        return e.code, raw, ctype or ""
    except urllib.error.URLError as e:
        return 502, str(getattr(e, "reason", e)).encode(), "text/plain"
    except Exception as e:
        return 502, str(e).encode(), "text/plain"


def save_bytes(raw: bytes, stem, out_dir=None):
    out = Path(out_dir or DEFAULT_OUT)
    out.mkdir(parents=True, exist_ok=True)
    ext, kind = sniff_media(raw)
    if ext == ".bin" and raw[:4] == b"RIFF":
        ext, kind = ".webp", "image"
    name = f"{str(stem or 'media').replace('|', '_').replace('/', '_')}_0{ext}"
    (out / name).write_bytes(raw)
    return [{"file": name, "url": f"/out/{name}", "bytes": len(raw), "kind": kind}]
