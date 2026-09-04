# v0791 计划：P0 + P1 + P2

日期：2026-09-04
分支：`feat/cloud-nodes-poc`
原则：UX 对标 Seko 无限画布；执行仍走现有 `/api/graph/compile` + `/api/generate`（Fal / Nano / 魔搭 / HF）。不接商汤付费接口，不入库任何 JWT。

## 0. 包裹

本提交：
- `static/storyboard.html` + `static/storyboard.js`（v0791-seko）
- `scripts/test_storyboard_graph.py`（10 例）
- 本计划

不推：
- 远端整棵 `server.py` / `providers/*`（避免覆盖 feat 上的稳定路由）
- `out/`、token、Seko 成片二进制

入口：`/` 配方台；`/storyboard.html` 与 `/cloud-nodes` 打开同一分镜画布。LiteGraph 仍在 `static/cloud-nodes.html`，顶栏可进。

## 1. 产品目标

选中分镜 → 底栏发图或视频 → `buildGraph()` 按连线决定 `t2i` / `i2i` / `i2v` → `/api/graph/compile` + `/api/generate` → 轮询 `/api/jobs/{id}` 回填到卡上。成片自动收进资产库，可再连到下一镜。

## 2. 对标合同（只抄合同，不接商汤）

| 用户动作 | 编译 |
|---|---|
| 图片 + 无参考 | `op=t2i` |
| 图片 + 已连且有 url 的资产 / 上一镜成片 | `op=i2i`，第一张进 image 口 |
| 视频 + 已连首帧 | `op=i2v`，`firstFrameId` 可在底栏切换 |
| 视频无首帧 | 前端拒绝；compile 也会红「未连线输入口 image」 |
| `@名` 未连边 | 纯文案，不进 ref |
| `/api/outs` 历史 | 只在左轨「历史」页，不进 compile |

## 3. 切片

### P0 — 已落地
- [x] 分镜卡 640×360，空态「点击查看或编辑提示词」
- [x] 芯片点击 = 连边并写入 `@标题`
- [x] 视频模式显示首帧槽；没连线底栏红字 + 发送拒绝
- [x] `buildGraph()`：无参考 t2i / 有参考 i2i / 视频 i2v
- [x] `scripts/test_storyboard_graph.py` 10/10

### P1 — 资产一等节点（本提交）
- [x] 资产是画布节点，可从左轨拖到空白处或分镜上
- [x] 上传走 `/api/upload-out`，失败回退 object URL
- [x] 生成成功后成片晋升为 `out-{shotId}` 资产节点
- [x] 有 url 的分镜可连到下一镜（shot → shot）
- [x] i2v 首帧默认第一张连线图，底栏 frame-chip 可切换
- [x] `@` 弹出资产 + 已出片的分镜

### P2 — 体验（本提交）
- [x] 新分镜预填【镜n】模板
- [x] 左轨「资产 / 历史」分页；历史不自动铺到画布
- [x] 左轨 ＋ 接到此镜（拖拽的点击替代）
- [x] 顶栏「剧本策划 / 编辑器」灰；配方台仍从右侧进 `/`
- [x] 底栏模型 / 时长 / 画幅 / 分辨率写入 session
- [x] 多结果宫格不做

## 4. 不做

- 假 Agent 自动铺镜
- 劫持首页 `/`
- JWT / cookie / WASM 入库
- 自托管 Comfy
- 九宫格 / 720° / 时间线 / 积分条

## 5. 验收

1. `/` 仍是配方台
2. `/storyboard.html` 打开 16:9 分镜画布，戳 v0791-seko
3. 空分镜图片模式 → t2i
4. 连资产再发 → i2i
5. 视频无首帧 → 拒绝
6. 连首帧再发视频 → i2v
7. 出图后右侧出现「分镜n成片」，可拖到下一镜
8. 仓库无凭证
