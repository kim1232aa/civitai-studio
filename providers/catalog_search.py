"""Cross-house catalog search for smart match. Official provider.catalog only."""
from __future__ import annotations

from providers.lora_search import alias_backend

MODEL_HOUSES = (
    "civitai",
    "fal",
    "nano-gpt",
    "huggingface",
    "modelscope-ai",
    "modelscope-cn",
)

OP_QUERY = {
    "t2i": "text-to-image",
    "i2i": "edit",
    "i2v": "image-to-video",
    "t2v": "text-to-video",
    "upscale": "upscale",
    "inpaint": "inpaint",
}


def model_search_houses(current: str) -> list:
    cur = alias_backend(current or "civitai")
    houses = [cur]
    for h in MODEL_HOUSES:
        if h not in houses:
            houses.append(h)
    return houses


def stamp_model_items(items, backend: str) -> list:
    out = []
    for it in items or []:
        if not isinstance(it, dict):
            continue
        row = dict(it)
        row.setdefault("source", row.get("source") or backend)
        row.setdefault("backend", backend)
        if not row.get("id") and row.get("name"):
            row["id"] = row["name"]
        out.append(row)
    return out


def search_models_one(backend: str, q: str, category: str = "", op: str = ""):
    import providers

    backend = alias_backend(backend or "civitai")
    prov = providers.get(backend)
    if prov is None or not hasattr(prov, "catalog"):
        return 200, {"items": [], "backend": backend, "error": "unknown backend"}
    query = (q or "").strip() or OP_QUERY.get(op or "", "")
    cat = category or ("video" if op in ("i2v", "t2v") else "image")
    try:
        body = prov.catalog(query, cat, "")
    except TypeError:
        try:
            body = prov.catalog(query, cat, "", page=1, pageSize=24)
        except Exception as exc:
            return 200, {"items": [], "backend": backend, "error": str(exc)}
    except Exception as exc:
        return 200, {"items": [], "backend": backend, "error": str(exc)}
    if not isinstance(body, dict):
        return 200, {"items": [], "backend": backend}
    items = stamp_model_items(body.get("items") or [], backend)
    out = dict(body)
    out["items"] = items[:24]
    out.setdefault("backend", backend)
    out["q"] = query
    out["op"] = op or ""
    return 200, out


def search_models_cross(q: str, current: str = "civitai", category: str = "", op: str = ""):
    from concurrent.futures import ThreadPoolExecutor, as_completed

    current = alias_backend(current or "civitai")
    houses = model_search_houses(current)
    items = []
    seen = set()
    errors = []
    with ThreadPoolExecutor(max_workers=6) as pool:
        futs = {pool.submit(search_models_one, h, q, category, op): h for h in houses}
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
                key = (str(it.get("backend") or h), str(it.get("id") or it.get("name") or ""))
                if key in seen or not key[1]:
                    continue
                seen.add(key)
                items.append(it)

    def _sk(it):
        src = str(it.get("backend") or it.get("source") or "")
        return (0 if src == current else 1, src, str(it.get("name") or it.get("id") or ""))

    items.sort(key=_sk)
    return 200, {
        "items": items[:32],
        "backend": current,
        "cross": True,
        "houses": houses,
        "op": op or "",
        "q": q or "",
        "errors": errors,
    }
