# o42 Nano GPT Image Edit: image bag reaches upstream

**Symptom:** page↑ Nano `openai/gpt-image-2.5/flare/edit` with UI 参考 5/5 + readable `/out/fill-cap-*.jpg` → 400 `GPT Image 2.5 Edit requires between 1 and 16 input images.` Audit `14:46:16` keys include `images`/`input_references`, nLoras=0. Local `_image_body` materializes 5 data URLs into `input_references` OK.

**Hypothesis (official docs):**
- Normalized `POST /api/v1/images` wants `input_references` (string URL/data URL or `{type,image_url}` objects).
- OpenAI-compatible `POST .../images/generations` wants `imageDataUrl` / `imageDataUrls` — **not** `input_references`.
- Adapter tries `GEN_IMAGES` then `GEN_IMAGES_OAI` with `_core_image_body(full)` which keeps `input_references` only → OAI path sees **0** images → exact upstream error.
- Edit-capable models may also need `POST /api/v1/images/edit(s)` with `image` / `imageDataUrls`.

**Fix stamp `v0821o42-nano-edit-refs`:**
1. When building OAI fallback body from full: if `input_references` present, also set `imageDataUrls` = same list (and single `imageDataUrl` = first). Do **not** mix both styles on the **same** endpoint request — normalized body keeps only `input_references`; OAI body keeps only `imageDataUrl(s)`.
2. For `*/edit` models (`_looks_like_required_edit`): prefer edit endpoint (`/api/v1/images/edit` or `/edits`) with `imageDataUrls` after/beside normalized path; fail-closed if all paths return empty-image error while local nRefs≥1 (surface `local_nRefs` in error).
3. Audit: log `nRefs`, `endpointTried`, and whether body had `input_references` vs `imageDataUrls` (lengths only, no data URL dump).
4. Verify: Nano flare/edit page↑ with fill-cap 1..5 → jobId non-null; api 核 outbound nRefs==5.

**Do not:** invent LoRA; curl as acceptance; claim closed-loop.
