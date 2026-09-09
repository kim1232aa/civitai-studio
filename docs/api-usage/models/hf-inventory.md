# Hugging Face 模型清单（inventory）
> 钉选源：`docs/hf-models.json`（**8** 条）。完整目录靠 Hub 实时搜索，无本地全量快照。
> 索引：[hf-index.json](hf-index.json)。

## 钉选模型

| id | name | category | task | tags |
| --- | --- | --- | --- | --- |
| `black-forest-labs/FLUX.1-schnell` | FLUX.1 schnell | image | text-to-image | t2i |
| `black-forest-labs/FLUX.1-dev` | FLUX.1 dev | image | text-to-image | t2i |
| `black-forest-labs/FLUX.1-Krea-dev` | FLUX.1 Krea | image | text-to-image | t2i |
| `Qwen/Qwen-Image` | Qwen Image | image | text-to-image | t2i |
| `Tongyi-MAI/Z-Image-Turbo` | Z-Image Turbo | image | text-to-image | t2i |
| `stabilityai/stable-diffusion-xl-base-1.0` | SDXL Base 1.0 | image | text-to-image | t2i |
| `tencent/HunyuanVideo` | HunyuanVideo | video | text-to-video | t2v |
| `Lightricks/LTX-Video-0.9.8-13B-distilled` | LTX Video distilled | video | text-to-video | t2v |

## 发现端点（代码）

| 用途 | URL / 行为 |
| --- | --- |
| Hub 搜索 | `GET https://huggingface.co/api/models?search=&limit=50`，pipeline ∈ t2i/i2i/t2v/i2v |
| LoRA 搜 | `GET …/models?search=&filter=lora` |
| Inference mapping | `GET {HUB}/{mid}?expand[]=inferenceProviderMapping` |
| 生成 Router | `POST https://router.huggingface.co/{provider}/{providerId}` 等 |
| Provider 偏好 | fal-ai → nscale → wavespeed → together → hf-inference；**跳过 replicate** |

## LoRA / 信心

- capabilities：`lora=path`，`loraConfidence=**unverified**`。
- 路由**没有** `…/turbo/lora` sibling（`_maybe_lora_pid` 保持 turbo）。
- OpenAI / hf-inference 通道不带或忽略 LoRA。

## 缺口

- 无离线全量 catalog；live Hub 结果不落盘到本 inventory。
- i2v：能力表 `i2v=none`；勿当稳定出片。
- 无 import 反查。
