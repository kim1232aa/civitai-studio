# 各供应商 LoRA / 自定义参数 / 代表问题

接线深挖（代码路径级）：[`lora-wiring-deep.md`](lora-wiring-deep.md)。

调查截止 **v0753**（`0fac0ea`，2026-09-02）。只记官方字段和实测，不把「找替代 LoRA」写成产品对照表。

夹具：Civitai 图 `139791102`（Z-Image Turbo），LoRA version `3231694`（Asian Mix），下载链 `https://civitai.com/api/download/models/3231694`。

判断生效看 sidecar `submittedInput`，不要只看成片栏有新图。页面成功路径只显示「好了」，**不读** `generate.warning`。

## 总表

| 供应商 | LoRA 官方形态 | Civitai 下载链 | 自定义参数（会发出去的） | 代表问题 |
| --- | --- | --- | --- | --- |
| Civitai | AIR / versionId，进工作流 resources | 官方下载 | sampler、scheduler、denoise、turbo/raw、seed、步数、CFG、宽高 | 社区节点 Comfy 不能当本地跑；AIR 对不上就 unmatched，不编 URN |
| Fal | `loras: [{path, scale}]`（部分端点是 `lora_url` / `lora_path`） | 可用。无 LoRA 字段时切到目录里的 `/lora` 兄弟端点 | prompt、negative_prompt、seed、steps→`num_inference_steps`、CFG→`guidance_scale`、宽高→`image_size`、scheduler、首帧/尾帧按 OpenAPI | 多填字段会 422；非 LoRA 端点不要硬塞 `loras` |
| Hugging Face | 路由映射到 `fal-ai/…` 后，把 `loras[]` 附在 **mapped turbo** 上 | 会塞进 body。路由 **没有** `…/turbo/lora` | seed 钳到 `[-1, 2147483647]`、宽高、`scheduler`（仅 fal 风格通道） | 发出去 ≠ 上游一定用。OpenAI 通道忽略 LoRA/scheduler。replicate 不能 POST |
| 魔搭 AI / CN | `loras` = Hub `owner/repo` 或 `{repo: weight}` | **不能用**。发了会 500「lora modelName 不能为空」 | model、prompt、negative_prompt、`size`=`WxH`、seed 钳 int32、steps、guidance、编辑模 `image_url` | 跳过 http LoRA 后仍出底模；warning 只在 API，UI 不显示。AI/CN 禁止互切 |
| NanoGPT | `loras: [{path, scale}]`，另带 `lora_1_url` / `lora_1_scale` | 可用（`z-image-turbo-lora`、`wavespeed-ai/krea-v2/turbo-lora` 实测出片） | 目录里的 resolution token、`aspect_ratio`、seed、negative、`input_references` + `strength`（来自 denoise）、steps、guidance | 图生图不能混 `image`/`image_url`/`imageDataUrl`。分辨率必须是目录 token，不能自己拼 `256*256` |

## Civitai

- 搜 LoRA：`GET /api/search?type=LORA`，版本：`GET /api/model-version/<id>`。
- 发出去的是 AIR + versionId，不是 Hub repo。
- 自定义：sampler / scheduler / denoise / turbo|raw 只在这家有意义。
- 工作流：zip > Comfy JSON > PNG tEXt；对不上的节点列 unmatched，不发明 `urn:air:…nodepacklayer`。

## Fal

官方（OpenAPI / `fal-ai/z-image/turbo/lora` 一类）：

```json
{ "prompt": "…", "loras": [{ "path": "https://civitai.com/api/download/models/3231694", "scale": 0.8 }] }
```

`path` 也可以是 HF `owner/repo`。scale 钳在 `[0, 4]`。

适配器行为（`providers/fal.py`）：

1. 当前 id 已支持 LoRA → 原端点。
2. 否则若本地目录有 `{id}/lora` → 改打兄弟端点（例：`fal-ai/z-image/turbo` → `fal-ai/z-image/turbo/lora`）。
3. 再否则前缀 / 连字符模糊匹配带 `lora` 的目录行。
4. AIR / `urn:` 不当 path；缺 URL 时用 versionId 拼 Civitai 下载链。

视频自定义字段按端点走 `image_url` / `end_image_url` / `image_urls` 等，见 `docs/fal-field-gaps.md`。Imagen4 preview 系列 OpenAPI 404，不要编字段。

代表问题：

- 非文档字段 422，队列日志里是 Unprocessable。
- `fal_lora_sibling` 会改 `serviceId`（用户点的是 turbo，提交可能是 turbo/lora）。这是切端点，不是换 LoRA 文件。
- 目录搜索不要把本地 ~1492 条滤成 1 条。

## Hugging Face

生成走 `https://router.huggingface.co/{provider}/{providerId}`。Z-Image-Turbo 常见映射：`fal-ai` + `fal-ai/z-image/turbo`。

实测：

- `POST …/fal-ai/fal-ai/z-image/turbo/lora` → 路由「Model not supported」。
- 同一请求打 mapped turbo，body 里带 `loras[]` → HTTP 200 能落盘。
- sidecar 能证明字段发出去了；**不能**证明 Fal 在非 `/lora` 端点一定加载了权重。

其它通道：

- `hf-inference`：bytes，不带 LoRA。
- OpenAI 兼容（nscale 等）：`/v1/images/generations`，忽略 LoRA / scheduler。
- `replicate`：明确禁止 POST，代码跳过。

自定义：seed 超 int32 会取模，不丢。宽高打成 `image_size: {width,height}`。

代表问题：假信心。表单还挂着 Civitai LoRA，成片也有，不代表风格一定吃到。

## 魔搭 AI / 魔搭 CN

两家，token 和 base 不共用。

| | AI | CN |
| --- | --- | --- |
| id | `modelscope-ai` | `modelscope-cn` |
| token | `~/.config/modelscope/token` | `~/.config/modelscope-cn/token` |
| 生成 | `https://api-inference.modelscope.ai/v1` | `https://api-inference.modelscope.cn/v1` |

旧域名 `api.modelscope.ai` 已 NXDOMAIN。连不上就报错，禁止改走另一家。

官方 AIGC 字段：`model` `prompt` `negative_prompt` `size` `seed` `steps` `guidance` `image_url` `loras`。

`loras` 只要 Hub `owner/repo`：

```json
{ "model": "Tongyi-MAI/Z-Image-Turbo", "prompt": "…", "loras": "Qwen/some-lora" }
```

或多条 `{ "owner/repo": 0.8, "other/repo": 0.2 }`（权重会归一）。

Civitai `https://…` 路径：**跳过**，不提交，响应带

`warning: 魔搭 LoRA 只要 Hub 的 owner/repo，Civitai 下载链不能用`

搜索框文案已经写了 owner/repo。从 Civitai 图导入后再切魔搭，LoRA 仍挂在表单上，生成时被丢掉。UI 不展示 warning。

v0752 曾把 `3231694` 静默换成 `laonansheng/Asian-beauty-Z-Image-Turbo-Tongyi-MAI-v1.0`。v0753 已撤。不要再加产品对照表。

目录列 Hub `openapi/v1/models`，task slug 是 `text-to-image-synthesis`（`text-to-image` 是 0 条）。老诊断 `docs/hf-modelscope-listing.md` 写的是改 Hub 之前的白名单实现，以当前 `providers/modelscope.py` 为准。

## NanoGPT

文档：<https://docs.nano-gpt.com/introduction>。目录：`GET /api/v1/images/models`、`GET /api/v1/video-models`。出图优先 `POST /api/v1/images`，失败再试 `/v1/images/generations`。

官方会吃的：

- `model` `prompt` `n` / `nImages`
- `resolution` / `size`（必须是该模型 `supported_parameters.resolutions` 里的 token：`1k`/`2k` 或 `1024*1536` 这种）
- `aspect_ratio`（`2:3` 等）
- `seed`（钳 int32：`n % 2147483647`；超大导入 seed 会立刻写回输入框并 dock 提示「原 M → N」）
- `negative_prompt`
- 图生图：只发 `input_references` + `strength`（denoise 映射过来，默认 0.65）
- LoRA：`loras: [{path, scale}]`（生成当下把 Civitai 链现解成新鲜 B2 直链；钥匙不出门；sidecar 只落稳定 versionId/download API，不落签名 URL）

**出站 / 落盘禁止 `width`/`height`（v0776）：** FE 可用导入宽高只挑最近目录 token；`_image_body` / `_core_image_body` / `sanitize_submitted_for_persist` 都不把自由 WxH 写进 Nano POST 或 `submittedInput`。UI 文案「导入尺寸仅参考，不进 POST」必须与 JSON 一致。

提示词上限 **1200** 字符（FE 预检 + 可截断；server 再拦）。

实测能带 Civitai 链的模型：`z-image-turbo-lora`、`wavespeed-ai/krea-v2/turbo-lora`。普通 `z-image-turbo` 不保证吃 LoRA。过关生图优先选目录里带 `*-lora` 的端点。

代表问题：

- 分辨率若按「第一个 token」会落到 `256*256`（已修接线）。
- 宽高收成目录 resolution token / aspect_ratio。**UI 必须让人看见实际提交的 token**（v0775：Nano 藏自由宽高行，只显 resolution 下拉）。
- 图生图同时塞 `image` / `imageUrl` / `imageDataUrl` / `input_references` 会被拒。
- denoise 曾在 slim 时被删，strength 出不去。
- 改 `providers/nanogpt.py` 后必须 `python3 scripts/restart.py && ./run.sh`；只硬刷 HTML 不够（旧进程会导致 JSON 仍带 WxH，如作废 out `nano-gpt_img_a1811e357469`）。

## 不要做的

- 不要把 Civitai LoRA 自动映射成另一家的 Hub 仓库。
- 不要用「成片栏有图」证明 LoRA 生效。
- 不要把魔搭 AI 失败切到 CN。
- 不要把 HF 路由上的 `loras[]` 写成「官方 /lora 端点」。
