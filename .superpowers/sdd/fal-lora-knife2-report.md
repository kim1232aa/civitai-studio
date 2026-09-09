# Fal LoRA knife ② report — v0821o-fal-lora

**Date:** 2026-09-08 (Asia/Shanghai)  
**Branch:** `feat/cloud-nodes-poc`  
**Stamp:** `v0821o-fal-lora` / STORE `nl-storyboard-v0821o`

## Goal

Hard-gate Fal **image** + LoRA (not MiniMax i2v): auto-mount `fal` + `fal-ai/z-image/turbo/lora` with LoRA http path so UI hard-refresh + ↑ works without hand edits. Outbound must include `loras[].path` (http) + `scale` 0.8.

## P0 silent fails closed

| Failure | Fix |
|---|---|
| AIR-only chips (`urn:air:…`) with no http path → body missing `loras[]` while chips visible | `packLorasForPayload` fal filter requires `isHttpUrl(path) && !looksAir(path)`; `chipsLackAirForOutbound` + `outboundLoraBlockMsg()` → red **「LoRA 缺 http path，无法出站」** |
| Drift to Civitai `image/…` service | `applyImport` `wantFal` forces `backend=fal`, rejects `looksCivitaiServiceId(sid)` |

## API contract

- `backend: "fal"`
- `serviceId: fal-ai/z-image/turbo/lora` (pin; sibling rewrite still available for plain `…/turbo`)
- Fixture: `versionId` **3231694**, `path=https://civitai.com/api/download/models/3231694`, `scale|strength` **0.8**
- Outbound shape: `{ "prompt": "…", "loras": [{ "path": "https://civitai.com/api/download/models/3231694", "scale": 0.8 }] }`
- Scale clamp `[0,4]` (existing `clampLoraScale` / `_clip_lora_scale`)

## How UI mounts the fixture (no hand edits)

1. **Import modal button** `#btnFalLoraFix` — 「Fal LoRA夹具」
2. **Query / hash auto-mount:** `?fixture=fal-lora` or `#fal-lora` / `#fal-lora-fixture` on boot
3. **Programmatic:** `mountFalLoraFixture()` → `applyImport(falLoraFixtureImport())`

After mount, STORE persists; hard-refresh keeps fal + service + LoRA chip; ↑ packs `loras[{path,scale:0.8}]`.

## Files touched

- `static/storyboard.js` — STORE, pack fal path filter, gate msg, `applyImport` wantFal, fixture helpers, boot query
- `static/storyboard.html` — stamp + script `?v=` + `#btnFalLoraFix`
- `scripts/test_storyboard_graph.py` — stamp bump + `test_v0821o_fal_lora_knife` (+ n2 msg assert via `outboundLoraBlockMsg`)
- `providers/fal.py` — unchanged (already `_fal_lora_path` / `apply_fal_loras` / `fal_lora_sibling`)

## Tests

`python3 scripts/test_storyboard_graph.py` → **44 / 44** ok.

## Server

Restarted on `127.0.0.1:8765`; `/storyboard` serves `v0821o-fal-lora` + `btnFalLoraFix`. Did **not** curl `/api/generate`.

## Out of scope

HF / 魔搭 / Nano; MiniMax i2v; gates/stageUrls.
