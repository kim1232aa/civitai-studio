# o151/o152 Outbound Debts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix api对接助手 outbound debts without inventing params: (1) Fal schnell must not silently change imported steps 20→12; (2) Nano outbound size must match UI width×height / aspect; (3) confirm Magao seed≫int32 shows warn (o149b), never silent.

**Architecture:** UI honesty first — if provider clamps a value, surface it in Composer before ↑; never rewrite imported steps/size without user-visible reason. Prefer keep original when API accepts it; if API hard-caps, show cap + remaining and send the capped value only after UI reflects it.

**Tech Stack:** static/storyboard.js, providers/fal.py or fal path in graph_compile, providers/nanogpt.py, scripts/test_o151_*.js, scripts/test_o152_*.js

---

### Task 1: o151 Fal schnell steps silent clamp

**Files:**
- Modify: `static/storyboard.js` (service rematch / afterImport / buildGraph steps)
- Modify: fal catalog or clamp helpers if steps max lives server-side
- Test: `scripts/test_o151_fal_schnell_steps_no_silent_clamp.js`

**Steps:**
1. Reproduce: import post with steps=20, house=Fal, service=flux/schnell → outbound steps becomes 12 without UI change.
2. Find clamp (likely schnell max_steps=12 or default overwrite on rematch).
3. Fix: either keep 20 if API accepts, OR when rematching to schnell set `#steps` to 12 **and** show visible hint「schnell 上限 12，已从原帖 20 改为 12」— never silent.
4. Unit test: import fixture steps=20 + select schnell → UI steps and outbound agree; if clamped, hint present.
5. Commit `o151 fix(fal): no silent steps clamp on schnell` + push main + bump stamp.

### Task 2: o152 Nano aspect/size mismatch

**Files:**
- Modify: `providers/nanogpt.py` and/or storyboard Nano payload builder
- Test: `scripts/test_o152_nano_aspect_matches_size.js` (+ py if server maps)

**Steps:**
1. Reproduce: UI 768×1344 → outbound `aspect_ratio=1:1` + `size=720*1280`.
2. Map UI w/h → Nano size token and aspect consistently (portrait → matching aspect, not 1:1).
3. Do not invent defaults; if UI has w/h, derive both fields from that; if only one, don't invent the other.
4. Test + commit `o152 fix(nano): align aspect_ratio with size from UI` + push + stamp.

### Task 3: Magao seed warn verify (no new feature if o149b ok)

**Files:** read-only check `static/storyboard.js` o149b path

**Steps:**
1. Confirm seed ≫ int32 shows「超魔搭区间」warn and does **not** block `#send`.
2. Confirm outbound omits seed (API) while UI still shows original seed + warn.
3. If silent (no warn), tip o149c; else mark verify done in MANIFEST note only.

**Done when:** o151+o152 on main with tests green; api can re-audit Fal schnell + Nano size; closed-loop still 0; no review call.
