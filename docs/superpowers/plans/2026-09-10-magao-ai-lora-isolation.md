# Magao AI LoRA isolation ↑ Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prove modelscope-ai page ↑ works for base model, then with a Hub LoRA that Infer accepts; hand jobId + inbound `loras` to api对接助手. Not a closed-loop Pass.

**Architecture:** Page-only ↑ on `/storyboard` (v0821o16). Isolate Fail `Model does not exist` on DistillPatch by (1) base-only Tongyi-MAI/Z-Image-Turbo, (2) Hub LoRA `YorickHe/polaroid_lora` strength 未填 → outbound string. Fix UI/search only if needed after evidence.

**Tech Stack:** Civitai Studio storyboard.js + providers/modelscope.py + :8765; Hub search via `/api/search`.

## Global Constraints

- Canon: `docs/00-IRON-RULES.md` + `docs/api-usage/modelscope.md` (aligned 2026-09-10).
- Never curl `/api/generate` as acceptance; page ↑ only.
- Never invent strength; single Magao LoRA without weight → outbound string `"owner/repo"`.
- Never claim closed-loop Pass without UI clean-refresh + §7 evidence.
- Do not tunnel on Civitai/Fal; this knife is Magao AI.

---

### Task 1: Base-only Magao ↑ (no LoRA)

**Files:** none (page evidence)

- [x] **Step 1:** Page ↑ backend=`modelscope-ai` serviceId=`Tongyi-MAI/Z-Image-Turbo` no LoRA chips
- [x] **Step 2:** Record jobId + GENERATE nLoras + `/out` path
- [ ] **Step 3:** Hand jobId to api对接助手 for POST/submittedInput check

**Done when:** job succeeds with `/out` and api has jobId.

### Task 2: Polaroid Hub LoRA ↑

**Files:** none (page evidence)

- [ ] **Step 1:** Add LoRA path `YorickHe/polaroid_lora`, strength empty
- [ ] **Step 2:** New unique prompt; page ↑ once
- [ ] **Step 3:** Capture inbound `loras` from Network POST `/api/generate` + jobId or Fail text
- [ ] **Step 4:** Hand evidence to api对接助手

**Done when:** api can Pass/Fail outbound LoRA shape; DistillPatch remains known bad Infer target.

### Task 3: Optional UI search route (only if blocking)

**Files:** Modify `static/storyboard.js` search URL if still calling `/api/search-loras`

- [ ] **Step 1:** Confirm UI still hits `/api/search-loras` (404) vs `/api/search`
- [ ] **Step 2:** If yes, patch to `/api/search` + stamp bump + 代码审查员

**Done when:** Magao LoRA search works from Composer or explicitly deferred as P1.

### Task 4: After Magao outbound Pass — rotate HF

- [ ] Open HF knife plan (separate) with Tongyi-MAI/Z-Image-Turbo + path LoRA; no invent nscale.

