"""Canvas catalog fields (H1/H2/H3).

`GET /api/catalog` items must expose canvas `operation` plus capability fields.
Native vendor ops stay on `nativeOperation` / `parameters.operation`.
"""
from __future__ import annotations

import re
from .capabilities import get_provider_capabilities

CANVAS_OPS = (
    "t2i",
    "i2i",
    "t2v",
    "i2v",
    "upscale",
    "transcode",
    "relight",
    "camera-angle",
    "inpaint",
    "bg",
    "text",
    "chat",
    "audio",
    "3d",
    "training",
    "deprecated",
    "utility",
)
CANVAS_OP_SET = set(CANVAS_OPS)

_CATEGORY_GROUPS = (
    frozenset({"camera-angle", "cameraangle", "camera_angle"}),
    frozenset({"inpaint", "erase", "eraser"}),
    frozenset({"text", "chat"}),
    frozenset({"bg", "background"}),
)

_CIVITAI_TRANSCODE_STEPS = frozenset(
    {
        "convertImage",
        "imageUpload",
        "preprocessImage",
        "imageToSvg",
        "transcode",
        "videoFrameExtraction",
        "mediaHash",
        "blobArchive",
        "composeMedia",
    }
)
_CIVITAI_T2I_OPS = frozenset({"createImage", "createVariant"})
_CIVITAI_I2I_OPS = frozenset({"editImage", "edit-image"})
_CIVITAI_I2V_OPS = frozenset(
    {
        "imageToVideo",
        "image-to-video",
        "firstLastFrameToVideo",
        "referenceToVideo",
        "reference-to-video",
        "first-last-frame-to-video",
    }
)
_CIVITAI_T2V_OPS = frozenset({"textToVideo", "text-to-video", "createVideo"})

_K_RE = re.compile(r"^(\d+(?:\.\d+)?)k$", re.I)
_P_RE = re.compile(r"^(\d+)p$", re.I)
_WH_RE = re.compile(r"(\d+)\s*[x×]\s*(\d+)", re.I)


def canonical_category(category: str | None) -> str:
    raw = (category or "").strip()
    if not raw:
        return ""
    key = raw.lower().replace("_", "-")
    for group in _CATEGORY_GROUPS:
        if raw in group or key in group or raw.lower() in group:
            if "camera" in key:
                return "camera-angle"
            if key in {"inpaint", "erase", "eraser"}:
                return "inpaint"
            if key in {"text", "chat"}:
                return "text"
            if key in {"bg", "background"}:
                return "bg"
    return raw


def category_matches(item_category: str | None, requested: str | None) -> bool:
    if not requested:
        return True
    want = canonical_category(requested)
    got = canonical_category(item_category)
    if want == got:
        return True
    if not item_category:
        return False
    a = (item_category or "").lower().replace("_", "-")
    b = (requested or "").lower().replace("_", "-")
    if a == b:
        return True
    for group in _CATEGORY_GROUPS:
        if a in group and b in group:
            return True
        if (item_category or "") in group and (requested or "") in group:
            return True
    return False


def native_operation(item: dict | None) -> str:
    item = item or {}
    native = item.get("nativeOperation")
    if native not in (None, ""):
        return str(native)
    params = item.get("parameters") or {}
    if isinstance(params, dict) and params.get("operation") not in (None, ""):
        op = str(params.get("operation"))
        if op not in CANVAS_OP_SET:
            return op
    op = item.get("operation")
    if op not in (None, "") and str(op) not in CANVAS_OP_SET:
        return str(op)
    return ""


def _as_enum(value) -> list:
    if isinstance(value, dict):
        return [x for x in (value.get("enum") or []) if x not in (None, "")]
    if isinstance(value, (list, tuple)):
        return [x for x in value if x not in (None, "")]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _num_range(rule) -> dict | None:
    if not isinstance(rule, dict):
        return None
    mn = rule.get("min") if "min" in rule else rule.get("minimum")
    mx = rule.get("max") if "max" in rule else rule.get("maximum")
    if mn is None and mx is None:
        return None
    return {"min": mn, "max": mx}


def resolution_score(value) -> float:
    text = str(value or "").strip().lower()
    match = _K_RE.fullmatch(text)
    if match:
        return float(match.group(1)) * 1000
    match = _P_RE.fullmatch(text)
    if match:
        return float(match.group(1))
    match = _WH_RE.search(text)
    if match:
        return float(max(int(match.group(1)), int(match.group(2))))
    try:
        return float(text)
    except ValueError:
        return 0.0


def _reference_limit(constraints: dict, frame_fields: list, item: dict) -> int | None:
    limit = None
    for field in frame_fields:
        rule = (constraints or {}).get(field) or {}
        if not isinstance(rule, dict):
            continue
        value = rule.get("maxItems", rule.get("maxLength"))
        if value is None:
            continue
        try:
            limit = max(limit or 0, int(value))
        except (TypeError, ValueError):
            continue
    if limit is not None:
        return limit
    if item.get("referenceLimit") not in (None, ""):
        try:
            return int(item["referenceLimit"])
        except (TypeError, ValueError):
            return None
    sp = item.get("supported_parameters") or {}
    if isinstance(sp, dict) and sp.get("max_images") not in (None, ""):
        try:
            return int(sp["max_images"])
        except (TypeError, ValueError):
            return None
    return None


def _resolution_fields(item: dict, cap: dict | None, backend: str) -> dict:
    constraints = (cap or {}).get("constraints") or {}
    extra = (cap or {}).get("extraFlags") or {}
    params = item.get("parameters") or {}
    sp = item.get("supported_parameters") or {}
    if not isinstance(sp, dict):
        sp = {}
    if not isinstance(params, dict):
        params = {}

    enum = _as_enum(item.get("resolutions"))
    mode = None
    if not enum:
        enum = _as_enum(params.get("resolutions"))
    if not enum:
        enum = _as_enum(constraints.get("resolution"))
        if enum:
            mode = "enum"
    if not enum:
        enum = _as_enum(extra.get("resolution"))
        if enum:
            mode = "enum"
    if not enum:
        enum = _as_enum(sp.get("resolutions"))
        if enum:
            mode = "catalog_token"

    width_range = _num_range(constraints.get("width"))
    height_range = _num_range(constraints.get("height"))
    wh_range = None
    if width_range or height_range:
        wh_range = {"width": width_range, "height": height_range}

    if enum:
        if mode is None:
            mode = "catalog_token" if backend == "nano-gpt" else "enum"
        max_resolution = max(enum, key=resolution_score, default="")
        return {
            "resolutions": list(enum),
            "maxResolution": max_resolution or "",
            "whRange": None,
            "resolutionMode": mode,
        }
    if wh_range:
        return {
            "resolutions": [],
            "maxResolution": "",
            "whRange": wh_range,
            "resolutionMode": "free_wh",
        }
    provider_mode = get_provider_capabilities(backend).get("resolution") or "none"
    if provider_mode in ("free_wh", "catalog_token", "aspect", "none"):
        return {
            "resolutions": [],
            "maxResolution": "",
            "whRange": None,
            "resolutionMode": provider_mode if provider_mode != "aspect" else "none",
        }
    return {
        "resolutions": [],
        "maxResolution": "",
        "whRange": None,
        "resolutionMode": "none",
    }


def civitai_canvas_op(item: dict) -> str:
    step = str(item.get("step") or "")
    native = native_operation(item)
    sid = str(item.get("id") or "")
    name = str(item.get("name") or "").lower()
    category = str(item.get("category") or "")

    if step in _CIVITAI_TRANSCODE_STEPS or sid.endswith("/transcode") or "/transcode" in sid:
        return "transcode"
    if step == "imageUpscaler" or "upscale" in name or "upscaler" in step.lower():
        return "upscale"
    if native in _CIVITAI_I2I_OPS or step == "editImage":
        return "i2i"
    if step == "imageGen" and (native in _CIVITAI_T2I_OPS or native == ""):
        return "t2i"
    if step == "videoGen":
        low = native.lower()
        if native in _CIVITAI_I2V_OPS or "image-to-video" in low or "imagetovideo" in low.replace("-", ""):
            return "i2v"
        if native in _CIVITAI_T2V_OPS or "text-to-video" in low or "texttovideo" in low.replace("-", ""):
            return "t2v"
        if "first" in low or "reference" in low or "image" in low:
            return "i2v"
        return "t2v" if native else "i2v"
    if step == "textToImage":
        return "deprecated"
    if step in ("training", "imageResourceTraining"):
        return "training"
    if step == "polyGen" or category == "3d":
        return "3d"
    if category == "audio" or "audio" in step.lower() or step in ("textToSpeech", "transcription"):
        return "audio"
    if step:
        return step
    return "utility"


def fal_canvas_op(item: dict) -> str:
    recipe = canonical_category(item.get("category"))
    eid = str(item.get("id") or "")
    fcat = str(item.get("falCategory") or "").lower()
    blob = f"{eid} {fcat} {recipe}".lower()
    if recipe == "upscale" or "upscale" in blob:
        return "upscale"
    if recipe == "bg":
        return "bg"
    if recipe == "relight":
        return "relight"
    if recipe == "camera-angle":
        return "camera-angle"
    if recipe == "inpaint":
        return "inpaint"
    if recipe == "video" or "video" in fcat or "video" in eid:
        if (
            item.get("needsFirstFrame")
            or "image-to-video" in blob
            or "first-last" in blob
            or "reference-to-video" in blob
        ):
            return "i2v"
        return "t2v"
    if (
        item.get("needsSource")
        or "/edit" in eid
        or fcat in ("image-to-image", "image-to-3d")
        or "image-to-image" in eid
    ):
        return "i2i"
    return "t2i"


def nano_canvas_op(item: dict) -> str:
    cat = canonical_category(item.get("category"))
    caps = item.get("capabilities") or {}
    task = str(item.get("task") or "")
    if cat in ("text", "chat"):
        return "text"
    if cat == "upscale":
        return "upscale"
    if cat == "bg":
        return "bg"
    if cat == "video" or "video" in task:
        if caps.get("image_to_video") or item.get("needsFirstFrame") or task == "image-to-video":
            return "i2v"
        return "t2v"
    if item.get("needsSource") or task == "image-to-image":
        return "i2i"
    if caps.get("image_to_image") and not caps.get("image_generation", True):
        return "i2i"
    return "t2i"


def hf_canvas_op(item: dict) -> str:
    task = str(item.get("task") or "")
    cat = canonical_category(item.get("category"))
    if cat == "upscale" or "upscale" in task:
        return "upscale"
    if task == "text-to-video":
        return "t2v"
    if task == "image-to-video":
        return "i2v"
    if task == "image-to-image":
        return "i2i"
    return "t2i"


def modelscope_canvas_op(item: dict) -> str:
    cat = canonical_category(item.get("category"))
    sid = str(item.get("id") or "").lower()
    task = str(item.get("task") or "")
    if cat == "upscale" or "upscale" in sid or "upscale" in task:
        return "upscale"
    if cat == "video" or "video" in task:
        if item.get("needsFirstFrame") or "image-to-video" in task:
            return "i2v"
        return "t2v"
    if item.get("needsSource") or "image-edit" in sid or "/edit" in sid or task == "image-to-image":
        return "i2i"
    return "t2i"


def canvas_operation(item: dict, backend: str) -> str:
    backend = backend or str((item or {}).get("backend") or "")
    if backend == "civitai":
        return civitai_canvas_op(item)
    if backend == "fal":
        return fal_canvas_op(item)
    if backend == "nano-gpt":
        return nano_canvas_op(item)
    if backend == "huggingface":
        return hf_canvas_op(item)
    if backend in ("modelscope-ai", "modelscope-cn", "modelscope"):
        return modelscope_canvas_op(item)
    return civitai_canvas_op(item)


def _supported_ops(item: dict, backend: str, op: str) -> list[str]:
    found: list[str] = []
    caps = item.get("capabilities") or {}
    if backend == "nano-gpt" and isinstance(caps, dict):
        if caps.get("image_generation"):
            found.append("t2i")
        if caps.get("image_to_image") or caps.get("inpainting"):
            found.append("i2i")
        if caps.get("text_to_video") or caps.get("video_generation"):
            found.append("t2v")
        if caps.get("image_to_video"):
            found.append("i2v")
    if op and op not in found:
        found.insert(0, op)
    provider = get_provider_capabilities(backend)
    if provider.get("i2i") == "none":
        found = [x for x in found if x != "i2i"]
    if provider.get("i2v") == "none":
        found = [x for x in found if x != "i2v"]
    if provider.get("upscale") is False:
        found = [x for x in found if x != "upscale"]
    unique = []
    for x in found:
        if x and x not in unique:
            unique.append(x)
    return unique or ([op] if op else [])


def _needs_flags(item: dict, op: str) -> tuple[bool, bool, bool]:
    needs_source = bool(item.get("needsSource"))
    needs_first = bool(item.get("needsFirstFrame"))
    needs_mask = bool(item.get("needsMask"))
    if op in ("i2i", "relight", "camera-angle", "upscale", "inpaint"):
        needs_source = True
    if op == "t2i":
        needs_source = False
    if op == "i2v":
        needs_first = True
        needs_source = False
    if op == "t2v":
        needs_first = False
        needs_source = False
    if op == "inpaint":
        needs_mask = True
    return needs_source, needs_first, needs_mask


def enrich_catalog_item(item: dict, backend: str, cap: dict | None = None) -> dict:
    row = dict(item or {})
    backend = backend or str(row.get("backend") or "civitai")
    row["backend"] = backend
    native = native_operation(row)
    if native:
        row["nativeOperation"] = native
    op = canvas_operation(row, backend)
    needs_source, needs_first, needs_mask = _needs_flags(row, op)
    constraints = (cap or {}).get("constraints") or {}
    frame_fields = list((cap or {}).get("frameFields") or row.get("frameFields") or [])
    aspect = _as_enum(row.get("aspectRatios"))
    if not aspect:
        aspect = _as_enum(
            constraints.get("aspectRatio") or constraints.get("aspect_ratio")
        )
    res = _resolution_fields(row, cap, backend)
    ref = _reference_limit(constraints, frame_fields, row)
    if ref is None and backend == "fal" and needs_source and op in ("i2i", "relight", "camera-angle", "inpaint", "upscale"):
        fields = list(row.get("imageFields") or [])
        if "image_urls" not in fields:
            ref = 1
    supported = _supported_ops(row, backend, op)
    row.update(
        {
            "operation": op,
            "supportedOperations": supported,
            "needsSource": needs_source,
            "needsFirstFrame": needs_first,
            "needsMask": needs_mask,
            "aspectRatios": aspect,
            "referenceLimit": ref,
            "resolutions": res["resolutions"],
            "maxResolution": res["maxResolution"],
            "whRange": res["whRange"],
            "resolutionMode": res["resolutionMode"],
        }
    )
    if cap:
        row["capability"] = {
            "status": cap.get("status") or "",
            "constraints": constraints,
            "frameFields": frame_fields,
            "extraFlags": cap.get("extraFlags") or {},
            "resolutions": res["resolutions"],
            "maxResolution": res["maxResolution"],
            "referenceLimit": ref,
            "supportedOperations": supported,
        }
    return row


def enrich_catalog_items(items: list, backend: str) -> list:
    return [enrich_catalog_item(x, backend) for x in items or []]
