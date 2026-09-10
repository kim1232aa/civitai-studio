# Canvas shell do-now (reuse API) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (or subagent-driven-development) task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Unblock canvas image/video generation UX and visible wiring while reusing existing `/api/generate` + providers; deeper Seko 原版对齐 waits for UI capture pack completion.

**Architecture:** Do not build a second outbound stack. Storyboard already POSTs `/api/graph/compile` then `/api/generate`. Fix shell gates, writeback-to-card, first-frame/wiring visibility against `docs/review-shots/s7-gap.md` + `s7-seko-standard.md`. Recipe desk v0776 stays the reference for “simple generate works.”

**Tech Stack:** `/workspace/civitai-studio` — `static/storyboard.js`, `static/storyboard.html`, `providers/graph_compile.py`, `server.py` storyboard-graph; canon `docs/00-IRON-RULES.md`.

## Global Constraints

- Canon: `docs/00-IRON-RULES.md` (page ↑ only; original params; no unverified Pass; no empty shells pretending done).
- Reuse `/api/generate` + `providers/*`; never second generate outbound.
- No empty hydrate/hard-refresh acceptance theater until bugs fixed.
- C维付费↑ without boss auth = 未验证.
- Boss questions to keep answering with evidence: API reuse; v0776 vs canvas; t2i/i2i/i2v completeness.
- Sequencing: **do-now** below → after UI审查 finishes capture → **deeper 原版对齐**.

**Evidence inputs (already):**
- `/workspace/docs/review-shots/s7-gap.md`
- `/workspace/docs/review-shots/s7-seko-standard.md`
- `/workspace/docs/seko-baseline/`

---

## Phase A — Do now (before deeper Seko polish)

### Task A1: Make “图片生成” path as obvious as v0776

**Files:** `static/storyboard.js`, `static/storyboard.html`

- [ ] Trace Composer default mode on new shot; ensure default is `image` not text/audio/video.
- [ ] When mode is text/audio stub, show clear 未接 and do not look like generate-ready.
- [ ] Soften confusion: if user is on video without first frame, message must say switch to 图片生成 OR attach first frame (already has 缺首帧 — verify copy).
- [ ] Manual check: select shot → 图片生成 → choose Civitai service → ↑ reaches `/api/generate` (no claim Pass).

### Task A2: Canvas writeback lands on originating card (not history-only)

**Files:** `static/storyboard.js` (`writebackResult`, poll path), `server.py` storyboard-graph

- [ ] Reproduce: after successful generate, does `shot.url` set before history-only?
- [ ] Fix poll/`saved[]` wait so card gets `/out/…` (commits o12–o16 trail).
- [ ] Persist via existing `persistServer` PUT `/api/storyboard-graph`; skip empty nodes without silent success.
- [ ] Evidence for later UI: card shows media without requiring 「接到此镜」 for the happy path. **No Pass until UI verifies.**

### Task A3: Visible wiring (源 → 结果)

**Files:** `static/storyboard.js`, CSS in `storyboard.html`

- [ ] Against `s7-seko-07-wiring.png`: implement/restore visible edge between source node and result/九宫格-style result when an edge exists in graph state.
- [ ] Ensure i2i/i2v first-frame link creates a visible connection, not only dock text 「缺首帧」.
- [ ] Manual: two nodes + edge renders a line (screenshot later for Critiquito).

### Task A4: i2v first-frame entry without stealing recipe desk

**Files:** `static/storyboard.js`

- [ ] Match standard: upload/select first frame on video Composer (Seko-like entry).
- [ ] Keep hard gate: no silent steal from recipe desk history as fake first frame unless user pins.
- [ ] Clear path: attach frame → 「首帧已就绪」→ generate via same `/api/generate`.

### Task A5: Text/audio empty shells honesty

**Files:** `static/storyboard.html`, `static/storyboard.js`

- [ ] Keep 未接 labels; do not fake working tabs.
- [ ] Optional later: wire if API supports — **out of do-now** unless trivial; prefer honest shell over fake.

### Task A6: Plan commit + handoff

- [ ] Commit plan + any A1–A5 code with clear messages.
- [ ] Call 代码审查员 before merge main.
- [ ] Do **not** start acceptance burns; wait Phase B.

---

## Phase B — After UI审查抓齐 (deeper 原版对齐)

**Gate:** UI审查员 says capture pack complete (pairs + any missing i2i/i2v HTML detail); Critiquito highest-impact list from final shots.

- [ ] Align Composer capsule / right chat / capability bar to `s7-seko-standard.md` (D维 HTML骨架).
- [ ] Multi-ref slots per provider capabilities table (api对接助手: shell must eat caps).
- [ ] Rotate providers after one honest writeback path.
- [ ] Then UI acceptance: hard refresh writeback + §7 pairs — only then closed-loop count.

---

## Boss Q&A board (keep updated)

| Q | Current evidence answer |
|---|---|
| Why not reuse API? | Canvas **does** reuse `/api/generate`; unfinished is shell. |
| Why v0776 works, canvas doesn’t? | Extra shell gates + writeback often history-only. |
| t2i/i2i/i2v complete? | Wired in compile; not closed-loop Pass; i2i/i2v/shell thin. |

---

## Out of scope now

- Second generate API
- Empty hard-refresh Pass claims
- Full Seko pixel-perfect before UI pack complete
