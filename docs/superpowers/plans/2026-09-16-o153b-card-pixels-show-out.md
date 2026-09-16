# o153b Card Pixels Show /out Implementation Plan

> **For Grok Build:** executing-plans. No mid-knife review.

**Goal:** After page ↑ writeback, the **visible pixels** on the original shot card must be the generated `/out/<job>_0.jpg`, not the imported still — even when DOM `img.src` already points at `/out`.

**Evidence:** Pack `civitai-28386614-t2i-o153-writeback/` on HEAD `903589a`:
- DOM afterSrc/hrSrc = `/out/12100372-20260916154529603_0.jpg?_wb=…`
- `/out` md5 `a6c284af` ≠ import CDN md5
- Harness: card screenshot NCC closer to import (0.908) than to `/out` (0.796) → `cardStillImport=true`
- Same failure class as voided 28386610 (card kept import face while job file differed)

### Hypotheses (verify, don't assume)
1. `renderCards()` after `patchShotCardMediaDom` rebuilds HTML and races / restores import face briefly or permanently.
2. CSS `background-image` / second media layer still paints import while `img.src` is `/out`.
3. Browser/http cache serves import bytes for the display URL despite `?_wb=`.
4. Harness false Fail because /out face crop ≈ import (similar portrait) — still must prove with pixel hash of full `/out` vs card face decode, not sliding-window NCC only.

### Task 1 — failing proof
- Add test / harness step: decode card `.face img` natural image bytes (or canvas drawImage) and compare perceptual hash / downsample MSE to `/out` file AND to `importSourceUrl`. Generated must win.
- Reproduce on 28386614 artifacts if possible.

### Task 2 — fix paint path
- After writeback: set `shot.url` to clean `/out`, clear any face background-image, remove import-only layers from `.face`.
- Patch DOM **after** final `renderCards()` in the writeback path (or make `renderCards` prefer `/out` + bust and never paint `importSourceUrl` into `.face` when `url` is `/out`).
- Force reload: `img.removeAttribute('src'); img.src = displayMediaSrc(/out, jobTs)` + `img.decode()`; optional `crossOrigin` not required for same-origin `/out`.
- Persist clean `/out` without losing to hydrate import CDN (keep o153 rules).

### Task 3 — verify
- Unit tests green; stamp `v0821o153b-…`; commit+push.
- Parent will page↑ unused post again: card pixels must match `/out` file (eyeball + hash), refresh still.

No prompt/provider changes. No review call. Closed-loop still 0.
