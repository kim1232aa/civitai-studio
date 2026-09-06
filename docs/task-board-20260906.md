# 调度任务板（2026-09-06 · 单一事实源）

> 本板由调度派单固化而成，是**当前派单 / 挂账 / 待拍板 / 文件归属的唯一事实源**。
> 引用文件：`dispatch_acceptance_rules.md`(v3，R 组+门序)、`dalao_original_requirements.md`(原话集+D 节)、`../../evidence_void_20260906.md`(作废清单)、`C_six_features_audit.md`、`docs/api-capability-investigation-20260906.md`、`docs/api-capability-落地-20260906.md`。
> 任何派单变更、任务状态翻转、拍板结论，先改本板再动手。板与群聊冲突时以本板 + 大佬原话为准。

---

## 0. 仓库快照（2026-09-06 实测）

| 项 | 值 |
|---|---|
| HEAD = origin | `dd38e2a`（链：`31fb9ce`→`95e2ec3`→grok `bdb0a87`+H4 `9e18203`→板 v4 `210dbc1`→**B `50ac1f8`**→**A-0 `2f29bf2`**→板 v6 `ca487eb`→**A2+P1 `626304a`**（storyboard.js：sampler 接线+nanogpt enrich 真数据）→**B html 壳 `dd38e2a`**（sampler/scheduler 两下拉静态壳，与 js `:1428` 契约同形），均已 push，D 增量+E 增量 s6-s8 双门通过） |
| 权威链 | 工作仓 `work-repo/civitai-studio`；主仓 `/home/ubuntu/work/civitai-studio` = 旧副本（落后多提交），**勿在那边提交** |
| origin/main 另线 | `46b5544`（kim1232aa：v0791–v0793 prompt node/reverse toolbar/text gen，仓库主另线推进，与 PR #4 分支并行）；PR 分支 `feat/v0794-prompt-nodes` origin 端=`dd38e2a`（=本仓 HEAD，ls-remote 无漂移）；合 PR 时若 main 已漂移，终审留意合并策略 |
| 服务 | `PORT=18772`（工作树源码；server.py `2f29bf2` 起，`2f29bf2→dd38e2a` 零改动故未重启，静态按磁盘现读=`dd38e2a`）。served md5 与 origin `dd38e2a` 三文件逐字一致（E 增量前置核验 + 调度 re-curl 双证）＝ A2 批次 D/E 增量验收对象 |
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
| **A 包** | gpt-5.6-sol（注：历史上 sol2 曾顶 A，回执时统一身份口径） | ①commit storyboard.js 工作树现有改动（地基）；②A-1 删 `slice(0,60)`×2(:2052/:4647)+`selectedIndex=1` 盲选×2(:2070/:4656)；③E5 前端 `/api/caption`(:104)、`/api/upload-out`(:905) 404 弹用户、拆 `catch(_){}` 静默降级；④E6–E9 按验收清单收口；⑤`/api/whatif` 前端接线；⑥H7 dock 费用（§2 转 A）；⑦画布 sampler/scheduler 的 params + backend 门控（§2 新行，storyboard.js 区） | commit 哈希 + `wc -l` + grep 证据 + `node --check`；A-1 全文件零命中 | ✅ A-0 `2f29bf2` D 放行（**含 P1**：`capabilityForCatalogItem` `:1805` join 对 nano-gpt 键域零命中、声明对主 backend 账面不符，civitai 144/144 命中不受影响）；**新派单（冻结已解）＝A2+P1 同批**：sampler params 收集+门控（非 civitai 控件消失）+ nano-gpt join 按 `docs/api-capability-落地-20260906.md:124` `supported_parameters` overlay 修，禁拿 civitai `raw.id` 蹭；依赖缺服务端点则**声明给 B 补**，勿碰 server.py/providers/*；与 B 两下拉合批走 D 复审+E 增量 s6-s8（deepseek 补记：slice(0,60) `:2052` 并入①核验范围）；✅ **A2+P1 `626304a` 已交付**（base=板 v6 `ca487eb`，单文件 storyboard.js +94/−12，node --check OK）＋**D 增量通过**＋**E 增量 s6-s8 通过**；A 包后续清单（A1/A3/①slice ②盲选 ③op 下拉 ④E5 拆 catch ⑤whatif ⑥H7 dock 费用）逐条另起 commit |
| **B 收尾** | default | ✅ `50ac1f8` 已交付：server.py canvas 净移植（923 行，diff +181/−1 六 hunk，保留 :947 E5 双路由）+ PUT 整状态替换真实现 + canvas_manager.js saveState 完整三件套 + strict FakeServer 测试；**新派单（冻结已解）**：storyboard.html 画布 sampler/scheduler 两下拉（§2 行 62，值源 `/api/defaults`、预选 er_sde/sgm_uniform），与 A2 **同批交付**（js 先读/html 后落会造成死下拉中间态被 E 打回）；三 TODO（页首 active tab、空项目 addAsset、duplicate 新画布绑旧资产）+ E2 持久化桥待 storyboard.js 解锁仍挂账 | `test_canvas_projects.py` 7/7 exit 0（含 PUT 整替换断言）+ `test_canvas_manager_js.js` OK；push 后工作树仅余未跟踪基准文档 | ✅ `50ac1f8` D **通过无保留**；✅ **B html 壳 `dd38e2a` 已交付**（storyboard.html +1 行，纯静态零逻辑，与 js 契约逐字同形）＋**D 增量通过**＋**E 增量 s6-s8 通过**；三 TODO（页首 active tab、空项目 addAsset、duplicate 绑旧资产）+E2 持久化桥仍挂账 |
| **G-2 + H 系** | grok | ✅ 已交付：`31fb9ce`（catalog 吐 operation H1/H2、cameraAngle H3、H6 禁 krea2 偷换、H8 CAPS、E5 `/api/caption`+`/api/upload-out`、modelscope/nanogpt 401 反空壳、H5 缓存保护）；✅ graph_compile 白名单透传（`bdb0a87`：t2i/i2i/i2v 补 sampler/scheduler，无 key 不发明默认）；✅ H4 t2v（`9e18203`：OP_SPEC 接 t2v、文生视频禁改打 i2v）；六个测试文件 PASS | `31fb9cefe50e04ec13f1cec0b741aaeaf90af0db` + `bdb0a873334ae6071f55d969a2aa9d8ea54462a5` + `9e182030d49f3da78f57ba49dfa2d27ca5c86ad2`（origin=HEAD）+ 测试原样输出 | 已交付无下一棒；画布接线剩余两截归 B/A（§2 行 62） |
| **D 门（预审+正式）** | deepseek（只读） | 预审：工作树两份未 commit diff（server.py canvas 净移植 923 行、storyboard.js A 区 697 行）；正式 D：复审 `50ac1f8`+`2f29bf2` 两 commit（PUT 分支+store update_state+capabilities 接线；live 探针全过、node --check 补跑） | 裁定书：「文件:行号」驳回明细 | ✅ 正式 D 裁定完成（2026-09-06）：B `50ac1f8` **通过无保留**、A `2f29bf2` **放行含 P1**（`:1805` join nano-gpt 键域零命中＝账面不符非造假，归 A2 修）；**A2 批次落地时实证 nano-gpt constraints 真驱动 vs 空兜底**，D 增量复审；✅ **D 增量复审 `dd38e2a` 通过、无驳回项**（B 壳契约逐字同形；A2 四件套门控三模式全封死：text 走 generateFromText、video 恒 `{}`；P1 enrich 384/384 ops 保住、referenceLimit 228 命中、civitai 304 零回归——旧算法同数据确实清零=修复真实；机械门 node --check+7 测试套全 EXIT=0；md5 三角 served=worktree=origin）。**三条记档不阻塞**：①fal/nano compile 层 sampler/scheduler verbatim echo（JS 门控已挡，现网无传递路径）归 A 包② ②loadCatalog slice(0,60) `:2140` 归 A 包① ③探针 27/28 假 FAIL 系口径错（bernini-r-video 声明 t2v/i2v、探针按 t2i 核）防误报；此后任何新哈希须重走 D 复审 |
| **E 门** | glm-5.3-flash | 对 18772 = origin `2f29bf2` 服务全量点击遍历（禁抽样，CSS selector）：每按钮/下拉/tab/弹窗点到底，前后截图（stableShot，md5 互异）+URL+控制台报错+失败请求 | 基线问题清单 | ✅ **正式 E 门通过（2026-09-06，glm-5.3-flash）**：对象=18772=origin `2f29bf2`，md5 3/3 与 origin 一致非工作树冒充；终轮 **11/11 全绿**（首轮 23/27 的 4 FAIL——putFull=400/svc 空首项/快照雷同/console 400——逐一根因排查**全坐实为探针口径**，产品行为正确）；项目 CRUD/PUT 整替换/capabilities civitai 144/144 join/backend 6/6/mode 三键/dock 逻辑/诚实报错/三 tab/DOM+文件快照 8/8 md5 互异/零 pageerror/零付费触发；无驳回项；产物 `temp/egate-accept/`；✅ **E 增量 s6-s8 对 `dd38e2a` 通过 22/22 无驳回**（2026-09-06）：s6 backend 6/6 遍历 civitai 唯一显现+compile body 实捕 `sampler=er_sde/scheduler=sgm_uniform`、fal/nano-gpt/modelscope-ai/modelscope-cn/huggingface 五后端 hidden+无 key；s7 mode 三态 text（自动切 nano-gpt）无 key / image（civitai）带 key / video 无首帧 `#send` 禁用=真门控（修正断言验证禁用本身，非产品 FAIL）；s8 boot 填值 31/7、预选 er_sde/sgm_uniform（值源 `/api/defaults`）、改选 euler 原样透传、P1「支持 1 个参考」徽标真数据驱动（:1947-1952→:2019，badCount=0）＝nano constraints **真驱动**闭环；pageErrors=0 consoleErrors=0、截图 6/6 md5 互异、清尾 items=0；产物 `temp/egate-dd38e2a-1788693359310/` |
| **F 门预备** | pi（只读） | ①9333 源站 `src_gt_*` 同尺寸同帧对照基准清单（GT 仍断，恢复待大佬拍板①）；②storyboard.js/html 素材/机器人文案**二轮 grep 复查**（可对 `2f29bf2` 做，只读，不影响 A2 批次推进） | grep 证据 | ②已回执（pi：二轮素材/机器人文案 grep 复查完成，详见其群聊回执）；①挂 9333（GT 口径待大佬拍板）；E 门 11/11+增量 s6-s8 已过，F 门全量视觉待口径拍板后对当前 HEAD 执行 |
| **任务卡固化** | 代码 | 本板落盘 docs/ 并 commit | ✅ 板 v6 `ca487eb`；**板 v7=本 commit**（销 A2+P1+B html、录双门增量、HEAD→`dd38e2a`） | 全房间以此为单一事实源 |

**缺口登记（条件未到不派）**：无（E 门已补 glm-5.3-flash）。

---

## 2. 挂账洞 / 未清技术债

| 项 | 位置 | 说明 | 认领 |
|---|---|---|---|
| modelscope whatif 401 假阳性 ✅已销 | `providers/modelscope.py:493` | 未知模型 200 放行、hub_unreachable 降级 | grok（随 `31fb9ce`） |
| nanogpt whatif 空壳 ✅已销 | `providers/nanogpt.py:1012` | 不在 G 派单范围，任务池挂账 | grok（随 `31fb9ce`：whatif 真校验非常量 return） |
| t2v 缺 OP_SPEC ✅已销 | H4 | catalog 无 t2v 声明；OP_SPEC `:61` 接 t2v（`required=["prompt"]`、ins 无 image）、compile `:639` 无 sourceImage/firstFrame、params 塞首帧即拒绝、无 video 能力后端直接报错——文生视频不再改打 i2v | grok（`9e18203`，origin=HEAD） |
| Nano 文本目录 0 条 ✅已销 | H5 | 失败缓存空 | grok（随 `31fb9ce`：失败不覆盖缓存） |
| dock 费用写死 7/10/18 | H7 | 不调 whatif；dock 在 storyboard.js = A 独占区 | **A 包前端**（gpt-5.6-sol，自 grok 转派） |
| 前端从未调 `/api/whatif` | `static/storyboard.js` grep 0 命中 | G 的真校验用户不可见 | A 包接线 |
| i2v/Fal 素材来源未证 | 账本 `28216428` 作废，其余 6 条「未验证」 | 真链路技术成立、素材未证 | 补证后重估 |
| **画布未接 sampler/scheduler（能力躺着，产品从未接线）** | storyboard.js:1465-1473（params 只塞 serviceId/resolution/duration）/ storyboard.html:238-255（面板无控件）/ graph_compile.py:380（透传白名单丢 key） | 后端链完整：civitai.py SAMPLERS 31 / SCHEDULERS 7（含 beta）、defaults_payload 吐 defaults、生成时 :607-610 消费、:660-667 白名单在列；对照 index.html 配方台已接（:2246 随请求、:2292-2299 非 civitai 剔除、:3669 下拉填值）——画布从未接上。大佬「模型有的能力帮我完善」= 源站能力禁删、只完善。验收口径：画布发起生成 payload 实际含所选 sampler（禁死 UI；列表值源 `/api/defaults` 禁手抄；预选 DEFAULTS 的 er_sde/sgm_uniform）；换非 civitai 后端控件消失、不假支持 | 归属拆三条：grok = ✅已销（`bdb0a87`：graph_compile.py 白名单 t2i/i2i `:389-390`、i2v `:599-600` 补 sampler/scheduler；params 无该 key 不发明默认，透传不再丢）；default(B) = storyboard.html 画布面板两下拉（**已派单，冻结已解**：值源 `/api/defaults`、预选 er_sde/sgm_uniform，与 A2 同批交付）；gpt-5.6-sol(A) = storyboard.js params 收集+backend 门控+**P1 join 修复**（**A2+P1 同批已派，冻结已解**，须与 B 两下拉合批走 D 复审+E 增量 s6-s8）**→✅ 已闭环（2026-09-06）：`626304a`+`dd38e2a` 交付，D 增量+E 增量 s6-s8 双门通过，画布 sampler/scheduler 真接线落地** |

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

- 当前门态：B `50ac1f8` **D 通过无保留**、A `2f29bf2` **D 放行含 P1**、**E 门 11/11 通过**（glm-5.3-flash，对 origin `2f29bf2`，md5 3/3，4 FAIL 全坐实探针口径）——**冻结自 E 门收讫（2026-09-06）解除**；A2 批次（`626304a`+`dd38e2a`）**D 增量通过**+**E 增量 s6-s8 22/22 通过**，无驳回。
- 新派单（新 commit 均须重走 D 复审 + E 增量 s6-s8）：gpt-5.6-sol = **A2+P1 同批**（sampler params+门控 + `supported_parameters` overlay 修 nano join，依赖缺服务端点声明给 B 补、勿碰 server.py/providers/*）；default = storyboard.html sampler/scheduler 两下拉（与 A2 同批交付，防死下拉中间态）；pi = 二轮素材 grep 复查回执（只读，**已回执**）；**A2+P1+B html 已销账**（§1）。**后续派单**：gpt-5.6-sol = A 包后续清单逐条另起 commit（A1/A3/①slice ②盲选 ③op 下拉 ④E5 拆 catch ⑤whatif ⑥H7 dock 费用）；default = 三 TODO+E2 持久化桥（待 storyboard.js 解锁）；pi = F 门全量视觉（等 9333 口径）。
- **P1 与 E「nano 0/218 非断链」裁定不矛盾**：E 测 UI 层不空（nano 条目内嵌 supportedOperations 走 `:1864-1886` constraints 路径），D 实读 `:1805` join 对 nano 键域零命中、声明对主 backend 账面不符；闭环＝A2 落地实证 nano-gpt constraints 真驱动 vs 空兜底，D 增量复审+E 增量 s6-s8 一并核。**已闭环（v7）：E 增量 s8 实证徽标「支持 1 个参考」由 referenceLimit 真值驱动（:1947-1952→:2019），nano constraints 真驱动，非空兜底。**
- 下一触发：A 包后续清单（gpt-5.6-sol）逐条另起 commit → 各哈希重走 D 复审+E 增量；F 门（pi：9333 口径拍板后对当前 HEAD 全量视觉对照，R5 唯一 GT）→ 终审 Ekko → 合 PR（PR #4 解冻仍待拍板 ⑦；main 漂移留意合并策略）。
- 变更记录：本板 v1 = default 派单（gpt-5.6-sol A / grok G-2+H / deepseek D 预审 / glm-5.3-flash E / pi F / 代码任务卡）固化。
- 变更记录：v2（17:13 大佬令重派）——实测工作树活跃写入区 = `providers/*`（civitai/fal/hf/modelscope/nanogpt/__init__/catalog_ops/media_io，17:07–17:11 连续改动）+ `server.py`（17:12 后仍在变）= **grok 密集推进区，不派新写手、不 commit、不围观**；`static/storyboard.js` 自 15:46 静止 → A 包（gpt-5.6-sol）开工令重申（先 commit 现有改动→A-1→E5 前端；A-2 等 grok catalog）；`nanogpt.py` 归属待代码声明（grok ④亦列此洞，禁双写）；pi F 门预备只读可推进 + 账本文档单独 commit；glm-5.3-flash 修基线截图 md5 雷同；**审查门（D/E/F/C）无新 commit 不叫**。
- 变更记录：v5（D 裁定收讫翻账，自 v4=`210dbc1`）——B `50ac1f8` **D通过**、A-0 `2f29bf2` **D放行**、D 门裁定完成、E 门转正式进行中（23/27、4 FAIL 查根因）、**冻结至 E 门结论**；deepseek 补记：`loadCatalog` `items.slice(0,60)`（`storyboard.js:2052`）上限并入 A 包①核验范围，不构成对 A-0 的新驳回。
- 变更记录：v6（E 门收讫翻账，v5 未 commit 随本版一并落）——**E 门 11/11 通过**（glm-5.3-flash，md5 3/3 对 origin `2f29bf2`，4 FAIL 全坐实探针口径、无驳回）；**冻结解除**；D 门 P1 记录（`capabilityForCatalogItem` `:1805` nano-gpt join 键域不交）归 gpt-5.6-sol 随 A2 同批修；新派单：gpt-5.6-sol=A2+P1、default=sampler/scheduler 两下拉（同批合批走 D+E 增量）、pi=素材 grep 二轮回执（只读）；F 门全量视觉仍挂 9333（待大佬拍板①）；origin/main 另线被 kim1232aa 推至 `46b5544`（v0791–v0793），PR 分支 `feat/v0794-prompt-nodes` origin 端仍=`2f29bf2` 未动，push 目标不受影响。
- 变更记录：v7（D/E 双门增量收讫翻账，自 v6=`ca487eb`）——HEAD 链→`dd38e2a`（**A2+P1 `626304a`**+**B html 壳 `dd38e2a`** 落库，origin 端同点无漂移，ls-remote 已核）；§1 销两单并录 **D 增量裁定（通过无驳回**；三条不阻塞照录：fal/nano verbatim echo 归 A 包②、slice(0,60) 归①、27/28 假 FAIL 系探针口径**）**与 **E 增量 s6-s8（22/22 PASS 无驳回**；s6 backend 6/6 仅 civitai 显 key、s7 mode 三态含 video 禁发真门控、s8 填值 31/7 预选真值源+P1 徽标真驱动**）**；P1 闭环＝nano constraints **真驱动**；18772 served=`dd38e2a` 字节双证（server.py 零改动未重启）；F ② pi grep 回执已交、①挂 9333；A 包后续清单逐条另起 commit 待派；default 三 TODO+E2 桥仍挂。
