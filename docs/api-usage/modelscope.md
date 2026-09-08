# ModelScope（魔搭 AI / CN）API 用法

适配器：`providers/modelscope.py` — **两家独立** `ModelScopeProvider("ai"|"cn")`。capabilities 相同：`lora=hub_repo`，`loraPath=hub_owner_repo`，`progress=status_only`，`cancel=False`，`seed` mod int32，`i2i=source`，`i2v=image_url`，`maxRefs=1`，`refImagesField=image_url`，`videoAspect=True`，`videoDuration=False`。

## Auth / Base（禁止交叉）

| | modelscope-ai | modelscope-cn |
| --- | --- | --- |
| Token 文件 | `~/.config/modelscope/token` | `~/.config/modelscope-cn/token` |
| Env 回退 | `MODELSCOPE_API_TOKEN` 等 | `MODELSCOPE_CN_API_TOKEN` |
| Generate base | `https://api-inference.modelscope.ai/v1` | `https://api-inference.modelscope.cn/v1` |
| Hub 列表（共用） | `https://www.modelscope.cn/openapi/v1/models` | 同左（搜目录） |

Header：`Authorization: Bearer {key}`；异步提交加 `X-ModelScope-Async-Mode: true`；轮询加 `X-ModelScope-Task-Type: image_generation`。

主机解析失败 → 502 文案声明 **不会改走另一边**。旧域 `api.modelscope.ai` 已 NXDOMAIN。

## Catalog

- Hub task slug：`text-to-image-synthesis`（**不是** `text-to-image`）、`image-to-image`、`text-to-video-synthesis`、`image-to-video`。
- 钉选：`docs/ms-models.json`。
- `GET /api/catalog?backend=modelscope-ai|modelscope-cn`。
- LoRA 搜：Hub search，返回 `path=owner/repo`。

## Import

同 HF：无云端反查。

## Generate 出站字段表

`POST {base}/images/generations`：

| Studio | Vendor | 必填? | 备注 |
| --- | --- | --- | --- |
| `serviceId` | `model`（owner/repo） | 是 | Civitai id→400；`payload.model` 与 serviceId 不一致→400 拒 remap |
| `prompt` | `prompt` | 是 | |
| `negativePrompt` | `negative_prompt` | 否 | |
| `seed` | `seed` | 否 | `_clamp_seed` int32 mod |
| `steps` | `steps` | 否 | |
| `cfgScale` | `guidance` | 否 | 注意字段名 **guidance** 非 guidance_scale |
| `width`+`height` | `size` `"WxH"` | 否 | |
| refs / firstFrame | `image_url` | i2i/i2v | maxRefs=1；多图仅当 edit 且 list |
| `loras[]` | `loras` | 否 | **仅 Hub owner/repo** |

官方键集合：`model,prompt,negative_prompt,size,seed,steps,guidance,image_url,loras`。多余键 4xx 时会 slim 重试。

任务：`{id}|{task_id}`；轮询 `GET {base}/tasks/{tid}`。

## LoRA / 静默丢

| | |
| --- | --- |
| 出站（实测） | `loras: [{ "model": "owner/repo", "weight": 0.8 }, …]`；见 [`../modelscope-hub-lora.md`](../modelscope-hub-lora.md) |
| 勿发 | 字符串 `"owner/repo"` 或 `{repo: weight}`（会 500 Model does not exist） |
| http / Civitai 链 | **`continue` 跳过** |
| 有 loras 入站但全跳过 | 响应 `warning: 魔搭 LoRA 只要 Hub 的 owner/repo，Civitai 下载链不能用`（UI 可能不展示） |
| AIR `urn:` | 跳过 |
| 禁止 | Civitai→Hub 自动换模对照表（v0753 已撤） |

夹具：path `…/3231694` → `_modelscope_loras` 返回 `None`（`test_p0_wiring`）。

## Seed / 进度 / 取消

| 项 | 行为 |
| --- | --- |
| seed | mod int32 |
| progress | `status_only`：wait.progress=None；状态 PENDING/RUNNING/SUCCEED… |
| cancel | False |

## Materialize

无 `/out`→data: 专用路径；`image_url` 需外网可达或 data URL。

## Code anchors

| 动作 | 行 |
| --- | --- |
| Token / BASE | `modelscope.py:15-21` |
| `_clamp_seed` / `_modelscope_loras` | `:78-140` |
| Hub fetch | `:201-275` |
| `generate` | `:427-531` |
| `job_status` | `:533-582` |
| register ai+cn | `:585-588` |

## AI vs CN

能力表相同；**仅** token 路径与 `api-inference.modelscope.{ai|cn}` 不同。对接时 `backend` 必须显式 `modelscope-ai` 或 `modelscope-cn`。

## Catalog 钉选 vs Hub 发现

钉选文件：`docs/ms-models.json`（Studio 常用 7 条，见 [models/modelscope-inventory.md](models/modelscope-inventory.md)）。

Hub 列表（AI/CN **共用**搜目录，**不**共用生成 base）：

| | |
| --- | --- |
| Hub | `GET https://www.modelscope.cn/openapi/v1/models` |
| 任务 slug | `text-to-image-synthesis`（**不是** `text-to-image`，后者 0 条）、`image-to-image`、`text-to-video-synthesis`、`image-to-video` |
| 分页 | `page_size=50`，最多 `_HUB_PAGES=2` |
| LoRA 搜 | Hub search → 返回 `path=owner/repo`（`search_loras`） |
| Studio | `GET /api/catalog?backend=modelscope-ai|modelscope-cn` |

钉选样本：`Tongyi-MAI/Z-Image-Turbo`、`Qwen/Qwen-Image`、`Qwen/Qwen-Image-Edit`、`krea/Krea-2-Turbo`、`krea/Krea-2-Raw`、`krea/krea-realtime-video`。

异步：提交头 `X-ModelScope-Async-Mode: true`；轮询 `X-ModelScope-Task-Type: image_generation`；任务 id `{backend}|{task_id}`。

## 静默丢 / drift（再钉）

| 风险 | 行为 |
| --- | --- |
| Civitai `serviceId`（`image/...`） | 400「当前选中的是 Civitai 服务…」 |
| `payload.model` ≠ `serviceId` | 400 拒 remap |
| http / AIR LoRA | `_modelscope_loras` `continue`；有入站 loras 但全跳过 → `warning`（UI 可能不展示） |
| AI 主机失败 | **禁止**改走 CN（文案声明） |
| 旧域 `api.modelscope.ai` | 已 NXDOMAIN |

## 官方对照（2026-09-08）

- Hub OpenAPI：`https://www.modelscope.cn/openapi/v1/models`（filter.task 用 synthesis slug）。
- 生成：`POST https://api-inference.modelscope.{ai|cn}/v1/images/generations`；官方键集合见上表（多余键 4xx 时 slim 重试）。
- LoRA：字符串 `owner/repo` 或权重 dict（归一）；**不要**发 Civitai 下载链。
- 能力表：`lora=hub_repo`，`progress=status_only`，`cancel=False`，`maxRefs=1`，`refImagesField=image_url`。
- 全量 Hub 不在本仓库落盘 → inventory 只保证钉选 + 发现端点诚实。
