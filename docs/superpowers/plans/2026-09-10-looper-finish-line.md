# Civitai Studio Looper Finish Line Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use executing-plans / fleet knives. Goal owner: Agent Looper. Code edits: civitai 开发 / Grok Build.

**Goal:** Keep fleet finish line honest per `docs/00-IRON-RULES.md` — original-post page ↑ closed loops across enabled providers; then Seko §7 gaps.

**Architecture:** Looper freezes Pass criteria only; does not edit code or click UI. Reviews stay with 代码审查员 / UI审查员 / Critiquito.

**Tech Stack:** `/workspace/civitai-studio`, page `http://127.0.0.1:8765`, providers Fal/Civitai/HF/魔搭/Nano.

---

### Task 1: Freeze Pass criteria (Looper)

**Pass means:** page ↑ + imported original prompt/params/LoRA outbound + media on original shot card after hard refresh.

**Fail means:** short/SFW/custom prompt, curl generate, history-only writeback, empty shells, feature cuts, unverified assertions.

### Task 2: Track current Civitai sample evidence

Sample primary `142210587` (@3203007 strength 1). Outbound claimed Pass — require UI writeback shots before counting closed loop.

### Task 3: Multi-provider rotation

After one honest provider writeback, next knife advances HF / 魔搭 / Nano — no Civitai+Fal tunnel vision.

### Task 4: Seko step 2 (after API straighten)

§7 paired shots (Seko baseline first). 大白话 before any cut/complete. No empty chrome Pass.
