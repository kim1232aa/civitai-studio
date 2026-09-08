# Fal 模型清单（inventory）
> 源：`docs/fal-models.json`（total=1492）+ `docs/fal-openapi-models.json`（overlay models=141）。
> `supportsLora` / `imageFields` / `maxRefs` 由 `providers.fal.overlay_image_fields` + `fal_supports_lora` 计算，与 `GET /api/catalog?backend=fal` 一致。
> **全文索引**：[fal-index.json](fal-index.json) / [fal-index.csv](fal-index.csv) — 勿把 1492 条写成散文。

## 计数总览

| 项 | 数 |
| --- | ---: |
| 目录条目 | **1492** |
| OpenAPI overlay 命中 | 129 / overlay 文件 141 |
| supportsLora=true | **160** |
| 有 imageFields | 293 |
| maxRefs>1（image_urls） | 65 |
| supportsI2v | 236 |
| FAL_PREFIXES（owns_service 即使用未入库） | `fal-ai/, krea/, minimax/, bytedance/, openai/, google/, xai/, wan/, kling/, alibaba/, lightricks/` |

## 按 category

| category | count |
| --- | ---: |
| image | 678 |
| video | 533 |
| audio | 165 |
| 3d | 66 |
| upscale | 27 |
| bg | 23 |

## 按 falCategory（top）

| falCategory | count |
| --- | ---: |
| image-to-image | 396 |
| image-to-video | 208 |
| video-to-video | 203 |
| text-to-image | 200 |
| text-to-video | 136 |
| training | 59 |
| text-to-audio | 47 |
| audio-to-audio | 43 |
| image-to-3d | 41 |
| vision | 34 |
| text-to-speech | 34 |
| audio-to-video | 21 |
| text-to-3d | 12 |
| 3d-to-3d | 12 |
| speech-to-text | 10 |
| llm | 8 |
| json | 6 |
| video-to-audio | 6 |
| video-to-text | 3 |
| text-to-json | 3 |
| speech-to-speech | 2 |
| image-to-json | 2 |
| unknown | 2 |
| audio-to-text | 2 |
| image-to-text | 1 |

## 按 id 前缀（vendor prefix）

| prefix | count |
| --- | ---: |
| fal-ai | 1201 |
| bria | 37 |
| bytedance | 19 |
| alibaba | 16 |
| topaz | 16 |
| xai | 15 |
| minimax | 14 |
| google | 12 |
| blackforestlabs | 12 |
| veed | 11 |
| tripo3d | 10 |
| openrouter | 9 |
| ideogram | 9 |
| mirelo-ai | 8 |
| luma | 8 |
| hitem3d | 8 |
| rundiffusion-fal | 8 |
| wan | 7 |
| nvidia | 7 |
| lightricks | 6 |
| sonilo | 6 |
| recraft | 6 |
| microsoft | 4 |
| imagineart | 4 |
| decart | 4 |
| moonvalley | 4 |
| krea | 3 |
| pixelcut | 3 |
| cassetteai | 3 |
| meshy | 3 |
| reve | 3 |
| openai | 2 |
| meta | 2 |
| clarityai | 2 |
| resemble-ai | 2 |
| mirage-api | 2 |
| perceptron | 2 |
| argil | 2 |
| smoretalk-ai | 1 |
| async | 1 |

## imageFields 形态分布

| imageFields | count | 暗示 maxRefs |
| --- | ---: | --- |
| `(none)` | 1199 | — |
| `image_url` | 122 | 1 |
| `image_url,end_image_url` | 81 | 1 |
| `image_urls` | 55 | 9 |
| `end_image_url,image_url` | 11 | 1 |
| `start_image_url,end_image_url` | 6 | 1 |
| `video_url,image_urls` | 5 | 9 |
| `first_frame_url,last_frame_url` | 5 | 1 |
| `start_image_url,end_image_url,image_urls` | 3 | 9 |
| `image_url,tail_image_url` | 2 | 1 |
| `mask_image_url,image_urls` | 1 | 9 |
| `image_url,image_urls` | 1 | 9 |
| `end_image_url,start_image_url` | 1 | 1 |

## supportsLora 样本（前 40）

启发式：id/name 含 `lora`，或 required/optional 含 `loras`/`lora_url`/`lora_path`/`lora`，或 falCategory/tags 含 lora。

- `fal-ai/flux-lora`
- `fal-ai/fast-sdxl`
- `fal-ai/qwen-image-edit-2511-multiple-angles`
- `fal-ai/flux-lora-fast-training`
- `fal-ai/flux-2/lora`
- `fal-ai/krea-2/turbo/lora`
- `fal-ai/flux-lora/image-to-image`
- `fal-ai/flux-kontext-lora`
- `fal-ai/krea-2-trainer`
- `fal-ai/flux-lora-portrait-trainer`
- `fal-ai/flux-2/lora/edit`
- `fal-ai/z-image/turbo/lora`
- `fal-ai/flux-general`
- `minimax/h3/reference-to-video/lora`
- `fal-ai/flux-2/klein/9b/edit/lora`
- `fal-ai/lora`
- `fal-ai/qwen-image-edit-2511/lora`
- `fal-ai/flux-general/inpainting`
- `fal-ai/flux-lora/inpainting`
- `fal-ai/flux-2/klein/9b/base/edit/lora`
- `fal-ai/flux-general/image-to-image`
- `fal-ai/flux-lora-fill`
- `fal-ai/stable-diffusion-v35-large`
- `minimax/h3/image-to-video/lora`
- `fal-ai/fast-sdxl/image-to-image`
- `fal-ai/qwen-image-2512/lora`
- `fal-ai/flux-control-lora-depth`
- `fal-ai/flux-2-lora-gallery/realism`
- `fal-ai/qwen-image-edit-plus-lora-gallery/multiple-angles`
- `fal-ai/flux-control-lora-canny`
- `fal-ai/flux-2-lora-gallery/multiple-angles`
- `fal-ai/flux-kontext-lora/inpaint`
- `fal-ai/lora/image-to-image`
- `fal-ai/flux-2/klein/4b/edit/lora`
- `fal-ai/flux-2-lora-gallery/apartment-staging`
- `fal-ai/flux-2/klein/9b/lora`
- `fal-ai/z-image-turbo-trainer-v2`
- `minimax/h3/text-to-video/lora`
- `fal-ai/wan/v2.2-a14b/image-to-video/lora`
- `fal-ai/qwen-image-edit-plus-lora`

…另有 120 条，见 JSON 索引 `supportsLora=true`。

## supportsI2v 样本（前 25）

- `minimax/h3-max/image-to-video`
- `fal-ai/kling-video/v3/pro/image-to-video`
- `bytedance/seedance-2.5/reference-to-video`
- `bytedance/seedance-2.5/image-to-video`
- `fal-ai/kling-video/v2.5-turbo/pro/image-to-video`
- `minimax/h3/reference-to-video`
- `fal-ai/kling-video/v3/standard/image-to-video`
- `bytedance/seedance-2.0/image-to-video`
- `bytedance/seedance-2.0/reference-to-video`
- `minimax/h3/image-to-video`
- `fal-ai/kling-video/v2.6/pro/image-to-video`
- `xai/grok-imagine-video/v1.5/image-to-video`
- `fal-ai/veo3.1/fast/image-to-video`
- `xai/grok-imagine-video/image-to-video`
- `fal-ai/bytedance/seedance/v1.5/pro/image-to-video`
- `fal-ai/veo3.1/image-to-video`
- `fal-ai/kling-video/v2.1/standard/image-to-video`
- `fal-ai/veo3.1/lite/image-to-video`
- `alibaba/wan-3.0-prime/reference-to-video`
- `blackforestlabs/flux-3/image-to-video`
- `fal-ai/bytedance/seedance/v1/pro/image-to-video`
- `google/gemini-omni-flash/image-to-video`
- `bytedance/seedance-2.0/fast/reference-to-video`
- `bytedance/seedance-2.0/fast/image-to-video`
- `alibaba/wan-3.0-prime/image-to-video`

## 已知缺口

- 本地 `fal-models.json` **没有**预存 `supportsLora` 键；运行时由适配器推断。 OpenAPI overlay 仅覆盖 **141** 端点，其余靠 id 启发式 + `infer_image_fields`。
- Imagen4 preview/fast/ultra：OpenAPI 404，`infer_image_fields` 故意返回 `[]`，勿编字段。
- `fal_lora_sibling` 会在无 LoRA 字段时改打 `{id}/lora` 兄弟端点（改 serviceId）——见 `docs/api-usage/fal.md`。
- camera_lora / distill_lora_*（LTX 视频）计入 schema 字段含 lora，但**不是**用户 Civitai path LoRA；对接时勿当普通 `loras[{path,scale}]`。
- Catalog 搜索：`q` **禁止**把本地 1492 滤成 1 条；live search 只追加。
