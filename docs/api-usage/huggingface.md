# Hugging Face API 用法

适配器：`providers/huggingface.py`。capabilities：`lora=path`，`loraConfidence=**unverified**`，`progress=none`，`cancel=False`，`estimate=none`，`seed` clamp=`none`（**禁止 mod int32**），`i2i=none`（映射 fal 通道可带图），`maxRefs=9`，`refImagesField=image_urls`。

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

Provider 偏好：`fal-ai` → `nscale` → `together` → `hf-inference`。**跳过** `replicate` 的 OpenAI 风格 POST（Hub LoRA 官方 SDK 可用 replicate；Studio 可验证出站以 Router fal-ai 为准）。

## Catalog

- 钉选：`docs/hf-models.json`
- 搜索：`search_hf` → Hub `?search=&limit=50`，pipeline ∈ text-to-image / image-to-image / text-to-video / image-to-video
- LoRA 搜：`GET …/models?search=&filter=lora`（**Hub tag ≠ supportsLora**）

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
| `seed` | `seed` | 否 | 整数原样；**禁止 mod int32** |
| `steps` | `num_inference_steps` | 否 | |
| `cfgScale` | `guidance_scale` | 否 | |
| `width`+`height` | `image_size:{w,h}` | 否 | |
| `scheduler` | `scheduler` | 否 | 仅 fal 通道 |
| refs | `image_url` / `image_urls` | i2i 类 endpoint | `wants_img` 启发式 |
| `loras[]` | `loras[{path,scale}]` | 否 | `apply_fal_loras` + `_force_loras`；**路由无 `/lora` sibling**；unverified |

### OpenAI 通道

| Studio | Vendor | 备注 |
| --- | --- | --- |
| prompt | `prompt` | |
| width×height | `size` `"WxH"` | |
| loras/scheduler | **忽略** | 官方 OpenAI 通道无 loras |

### Bytes / hf-inference

`{inputs: prompt, parameters: {negative_prompt, num_inference_steps, …}}` — **不带 LoRA**。

## LoRA / Hub-LoRA-as-model / 静默丢 / 假信心

### 官方路径 A — Hub LoRA 当 model（huggingface_hub ≥0.31）

```python
InferenceClient(provider="fal-ai").text_to_image(..., model="<hub-lora-id>")
# 或 provider="replicate"
```

- 条件：Hub `inferenceProviderMapping` live 且带 `adapter=lora` / `adapterWeightsPath`。
- Studio：`serviceId=<hub-lora-id>` → Router `fal-ai` + 把 adapter 权重 URL 写入 `loras[{path}]`（**不 invent scale**；IRON §5）。
- Catalog：`hubLoraAsModel=true`，`loraChannel=hub-lora-as-model`，`loraConfidence=official`（仅此路径）。
- 搜：`filter=lora` + exact `owner/repo`；匹配不上如实 miss，**禁止发明 Hub id**。
- **replicate**：官方 SDK 支持；Studio Router 的 OpenAI 风格 POST 仍跳过 replicate（与底模相同）。无 fal-ai 映射 → 诚实 400，不假装已发。
- 例（官方 release 样例，非发明）：`openfree/flux-chatgpt-ghibli-lora`。

### 路径 B — 底模 mapped fal 通道附 `loras[]`（仍 unverified）

- 发出去 ≠ 上游加载。`warning`：「已把 loras[] 附在 mapped 端点…路由没有 /lora sibling」。
- UI **禁止**把 `loraConfidence=unverified` 当绿勾「已加载」。
- `_maybe_lora_pid`：**不**改成 `…/turbo/lora`（Router「Model not supported」）。
- AIR 经 `_fal_lora_path` 丢弃；无 path 则该条不进。
- **禁止**把 `fal-ai/flux-lora` 等当成 HF `serviceId`（o33：换家 Fal 或选 Hub mid）。

夹具 path：`https://civitai.com/api/download/models/3231694`。

## Seed / 进度 / 取消

| 项 | 行为 |
| --- | --- |
| seed | 官方 integer 无 min/max；适配器不 wrap；禁止抄魔搭 int32 |
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

## 官方对照（2026-09-17，Inference Providers + Hub LoRA）

来源：https://huggingface.co/docs/inference-providers/guides/first-api-call ；huggingface_hub v0.31 release（LoRAs with fal.ai and Replicate）。

- SDK：`huggingface_hub.InferenceClient`；`api_key` = `HF_TOKEN`。
- 图：`text_to_image(prompt, model=…)`；可选 `provider="auto"|"fal-ai"|"replicate"|…`。
- **Hub LoRA-as-model**：`model="<hub-lora-id>"` + `provider="fal-ai"|"replicate"`（映射带 `adapterWeightsPath`）。
- 常见参数：`negative_prompt`、`num_inference_steps`、`guidance_scale`、`target_size`、`seed`（integer，**无公布 max**）。
- Studio 走 **Router**（`router.huggingface.co`）；Hub LoRA-as-model → `loraConfidence=official`；底模附 `loras[]` → 仍 `unverified`。

## v0821o33 HF score honesty

- HF Router **does not** host official Fal `/lora` apps (`fal-ai/flux-lora`, `fal-ai/krea-2/turbo/lora`, …).
- Default: `backend=huggingface` + those sids → **400** `HF Router 不托管该 Fal LoRA 端点，请换家 Fal`；`scoresAsHfClosedLoop=false`；chips kept in Composer.
- Debug only: `HF_ALLOW_FAL_TRANSPORT=1` re-enables o32 Path A (Fal key → `queue.fal.run`); still `transport=fal` / **not** HF closed-loop score.
- Real HF outbound: Hub mid → `router.huggingface.co` + HF token；`submittedInput` must **not** carry `transport=fal`.


## v0822o162 HF Hub-LoRA-as-model

- Catalog/search：Hub LoRA（mapping adapter）可发现；`hubLoraAsModel` 诚实戳。
- Outbound：`serviceId=<hub-lora-id>` → Router fal-ai + adapter path；不 invent scale / Hub id。
- 禁止：Midjourney 顶替、静默换家、curl `/api/generate` 当验收。
