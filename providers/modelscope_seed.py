"""ModelScope official seed outbound (AI + CN).

https://www.modelscope.cn/docs/model-service/API-Inference/intro
  seed: int, range [0, 2^31-1]

Studio uses -1 / 'random' as "omit and let upstream pick". Sending -1 is
outside the official table. Do not wrap/modulo.

o149: over-int32 (>2147483647) is also omitted (official Magao omit — never
wrap to a fake in-range value, never rewrite UI to silent -1). Values < -1
still reject.
"""
from __future__ import annotations

from typing import Any

INT32_MAX = 2147483647


def official_seed_outbound(raw: Any) -> int | None:
    """None = omit key. int in [0, int32] = send. Else raise (invalid < -1)."""
    if raw in (None, "", "random", -1, "-1"):
        return None
    try:
        if isinstance(raw, bool):
            raise ValueError()
        value = int(raw)
        if not isinstance(raw, str) and value != raw:
            raise ValueError()
    except (TypeError, ValueError, OverflowError):
        raise ValueError(f"魔搭 seed 必须是整数 [0,{INT32_MAX}]，-1/空=随机省略；收到 {raw!r}，拒绝静默改值") from None
    if value < -1:
        raise ValueError(
            f"魔搭 seed 官方区间 [0,{INT32_MAX}]，收到 {value}；-1=省略不发，拒绝 wrap"
        )
    if value < 0 or value > INT32_MAX:
        # o149: over-int32 (and stray negatives other than -1) → omit, never wrap
        return None
    return value


def strip_unofficial_seed(body: Any) -> Any:
    """Drop seed when -1 or over int32 (omit). Leave in-range ints alone."""
    if not isinstance(body, dict):
        return body
    if "seed" not in body:
        return body
    raw = body.get("seed")
    if raw in (-1, "-1"):
        out = dict(body)
        out.pop("seed", None)
        return out
    try:
        if isinstance(raw, bool):
            return body
        value = int(raw)
    except (TypeError, ValueError, OverflowError):
        return body
    if value < 0 or value > INT32_MAX:
        out = dict(body)
        out.pop("seed", None)
        return out
    return body


def install_modelscope_seed() -> None:
    """Wrap modelscope._image_body so -1 / over-int32 are omitted. Idempotent. AI+CN."""
    from . import modelscope as ms

    if getattr(ms, "_o57_seed_omit", False):
        return
    orig = getattr(ms, "_image_body", None)
    if not callable(orig):
        return

    def _image_body(payload, mid, backend, *args, **kwargs):
        # o149: pre-normalize seed so orig _clamp_seed never raises on over-int32 —
        # official Magao omit (do not wrap). Keep real seed in UI; outbound drops key.
        pl = payload
        if isinstance(payload, dict) and "seed" in payload:
            raw = payload.get("seed")
            try:
                out = official_seed_outbound(raw)
            except ValueError:
                raise
            else:
                if out is None and raw not in (None, ""):
                    pl = dict(payload)
                    pl.pop("seed", None)
                elif out is not None:
                    pl = dict(payload)
                    pl["seed"] = out
        body = orig(pl, mid, backend, *args, **kwargs)
        return strip_unofficial_seed(body)

    ms._image_body = _image_body
    ms._o57_seed_omit = True
