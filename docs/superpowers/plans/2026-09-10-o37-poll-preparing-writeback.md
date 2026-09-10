# o37 poll must survive long PREPARING → auto writeback Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: executing-plans. Steps use checkbox (`- [x]`) syntax.

**Goal:** Page↑ auto-writeback to original shot card when Civitai job stays `preparing` longer than current poll budget (~120×2.5s≈5min). Sample `28533250` job `…130036029` succeeded + `/out` saved, but UI stopped polling → card empty until manual「接到此镜」(does **not** count as closed-loop).

**Evidence:**
- Outbound Pass; job eventually succeeded; server `saved[]` → `/out/…_0.jpg`.
- Poll: `pollMax=120` materializing images @ 2500ms.
- `stillGoing` after poll **omits** `preparing`/`scheduled` → false「无预览」and skip `writebackResult`.
- computerUse used hist-pin「接到此镜」— **not** scoreable writeback.

**Architecture:** Keep polling while status is in-flight including preparing/scheduled/processing; only stop on terminal+saved or true failure. After loop, treat preparing as stillGoing (honest wait/retry), never leave card blank when `/out` appears mid-poll.

**Tech Stack:** `static/storyboard.js` poll loop ~5573–5665; stamp `v0821o37-poll-preparing-wb`

---

### Task 1: Failing test

- [x] Simulate: poll responses preparing×N then succeeded+saved`/out/…` → `writebackResult` / shot.url set (unit or storyboard graph test).
- [x] After max ticks still `preparing` → stillGoing path (not empty-url hard fail pretending done).

### Task 2: Fix poll

- [x] `inFlight` already has PREPARING — also treat `scheduled` if needed (case-insensitive).
- [x] While `inFlight`, do **not** exhaust budget blindly: either extend `pollMax` when preparing (e.g. civitai image up to ~20–30 min) **or** don't increment failure budget while preparing (prefer extend pollMax for civitai materializing to ≥480 ticks @2.5s ≈20min, matching observed ~18min).
  - **api/开发 override:** use **≥720 @ 2.5s ≈30min** (covers sample ~29min preparing).
- [x] `stillGoing` regex/status list: add `preparing`, `prepared`, `scheduled`, `queued` (mirror inFlight).
- [x] On saved`/out` break → existing writebackResult path unchanged.
- [x] Stamp `v0821o37-poll-preparing-wb`; push; report hash.
- [x] Hand back for **fresh** page↑ `28533250` (or unused AIImageStudio if burned) — auto card writeback + hard refresh **without** clicking「接到此镜」. No curl generate acceptance.

**Done when:** tip hash; tests green; closed-loop still 0 until auto writeback evidenced.
