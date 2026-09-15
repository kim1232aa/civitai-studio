# 2026-09-15 nano-t2v 状态解析修复 + t2v 三家实发验证

## 背景

round2 期间发现 nano-t2v 页面点击后永远 pending。curl 直探上游证实两单早已 COMPLETED
且有成片 URL，定位为本地状态解析 bug（详见 HANDOFF §3.1-4）。本轮修复并回归。

## 修复

- providers/nanogpt.py `job_status`：视频状态优先读内层 `data.data.status`
  （上游实测为大写 "COMPLETED"，映射表已覆盖 completed→succeeded）；
  progress/eta/error 同步读内层。成片 URL 由 `_save_result` → `collect_urls`
  兜底抓取嵌套 `data.output.video.url`，无需额外改动。

## 验证记录（全部为真机页面点击 / 真实 API）

| 项 | 命令 | 结果 |
|---|---|---|
| 历史任务1 状态回收 | `curl /api/jobs/nano-gpt\|vid\|vid_mu280ovk2ef76402eaa5` | succeeded，落盘 nano-gpt_vid_vid_mu280ovk2ef76402eaa5_0.mp4（2,560,391 B，h264 832x480 5.184s，minimax/h3-max） |
| 历史任务2 状态回收 | `curl /api/jobs/nano-gpt\|vid\|vid_mu28q15s1c511dbc9e4e` | succeeded，落盘 nano-gpt_vid_vid_mu28q15s1c511dbc9e4e_0.mp4（3,883,505 B，h264 854x480 5.056s，seedance-2.5） |
| nano-t2v 页面点击全链路 | `NANO_T2V_SID=bytedance/seedance-2.5 node scripts/round2_verify.mjs nano-t2v` | ok=true，「此镜完成，已写入卡片」，400.6s 出片 nano-gpt_vid_vid_mu29syxh2f4d2d5fd0f1_0.mp4（3,595,260 B，h264 854x480 5.042s），硬刷 persisted=true、shotMediaAfterReload=1，negative 参数成功发送（seedance 官方支持） |
| fal-t2v（前一轮，本次复证出站模型） | `node scripts/round2_verify.mjs fal-t2v` | uservspick 修复后出站确为用户手选 fal-ai/minimax/video-01；先撞 negativePrompt 诚实硬拒，清负重发 200 出片，硬刷保持 |
| civ-t2v（前一轮） | `node scripts/round2_verify.mjs civ-t2v` | wan v2.2 文生视频出片 out/12100372-20260915050557546_0.mp4，硬刷保持 |

## 回归（全绿）

| 套件 | 结果 |
|---|---|
| node --check static/storyboard.js | OK |
| test_o133_family_smart_match | PASS |
| test_nanogpt_media_contract | PASS 106 |
| test_fal_parameter_contract | 26 tests OK |
| test_storyboard_graph（带代理，含 civitai 活样本导入） | 75/75 |
| run_ui_eval | 32/32 |
| test_o42_nano_edit_refs | 38 checks ok |
| test_o47_composer_board_sync | PASS |
| test_o58_composer_caps | PASS |
| test_o59_composer_prompt | PASS |

## 运维备注

- 18832 测试服曾因启动命令误读不存在的 `~/.config/nanogpt/token` 而以空 key 运行：
  状态查询（上游该端点不强制鉴权）正常返回，generate 却 401「没有 NanoGPT API Key」，
  排查极具迷惑性。nano/HF/魔搭 key 只存在于 env_up.sh / bootstrap.sh 的内联启动行。
