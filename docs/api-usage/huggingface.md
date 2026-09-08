# Hugging Face API 用法

适配器：`providers/huggingface.py`。capabilities：`lora=path`，`loraConfidence=**unverified**`，`progress=none`，`cancel=False`，`estimate=none`，`seed` min=-1 max=2147483647 clamp=`mod`，`i2i=none`（映射 fal 通道可带图），`maxRefs=9`，`refImagesField=image_urls`。

## Auth

| | |
| --- | --- |
| Token | `~/.config/huggingface/token`；回退 env `HF_TOKEN` / `HUGGINGFACE_TOKEN` |
| Header | `Authorization: Bearer {key}` |

## Base URLs

| 用途 | URL |
| --- | --- |
| Router | `https://router.huggingface.co` |
| Hub models | `https://huggingface.co/api/models` |
| Inference mapping | `GET {HUB}/{mid}?expand[]=inferenceProviderMapping` |
| Fal 风格 | `POST {ROUTER}/{provider}/{providerId}` |
| OpenAI 风格 | `POST {ROUTER}/{provider}/v1/images/generations` |
| Bytes / hf-inference | `POST {ROUTER}/hf-inference/models/{mid}` |

Provider 偏好：`fal-ai` → `nscale` → `wavespeed` → `together` → `hf-inference`。**跳过** `replicate` POST。

## Catalog

- 钉选：`docs/hf-models.json`
- 搜索：`search_hf` → Hub `?search=&limit=50`，pipeline ∈ text-to-image / image-to-image / text-to-video / image-to-video
- LoRA 搜：`GET …/models?search=&filter=lora`

## Import

无云端按图反查。`handle_import` 对 hf/魔搭/nano 返回 empty + 提示贴 Civitai 链接或上传带 parameters 的 PNG。

## Generate 出站字段表

同步完成（job id `hf|sync|{hex}`），无真实轮询。

### Fal 风格通道（`_call_fal`）

| Studio | Vendor | 必填? | 备注 |
| --- | --- | --- | --- |
| `serviceId` | Hub mid → mapped providerId | 是 | Civitai id → 400 |
| `prompt` | `prompt` | 是 | |
| `negativePrompt` | `negative_prompt` | 否 | |
| `seed` | `seed` | 否 | **mod int32**（`_prompt_body`） |
| `steps` | `num_inference_steps` | 否 | |
| `cfgScale` | `guidance_scale` | 否 | |
| `width`+`height` | `image_size:{w,h}` | 否 | |
| `scheduler` | `scheduler` | 否 | 仅 fal 通道 |
| refs | `image_url` / `image_urls` | i2i 类 endpoint | `wants_img` 启发式 |
| `loras[]` | `loras[{path,scale}]` | 否 | `apply_fal_loras` + `_force_loras`；**路由无 `/lora` sibling** |

### OpenAI 通道

| Studio | Vendor | 备注 |
| --- | --- | --- |
| prompt | `prompt` | |
| width×height | `size` `"WxH"` | |
| loras/scheduler | **忽略** | |

### Bytes / hf-inference

`{inputs: prompt, parameters: {negative_prompt, num_inference_steps, …}}` — **不带 LoRA**。

## LoRA / 静默丢 / 假信心

- 发出去 ≠ 上游加载。`warning`：「已把 loras[] 附在 mapped 端点…路由没有 /lora sibling」。
- UI **禁止**把 `loraConfidence=unverified` 当绿勾「已加载」。
- `_maybe_lora_pid`：**不**改成 `…/turbo/lora`（Router「Model not supported」）。
- AIR 经 `_fal_lora_path` 丢弃；无 path 则该条不进。

夹具 path：`https://civitai.com/api/download/models/3231694`。

## Seed / 进度 / 取消

| 项 | 行为 |
| --- | --- |
| seed | `n<-1→-1`；`n>2147483647→n%limit`（0→limit） |
| progress | `none` — job_status 直接 succeeded + progress=1；**禁止假百分比动画当真实** |
| cancel | False |

## Materialize

无专用 materialize；若走 fal 通道且图为 `/out`，当前 HF 路径**未**调用 `materialize_fal_media` — 优先 http/data URL。

## Code anchors

| 动作 | 行 |
| --- | --- |
| TOKEN / ROUTER | `huggingface.py:16-38` |
| `_prompt_body` seed | `:130-168` |
| `_force_loras` / `_call_fal` | `:215-280` |
| `generate` | `:487-577` |
| `job_status` | `:579-585` |

## 夹具

`test_p0_wiring`：`_maybe_lora_pid` 保持 turbo；`_force_loras` 塞 3231694。

## 官方对照（2026-09-08，Inference Providers）

来源：https://huggingface.co/docs/inference-providers/guides/first-api-call

- SDK：`huggingface_hub.InferenceClient` / `@huggingface/inference`；`api_key` = `HF_TOKEN`。
- 图：`text_to_image(prompt, model=…)`；可选 `provider="auto"|"fal-ai"|"replicate"|…`。
- 常见参数：`negative_prompt`、`num_inference_steps`、`guidance_scale`、`target_size`（部分 provider）。
- Studio 走 **Router**（`router.huggingface.co`）映射通道，不是裸 Hub widget；`loraConfidence=unverified` 仍成立——官方 client 示例也不保证 LoRA sibling。
