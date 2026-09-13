# 2026-09-14 后端+前端修复回归(离线单测层)

- 命令: `for f in scripts/test_*.py; do python3 $f; done` + `for f in scripts/test_*.js; do node $f; done`(全量 81 个)
- 基线(dec4ab7 pristine worktree): **PASS 39 / FAIL 42**
- 修复后(工作树): **PASS 61 / FAIL 20**,exit 逐文件记录于 /tmp/fin_*.log
- **零 PASS→FAIL 回归**(现存 20 红全部为基线 42 红子集)

## 本轮修绿(22 项,含裁决对齐)
- test_p0_wiring.py(1274 行主链路硬门)全绿: NanoGPT seed 超大透传裁决(对齐 0163679 "官方无上限不发明"); HF i2v 已接线(image_url)更新过期 "none" 断言; 魔搭 i2v 官方无 API → caps=none, 编译期诚实拦截; cloud-nodes.html 过期 DOM 标记对齐现结构
- test_ref_images.py: 魔搭 maxRefs 1→3(对齐 6a313ce 官方 Edit-2509 收 1–3 张)
- test_e5_media_io.py: 空图不入库(o91)与合法上传两意图共存——1×1 空白图验 400, 16×16 非空白渐变图验 200 落盘
- test_o44: flux1 editImage maxRefs 9→2(以 docs/capabilities.json 官方 maxItems=2 为准)
- test_nanogpt_media_contract.py: 超大 seed 透传裁决; 新增 out/ fixture
- test_o57_six_catalog_stamp.py: fal overlay LoRA token 判定(six_catalog_caps.py)
- test_o46_resume_writeback.py、test_air_map.py(后端代理修)
- test_o47_composer_board_sync.py、test_lora_type_gate.py、test_o42、test_o45、test_o79_smart_match_six.js(bust→o135fix)、test_o101_shell.js、test_o112_attach.js、test_o48/o52/o53/o54/o54b/o90/o96(前端代理修)

## 代码改动
- providers/modelscope.py: 视频类 payload generate 级硬拒(400 中文诚实拒绝, 不拿 /images/generations 冒充)
- providers/capabilities.py: 魔搭两家 i2v="none"(官方 API-Inference 无视频任务, 实测 /v1/models 48 个全 LLM/VLM+图像编辑)
- providers/six_catalog_caps.py: fal overlay LoRA token 判定
- static/storyboard.js + smart-family-match.js + storyboard.html + composer-field-adapt.js: 帖子智能匹配四缺口(删 Krea2 写死默认死路径 / fam="" 清空+警告不播"已智能匹配" / 删跨家换家 / LoRA 搜索带 baseFamily 过滤+addLora 家族硬拒 / pickByFamily 活目录优先写死表兜底 / 跨家搜开关默认关)
- 常量 FAL/HF/MS_LORA_PREF_SERVICE 保留(o79 VM seam 依赖; 现仅承担 krea2 家族→端点的正确映射, 全部"未知家族套默认"用途已删)

## 现存 20 红分类(全部基线即红, 非本轮引入)
- 环境受限: test_workspace_delete_browser(需 --out 参数)、o127/o130/o131(需 127.0.0.1:8080, 被外部 Go 服务占用)、test_import_meta(需外网+fixture)、storyboard_graph(部分用例需外网)
- 过期断言待裁决(后端代理报告 #5/#6): test_fal_fields、test_o43(静默切片期望 vs fail-closed 现行语义)
- 其余静态戳/DOM 漂移类: astra3_gates、cloud_nodes×2、o39/o40/o41/o49b/o93、storyboard_catalog_paging/mojibake/persist_restore/ui

## 付费真机验证
未执行(Stage 3 待做): 本轮为离线单测层; 页面点选付费验证按 criteria.md 在 Stage 3 进行。
