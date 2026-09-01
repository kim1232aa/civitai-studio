from __future__ import annotations

PROVIDERS = {}
ORDER = []


def register(p):
    PROVIDERS[p.id] = p
    if p.id not in ORDER:
        ORDER.append(p.id)


def get(pid: str):
    return PROVIDERS.get(pid)


def all_providers():
    return [PROVIDERS[i] for i in ORDER if i in PROVIDERS]


def resolve_from_payload(payload: dict):
    payload = payload or {}
    bid = (payload.get("backend") or "").strip()
    aliases = {"hf": "huggingface", "ms": "modelscope-ai", "modelscope": "modelscope-ai", "魔搭": "modelscope-ai", "魔搭ai": "modelscope-ai", "魔搭cn": "modelscope-cn", "nano": "nano-gpt", "nanogpt": "nano-gpt", "nano_gpt": "nano-gpt"}
    bid = aliases.get(bid, bid)
    if bid in PROVIDERS:
        return PROVIDERS[bid]
    sid = payload.get("serviceId") or ""
    for p in all_providers():
        if p.owns_service(sid):
            return p
    return PROVIDERS.get("civitai")


def resolve_from_job(job_id: str):
    from .http import parse_job_id
    pid, _ = parse_job_id(job_id or "")
    aliases = {"hf": "huggingface", "ms": "modelscope-ai", "modelscope": "modelscope-ai", "nano": "nano-gpt", "nanogpt": "nano-gpt"}
    pid = aliases.get(pid, pid)
    if pid in PROVIDERS:
        return PROVIDERS[pid]
    for p in all_providers():
        if p.owns_job(job_id or ""):
            return p
    return PROVIDERS.get("civitai")


def list_public():
    return [
        {"id": p.id, "label": p.label, "hasKey": p.has_key(), "categories": p.categories()}
        for p in all_providers()
    ]


def load():
    from . import civitai as _civitai  # noqa: F401
    from . import fal as _fal  # noqa: F401
    from . import huggingface as _hf  # noqa: F401
    from . import modelscope as _ms  # noqa: F401
    from . import nanogpt as _nano  # noqa: F401


def _boot_ui_patch():
    """Upgrade v0737 Night Lab HTML even if started via python3 server.py."""
    try:
        import static_patch
        from pathlib import Path
        target = Path(__file__).resolve().parent.parent / "static" / "index.html"
        raw = target.read_text(encoding="utf-8")
        if "v0749" in raw or "v0748" in raw or "v0747" in raw or "v0746" in raw:
            return
        out = static_patch.patch_index(raw)
        if out != raw:
            target.write_text(out, encoding="utf-8")
            print("[web] patched static/index.html to v0739", flush=True)
    except Exception as e:
        print("[web] static_patch skip", e, flush=True)


load()
_boot_ui_patch()
