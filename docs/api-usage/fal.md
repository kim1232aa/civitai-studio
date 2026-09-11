# Fal API 用法

适配器：`providers/fal.py`。capabilities：`lora=path`，`loraPath=http`，`progress=queue`，`cancel=True`，`estimate=pricing_api`，`resolution=free_wh`，`negative=True`，`i2i=first_frame`，`i2v=fal_endpoint`，`maxRefs` **仅该端点 OpenAPI maxItems**（无则未知，禁止发明 9），`refImagesField=image_urls`。

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
| `prompt` | `prompt`（或 `promptField`） | 视 required | **空字符串也保留 key** |
| `negativePrompt` | `negative_prompt` | 否 | schema 有才发 |
| `seed` | `seed` | 否 | int；无 clamp |
| `steps` | `num_inference_steps` | 否 | schema 有才发 |
| `cfgScale` | `guidance_scale` | 否 | |
| `width`+`height` | `image_size:{width,height}` | 否 | 非纯视频 |
| `aspectRatio` | `aspect_ratio` 或 `ratio` | 否 | |
| `duration` | `duration` | 否 | **仅该端点 OpenAPI enum**，禁发明 5/12/16 |
| `quantity`/`qty` | `num_images` | 否 | 上限也只能来自 schema |
| `scheduler` | `scheduler` | 否 | |
| `firstFrame`/refs | `image_url`/`image_urls`… | i2v | catalog / OpenAPI |
| `loras[]` | 见 LoRA | 否 | |

提交前：`materialize_fal_media(inp)`。

## LoRA

| | |
| --- | --- |
| 形态 | schema 有才发 `loras:[{path,scale}]` |
| AIR | 不当 path，该条跳过 |
| 静默丢 | AIR-only 列表 → body 无 `loras` |

## 官方对照

Queue：https://docs.fal.ai/model-apis/model-endpoints/queue

每端点 OpenAPI：`https://fal.ai/api/openapi/queue/openapi.json?endpoint_id=…`
