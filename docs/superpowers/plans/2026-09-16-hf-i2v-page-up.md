# HF 官方视频能选能发（页面↑）— 2026-09-16

> HEAD: `263415b`+ · Boss：六家官方有的都要能选能发；HF 官方有 t2v/i2v，出站未核。
> 禁 curl `/api/generate` 当验收。合格包仍 0。样本：未用 AIImageStudio。

## Goal
1. 画布选 `huggingface` + 视频 mid（优先 `Wan-AI/Wan2.2-I2V-A14B` 或 catalog i2v）能点 ↑
2. 同次 jobId + outbound 证明发了 video 任务（非冒充 images）
3. 成片落本地 / 写回原卡（有则记；无则诚实 Fail 原因）
4. jobId 甩 api对接助手核出站

## Non-goals
- 不宣称闭环 Pass / 不叫审
- 不改魔搭硬拒（官方文档仍无视频生成）
- 不发明 prompt；导入原帖全文

## Files likely touch (only if wire broken)
- `providers/huggingface.py`（Router/SDK video path）
- `static/storyboard.js`（若视频 mid 选不出 / ↑ 灰）
- 文档对齐：`docs/api-usage/huggingface.md` / REPORT HF 行（过期 none）

## Tasks
1. 挑未用 AIImageStudio 帖；导入 → backend=huggingface → 视频/i2v 选 Wan i2v
2. 页面点 ↑；记 jobId、submittedInput、错误体
3. 若 4xx/接线洞 → 最小修（对齐官方 InferenceClient / Router）再烧
4. 甩 api；打包证据目录（即使 Fail 也写 MANIFEST 原因）

## Done when
- api 能核同次 outbound；或诚实写出「官方有但本站仍不能发」的精确堵点
