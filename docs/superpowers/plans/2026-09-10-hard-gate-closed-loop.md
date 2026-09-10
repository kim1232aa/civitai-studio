# Hard-gate closed loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: executing-plans / fleet knives. Goal owner: Agent Looper.

**Goal:** Move closed-loop count from 0 → ≥1 with original-params page ↑ writeback evidence pack that makes `bash .cursor/loops/hard-gate-closed-loop/verify.sh` exit 0.

**Architecture:** Workers ship code + page ↑; fill `docs/review-shots/closed-loop/<id>/`. Looper does not edit product code. No second generate stack — reuse `/api/generate`.

**Tech Stack:** `/workspace/civitai-studio`, storyboard UI, providers Fal/Civitai/HF/魔搭/Nano.

---

### Task 1: Finish writeback hard gate (Grok Build / 开发)

Ship until original card keeps media after hard refresh (o19 tip ≠ deliver).

### Task 2: One honest sample burn (开发 + UI审查 + api)

Fresh hinablue post, original prompt/params/LoRA, page ↑ only. api proves outbound; UI shots for composer + card + hard refresh.

### Task 3: Evidence pack

Copy shots + MANIFEST into `docs/review-shots/closed-loop/<provider>-<sampleId>/` per `_template`. Run verify.sh.

### Task 4: Rotate provider

Next knife advances a different enabled provider — no Fal+Civitai-only stacking.

### Task 5: Seko §7 (after count≥1)

Paired shots; 大白话 before cuts/completes.
