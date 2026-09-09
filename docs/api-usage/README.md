# API 用法索引（api对接助手）

面向 Civitai Studio 本地服务 `127.0.0.1:8765`。本文档从代码抽出，供对接助手出站/轮询/导入时对照。**不要 POST `/api/generate` 做探测**；只读代码 + 可选 `GET /api/health` / `/api/providers` / `/api/catalog`。

权威能力表：`docs/capability-schema.md` + `providers/capabilities.py`（`GET /api/providers[].capabilities`）。

## 总入口

- **[REPORT.md](REPORT.md)** — 《API 各家各模型调查》大白话总报告（对照矩阵、硬闸夹具、下一轮清单模板、官方链接）
- **[models/](models/)** — 各家模型 inventory 摘要 + 机器可读索引（Fal 1492 / Civitai 304 全量；HF/魔搭钉选；Nano 发现端点）

## 何时用哪份

| 场景 | 文档 |
| --- | --- |
| **调查总报告 / 六家矩阵 / 硬闸** | [REPORT.md](REPORT.md) |
| **模型清单与 JSON/CSV 索引** | [models/](models/) |
| Studio 本地路由（import / generate / jobs / catalog / upload-out / providers） | [studio-routes.md](studio-routes.md) |
| Civitai orchestration（AIR LoRA、Buzz、rate 进度、cancel） | [civitai.md](civitai.md) |
| Fal queue（`/out`→data: materialize、`loras[{path,scale}]`、queue 进度） | [fal.md](fal.md) |
| Hugging Face Router（sync、loraConfidence=unverified） | [huggingface.md](huggingface.md) |
| 魔搭 AI / CN（两套 token+base，hub_repo LoRA） | [modelscope.md](modelscope.md) |
| NanoGPT（catalog_token 分辨率、≤3 LoRA B2 直链、promptMax 1200） | [nanogpt.md](nanogpt.md) |

## 六家 id（勿写错）

| id | 适配器 | token |
| --- | --- | --- |
| `civitai` | `providers/civitai.py` | `~/.config/civitai/token` |
| `fal` | `providers/fal.py` | `~/.config/fal/token` |
| `huggingface` | `providers/huggingface.py` | `~/.config/huggingface/token`（或 `HF_TOKEN`） |
| `modelscope-ai` | `providers/modelscope.py` (`ai`) | `~/.config/modelscope/token` |
| `modelscope-cn` | 同上 (`cn`) | `~/.config/modelscope-cn/token` |
| `nano-gpt` | `providers/nanogpt.py` | `~/.config/nano-gpt/token` |

别名（`providers/__init__.py`）：`hf`→huggingface；`ms`/`modelscope`/`魔搭`/`魔搭ai`→modelscope-ai；`魔搭cn`→modelscope-cn；`nano`/`nanogpt`→nano-gpt。

任务 id：`{backend}|{opaque}`（Fal=`fal|{endpoint}|{request_id}`）。

## 六家通规

1. **禁止静默丢字段**：UI 芯片还挂着 LoRA / 负面 / seed，出站却删掉且不报错 = P0。该 skip 的必须带 `warning` 或硬 400（魔搭 http LoRA→warning；Nano 无直链→400 `lora_no_direct_url`；Fal AIR 不当 path→不塞 `loras`）。
2. **禁止 provider drift**：`serviceId` 是 Civitai 形态（`image/...`）时发给 Fal/HF/魔搭/Nano → 400「当前选中的是 Civitai 服务…」。魔搭 AI 失败**禁止**改走 CN（base/token 不交叉）。
3. **Civitai empty service 硬错**：storyboard / Composer 无 `serviceId` → 阻断生成（文案含「缺少 serviceId」/「请先选择 Civitai 服务」），不得静默落到 Fal 默认端点。
4. **Civitai LoRA 必须有 `air`**：出站 `loras` = `{air: strength}`（`lora_map`）；无 air 的条目跳过。硬闸夹具见下。
5. **能力表不得抬高**：catalog override 只能收紧（`merge_catalog_override`）；`lora=none` 不可抬成 path/air；`progress=none` 禁止假百分比。
6. **参考图按 caps**：`maxRefs`/`refImagesField` 见 `providers/ref_images.py`；画布 `image_urls`/`input_references` 入站并集，`/api/generate` 调 `normalize_payload_refs`。
7. **Materialize**：Fal（及任何外网拉图的家）本地 `/out/...` 必须先变 `data:`（`materialize_fal_media`）；缺文件硬错，不发相对路径。
8. **成片生效看 sidecar `submittedInput`**，不要只看成片栏有图；页面成功路径不读 `generate.warning`。

## 硬闸 / 夹具（tests）

| 夹具 | 用途 | 出处 |
| --- | --- | --- |
| 图 `134923572`；LoRA `urn:air:krea2:lora:civitai:2323765@3071582` strength `0.8` | Civitai import→chip→outbound air | `docs/superpowers/plans/2026-09-08-storyboard-134923572-lora-air-hardgate.md`；`scripts/test_storyboard_graph.py` `test_v0821n_krea2_import_hardgate` |
| LoRA version `3231694`（Asian Mix）；下载链 `https://civitai.com/api/download/models/3231694` | Fal/HF/Nano path；魔搭必须 skip | `docs/provider-lora.md`；`scripts/test_p0_wiring.py` |
| AIR-only Fal：`{"air":"urn:air:sdxl:lora:civitai:1@2"}` → body **无** `loras` | AIR 不当 path | `scripts/test_fal_fields.py` |
| Nano prompt >1200 → `prompt_too_long` | FE+server 双拦 | `nanogpt.NANO_PROMPT_MAX` |

## 读源顺序

`providers/capabilities.py` → 各 `providers/<id>.py` → `providers/ref_images.py` → `server.py` Handler → `docs/capability-schema.md`。`graph_compile.py`：边=数据依赖，出站只带连线字段。

## 官方文档快照

2026-09-08 对照过官方页（Context7 月配额满时改走 WebFetch）：

- Fal queue：https://fal.ai/docs/documentation/model-apis/inference/queue
- HF Inference Providers：https://huggingface.co/docs/inference-providers/guides/first-api-call
- Civitai orch recipes：https://developer.civitai.com/orchestration/recipes/

详见各 provider 文末「官方对照」节。**Comfy-krea2+AIR ≠ Fal-Krea v2**。
