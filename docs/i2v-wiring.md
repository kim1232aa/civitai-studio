# 图→视频（i2v）真连线对照

用户主路径：**image 口 → i2v 节点 → 出视频**。  
链式 `t2i→i2v` / `t2i→i2i→i2v` = **真边多步 stages**，禁止一次假跑通（单次 generate 假装整链出片）。

## 画布端口（建议）

| 端口 | 类型 | 谁出 | 谁吃 |
|---|---|---|---|
| `image` | image | `image` 源 / 上游 t2i·i2i 成片口（真边） | `i2i` / `i2v` 必连 |
| `prompt` | prompt | `prompt` 节点 | `i2v` 按家可选/必填 |
| `seed` | seed | `seed` 节点 | 只认连线 |
| `negative` | prompt | `negative` 节点 | 只认连线 |
| `video` | video | `i2v` 出口 | （POC 汇点） |

未连 `image` → `blocked`，**禁止**偷成片栏 / 左侧残留。

## 出站字段（Studio payload → 各家）

统一入站：`sourceImage` / `firstFrame`（已有别名兼容）。

| backend | 官方图字段 | 时长 | 尺寸 | LoRA | 备注 |
|---|---|---|---|---|---|
| **civitai** | `sourceImage` / `startImage`（引擎分叉，见 `civitai._video_frames`） | `duration` | `aspectRatio` | AIR | 默认视频服务含 imageToVideo；引擎不同字段名不同 |
| **fal** | 端点相关：`image_url` / `start_image_url` / `first_frame_url`；尾帧 `end_image_url`/`tail_image_url` | 端点 schema | 端点 | path（sibling） | `fal_image_fields()` 已按 endpoint 解析；**禁止**误塞 i2i 的 source 槽 |
| **nano-gpt** | `imageUrl`/`image_url`/`imageDataUrl` + `mode=image-to-video` | `duration` | **catalog `resolution` token**，禁 WxH | path | 与图同：有 token 出站剥 WxH |
| **modelscope-ai/cn** | `image_url`（Hub 任务 `image-to-video`） | 偶有 | `size` | hub_repo | catalog 已标 `i2v` |
| **huggingface** | 路由相关；多数无稳定官方 i2v | — | — | unverified | 能力表宜 `i2v: none` 或 unverified，UI 勿当能出片 |

## capabilities 补字段（下一刀）

```text
capabilities.i2v: "sourceImage" | "image_url" | "first_frame" | "fal_endpoint" | "none"
capabilities.videoDuration: bool | "string_seconds"
capabilities.videoAspect: bool
```

catalog 覆盖：仅当服务 `task`/`tags` 含 i2v 才抬；`provider.i2v=none` 禁止模级抬高。

## compile 契约

1. **单汇点**（`image` 源 → `i2v`）：必边 `image→i2v.image`；payload.`kind`/`recipe`=`video`；`execute=single`。
2. **真边多步链**（`t2i→i2i` / `i2i→i2v` / `t2i→i2v` / `t2i→i2i→i2v`）：上游 image 出口接到下游 image 入口即合法。compile 返回 `stages[]` + `multiStep:true` + `execute:"staged"`；下游 `sourceImage` 可为 `{__stageOut__: <上游节点id>}`（待物化）。**不是**一次 generate 假跑通整链。
3. 缺边 / 类型不兼容 / 未连必口 → `blocked`，生成按钮不可用；**禁止**偷 form/gallery。
4. 并行多个**终端**汇点（彼此无 image 真边串起）→ 阻断。
5. wiring 断言：物化图有 `firstFrame`/`sourceImage` URL；Nano 无 `width`/`height`；无边不得出现图字段。

## UI demo（cloud-nodes.html）

| 入口 | 图 | 校验后 |
|---|---|---|
| `/cloud-nodes.html` 或 `?demo=i2v` / 「单步 demo」 | image→i2v | 绿 ok · 生成可点 |
| `/cloud-nodes.html?demo=chain` / 「链式 demo」 | t2i→i2v（同 `scripts/demo_graph_chain.py`） | 琥珀 info · `multiStep` · 生成灰 |
| `?demo=chain3` | t2i→i2i→i2v | 同上 |

## 不做

- 一次点击串跑 t2i+i2v 假装整链出片（无 stages / 无真边）
- 未连图口偷 gallery / 左栏
- HF 无官方 i2v 时画可点绿节点
