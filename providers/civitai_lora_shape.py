"""Official Civitai orchestration LoRA payload shape by recipe.

Sources (developer.civitai.com/orchestration/recipes, 2026-09-11):
- Flux 2 Klein: loras is a map { airUrn: strength }
- Flux 2 Dev: loras is an array of { air, strength }
- Flux 2 flex/pro/max: no LoRA
- WAN image (v2.2 / v2.2-5b / v2.5 / v2.7): loras[] = [{ air, strength }]
- LTX2 video: loras is a map { airUrn: strength }
- Fal-Krea recipe (engine=fal + krea): no LoRA / negative / free WH
- Comfy-krea2 (engine=comfy, ecosystem=krea2): AIR map — do NOT switch to array

Adapter lora_map historically always emitted a dict. Hunyuan already
converted to a list. This module applies the official split without
converting the whole house to arrays.
"""
from __future__ import annotations

from typing import Any

_ARRAY_MODELS = {"dev", "flux2-dev", "flux2dev"}
_NO_LORA_FLUX2 = {"flex", "pro", "max"}


def _norm(v: Any) -> str:
    return str(v or "").strip().lower()


def _as_map(loras: Any) -> dict[str, float]:
    """Pack known strengths only. null/missing strength → omit (never invent 1.0)."""
    out: dict[str, float] = {}
    if not loras:
        return out
    if isinstance(loras, dict):
        for air, strength in loras.items():
            key = str(air or "").strip()
            if not key:
                continue
            if strength is None:
                continue
            try:
                out[key] = float(strength)
            except (TypeError, ValueError) as e:
                raise ValueError(f"LoRA strength 无法解析（不发明 1.0）: {air!r}={strength!r}") from e
        return out
    if isinstance(loras, list):
        for row in loras:
            if not isinstance(row, dict):
                continue
            air = str(row.get("air") or "").strip()
            if not air:
                continue
            if "strength" in row:
                raw = row.get("strength")
            elif "scale" in row:
                raw = row.get("scale")
            else:
                continue  # omit — do not invent 1.0
            if raw is None:
                continue
            try:
                out[air] = float(raw)
            except (TypeError, ValueError) as e:
                raise ValueError(f"LoRA strength 无法解析（不发明 1.0）: {air!r}={raw!r}") from e
    return out


def _as_array(mapped: dict[str, float]) -> list[dict[str, Any]]:
    return [{"air": air, "strength": strength} for air, strength in mapped.items()]


def lora_shape_for_recipe(
    engine: str | None = None,
    model: str | None = None,
    ecosystem: str | None = None,
    operation: str | None = None,
) -> str:
    """Return 'map' | 'array' | 'none'. Unknown recipes stay 'map' (Comfy default)."""
    eng = _norm(engine)
    model_s = _norm(model)
    eco = _norm(ecosystem)
    blob = " ".join((eng, model_s, eco, _norm(operation)))

    if eng == "fal" and "krea" in blob:
        return "none"
    if eng == "flux2" and model_s in _NO_LORA_FLUX2:
        return "none"
    if eng == "flux2" and model_s in _ARRAY_MODELS:
        return "array"
    if "hunyuan" in blob:
        return "array"
    if eng.startswith("wan") or eco.startswith("wan") or model_s.startswith("v2."):
        # WAN image recipe versions are v2.2 / v2.5 / v2.7; video WAN also uses array-or-map
        # Official WAN *image* page is array. Video WAN not rewritten here unless engine=wan.
        if eng.startswith("wan") or "image" in blob or model_s.startswith("v2."):
            return "array"
    return "map"


def official_lora_payload(
    loras: Any,
    engine: str | None = None,
    model: str | None = None,
    ecosystem: str | None = None,
    operation: str | None = None,
) -> dict[str, float] | list[dict[str, Any]] | None:
    """Reshape adapter loras to the official recipe. Empty → None (omit key).

    Fal-Krea / Flux2 flex|pro|max with a non-empty list raise — no silent drop.
    """
    mapped = _as_map(loras)
    shape = lora_shape_for_recipe(engine, model, ecosystem, operation)
    if not mapped:
        return None
    if shape == "none":
        label = engine or model or ecosystem or "current recipe"
        raise ValueError(
            f"{label} 官方 recipe 不接 LoRA，请换 Comfy-krea2 / Flux2 Klein / Dev，不会静默丢掉"
        )
    if shape == "array":
        return _as_array(mapped)
    return mapped


def reshape_workflow_loras(wf: dict | None) -> dict:
    """Post-process orchestration workflow steps[n].input.loras."""
    if not isinstance(wf, dict):
        return {}
    out = dict(wf)
    steps = out.get("steps")
    if not isinstance(steps, list):
        return out
    new_steps = []
    for st in steps:
        if not isinstance(st, dict):
            new_steps.append(st)
            continue
        step = dict(st)
        inp = step.get("input")
        if isinstance(inp, dict) and "loras" in inp:
            inp = dict(inp)
            shaped = official_lora_payload(
                inp.get("loras"),
                engine=inp.get("engine"),
                model=inp.get("model"),
                ecosystem=inp.get("ecosystem"),
                operation=inp.get("operation"),
            )
            if shaped is None:
                inp.pop("loras", None)
            else:
                inp["loras"] = shaped
            step["input"] = inp
        new_steps.append(step)
    out["steps"] = new_steps
    return out


def install_civitai_lora_shape() -> None:
    """Wrap civitai.build_workflow so outbound LoRA matches official recipes."""
    from . import civitai as civitai_mod

    if getattr(civitai_mod, "_o57_lora_shape", False):
        return
    if not hasattr(civitai_mod, "build_workflow"):
        return
    orig = civitai_mod.build_workflow

    def build_workflow(*args, **kwargs):
        wf = orig(*args, **kwargs)
        return reshape_workflow_loras(wf) if isinstance(wf, dict) else wf

    civitai_mod.build_workflow = build_workflow
    civitai_mod._o57_lora_shape = True
