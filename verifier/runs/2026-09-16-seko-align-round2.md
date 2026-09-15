# 2026-09-16 Seko 对齐第二轮 + 导入弹层修复

## 范围
- P0-1/P0-2：Composer 模型单元 → Seko 式单 pill（`#svcPill`）+ 上弹层（`#svcPop`，
  内含六家后端 select、搜索、`#service` size=8 列表、能力徽标、目录分页条）。
  **控件原 id 全部保留，既有 JS 逻辑零改动**；新增 `syncSvcPill()` 同步 pill 文案
  （renderServiceOptions 两处 + sekoRow change 委托 + 初次绑定），点外/Esc/选中自动关层。
- P0-3：`.card.sel` 白色 2px 描边 + 左右白色 ⊕ 连线柄（18px，::after「+」，
  覆盖 `.port` 的 `background:#5ee0c5!important`）。
- P0-4：缩放条并入左下小地图组合条（left 14 / bottom 126，深色胶囊；
  覆盖旧 `left:50%!important + translateX(-50%)` 需 `transform:none!important`）。
- 导入弹层（用户「空壳/附件显示有问题」反馈）：
  - 根因：`.import-grid/.import-card/.ibadge/.icheck/.import-tabs/.import-filters/.icap/.iph`
    此前**完全无 CSS**，按钮裸渲染成灰盒。本轮补齐全部样式。
  - 素材卡底部常驻名称条；img/video `onerror` → `.no-thumb` 斜纹占位 + 标题（破图不再误导）；
    img `loading="lazy" decoding="async"`。
  - `runImportFromUrl` 增加 45s AbortController 超时 + 明示文案 + 按钮 finally 复位。
  - 「导入参数」title 明示只取参数不挂附件。

## 验证（页面级，playwright，18832 实例）
脚本：/mnt/agents/work/verify/seko_round2_verify.mjs（副本 .tmp_seko_round2_verify.mjs 跑完即删）
截图：/mnt/agents/work/verify/seko-round2/01~04

| 项 | 结果 |
|---|---|
| svcPill 存在 / 初始文案「选择模型 ▾」 | PASS |
| 点击开弹层（含 backend/filter/service 三控件） | PASS |
| fal 目录加载 options=960 | PASS |
| 选 Nano Banana 2 → pill 文案「Fal · Nano Banana 2」+ 弹层自动关 | PASS |
| Esc 关弹层 | PASS |
| 选中节点白描边 rgb(255,255,255) 2px | PASS |
| 白色⊕手柄 18px rgb(255,255,255) | PASS |
| 缩放条 left=14 与小地图对齐、正上方 gap=10px | PASS |
| Composer「导入」开弹层 | PASS |
| 素材卡 84 张 grid 布局、圆角、角标、名称条 | PASS |
| 注入破图 → no-thumb 降级占位可见、img 摘除 | PASS |
| runImportFromUrl 含 45s AbortController + 超时文案 | PASS |

**合计 18/18 通过**（首轮 3 失败：port 白柄被旧 !important 规则压、zoom translateX 未清、
破图注入撞上异步重渲染——前两项修真规则冲突，第三项修测试时序，复跑全绿）。

## 回归
- node --check static/storyboard.js OK
- UI eval 32/32 PASS
- graph（test_storyboard_graph.py，走代理）75/75 PASS
- test_io_meta / test_e5_media_io / test_lora_air_resolve / test_air_map PASS
- test_import_meta FAIL = 既有环境问题（/tmp/civitai-img fixture 缺失 + 需代理），
  stash 本批改动后同样失败 → 非本轮回归。
- 配方台（index.html）：6 家 pills 齐（Civitai/Fal/HF/魔搭AI/魔搭CN/Nano），
  SmartFamilyMatch 已加载，无 pageerror。

## 安全
- 本批改动仅 static/storyboard.{html,js,css} + docs + verifier，无密钥；
  commit 前已 grep 暂存 diff（sk-nano-/hf_/github_pat/ms-b6/29d62265/a437ae76/438a74c5/
  EbPvBusV/018bbb1d/eyJhbGci）零命中。
