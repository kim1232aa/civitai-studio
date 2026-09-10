# o27 Import Strength REST Backfill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** When trpc `image.getGenerationData` leaves LoRA `strength` null/missing, backfill the official REST ` /api/generation/data` strength for the same versionId (image 28533344 → 0.7). Never invent 0.8/defaults.

**Architecture:** Add public REST fetch + versionId merge helper in `providers/civitai.py`; call from `import_image` after trpc/meta resource collect, before `_loras_from_import_sources`. Offline unit test with 28533344 fixture shape; stamp `v0821o27-import-strength`.

**Tech Stack:** Python providers, unittest offline mocks

**Spec:** Steering knife v0821o27-import-strength; Iron Rules §2.9 (no invent defaults); REST official strength is original param.

## Global Constraints

- NEVER invent 0.8 / silent defaults / model swaps
- Do NOT touch §4 / short prompt / delete capabilities / Composer adaptive UI
- Keep o23–o26 paths working
- Stamp v0821o27-import-strength; commit+push feat/cloud-nodes-poc
- NEVER 可交付

---

### Task 1: REST backfill helpers + import_image wiring

**Files:**
- Modify: `providers/civitai.py`
- Test: `scripts/test_civitai_parameter_contract.py`

- [ ] **Step 1: Add helpers** `fetch_generation_data_rest`, `_resource_version_id_for_strength`, `_backfill_strength_from_rest`
- [ ] **Step 2: Wire** into `import_image` after resources collected
- [ ] **Step 3: Unit test** fixture 28533344 → strength 0.7, no strengthMissing; null+null stays missing; explicit trpc not overwritten
- [ ] **Step 4: Stamp** storyboard.html + storyboard.js header
- [ ] **Step 5: Run tests, commit, push, report**
