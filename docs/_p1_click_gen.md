# P1 — Human QA: click 生成 on Fal / Hugging Face / 魔搭

Date: 2026-09-01 (UTC+8)
Studio: http://127.0.0.1:8765/ (hard-refreshed, Ctrl+Shift+R)
Civitai source image: https://civitai.red/images/139791102 (hinablue, "Image posted by hinablue")

## Feature-count check
- Recipe tabs: 7 present — 图片 / 视频 / 超分 / 去背景 / 3D / 音频 / 工作流 ✅
- Backend tabs: were 4 (Civitai / Fal / Hugging Face / 魔搭) at first load; during the session the
  running build changed under me to 5 (Civitai / Fal / Hugging Face / 魔搭 AI / 魔搭 CN). Nothing deleted. ✅

## Result table

| Backend | Service picked | 导入 filled prompt? | 提交中 seen? | Error text | New image in 成片? |
|---|---|---|---|---|---|
| Fal | FLUX.1 [dev] · flux (fal-ai/flux/dev) | YES — prompt filled from the Civitai image | NO — #go stayed "生成" | none on the button; earlier build showed "导入失败 请贴 Fal request id（uuid），或 fal\|endpoint\|uuid，或 endpoint + request_id" for a Civitai URL (later build accepts Civitai links: placeholder "Civitai 图 id / 链接，也可 Fal request id") | NO — dock stayed 7 张; UI jumped to Hugging Face right after the click |
| Hugging Face | (not reached — see blocker) | n/a | not reached | n/a | not reached |
| 魔搭 | (not reached — see blocker) | n/a | not reached | n/a | not reached |

## What actually happened
1. Fal + FLUX.1 [dev] · flux + Civitai URL → 导入 DID populate 提示词 with the real image prompt
   ("A gallant looking japanese woman, makeup. long face, long eyelashes, sideways glance, serious
   expression, white hair, hime cut, yellow jacket, cyberpunk, tech wear, holding gun with one hand,
   aiming at viewer, ..."). Import works.
2. Clicking the red 生成: the button text never changed to 提交中, no queue/status row appeared, and the
   成片 count did not increase. Instead the provider tab flipped from Fal to Hugging Face by itself.
   => Per the literal contract this is a SILENT-CLICK FAIL for Fal.

## BLOCKER (why HF and 魔搭 were not completed)
The running app is being rebuilt / hot-reloaded live while QA is in progress. Observed repeatedly:
- The SPA resets itself back to the Civitai backend every ~15-30 s, wiping the selected provider,
  the selected service and any in-progress selection (screenshots p1-state-reset-loop.png,
  p1-reset-to-civitai.png).
- On each restart a brand new browser tab to http://127.0.0.1:8765/ is opened automatically.
- Catalog sizes and gallery counts changed between reloads (Fal 1492 → 398 → 1492 models;
  成片 7 张 → 12 张 → 4 张), and the backend tab list changed from 4 to 5 and back.
Under these conditions a provider → service → 导入 → 生成 → 90 s wait sequence cannot be completed
reliably. Re-run this QA against a frozen build (stop the watcher/rebuild loop) to get clean results
for Hugging Face and 魔搭.

## Screenshots (/workspace/civitai-studio/docs/review-shots/)
- p1-hinablue.png — the Civitai image page used
- p1-fal-before.png — Fal, FLUX.1 [dev]·flux selected, prompt imported, 生成 looks enabled
- p1-fal-clicked.png — <1 s after clicking 生成: #go still reads "生成", no dock/status change, provider flipped to Hugging Face
- p1-fal-after.png — after wait: #go "生成", dock "成片 7 张" unchanged, status line "Hugging Face 已加载 37 个模型。自己点生成。"
- p1-fal-import-ok.png — proof 导入 fills the prompt on Fal
- p1-state-reset-loop.png / p1-reset-to-civitai.png — the self-reset back to Civitai
