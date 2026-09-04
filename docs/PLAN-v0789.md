# v0789 计划：把分镜画布做到能跑通 t2i → i2i → i2v

日期：2026-09-04
分支：`feat/cloud-nodes-poc`
原则：UX 对标 Seko 无限画布；执行仍走现有 `/api/graph/compile` + `/api/generate`（Fal / Nano / 魔搭 / HF）。不接商汤付费接口，不入库任何 JWT。

## 0. 包裹

已推（文档）：`docs/PLAN-seko-storyboard.md`、`docs/seko-live-chain.md`

本提交要推：
- `static/storyboard.html` + `static/storyboard.js`（v0789-seko，640×360 卡）
- 本计划

不推：
- 远端 `static/cloud-nodes.html`（保留 LiteGraph v0787）
- 本地过期 `server.py` / `providers/*`
- `out/`、token、Seko 成片二进制

入口：`/` 配方台；`/storyboard.html` 分镜画布。`/cloud-nodes.html` 暂时仍是 LiteGraph。

## 1. 产品目标

选中分镜 → 底栏发图或视频 → `buildGraph()` 按连线决定 `t2i` / `i2i` / `i2v` → `/api/graph/compile` + `/api/generate` → 轮询 `/api/jobs/{id}` 回填到卡上。

## 2. 对标合同

| 用户动作 | 编译 |
|---|---|
| 图片 + 无参考 | `op=t2i` |
| 图片 + 已连且有 url 的资产 | `op=i2i`，第一张进 image 口 |
| 视频 + 已连首帧 | `op=i2v` |
| 视频无首帧 | 前端拒绝；compile 也会红 |
| `@名` 未连边 | 纯文案，不进 ref |

不要写死 Seedream 5.0 Pro / Seedance 2.5。

## 3. P0 本地已落地

- [x] 分镜卡 640×360
- [x] 戳 `v0789-seko`
- [x] 芯片点击切换边 + `@标题`
- [x] 视频首帧槽；没连线拒绝发送
- [x] `buildGraph()` t2i / i2i / i2v
- [ ] 远端 storyboard.html 仍是 stub，需盖上

## 4. 不做

假 Agent、劫持 `/`、JWT 入库、自托管 Comfy、九宫格 / 720° / 时间线。
