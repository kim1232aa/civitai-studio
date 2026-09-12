"""Cross-house LoRA search. Official indexes only — no invented adapters."""
from __future__ import annotations

HF_SHAPED = ("huggingface", "fal", "nano-gpt")
MS_SHAPED = ("modelscope-ai", "modelscope-cn")

_ALIASES = {
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


def alias_backend(bid: str) -> str:
    bid = (bid or "civitai").strip()
    return _ALIASES.get(bid, bid)


def lora_search_houses(current: str) -> list:
    """Current house first, then other official LoRA indexes.

    Fal / Nano / HF all search Hub ``filter=lora`` — do not query that pool three times.
    """
    cur = alias_backend(current or "civitai")
    houses = [cur]
    if cur != "civitai":
        houses.append("civitai")
    if cur not in HF_SHAPED:
        houses.append("huggingface")
    if cur not in MS_SHAPED:
        houses.append("modelscope-ai")
    return houses


def stamp_lora_items(items, backend: str) -> list:
    out = []
    for it in items or []:
        if not isinstance(it, dict):
            continue
        row = dict(it)
        row.setdefault("source", row.get("source") or backend)
        row.setdefault("backend", backend)
        out.append(row)
    return out


def search_loras_one(backend: str, q: str, nsfw: bool = True, types: str = "LORA"):
    import providers

    backend = alias_backend(backend or "civitai")
    prov = providers.get(backend) or providers.get("civitai")
    if prov is None:
        return 404, {"items": [], "backend": backend, "error": "unknown backend"}
    try:
        if hasattr(prov, "search_loras"):
            code, data = prov.search_loras(q, nsfw=nsfw)
        else:
            return 200, {
                "items": [],
                "backend": backend,
                "note": f"{getattr(prov, 'label', backend)} 没有 LoRA 搜索",
            }
    except Exception as exc:
        return 200, {"items": [], "backend": backend, "error": str(exc)}
    if not isinstance(data, dict):
        return code, {"items": [], "backend": backend}
    items = stamp_lora_items(data.get("items") or [], backend)
    out = dict(data)
    out["items"] = items
    out.setdefault("backend", backend)
    out.setdefault("nsfw", nsfw)
    return code, out


def search_loras_cross(q: str, nsfw: bool = True, current: str = "civitai", types: str = "LORA"):
    from concurrent.futures import ThreadPoolExecutor, as_completed

    current = alias_backend(current or "civitai")
    houses = lora_search_houses(current)
    items = []
    seen = set()
    errors = []
    with ThreadPoolExecutor(max_workers=4) as pool:
        futs = {pool.submit(search_loras_one, h, q, nsfw, types): h for h in houses}
        for fut in as_completed(futs):
            h = futs[fut]
            try:
                _code, data = fut.result()
            except Exception as exc:
                errors.append({"backend": h, "error": str(exc)})
                continue
            if not isinstance(data, dict):
                continue
            if data.get("error"):
                errors.append({"backend": h, "error": data.get("error")})
            for it in data.get("items") or []:
                if not isinstance(it, dict):
                    continue
                vers = it.get("versions") or []
                vid = ""
                if vers and isinstance(vers[0], dict):
                    vid = vers[0].get("id") or ""
                key = (
                    str(it.get("backend") or h),
                    str(it.get("path") or it.get("id") or ""),
                    str(vid or ""),
                )
                if key in seen:
                    continue
                seen.add(key)
                items.append(it)

    def _sk(it):
        src = str(it.get("backend") or it.get("source") or "")
        return (0 if src == current else 1, src, str(it.get("name") or ""))

    items.sort(key=_sk)
    return 200, {
        "items": items[:16],
        "nsfw": nsfw,
        "backend": current,
        "cross": True,
        "houses": houses,
        "errors": errors,
    }
