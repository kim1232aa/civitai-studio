"""Sidecar metadata, PNG tEXt/iTXt parse, Civitai-id guard. No cloud calls."""
from __future__ import annotations

import json
import re
import threading
import zlib
from pathlib import Path

DEFAULT_OUT = Path(__file__).resolve().parent.parent / "out"

_JOB_META: dict[str, dict] = {}
_JOB_LOCK = threading.Lock()

CIVITAI_PREFIXES = ("image/", "video/", "audio/", "3d/", "utility/")


def looks_like_civitai_service(service_id: str) -> bool:
    s = (service_id or "").strip().lstrip("/")
    if not s:
        return False
    if s.startswith(CIVITAI_PREFIXES):
        return True
    if "/comfy/" in s:
        return True
    return False


def remember_job(job_id: str, meta: dict | None):
    if not job_id:
        return
    with _JOB_LOCK:
        _JOB_META[str(job_id)] = dict(meta or {})


def job_meta(job_id: str) -> dict:
    with _JOB_LOCK:
        return dict(_JOB_META.get(str(job_id) or "") or {})


def sidecar_path(media_name: str, out_dir=None) -> Path:
    out = Path(out_dir or DEFAULT_OUT)
    p = Path(media_name)
    stem = p.stem if p.suffix else str(media_name)
    return out / f"{stem}.json"


def write_sidecar(saved: list, meta: dict | None, out_dir=None):
    if not meta or not saved:
        return
    payload = {
        "backend": meta.get("backend"),
        "serviceId": meta.get("serviceId") or meta.get("endpoint"),
        "submittedInput": meta.get("submittedInput"),
        "prompt": meta.get("prompt"),
        "negativePrompt": meta.get("negativePrompt"),
        "seed": meta.get("seed"),
        "jobId": meta.get("jobId") or meta.get("id"),
    }
    for item in saved:
        name = (item or {}).get("file")
        if not name:
            continue
        fp = sidecar_path(name, out_dir)
        try:
            fp.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
        except Exception:
            pass


def read_sidecar(name: str, out_dir=None) -> dict | None:
    if not name:
        return None
    out = Path(out_dir or DEFAULT_OUT)
    raw_name = Path(str(name).split("?")[0]).name
    candidates = [
        sidecar_path(raw_name, out),
        out / f"{raw_name}.json",
        out / raw_name if raw_name.endswith(".json") else None,
    ]
    for fp in candidates:
        if fp and fp.exists() and fp.is_file():
            try:
                data = json.loads(fp.read_text())
                if isinstance(data, dict):
                    return data
            except Exception:
                continue
    return None


def decode_data_url(url: str) -> bytes | None:
    if not isinstance(url, str) or not url.startswith("data:"):
        return None
    try:
        header, b64 = url.split(",", 1)
    except ValueError:
        return None
    import base64
    try:
        return base64.b64decode(b64)
    except Exception:
        return None


def parse_png_text(data: bytes) -> dict[str, str]:
    """Return tEXt/iTXt keyword -> text. Empty dict if not PNG or no chunks."""
    out: dict[str, str] = {}
    if not data or data[:8] != b"\x89PNG\r\n\x1a\n":
        return out
    offset = 8
    n = len(data)
    while offset + 12 <= n:
        length = int.from_bytes(data[offset:offset + 4], "big")
        ctype = data[offset + 4:offset + 8]
        start = offset + 8
        end = start + length
        if end + 4 > n:
            break
        chunk = data[start:end]
        offset = end + 4
        if ctype == b"IEND":
            break
        if ctype == b"tEXt":
            nul = chunk.find(b"\x00")
            if nul <= 0:
                continue
            key = chunk[:nul].decode("latin-1", "replace")
            val = chunk[nul + 1:].decode("utf-8", "replace")
            out[key] = val
        elif ctype == b"iTXt":
            nul = chunk.find(b"\x00")
            if nul <= 0:
                continue
            key = chunk[:nul].decode("latin-1", "replace")
            rest = chunk[nul + 1:]
            if len(rest) < 2:
                continue
            compressed = rest[0]
            rest = rest[2:]
            for _ in range(2):
                z = rest.find(b"\x00")
                if z < 0:
                    rest = b""
                    break
                rest = rest[z + 1:]
            if compressed == 1:
                try:
                    rest = zlib.decompress(rest)
                except Exception:
                    continue
            try:
                out[key] = rest.decode("utf-8", "replace")
            except Exception:
                pass
    return out


def parse_a1111(text: str) -> dict:
    text = (text or "").strip()
    if not text:
        return {}
    lines = text.splitlines()
    prompt_lines = []
    negative = ""
    extras = ""
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.lower().startswith("negative prompt:"):
            negative = line.split(":", 1)[1].strip()
            i += 1
            extra_neg = []
            while i < len(lines) and not re.match(
                r"^(steps|sampler|cfg scale|seed|size|model)\s*:", lines[i], re.I
            ) and not re.match(r"^steps:\s*\d", lines[i], re.I):
                if "," in lines[i] and re.search(r"steps:\s*\d", lines[i], re.I):
                    extras = lines[i]
                    i += 1
                    break
                extra_neg.append(lines[i])
                i += 1
            if extra_neg and not extras:
                negative = (negative + "\n" + "\n".join(extra_neg)).strip()
            continue
        if re.search(r"steps:\s*\d", line, re.I) and (":" in line) and i >= 1:
            extras = line
            i += 1
            continue
        prompt_lines.append(line)
        i += 1
    out = {"prompt": "\n".join(prompt_lines).strip(), "negativePrompt": negative}
    blob = extras or (lines[-1] if lines else "")
    def grab(pat, cast=str):
        m = re.search(pat, blob, re.I)
        if not m:
            return None
        try:
            return cast(m.group(1).strip())
        except (TypeError, ValueError):
            return m.group(1).strip()
    steps = grab(r"steps:\s*(\d+)", int)
    if steps is not None:
        out["steps"] = steps
    cfg = grab(r"cfg scale:\s*([0-9.]+)", float)
    if cfg is not None:
        out["cfgScale"] = cfg
    seed = grab(r"seed:\s*(-?\d+)", int)
    if seed is not None:
        out["seed"] = seed
    size = grab(r"size:\s*(\d+)\s*x\s*(\d+)" if False else r"size:\s*(\d+x\d+)")
    m = re.search(r"size:\s*(\d+)\s*[x×]\s*(\d+)", blob, re.I)
    if m:
        out["width"] = int(m.group(1))
        out["height"] = int(m.group(2))
    sampler = grab(r"sampler:\s*([^,]+)")
    if sampler:
        out["sampler"] = sampler
    return {k: v for k, v in out.items() if v not in (None, "")}


def parse_comfy(prompt_json: str, workflow_json: str | None = None) -> dict:
    try:
        graph = json.loads(prompt_json)
    except Exception:
        return {}
    if not isinstance(graph, dict):
        return {}
    nodes = graph.get("nodes") if isinstance(graph.get("nodes"), list) else None
    items = []
    if nodes:
        items = nodes
    else:
        for nid, node in graph.items():
            if isinstance(node, dict) and (node.get("class_type") or node.get("type")):
                node = dict(node)
                node["_id"] = nid
                items.append(node)
    prompt = ""
    negative = ""
    out = {}
    for node in items:
        ctype = str(node.get("class_type") or node.get("type") or "")
        inputs = node.get("inputs") or {}
        widgets = node.get("widgets_values") or []
        title = str(node.get("title") or node.get("meta", {}).get("title") if isinstance(node.get("meta"), dict) else "")
        if "CLIPTextEncode" in ctype or ctype in ("CLIP Text Encode (Prompt)",):
            text = inputs.get("text") if isinstance(inputs, dict) else None
            if not text and widgets:
                text = widgets[0]
            if isinstance(text, list):
                text = text[0] if text else ""
            text = str(text or "")
            blob = (ctype + " " + title).lower()
            if "negative" in blob and not negative:
                negative = text
            elif not prompt:
                prompt = text
            elif "negative" in blob:
                negative = text
        if "KSampler" in ctype:
            for key, dest, cast in (
                ("steps", "steps", int),
                ("cfg", "cfgScale", float),
                ("seed", "seed", int),
                ("sampler_name", "sampler", str),
                ("scheduler", "scheduler", str),
            ):
                val = inputs.get(key) if isinstance(inputs, dict) else None
                if val in (None, "") and key == "steps" and len(widgets) > 2:
                    val = widgets[2] if len(widgets) > 2 else None
                if val in (None, ""):
                    continue
                try:
                    out[dest] = cast(val)
                except (TypeError, ValueError):
                    pass
        if "EmptyLatentImage" in ctype:
            w = inputs.get("width") if isinstance(inputs, dict) else None
            h = inputs.get("height") if isinstance(inputs, dict) else None
            if w is None and len(widgets) >= 2:
                w, h = widgets[0], widgets[1]
            try:
                if w:
                    out["width"] = int(w)
                if h:
                    out["height"] = int(h)
            except (TypeError, ValueError):
                pass
    if prompt:
        out["prompt"] = prompt
    if negative:
        out["negativePrompt"] = negative
    return out


def parse_media_bytes(data: bytes, filename: str = "") -> dict:
    """Cross-provider local parse. Empty result if no chunks — never invent params."""
    empty = {
        "empty": True,
        "prompt": "",
        "source": "file",
        "fileName": filename or "",
        "error": "这个文件没有可解析的 PNG 参数块（tEXt/iTXt parameters 或 Comfy prompt）。没有云端反查，请自己填参数。",
    }
    if not data:
        return empty
    texts = parse_png_text(data)
    if not texts:
        return empty
    if "parameters" in texts:
        parsed = parse_a1111(texts["parameters"])
        parsed["source"] = "png-a1111"
        parsed["empty"] = not bool(parsed.get("prompt") or parsed.get("steps"))
        parsed["fileName"] = filename or ""
        return parsed
    if "prompt" in texts:
        parsed = parse_comfy(texts["prompt"], texts.get("workflow"))
        parsed["source"] = "png-comfy"
        parsed["empty"] = not bool(parsed.get("prompt") or parsed.get("steps"))
        parsed["fileName"] = filename or ""
        if parsed["empty"]:
            parsed["error"] = "PNG 里有 Comfy prompt 块，但没解析出提示词/步数。"
        return parsed
    return empty


def sidecar_to_import(meta: dict) -> dict:
    inp = meta.get("submittedInput") or {}
    if not isinstance(inp, dict):
        inp = {}
    prompt = meta.get("prompt") or inp.get("prompt") or inp.get("inputs") or ""
    if isinstance(prompt, dict):
        prompt = prompt.get("prompt") or ""
    neg = meta.get("negativePrompt") or inp.get("negative_prompt") or inp.get("negativePrompt") or ""
    steps = inp.get("num_inference_steps") or inp.get("steps")
    cfg = inp.get("guidance_scale") or inp.get("guidance") or inp.get("cfgScale")
    seed = meta.get("seed") if meta.get("seed") is not None else inp.get("seed")
    width = inp.get("width")
    height = inp.get("height")
    size = inp.get("image_size") or inp.get("size")
    if isinstance(size, dict):
        width = width or size.get("width")
        height = height or size.get("height")
    elif isinstance(size, str) and "x" in size.lower():
        try:
            a, b = size.lower().split("x", 1)
            width, height = int(a), int(b)
        except (TypeError, ValueError):
            pass
    first = inp.get("image_url") or inp.get("firstFrame") or inp.get("sourceImage")
    if isinstance(first, list) and first:
        first = first[0]
    out = {
        "backend": meta.get("backend"),
        "serviceId": meta.get("serviceId") or inp.get("model"),
        "prompt": prompt or "",
        "negativePrompt": neg or "",
        "source": "sidecar",
        "empty": not bool(prompt or meta.get("serviceId")),
        "submittedInput": inp,
    }
    if steps not in (None, ""):
        try:
            out["steps"] = int(steps)
        except (TypeError, ValueError):
            pass
    if cfg not in (None, ""):
        try:
            out["cfgScale"] = float(cfg)
        except (TypeError, ValueError):
            pass
    if seed not in (None, "", "random"):
        try:
            out["seed"] = int(seed)
        except (TypeError, ValueError):
            pass
    if width:
        try:
            out["width"] = int(width)
        except (TypeError, ValueError):
            pass
    if height:
        try:
            out["height"] = int(height)
        except (TypeError, ValueError):
            pass
    if first:
        out["firstFrame"] = first
        out["sourceImage"] = first
    return out
