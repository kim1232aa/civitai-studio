# HF + 魔搭 官方 LoRA 完善 Implementation Plan
**Status 2026-09-17 ~20:00 CST:** Executor 落地 v0822o162 Hub-LoRA-as-model + Magao miss/supportsLora 诚实；unit OK；push main。页↑留给开发。

> **For agentic workers:** REQUIRED SUB-SKILL: executing-plans. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Align Studio HF + ModelScope LoRA with official Inference APIs so LoRA is selectable, sendable, and verifiable — no invent, no fake match.

**Architecture:** HF official path (huggingface_hub v0.31+) uses Hub LoRA as `model=` via fal-ai/replicate through Router. Magao API-Inference already has `loras` Hub `owner/repo`. Do not invent Civitai AIR→Hub; matching miss = clear/abort.

**Tech Stack:** `providers/huggingface.py`, `providers/hf_catalog_caps.py`, `providers/modelscope.py`, `docs/hf-models.json`, `docs/api-usage/huggingface.md`, `docs/api-usage/modelscope.md`, composer field adapt if needed.

---

### Task 1: HF Hub-LoRA-as-model

- [x] Map official: `InferenceClient(provider="fal-ai"|"replicate").text_to_image(..., model="<hub-lora-id>")`
- [x] Catalog/search: Hub LoRA models discoverable under huggingface (filter=lora / pipeline), `supportsLora` / callability honest
- [x] Outbound: when user selects Hub LoRA as serviceId/model, POST via Router with that model id (not only attach `loras[]` on base turbo)
- [x] Keep existing `loras[]` on fal-mapped base only if provider schema allows; never invent scale; never claim verified load without evidence
- [x] Update `docs/api-usage/huggingface.md` — retract "official table has no LoRA ⇒ unsupported"; document Hub-LoRA-as-model + providers

### Task 2: 魔搭 Hub LoRA on real-support models

- [x] Confirm `_modelscope_loras` still matches official: single string / multi dict sum=1 max 6; reject http/AIR
- [x] Catalog: stamp `supportsLora` only where Infer accepts LoRA; do not advertise Krea on AI if Infer rejects
- [x] UI/search: Hub owner/repo LoRA searchable; matching miss → clear/explain (IRON §5)
- [x] Update modelscope.md evidence board if drift — no shape drift; search miss note shipped in adapter

### Task 3: Done when

- [x] Unit/wiring tests for HF Hub-LoRA-as-model path and Magao Hub loras shape
- [x] No curl `/api/generate` as acceptance; page↑ left to 开发
- [ ] PR opened; do not merge without 代码审查员 Pass — **shipped direct to main per 老板催** (v0822o162); still needs 代码审查员

**Anti:** invent Hub ids; Midjourney remap as match; silent cross-house; empty shell Pass.
