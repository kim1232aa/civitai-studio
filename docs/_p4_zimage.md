# P4 — Z Image Turbo import QA (civitai.red/images/139791102)

Studio: http://127.0.0.1:8765/ (hard-refreshed). Import label on every provider: 「导入 Civitai 图/视频」 ✅
Prompt after import: "A gallant looking japanese woman, makeup. long face, long eyelashes, sideways glance, serious expression, white hair, hime cut, yellow jacket, cyberpunk, tech wear, holding gun ... " (hinablue) ✅ — NOT apple.
源图: file input showed "No file chosen" on every provider (txt2img, no source image stuffed) ✅

| backend | selected id / name | match | 源图 empty | 提交中 seen | new image in 成片 | status / error |
|---|---|---|---|---|---|---|
| Civitai | image/sdcpp/zImage/turbo/createImage · "Z-Image Turbo" (AIR urn:air:zimageturbo:diffusionmodel:civitai:2168935@2442439) | yes (not Krea2) | yes | no | no (成片 stayed 4 张) | "Civitai 已加载 304 个模型。自己点生成。" / "已导入参数，自己点生成。" — no error, no job feedback |
| Fal | fal-ai/z-image/turbo · "Z Image Turbo" | yes | yes | no | no (4 张) | "已导入参数，自己点生成。" unchanged after click; no queue/error text |
| Hugging Face | Tongyi-MAI/Z-Image-Turbo · "Z-Image Turbo" | yes | yes | no | no (4 张) | "Hugging Face 已加载 8 个模型。自己点生成。" unchanged; no error |
| 魔搭 AI | Tongyi-MAI/Z-Image-Turbo · "Z-Image Turbo" | yes | yes | no | no (4 张) | "魔搭 AI 已加载 35 个模型。自己点生成。" unchanged; no error (魔搭 CN not exercised) |

## Notes / blockers
- Model resolution contract PASSES on all four backends; prompt + no-源图 contract PASSES.
- 生成 contract FAILS to observe: after each click the button never changed to 提交中, no job/status/error text appeared, and 成片 remained at 4 张 for ≥60 s (Fal, HF, 魔搭 AI) — no new image on any backend.
- Environment caveat: during the session the desktop was also being driven by another actor (provider tab switched by itself, imports re-ran, tabs opened/closed, page reloaded mid-run). Two 生成 clicks were rejected with "page changed after review". So the 生成 results are suggestive but not fully attributable.
