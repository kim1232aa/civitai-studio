# o43 Fal flux-2/edit maxRefs=4 (official)

**Symptom:** Fal page↑ `fal-ai/flux-2/edit` 灌满 9/9 → queue accept then **Fal HTTP 422**: `Number of image URLs must be less than or equal to 4` (request `01a08be3-dfcf-7d41-af91-eee76deb56da`). Audit nRefs=9.

**Cause:** Provider default `maxRefs=9` / catalog overlay left flux-2/edit at 9; official Fal validation for this endpoint is **≤4**.

**Fix stamp `v0821o43-fal-flux2-edit-maxrefs4`:**
1. OpenAPI/catalog overlay: set `fal-ai/flux-2/edit` (and siblings that share the same constraint if schema says so) `maxRefs`/`max_input_images` = **4** — tighten-only from official schema, do not invent lower.
2. 灌满/UI/gate must read model cap (4), not provider 9 → 参考 4/4 exact.
3. Re-verify other `*/edit` rows that advertise 9: if openapi says ≤4/≤N, clamp; if schema truly allows 9, leave.
4. Verify: page↑ flux-2/edit 灌满 → 4/4 → outbound `image_urls.length==4` → job succeeds (or non-422). Soft-fail if still 422 with clearer detail.

**Do not:** cut UI slots below official; curl as acceptance; claim closed-loop.
