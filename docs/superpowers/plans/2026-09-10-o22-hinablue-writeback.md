# o22 hinablue writeback harden Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans task-by-task.

**Goal:** Harden canvas outbound + writeback for a *fresh* hinablue Civitai import (any new image id). Do not lock acceptance to fixture `142210587`. Keep jobId/backend fail capture. closed-loop stays 0.

**Architecture:** Reuse single `/api/generate`. Import → applyImport → Composer → compile → packLoras/packComfy(+diffusionModel) → POST → poll saved[] → writebackResult → persist + persistServer(keepalive).

**Tech Stack:** `static/storyboard.js`, `static/storyboard.html`, `scripts/test_storyboard_graph.py`. Canon: `docs/00-IRON-RULES.md`.

## Constraints
- No curl `/api/generate` as acceptance.
- NEVER invent Pass / 可交付 / 请审. closed-loop = 0.
- Do not break o21 jobId/backend fail paths.
- Keep single ↑ only.
- 142210587 = optional non-acceptance unit fixture only.

## Tasks
1. Wire diffusionModel from import → outbound (generic hinablue).
2. CDN writeback honesty after materializing poll.
3. Demote 142210587 from acceptance posture.
4. Lightweight visual P0: UI 参考 count includes own chip; send-path excludes own url.
5. Stamp v0821o22-hinablue-wb + tests + commit + push + report.
