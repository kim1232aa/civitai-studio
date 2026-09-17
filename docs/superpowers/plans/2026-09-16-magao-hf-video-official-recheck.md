# Magao / HF 视频 API 官方复核（2026-09-16）

> HEAD: `db4c44be33b0d639a5a54b3febb9894aa4724582`（或当时 origin/main）  
> 目的：Boss 规则 — HANDOFF「魔搭/HF 无视频 API」**不得**当官方真理；重查官方文档后写清是否可接 t2v/i2v。  
> **不**宣称闭环 Pass；**不** push；本文件为事实复核，无业务代码改动。

---

## 1. 结论摘要（先读）

| 家 | 官方是否有 t2v / i2v 推理 API | 本仓库当前行为 | vs 六家都要 t2i/i2i/i2v |
| --- | --- | --- | --- |
| **Hugging Face** Inference Providers / Router | **有** `text_to_video` + `image_to_video`（官方任务表 + InferenceClient） | caps `i2v=image_url`（编译层**不**因 i2v==none 硬拒）；适配器已识别 t2v/i2v pipeline，但**未见**独立「官方无视频」硬拒；出片链路未在本复核中实测 | **缺口在接线/出片验证**，不是「官方没有」 |
| **魔搭 AI / CN** API-Inference | **官方文档覆盖范围仍是 LLM + 多模态理解 + 文生图**；生成范例仅 `POST …/v1/images/generations`。Hub 有视频**模型** task slug，≠ 托管视频生成 API | caps `i2v=none`；`graph_compile` t2v/i2v 硬拒；`modelscope.generate` `_wants_video` 400 硬拒 | **官方可文档化的 i2v/t2v 仍缺**；勿把 Alibaba Model Studio / DashScope 万相 API 当成魔搭 API-Inference |

HANDOFF-20260914 §0 / §P3「魔搭/HF 官方无视频生成 API…双层诚实硬拒」对 **HF 已过期且与官方文档矛盾**；对 **魔搭** 与现有官方公开材料大体一致，但须把「路径探测 / 第三方探针」与「官方文档化可集成」分开写。

---

## 2. Hugging Face — 官方 endpoints / pipelines（含 URL）

### 2.1 任务与 SDK（官方）

| 项 | 出处 |
| --- | --- |
| Text-to-video 任务页（Inference Providers） | https://huggingface.co/docs/inference-providers/en/tasks/text-to-video |
| 同页 mirror | https://huggingface.co/docs/inference-providers/main/en/tasks/text-to-video |
| InferenceClient `text_to_video` / `image_to_video` | https://huggingface.co/docs/huggingface_hub/en/package_reference/inference_client |
| Providers × tasks 矩阵（含 t2v / i2v 列） | https://huggingface.co/docs/huggingface_hub/guides/inference |
| 首次调用总览 | https://huggingface.co/docs/inference-providers/guides/first-api-call |

**官方示例（t2v）**（任务页）：`InferenceClient(provider="fal-ai", api_key=HF_TOKEN).text_to_video(…, model="Wan-AI/Wan2.1-T2V-1.3B")` → 返回 video bytes。

**官方示例（i2v）**（InferenceClient 包文档）：`client.image_to_video("cat.jpg", model="Wan-AI/Wan2.2-I2V-A14B", prompt=…)` → `bytes`。

**矩阵（guides/inference，复核当日）**：

- `text_to_video()`：fal-ai ✅ · novita ✅ · replicate ✅ · wavespeed ✅（hf-inference ❌）
- `image_to_video()`：fal-ai ✅ · wavespeed ✅

> 注：`https://huggingface.co/docs/inference-providers/tasks/image-to-video` 与 `…/main/en/tasks/image-to-video` 本次 WebFetch **404**；i2v 以 **InferenceClient 包文档 + providers 矩阵** 为准，不编造独立 task 页内容。

### 2.2 集成要点（如何接，非本轮改码）

1. Hub mid → `inferenceProviderMapping` → Router：`POST https://router.huggingface.co/{provider}/{providerId}`（本仓库已有 fal 风格通道；视频任务官方对 fal-ai 使用 queue subdomain）。
2. 或直接 SDK：`huggingface_hub.InferenceClient.text_to_video` / `image_to_video`（与官方文档同形）。
3. Studio 钉选已含视频 mid（如 `tencent/HunyuanVideo`、`Lightricks/LTX-Video-…`）；catalog 搜索 pipeline ∈ `text-to-video` / `image-to-video`（见 `docs/api-usage/huggingface.md`）。

---

## 3. ModelScope（魔搭 AI + CN）— 官方材料

### 3.1 文档化生成面（官方 / 官方头条）

| 项 | 出处 | 内容 |
| --- | --- | --- |
| API-Inference 介绍（SPA；curl 无正文） | https://www.modelscope.cn/docs/model-service/API-Inference/intro | 仓库 `OFFICIAL-SOURCES.md` / `modelscope.md` 对照此页；本环境无法从 HTML 抽出正文 |
| 社区头条「免费模型推理 API…」（官方账号） | https://modelscope.cn/headlines/article/960 | **明文范围**：大语言模型、多模态理解、**文生图**；范例仅 `https://api-inference.modelscope.cn/v1/images/generations`；**无**文生视频/图生视频章节 |
| 仓库已钉官方对照 | `docs/api-usage/OFFICIAL-SOURCES.md` §ModelScope | 仅 `POST {ai\|cn}/v1/images/generations` |

AI vs CN：生成 base 分别为  
`https://api-inference.modelscope.ai/v1` 与 `https://api-inference.modelscope.cn/v1`（token **禁止交叉**）；Hub 搜目录共用 `https://www.modelscope.cn/openapi/v1/models`。

### 3.2 Hub 视频任务 ≠ API-Inference 视频生成

本仓库 `providers/modelscope.py` `HUB_TASKS` 含：

- `text-to-video-synthesis` → studio `text-to-video`
- `image-to-video` → studio `image-to-video`

代码注释已写明：Hub inclusion **does not prove** AI/CN inference availability。  
本地 ModelScope `pipeline('text-to-video-synthesis', …)` 是**本机推理**，不是 API-Inference 托管端点。

### 3.3 路径探测（非官方成功契约）

本机无 token `POST`：

- `https://api-inference.modelscope.cn/v1/videos/generations`
- `https://api-inference.modelscope.ai/v1/videos/generations`

均返回 **非 404**（HTTP 500 外壳 + JSON `errors.code=401` Authentication failed）。  
说明路由**可能存在**，但：

1. **官方文档 / 头条未给出**可复现的视频请求表、成功响应、轮询 `X-ModelScope-Task-Type`；
2. 第三方探针（lilting.ch, 2026-09-05，https://lilting.ch/en/articles/modelscope-api-inference-magicube-probe ）在带 token 时对 Wan 模型得到 `Invalid model provider` / DataInspection 错误，**未出片**；文中写 Magicube 范围含 text-to-image、**无 mention of video**。

→ **不得**据此宣称「魔搭已有可用视频 API」；也**不得**用 HANDOFF 一句话代替上述区分。

### 3.4 勿混淆：Alibaba Cloud Model Studio（万相）

Web 搜索常命中 DashScope / Model Studio 万相 `…/video-generation/video-synthesis`（如 help.aliyun.com / modelstudio 文档）。  
那是 **阿里云百炼 / Model Studio** 产品线，**不是** `api-inference.modelscope.{ai|cn}`。  
Boss「六家」里的魔搭指本仓库 `modelscope-ai` / `modelscope-cn` 适配器，**不能**把万相端点静默当成魔搭闭环。

---

## 4. 本仓库现有文档提及（api-usage）

| 文件 | 视频相关事实 |
| --- | --- |
| `docs/api-usage/modelscope.md` | Hub slug 含 `text-to-video-synthesis` / `image-to-video`；capabilities 行写 `i2v=image_url`（与 **代码 caps 不一致**，见下） |
| `docs/api-usage/huggingface.md` | 搜索 pipeline ∈ t2i/i2i/**t2v/i2v**；官方对照段偏 text_to_image，**未**写清已有 text_to_video / image_to_video |
| `docs/api-usage/REPORT.md` | 表行 HF `i2i/i2v` 写成 `none / none`（**过期** vs 当前 caps） |
| `docs/api-usage/models/hf-inventory.md` | 钉选含 HunyuanVideo / LTX；缺口写 `i2v=none`（**过期**） |
| `docs/api-usage/OFFICIAL-SOURCES.md` | 魔搭仅 images/generations；HF 仅链到 text-to-image 任务页 |
| `docs/HANDOFF-20260914.md` | 「魔搭/HF 官方无视频…硬拒」— **HF 部分与官方矛盾** |

---

## 5. 代码当前做什么（硬拒？）

### 5.1 capabilities（运行时实测本 HEAD）

```
huggingface     i2i=source  i2v=image_url  video=True
modelscope-ai   i2i=source  i2v=none       video=True
modelscope-cn   i2i=source  i2v=none       video=True
```

- 魔搭注释：`官方 API-Inference 无视频生成…目录仅展示, 生成/编译硬拒`（`providers/capabilities.py`）。
- HF：**不是** `i2v=none`。

### 5.2 编译层 `providers/graph_compile.py`

- `op == "i2v"`：若 `caps["i2v"] in (None, "none")` → 硬拒「不支持图生视频」。
- `op == "t2v"`：同一条件 → 硬拒「官方没有视频生成 API…」；注释仍写「魔搭/**HF**」，但 **HF 因 caps 已非 none，不会走此闸**。

### 5.3 魔搭发送层 `providers/modelscope.py`

- `_wants_video(payload, mid)`：kind/recipe/task/op/mid 含 video/i2v/t2v/…  
- `generate`：若 `_wants_video` → **400**「官方没有视频生成 API，拒绝拿 /images/generations 冒充…」  
- 实际出站仍只有 `POST {base}/images/generations`。

### 5.4 HF 发送层 `providers/huggingface.py`

- `_task` 可推断 `text-to-video` / `image-to-video`；`HF_PIPES` 含二者；fal 通道对视频任务加 `?_subdomain=queue`；bytes 通道对 t2v 设 `Accept: video/mp4`。  
- **无**与魔搭同形的「官方没有视频 API」400 闸门。

---

## 6. Gap vs Boss「六家都要 t2i / i2i / i2v」

| 家 | t2i | i2i | i2v（+ t2v 期望） |
| --- | --- | --- | --- |
| Civitai / Fal / Nano | 已有主链路（HANDOFF 证据，本文件不复验） | 同左 | 同左 |
| **HF** | 有官方 + 代码路径 | caps `i2i=source`；实发未在本复核关 | **官方有 t2v/i2v**；需 Router/SDK 接线 + 真机出片，**修正 HANDOFF/过期 inventory** |
| **魔搭 AI/CN** | 有官方 images/generations | 编辑模型 `image_url` | **官方公开材料仍无文档化视频生成**；硬拒与文档一致；若日后官方发布 videos 契约再开闸，**禁止**用图片端点冒充 |

---

## 7. Recommended next knife（仅建议，本轮不改码）

1. **HF（优先，官方已齐）**  
   - 选 1 个映射到 fal-ai 或 wavespeed 的 Hub 视频 mid（例：任务页 `Wan-AI/Wan2.1-T2V-1.3B` 或钉选 HunyuanVideo）。  
   - 走现有 Router 映射或 `InferenceClient.text_to_video` / `image_to_video` 做 **最小真机 smoke**（计费注意 HF key）。  
   - 文档刀：改 HANDOFF P3、`REPORT.md` HF 行、`hf-inventory.md`「i2v=none」、补 `huggingface.md` 官方 t2v/i2v URL；改 `graph_compile` 误导注释「魔搭/HF」。

2. **魔搭（文档优先于开闸）**  
   - 保持双层硬拒，直到 **官方** 给出 videos 请求/轮询契约（或模型页出现 API-Inference 面板且可复现出片）。  
   - 可选：带 token 复测 `/v1/videos/generations`（记失败体，不开冒充路径）。  
   - 文档刀：`modelscope.md` 能力行与 caps 对齐为 `i2v=none`；明确「Hub 视频模型 ≠ Infer 视频 API」；划清与 DashScope 万相边界。

3. **明确不做**  
   - 不把 `/images/generations` + `image_url` 当 i2v。  
   - 不把 Alibaba Model Studio 万相接到 `modelscope-*` backend。  
   - 不宣称本复核 = closed-loop Pass。

---

## 8. 源清单（本文件引用）

- HF text-to-video: https://huggingface.co/docs/inference-providers/en/tasks/text-to-video  
- HF InferenceClient: https://huggingface.co/docs/huggingface_hub/en/package_reference/inference_client  
- HF providers matrix: https://huggingface.co/docs/huggingface_hub/guides/inference  
- 魔搭 API-Inference intro: https://www.modelscope.cn/docs/model-service/API-Inference/intro  
- 魔搭头条 #960（范围 LLM/多模态/文生图）: https://modelscope.cn/headlines/article/960  
- 第三方探针（非官方）: https://lilting.ch/en/articles/modelscope-api-inference-magicube-probe  
- 本仓：`providers/capabilities.py`、`graph_compile.py`、`modelscope.py`、`huggingface.py`；`docs/HANDOFF-20260914.md`；`docs/api-usage/{modelscope,huggingface,REPORT,OFFICIAL-SOURCES}.md`

*复核时间：2026-09-16（Asia/Shanghai）。*
