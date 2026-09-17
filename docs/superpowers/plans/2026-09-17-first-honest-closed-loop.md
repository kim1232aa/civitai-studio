# First Honest Product Closed-Loop Evidence Pack Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce the first honest **product** closed-loop evidence pack (not tip): page ↑ with full imported original-post params, outbound proof, media on the **original** shot card after hard refresh — Pass default **False**.

**Architecture:** Burn-first on one already-tip house (Civitai). Writeback path o146/o153/o154 is already on `main`; product closed-loop is still **0** because tip packs keep `Pass=False` and Looper requires iron §3 + eyeball, not Phase-1 tip stacking. Next knife = unused AIImageStudio t2i page↑ burn + complete evidence pack under `docs/review-shots/closed-loop/`. Only open a **code** knife if this burn proves a concrete writeback/hydrate regression.

**Tech Stack:** Civitai Studio (`server.py` :8765), `static/storyboard.js`, Playwright page↑ (`scripts/page-up-op.mjs` / burn harness), `.cursor/loops/hard-gate-closed-loop/verify.sh`, Seko paired shots (node Composer dock — never Agent welcome).

**Spec:** `docs/00-IRON-RULES.md` §1–§3 + §7; `.cursor/loops/hard-gate-closed-loop/GOAL.md` (product 闭环=0 until iron hard gate + six-provider pillars; tip≠验收).

## Global Constraints

- Branch: **ONLY `main`**. No `feat/*` / `fix/*` / agent branches.
- Closed-loop = page ↑ + full imported original post params outbound + media on **ORIGINAL** shot card after hard refresh. Anything less keeps product count at **0**.
- NEVER curl `/api/generate` as acceptance. NEVER shorten acceptance prompts. NEVER invent strength/defaults or silent model/LoRA swaps.
- Civitai `strength=null`: match-missing is missing — do not invent 0.75/1.0.
- 魔搭/HF matching: no approximate sibling swap; match or say so.
- Pass default **False**. Do not claim Pass / 验收 / product closed-loop++. Tip ≠ 验收.
- Seko: live node Composer dock (禁 Agent「新对话 Beta」欢迎页); seko-03↔04 visdiff honest; no reuse of void/cross-pack Seko PNGs as same-flow.
- Prefer burn evidence over Phase-1 i2i→i2v tip stacking while product gate is still 0.

### Writeback path (must all succeed)

| Step | Where | What must succeed |
| --- | --- | --- |
| 1. Page ↑ | `static/storyboard.js` Composer `#send` → `POST /api/generate` | Real click; original prompt/params/LoRA; house-first `civitai` |
| 2. Job poll | `GET /api/jobs/<id>` in `server.py` (~1551–1580) | Upstream done; media materialized |
| 3. Media save | `server.py` `saved.append` → `/out/<job>_0.jpg` (~992, ~1030) | Bytes on disk under `/out/` |
| 4. Server belt | `apply_pending_job_to_graph` (`server.py:138`) → `pendingWriteback` (~1578–1580) | Graph/pending carries `/out` URL for originating shot |
| 5. Client writeback | poll → `writebackResult(shot, url)` (`storyboard.js:9061`) | Sets `live.url` to `/out/...`; demotes import asset (`importSourceUrl` / `_demotedAfterGen`) |
| 6. Card pixels | `patchShotCardMediaDom` (`storyboard.js:9178`, o154 blob ObjectURL) | Visible face pixels match `/out`, not import CDN |
| 7. Persist | `persist` + `persistServer` + `persistActiveCanvas` (`storyboard.js:1806`) | Canvas project PUT keeps shot.url |
| 8. Hard refresh | `hydrateFromServer` (`storyboard.js:2155`, o146 canvas-scoped) + `mergeAdoptShotUrls` (`:1946`) | After reload, **same original shot id** still shows this burn’s `/out` (no Magao house resurrect) |

### Chosen burn target

| Field | Value |
| --- | --- |
| House | **Civitai** (tip house; `hasKey=true`; avoid HF 402) |
| Sample | **AIImageStudio `28386611`** — unused (no pack dir); same family as tip `28978240` |
| Import shape | `image/sdcpp/flux1/createImage` · promptLen **470** · 832×1216 · steps 20 · cfg 3.5 · LoRA Kolors Asian face `…730162@819842` strength **0.7** (imported, not invented) |
| Pack dir | `docs/review-shots/closed-loop/civitai-28386611-t2i-closed-o154-seko/` |
| Why not `134923572` | Boss-named fixture, but docs record product deadlocks (Civitai `strength=null` / 魔搭 Hub-LoRA / HF sibling) — wrong first knife for product 0→? |
| Why not HF | tip=0 honest 402 (`hf-119393527-t2i-closed-seko`) |

### Top blockers keeping product closed-loop at 0 (ranked)

1. **Acceptance gap (tip≠产品闭环)** — `verify.sh` already PASS on packs like `civitai-28978240-t2i-closed-o154-seko2/`, but MANIFEST `Pass=False` and Looper tip notes say ≠验收. GOAL: product 闭环 stays **0** until iron hard gate + six-provider pillars. Phase-0 tip stacking / Phase-1 i2i→i2v does not bump product count.
2. **Card face = import not `/out` (historical + eyeball gate)** — `_invalid-civitai-28386610-t2i-closed3-card-is-original-not-out/VOID.md`: job `/out` was singer; card PNG stayed floral import; `afterSrc=None`; NCC≈0. o153/o154 fixed paint path; product still needs a **new** burn where Looper eyeballs card≡/out after HR.
3. **Seko / hard-refresh honesty voids** — e.g. `magao-ai-119393360` `seko_paired_contrast: no` (Agent welcome / visdiff); `_invalid-magao-ai-119393358-t2i-true-soft-hardrefresh` soft HR; Fal Agent-modal fake paired. Soft or fake Seko keeps Fail.

**Recommended first knife:** **burn-first** (Tasks 1–4). Code knife only if burn proves writeback/hydrate still broken (Task 5 contingency).

---

### Task 1: Preflight (stamp, house, unused sample)

**Files:**
- Read: `docs/00-IRON-RULES.md`, `.cursor/loops/hard-gate-closed-loop/GOAL.md`, `docs/review-shots/closed-loop/_template/MANIFEST.md`
- Read: `static/storyboard.js` stamp header (~46–56 o153/o154)
- Test: none yet

**Interfaces:**
- Consumes: server `http://127.0.0.1:8765`, providers with keys
- Produces: confirmed HEAD stamp ≥ o154; sample `28386611` import recipe logged (full prompt length, LoRA air+strength)

- [ ] **Step 1: Confirm main + server**

```bash
cd /workspace/civitai-studio
git branch --show-current   # must be main
git log -1 --oneline        # note HEAD
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8765/storyboard.html  # 200
curl -s http://127.0.0.1:8765/api/providers | python3 -c "import sys,json;d=json.load(sys.stdin);print([(i['id'],i.get('hasKey')) for i in (d.get('items')or d)])"
```

Expected: `main`; storyboard 200; `civitai hasKey=True`. HF may be keyed but 402 on generate — do not choose HF.

- [ ] **Step 2: Confirm sample unused + full import**

```bash
ls docs/review-shots/closed-loop/ | rg '28386611' || echo 'OK unused'
curl -s http://127.0.0.1:8765/api/import-image/28386611 | python3 -c "import sys,json;d=json.load(sys.stdin);print(d.get('serviceId'),len(d.get('prompt')or''),d.get('loras'))"
```

Expected: no existing pack dir; promptLen=470; LoRA strength 0.7 present (do not rewrite).

- [ ] **Step 3: Stop if preflight fails**

If Civitai key missing or import empty prompt → record blocker in pack NOTES and stop (no Pass, no curl generate workaround).

---

### Task 2: Page↑ burn on Civitai (original params only)

**Files:**
- Create: `docs/review-shots/closed-loop/civitai-28386611-t2i-closed-o154-seko/` (shots + `report.json`)
- Use: Playwright page↑ harness (`scripts/page-up-op.mjs` or existing burn script). **No** `curl -X POST /api/generate`.

**Interfaces:**
- Consumes: import `28386611`, house-first backend `civitai`, service `image/sdcpp/flux1/createImage`
- Produces: `job_id`, outbound audit (promptLen, seed, steps, cfg, w/h, nLoras, lora air+strength), `/out/<job>_0.jpg`

- [ ] **Step 1: New canvas + import**

Open storyboard → new burn canvas named `civitai-28386611-t2i-closed-o154-seko` → import `https://civitai.com/images/28386611` (or studio import id) → select house **Civitai** first → confirm Composer shows full original prompt (len 470), LoRA chip strength 0.7, size 832×1216. Screenshot `composer-mounted.png`.

- [ ] **Step 2: Page click ↑ only**

Click `#send`. Capture network: POST `/api/generate` status + body keys (prompt length, loras, diffusionModel/serviceId, backend=civitai). Screenshot `outbound-or-job.png` with job id visible or from audit log.

Forbidden: shortened prompt, SFW rewrite, provider swap to Fal/HF, inventing strength, curl generate.

- [ ] **Step 3: Wait poll → `/out`**

Poll until saved URL `/out/<jobId>_0.jpg` exists on disk. Record job id + out path + out md5 in `report.json`.

- [ ] **Step 4: Commit progress checkpoint (optional docs-only)**

Only if parent asks; default **no commit** from this audit plan. Burn agent may commit evidence later on main.

---

### Task 3: Original-card writeback + hard refresh proof

**Files:**
- Modify/create in pack: `card-after-gen.png`, `card-after-hard-refresh.png`, `card-media-crop.png`, `card-media-crop-hr.png`, `local-contrast-same-flow.png`, `report.json`
- Code touch: **none** unless failure (see Task 5)

**Interfaces:**
- Consumes: `writebackResult` + `patchShotCardMediaDom` + `persistActiveCanvas` + `hydrateFromServer`
- Produces: DOM `data-face-url` = `/out/...` on **same** shot id before and after hard refresh; blob/NCC match out; `cardShowsNewMedia=true`, `hardRefreshOk=true`

- [ ] **Step 1: Hide Composer; shoot card-after-gen**

Same framing full original shot card. Confirm face is new media (not import still). Prefer pixel check: card crop NCC vs `/out` ≫ vs import thumb; `data-face-url` starts with `/out/`.

- [ ] **Step 2: Hard refresh (real reload)**

Full browser reload of the burn canvas URL (not soft re-render). Confirm o146: canvas-scoped hydrate must **not** `applyGraph(house)` Magao dirt. Same shot id; `data-face-url` still this job’s `/out/...`.

- [ ] **Step 3: Shoot card-after-hard-refresh**

PNG md5 of card-after-gen vs card-after-hard-refresh should differ as two real captures (verify.sh rejects identical files). Both must show `/out` media.

- [ ] **Step 4: local-contrast-same-flow.png**

Full-page local UI (not a copy of the card crop).

- [ ] **Step 5: Record honesty flags in report.json**

```json
{
  "cardShowsNewMedia": true,
  "hardRefreshOk": true,
  "afterFaceUrl": "/out/<job>_0.jpg",
  "hrFaceUrl": "/out/<job>_0.jpg",
  "blobByteMatch": true,
  "importMd5": "<import>",
  "outMd5": "<out>",
  "shotId": "<original shot id>"
}
```

If any flag false → Fail pack; go Task 5 before claiming tip even.

---

### Task 4: Seko paired contrast + MANIFEST (Pass=False)

**Files:**
- Create: pack `MANIFEST.md`, `seko-01.png`…`seko-04.png`, `seko-baseline-same-flow.png`
- Read: `docs/review-shots/closed-loop/_template/MANIFEST.md`, iron §7

**Interfaces:**
- Consumes: live Seko `https://seko.sensetime.com/my-space?tab=canvas` (logged-in canvas with nodes)
- Produces: verify.sh-satisfying declarations; Pass **False**

- [ ] **Step 1: Capture Seko same-flow (same session as burn if possible)**

1. seko-01 — myspace?tab=canvas list  
2. seko-02 — content canvas with nodes (Agent closed)  
3. seko-03 — **node bottom Composer** (图片生成 + prompt + ↑) — NOT Agent welcome  
4. seko-04 — generating/result state visually different from 03 (visdiff ≥ ~8)

- [ ] **Step 2: Write MANIFEST.md declarations**

Must include exactly (verify.sh):

```text
provider: civitai
sample_id: 28386611
job_id: <real job id>
original_prompt: yes
curl_generate: no
short_or_sfw_prompt: no
writeback_original_card: yes
hard_refresh_ok: yes
seko_paired_contrast: yes
seko_baseline_path: docs/review-shots/closed-loop/civitai-28386611-t2i-closed-o154-seko/seko-baseline-same-flow.png
```

Header: **判定：Pass=False**（候 Looper；不喊验收；tip≠产品闭环）.

- [ ] **Step 3: Run verify.sh**

```bash
bash .cursor/loops/hard-gate-closed-loop/verify.sh 2>&1 | rg '28386611|PASS pack|FAIL: closed-loop|OK:'
```

Expected: `PASS pack: .../civitai-28386611-t2i-closed-o154-seko/` appears. Still **do not** self-write product Pass or bump closed-loop count.

- [ ] **Step 4: Hand path to Looper**

Deliver pack path only. Looper eyeballs card≡/out + Seko node Composer. Product closed-loop 0→1 only if Looper says so under iron gate — not agent self-score.

---

### Task 5: Contingency code knife (only if burn proves bug)

**Files (only if needed):**
- Modify: `static/storyboard.js` (`writebackResult` ~9061, `patchShotCardMediaDom` ~9178, `hydrateFromServer` ~2155, `persistActiveCanvas` ~1806)
- Modify: `server.py` (`apply_pending_job_to_graph` ~138, job poll pendingWriteback ~1578)
- Test: extend `scripts/test_o153_result_writeback_original_card.js` / `scripts/test_o146_canvas_hydrate_scope.js` / `scripts/test_o154_*`

**Interfaces:**
- Consumes: failing burn report (`afterFaceUrl` empty, card≡import, HR resurrects house graph, etc.)
- Produces: minimal fix + stamp bump + **new** unused-sample reburn (never reuse failed sample as Pass)

- [ ] **Step 1: Classify failure from report**

| Symptom | Likely locus |
| --- | --- |
| `/out` on disk but card shows import | `writebackResult` / `patchShotCardMediaDom` / import demote |
| Card OK then HR → Magao/other graph | `hydrateFromServer` canvasScoped (o146 regression) |
| Card OK then HR → empty / wrong shot | `persistActiveCanvas` / `mergeAdoptShotUrls` |
| No `/out` / no pendingWriteback | `server.py` materialize / `apply_pending_job_to_graph` |

- [ ] **Step 2: Write failing regression test first**

Reproduce the exact honesty failure in `scripts/test_oNN_*.js` (DOM face url / hydrate scope). Run → FAIL.

- [ ] **Step 3: Minimal fix on main**

No new gates; no prompt/strength invention; no feature cuts. Stamp bump in `storyboard.js` header.

- [ ] **Step 4: Reburn on a fresh unused id**

Do **not** reuse `28386611` if it was tainted by partial state; pick next unused AIImageStudio flux1 post via import probe. Repeat Tasks 2–4. Pass still False.

- [ ] **Step 5: Commit only when parent ships**

```bash
git add static/storyboard.js scripts/test_oNN_*.js
git commit -m "$(cat <<'EOF'
fix(storyboard): closed-loop writeback honesty for original card HR

EOF
)"
```

Default for this plan file author: **no commit**.

---

## Self-review

1. **Spec coverage:** Iron §3 writeback + §1 page↑ original params + §7 Seko paired → Tasks 2–4. Global Constraints copied. Pass default False.  
2. **Placeholders:** Sample id, paths, function:line, verify commands are concrete.  
3. **Consistency:** Pack name `civitai-28386611-t2i-closed-o154-seko` used throughout; house Civitai; burn-first before code.

## Execution handoff

Plan complete and saved to `docs/superpowers/plans/2026-09-17-first-honest-closed-loop.md`.

Recommended: **burn-first** (Tasks 1–4) on Civitai + `28386611`. Do not start Phase-1 i2i→i2v tip stacking while product closed-loop is 0. Code knife only on proven writeback failure.
