# o40 fill-exact-cap (灌满 N==maxRefs) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: executing-plans. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Nano Flare Edit「灌满测试」must not show **参考 6/5 超出**. 灌满 + gate share outbound口径 `countRefUrls`; completed-shot 成片 chip is visual-only.

**Evidence (开发 hard-refresh after o39):** `openai/gpt-image-2.5/flare/edit` 灌满 → UI 6/5. Root: fill used `countRefUrls`→5 while UI numerator used `displayRefUrls` (+成片)→6.

**Architecture:** One 口径 — `countRefUrls` for 参考 N/cap hint, remain/empty slots, 灌满 loop, and hard-gate. Keep rendering 成片 chip (`data-self-ref`) but do not count it in numerator / outbound bag.

**Stamp:** `v0821o40-fill-exact-cap` · cache-bust `20260910-o40fillexactcap`

**Out of scope:** Magao Edit-2509 maxRefs=3 (later knife). closed-loop 0. No curl generate.

---

### Task 1: Failing tests
- [x] Nano maxRefs=5 + shot.url 成片 → 灌满 outbound N==5; bag==5; 成片 not in bag
- [x] Without 成片 → still exact 5
- [x] Already at cap → add 0

### Task 2: Fix + tip
- [x] UI `refCount` = `countRefUrls` (not `displayRefUrls`)
- [x] `fillRefSlotsToCap` stops at outbound N==cap (never N>cap)
- [x] Stamp + push; closed-loop 0

**Done when:** tip hash; tests green; 灌满 never paints 6/5.
