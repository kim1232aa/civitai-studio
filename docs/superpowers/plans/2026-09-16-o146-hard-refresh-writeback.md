# o146 — Hard-refresh writeback (Magao dirty revive)

> 2026-09-16 · Asia/Shanghai · **不宣称 Pass until card+hard-refresh proven**

## Symptom
Civitai 28216425 page↑ wrote `/out/12100372-20260916083056313_0.jpg` onto `shot-kfhg25`.
Hard refresh → `shot-1` + Magao leftover. Canvas store for burn canvas had 29 dirty nodes.

## Hypotheses
1. `createCanvas` then somehow PUTs/adopts main house graph (Magao 29 nodes) into new canvas.
2. `persistServer` / `persistActiveCanvas` writes session `storyboard_graph.json` over canvas, or hydrate prefers global graph.
3. `mergeAdoptShotUrls` / `isMainHouseGraph` mis-scopes and revives wrong canvas nodes.
4. Writeback only updates in-memory state; canvas PUT races with hydrate of dirty project graph.

## Plan
1. Trace createCanvas → persist → writeback → PUT → hydrate on reload.
2. Fix: active canvas must own its nodes; never resurrect another canvas's graph into burn canvas.
3. Regression test + stamp o146 + commit/push.
4. Reburn 28216425; evidence under `civitai-28216425-t2i-reburn/`. Honest Pass/Fail.

## Root cause (confirmed)
`hydrateFromServer` when `!shotsHaveMedia()` did `applyGraph(storyboard_graph)` — the shared Magao house graph.
Fresh `createCanvas` → `loadEmptyBoard` (blank shot, no url) sets `_canvasAdopted`, then in-flight/next hydrate replaced the blank board with Magao 29 nodes; `persistActiveCanvas` PATCHed that dirt into the new canvas. Hard refresh adopted Magao `shot-1`.

## Fix (o146)
- `canvasScoped = _canvasAdopted && !isMainHouseGraph()` → never full `applyGraph(house)`; by-id URL merge only.
- `persistActiveCanvas` captures canvas id (no mid-flight retarget).
- Test: `scripts/test_o146_canvas_hydrate_scope.js`
