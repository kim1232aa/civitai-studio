# Plan: AIImageStudio → Fal page↑ burn

## Goal
Closed-loop knife (not yet deliverable Pass): import unused AIImageStudio image, page-click ↑ on **Fal** backend with **original** imported prompt/params/LoRA (no rewrite), hand jobId to api对接助手 for outbound proof.

## Sample (locked)
- Author: https://civitai.red/user/AIImageStudio/images
- Image id: `28978604` (unused in closed-loop packs)
- Import: `https://civitai.com/images/28978604`
- Expect: original prompt + LoRA present; strength may be missing → UI shows「未填」, **never invent 0.8**

## Provider
Fal (换家 — not Civitai-only)

## Tasks
1. Confirm :8765 up; HEAD has o23/o25 tips if needed for import maps (Fal path separate).
2. Page only: open `/storyboard`, clear/import `28978604`, switch backend to Fal, verify Composer shows original prompt + LoRA.
3. Click ↑ once; capture jobId + distinct screenshots (import / composer / after-gen) — MD5 unique.
4. Send jobId + image id to api对接助手; they verify Fal outbound prompt + LoRA path.
5. Do **not** claim closed-loop Pass until outbound + card writeback + hard-refresh evidence.

## Anti
- No curl `/api/generate`
- No short/custom prompt
- No reuse of 136802026 / 142210587 / 19201654 / hinablue as designated samples
- No invent strength
