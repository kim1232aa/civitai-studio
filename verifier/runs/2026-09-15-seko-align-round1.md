# 2026-09-15 Seko 对齐第一轮：LoRA 折叠 + 模型单元紧凑化

## 背景

P0（用户最高优先级）：UI/逻辑对齐 seko.sensetime.com。本轮先拍现站对照截图建清单，
再做第一批差距修复。对照截图：/mnt/agents/work/verify/seko-align/
（seko-01/02/04/05 vs ours-01/02/04/05，1920x1080 同视口）。

## 改动

- static/storyboard.html：lora-hd 增加折叠开关 #loraFold（aria-expanded/aria-controls），
  lora-row 加 id；loraBlock 初始带 .lora-mini。
- static/storyboard.js：syncLoraUi 接入 applyLoraFold——默认收起；有 LoRA 芯片或
  不匹配告警时自动展开（不藏状态）；手动开关会话级优先（loraFoldOpen）。
  bindLoraUi 绑定开关点击。
- static/storyboard-shell.css：.lora-mini 收起提示/搜索行/命中/芯片（标题行常显）；
  模型单元紧凑化（#serviceFilterLbl 视觉隐藏保留 a11y、搜索框 92px、后端/模型自适应）。

## 验证

| 项 | 结果 |
|---|---|
| node --check static/storyboard.js | OK |
| test_o133_family_smart_match | PASS |
| run_ui_eval（1440x900） | 32/32 PASS（含「parameter visibility gate preserved」×2） |
| test_storyboard_graph（带代理） | 75/75（首跑 73/75 系 ~/.config 被基础设施清空 + Civitai 活样本 404 抖动，env_up.sh 恢复后全绿） |
| test_o58_composer_caps / test_o59_composer_prompt | PASS |
| 人工截图比对 ours-01 | LoRA 收起为单行「▸ LoRA」，模型行单行排布，Composer 高度明显下降 |

## 已知剩余差距

见 docs/HANDOFF-20260914.md §2 P0 对照清单（Composer 底排并单排、模型 pill 弹层、
节点选中描边/连线柄、缩放条一体形态、右侧 AI 助手面板决策）。
