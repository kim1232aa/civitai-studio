# P5 — Z-Image Turbo cross-provider QA (ABORTED: concurrent actor on desktop)

Import URL: https://civitai.red/images/139791102 (imported OK on Civitai, "已导入参数")

| Provider | Model/service match | 提交中… seen | New image in 成片 | Errors / notes |
|---|---|---|---|---|
| Civitai | PASS — service Z-Image Turbo (not Krea), 底模 `Z Image Turbo`, AIR `urn:air:zimageturbo:diffusionmodel:civitai:2168935@2442439`, 源图 empty (No file chosen), prompt = hinablue (white hair, yellow jacket, gun) | n/a (not clicked) | n/a | Import label `导入 Civitai 图/视频` correct |
| Fal | PASS — `Z Image Turbo` selected via search `z-image` | **NO** | **NO** | On clicking 生成 the UI silently jumped to 魔搭 AI and reset the model list. Also observed unsolicited backend switch Civitai→魔搭 AI earlier. |
| Hugging Face | NOT TESTED | — | — | Aborted |
| 魔搭 AI / CN | NOT TESTED | — | — | Aborted |

## Why aborted
The desktop/Chrome is being driven concurrently by another actor: between my own actions the page
switched backends by itself, text (`Z-Image-Turbo`) was typed into the model search I never touched,
a model tooltip opened, and Chrome tabs were closed (5 → 3) while I performed no actions.
Two idle screenshots 8s apart differed with no input from me. Results here cannot be trusted as
evidence of app behaviour, and the Fal "silent 生成" may be caused by the other actor rather than the app.

Screenshots: p5-civitai-import.png, p5-fal-model.png, p5-fal-clicked.png, p5-fal-after.png
(p5-hf-*, p5-ms-* not produced).
