# 分镜画布完善计划（v0788 → Seko 对标）

日期：2026-09-04
分支：`feat/cloud-nodes-poc`
约束：执行仍走现有 `/api/graph/compile` + `/api/generate`（Fal / Nano / 魔搭 / HF）。不自托管 Comfy。不劫持首页 `/`。不做假 Agent。

## 0. 这次先推上去的包裹

- `static/storyboard.html` + `static/storyboard.js`：v0788 Seko 风无限画布
- `static/cloud-nodes.html`：同一壳，入口 `/cloud-nodes` 与 `/storyboard` 都指到 storyboard
- `docs/seko-live-chain.md`：商汤实打 t2i / i2i / i2v 合同（无 token）
- 本计划

远端 `feat/cloud-nodes-poc@4780866` 还停在 LiteGraph 整页 HTML。本次把 storyboard 拆页推上去。

## 1. 已对齐

- 点阵无限画布、左资产右分镜、贝塞尔、点选底栏
- 图片 / 视频 tab
- `@` 芯片（文案层）
- 视频缺首帧不偷配方台残留图
- compile：无参考 → `t2i`；有参考图 → `i2i`；视频模式 → `i2v`

## 2. P0（下一刀，可见像素）

1. 分镜卡改成 640×360，空态大字「查看/编辑提示词」
2. 底栏补「文本生成」档（可先只写 prompt，不接 LLM）
3. 视频模式显示首帧缩略图槽；没连线禁止发送
4. 模型条做成四段芯片：模型 / 时长 / 画幅 / 分辨率（值仍映射现有 Fal serviceId）
5. 分镜卡空态不要 280×168 小方块

## 3. P1（编译合同，对标这次实打）

| 用户动作 | 图编译 | 备注 |
|---|---|---|
| 图片 + 无参考 | `t2i` | 默认走便宜能跑的模型，不要写死 Seedream 5.0 Pro |
| 图片 + 已连 / 已 @ 到资产 | `i2i` | `@名` 必须有 server/asset id 才进 ref；没连上的 @ 当纯文案 |
| 视频 + 已连首帧 | `i2v` | `firstFrame` = 连上的第一张图 URL |
| 视频无首帧 | 拒绝 | 已有 |

发送前可把 `@角色名` 归一成 `@图片N`（Seko `xit()`）。

实打教训：
- `z-image` 适合纯文生图，带 ref 会失败
- 图生图用 `auto` / 即梦类编辑模型
- 免费档 Seedance 2.5 会受理后失败；Vidu turbo 5s 能出片

## 4. P2（产品结构）

- 资产是画布一等节点，可拖离左列
- 左浮层：+ / 资产库 / 生成历史
- 顶栏「剧本策划 / 编辑器」继续灰，只留入口
- 九宫格 / 720° / 时间线继续不做

## 5. 不做

- 假 Agent 自动铺 6 镜
- 把首页改成画布
- 把 Seko JWT / cookie / WASM 密钥带进仓库
- 自托管 Comfy

## 6. 验收

- `/` 仍是原 studio
- `/cloud-nodes` 与 `/storyboard` 打开同一 v0788 画布
- 选中分镜 → 文生图能出图
- 连一张资产 → 图生图带上参考
- 连首帧 + 视频 tab → i2v
- 未连首帧点发送 → 明确报错，不偷图
