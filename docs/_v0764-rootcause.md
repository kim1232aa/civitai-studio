# v0764 root cause — MusePublic / 2512 drift, silent double-fire, umt5, Allegro

## Evidence (v0763)
- Job `out/modelscope-ai_0dc2e62f-3a9d-4535-bc5f-9ee7cac702cf_0.json`:
  `serviceId` **and** `submittedInput.model` = `Qwen/Qwen-Image-2512`.
- Screenshots: dock/chip show short name "Qwen-Image" while list has cousins
  (`Qwen-image`, `Qwen-Image`, `Qwen-Image-2512`); after gen, 2512 is `.on`.
- First Generate click silent; later ghost submit of the 2512 job.
- Image search `umt5` still lists `umt5_xxl_encoder` text encoders.
- After image gen, video tab / Allegro-class auto-select still reachable.

## What does NOT remap on the server
- `providers/modelscope.py` `model_id` (L70–75) only strips `ms/` prefixes.
- `generate` (L434–512): `mid = model_id(payload.serviceId)` → `body["model"]=mid`
  → `remember_job(..., serviceId=mid, submittedInput=body)`.
- So **2512 was POSTed by the client** as `serviceId` (same as v0762 finding).

## MusePublic remap path (exact file:line)
- `static/index.html` **L2143** in `pickForBackend`:
  `if (src) want = ['Qwen/Qwen-Image-Edit', 'MusePublic/Qwen-Image-Edit'];`
- Trigger: `hasSourceNow()` (L2058–2059) true when `sourceImage` **or** `firstFrame`
  is non-empty (leftover from prior i2i / sticky frame). Catalog refresh /
  backend switch / import then calls `pickForBackend` (L2615, L3192) **without**
  setting `userPickedId`, so the dock can jump to MusePublic\* while the chip
  still *looks* like "Qwen Image" via `selectedPickLabel` preferring `name`
  (L1656–1664 / `svcRow` L1639).
- Live Hub also exposes `MusePublic/Qwen-image` (leaf `Qwen-image`); name-only
  chip cannot distinguish it from `Qwen/Qwen-Image`.

## 2512 write path (exact file:line)
1. UI: `runGenerate` L2822 freezes `userPickedId || selected.id`. If the visible
   row was a **cousin** (name "Qwen Image" / leaf "Qwen-Image" but
   `data-id=Qwen/Qwen-Image-2512`), freeze **locks 2512**.
2. L2921 forces `pl.serviceId = frozenPick` → POST `/api/generate`.
3. Server: `providers/modelscope.py` **L437–440, L500–507** writes that mid into
   `submittedInput.model` and `remember_job` / sidecar. No cousin invent — client
   already sent 2512.

Import of fixture 136741732 never sets `userPickedId` (only `selectService`
without `{user:true}` / `pickForBackend`), so freeze is only as good as the
possibly-drifted `selected.id`.

## Double-fire / silent first click
Triple Generate wiring:
1. `onclick="__studioGo"` on `#go` (L1011)
2. `document` capture listener (L1074–1080)
3. **extra** `go.addEventListener('click', fire, true)` (L3309–3311)

`__goOnce` (400ms) dedupes same-gesture fires, but `goBusy` is set **late**
(L2914, after validation / `afterPaint`). Early abort paths can leave the first
click looking silent; a second click after 400ms can submit a drifted pick.
`goClickLock` only wraps `runGenerate` and releases in `finally` after poll —
good for in-flight, not for the pre-`goBusy` window.

## umt5 still listed on image search
- FE `hubUtilityBlob` / PY `_TEXT_ENCODER` use `\bu[_-]?mt5\b`.
- Ids like `umt5_xxl_encoder` have `_` after `mt5`; `_` is a word char → **no**
  `\b` → `hub_utility_blob` returns False → stays `category=image` →
  `matchRecipe` keeps it. Confirmed: `umt5_xxl_encoder` → util False.

## Allegro / video jump
- `pickForBackend` no longer uses `lastImport.kind` for `vid` (L2104–2105) — good.
- Residual risk: `loadCatalog` → `pickForBackend` with empty modelscope video
  wants → `renderServiceList` default first video row (Allegro sorts early);
  `selectServiceById(..., {allowRecipeSwitch:true})` only on import (L2564) but
  post-gen `goBusy=false` unlocks catalog refresh steals if `userPickedId` cleared.

## Fix direction (v0764)
1. Import freeze → always set `userPickedId` to exact Hub id shown; no fuzzy.
2. Generate: early `goBusy`; POST `serviceId`/`model` must === `frozenPickId`; abort cousins.
3. Ban MusePublic / 2512 from remap/`want` when user has `Qwen/Qwen-Image`.
4. Single `#go` handler; immediate dock progress.
5. Chip/row show id leaf matching `data-id`.
6. Fix umt5 regex FE+PY; never Allegro/recipe switch after image gen.
