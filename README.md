# Civitai Studio

本地云配方生成台。浏览器里选供应商、填参数、**自己点生成**。密钥只存在本机，不进页面、不进仓库。

- 地址：<http://127.0.0.1:8765>（只绑回环）
- 仓库：<https://github.com/kim1232aa/civitai-studio>
- 当前界面版本戳：标题栏 `v0756`（每次修 UI/行为都要改这个数字并 push main）
- 开发约定：[`docs/dev.md`](docs/dev.md)
- 审查规范：[`docs/review-spec.md`](docs/review-spec.md)
- 供应商插件：[`docs/providers.md`](docs/providers.md)
- 各家 LoRA / 自定义参数 / 代表问题：[`docs/provider-lora.md`](docs/provider-lora.md)

## 待解决问题（按提到的次数）

1. **P0 点生成必须出新成片**  
   Fal / Hugging Face / 魔搭 AI / 魔搭 CN 还没有一次「导入 + 写提示词 + 点生成」在成片栏出现新图。空提示词弹出「先写提示词」**不算过关**。这是产品标准。
2. **P0 魔搭会自己换台**  
   点「魔搭 AI / 魔搭 CN」后几秒，URL 自己漂到 `#fal` 或 `#huggingface`，不用再点。审查里反复出现。
3. **P0 审查必须看标题版本**  
   多次打回其实测的是旧标签（v0721 / v0731）。过关截图标题必须等于当时最新戳。关掉旧标签再硬刷新。
4. **P1 选模型不稳**  
   搜目录、切供应商、loadCatalog 会冲掉刚点的模型；橙框有时只是 hover。列表下应出现「已选 …」。
5. **P1 工作流页**  
   zip 能导入后：对照表曾被 HF 模型列表挤掉（`.svc-list{display:flex}` 盖掉 `hidden`）；刷新会丢导入；sidecar `config.json` / 纯 PNG 版本曾报「不是合法 JSON」。完整 Comfy 图（社区节点）仍不能当本地 Comfy 跑。
6. **P2 还没做完的能力**  
   Civitai 剩余配方进 UI（音频 / 3D / 试穿等）；Fal `request_id` + PNG 元数据反查；Fal 大目录一次渲染过多曾整页 `GET /` 并跳回 Civitai（已限 60 条，仍要防回归）。
7. **P2 LoRA 假信心**  
   魔搭丢掉 Civitai 下载链后仍出底模，页面只显示「好了」。HF 把 `loras[]` 附在没有 `/lora` 的 turbo 上，sidecar 有字段不等于上游加载。详见 [`docs/provider-lora.md`](docs/provider-lora.md)。

## 能干什么

- **Civitai**：图 / 视频 / customComfy。导入 Civitai 图抽参数。工作流按文件名和节点查 AIR，查不到就列 unmatched，不编 URN。
- **Fal.ai**：图、视频、放大、3D、音频。LoRA 走 `loras: [{path, scale}]`，无该字段时切目录里的 `/lora` 兄弟端点。目录不要一次画出全部按钮。
- **Hugging Face**：FLUX、Qwen、Z-Image-Turbo、HunyuanVideo。同步返回文件。路由没有 Fal `/lora` 端点；Civitai 链会塞进 mapped turbo 的 `loras[]`，是否生效未证实。
- **NanoGPT**：图 / 视频。官方目录 200+ 图模、LoRA、图生图、seed、比例。密钥 `~/.config/nano-gpt/token`。LoRA 用带 `-lora` 的模型 + Civitai/HF path。
- **魔搭 AI** 与 **魔搭 CN** 是两家，**禁止互相 fallback**。AI 连不上就报连接错误，不要改走 CN。LoRA 只要 Hub `owner/repo`，Civitai 下载链不能用。

## 跑起来

Python 3.11+，标准库，无 pip 依赖。

```sh
cd civitai-studio
chmod +x run.sh
./run.sh
```

重启：`python3 scripts/restart.py && ./run.sh`

成图：`out/`。静态页：`static/index.html`。

## 密钥路径

权限建议 `600`。缺 key 只在界面提示，不把密钥打到前端。

| 供应商 | id | 密钥 | 接口 |
| --- | --- | --- | --- |
| Civitai | `civitai` | `~/.config/civitai/token` | orchestration + site API |
| Fal | `fal` | `~/.config/fal/token`（`KEY_ID:KEY_SECRET`） | fal.run |
| Hugging Face | `huggingface` | `~/.config/huggingface/token` | router / Inference |
| 魔搭 AI | `modelscope-ai` | `~/.config/modelscope/token` | `https://api-inference.modelscope.ai/v1` |
| 魔搭 CN | `modelscope-cn` | `~/.config/modelscope-cn/token` | `https://api-inference.modelscope.cn/v1` |
| NanoGPT | `nano-gpt` | `~/.config/nano-gpt/token` | `https://nano-gpt.com/api/v1` |

不要用 `~/.config/modelscope/base_url` 把 AI 指到 CN。

## 注意

- 这是云 API 配方台，不是本地 ComfyUI。
- 不要代点「生成 / 预估 / 导入」。审查只截图、读代码、点页面，不调生成 API。
- 成人内容默认开。
- 不要把 token、`out/`、测试草稿 `docs/_p*.md` 提交进 git。
- 不要把「找替代 LoRA」写进产品代码当自动映射。
