# Capsule/Composer 锚底自适应 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans. Steps use checkbox (`- [x]`) syntax.

**Goal:** Fix boss-screenshot capsule/Composer wrong vs Seko — truncated「图…/视…」, orphan empty slots, mid-canvas float — with **锚底自适应** (width follows content, stick bottom / selected-node-aware). FORBIDDEN: revert to earlier full-width bottom-bar chrome. closed-loop stays 0; NEVER 可交付.

**Architecture:** Prefer `static/storyboard.html` + `static/storyboard-ui.css` + `positionDock()` in `static/storyboard.js`. Do not fight outbound/serviceId (o23 tip already landed). Keep single ↑ (`#send` only).

**Tech Stack:** `/workspace/civitai-studio` feat/cloud-nodes-poc; canon `docs/00-IRON-RULES.md`; Seko evidence `/workspace/docs/review-shots/s7-seko-*` + `seko-baseline/` (reuse, no re-capture).

## Global Constraints

- Seko = baseline; local = under test.
- No mid-knife review / 可交付 / 请审.
- Stamp `o23+/capsule` (e.g. `v0821o23b-capsule` or `v0821o24-capsule`).
- Prefer storyboard.html/css + capsule layout JS; avoid serviceId/outbound churn.

---

### Task 1: Full mode labels (no「图…/视…」)

**Files:** `static/storyboard.html`, `static/storyboard-ui.css`

- [x] Remove ellipsis truncation on `.modes button` (no `overflow:hidden` + `text-overflow:ellipsis` + `min-width:0` that clips 图片生成/视频生成).
- [x] Mode chips `flex: 0 0 auto` / `white-space: nowrap`; dock width follows content (`width: fit-content` / measured natural width), not a too-narrow fixed box that forces clip.
- [x] Keep stub 文本/音频 honest with 未接 tag; do not invent fake working tabs.

### Task 2: positionDock 锚底自适应

**Files:** `static/storyboard.js` `positionDock()`

- [x] Default: dock sticks near **bottom** of usable canvas (`area.bottom`), prefer **bottom-right** of selected node (or canvas right if node off-screen) — not mid-float overlay at `area.top`.
- [x] Width = content-driven (measure collapsed/expanded natural width; clamp to area). Height still mode-aware.
- [x] Selected-node-aware: prefer below node when room; else clamp to bottom edge — never orphan mid-canvas float when bottom room exists.
- [x] Do **not** restore full-bleed bottom bar chrome (no `left:0;right:0;width:100%` dock strip).

### Task 3: No orphan empty slots

**Files:** `static/storyboard.js` `renderDock` refs, CSS collapsed rules

- [x] Collapsed capsule: hide empty ref chip row / disconnected empty slots when no refs and not needing frame actions; keep upload/select only when relevant (image refs or video 缺首帧).
- [x] Empty `.refs` must not render as floating disconnected boxes beside the capsule.

### Task 4: Stamp + commit + report

- [x] Bump stamp + `storyboard.js?v=` cache-bust to `o23+/capsule`.
- [x] Keep single ↑; no dual ↑; no debug copy.
- [x] Commit + push; short report under `/workspace/projects/` with hash, stamp, fixed vs open; NEVER 可交付.

## Done when

- Capsule labels full (图片生成/视频生成 readable)
- Composer anchors bottom-right (or selected-node-aware) adaptive, not mid-float
- No orphan empty slots
- Single ↑ kept
- Commit+push stamp o23+/capsule; report under `/workspace/projects/`
