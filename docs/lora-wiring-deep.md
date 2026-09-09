# LoRA 接线深挖（v0753）

夹具：Civitai version `3231694` → `https://civitai.com/api/download/models/3231694`。
看生效用 sidecar `submittedInput`，不要只看成片。UI 成功路径不读 `generate.warning`。

## 总流程

1. UI `#loraQ` → `GET /api/search?type=LORA&backend=` → 各家 `search_loras`（Civitai 默认搜社区）。
2. `payload().loras[]` 带 `air/path/url/versionId/scale`。
3. `slimPayload` 非 Civitai 仍保留 path 形态；切供应商不自动换 Hub 仓库。
4. 各 `generate()` 自己翻译；禁止 Civitai→Hub 静默对照表。

## Civitai

- 搜：`GET civitai.com/api/v1/models?types=LORA&query=`
- 提交：`lora_map` → `inp.loras = {air: strength}`；无 air 的条目直接丢。
- Hunyuan：dict 再展成 `[{air,strength}]`。
- 导入图：tRPC resources + `<lora:name:w>` prompt 标签；versionId → AIR。
- 工作流 resources 也是 AIR，unmatched 不编 URN。
- **Civitai 下载链**：官方资源体系，不靠 http path。

## Fal（目录约 1492，supportsLora≈160）

路径解析 `_fal_lora_path`：

1. `path` / `url` / `downloadUrl`（非 `urn:air:`）
2. 否则数字 `versionId` → 拼 Civitai 下载链
3. AIR / `urn:` **永不**当 path

字段形状 `_lora_field_shape`：优先 OpenAPI `loras` / `lora_url` / `lora_path` / `lora`；id 含 lora 默认 `loras`。实测 shape 计数：`loras` 136，名含 lora 但无字段 `?` 24。

端点重写 `fal_lora_sibling`（有 LoRA 时）：

1. 当前 id 已支持 → 不动
2. `{id}/lora` 在目录 → 切过去（`z-image/turbo`→`…/turbo/lora`）
3. `{id}/…` 且含 lora
4. 连字符模糊（`flux/dev`→`flux-lora`，`flux/krea`→`flux-krea-lora`）
5. 找不到 → **不塞 loras**（避免 422）

`apply_fal_loras` 按 shape 写入；scale 钳 `[0,4]`。

注意：`krea/v2/large/text-to-image` sibling=`(none)`，挂 LoRA 不会改端点也不会硬塞。`serviceId` 可能被改成 `/lora` 兄弟，sidecar 为准。

## Hugging Face

生成：`POST router.huggingface.co/{provider}/{providerId}`。

- `_maybe_lora_pid`：**不**切到 Fal `/lora`（路由 404「Model not supported」）。
- fal 通道：先 `apply_fal_loras`（mapped id 多半无 lora 字段 → 空），再 `_force_loras` **硬塞** `loras[{path,scale}]` 最多 3 条（Civitai http 可用）。
- OpenAI 兼容通道（nscale 等 `POST …/v1/images/generations`）：官方无 `loras`，忽略。禁止发明字段。**不是**整家 HF 不能 LoRA。
- `hf-inference` bytes：无 LoRA。
- replicate：禁止 POST。
- 搜：`GET huggingface.co/api/models?search=&filter=lora` → 选中的是 Hub `owner/repo`，但 fal 通道实际更吃 http/Civitai 链。

**假信心**：200 + 成片 ≠ 非 `/lora` 端点一定加载了权重。

## 魔搭 AI / CN

- 出站（2026-09-08 实测）：`loras: [{ "model": "owner/repo", "weight": 0.8 }, …]`（**单条也用数组对象**）。
- 字符串 `"owner/repo"` 或 `{repo: weight}` 会 500「Model does not exist」。详见 [`modelscope-hub-lora.md`](modelscope-hub-lora.md)。
- `_modelscope_loras`：**丢弃**所有 `http(s)://`（Civitai 链不能用）；只要恰好 `owner/repo`。
- 全是 http / AIR → `loras` 不进 body，`warning` 写回 API；**UI 不显示**。
- 搜：Hub `search={q} lora`，结果 id 即 repo。
- AI/CN 分 token/base，禁止互切。不要做 Civitai→Hub 自动换模。

## NanoGPT

- 搜：仍走 `/api/search`；目录 id 名带 `lora` 的约 15 个（如 `z-image-turbo-lora`、`wavespeed-ai/krea-v2/turbo-lora`、`flux-lora`…）。
- `_loras`：path/url/downloadUrl；AIR 丢；数字 versionId→Civitai 链；最多 3 条；scale `[0,4]`。
- body：`loras[{path,scale}]` **且** `lora_1_url` / `lora_1_scale` …
- 普通 `z-image-turbo` **不保证**吃 LoRA；应用 `*-lora` 模型。
- 图生图只 `input_references`+`strength`，勿混 image 字段。

## 对照

| 家 | path 形态 | Civitai http | 无字段时行为 | 搜什么 |
|---|---|---|---|---|
| Civitai | AIR | n/a（AIR） | 无 air 丢弃 | 社区 LORA |
| Fal | http / HF repo | 可用 | 切 `/lora` sibling 或跳过 | 仍常搜 Civitai；path 用下载链 |
| HF | 同 Fal path | 会塞进 fal 通道 | 硬塞 mapped turbo | Hub `filter=lora` |
| 魔搭 | Hub owner/repo | **不能用** | 跳过 + warning | Hub |
| Nano | http | 在 `*-lora` 可用 | 非 lora 模型不保证 | 宜选目录 lora 模型 |

## 不要做

- Civitai LoRA 自动映射成 Hub 仓库
- 用成片证明 LoRA 生效
- 魔搭 AI 失败切 CN
- 把 HF 硬塞写成「官方 /lora 端点」
