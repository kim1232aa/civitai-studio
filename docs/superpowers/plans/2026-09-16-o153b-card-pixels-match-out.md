# o153b Card Pixels Match /out Implementation Plan

> **For Grok Build:** REQUIRED SUB-SKILL: executing-plans. No mid-knife review.

**Goal:** After page ↑ success, the **visible pixels** on the original shot card must match `/out/<job>_0.jpg`, not the imported source. o153 only made DOM `src` / afterSrc point at `/out` while card screenshot pixels still ≈ import (NCC card→import 0.908 > card→out 0.796). Same class as voided 28386610.

**Evidence pack:** `docs/review-shots/closed-loop/civitai-28386614-t2i-o153-writeback/`
- jobId `12100372-20260916154529603`
- afterSrc DOM = `/out/12100372-20260916154529603_0.jpg?...`
- /out md5 ≠ import md5, but card-after-gen.png still looks like import

### Task 1 — find why src≠pixels
Hypothesis (verify, don't assume): wrong img node updated; overlay/still thumb wins; canvas draw from import blob; cache-busted src not painted; dual media slots (source vs result).

### Task 2 — fix so card paints /out
1. Update the same element the user sees on the shot card.
2. Force reload of painted media (onload / bust / replace node) so pixels change.
3. Import source stays reference only — never covers result layer after gen.
4. afterSrc continues to be read from visible card DOM.
5. Failing test: after mock writeback, card screenshot/hash must correlate with out file not import.

### Task 3 — ship
stamp `v0821o153b-…`; commit+push; report hash. No Pass claim; parent will re-burn page ↑.
