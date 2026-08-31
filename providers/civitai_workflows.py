"""Civitai Workflows models (ComfyUI graphs). Not a generic node editor."""
from __future__ import annotations

import json
import re
import threading
import time
import urllib.parse
import urllib.request
from pathlib import Path

from .http import json_call

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
CACHE = DOCS / "workflows"
CACHE.mkdir(parents=True, exist_ok=True)
AIR_CACHE = DOCS / "air-cache"
AIR_CACHE.mkdir(parents=True, exist_ok=True)

MOODY_USER = "catlover1937"
MOODY_COLLECTION = 16706087

SITE = "https://civitai.com/api/v1"
TOKEN_PATH = Path.home() / ".config/civitai/token"
MANAGER_NODE_MAP = "https://raw.githubusercontent.com/ltdrdata/ComfyUI-Manager/main/extension-node-map.json"
MANAGER_NODE_LIST = "https://raw.githubusercontent.com/ltdrdata/ComfyUI-Manager/main/custom-node-list.json"
REGISTRY = "https://api.comfy.org"
OFFICIAL_COMFY = "https://github.com/comfyanonymous/comfyui"

# Built-in ComfyUI class_types. Keep generic — not a workflow-specific allowlist.
CORE_NODES = {
    "CLIPTextEncode", "CLIPTextEncodeSDXL", "CLIPTextEncodeSDXLRefiner", "CLIPTextEncodeFlux",
    "CLIPTextEncodeHunyuanDiT", "CLIPTextEncodeSD3", "CLIPSetLastLayer", "CLIPLoader",
    "DualCLIPLoader", "TripleCLIPLoader", "QuadrupleCLIPLoader", "CLIPVisionLoader",
    "CLIPVisionEncode", "unCLIPCheckpointLoader", "unCLIPConditioning",
    "VAEDecode", "VAEEncode", "VAEEncodeForInpaint", "VAELoader", "VAEDecodeTiled", "VAEEncodeTiled",
    "UNETLoader", "CheckpointLoader", "CheckpointLoaderSimple", "DiffusersLoader",
    "LoraLoader", "LoraLoaderModelOnly", "ControlNetLoader", "DiffControlNetLoader",
    "ControlNetApply", "ControlNetApplyAdvanced", "ControlNetApplySD3", "ControlNetInpaintingAliMamaApply",
    "StyleModelLoader", "StyleModelApply", "GLIGENLoader", "GLIGENTextBoxApply",
    "KSampler", "KSamplerAdvanced", "KSamplerSelect", "SamplerCustom", "SamplerCustomAdvanced",
    "EmptyLatentImage", "EmptyImage", "EmptySD3LatentImage", "EmptyHunyuanLatentVideo",
    "LatentUpscale", "LatentUpscaleBy", "LatentComposite", "LatentCompositeMasked",
    "LatentFromBatch", "RepeatLatentBatch", "LatentRotate", "LatentFlip", "LatentCrop",
    "SetLatentNoiseMask", "LatentAdd", "LatentSubtract", "LatentMultiply", "LatentInterpolate",
    "SaveImage", "PreviewImage", "LoadImage", "LoadImageMask", "ImageScale", "ImageScaleBy",
    "ImageScaleToTotalPixels", "ImageInvert", "ImagePadForOutpaint", "ImageBatch",
    "ImageBlend", "ImageBlur", "ImageQuantize", "ImageSharpen", "ImageToMask", "MaskToImage",
    "ImageCompositeMasked", "ImageCrop", "RepeatImageBatch", "RebatchImages", "ImageFromBatch",
    "SolidMask", "InvertMask", "CropMask", "MaskComposite", "FeatherMask", "GrowMask", "PreviewMask",
    "SaveLatent", "LoadLatent",
    "ConditioningCombine", "ConditioningAverage", "ConditioningConcat",
    "ConditioningSetArea", "ConditioningSetAreaPercentage", "ConditioningSetMask",
    "ConditioningZeroOut", "ConditioningSetTimestepRange",
    "Reroute", "Note", "PrimitiveNode", "PrimitiveInt", "PrimitiveFloat", "PrimitiveBoolean",
    "PrimitiveString", "GetImageSize", "ImageUpscaleWithModel", "UpscaleModelLoader",
    "PhotoMakerEncode", "PhotoMakerLoader",
    "FreeU", "FreeU_V2", "HyperTile", "PatchModelAddDownscale",
    "ModelMergeSimple", "ModelMergeBlocks", "CheckpointSave", "CLIPMergeSimple", "CLIPSave", "VAESave",
    "TomePatchModel", "RescaleCFG", "PerpNeg", "PerpNegGuider", "CFGGuider", "BasicGuider",
    "BasicScheduler", "KarrasScheduler", "ExponentialScheduler", "PolyexponentialScheduler",
    "SDTurboScheduler", "VPScheduler", "BetaSamplingScheduler", "SplitSigmas", "FlipSigmas",
    "RandomNoise", "DisableNoise",
    "InpaintModelConditioning", "SelfAttentionGuidance", "PerturbedAttentionGuidance",
    "DifferentialDiffusion", "InstructPixToPixConditioning",
    "ModelSamplingAuraFlow", "ModelSamplingSD3", "ModelSamplingFlux", "ModelSamplingContinuousEDM",
    "ModelSamplingContinuousV", "ModelSamplingDiscrete",
    "MaskPreview",
}

MODEL_TYPE_TO_AIR = {
    "checkpoint": "checkpoint",
    "lora": "lora",
    "locon": "lycoris",
    "lycoris": "lycoris",
    "dora": "dora",
    "textualinversion": "embedding",
    "hypernetwork": "hypernet",
    "aestheticgradient": "embedding",
    "controlnet": "controlnet",
    "poses": "other",
    "wildcards": "other",
    "vae": "vae",
    "upscaler": "upscaler",
    "motionmodule": "other",
    "workflow": "other",
    "workflows": "other",
    "detection": "other",
    "other": "other",
    "textencoder": "clip",
    "clip": "clip",
    "unet": "unet",
    "diffusionmodel": "diffusionmodel",
}

FILE_TYPE_TO_AIR = {
    "diffusion model": "diffusionmodel",
    "unet": "unet",
    "vae": "vae",
    "text encoder": "clip",
    "clip": "clip",
    "lora": "lora",
}

_air_lock = threading.Lock()
_maps_mem = {"node_map": None, "node_list": None, "loaded": 0}
_repo_pack_mem = {}

CUSTOM_HINTS = (
    "rgthree", "impact", "ultralytics", "detailer", "seedvr", "was ",
    "efficiency", "comfyui-easy", "kjnodes", "ipadapter", "controlnet",
)



def _wf_rank(f: dict) -> int:
    name = (f.get("name") or "").lower()
    typ = str(f.get("type") or "")
    is_zip = name.endswith(".zip") or typ in ("Archive", "Archives")
    is_json = name.endswith(".json") or typ in ("Config", "Workflow", "Workflows")
    is_png = name.endswith((".png", ".webp"))
    sidecar = name in ("config.json", "metadata.json", "extra.json") or name.endswith(".config.json")
    looks_wf = ("workflow" in name) or ("comfy" in name) or typ in ("Workflow", "Workflows")
    if is_zip and looks_wf:
        return 50
    if is_zip:
        return 40
    if is_json and looks_wf and not sidecar:
        return 35
    if is_json and not sidecar:
        return 20
    if is_png:
        return 10
    if is_json and sidecar:
        return 5
    return 0


def pick_workflow_files(files: list) -> list:
    """Zip workflow packs beat sidecar config.json. Never pick weights."""
    ranked = []
    for f in files or []:
        r = _wf_rank(f)
        if r:
            ranked.append((r, f))
    ranked.sort(key=lambda x: x[0], reverse=True)
    out, seen = [], set()
    for _r, f in ranked:
        k = f.get("id") or f.get("name")
        if k in seen:
            continue
        seen.add(k)
        out.append(f)
    return out


def pick_workflow_file(files: list) -> dict | None:
    xs = pick_workflow_files(files)
    return xs[0] if xs else None


def _looks_comfy(obj) -> bool:
    if not isinstance(obj, dict):
        return False
    if isinstance(obj.get("nodes"), list):
        return True
    return any(isinstance(v, dict) and "class_type" in v for v in obj.values())


def parse_workflow_bytes(raw: bytes) -> dict:
    """Accept raw JSON, gzip JSON, or a zip that contains a Comfy graph."""
    if not raw:
        raise ValueError("工作流文件是空的")
    head = raw[:8]
    # zip
    if head.startswith(b"PK"):
        import io, zipfile
        try:
            z = zipfile.ZipFile(io.BytesIO(raw))
        except zipfile.BadZipFile as e:
            raise ValueError("工作流 zip 打不开") from e
        candidates = []
        for info in z.infolist():
            name = info.filename.replace("\\", "/")
            base = name.rsplit("/", 1)[-1]
            if info.is_dir() or base.startswith(".") or "/__MACOSX/" in ("/" + name):
                continue
            if not base.lower().endswith(".json"):
                continue
            try:
                obj = json.loads(z.read(info).decode("utf-8"))
            except Exception:
                continue
            if _looks_comfy(obj):
                candidates.append((info.file_size, obj, base))
        if not candidates:
            names = [i.filename for i in z.infolist() if not i.is_dir()]
            raise ValueError("这个 zip 里没有 Comfy JSON 工作流（文件: " + ", ".join(names[:8]) + ")")
        candidates.sort(key=lambda x: x[0], reverse=True)
        return candidates[0][1]
    # gzip
    if head.startswith(b"\x1f\x8b"):
        import gzip
        raw = gzip.decompress(raw)
    text = raw.decode("utf-8", errors="replace").strip()
    if text.startswith("<") or text.startswith("<!DOCTYPE"):
        raise ValueError("下载到的是网页，不是工作流。可能要登录或换文件。")
    try:
        obj = json.loads(text)
    except Exception as e:
        raise ValueError("工作流文件不是合法 JSON") from e
    if not _looks_comfy(obj):
        raise ValueError("JSON 不是 Comfy 工作流（没有 nodes / class_type）")
    return obj


def parse_workflow_ref(raw: str) -> dict:
    s = (raw or "").strip()
    out = {"modelId": None, "versionId": None}
    m = re.search(r"modelVersionId=(\d+)", s, re.I)
    if m:
        out["versionId"] = int(m.group(1))
    m = re.search(r"/models/(\d+)", s, re.I)
    if m:
        out["modelId"] = int(m.group(1))
    elif re.fullmatch(r"\d+", s):
        n = int(s)
        # version ids are usually larger; treat 7+ digits as version if user pasted one
        out["modelId"] = n
    if not out["modelId"] and not out["versionId"]:
        raise ValueError("请填 Civitai 工作流网址或模型 ID")
    return out


def ui_to_api(wf: dict) -> dict:
    """Convert ComfyUI save (nodes/links) to API prompt format {id: {class_type, inputs}}."""
    if not isinstance(wf, dict):
        raise ValueError("工作流不是 JSON 对象")
    if wf.get("nodes") is None:
        # already API-ish
        sample = next((v for v in wf.values() if isinstance(v, dict)), None)
        if sample and "class_type" in sample:
            return {str(k): v for k, v in wf.items() if isinstance(v, dict) and "class_type" in v}
    links = {}
    for L in wf.get("links") or []:
        if isinstance(L, (list, tuple)) and len(L) >= 5:
            links[L[0]] = (str(L[1]), int(L[2]))
    api = {}
    for n in wf.get("nodes") or []:
        nid = str(n.get("id"))
        inputs = {}
        widgets = list(n.get("widgets_values") or [])
        wi = 0
        for inp in n.get("inputs") or []:
            name = inp.get("name") or inp.get("label")
            if not name:
                continue
            link = inp.get("link")
            if link is not None and link in links:
                src, slot = links[link]
                inputs[name] = [src, slot]
            elif widgets and (inp.get("widget") is not None or link is None):
                # widget-backed input consumes next widgets_values entry
                if wi < len(widgets):
                    val = widgets[wi]
                    wi += 1
                    if not isinstance(val, dict):
                        inputs[name] = val
        t = n.get("type") or ""
        if t == "CLIPTextEncode" and "text" not in inputs and widgets:
            inputs["text"] = widgets[0] if isinstance(widgets[0], str) else widgets[0]
        api[nid] = {"class_type": t, "inputs": inputs}
    return api


def extract_prompts(wf: dict) -> list:
    out = []
    nodes = wf.get("nodes") or []
    if nodes:
        for n in nodes:
            t = n.get("type") or ""
            if "CLIPTextEncode" not in t and "Prompt" not in t:
                continue
            w = n.get("widgets_values") or []
            text = w[0] if w and isinstance(w[0], str) else ""
            title = n.get("title") or t
            out.append({"id": str(n.get("id")), "title": title, "type": t, "text": text})
        return out
    for nid, node in wf.items():
        if not isinstance(node, dict):
            continue
        if node.get("class_type") != "CLIPTextEncode":
            continue
        text = (node.get("inputs") or {}).get("text") or ""
        out.append({"id": str(nid), "title": "CLIPTextEncode", "type": "CLIPTextEncode", "text": text if isinstance(text, str) else ""})
    return out


def extract_files(wf: dict) -> list:
    names = []
    def walk(v):
        if isinstance(v, str) and v.lower().endswith((".safetensors", ".pth", ".pt", ".ckpt", ".gguf", ".bin")):
            names.append(v.replace("\\", "/").split("/")[-1])
        elif isinstance(v, dict):
            if v.get("lora"):
                names.append(str(v.get("lora")).replace("\\", "/").split("/")[-1])
            for x in v.values():
                walk(x)
        elif isinstance(v, list):
            for x in v:
                walk(x)
    if wf.get("nodes"):
        for n in wf["nodes"]:
            walk(n.get("widgets_values"))
    else:
        walk(wf)
    # unique
    seen = []
    for n in names:
        if n and n not in seen:
            seen.append(n)
    return seen


def custom_nodes(wf: dict) -> list:
    types = []
    if wf.get("nodes"):
        types = [n.get("type") or "" for n in wf["nodes"]]
    else:
        types = [v.get("class_type") or "" for v in wf.values() if isinstance(v, dict)]
    custom = []
    for t in types:
        if not t or t in CORE_NODES or t.startswith("Markdown"):
            continue
        if t not in custom:
            custom.append(t)
    return custom


def apply_prompt_edits(api_wf: dict, edits: list) -> dict:
    by_id = {str(e.get("id")): e.get("text") for e in (edits or []) if e.get("id") is not None}
    for nid, node in api_wf.items():
        if nid in by_id and isinstance(node, dict):
            node.setdefault("inputs", {})
            node["inputs"]["text"] = by_id[nid]
    return api_wf


def summarize(wf: dict, meta=None) -> dict:
    nodes = wf.get("nodes") or []
    ncount = len(nodes) if nodes else sum(1 for v in wf.values() if isinstance(v, dict) and v.get("class_type"))
    return {
        "nodes": ncount,
        "prompts": extract_prompts(wf),
        "files": extract_files(wf),
        "customNodes": custom_nodes(wf),
        "meta": meta or {},
    }


def _token() -> str:
    try:
        return TOKEN_PATH.read_text().strip()
    except Exception:
        return ""


def _http_get(url: str, auth=False, timeout=30):
    headers = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
    if auth:
        tok = _token()
        if tok:
            headers["Authorization"] = f"Bearer {tok}"
    return json_call(url, method="GET", headers=headers, timeout=timeout)


def _cache_json(name: str, default):
    fp = AIR_CACHE / name
    if not fp.exists():
        return default
    try:
        data = json.loads(fp.read_text())
        return data if data is not None else default
    except Exception:
        return default


def _write_json(name: str, data):
    fp = AIR_CACHE / name
    fp.parent.mkdir(parents=True, exist_ok=True)
    tmp = fp.with_suffix(fp.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    tmp.replace(fp)


def _file_cache_get(filename: str):
    key = (filename or "").replace("\\", "/").split("/")[-1]
    if not key:
        return None
    with _air_lock:
        blob = _cache_json("files.json", {})
    rec = blob.get(key) or blob.get(key.lower())
    if isinstance(rec, dict) and rec.get("status") == "rate_limited":
        return None
    return rec


def _file_cache_set(filename: str, rec: dict):
    key = (filename or "").replace("\\", "/").split("/")[-1]
    if not key:
        return
    with _air_lock:
        blob = _cache_json("files.json", {})
        blob[key] = rec
        _write_json("files.json", blob)


def _pack_cache_get(class_type: str):
    if not class_type:
        return None
    with _air_lock:
        blob = _cache_json("packs.json", {})
    rec = blob.get(class_type)
    if isinstance(rec, dict) and rec.get("status") == "rate_limited":
        return None
    return rec


def _pack_cache_set(class_type: str, rec: dict):
    if not class_type:
        return
    with _air_lock:
        blob = _cache_json("packs.json", {})
        blob[class_type] = rec
        _write_json("packs.json", blob)


def _refresh_manager_maps(force=False):
    mgr = AIR_CACHE / "manager"
    mgr.mkdir(parents=True, exist_ok=True)
    now = time.time()
    if not force and _maps_mem["loaded"] and now - _maps_mem["loaded"] < 3600:
        return _maps_mem["node_map"], _maps_mem["node_list"]
    mapping = {
        "extension-node-map.json": MANAGER_NODE_MAP,
        "custom-node-list.json": MANAGER_NODE_LIST,
    }
    loaded = {}
    for name, url in mapping.items():
        fp = mgr / name
        # Prefer the on-disk Manager maps. Do not require a download first.
        if force or not fp.exists():
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=60) as r:
                    fp.write_bytes(r.read())
            except Exception:
                if not fp.exists():
                    loaded[name] = {} if "map" in name else {"custom_nodes": []}
                    continue
        try:
            loaded[name] = json.loads(fp.read_text())
        except Exception:
            loaded[name] = {} if "map" in name else {"custom_nodes": []}
    node_map = loaded.get("extension-node-map.json") or {}
    node_list = loaded.get("custom-node-list.json") or {}
    _maps_mem["node_map"] = node_map if isinstance(node_map, dict) else {}
    _maps_mem["node_list"] = node_list if isinstance(node_list, dict) else {"custom_nodes": []}
    _maps_mem["loaded"] = now
    return _maps_mem["node_map"], _maps_mem["node_list"]


def _norm_repo(url: str) -> str:
    u = (url or "").strip().rstrip("/")
    u = re.sub(r"^git\+", "", u)
    u = u.replace("http://", "https://")
    u = u.replace("https://www.github.com/", "https://github.com/")
    if u.endswith(".git"):
        u = u[:-4]
    return u.lower()


def _github_parts(url: str):
    m = re.search(r"github\.com/([^/]+)/([^/#?]+)", url or "", re.I)
    if not m:
        return None, None
    owner, repo = m.group(1), m.group(2)
    if repo.endswith(".git"):
        repo = repo[:-4]
    return owner, repo


def _index_manager():
    node_map, node_list = _refresh_manager_maps()
    class_to_repos = {}
    repo_nclass = {}
    map_patterns = []
    for repo, payload in (node_map or {}).items():
        names = []
        meta = {}
        if isinstance(payload, list) and payload:
            first = payload[0]
            if isinstance(first, list):
                names = [str(x) for x in first if x]
            elif isinstance(first, str):
                names = [str(x) for x in payload if isinstance(x, str)]
            if len(payload) > 1 and isinstance(payload[1], dict):
                meta = payload[1]
        repo_nclass[_norm_repo(repo)] = len(names)
        for n in names:
            class_to_repos.setdefault(n, [])
            if repo not in class_to_repos[n]:
                class_to_repos[n].append(repo)
        pat = meta.get("nodename_pattern")
        if pat:
            map_patterns.append((pat, {"id": None, "title": meta.get("title") or meta.get("title_aux"), "reference": repo, "nodename_pattern": pat}))
    list_by_repo = {}
    patterns = []
    for it in (node_list.get("custom_nodes") or []):
        if not isinstance(it, dict):
            continue
        refs = []
        if it.get("reference"):
            refs.append(it["reference"])
        for f in it.get("files") or []:
            if isinstance(f, str):
                refs.append(f)
        rec = {
            "id": it.get("id"),
            "title": it.get("title"),
            "reference": it.get("reference"),
            "nodename_pattern": it.get("nodename_pattern"),
        }
        for r in refs:
            list_by_repo[_norm_repo(r)] = rec
        pat = it.get("nodename_pattern")
        if pat:
            patterns.append((pat, rec))
    for pat, rec in map_patterns:
        ref = rec.get("reference")
        listed = list_by_repo.get(_norm_repo(ref or "")) if ref else None
        if listed:
            rec = dict(listed)
            rec.setdefault("reference", ref)
        patterns.append((pat, rec))
    return class_to_repos, list_by_repo, patterns, repo_nclass


CORE_REPOS = {
    "https://github.com/comfyanonymous/comfyui",
    "https://github.com/comfy-org/comfyui",
}


def _canonical_air(air: str) -> str:
    """Only normalize an existing AIR. Never invent from modelId."""
    a = (air or "").strip()
    if not a:
        return ""
    if a.startswith("urn:air:"):
        return a
    if a.startswith("air:"):
        return "urn:" + a
    if ":" in a and not a.lower().startswith("http"):
        return "urn:air:" + a
    return ""


def _civitai_get(url: str):
    """Reuse providers.civitai.civitai(); fall back to public GET."""
    try:
        from . import civitai as civ
        code, data = civ.civitai(url)
        if code != 401:
            return code, data
    except Exception:
        pass
    return _http_get(url, auth=False, timeout=30)


def _search_models(query: str):
    """GET /api/v1/models?limit=8&query={stem}. Nested versions have no air."""
    from . import civitai as civ
    code, data = civ.fetch_models(query, limit=8, types=None)
    if code in (429, 503):
        time.sleep(1.5)
        code, data = civ.fetch_models(query, limit=8, types=None)
    if code in (429, 503):
        return code, []
    if code != 200 or not isinstance(data, dict):
        return code, []
    return code, data.get("items") or []


def _collect_exact_files(items, filename: str):
    want = filename.lower()
    hits = []
    seen = set()
    for it in items or []:
        if not isinstance(it, dict):
            continue
        mid = it.get("id")
        mtype = it.get("type")
        for v in it.get("modelVersions") or []:
            vid = v.get("id")
            for f in v.get("files") or []:
                name = (f.get("name") or "").replace("\\", "/").split("/")[-1]
                if name.lower() != want:
                    continue
                key = (mid, vid, f.get("id"), name.lower())
                if key in seen:
                    continue
                seen.add(key)
                hashes = f.get("hashes") if isinstance(f.get("hashes"), dict) else {}
                hits.append({
                    "modelId": mid,
                    "versionId": vid,
                    "fileId": f.get("id"),
                    "filename": name,
                    "modelType": mtype,
                    "fileType": f.get("type"),
                    "baseModel": v.get("baseModel"),
                    "air": v.get("air"),
                    "modelName": it.get("name"),
                    "versionName": v.get("name"),
                    "hashes": hashes,
                })
    return hits


def _version_air(vid, filename: str | None = None):
    """GET /model-versions/{id} then mini/{id} for the air field only."""
    from . import civitai as civ
    if not vid:
        return "", None
    code, ver = civ.fetch_model_version(vid)
    if code in (429, 503):
        time.sleep(1.2)
        code, ver = civ.fetch_model_version(vid)
    if code == 200 and isinstance(ver, dict):
        air = _canonical_air(ver.get("air") or "")
        if air:
            return air, ver
    code, mini = civ.fetch_model_version_mini(vid)
    if code == 200 and isinstance(mini, dict):
        air = _canonical_air(mini.get("air") or "")
        if air:
            return air, ver if isinstance(ver, dict) else mini
    return "", ver if isinstance(ver, dict) else None


def lookup_filename(filename: str, file_hash: str | None = None) -> dict:
    """Resolve one weight basename to a Civitai AIR. Cached. Never invents URNs."""
    from . import civitai as civ
    name = (filename or "").replace("\\", "/").split("/")[-1]
    empty = {
        "filename": name, "air": None, "modelId": None, "versionId": None,
        "fileId": None, "status": "unmatched", "ambiguous": False,
    }
    if not name:
        return empty
    cached = _file_cache_get(name)
    if isinstance(cached, dict) and cached.get("status") in ("matched", "unmatched"):
        rec = dict(cached)
        rec.setdefault("filename", name)
        return rec
    # 1. hash → GET /model-versions/by-hash/{hash}
    h = (file_hash or "").strip()
    if h:
        code, ver = civ.fetch_model_version_by_hash(h)
        if code == 200 and isinstance(ver, dict):
            air = _canonical_air(ver.get("air") or "")
            if air:
                rec = {
                    "filename": name,
                    "air": air,
                    "modelId": ver.get("modelId"),
                    "versionId": ver.get("id"),
                    "fileId": None,
                    "status": "matched",
                    "ambiguous": False,
                    "via": "by-hash",
                    "name": (ver.get("model") or {}).get("name"),
                }
                _file_cache_set(name, rec)
                return rec
    # 2. fuzzy stem search, pin files[].name, GET /model-versions/{id} for air
    stem = name.rsplit(".", 1)[0] if "." in name else name
    code, items = _search_models(stem)
    if code in (429, 503):
        rec = dict(empty)
        rec["status"] = "unmatched"
        return rec
    hits = _collect_exact_files(items, name)
    if not hits:
        rec = dict(empty)
        rec["status"] = "unmatched"
        _file_cache_set(name, rec)
        return rec
    ambiguous = len(hits) > 1
    hit = hits[0]
    air, ver = _version_air(hit.get("versionId"), name)
    rec = {
        "filename": name,
        "air": air or None,
        "modelId": hit.get("modelId") or (ver or {}).get("modelId"),
        "versionId": hit.get("versionId"),
        "fileId": hit.get("fileId"),
        "status": "matched" if air else "unmatched",
        "ambiguous": ambiguous,
        "modelType": hit.get("modelType"),
        "name": hit.get("modelName"),
        "via": "search+version",
    }
    _file_cache_set(name, rec)
    return rec


WEIGHT_EXT = (".safetensors", ".pth", ".pt", ".ckpt", ".gguf", ".bin")


def extract_file_hashes(wf: dict) -> dict:
    """Best-effort basename → hash from graph metadata. Generic, not per-workflow."""
    out = {}
    def consider(name, h):
        if not isinstance(name, str) or not isinstance(h, str):
            return
        base = name.replace("\\", "/").split("/")[-1]
        if not base.lower().endswith(WEIGHT_EXT):
            return
        h = h.strip()
        if len(h) < 8:
            return
        out.setdefault(base, h)
    def walk(v):
        if isinstance(v, dict):
            name = v.get("name") or v.get("filename") or v.get("fileName")
            hashes = v.get("hashes") if isinstance(v.get("hashes"), dict) else {}
            h = hashes.get("SHA256") or hashes.get("AutoV2") or hashes.get("SHA256_12") or hashes.get("AutoV3")
            h = h or (v.get("sha256") if isinstance(v.get("sha256"), str) else None)
            consider(name, h)
            for x in v.values():
                walk(x)
        elif isinstance(v, list):
            for x in v:
                walk(x)
    walk(wf or {})
    return out


def extract_cnr_ids(wf: dict) -> dict:
    out = {}
    for n in (wf.get("nodes") or []):
        if not isinstance(n, dict):
            continue
        ct = n.get("type") or ""
        cnr = ((n.get("properties") or {}) or {}).get("cnr_id")
        if ct and cnr and str(cnr) not in ("comfy-core", "comfyui"):
            out.setdefault(ct, str(cnr))
    return out


def _mint_pack_air(data: dict) -> dict | None:
    if not isinstance(data, dict) or not data.get("id"):
        return None
    pub = ((data.get("publisher") or {}) or {}).get("id") or ""
    ver = ((data.get("latest_version") or {}) or {}).get("version")
    if not ver:
        return None
    nid = str(data.get("id"))
    ident = f"{pub}/{nid}" if pub else nid
    return {
        "air": f"urn:air:comfy:nodepack:comfyregistry:{ident}@{ver}",
        "registryId": ident,
        "nodeId": nid,
        "publisher": pub,
        "version": ver,
        "repo": data.get("repository"),
        "name": data.get("name"),
    }


def _comfy_node_by_class(class_type: str):
    """GET https://api.comfy.org/comfy-nodes/{class_type}/node — primary resolver."""
    url = f"{REGISTRY}/comfy-nodes/{urllib.parse.quote(class_type, safe='')}/node"
    code, data = _http_get(url, timeout=20)
    if code == 429:
        time.sleep(1.2)
        code, data = _http_get(url, timeout=20)
    if code == 200:
        hit = _mint_pack_air(data if isinstance(data, dict) else {})
        if hit:
            hit["via"] = "comfy-nodes"
            return hit
    return None


def _registry_candidates(list_id, owner, repo):
    out = []
    def add(x):
        x = (x or "").strip()
        if x and x not in out:
            out.append(x)
    add(list_id)
    add(repo)
    if repo:
        add(repo.lower())
        add(repo.replace("_", "-"))
        add(repo.replace("-", "_"))
        add(repo.replace("_", "-").lower())
        add(repo.replace("-", "_").lower())
        low = repo.lower()
        for pfx in ("comfyui-", "comfyui_", "comfyui"):
            if low.startswith(pfx):
                rest = repo[len(pfx):]
                add(rest)
                add(rest.lower())
                add(rest.replace("-", "_").lower())
                add(rest.replace("_", "-").lower())
        if list_id and not str(list_id).lower().startswith("comfyui"):
            add("comfyui-" + str(list_id))
            add("comfyui_" + str(list_id))
    return out


def _registry_lookup(node_id: str, expect_repo: str | None):
    if not node_id:
        return None
    code, data = _http_get(f"{REGISTRY}/nodes/{urllib.parse.quote(node_id, safe='')}", timeout=20)
    if code == 429:
        time.sleep(1.2)
        code, data = _http_get(f"{REGISTRY}/nodes/{urllib.parse.quote(node_id, safe='')}", timeout=20)
    if code != 200 or not isinstance(data, dict) or not data.get("id"):
        return None
    repo = _norm_repo(data.get("repository") or "")
    if expect_repo and repo and repo != _norm_repo(expect_repo):
        if str(data.get("id")).lower() != str(node_id).lower():
            return None
    hit = _mint_pack_air(data)
    if not hit:
        return None
    hit["via"] = "nodes"
    return hit


def _resolve_repo_to_pack(repo_url: str, list_rec: dict | None):
    owner, repo = _github_parts(repo_url)
    list_id = (list_rec or {}).get("id")
    for cand in _registry_candidates(list_id, owner, repo):
        hit = _registry_lookup(cand, repo_url)
        if hit:
            hit["repo"] = repo_url
            return hit
        time.sleep(0.04)
    return None


def _class_repos(class_type: str, class_to_repos, list_by_repo, patterns, repo_nclass=None):
    repos = list(class_to_repos.get(class_type) or [])
    pattern_hits = set()
    for pat, rec in patterns:
        try:
            if re.search(pat, class_type):
                ref = rec.get("reference")
                if ref:
                    pattern_hits.add(_norm_repo(ref))
                    if ref not in repos:
                        repos.append(ref)
        except re.error:
            continue
    repo_nclass = repo_nclass or {}
    def score(r):
        rec = list_by_repo.get(_norm_repo(r)) or {}
        pat = 0 if _norm_repo(r) in pattern_hits else 1
        has_id = 0 if rec.get("id") else 1
        size = repo_nclass.get(_norm_repo(r), 10**6)
        in_list = 0 if rec else 1
        core = 0 if _norm_repo(r) in CORE_REPOS else 0
        is_core = 1 if _norm_repo(r) in CORE_REPOS else 0
        return (is_core, pat, has_id, in_list, size)
    repos.sort(key=score)
    return repos


def lookup_nodepack(class_type: str, maps=None, cnr_id: str | None = None) -> dict:
    empty = {
        "class_type": class_type, "air": None, "status": "unmatched",
        "ambiguous": False, "core": False, "repo": None, "registryId": None, "version": None,
    }
    if not class_type or class_type in CORE_NODES or class_type.startswith("Markdown"):
        rec = dict(empty)
        rec["status"] = "core"
        rec["core"] = True
        return rec
    cached = _pack_cache_get(class_type)
    if isinstance(cached, dict) and cached.get("status") in ("matched", "unmatched", "core"):
        # Do not trust a prior "core" label unless it is in CORE_NODES
        # (Manager maps list some custom class_types under ComfyUI forks).
        if not (cached.get("status") == "core" and class_type not in CORE_NODES):
            rec = dict(cached)
            rec.setdefault("class_type", class_type)
            return rec
    # 1. Comfy Registry by class_type. 404 is normal for core / some rgthree internals.
    hit = _comfy_node_by_class(class_type)
    if hit and hit.get("air"):
        rec = {
            "class_type": class_type,
            "air": hit["air"],
            "status": "matched",
            "ambiguous": False,
            "core": False,
            "repo": hit.get("repo"),
            "registryId": hit.get("registryId"),
            "version": hit.get("version"),
            "name": hit.get("name"),
            "via": hit.get("via") or "comfy-nodes",
        }
        _pack_cache_set(class_type, rec)
        return rec
    # 2. Optional cnr_id stamped on the graph (generic Comfy frontend field).
    if cnr_id and str(cnr_id) not in ("comfy-core", "comfyui"):
        hit = _registry_lookup(str(cnr_id), None)
        if hit and hit.get("air"):
            rec = {
                "class_type": class_type,
                "air": hit["air"],
                "status": "matched",
                "ambiguous": False,
                "core": False,
                "repo": hit.get("repo"),
                "registryId": hit.get("registryId"),
                "version": hit.get("version"),
                "name": hit.get("name"),
                "via": "cnr_id",
            }
            _pack_cache_set(class_type, rec)
            return rec
    # 3. Fall back to on-disk Manager extension-node-map.
    if maps is None:
        maps = _index_manager()
    class_to_repos, list_by_repo, patterns, repo_nclass = maps
    repos = _class_repos(class_type, class_to_repos, list_by_repo, patterns, repo_nclass)
    non_core = [r for r in repos if _norm_repo(r) not in CORE_REPOS]
    if repos and not non_core:
        rec = dict(empty)
        rec["status"] = "core"
        rec["core"] = True
        rec["repo"] = repos[0]
        rec["via"] = "manager-core"
        _pack_cache_set(class_type, rec)
        return rec
    repos = non_core
    if not repos:
        rec = dict(empty)
        rec["status"] = "unmatched"
        rec["via"] = "comfy-nodes-404"
        _pack_cache_set(class_type, rec)
        return rec
    hit = None
    for repo in repos:
        list_rec = list_by_repo.get(_norm_repo(repo))
        hit = _resolve_repo_to_pack(repo, list_rec)
        if hit:
            hit["repo"] = repo
            break
    if not hit:
        rec = dict(empty)
        rec["status"] = "unmatched"
        rec["repo"] = repos[0]
        rec["via"] = "manager-miss"
        _pack_cache_set(class_type, rec)
        return rec
    rec = {
        "class_type": class_type,
        "air": hit.get("air"),
        "status": "matched",
        "ambiguous": len(repos) > 1,
        "core": False,
        "repo": hit.get("repo"),
        "registryId": hit.get("registryId"),
        "version": hit.get("version"),
        "name": hit.get("name"),
        "via": "manager-map",
    }
    _pack_cache_set(class_type, rec)
    return rec


def resolve_resources(wf: dict) -> dict:
    """Map extracted weight filenames + custom node class_types to AIR URNs.

    Generic: driven by extract_files / custom_nodes, not a per-workflow allowlist.
    """
    files = extract_files(wf or {})
    nodes = custom_nodes(wf or {})
    hashes = extract_file_hashes(wf or {})
    cnr = extract_cnr_ids(wf or {})
    file_rows = []
    unmatched_files = []
    resources = []
    seen_air = set()

    def add_air(air: str):
        a = (air or "").strip()
        if not a or a in seen_air:
            return
        seen_air.add(a)
        resources.append(a)

    for name in files:
        rec = lookup_filename(name, file_hash=hashes.get(name))
        file_rows.append(rec)
        if rec.get("status") == "matched" and rec.get("air"):
            add_air(rec["air"])
        else:
            unmatched_files.append(name)

    pack_rows = []
    unmatched_nodes = []
    pack_by_air = {}
    maps = None
    for ct in nodes:
        rec = lookup_nodepack(ct, maps=maps, cnr_id=cnr.get(ct))
        if rec.get("via") == "manager-map" or rec.get("via") == "manager-miss" or rec.get("via") == "manager-core":
            if maps is None:
                maps = _index_manager()
        if rec.get("core") or rec.get("status") == "core":
            continue
        if rec.get("status") == "matched" and rec.get("air"):
            air = rec["air"]
            add_air(air)
            bucket = pack_by_air.get(air)
            if bucket:
                if ct not in bucket["nodes"]:
                    bucket["nodes"].append(ct)
                if rec.get("ambiguous"):
                    bucket["ambiguous"] = True
            else:
                bucket = {
                    "air": air,
                    "registryId": rec.get("registryId"),
                    "version": rec.get("version"),
                    "repo": rec.get("repo"),
                    "status": "matched",
                    "ambiguous": bool(rec.get("ambiguous")),
                    "nodes": [ct],
                    "name": rec.get("name"),
                    "via": rec.get("via"),
                }
                pack_by_air[air] = bucket
                pack_rows.append(bucket)
        else:
            unmatched_nodes.append(ct)

    return {
        "resources": resources,
        "files": file_rows,
        "nodepacks": pack_rows,
        "unmatchedFiles": unmatched_files,
        "unmatchedNodes": unmatched_nodes,
    }
