# 能力表草案（云 API 连线画布 · 多云配方台）

选型钉死：**节点 = 云能力积木，执行 = 各家 HTTP**，不嵌 Comfy `/prompt`。
本文只定「后端一份声明 → 前端按声明渲染 → 出站按声明剥离」。未立项前不改 `index.html` 主路径。

## 原则

1. **单一真相**：能力只从 `GET /api/providers` 或 `GET /api/catalog` 条目上的 `capabilities` 来；前端禁止再写死 `isNanogpt` / `isModelscope` 旁路。
2. **缺省显式**：未知字段 = `null` / `"none"`，禁止静默当成「全支持」或「全关」。
3. **出站同源**：`compile(graph|form) → body` 只许带能力表允许的键；禁止 persist 发明字段（例：Nano 禁 `width`/`height`）。
4. **图/视频共用同一 schema**，用 `media` / `progress` 区分。

## Provider 级（`/api/providers`）

| 字段 | 类型 | 含义 | 例 |
|---|---|---|---|
| `id` | string | 已有 | `nano-gpt` |
| `label` | string | 已有 | NanoGPT |
| `capabilities.lora` | `"air" \| "path" \| "hub_repo" \| "none"` | LoRA 官方形态 | Civitai=`air`；Fal/Nano=`path`；魔搭=`hub_repo`；无=`none` |
| `capabilities.loraPath` | `"http" \| "civitai_download" \| "hub_owner_repo" \| "none"` | path 允许什么 | 魔搭不要 http |
| `capabilities.resolution` | `"free_wh" \| "catalog_token" \| "aspect" \| "none"` | 尺寸怎么交 | Nano=`catalog_token`；Civitai/Fal 图常 `free_wh` |
| `capabilities.seed` | `{ min, max, clamp: "reject"\|"mod"\|"none" }` | 种子域 | Nano int32 + `mod` |
| `capabilities.promptMax` | number \| null | 提示词上限字符 | Nano `1200`；无上限 `null` |
| `capabilities.negative` | bool | 是否吃负面 | |
| `capabilities.progress` | `"rate" \| "queue" \| "status_only" \| "none"` | waitPane | Civitai=`rate`；Fal=`queue`；魔搭=`status_only`；HF/Nano 同步=`none` |
| `capabilities.cancel` | bool | 能否取消队列 | |
| `capabilities.estimate` | `"buzz" \| "pricing_api" \| "catalog_price" \| "none"` | 预估 | |
| `capabilities.sampler` | bool | sampler/scheduler UI | 仅 Civitai（及明确文档的家） |
| `capabilities.i2i` | `"source" \| "first_frame" \| "input_references" \| "none"` | 图生图字段名族 | |
| `capabilities.video` | bool | 是否暴露视频 tab | |

## Model / 服务级（catalog item）

继承 provider，可覆盖：

| 字段 | 类型 | 含义 |
|---|---|---|
| `supportsLora` | bool | 该端点是否真吃 LoRA（Fal `/lora` sibling、Nano `*-lora`） |
| `resolutionTokens` | string[] \| null | `catalog_token` 时必填，来自官方目录 |
| `imageFields` | string[] | Fal 已有：首尾帧字段名 |
| `aspectRatioField` | string \| null | `aspect_ratio` / `ratio` / null |
| `durationField` | string \| null | |
| `promptField` | string | 默认 `prompt` |
| `progress` | 覆盖 provider | 极少需要 |
| `loraShape` | `"loras" \| "lora_url" \| "lora_path" \| "lora" \| null` | Fal 字段形状 |

## 出站剥离规则（编译器用）

- `resolution=catalog_token` → body 只留 `resolution`/`size`/`aspect_ratio`，**删除** `width`/`height`
- `lora=hub_repo` → 丢 http/AIR；只留 `owner/repo`
- `lora=path` → AIR/`urn:` 不当 path；可 versionId→Civitai 下载链
- `lora=none` 或 `supportsLora=false` → 删除全部 lora 键，UI 可提示
- `progress=none` → waitPane **禁止**假百分比
- `promptMax` → 超长生成前截断或阻断（与现 Nano 红字一致，文案要诚实）

## 现网六家初填（待核实后冻结）

| id | lora | resolution | seed | progress | cancel | estimate |
|---|---|---|---|---|---|---|
| civitai | air | free_wh | none clamp | rate | yes | buzz |
| fal | path | free_wh (+aspect 字段) | none | queue | yes | pricing_api |
| huggingface | path* | free_wh | mod int32 | none | no | none |
| modelscope-ai | hub_repo | free_wh (`size`) | mod int32 | status_only | no | none |
| modelscope-cn | hub_repo | free_wh (`size`) | mod int32 | status_only | no | none |
| nano-gpt | path | catalog_token | mod int32 | none | no | catalog_price |

\*HF：路由硬塞 path≠官方 `/lora`；能力表应标 `loraConfidence: "unverified"`，UI 不得当「已加载」绿勾。

## 画布节点（后挂，线性 POC）

节点 `op` ∈ 能力表云操作：`t2i` `i2i` `t2v` `i2v` `upscale` `bg` `lora_apply`…  
连线端口类型：`prompt` `image` `seed` `latent?`（先不做 latent）。  
`compile(linear)` → 有序 `Provider.generate` 调用；与表单模式共用同一 compile。

## 验收（审查合同）

- 声明 = 渲染 = 出站；缺能力显式藏/红，不静默
- 芯片 = 节点同值；缺挂 P0
- `test_p0_wiring`：图/表单 JSON → body 字段断言（Nano 无 WxH 已有样板）

## 不做

- 不嵌 ComfyDeploy / 本地 `/prompt`
- 不把 Comfy 类名（CheckpointLoader 等）画成节点骗自己
- 能力表未落地前不上自由连线
