# Studio 本地路由

入口：`server.py` `Handler`，默认 `127.0.0.1:8765`。注册表：`providers/__init__.py`。

**对接探测允许**：GET health / providers / catalog。**禁止**对本机或生产 POST `/api/generate` 做文档验证。

## 总览

| 方法 | 路径 | 作用 |
| --- | --- | --- |
| GET | `/api/providers` | 六家 `{id,label,hasKey,categories,capabilities}` |
| GET | `/api/catalog?backend=&q=&category=&status=&refresh=` | 各家目录 |
| GET | `/api/defaults` | Civitai defaults + hasKeys + providers |
| GET | `/api/capabilities` | `docs/capabilities.json`（Civitai 引擎级） |
| GET | `/api/health` | Civitai orchestration health |
| GET/POST | `/api/import` | 导入（永不触发 generate） |
| POST | `/api/upload-out` | dataUrl → `/out/upload_…` |
| POST | `/api/generate` | 出图/视频（**文档勿打**） |
| POST | `/api/whatif` | 预估 |
| GET | `/api/jobs` | Civitai 工作流列表 |
| GET | `/api/jobs/{id}` | 按 backend 前缀路由 `job_status` |
| POST/DELETE | `/api/jobs/{id}/cancel` | cancel（仅 civitai/fal 真有） |
| POST | `/api/graph/compile` | 画布编译 |
| GET | `/api/search?backend=&q=&type=` | LoRA 搜索 |
| GET | `/api/model-version/{id}` | Civitai 版本 + downloadUrl |
| GET | `/out/{file}` | 成片 |
| GET | `/api/outs` | 最近 60 个成片 |
| POST | `/api/catalog/refresh` | 刷 Civitai 目录 |
| POST | `/api/recipes/{name}` | Civitai recipe |

## `/api/providers`

`providers.list_public()` ← `get_provider_capabilities(id)`。缺字段或静默全开 = P0。六家 id 见 README。

## `/api/catalog`

`backend` 默认 civitai。`refresh=1` 仅 civitai 调 `refresh_catalog`。Fal：q 不收缩本地全量。

## `/api/import`

`handle_import(backend, q, file_bytes, filename, endpoint)`：

1. 有文件 → PNG/Comfy/A1111 解析 + 可选 sidecar。
2. q 像 Civitai（数字 id / civitai.com /images/）→ `import_image`（**强制 backend 语义落 civitai**）。
3. backend=fal → `fal.import_request`。
4. hf/魔搭/nano → empty + 说明文案。

GET 与 POST 同源；POST 可带 `fileB64`。

## `/api/upload-out`

Body：`{dataUrl, filename?}` → `{file,url:/out/…,bytes,kind,contentType}`。供 storyboard 本地上传；Fal generate 前 materialize。

## `/api/generate` / `/api/whatif`（说明 only）

流水线：

1. generate：`reject_staged_generate`（禁止未物化的 stage-out 引用）。
2. `normalize_payload_refs`（并集镜像到 `images`）。
3. `resolve_from_payload` → `prov.generate` / `whatif`。

Studio 常用 payload 键：`backend`、`serviceId`、`prompt`、`negativePrompt`、`seed`、`width`/`height`、`steps`、`cfgScale`、`loras`、`firstFrame`/`images`/`image_urls`/`input_references`、`kind`、`denoise`、`quantity`、`duration`、`aspectRatio`、`allowMatureContent`、`resolution`。

各家字段映射见对应 provider doc。

## `/api/jobs`

- 列表 GET `/api/jobs`：仅 Civitai orchestration 列表。
- 单条：`resolve_from_job`（id 前缀 fal|、hf|、modelscope-ai|、nano-gpt|…）。
- 成功时各家 `saved` → `out/` + sidecar。

Cancel：`capabilities.cancel` 为 True 的家（civitai、fal）；其余 400「没有取消接口」。

## `/api/graph/compile`

`providers/graph_compile.py`：`compile(graph)` 只沿边取 prompt/image/seed/loras；未连口不偷全局。出站再进 `/api/generate`。

## 参考图合同（全路由）

见 `docs/hard-gate-wiring.md` + `ref_images.py`：

| backend | maxRefs | refImagesField |
| --- | --- | --- |
| civitai | 9 | images |
| fal | 9（单图 schema→1） | image_urls |
| huggingface | 9 | image_urls |
| nano-gpt | 5 | input_references |
| modelscope-* | 1 | image_url |

## Code anchors（server.py）

| 路由 | 行（约） |
| --- | --- |
| `handle_import` | `:517-592` |
| `save_upload_out` | `:673-720` |
| GET providers/catalog/health/jobs/import | `:812-915` |
| POST import/upload-out/generate/whatif | `:1001-1050` |
| cancel | `:754-762`, `:1065-1073` |

## Capabilities 合并

Catalog item 可带 `capabilities` / `supportsLora` / `imageFields` / `maxRefs`；服务端 `merge_catalog_override` **只许收紧**。
