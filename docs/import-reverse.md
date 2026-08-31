# Import reverse-lookup (Fal / HF / 魔搭 / Civitai)

Research 2026-09-01. Docs + GET only. No generate POST. No tokens here.

Legend: **有** = image URL/id → params API; **仅 job 回放** = own request_id/job_id → original input; **仅文件元数据** = PNG tEXt / Comfy / A1111 on the file; **无**.

## Verdict

| backend | 从图 URL/id 反查 | 用自己的 job/request id 回放 input | 成图 PNG 元数据（跨厂商本地） | Studio 可映射 |
|---|---|---|---|---|
| Civitai | **有** | **有** | 有则解析；主路径是 tRPC 不是 PNG | prompt / negative / size / steps / cfg / sampler / scheduler / seed / checkpoint AIR / LoRAs / serviceId |
| Fal | **无** | **仅 job 回放** | 文档未写会嵌入 parameters；有 tEXt 才本地解析 | json_input：prompt, steps, size, seed, guidance, image_url… 无 AIR |
| Hugging Face | **无** | **无**（同步，无 job store） | 同上，仅文件里真有 chunk | 无云字段；只能靠 Studio 当时存的 `submittedInput` |
| 魔搭 | **无** | **无**（GET task 文档只有 status + output_images） | 同上 | 无云字段；只能靠 `submittedInput` |

不要第五家。

## Civitai（已接）

1. 图 id：`GET https://civitai.com/api/trpc/image.getGenerationData?input={"json":{"id":N}}` + `image.get`。`providers/civitai.py` `import_image`。
2. job：`GET https://orchestration.civitai.com/v2/consumer/workflows/{id}` → `steps[].input`。现场 imageGen keys：`width,height,prompt,sampler,scheduler,steps,cfgScale,seed,quantity,loras,ecosystem,engine,outputFormat`。
3. 文件：A1111 `tEXt parameters` / Comfy `prompt`+`workflow` 是通用本地解析，不是 Civitai API。

## Fal

1. 无「给 CDN 图 URL 返回 prompt」的接口。`v3.fal.media` 不是图库。
2. job 回放（已 GET 200）：
   - `GET https://api.fal.ai/v1/models/requests/by-endpoint?endpoint_id={id}&request_id={uuid}&expand=payloads`
   - 文档：https://fal.ai/docs/platform-apis/v1/models/requests/by-endpoint
   - 鉴权 `Authorization: Key`。返回 `items[].json_input` + `json_output`。现场 flux/schnell `json_input` keys：`prompt`, `num_inference_steps`, `image_size`。
   - Queue `GET queue.fal.run/{endpoint}/requests/{id}` 是**结果**不是 input；本账户一条已完成请求对该 URL 返回 **405**（队列结果过期，历史仍在 platform API）。
   - `X-Fal-Store-IO` 会禁止存 payload，那时 expand=payloads 为空。默认存 30 天。
3. PNG：官方 queue/OpenAPI **没有** 写入 A1111/Comfy chunk 的承诺。

映射：`json_input.prompt`→prompt；`num_inference_steps`→steps；`image_size` `{width,height}` 或枚举→width/height；`guidance_scale`→cfgScale；`negative_prompt`→negativePrompt；`seed`；`image_url`→firstFrame。`serviceId`=endpoint_id。无 checkpoint AIR / LoRA。

## Hugging Face

Inference 是同步 POST `router.huggingface.co/hf-inference/models/{id}`，返回图字节。无 request store、无 GET-by-id。文档：https://huggingface.co/docs/huggingface_hub/en/guides/inference 。Studio `job_status` 直接 succeeded。无云回放。

## 魔搭

`GET https://api-inference.modelscope.cn/v1/tasks/{task_id}` + `X-ModelScope-Task-Type: image_generation` 文档/示例只有 `task_status` 与成功后的 `output_images`。没有「原 prompt」字段（不要和阿里云 DashScope `orig_prompt` 搞混）。无图 URL 反查。未 POST 新 task。

## 跨厂商文件元数据（不是云 API）

PNG `tEXt`/`iTXt`：Automatic1111 `parameters`；ComfyUI `prompt` + `workflow`。有就解析，没有就空。Fal/HF/魔搭官方都没保证写出这些 chunk。
