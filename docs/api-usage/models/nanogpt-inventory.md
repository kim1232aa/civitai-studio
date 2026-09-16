# NanoGPT 模型清单（inventory）
> **仓库无离线全量目录**。运行时 `providers.nanogpt.fetch_catalog` 合并图+视频（TTL 300s）。
> 机器可读说明：[nanogpt-index.json](nanogpt-index.json)。 Studio：`GET /api/catalog?backend=nano-gpt`。

## 发现端点

| 用途 | URL |
| --- | --- |
| 图模型 | `GET https://nano-gpt.com/api/v1/images/models` |
| 视频模型 | `GET https://nano-gpt.com/api/v1/video-models` |
| 出图 | `POST /api/v1/images`（回退 `/v1/images/generations`） |
| 视频 | `POST /api/generate-video`；状态 `GET /api/video/status?requestId=` |
| 官方文档 | https://docs.nano-gpt.com/introduction |

## Studio 实测 / 文档点名样本

| id | supportsLora | 备注 |
| --- | --- | --- |
| `z-image-turbo-lora` | True | 实测 Civitai 下载链 LoRA |
| `wavespeed-ai/krea-v2/turbo-lora` | True | 实测 Civitai 下载链 LoRA |
| `z-image-turbo` | False | 普通 turbo；不保证吃 LoRA — 优先 *-lora |

## supportsLora 判定（代码）

- 图：`*-lora` / id·name·tags 含 `lora`；**upscale/bg/utility 禁止**因裸子串标 true（v0771）。
- 出站：`model_supports_lora` 假 → 400 `lora_model_unsupported`；无直链 → 400 `lora_no_direct_url`（fail-closed）。
- 分辨率：必须目录 `supported_parameters.resolutions` token；空目录 → 400。
- prompt：官方 schema 无 max；o150 实测 fail-closed 400（HTTP 400 `prompt_too_long`）；目录 metadata 优先；禁止发明 1200、禁止静默截断。

## 缺口

- 未在本仓库落盘完整 models JSON（需有效 token 拉 live）。对接请用 Studio catalog 或官方 API。
- 视频 progress 仍为 None（capabilities.progress=none）。
