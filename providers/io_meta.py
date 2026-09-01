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


SAMPLER_CANON = {
    "er_sde": "er_sde",
    "ersde": "er_sde",
    "euler": "euler",
    "eulera": "euler_ancestral",
    "euler_a": "euler_ancestral",
    "eulerancestral": "euler_ancestral",
    "euler_ancestral": "euler_ancestral",
    "heun": "heun",
    "dpm_2": "dpm_2",
    "dpm2": "dpm_2",
    "dpmpp_2m": "dpmpp_2m",
    "dpm++2m": "dpmpp_2m",
    "dpmpp2m": "dpmpp_2m",
    "dpmpp_sde": "dpmpp_sde",
    "dpm++sde": "dpmpp_sde",
    "dpmpp_2m_sde": "dpmpp_2m_sde",
    "lcm": "lcm",
    "ddim": "ddim",
    "uni_pc": "uni_pc",
    "unipc": "uni_pc",
}

SCHEDULER_CANON = {
    "sgm_uniform": "sgm_uniform",
    "sgmuniform": "sgm_uniform",
    "simple": "simple",
    "normal": "normal",
    "karras": "karras",
    "exponential": "exponential",
    "ddim_uniform": "ddim_uniform",
    "ddimuniform": "ddim_uniform",
    "beta": "beta",
}


def _fold_name(name: str) -> str:
    s = (name or "").strip().lower()
    s = s.replace("++", "pp")
    s = re.sub(r"[\s\-]+", "_", s)
    s = re.sub(r"[^a-z0-9_]+", "", s)
    return s


def normalize_sampler(name: str, allowed: list | tuple | None = None) -> str:
    raw = (name or "").strip()
    if not raw:
        return ""
    folded = _fold_name(raw)
    canon = SAMPLER_CANON.get(folded, folded)
    if allowed:
        allow = {str(x) for x in allowed}
        if canon in allow:
            return canon
        if raw in allow:
            return raw
        if folded in allow:
            return folded
        return ""
    return canon


def normalize_scheduler(name: str, allowed: list | tuple | None = None) -> str:
    raw = (name or "").strip()
    if not raw:
        return ""
    folded = _fold_name(raw)
    canon = SCHEDULER_CANON.get(folded, folded)
    if allowed:
        allow = {str(x) for x in allowed}
        if canon in allow:
            return canon
        if raw in allow:
            return raw
        if folded in allow:
            return folded
        return ""
    return canon


def split_sampler_scheduler(sampler: str, scheduler: str = "") -> tuple[str, str]:
    samp = (sampler or "").strip()
    sched = (scheduler or "").strip()
    folded = _fold_name(samp)
    if folded.endswith("_simple"):
        return samp[: -len("_simple")].strip("_") or "er_sde", "simple"
    for tail in ("sgm_uniform", "karras", "exponential", "ddim_uniform", "normal", "beta", "simple"):
        token = "_" + tail
        if folded.endswith(tail) and folded != tail:
            head = folded[: -len(tail)].strip("_")
            if head:
                return head, tail
    return samp, sched


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
    m = re.search(r"size:\s*(\d+)\s*[x×]\s*(\d+)", blob, re.I)
    if m:
        out["width"] = int(m.group(1))
        out["height"] = int(m.group(2))
    sampler = grab(r"sampler:\s*([^,]+)")
    scheduler = grab(r"schedule(?:r)?:\s*([^,]+)")
    if sampler:
        sampler, sched_from_samp = split_sampler_scheduler(sampler, scheduler or "")
        out["sampler"] = normalize_sampler(sampler) or sampler
        scheduler = scheduler or sched_from_samp
    if scheduler:
        out["scheduler"] = normalize_scheduler(scheduler) or scheduler
    denoise = grab(r"denoising strength:\s*([0-9.]+)", float) or grab(r"denoise:\s*([0-9.]+)", float)
    if denoise is not None:
        out["denoise"] = denoise
    model = grab(r"model:\s*([^,]+)")
    if model:
        out["checkpointName"] = model
        out["Model"] = model
    return {k: v for k, v in out.items() if v not in (None, "")}


def coerce_int(val, default=None):
    """int() that will not explode on a Comfy node dict or ["node", 0] link."""
    if val is None or val is False:
        return default
    if isinstance(val, bool):
        return default
    if isinstance(val, int):
        return val
    if isinstance(val, float):
        if val != val:  # NaN
            return default
        return int(val)
    if isinstance(val, str):
        s = val.strip()
        if not s:
            return default
        try:
            return int(s, 10)
        except ValueError:
            try:
                return int(float(s))
            except ValueError:
                m = re.search(r"-?\d+", s)
                return int(m.group(0)) if m else default
    if isinstance(val, (list, tuple)):
        if not val:
            return default
        return coerce_int(val[0], default)
    if isinstance(val, dict):
        dims = dims_from_selector(val)
        if dims:
            return dims[0]
        for key in ("width", "height", "value", "int", "seed", "steps", "multiple"):
            if key in val:
                n = coerce_int(val.get(key), None)
                if n is not None:
                    return n
        inputs = val.get("inputs")
        if isinstance(inputs, dict):
            return coerce_int(inputs, default)
        return default
    try:
        return int(val)
    except (TypeError, ValueError):
        return default


def first_int(*vals, default=None):
    for v in vals:
        n = coerce_int(v, None)
        if n is not None:
            return n
    return default


def dims_from_selector(node):
    """ResolutionSelector (megapixels + aspect_ratio + multiple) → (w, h) ints."""
    if not isinstance(node, dict):
        return None
    src = node.get("inputs") if isinstance(node.get("inputs"), dict) else node
    if not isinstance(src, dict):
        src = node
    ctype = str(node.get("class_type") or node.get("type") or "")
    ar = str(src.get("aspect_ratio") or src.get("aspect") or src.get("ratio") or "")
    mp = src.get("megapixels")
    if mp is None:
        mp = src.get("mp") or src.get("target_megapixels")
    looks = ("ResolutionSelector" in ctype) or (ar and mp is not None)
    w_direct = coerce_int(src.get("width"), None)
    h_direct = coerce_int(src.get("height"), None)
    if w_direct and h_direct and w_direct >= 64 and h_direct >= 64 and not looks:
        return (w_direct, h_direct)
    if not looks and not (w_direct and h_direct):
        return None
    m = re.search(r"(\d+)\s*[:/x×]\s*(\d+)", ar)
    if m:
        aw, ah = int(m.group(1)), int(m.group(2))
    else:
        aw, ah = 1, 1
    if aw <= 0 or ah <= 0:
        aw, ah = 1, 1
    try:
        megapixels = float(mp) if mp not in (None, "") else 1.0
    except (TypeError, ValueError):
        megapixels = 1.0
    if megapixels <= 0:
        megapixels = 1.0
    multiple = coerce_int(src.get("multiple") or src.get("divisible") or 64, 64) or 64
    if multiple < 8:
        multiple = 8
    pixels = megapixels * 1_000_000.0
    import math
    w = math.sqrt(pixels * aw / ah)
    h = w * ah / aw

    def snap(n):
        n = int(round(n / multiple) * multiple)
        return max(multiple, n)

    return (snap(w), snap(h))


def _comfy_lookup(by_id: dict, val, prefer_keys=()):
    """Resolve Comfy link ["nodeId", port] to a scalar when possible."""
    if not (isinstance(val, list) and val):
        return val
    nid = str(val[0])
    node = by_id.get(nid)
    if not isinstance(node, dict):
        return None
    inputs = node.get("inputs") if isinstance(node.get("inputs"), dict) else {}
    widgets = node.get("widgets_values") or []
    for key in prefer_keys:
        if key in inputs and not isinstance(inputs.get(key), list):
            return inputs.get(key)
    for key in ("seed", "text", "value", "int", "float"):
        if key in inputs and not isinstance(inputs.get(key), list):
            return inputs.get(key)
    if widgets:
        return widgets[0]
    return None


def parse_comfy(prompt_json: str, workflow_json: str | None = None) -> dict:
    try:
        graph = json.loads(prompt_json)
    except Exception:
        return {}
    if not isinstance(graph, dict):
        return {}
    nodes = graph.get("nodes") if isinstance(graph.get("nodes"), list) else None
    items = []
    by_id = {}
    if nodes:
        items = nodes
        for node in nodes:
            if isinstance(node, dict) and node.get("id") is not None:
                by_id[str(node.get("id"))] = node
    else:
        for nid, node in graph.items():
            if isinstance(node, dict) and (node.get("class_type") or node.get("type")):
                node = dict(node)
                node["_id"] = nid
                items.append(node)
                by_id[str(nid)] = node
    prompt = ""
    negative = ""
    out = {}
    models = []
    vaes = []
    extras = []
    node_types = []
    for node in items:
        ctype = str(node.get("class_type") or node.get("type") or "")
        node_types.append(ctype)
        inputs = node.get("inputs") or {}
        widgets = node.get("widgets_values") or []
        title = str(node.get("title") or node.get("meta", {}).get("title") if isinstance(node.get("meta"), dict) else "")
        if "CLIPTextEncode" in ctype or ctype in ("CLIP Text Encode (Prompt)",):
            text = inputs.get("text") if isinstance(inputs, dict) else None
            if isinstance(text, list):
                text = _comfy_lookup(by_id, text, ("text",))
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
        if "KSampler" in ctype or ctype in ("SamplerCustom", "SamplerCustomAdvanced", "KSamplerAdvanced"):
            def take(key, dest, cast):
                val = inputs.get(key) if isinstance(inputs, dict) else None
                if isinstance(val, list):
                    val = _comfy_lookup(by_id, val, (key, "seed", "value"))
                if val in (None, "") and key == "steps" and len(widgets) > 2:
                    val = widgets[2]
                if val in (None, ""):
                    return
                try:
                    out[dest] = cast(val)
                except (TypeError, ValueError):
                    if dest in ("sampler", "scheduler") and val:
                        out[dest] = str(val)
            take("steps", "steps", int)
            take("cfg", "cfgScale", float)
            take("seed", "seed", int)
            take("noise_seed", "seed", int)
            take("sampler_name", "sampler", str)
            take("scheduler", "scheduler", str)
            take("denoise", "denoise", float)
        if "ResolutionSelector" in ctype or (
            isinstance(inputs, dict) and ("megapixels" in inputs or "aspect_ratio" in inputs)
            and not out.get("width")
        ):
            wh = dims_from_selector(node)
            if wh:
                out["width"], out["height"] = wh
        if ctype in ("SeedNode", "Seed", "PrimitiveInt", "ImpactInt"):
            seed_val = inputs.get("seed") if isinstance(inputs, dict) else None
            if seed_val in (None, "") and widgets:
                seed_val = widgets[0]
            if seed_val not in (None, "") and "seed" not in out:
                try:
                    out["seed"] = int(seed_val)
                except (TypeError, ValueError):
                    pass
        if ctype in ("UNETLoader", "CheckpointLoaderSimple", "CheckpointLoader", "unCLIPCheckpointLoader"):
            fname = None
            if isinstance(inputs, dict):
                fname = inputs.get("unet_name") or inputs.get("ckpt_name") or inputs.get("ckptName")
            if not fname and widgets:
                fname = widgets[0]
            if fname and not isinstance(fname, list):
                models.append(str(fname))
        if ctype in ("VAELoader",):
            fname = inputs.get("vae_name") if isinstance(inputs, dict) else None
            if not fname and widgets:
                fname = widgets[0]
            if fname and not isinstance(fname, list):
                vaes.append(str(fname))
        if "EmptyLatentImage" in ctype:
            w = inputs.get("width") if isinstance(inputs, dict) else None
            h = inputs.get("height") if isinstance(inputs, dict) else None
            if isinstance(w, list):
                w = _comfy_lookup(by_id, w, ("width",))
            if isinstance(h, list):
                h = _comfy_lookup(by_id, h, ("height",))
            if w is None and len(widgets) >= 2:
                w, h = widgets[0], widgets[1]
            wi = coerce_int(w, None)
            hi = coerce_int(h, None)
            if wi:
                out["width"] = wi
            if hi:
                out["height"] = hi
        extra_types = ("SeedVR2", "Upscale", "ControlNet", "IPAdapter", "InstantID", "PuLID")
        if any(tok.lower() in ctype.lower() for tok in extra_types):
            extras.append(ctype)
    if prompt:
        out["prompt"] = prompt
    if negative:
        out["negativePrompt"] = negative
    if out.get("sampler"):
        samp, sched = split_sampler_scheduler(str(out["sampler"]), str(out.get("scheduler") or ""))
        out["sampler"] = normalize_sampler(samp) or samp
        if sched and not out.get("scheduler"):
            out["scheduler"] = sched
    if out.get("scheduler"):
        out["scheduler"] = normalize_scheduler(str(out["scheduler"])) or out["scheduler"]
    if models:
        out["models"] = models
        stem = Path(models[0]).stem
        out["checkpointName"] = stem
        out["Model"] = stem
    if vaes:
        out["vaes"] = vaes
    if extras:
        out["unmatchedNodes"] = sorted(set(extras))
    if node_types:
        out["comfyNodeCount"] = len(node_types)
        out["engine"] = "ComfyUI"
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
        parsed["empty"] = not bool(parsed.get("prompt") or parsed.get("steps") or parsed.get("checkpointName"))
        parsed["fileName"] = filename or ""
        if texts.get("workflow"):
            parsed["hasComfyWorkflow"] = True
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
