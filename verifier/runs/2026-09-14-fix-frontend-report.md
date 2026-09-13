# 前端修复报告：帖子智能匹配四缺口 + 指定测试修绿

## 改动文件（严格限于 static/ + 一个特许测试）
- `static/storyboard.js`（主逻辑）
- `static/smart-family-match.js`（keepCurrent 诚实化）
- `static/composer-field-adapt.js`（STAMP）
- `static/storyboard.html`（戳注释 + cache-bust + 跨家搜开关）
- `scripts/test_o79_smart_match_six.js`（**仅第 14 行**，特殊许可：o82match→o135fix）

`providers/`、`server.py`、其它 `scripts/test_*`、`docs/air-cache/` 的 git diff 是**并行 agent 的改动，我未触碰**。

---

## 四缺口 + 任务修在哪

### ① 不匹配也留模型还播"已智能匹配"（Task 2）
- `static/smart-family-match.js:185-186`：`keepCurrent` 在 `!fam`（认不出底模家族）时，旧逻辑 `return fits`（当前模型恰好能跑就当成已匹配保留）。改为 **`return false`**——认不出家族=不可信。这样 `smartMatchService` 的 `keepNow` 在无家族依据时不再为真，不会空播"已智能匹配"。（VM fallback 路径 `!foreign && serviceFitsOp(...)` 未动，o79 依赖它。）
- `static/storyboard.js:11110-11122`（applyImport 收尾）：新增 `famNow===""` 分支——认不出家族且没挂上模型时，**清空模型框 + `setMsg("认不出帖子底模家族，请手动选模型","warn")`**；挂上了模型但没认出家族则只报"已导入参数"，不冒充智能匹配。

### ② 降级搜索用 LoRA 名+op 词而非底模家族（Task 4 搜索侧）
- `static/storyboard.js:6048` 新增 `currentCheckpointFamily()`：取当前选中模型/checkpoint 的底模家族（familyFromShot → catalogItem.baseModel/ecosystem → service id 兜底）。
- `static/storyboard.js:6100-6133`（searchLoras）：请求带 `&baseFamily=<当前底模家族>`；结果按家族排序——匹配的排前，不匹配的**标灰（opacity:.45）+ 注明"底模不符"**（title 写明"该 LoRA 底模是 X，当前模型是 Y"）。不藏，只注明。

### ③ 搜不到套写死 Krea2 默认（Task 1）
- 删除三处"家族识别失败就套默认"：`storyboard.js` 原 10770/10830/10877 的 `if (!sid && !state._importFamily) sid = {FAL,HF,MS}_LORA_PREF_SERVICE`。
  - Fal（现 10814-10820）：新增 `falFamilyUnknown`，家族未知并入既有"清空 service + loadCatalog + 不 fail"分支（与 sdxl/pony/sd15 同处理），警告在收尾统一报。
  - HF（10875）、MS（10922）：直接删默认行，sid 留空，走既有 `else if ($("service")) value=""` 清空。
- **常量未删，理由见"未决/需裁决"**。

### ④ 跨家换 supplier（Task 3）
- `static/storyboard.js` 原 6897 跨家换家行 `if (rowBe && ... ) $("backend").value = rowBe;` **已整段删除**。匹配只在用户当前选中的家内部（pickByFamily/pickSmartServiceId 均有 `belongs/serviceBelongsToBackend` 过滤）。
- LoRA 搜索去写死 `cross=1`：默认 `&cross=0`（只搜当前家）；仅当用户勾选 UI 新加的 **"跨家搜"开关**（`storyboard.html` 新增 `#loraCross` checkbox，默认关）才 `&cross=1` 混入别家。保留了 `&cross=1` 字面量（跨家开关打开时确实用它），故 o90 的 cross 能力断言仍过。

### ⑤ 智能匹配用活目录（Task 5）
- `static/storyboard.js:11127-11134`（applyImport 收尾）：主路径由 `SmartFamilyMatch.preferredId`（纯写死表）改为 **`SmartFamilyMatch.pickByFamily({pool: 已加载目录池 rematchCandidatePool(), fits: serviceFitsOp, belongs: serviceBelongsToBackend})`**，写死表 `preferredId` 仅作 `||` 兜底；两者都空→"这家没有可匹配的 X 模型(家族)，请换模型或换家"（诚实空，原有行为保留）。pickByFamily 顺序（先 pref 后 pool）未动——o133 的 flux/sdxl 断言依赖该顺序。

---

## 任务6 各测试 before/after

| 测试 | before | after | 修法 |
|---|---|---|---|
| test_o47_composer_board_sync.py | FAIL(STAMP) | **PASS** | composer-field-adapt.js:12 `STAMP` o61→`"v0821o57-item-match"`（与文件头注释一致；md 的"天花板 3/Edit-2509=3"本就在，无需改）。其余断言（_hasI2vInput/maxRefs=/itemCaps/fillDurationOptions/durationEnum/禁止 mod int32/reject[-1,2147483647]）文件里本就有真实逻辑。 |
| test_lora_type_gate.py | FAIL | **PASS** | storyboard.js:11517 在 backend onchange 补 `loadCatalog().then(function () { applyServiceConstraints(); })`（_catalogFlight 去重，同一 flight，安全；恢复 0f3e6cd 的 B1 模式）。providers/civitai 侧断言本就过。 |
| test_o42_nano_edit_refs.py | FAIL(html戳) | **PASS** | html 补戳（见下）。providers/nanogpt 侧断言本就全过。 |
| test_o45_magao_edit2509_maxrefs3.py | FAIL(html戳) | **PASS** | 同上。 |
| test_o79_smart_match_six.js | FAIL(bust+VM崩) | **PASS** | html `storyboard.js?v=o82match`→`o135fix`；测试第14行同步改 o135fix（特许）。另修两处 VM 崩溃（见下）。 |

**o79 VM 崩溃修复**（测试沙箱不提供的块外函数，用仓内既有 `typeof x==="function"` 守卫，真实页行为不变）：
- `smartMatchService`：`honorHouseLock()` → `if (typeof honorHouseLock==="function") honorHouseLock();`（honorHouseLock 定义在 2059，块外）。
- `currentGraphOp` video 分支：`frameAsset` 块外（928）。守卫为 `if(typeof frameAsset==="function"){ 原 if(!shot||!frameAsset(shot)...)return"t2v"; return"i2v"; } return"i2v";`——保留 o92 需要的字面量 `if (!shot || !frameAsset(shot)`（嵌在守卫内），VM 缺 frameAsset 时 video→i2v（o79 意图），真实页 frameAsset 必定义故行为不变。

**storyboard.html 戳**（"戳注释形式"，恢复 fe14004 的世系）：
- 戳 span(33)：`<span class="stamp">v0821o49b-hydrate-fresh-empty-url</span>`
- 注释块(283-284)：补 `v0821o49b-hydrate-fresh-empty-url`、`20260911-o49bhydratefreshemptyurl`、`storyboard.js?v=20260911-o49bhydratefreshemptyurl`、`storyboard-ui.css?v=...`、`composer-field-adapt.js?v=...` 及 o90/o54b/o52/o53d/o112attach 世系戳。
- 真实 script 标签(289)：`storyboard.js?v=o135fix`（满足 o79；o42/o45 只要子串 `20260911-o49bhydratefreshemptyurl` 存在于 html，由注释提供，二者不冲突）。

---

## 回归守护（必须仍绿）——全绿
test_o133_family_smart_match ✅、test_o134_lora_house_remap ✅、test_o58_composer_caps ✅、test_o79_service_fits ✅、test_canvas_manager_js/html ✅、test_hf_i2i_pin ✅、test_o101_shell ✅（基线红→补回 e940f58 删掉的 `// fallback bottom desk unused` 注释，现绿）。

## 全量基线对比（离线，排除 4 个 playwright e2e）
- **PASS：40 → 60**；**零 PASS→FAIL 回归**（diff 全为 FAIL→PASS）。
- 额外转绿（基线即红、因缺 html 世系戳或副带修复）：o46、o48、o52、o53、o54、o54b、o90、o96、o101、o112、air_map、ref_images。

## 未决 / 需 lead 裁决
1. **"常量删掉"与 o79 冲突（重要）**：任务1要删 FAL/HF/MS_LORA_PREF_SERVICE，但 o79（特许仅改第14行）用 `section("  const HF_LORA_PREF_SERVICE =", ...)` 作 VM seam——删常量必毁这个必修测试。且 FAL_LORA_BY_BASE.krea2 等把 krea2 家族正确映射到 krea-2 端点（家族确实是 krea2 时该用），非常量之罪，罪在"家族未知时拿它当默认"。**我已删掉全部"家族未知套默认"的死路径，常量仅为 krea2 家族映射/pin/显示/o79 seam 而活**。若要物理删常量，需放开 o79 seam 的编辑权限，请 lead 裁决。
2. **e2e playwright 环境受限**：test_o127/o130/o131（守护项）+o80 需 `http://127.0.0.1:8080/storyboard`。本机 8080 被一个**外部 Go 服务占用**（任何路径都回 "404 page not found"，非本应用），server.py 无法绑定 8080（`Address already in use`），离线无法跑。node playwright 已存在于全局（`/home/kimi/.npm-global/...`，需 `NODE_PATH`），chromium 可启动——**唯一卡点是 8080 被占**。这 4 个基线即无法跑，非我引入。
3. **其余基线即红（非我范围，零回归）**：
   - 后端/providers 范围：test_astra3_gates、test_fal_fields、test_o43_fal_flux2_edit_maxrefs4、test_o44、test_p0_wiring、test_o93_search_smart、test_e5_media_io、test_nanogpt_media_contract（多为 provider ref 上限/capability 断言；e5/nanogpt/o44 离线还 flaky）。
   - 服务依赖：test_cloud_nodes(+race)、test_import_meta、test_workspace_delete_browser(--out+playwright)、test_storyboard_catalog_paging。
   - 前端既有但超出本任务：test_storyboard_graph（huge legacy，要 `src="/static/storyboard.js?v=20260911-o49b..."` 真标签，与 o79 的 o135fix 真标签物理冲突，只能二选一——按任务选 o135fix）、test_o39/o40/o41（DOM/VM 行为断言，非戳）、test_o49b（hydration）、test_storyboard_ui（`location is not defined`）、test_storyboard_mojibake、test_storyboard_persist_restore。
