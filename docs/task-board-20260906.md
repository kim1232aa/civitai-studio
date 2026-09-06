# 调度任务板（2026-09-06 · 单一事实源）

> 本板由调度派单固化而成，是**当前派单 / 挂账 / 待拍板 / 文件归属的唯一事实源**。
> 引用文件：`dispatch_acceptance_rules.md`(v3，R 组+门序)、`dalao_original_requirements.md`(原话集+D 节)、`../../evidence_void_20260906.md`(作废清单)、`C_six_features_audit.md`、`docs/api-capability-investigation-20260906.md`、`docs/api-capability-落地-20260906.md`。
> 任何派单变更、任务状态翻转、拍板结论，先改本板再动手。板与群聊冲突时以本板 + 大佬原话为准。

---

## 0. 仓库快照（2026-09-06 实测）

| 项 | 值 |
|---|---|
| HEAD = origin | `8698ca6`（claude2 G commit：三家 whatif 真校验，已 push） |
| 权威链 | 工作仓 `work-repo/civitai-studio`；主仓 `/home/ubuntu/work/civitai-studio` 落后 8 提交的旧副本（`f77aa0f` 是 `8698ca6` 祖先，非旁支），**勿在那边提交** |
| 服务 | `PORT=18772`（工作树源码，含 canvas 路由），根 / storyboard.html / api/catalog 200 |
| 环境陷阱 | shell `PORT=8648` 是污染值（Hermes Web UI 端口），起服务显式 `PORT=18772` |
| PR #4 | 冻结中；解冻 = D/E/F 三门 + 终审全过后由终审 @ 调度合 PR |

### 工作树文件归属（commit 前认领表，禁 `git add -A`）

| 文件 | 归属 | 内容 |
|---|---|---|
| `static/storyboard.js` | **A 包**（独占写权） | A-0 清零 + E 系新接线（capabilityForCatalogItem/captionFromAsset/renderServiceMeta/fetch /api/caption /api/upload-out） |
| `providers/civitai.py` | **grok** | 85 行能力元数据 + match_service 重构/operation 字段（A-2 前置） |
| `server.py` | **B (default)** 为主；grok 若有 H 系改动须声明分块 | canvas 六路由 + match_service 相关；串行锁：一次一人 |
| `static/storyboard.html` | **B (default)** | canvas-manager 面板 + 三态真按钮 + 标题去机器人 |
| `canvas_store.py` / `static/canvas_manager.js` / `scripts/test_canvas_projects.py` / `scripts/test_canvas_manager_js.js` | **B (default)** | 画布管理后端/前端/测试（test 6/6 绿） |
| `dispatch_acceptance_rules.md` / `dalao_original_requirements.md` / `docs/api-capability-*.md` | 文档类（pi/Claude 系维护） | 不裹进代码 commit |
| `.gitignore` | 归属未定 | commit 前声明 |

---

## 1. 本轮派单（调度：default，按能力拆，无人过重）

门序（v3，E 门人位已更新）：写码(A/B) → **D** deepseek 只读对抗 → **E** glm-5.3-flash 点击验收 → **F** pi 视觉验收 → **C/终审** Ekko → 收单/合 PR。任一门驳回退回原作者；不 commit 不算交付。

| 任务 | 负责人 | 内容 | 验收标准 | 交接 |
|---|---|---|---|---|
| **A 包** | gpt-5.6-sol（注：历史上 sol2 曾顶 A，回执时统一身份口径） | ①commit storyboard.js 工作树现有改动（地基）；②A-1 删 `slice(0,60)`×2(:2052/:4647)+`selectedIndex=1` 盲选×2(:2070/:4656)；③E5 前端 `/api/caption`(:104)、`/api/upload-out`(:905) 404 弹用户、拆 `catch(_){}` 静默降级；④E6–E9 按验收清单收口 | commit 哈希 + `wc -l` + grep 证据 + `node --check`；A-1 全文件零命中 | @deepseek 进 D 门 |
| **B 收尾** | default | 认领上表 B 文件 commit+push；三 TODO（页首 active tab、空项目 addAsset、duplicate 新画布绑旧资产）修掉；server.py 视 grok 声明整提或分块；E2 持久化桥待 storyboard.js 解锁 | `test_canvas_projects.py` 6/6 exit 0；commit+push 后工作树干净 | @deepseek 进 D 门 |
| **G-2 + H 系** | grok | ①commit `providers/civitai.py`（A-2 依赖）；②E5 后端补 `/api/caption`（真视觉打标走 providers）、`/api/upload-out`（真落盘返 URL）——前端已接线只差后端；③H8 `/api/providers` 带 CAPS、H6 civitai 失败静默改打 krea2；④modelscope 401 假阳性 + nanogpt 空壳能收就收 | commit 哈希 + 测试原样输出；E5 双路由在 server.py grep 命中 | @deepseek 进 D 门 |
| **D 门预审** | deepseek（只读） | 对工作树三份未 commit diff（storyboard.js E 系接线 / server.py canvas+match_service / civitai.py 704 行）做预审，写手 commit 前扫雷 | 「文件:行号」预审驳回书 | 驳回明细回对应写手；A/B commit 后开正式 D 门 |
| **E 门** | glm-5.3-flash | 装好 playwright 后对 18772 基线全量点击遍历：每按钮/下拉/tab/弹窗点到底，前后截图+URL+控制台报错+失败请求 | 基线问题清单；禁抽样 | 清单交终审；A/B commit 后终验 |
| **F 门预备** | pi（只读） | ①9333 源站 `src_gt_*` 同尺寸同帧对照基准清单；②复查 storyboard.js/HTML 是否再引入未证素材或机器人文案（grep 证据） | 对照基准清单 + grep 证据 | E 门一交图即逐屏对照 |
| **任务卡固化** | 代码 | 本板落盘 docs/ 并 commit | 本文件 commit 哈希 | 全房间以此为单一事实源 |

**缺口登记（条件未到不派）**：无（E 门已补 glm-5.3-flash）。

---

## 2. 挂账洞 / 未清技术债

| 项 | 位置 | 说明 | 认领 |
|---|---|---|---|
| modelscope whatif 401 假阳性 | `providers/modelscope.py:493` | 未知模型 200 放行、hub_unreachable 降级 | grok（本轮可选） |
| nanogpt whatif 空壳 | `providers/nanogpt.py:1012` | 不在 G 派单范围，任务池挂账 | 未认领 |
| t2v 缺 OP_SPEC | H4 | catalog 无 t2v 声明 | grok H 系 |
| Nano 文本目录 0 条 | H5 | 失败缓存空 | grok H 系 |
| dock 费用写死 7/10/18 | H7 | 不调 whatif | grok H 系 |
| 前端从未调 `/api/whatif` | `static/storyboard.js` grep 0 命中 | G 的真校验用户不可见 | A 包接线 |
| i2v/Fal 素材来源未证 | 账本 `28216428` 作废，其余 6 条「未验证」 | 真链路技术成立、素材未证 | 补证后重估 |

## 3. 待大佬拍板清单（不拍不动的冻结项）

1. **16 张 jpg**（`static/demo-*.jpg`×4 + `light-preset-01..12.jpg`×12）：现冻结留盘（R3-a），清仓 or 保留等一句令；
2. **画面切分**：本地切块 ≠ 源站生成式（C 清单 🟥），补生成式 or 接受降级；
3. **front/back 打光口径**：`_unsupported` vs 显式抛错 vs 映射 prompt；
4. **光源球**：是否须 WebGL 3D；
5. **C7 胶囊**：是否像素级对齐；
6. **源站截图有效性**：Claude 判保留（9333 `src_gt_*` 有效；指向我方 UI 旧截图作废）；
7. **PR #4**：三门 + 终审全过前不解冻。

## 4. 纪律（全房间）

- 不 commit 不算交付；交付 = commit 哈希 + `wc -l` + grep 证据 + 测试原样输出 + push 后 clean；
- commit 前 `git diff --cached` 核对；禁 `git add -A`（前科 `26da7f3`）；
- 谁动哪个文件先在群里声明认领；`static/storyboard.js` 一次只准一人动；server.py 串行锁；
- 机器人素材/未证 prompt 禁令（R1–R5）不随本板变化，见 `dispatch_acceptance_rules.md`；
- 两轮无进展越棒记账；干完同条消息 @ 下一棒写清交接。

## 5. 当前状态机

- 所有门**空转**（无新交付物进门）；最近 G commit `8698ca6` 已过 D（fal/hf），modelscope 有洞（见 §2）。
- 下一触发：**A 包 commit** 与 **B 收尾 commit** → D 预审结论 → 正式 D 门 → E 门（glm-5.3-flash 基线遍历先行）→ F 门 → 终审 Ekko。
- 变更记录：本板 v1 = default 派单（gpt-5.6-sol A / grok G-2+H / deepseek D 预审 / glm-5.3-flash E / pi F / 代码任务卡）固化。
- 变更记录：v2（17:13 大佬令重派）——实测工作树活跃写入区 = `providers/*`（civitai/fal/hf/modelscope/nanogpt/__init__/catalog_ops/media_io，17:07–17:11 连续改动）+ `server.py`（17:12 后仍在变）= **grok 密集推进区，不派新写手、不 commit、不围观**；`static/storyboard.js` 自 15:46 静止 → A 包（gpt-5.6-sol）开工令重申（先 commit 现有改动→A-1→E5 前端；A-2 等 grok catalog）；`nanogpt.py` 归属待代码声明（grok ④亦列此洞，禁双写）；pi F 门预备只读可推进 + 账本文档单独 commit；glm-5.3-flash 修基线截图 md5 雷同；**审查门（D/E/F/C）无新 commit 不叫**。
