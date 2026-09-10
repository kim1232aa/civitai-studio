# o35 flux1 diffuser AIR normalize Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: executing-plans. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Fix instant Civitai flux1 job fail for sample `28533250` by sending official-shaped `diffuserModel` AIR — no invented companion VAE/CLIP/T5.

**Evidence:**
- Job `12100372-20260910124330942`: outbound fields Pass; step failed instantly; blob `available=false`; full buzz refund.
- Studio outbound had `diffuserModel=urn:air:flux:diffusionmodel:civitai:1752722@1983609` (from `_air_from_ids`).
- Civitai REST `GET /api/v1/model-versions/1983609` returns `air: urn:air:flux1:checkpoint:civitai:1752722@1983609`.
- Official recipe example uses `urn:air:flux1:diffuser:civitai:618692@691639` (a *different* resource — **not** a license to rewrite site `checkpoint` → `diffuser`).
- Green-Sky schnell companions are **upstream defaults** — Studio must **not** invent/fill them (api 2026-09-10).

**Architecture (api formal 2026-09-10):**
1. Import/outbound prefer model-versions **`air` verbatim** (sample → `urn:air:flux1:checkpoint:civitai:1752722@1983609`).
2. FORBIDDEN: `_air_from_ids` hand-rolling `flux:diffusionmodel`.
3. `_ecosystem_from_blob`: recognize `flux.1` / `flux1` → `flux1` first, then bare `flux`.
4. Field name stays `diffuserModel`; **value** = official air (`checkpoint` verbatim is OK).
5. FORBIDDEN: unilaterally rewrite site `checkpoint` into `diffuser`.
6. Never invent companion AIRs. Never invent new model/version ids.
7. Defensive outbound only: known-broken `urn:air:flux:diffusionmodel:civitai:<mid>@<ver>` → `urn:air:flux1:checkpoint:civitai:<mid>@<ver>` (same ids). Official `flux1:diffuser` passes through.

**Tech Stack:** `providers/civitai.py`, contract tests, stamp `v0821o35-flux1-diffuser-air`

---

### Task 1: Failing tests

- [x] `_air_from_ids` / import path for Flux.1 D checkpoint must not emit `urn:air:flux:diffusionmodel:…` when REST air is available — prefer REST air; mint `flux1:checkpoint` only as fallback.
- [x] `build_workflow` on `image/sdcpp/flux1/createImage` with REST `urn:air:flux1:checkpoint:civitai:1752722@1983609` → outbound `diffuserModel` **same** (verbatim).
- [x] Legacy `urn:air:flux:diffusionmodel:civitai:1752722@1983609` → `flux1:checkpoint` (same mid@version) — **not** `flux1:diffuser`.
- [x] Already-correct `flux1:diffuser:…` / `flux1:checkpoint:…` pass through.
- [x] Does **not** inject vaeModel/clipLModel/t5XXLModel.
- [x] Non-flux1 services unchanged.
- [x] `_ecosystem_from_blob` flux.1/flux1 → flux1 before bare flux.

### Task 2: Implement + tip

- [x] Import: when model-versions JSON has `air`, use it for checkpoint_air (don't overwrite with broken `_air_from_ids` flux:diffusionmodel).
- [x] Outbound: field `diffuserModel`; value = official air; defensive legacy diffusionmodel→checkpoint only; never checkpoint→diffuser.
- [x] Stamp `v0821o35-flux1-diffuser-air`; push `feat/cloud-nodes-poc`.
- [ ] Hand back for page↑ `28533250` (no curl generate as acceptance). closed-loop stays 0 until writeback evidence.

**Done when:** tests green; tip hash reported; import/outbound show REST `flux1:checkpoint` for sample 1752722@1983609 (NOT remapped to diffuser).
