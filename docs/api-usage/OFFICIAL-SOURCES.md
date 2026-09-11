# 官方 API 出处（2026-09-11）

对照仓库文档用。未页↑不报 Pass。闭环 0。

## Civitai Orchestration

- 索引：https://developer.civitai.com/orchestration/recipes
- Flux 2：https://developer.civitai.com/orchestration/recipes/flux2
  - Klein：`loras` = `{ "urn:air:…": strength }` map
  - Dev：`loras` = `[{ "air", "strength" }]` array（官方写明和 Klein 不同）
- WAN image：https://developer.civitai.com/orchestration/recipes/wan-image
  - `loras[]` = `[{ air, strength }]`
- HunyuanVideo：https://developer.civitai.com/orchestration/recipes/hunyuan
  - `loras` = `[{ air, strength }]`
- 提交：`POST https://orchestration.civitai.com/v2/consumer/workflows`

仓库错：`civitai.md` / field-board 写「一律 `{air:float}`」。

## Fal

- Queue：https://docs.fal.ai/model-apis/model-endpoints/queue
- 每端点 OpenAPI：`https://fal.ai/api/openapi/queue/openapi.json?endpoint_id=…`
- LoRA 常见形：`loras: [{ path, scale }]`（该端点 schema 有才发）
- duration / max images：只抄该端点 enum / maxItems，禁止发明 5/12/16 或默认 9

## Hugging Face Inference Providers

- https://huggingface.co/docs/inference-providers/guides/first-api-call
- 任务表：https://huggingface.co/docs/inference-providers/tasks/text-to-image
- 官方请求：`inputs` + `parameters.{guidance_scale,negative_prompt,num_inference_steps,width,height,scheduler,seed}`
- **无** `loras` 键；**无** seed max
- Router 不托管 `fal-ai/*lora` 独立 app

## ModelScope API-Inference

- https://www.modelscope.cn/docs/model-service/API-Inference/intro
- `POST {ai|cn}/v1/images/generations`
- seed：`[0, 2^31-1]`；没有 -1
- prompt / negative：长度 < 2000
- loras：单条 `"owner/repo"`；多条 `{repo: w}` 且和 = 1.0，最多 6
- image_url：仅编辑模型；Edit-2509 参考 1–3 张
- 禁止把未知写成 maxRefs=1 预拦

## NanoGPT Image API

- https://docs.nano-gpt.com/api-reference/endpoint/image-api-generate
- `POST /api/v1/images`
- 键：model, prompt, n, resolution, aspect_ratio, quality, output_format, seed, input_references
- **无** prompt max 1200；**无** seed 区间；**无** loras 键
- 能力看 `GET /api/v1/images/models` 的 `supported_parameters`
