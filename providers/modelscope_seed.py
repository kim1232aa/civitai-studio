"""ModelScope official seed outbound (AI + CN).

https://www.modelscope.cn/docs/model-service/API-Inference/intro
  seed: int, range [0, 2^31-1]

Studio uses -1 / 'random' as "omit and let upstream pick". Sending -1 is
outside the official table. Do not wrap/modulo. Values < -1 or > int32
stay rejected by the adapter.
"""
from __future__ import annotations

from typing import Any

INT32_MAX = 2147483647


def official_seed_outbound(raw: Any) -> int | None:
    """None = omit key. int in [0, int32] = send. Else raise."""
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
    if value < 0 or value > INT32_MAX:
        raise ValueError(
            f"魔搭 seed 官方区间 [0,{INT32_MAX}]，收到 {value}；-1=省略不发，拒绝 wrap"
        )
    return value


def strip_unofficial_seed(body: Any) -> Any:
    if not isinstance(body, dict):
        return body
    if "seed" not in body:
        return body
    raw = body.get("seed")
    if raw in (-1, "-1"):
        out = dict(body)
        out.pop("seed", None)
        return out
    return body


def install_modelscope_seed() -> None:
    """Wrap modelscope._image_body so -1 is omitted. Idempotent. AI+CN."""
    from . import modelscope as ms

    if getattr(ms, "_o57_seed_omit", False):
        return
    orig = getattr(ms, "_image_body", None)
    if not callable(orig):
        return

    def _image_body(payload, mid, backend):
        body = orig(payload, mid, backend)
        return strip_unofficial_seed(body)

    ms._image_body = _image_body
    ms._o57_seed_omit = True
