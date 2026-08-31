# Fal.ai model APIs + Civitai Studio recipe gaps

Fetched `2026-08-31T21:24:01Z` (UTC). Source: official Fal Platform APIs. **No generation jobs were submitted.** API key is not stored in this file.

## Auth

- Header: `Authorization: Key <KEY_ID>:<KEY_SECRET>` (same string as `/home/box/.config/fal/token`).
- Platform list/search: `GET https://api.fal.ai/v1/models` — this run returned **HTTP 200** (1491 endpoints paginated).
- Per-model OpenAPI: `GET https://api.fal.ai/v1/models?endpoint_id={id}&expand=openapi-3.0` or `GET https://fal.ai/api/openapi/queue/openapi.json?endpoint_id={id}`.
- Per-model agent schema: `GET https://fal.ai/models/{id}/llms.txt`.
- Do **not** put the key in JSON, markdown, logs, or client-side code. Prefer `$FAL_KEY`.

## Submit (queue vs sync) — do not call from this catalog job

| Mode | Method | URL |
|---|---|---|
| Queue submit (recommended) | POST | `https://queue.fal.run/{model_id}` |
| Sync / `run` | POST | `https://fal.run/{model_id}` |
| Status | GET | `https://queue.fal.run/{model_id}/requests/{request_id}/status` |
| Result | GET | `https://queue.fal.run/{model_id}/requests/{request_id}` |
| Cancel | PUT | `https://queue.fal.run/{model_id}/requests/{request_id}/cancel` |

Queue lifecycle: `IN_QUEUE` → `IN_PROGRESS` → `COMPLETED`. Optional webhook: `?fal_webhook=https://...`.
Sync (`fal.run`) blocks until the result; no durable queue retries. Prefer queue for video and production.

Body is model-specific JSON from OpenAPI (usually `prompt`, plus image URL fields below). Response media are CDN URLs.

## Discovery

- List: `GET https://api.fal.ai/v1/models?limit=100&cursor=` (`has_more`, `next_cursor`).
- Search: `?q=sora&category=text-to-video&status=active`.
- Find: `?endpoint_id=fal-ai/flux/dev` (repeatable, up to 50).
- Gallery HTML/JSON: `https://fal.ai/models` / `GET https://fal.ai/api/models` (1491 total this run).
- `GET https://fal.run/{owner}/{app}/openapi.json` works for 2-segment ids (e.g. `fal-ai/flux-pro`) and 404s for 3-segment ids (`fal-ai/flux/dev`).

## Main models

Catalog in `fal-models.json`: **111** endpoints (image=49, video=62). Field names are from live OpenAPI, not guesses.

### Image

| model id | prompt | image fields | aspect | required |
|---|---|---|---|---|
| `fal-ai/flux/schnell` | prompt | — | — | prompt |
| `fal-ai/flux/dev` | prompt | — | — | prompt |
| `fal-ai/flux/dev/image-to-image` | prompt | image_url | — | image_url, prompt |
| `fal-ai/flux-pro` | prompt | — | — | prompt |
| `fal-ai/flux-pro/v1.1` | prompt | — | — | prompt |
| `fal-ai/flux-pro/v1.1-ultra` | prompt | image_url | aspect_ratio | prompt |
| `fal-ai/flux-pro/kontext` | prompt | image_url | aspect_ratio | prompt, image_url |
| `fal-ai/flux-pro/kontext/max` | prompt | image_url | aspect_ratio | prompt, image_url |
| `fal-ai/flux-pro/kontext/text-to-image` | prompt | — | aspect_ratio | prompt |
| `fal-ai/flux-kontext/dev` | prompt | image_url | — | prompt, image_url |
| `fal-ai/flux-2` | prompt | — | — | prompt |
| `fal-ai/flux-2/edit` | prompt | image_urls | — | prompt, image_urls |
| `fal-ai/flux-2-pro` | prompt | — | — | prompt |
| `fal-ai/flux-2-pro/edit` | prompt | image_urls | — | prompt, image_urls |
| `fal-ai/flux-2/turbo` | prompt | — | — | prompt |
| `fal-ai/flux-2/flash` | prompt | — | — | prompt |
| `fal-ai/flux-2-flex` | prompt | — | — | prompt |
| `fal-ai/flux-lora` | prompt | — | — | prompt |
| `fal-ai/fast-sdxl` | prompt | — | — | prompt |
| `fal-ai/fast-sdxl/image-to-image` | prompt | image_url | — | image_url, prompt |
| `fal-ai/fast-lightning-sdxl` | prompt | — | — | prompt |
| `fal-ai/stable-diffusion-v3-medium` | prompt | — | — | prompt |
| `fal-ai/stable-diffusion-v35-large` | prompt | — | — | prompt |
| `fal-ai/stable-diffusion-v35-medium` | prompt | — | — | prompt |
| `fal-ai/recraft/v3/text-to-image` | prompt | — | — | prompt |
| `fal-ai/recraft/v4/text-to-image` | prompt | — | — | prompt |
| `fal-ai/recraft/v4/pro/text-to-image` | prompt | — | — | prompt |
| `fal-ai/recraft/v4.1/text-to-image` | prompt | — | — | prompt |
| `fal-ai/recraft/v4.1/pro/text-to-image` | prompt | — | — | prompt |
| `fal-ai/recraft/v3/image-to-image` | prompt | image_url | — | prompt, image_url |
| `fal-ai/ideogram/v2` | prompt | — | aspect_ratio | prompt |
| `fal-ai/ideogram/v3` | prompt | image_urls | — | prompt |
| `fal-ai/ideogram/v3/edit` | prompt | image_url, image_urls | — | prompt, image_url, mask_url |
| `ideogram/v4` | prompt | — | — | prompt |
| `ideogram/v4/image-to-image` | prompt | image_url | — | prompt, image_url |
| `fal-ai/imagen3` | prompt | — | aspect_ratio | prompt |
| `fal-ai/imagen3/fast` | prompt | — | aspect_ratio | prompt |
| `fal-ai/imagen4/preview` | — | — | — | — |
| `fal-ai/imagen4/preview/fast` | — | — | — | — |
| `fal-ai/imagen4/preview/ultra` | — | — | — | — |
| `fal-ai/gpt-image-1/text-to-image` | prompt | — | — | prompt |
| `fal-ai/gpt-image-1/edit-image` | prompt | image_urls | — | prompt, image_urls |
| `fal-ai/gpt-image-1.5` | prompt | — | — | prompt |
| `fal-ai/gpt-image-1.5/edit` | prompt | mask_image_url, image_urls | — | prompt, image_urls |
| `openai/gpt-image-2` | prompt | — | — | prompt |
| `openai/gpt-image-2/edit` | prompt | image_urls | — | prompt, image_urls |
| `fal-ai/nano-banana-2` | prompt | — | aspect_ratio | prompt |
| `fal-ai/nano-banana-2/edit` | prompt | image_urls | aspect_ratio | prompt |
| `fal-ai/nano-banana-pro` | prompt | — | aspect_ratio | prompt |

### Video

| model id | prompt | image fields | duration | aspect | required |
|---|---|---|---|---|---|
| `fal-ai/kling-video/v3/pro/text-to-video` | prompt | — | duration | aspect_ratio | — |
| `fal-ai/kling-video/v3/pro/image-to-video` | prompt | start_image_url, end_image_url | duration | — | start_image_url |
| `fal-ai/kling-video/v3/standard/text-to-video` | prompt | — | duration | aspect_ratio | — |
| `fal-ai/kling-video/v3/standard/image-to-video` | prompt | start_image_url, end_image_url | duration | — | start_image_url |
| `fal-ai/kling-video/v2.5-turbo/pro/text-to-video` | prompt | — | duration | aspect_ratio | prompt |
| `fal-ai/kling-video/v2.5-turbo/pro/image-to-video` | prompt | image_url, tail_image_url | duration | — | prompt, image_url |
| `fal-ai/kling-video/v2.6/pro/text-to-video` | prompt | — | duration | aspect_ratio | prompt |
| `fal-ai/kling-video/v2.6/pro/image-to-video` | prompt | start_image_url, end_image_url | duration | — | prompt, start_image_url |
| `fal-ai/kling-video/o3/pro/text-to-video` | prompt | — | duration | aspect_ratio | — |
| `fal-ai/kling-video/o3/pro/image-to-video` | prompt | end_image_url, image_url | duration | — | image_url |
| `minimax/h3/text-to-video` | prompt | — | duration | aspect_ratio | prompt |
| `minimax/h3/image-to-video` | prompt | image_url, end_image_url | duration | — | prompt |
| `minimax/h3-max/text-to-video` | prompt | — | duration | aspect_ratio | prompt, prompt_expansion_mode |
| `minimax/h3-max/image-to-video` | prompt | end_image_url, image_url | duration | — | prompt, prompt_expansion_mode |
| `fal-ai/minimax/hailuo-02/pro/text-to-video` | prompt | — | — | — | prompt |
| `fal-ai/minimax/hailuo-02/pro/image-to-video` | prompt | end_image_url, image_url | — | — | prompt, image_url |
| `fal-ai/minimax/hailuo-2.3/pro/text-to-video` | prompt | — | — | — | prompt |
| `fal-ai/minimax/hailuo-2.3/pro/image-to-video` | prompt | image_url | — | — | prompt, image_url |
| `fal-ai/minimax/video-01` | prompt | — | — | — | prompt |
| `fal-ai/minimax/video-01/image-to-video` | prompt | image_url | — | — | prompt, image_url |
| `fal-ai/wan/v2.2-a14b/text-to-video` | prompt | — | — | aspect_ratio | prompt |
| `fal-ai/wan/v2.2-a14b/image-to-video` | prompt | image_url, end_image_url | — | aspect_ratio | prompt, image_url |
| `fal-ai/wan/v2.7/text-to-video` | prompt | — | duration | aspect_ratio | prompt |
| `fal-ai/wan/v2.7/image-to-video` | prompt | end_image_url, image_url | duration | — | — |
| `wan/v2.6/text-to-video` | prompt | — | duration | aspect_ratio | prompt |
| `wan/v2.6/image-to-video` | prompt | image_url | duration | — | prompt, image_url |
| `alibaba/wan-3.0/text-to-video` | prompt | — | duration | aspect_ratio | prompt |
| `alibaba/wan-3.0/image-to-video` | prompt | start_image_url, end_image_url | duration | aspect_ratio | start_image_url |
| `fal-ai/ltx-2.3/text-to-video` | prompt | — | duration | aspect_ratio | prompt |
| `fal-ai/ltx-2.3/image-to-video` | prompt | end_image_url, image_url | duration | aspect_ratio | prompt, image_url |
| `fal-ai/ltx-2-19b/text-to-video` | prompt | — | — | — | prompt |
| `fal-ai/ltx-2-19b/image-to-video` | prompt | end_image_url, image_url | — | — | prompt, image_url |
| `lightricks/ltx-2.5/text-to-video/pro` | prompt | — | duration | aspect_ratio | prompt |
| `lightricks/ltx-2.5/image-to-video/pro` | prompt | image_url, end_image_url | duration | aspect_ratio | prompt, image_url |
| `fal-ai/veo3.1` | prompt | — | duration | aspect_ratio | prompt |
| `fal-ai/veo3.1/image-to-video` | prompt | image_url | duration | aspect_ratio | prompt, image_url |
| `fal-ai/veo3.1/fast` | prompt | — | duration | aspect_ratio | prompt |
| `fal-ai/veo3.1/fast/image-to-video` | prompt | image_url | duration | aspect_ratio | prompt, image_url |
| `fal-ai/veo3.1/first-last-frame-to-video` | prompt | first_frame_url, last_frame_url | duration | aspect_ratio | prompt, first_frame_url, last_frame_url |
| `fal-ai/sora-2/text-to-video` | prompt | — | duration | aspect_ratio | prompt |
| `fal-ai/sora-2/image-to-video` | prompt | image_url | duration | aspect_ratio | prompt, image_url |
| `fal-ai/sora-2/text-to-video/pro` | prompt | — | duration | aspect_ratio | prompt |
| `fal-ai/sora-2/image-to-video/pro` | prompt | image_url | duration | aspect_ratio | prompt, image_url |
| `fal-ai/runway-gen3/turbo/image-to-video` | — | — | — | — | — |
| `fal-ai/runway-gen3/turbo/text-to-video` | — | — | — | — | — |
| `fal-ai/hunyuan-video` | prompt | — | — | aspect_ratio | prompt |
| `fal-ai/hunyuan-video-image-to-video` | prompt | image_url | — | aspect_ratio | prompt, image_url |
| `fal-ai/hunyuan-video-v1.5/text-to-video` | prompt | — | — | aspect_ratio | prompt |
| `fal-ai/hunyuan-video-v1.5/image-to-video` | prompt | image_url | — | aspect_ratio | prompt, image_url |
| `fal-ai/bytedance/seedance/v1/pro/text-to-video` | prompt | — | duration | aspect_ratio | prompt |
| `fal-ai/bytedance/seedance/v1/pro/image-to-video` | prompt | image_url, end_image_url | duration | aspect_ratio | prompt, image_url |
| `fal-ai/bytedance/seedance/v1.5/pro/text-to-video` | prompt | — | duration | aspect_ratio | prompt |
| `fal-ai/bytedance/seedance/v1.5/pro/image-to-video` | prompt | image_url, end_image_url | duration | aspect_ratio | prompt, image_url |
| `bytedance/seedance-2.0/text-to-video` | prompt | — | duration | aspect_ratio | prompt |
| `bytedance/seedance-2.0/image-to-video` | prompt | image_url, end_image_url | duration | aspect_ratio | prompt, image_url |
| `bytedance/seedance-2.5/text-to-video` | prompt | — | duration | aspect_ratio | prompt |
| `bytedance/seedance-2.5/image-to-video` | prompt | image_url, end_image_url | duration | aspect_ratio | prompt, image_url |
| `fal-ai/vidu/q3/text-to-video` | prompt | — | duration | aspect_ratio | prompt |
| `fal-ai/vidu/q3/image-to-video` | prompt | image_url, end_image_url | duration | — | image_url |
| `fal-ai/vidu/q1/text-to-video` | prompt | — | — | aspect_ratio | prompt |
| `fal-ai/vidu/q1/image-to-video` | prompt | image_url | — | — | prompt, image_url |
| `fal-ai/vidu/q1/start-end-to-video` | prompt | end_image_url, start_image_url | — | — | prompt, start_image_url, end_image_url |

Notes:

- Flux T2I uses `image_size` (not `aspect_ratio`) except Kontext / Ultra.
- Kling I2V uses `start_image_url` + `end_image_url` (v3/v2.6) or `image_url` + `tail_image_url` (v2.5). Kling v3 T2V lists `prompt` as optional with a default duration/aspect.
- Veo first/last frame: `first_frame_url`, `last_frame_url`.
- MiniMax Hailuo **pro** 02/2.3 I2V OpenAPI has no `duration`/`aspect_ratio` (prompt + `image_url`, 02-pro also `end_image_url`). Hailuo **standard** 02/2.3/2.3-fast and `hailuo-02-fast` I2V now expose `duration`.
- Imagen 4 preview ids are listed by search `q=imagen4` as **deprecated** but find + OpenAPI + docs/`llms.txt` are all **404**. No working alias. No fields invented. Imagen 3 schemas remain in the 111 set (search also marks imagen3 deprecated).
- Runway Gen-3 turbo I2V: find 200 + expansion_failed; filled from parent `GET https://fal.run/fal-ai/runway-gen3/openapi.json` path `/turbo/image-to-video` (`image_url`, `end_image_url`, `prompt`, `duration`; aspect is `ratio` not `aspect_ratio`). T2V still has no schema (parent OpenAPI has no T2V path; docs 404).
- Google Imagen on Fal is `fal-ai/imagen3` (and empty Imagen4 ids above). GPT-image: `fal-ai/gpt-image-1*`, `openai/gpt-image-2`.

## Field-gap fill (2026-09-01 CST)

GET OpenAPI only (no generation). `fal-models.json` still 1491 items. Details: `fal-field-gaps.md`.

| id | imageFields |
|---|---|
| `fal-ai/kling-video/o3/standard/image-to-video` | image_url, end_image_url |
| `fal-ai/kling-video/o3/pro/reference-to-video` | image_urls, start_image_url, end_image_url |
| `fal-ai/kling-video/o3/standard/reference-to-video` | image_urls, start_image_url, end_image_url |
| `fal-ai/kling-video/o3/pro/video-to-video/edit` | image_urls, video_url |
| `fal-ai/kling-video/o3/4k/image-to-video` | image_url, end_image_url |
| `fal-ai/kling-video/o3/standard/text-to-video` | — (prompt only) |
| `fal-ai/minimax/hailuo-02/standard/image-to-video` | image_url, end_image_url |
| `fal-ai/minimax/hailuo-2.3/standard/image-to-video` | image_url |
| `fal-ai/minimax/hailuo-2.3-fast/standard/image-to-video` | image_url |
| `fal-ai/minimax/hailuo-02-fast/image-to-video` | image_url |
| `lightricks/ltx-2.5/image-to-video/fast` | image_url, end_image_url |
| `lightricks/ltx-2.5/text-to-video/fast` | — (prompt only) |
| `lightricks/ltx-2.5/audio-to-video/pro` | image_url (required: audio_url) |
| `lightricks/ltx-2.5/audio-to-video/fast` | image_url (required: audio_url) |
| `fal-ai/ltx-2.3/image-to-video/fast` | image_url, end_image_url |
| `fal-ai/ltx-2.3-22b/image-to-video` | image_url, end_image_url |
| `fal-ai/ltx-2.3-quality/image-to-video` | image_url |
| `fal-ai/kling-video/v2.1/standard/image-to-video` | image_url |
| `fal-ai/kling-video/v2.1/pro/image-to-video` | image_url, tail_image_url |
| `fal-ai/kling-video/v2.5-turbo/standard/image-to-video` | image_url |
| `fal-ai/kling-video/v3/turbo/pro/image-to-video` | image_url |
| `fal-ai/veo3.1/lite/image-to-video` | image_url |
| `fal-ai/veo3.1/fast/first-last-frame-to-video` | first_frame_url, last_frame_url |
| `fal-ai/veo3.1/lite/first-last-frame-to-video` | first_frame_url, last_frame_url |
| `fal-ai/veo3.1/reference-to-video` | image_urls |
| `fal-ai/runway-gen3/turbo/image-to-video` | image_url, end_image_url (via parent OpenAPI) |

Still empty: Imagen4 preview/fast/ultra; Runway Gen-3 turbo **text-to-video**.

## HTTP errors this run

- List/auth: **200**. No 401.
- 401 count: 0
- Field-gap retry: Imagen4 find **404** (3 ids + aliases); Runway I2V/T2V find **200** but expansion_failed; Runway I2V filled from parent `fal.run` OpenAPI **200**; T2V and Imagen4 docs **404**.

## Civitai Studio gaps

Compared `docs/catalog.json` (304 services) to `server.py` + `static/index.html`. `server.py` was not modified.

**Studio currently exposes**

- UI tabs: 图片 `imageGen`, 视频 `videoGen`, 超分 (tag `upscaling` or name contains `upscaler`), 去背景 (tag `background-removal`).
- Generate path: `POST /api/generate` and `POST /api/whatif` → orchestration `POST /v2/consumer/workflows` with `$type` = selected service `step`.
- Those extra UI-selectable non-gen steps: `image/imageUpscaler`, `video/videoUpscaler`, `video/videoEnhancement`, `image/imageBackgroundRemoval`, `video/videoBackgroundRemoval`.
- Unused API: `POST /api/recipes/{step}` proxies any recipe but the UI never calls it. No audio / 3D / training / try-on tab.

**Not exposed** (no UI selection; generate builder is image/video-centric; 88 catalog rows):

| id | step | category | name |
|---|---|---|---|
| `image/convertImage` | `convertImage` | image | Convert Image |
| `image/textToImage` | `textToImage` | image | Text to Image (Deprecated) |
| `video/transcode` | `transcode` | video | Transcode |
| `text/wdTagging` | `wdTagging` | text | WD Tagging |
| `text/mediaRating` | `mediaRating` | text | Media Rating |
| `video/videoFrameExtraction` | `videoFrameExtraction` | video | Video Frame Extraction |
| `utility/mediaHash` | `mediaHash` | utility | Media Hash |
| `utility/comfy` | `comfy` | utility | Comfy |
| `text/mediaCaptioning` | `mediaCaptioning` | text | Media Captioning |
| `utility/repeat` | `repeat` | utility | Repeat |
| `image/imageUpload` | `imageUpload` | image | Image Upload |
| `text/prompt` | `shieldstralModeration` | text | Prompt Moderation |
| `model/modelParseMetadata` | `modelParseMetadata` | model | Model Parse Metadata |
| `model/modelClamScan` | `modelClamScan` | model | Model Clam Scan |
| `model/modelHash` | `modelHash` | model | Model Hash |
| `model/modelPickleScan` | `modelPickleScan` | model | Model Pickle Scan |
| `text/promptEnhancement` | `promptEnhancement` | text | Prompt Enhancement |
| `text/text` | `shieldstralModeration` | text | Text Moderation |
| `image/preprocessImage` | `preprocessImage` | image | Preprocess Image |
| `model/ai-toolkit/sdxl` | `training` | model | LoRA Training · SDXL |
| `video/videoMetadata` | `videoMetadata` | video | Video Metadata |
| `utility/customComfy` | `customComfy` | utility | Custom Comfy |
| `model/ai-toolkit/krea2` | `training` | model | LoRA Training · Krea 2 |
| `model/kohya` | `imageResourceTraining` | model | LoRA Training · Kohya |
| `model/ai-toolkit/anima` | `training` | model | LoRA Training · Anima |
| `utility/blobArchive` | `blobArchive` | utility | Blob Archive |
| `3d/model3DPreview` | `model3DPreview` | 3d | Model 3D Preview |
| `3d/fal/meshy/v6/imageTo3D` | `polyGen` | 3d | Fal Meshy V6 Image To3D |
| `video/videoInterpolation` | `videoInterpolation` | video | Video Interpolation |
| `model/ai-toolkit/flux2klein/9b` | `training` | model | LoRA Training · FLUX.2 Klein 9B |
| `model/ai-toolkit/minimaxh3` | `training` | model | Ai-toolkit Minimaxh3 |
| `model/ai-toolkit/sd1` | `training` | model | LoRA Training · SD 1.5 |
| `model/ai-toolkit/zimageturbo` | `training` | model | LoRA Training · Z-Image Turbo |
| `model/ai-toolkit/flux1/dev` | `training` | model | LoRA Training · FLUX.1 Dev |
| `model/ai-toolkit/flux2klein/4b` | `training` | model | LoRA Training · FLUX.2 Klein 4B |
| `model/comfyNodepackSnapshot` | `comfyNodepackSnapshot` | model | Comfy Nodepack Snapshot |
| `3d/comfy/hunyuan3D/imageTo3D` | `polyGen` | 3d | Hunyuan3D · Image to 3D |
| `audio/aceStepAudio` | `aceStepAudio` | audio | ACE-Step |
| `model/ai-toolkit/wan/2.1` | `training` | model | LoRA Training · Wan 2.1 |
| `3d/fal/meshy/v6/textTo3D` | `polyGen` | 3d | Fal Meshy V6 Text To3D |
| `3d/fal/tripo` | `polyGen` | 3d | Tripo |
| `model/ai-toolkit/boogu` | `training` | model | LoRA Training · Boogu |
| `model/ai-toolkit/ltx23` | `training` | model | LoRA Training · LTX-2.3 |
| `model/ai-toolkit/ltx25` | `training` | model | Ai-toolkit Ltx25 |
| `model/flux-dev-fast` | `imageResourceTraining` | model | LoRA Training · FLUX.1 Dev (Fast) |
| `model/ai-toolkit/ernie` | `training` | model | LoRA Training · ERNIE |
| `model/ai-toolkit/mageflow` | `training` | model | Ai-toolkit Mageflow |
| `model/musubi` | `imageResourceTraining` | model | LoRA Training · Musubi |
| `3d/comfy/hunyuan3D/shapeGen` | `polyGen` | 3d | Hunyuan3D · Shape Generation |
| `3d/comfy/hunyuan3D/texGen` | `polyGen` | 3d | Hunyuan3D · Texture Generation |
| `3d/comfy/trellis2/imageTo3D` | `polyGen` | 3d | Comfy Trellis2 Image To3D |
| `3d/comfy/trellis2/shapeGen` | `polyGen` | 3d | — |
| `3d/comfy/trellis2/texGen` | `polyGen` | 3d | — |
| `3d/fal/meshy/v7/imageTo3D` | `polyGen` | 3d | — |
| `3d/fal/meshy/v7/multiImageTo3D` | `polyGen` | 3d | Fal Meshy V7 Multi Image To3D |
| `audio/audioCaptioning` | `audioCaptioning` | audio | Audio Captioning |
| `audio/custom` | `textToSpeech` | audio | Custom Text-to-Speech |
| `audio/miniMaxMusic3` | `miniMaxMusic3` | audio | — |
| `audio/transcription` | `transcription` | audio | Transcription |
| `audio/vllm-omni/omnivoice` | `textToSpeech` | audio | OmniVoice |
| `audio/vllm-omni/qwen3/base` | `textToSpeech` | audio | Qwen3-TTS Voice Clone |
| `audio/vllm-omni/qwen3/customVoice` | `textToSpeech` | audio | Qwen3-TTS Custom Voice |
| `audio/vllm-omni/qwen3/voiceDesign` | `textToSpeech` | audio | Qwen3-TTS Voice Design |
| `image/comfy/omnisvg` | `imageToSvg` | image | OmniSVG |
| `image/comfy/starvector` | `imageToSvg` | image | StarVector |
| `image/comfy/vtracer` | `imageToSvg` | image | Comfy Vtracer |
| `image/humanoidImageMask` | `humanoidImageMask` | image | Humanoid Image Mask |
| `image/tryOnU` | `tryOnU` | image | Try-On U |
| `model/ai-toolkit` | `training` | model | LoRA Training · AI Toolkit |
| `model/ai-toolkit/ace_step_15` | `training` | model | LoRA Training · ACE-Step 1.5 |
| `model/ai-toolkit/ace_step_15_xl/base` | `training` | model | LoRA Training · ACE-Step 1.5 XL (base) |
| `model/ai-toolkit/ace_step_15_xl/sft` | `training` | model | LoRA Training · ACE-Step 1.5 XL (SFT) |
| `model/ai-toolkit/chroma` | `training` | model | LoRA Training · Chroma |
| `model/ai-toolkit/flux1/schnell` | `training` | model | LoRA Training · FLUX.1 Schnell |
| `model/ai-toolkit/hidream-o1` | `training` | model | LoRA Training · HiDream-o1 |
| `model/ai-toolkit/ideogram4` | `training` | model | Ai-toolkit Ideogram4 |
| `model/ai-toolkit/ltx2` | `training` | model | LoRA Training · LTX-2 |
| `model/ai-toolkit/qwen` | `training` | model | LoRA Training · Qwen-Image |
| `model/ai-toolkit/wan/2.2` | `training` | model | LoRA Training · Wan 2.2 |
| `model/ai-toolkit/zimagebase` | `training` | model | LoRA Training · Z-Image Base |
| `model/flux2-dev` | `imageResourceTraining` | model | LoRA Training · FLUX.2 Dev |
| `model/flux2-dev-edit` | `imageResourceTraining` | model | LoRA Training · FLUX.2 Dev Edit |
| `text/ageClassification` | `ageClassification` | text | Age Classification |
| `text/batchOCRSafetyClassification` | `batchOCRSafetyClassification` | text | Batch OCR Safety Classification |
| `text/qwenImageBench` | `qwenImageBench` | text | Qwen Image Bench |
| `utility/composeMedia` | `composeMedia` | utility | Compose Media |
| `utility/echo` | `echo` | utility | Echo |
| `utility/prepareResource` | `prepareResource` | utility | — |

Especially missing vs requested families: `polyGen` (all 3D), `aceStepAudio`, `miniMaxMusic3`, `textToSpeech` (5), `tryOnU`, `videoInterpolation`, `convertImage`, `imageToSvg` (3), `composeMedia`, `training` (27), `imageResourceTraining` (5).

See `fal-models.json` keys `models`, `civitaiGaps`, `civitaiMissingRecipes`.
