# Plan — 下一步（老板 2026-09-17「做个 plan」）

**Authority:** 群里老板原话三块 + `docs/REQUIREMENTS-20260910.md` §0–§1；`GOAL.md` 记分。  
**现状:** tip 只认 `civitai-28978240-…-seko2`=1；Fal seko2 已作废（Agent 欢迎冒充节点 Composer）；**产品闭环仍 0**。不叫验收。

## 原则（先 API 画布，再 Seko 差距）

1. 只认页↑原参 + 出站对官方 schema + 原镜卡写回（硬刷仍在）+ 真 Seko 同流程成对。
2. 禁 curl generate、禁缩 prompt、禁跨家偷换、禁 Agent 欢迎/modal 冒充节点 dock。
3. 轮换家：Civitai tip 已有 → **下一刀不堆 Civitai**；Fal 作废可另刀收回，但不挡换家。

## Phase 0 — 立刻（本周主线：换家 tip）

| 序 | 家 | 动作 | Done when |
|---|---|---|---|
| 0.1 | **魔搭 AI** | 未用 AIImageStudio 帖 · t2i 页↑原参 · 卡像素=/out+硬刷 · 真 Seko 03底栏+04生成态 | 包路径交 Looper；Pass 默认 False |
| 0.2 | **魔搭 CN** | 同上 | 同上 |
| 0.3 | **Nano** | 同上（注意 prompt 过长 UI 明示、不截断出站） | 同上 |
| 0.4 | **HF** | 有额度才烧；402/无 jobId 诚实 Fail，不假绿 | 同上或诚实阻塞 |
| 0.5 | **Fal tip 收回** | 新未用帖；Seko 必须真节点 Composer dock（禁 Agent 欢迎） | Looper 抬 tip 或作废理由 |

Owner: **civitai 开发** 烧包；**api对接助手** 每刀出站核；**Grok Build** 只修挡刀 bug；**Looper** 记分不派验收。

## Phase 1 — 同家能力补齐（tip 家≥3 后并行）

每家在 t2i tip 站住后：`i2i` → `i2v`（魔搭若官方无视频：文档+UI 明示，不空壳按钮装能发）。  
LoRA/模型搜：只跟当前底模 + 官方 `supportsLora`；null strength 不发明。

## Phase 2 — 智能匹配（六家都能做）

导入 → 原配方全上屏 → **先认人选的家** → 家内可跑模型；找不到明说。  
禁：缩 prompt、默认 Krea2、跳 Fal、跨家偷换。

## Phase 3 — Seko 真功能（API tip 稳住后再加刀）

对照源站：节点有货、Composer 展开/生成态、创作链；配方台另面但匹配也要能跑。  
交付仍要 §7 成对截图；半成品不叫审。

## Anti

- tip/合码/绿测 ≠ 产品验收  
- 假 hardRefresh / 磁盘有文件 / 旧卡像素 ≠ 写回证据  
- 不每刀叫审查；自认无已知 bug、准备交付才叫

## 本回合开干

从 **Phase 0.1 魔搭 AI 未用帖 t2i 闭环包** 起烧；Fal 收回排在换家之后。

## Status 2026-09-17 ~15:23 CST
- tip=**5**（Civitai/魔搭AI/魔搭CN/Nano/Fal）；HF tip=0（402 额度耗尽诚实阻塞 `hf-119393527-t2i-closed-seko`）
- 闭环仍 **0**；≠验收
- Phase 0 tip 主线（除 HF 额度）完成 → **Phase 1**：各 tip 家补 i2i→i2v
