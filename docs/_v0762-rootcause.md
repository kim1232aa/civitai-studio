# v0762 root cause — `serviceId=Qwen/Qwen-Image-2512` vs UI "Qwen-Image"

## Symptom
On-disk job sidecar (`out/modelscope-ai_*_0.json`) can store
`serviceId` / `submittedInput.model` = `Qwen/Qwen-Image-2512` while the UI chip/list
looked like plain **Qwen-Image**.

Evidence: `out/modelscope-ai_c58f367f-…_0.json` has 2512; sibling job
`out/modelscope-ai_f3761ee8-…_0.json` (same prompt) has exact `Qwen/Qwen-Image`.

## What does NOT remap
- **Server / ModelScope** (`providers/modelscope.py` `model_id` ~L70–75, `generate` ~L434–506):
  strips `ms/` prefixes only; writes `remember_job(…, serviceId=mid)` from the
  **request** `payload.serviceId`. No "latest cousin" remap.
- **Sidecar** (`providers/io_meta.py` `write_sidecar` ~L48–53): copies job meta as-is.

So 2512 was **sent by the client**.

## Root cause (UI cousin match)
1. **v0760** `selectFirstInCatalog` used leaf `includes()` matching
   (`(id+' '+name).toLowerCase().includes(wantLeaf)`).
   Want `Qwen/Qwen-Image` → leaf `qwen-image` **matches** id
   `Qwen/Qwen-Image-2512` (substring cousin). File: historically
   `static/index.html` `selectFirstInCatalog` (pre-0761).
2. **v0761** replaced that with `catalogIdMatchesWant` using exact id **or name**
   + `startsWith(want+'/')` (`static/index.html` ~L2046–2058 in 91635fe).
   Still not a hard lock: `runGenerate` only froze when `userPickedId` was set
   (`frozenPick = userPickedId ? … : null` ~L2777–2778). Auto-picked / drifted
   `selected.id` could POST without asserting against a frozen id; `payload()`
   reads `currentServiceId()` (`~L1936`) from `picked.serviceId || selected.id`.
3. Chip label prefers **name** (`selectedPickLabel` ~L1654–1657), so a 2512 row
   named like "Qwen Image" reads as Qwen-Image in the UI while `data-id` is 2512.

## Secondary jumps (post-gen / import)
- `pickForBackend` used `vid = recipe === 'video' || (lastImport && lastImport.kind === 'video')`
  (v0761 ~L2083) → after a video-tagged import, catalog refresh / gen cleanup could
  auto-prefer **video** models (Allegro / Wan) even on the image tab.
- `selectServiceById` always did `recipe = recipeFor(it)` (v0761 ~L2505–2507) →
  programmatic selects could flip image → video.
- Import image **136741732**: Civitai import stores a **Civitai** `serviceId`
  (`providers/civitai.py` `import_image` ~L910) + ecosystem blob; it does **not**
  write `Qwen/Qwen-Image-2512`. After switching to ModelScope, `pickForBackend`
  prefs (`Tongyi-MAI/Z-Image-Turbo`, `Qwen/Qwen-Image`) plus the old cousin
  matcher could land on 2512. `userPickedId` is only set on explicit row click
  (`selectService(…, {user:true})` ~L1797–1798), so import alone does not freeze
  the Hub id unless the user re-clicks.

## hub_classify notes
- Pre-0762: all GGUF → utility (video Wan GGUF over-filtered off video tab).
- umt5 / text-encoder were still **image** (not utility) → cluttered image tab.

## Fix (v0762)
- Hard-lock: `frozenPickId` from `userPickedId || selected.id`; force
  `pl.serviceId = frozenPick` before POST; ignore server endpoint/model echo.
- `catalogIdMatchesWant`: **exact id string only** (no name / includes / prefix).
- No post-gen tab/recipe jump: `allowRecipeSwitch` only on import; sticky
  `userPickedId` + `selectionLocked()` (~8s) block auto pick / lastImport steal.
- Poll fail/empty/timeout → `setDock`.
- umt5 / text-encoder → utility; video-family GGUF/LoRA stay video.
