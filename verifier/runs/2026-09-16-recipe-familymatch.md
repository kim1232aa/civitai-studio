# 2026-09-16 配方台家族匹配 + 画布导入入口 + stub 行隐藏

## 背景

用户截图反馈四连：NanoGPT 被砍 / 模型砍少 / 导入报「Only HTML requests are supported here」/
配方台不能匹配 / 画布没有导入。逐项定案与修复。

## 定案

| 反馈 | 结论 |
|---|---|
| 配方台无 NanoGPT pill、模型少 | 用户截图为旧构建（v0802；HEAD 为 v0776 之后多个版本）。当前 HEAD 实测 6 家 pills 齐全（含 Nano），各家目录完整：fal 1492 / nano 392 / ms-ai 332 / ms-cn 332 / hf 29 / civitai 304。server 对 HTML/JS 已发 no-store。 |
| 导入报 Only HTML requests | 旧构建问题。当前 HEAD 实测 `POST /api/import {backend:fal, q:https://civitai.red/images/136863587}` → 200，完整配方铺开（prompt/负面/宽高/步数/CFG/seed/LoRA/AIR 齐全）。 |
| 配方台不能匹配 | **真 bug**：resolveExactHubFromImport 只有 Hub 精确 id 匹配 + 小白名单，krea2 帖子在 Fal 家落空，而 fal-ai/krea-2/turbo 明明在目录。 |
| 画布没有导入 | **入口隐蔽**：弹层/URL 导入/家内匹配早已存在（⇪ 工具栏），用户找不到。 |

## 改动

1. static/index.html：
   - 引入 `/static/smart-family-match.js`（与画布同源的家族匹配模块）。
   - applyImport 非 Civitai 分支：精确 Hub 匹配落空后 → SmartFamilyMatch.familyFromImport
     识别底模家族 → pickByFamily 在当前家目录内匹配（fits 内卡 it.backend===当前家，
     防 §3.2 跨家混入）；命中明示「按底模家族 X 匹配到 Y（非精确 id）」，落空维持诚实明说并附家族名。
2. static/storyboard.html：Composer 动作区新增「导入」按钮（btnImportPost）打开导入弹层。
3. static/storyboard.js：绑定 btnImportPost → openImportModal；stub 模式给 dock 加
   .stub-mode 类。
4. static/storyboard-shell.css：.dock.stub-mode 隐藏模型行/LoRA 行/高级参数
   （文本/音频本版未接，杜绝空下拉误读），切回图片/视频自动恢复。

## 验证（页面级真机）

| 项 | 结果 |
|---|---|
| 配方台 6 家 pills | Civitai/Fal/HF/魔搭AI/魔搭CN/Nano 全渲染 ✓ |
| 配方台各家目录行数与属主 | civ 44 行 / fal 61 / hf 7（全 HF 属主）/ ms-ai 44 / ms-cn 44 / nano 61，无跨家混入 ✓ |
| 配方台 Fal 家导入 civitai.red/136863587 | 「按底模家族 krea2 匹配到 Krea 2 Turbo」→ 已选 fal-ai/krea-2/turbo，prompt 铺开 ✓ |
| 画布 Composer 导入按钮 | 存在、点开弹层 ✓ |
| 画布 URL 导入同链接 | 「已智能匹配文生图 · krea2 · fal-ai/krea-2/turbo · 15 节点 Comfy」✓ |
| 文本 stub 模式 | 模型行隐藏 + 「文本生成 · 本版未接」；切回图片恢复 ✓ |
| 无 pageerror | ✓ |

## 回归

node --check storyboard.js OK · o133 PASS · o58/o59 PASS · graph 75/75（带代理）· UI eval 32/32。
