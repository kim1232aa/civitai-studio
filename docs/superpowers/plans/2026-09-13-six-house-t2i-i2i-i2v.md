# 六家 × 文生图 / 图生图 / 图生视频（页 ↑）

> executing-plans：按任务勾选推进。只能页面点 ↑。禁 curl `/api/generate`。每格一张没用过的 hinablue 原帖全文 prompt。

**Goal:** 六家（civitai / fal / huggingface / modelscope-ai / modelscope-cn / nano-gpt）各打通文生图、图生图、图生视频，成片写回原卡。

## Constraints

- 页面点 `#send` ↑。POST `/api/import` 允许。
- Prompt 来自 https://civitai.red/user/hinablue/images，全文，不重复。
- 禁旧夹具：142373903, 142373894, 142373085, 142337256, 142337258。已用：142526583（Civitai 文生图）。
- API 支持的参数填满。LoRA 官方不接则换图或按该家 schema 发支持的字段，不发明 strength。
- 只能完善不许删功能。禁空壳。

## Matrix

| # | 家 | 操作 | hinablue | 服务偏好 |
|---|---|---|---|---|
| T1 | civitai | t2i | 142526583 已出片 | krea2 turbo createImage |
| T2 | civitai | i2i | 142337259 | krea2 edit / flux2 klein edit |
| T3 | civitai | i2v | 142559567 | minimax-h3-comfy imageToVideo |
| T4 | fal | t2i | 142337262 | fal-ai/krea-2/turbo |
| T5 | fal | i2i | 142337270 | flux-pro/kontext 或 z-image i2i |
| T6 | fal | i2v | 142337277 | kling / minimax image-to-video |
| T7 | huggingface | t2i | 141695613 | krea/Krea-2-Turbo |
| T8 | huggingface | i2i | 141696147 | Qwen-Image-Edit |
| T9 | huggingface | i2v | 141696150 | Wan2.2-TI2V-5B |
| T10 | modelscope-ai | t2i | 142337257 | krea/Krea-2-Turbo |
| T11 | modelscope-ai | i2i | 142337266 | Qwen-Image-Edit |
| T12 | modelscope-ai | i2v | 142337283 | Wan2.1-I2V-14B-720P |
| T13 | modelscope-cn | t2i | 141696154 | krea/Krea-2-Turbo |
| T14 | modelscope-cn | i2i | 140608943 | Qwen-Image-Edit |
| T15 | modelscope-cn | i2v | 142526390 | Wan2.1-I2V-14B-720P |
| T16 | nano-gpt | t2i | 142526398 | z-image-turbo / krea-v2 |
| T17 | nano-gpt | i2i | 139793404 | z-image-turbo-image-to-image |
| T18 | nano-gpt | i2v | 139791098 | seedance / minimax i2v |

## How to execute

每格：选对应家分镜 → 导入原帖 → 切 backend / 图片|视频 → 匹配服务 → 图生图连参考、图生视频挂首帧 → 点 ↑ → 等写回原卡。失败则查官方 schema，换图，不装接。
