# o38 pack diffusionModel from generate shot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: executing-plans. Steps use checkbox (`- [x]`) syntax.

**Goal:** Civitai flux1 page↑ must outbound `diffusionModel` (→ server `diffuserModel`) from the **imported shot**. Audit `2026-09-10T13:39:29` / `13:40:07`: serviceId=`image/sdcpp/flux1/createImage`, promptLen=446, nLoras=1, keys **缺少 diffusionModel**（有 checkpointName/ecosystem/loras）→ upstream 400 `missing … 'diffuserModel'`. jobId=null. Closed-loop **0**.

**Evidence:**
- `/api/import?q=28533250` still returns `diffusionModel=urn:air:flux1:checkpoint:civitai:1752722@1983609` + LoRA@823089@0.7
- Same payload without dm → 400; with REST air as diffuserModel → shape OK (api对接助手)
- Prior success `13:00:38` **had** `diffusionModel` in keys → regression is pack/hydrate path, not poll (o37)

**Architecture:**
1. `packComfyParamsForPayload(shot)` must prefer the **generate** shot (runShotStepWork’s `shot`), not only `state.selected` / `lastComposerShot`.
2. After merge, if `shot.diffusionModel` set → ensure `payload.diffusionModel` (no silent drop).
3. `applyImport`: **do not** `delete shot.diffusionModel` (or cn/eco) when import JSON omits the key — only assign when present (prevent wipe races).
4. Preflight for civitai `*/flux1/*` (or sid needing diffuser): if no dm on shot/payload → hard fail before POST（诚实红字，不假跑）.
5. Stamp `v0821o38-dm-pack-shot`; push tip; **do not** claim closed-loop; no curl generate acceptance; no prompt/strength invent.

**Tech Stack:** `static/storyboard.js` packComfy + applyImport + runShotStepWork; optional tiny storyboard graph / node test.

---

### Task 1: Failing test
- [x] Assert pack/outbound includes `diffusionModel` when generate shot has AIR and selected is wrong/empty.
- [x] Assert applyImport with j missing `diffusionModel` does **not** wipe existing shot.diffusionModel.
- [x] Assert flux1 without dm → blocked before generate (message mentions diffusionModel / diffuser).

### Task 2: Fix + tip
- [x] Implement (1)–(4); stamp `v0821o38-dm-pack-shot`; push `feat/cloud-nodes-poc`; report hash.
- [x] Hand back for hard-refresh + fresh 28533250 page↑ (api 核出站 dm; 开发证自动写回，禁接到此镜).

**Done when:** tip hash; tests green for o38; closed-loop still 0 until auto writeback evidenced.
