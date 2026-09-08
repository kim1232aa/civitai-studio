# 魔搭 ModelScope 模型清单（inventory）
> 钉选源：`docs/ms-models.json`（**7** 条）。AI/CN 共用 Hub 列表；生成 base/token **禁止交叉**。
> 索引：[modelscope-index.json](modelscope-index.json)。

## 钉选模型（Studio 常用）

| id | name | category | task | tags |
| --- | --- | --- | --- | --- |
| `Qwen/Qwen-Image` | Qwen Image | image | text-to-image | t2i |
| `Qwen/Qwen-Image-Edit` | Qwen Image Edit | image | image-to-image | i2i |
| `MusePublic/Qwen-Image-Edit` | Qwen Image Edit (MusePublic) | image | image-to-image | i2i |
| `Tongyi-MAI/Z-Image-Turbo` | Z-Image Turbo | image | text-to-image | t2i |
| `krea/Krea-2-Turbo` | Krea 2 Turbo | image | text-to-image | t2i, krea2 |
| `krea/Krea-2-Raw` | Krea 2 Raw | image | text-to-image | t2i, krea2 |
| `krea/krea-realtime-video` | Krea Realtime Video | video | text-to-video | t2v, krea |

## 发现端点

| | |
| --- | --- |
| Hub | `GET https://www.modelscope.cn/openapi/v1/models` |
| 任务 filter | `filter.task=` `text-to-image-synthesis` / `image-to-image` / `text-to-video-synthesis` / `image-to-video` |
| 分页 | page_size=50，最多 2 页（`_HUB_PAGES`） |
| LoRA 搜 | Hub search，返回 `path=owner/repo` |
| 生成 | `POST {ai|cn}/images/generations`；任务轮询 `GET …/tasks/{tid}` |

## Studio 出站键（官方集合）

`model, prompt, negative_prompt, size, seed, steps, guidance, image_url, loras`

LoRA **只要** Hub `owner/repo`；Civitai http / AIR → skip + warning。

## 缺口

- 无离线全量 Hub 快照；本 inventory 仅钉选 + 发现说明。
- `docs/ms-models.json` 的 `task` 用 `text-to-image` 标签，但 Hub **filter** 必须用 `text-to-image-synthesis`。
- cancel=False；progress=status_only。
