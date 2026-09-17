# o154 Card Pixels Match /out Implementation Plan

> **For Grok Build:** REQUIRED SUB-SKILL: executing-plans. No mid-knife review.

**Goal:** After page ↑, the **visible pixels** on the original shot card must match the new `/out/<job>_0.jpg`, not the imported source image.

**Evidence (o153 still Fail):** pack `docs/review-shots/closed-loop/civitai-28386614-t2i-o153-writeback/`
- jobId `12100372-20260916154529603`
- DOM afterSrc = `/out/…_0.jpg` (URL md5 matches out file)
- card screenshot NCC: card↔import **0.908** > card↔out **0.796** → **cardStillImport=true**
- Same class as voided `28386610` (singer /out vs floral-shirt card)

So o153 may update the src string / state URL, but the **rendered card still shows import**. Trace overlays, cached blob URLs, dual `<img>`, `object-fit` layers, import thumb winning z-index, or screenshot of wrong element.

### Task 1 — root cause
1. Reproduce on HEAD `903589a` with the 28386614 pack artifacts + live DOM.
2. Find why afterSrc URL is /out while card pixels ≈ import.
3. Failing test: after adopt/writeback, card `<img>` natural/decoded content fingerprint matches /out file, not import.

### Task 2 — fix
1. Make the shot card’s visible media element load and display the generated file.
2. Import stays reference only (separate slot/chip); must not paint over generated media.
3. Bust cache if needed (`?_wb=`) on the **displayed** element; force reload if browser keeps old decode.
4. afterSrc/hrSrc continue to be read from the real card DOM.
5. No prompt/param/provider changes; no new gates; no review calls.

### Task 3 — ship + prove
1. Unit/DOM test green; stamp `v0821o154-…`; commit+push main.
2. Report hash. Parent will re-burn unused post for pixel proof.
