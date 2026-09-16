# o142 — house PUT shot-1 + adopt merge + Magao failed+saved

**Stamp:** `v0821o142-house-put-adopt-poll` · bust `o142house`

## Root cause (Magao 119689290 hard-refresh)

1. **o120 `isMainHouseGraph()` required `shot-civitai` only.** Live house graph uses **`shot-1`** (no `shot-civitai`). Session writeback → `persistServer` **skipped PUT** to `storyboard_graph.json` → server kept old `2ad94576…` while session card showed `367d6512…`.
2. **Hard refresh:** `adoptCanvas` blind-applied stale canvas nodes (old url) and `persist()` stomped LS; hydrate could not recover because server graph never got the new url.
3. **o48 server-wins** only helps when server PUT landed; gate regression broke that belt.

## Magao poll debt (same tip)

Enqueue 200 OK; later poll can flip `failed` + `invalid response format` while `/out` already exists (o46b). Live generate poll **threw before** reading `saved[]` / `pendingWriteback` (resume path already handled). Frontend: on failed, prefer `failSaved` then writeback.

## Fix

| Spot | Change |
| --- | --- |
| `isMainHouseGraph` | `shot-1` \|\| `shot-civitai` |
| `adoptCanvas` | `mergeAdoptShotUrls` (fresher LS/memory wins) + re-`hydrateFromServer` |
| generate poll | failed → `pickSavedUrl` / `pendingWriteback.url` → break (not throw) |

## Verify

Frontend only: writeback `367d6512` on shot-1 → hard refresh keeps card. No Pass claim.
