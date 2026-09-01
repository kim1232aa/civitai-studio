# 供应商插件

每个云厂商一个文件，放在 `providers/`。HTTP 路由只认注册表 `providers/__init__.py`。

LoRA / 自定义参数 / 代表问题的实测表：[`provider-lora.md`](provider-lora.md)。

## 会复用

JSON 请求、落盘 `out/`、任务 id `{provider}|其余`、目录过滤、`GET /api/providers`、UI 从 `/api/providers` 画切换条。

## 不要复用

鉴权头、出图字段、预估费用、Civitai 导入 / 配方 / 搜模型 / 工作流 AIR。

## 现有 id

见 [`dev.md`](dev.md) 的供应商表。魔搭是 **两家**：`modelscope-ai` 与 `modelscope-cn`，token 和 base URL 都不共用。NanoGPT 是独立一家：`nano-gpt`，token 在 `~/.config/nano-gpt/token`，不要和 Fal / HF 混用。

## LoRA 一句话

| id | 官方 LoRA | Civitai 下载链 |
| --- | --- | --- |
| `civitai` | AIR / versionId | 官方 |
| `fal` | `loras[{path,scale}]`，可切 `/lora` 兄弟端点 | 可用 |
| `huggingface` | 附在 mapped turbo 的 `loras[]`（路由无 `/lora`） | 会发出去，上游是否加载未证实 |
| `modelscope-ai` / `modelscope-cn` | Hub `owner/repo` | 不能用（500 空 modelName，现跳过） |
| `nano-gpt` | `loras[{path,scale}]` | 在 `*-lora` 模型上可用 |

不要做 Civitai→Hub 自动换模。

## 加一家

1. 写 `providers/foo.py` 实现 Provider（`id` `label` `has_key` `catalog` `generate` `job`）。
2. token 放 `~/.config/foo/token`。
3. 文件末尾 `register(FooProvider())`。
4. 任务 id `foo|{opaque}`。
5. `python3 scripts/restart.py && ./run.sh`。

不要在新适配器里 fallback 到另一家的 token 或域名。
