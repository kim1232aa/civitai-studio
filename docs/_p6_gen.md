# P6 human QA — import https://civitai.red/images/139791102 + 生成 (one session, one hard refresh)

App: http://127.0.0.1:8765/ (v0721). Import succeeded on both Fal and Civitai ("已导入参数,自己点生成。").
Imported params observed: prompt = "A gallant looking japanese woman, makeup. ..." (matches source image), 960x1440, 步数 8, CFG 1, 源图/Choose File = empty.

| # | Backend | Check | Result | Shot |
|---|---------|-------|--------|------|
| 1 | Civitai | selected Z-Image Turbo, not Krea, 源图 empty | INCONCLUSIVE/FAIL — import OK, but selected service could not be confirmed; UI self-switched away from #civitai to #fal without input | p6-civitai.png, p6-civitai-list.png, p6-civitai-jump-FAIL.png |
| 2 | Fal | stays on Fal, model fal-ai/z-image/turbo, label 导入 Civitai 图/视频 | PASS — stayed on #fal after 导入; selected "Z Image Turbo"; label correct | p6-fal-model.png |
| 3 | Fal | 生成 → #go 提交中… within 1s, new 成片 card ≤2min | FAIL — button stayed 成/生成, never 提交中…; 成片 stayed 4 张 after ~90s | p6-fal-clicked.png, p6-fal-after.png |
| 4 | Hugging Face | Tongyi-MAI/Z-Image-Turbo, 生成 → 提交中, new image | FAIL — model selection OK (Z-Image Turbo highlighted); on 生成 click the app jumped by itself to #modelscope-ai; no 提交中, no new image | p6-hf-model.png, p6-hf-clicked-JUMP-FAIL.png |
| 5 | 魔搭 AI | Tongyi-MAI/Z-Image-Turbo, 生成 → 提交中, new image | FAIL — selection OK (Z-Image-Turbo highlighted, prompt imported, 源图 empty); after 生成 button stayed 生成, no new card, then app self-jumped back to #fal | p6-ms-model.png, p6-ms-clicked.png, p6-ms-after-JUMP-FAIL.png |

Additional observations
- The page reloaded itself once early in the session (wiping the first Fal import) without any user action.
- Input is processed with very large delays: text typed into the 服务/搜索模型 filter appeared minutes later, inside whatever provider panel was current at that time. Provider tab also reverted/changed on its own several times.
- No generation was ever submitted: 成片 count remained 4 张 throughout; #go never displayed 提交中….
