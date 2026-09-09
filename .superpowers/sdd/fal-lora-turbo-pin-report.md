# v0821o2-fal-turbo-pin report

**Stamp:** `v0821o2-fal-turbo-pin`  
**STORE:** `nl-storyboard-v0821o2` (OLDS keeps `nl-storyboard-v0821o`)  
**Branch:** `feat/cloud-nodes-poc`  
**Date:** 2026-09-08 (Asia/Shanghai)

## Failure (evidence)

- UI: Composer `#service` showed **「默认模型」** after Fal LoRA fixture mount.
- Outbound job: `fal|fal-ai/flux-lora|01a07f7a-1476-73a0-88a1-e98fb18a728b`
- LoRA path@0.8 OK; **endpoint wrong** (`fal-ai/flux-lora` ≠ `fal-ai/z-image/turbo/lora`).

## Root cause

1. `mountFalLoraFixture()` set `#service` to `fal-ai/z-image/turbo/lora`.
2. Boot `loadComfyDefaults().then(loadCatalog)` **wiped** `#service` back to empty 「默认模型」 (no `_pendingService` / no preserve).
3. `buildGraph` empty-service fallback → `FAL_T2I_DEFAULT` = `fal-ai/flux/schnell`.
4. Server `fal_lora_sibling(flux/schnell)` with `loras[]` → **`fal-ai/flux-lora`**.

Not a path/scale bug; pure **serviceId drift** empty → schnell → sibling flux-lora.

## Fix

| Area | Change |
|------|--------|
| Fixture | Literal `serviceId: "fal-ai/z-image/turbo/lora"` (+ `serviceName`) |
| Mount | Sets `_pinFalLoraService` / `_pendingService`; `ensureFalLoraServiceSelected()` |
| Boot | Fixture mounts **after** first `loadCatalog` (no race wipe) |
| `loadCatalog` | Remembers `prevService`; restores pin; injects turbo/lora option with **Z-Image Turbo LoRA · id** label |
| `buildGraph` | LoRAs present → pin `FAL_LORA_PREF_SERVICE` (never empty→schnell) |
| `runShotStep` | After pack loras: `payload.serviceId = pinFalLoraServiceId(...)` — blocks flux-lora / schnell drift |
| Sibling | Only explicit `turbo` → `turbo/lora`; **never** fuzzy to flux-lora for this path |

## Tests

- `scripts/test_storyboard_graph.py` → **45 / 45**
- Extended knife + new `test_v0821o2_fal_turbo_pin`: fixture serviceId is turbo/lora, not flux-lora; pin helpers; catalog preserve; visible label; sim empty/schnell/flux-lora → turbo/lora.
- Unrelated pre-existing fails elsewhere (`test_fal_fields`, `test_p0_wiring` cloud-nodes.html, etc.) unchanged.

## Acceptance

- After mount: `#service.value === "fal-ai/z-image/turbo/lora"` (visible label, not 「默认模型」, not flux-lora).
- Generate outbound serviceId/endpoint stays `fal-ai/z-image/turbo/lora`.
- Did **not** curl `/api/generate`; did **not** expand other providers.
