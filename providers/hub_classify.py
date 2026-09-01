"""Shared Hub upscale classifier for ModelScope + Hugging Face catalog rows.

Widen carefully: Nomos/4x family upscalers must become category=upscale, but
plain t2i (Z-Image-Turbo, flux, etc.) must stay image. Bare ``4x`` alone is
not enough — require known upscale family tokens or explicit upscale/onnx.
"""
from __future__ import annotations

import re

# Explicit upscale tokens (existing + pipeline/task "upscal*")
_UPSCALE_EXPLICIT = re.compile(
    r"onnx|upscal|apisr|realesr|esrgan|super.?res|generator-onnx",
    re.I,
)

# Scale factor glued to known upscaler family (Nomos, APISR, ESRGAN, …)
_FAMILY = (
    r"nomos|esrgan|apisr|realesr(?:gan)?|cugan|ultrasharp|remacri|"
    r"swinir|hat|dat|span|animesharp|animevig|schat|compact|"
    r"latent.?upscaler|lds?r|upscaler?"
)
_SCALE_FAMILY = re.compile(rf"\d+x[_-]?(?:{_FAMILY})", re.I)

# Compact Nomos ids: nomos8k, nomos4, 4xnomos, …
_NOMOS = re.compile(r"\bnomos\d|nomos8k|4xnomos|8xnomos|\d+x[_-]?nomos", re.I)

# ``4x`` within ~20 chars of a family token (covers 4x-Foo-Nomos style)
_SCALE_NEAR = re.compile(
    rf"\d+x.{{0,20}}(?:{_FAMILY})|(?:{_FAMILY}).{{0,20}}\d+x",
    re.I,
)

# Back-compat alias used by older imports / tests that poke at the regex
_UPSCALE_RE = re.compile(
    rf"(?:onnx|upscal|apisr|realesr|esrgan|super.?res|generator-onnx|"
    rf"\d+x[_-]?(?:{_FAMILY})|\bnomos\d|nomos8k|4xnomos|8xnomos)",
    re.I,
)


def blob_is_upscale(blob: str) -> bool:
    s = blob or ""
    if not s.strip():
        return False
    if _UPSCALE_EXPLICIT.search(s):
        return True
    if _NOMOS.search(s):
        return True
    if _SCALE_FAMILY.search(s):
        return True
    if _SCALE_NEAR.search(s):
        return True
    return False


def hub_upscale_blob(it) -> bool:
    """True when Hub id/name/task/tags look like an upscaler (not Z-Image-Turbo)."""
    if not isinstance(it, dict):
        return False
    parts = [
        it.get("id") or "",
        it.get("name") or "",
        it.get("chinese_name") or "",
        it.get("task") or "",
        it.get("hubTask") or "",
        it.get("pipelineTag") or "",
        it.get("pipeline_tag") or "",
        " ".join(str(t) for t in (it.get("tags") or []) if t),
    ]
    tasks = it.get("tasks") or it.get("Tasks") or []
    if isinstance(tasks, str):
        parts.append(tasks)
    elif isinstance(tasks, (list, tuple)):
        parts.append(" ".join(str(t) for t in tasks))
    return blob_is_upscale(" ".join(parts))


def apply_upscale_category(row: dict) -> dict:
    """Force category=upscale when blob matches; keep Z-Image / normal t2i as image."""
    if not isinstance(row, dict):
        return row
    if hub_upscale_blob(row) and (row.get("category") or "image") == "image":
        row = dict(row)
        row["category"] = "upscale"
        row["task"] = "upscale"
        tags = list(row.get("tags") or [])
        if "upscale" not in tags:
            tags = ["upscale"] + tags
        row["tags"] = tags
        row.pop("needsSource", None)
    return row
