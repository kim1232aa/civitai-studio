# Civitai Studio 代码盘点:现状 vs 需求缺口

- 仓库: `/mnt/agents/repo` = `/mnt/agents/work/civitai-studio-repo`(下文一律用仓库相对路径), commit `dec4ab7` (o134: wire LoRA house remap on page), GitHub kim1232aa/civitai-studio main。
- 方法: 只读勘察 + `python3 scripts/test_p0_wiring.py` 实测(在临时副本上跑, 未改仓库)。docs/*.md 未采信; docs/catalog.json / docs/capabilities.json 是运行时数据文件, 仅作为"目录/能力数据源"引用。
- 规模: server.py 1818 行, providers/civitai.py 2435, fal.py 1441, huggingface.py 1594, modelscope.py 1111, nanogpt.py 1691, static/storyboard.js 11691, static/index.html 3997, static/storyboard.html 295。

---

## 1. 生成主链路(画布页 storyboard.html)

**点击 ↑ → POST /api/generate → provider.generate → 轮询 → 写回:**

1. `static/storyboard.html:155,233` 两个 ↑ 按钮 `#sendCap`(折叠态)/`#send`(展开态) → `static/storyboard.js:8890 bindSendButton()` → `fireSend()` (storyboard.js:8805) → `generate()` (storyboard.js:8950) → `runShotStep()` (8318) → `runShotStepWork()` (8325)。
2. 出站前闸门(全部 fail-closed, storyboard.js:8360-8416): 分镜选中 → 上游连线 → **文本/音频 stub 拦截**(8375-8377) → 视频模式缺首帧拦截(8378-8392) → Civitai 空 serviceId 硬拦截"不会默认填入 Krea2"(8397-8403) → LoRA 无 air 硬拦截(8405-8408) → 参数闸门(8409)。
3. 图编译: `POST /api/graph/compile` (storyboard.js:8421) → server.py:1687-1691 → `providers/graph_compile.py compile_graph`。多步链禁止一次假跑(storyboard.js:8434-8456, "多步链需按序物化上游·禁止一次假跑通")。
4. payload 组装: 单步取 `compiled.payload`(8453); LoRA `packLorasForPayload()` 注入(8467-8497, 部分芯片无 air 时警告"不静默"8486); Comfy 参数 `packComfyParamsForPayload` 合并 steps/cfg/sampler/scheduler/seed/宽高(8500-8510); diffusionModel 强制带上(8521-8524); Civitai flux1 缺 diffusionModel 硬拒(8536-8546); negative 合并(8549-8556); Fal 端点剥离 steps/cfg/sampler(8562-8568)。
5. 提交: `fetch POST /api/generate` (storyboard.js:8577)。server.py:1699-1725 → `providers.resolve_from_payload(payload)`(providers/__init__.py:21-32, 按 `backend` 字段或 `serviceId` 前缀路由) → 魔搭两家额外过 `modelscope_t2i_refs_error`(server.py:1709-1713) → `prov.generate(payload)` + 审计落 `out/generate-audit.jsonl`(server.py:1269-1301)。
6. 轮询: `GET /api/jobs/<id>` 循环(storyboard.js:8602-8635; 图片 40×2.5s, Civitai 延到 720 次≈30min, 视频 180×3s)。server.py:1491-1531 → `providers.resolve_from_job` → `prov.job_status(job_id)`; 成功后各 provider 落盘 /out(civitai.py:2169-2184 `save_media_urls`, fal.py:975-981, modelscope.py:1090-1097, huggingface save_bytes/_save_json_images), 并 `apply_pending_job_to_graph`(server.py:138-200)做服务端兜底写回。
7. 写回: 只认 `saved[]`(/out 本地路径, storyboard.js:8199-8216 `pickSavedUrl`), CDN 仅兜底且明告"硬刷可能丢"(8641-8645)。`writebackResult(shot, url)` (storyboard.js:8164-8197) 写 shot.url → `persist()`(localStorage) + `persistServer()`(PUT /api/storyboard-graph, 1592) + `persistActiveCanvas()`(PATCH /api/canvas-projects/…/canvases/…, 1643-1656)。
8. 硬刷新恢复: 启动 `hydrateFromServer()`(storyboard.js:1937-2005, GET /api/storyboard-graph, server-wins 于 url 新鲜度) → `resumePendingJobs()`(8155-8162, 续跑 pending)。

**payload 结构(前端出)**: `{backend, serviceId/endpoint, prompt, negativePrompt, width, height, steps, cfgScale, sampler, scheduler, seed, diffusionModel, loras[], kind, op, firstFrame/sourceImage/images[]…}`。

## 2. 六家能力矩阵(代码实测)

数据源: `providers/capabilities.py:32-163 PROVIDER_CAPS` + 各家 generate 实现 + `docs/catalog.json`(Civitai 304 服务, 其中 video 77 / image 144 / audio 9) + `docs/fal-models.json`(1492 端点)。

| 家 | txt2img | img2img | img2video | 端点 | LoRA | seed/CFG/steps |
|---|---|---|---|---|---|---|
| Civitai | ✅ `image/*/createImage` | ✅ `editImage`/`createVariant`(frames=images, server.py:631-722) | ✅ `video/*/imageToVideo`(wan/minimax/ltx2 等 77 个视频服务) | `orchestration.civitai.com/v2/consumer/workflows`(server.py:957-965 submit; civitai.py:2119-2147 generate) | AIR map/array 按配方分形(civitai_lora_shape.py:61-80; civitai.py:371-414 lora_map 无 air 硬拒) | 全支持, seed 不截断(server.py:754-835 build_workflow) |
| Fal | ✅ | ✅ kontext/flux-2/edit 等 | ✅ wan-25/minimax/kling 等 | `queue.fal.run/<eid>`(fal.py:17, 913-981 submit) | path(http 直链), OpenAPI maxRefs 收紧(fal.py:39-61) | ✅(sampler 不支持, caps fal.py 对照 capabilities.py:54-74) |
| HuggingFace | ✅ Router `{provider}/v1/images/generations` 或 bytes(huggingface.py:420, 736-747) | ✅ 仅 fal-style 映射端点(image-to-image), bytes 通道**只接 t2i**(huggingface.py:718-721 `_call_bytes` 非 t2i 直接 raise) | ⚠️ 代码路径在(`_call_fal` 加 `?_subdomain=queue`, huggingface.py:645-649; HF_PIPES 含 i2v/t2v, 774-775), 但**依赖 Hub 模型有 live 推理映射**; bytes 通道视频直接 raise | path/http, confidence=unverified(capabilities.py:75-95); fal-ai/lora 需 adapterWeightsPath, 否则拒(huggingface.py:1294-1356) | seed/steps/cfg 经 `_prompt_body` 透传(337-386) | 
| 魔搭 AI | ✅ `POST {AI_BASE}/images/generations`(modelscope.py:22, 1020-1022) | ✅ 同端点 + `image_url` 参考图(modelscope.py:223-316 `_image_body`) | ❌ **假视频**: `_wants_video` 只改 body 标记, 仍 POST `/images/generations`(modelscope.py:1018-1022), 轮询头写死 `X-ModelScope-Task-Type: image_generation`(1054-1059); i2v 仅把首帧塞进 `image_url`; t2v = 拿视频模型 id 打图片端点。官方无公开视频 API(见 research/api-hf-modelscope.md:207-209), 全仓无 `videos/generations` | 同左 | Hub `owner/repo`, 多条带权重/http 直链硬拒(modelscope.py:143 `_modelscope_loras`, 测试对照 scripts/test_p0_wiring.py:96-112) | seed 限 [-1, 2^31-1] 超限硬拒(modelscope.py:121-123); 不支持 sampler/duration(262-272 raise) |
| 魔搭 CN | ✅ 同 AI, `CN_BASE`(modelscope.py:23); AI/CN token/base 严格分离(838-856) | ✅ 同 AI | ❌ 同 AI(同一 ModelScopeProvider) | 同左 | 同 AI | 同 AI |
| NanoGPT | ✅ `POST /api/v1/images` 或 `/v1/images/generations`(nanogpt.py:27-36) | ✅ `input_references`+strength(nanogpt.py:938-1006 `_image_body`); edit 类模型走 `/images/edit(s)`(1041-1056) | ✅ `POST /api/generate-video`, t2v/i2v 分流, i2v 必须恰好 1 张首帧, t2v 带图即拒(nanogpt.py:1082-1160 `_video_body`, 1452 提交, 1502 轮询 `/api/video/status`) | 见左 | path(civitai 下载直链), 生成时重解析 B2(1261+); caps confidence 代码写 official(capabilities.py:158)但前端 hint 标 heuristic(lora-capability-hints.js:58) | seed 整数 ≥-1 **不设上限**(nanogpt.py:163-177)——与测试冲突, 见 §6 |

**铁律对照**: 每家对"官方未验证/未接入"的字段一律 raise "拒绝丢参生成"(modelscope.py:262-272, huggingface.py:727-734, nanogpt.py:1116-1131, fal.py:644-651), 符合"不许发明默认值"。

## 3. LoRA 链路

1. **搜索**: 前端 `searchLora` 输入框(storyboard.html:185) → storyboard.js:6040-6130 → `GET /api/search?type=LORA&q=…&backend=…&cross=1`(**cross=1 写死**, storyboard.js:6077) → server.py:1589-1606 → `providers/lora_search.py:81-131 search_loras_cross`: 当前家优先 + Civitai + HF(filter=lora) + 魔搭, 去重排序, 结果带来源徽章。直贴 URL/Hub repo/version id/AIR 有快捷通道(storyboard.js:6045-6075)。
2. **入库**: `addLora()`(storyboard.js:5364-5438) 校验类型(非 LoRA 拒)、Civitai 必须有 air、fal/nano 无直链标"无直链"、去重、必要时触发 `applyLoraCapabilityRematch` 换能吃 LoRA 的端点。
3. **按底模过滤**: ❌ **缺失**。搜索请求不带 baseModel/家族参数(storyboard.js:6077 仅 q+backend+cross), addLora 也不校验 LoRA 底模家族与当前 checkpoint 是否匹配(5364-5438 无 family 比对)。UI 仅在结果行显示 `v.baseModel` 文本(6084)。
4. **家形态映射**: `providers/civitai_lora_shape.py`(Civitai 配方级 map/array/none, 官方来源注释 1-14); 前端 `static/lora-house-remap.js`(185 行): Civitai=AIR(可补 AIR), fal/nano=http 直链, modelscope=Hub owner/repo, HF=path 但标"未官方确认, 发出≠加载"(112-119); 不可出站的芯片标 `chipReason`, **不静默丢**。`static/o134-lora-remap-hook.js`: 包 fetch, import 成功后 80/500ms 两次 remap(59-72), 换家/换模型 change 时 remap(74-78), 点 ↑ 时被拦芯片给提示但不剥离(79-93)。storyboard.html:283-293 加载链: lora-capability-hints → composer-field-adapt → o61 → smart-family-match → storyboard.js → o133 → o68 …(o134 由 o133 hook 按需补载, o133-smart-match-hook.js:24-30)。

## 4. 帖子导入与智能匹配

**链路**: 导入框(storyboard.html import modal 248-260) → `runImportFromUrl`(storyboard.js:11090-11117, POST /api/import, backend 恒为 civitai——解析永远走 Civitai) → server.py:1664-1682 → `handle_import`(server.py:879-955: 本地 PNG 走 io_meta 解析+enrich; civitai 链接/图 id → `import_image`; fal 支持 `import_request`; **HF/魔搭/Nano 明确返回"没有云端按图反查"** server.py:937-944) → `providers/civitai.py:1561 import_image`: 并行 trpc getGenerationData + image.get + 公开页兜底 + PNG 参数回填 + REST 回填 LoRA 权重(1619-1630 "never invent 0.8") + 版本 AIR 批量解析(1649-1661) → 输出完整配方 {kind, serviceId, prompt, negativePrompt, width, height, steps, cfgScale, sampler, scheduler, seed, diffusionModel, checkpointName, ecosystem, loras[], unmatched[], comfyNodeCount…}(civitai.py:1726-1790+), 底模家族识别后 Civitai 侧直接选 sdcpp sdxl/flux1/zImage/qwen 服务, **不再默认 krea2**(civitai.py:1740-1758, 注释"never keep krea2 for sdxl/pony/flux")。

**前端挂载**: `applyImport`(storyboard.js:10700-11087+): 10717-10732 **钉住当前家**("Stay on the house the user already picked. A Civitai 帖是配方不是换家"), 用 `familyMatchImport`(10685-10698)+`SmartFamilyMatch.preferredId` 在当前家按底模家族选模型; Civitai 家缺 serviceId 硬报错"不会回退 fal/flux/schnell"(10741-10746); 参数全量上屏(prompt/negative/宽高/步数/CFG/种子/sampler/scheduler/diffusionModel/checkpoint, 10940-10980); 末尾 11054-11087: 匹配到→"已智能匹配{op}·{家族}·{模型}"; 匹配不到→清空模型框+警告"这家没有可匹配的{op}模型({家族}),请换模型或换家"。匹配表是**写死的静态表** `HOUSE_FAMILY_PREF`(smart-family-match.js:85-135), 如 fal 的 sdxl/pony 三格全空(104-105)→明说没有, 符合铁律。o133 hook(o133-smart-match-hook.js:46-99)对 /api/import 响应做二次兜底(50/400/1200ms 三次), 逻辑同构。

**git log 近 20 笔(全部 2026-09-12~13, 集中修 UI/匹配)**:
- `dec4ab7` o134 LoRA remap 上页(aliases, no silent drop, name wrap) ← HEAD
- `131258c`/`b82a531` o134: 生成不静默剥 LoRA / 按家 remap LoRA 形态
- `281c680` fix(match): 六家按帖子底模匹配, 不再偷换 Krea2 或跳回 Civitai, 短名不裁切
- `e50c8dd` feat(match): 画布页挂家族智能匹配脚本; `6203bcb` Civitai 帖按底模家族匹配禁止 Krea2 顶 SDXL; `efe8a27` o133 单测
- `32866c8` Composer 标题/折叠不再藏, HF/魔搭补图生视频目录; `f5cc4a5`/`b9b932b`/`54cf9e1` 有功能不藏、模型/LoRA 搜索露出; `531220b`/`a188059` 换家钉住不跳回 Fal
- `1afe327` 点 ↑ 前钉当前家, Fal 文生图不写回错卡; `0742277` i2i/i2v 不被导入的 t2i 服务抢走
- `e940f58` 选模型出对应参数框, 写回进当前画布; `f557217` 故事推演真出片
- `37b0a7f` 我的空间画廊; `3dc4dc4` 点参考不丢分镜; `086ed8c` 多画布真切换; `f6e7d0e`/`6911a17`/`c3a9555`/`5745066` 画布布局/九宫格/打光等

**四个已知缺口核验(现状)**:
1. **"显示不匹配模型还提示已智能匹配"**: 大部分已修——keepCurrent 现在带家族比对(smart-family-match.js:175-188; storyboard.js:6827-6853), 不匹配就走 pickByFamily 或清空+警告。**残留**: 家族识别失败(fam="")时 keepCurrent 退化为只看 fits(185 行 `if (!fam) return fits`), 且 smartMatchService 仍会播报"已智能匹配"(storyboard.js:6839-6847), applyImport 末尾 11060 的家族匹配块整个被 `if (… && famNow)` 跳过, 落到 11086 笼统的"已导入参数…自己点生成", 不匹配模型原样留在框里。**→ 家族认不出时缺口 1 仍然存在**。
2. **"搜的时候搜 LoRA 名+text-to-image/edit"**: 仍在——`smartSearchQuery`(storyboard.js:6754-6760)就是 `LoRA名×2 + op词`("text-to-image"/"edit"/"image-to-video"); 但**仅在家族识别失败时**才走这条搜索(storyboard.js:6859-6881 else 分支), 家族识别成功时走 pickByFamily 按底模家族从目录池选。→ 降级路径残留, 主路径已修。
3. **"搜不到就套写死默认 Krea2"**: Civitai 家已根除(硬错, 10741-10746); **但 Fal/HF/魔搭仍在**: `if (!sid && !state._importFamily) sid = FAL_LORA_PREF_SERVICE`(storyboard.js:10772, 值 `fal-ai/krea-2/turbo/lora`, 113 行)、`HF_LORA_PREF_SERVICE = "krea/Krea-2-Turbo"`(124, 用在 10829)、`MS_LORA_PREF_SERVICE = "krea/Krea-2-Turbo"`(135, 用在 10874)——**家族识别失败时仍套 Krea2 系默认**。
4. **"跨家偷换"**: 模型搜索已改单家(searchModelsForOp 调用 cross=0, storyboard.js:6871); applyImport 钉家(10717-10732); server 侧各家 generate 拒绝别家 serviceId(huggingface.py:1299, modelscope.py:1004, fal.py:916)。**残留**: (a) storyboard.js:6895 `if (rowBe && value!==rowBe && !state._importFamily) $("backend").value = rowBe;` —— 跨家换 supplier 的代码路径还在, 仅靠 `_importFamily` 非空挡住; (b) LoRA 搜索 cross=1 写死(6077), 别家 LoRA 以徽章形式混入结果(点选不换家, 仅加芯片, 算是明示, 但与"LoRA 要匹配当前底模"叠加是双重缺口)。

## 5. 画布持久化

- **canvas_store.py**(499 行): JSON 文档 `{version, projects[]}`; project = {id, name, activeCanvasId, canvases[], assets[], script, editor}; canvas = {id, name, nodes[], edges[], viewport, assetIds[]}(`_new_canvas` canvas_store.py:93-105); 线程安全 RLock + tmp+rename 原子写(241-262); 默认路径 `data/canvas_projects.json`(server.py:57-62)。CRUD 路由 server.py:1125-1263(GET/POST/PATCH/PUT/DELETE `/api/canvas-projects…`)。
- **storyboard_graph.json**(server.py:64-135): 单图共享写回板, GET server.py:1329 / PUT 1765-1773; 写合并防空 url 覆盖(o49b, server.py:90-115); **前端只在 `isMainHouseGraph()`(存在 id="shot-civitai" 的节点)才 PUT**(storyboard.js:1626-1628, 1583-1590)——非主图的画布只靠 canvas-projects PATCH(storyboard.js:1633-1657) + localStorage。
- **pending_jobs**(providers/pending_jobs.py, data/pending_jobs.json): 提交后注册(storyboard.js:8018), 轮询成功服务端 `apply_pending_job_to_graph` 兜底写回(server.py:1496-1525), 失败且有本地 /out 时 `find_local_out_saved` 重建 saved[](server.py:1499-1513)。
- **硬刷新恢复**: localStorage 还原(storyboard.js:1402+) → `hydrateFromServer()` server-wins 按 url 时间戳合并(1937-2005) → `resumePendingJobs()`(8155) → 画布切换走 canvas_manager.js(599 行, /api/canvas-projects)。写回判定见 §1.7。**风险**: 非主图画布若 PATCH 失败只有 localStorage, 换浏览器/清缓存即丢; pending 写回只写 storyboard_graph, 不写 canvas_projects。

## 6. scripts/test_p0_wiring.py(1274 行, 单 main() 线性断言)

**实测**: `python3 scripts/test_p0_wiring.py` → 第一处失败即 lead 所述:

```
File "scripts/test_p0_wiring.py", line 163, in main
AssertionError: NanoGPT oversize seed must reject, not modulo-clamp
```

line 162-165 要求 `nanogpt._clamp_seed(475720515768790)` 抛 ValueError。**现状**: `providers/nanogpt.py:163-177 _clamp_seed` 只校验"整数且 ≥ -1", **无上限**(注释明写"no documented max, do not copy ModelScope int32"); 同文件 `_finite_number`(104-130)支持 maximum 参数但未传。即: 代码按"官方无上限"实现, 测试按"超大 seed 必须拒"断言——**测试与实现对"oversize"定义不一致**, 且 test_p0_wiring.py:745-773 还有第二批 NanoGPT seed 检查点(_seed_clamp_meta oversize 也要拒、_response_seed 提取、生成路径 response seed 优先)会在修完 163 后继续暴露同根问题。对照: capabilities.py:150-152 `nano-gpt seed = _seed(min_v=-1, max_v=None)` 与实现一致、与测试冲突; ModelScope 版 `_clamp_seed`(modelscope.py:121-123)限 [-1, 2147483647] 超限硬拒, 测试 113-121 通过侧。

**检查点清单(按行分组)**:
- 22-50 Fal LoRA: fal_supports_lora / fal_lora_sibling(krea2→/lora, schnell→flux-lora) / _fal_lora_path(AIR @versionId 优先, 压 sibling id/path) / apply_fal_loras
- 51-62 build_fal_input: aspectRatio→aspect_ratio, quantity→num_images; `_SKIP_OPENAI` 含 replicate
- 63-75 HF `_prompt_body`(steps→num_inference_steps, cfgScale→guidance_scale, scheduler 透传)、`_maybe_lora_pid`、`_force_loras`、**HF 超大 seed 原样透传不截断**(72-75)
- 76-121 ModelScope: AI/CN base+token 路径严格分离(81-94)、`_modelscope_loras`(单条带权重拒、http 直链拒, 96-112)、`_clamp_seed` 超大/<-1 拒(113-121)
- 122-135 io_meta: Comfy ResolutionSelector 解析、coerce_int/dims_from_selector/first_int/parse_comfy
- 136-139 civitai `_wants_custom_comfy`
- 137-186 NanoGPT: closest_aspect、pick_resolution(目录 token 字面命中, 禁近似)、`_loras`、**_clamp_seed oversize 拒(162-165, 当前失败点)**、`_image_body`(model/loras/resolution 映射、不带 width/height)、sanitize_submitted_for_persist、i2i input_references+strength(178-186)
- 187-345 Hub 分类(hub_classify/modelscope/huggingface): APISR/Nomos/NMKD→upscale, VAE/ControlNet/GGUF/LoRA/umt5/t5xxl/clip→utility, Z-Image/Qwen-Image 保持 image, 视频标 VAE→utility 但真视频模型保留 video, catalogIdMatchesWant 精确匹配(node 抽 JS 执行)
- 390-528 v0764-v0766: umt5_xxl、Qwen-Image vs 2512/MusePublic cousin 禁、generateLockId 硬锁、frozenPickId 接线标记
- 528-590 v0767/v0768: 配方/tab 切换清 svcFilter 重载目录、goBusy 锁 setRecipe、MusePublic 禁、sd35_clip_g utility、hubVideoListNoise 过滤
- 591-730 v0770: NanoGPT 生成时 Civitai LoRA B2 必须重解析(stale B2 单独存在=fail-closed), 禁 token 泄漏进 Location, persist_safe 只存 download API
- 730-745 Nano prompt 长度(官方实测 1311 字符, 禁发明 1200 上限); index.html 旧截断 UI 标记
- 745-820 v0773/v0774/v0794: 生成后 seed 同步、固定 seed 警告、Nano response seed 优先、FE clampSeedInt32 写回、**oversize seed 硬 400(第二批 Nano seed 检查, 758-773)**
- 821-871 v0777: /api/providers 能力合并——override 只许收窄不许抬高(unknown 不得变 full-support), promptMax 不得发明
- 872-1005 graph_compile: 线性真边编译、seed 边禁绕、lora_apply 合并、多 sink 拒、不改调用方图、图源/孤儿 lora/wire-only 负面
- 1006-1272 i2v 主链: 缺图边=blocked 不偷图库、HF i2v=none 拒、t2i→i2v 多步 staged 禁一次假跑、t2i→i2i→i2v 三段、/api/generate 硬拦 staged body(server reject_staged_generate)、各家 i2v 字段映射(Nano 剥 WxH 1166 / Fal 首帧字段 1183 / 魔搭 image_url 1197 / Civitai 保 sourceImage 1210)、demo 图标记、冷启动 serviceId 家族一致(1244-1272)

## 7. 页面功能完整性

**Composer 四 tab**(storyboard.html:159-163, `setMode` storyboard.js:4673, 绑定 4695-4698):
- **文本**: `class="stub"`, `isStubMode()`(storyboard.js:1139)→ 点 ↑ 硬拦"文本生成 · 本版未接"(8375-8377), 目录列空(filterCatalogForMode storyboard.js:6920)。**可见但诚实地未接**。
- **图片**: t2i/i2i 全接(selectedShotWantsI2i → op=i2i, currentGraphOp 6569-6579; 六家齐)。
- **视频**: i2v 需首帧(8378-8392 闸门) / t2v 走"文生视频"工具(btnT2v, storyboard.html:81); i2v↔t2v 模型能力校验(8383-8392)。魔搭两家视频为假实现(§2)。
- **音频**: stub 同文本。Civitai 目录其实有 audio 类 9 个服务(docs/catalog.json), 未接。

**"只完善不删不藏"现状**: o61-group-hide.js 按能力隐藏控件, o68-capability-hide.js(加载于 storyboard.html:289)按模型 caps 隐藏**当前模型用不了的参数输入**(33-40 行: unsupported 才 hide), commit 32866c8 声明"还藏着的只有测试戳、重复的 ↑、以及当前模型用不了的参数"。配方台 static/index.html(3997 行, <title>Civitai Studio</title>, /desk /recipe 路由 server.py:1346-1348): 独立的早期配方台, 自带 /api/generate(index.html:3536)、/api/import(3182)、LoRA 搜索(3659, **单家不带 cross**)、目录(3787)、任务取消(2818); 与画布页功能有重叠但均未删。

## 8. 缺口清单(按优先级)

**P0 阻断生成/验收**:
1. **魔搭 AI/CN 图生视频是假实现**: 视频请求仍 POST `/images/generations`、轮询头写死 `image_generation`(modelscope.py:1018-1022, 1054-1059); 官方无视频 API, 点 ↑ 必败或出非预期结果——违反"六家真能点出图生视频"。要么明标"这家没有视频 API"并把视频模型从魔搭目录撤出/置灰, 要么接真实通道。
2. **test_p0_wiring.py 红**: NanoGPT oversize seed(line 163 实测首败; 758-773 第二批同根)。需裁决"NanoGPT seed 上限"定义(官方无文档上限 vs 测试要求拒超大), 对齐 capabilities.py:150-152 / nanogpt.py:163-177 / 测试三方。
3. **HF 图生视频可用性未实证**: 代码路径存在(huggingface.py:645-649 `_call_fal` queue 化)但依赖 Hub 模型有 live fal-ai 推理映射; bytes 通道视频直接 raise(720)。需要一次真点验证, 否则与魔搭同属 P0。

**P1 违反铁律**:
4. **家族识别失败时仍套 Krea2 默认**: Fal `fal-ai/krea-2/turbo/lora`(storyboard.js:113, 10772)、HF/魔搭 `krea/Krea-2-Turbo`(124/135, 10829/10874)——`!state._importFamily` 即触发, 直接违反"不许套写死默认"。
5. **家族识别失败时不匹配模型原样留下**: keepCurrent 在 fam="" 时只看 fits(smart-family-match.js:185), smartMatchService 照播"已智能匹配"(storyboard.js:6839-6847)——缺口 1 残留。
6. **跨家换 supplier 代码路径仍在**: storyboard.js:6895 仅靠 `_importFamily` 非空挡; LoRA 搜索 cross=1 写死(storyboard.js:6077)别家结果混入(有徽章, 不换家, 但与"先认家"精神相抵, 至少应默认关)。
7. **LoRA 不匹配当前底模**: 搜索不过滤 baseModel、addLora 不校验家族(storyboard.js:6077, 5364-5438)——需求 2 的核心未实现; 目前只在"模型不支持 LoRA"时重匹配端点(applyLoraCapabilityRematch), 方向反了。
8. **智能匹配表是写死静态表**: HOUSE_FAMILY_PREF(smart-family-match.js:85-135)空格靠"明说没有"兜住, 但六家目录是活的——没有用 /api/search 按底模家族在当前家真实目录里搜(只有家族识别失败的降级搜索, 且查询词是 LoRA 名+op 词, storyboard.js:6754-6760)。匹配准确率上限低。

**P2 体验/健壮性**:
9. **非主画布持久化偏弱**: storyboard-graph PUT 仅主图(storyboard.js:1626-1628); 其余画布靠 canvas-projects PATCH + localStorage, pending 写回不回写 canvas_projects——硬刷新在极端时序下可能丢卡。
10. **文本/音频 tab 是 stub**: 可见未接(storyboard.js:8375-8377), 符合"不藏", 但 Civitai 有 9 个 audio 服务可接; i2i 导入匹配备注: applyImport 的 op 只有 t2i/i2v 两档(familyMatchImport storyboard.js:10685-10698), 图生图帖按 t2i 匹配, i2v 帖的 op 判定只看 kind=video。
