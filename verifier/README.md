# Verifier 索引(append-only)

| 版本 | 创建时间 | 测量内容 | 与上一版差异 |
|---|---|---|---|
| v1 | 2026-09-13 23:55 | 六家生成能力(A)、参数一致性(B)、搜索(C)、帖子智能匹配(D)、持久化(E)、画布体验(F)、测试纪律(G) | 首版,源自需求.txt 全文 |

## 最近提交

| 提交 | 内容 |
| --- | --- |
| 766fefe | 四缺口修复 + 魔搭视频诚实化 + 测试裁决 + verifier 体系（39→61 绿零回归） |
| 1bec2fb | Stage3 真机验收的 4 个页面 bug 修复 + 验收记录 |
| 1c64934 | round2 三连修：NanoGPT 双字段超cap / Civitai 档位token / Fal别名越权 |
| 4e4739b | t2v 端到端补全（graph_compile t2v op + 前端 op 对齐）+ Fal official_fields 收紧 |
| ccc2c77 | round2 驱动：卡面 .result-error 检测 + 硬拒重发语义 |
| 10a3dd9 | NanoGPT 视频状态嵌套解析修复 + 智能匹配覆盖手选模型(uservspick)修复 + t2v 三家实发验证 |
| 9c991b8 | Seko 对齐第一轮：LoRA 面板默认收起 + 模型单元紧凑化 + P0 对照差距清单入库 |
| d411e8b | 配方台家族级智能匹配 + 画布 Composer 导入入口 + stub 模式隐藏模型行 |
| cfed198 | Seko 对齐第二轮：模型 pill+弹层 / 白描边⊕选中态 / 缩放条并入小地图 + 导入弹层补样式、破图降级、45s 超时 |

## runs 目录
每次验证运行追加一条记录: 时间、命令、exit code、产出文件、结论(pass/fail + 证据路径)。
| 本轮运行记录 | 2026-09-14 04:00 | 离线单测全量回归(81 测试): 39→61 绿, 零回归; 四缺口修复 + 后端诚实化 | 见 runs/2026-09-14T0400-offline-regression.md · 766fefe |
| 本轮运行记录 | 2026-09-14 Stage3 | 真机验收 4 个页面 bug + 六家点选 A5/6 D F | 见 runs/2026-09-14-stage3-live.md · 1bec2fb |
| 本轮运行记录 | 2026-09-14 round2 | 九用例收官：civ/fal/nano i2i+i2v 实片、ms 诚实硬拒、hf-t2i 硬拒→重发出图、nano 视频目录、LoRA 不匹配硬拒 | 见 runs/2026-09-14-round2-live.md · 4e4739b/ccc2c77 |
| 本轮运行记录 | 2026-09-14 t2v 回归 | graph 75/75 · UI 32/32 · o42 38 · nano 契约 106 · fal 契约 OK | 见 runs/2026-09-14-t2v-regression.md |
| 本轮运行记录 | 2026-09-15 nano-t2v | 状态嵌套修复后两单历史任务回收落盘 + nano-t2v 页面点击全链路 ok（400s 出片硬刷保持）；回归全绿 | 见 runs/2026-09-15-nano-t2v-status-fix.md · 10a3dd9 |
| 本轮运行记录 | 2026-09-15 Seko 对齐 r1 | LoRA 折叠 + 模型单元紧凑化；UI 32/32 · graph 75/75 · o133/o58/o59 全绿；对照截图建清单 | 见 runs/2026-09-15-seko-align-round1.md · 9c991b8 |
| 本轮运行记录 | 2026-09-16 配方台/画布 | 配方台家族匹配（krea2→fal-ai/krea-2/turbo 页面实测）+ 画布导入入口 + stub 行隐藏；回归全绿 | 见 runs/2026-09-16-recipe-familymatch.md · d411e8b |
| 本轮运行记录 | 2026-09-16 Seko 对齐 r2 | 页面级 18/18（pill 弹层/白描边⊕/缩放合并/导入卡样式/破图降级/超时）· UI 32/32 · graph 75/75 | 见 runs/2026-09-16-seko-align-round2.md |
