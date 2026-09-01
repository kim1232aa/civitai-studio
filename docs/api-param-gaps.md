# API 参数漏接清单（v0755）

对照：`payload()` + 各 `providers/*.py` generate。只读文档 / GET。禁止 POST 生成。

图例：**漏** = 官方有我们没发或发错；**编** = 官方没有我们在发明；**已接** = 现状 OK。

## Civitai

| 字段 | 官方 | 现状 | 优先级 |
|---|---|---|---|
| prompt / negative / width / height / steps / cfgScale / seed / sampler / scheduler / denoise / loras(AIR) / quantity | orchestration OpenAPI / recipe input | 已接；allowed set 在 `build_input` | — |
| 首尾帧 / duration / resolution（按引擎） | 各 video recipe | 已接（UI 按 engine 显字段） | — |
| 取消 | `DELETE /v2/consumer/workflows/{id}` | 已接 `cancel_job` | — |
| 预估 | `whatif=true` | 已接 | — |
| 进度 | `estimatedProgressRate` / `precedingJobs` | waitPane 已接 | — |

无大漏。P2：catalog dump 304 vs live 309（chat 行），与出图无关。

## Fal

| 字段 | 官方 | 现状 | 优先级 |
|---|---|---|---|
| **aspect_ratio / ratio** | 多端 OpenAPI（kling o3 ref、ltx、veo、runway `ratio` 等）；`fal.py` 只在 `payload.aspectRatio` 有值时写入 | **漏**：`index.html` 全文无 `aspectRatio`，视频只发 WxH/duration | **P0** |
| num_images / quantity | 多端 `num_images` | UI 有 `qty`，`build_fal_input` **不映射** | **P1** |
| 预估 | `GET https://api.fal.ai/v1/models/pricing?endpoint_id=`（unit_price） | whatif 固定 note「无黄 Buzz」，不调 pricing | **P1** |
| prompt / negative_prompt / seed / steps→num_inference_steps / cfg→guidance_scale / image_size / scheduler / 首尾帧 imageFields / LoRA path | OpenAPI | 已接（字段门控 optional）；LoRA 可切 `/lora` sibling | — |
| 取消 | `PUT …/requests/{id}/cancel` | 已接 | — |
| Imagen4 preview* 字段 | OpenAPI 404 | **不编**（正确） | — |
| 非文档字段硬塞 | — | 有 422 风险；勿编 | P2 防回归 |

## Hugging Face

| 字段 | 官方 | 现状 | 优先级 |
|---|---|---|---|
| LoRA | 路由无 `…/turbo/lora`；只能附在 mapped body | 会发出去，**上游是否加载未证实**；UI 不展示 warning | **P0**（假信心） |
| scheduler | InferenceClient/fal 通道有；OpenAI `/v1/images/generations` 无 | UI 对 HF 显示 scheduler；OpenAI 通道忽略 | **P1** |
| seed 钳 int32 | 文档/上游限 | 已接（取模不丢） | — |
| width/height → image_size | fal 风格通道 | 已接 | — |
| steps / guidance_scale | fal 风格 | 已接 | — |
| 取消 | 同步生成，无 queue cancel | 按钮会打到「没有取消接口」 | P2 |
| 预估 | 无统一官方 estimate | whatif stub | P2 |
| 图生视频参数 | 部分 provider | `num_frames≈duration*8` **半编** | **P1** 核对各 provider 文档后再定 |

## 魔搭 AI / 魔搭 CN（两家，禁止互切）

| 字段 | 官方 | 现状 | 优先级 |
|---|---|---|---|
| model / prompt / negative_prompt / size=`WxH` / seed / steps / guidance / image_url / loras(Hub owner/repo) | AIGC 文档；`docs/provider-lora.md` | 已接；Civitai http LoRA **跳过** + warning（UI 不显示） | **P1** UI 显示 warning |
| sampler / scheduler / denoise / AIR | 官方无 | slimPayload 已删 sampler；勿再塞 | — |
| 取消 | 未见公开 cancel task | base 默认「没有取消接口」 | P2 |
| 预估 | 无 | stub | P2 |
| AI↔CN fallback | 禁止 | 代码分 token/base，勿互切 | P0 防回归 |

## NanoGPT (`nano-gpt`)

| 字段 | 官方 | 现状 | 优先级 |
|---|---|---|---|
| **resolution** | 必须是目录 `supported_parameters.resolutions` token（`1k`/`2k`/`1024*1536`/`square_hd`…） | `pick_resolution` 在 **空列表时发明 `{w}x{h}`** | **P0** 删发明分支；空列表则 400 |
| 分辨率 UI | 同上 | UI 仍是自由 WxH，靠最近点选 token；未暴露目录 token 下拉 | **P1** |
| aspect_ratio | 文档 + body | 适配器由 WxH 推 `aspect_ratio`；UI 无独立控件 | P1 |
| LoRA `loras[{path,scale}]` + `lora_N_url` | 实测 `*-lora` 模型 | 已接；非 lora 模型不保证 | — |
| 图生图 | 只 `input_references` + `strength`（denoise） | 已接；勿混 image/image_url | — |
| seed / negative / steps / guidance | 文档 | 已接 | — |
| 预估 | 目录 `pricing.per_image` | whatif 已读 per_image | — |
| 取消 | 视频 status 有 canceled 映射；未见通用 cancel | 无 `cancel_job` | P2 |

## 跨家 UI

| 项 | 现状 | 优先级 |
|---|---|---|
| 切供应商丢掉 AIR/sampler，只映射各家字段 | slimPayload 已做大半 | — |
| 取消按钮对 HF/魔搭/Nano 无效文案 | 统一按钮 | P2 按 backend 隐藏 |
| generate.warning 不展示 | 魔搭 LoRA 跳过用户看不见 | **P1** |

