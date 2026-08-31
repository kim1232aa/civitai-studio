#!/usr/bin/env python3
"""Build docs/capabilities.json + capabilities.md from catalog.json and local OpenAPI yamls.

Read-only: does not call the live API.
"""
from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

ROOT = Path("/workspace/civitai-studio/docs")
RAW = ROOT / "_raw"
CATALOG = ROOT / "catalog.json"
SERVER = Path("/workspace/civitai-studio/server.py")
OUT_JSON = ROOT / "capabilities.json"
OUT_MD = ROOT / "capabilities.md"

FRAME_EXACT = {
    "firstFrame", "lastFrame", "firstFrameImage", "lastFrameImage",
    "startImage", "endImage", "endSourceImage", "startFrame", "endFrame",
    "image", "images", "inputImage", "inputImages", "initImage",
    "sourceImage", "sourceImageUrl", "lastImage", "firstImage",
    "reference", "references", "referenceImage", "referenceImages",
    "referenceVideo", "referenceVideos", "referenceVideoUrls",
    "referenceAudios", "referenceAudio",
    "video", "videos", "videoUrl", "sourceVideo", "sourceVideoUrl",
    "startVideo", "endVideo", "cover",
    "mask", "maskImage", "maskUrl",
    "keyframes", "frames", "frame",
    "styleImages", "styleImage", "styleReferences", "styleReference",
    "imageStyleReferences",
    "garmentUrl", "garmentImage", "personImage", "faceImage", "poseImage",
    "subjectUrl", "subjectMaskUrl", "subjectMaskBlobKey",
    "audioUrl", "imageUrl", "imageBlob", "videoBlob",
    "audio", "sourceAudio",
}
FRAME_SKIP = {
    "imagemetadata", "imagesize", "outputformat", "generateaudio",
    "enableaudio", "keepaudio", "numimages", "numframes", "audiocfg",
    "enablepromptenhancer", "enablepromptexpansion", "enableprompt",
}
IDENT_KEYS = ("engine", "operation", "ecosystem", "model", "version", "provider")


def load_yaml(path: Path) -> dict:
    with path.open() as f:
        return yaml.safe_load(f) or {}


def schema_name_from_ref(ref: str) -> str:
    return ref.split("/")[-1]


def find_root_input(spec: dict) -> str | None:
    paths = spec.get("paths") or {}
    for _path, ops in paths.items():
        for method, op in (ops or {}).items():
            if method.startswith("x-") or not isinstance(op, dict):
                continue
            content = ((op.get("requestBody") or {}).get("content") or {})
            for _ctype, body in content.items():
                sch = (body or {}).get("schema") or {}
                if "$ref" in sch:
                    return schema_name_from_ref(sch["$ref"])
    comps = (spec.get("components") or {}).get("schemas") or {}
    inputs = [n for n in comps if n.endswith("Input")]
    preferred = [n for n in inputs if n[:-5] in (spec.get("info") or {}).get("title", "")]
    return (preferred[0] if preferred else None) or (inputs[0] if inputs else None)


def find_inline_body(spec: dict) -> dict | None:
    paths = spec.get("paths") or {}
    for _path, ops in paths.items():
        for method, op in (ops or {}).items():
            if method.startswith("x-") or not isinstance(op, dict):
                continue
            content = ((op.get("requestBody") or {}).get("content") or {})
            for _ctype, body in content.items():
                sch = (body or {}).get("schema") or {}
                if sch and "$ref" not in sch:
                    return sch
    return None


def recipe_paths(spec: dict) -> list[str]:
    return list((spec.get("paths") or {}).keys())


def query_params(spec: dict) -> list[str]:
    names = []
    for _path, ops in (spec.get("paths") or {}).items():
        for method, op in (ops or {}).items():
            if not isinstance(op, dict):
                continue
            for prm in op.get("parameters") or []:
                if isinstance(prm, dict) and prm.get("in") == "query" and prm.get("name"):
                    names.append(prm["name"])
    return sorted(set(names))


def own_discriminator(schema: dict | None) -> dict | None:
    if not isinstance(schema, dict):
        return None
    if "discriminator" in schema:
        return schema["discriminator"]
    for part in schema.get("allOf") or []:
        if isinstance(part, dict) and "$ref" not in part and "discriminator" in part:
            return part["discriminator"]
    return None


def collect_oneofs(schema: dict | None) -> list:
    if not isinstance(schema, dict):
        return []
    out = list(schema.get("oneOf") or []) + list(schema.get("anyOf") or [])
    for part in schema.get("allOf") or []:
        if isinstance(part, dict) and "$ref" not in part:
            out.extend(part.get("oneOf") or [])
            out.extend(part.get("anyOf") or [])
    return out


def unwrap_nullable(t: Any) -> Any:
    if isinstance(t, list):
        non_null = [x for x in t if x != "null"]
        if len(non_null) == 1:
            return non_null[0]
        return non_null
    return t


def merge_two(base: dict, extra: dict) -> dict:
    out = dict(base)
    for k, v in extra.items():
        if k == "properties" and isinstance(v, dict):
            props = dict(out.get("properties") or {})
            props.update(v)
            out["properties"] = props
        elif k == "required" and isinstance(v, list):
            req = list(out.get("required") or [])
            for r in v:
                if r not in req:
                    req.append(r)
            out["required"] = req
        elif k == "enum" and v:
            out["enum"] = v
        elif v is not None:
            out[k] = v
    return out


def resolve_schema(schema: dict, spec: dict, stack: set[str] | None = None) -> dict:
    """Merge allOf / $ref. Does not follow discriminator mappings (siblings stay separate)."""
    if not isinstance(schema, dict):
        return {}
    stack = set(stack or [])
    schemas = (spec.get("components") or {}).get("schemas") or {}

    if "$ref" in schema:
        name = schema_name_from_ref(schema["$ref"])
        if name in stack:
            return {k: v for k, v in schema.items() if k != "$ref"}
        target = schemas.get(name)
        if not isinstance(target, dict):
            return {"$ref": schema["$ref"]}
        merged = resolve_schema(target, spec, stack | {name})
        extra = {k: v for k, v in schema.items() if k != "$ref"}
        return merge_two(merged, extra)

    acc: dict = {
        "properties": {},
        "required": [],
        "enum": None,
        "type": schema.get("type"),
        "description": schema.get("description"),
        "default": schema.get("default") if "default" in schema else None,
        "minimum": schema.get("minimum"),
        "maximum": schema.get("maximum"),
        "minLength": schema.get("minLength"),
        "maxLength": schema.get("maxLength"),
        "minItems": schema.get("minItems"),
        "maxItems": schema.get("maxItems"),
        "pattern": schema.get("pattern"),
        "format": schema.get("format"),
        "items": schema.get("items"),
        "additionalProperties": schema.get("additionalProperties"),
        "const": schema.get("const"),
    }
    if "enum" in schema:
        acc["enum"] = list(schema["enum"])
    if schema.get("properties"):
        acc["properties"].update(schema["properties"])
    if schema.get("required"):
        acc["required"] = list(schema["required"])

    for part in schema.get("allOf") or []:
        if not isinstance(part, dict):
            continue
        acc = merge_two(acc, resolve_schema(part, spec, stack))

    # Property-level oneOf/anyOf (e.g. ["null", string]) — merge type/enum only.
    # Do NOT merge incompatible object variants at the schema-root (handled by walk).
    for key in ("anyOf", "oneOf"):
        variants = schema.get(key) or []
        if not variants:
            continue
        enums: list = []
        types: list = []
        objectish = False
        for v in variants:
            if not isinstance(v, dict):
                continue
            rv = resolve_schema(v, spec, stack)
            if rv.get("enum"):
                enums.extend(rv["enum"])
            t = unwrap_nullable(rv.get("type"))
            if t:
                types.append(t)
            if rv.get("properties"):
                objectish = True
        if enums:
            acc["enum"] = list(dict.fromkeys(enums))
        if types and acc.get("type") is None:
            acc["type"] = types[0] if len(set(map(str, types))) == 1 else types
        if objectish and not acc.get("properties"):
            # root-level oneOf objects should have been split by the walker;
            # if we still see them here, do not blindly union properties.
            pass

    if acc.get("const") is not None and not acc.get("enum"):
        acc["enum"] = [acc["const"]]
    return acc


def flatten_named(name: str, spec: dict) -> dict:
    schemas = (spec.get("components") or {}).get("schemas") or {}
    raw = schemas.get(name)
    if not isinstance(raw, dict):
        return {"properties": {}, "required": [], "schemaName": name}
    merged = resolve_schema(raw, spec, {name})
    merged["schemaName"] = name
    return merged


def flatten_inline(schema: dict, spec: dict) -> dict:
    merged = resolve_schema(schema, spec, set())
    merged["schemaName"] = merged.get("schemaName") or "inline"
    return merged


def constraint_from_schema(prop: dict, spec: dict, stack: set[str]) -> dict:
    prop = resolve_schema(prop, spec, stack)
    out: dict[str, Any] = {}
    t = unwrap_nullable(prop.get("type"))
    if t:
        out["type"] = t
    if prop.get("enum") is not None:
        out["enum"] = list(prop["enum"])
    if "minimum" in prop and prop["minimum"] is not None:
        out["min"] = prop["minimum"]
    if "maximum" in prop and prop["maximum"] is not None:
        out["max"] = prop["maximum"]
    if prop.get("minLength") is not None:
        out["minLength"] = prop["minLength"]
        out.setdefault("min", prop["minLength"])
    if prop.get("maxLength") is not None:
        out["maxLength"] = prop["maxLength"]
        out.setdefault("max", prop["maxLength"])
    if prop.get("minItems") is not None:
        out["minItems"] = prop["minItems"]
    if prop.get("maxItems") is not None:
        out["maxItems"] = prop["maxItems"]
    if prop.get("format"):
        out["format"] = prop["format"]
    if "default" in prop and prop["default"] is not None:
        out["default"] = prop["default"]
    return out


def compact_constraints(props: dict, spec: dict) -> dict:
    out = {}
    for name, sch in props.items():
        if not isinstance(sch, dict):
            continue
        c = constraint_from_schema(sch, spec, set())
        slim = {k: v for k, v in c.items() if k in {
            "min", "max", "enum", "type", "minLength", "maxLength",
            "minItems", "maxItems",
        } and v is not None and v != []}
        if slim:
            out[name] = slim
    return out


def defaults_from_props(props: dict, spec: dict) -> dict:
    out = {}
    for name, sch in props.items():
        if not isinstance(sch, dict):
            continue
        c = constraint_from_schema(sch, spec, set())
        if "default" in c:
            out[name] = c["default"]
        elif c.get("enum") and len(c["enum"]) == 1 and name in IDENT_KEYS:
            out[name] = c["enum"][0]
    return out


def ident_from_props(props: dict, spec: dict, disc: dict) -> dict:
    out = {k: disc.get(k) for k in IDENT_KEYS}
    for name in IDENT_KEYS:
        if out.get(name) is not None:
            continue
        sch = props.get(name)
        if not isinstance(sch, dict):
            continue
        c = constraint_from_schema(sch, spec, set())
        if c.get("enum") and len(c["enum"]) == 1:
            out[name] = c["enum"][0]
        elif "default" in c and name in ("operation", "version", "model"):
            # keep None for matching; default lives in defaults
            pass
    return out


def detect_frame_fields(prop_names) -> list:
    out = []
    for k in prop_names:
        lk = k.lower()
        if lk in FRAME_SKIP:
            continue
        if lk.endswith(("seconds", "strength", "scale", "count", "size", "metadata", "format", "expansion", "checker")):
            continue
        if k in FRAME_EXACT or lk in {x.lower() for x in FRAME_EXACT}:
            out.append(k)
            continue
        if lk.endswith(("image", "images", "frame", "frames", "video", "videos", "mask")):
            out.append(k)
            continue
        if "reference" in lk and any(tok in lk for tok in ("image", "video", "audio", "url", "s")):
            out.append(k)
            continue
        if lk.endswith("url") and any(tok in lk for tok in (
            "image", "video", "frame", "mask", "garment", "subject", "audio", "source",
        )):
            out.append(k)
    # stable unique
    seen = set()
    uniq = []
    for x in out:
        if x not in seen:
            seen.add(x)
            uniq.append(x)
    return uniq


def extra_flags(props: dict, spec: dict, defaults: dict, constraints: dict,
                name: str | None, schema_name: str | None, model: str | None) -> dict:
    blob = " ".join(x or "" for x in (name, schema_name, str(model or ""))).lower()

    def boolish(field_names: tuple[str, ...], variant_tokens: tuple[str, ...]):
        present_field = next((f for f in field_names if f in props), None)
        is_variant = any(tok in blob for tok in variant_tokens)
        if is_variant:
            return True
        if present_field:
            val = defaults.get(present_field)
            if isinstance(val, bool):
                return val
            return False
        return None

    def numeric_flag(field: str, with_enum: bool = False):
        if field not in props:
            return None
        c = constraints.get(field) or {}
        # constraints may have dropped default; recover
        d = defaults.get(field, c.get("default"))
        out = {
            "present": True,
            "default": d,
            "min": c.get("min"),
            "max": c.get("max"),
        }
        if with_enum:
            out["enum"] = c.get("enum")
        # drop Nones except present
        return {k: v for k, v in out.items() if v is not None or k == "present"}

    def resolution_flag():
        if "resolution" not in props:
            return None
        c = constraints.get("resolution") or {}
        out = {"present": True}
        if c.get("enum"):
            out["enum"] = c["enum"]
        if c.get("min") is not None:
            out["min"] = c["min"]
        if c.get("max") is not None:
            out["max"] = c["max"]
        if "resolution" in defaults:
            out["default"] = defaults["resolution"]
        return out

    return {
        "turbo": boolish(("turbo", "useTurbo"), ("turbo",)),
        "fast": boolish(("fast", "fastMode", "useFastWan"), ("fast",)),
        "quantity": numeric_flag("quantity"),
        "duration": numeric_flag("duration", with_enum=True),
        "resolution": resolution_flag(),
    }


def map_type(step: str | None) -> str:
    if step == "imageGen":
        return "image"
    if step == "videoGen":
        return "video"
    return "other"


def map_status(raw: str | None) -> str:
    s = (raw or "unknown").lower()
    if s in {"available", "healthy", "online", "ok", "ready"}:
        return "available"
    if s in {"degraded", "partial", "throttled"}:
        return "degraded"
    if s in {"unavailable", "down", "offline", "disabled", "error"}:
        return "unavailable"
    return s if s else "unknown"


def mapping_lookup(mapping: dict, val: Any) -> str | None:
    if val is None:
        return None
    if val in mapping:
        return mapping[val]
    sval = str(val)
    if sval in mapping:
        return mapping[sval]
    lower = {str(k).lower(): v for k, v in mapping.items()}
    if sval.lower() in lower:
        return lower[sval.lower()]
    compact = sval.replace("-", "").replace("_", "").replace(".", "").lower()
    for k, v in mapping.items():
        if str(k).replace("-", "").replace("_", "").replace(".", "").lower() == compact:
            return v
    return None


def walk_to_leaf(root_name: str, spec: dict, params: dict) -> tuple[str, dict, list[str], dict]:
    """Follow discriminators using known params. Returns schemaName, flat, trail, disc_values."""
    schemas = (spec.get("components") or {}).get("schemas") or {}
    current = root_name
    trail = [current]
    seen = {current}
    disc_values: dict[str, Any] = {}
    while current in schemas:
        own = own_discriminator(schemas[current])
        if not own:
            break
        prop = own.get("propertyName")
        mapping = own.get("mapping") or {}
        if not prop or not mapping:
            break
        val = params.get(prop)
        if val is None:
            break
        ref = mapping_lookup(mapping, val)
        if not ref:
            break
        nxt = schema_name_from_ref(ref)
        if nxt in seen:
            break
        disc_values[prop] = val
        seen.add(nxt)
        current = nxt
        trail.append(current)
    return current, flatten_named(current, spec), trail, disc_values


def walk_all_leaves(root_name: str, spec: dict) -> list[dict]:
    """Concrete discriminator leaves. Does not merge incompatible oneOfs."""
    schemas = (spec.get("components") or {}).get("schemas") or {}
    out: list[dict] = []
    if root_name not in schemas:
        return out

    def rec(name: str, disc_values: dict, chain: list[str]):
        if name in chain:
            return
        schema = schemas.get(name)
        if not isinstance(schema, dict):
            return
        own = own_discriminator(schema)
        mapping = (own or {}).get("mapping") or {}
        prop = (own or {}).get("propertyName")
        if prop and mapping:
            for key, ref in mapping.items():
                child = schema_name_from_ref(ref)
                rec(child, {**disc_values, prop: key}, chain + [name])
            return
        variants = collect_oneofs(schema)
        refs = [schema_name_from_ref(v["$ref"]) for v in variants if isinstance(v, dict) and "$ref" in v]
        if refs and not own:
            for child in refs:
                rec(child, disc_values, chain + [name])
            return
        # leaf
        flat = flatten_named(name, spec)
        ident = ident_from_props(flat.get("properties") or {}, spec, disc_values)
        out.append({
            "schemaName": name,
            "trail": chain + [name],
            "disc": disc_values,
            "ident": ident,
            "flat": flat,
        })

    rec(root_name, {}, [])
    return out


def fields_from_catalog_params(params: dict) -> tuple[list, list, dict, dict]:
    required = [k for k, v in params.items() if v is not None]
    optional: list[str] = []
    defaults = {k: v for k, v in params.items() if v is not None}
    constraints = {k: {"type": type(v).__name__} for k, v in params.items() if v is not None}
    return required, optional, defaults, constraints


def build_record(
    *,
    engine, operation, ecosystem, typ, step, status, name,
    required, optional, defaults, constraints, frame_fields, flags,
    raw,
) -> dict:
    return {
        "engine": engine,
        "operation": operation,
        "ecosystem": ecosystem,
        "type": typ,
        "step": step,
        "status": status,
        "name": name,
        "required": required,
        "optional": optional,
        "defaults": defaults,
        "constraints": constraints,
        "frameFields": frame_fields,
        "extraFlags": flags,
        "raw": raw,
    }


def combo_key(engine, operation, ecosystem, step, model=None, version=None, provider=None):
    return (engine, operation, ecosystem, step, model, version, provider)


def server_engine_mentions(src: str) -> set[str]:
    found = set()
    # string literals that look like engine ids used in server.py
    for m in re.findall(r'["\']([A-Za-z0-9._-]+)["\']', src):
        found.add(m)
    return found


def write_md(doc: dict, unmatched_catalog: list, extra_openapi: list, gaps: dict) -> str:
    caps = doc["capabilities"]
    notes = doc["notes"]
    by_type = Counter(c["type"] for c in caps)
    by_status = Counter(c["status"] for c in caps)
    by_step = Counter(c.get("step") or "(none)" for c in caps)
    from_oa = sum(1 for c in caps if c.get("required") and not (c.get("raw") or {}).get("unmatched"))
    nonempty_req = sum(1 for c in caps if c.get("required"))
    image_video = [c for c in caps if c["type"] in ("image", "video")]
    iv_req = sum(1 for c in image_video if c.get("required") and not (c.get("raw") or {}).get("unmatched"))

    frame_counter = Counter()
    turbo_n = fast_n = qty_n = dur_n = res_n = 0
    for c in caps:
        for f in c.get("frameFields") or []:
            frame_counter[f] += 1
        ef = c.get("extraFlags") or {}
        if ef.get("turbo") is not None:
            turbo_n += 1
        if ef.get("fast") is not None:
            fast_n += 1
        if ef.get("quantity"):
            qty_n += 1
        if ef.get("duration"):
            dur_n += 1
        if ef.get("resolution"):
            res_n += 1

    notable_frames = ", ".join(f"{k} ({v})" for k, v in frame_counter.most_common(18))

    lines = []
    a = lines.append
    a("# Civitai Studio — capabilities")
    a("")
    a(f"Generated from local `catalog.json` + `docs/_raw/*.openapi.yaml`. Source `{doc['source']}`. Fetched `{doc['fetchedAt']}`.")
    a("")
    a("## Defaults (local studio)")
    a("")
    a("- **Image:** engine `comfy`, ecosystem `krea2` (catalog default service `image/comfy/krea2/turbo/createImage`).")
    a("- **Video:** engine `minimax-h3-comfy`, operation `imageToVideo` (I2V). MiniMax H3 I2V is the user reference-video default (catalog engine id `minimax-h3-comfy`).")
    a("- Mature: workflow body `allowMatureContent: true`; query `hideMatureContent=false`.")
    a("- Submit: `POST /v2/consumer/workflows?whatif=&wait=0` (also `hideMatureContent=`). Recipe invoke is `POST /v2/consumer/recipes/{step}`.")
    a("")
    a("## Counts")
    a("")
    a(f"- Rows total: **{len(caps)}**")
    a(f"- By type: image={by_type.get('image', 0)}, video={by_type.get('video', 0)}, other={by_type.get('other', 0)}")
    a(f"- By status: " + ", ".join(f"{k}={v}" for k, v in by_status.most_common()))
    a(f"- Non-empty `required[]`: {nonempty_req} (image+video with OpenAPI fields: {iv_req}/{len(image_video)})")
    a(f"- OpenAPI-only extras (no catalog row): {len(extra_openapi)}")
    a(f"- Catalog items with no matching schema: {len(unmatched_catalog)}")
    a("")
    a("### By step (top)")
    a("")
    for step, n in by_step.most_common(20):
        a(f"- `{step}`: {n}")
    a("")
    a("## Flags present")
    a("")
    a(f"- `turbo` set (variant or boolean field): {turbo_n}")
    a(f"- `fast` set: {fast_n}")
    a(f"- `quantity` field: {qty_n}")
    a(f"- `duration` field: {dur_n}")
    a(f"- `resolution` field: {res_n}")
    a("")
    a("## Notable frame / reference fields")
    a("")
    a(notable_frames or "(none)")
    a("")
    a("Typical I2V mapping:")
    a("")
    a("- `minimax-h3-comfy` / `imageToVideo`: `firstFrame`, `lastFrame`")
    a("- `minimax-h3-comfy` / `referenceToVideo`: `images`")
    a("- `happyHorse` I2V: `image`")
    a("- `wan` I2V: `startImage` / `endImage` or `images` depending on version")
    a("- `ltx2` / `ltx2.3` / `ltx2.5` FLF: `firstFrame`, `lastFrame`")
    a("- image edit: `images` (krea2 edit maxItems=2)")
    a("")
    a("## Unmatched catalog items")
    a("")
    if unmatched_catalog:
        for u in unmatched_catalog[:40]:
            a(f"- `{u}`")
        if len(unmatched_catalog) > 40:
            a(f"- … {len(unmatched_catalog) - 40} more")
    else:
        a("None.")
    a("")
    a("## OpenAPI leaves not in catalog (sample)")
    a("")
    if extra_openapi:
        for e in extra_openapi[:30]:
            a(f"- `{e}`")
        if len(extra_openapi) > 30:
            a(f"- … {len(extra_openapi) - 30} more")
    else:
        a("None.")
    a("")
    a("## Gaps vs `server.py` (do not edit server here)")
    a("")
    a(gaps.get("md") or "")
    a("")
    a("## Suggested local endpoints")
    a("")
    for line in gaps.get("endpoints") or []:
        a(f"- {line}")
    a("")
    return "\n".join(lines) + "\n"


def analyze_gaps(caps: list, server_src: str, specs: dict) -> dict:
    # Engines hardcoded / mentioned in server.py
    hardcoded_image = {"comfy"}
    hardcoded_video = {"minimax-h3-comfy", "wan", "happyHorse", "hunyuan", "ltx2.5", "ltx2.3"}
    # also ltx2 via apply_frames generic
    mentioned = hardcoded_image | hardcoded_video | {"ltx2"}

    cap_engines = sorted({c["engine"] for c in caps if c.get("engine") and c["type"] in ("image", "video")})
    missing_engines = [e for e in cap_engines if e not in mentioned]

    image_engines = sorted({c["engine"] for c in caps if c["type"] == "image" and c.get("engine")})
    video_engines = sorted({c["engine"] for c in caps if c["type"] == "video" and c.get("engine")})
    image_missing = [e for e in image_engines if e not in hardcoded_image]
    video_missing = [e for e in video_engines if e not in hardcoded_video and e != "ltx2"]

    steps = sorted({c.get("step") for c in caps if c.get("step")})
    implemented_steps = {"imageGen", "videoGen"}  # generic $type from catalog, but UI only image/video
    other_steps = [s for s in steps if s not in implemented_steps]

    # fields
    has_allow = "allowMatureContent" in server_src
    has_whatif = "whatif" in server_src
    has_wait = '"wait"' in server_src or "'wait'" in server_src
    has_hide = "hideMatureContent" in server_src
    has_turbo = "turbo" in server_src
    has_fast = "fast" in server_src
    has_qty = "quantity" in server_src
    has_dur = "duration" in server_src
    has_res = "resolution" in server_src
    has_first = "firstFrame" in server_src
    has_last = "lastFrame" in server_src
    has_start = "startImage" in server_src

    recipe_paths = []
    for name, spec in sorted(specs.items()):
        for p in recipe_paths_of(spec):
            recipe_paths.append(p)
    recipe_paths = sorted(set(recipe_paths))

    md_lines = []
    m = md_lines.append
    m(f"Image engines in capabilities ({len(image_engines)}): " + ", ".join(f"`{e}`" for e in image_engines))
    m("")
    m(f"Video engines in capabilities ({len(video_engines)}): " + ", ".join(f"`{e}`" for e in video_engines))
    m("")
    m("**server.py currently hardcodes** image `comfy` (krea2/turbo/createImage); video `minimax-h3-comfy`, plus frame heuristics for `wan`, `happyHorse`, `hunyuan`, `ltx2.5`/`ltx2.3`.")
    m("")
    m(f"- Image engines with no dedicated builder (fall through to generic parameter copy): {', '.join(f'`{e}`' for e in image_missing) or '(none)'}")
    m(f"- Video engines with no dedicated builder: {', '.join(f'`{e}`' for e in video_missing) or '(none)'}")
    m("")
    m("**Fields / flags:**")
    m("")
    m(f"- Frame fields: server maps `firstFrame`/`lastFrame`/`startImage`/`endImage`/`image`/`images` for a few engines only. Missing per-engine maps for `referenceImages`, `sourceVideo`, `videoUrl`, `keyframes`, `firstFrameImage`, etc.")
    m(f"- `turbo`/`fast`: applied only for `minimax-h3-comfy`. Many other schemas expose `turbo`, `useTurbo`, `fast`, `fastMode`, `useFastWan`, or turbo **models** (`krea2` turbo/raw).")
    m(f"- `quantity` (1–12 clamp), `duration` (1–30 clamp), `resolution`, `aspectRatio` are copied if present but clamps/enums are not schema-aware.")
    m(f"- `allowMatureContent` is set on the workflow body (default true). `hideMatureContent=false` is on the submit query. `whatif` + `wait=0` are implemented for `/api/whatif` and `/api/generate`.")
    m("")
    m("**Recipes not implemented in the UI/server** (catalog `step` other than imageGen/videoGen):")
    m("")
    m(", ".join(f"`{s}`" for s in other_steps[:40]) + ("…" if len(other_steps) > 40 else ""))
    m("")
    m("Upscale / try-on / audio / 3D / training have OpenAPI recipe POSTs but no local `/api/*` handlers beyond the generic workflow submit.")

    endpoints = [
        "`GET /api/capabilities` — serve this `docs/capabilities.json` (no live POST).",
        "`GET /api/catalog` — already present (`GET /v2/services?limit=&offset=`).",
        "`POST /api/generate` → `POST /v2/consumer/workflows?whatif=false&wait=0&hideMatureContent=false`.",
        "`POST /api/whatif` → same with `whatif=true` (already present).",
        "`GET /api/jobs/{id}` → `GET /v2/consumer/workflows/{id}` (already present).",
        "`POST /api/recipes/{step}` → `POST /v2/consumer/recipes/{step}` (imageGen, videoGen, imageUpscaler, tryOnU, polyGen, …) for estimate/`whatif` without wrapping a full workflow.",
        "`GET /v2/consumer/recipes/{step}/openapi.yaml` — already mirrored under `docs/_raw/`.",
        "Blob input: data URLs work in many `images`/`firstFrame` fields; if a dedicated blob API is needed, proxy `GET /v2/consumer/blobs?blobId=` (download) — do not POST generation jobs.",
        "Pass schema `quantity`/`duration`/`resolution` enums from capabilities instead of the current 1–12 / 1–30 clamps.",
    ]
    return {"md": "\n".join(md_lines), "endpoints": endpoints, "image_missing": image_missing, "video_missing": video_missing, "other_steps": other_steps}


def recipe_paths_of(spec: dict) -> list[str]:
    return list((spec.get("paths") or {}).keys())


def record_from_flat(flat: dict, spec: dict, *, engine, operation, ecosystem, step, status, name, raw_extra: dict) -> dict:
    props = flat.get("properties") or {}
    required = list(flat.get("required") or [])
    optional = [k for k in props.keys() if k not in required]
    constraints = compact_constraints(props, spec) if spec else {}
    defaults = defaults_from_props(props, spec) if spec else {}
    flags = extra_flags(props, spec or {}, defaults, constraints, name, flat.get("schemaName"), raw_extra.get("model"))
    ident = ident_from_props(props, spec or {}, {
        "engine": engine, "operation": operation, "ecosystem": ecosystem,
        "model": raw_extra.get("model"), "version": raw_extra.get("version"),
        "provider": raw_extra.get("provider"),
    })
    engine = engine if engine is not None else ident.get("engine")
    operation = operation if operation is not None else ident.get("operation")
    ecosystem = ecosystem if ecosystem is not None else ident.get("ecosystem")
    raw = {
        "id": raw_extra.get("id"),
        "provider": raw_extra.get("provider") or ident.get("provider"),
        "model": raw_extra.get("model") or ident.get("model"),
        "version": raw_extra.get("version") or ident.get("version"),
        "schemaName": flat.get("schemaName"),
    }
    for k, v in raw_extra.items():
        if k not in raw and v is not None:
            raw[k] = v
    return build_record(
        engine=engine,
        operation=operation,
        ecosystem=ecosystem,
        typ=map_type(step),
        step=step,
        status=map_status(status),
        name=name,
        required=required,
        optional=optional,
        defaults=defaults,
        constraints=constraints,
        frame_fields=detect_frame_fields(props.keys()),
        flags=flags,
        raw=raw,
    )


def main() -> None:
    catalog = json.loads(CATALOG.read_text())
    items = catalog.get("items") or []
    specs: dict[str, dict] = {}
    for p in sorted(RAW.glob("*.openapi.yaml")):
        name = p.name.replace(".openapi.yaml", "")
        specs[name] = load_yaml(p)

    fetched_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Precompute OpenAPI leaves per recipe
    leaves_by_step: dict[str, list[dict]] = {}
    for step, spec in specs.items():
        if step == "repeat":
            # RepeatInput only; do not expand the 700+ embedded template schemas
            root = "RepeatInput"
            schemas = (spec.get("components") or {}).get("schemas") or {}
            if root in schemas:
                flat = flatten_named(root, spec)
                ident = ident_from_props(flat.get("properties") or {}, spec, {})
                leaves_by_step[step] = [{
                    "schemaName": root, "trail": [root], "disc": {}, "ident": ident, "flat": flat,
                }]
            continue
        root = find_root_input(spec)
        if not root:
            continue
        leaves_by_step[step] = walk_all_leaves(root, spec)

    capabilities: list[dict] = []
    unmatched_catalog: list[str] = []
    covered_leaves: set[tuple] = set()  # schemaName + step
    covered_combos: set[tuple] = set()  # engine, operation, ecosystem, step (for extras skip)

    for item in items:
        step = item.get("step")
        params = dict(item.get("parameters") or {})
        engine = item.get("engine") if item.get("engine") is not None else params.get("engine")
        operation = item.get("operation") if item.get("operation") is not None else params.get("operation")
        ecosystem = item.get("ecosystem") if item.get("ecosystem") is not None else params.get("ecosystem")
        model = item.get("model") if item.get("model") is not None else params.get("model")
        version = item.get("version") if item.get("version") is not None else params.get("version")
        provider = item.get("provider") if item.get("provider") is not None else params.get("provider")
        spec = specs.get(step) if step else None
        matched = False
        flat = {"properties": {}, "required": [], "schemaName": None}
        trail: list[str] = []
        disc_values: dict = {}
        schema_name = None

        if spec:
            root = find_root_input(spec)
            walk_params = dict(params)
            for k, v in (("engine", engine), ("operation", operation), ("ecosystem", ecosystem),
                         ("model", model), ("version", version), ("provider", provider)):
                if v is not None:
                    walk_params[k] = v
            if root:
                schema_name, flat, trail, disc_values = walk_to_leaf(root, spec, walk_params)
                props = flat.get("properties") or {}
                # Abstract roots (ImageGenInput / VideoGenInput) are not a real engine match.
                abstract_roots = {"ImageGenInput", "VideoGenInput"}
                if schema_name in abstract_roots:
                    matched = False
                elif props or (flat.get("required")):
                    matched = True
            if not matched:
                inline = find_inline_body(spec)
                if inline:
                    matched = True
                    schema_name = "inlineJSON"
                    t = inline.get("type") or "string"
                    flat = {
                        "properties": {
                            "body": {"type": t, "description": "Raw JSON body (no named object fields)."},
                        },
                        "required": ["body"],
                        "schemaName": "inlineJSON",
                    }
                    trail = ["inlineJSON"]

        raw_extra = {
            "id": item.get("id"),
            "provider": provider,
            "model": model,
            "version": version,
            "schemaName": schema_name,
        }
        if not matched:
            raw_extra["unmatched"] = True
            unmatched_catalog.append(item.get("id") or f"{step}:{engine}:{operation}")
            req, opt, defs, cons = fields_from_catalog_params(params)
            rec = build_record(
                engine=engine,
                operation=operation,
                ecosystem=ecosystem,
                typ=map_type(step),
                step=step,
                status=map_status(item.get("status")),
                name=item.get("name"),
                required=req,
                optional=opt,
                defaults=defs,
                constraints=cons,
                frame_fields=detect_frame_fields(list(params.keys()) + list((flat.get("properties") or {}).keys())),
                flags=extra_flags({}, {}, defs, cons, item.get("name"), None, model),
                raw=raw_extra,
            )
        else:
            rec = record_from_flat(
                flat, spec,
                engine=engine, operation=operation, ecosystem=ecosystem,
                step=step, status=item.get("status"), name=item.get("name"),
                raw_extra=raw_extra,
            )
            # If OpenAPI required is empty but catalog has identity params, keep OpenAPI lists
            # (identity fields often live in required already).
            if not rec["required"] and not rec["optional"] and params:
                rec["required"], rec["optional"], rec["defaults"], rec["constraints"] = fields_from_catalog_params(params)
                rec["raw"]["unmatched"] = True
                unmatched_catalog.append(item.get("id") or "")

        capabilities.append(rec)
        covered_leaves.add((schema_name, step))
        covered_combos.add((rec["engine"], rec["operation"], rec["ecosystem"], rec["step"]))

    extra_openapi_labels: list[str] = []
    for step, leaves in leaves_by_step.items():
        spec = specs.get(step)
        for leaf in leaves:
            ident = leaf["ident"]
            schema_name = leaf["schemaName"]
            if (schema_name, step) in covered_leaves:
                continue
            engine = ident.get("engine")
            operation = ident.get("operation")
            ecosystem = ident.get("ecosystem")
            combo = (engine, operation, ecosystem, step)
            if combo in covered_combos:
                continue
            # skip huge/noisy intermediates that have no engine and no operation when the
            # catalog already has a row for this step with null engine (single-recipe steps)
            rec = record_from_flat(
                leaf["flat"], spec,
                engine=engine, operation=operation, ecosystem=ecosystem,
                step=step, status="unknown",
                name=schema_name,
                raw_extra={
                    "id": None,
                    "provider": ident.get("provider"),
                    "model": ident.get("model"),
                    "version": ident.get("version"),
                    "schemaName": schema_name,
                    "openapiOnly": True,
                },
            )
            capabilities.append(rec)
            covered_leaves.add((schema_name, step))
            covered_combos.add(combo)
            extra_openapi_labels.append(f"{step} {engine}/{operation}/{ecosystem} [{schema_name}]")

    # Stable sort: image, video, other; then engine, ecosystem, operation, name
    type_rank = {"image": 0, "video": 1, "other": 2}

    def sort_key(c):
        return (
            type_rank.get(c.get("type"), 9),
            c.get("step") or "",
            c.get("engine") or "",
            c.get("ecosystem") or "",
            c.get("operation") or "",
            (c.get("raw") or {}).get("model") or "",
            (c.get("raw") or {}).get("version") or "",
            c.get("name") or "",
            (c.get("raw") or {}).get("id") or "",
        )

    capabilities.sort(key=sort_key)

    notes = {
        "allowMatureContent": True,
        "hideMatureContent": False,
        "submitEndpoint": "POST /v2/consumer/workflows?whatif=&wait=0",
        "defaults": {
            "imageGen": {"engine": "comfy", "ecosystem": "krea2"},
            "videoGen": {
                "engine": "minimax-h3-comfy",
                "operationHint": "I2V / image-to-video",
                "note": "MiniMax H3 I2V is the user reference-video default (catalog engine id minimax-h3-comfy)",
            },
        },
    }

    doc = {
        "source": "https://orchestration.civitai.com",
        "fetchedAt": fetched_at,
        "notes": notes,
        "capabilities": capabilities,
    }

    server_src = SERVER.read_text() if SERVER.exists() else ""
    gaps = analyze_gaps(capabilities, server_src, specs)

    OUT_JSON.write_text(json.dumps(doc, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    OUT_MD.write_text(write_md(doc, unmatched_catalog, extra_openapi_labels, gaps))

    # Validation
    loaded = json.loads(OUT_JSON.read_text())
    assert isinstance(loaded["capabilities"], list)
    n = len(loaded["capabilities"])
    n_image = sum(1 for c in loaded["capabilities"] if c["type"] == "image")
    n_video = sum(1 for c in loaded["capabilities"] if c["type"] == "video")
    n_other = sum(1 for c in loaded["capabilities"] if c["type"] == "other")
    n_req = sum(1 for c in loaded["capabilities"] if c.get("required"))
    n_req_oa = 0
    for c in loaded["capabilities"]:
        if c["type"] in ("image", "video") and c.get("required") and not (c.get("raw") or {}).get("unmatched"):
            n_req_oa += 1

    print("wrote", OUT_JSON, "bytes", OUT_JSON.stat().st_size)
    print("wrote", OUT_MD, "bytes", OUT_MD.stat().st_size)
    print("rows", n, "image", n_image, "video", n_video, "other", n_other)
    print("nonempty required", n_req, "image+video from OpenAPI", n_req_oa)
    print("unmatched catalog", len(unmatched_catalog))
    print("openapi extras", len(extra_openapi_labels))
    print("unmatched ids:", unmatched_catalog)
    print("extras sample:", extra_openapi_labels[:25])

    def show(pred, label):
        hits = [c for c in loaded["capabilities"] if pred(c)]
        print(f"\n=== {label} n={len(hits)} ===")
        for c in hits[:6]:
            print(json.dumps({
                "engine": c["engine"], "operation": c["operation"], "ecosystem": c["ecosystem"],
                "name": c["name"], "status": c["status"],
                "required": c["required"], "optional": c["optional"],
                "defaults": c["defaults"], "frameFields": c["frameFields"],
                "extraFlags": c["extraFlags"], "raw": c["raw"],
            }, ensure_ascii=False, indent=2)[:4000])

    show(lambda c: c.get("engine") == "comfy" and c.get("ecosystem") == "krea2" and c.get("operation") == "createImage", "comfy krea2 createImage")
    show(lambda c: c.get("engine") == "comfy" and c.get("ecosystem") == "krea2" and c.get("operation") == "editImage", "comfy krea2 editImage")
    show(lambda c: c.get("engine") == "minimax-h3-comfy" and c.get("operation") in ("imageToVideo", "image-to-video"), "minimax-h3-comfy I2V")


if __name__ == "__main__":
    main()
