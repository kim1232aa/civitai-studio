# 开发约定

和 [`README.md`](../README.md) 一起看。改行为先改这里对应的路径和禁区，再改代码。

## 仓库与本机路径

| 用途 | 路径 |
| --- | --- |
| 仓库根 | 本机 `civitai-studio/`（当前私有仓 `kim1232aa/civitai-studio`） |
| HTTP 入口 | `server.py`，`PORT` 默认 `8765` |
| 启动 | `run.sh` → `python3 server.py` |
| 重启 | `python3 scripts/restart.py` 然后 `./run.sh` |
| UI | `static/index.html`（单文件 Night Lab） |
| 适配器 | `providers/<id>.py`，注册表 `providers/__init__.py` |
| 工作流解析 | `providers/civitai_workflows.py` |
| PNG tEXt | `providers/io_meta.py` `parse_png_text` |
| 成片 | `out/`（不提交） |
| 能力/缓存文档 | `docs/` |
| AIR 缓存 | `docs/air-cache/files.json` `docs/air-cache/packs.json` |
| 工作流 fixture | `docs/workflows/<versionId>.json` |

绑定：`127.0.0.1:8765`。不要改成 `0.0.0.0`。浏览器地址栏用 `http://127.0.0.1:8765/#<backend>`。

## URL / 存储

| 键 | 位置 | 含义 |
| --- | --- | --- |
| `#civitai` `#fal` `#huggingface` `#modelscope-ai` `#modelscope-cn` | `location.hash` 第一段 | 当前供应商 |
| `&recipe=workflow` | hash 第二段 | 仅当工作流 tab 真的打开 |
| `civitai-studio-backend` | localStorage + sessionStorage | 供应商，刷新后还在 |
| `civitai-studio-recipe` | sessionStorage | 配方 tab；**不要**单靠它在 boot 时切到工作流 |
| `civitai-studio-wf` | sessionStorage | 上次导入的工作流 JSON |
| `civitai-studio-gallery-v2` | localStorage | 成片缩略图列表 |

`savedBackend()` 优先读 hash，再 session，再 local。hash 空时不要误用别家的 localStorage 把魔搭漂到 Fal。

## 供应商 id（不要写错）

| UI | `backend` | 适配器 |
| --- | --- | --- |
| Civitai | `civitai` | `providers/civitai.py` |
| Fal | `fal` | `providers/fal.py` |
| Hugging Face | `huggingface` | `providers/huggingface.py` |
| 魔搭 AI | `modelscope-ai` | `providers/modelscope.py` `ModelScopeProvider("ai")` |
| 魔搭 CN | `modelscope-cn` | 同上 `("cn")` |

别名：不要再把 `modelscope` 当成合并后的一家。AI 与 CN **禁止** token / base URL 交叉。

任务 id：`{backend}|{opaque}`。

## HTTP

前缀都在 `server.py`。

| 方法 | 路径 | 作用 |
| --- | --- | --- |
| GET | `/` `static/index.html` | UI，`Cache-Control: no-store` |
| GET | `/api/providers` | 供应商列表 + hasKey |
| GET | `/api/catalog?backend=&q=` | 模型目录。Fal 不要用 q 把本地目录滤成 1 条 |
| GET | `/api/defaults` | 默认宽高步数、是否有 Civitai token |
| GET | `/api/go` | 前端点到生成时打日志 `[web] GO_CLICK` |
| POST | `/api/generate` | 真正出图。空提示词不应发到这里 |
| POST | `/api/whatif` | 预估 |
| POST | `/api/import` | 导入 Civitai 图/视频参数 |
| GET | `/api/workflows` | Moody 收藏列表 |
| GET | `/api/workflows/import?url=` | 导入工作流（zip / JSON / PNG tEXt） |
| GET | `/api/jobs/<id>` | 轮询 |
| GET | `/out/<file>` | 成片文件 |
| GET | `/api/outs` | 磁盘成片清单 |
| GET | `/api/search` `/api/model-version/<id>` | Civitai LoRA / 版本 |

## 密钥文件

只读本机文件，不要写进 git、不要 `git config`、不要打到 HTML。

```
~/.config/civitai/token
~/.config/fal/token
~/.config/huggingface/token
~/.config/modelscope/token          # 仅魔搭 AI
~/.config/modelscope-cn/token       # 仅魔搭 CN
```

git 身份只用环境变量：`GIT_AUTHOR_NAME=kim1232aa`，`GIT_AUTHOR_EMAIL=193197560+kim1232aa@users.noreply.github.com`。不要 `git config`。

## 界面版本戳

`static/index.html` 里三处必须一起改：标题旁、`#go` 的 `title`、`#dockStatus` 文案里的 `v0xxx`。

规则：每修一个可感知行为 → 戳 +1 → commit → `git push origin HEAD`。审查截图对标题，不对 dock（dock 会被「已加载 N 个模型」覆盖）。

## 生成按钮

- `type="button"`，`onclick` + 捕获阶段 `click`。不要 `onmousedown`，不要 `disabled=true`（会吃掉随后的 click）。
- `__studioGo` 只负责 `GET /api/go` 和调用 `onGenerate`。不要在点击里 `persistBackend`。
- 校验（空提示词、没选模型、没工作流）必须在 `goBusy=true` **之前** `setDock(..., "bad")`。失败了 `loadCatalog` 不得盖掉 `.bad`。
- 通过校验后按钮文案「提交中…」，再 `POST /api/generate`。
- **禁止代点生成 / 预估 / 导入**。审查员只点页面、截图、读代码，不跑生成 API。
- 产品过关：成片栏出现**新文件**。空提示词「先写提示词」不是过关。

## 模型列表

- Fal 目录可见行 `CAP = 60`，其余靠搜索。
- `userPickedId`：用户点行才写。搜目录 / `loadCatalog` 不得 `pickForBackend()` 冲掉已选手选。
- 切供应商时清空 `userPickedId`，再按导入类比选 Z-Image-Turbo 等。
- `.svc-list` 是 `display:flex`。隐藏必须用 `.hidden`（`display:none !important`）和 `[hidden]`，单靠 `hidden` 属性会被 flex 顶掉。

## 导入

- 文案始终「导入 Civitai 图/视频」，所有 backend 都能导入 Civitai 图。
- 文生图导入不要把 `mediaUrl` 填进 `sourceImage` / `firstFrame`（否则会变成图生图并错配模型）。
- 底模类比：Civitai Z Image Turbo → Fal `fal-ai/z-image/turbo`（有 LoRA 用 `.../lora`）→ HF/魔搭 `Tongyi-MAI/Z-Image-Turbo`。不要凭 `selected.id` 嗅探 Krea。
- 审查夹具：`https://civitai.red/images/139791102`（hinablue，Z Image Turbo）。

## 工作流

- 选文件：zip（名里带 workflow 优先）> 真 Comfy JSON > PNG > sidecar `config.json`。`.yaml` 不当图。
- `import_workflow` 按排序逐个下载，`parse_workflow_bytes` 失败试下一个。
- `parse_workflow_bytes`：`PK` 拆 zip 里最大的 Comfy JSON；`\x89PNG` 走 `parse_png_text` 的 `workflow` / `prompt` tEXt；不要对 PNG 直接 `json.loads`。
- `customComfy` 的 `comfyImage` 只接受已是 `urn:air:...comfyimage...` 的 AIR，**不要**把 `firstFrame` 写进去。
- 工作流 tab 必须藏 `#serviceList` `#svcFilter` `#svcPicked` `#importBlock`，只留 `#wfPanel`。AIR 用表格，不要一长串逗号。
- 全部 unmatched 且没有 resources 时生成要拦。

## 审查

- 过关截图标题 = 当前戳。旧标签直接打回。
- 不要对 8765 开 browserUse / 桌面自动化（抢焦点）。
- 魔搭 AI 在部分机器上 `api.modelscope.ai` 解析失败 → 应 502/连接错误，不是切 CN。

## 提交

```
GIT_AUTHOR_NAME=kim1232aa \
GIT_AUTHOR_EMAIL=193197560+kim1232aa@users.noreply.github.com \
git commit ... && git push origin HEAD
```

不要提交：`out/`、token、`docs/_p*.md` 测试草稿、`docs/p0-hinablue.png` 这类审查截图（除非明确当 fixture）。
