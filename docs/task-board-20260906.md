# 调度任务板（2026-09-06 · 单一事实源）

> 本板由调度派单固化而成，是**当前派单 / 挂账 / 待拍板 / 文件归属的唯一事实源**。
> 引用文件：`dispatch_acceptance_rules.md`(v3，R 组+门序)、`dalao_original_requirements.md`(原话集+D 节)、`../../evidence_void_20260906.md`(作废清单)、`C_six_features_audit.md`、`docs/api-capability-investigation-20260906.md`、`docs/api-capability-落地-20260906.md`。
> 任何派单变更、任务状态翻转、拍板结论，先改本板再动手。板与群聊冲突时以本板 + 大佬原话为准。

---

## 0. 仓库快照（2026-09-06 实测）

| 项 | 值 |
|---|---|
| HEAD = origin | `31fb9ce`（grok G-2+H：catalog 吐 canvas operation、E5 真路由、禁 krea2 偷换，已 push） |
| 权威链 | 工作仓 `work-repo/civitai-studio`；主仓 `/home/ubuntu/work/civitai-studio` = 旧副本（落后多提交），**勿在那边提交** |
| 服务 | `PORT=18772`（工作树源码）。⚠ 现 18772 进程（pid 3986）跑 `31fb9ce` 前旧代码，E5 双路由 404；B commit 后须显式 `PORT=18772` 重启，才可当验收对象 |
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
| **A 包** | gpt-5.6-sol（注：历史上 sol2 曾顶 A，回执时统一身份口径） | ①commit storyboard.js 工作树现有改动（地基）；②A-1 删 `slice(0,60)`×2(:2052/:4647)+`selectedIndex=1` 盲选×2(:2070/:4656)；③E5 前端 `/api/caption`(:104)、`/api/upload-out`(:905) 404 弹用户、拆 `catch(_){}` 静默降级；④E6–E9 按验收清单收口；⑤`/api/whatif` 前端接线；⑥H7 dock 费用（§2 转 A）；⑦画布 sampler/scheduler 的 params + backend 门控（§2 新行，storyboard.js 区） | commit 哈希 + `wc -l` + grep 证据 + `node --check`；A-1 全文件零命中 | @deepseek 进 D 门 |
| **B 收尾** | default | 认领上表 B 文件；server.py canvas 净移植版（923 行，diff +181/−1 六 hunk，保留 :947 E5 双路由）待 D 预审放行即 commit+push，随后另起 storyboard.html 画布 sampler/scheduler 面板 commit（见 §2 新行）；三 TODO（页首 active tab、空项目 addAsset、duplicate 新画布绑旧资产）修掉；E2 持久化桥待 storyboard.js 解锁 | `test_canvas_projects.py` 6/6 exit 0；commit+push 后工作树干净 | @deepseek 进 D 门 |
| **G-2 + H 系** | grok | ✅ 已交付（`31fb9ce` 已 push）：civitai.py catalog 吐 operation（H1/H2）、cameraAngle（H3）、H6 find_service 失败 400 禁 krea2 偷换、H8 `/api/providers` 带 CAPS、E5 `/api/caption` + `/api/upload-out`、modelscope/nanogpt 401 反空壳、H5 缓存保护；四测试文件 PASS | `31fb9cefe50e04ec13f1cec0b741aaeaf90af0db` + 测试原样输出 | 已交付无下一棒；新活 = graph_compile 白名单两 key（§2 新行） |
| **D 门预审** | deepseek（只读） | 对工作树两份未 commit diff 预审扫雷：server.py canvas 净移植（923 行 / diff +181/−1 六 hunk）、storyboard.js A 区 697 行；civitai.py 已随 `31fb9ce` 进 origin 不预审 | 「文件:行号」预审驳回书 | 放行序 = **B 先 commit server.py、A 再 commit storyboard.js**；驳回明细回对应写手；A/B push 后开正式 D 门 |
| **E 门** | glm-5.3-flash | 装好 playwright 后对 18772 基线全量点击遍历：每按钮/下拉/tab/弹窗点到底，前后截图+URL+控制台报错+失败请求 | 基线问题清单；禁抽样 | 清单交终审；A/B commit 后终验 |
| **F 门预备** | pi（只读） | ①9333 源站 `src_gt_*` 同尺寸同帧对照基准清单；②复查 storyboard.js/HTML 是否再引入未证素材或机器人文案（grep 证据） | 对照基准清单 + grep 证据 | E 门一交图即逐屏对照 |
| **任务卡固化** | 代码 | 本板落盘 docs/ 并 commit | 本文件 commit 哈希 | 全房间以此为单一事实源 |

**缺口登记（条件未到不派）**：无（E 门已补 glm-5.3-flash）。

---

## 2. 挂账洞 / 未清技术债

| 项 | 位置 | 说明 | 认领 |
|---|---|---|---|
| modelscope whatif 401 假阳性 ✅已销 | `providers/modelscope.py:493` | 未知模型 200 放行、hub_unreachable 降级 | grok（随 `31fb9ce`） |
| nanogpt whatif 空壳 ✅已销 | `providers/nanogpt.py:1012` | 不在 G 派单范围，任务池挂账 | grok（随 `31fb9ce`：whatif 真校验非常量 return） |
| t2v 缺 OP_SPEC | H4 | catalog 无 t2v 声明 | grok H 系 |
| Nano 文本目录 0 条 ✅已销 | H5 | 失败缓存空 | grok（随 `31fb9ce`：失败不覆盖缓存） |
| dock 费用写死 7/10/18 | H7 | 不调 whatif；dock 在 storyboard.js = A 独占区 | **A 包前端**（gpt-5.6-sol，自 grok 转派） |
| 前端从未调 `/api/whatif` | `static/storyboard.js` grep 0 命中 | G 的真校验用户不可见 | A 包接线 |
| i2v/Fal 素材来源未证 | 账本 `28216428` 作废，其余 6 条「未验证」 | 真链路技术成立、素材未证 | 补证后重估 |
| **画布未接 sampler/scheduler（能力躺着，产品从未接线）** | storyboard.js:1465-1473（params 只塞 serviceId/resolution/duration）/ storyboard.html:238-255（面板无控件）/ graph_compile.py:380（透传白名单丢 key） | 后端链完整：civitai.py SAMPLERS 31 / SCHEDULERS 7（含 beta）、defaults_payload 吐 defaults、生成时 :607-610 消费、:660-667 白名单在列；对照 index.html 配方台已接（:2246 随请求、:2292-2299 非 civitai 剔除、:3669 下拉填值）——画布从未接上。大佬「模型有的能力帮我完善」= 源站能力禁删、只完善。验收口径：画布发起生成 payload 实际含所选 sampler（禁死 UI；列表值源 `/api/defaults` 禁手抄；预选 DEFAULTS 的 er_sde/sgm_uniform）；换非 civitai 后端控件消失、不假支持 | 归属拆三条：grok = graph_compile.py 白名单补 sampler/scheduler 两 key（H4 同文件活跃，勿碰 OP_SPEC）；default(B) = storyboard.html 画布面板加两下拉（先推净 server.py canvas commit 再另起，不污染待审 diff）；gpt-5.6-sol(A) = storyboard.js 带 params + backend 门控（并入已派大包；久不回执则 default 声明认领该小块） |

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

- 所有门**空转**；最近交付 `31fb9ce`（grok G-2+H，已 push）待 D/E 门；modelscope/nanogpt 旧洞已随该 commit 销（见 §2）。
- 下一触发：**A 包 commit** 与 **B 收尾 commit** → D 预审结论 → 正式 D 门 → E 门（glm-5.3-flash 基线遍历先行）→ F 门 → 终审 Ekko。
- 变更记录：本板 v1 = default 派单（gpt-5.6-sol A / grok G-2+H / deepseek D 预审 / glm-5.3-flash E / pi F / 代码任务卡）固化。
- 变更记录：v2（17:13 大佬令重派）——实测工作树活跃写入区 = `providers/*`（civitai/fal/hf/modelscope/nanogpt/__init__/catalog_ops/media_io，17:07–17:11 连续改动）+ `server.py`（17:12 后仍在变）= **grok 密集推进区，不派新写手、不 commit、不围观**；`static/storyboard.js` 自 15:46 静止 → A 包（gpt-5.6-sol）开工令重申（先 commit 现有改动→A-1→E5 前端；A-2 等 grok catalog）；`nanogpt.py` 归属待代码声明（grok ④亦列此洞，禁双写）；pi F 门预备只读可推进 + 账本文档单独 commit；glm-5.3-flash 修基线截图 md5 雷同；**审查门（D/E/F/C）无新 commit 不叫**。
