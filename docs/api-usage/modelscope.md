# ModelScope（魔搭 AI / CN）API 用法

适配器：`providers/modelscope.py` — **两家独立** `ModelScopeProvider("ai"|"cn")`。capabilities 相同：`lora=hub_repo`，`loraPath=hub_owner_repo`，`progress=status_only`，`cancel=False`，`seed` clamp=`reject` min=0 max=2147483647（**-1/空/「random」省略不发**，**禁止 mod**），`i2i=source`，`i2v=image_url`，`maxRefs=3`（天花板；目录可收紧），`refImagesField=image_url`，`videoAspect=True`，`videoDuration=False`。

## Auth / Base（禁止交叉）

| | modelscope-ai | modelscope-cn |
| --- | --- |
| Token 文件 | `~/.config/modelscope/token` | `~/.config/modelscope-cn/token` |
| Env 回退 | `MODELSCOPE_API_TOKEN` 等 | `MODELSCOPE_CN_API_TOKEN` |
| Generate base | `https://api-inference.modelscope.ai/v1` | `https://api-inference.modelscope.cn/v1` |
| Hub 列表（共用） | `https://www.modelscope.cn/openapi/v1/models` | 同左（搜目录） |

Header：`Authorization: Bearer {key}`；异步提交加 `X-ModelScope-Async-Mode: true`；轮询加 `X-ModelScope-Task-Type: image_generation`。

主机解析失败 → 502 文案声明 **不会改走另一边**。旧域 `api.modelscope.ai` 已 NXDOMAIN。

## Catalog

- Hub task slug：`text-to-image-synthesis`（**不是** `text-to-image`）、`image-to-image`、`text-to-video-synthesis`、`image-to-video`。
- 钉选：`docs/ms-models.json`。
- `GET /api/catalog?backend=modelscope-ai|modelscope-cn`。
- LoRA 搜：Hub search，返回 `path=owner/repo`；Studio 路由 `GET /api/search?backend=modelscope-ai|modelscope-cn`（无 `/api/search-loras`）。

## Import

同 HF：无云端反查。

## Generate 出站字段表

`POST {base}/images/generations`：

| Studio | Vendor | 必填? | 备注 |
| --- | --- | --- | --- |
| `serviceId` | `model`（owner/repo） | 是 | Civitai id→400；`payload.model` 与 serviceId 不一致→400 拒 remap |
| `prompt` | `prompt` | 是 | 官方表长度 < 2000；**本地不发明上限门闹** |
| `negativePrompt` | `negative_prompt` | 否 | 官方表长度 < 2000 |
| `seed` | `seed` | 否 | 官方 **[0, 2147483647]**；reject 不 wrap；**-1 / random / 空 → 省略不 POST** |
| `steps` | `steps` | 否 | 官方表 [1,100] |
| `cfgScale` | `guidance` | 否 | 字段名 **guidance** 非 guidance_scale；官方表 [1.5,20] |
| `width`+`height` | `size` `"WxH"` | 否 | |
| refs / firstFrame | `image_url` | i2i/i2v | 天花板 3；Edit-2509 官方 `images` 1–3 |
| `loras[]` | `loras` | 否 | **仅 Hub owner/repo** |

官方键集合：`model,prompt,negative_prompt,size,seed,steps,guidance,image_url,loras`。多余键 4xx 时会 slim 重试。

任务：`{id}|{task_id}`；轮询 `GET {base}/tasks/{tid}`。

## LoRA / 静默丢

权威：官方 AIGC 表 + `providers/modelscope.py` `_modelscope_loras`。

| | |
| --- | --- |
| 单条（无 weight） | 出站 **字符串** `"owner/repo"` |
| 单条带 weight/scale/strength | **本地 400**：单条官方字段是 owner/repo 字符串，没有 weight |
| 多条 | 出站 `{ "owner/repo": weight, …}`，且 **weight 之和必须 = 1.0**，最多 6；缺 weight → 400（拒默认 1.0） |
| 勿发 | `[{ "model": "owner/repo", "weight": 0.8 }]`；单条 `{repo: weight}` |
| http / Civitai / AIR | **硬拒** 400，不再 `continue` 只出底模 |
| Hub 搜 | `GET /api/search?backend=modelscope-ai|modelscope-cn&q=` |
| 禁止 | Civitai→Hub 自动换模；发明默认 strength |

夹具：path `…/3231694` → 非 Hub → 400。

现场债（2026-09-10）：`Tongyi-MAI/Z-Image-Turbo` + 单条字符串 `DiffSynth-Studio/Z-Image-Turbo-DistillPatch` → Infer 500 `Model does not exist`。待无 LoRA 底模 ↑ 隔离。

## Seed / 进度 / 取消

| 项 | 行为 |
| --- | --- |
| seed | 官方 [0, 2^31-1]；reject 不 wrap；-1/random 省略（`providers/modelscope_seed.py` + `aec35f6` boot） |
| progress | `status_only` |
| cancel | False |

注：Civision **网页** 「-1=每次随机」不等于 API-Inference 表。API 区间从 0 起；Studio -1 只表省略键，不 POST -1，也不改成本地 randint。

## Materialize

无 `/out`→data: 专用路径；`image_url` 需外网可达或 data URL。

## Code anchors

| 动作 | 行 |
| --- | --- |
| Token / BASE | `modelscope.py:15-21` |
| `_clamp_seed` / `_modelscope_loras` | `:78-180` |
| seed -1 省略 | `providers/modelscope_seed.py` |
| Hub fetch | `:201-275` |
| `generate` | `:427-531` |
| `job_status` | `:533-582` |
| register ai+cn | `:585-588` |

## AI vs CN

能力表相同；**仅** token 路径与 `api-inference.modelscope.{ai|cn}` 不同。对接时 `backend` 必须显式 `modelscope-ai` 或 `modelscope-cn`。

## Catalog 钉选 vs Hub 发现

钉选：`docs/ms-models.json`（见 [models/modelscope-inventory.md](models/modelscope-inventory.md)）。

Hub（AI/CN **共用**搜目录，**不**共用生成 base）：`GET https://www.modelscope.cn/openapi/v1/models`；slug `text-to-image-synthesis`（不是 `text-to-image`）。

钉选样本：`Tongyi-MAI/Z-Image-Turbo`、`Qwen/Qwen-Image`、`Qwen/Qwen-Image-Edit`、`krea/Krea-2-Turbo`、`krea/Krea-2-Raw`、`krea/krea-realtime-video`。

## 静默丢 / drift

| 风险 | 行为 |
| --- | --- |
| Civitai `serviceId` | 400 |
| `payload.model` ≠ `serviceId` | 400 拒 remap |
| http / AIR LoRA | 400 |
| AI 主机失败 | **禁止**改走 CN |
| 旧域 `api.modelscope.ai` | NXDOMAIN |

## 官方对照（2026-09-11）

- API-Inference：https://www.modelscope.cn/docs/model-service/API-Inference/intro
- Edit-2509 多图 1–3：https://www.modelscope.cn/learn/2577
- seed **[0, 2^31-1]**，禁 wrap；Studio -1=随机 → 省略。
- LoRA：单条 `"owner/repo"`；多条 `{repo:weight}` 且和为 1.0，最多 6。
- 能力表：`maxRefs=3`（不是 1），`refImagesField=image_url`。
