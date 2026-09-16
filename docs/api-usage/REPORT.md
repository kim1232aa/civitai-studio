# Civitai Studio · API 各家各模型调查报告

> 大白话入口：**想知道六家怎么 auth、LoRA 长啥样、seed 会不会被钳、进度/取消有没有、参考图往哪塞、哪里会静默丢字段** —— 先看这份，再点进各家 md + `models/` 清单。
>
> 依据：适配器代码（`providers/*.py`）、本地目录 JSON、已有 `docs/api-usage/*.md`。**不发明**代码/目录/OpenAPI overlay 里没有的官方字段。  
> 探测允许：`GET /api/health` / `/api/providers` / `/api/catalog`。**禁止 POST `/api/generate` 做文档验证。**  
> 生成日：2026-09-08（UTC+8）。

## 怎么用这份报告

| 你想… | 去哪 |
| --- | --- |
| 六家对照一眼看完 | 下文「六家对照矩阵」 |
| 某家出站字段 / 端点 | [civitai.md](civitai.md) / [fal.md](fal.md) / [huggingface.md](huggingface.md) / [modelscope.md](modelscope.md) / [nanogpt.md](nanogpt.md) |
| Studio 本地路由 | [studio-routes.md](studio-routes.md) |
| 模型有哪些、条数对不对 | [models/](models/)（Fal 1492 / Civitai 304 有全量 JSON；HF/魔搭钉选；Nano 仅发现端点+样本） |
| 能力枚举合同 | [`docs/capability-schema.md`](../capability-schema.md) + `providers/capabilities.py` |
| LoRA 深挖 | [`docs/provider-lora.md`](../provider-lora.md) |
| 索引总表 | [README.md](README.md) |

**成片是否吃到 LoRA**：看 sidecar `submittedInput`，不要只看成片栏有图。页面成功路径不读 `generate.warning`。

---

## 六家对照矩阵

| 项 | civitai | fal | huggingface | modelscope-ai | modelscope-cn | nano-gpt |
| --- | --- | --- | --- | --- | --- | --- |
| **id** | `civitai` | `fal` | `huggingface` | `modelscope-ai` | `modelscope-cn` | `nano-gpt` |
| **适配器** | `providers/civitai.py` | `fal.py` | `huggingface.py` | `modelscope.py` (`ai`) | 同上 (`cn`) | `nanogpt.py` |
| **Auth token 文件** | `~/.config/civitai/token` | `~/.config/fal/token` | `~/.config/huggingface/token`（或 `HF_TOKEN`） | `~/.config/modelscope/token` | `~/.config/modelscope-cn/token` | `~/.config/nano-gpt/token` |
| **Auth header** | `Bearer` | `Key` | `Bearer` | `Bearer` | `Bearer` | `Bearer` **且** `x-api-key` |
| **Base / 提交** | `orchestration.civitai.com` workflows | `queue.fal.run/{endpoint}` | `router.huggingface.co` | `api-inference.modelscope.ai/v1` | `api-inference.modelscope.cn/v1` | `nano-gpt.com/api/v1` |
| **LoRA 形态** | **air** `{air: strength}` | **path** `loras[{path,scale}]`（或 lora_url/path） | **path**（mapped） | **hub_repo** `owner/repo` | 同左 | **path** ≤3 + B2 直链 |
| **loraPath** | none（不吃 http） | http / versionId→Civitai DL | http | hub_owner_repo | hub_owner_repo | civitai_download |
| **loraConfidence** | official | official | **unverified** | official | official | official |
| **Seed clamp** | none（原样 int） | none | mod int32 | mod int32 | mod int32 | mod int32 |
| **分辨率** | free_wh | free_wh (+aspect) | free_wh | free_wh → `size` WxH | 同左 | **catalog_token**（禁自由 WxH） |
| **负面** | yes | yes（schema 允许时） | yes（通道相关） | yes | yes | yes |
| **progress** | **rate**（estimatedProgressRate） | **queue**（IN_QUEUE/…） | **none**（sync） | **status_only** | status_only | **none**（图 sync；视频 poll 仍无 %） |
| **cancel** | yes DELETE workflows | yes PUT cancel | no | no | no | no |
| **estimate** | buzz | pricing_api | none | none | none | catalog_price |
| **sampler/scheduler UI** | yes | no | no（fal 通道可带 scheduler） | no | no | no |
| **i2i / i2v** | source / sourceImage | first_frame / fal_endpoint | none / none | source / image_url | 同左 | input_references / image_url |
| **maxRefs / 字段** | 9 / `images` | 9（单图 schema→1）/ `image_urls` | 9 / `image_urls` | 1 / `image_url` | 1 / `image_url` | 5 / `input_references` |
| **Materialize `/out`→data:** | 不需要（orch blob） | **必须** `materialize_fal_media` | 未专用调用；优先 http/data | 无专用；需可达 URL | 同左 | 无专用；http/data |
| **Import 反查** | 强（图 id / AIR / meta） | Fal request id | 无 | 无 | 无 | 无 |
| **静默丢风险（高）** | 无 `air` 的 LoRA 条被 `continue` | AIR-only → body 无 `loras`；非 LoRA 端点硬塞 422 | 发出去≠加载；OpenAI 通道忽略 LoRA | http/AIR LoRA skip（有 warning，UI 可能不展示） | 同左 | **fail-closed**（缺直链 400，不静默） |
| **本地目录条数** | **304**（`catalog.json`） | **1492**（`fal-models.json`） | 8 钉选 | 7 钉选 | 同左（共享 Hub） | 0 离线全量（live TTL 300s） |

别名（`providers/__init__.py`）：`hf`→huggingface；`ms`/`modelscope`/`魔搭`/`魔搭ai`→modelscope-ai；`魔搭cn`→modelscope-cn；`nano`/`nanogpt`→nano-gpt。

任务 id：`{backend}|{opaque}`（Fal=`fal|{endpoint}|{request_id}`）。

---

## 通规（对接红线）

1. **禁止静默丢字段**：芯片还挂着 LoRA/负面/seed，出站却删掉且不报错 = P0。该 skip 的必须 `warning` 或硬 400。
2. **禁止 provider drift**：Civitai 形态 `serviceId`（如 `image/...`）发给 Fal/HF/魔搭/Nano → 400。魔搭 AI 失败**禁止**改走 CN。
3. **Civitai empty service 硬错**：storyboard / Composer 无 `serviceId` → 阻断，不得静默落到 Fal 默认端点。
4. **Civitai LoRA 必须有 `air`**：出站 `loras = {air: strength}`；无 air 跳过。
5. **能力表不得抬高**：`merge_catalog_override` 只能收紧；`lora=none` 不可抬成 path/air；`progress=none` 禁止假百分比。
6. **参考图按 caps**：见 `providers/ref_images.py`；画布 `image_urls`/`input_references` 入站并集。
7. **Materialize**：Fal（及外网拉图）本地 `/out/...` 必须先变 `data:`；缺文件硬错。

---

## ⚠ Comfy-krea2+AIR ≠ Fal-Krea v2

这是最容易写错文档/夹具的地方，单独钉死：

| 路径 | 是什么 | LoRA | 备注 |
| --- | --- | --- | --- |
| **Studio 硬闸（Civitai Comfy）** | `serviceId` = `image/comfy/krea2/turbo/createImage`（engine=`comfy`, ecosystem=`krea2`） | **吃** `urn:air:krea2:lora:civitai:…` | 夹具图 `134923572`；job `12100372-20260908044346005` air@0.8 Pass |
| **Civitai recipe「Fal-Krea v2」** | orchestration `engine:"fal"`, `model:"krea2"` | **官方写明不接** LoRA / negative / width·height | 用 aspectRatio + creativity；**勿**把这份 recipe 文档套到 Comfy-krea2 |
| **Fal queue 端点** | 如 `fal-ai/krea-2/turbo/lora` | path `loras[{path,scale}]` | 另一家 HTTP；与 Comfy AIR 无关 |

**一句话**：硬闸验收的是 **Comfy + AIR**，不是 Fal-Krea v2 recipe，也不是 `fal-ai/krea-2/*`。

---

## Per-provider（详情 + inventory）

### 1. Civitai — [civitai.md](civitai.md) · [models/civitai-inventory.md](models/civitai-inventory.md)

- Orchestration：`POST …/v2/consumer/workflows`；状态 GET；取消 DELETE。
- Catalog：304 条；默认图 Comfy-krea2 turbo；默认视频 `video/minimax-h3-comfy/imageToVideo`。
- LoRA：`lora_map` → `{air: float}`；hunyuan 等引擎可能改成 `[{air,strength}]` 列表（见 `apply_frames` / build）。
- 进度：`rate` ← `estimatedProgressRate`；含 `precedingJobs` / `etaSeconds`。
- 全量索引：`models/civitai-index.json`。

### 2. Fal — [fal.md](fal.md) · [models/fal-inventory.md](models/fal-inventory.md)

- Queue：submit → poll status → result；cancel PUT。
- Catalog：**1492**；OpenAPI overlay **141**；`supportsLora` 运行时推断（本轮 inventory ≈ **160** true）；`supportsI2v` ≈ **236**。
- Materialize：`/out` → data: 硬门槛。
- LoRA sibling 可能改 `serviceId`（turbo → turbo/lora）。
- 全量索引：`models/fal-index.json` + `.csv`（摘要表，非 1492 篇散文）。

### 3. Hugging Face — [huggingface.md](huggingface.md) · [models/hf-inventory.md](models/hf-inventory.md)

- Router 映射；sync 完成（`hf|sync|{hex}`）；progress/cancel = none/false。
- 钉选 8 条；其余 Hub live search。
- **`loraConfidence=unverified`**：UI 禁止绿勾「已加载」。

### 4. 魔搭 AI / CN — [modelscope.md](modelscope.md) · [models/modelscope-inventory.md](models/modelscope-inventory.md)

- **两家独立** token + base，主机失败也不互切。
- Hub task slug：`text-to-image-synthesis`（不是 `text-to-image`）。
- 钉选 7 条（含 `Tongyi-MAI/Z-Image-Turbo`、`krea/Krea-2-*`）。
- http LoRA → skip + warning。

### 5. NanoGPT — [nanogpt.md](nanogpt.md) · [models/nanogpt-inventory.md](models/nanogpt-inventory.md)

- Live catalog；仓库无全量 dump。
- promptMax 官方无；o150 实测 fallback **400**（禁止发明 1200）；resolution **仅**目录 token；LoRA fail-closed。
- 实测样本：`z-image-turbo-lora`、`wavespeed-ai/krea-v2/turbo-lora`。

### 6. Studio 本地 — [studio-routes.md](studio-routes.md)

- `127.0.0.1:8765`；`/api/providers` / catalog / import / upload-out / jobs / graph/compile。
- 文档**不要** POST `/api/generate`。

---

## 硬闸夹具（已通过 / 参考）

| 夹具 | Provider | 期望 | 出处 |
| --- | --- | --- | --- |
| 图 **`134923572`**；LoRA `urn:air:krea2:lora:civitai:2323765@3071582` strength **0.8**；service `image/comfy/krea2/turbo/createImage`；job **`12100372-20260908044346005`** | **civitai** | import→chip 带 air；出站 `loras` 含该 air@0.8；非黑图 | `docs/superpowers/plans/2026-09-08-storyboard-134923572-lora-air-hardgate.md`；`scripts/test_storyboard_graph.py` `test_v0821n_krea2_import_hardgate`；`out/12100372-20260908044346005_0.jpg` |
| Fal i2v smoke **`01a07eb5`**（全 id `01a07eb5-763f-76d2-a71c-a59928ea5f55`） | **fal** | endpoint `fal-ai/minimax/video-01/image-to-video`；`submittedInput` 含 `prompt` + **materialized** `image_url`（`data:image/jpeg;base64,…`）；jobId `fal|fal-ai/minimax/video-01/image-to-video|01a07eb5-…` | `out/fal_fal-ai_minimax_video-01_image-to-video_01a07eb5-…_0.json` + `.mp4` |
| LoRA version **`3231694`**（Asian Mix）；DL `https://civitai.com/api/download/models/3231694` | Fal/HF/Nano path；魔搭必须 skip | `docs/provider-lora.md`；`scripts/test_p0_wiring.py` |
| AIR-only Fal：`{"air":"urn:air:sdxl:lora:civitai:1@2"}` → body **无** `loras` | fal | `scripts/test_fal_fields.py` |
| Nano prompt >400（实测）→ `prompt_too_long` 明示超 N 字 | nano-gpt | `NANO_PROMPT_MAX` |

---

## 下一轮硬闸清单模板（Fal / HF / 魔搭 / Nano）

复制下面表格，每家填一行；**只许页面 ↑ 验收**，代理勿 curl POST `/api/generate`。

| 检查项 | Fal | HF | 魔搭-ai | 魔搭-cn | Nano |
| --- | --- | --- | --- | --- | --- |
| Token 文件存在 / `hasKey` | ☐ | ☐ | ☐ | ☐ | ☐ |
| Catalog 能列出（本地或 live） | ☐ 1492 | ☐ 钉选+搜索 | ☐ 钉选+Hub | ☐ 同左不同 base | ☐ live |
| 选中非 Civitai `serviceId`（防 drift） | ☐ | ☐ | ☐ | ☐ | ☐ |
| 空/错误 service → **硬错** 非静默 | ☐ | ☐ | ☐ | ☐ | ☐ |
| LoRA 形态正确进 `submittedInput` | ☐ path/scale | ☐ path（unverified 提示） | ☐ owner/repo | ☐ owner/repo | ☐ ≤3 B2；sidecar 无签名 URL |
| Civitai http LoRA 行为 | ☐ 可用 | ☐ 塞 body | ☐ **skip+warning** | ☐ skip+warning | ☐ 解 B2 或 400 |
| AIR-only LoRA | ☐ 不进 path | ☐ 丢弃 | ☐ 跳过 | ☐ 跳过 | ☐ 400 `lora_no_direct_url` |
| Seed：超大导入是否 mod / 不丢 | ☐ none | ☐ mod | ☐ mod | ☐ mod | ☐ mod + UI 回写 |
| 分辨率出站 | ☐ free_wh/aspect | ☐ image_size | ☐ size WxH | ☐ size WxH | ☐ **仅 token**；无 width/height |
| 负面是否按 caps 发出 | ☐ | ☐ | ☐ | ☐ | ☐ |
| 参考图字段 / maxRefs | ☐ image_urls≤caps | ☐ | ☐ image_url×1 | ☐ | ☐ input_references≤5 |
| `/out` materialize（若用本地帧） | ☐ 必须 data: | ☐ 优先 http/data | ☐ 可达 URL | ☐ | ☐ |
| progress UI 不假造 % | ☐ queue | ☐ none | ☐ status_only | ☐ | ☐ none |
| cancel（仅宣称 True 的家） | ☐ PUT | — | — | — | — |
| AI≠CN（魔搭：失败不互切） | — | — | ☐ | ☐ | — |
| promptMax（Nano 1200） | — | — | — | — | ☐ |
| sidecar `submittedInput` 人工核对 | ☐ | ☐ | ☐ | ☐ | ☐ |
| 夹具 id / out 文件名记下 | | | | | |

**建议夹具种子（可换，但要写进 PR）：**

- Fal 图：`fal-ai/z-image/turbo/lora` + DL `3231694`；Fal 视频：延续 `minimax/video-01/image-to-video` materialize。
- HF：钉选 `Tongyi-MAI/Z-Image-Turbo`（mapped）+ path LoRA；确认 warning / unverified。
- 魔搭：`Tongyi-MAI/Z-Image-Turbo`；故意挂 Civitai DL → 必须 warning 且不进 body。
- Nano：`z-image-turbo-lora` + version `3231694`；另测超长 prompt → `prompt_too_long`。

---

## 官方文档链接（2026-09-08 对照）

| 家 | 链接 | Studio 对齐要点 |
| --- | --- | --- |
| Fal queue | https://fal.ai/docs/documentation/model-apis/inference/queue | submit→poll；`Authorization: Key`；status `?logs=1`；cancel PUT |
| HF Inference Providers | https://huggingface.co/docs/inference-providers/guides/first-api-call | Studio 走 Router 映射，非裸 widget；LoRA 不保证 |
| Civitai orch recipes | https://developer.civitai.com/orchestration/recipes/ | workflows + AIR LoRA；**分清 Comfy-krea2 vs Fal-Krea v2** |
| NanoGPT | https://docs.nano-gpt.com/introduction | images/models + video-models；resolution token |
| 魔搭 Hub OpenAPI | `https://www.modelscope.cn/openapi/v1/models` | task slug `*-synthesis`；生成 `api-inference.modelscope.{ai\|cn}` |

各家文末「官方对照」节有更细摘录。

---

## 缺口汇总（诚实条）

| 缺口 | 说明 |
| --- | --- |
| Fal OpenAPI 覆盖不全 | overlay 141 / 目录 1492；大量端点靠 `infer_image_fields` 启发式 |
| Fal `supportsLora` 非 catalog 预存 | 运行时推断；LTX `camera_lora` 等会进「含 lora」但非用户 path LoRA |
| HF / 魔搭 / Nano 无离线全量 | 仅钉选或 live；inventory 写清发现端点 |
| Nano 全量需 token | 本报告未拉取 live 目录（避免依赖密钥写进文档） |
| Civitai catalog `status=unknown` 多 | 磁盘缓存；需 refresh 才接近 live health |
| HF `/out` materialize | 当前路径未调用 `materialize_fal_media` |
| UI 不展示部分 warning | 魔搭 skip LoRA 等；对接以 API JSON / sidecar 为准 |
| 未对生产 POST generate | 符合安全合同；夹具来自既有 out/ 与测试 |

---

## 文件地图

```
docs/api-usage/
  REPORT.md          ← 本文件（总入口）
  README.md          ← 索引 + 通规
  studio-routes.md
  civitai.md / fal.md / huggingface.md / modelscope.md / nanogpt.md
  models/
    README.md
    fal-inventory.md + fal-index.json + fal-index.csv
    civitai-inventory.md + civitai-index.json
    hf-inventory.md + hf-index.json
    modelscope-inventory.md + modelscope-index.json
    nanogpt-inventory.md + nanogpt-index.json
```
