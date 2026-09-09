# Provider / 模型 / 路由 官方参数矩阵

调查截止 **2026-09-09**。工作树 `feat/cloud-nodes-poc`（stamp `v0821o6b-ms-lora-shape`）。

本文是 F1 官方契约。**仓库 TODO / 能力表 / 适配器代码都不是官方依据。** 三列必须分开：

| 列 | 含义 |
|---|---|
| **官方** | 该路由当日能打开的 schema / recipe / API 页写了的字段 |
| **适配器** | `providers/*.py` 现在会不会映射、会不会改值 |
| **未知** | 官方页没写。**没查到 ≠ 不支持**，也 ≠ 可以发明字段发出去 |

`docs/api-param-gaps.md` 是旧漏接清单，若干行已被代码改过，以本文「适配器」列为准。

覆盖范围：六家已接入 backend。Fal 约 1492 端点、Civitai catalog 约 310 行，**不能用一张样例表冒充全量**。全量分母由 F2 盘；本文给官方字段契约和代表模型。图 `134923572` 是跨家挑选验收样本，不是目录完成证明。

---

## 读法

- **support**：官方页列出该字段。
- **unknown**：官方页未列；禁止写成「API 不支持」。
- **unsupported（有据）**：官方明确拒绝（例：Civitai Krea v2「does not accept LoRAs」；HF router `replicate` 禁止 POST）。
- 允许有据改名（`steps`→`num_inference_steps`）。禁止静默换模型、换 LoRA、截 prompt、取模 seed 当「原样」、近似尺寸当原尺寸。
- 发出字段 ≠ 上游加载。LoRA 看 sidecar `submittedInput`，成片不能当生效证据。
- 实测生成只能前端点击。本文只读官方页 + 适配器源码，**不冒充实测**。

### 通道拆分（禁止项钉的是通道，不是整家）

| 通道 | 官方 `loras` | 禁止发明？ |
|---|---|---|
| HF Fal 路由 `POST router.huggingface.co/{provider}/{providerId}` | 跟 Fal schema，mapped turbo 可带 `loras[]`。发出去 ≠ 一定加载 | 否 |
| HF OpenAI 兼容体 nscale 等 `POST …/v1/images/generations` | **无** | **是。禁止的是这条兼容体，不是整家 HF** |
| HF `hf-inference` bytes | 统一 T2I 表无 `loras` | 不要发明 |
| 魔搭 Inference Hub `POST {ai\|cn}/v1/images/generations` | 要 Hub `owner/repo`；cloud 出站 `[{model,weight}]` | 否（不是发明字段） |

---

## 1. Civitai · orchestration recipes

出处：`https://developer.civitai.com/orchestration/recipes/*`，2026-09-09 GET。提交：`POST /v2/consumer/workflows`，step 多为 `imageGen` / `videoGen`。公开 `GET https://civitai.com/api/v1/images` 的 `meta` 是 `object|null`，`withMeta` 默认 false，**不能当完整导入**（GitHub issues #1037 / #1297 / #1329）。

### 1.1 共用 imageGen 字段（多数引擎）

| 字段 | 类型 | 范围 / 默认 | 官方 | 适配器 `providers/civitai.py` |
|---|---|---|---|---|
| `prompt` | string | 常 ≤10000 | support | 原样 |
| `negativePrompt` | string | 页上有 | support | 原样；个别 recipe（Flux1 comfy）可能省略 |
| `width` / `height` | int | 常 64–2048，/16 或 /8 | support | `_set_int` **钳** 16–2048，越界被改值不是原样 |
| `cfgScale` | number | 随模型 | support | 原样 float |
| `steps` | int | 随模型 | support | 钳 1–150 |
| `seed` | int64 | 页上 int64 | support | `int(seed)`，**不取模** |
| `quantity` | int | 1–12 | support | 钳 1–12 |
| `loras` | 见下 | 强度常 0–2 | 多数 support；Krea v2 **明确不收** | `lora_map` → `{air: strength}`；无 air 丢；hunyuan dict→`[{air,strength}]` |
| `sampler` / `scheduler` | string | **仅 comfy 族** | 按 recipe | 有则写入。sdcpp 官方名是 `sampleMethod` / `schedule`，不是这俩键 |
| `denoise` | number | variant | 部分 | 有则写入 |
| `aspectRatio` | enum | 见 krea | 部分 | payload 有则写；allowed 集合默认不含，除非 catalog `required/optional` 放行 |
| `engine` / `operation` / `ecosystem` / `model` / `version` | string | recipe 钉死 | support | 从 catalog / payload |

### 1.2 代表模型（官方 recipe，不是 catalog 抄一份）

| 模型 / engine | 任务 | 官方要点 | LoRA | 适配器风险 |
|---|---|---|---|---|
| **Krea v2** `engine=fal` `model=krea2` `createImage` | t2i | `prompt` 1–5000；`size` medium\|large 默认 medium；`aspectRatio` 1:1, 4:3, 3:2, 16:9, 2.35:1, 4:5, 2:3, 9:16 默认 1:1；`creativity` raw\|low\|medium\|high 默认 medium（**raw 是 creativity，不是 turbo 变体**）；`quantity` 1–10 默认 1；`seed` uint32；`imageStyleReferences[]` 最多 10，`strength` −2.0–2.0 默认 1.0 | **官方：does not accept LoRAs** | 适配器仍可能 `lora_map` 塞 `loras`；UI 若显示 LoRA = 空壳。默认 catalog 是 `image/comfy/krea2/turbo/createImage`，和这条 fal/krea2 recipe **不是同一条** |
| **Z-Image** `sdcpp/zImage` | t2i only | turbo：cfgScale 1、steps 9；base：cfgScale 4、steps 20；`sampleMethod` euler；`schedule` simple；**只有 createImage，无 i2i** | `{urn: strength}` | 适配器发 `sampler`/`scheduler` 对不上 sdcpp 键名。导入图当 i2i 会编不存在的操作 |
| **ERNIE** comfy | t2i | sampler euler；scheduler simple | 只 `urn:air:ernie:lora:…` | 别家 AIR 不能硬编 ernie URN |
| **Flux1** sdcpp vs comfy | t2i | sdcpp：`sampleMethod`/`schedule`；comfy：`sampler`/`scheduler`；comfy 可能无 `negativePrompt` | 有 | 一套 UI 名不能两族共用 |
| **Flux2 Klein** | t2i | `loras` dict | `{air: strength}` | — |
| **Flux2 Dev** | t2i | `loras[]` `{air,strength}`；`guidanceScale` / `numInferenceSteps`（不是 cfgScale/steps） | array | 适配器默认键是 cfgScale/steps，catalog 不放行就丢 |
| **Qwen** sdcpp | t2i / variant | version latest/2509/2512/2511；宽高 /8；createVariant 用 `strength` | 有 | — |
| **hunyuan** | t2i | — | 适配器把 dict 展成 `[{air,strength}]` | 官方页本轮未单独展开，array 形状以 catalog 为准 |

### 1.3 取消 / 预估 / 导入

| 能力 | 官方 | 适配器 |
|---|---|---|
| 取消 | `DELETE /v2/consumer/workflows/{id}` | 已接 |
| 预估 | `whatif=true` | 已接 |
| 公开图导入 | `GET /api/v1/images` `meta` 常 null | 禁止用公开 API 冒充完整导入 |

**告知 A1（Claude）**：sampler 键按 engine 分；Krea v2 官方无 LoRA；width/height/steps/quantity **钳值**违反「越界报错不改值」；Flux2 Dev 官方键名不同。

---

## 2. Fal · 按 endpoint OpenAPI，不是 provider 总能力

出处：`https://fal.ai/models/{id}/api` + `https://fal.run/{id}/openapi.json`。定价：`GET https://api.fal.ai/v1/models/pricing?endpoint_id=`。取消：submit 返回的 `cancel_url`，`PUT …/requests/{id}/cancel`。训练端点产出 safetensors，**不是图**。

### 2.1 通用 LoRA 端点 `fal-ai/flux-lora`（2026-09-09）

| 字段 | 类型 | 默认 / 范围 | 官方 |
|---|---|---|---|
| `prompt` | string * | — | support |
| `loras` | `list<LoraWeight>` | 「any number，merged」；**页上无 max 条数** | support |
| `LoraWeight.path` | string * | URL 或 LoRA 权重路径 | support |
| `LoraWeight.scale` | float | 默认 1；**页上无 min/max** | support |
| `image_size` | enum 或 `{width,height}` | 默认 `landscape_4_3`；enum：square_hd / square / portrait_4_3 / portrait_16_9 / landscape_4_3 / landscape_16_9 | support |
| `num_inference_steps` | int | 默认 28；范围页上未写 | support |
| `guidance_scale` | float | 默认 3.5；范围页上未写 | support |
| `seed` | int | 无默认 | support |
| `num_images` | int | 默认 1 | support |
| `negative_prompt` | — | **本页 schema 无** | unknown（别家 generic lora 页有；本页不要当一定有） |

适配器：`apply_fal_loras` 按 OpenAPI shape 写 `loras` / `lora_url` / `lora_path` / `lora`。scale **钳 [0,4]**（官方 flux-lora 页无此范围）。AIR/`urn:` 不当 path；缺 URL 时 versionId→Civitai 下载链。无 LoRA 字段则 `fal_lora_sibling` 改打 `{id}/lora`（改 `serviceId`，不是换 LoRA 文件）。找不到 sibling **不硬塞**（避免 422）。

### 2.2 `fal-ai/z-image/turbo/lora`（2026-09-09）

| 字段 | 官方 |
|---|---|
| `loras` | `list<LoRAInput>` **max 3**。该页 snippet **未展开** path/scale；形状沿用通用 `LoraWeight`，标 **部分未知** |
| `image_size` | 默认 `landscape_4_3` |
| `num_inference_steps` | 默认 8 |
| `enable_safety_checker` | 默认 true |
| 基座 `fal-ai/z-image/turbo` | 无 `loras`；有 LoRA 时应走 sibling，这是官方拆端点 |

### 2.3 视频字段（OpenAPI overlay，`docs/fal-field-gaps.md` 2026-08-31 GET）

按 **端点** 列 `imageFields` / `durationField` / `aspectRatioField`。例：

| 端点 | 图字段 | duration | 比例字段 |
|---|---|---|---|
| kling o3 ref-to-video | start/end + `image_urls` | duration | **`aspect_ratio`** |
| runway-gen3 turbo i2v | `image_url`, `end_image_url`(deprecated) | duration | **`ratio`**（不是 aspect_ratio） |
| veo3.1 first-last | `first_frame_url`, `last_frame_url` | duration | `aspect_ratio` |
| `fal-ai/imagen4/preview*` | OpenAPI **404** | — | **不编字段**（deprecated） |

适配器 `build_fal_input`：`aspectRatioField` 来自 catalog；否则 schema 有 `ratio`/`aspect_ratio` 才写。**只在 `payload.aspectRatio` 有值时发出**。`qty`/`quantity` → `num_images`（1–12）**当 schema 列出该字段**。`docs/api-param-gaps.md` 仍写「不映射 num_images」「index.html 无 aspectRatio」——对 **cloud `fal.py` 已过时**；UI 是否有控件是 C1 的事。

### 2.4 训练端点（禁止当生成）

| id | 官方产出 | 适配器 |
|---|---|---|
| `fal-ai/krea-2-trainer` | 训练 / safetensors | 禁止 generate |
| `z-image-trainer` 同类 | 同上 | 禁止 generate |

**告知 A2（Claude）**：scale 钳 [0,4] 不是 flux-lora 官方范围；turbo/lora 的 LoRAInput 页上未完整定义；`krea/v2/large/text-to-image` sibling=`(none)`，挂 LoRA 不得硬塞；Imagen4 404 不编。

---

## 3. Hugging Face · 一家多路由

生成入口：`POST https://router.huggingface.co/{provider}/{providerId}`。适配器 `_PREF = ("fal-ai", "nscale", "together", "hf-inference")`，`replicate` 跳过。`_style_for`：`hf-inference`=bytes；`fal-ai`/`wavespeed`=fal；其余=openai。

**能力表 `huggingface.lora=path` 是 provider 级，会把 nscale / hf-inference 的「无 loras」盖掉。catalog 只能收紧，不能按路由拆。这是 D1 缺口，不是官方。**

### 3.1 Fal 映射（例 Z-Image-Turbo → `fal-ai` + `fal-ai/z-image/turbo`）

| 字段 | 类型 | 官方 | 适配器 |
|---|---|---|---|
| `prompt` | string | Fal schema | 原样 |
| `negative_prompt` | string | Fal 部分端点 | 有则发 |
| `num_inference_steps` | int | Fal | `steps`→此键 |
| `guidance_scale` | float | Fal | `cfgScale`→此键 |
| `image_size` | `{width,height}` | Fal | 有宽高则发 |
| `seed` | int | Fal 无 int32 上限（页上未写） | **钳/取模 int32** `[-1, 2147483647]` |
| `scheduler` | string | Fal 部分 | 有则发 |
| `loras` | `[{path,scale}]` | **Fal `/lora` sibling 官方有**；HF router `…/turbo/lora` 实测 404「Model not supported」 | `_maybe_lora_pid` **不改** mapped id；`_force_loras` 硬塞最多 3 条。`loraConfidence=unverified` |

发出去 ≠ Fal 在非 `/lora` 端点加载权重。

### 3.2 OpenAI 兼容体（nscale / together 等）`POST {ROUTER}/{provider}/v1/images/generations`

对照：OpenAI Images create（platform.openai.com/docs/api-reference/images；本轮直连 403，用公开文档摘要，**不当 2026 现场 schema**）+ nscale 供应商页 Text-to-Image snippet。

| 字段 | 官方 Images create / nscale T2I | 适配器 `_call_openai` |
|---|---|---|
| `model` | support | providerId |
| `prompt` | support * | 原样 |
| `n` | support | 写死 **1**（payload quantity 丢掉） |
| `size` | 枚举或 `WxH` 字符串 | 有宽高则 `{w}x{h}` |
| `response_format` | url / b64_json | 写死 `b64_json` |
| `quality` / `style` | OpenAI 有；nscale 页 **未列** | **不发** |
| `loras` / `scheduler` / `steps` / `guidance` / `negative` / `seed` | **官方无** | **不发。禁止发明** |

nscale 页有 Chat Completions，那是另一条 API，不要把 chat 字段塞进 images。

### 3.3 `hf-inference` bytes

出处：HF 统一 text-to-image（huggingface.co 推理文档，2026-09-09）：

| 字段 | 官方 | 适配器 |
|---|---|---|
| `inputs` | * | prompt |
| `parameters.guidance_scale` | support | 有则发 |
| `parameters.negative_prompt` | support | 有则发 |
| `parameters.num_inference_steps` | support | 有则发 |
| `parameters.width` / `height` | support | 有则发 |
| `parameters.scheduler` | support | 有则发 |
| `parameters.seed` | support | int32 取模 |
| `loras` | **该表无** | 不发 |

### 3.4 取消 / 预估 / replicate

| | 官方 | 适配器 |
|---|---|---|
| 取消 | 同步，无 Fal `cancel_url` | 基类「没有取消接口」。**不是「查不到」**，是这套 router 调用没有队列 cancel |
| 预估 | 无统一 pricing API | stub |
| replicate | 明确 Not allowed to POST | 跳过 |

**告知 B1（sol）**：按真实路由拆能力，禁止 provider 级 `lora=path` 扩到 nscale；失败不得漂到不兼容路由；`_force_loras` 保持 unverified；seed 取模不是原样。

---

## 4. 魔搭 AI / 魔搭 CN · 两家，禁止互切

| | AI | CN |
|---|---|---|
| id | `modelscope-ai` | `modelscope-cn` |
| token | `~/.config/modelscope/token` | `~/.config/modelscope-cn/token` |
| 生成 | `https://api-inference.modelscope.ai/v1` | `https://api-inference.modelscope.cn/v1` |

旧 `api.modelscope.ai` NXDOMAIN。Hub 列模型：`https://www.modelscope.cn/openapi/v1/models`，task slug **`text-to-image-synthesis`**（`text-to-image` 是 0 条）。

### 4.1 Inference `POST /v1/images/generations`

头：`X-ModelScope-Async-Mode: true`。轮询：`GET /v1/tasks/{id}` + `X-ModelScope-Task-Type: image_generation`。

Hub 模型页 Example Codes（多页，2026-09-09，如 SuperHurio/xuan、zzjj66/mling12）**只示范** `model` + `prompt`。AIGC 还吃更多键——下面「support」来自适配器注释的 AIGC 字段集 + 2026-09-08 出站实测，**不是每张 Hub 模型页都列出**。没出现在某张模型页 ≠ 该字段不存在。

| 字段 | 类型 | 官方页 / 实测 | cloud 适配器 | v0794 适配器（勿抄 o6b） |
|---|---|---|---|---|
| `model` | Hub `owner/repo` * | Hub 示例 | `serviceId`；与 payload.model 不一致 **400 拒 remap** | 同左 |
| `prompt` | string * | Hub 示例 | 原样 | 原样 |
| `negative_prompt` | string | AIGC 字段集 | 有则发 | 有则发 |
| `size` | `WxH` 字符串 | AIGC | 宽高拼 `WxH` | 同 |
| `seed` | int | AIGC；适配器当 int32 | **取模** `[-1, 2147483647]` | 同 |
| `steps` | int | AIGC | 有则发 | 同 |
| `guidance` | float | AIGC（不是 guidance_scale） | `cfgScale`→`guidance` | 同 |
| `image_url` | string 或 list | 编辑 / i2v | 编辑或多参考 | 同 |
| `loras` | 见下 | Hub 示例常 **不写**；AIGC 字段存在。形状以 **2026-09-08 实测** 为准 | `[{model: owner/repo, weight}]` 单条也数组。http/AIR 丢弃 | **字符串 `owner/repo` 或 `{repo: weight}`**（官方实测这俩 500；v0794 文档保持现状，不把 o6b 形状写进去） |
| 取消 | 本 inference host **无** Fal 式 `cancel_url`。DashScope 取消是另一产品 | 基类无取消 | 同 |
| 预估 | 未见 | stub | 同 |

**会 500 的形状**（cloud 已弃，v0794 仍可能发）：

```json
{ "loras": "owner/repo" }
{ "loras": { "owner/repo": 0.8 } }
```

**cloud 能过的形状**：

```json
{ "loras": [{ "model": "owner/repo", "weight": 0.8 }] }
```

Civitai `https://…`：**跳过** + `warning`（UI 不显示）。不要做 Civitai→Hub 自动对照表。

**告知 B2（sol）**：AI/CN 分 token/host；seed 取模不是原样；http LoRA 跳过后仍出底模是假信心；cloud 必须数组对象。v0794 仍发字符串/`{repo:w}`，与 2026-09-08 实测相反，但 **F1 不改 v0794 产品代码**。

---

## 5. NanoGPT · 两条图 API + 目录 token

文档：`https://docs.nano-gpt.com/introduction`。目录：`GET /api/v1/images/models`、`GET /api/v1/video-models`。出图优先 `POST /api/v1/images`，失败再 `POST /v1/images/generations`。prompt 超长官方 400 `prompt_too_long`（实测 1408>1200）→ **`NANO_PROMPT_MAX=1200`**。

### 5.1 专用 Image API `POST /api/v1/images`

目录 `supported_parameters` 为真值。该页常见字段（2026-09-09）：

| 字段 | 官方专用页 | 适配器 |
|---|---|---|
| `model` `prompt` `n` | support | 有 |
| `resolution` | **必须是该模型 `resolutions` token**（`1k`/`2k`/`1024*1536`/`square_hd`…） | `pick_resolution`：空列表 → **None（caller 400）**。**不再发明 `{w}x{h}`**。有列表时按 WxH **最近点**，不是原样自由宽高 |
| `aspect_ratio` | support | 由 WxH 推最近比 |
| `quality` `output_format` | 页上有 | 看 `_image_body` 是否映射（未在本表当已接，除非代码发了） |
| `seed` | support | int32 取模；超限写回 + dock「原 M → N」 |
| `input_references` | i2i | 只发这个 + `strength`（denoise）。禁止混 `image`/`image_url`/`imageDataUrl` |
| `loras` / `negative_prompt` | **专用页未列** | 适配器在 `*-lora` 模型仍发 `loras[{path,scale}]` + `lora_N_url`/`lora_N_scale`。**adapter/measured，不是该页官方**。未知 ≠ 禁止发，也 ≠ 已文档化 |
| `width`/`height` | 无（用 resolution token） | 出站 / persist **删除** |

`docs/api-param-gaps.md` 写 `pick_resolution` 空列表发明 `{w}x{h}`：**对当前 cloud `nanogpt.py` 过时**。

### 5.2 OpenAI 兼容 `POST /v1/images/generations`（Nano 文档，2026-09-09）

| 字段 | 官方 | 适配器 |
|---|---|---|
| `prompt` * `model`（默认 hidream）`n` | support | 有 |
| `size` | 来自目录 resolutions | token，不是自由 WxH |
| `response_format` | support | 有 |
| `imageDataUrl(s)` `maskDataUrl` | support | 图路径应走 `input_references`，勿混 |
| `strength` | 0–1 默认 0.8 | denoise 映射 |
| `guidance_scale` | 0–20 默认 7.5 | 有则发 |
| `num_inference_steps` | 1–100 默认 30 | 有则发 |
| `seed` | support | int32 取模 |
| `kontext_max_mode` | support | 未知是否映射 |
| `loras` | **本页无** | 同 5.1：仅 `*-lora` 实测 |

### 5.3 视频

许多字段按模型。部分视频模型文档有 `negative_prompt`。`duration` 官方常是字符串秒。不要把图片 resolution token 套到所有视频模型。

**告知 D3（default）**：resolution 必须是目录 token，最近点 ≠ 原样 WxH，UI 必须露出实际 token；专用页未列 `loras` 时不要把能力表 `lora=path` 写成「官方专用 Image API 支持」；>3 条 / 无直链 / 过期 B2 缺 versionId 应拒。

---

## 6. 跨家对照（同一用户参数怎么走）

用户要求：API 支持则 **原样输入并实际发送**；不支持则逐字段展示原值、官方限制和证据，不能标通过，也不能扩成整家不支持。

以样例图常见键为例（真值以 G2 从原页读取为准，本表只定契约）：

| 用户键 | Civitai | Fal | HF Fal 路由 | HF nscale | 魔搭 | Nano |
|---|---|---|---|---|---|---|
| prompt | 原样（注意 krea 5000 vs 共用 10000 vs Nano 1200） | 原样 | 原样 | 原样 | 原样 | 超 1200 应阻断 |
| negative | 多数有；Flux1 comfy 可能无 | 端点有才发 | 同 Fal | **官方无** | AIGC 有 | 专用页未列；兼容体未列；适配器仍可能发 |
| width/height | 钳 16–2048 | `image_size` 对象或 enum | 同 Fal | `size`=`WxH` | `size`=`WxH` | **改成 catalog token**（不是原像素） |
| steps | 钳 1–150；Flux2 Dev 官方是 `numInferenceSteps` | `num_inference_steps` | 同 | **无** | `steps` | 兼容体有；专用页看目录 |
| cfg | `cfgScale`；Flux2 Dev 是 `guidanceScale` | `guidance_scale` | 同 | **无** | `guidance` | `guidance_scale` |
| seed | int64 原样 | 原样 int | **取模 int32** | **无** | **取模 int32** | **取模 int32** |
| sampler/scheduler | comfy 有；sdcpp 换名；krea2 无 | 部分端点 `scheduler` | fal 通道有 | **无** | **无** | **无** |
| LoRA | AIR dict 或 array；**krea2 官方拒绝** | `{path,scale}` 或 sibling | 硬塞 unverified | **禁止发明** | Hub `[{model,weight}]`（cloud） | `*-lora` 实测 path；专用页未知 |
| quantity | 1–12 | schema 有则 `num_images` 1–12 | openai 通道写死 n=1 | n=1 | 未见 | `n` |
| i2i | 按 recipe；z-image **无** | 按 `imageFields` | blob 含 i2i 才试 | 无 | `image_url` | 只 `input_references`+`strength` |

---

## 7. 过时文档（对照矩阵，不改那些文件的锁）

| 文件 | 过时断言 | 现况 |
|---|---|---|
| `docs/api-param-gaps.md` Fal `num_images` P1 不映射 | cloud `build_fal_input` **已映射** 1–12（schema 有该字段时） |
| 同文件 Fal aspect_ratio P0「index.html 无 aspectRatio」 | 适配器已按 catalog 字段发；**UI 控件仍可能缺**（C1） |
| 同文件 Nano 空列表发明 `{w}x{h}` | `pick_resolution` 空 → None / 400 |
| `docs/provider-lora.md` 总表曾写魔搭 `{repo:w}` | cloud 实测数组对象；总表已改。v0794 适配器仍可能发旧形状 |
| provider 级 `huggingface.lora=path` | 只描述 Fal 通道；nscale / bytes 官方无 loras |

三份已改文档（`TODO.md` / `provider-lora.md` / `lora-wiring-deep.md`）通道拆分有效，继续保留。

---

## 8. 适配器负责人（字段/范围不一致，F1 不改产品代码）

| 锁 | 谁 | 官方 vs 现状 |
|---|---|---|
| A1 `providers/civitai.py` | Claude | sdcpp `sampleMethod`/`schedule` vs UI `sampler`/`scheduler`；Krea v2 官方无 LoRA；宽高/步数/数量钳值；Flux2 Dev `guidanceScale`/`numInferenceSteps`；allowed 默认集可能丢掉 recipe 键 |
| A2 `providers/fal.py` | Claude | 按端点 schema 发，禁止 trainer 当生成；scale 钳 [0,4] 非 flux-lora 官方范围；`aspectRatio` 依赖 payload 有值；Imagen4 404 不编 |
| B1 `providers/huggingface.py` | gpt-5.6-sol | 三路由分能力；nscale 禁止发明 loras；`_force_loras` unverified；n=1；seed 取模；replicate 继续跳过 |
| B2 `providers/modelscope.py` | gpt-5.6-sol | AI/CN 不互切；cloud 必须 `[{model,weight}]`；http LoRA 跳过要让 UI 看见；seed 取模不是原样 |
| C1/C2 画布 | 代码 | 模型/路由切换后，**官方 support 的字段要有真实输入口**；nscale 不显示 LoRA；魔搭显示 Hub owner/repo；Nano 显示实际 resolution token；warning 要看见 |
| D1 能力/编译 | default | 能力收到 **路由/模型级**；HF 不能一家 `lora=path`；catalog 不得抬高 |
| D3 `nanogpt.py` | default | 空 resolutions 400；专用页未列 loras 保持 measured/unknown；自由 WxH 禁止 persist |

审查（deepseek）只看代码。验收（glm）只点 UI，不读源码。本文不是通过证明。
