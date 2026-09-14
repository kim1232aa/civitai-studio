# 运行记录 2026-09-14 t2v 改动后全量回归

## 命令
- `python3 scripts/test_storyboard_graph.py`（需 `https_proxy=http://127.0.0.1:7890`，否则 civitai 活样本用例网络超时）
- `PW_VERSION_OVERRIDE=1.56.1 PORT=18832 node scripts/run_ui_eval.mjs`
- `python3 scripts/test_o42_nano_edit_refs.py`
- `python3 scripts/test_nanogpt_media_contract.py`
- `python3 scripts/test_fal_parameter_contract.py`

## 结果（exit 全 0）

| 套件 | 结果 |
|---|---|
| storyboard_graph | 75/75（含 t2v op 新增后零回归；test_import_19201654_original_params 为活样本，须代理） |
| run_ui_eval | 32/32 PASS |
| o42_nano_edit_refs | 38 checks ok |
| nanogpt_media_contract | 106 assertions PASS |
| fal_parameter_contract | OK |

## t2v 编译冒烟（内嵌 python）
- modelscope-ai t2v → 诚实硬拒（duration 能力门/无视频 API，均被拦）
- fal / civitai / nano-gpt t2v → 编译通过，payload kind=video、prompt 连线值正确

## 关联提交
- 4e4739b（被验改动）、ccc2c77（驱动）
