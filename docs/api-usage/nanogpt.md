# NanoGPT API 用法

适配器：`providers/nanogpt.py`。capabilities：`lora=path`，`loraPath=civitai_download`，`resolution=catalog_token`，`promptMax=None`（**无公布上限**），`seed` clamp=`none`（**禁止 mod int32**），`progress=none`，`cancel=False`，`estimate=catalog_price`，`i2i=input_references`，`i2v=image_url`，`maxRefs=5`，`refImagesField=input_references`，`videoDuration=string_seconds`。

## Auth

| | |
| --- | --- |
| Token | `~/.config/nano-gpt/token`；env `NANO_GPT_API_KEY` / `NANOGPT_API_KEY` |
| Header | `Authorization: Bearer` **且** `x-api-key` |
| Civitai（仅本机解析 LoRA） | `~/.config/civitai/token` — **永不**发给 Nano、永不 `?token=` |

## Base URLs

| 用途 | URL |
| --- | --- |
| API root | `https://nano-gpt.com/api/v1` |
| 图模型目录 | `GET /api/v1/images/models` |
| 视频目录 | `GET /api/v1/video-models` |
| 出图（优先） | `POST /api/v1/images`（`input_references`） |
| 出图（回退 OAI） | `POST /v1/images/generations`（`imageDataUrl(s)` only — never mix `input_references`） |
| 出图（Edit 优先） | `POST /api/v1/images/edits` + `/edit`（`imageDataUrl(s)`；`*/edit` 模型） |
| 视频提交 | `POST /api/generate-video` |
| 视频状态 | `GET /api/video/status?requestId=` |

文档：https://docs.nano-gpt.com/introduction

## Catalog

`fetch_catalog` 合并图+视频；TTL 300s。行含 `supported_parameters.resolutions`、`supportsLora`（`*-lora` / tags，**heuristic**）、`pricing`。

`GET /api/catalog?backend=nano-gpt`。

## Import

无云端反查。导入 WxH **仅 FE 挑 resolution token**，不进 POST。

## Generate 出站字段表（图 `_image_body`）

| Studio | Vendor | 必填? | 备注 |
| --- | --- | --- | --- |
| `serviceId` | `model` | 是 | Civitai id→400；无 resolutions 列表→400 |
| `prompt` | `prompt` | 是 | **无官方 max**；`NANO_PROMPT_MAX=None`，禁止本地 1200 门闹。上游 `prompt_too_long` 仍按 400 出面 |
| `negativePrompt` | `negative_prompt` + `negativePrompt` | 否 | |
| `resolution` / WxH 参考 | `resolution` + `size`（**同一 token**） | 是 | `pick_resolution`；**禁止**自由 width/height 出站 |
| `width`/`height` | 仅算 `aspect_ratio` | — | `_core_image_body` / `sanitize_submitted_for_persist` **pop 掉** |
| `aspect` 推导 | `aspect_ratio` | 否 | `closest_aspect` |
| `seed` | `seed` | 否 | 整数 ≥ -1；**禁止 mod int32**；无 `seedClamped` |
| `quantity` | `n` / `nImages` | 否 | 1–4 |
| refs | `input_references`（normalized）/ `imageDataUrl(s)`（OAI+edit） | i2i | **禁止**同请求混两种风格；混用官方 `conflicting_image_inputs` |
| `denoise`/`strength` | `strength` | i2i | **未填省略**（不发明 0.65） |
| `steps` | `num_inference_steps` + `steps` | 否 | |
| `cfgScale` | `guidance_scale` | 否 | |
| `loras[]` | `loras[{path,scale}]` + `lora_i_url`/`lora_i_scale` | 否 | 官方 Image API **请求表无 loras**；仅 `*-lora` 模型 heuristic 通道；≤3 |
| mature | `enable_safety_checker:false` | 否 | |

视频 `_video_body`：`duration` 字符串；首帧 `imageDataUrl` 或 `imageUrl`/`image_url`；`mode` image-to-video|text-to-video。

## LoRA（fail-closed）

1. `model_supports_lora` 假 → 400 `lora_model_unsupported`。
2. `resolve_nano_loras`：versionId/download API → HEAD 307 → **新鲜 B2**（`Authorization=`）；禁止过期 B2 当入口；禁止 URL 含 Civitai API key / `?token=`。
3. 任一条失败 → 400 `lora_no_direct_url`（**不静默丢**）。
4. sidecar persist：`persist_safe_lora_path` 只存 download API / versionId。
5. 实测模型：`z-image-turbo-lora`、`wavespeed-ai/krea-v2/turbo-lora`。

夹具：version `3231694`；AIR-only 无 url → err。

## Seed / 分辨率 / 负面 / 进度 / 取消

| 项 | 行为 |
| --- | --- |
| seed | 整数原样出站；禁止 mod / clip int32；响应 seed 优先写入 meta |
| resolution | **仅**目录 token；空目录 → 400 |
| negative | 支持 |
| progress | 图 sync `none`；视频可 poll status，progress 仍 None |
| cancel | False |

## Materialize

无 Fal 式 `/out` 转换；`input_references` 用 http 或 data URL。

## Code anchors

| 动作 | 行 |
| --- | --- |
| TOKEN / endpoints / `NANO_PROMPT_MAX=None` | `nanogpt.py:18-55` |
| `pick_resolution` | `:174-244` |
| B2 resolve / sanitize | `:349-448` |
| `resolve_nano_loras` | `:474-598` |
| `_image_body` / `_video_body` | `:766-904` |
| `generate` / `_generate_image` | `:972-1073` |
| `job_status` | `:1141+` |

改 `nanogpt.py` 后必须 `python3 scripts/restart.py && ./run.sh`。

## Catalog 发现细节

仓库**无**离线全量 `*-models.json`。`fetch_catalog(force=False)`：

1. `GET /api/v1/images/models` → `_row_image`（TTL 内缓存）
2. `GET /api/v1/video-models` → `_row_video`
3. Studio：`GET /api/catalog?backend=nano-gpt`

`supportsLora`：id/name/tags 含 `lora` 或 `*-lora`；**upscale/bg/utility 禁止**因裸子串标 true（v0771）。**官方 supported_parameters 无 loras 键** — 此旗 heuristic。

机器可读说明 + 实测样本：[models/nanogpt-inventory.md](models/nanogpt-inventory.md) / [models/nanogpt-index.json](models/nanogpt-index.json)。

## 分辨率 / 出站剥离（再钉）

| 规则 | 行为 |
| --- | --- |
| `resolution=catalog_token` | 必须来自该模型 `supported_parameters.resolutions` |
| 空 resolutions | 400 |
| `width`/`height` | 仅用于挑最近 token / 算 `aspect_ratio`；`_image_body` / `_core_image_body` / `sanitize_submitted_for_persist` **pop 掉**，不进 POST、不进 sidecar |
| UI | 藏自由宽高行，只显 resolution 下拉（与 JSON 一致） |

## LoRA fail-closed 流程

```
model_supports_lora? --no--> 400 lora_model_unsupported
        |
       yes
resolve_nano_loras (versionId/download → HEAD 307 → 新鲜 B2)
        |
   任一条失败 --> 400 lora_no_direct_url
        |
   成功：loras[{path,scale}] + lora_i_url/scale（≤3）
persist：只存 download API / versionId（禁止签名 B2 / ?token=）
```

Civitai API key **永不**发给 Nano、永不进 URL query。

## 官方对照（2026-09-11）

- 文档：https://docs.nano-gpt.com/api-reference/endpoint/image-api-generate
- 目录：`GET /api/v1/images/models`、`GET /api/v1/video-models`（勿硬编能力表）
- 出图优先 `POST /api/v1/images`，失败再试 `/v1/images/generations`
- 官方请求键：`model, prompt, n, resolution, aspect_ratio, quality, output_format, seed, input_references`
- **没有** prompt 字符上限；**没有** seed int32；**没有** 官方 `loras[]` 键
- 视频：`POST /api/generate-video` + `GET /api/video/status?requestId=`
- 改 `nanogpt.py` 后必须 `python3 scripts/restart.py && ./run.sh`
