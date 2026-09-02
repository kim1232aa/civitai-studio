# P3 HUMAN QA — hinablue image 139791102 (Z Image Turbo)

Source post: https://civitai.red/images/139791102
Resources used (from Civitai page): CHECKPOINT **Z Image Turbo**, LORA **[Z Image Turbo] Asian Mix Lora - EOL v5.0**,
ENGINE COMFYUI, 960x1440, STEPS 8, CFGSCALE 1, SAMPLER ER_SDE, SCHEDULER BONG_TANGENT, SEED 1074720209731743.

Method: click-only in Chrome on http://127.0.0.1:8765/ (hard refresh Ctrl+Shift+R). No curl generate. Prompt never typed by hand.

## Provider buttons (5)
Civitai | Fal | Hugging Face | **魔搭 AI** | **魔搭 CN**  → 魔搭 IS split into two buttons.

## Results

| Provider | 底模/service after 导入 | Import label | 提交中 shown? | New image in 成片? | Errors |
|---|---|---|---|---|---|
| Civitai | **Z-Image Turbo** (highlighted in 服务) — PASS | 导入 Civitai 图/链接 | No | No (成片 stays 4 张) | none shown |
| Fal | **Z Image Turbo** (highlighted, filter z-image) — PASS | **导入 Civitai 图/视频** ✓ | No | No | none shown |
| Hugging Face | **Z-Image Turbo** — PASS | 导入 Civitai 图/视频 | No | No | none shown |
| 魔搭 AI | **Z-Image-Turbo** — PASS | 导入 Civitai 图/视频 | No | No | none shown |
| 魔搭 CN | not exercised (time) | — | — | — | — |

Imported parameters verified on Fal/Civitai panels: 提示词 = "A gallant looking japanese woman, makeup. long face, long eyelashes,
sideways glance, serious expression, white hair, hime cut, yellow jacket, cyberpunk, tech wear, holding gun with one hand,
aiming at viewer, knee up, pink and green neon colored graffiti wall, night, sitting by wall, view from side, (glitch),
dynamic composition, dynamic angle, foreshortening." ; 宽 960 / 高 1440 ; 步数 8 ; CFG 1.  → matches source. PASS
No wrong-model fallback observed (no Krea / Bria / Seedream / first-catalog-item pick).

## Bugs / observations
1. **生成 does nothing.** On all four providers, after a successful 导入 ("已导入参数，自己点生成。"), clicking 生成 produces
   NO "提交中", no toast, no error, no status change, and no new file (out/ stays at the same 4 jpgs; 成片 stays "4 张").
   Silent no-op — highest-severity finding.
2. **导入 sometimes changes the active provider.** Importing while Civitai was active jumped the active provider to Fal
   (twice) and to 魔搭 AI (once), non-deterministically. Violates "stay on provider". The model chosen was still
   Z Image Turbo, so it looks like "auto-pick provider that serves the model" leaking into the UI.
3. **State churn / duplicate tabs.** During the session extra tabs to 127.0.0.1:8765 (one of them 127.0.0.1:8765/#fal)
   appeared without being opened by a click, and the panel state (provider, 服务 filter, prompt) reset or changed
   spontaneously between actions (e.g. filter text "Z-Image-Turbo" appeared on its own). Any multi-tab state sync should
   be checked; it makes the UI feel non-deterministic.
4. 服务 filter box triggers Chrome autofill dropdown (Krea/flux/FLUX) covering the list — minor annoyance.

## Screenshots (/workspace/civitai-studio/docs/review-shots/)
p3-civitai-imported.png, p3-civitai-gen-clicked.png, p3-fal-import.png, p3-fal-gen-clicked.png,
p3-hf-import.png, p3-hf-gen-clicked.png, p3-ms-import.png
