# o39 refs fill-to-cap + smart i2i match Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: executing-plans. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Boss 2026-09-10: when testing 参考图, **fill outbound to model `maxRefs`** (灌满); smart-match to real i2i-capable services (not leave t2i + silent drop / half slots). Rotate evidence across enabled providers — never Civitai-only.

**Canon:** docs/00-IRON-RULES.md §多参考 — 模型支持几路就露几路；禁空壳；禁发明 strength；禁 curl `/api/generate` 当验收。

**Current (honest):**
- UI shows `参考 N/cap`; over-cap hard-block; t2i+refs → `refUnusedGateMessage` + Edit sibling hint.
- `attachExtraImages` slices to cap — does **not** auto-fill to cap.
- Smart match partial (import match_service / LoRA pins / Edit hint) — **not** done for multi-ref capacity across 六家.

**Architecture:**
1. **Fill-to-cap (test + product):** For i2i services, Composer/canvas must expose **cap** link slots (not 1–2 when cap=5/9). Acceptance burns: connect/upload until `N==cap`, assert outbound `images`/`image_urls`/`input_references`/`image_url` length == cap (魔搭 singular=1).
2. **Smart match:** If refs linked and current service `catalogEatsRefs=false`, auto-suggest/select Edit/i2i sibling (already hinted) — strengthen to **one-click apply** without inventing models; if no sibling → hard block (already). Import/backend switch must re-resolve `maxRefs` from catalog caps (tighten-only).
3. **Provider rotate burn order:** Nano (maxRefs=5) → Fal multi `image_urls` → Civitai images≤9 → 魔搭 Edit (1 or 2509≤3) → HF only if true i2i path (能力表 i2i=none → 明示不支持，不计分).

**Stamp:** `v0821o39-refs-fill-smart-match`

---

### Task 1: Failing tests
- [x] UI/outbound: service with maxRefs=5 shows 5 capacity; with 5 linked URLs, payload bag length=5.
- [x] maxRefs=1 (魔搭): bag/singular length=1; never claim 5.
- [x] t2i + refs: still hard-block or smart-switch to Edit sibling (no silent ignore).

### Task 2: Implement
- [x] Expose full cap slots / remain chips; optional「灌满测试」dev action that attaches N distinct local/fixture images up to cap (page path still human-clickable for acceptance).
- [x] Smart-match: when refs>0 and !eatsRefs, offer/apply `editSibling` serviceId if catalog has it.
- [x] Stamp + push tip hash; closed-loop still 0. (510532c)

### Task 3: Burns (开发)
- [ ] Page↑ per provider with **灌满** refs + api 核 outbound count==cap; auto writeback; no 接到此镜; no curl generate.

**Done when:** tip + at least one provider 灌满 outbound evidence; others scheduled; never claim 六家 Pass early.
