# o49b + o50 — merge-review P0s (2026-09-11)

**Role:** Grok Build · tip wiring only · no closed-loop Pass · no merge main  
**Stamps:** `v0821o49b-hydrate-fresh-empty-url` (+ Nano tip `v0821o50-nano-no-default-strength` same or follow-up commit)  
**Branch:** `feat/cloud-nodes-poc` @ after `1f4a918`

## Goal

Unblock 合码审 without inventing product Pass. Fix four P0s:

1. **hydrate freshness** — server url non-empty must NOT unconditionally overwrite local. Keep local when: pending PUT in flight, or local media newer than server (mtime / `urlUpdatedAt` / pending marker).
2. **empty url merge** — `write_storyboard_graph` (and client `persistServer` payload) must not let empty `shot.url` last-PUT-wins stomp another desk's non-empty url. Merge: incoming empty → keep existing non-empty.
3. **pending retire** — on new job register for same `shotId`, clear/retire old `jobId`s; resume/apply must not write stale `/out` onto a card that already moved on (newer job / newer url).
4. **Nano LoRA strength** — `resolve_nano_loras` / `_loras`: null/missing strength → **omit scale** (Fal/HF style) or fail 400; **never invent `1.0`**. Plain string LoRA entries: omit scale (no default). Invalid non-numeric → 400/error.

## Files

| File | Change |
|------|--------|
| `static/storyboard.js` | hydrate freshness; registerPendingJob retires same-shot old jobs; resumeOnePending skip if shot already has newer url / different `_jobId`; stamp comment |
| `static/storyboard.html` | stamp + cache-bust |
| `server.py` | `write_storyboard_graph` merge empty-url preserve; `apply_pending_job_to_graph` refuse overwrite if shot url already set to different newer media OR pending retired |
| `providers/pending_jobs.py` | `register_pending` clears other jobs with same shotId |
| `providers/nanogpt.py` | no default 1.0 scale |
| `scripts/test_o49b_*.js/py` + nano test + update o48 harness expectations for freshness | |

## Tasks

### T1 — Tests first (red)
- `scripts/test_o49b_hydrate_freshness.js`: hydrate keeps local when `pendingPut` / `urlUpdatedAt` newer than server; still adopts server when local older/stale.
- `scripts/test_o49b_empty_url_merge.py`: write_storyboard_graph empty url does not wipe existing.
- `scripts/test_o49b_pending_retire.py`: register new job retires old same-shot; apply old jobId does not overwrite.
- Extend `scripts/test_nanogpt_lora_resolve.py` (or new): strength null → no scale key / not 1.0.

### T2 — Implement
- Hydrate: compare freshness; only adopt server when local is empty OR server clearly fresher AND no pendingPut for that shot.
- Graph write: deep-merge per shot id: if incoming url empty/whitespace and existing non-empty → keep existing.
- pending_jobs.register_pending: before insert, delete jobs where shotId matches.
- Client registerPendingJob: same local retire; clearPendingJob old ids.
- resumeOnePending / apply_pending: if shot._jobId exists and != jid → skip+clear old; if shot.url already set and pending is retired → skip.
- Nano: mirror Fal omit-null scale; string entries omit scale.

### T3 — Stamp + green
- HTML stamp `v0821o49b-hydrate-fresh-empty-url`, bust `20260911-o49bhydratefreshemptyurl`
- Update persist_restore / graph stamp asserts if needed (same pattern as o49)
- Run: persist_restore, o15, o46, o48 (may need soft update for freshness), new o49b tests, nanogpt lora, graph (P1 leftovers ok)

### T4 — Commit push report
- One or two commits on feat branch; push; tell 开发 hash; **no merge main**; closed-loop 0.

## Non-goals
P1 Magao singular / over-cap / empty service defaults. Blind merge. Claiming closed-loop.
