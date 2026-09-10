# o46 — resume writeback after tab death (Magao long jobs)

**Stamp:** `v0821o46-resume-job-writeback`

**Why:** Edit-2509 job `2ad94576` SUCCEED + `/out` materialize OK; browser OOM mid-poll → `writebackResult` never ran; hard-refresh left `shot-1.url` on prior `0808a50b` while History showed new media. Writeback is client-only today.

## Goal
If tab dies / hard-refresh before poll finishes, boot (or server) still binds **succeeded job's saved[]** to the **originating shot card** + PUT `/api/storyboard-graph`. No「接到此镜」required. Do not invent Pass for closed-loop.

## Approach (prefer smallest)
1. On `/api/generate` success: persist `{ jobId, shotId, backend, startedAt }` in `localStorage` **and** a small server sidecar (e.g. `data/pending_jobs.json` keyed by jobId) so clean-profile hydrate can resume.
2. On storyboard boot (after hydrate): for each pending job, `GET /api/jobs/:id`; if `saved[]` present → `writebackResult(shot, saved[0].url)` then clear pending; if still running → resume poll loop; if failed → clear + toast.
3. Optional harden: when modelscope (or any) `job_status` first materializes `saved[]`, if pending sidecar has shotId, server updates that shot.url in `storyboard_graph.json` (belt for OOM). Keep client path as source of truth for History push.

## Tests
- Unit: pending register/clear; boot resume with mock succeeded+saved writes shot.url.
- Manual: start Magao Edit-2509↑, kill tab before SUCCEED, reopen → shot card gets `/out/...2ad94576...png` without pin.

## Out of scope
- Closed-loop scoring; Composer adaptive (Looper → separate); unused-post burns (after this tip).
