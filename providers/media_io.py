"""E5: real POST /api/caption and POST /api/upload-out."""
from __future__ import annotations

import base64
import mimetypes
import os
import re
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

from .http import DEFAULT_OUT, sniff_media
from .io_meta import decode_data_url

ROOT = Path(__file__).resolve().parent.parent
OUT = DEFAULT_OUT
STATIC = ROOT / "static"
MAX_UPLOAD_BYTES = 25 * 1024 * 1024
_SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]+")

CAPTION_PROMPT = (
    "请用中文按下列标签描述这张图，输出必须能直接当作可编辑的反推提示词。"
    "没有依据的标签留空，禁止编造角色名、剧情、服装或光线。"
    "不要前言、不要解释。格式：\n"
    "【反推提示词】\n"
    "主体：\n"
    "外观：\n"
    "服装：\n"
    "姿态：\n"
    "场景：\n"
    "光线：\n"
    "构图：\n"
    "画面：\n"
    "运镜：\n"
    "约束：\n"
    "负面："
)


def _mime_from_header(header: str) -> str:
    rest = (header or "")[5:] if (header or "").startswith("data:") else (header or "")
    mime = rest.split(";", 1)[0].strip().lower()
    return mime or "application/octet-stream"


def resolve_media_bytes(url: str) -> tuple[bytes, str]:
    u = (url or "").strip()
    if not u:
        raise ValueError("缺少 url")
    if u.startswith("data:"):
        header = u.split(",", 1)[0]
        raw = decode_data_url(u)
        if not raw:
            raise ValueError("dataUrl 不是合法 base64")
        return raw, _mime_from_header(header)
    path = None
    if u.startswith("/out/"):
        path = OUT / Path(u.split("/out/", 1)[1]).name
    elif u.startswith("/static/"):
        path = STATIC / Path(u.split("/static/", 1)[1]).name
    if path is not None:
        resolved = path.resolve()
        allowed = (OUT.resolve(), STATIC.resolve())
        if not any(resolved == root or root in resolved.parents for root in allowed):
            raise ValueError("拒绝读取资产目录以外的路径")
        if not resolved.is_file():
            raise FileNotFoundError(f"本地资产不存在：{u}")
        mime = mimetypes.guess_type(str(resolved))[0] or "application/octet-stream"
        return resolved.read_bytes(), mime
    if u.startswith("http://") or u.startswith("https://"):
        req = urllib.request.Request(u, headers={"User-Agent": "civitai-studio-caption"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read(MAX_UPLOAD_BYTES + 1)
            if len(raw) > MAX_UPLOAD_BYTES:
                raise ValueError("远程图片过大")
            mime = (resp.headers.get("Content-Type") or "application/octet-stream").split(";", 1)[0]
            return raw, mime
    raise ValueError(f"不支持的 url：{u}")


def as_data_url(raw: bytes, mime: str) -> str:
    kind = (mime or "").split(";", 1)[0].strip() or "image/jpeg"
    if kind == "application/octet-stream":
        ext, _media = sniff_media(raw)
        kind = {".png": "image/png", ".jpg": "image/jpeg", ".webp": "image/webp"}.get(ext, "image/jpeg")
    return f"data:{kind};base64,{base64.b64encode(raw).decode('ascii')}"


def _is_public_http(url: str) -> bool:
    u = (url or "").strip().lower()
    if not u.startswith(("http://", "https://")):
        return False
    host = urllib.parse.urlparse(url).hostname or ""
    if host in ("127.0.0.1", "localhost", "::1") or host.startswith("192.168.") or host.startswith("10."):
        return False
    return True


def caption_request(payload: dict | None) -> tuple[int, dict]:
    payload = payload or {}
    url = (payload.get("url") or payload.get("mediaUrl") or "").strip()
    if not url:
        return 400, {"error": "缺少 url", "code": "missing_url"}
    model = (payload.get("model") or "").strip()
    errors = []

    from . import nanogpt as nano_mod

    if nano_mod.nano_key():
        try:
            raw, mime = resolve_media_bytes(url)
        except FileNotFoundError as e:
            return 404, {"error": str(e), "code": "not_found"}
        except ValueError as e:
            return 400, {"error": str(e), "code": "bad_url"}
        except urllib.error.URLError as e:
            return 502, {"error": f"读取资产失败：{getattr(e, 'reason', e)}", "code": "fetch_failed"}
        data_url = url if url.startswith("data:") else as_data_url(raw, mime)
        code, data = nano_mod.caption_image(data_url, model=model)
        if code < 400 and isinstance(data, dict) and (data.get("caption") or "").strip():
            return code, data
        errors.append(data if isinstance(data, dict) else {"error": str(data)})
    else:
        errors.append({"error": "没有 NanoGPT API Key", "code": "no_key"})

    from . import civitai as civitai_mod

    if civitai_mod.has_key() and _is_public_http(url):
        code, data = civitai_mod.caption_media(url, model=model or "joy-caption")
        if code < 400 and isinstance(data, dict) and (data.get("caption") or "").strip():
            return code, data
        errors.append(data if isinstance(data, dict) else {"error": str(data)})
    elif civitai_mod.has_key() and not _is_public_http(url):
        errors.append(
            {
                "error": "Civitai mediaCaptioning 只接受公网 http(s) URL，本地 /out 资产请走 NanoGPT 视觉",
                "code": "local_url",
            }
        )

    detail = "；".join(
        str(x.get("error") or x) for x in errors if x
    ) or "没有可用的视觉打标后端"
    return 503, {
        "error": f"视觉打标失败：{detail}",
        "code": "caption_unavailable",
        "errors": errors,
    }


def upload_out_request(payload: dict | None, out_dir: Path | None = None) -> tuple[int, dict]:
    payload = payload or {}
    data_url = payload.get("dataUrl") or payload.get("data_url") or ""
    if not isinstance(data_url, str) or not data_url.startswith("data:"):
        return 400, {"error": "需要 dataUrl（data:...;base64,...）", "code": "invalid_data_url"}
    header = data_url.split(",", 1)[0]
    raw = decode_data_url(data_url)
    if not raw:
        return 400, {"error": "dataUrl 不是合法 base64 或为空", "code": "invalid_data_url"}
    if len(raw) > MAX_UPLOAD_BYTES:
        return 400, {"error": f"文件过大（{len(raw)}>{MAX_UPLOAD_BYTES}）", "code": "too_large"}
    from .http import is_blank_image
    if is_blank_image(raw=raw):
        return 400, {"error": "这是空图/1×1 占位，不入库", "code": "blank_image"}
    mime = _mime_from_header(header)
    ext, kind = sniff_media(raw)
    if ext == ".bin":
        guessed = mimetypes.guess_extension(mime) or ""
        if guessed:
            ext = guessed if guessed.startswith(".") else f".{guessed}"
        elif mime.startswith("image/"):
            ext = ".png"
        else:
            return 400, {"error": f"无法识别的文件类型：{mime}", "code": "unsupported_type"}
    given = Path(str(payload.get("filename") or payload.get("fileName") or "upload")).name
    stem = _SAFE_NAME.sub("_", Path(given).stem) or "upload"
    stamp = time.strftime("%Y%m%d%H%M%S")
    name = f"{stem}_{stamp}_{uuid.uuid4().hex[:8]}{ext}"
    dest_dir = Path(out_dir or OUT)
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / name
    fd, tmp_name = tempfile.mkstemp(prefix=".up_", dir=str(dest_dir))
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(raw)
        os.replace(tmp_name, dest)
    except Exception:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise
    return 200, {
        "url": f"/out/{dest.name}",
        "file": dest.name,
        "bytes": dest.stat().st_size,
        "kind": kind,
    }


def handle_media_post(path: str, payload: dict | None) -> tuple[int, dict]:
    if path == "/api/caption":
        return caption_request(payload)
    if path == "/api/upload-out":
        return upload_out_request(payload)
    return 404, {"error": "not found"}
