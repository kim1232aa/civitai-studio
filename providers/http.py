from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path

DEFAULT_OUT = Path(__file__).resolve().parent.parent / "out"


def extract_error(parsed, fallback="请求失败"):
    """Pull a human error string out of nested provider JSON."""
    if not isinstance(parsed, dict):
        return fallback
    for key in ("error", "message", "msg", "title", "detail"):
        v = parsed.get(key)
        if isinstance(v, str) and v.strip() and v.strip().upper() != f"HTTP {fallback}".upper():
            if not (v.startswith("HTTP ") and len(v) < 12):
                return v.strip()
        if isinstance(v, dict):
            m = v.get("message") or v.get("msg") or v.get("detail")
            if m:
                return str(m)
    errors = parsed.get("errors")
    if isinstance(errors, dict):
        m = errors.get("message") or errors.get("msg") or errors.get("detail")
        if m:
            return str(m)
    if isinstance(errors, str) and errors.strip():
        return errors.strip()
    if isinstance(errors, list) and errors:
        first = errors[0]
        if isinstance(first, str):
            return first
        if isinstance(first, dict):
            return str(first.get("message") or first.get("msg") or first)
    return fallback


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
            parsed.setdefault("error", extract_error(parsed, f"HTTP {e.code}"))
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


def save_media_urls(urls, stem, out_dir=None, meta=None):
    """Download URLs, sniff png/jpg/mp4/webp/riff, write out_dir, return [{file,url,bytes,kind}]."""
    from .io_meta import decode_data_url, write_sidecar
    out = Path(out_dir or DEFAULT_OUT)
    out.mkdir(parents=True, exist_ok=True)
    saved = []
    stem = str(stem or "media").replace("|", "_").replace("/", "_")
    for i, url in enumerate(urls or []):
        if not url or not isinstance(url, str):
            continue
        raw = None
        if url.startswith("data:"):
            raw = decode_data_url(url)
            if not raw:
                continue
        elif url.startswith("http"):
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=120) as r:
                raw = r.read()
        else:
            continue
        ext, kind = sniff_media(raw)
        name = f"{stem}_{i}{ext}"
        (out / name).write_bytes(raw)
        saved.append({"file": name, "url": f"/out/{name}", "bytes": len(raw), "kind": kind})
    saved = drop_blank_saved(saved, out)
    if meta:
        write_sidecar(saved, meta, out)
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


def _looks_media(u: str) -> bool:
    s = (u or "").strip()
    if s.startswith("data:image") or s.startswith("data:video"):
        return True
    if not s.startswith("http"):
        return False
    low = s.lower()
    if "queue.fal.run" in low or ("/requests/" in low and "fal.run" in low):
        return False
    if any(x in low for x in (
        ".png", ".jpg", ".jpeg", ".webp", ".gif", ".mp4", ".webm",
        "fal.media", "v3.fal.media", "v3b.fal.media", "/files/",
        "nano-gpt.com", "nanogpt", "wavespeed.ai",
    )):
        return True
    return False


def collect_urls(obj) -> list[str]:
    """Pull http(s) URLs out of typical image/video result blobs."""
    urls = []

    def add(val):
        if isinstance(val, str) and _looks_media(val):
            urls.append(val)
        elif isinstance(val, dict):
            if val.get("available") is False:
                return
            for k in (
                "url", "image_url", "video_url", "audio_url", "file_url",
                "signed_url", "imageUrl", "videoUrl", "fileUrl",
            ):
                u = val.get(k)
                if isinstance(u, str) and _looks_media(u):
                    urls.append(u)
            for nested in ("images", "image", "videos", "video", "urls", "files", "output"):
                if nested in val and nested != "url":
                    add(val.get(nested))
        elif isinstance(val, list):
            for item in val:
                add(item)

    if isinstance(obj, dict):
        for key in (
            "images", "image", "videos", "video", "blobs", "audio", "audios",
            "image_url", "video_url", "audio_url", "output", "output_images",
            "result", "json_output", "data", "urls", "files", "payload",
            "response",
        ):
            if key in obj:
                add(obj.get(key))
        add(obj)
    elif isinstance(obj, list):
        add(obj)
    seen = []
    for u in urls:
        if u not in seen:
            seen.append(u)
    return seen


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


def is_blank_image(path=None, raw=None) -> bool:
    """True if the file is a real PNG that is essentially all black. Stdlib only."""
    import zlib
    try:
        if raw is None and path:
            raw = Path(path).read_bytes()
        if not raw:
            return True
        if raw[:8] != b"\x89PNG\r\n\x1a\n":
            return False
        offset = 8
        n = len(raw)
        idat = []
        w = h = 0
        while offset + 12 <= n:
            length = int.from_bytes(raw[offset:offset + 4], "big")
            ctype = raw[offset + 4:offset + 8]
            start = offset + 8
            end = start + length
            if end + 4 > n:
                break
            chunk = raw[start:end]
            if ctype == b"IHDR" and length >= 8:
                w = int.from_bytes(chunk[0:4], "big")
                h = int.from_bytes(chunk[4:8], "big")
            elif ctype == b"IDAT":
                idat.append(chunk)
            elif ctype == b"IEND":
                break
            offset = end + 4
        if not idat or w <= 0 or h <= 0:
            return False
        data = zlib.decompress(b"".join(idat))
        if not data:
            return True
        return (sum(data) / len(data)) < 3.0
    except Exception:
        return False


def drop_blank_saved(saved, out_dir=None):
    out = Path(out_dir or DEFAULT_OUT)
    kept = []
    for item in saved or []:
        if not isinstance(item, dict):
            continue
        name = item.get("file") or ""
        fp = out / name if name else None
        raw = None
        if fp and fp.exists():
            raw = fp.read_bytes()
        if raw and is_blank_image(raw=raw):
            try:
                fp.unlink()
            except Exception:
                pass
            continue
        kept.append(item)
    return kept


def save_bytes(raw: bytes, stem, out_dir=None, meta=None):
    from .io_meta import write_sidecar
    out = Path(out_dir or DEFAULT_OUT)
    out.mkdir(parents=True, exist_ok=True)
    ext, kind = sniff_media(raw)
    if ext == ".bin" and raw[:4] == b"RIFF":
        ext, kind = ".webp", "image"
    name = f"{str(stem or 'media').replace('|', '_').replace('/', '_')}_0{ext}"
    (out / name).write_bytes(raw)
    saved = [{"file": name, "url": f"/out/{name}", "bytes": len(raw), "kind": kind}]
    saved = drop_blank_saved(saved, out)
    if meta:
        write_sidecar(saved, meta, out)
    return saved
