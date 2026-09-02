# Harsh QA — v0766 (f50a727 / 80f1511)

Scope: read-only. No product mods. No POST `/api/generate`.
GET `http://127.0.0.1:8765/` → **200**.
Pinned review commits: **f50a727** (code) + **80f1511** (docs note at `userPickedId` write).
Note: shared box HEAD later moved to **221bed1 v0767** (catalog reload on tab + version stamp only). The five issue surfaces below are **unchanged** vs 80f1511 (`git diff 80f1511..221bed1 -- static/index.html providers/hub_classify.py` is stamp + `setRecipe` reload only).

Verdict: **NO PRODUCT PASS.** Two claimed fixes hold; three still fail or only partially hold under live Hub data.

---

## 1) Chip / list full owner/leaf

### Status: mostly FIXED (residual P2)

| Site | File:line | Behavior |
|------|-----------|----------|
| List row label | `static/index.html:1671–1694` `svcRow` | Always `owner + '/' + leaf` from `it.id` (v0766 comment :1676). |
| Chip / dock label | `static/index.html:1703–1708` `selectedPickLabel` | Returns **full `it.id`**, not `name`. |
| Chip paint | `static/index.html:1710–1723` `showPickedChip` | `已选 ` + full id. |
| Dock align | `static/index.html:1725–1735` `syncPickedDockIfStale` | Same label source. |

**Evidence:** live `GET /api/catalog?backend=modelscope-ai&q=Qwen-Image&category=image` still returns both `Qwen/Qwen-Image` and `MusePublic/Qwen-image`. Labels now differ (`Qwen/Qwen-Image` vs `MusePublic/Qwen-image`). Screenshots: `docs/review-shots/v0765-selected.png` leaf-only (`Qwen-Image`) vs `docs/review-shots/v0766-selected.png` owner/leaf (`Tongyi-MAI/…`, `MusePublic/…`).

**Residual**

- **P2** `static/index.html:690` `.svc-name { text-overflow:ellipsis }` and `:632–642` `.svc-picked` ellipsis — long ids still clip; owner usually visible (differs at start for MusePublic vs Qwen) but leaf can vanish on narrow sidebar.
- **P2** `static/index.html:1682–1687` empty case-insensitive cousin branch (dead code after always-on owner/leaf).
- **P2** multi-segment Hub ids (`a/b/c`) collapse to `a/c` in `svcRow` (first/last only); chip still shows full id via `selectedPickLabel` → list≠chip possible.

---

## 2) userPickedId freeze vs MusePublic remap

### Status: FAIL / incomplete (P0 + P1)

### Exact write (still the only Hub pick write)

- **`static/index.html:1852–1853`** — sole non-civitai assignment: `userPickedId = it.id` when `opts.user && !(goBusy \|\| generateLockId)`.
- Documented at 80f1511 / `docs/_v0766-rootcause.md`.

### What v0766 actually closed

| Guard | File:line |
|-------|-----------|
| Generate locks `userPickedId` before await | `static/index.html:2955–2976` `onGenerate` |
| Exact `findCatalogItem` only | `:1696–1701`, `:2963`, `:3072` |
| Ban `selectService` / ById / `pickForBackend` / `selectFirstInCatalog` while busy/lock | `:1838–1848`, `:2135–2157`, `:2590–2593`, `:3401–3403` |
| Strip `MusePublic/*` from want | `:2143–2147`, `:2252–2253` |
| ModelScope want no longer lists MusePublic | `:2206–2209` |
| Import exact Hub only | `:2665–2682`, `:2759–2770` |
| POST forces `pl.serviceId` / `pl.model === frozenPick` | `:3124–3146` |
| `isForbiddenHubRemap` cousin ban | `:2998–3009` |

**Live catalog still serves remap bait as first-class image rows** (not inventing on server; client can still freeze them if clicked):

- `MusePublic/Qwen-image` · `MusePublic/Qwen-image-fp8` · `MusePublic/Qwen-Image-Edit`
- `Qwen/Qwen-Image-2512` and other cousins

### Still broken / open

1. **P0 — freeze does not mean “cannot be MusePublic.”**  
   If the user (or import Pass 2) lands on `MusePublic/Qwen-image`, `userPickedId` **is** MusePublic (`:1853`). `isForbiddenHubRemap` (`:3005`) only bans MusePublic when **frozen is already Qwen/***; it does **not** refuse posting MusePublic as the locked id. Chip now shows the truth (issue 1) — steal-by-hidden-label is fixed; steal-by-wrong-row / wrong-import is not.

2. **P1 — `resolveExactHubFromImport` Pass 2** (`:2676–2682`) still accepts literal `MusePublic/*` whenever the import blob does **not** also name `Qwen/Qwen-Image*`. That path calls `selectService(keep, { user: true })` (`:2762–2764`) → writes `userPickedId`.

3. **P1 — `setRecipe` clears freeze with no lock** (`:1884–1889`): `userPickedId = null` with **zero** `goBusy` / `generateLockId` check (confirmed on `80f1511:static/index.html`). Tabs stay clickable mid-generate → clears sticky id while POST in flight; `finally` (`:3230–3232`) re-stamps `frozenPick`, but mid-flight readers of `userPickedId` see null.

4. **P1 — cousins remain one click away.** List still shows `Qwen/Qwen-Image-2512` etc. Freeze is exact — good — but UX still allows locking the wrong cousin; no generate-time “must be allow-listed Hub id” beyond equality.

5. **P2 — `finally` drops `generateLockId` immediately** (`:3244`) after `renderServiceList`, then unlocks. Narrow race vs concurrent `loadCatalog` / tab handlers; `userPickedId` restore helps but lock window is short.

**Non-cause (reconfirmed):** `providers/modelscope.py` does not invent MusePublic; sidecar echoes client `serviceId`.

---

## 3) Immediate 「正在提交」 dock

### Status: FAIL vs claim (P1) — partial mitigation only

### Claimed path

- `onGenerate` `:2970–2971` / `:2979–2980`: `goBusy = true; setDock('正在提交…')` **before** `await runGenerate()`.
- Re-assert `:3120–3122` before `afterPaint`.

### Actual first paint

- **`static/index.html:1043–1048` `__studioGo`** sets dock to **`已点到生成`** *before* `onGenerate`.
- Only then `:1075–1077` calls `onGenerate` → overwrites to `正在提交…`.

**Harsh read:** the *immediate* dock string is **not** `正在提交…`; it is `已点到生成`. Claim “Immediate 正在提交 dock” is false as specified.

### Worse residual

- **P1** `:1060–1061` `__goOnce` 800ms dedupe: if it `return false` **after** `:1046–1048` already wrote `已点到生成`, dock **sticks** on `已点到生成` and never reaches `正在提交…` / generate. Silent-ish second click with wrong dock.
- **P2** `#go` label stays `生成` until `:3121` (`提交中…`) — after validation — while dock already says submitting.
- **P2** empty-prompt fail (`:3101–3109`) flashes `正在提交…` then `先写提示词` — acceptable but noisy.
- **OK:** early `goBusy` (`:2970`) + `goClickLock` (`:2949–2952`) closes the old late-busy double-fire window from v0764 notes. Document/go capture duplicates remain removed (`:1088`, `:3249`, `:3547`).

---

## 4) sd35_t5xxl / sd35_clip_l out of image

### Status: PASS for named ids (residual P2)

| Layer | File:line | Result |
|-------|-----------|--------|
| PY `_TEXT_ENCODER` | `providers/hub_classify.py:76–85` | `(?:^|[\W_])t5[_-]?xxl…` / `clip[_-]l` — `_` prefix hole fixed. |
| FE `hubUtilityBlob` | `static/index.html:1306–1308` | Same pattern; kept in sync. |
| Apply category | `providers/hub_classify.py:239–247` `apply_hub_category` | → `category=utility`. |
| FE recipe filter | `static/index.html:1356–1357` | `hubUtilityBlob \|\| cat==='utility'` → excluded from **all** recipe tabs. |

**Live GET (no POST):**

- `muse/sd35_t5xxl` → `category=utility`, `hub_utility_blob=True`, hidden from image.
- `muse/sd35_clip_l` → same.
- `q=clip_l` / `t5xxl` / `umt5` with `category=image` → **0** image hits for those encoder dumps on modelscope-ai / huggingface (encoders classified utility).

**Residual**

- **P2** `muse/sd35_clip_g` still `category=image` (pattern is `clip_l` only, not `clip_g` / `clip_g`). Related encoder junk can remain on image search for `q=sd35`.
- **P2** true SD3.5 checkpoints (`muse/sd35_large`, etc.) correctly stay image — do not over-filter.

---

## 5) Video wan Comfy / LoRA noise reduced

### Status: FAIL (P0) — filter ineffective on live wan video list

Implementation: **FE-only** `hubVideoListNoise` `static/index.html:1332–1349`, applied in `matchRecipe` video branch `:1366–1369`. **No** PY equivalent in `providers/hub_classify.py` (Comfy/LoRA wan still `category=video` from Hub).

**Live:** `GET …/catalog?backend=modelscope-ai&q=wan&category=video` → **39** rows. FE noise predicate dropped **0/39**.

### Root causes (file:line)

1. **P0 — `\bcomfyui\b` fails when glued with `_` (same class as old t5xxl hole).**  
   `static/index.html:1345`  
   Id `Comfy-Org/Wan_2.2_ComfyUI_Repackaged` → blob `…wan_2.2_comfyui_repackaged…`. In JS/Python, `_` is a word char → **no** `\b` before `comfyui` → noise check false → **row kept**.  
   Confirmed: `re.search(r'\bcomfyui\b', '…_comfyui_…') is False`; `(?:^|[\W_])comfyui…` is True.

2. **P0 — `wan2.x` early KEEP overrides LoRA / weight junk.**  
   `:1343–1344`  
   If `\bwan2[._-]\d` matches and comfy regex misses → `return false` (keep).  
   Live kept junk:
   - `lightx2v/Wan2.2-Distill-Loras`
   - `acevsok/wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors`
   - `Comfy-Org/Wan_2.2_ComfyUI_Repackaged`
   - `Kijai/WanVideo_comfy` (`comfy` without `comfyui`; `:1345` patterns miss)

3. **P1 — LoRA drop requires `!hubVideoFamilyBlob`** (`:1347`).  
   Anything with `\bwan\b` / category video is “family” → LoRA clause never fires for wan LoRAs.

4. **P1 — PY leaves these as `category=video`** (`providers/hub_classify.py:96–104` `_VIDEO_FAMILY` includes bare `wan`; `:183–185` GGUF exception). Server will keep returning them; FE must filter — and FE currently does not.

Real Wan-AI T2V/I2V/GGUF rows correctly survive (keep rules) — the failure is **not** over-filtering good checkpoints; it is **under-filtering** Comfy/LoRA/safetensors noise.

---

## Severity rollup

| ID | Issue | Sev | Verdict |
|----|-------|-----|---------|
| 1 | Chip/list full owner/leaf | P2 residual | **Mostly fixed** |
| 2 | userPickedId freeze vs MusePublic remap | **P0/P1** | **Incomplete** — hidden remap closed; MusePublic still freezable; setRecipe clears lock; import Pass 2 hole |
| 3 | Immediate 正在提交 dock | **P1** | **Fail claim** — first string is `已点到生成`; `__goOnce` can stick it |
| 4 | sd35_t5xxl / clip_l out of image | P2 residual | **Pass** (named ids); `clip_g` still image |
| 5 | Video wan Comfy/LoRA noise | **P0** | **Fail** — 0 drops on live wan video list; `\b` + wan2 keep |

### P0
- **5** `static/index.html:1343–1345` — Comfy/LoRA/safetensors wan noise not removed (`\bcomfyui\b` + wan2 keep).
- **2** MusePublic remains a valid frozen `userPickedId` / POST target when selected (`:1853` + weak `:3005`).

### P1
- **3** `__studioGo` `:1043–1061` immediate dock ≠ `正在提交…`; `__goOnce` abort leaves wrong dock.
- **2** `setRecipe` `:1888–1889` clears `userPickedId` during generate; import Pass 2 `:2676–2682` can freeze MusePublic.
- **5** PY never demotes Comfy wan packs; FE-only filter is the single broken gate.

### P2
- **1** ellipsis / dead cousin branch / multi-segment list≠chip.
- **3** button label lag; prompt-fail flash.
- **4** `sd35_clip_g` still on image.

---

## Checks performed

- `GET /` → 200.
- `GET /api/providers`, `GET /api/catalog?backend=modelscope-ai&q=…` (Qwen-Image, wan, sd35, clip_l, t5xxl, umt5) — read-only.
- `python3 scripts/test_p0_wiring.py` → PASS (unit wiring; does **not** cover live wan noise `\b` hole).
- Regex probes for `_comfyui_` / `sd35_*` / wan2 LoRA keep.
- No POST generate / whatif.

**Product pass: NO.**
