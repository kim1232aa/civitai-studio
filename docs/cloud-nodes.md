# 节点画布 · Night Lab

Comfy 手感的连线画布。执行走云 API（Fal / Nano / 魔搭 / Civitai / HF），不是自托管 Comfy。

## 入口

- `/` 配方台
- `/cloud-nodes.html` 节点画布
- 两边顶栏互切。不要把 `/` 劫持成画布。

## 操作

- 双击空白搜节点（中文名可用）
- 左侧节点库点一下添加
- 端口拖线，空格/中键平移，滚轮缩放
- Delete 删选中，Ctrl+Z 撤销，Ctrl+Enter 校验或运行
- 点节点在左侧改参数；`serviceId` 来自 `/api/catalog`

## 节点

`prompt` `negative` `seed` `image` `t2i` `i2i` `i2v` `lora_apply`

没有 `CheckpointLoader`。seed / 提示词 / 负面词 / LoRA 只认连线。

## 执行

1. 校验连线 → `POST /api/graph/compile`
2. 单步：运行此步 → `POST /api/generate`，若返回 job id 则轮询 `/api/jobs/{id}`
3. 多步：按钮变成「运行下一步 · op」。上游成片 url 填进 `__stageOut__`。禁止一次 generate 假跑整链。
   LiteGraph 已有 step runner（`fillStageRefs` / `nextRunnableStage`）；`invalidate()` 会清空 `stageUrls`，避免拓扑变更后复用陈旧成片。

Hugging Face 无官方 i2v，校验会红。

## 验证

```
python3 scripts/test_cloud_nodes.py
```
