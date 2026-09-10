# o45 Magao Edit-2509 maxRefs=3 (restore official) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: executing-plans. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Stop silently clamping `Qwen/Qwen-Image-Edit-2509` to maxRefs=1. Official docs: `image_url` list, **1–3**. o39 tip admitted clamp-to-1; boss/开发: that is capability gutting — restore official 3.

**Evidence:**
- `MODELSCOPE_REF_POLICY["Qwen/Qwen-Image-Edit-2509"].maxRefs = 3` already recorded
- Provider ceiling `modelscope-ai`/`modelscope-cn` maxRefs=1 + catalog-may-only-tighten → 2509 cannot raise to 3
- `static/storyboard.js` `PROVIDER_REF_CAPS` same ceil=1
- Outbound already: `body["image_url"] = refs[0] if len(refs)==1 else refs` (list OK)

**Architecture:** Raise Magao **provider ceiling** to 3 (official max across known AIGC image_url list). Catalog/policy still **tightens** per model (Edit=1, t2i=1, Edit-2509=3). Never invent models; never raise above official 3; other providers unchanged.

**Stamp:** `v0821o45-magao-edit2509-refs3`

---

### Task 1: Failing tests
- [ ] Edit-2509 catalog/resolve → maxRefs=3; UI capacity 3; outbound bag length can be 3
- [ ] Qwen-Image-Edit (non-2509) still maxRefs=1
- [ ] t2i Magao still does not eat refs / maxRefs policy unchanged

### Task 2: Fix + tip
- [ ] `providers/capabilities.py` PROVIDER_CAPS modelscope-ai/cn: maxRefs/maxImages ceiling **3**; update comments (catalog tightens; 2509 can reach 3)
- [ ] `static/storyboard.js` PROVIDER_REF_CAPS modelscope-*: maxRefs **3**
- [ ] `providers/ref_images.py` sync comment/default if needed
- [ ] Ensure resolveRefCaps does not force singular→1 when catalog says 3 and schema accepts list (`image_url` list for 2509)
- [ ] Stamp `v0821o45-magao-edit2509-refs3`; push `feat/cloud-nodes-poc`; report hash
- [ ] No curl generate; closed-loop 0; hand burns to 开发

**Done when:** tip hash; Edit-2509 maxRefs=3 in resolve + tests green.
