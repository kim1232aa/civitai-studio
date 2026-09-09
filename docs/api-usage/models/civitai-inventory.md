# Civitai orchestration 服务清单（inventory）
> 源：`docs/catalog.json`（`total=304`）。刷新：`POST /api/catalog/refresh` 或 `GET /api/catalog?backend=civitai&refresh=1` → `ORCH/v2/services`。
> 全文索引：[civitai-index.json](civitai-index.json)。

## 计数总览

| 项 | 数 |
| --- | ---: |
| 服务条目 | **304** |
| engine=comfy | 40 |
| ecosystem/id 含 krea* | 8 |

## 按 category

| category | count |
| --- | ---: |
| image | 144 |
| video | 77 |
| model | 37 |
| 3d | 12 |
| text | 9 |
| audio | 9 |
| utility | 8 |
| chat | 8 |

## 按 status

| status | count |
| --- | ---: |
| unknown | 197 |
| available | 64 |
| degraded | 36 |
| unavailable | 7 |

## 按 engine（top）

| engine | count |
| --- | ---: |
| (null) | 50 |
| comfy | 40 |
| sdcpp | 29 |
| ai-toolkit | 27 |
| wan | 24 |
| flux2 | 18 |
| fal | 14 |
| qwen | 11 |
| grok | 10 |
| openai | 9 |
| happyHorse | 7 |
| ltx2.3 | 6 |
| ltx2.5 | 6 |
| seedream | 5 |
| google | 4 |
| ltx2 | 4 |
| vllm-omni | 4 |
| flux1-kontext | 3 |
| krea | 3 |
| ltx2-fal | 3 |

## 按 operation（top）

| operation | count |
| --- | ---: |
| (null) | 120 |
| createImage | 60 |
| editImage | 41 |
| createVariant | 14 |
| image-to-video | 8 |
| text-to-video | 8 |
| imageToVideo | 4 |
| referenceToVideo | 4 |
| createVideo | 4 |
| imageTo3D | 4 |
| extendVideo | 4 |
| firstLastFrameToVideo | 3 |
| textToVideo | 3 |
| editVideo | 3 |
| edit-video | 2 |
| reference-to-video | 2 |
| shapeGen | 2 |
| texGen | 2 |
| audioToVideo | 2 |
| videoToVideo | 2 |
| textTo3D | 1 |
| multiImageTo3D | 1 |
| base | 1 |
| customVoice | 1 |
| voiceDesign | 1 |

## 按 ecosystem（非空）

| ecosystem | count |
| --- | ---: |
| flux2Klein | 12 |
| flux1 | 7 |
| anima | 5 |
| sdxl | 5 |
| sd1 | 5 |
| boogu | 5 |
| hidream-o1 | 5 |
| mageflow | 5 |
| flux2Dev | 5 |
| krea2 | 4 |
| qwen | 4 |
| ernie | 3 |
| qwen3 | 3 |
| zImage | 2 |
| flux2klein | 2 |
| wan | 2 |
| lens | 2 |
| ideogram4 | 2 |
| ace_step_15_xl | 2 |
| minimaxh3 | 1 |
| zimageturbo | 1 |
| ltx23 | 1 |
| ltx25 | 1 |
| omnivoice | 1 |
| omnisvg | 1 |
| starvector | 1 |
| vtracer | 1 |
| ace_step_15 | 1 |
| chroma | 1 |
| ltx2 | 1 |
| zimagebase | 1 |
| (null) | 212 |

## 硬闸相关服务（krea / comfy 默认）

默认图：`image/comfy/krea2/turbo/createImage`（`DEFAULTS.serviceId`）。

默认视频：`video/minimax-h3-comfy/imageToVideo`。

| serviceId | engine | ecosystem | model | operation | status |
| --- | --- | --- | --- | --- | --- |
| `image/comfy/krea2/turbo/createImage` | comfy | krea2 | turbo | createImage | available |
| `image/comfy/krea2/edit/editImage` | comfy | krea2 | edit | editImage | degraded |
| `image/comfy/krea2/raw/createImage` | comfy | krea2 | raw | createImage | available |
| `image/fal/krea2/createImage` | fal | None | krea2 | createImage | degraded |
| `model/ai-toolkit/krea2` | ai-toolkit | krea2 | None | None | available |
| `image/krea/createImage/krea2-large` | krea | None | krea2-large | createImage | unknown |
| `image/krea/createImage/krea2-medium` | krea | None | krea2-medium | createImage | unknown |
| `image/krea/createImage/krea2-medium-turbo` | krea | None | krea2-medium-turbo | createImage | unknown |

## ⚠ Comfy-krea2+AIR ≠ Fal-Krea v2

- **Studio 硬闸**：`serviceId=image/comfy/krea2/turbo/createImage`，LoRA 形态 AIR `urn:air:krea2:lora:…`。
- **Civitai recipe「Fal-Krea v2」**：`engine:"fal" model:"krea2"` — 官方不接 LoRA / negative / 自由 WxH。
- **Fal 端点** `fal-ai/krea-2/turbo/lora` 是另一家 queue path LoRA，与 orchestration Comfy 路径无关。

## 缺口

- 大量 `status=unknown`（磁盘缓存未刷新 live health）。
- `engine`/`operation`/`ecosystem` 对 utility/chat 类常为 null。
- 本清单不展开 `parameters` 全文（见各服务 orchestration schema / `docs/capabilities.json`）。
