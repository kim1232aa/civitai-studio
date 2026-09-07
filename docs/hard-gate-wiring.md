# 硬闸出站：多参考图 + i2v 首帧

## 合同
- UI pack：`images = refs.slice(0, caps.maxRefs || caps.maxImages)`
- 出站字段：`caps.refImagesField`（images / image_urls / input_references / image_url）
- i2v：`firstFrame`/`sourceImage` 必须进各家官方图字段
- Catalog 只能收紧 `maxRefs`，不能抬高
- 门闩 / `stageUrls` 不动

## 共享模块
`providers/ref_images.py`：`payload_ref_images` / `primary_frame` / `max_refs`

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
画布可能写  / （不是只有 ）。
 四键并集； 调  镜像到 ，原字段保留。
