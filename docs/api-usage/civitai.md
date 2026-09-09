# Civitai API 用法

适配器：`providers/civitai.py`（+ `civitai_workflows.py`）。capabilities：`lora=air`，`progress=rate`，`cancel=True`，`estimate=buzz`，`resolution=free_wh`，`negative=True`，`sampler=True`，`i2v=sourceImage`，`maxRefs=9`，`refImagesField=images`。

## Auth

| | |
| --- | --- |
| Token 路径 | `~/.config/civitai/token`（`TOKEN_PATH`） |
| Header | `Authorization: Bearer {token}` |
| 无 key | HTTP 401 `"没有 API Key"` |

## Base URLs / 官方端点

| 用途 | URL |
| --- | --- |
| Orchestration | `https://orchestration.civitai.com`（`ORCH`） |
| 站点 REST | `https://civitai.com/api/v1`（`SITE`） |
| 目录刷新 | `GET {ORCH}/v2/services?limit=200&offset=` |
| 提交工作流 | `POST {ORCH}/v2/consumer/workflows?whatif=&wait=0&hideMatureContent=` |
| 任务状态 | `GET {ORCH}/v2/consumer/workflows/{wf_id}` |
| 取消 | `DELETE {ORCH}/v2/consumer/workflows/{wf_id}` |
| 健康 | `GET {ORCH}/health` |
| 模型搜索 | `GET {SITE}/models?query=&types=LORA&nsfw=` |
| 版本 / AIR | `GET {SITE}/model-versions/{id}`（公开优先；auth mini/full 回退） |
| 导入生成数据 | tRPC `image.getGenerationData` / `image.get`；公开页 `__NEXT_DATA__` |
| Recipe | `POST {ORCH}/v2/consumer/recipes/{recipe}`（含 `customComfy`） |

## Catalog 发现

1. 磁盘缓存 `docs/catalog.json`（`load_catalog_disk`）。
2. `refresh_catalog` 分页拉 `ORCH/v2/services`，`slim_item` 写入。
3. Studio：`GET /api/catalog?backend=civitai&q=&category=&status=&refresh=1`。
4. `find_service(serviceId)` / `match_service(engine,operation,ecosystem,model,category)`。

默认服务（`DEFAULTS`）：图 `image/comfy/krea2/turbo/createImage`；视频 `video/minimax-h3-comfy/imageToVideo`。

## Import 映射

`import_image` → Studio 字段（节选）：

| 导入结果键 | 含义 |
| --- | --- |
| `backend` | 固定 `"civitai"`（禁止留 fal 默认） |
| `serviceId` / `engine` / `ecosystem` / `model` / `operation` | 匹配目录服务 |
| `prompt` / `negativePrompt` | meta / PNG |
| `width`/`height`/`steps`/`cfgScale`/`seed` | |
| `sampler`/`scheduler` | 归一到 `SAMPLERS`/`SCHEDULERS` |
| `diffusionModel` | AIR |
| `loras[]` | `{air, strength, name, versionId, …}` — **air 必填才出站** |
| `mediaUrl` | 原图 |

本地 PNG：`handle_import` → `io_meta.parse_media_bytes` + `enrich_local_parse`。

## Generate 出站字段表

Studio payload → orchestration `steps[0].input`（`build_workflow`）：

| Studio key | Vendor field | 必填? | 备注 |
| --- | --- | --- | --- |
| `serviceId` | 选服务 → 填入 parameters | 推荐 | 空则 match_service / DEFAULTS；storyboard 空 service **硬阻断** |
| `prompt` | `prompt` | 视 cap | |
| `negativePrompt` | `negativePrompt` | 否 | caps.negative=True |
| `width`/`height` | `width`/`height` | 视 required | clamp 16–2048 |
| `steps` | `steps` | 否 | 1–150 |
| `cfgScale` | `cfgScale` | 视 required | float |
| `seed` | `seed` | 否 | int；空/`random` 不发；**无 int32 clamp**（clamp=none） |
| `sampler`/`scheduler` | 同名 | 否 | 仅 Civitai 有意义 |
| `denoise` | `denoise` | 否 | float |
| `quantity` | `quantity` | 否 | 1–12 |
| `duration`/`aspectRatio`/`resolution` | 同名 | 视频 | kling duration→str |
| `diffusionModel` | `diffusionModel` | 否 | AIR |
| `loras[]` | `loras` | 否 | **`{air: strength}` dict**；无 air **静默跳过该条**（chip 应保证有 air） |
| `firstFrame`/`sourceImage`/`images`… | `apply_frames` → frameFields | i2v/i2i | 见下 |
| `allowMatureContent` | 顶层 + query | 否 | 默认 True |
| `engine`/`operation`/`ecosystem`/`model`/`version`/`provider` | 同名覆盖 | 否 | |

顶层 body：`{allowMatureContent, steps:[{$type: imageGen|videoGen|…, input}]}`。

**帧字段**（`apply_frames` + `capabilities.json` `frameFields`）：

- 首帧名族：`firstFrame`/`sourceImage`/`image`/`sourceImageUrl`/`startImage`
- 尾帧：`lastFrame`/`endImage`/`endSourceImage`
- 多参考：`images`/`referenceImages`（≤`maxRefs` 9）
- wan v2.2/2.5/2.6：用 `sourceImage`+`images`，**不发** `startImage`
- hunyuan：`loras` dict → `[{air,strength}]` 列表

## LoRA 形态 / 静默丢风险

| | |
| --- | --- |
| 官方形态 | AIR：`urn:air:{eco}:lora:civitai:{modelId}@{versionId}` |
| Studio chip | `{air, strength|scale, name, versionId, path?, downloadUrl?}` |
| 出站 | `lora_map`：仅 `air` 非空 → `{air: float(strength)}` |
| 静默丢 | **无 air 的条目被 continue 掉** — UI 必须保证 import/搜模写入 air |
| path/url | Civitai orchestration **不吃** http path；那是 Fal/Nano 的事 |

硬闸夹具：`134923572` → air `urn:air:krea2:lora:civitai:2323765@3071582` @ 0.8。

## Seed / 分辨率 / 负面 / 进度 / 取消

| 项 | 行为 |
| --- | --- |
| seed | 无 clamp；原样 int |
| resolution | `free_wh`；视频另可有 `resolution` token（720p/1080p） |
| negative | 支持 |
| progress | `rate`：`wait.progress`←`estimatedProgressRate`；`precedingJobs`/`etaSeconds`/`completeAt`（`_wait_snapshot`） |
| cancel | `DELETE` workflows；Studio `POST|DELETE /api/jobs/{id}/cancel` |

## Materialize

Civitai blob URL 由 orchestration 返回；本地 `/out` 不经 materialize。导入媒体走公开 CDN。

## Code anchors

| 动作 | 位置 |
| --- | --- |
| Auth / call | `civitai.py:18-75` |
| Catalog refresh | `:116-134` |
| `lora_map` | `:175-185` |
| `apply_frames` | `:248-330` |
| `build_workflow` | `:363-443` |
| `import_image` | `:665-942` |
| `submit` | `:945-952` |
| `generate` / `job_status` / `cancel_job` | `:1109-1167` |
| Provider register | `:1399+` |

## 已知夹具

- Image `134923572` + LoRA air `urn:air:krea2:lora:civitai:2323765@3071582`
- Legacy 调查图 `139791102` + version `3231694`（provider-lora.md；审查勿写死单一旧 id）

## 官方对照（2026-09-08，developer.civitai.com recipes）

索引：https://developer.civitai.com/orchestration/recipes/

- 工作流：`POST https://orchestration.civitai.com/v2/consumer/workflows`（`wait=0` 后 GetWorkflow 轮询）。
- LoRA 通用形态：`loras: { "urn:air:…": strength }`（与 Studio `lora_map` 一致）。
- **两条 Krea 勿混**：
  - **Fal-Krea v2** recipe：`engine:"fal"`, `model:"krea2"`, `size` medium|large — **官方写明不接 LoRA / negative / width·height**（aspectRatio + creativity）。
  - **Studio 硬闸路径**：`serviceId` `image/comfy/krea2/turbo/createImage`（Comfy + ecosystem `krea2`）— **吃** `urn:air:krea2:lora:…`；夹具 job `12100372-20260908044346005` air@0.8 Pass。
- 需要 LoRA 的开放权重族：Flux 2 Klein / Flux 1 / SDXL / Qwen sdcpp / ERNIE 等 recipe；勿把 Fal-Krea 文档套到 Comfy-krea2 出站上。
