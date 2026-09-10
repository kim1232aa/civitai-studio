# o34 Flux import match_service Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: executing-plans. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Import of Flux AIImageStudio posts must pin `image/sdcpp/flux1/createImage` (not `zImage/turbo`), so page↑ does not 400 on `diffusionModel`.

**Architecture:** `match_service` currently scores engine+operation even when ecosystem mismatches; `available` (+2) lets zImage beat `flux1` (`unknown`). Import maps blob eco `flux` but catalog uses `flux1`. Fix: (1) catalog alias flux→flux1 on import; (2) when ecosystem is requested, require ecosystem match (or score it high enough that mismatch cannot win); (3) regression test for sample 28533250-shaped payload.

**Tech Stack:** Python `providers/civitai.py`, `scripts/test_civitai_parameter_contract.py`, stamp bump `v0821o34-…`

---

### Task 1: Failing tests

**Files:**
- Modify: `scripts/test_civitai_parameter_contract.py`

- [ ] Test: `match_service(engine=sdcpp, operation=createImage, ecosystem=flux1)` returns id ending `flux1/createImage` (not zImage).
- [ ] Test: import-shaped `build_workflow` with `serviceId=image/sdcpp/flux1/createImage` + `diffusionModel` flux AIR maps to `model` AIR, no `diffusionModel` leak.
- [ ] Test: helper or import path maps eco label `flux` → catalog `flux1` (or match accepts both).
- [ ] Run tests — expect FAIL before fix.

### Task 2: Fix match + import eco

**Files:**
- Modify: `providers/civitai.py` (`match_service`, import eco branch ~1559)

- [ ] When `ecosystem` arg is set: only consider items whose `ecosystem` matches (after alias map: `flux`↔`flux1`). Do **not** let available-but-wrong-eco win.
- [ ] Import branch: use `flux1` (catalog) when `_ecosystem_from_blob` returns `flux`.
- [ ] Keep honest 400 if UI sends wrong serviceId + diffusionModel (no silent drop).
- [ ] Run contract tests — PASS.
- [ ] Bump visible stamp to `v0821o34-flux-import-match` (or similar).
- [ ] Commit + push `feat/cloud-nodes-poc`.

### Task 3: Verify import live

- [ ] Restart `:8765`; `GET /api/import?q=28533250` → `serviceId=image/sdcpp/flux1/createImage`, promptLen>0, LoRA strength 0.7.
- [ ] Hand back to civitai 开发 for page↑ (no curl generate as acceptance).

**Done when:** import pins flux1; contract tests green; stamp o34 on branch.
