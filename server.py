#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import mimetypes
import os
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import providers
from providers.capabilities import get_provider_capabilities
from providers import civitai as civitai_prov

ROOT = Path(__file__).resolve().parent
STATIC = ROOT / "static"
DOCS = ROOT / "docs"
OUT = ROOT / "out"
TOKEN_PATH = Path.home() / ".config/civitai/token"
ORCH = "https://orchestration.civitai.com"
SITE = "https://civitai.com/api/v1"
PORT = int(os.environ.get("PORT", "8765"))
OUT.mkdir(parents=True, exist_ok=True)
DOCS.mkdir(parents=True, exist_ok=True)

SAMPLERS = [
    "er_sde", "euler", "euler_ancestral", "euler_cfg_pp", "euler_ancestral_cfg_pp",
    "heun", "heunpp2", "dpm_2", "dpm_2_ancestral", "lms", "dpm_fast", "dpm_adaptive",
    "dpmpp_2s_ancestral", "dpmpp_2s_ancestral_cfg_pp", "dpmpp_sde", "dpmpp_sde_gpu",
    "dpmpp_2m", "dpmpp_2m_cfg_pp", "dpmpp_2m_sde", "dpmpp_2m_sde_gpu",
    "dpmpp_3m_sde", "dpmpp_3m_sde_gpu", "ddpm", "lcm", "ipndm", "ipndm_v",
    "deis", "ddim", "uni_pc", "uni_pc_bh2", "res_multistep",
]
SCHEDULERS = ["sgm_uniform", "simple", "normal", "karras", "exponential", "ddim_uniform", "beta"]


# 工作流组装（build_workflow / cap 匹配 / 分辨率处理）只有一份真链：providers/civitai.py。
# server.py 这边历史上有一份逐字节相同的拷贝，无任何调用方，已删；别再往这里加。
_catalog_lock = threading.Lock()
_catalog = {"total": 0, "items": [], "fetchedAt": None}


def token() -> str:
    try:
        return TOKEN_PATH.read_text().strip()
    except Exception:
        return ""


def civitai(url: str, method="GET", body=None, timeout=90):
    tok = token()
    if not tok:
        return 401, {"error": "没有 API Key"}
    headers = {
        "Authorization": f"Bearer {tok}",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0",
    }
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
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
        if isinstance(parsed, dict) and "error" not in parsed:
            parsed = dict(parsed)
            parsed.setdefault("error", parsed.get("title") or f"HTTP {e.code}")
        return e.code, parsed
    except urllib.error.URLError as e:
        return 502, {"error": "网络错误", "detail": str(getattr(e, "reason", e))}
    except Exception as e:
        return 502, {"error": "请求失败", "detail": str(e)}


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


def _provider_id(payload: dict) -> str:
    return _alias_backend(payload.get("backend") or "civitai")


def parse_image_id(raw: str) -> int:
    import re
    s = (raw or "").strip()
    for pat in (r"/images/(\d+)", r"/image/(\d+)", r"[?&]imageId=(\d+)", r"[?&]id=(\d+)", r"^(\d+)$"):
        m = re.search(pat, s, re.I)
        if m:
            return int(m.group(1))
    raise ValueError("请填图片数字 ID 或完整网址")


def import_image(image_id: str) -> dict:
    return civitai_prov.import_image(image_id)


def _alias_backend(bid: str) -> str:
    aliases = {
        "hf": "huggingface",
        "ms": "modelscope-ai",
        "modelscope": "modelscope-ai",
        "魔搭": "modelscope-ai",
        "魔搭ai": "modelscope-ai",
        "魔搭cn": "modelscope-cn",
        "nano": "nano-gpt",
        "nanogpt": "nano-gpt",
        "nano_gpt": "nano-gpt",
    }
    bid = (bid or "civitai").strip()
    return aliases.get(bid, bid)


def _looks_civitai_import(q: str) -> bool:
    s = (q or "").strip()
    low = s.lower()
    if "civitai.com" in low or "civitai.red" in low:
        return True
    if re.search(r"/images/\d+", s, re.I):
        return True
    if re.fullmatch(r"\d+", s):
        return True
    return False


def handle_import(backend="civitai", q="", file_bytes=None, filename="", endpoint=None):
    """Provider-aware import. Never triggers generate."""
    import base64
    from providers import io_meta
    from providers import fal as fal_prov

    backend = _alias_backend(backend)
    filename = Path(filename or "").name
    if file_bytes:
        parsed = io_meta.parse_media_bytes(file_bytes, filename)
        side = io_meta.read_sidecar(filename) if filename else None
        if not side and q:
            side = io_meta.read_sidecar(q)
        if parsed and not parsed.get("empty"):
            try:
                from providers import civitai as civitai_mod
                parsed = civitai_mod.enrich_local_parse(parsed)
                samp, sched = civitai_mod._normalize_pair(parsed.get("sampler"), parsed.get("scheduler"))
                parsed["sampler"] = samp
                parsed["scheduler"] = sched
                if parsed.get("diffusionModel") or parsed.get("checkpointName"):
                    eco = civitai_mod._ecosystem_from_blob(parsed.get("diffusionModel"), parsed.get("checkpointName"), parsed.get("engine"))
                    engine, operation, model = "comfy", "createImage", "turbo"
                    ecosystem = eco or "krea2"
                    if ecosystem == "zImage":
                        engine, ecosystem = "sdcpp", "zImage"
                    elif ecosystem == "qwen":
                        engine, ecosystem = "sdcpp", "qwen"
                    svc = civitai_mod.match_service(engine=engine, operation=operation, ecosystem=ecosystem, model=model, category="image")
                    parsed.setdefault("kind", "image")
                    parsed.setdefault("engine", engine)
                    parsed.setdefault("operation", operation)
                    parsed.setdefault("ecosystem", ecosystem)
                    parsed.setdefault("model", model)
                    if svc:
                        parsed.setdefault("serviceId", svc.get("id"))
                        parsed.setdefault("serviceName", svc.get("name"))
            except Exception:
                pass
        if side:
            merged = io_meta.sidecar_to_import(side)
            for k, v in parsed.items():
                if k in ("empty", "error", "source"):
                    continue
                if v not in (None, "", []):
                    merged[k] = v
            merged["fileName"] = filename
            if parsed.get("prompt") or merged.get("prompt") or merged.get("serviceId"):
                merged["empty"] = False
                merged.pop("error", None)
            return 200, merged
        return 200, parsed
    q = (q or "").strip()
    if not q:
        return 400, {"error": "请填导入内容"}
    if _looks_civitai_import(q):
        try:
            return 200, import_image(q)
        except Exception as e:
            return 400, {"error": str(e)}
    side = io_meta.read_sidecar(q)
    if side:
        return 200, io_meta.sidecar_to_import(side)
    if backend == "fal":
        return fal_prov.import_request(q, endpoint=endpoint)
    if backend in ("huggingface", "modelscope", "modelscope-ai", "modelscope-cn", "nano-gpt", "nanogpt"):
        return 200, {
            "empty": True,
            "backend": backend,
            "prompt": "",
            "error": "Hugging Face / 魔搭没有云端按图反查。Civitai 图请贴 civitai 链接或数字 id；或上传带 parameters 的 PNG。",
        }
    try:
        return 200, import_image(q)
    except Exception as e:
        return 400, {"error": str(e)}


def submit(body, whatif=False):
    allow = True if not isinstance(body, dict) else bool(body.get("allowMatureContent", True))
    q = urllib.parse.urlencode({
        "whatif": "true" if whatif else "false",
        "wait": "0",
        "hideMatureContent": "false" if allow else "true",
    })
    return civitai(f"{ORCH}/v2/consumer/workflows?{q}", method="POST", body=body)


def save_blobs(wf: dict) -> list[dict]:
    saved = []
    wf_id = wf.get("id") or "wf"
    for step in wf.get("steps") or []:
        out = step.get("output") or {}
        items = []
        for key in ("images", "videos", "blobs"):
            items.extend(out.get(key) or [])
        for i, item in enumerate(items):
            url = item.get("url")
            if not url or item.get("available") is False:
                continue
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=120) as r:
                raw = r.read()
            if raw[:8] == b"\x89PNG\r\n\x1a\n":
                ext = ".png"
            elif raw[:3] == b"\xff\xd8\xff":
                ext = ".jpg"
            elif raw[4:8] == b"ftyp" or b"ftyp" in raw[:12]:
                ext = ".mp4"
            else:
                ext = ".bin"
            name = f"{wf_id}_{i}{ext}"
            (OUT / name).write_bytes(raw)
            saved.append({"file": name, "url": f"/out/{name}", "bytes": len(raw), "kind": "video" if ext == ".mp4" else "image"})
    return saved


def save_fal_result(data: dict) -> list[dict]:
    result = data.get("result") or {}
    urls = []
    for key in ("images", "image", "video", "videos", "audio", "audios"):
        val = result.get(key)
        if isinstance(val, str) and val.startswith("http"):
            urls.append(val)
        elif isinstance(val, dict) and val.get("url"):
            urls.append(val["url"])
        elif isinstance(val, list):
            for item in val:
                if isinstance(item, str) and item.startswith("http"):
                    urls.append(item)
                elif isinstance(item, dict) and item.get("url"):
                    urls.append(item["url"])
    saved = []
    job_id = (data.get("id") or "fal").replace("|", "_").replace("/", "_")
    for i, url in enumerate(urls):
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=120) as r:
            raw = r.read()
        if raw[:8] == b"\x89PNG\r\n\x1a\n":
            ext = ".png"
        elif raw[:3] == b"\xff\xd8\xff":
            ext = ".jpg"
        elif b"ftyp" in raw[:12]:
            ext = ".mp4"
        elif raw[:4] == b"RIFF":
            ext = ".webp"
        else:
            ext = ".bin"
        name = f"{job_id}_{i}{ext}"
        (OUT / name).write_bytes(raw)
        kind = "video" if ext == ".mp4" else ("audio" if ext in (".wav", ".mp3") else "image")
        saved.append({"file": name, "url": f"/out/{name}", "bytes": len(raw), "kind": kind})
    return saved


class Handler(BaseHTTPRequestHandler):
    server_version = "CivitaiStudio/2.0"

    def log_message(self, fmt, *args):
        print("[web]", self.address_string(), fmt % args, flush=True)

    def _json(self, code, obj):
        data = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _bytes(self, code, data, ctype):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        if "html" in (ctype or "") or "javascript" in (ctype or ""):
            self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
            self.send_header("Pragma", "no-cache")
        self.end_headers()
        self.wfile.write(data)

    def _read_json(self):
        n = int(self.headers.get("Content-Length") or 0)
        if n <= 0:
            return {}
        return json.loads(self.rfile.read(n).decode())

    def _cancel_job(self, path):
        rest = urllib.parse.unquote(path.split("/api/jobs/", 1)[1])
        job_id = rest[:-7] if rest.endswith("/cancel") else rest
        job_id = job_id.strip("/")
        if not job_id:
            return self._json(400, {"error": "缺少任务 id"})
        prov = providers.resolve_from_job(job_id)
        code, data = prov.cancel_job(job_id)
        return self._json(code, data)

    def do_GET(self):
        try:
            return self._handle_get()
        except Exception as e:
            print("[web] GET", e, flush=True)
            try:
                return self._json(500, {"error": "服务器出错"})
            except Exception:
                return

    def _handle_get(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        qs = urllib.parse.parse_qs(parsed.query)
        if path in ("/", "/index.html"):
            return self._bytes(200, (STATIC / "index.html").read_bytes(), "text/html; charset=utf-8")
        if path == "/storyboard.html":
            return self._bytes(
                200,
                (STATIC / "storyboard.html").read_bytes(),
                "text/html; charset=utf-8",
            )
        if path.startswith("/static/"):
            name = Path(path.split("/static/", 1)[1]).name
            fp = STATIC / name
            if not fp.exists():
                return self._json(404, {"error": "not found"})
            ctype = mimetypes.guess_type(str(fp))[0] or "application/octet-stream"
            return self._bytes(200, fp.read_bytes(), ctype)
        if path == "/api/providers":
            return self._json(200, {"items": providers.list_public()})
        if path == "/api/workflows":
            civ = providers.get("civitai")
            q = (qs.get("q") or [""])[0]
            user = (qs.get("username") or [""])[0]
            nsfw_raw = (qs.get("nsfw") or ["true"])[0]
            nsfw = str(nsfw_raw).lower() in ("1", "true", "yes")
            code, data = civ.list_workflows(q=q, username=user, nsfw=nsfw)
            return self._json(code, data)
        if path == "/api/workflows/air":
            civ = providers.get("civitai")
            filename = (qs.get("filename") or qs.get("q") or [""])[0]
            if not filename:
                return self._json(400, {"error": "filename required"})
            try:
                code, data = civ.lookup_air_file(filename)
            except Exception as e:
                return self._json(502, {"error": str(e)})
            return self._json(code, data)
        if path == "/api/workflows/import":
            civ = providers.get("civitai")
            raw = (qs.get("url") or qs.get("q") or [""])[0]
            try:
                code, data = civ.import_workflow(raw)
            except ValueError as e:
                return self._json(400, {"error": str(e)})
            except Exception as e:
                return self._json(502, {"error": str(e)})
            return self._json(code, data)
        if path == "/api/catalog":
            backend = _alias_backend((qs.get("backend") or ["civitai"])[0])
            prov = providers.get(backend)
            if not prov:
                return self._json(400, {"error": f"未知后端 {backend}", "code": "unknown_backend"})
            if backend != "civitai" and (qs.get("refresh") or ["0"])[0] in ("1", "true"):
                pass
            elif backend == "civitai" and (qs.get("refresh") or ["0"])[0] in ("1", "true"):
                try:
                    prov.refresh_catalog()
                except Exception as e:
                    print("catalog refresh", e, flush=True)
            body = prov.catalog((qs.get("q") or [""])[0], (qs.get("category") or [""])[0], (qs.get("status") or [""])[0])
            if isinstance(body, dict) and body.get("error") and not (body.get("items") or []):
                return self._json(502, body)
            return self._json(200, body)
        if path == "/api/defaults":
            civ = providers.get("civitai")
            extra = civ.defaults_payload() if civ else {}
            keys = {p.id: p.has_key() for p in providers.all_providers()}
            extra.update({
                "hasToken": keys.get("civitai", False),
                "hasFal": keys.get("fal", False),
                "hasKeys": keys,
                "providers": providers.list_public(),
            })
            return self._json(200, extra)
        if path == "/api/capabilities":
            fp = DOCS / "capabilities.json"
            if not fp.exists():
                return self._json(404, {"error": "no capabilities.json"})
            return self._json(200, json.loads(fp.read_text()))
        if path == "/api/services":
            limit = (qs.get("limit") or ["50"])[0]
            offset = (qs.get("offset") or ["0"])[0]
            code, data = civitai(f"{ORCH}/v2/services?limit={urllib.parse.quote(str(limit))}&offset={urllib.parse.quote(str(offset))}")
            return self._json(code, data)
        if path == "/api/outs":
            items = []
            for fp in sorted(OUT.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
                if not fp.is_file():
                    continue
                ext = fp.suffix.lower()
                if ext not in (".jpg", ".jpeg", ".png", ".webp", ".gif", ".mp4", ".webm", ".wav", ".mp3"):
                    continue
                items.append({
                    "file": fp.name,
                    "url": f"/out/{fp.name}",
                    "bytes": fp.stat().st_size,
                    "kind": "video" if ext in (".mp4", ".webm") else ("audio" if ext in (".wav", ".mp3") else "image"),
                })
            return self._json(200, {"items": items[:60]})
        if path == "/api/jobs":
            code, data = civitai(f"{ORCH}/v2/consumer/workflows")
            return self._json(code, data)
        if path == "/api/blobs":
            blob = (qs.get("blobId") or [""])[0]
            if not blob:
                return self._json(400, {"error": "blobId required"})
            code, data = civitai(f"{ORCH}/v2/consumer/blobs?blobId={urllib.parse.quote(blob)}")
            return self._json(code, data)
        if path == "/api/go":
            print("[web] GO_CLICK", flush=True)
            return self._json(200, {"ok": True})
        if path == "/api/health":
            code, data = civitai(f"{ORCH}/health")
            return self._json(code, data if isinstance(data, dict) else {"status": data})
        if path.startswith("/api/jobs/"):
            wf_id = urllib.parse.unquote(path.split("/api/jobs/", 1)[1])
            prov = providers.resolve_from_job(wf_id)
            code, data = prov.job_status(wf_id)
            return self._json(code, data)
        if path == "/api/import":
            backend = (qs.get("backend") or ["civitai"])[0]
            q = (qs.get("q") or qs.get("query") or [""])[0]
            endpoint = (qs.get("endpoint") or qs.get("serviceId") or [""])[0]
            code, data = handle_import(backend, q, endpoint=endpoint or None)
            return self._json(code, data)
        if path.startswith("/api/import-image/"):
            image_id = urllib.parse.unquote(path.split("/api/import-image/", 1)[1]).strip()
            try:
                return self._json(200, import_image(image_id))
            except Exception as e:
                return self._json(400, {"error": str(e)})
        if path.startswith("/api/model-version/"):
            vid = urllib.parse.unquote(path.split("/api/model-version/", 1)[1])
            code, data = civitai(f"{SITE}/model-versions/{vid}")
            if isinstance(data, dict):
                files = []
                for f in (data.get("files") or []):
                    if not isinstance(f, dict):
                        continue
                    files.append({
                        "id": f.get("id"),
                        "name": f.get("name"),
                        "type": f.get("type"),
                        "downloadUrl": f.get("downloadUrl") or f.get("download_url"),
                    })
                download = next((x.get("downloadUrl") for x in files if x.get("downloadUrl")), None)
                vid = data.get("id")
                if not download and vid:
                    download = f"https://civitai.com/api/download/models/{vid}"
                return self._json(code, {
                    "id": data.get("id"),
                    "name": data.get("name"),
                    "air": data.get("air"),
                    "baseModel": data.get("baseModel"),
                    "model": (data.get("model") or {}).get("name"),
                    "type": (data.get("model") or {}).get("type"),
                    "trainedWords": data.get("trainedWords") or [],
                    "files": files,
                    "downloadUrl": download,
                })
            return self._json(code, data)
        if path == "/api/search":
            q = (qs.get("q") or [""])[0]
            types = (qs.get("type") or ["LORA"])[0]
            nsfw_raw = (qs.get("nsfw") or ["true"])[0]
            nsfw = str(nsfw_raw).lower() in ("1", "true", "yes")
            backend = _alias_backend((qs.get("backend") or ["civitai"])[0])
            prov = providers.get(backend) or providers.get("civitai")
            if backend != "civitai" and hasattr(prov, "search_loras"):
                code, data = prov.search_loras(q, nsfw=nsfw)
                if isinstance(data, dict):
                    data.setdefault("backend", backend)
                    data.setdefault("nsfw", nsfw)
                return self._json(code, data if isinstance(data, dict) else {"items": []})
            url = (
                f"{SITE}/models?limit=8&query={urllib.parse.quote(q)}"
                f"&types={urllib.parse.quote(types)}&nsfw={'true' if nsfw else 'false'}"
            )
            code, data = civitai(url)
            items = []
            if isinstance(data, dict):
                for it in (data.get("items") or [])[:8]:
                    vers = [{"id": v.get("id"), "name": v.get("name"), "baseModel": v.get("baseModel")} for v in (it.get("modelVersions") or [])[:6]]
                    items.append({"id": it.get("id"), "name": it.get("name"), "type": it.get("type"), "source": "civitai", "nsfw": it.get("nsfw"), "versions": vers})
            return self._json(code, {"items": items, "nsfw": nsfw, "backend": "civitai"})
        if path.startswith("/out/"):
            name = Path(path.split("/out/", 1)[1]).name
            fp = OUT / name
            if not fp.exists():
                return self._json(404, {"error": "not found"})
            ctype = mimetypes.guess_type(str(fp))[0] or "application/octet-stream"
            return self._bytes(200, fp.read_bytes(), ctype)
        self._json(404, {"error": "not found"})

    def do_POST(self):
        try:
            return self._handle_post()
        except Exception as e:
            print("[web] POST", e, flush=True)
            try:
                return self._json(500, {"error": "服务器出错"})
            except Exception:
                return

    def _handle_post(self):
        path = urllib.parse.urlparse(self.path).path
        try:
            payload = self._read_json()
        except Exception:
            return self._json(400, {"error": "invalid json"})
        if path in ("/api/caption", "/api/upload-out"):
            from providers.media_io import handle_media_post
            code, data = handle_media_post(path, payload)
            return self._json(code, data)
        if path == "/api/import":
            raw = None
            b64 = payload.get("fileB64") or payload.get("file")
            if b64:
                import base64
                if isinstance(b64, str) and "," in b64:
                    b64 = b64.split(",", 1)[1]
                try:
                    raw = base64.b64decode(b64)
                except Exception:
                    return self._json(400, {"error": "文件不是合法 base64"})
            code, data = handle_import(
                payload.get("backend") or "civitai",
                payload.get("q") or payload.get("query") or "",
                file_bytes=raw,
                filename=payload.get("fileName") or payload.get("filename") or "",
                endpoint=payload.get("endpoint") or payload.get("serviceId"),
            )
            return self._json(code, data)
        if path == "/api/graph/compile":
            from providers.graph_compile import compile_graph
            graph = payload.get("graph") if isinstance(payload.get("graph"), dict) else payload
            if isinstance(graph, dict) and graph.get("backend"):
                graph = dict(graph)
                graph["backend"] = _alias_backend(graph["backend"])
            result = compile_graph(graph)
            code = 200 if result.get("ok") else 400
            return self._json(code, result)
        if path in ("/api/generate", "/api/whatif"):
            if path == "/api/generate":
                from providers.graph_compile import reject_staged_generate
                blocked = reject_staged_generate(payload)
                if blocked:
                    return self._json(400, blocked)
            prov = providers.resolve_from_payload(payload)
            if prov is None:
                return self._json(400, {"error": "未知后端或服务，拒绝默认改打 Civitai", "code": "unknown_backend"})
            if path == "/api/whatif":
                code, data = prov.whatif(payload)
            else:
                code, data = prov.generate(payload)
            return self._json(code, data)
        if path in ("/api/story", "/api/story/plan"):
            from providers.nanogpt import chat_story
            code, data = chat_story(payload)
            return self._json(code, data)
        if path == "/api/grid/plan":
            # 九宫格: catalog 里没有一次出多联图的模型, 所以先把 1 条提示词
            # 拆成 N 条子提示词, 前端再跑 N 次 t2i 并 canvas 拼成一张卡。
            from providers.nanogpt import plan_grid
            code, data = plan_grid(payload)
            return self._json(code, data)
        if path == "/api/catalog/refresh":
            try:
                return self._json(200, refresh_catalog())
            except Exception as e:
                return self._json(502, {"error": str(e)})
        if path.startswith("/api/recipes/"):
            recipe = urllib.parse.unquote(path.split("/api/recipes/", 1)[1]).strip("/")
            q = urllib.parse.urlencode({
                "whatif": "true" if payload.get("whatif") else "false",
                "allowMatureContent": "true" if payload.get("allowMatureContent", True) else "false",
            })
            body = payload.get("input") or payload
            code, data = civitai(f"{ORCH}/v2/consumer/recipes/{recipe}?{q}", method="POST", body=body)
            return self._json(code, data)
        if path.startswith("/api/jobs/") and path.rstrip("/").endswith("/cancel"):
            return self._cancel_job(path)
        self._json(404, {"error": "not found"})

    def do_DELETE(self):
        try:
            path = urllib.parse.urlparse(self.path).path
            if path.startswith("/api/jobs/") and path.rstrip("/").endswith("/cancel"):
                return self._cancel_job(path)
            return self._json(404, {"error": "not found"})
        except Exception as e:
            print("[web] DELETE", e, flush=True)
            try:
                return self._json(500, {"error": "服务器出错"})
            except Exception:
                return


def main():
    civ = providers.get("civitai")
    n = 0
    if civ:
        try:
            n = civ.defaults_payload().get("catalogTotal") or 0
        except Exception:
            n = 0
    httpd = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"Civitai Studio http://127.0.0.1:{PORT} providers={','.join(p.id for p in providers.all_providers())} catalog={n}", flush=True)
    httpd.serve_forever()


if __name__ == "__main__":
    main()
