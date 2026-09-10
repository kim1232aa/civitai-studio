# o36 checkpoint AIR must not enter loras[] Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: executing-plans. Steps use checkbox (`- [x]`) syntax.

**Goal:** Stop Civitai page↑ 400 `导入 strength 为空：urn:air:flux1:checkpoint:…` caused by checkpoint AIR appearing as a second `loras[]` row with null strength.

**Evidence (api 2026-09-10):**
- o35 import + clean `build_workflow` Pass: `diffuserModel=flux1:checkpoint:…@1983609`, one LoRA `@823089@0.7`, no companions.
- page↑ Fail: `nLoras=2`, error names the **checkpoint** AIR as empty-strength lora.
- Import API for `28533250` returns **1** lora only — pollution is UI/`state.loras` (or pack) before POST.

**Architecture:** Base-model AIR belongs on `diffusionModel` → outbound `diffuserModel`. LoRA chips may only hold LoRA/LyCORIS/etc AIRs (`:lora:` / `:lycoris:` / …). Filter non-LoRA AIRs on import apply + pack outbound; never invent strength for them.

**Tech Stack:** `static/storyboard.js` (+ contract/UI test if present), stamp `v0821o36-checkpoint-not-lora`

---

### Task 1: Failing test / repro

- [x] Unit/DOM or node test: packing/applying loras that include `{air: urn:air:flux1:checkpoint:…, strength: null}` plus real LoRA → outbound civitai `loras` has **only** the real LoRA; checkpoint stays on `diffusionModel` only.
- [x] Prefer also assert applyImport does not leave checkpoint chips when `j.diffusionModel` equals a chip air.

### Task 2: Fix

- [x] Helper `isLoraAir(air)` — true only for LoRA-family resource types in AIR (`:lora:`, `:lycoris:`, `:lora|…` per existing `_is_lora` / UI norms). **False** for `:checkpoint:`, `:diffusionmodel:`, `:diffuser:`, bare checkpoints.
- [x] `applyImport`: when mapping `j.loras`, drop rows whose air is non-LoRA (especially if equal to `j.diffusionModel`).
- [x] `packLorasForPayload` (civitai): skip non-LoRA airs; if any skipped, `setMsg` warn honesty (count), do not invent strength.
- [x] Hunt/remove any path that `addLora`s `shot.diffusionModel`.
- [x] Stamp `v0821o36-checkpoint-not-lora`; push feat; report hash.
- [x] No curl generate acceptance; no companion invent; closed-loop 0.

**Done when:** tip hash; tests green; hand back for page↑ `28533250`.
