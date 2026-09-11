# Fal API 用法

适配器：`providers/fal.py`。capabilities：`lora=path`，`loraPath=http`，`progress=queue`，`cancel=True`，`estimate=pricing_api`，`resolution=free_wh`，`negative=True`，`i2i=first_frame`，`i2v=fal_endpoint`，`maxRefs` 仅该端点 OpenAPI maxItems（无则未知，禁止发明 9），`refImagesField=image_urls`。

## Auth

| | |
| --- | --- |
| Token | `~/.config/fal/token` |
| Header | `Authorization: Key {key}` |
| 无 key | 401 `"没有 Fal API Key"` |

## Base URLs

| 用途 | URL |
| --- | --- |
| Queue 提交 | `POST https://queue.fal.run/{endpoint_id}` |
| Status | `GET {QUEUE}/{base}/requests/{rid}/status?logs=1` |
| Result | `GET …/requests/{rid}` 或 `/response` |
| Cancel | `PUT …/requests/{rid}/cancel` |
| Models API | `https://api.fal.ai/v1/models` |
| 按端点查请求 | `GET …/models/requests/by-endpoint?endpoint_id=&request_id=&expand=payloads` |

`queue_bases`：嵌套端点（如 `fal-ai/flux/schnell`）状态可能挂在前两段 `fal-ai/flux`。

## Catalog

1. 本地 `docs/fal-models.json`（~1492）+ overlay `docs/fal-openapi-models.json`。
2. `GET /api/catalog?backend=fal`：`overlay_image_fields` 填 `imageFields`/`maxRefs`/`supportsLora`。
3. **禁止**用 `q` 把本地目录滤成 1 条；live `search_fal` 只 **追加** 新 id。
4. `FAL_PREFIXES`：`fal-ai/`、`krea/`、`minimax/`… 即使未入库也 `owns_service`。

## Import

`import_request(q, endpoint)`：解析 `fal|{eid}|{rid}` 或 UUID；`platform_payloads` → `map_fal_json_input` → Studio 字段（prompt、negativePrompt、steps←num_inference_steps、cfgScale←guidance_scale、image_size→width/height、loras path…）。

## Generate 出站字段表

`build_fal_input` → queue POST body：

| Studio key | Vendor field | 必填? | 备注 |
| --- | --- | --- | --- |
| `serviceId`/`endpoint` | URL path | 是 | Civitai 形态 id → 400 |
| `prompt` | `prompt`（或 `promptField`） | 视 required | **空字符串也保留 key**（minimax i2v 422 Field required） |
| `negativePrompt` | `negative_prompt` | 否 | optional 列表含该键或无 schema 时发 |
| `seed` | `seed` | 否 | int；无 clamp |
| `steps` | `num_inference_steps` | 否 | schema 有才发 |
| `cfgScale` | `guidance_scale` | 否 | |
| `width`+`height` | `image_size:{width,height}` | 否 | 非纯视频 |
| `aspectRatio` | `aspect_ratio` 或 `ratio` | 否 | `aspectRatioField` / kontext |
| `duration` | `duration` | 否 | 仅该端点 OpenAPI enum；禁发明 5/12/16 |
| `quantity`/`qty` | `num_images` | 否 | 上限也只能来自 schema |
| `scheduler` | `scheduler` | 否 | |
| `firstFrame`/refs | `image_url`/`start_image_url`/`first_frame_url`/`image_urls`… | i2v | `infer_image_fields` / catalog |
| `lastFrame` | `end_image_url`/`tail_image_url`/`last_frame_url` | 否 | |
| `loras[]` | 见 LoRA | 否 | |
| `videoUrl`/`audioUrl` | `video_url`/`audio_url` | 否 | |

提交前：`materialize_fal_media(inp)`；响应 `submittedInput` = **物化后** body。

## LoRA

| | |
| --- | --- |
| 形态 | schema 有才发 `loras:[{path,scale}]`；或 `lora_url`/`lora_path`/`lora` + scale |
| path 来源 | `path`/`url`/`downloadUrl`；否则 `versionId`→`https://civitai.com/api/download/models/{id}` |
| AIR | `_is_civitai_air` → **不当 path**，该条跳过 |
| scale | clip `[0,4]`；缺省读 `strength` |
| Sibling | 当前端点不支持 LoRA 且 payload 有 loras → `fal_lora_sibling` 改打 `{id}/lora` 等（**改 serviceId**） |
| 静默丢风险 | AIR-only 列表 → body 无 `loras`（测试断言）；非 LoRA 端点硬塞会 422 |

夹具：`3231694` 下载链；AIR-only `urn:air:sdxl:lora:civitai:1@2` → 无 loras。

## Seed / 分辨率 / 负面 / 进度 / 取消

| 项 | 行为 |
| --- | --- |
| seed | 无 clamp |
| resolution | free_wh + 可选 aspect |
| negative | 支持（schema 允许时） |
| progress | `queue`：status IN_QUEUE/IN_PROGRESS；勿造假 % |
| cancel | PUT cancel_urls；caps.cancel=True |

## Materialize（关键）

`local_out_to_data_url` / `materialize_fal_media`：

- `/out/<file>` → 读 `out/` → `data:{mime};base64,…`
- http(s)/已有 `data:` 不动
- 缺文件 → `ValueError` → 400，**禁止**把相对路径发给 Fal（`file_download_error`）

键：`image_url`、`start_image_url`、`first_frame_url`、`image`、`end_*`、`image_urls`、`video_url`、`audio_url`。

配合：`POST /api/upload-out` 先落盘再在 generate 时 materialize。

## Code anchors

| 动作 | 行 |
| --- | --- |
| TOKEN / QUEUE | `fal.py:13-51` |
| LoRA sibling / apply | `:291-380` |
| materialize | `:402-450` |
| `build_fal_input` | `:481-588` |
| `submit` | `:700-771` |
| `job_status` | `:908+` |
| `FalProvider.generate` | `:1182-1183` |
| cancel | `:1195+` |

## 夹具 / 注意

- Imagen4 preview OpenAPI 404 → `infer_image_fields` 返回 `[]`，勿编字段。
- 多填非文档字段 → 422 Unprocessable。

## 官方对照

来源：https://docs.fal.ai/model-apis/model-endpoints/queue

每端点 OpenAPI：`https://fal.ai/api/openapi/queue/openapi.json?endpoint_id=…`

- 推荐生产用 **submit → poll/webhook**。
- REST：`POST https://queue.fal.run/{endpoint}`，`Authorization: Key $FAL_KEY`。
- Studio：空 `prompt` 仍保留 key；`/out` 必须 materialize。
