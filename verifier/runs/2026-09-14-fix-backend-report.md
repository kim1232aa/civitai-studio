# fix-backend 报告(working tree = /mnt/agents/work/civitai-studio-repo @ dec4ab7 + 并行前端 agent 改动)

## 结论速览
8 项任务里 **4 项的红测试是"过期断言/测试互相冲突",不是代码 bug**,按铁律停下待裁决(冲突 #1/#2/#3/#4,另发现 #5/#6 同族)。
已实际修复并验证:test_o57_six_catalog_stamp(代码)、o44/o46/nanogpt_media_contract 的 fixture 缺口、test_air_map 路径。
**未把任何基线绿的测试弄红**(逐项对照 pristine dec4ab7 基线)。

## 我改了哪些文件
| 文件 | 改动 | 行号 |
|---|---|---|
| providers/modelscope.py | generate() 增加视频硬拒闸门:`_wants_video(payload, mid)` 为真 → 400,中文说明"魔搭官方没有视频生成 API,拒绝拿 /images/generations 图片端点冒充";不落库 remember_job、不 POST | ~1009-1020(generate 内,mid 计算之后) |
| providers/six_catalog_caps.py | 新增 `_sid_has_lora_token()`(token 级 lora 判定,避免 "floral" 误判);overlay_fal_catalog_item 的 lora 检测由 `"/lora" in sid` 扩为 token 匹配 | 48-56, 72 |
| scripts/test_air_map.py | 仅修 harness:ROOT 由写死的 `/workspace/civitai-studio` 改为 `Path(__file__).resolve().parents[1]`;断言未动 | 10 |
| scripts/test_fal_fields.py | 同上(仅 sys.path 修复) | 3 |
| out/fill-cap-1..9.jpg | 新增:合法小 JPEG(16×16 渐变,~710-750B),o44/o41/storyboard_graph 的 fixture | - |
| out/upload_20260909150943_1.jpg、upload_20260909150949_1.jpg | 新增:合法小 JPEG,nanogpt_media_contract / test_ref_images 的 fixture | - |
| out/modelscope-ai_2ad94576-35b7-47c4-8765-f19f6cf1fbe2_0.png | 新增:合法小 PNG,o46 find_local_out_saved 的 fixture | - |

注:out/ 在 .gitignore 里,是项目公认的运行时 fixture 机制(server.py `ensure_fill_cap_fixtures` 也是往 out/ 拷)。

## 每测试 before → after
### 修绿
- **test_o57_six_catalog_stamp**: KeyError 'supportsLora'(fal "fal-ai/flux-lora" 不含 "/lora" 段)→ **PASS**。fal overlay 现按 token 识别 lora 端点。
- **test_air_map**: ModuleNotFoundError(写死 /workspace 路径)→ **PASS**。
- **test_o46_resume_writeback**: find_local_out_saved 找不到 /out fixture → **PASS**(补 fixture 后全绿,含 static 戳——前端 agent 已落地)。
- **test_o42 / test_o45**:基线败在 html stamp;我未改代码,**前端 agent 落地 static 戳后两测试全绿**(o42 32 checks、o45 PASS)。其 providers 逻辑断言本来就全过。
- **test_o44**: fixture missing → 补了 fill-cap-1..9.jpg,fixture 断言过;现卡在冲突 #4(见下),仍红。

### 仍红 —— 冲突待裁决(全部附证据)
- **冲突#1 test_p0_wiring**(L162/760/765/814: nano seed 475720515768790、891104780613135 必须 ValueError/400)vs **test_nanogpt_parameters**(必须保绿;L189-191 要求 2147483648、467475143677094 **透传**,L176 禁止源码出现 "2147483647",注释明写 "official WaveSpeed/NanoGPT have no int32 max")。考古:0163679(任务所依据的 p0 断言来自更早的 0178eac)刻意移除 nano int32 上限;两值区间 [467475143677094, 475720515768790) 内无任何自然边界(2^49 太大、JS safe int 9e15),475720515768790 本身是 civitai/fal 测试里的真实样本种子。**lead 指示的 max=2147483647 会直接弄红 test_nanogpt_parameters,两边不可兼得。** 附带:test_nanogpt_media_contract(我补 fixture 后推进到 L231)与 p0 同边。
- **冲突#2 test_ref_images L25**(max_refs("modelscope-ai")==1,断言源自 09b117e/Sep-07)vs **test_modelscope_catalog_refs**(保绿,L32-34 ceiling==3)与 **test_o45**(L24-37 ceiling==3)。6a313ce(Sep-10)有官方依据(Qwen-Image-Edit-2509 官方收 1–3 张 image_url)刻意把魔搭 ceiling 1→3。test_ref_images L25 是过期断言。
- **冲突#3 test_e5_media_io L42-54**(1×1 PNG 上传必须 200 落盘,源自 31abe24/Sep-09)vs **test_o91_blank_outs**(绿;同字节级 1×1 PNG 必须 400 blank_image,17d5532/Sep-12 刻意加"空图不入库"闸门)。e5 的 KeyError 'file' 正是 blank 闸门 400 所致。
- **冲突#4 test_o44**(sdcpp/flux1/editImage 必须收 9 张,自称 "official maxRefs=9")vs docs/capabilities.json 官方抓取该服务 constraints.images.**maxItems=2**(自首提交未变;94e9d89 刻意加 constraints 强制,test_ref_images boogu maxItems=2 也锁它)。docs/ 不在我可改路径。o44 在 authoring commit f8c6f27 绿是因为当时 ref_images 不读 constraints(分支在 94e9d89 合入前)。
- **冲突#5 test_fal_fields**(我修路径后暴露):期望 2 张参考图静默映射进单槽 image_url;与 fail-closed "拒绝截断"(test_ref_images L54-67 锁)直接矛盾,过期。
- **冲突#6 test_o43_fal_flux2_edit_maxrefs4**(非任务单内,基线红):期望 fal flux-2/edit 9 张**静默切片到 4**;与 fail-closed 矛盾。05dc155 时绿是因为当时 `extra[:ref_cap]` 切片,d4b3377 合入 fail-closed 后红。

### 仍红 —— 环境/前端范围(非我引入,基线同红)
- test_astra3_gates(cache stamp)、test_cloud_nodes_disconnect_race(cloud-nodes.html guard):static/html 戳 → **前端范围**。test_lora_type_gate 前端 agent 已修绿。
- test_cloud_nodes 11/12:test_hf_i2v_blocked 期望 HF i2v 被 compile_graph 拦,当前 HF caps video=True 放行 —— 能力数据问题,基线同红,未动。
- test_import_meta:需 /tmp/civitai-img fixture + **live 网络**(civitai.red),离线必红,基线同红。
- test_storyboard_graph 17/75(前端 agent 工作中,基线 14/75,在好转);test_workspace_delete_browser 需要 --out 参数(harness 用法)。
- JS 红测试全部读 static/(o101/o112/o127/o130/o131/o39/o40/o41/o48/o49b/o52/o53/o54/o54b/o79_smart/o90/o93/o96/storyboard_*)→ **前端范围**;o40/o41 里 fixture 存在性断言已因我的 out/ fixture 而满足。

### 保绿确认(任务点名清单,当前全绿)
civitai_parameter_contract ✓ fal_parameter_contract ✓ hf_parameter_contract ✓ nanogpt_parameters ✓ o58_import_hinablue ✓ lora_air_resolve ✓ modelscope_video_body ✓ o57_civitai_lora_shape ✓ o57_item_param_caps ✓ io_meta ✓ nanogpt_lora_resolve ✓ hf_catalog ✓ modelscope_catalog_hub ✓ modelscope_catalog_refs ✓ canvas_projects ✓(import_meta 基线即红,见上)

## 任务2 调和说明(modelscope 视频)
test_modelscope_video_body 锁的是 `_image_body(..., video=True)` 纯 body 构造器(model/prompt/size/image_url、无 duration)。我把硬拒放在 `generate()` 入口:生产路径视频 payload 100% 被 400 拦下(已单测验证 AI/CN 两种 flavor、i2v/t2v 两种触发,json_call 零调用);`_image_body(video=True)` 作为"假如官方有 API 时的正确 body 形状"保留并被单测锁定,生产不可达。轮询头 `X-ModelScope-Task-Type: image_generation` 在闸门后**永远如实**(只剩图片任务),无需改;job_status 的 output_videos 收集与 providers/http.py 共享,属防御性解析,保留。

## 未决清单(等 lead 裁决)
1. #1 nano seed:授权改 test_p0_wiring 的 4 处过期断言(推荐,符合 0163679 最新意图),或授权发明阈值(两绿但语义凭空),或 p0 保持红。
2. #2 魔搭 maxRefs:豁免/更新 test_ref_images L25 为 3(推荐,符合 6a313ce 官方依据)。
3. #3 e5 vs o91:豁免/更新 e5 的 1×1 上传段(推荐,17d5532 更新且有产品理由)。
4. #4 o44 9 张断言 vs 官方 maxItems=2:更新 o44(推荐)或授权改 docs/capabilities.json。
5. #5/#6 fal_fields / o43 的静默切片期望 vs fail-closed:建议标注过期。
6. capabilities.py nano seed max_v 是否写 2147483647 —— 受 #1 结果约束,暂不动作。
