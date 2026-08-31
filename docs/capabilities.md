# Civitai Studio — capabilities

Generated from local `catalog.json` + `docs/_raw/*.openapi.yaml`. Source `https://orchestration.civitai.com`. Fetched `2026-08-31T21:00:13Z`.

## Defaults (local studio)

- **Image:** engine `comfy`, ecosystem `krea2` (catalog default service `image/comfy/krea2/turbo/createImage`).
- **Video:** engine `minimax-h3-comfy`, operation `imageToVideo` (I2V). MiniMax H3 I2V is the user reference-video default (catalog engine id `minimax-h3-comfy`).
- Mature: workflow body `allowMatureContent: true`; query `hideMatureContent=false`.
- Submit: `POST /v2/consumer/workflows?whatif=&wait=0` (also `hideMatureContent=`). Recipe invoke is `POST /v2/consumer/recipes/{step}`.

## Counts

- Rows total: **310**
- By type: image=133, video=75, other=102
- By status: unknown=203, available=64, degraded=36, unavailable=7
- Non-empty `required[]`: 302 (image+video with OpenAPI fields: 204/208)
- OpenAPI-only extras (no catalog row): 6
- Catalog items with no matching schema: 12

### By step (top)

- `imageGen`: 133
- `videoGen`: 75
- `training`: 28
- `polyGen`: 11
- `(none)`: 8
- `imageResourceTraining`: 5
- `textToSpeech`: 5
- `imageToSvg`: 3
- `shieldstralModeration`: 2
- `aceStepAudio`: 1
- `ageClassification`: 1
- `audioCaptioning`: 1
- `batchOCRSafetyClassification`: 1
- `blobArchive`: 1
- `comfy`: 1
- `comfyNodepackSnapshot`: 1
- `composeMedia`: 1
- `convertImage`: 1
- `customComfy`: 1
- `echo`: 1

## Flags present

- `turbo` set (variant or boolean field): 15
- `fast` set: 6
- `quantity` field: 142
- `duration` field: 68
- `resolution` field: 51

## Notable frame / reference fields

images (76), image (29), sourceImage (25), sourceVideo (10), imageUrl (10), videoUrl (5), audioUrl (5), imageStyleReferences (4), endImage (4), firstFrame (4), lastFrame (4), video (4), startImage (3), referenceImages (3), referenceImage (3), refAudioUrl (3), mask (2), sourceAudio (2)

Typical I2V mapping:

- `minimax-h3-comfy` / `imageToVideo`: `firstFrame`, `lastFrame`
- `minimax-h3-comfy` / `referenceToVideo`: `images`
- `happyHorse` I2V: `image`
- `wan` I2V: `startImage` / `endImage` or `images` depending on version
- `ltx2` / `ltx2.3` / `ltx2.5` FLF: `firstFrame`, `lastFrame`
- image edit: `images` (krea2 edit maxItems=2)

## Unmatched catalog items

- `chat/z-ai/glm-5.3-flash:nitro`
- `chat/openai/gpt-4o-mini`
- `chat/gpt-4o-mini`
- `chat/nousresearch/hermes-3-llama-3.1-70b`
- `chat/deepseek/deepseek-v4-pro`
- `chat/openai/gpt-oss-120b`
- `chat/qwen/qwen3-vl-8b-instruct`
- `chat/openai/gpt-5.6-luna`
- `video/comfy`
- `video/ltx2-fal/createVideo`
- `video/ltx2-fal/extendVideo`
- `video/ltx2-fal/remixVideo`

## OpenAPI leaves not in catalog (sample)

- `training comfy/None/None [ComfyTrainingInput]`
- `videoGen flux/textToVideo/None [Flux3V3TextToVideoInput]`
- `videoGen flux/imageToVideo/None [Flux3V3ImageToVideoInput]`
- `videoGen flux/firstLastFrameToVideo/None [Flux3V3FirstLastFrameToVideoInput]`
- `videoGen flux/keyframesToVideo/None [Flux3V3KeyframesToVideoInput]`
- `videoGen flux/extendVideo/None [Flux3V3ExtendVideoInput]`

## Gaps vs `server.py` (do not edit server here)

Image engines in capabilities (13): `comfy`, `fal`, `flux1-kontext`, `flux2`, `gemini`, `google`, `grok`, `krea`, `openai`, `qwen`, `sdcpp`, `seedream`, `wan`

Video engines in capabilities (24): `comfy`, `flux`, `gemini-omni`, `grok`, `haiper`, `happyHorse`, `hunyuan`, `kling`, `kling-v3`, `lightricks`, `ltx2`, `ltx2-fal`, `ltx2.3`, `ltx2.5`, `minimax`, `minimax-h3`, `minimax-h3-comfy`, `mochi`, `seedance`, `sora`, `veo3`, `vidu`, `vidu-q3`, `wan`

**server.py currently hardcodes** image `comfy` (krea2/turbo/createImage); video `minimax-h3-comfy`, plus frame heuristics for `wan`, `happyHorse`, `hunyuan`, `ltx2.5`/`ltx2.3`.

- Image engines with no dedicated builder (fall through to generic parameter copy): `fal`, `flux1-kontext`, `flux2`, `gemini`, `google`, `grok`, `krea`, `openai`, `qwen`, `sdcpp`, `seedream`, `wan`
- Video engines with no dedicated builder: `comfy`, `flux`, `gemini-omni`, `grok`, `haiper`, `kling`, `kling-v3`, `lightricks`, `ltx2-fal`, `minimax`, `minimax-h3`, `mochi`, `seedance`, `sora`, `veo3`, `vidu`, `vidu-q3`

**Fields / flags:**

- Frame fields: server maps `firstFrame`/`lastFrame`/`startImage`/`endImage`/`image`/`images` for a few engines only. Missing per-engine maps for `referenceImages`, `sourceVideo`, `videoUrl`, `keyframes`, `firstFrameImage`, etc.
- `turbo`/`fast`: applied only for `minimax-h3-comfy`. Many other schemas expose `turbo`, `useTurbo`, `fast`, `fastMode`, `useFastWan`, or turbo **models** (`krea2` turbo/raw).
- `quantity` (1–12 clamp), `duration` (1–30 clamp), `resolution`, `aspectRatio` are copied if present but clamps/enums are not schema-aware.
- `allowMatureContent` is set on the workflow body (default true). `hideMatureContent=false` is on the submit query. `whatif` + `wait=0` are implemented for `/api/whatif` and `/api/generate`.

**Recipes not implemented in the UI/server** (catalog `step` other than imageGen/videoGen):

`aceStepAudio`, `ageClassification`, `audioCaptioning`, `batchOCRSafetyClassification`, `blobArchive`, `comfy`, `comfyNodepackSnapshot`, `composeMedia`, `convertImage`, `customComfy`, `echo`, `humanoidImageMask`, `imageBackgroundRemoval`, `imageResourceTraining`, `imageToSvg`, `imageUpload`, `imageUpscaler`, `mediaCaptioning`, `mediaHash`, `mediaRating`, `miniMaxMusic3`, `model3DPreview`, `modelClamScan`, `modelHash`, `modelParseMetadata`, `modelPickleScan`, `polyGen`, `prepareResource`, `preprocessImage`, `promptEnhancement`, `qwenImageBench`, `repeat`, `shieldstralModeration`, `textToImage`, `textToSpeech`, `training`, `transcode`, `transcription`, `tryOnU`, `videoBackgroundRemoval`…

Upscale / try-on / audio / 3D / training have OpenAPI recipe POSTs but no local `/api/*` handlers beyond the generic workflow submit.

## Suggested local endpoints

- `GET /api/capabilities` — serve this `docs/capabilities.json` (no live POST).
- `GET /api/catalog` — already present (`GET /v2/services?limit=&offset=`).
- `POST /api/generate` → `POST /v2/consumer/workflows?whatif=false&wait=0&hideMatureContent=false`.
- `POST /api/whatif` → same with `whatif=true` (already present).
- `GET /api/jobs/{id}` → `GET /v2/consumer/workflows/{id}` (already present).
- `POST /api/recipes/{step}` → `POST /v2/consumer/recipes/{step}` (imageGen, videoGen, imageUpscaler, tryOnU, polyGen, …) for estimate/`whatif` without wrapping a full workflow.
- `GET /v2/consumer/recipes/{step}/openapi.yaml` — already mirrored under `docs/_raw/`.
- Blob input: data URLs work in many `images`/`firstFrame` fields; if a dedicated blob API is needed, proxy `GET /v2/consumer/blobs?blobId=` (download) — do not POST generation jobs.
- Pass schema `quantity`/`duration`/`resolution` enums from capabilities instead of the current 1–12 / 1–30 clamps.

## Wan v2.2 vs v2.5 (video I2V)

Frame fields are **the same**: `sourceImage` + `images`. Neither version has `startImage` / `endImage`.

| | v2.2 fal I2V | v2.5 fal I2V |
|---|---|---|
| frame | `sourceImage`, `images` | `sourceImage`, `images` |
| required | engine, prompt, cfgScale, version, provider, operation | same |
| turbo | `useTurbo` (default false) | none |
| extra | `shift`, `interpolatorModel` | — |
| resolution | 480p / 720p (default 720p) | 480p / 720p / **1080p** (default 1080p) |
| prompt expand | default false | default **true** |

`startImage` / `endImage` only appear later: Wan **v2.7** and **v3.0** I2V. v2.6 I2V adds `audioUrl` but still no start/end.
