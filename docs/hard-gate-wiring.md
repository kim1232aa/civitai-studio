# 硬闸出站：多参考图 + i2v 首帧

## 合同
- UI pack：`images = refs.slice(0, caps.maxRefs || caps.maxImages)` 或写到 `caps.refImagesField`
- 出站字段：`caps.refImagesField`（images / image_urls / input_references / image_url）
- i2v：`firstFrame`/`sourceImage` 必须进各家官方图字段
- Catalog 只能收紧 `maxRefs`，不能抬高
- 门闩 / `stageUrls` 不动

## 共享模块
`providers/ref_images.py`：`payload_ref_images` / `primary_frame` / `max_refs` / `normalize_payload_refs`

已接线：Civitai `apply_frames`、Fal `build_fal_input`、Nano `_source_images`、ModelScope generate、HF fal 路由。

## Provider 默认（= capabilities）
| backend | maxRefs | field |
|---|---|---|
| civitai | 9 | images |
| fal | 9 | image_urls |
| huggingface | 9 | image_urls |
| nano-gpt | 5 | input_references |
| modelscope-* | 1 | image_url |

## 入站字段对齐
画布可能写 `image_urls` / `input_references`（不是只有 `images`）。
`collect_ref_images` 对四键做并集；`/api/generate` 调 `normalize_payload_refs` 镜像到 `images`，原字段保留。

## Fal 单图端点
`imageFields` 仅有 `image_url`/`start_image_url` 等、无 `image_urls` 时，`overlay_image_fields` 强制 `maxRefs=1`（禁止挂 9 假装能吃满）。有 `image_urls` 才用 9。
