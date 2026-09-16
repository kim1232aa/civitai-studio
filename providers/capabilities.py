"""Provider capability declarations (docs/capability-schema.md).

Single source for GET /api/providers[].capabilities.
Catalog overrides may narrow / specialize, never raise a weaker provider limit.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any

# Formal enums — missing key in tests = fail (never silent full-support).
LORA = ("air", "path", "hub_repo", "none")
LORA_PATH = ("http", "civitai_download", "hub_owner_repo", "none")
LORA_CONF = ("official", "unverified", "none")
RESOLUTION = ("free_wh", "catalog_token", "aspect", "none")
PROGRESS = ("rate", "queue", "status_only", "none")
ESTIMATE = ("buzz", "pricing_api", "catalog_price", "none")
I2I = ("source", "first_frame", "input_references", "none")
I2V = ("sourceImage", "image_url", "first_frame", "fal_endpoint", "none")
SEED_CLAMP = ("reject", "mod", "none")

_WEAK_LORA_RANK = {"none": 0, "hub_repo": 1, "path": 2, "air": 3}
_WEAK_RES_RANK = {"none": 0, "aspect": 1, "catalog_token": 2, "free_wh": 3}
_WEAK_I2V_RANK = {"none": 0, "first_frame": 1, "image_url": 2, "sourceImage": 2, "fal_endpoint": 2}


def _seed(min_v=None, max_v=None, clamp="none"):
    return {"min": min_v, "max": max_v, "clamp": clamp}


# Six backends — explicit none everywhere unknown.
PROVIDER_CAPS: dict[str, dict[str, Any]] = {
    "civitai": {
        "lora": "air",
        "loraPath": "none",
        "loraConfidence": "official",
        "resolution": "free_wh",
        "seed": _seed(clamp="none"),
        "promptMax": None,
        "negative": True,
        "progress": "rate",
        "cancel": True,
        "estimate": "buzz",
        "sampler": True,
        "i2i": "source",
        "video": True,
        "i2v": "sourceImage",
        "videoDuration": True,
        "videoAspect": True,
        "maxRefs": 9,
        "maxImages": 9,
        "refImagesField": "images",
    },
    "fal": {
        "lora": "path",
        "loraPath": "http",
        "loraConfidence": "official",
        "resolution": "free_wh",
        "seed": _seed(clamp="none"),
        "promptMax": None,
        "negative": True,
        "progress": "queue",
        "cancel": True,
        "estimate": "pricing_api",
        "sampler": False,
        "i2i": "first_frame",
        "video": True,
        "i2v": "fal_endpoint",
        "videoDuration": True,
        "videoAspect": True,
        "maxRefs": 9,
        "maxImages": 9,
        "refImagesField": "image_urls",
    },
    "huggingface": {
        "lora": "path",
        "loraPath": "http",
        "loraConfidence": "unverified",  # routed path ≠ official /lora
        "resolution": "free_wh",
        "seed": _seed(clamp="none"),
        "promptMax": None,
        "negative": True,
        "progress": "none",
        "cancel": False,
        "estimate": "none",
        "sampler": False,
        "i2i": "source",
        "video": True,
        "i2v": "image_url",
        "videoDuration": False,
        "videoAspect": False,
        "maxRefs": 9,
        "maxImages": 9,
        "refImagesField": "image_urls",
    },
    "modelscope-ai": {
        "lora": "hub_repo",
        "loraPath": "hub_owner_repo",
        "loraConfidence": "official",
        "resolution": "free_wh",
        "seed": _seed(min_v=-1, max_v=2147483647, clamp="reject"),
        "promptMax": None,
        "negative": True,
        "progress": "status_only",
        "cancel": False,
        "estimate": "none",
        "sampler": False,
        "i2i": "source",
        "video": False,
        "i2v": "none",  # 官方 API-Inference 无视频生成; Hub video task ≠ Infer; catalog 过滤 + 生成/编译硬拒
        "videoDuration": False,
        "videoAspect": True,
        "maxRefs": 3,
        "maxImages": 3,
        "refImagesField": "image_url",
    },
    "modelscope-cn": {
        "lora": "hub_repo",
        "loraPath": "hub_owner_repo",
        "loraConfidence": "official",
        "resolution": "free_wh",
        "seed": _seed(min_v=-1, max_v=2147483647, clamp="reject"),
        "promptMax": None,
        "negative": True,
        "progress": "status_only",
        "cancel": False,
        "estimate": "none",
        "sampler": False,
        "i2i": "source",
        "video": False,
        "i2v": "none",  # 同 modelscope-ai: 官方无视频 API; catalog 不过视频可发送行
        "videoDuration": False,
        "videoAspect": True,
        "maxRefs": 3,
        "maxImages": 3,
        "refImagesField": "image_url",
    },
    "nano-gpt": {
        "lora": "path",
        "loraPath": "civitai_download",
        "loraConfidence": "official",
        "resolution": "catalog_token",
        # WaveSpeed krea-v2/turbo-lora seed Range is "-" (no max); -1 = random.
        # NanoGPT Image API seed is integer with no documented max. Do not copy ModelScope int32.
        "seed": _seed(min_v=-1, max_v=None, clamp="none"),
        "promptMax": None,
        "negative": True,
        "progress": "none",
        "cancel": False,
        "estimate": "catalog_price",
        "sampler": False,
        "i2i": "input_references",
        "video": True,
        "i2v": "image_url",
        "videoDuration": "string_seconds",
        "videoAspect": True,
        "maxRefs": 5,
        "maxImages": 5,
        "refImagesField": "input_references",
    },
}

REQUIRED_KEYS = (
    "lora",
    "loraPath",
    "loraConfidence",
    "resolution",
    "seed",
    "promptMax",
    "negative",
    "progress",
    "cancel",
    "estimate",
    "sampler",
    "i2i",
    "video",
    "i2v",
    "videoDuration",
    "videoAspect",
    "maxRefs",
    "maxImages",
    "refImagesField",
)


def get_provider_capabilities(provider_id: str) -> dict[str, Any]:
    base = PROVIDER_CAPS.get(provider_id)
    if not base:
        # Unknown provider: explicit none everywhere (never silent full-support).
        return {
            "lora": "none",
            "loraPath": "none",
            "loraConfidence": "none",
            "resolution": "none",
            "seed": _seed(clamp="none"),
            "promptMax": None,
            "negative": False,
            "progress": "none",
            "cancel": False,
            "estimate": "none",
            "sampler": False,
            "i2i": "none",
            "video": False,
            "i2v": "none",
            "videoDuration": False,
            "videoAspect": False,
            "maxRefs": 0,
            "maxImages": 0,
            "refImagesField": None,
        }
    return deepcopy(base)


def merge_catalog_override(provider_caps: dict, override: dict | None) -> dict:
    """Catalog may specialize / narrow; must never raise a weaker provider limit.

    Raise examples that must be rejected:
    - loraConfidence: unverified → official
    - progress: none → rate|queue|status_only
    - promptMax: 1200 → None (unlimited is weaker constraint / raise)
    - lora: none → path|air|hub_repo
    - supportsLora True when provider lora is none
    """
    out = deepcopy(provider_caps or {})
    if not override:
        return out
    o = dict(override)

    # --- lora ---
    if "lora" in o:
        p, c = out.get("lora", "none"), o["lora"]
        if _WEAK_LORA_RANK.get(c, -1) <= _WEAK_LORA_RANK.get(p, 0):
            out["lora"] = c
            if c == "none":
                out["loraConfidence"] = "none"
        # else reject raise

    if "supportsLora" in o:
        want = bool(o["supportsLora"])
        if out.get("lora") == "none" and want:
            want = False
        out["supportsLora"] = want

    # --- loraConfidence: official > unverified > none; only allow equal or weaker ---
    _CONF_RANK = {"none": 0, "unverified": 1, "official": 2}
    if "loraConfidence" in o:
        if out.get("lora") == "none":
            out["loraConfidence"] = "none"
        else:
            p = out.get("loraConfidence", "none")
            c = o["loraConfidence"]
            if _CONF_RANK.get(c, -1) <= _CONF_RANK.get(p, 0):
                out["loraConfidence"] = c
            # else reject raise (keep provider)

    # --- progress: none is weakest; cannot raise to rate/queue/status_only ---
    _PROG_RANK = {"none": 0, "status_only": 1, "queue": 2, "rate": 3}
    if "progress" in o:
        p = out.get("progress", "none")
        c = o["progress"]
        if _PROG_RANK.get(c, -1) <= _PROG_RANK.get(p, 0):
            out["progress"] = c

    # --- promptMax: smaller is stricter; None means unlimited = raise if provider had a finite max ---
    if "promptMax" in o:
        p = out.get("promptMax", None)
        c = o["promptMax"]
        if p is None:
            # provider unlimited: catalog may set a finite max (narrow) or stay None
            out["promptMax"] = c
        elif c is None:
            # reject raise to unlimited
            pass
        else:
            try:
                if int(c) <= int(p):
                    out["promptMax"] = int(c)
            except (TypeError, ValueError):
                pass

    # --- resolution: allow specialize free_wh → catalog_token; none is weakest ---
    if "resolution" in o:
        p, c = out.get("resolution", "none"), o["resolution"]
        if c == "none" or _WEAK_RES_RANK.get(c, 0) <= _WEAK_RES_RANK.get(p, 0) or (
            p == "free_wh" and c == "catalog_token"
        ):
            out["resolution"] = c

    # --- i2v: none weakest; catalog cannot invent i2v if provider has none ---
    if "i2v" in o:
        p0, c = out.get("i2v", "none"), o["i2v"]
        if p0 == "none":
            out["i2v"] = "none"
        elif c == "none" or c == p0:
            out["i2v"] = c
        # else reject raise / swap to invented shape

    if "videoDuration" in o:
        p = out.get("videoDuration", False)
        c = o["videoDuration"]
        if p in (False, 0, None):
            out["videoDuration"] = False
        else:
            out["videoDuration"] = c

    if "videoAspect" in o:
        if not out.get("videoAspect"):
            out["videoAspect"] = False
        else:
            out["videoAspect"] = bool(o["videoAspect"])

    # --- maxRefs / maxImages: smaller = stricter; cannot raise above provider ---
    for mk in ("maxRefs", "maxImages"):
        if mk in o:
            try:
                c = int(o[mk])
            except (TypeError, ValueError):
                continue
            p = out.get(mk, 0)
            try:
                p = int(p)
            except (TypeError, ValueError):
                p = 0
            if p <= 0:
                # provider unknown/zero: allow catalog to set finite (still not invent unlimited)
                if c > 0:
                    out[mk] = c
            elif 0 < c <= p:
                out[mk] = c
            # else reject raise

    if "refImagesField" in o and o["refImagesField"]:
        # catalog may specialize field name when provider already accepts refs
        if int(out.get("maxRefs") or 0) > 0:
            out["refImagesField"] = o["refImagesField"]

    for k in (
        "resolutionTokens",
        "imageFields",
        "aspectRatioField",
        "durationField",
        "durationEnum",
        "promptField",
        "loraShape",
        "loraChannel",
        "loraSource",
    ):
        if k in o:
            out[k] = o[k]

    return out


# Official ModelScope AIGC image_url (2026-09-09). Catalog rows used to ship
# capabilities=None, so the canvas fell back to provider maxRefs=1 for every
# 魔搭 model — including t2i Krea-2-Raw — and showed「参考图 5/1」instead of
# 「文生图不吃参考图」.
#
# Sources:
# - Generic AIGC table: image_url is string, editing models only
#   https://www.modelscope.cn/docs/model-service/API-Inference/intro
# - Qwen/Qwen-Image-Edit: image_url string
#   https://modelscope.cn/models/qwen/Qwen-Image-Edit
# - Qwen/Qwen-Image-Edit-2509: image_url list, 1–3
#   https://www.modelscope.cn/models/Qwen/Qwen-Image-Edit-2509
#   https://www.modelscope.cn/learn/2577
#
# Provider maxRefs ceiling = 3 (official max for image_url list / Edit-2509).
# Do NOT copy Nano's 5 (different API: input_references). Catalog may only
# tighten per model (Edit=1, t2i=1, Edit-2509=3).
# Do NOT guess i2i from id/name containing "edit" (REQUIREMENTS §3.5).
MODELSCOPE_REF_POLICY: dict[str, dict[str, Any]] = {
    "Qwen/Qwen-Image": {"task": "text-to-image", "image_to_image": False, "maxRefs": 1},
    "Qwen/Qwen-Image-Edit": {"task": "image-to-image", "image_to_image": True, "maxRefs": 1},
    "MusePublic/Qwen-Image-Edit": {"task": "image-to-image", "image_to_image": True, "maxRefs": 1},
    "Tongyi-MAI/Z-Image-Turbo": {"task": "text-to-image", "image_to_image": False, "maxRefs": 1},
    "krea/Krea-2-Turbo": {"task": "text-to-image", "image_to_image": False, "maxRefs": 1},
    "krea/Krea-2-Raw": {"task": "text-to-image", "image_to_image": False, "maxRefs": 1},
    "krea/krea-realtime-video": {"task": "text-to-video", "image_to_image": False, "maxRefs": 1},
    "Qwen/Qwen-Image-Edit-2509": {"task": "image-to-image", "image_to_image": True, "maxRefs": 3},
    "Wan-AI/Wan2.1-I2V-14B-720P": {"task": "image-to-video", "image_to_image": True, "maxRefs": 1},
    "Wan-AI/Wan2.1-FLF2V-14B-720P": {"task": "image-to-video", "image_to_image": True, "maxRefs": 1},
}


def _modelscope_mid(service_id: str | None) -> str:
    s = (service_id or "").strip().lstrip("/")
    for pfx in ("modelscope-ai/", "modelscope-cn/", "ms/", "modelscope/", "魔搭/"):
        if s.startswith(pfx):
            s = s[len(pfx):]
    return s


def overlay_modelscope_catalog_item(row: dict | None) -> dict:
    """Fill image_to_image / maxRefs from official policy or Hub task/tags.

    Unknown (no policy, no Hub task/tags, no needsSource) stays unknown:
    do not invent i2i / maxRefs=1 from the word "edit" in the model id.
    o57: also stamp supportsLora / loraShape from official AIGC keys, not name guess.
    """
    row = dict(row or {})
    mid = _modelscope_mid(row.get("id") or row.get("model") or "")
    policy = MODELSCOPE_REF_POLICY.get(mid)
    task = str(row.get("task") or row.get("hubTask") or (policy or {}).get("task") or "").strip().lower()
    tags = [str(t).lower() for t in (row.get("tags") or []) if t]

    eats: bool | None = None
    max_r = 1
    if policy:
        eats = bool(policy["image_to_image"])
        max_r = int(policy["maxRefs"])
        if not task:
            task = str(policy["task"])
            row["task"] = task
    if eats is None:
        if row.get("needsSource") or task in ("image-to-image", "image-to-video") or "i2i" in tags or "i2v" in tags:
            eats = True
            max_r = 1
        elif task in ("text-to-image", "text-to-video") or "t2i" in tags or "t2v" in tags:
            eats = False
            max_r = 1
        # Name containing "edit" is not an official schema. Leave eats=None.

    caps = dict(row["capabilities"]) if isinstance(row.get("capabilities"), dict) else {}
    if eats is True:
        caps.setdefault("image_to_image", True)
        caps.setdefault("maxRefs", max_r)
        caps.setdefault("maxImages", max_r)
        caps.setdefault("refImagesField", "image_url")
        caps.setdefault("imageFields", ["image_url"])
        if task == "image-to-image" and not row.get("needsSource"):
            row["needsSource"] = True
        sp = dict(row["supported_parameters"]) if isinstance(row.get("supported_parameters"), dict) else {}
        sp.setdefault("max_input_images", int(caps.get("maxRefs") or max_r))
        row["supported_parameters"] = sp
    elif eats is False:
        caps.setdefault("image_to_image", False)
        caps.setdefault("maxRefs", 1)
        caps.setdefault("maxImages", 1)
        caps.setdefault("refImagesField", "image_url")
        caps.setdefault("imageFields", [])

    # o57: official AIGC image keys include loras
    # https://www.modelscope.cn/docs/model-service/API-Inference/intro
    # Video adapter does not wire loras. Unknown mid does not invent supportsLora.
    cat = str(row.get("category") or "").strip().lower()
    if cat == "video" or task in ("text-to-video", "image-to-video") or "t2v" in tags or "i2v" in tags:
        caps.setdefault("supportsLora", False)
        caps.setdefault("loraShape", "hub_repo")
        caps.setdefault("loraSource", "official-aigc-image-keys-not-wired-for-video")
    elif cat == "image" or task in ("text-to-image", "image-to-image") or "t2i" in tags or "i2i" in tags:
        caps.setdefault("supportsLora", True)
        caps.setdefault("loraShape", "hub_repo")
        caps.setdefault("loraConfidence", "official")
        caps.setdefault("loraSource", "official-aigc-keys")
    else:
        caps.setdefault("loraShape", "hub_repo")
        caps.setdefault("loraSource", "unknown")
    if "supportsLora" in caps and row.get("supportsLora") is None:
        row["supportsLora"] = caps["supportsLora"]

    # Magao API-Inference has no video API. Hub i2v/t2v rows are not sendable:
    # never stamp supportsI2v=True (that would advertise a fake send path).
    if cat == "video" or task in ("text-to-video", "image-to-video") or "t2v" in tags or "i2v" in tags:
        if task == "image-to-video" or "i2v" in tags:
            row.setdefault("needsFirstFrame", True)
        row["supportsI2v"] = False
        caps["supportsI2v"] = False
        row["sendable"] = False
        row["unsendable"] = True
        row["unsendableLabel"] = "不可发"
        row["unsendableReason"] = (
            "魔搭 API-Inference 无视频生成 API（Hub 视频 task ≠ Infer）；目录应过滤，硬拒故意"
        )
        caps.setdefault("maxRefs", max_r if max_r else 1)
        caps.setdefault("maxImages", caps.get("maxRefs") or 1)
        caps.setdefault("refImagesField", "image_url")
        if not caps.get("imageFields"):
            caps["imageFields"] = ["image_url"]

    if caps:
        row["capabilities"] = caps
    if mid and not row.get("id"):
        row["id"] = mid
    return row


def overlay_modelscope_catalog(body: dict | None) -> dict:
    """HTTP-boundary overlay: policy/task rows get caps; unknown rows stay unknown."""
    if not isinstance(body, dict):
        return {}
    out = dict(body)
    items = out.get("items")
    if not isinstance(items, list):
        return out
    out["items"] = [overlay_modelscope_catalog_item(x) if isinstance(x, dict) else x for x in items]
    return out


def modelscope_t2i_refs_error(service_id: str | None, n_refs: int, item: dict | None = None) -> str | None:
    """Chinese 400 when a 魔搭 t2i row is sent connected refs (same class as Nano Flare)."""
    if n_refs <= 0:
        return None
    row = overlay_modelscope_catalog_item(item if isinstance(item, dict) else {"id": _modelscope_mid(service_id)})
    if service_id and not row.get("id"):
        row["id"] = _modelscope_mid(service_id)
        row = overlay_modelscope_catalog_item(row)
    caps = row.get("capabilities") if isinstance(row.get("capabilities"), dict) else {}
    task = str(row.get("task") or "").strip().lower()
    tags = [str(t).lower() for t in (row.get("tags") or []) if t]
    cat = str(row.get("category") or "").strip().lower()
    if cat == "video" or task in ("image-to-video", "text-to-video") or "i2v" in tags or "t2v" in tags:
        return None
    if caps.get("image_to_image") is False:
        name = row.get("name") or row.get("id") or service_id or "当前模型"
        return (
            f"{name} 是文生图，不吃参考图（已连 {n_refs} 张）。"
            "请改选 Qwen Image Edit 或断开参考连线，不能静默忽略"
        )
    return None


def overlay_civitai_catalog_item(row: dict | None) -> dict:
    """Stamp Civitai service rows with item-level LoRA / duration match fields.

    Official sources:
    - GET https://orchestration.civitai.com/v2/services parameters schema
    - Fal-Krea recipe: engine=fal model=krea2 does NOT accept LoRA / negative / free WxH
      https://developer.civitai.com/orchestration/recipes/
    - Comfy-krea2 `image/comfy/krea2/turbo/createImage` accepts AIR `{air: strength}`
    Never invent duration 5/12/16.
    """
    row = dict(row or {})
    sid = str(row.get("id") or row.get("serviceId") or "").strip()
    params = row.get("parameters") if isinstance(row.get("parameters"), dict) else {}
    engine = str(row.get("engine") or params.get("engine") or "").strip().lower()
    model = str(row.get("model") or params.get("model") or "").strip().lower()
    ecosystem = str(row.get("ecosystem") or params.get("ecosystem") or "").strip().lower()
    sid_l = sid.lower()
    caps = dict(row["capabilities"]) if isinstance(row.get("capabilities"), dict) else {}

    has_loras_key = "loras" in params
    fal_krea = engine == "fal" and (
        "krea" in model or "krea" in ecosystem or "krea" in sid_l
    )
    comfy = engine == "comfy" or "/comfy/" in sid_l

    if fal_krea and not has_loras_key:
        caps["supportsLora"] = False
        caps["loraShape"] = "none"
        caps["loraSource"] = "official-fal-krea-recipe-no-lora"
    elif has_loras_key or comfy:
        caps.setdefault("supportsLora", True)
        caps.setdefault("loraShape", "air")
        caps.setdefault("loraConfidence", "official")
        caps.setdefault("loraSource", "orch-v2-services" if has_loras_key else "comfy-air")
    else:
        caps.setdefault("loraShape", "air")
        caps.setdefault("loraSource", "unknown")

    if "durationEnum" not in caps:
        raw_dur = params.get("duration") or params.get("videoDuration")
        enum = None
        if isinstance(raw_dur, dict):
            enum = raw_dur.get("enum") or raw_dur.get("options") or raw_dur.get("oneOf")
        elif isinstance(raw_dur, list):
            enum = raw_dur
        if isinstance(enum, list) and enum:
            caps["durationEnum"] = list(enum)

    frame = row.get("frameFields") or params.get("frameFields") or caps.get("imageFields")
    if isinstance(frame, list) and frame:
        caps.setdefault("imageFields", list(frame))

    if caps:
        row["capabilities"] = caps
    if "supportsLora" in caps and row.get("supportsLora") is None:
        row["supportsLora"] = caps["supportsLora"]
    return row


def overlay_civitai_catalog(body: dict | None) -> dict:
    """HTTP-boundary overlay for Civitai /v2/services rows."""
    if not isinstance(body, dict):
        return {}
    out = dict(body)
    items = out.get("items")
    if not isinstance(items, list):
        return out
    out["items"] = [overlay_civitai_catalog_item(x) if isinstance(x, dict) else x for x in items]
    return out
