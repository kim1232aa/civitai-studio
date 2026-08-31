# Civitai Studio

本地云配方生成台。浏览器里选供应商、填参数、自己点生成。密钥只存在本机 `~/.config/`，不会进页面也不会进仓库。

默认地址：[http://127.0.0.1:8765](http://127.0.0.1:8765)

## 能干什么

- **Civitai**：编排配方（图 / 视频 / customComfy）。导入图片会抽参数；Comfy 工作流会按文件名和节点类型查 AIR，查不到就空着，不编 URN。
- **Fal.ai**：图、视频、放大、3D、音频。字段按 OpenAPI 推断（Kling o3、Hailuo、Runway `ratio`、LTX `audio_url` 等）。
- **Hugging Face**：FLUX、Qwen Image、HunyuanVideo。同步返回文件。
- **魔搭**：Qwen Image / Edit（异步）。`api.modelscope.ai` 不通时走 `api-inference.modelscope.cn`。

界面是 Night Lab。生成按钮不会自动点。

## 跑起来

需要 Python 3.11+，标准库即可，没有 pip 依赖。

```sh
git clone <this-repo>
cd civitai-studio
chmod +x run.sh
./run.sh
```

浏览器打开 `http://127.0.0.1:8765`。只绑本机回环。

成图写到仓库旁的 `out/`。

## 密钥

每家一个文件，权限建议 `600`：

| 供应商 | 路径 | 格式 |
| --- | --- | --- |
| Civitai | `~/.config/civitai/token` | Bearer token |
| Fal | `~/.config/fal/token` | `KEY_ID:KEY_SECRET` |
| Hugging Face | `~/.config/huggingface/token` | `hf_…` |
| 魔搭 | `~/.config/modelscope/token` | ModelScope token |

可选：`~/.config/modelscope/base_url` 覆盖推理地址。

缺 key 的供应商在界面里会显示没配，不会把密钥打到前端。

## 目录

```
server.py            HTTP（stdlib ThreadingHTTPServer）
providers/           一家一个适配器
static/index.html    Night Lab UI
docs/                能力表、OpenAPI 缓存、AIR 查找说明
scripts/restart.py   重启本机服务
samples/             工作流样例（Moody 只当 fixture）
```

加一家供应商：写 `providers/foo.py`，实现 Provider，token 放 `~/.config/foo/token`，文件末尾 `register(...)`，重启。细节见 `docs/providers.md`。

## 注意

- 这是云 API 配方台，不是本地 ComfyUI。Civitai customComfy 跑不了社区节点全图；没有接 Comfy Cloud / RunComfy。
- 成人内容开关默认开（`allowMatureContent`），跟 Civitai 账号策略走。
- 不要把 token、`out/`、截图提交进 git。
