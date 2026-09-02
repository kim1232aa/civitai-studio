# 云节点画布 · Night Lab 样式稿（POC）

分支：`feat/cloud-nodes-poc`。壳可 React/Drawflow，**不强制单页**。执行仍走云 API `compile(graph)`，不嵌 Comfy 运行时。

## 视觉原则
- 背景：Night Lab 深底 `#0e1016` / 面板 `#161922`
- 强调：珊瑚 `#e85d4c`（选中边、主按钮）
- **禁止** CheckpointLoader / KSampler 等假 Comfy 类名；节点标题用能力名：文生图、LoRA、超分、视频、提示词…

## 节点卡（可读卡，禁止纯文字堆）
| 元素 | 规格 |
|---|---|
| 尺寸 | 宽 232px，圆角 12px |
| 顶条 | 3px 能力色（按 op：prompt/t2i 珊瑚、seed 金、image 绿、i2i/超分 青、i2v 紫、LoRA 靛） |
| 头 | **类型色块图标** 22×22 + 标题 + 右侧 `···`；选中边框珊瑚 |
| 身 | **短摘要行** `键 · 值`（模型 / 尺寸 / 文案截断）；状态用 pill（image 已连 / 缺 image·阻断），**不**把 wiring JSON 堆在卡上 |
| 口 | 左入右出，圆点 10px；未连=灰，已连=珊瑚，缺必连=红 |

落地：`static/cloud-nodes.html` `v0782-node-preview`（`OP_ICON` / `OP_CLS` / `nodeBodyHtml` / `previewHtml`）。门闩 / validate / Gen 行为勿动。

## 节点预览（卡上挂缩略）
- **有成片/首帧就显示**：`params.url`（image 源）、`params.previewUrl` / `resultUrl`（t2i / i2i / i2v）
- 预览槽：16:10、圆角 8px；图片 `object-fit:cover`；视频可用 `<video>` 或静帧 +「视频」badge
- 无资源：斜纹占位「待成片 · 图片/视频」——像常见 Comfy/工作流台节点预览，**不是**纯文字堆
- wiring JSON 仍只在左栏 outBox，不进卡面

## 芯片 = 节点
- 选中节点时，左侧（或检视抽屉）芯片必须同值：底模 / LoRA / seed / resolution
- 对不上：节点头红点 + 文案「与配方不一致」

## 连线
- 贝塞尔，宽 2px；悬停加粗
- 断线/跨类型：生成按钮旁红字，**点前阻断**

## 布局草图
```
┌────────左栏配方/检视────────┬────────画布──────────────┐
│ 能力芯片 / LoRA / seed      │  [提示词]──▶[文生图]──▶… │
│ 与选中节点双向高亮          │                         │
└─────────────────────────────┴──底栏：校验 · 生成───────┘
```

## 交付顺序
1. 本样式稿（可并行）
2. compile P1 放行后挂壳
3. 可点界面再叫 @UI审查员
