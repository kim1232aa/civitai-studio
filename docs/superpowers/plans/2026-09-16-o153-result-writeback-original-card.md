# o153 Result Writeback Original Card Implementation Plan

> **For Grok Build:** REQUIRED SUB-SKILL: use executing-plans. Do not call reviewers mid-knife.

**Goal:** Fix successful page generation whose `/out/<job>_0.jpg` is saved but the original shot card still displays the imported source image.

**Evidence:** Voided pack `_invalid-civitai-28386610-t2i-closed3-card-is-original-not-out/`: job output is a singer holding a microphone; card screenshots remain the imported floral-shirt portrait. `report.json afterSrc=None` was real. Seko node-Composer shots are valid and need no recapture.

### Task 1 — reproduce and trace
1. Read the voided pack report, DOM/card screenshots, and audit for job `12100372-20260916150219332`.
2. Trace page `#send` success from poll result to current shot state, DOM image `src`, persisted canvas JSON, and refresh hydrate.
3. Add a failing test proving imported source media cannot mask generated output on the original shot card.

### Task 2 — fix writeback
1. On successful saved result, update the selected/original shot's generated-media field and rendered card DOM immediately.
2. Keep imported source image as source/reference metadata only; it must not win rendering after generation.
3. Persist the active canvas and hydrate from the same generated URL.
4. Read `afterSrc` from the actual card DOM, not from constructed JSON.
5. Do not change prompts, params, providers, or add gates.

### Task 3 — verify code
1. Test immediate card source = `/out/<current job>_0.jpg` and source differs from imported image.
2. Test refresh hydrate preserves that generated URL.
3. Bump visible stamp; commit and push main.

### Task 4 — new page run
After code lands, use a new unused AIImageStudio post and page `#send` only. Prove the card visibly matches the new `/out` media and remains after refresh. Reuse the already-valid Seko node-Composer comparison only if the flow matches; no fake Pass.
