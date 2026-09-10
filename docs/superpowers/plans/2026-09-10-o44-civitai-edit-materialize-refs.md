# o44 Civitai editImage materialize /out refs

**Symptom:** Civitai `image/sdcpp/flux1/editImage` 灌满 9/9 → 400 `One or more validation errors occurred.` / `Input image failed to decode Base64 data.`

**Evidence (repro 2026-09-10):** `submittedInput.images` = `["/out/fill-cap-1.jpg", …]` raw paths — Civitai cannot fetch localhost; expects Base64/data URL (or hosted URL).

**Fix stamp `v0821o44-civitai-edit-materialize-refs`:**
1. Before POST, materialize every `/out/…` (and relative local) entry in `images` / `referenceImages` / `sourceImage` / `firstFrame` via existing `materialize_local_refs` / `local_out_to_data_url` — same as Fal/Nano.
2. Fail-closed if any local file missing (never drop silently).
3. Keep official maxRefs clamp; do not invent lower caps.
4. Audit: nRefs + note whether images were data: URLs (length only).
5. Verify: page↑ editImage 灌满 N/N → no Base64 decode error; jobId or clearer upstream error; api 核 images are data/http not `/out`.

**Also note (separate debt, don’t invent):** shot `diffusionModel` currently checkpoint AIR mapped to `diffuserModel` — may need diffuser AIR per o35; only fix if still failing after materialize.

**Do not:** curl as acceptance; claim closed-loop.
