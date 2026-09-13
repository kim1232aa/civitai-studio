# 换家可点 + 各家模型搜索 + LoRA 搜索

> plan-loop：按任务勾选。上一轮六家出图用脚本写死供应商，页面选不了家，那次不算过。

## 事实

- 选 HF / 魔搭 / Nano 会被旧分镜配方拽回 Fal（已修换家钉住）。
- `#serviceFilter`（搜索模型）被 CSS `.dock.show #serviceFilter { display:none }` 藏掉，页面只剩 LoRA 搜索。
- 点 ↑ 的 `#send` 也被藏，看得见的是 `#sendCap`。

## 任务

- [x] T1 展开模型搜索：六家下拉旁都能搜当前家目录
- [x] T2 LoRA 搜索保留，按当前家提示
- [x] T3 截图：LoRA 搜 + 模型搜都在，换家不跳回 Fal
