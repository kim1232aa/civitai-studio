# v0766 root cause — MusePublic/Qwen-image steal into userPickedId

## Evidence (v0765)
- User selects `Qwen/Qwen-Image` (chip/list leaf `Qwen-Image`).
- On Generate: `data-id` jumps to **`MusePublic/Qwen-image`**; later dock
  `已选模型不在当前目录：MusePublic/Qwen-image`; gallery stuck at 14; no new out JSON.
- Screenshots `docs/review-shots/v0765-*.png`: list shows both leaf `Qwen-image`
  and `Qwen-Image` **without owner**; after click, lowercase leaf is `.on`.

## Exact write of MusePublic into userPickedId

**Exact assignment: `static/index.html:1853`** — `userPickedId = it.id` inside `selectService` when `opts.user` (sole Hub pick write; pre-v0766 was ~L1807).

```js
if (opts.user && it && it.id && !(goBusy || generateLockId)) {
  userPickedId = it.id;   // ← ONLY non-civitai write path for a new pick
}
```

Called from **`bindRows` svc-row click** (`selectService(it, { user: true })`).
When the clicked row's `data-id` is `MusePublic/Qwen-image`, that string is
assigned verbatim to `userPickedId`.

Secondary write (only if import literally carries that id):
`applyImport` → `resolveExactHubFromImport` → `selectService(keep, { user: true })`.
Fixture `136741732` does not invent MusePublic; the row-click path is the one
that produced the dock string.

There is **no** `userPickedId = 'MusePublic/…'` literal elsewhere. Restores
(`userPickedId = frozenPick` in `runGenerate` finally) only echo whatever was
already frozen — so if freeze captured MusePublic, finally re-stamps it.

## Why the UI looked like Qwen/Qwen-Image

1. **`selectedPickLabel` / `svcRow` showed leaf only** (`Qwen-image` /
   `Qwen-Image`). Owner `MusePublic` vs `Qwen` was hidden unless exact leaf
   collision (case-sensitive). `Qwen-image` ≠ `Qwen-Image` → **no owner suffix**.
2. Chip `已选 Qwen-Image` could not prove `data-id === Qwen/Qwen-Image`.
3. Hub search `q=Qwen-Image` is case-insensitive → both cousins in the list.
4. Dock `已选模型不在当前目录：MusePublic/Qwen-image` is emitted by
   `loadCatalog` when `userPickedId` is already MusePublic and
   `findCatalogItem(userPickedId)` misses after a catalog refresh — proof the
   overwrite already happened **before** that dock line.

`isForbiddenHubRemap` / generate-time cousin guards ran **after** selection was
already MusePublic, so they could not prevent the write at selectService opts.user.

## What v0766 changes
1. `onGenerate`: `lockId = userPickedId`; exact `findCatalogItem(lockId)` only;
   set `selected`/`copyPicked`/`generateLockId`/`goBusy`/`正在提交…` **before**
   any await; fail dock with lockId if missing from catalog (no cousin search).
2. Ban `selectService` / `selectServiceById` / `pickForBackend` /
   `selectFirstInCatalog` / svc-row clicks while `goBusy || generateLockId`.
3. Strip all `MusePublic/*` from `pickForBackend` want lists.
4. Chip + svc-row always show **full `owner/leaf`**.
5. `findCatalogItem` / `catalogIdMatchesWant` remain case-sensitive exact `===`.
6. P1: `sd35_t5xxl` / `sd35_clip_l` utility (`\\b` hole, FE+PY); video list
   `hubVideoListNoise` drops Comfy/nodepack weight junk, keeps real wan GGUF.

## Non-causes (ruled out)
- Server `providers/modelscope.py` does not invent MusePublic.
- `pickForBackend` ModelScope want list already dropped MusePublic in v0764;
  residual risk was **userPickedId already wrong** + leaf-only chip.
