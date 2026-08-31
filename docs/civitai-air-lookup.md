# Civitai AIR lookup (filename → AIR, class_type → nodepack)

Research: 2026-09-01 ~05:53–06:15 CST (UTC+8). GET-only. No POST generation (`POST /v2/consumer/workflows`, `POST /v2/consumer/recipes/*` unused). Token never written to these files or stdout. `server.py` untouched.

Auth (existing scripts): `Authorization: Bearer <token>` from `/home/box/.config/civitai/token` (`fetch_openapi.py`, `server.py` `civitai()`). Site REST model-version GETs work **without** auth. Orchestration `GET /v2/resources/{air}` is **401** without Bearer (empty body). `GET /v2/services` is public (200 unauthenticated).

---

## 1. customComfy resource item schema

Source: `/workspace/civitai-studio/docs/_raw/customComfy.openapi.yaml` (`CustomComfyInput`). Live `GET https://orchestration.civitai.com/v2/consumer/recipes/customComfy/openapi.yaml` **200**, same schema. Catalog row `utility/customComfy` (status `degraded`). Capabilities required: `resources`, `trace`, `workflow`.

**`resources` is `string[]`, not objects.** There is no per-item `{air, type, filename}` schema. Each entry is one AIR URN. `minItems: 1`. Orchestrator does **not** scan the graph.

Quoted fields:

| Field | Required | Type | Notes |
|---|---|---|---|
| `resources` | yes | `string[]` (min 1) | AIR URNs: checkpoints/loras/vae **and** `comfy:nodepack`. Example in schema: `urn:air:comfy:nodepack:comfyregistry:kijai/comfyui-kjnodes@1.4.0`. Missing refs fail at Comfy load. |
| `workflow` | yes | opaque | Raw ComfyUI graph. Not inspected. |
| `trace` | yes | enum `none` \| `logs` \| `binary` | Comfy `/ws` recording. |
| `sessionId` | no | string \| null | Worker session affinity. |
| `comfyImage` | no | AIR string \| null | `urn:air:oci:image:<source>:<repo>@<tag\|sha256:…>` e.g. `urn:air:oci:image:ghcr:civitai/civitai-spine-comfy@v2.5.5`. |
| `sessionOwnerApiToken` | no | string \| null | **Sensitive** — do not log. Forwarded as `CIVITAI_API_TOKEN`. |
| `minVramGb` | no | int32 \| null | Scheduler VRAM floor. |
| `useSageAttention` | no | bool \| null | `--use-sage-attention`. |
| `minimumDurationSeconds` | no | int32 \| null | Submit-time affordability gate. |

AIR pattern (same regex on `comfyImage` and many other recipe fields):

```
^(?:urn:)?(?:air:)?(?:(?<ecosystem>[a-zA-Z0-9_\-\/]+):)?(?:(?<type>[a-zA-Z0-9_\-\/]+):)?(?<source>[a-zA-Z0-9_\-\/]+):(?<id>[a-zA-Z0-9_\-\/\.]+)(?:@(?<version>[a-zA-Z0-9_\-\/.=,%+:]+))?(?:\.(?<format>[a-zA-Z0-9_\-]+))?$
```

`GET /v2/consumer/recipes/customComfy` (no body) → **405** Method Not Allowed. Submit is POST-only (not called).

**Snapshot layer vs bare pack:** `comfyNodepackSnapshot` output `layerAir` is `urn:air:comfy:nodepacklayer:…@<ver>+<hex(image)>`. That recipe’s OpenAPI says consumers should declare **`layerAir`** on customComfy `resources` (not the bare pack). customComfy’s own description still lists bare `comfy:nodepack` URNs. Snapshot submit is POST — not probed.

---

## 2. AIR format (public docs)

Docs: https://developer.civitai.com/site/guide/air

Canonical:

```
urn:air:{ecosystem}:{type}:{source}:{id}[@{version}][+{fileId}][.{format}]
```

`urn:` and `air:` prefixes are optional; parsers accept full, `air:…`, and bare `sdxl:checkpoint:civitai:827184@2514310`. **Use full `urn:air:…` in API requests.** Live `GET /v2/resources/{short}` and `air:…` both **200** and echo canonical `urn:air:…`.

| Segment | Role |
|---|---|
| ecosystem | `sd1`, `sdxl`, `flux1`, `krea2`, `comfy`, `oci`, `other`, … (optional in grammar) |
| type | `checkpoint`, `lora`, `embedding`, `vae`, `controlnet`, `upscaler`; file-kind overrides `diffusionmodel` / `unet`; nodepacks use `nodepack`; containers `image` |
| source | `civitai`, `civitai-r2`, `huggingface`, `orchestrator`, `comfyregistry`, `ghcr`, `dockerhub` |
| id | For `civitai`: model ID. For nodepack: `publisher/pack` (slash is part of id) |
| version | For `civitai`: model **version** ID. For nodepack: semver/tag |

Prefer the site-generated `air` field over hand-construction. `GET /v2/resources` canonicalizes ecosystem (sent `urn:air:sdxl:lora:civitai:82098@87153` → returned `urn:air:sd1:lora:civitai:82098@87153`).

Nodepack pattern (OpenAPI example, live-confirmed):

```
urn:air:comfy:nodepack:comfyregistry:{publisherId}/{nodeId}@{version}
```

---

## 3. Filename → Civitai AIR — GET endpoints that exist

**There is no GET `/model-versions/by-filename` (404).** Filename is not a first-class lookup key. Reliable path is **hash or version id → `.air`**. Fuzzy `models?query=` is not exact `files[].name` match.

### Working GETs (where AIR lives)

| Method | URL | Auth | Status | AIR location | Notes |
|---|---|---|---|---|---|
| GET | `https://civitai.com/api/v1/model-versions/{id}` | public | **200** (id `2514310`) | **top-level `air`** | Also `modelId`, `model.type`, `files[].name`, `files[].id`, `files[].hashes.{SHA256,AutoV1,AutoV2,AutoV3,BLAKE3,CRC32}`, `files[].primary`. Nested `GET /models/{id}` **versions do not include `air`**. |
| GET | `https://civitai.com/api/v1/model-versions/mini/{id}` | public | **200** | **top-level `air`** | Also `fileName`, `hashes`, `downloadUrls`, `canGenerate`. `fileName` can differ from `files[].name` on the full version (v2514310 mini=`WAI-Nsfw-Illustrious-16.safetensors`, full `files[0].name`=`waiIllustriousSDXL_v160.safetensors`). |
| GET | `https://civitai.com/api/v1/model-versions/by-hash/{hash}` | public | **200** | **top-level `air`** | Accepts AutoV1/AutoV2/AutoV3/SHA256/BLAKE3/CRC32, case-insensitive. AutoV2 `A5F58EB1C3` and full SHA256 both 200 → `urn:air:sdxl:checkpoint:civitai:827184@2514310`. Same shape as by-id. |
| GET | `https://civitai.com/api/v1/models/{id}` | public | **200** | **no `air`** | `modelVersions[].files[].name` + `files[].hashes` + version `id`. Follow with `GET …/model-versions/{versionId}` for AIR. |
| GET | `https://civitai.com/api/v1/models?limit=&query=` | public | **200** | **no `air` on list items** | Meilisearch. Requires cursor paging (not `page`). Matches titles/tags more than exact filenames. `query=moodyKrea2` → Workflow JSON models, not a `.safetensors` checkpoint. `query=MysticXXX_KREA2` → `items=[]`. `query=waiIllustriousSDXL_v160.safetensors` → **503** `"Model search is temporarily overloaded — please retry."` once. Stem search returned a different LoRA. |
| GET | `https://orchestration.civitai.com/v2/resources/{air}` | **Bearer required** | **200** | echoes **`air`** (canonical) | **Requires you already have an AIR.** Not a filename search. Keys: `air`, `size`, `hashes`, `downloadUrls`, `modelName`, `resourceName` (**display name, not filename**), `versionName`, `fileFormat`, `canGenerate`, `availability.{status,workers}`, `checkPermission`, `fees`, `userId`. Checkpoint example: workers=294 `status=available`. LoRA same shape. |
| GET | `https://orchestration.civitai.com/v2/services?limit=1&query=customComfy` | public | **200** | none | `items[0].id=utility/customComfy`. |

Example version object (trimmed):

```json
{
  "id": 2514310,
  "modelId": 827184,
  "name": "v16.0",
  "baseModel": "Illustrious",
  "air": "urn:air:sdxl:checkpoint:civitai:827184@2514310",
  "model": { "name": "WAI-illustrious-SDXL", "type": "Checkpoint" },
  "files": [{ "id": 2402203, "name": "waiIllustriousSDXL_v160.safetensors", "primary": true, "hashes": { "SHA256": "A5F58EB1C3…", "AutoV2": "A5F58EB1C3" } }]
}
```

Pin a specific file with `+{fileId}`: `urn:air:sdxl:checkpoint:civitai:827184@2514310+2402203` (docs; not required if primary file is fine).

**Import recipe for a Comfy filename when a hash is known:** `GET /api/v1/model-versions/by-hash/{hash}` → `.air` → put that string in customComfy `resources`.

**When only a filename is known:** no dedicated endpoint. Options that exist: (1) fuzzy `GET /models?query={stem}` then inspect `modelVersions[].files[].name` and `GET /model-versions/{id}` — **unreliable, not exact**; (2) compute a Civitai hash locally and use by-hash. Do not invent a by-filename API.

Docs also describe **POST** `/api/v1/model-versions/by-hash` (bulk SHA256, up to 100) and **POST** `/by-hash/ids` — not called (GET-only).

`server.py` already: `GET {SITE}/model-versions/{vid}` and copies `air`; `/api/search` uses `GET /models?query=` and **drops** AIR (versions only `id/name/baseModel`).

---

## 4. class_type → `comfy:nodepack` AIR

**Civitai has no GET catalog that maps Comfy `class_type` → nodepack.** Must use Comfy Registry (not Civitai) then construct the AIR; optionally verify with orchestration `GetResource`.

| Method | URL | Status | Result |
|---|---|---|---|
| GET | `https://orchestration.civitai.com/v2/nodepacks` | **404** | empty |
| GET | `https://orchestration.civitai.com/v2/consumer/nodepacks` | **404** | empty |
| GET | `https://orchestration.civitai.com/v2/consumer/resources` | **404** | empty |
| GET | `https://orchestration.civitai.com/v2/resources` (no `{air}`) | **400** | `errors.view`: "The view field is required." |
| GET | `https://orchestration.civitai.com/v2/resources?filename=…` | **400** | same; filename query ignored |
| GET | `https://orchestration.civitai.com/v2/services?query=nodepack` | **200** | 2 services: `utility/customComfy`, `model/comfyNodepackSnapshot` — not a node index |
| GET | `https://api.comfy.org/comfy-nodes/{class_type}/node` | **200** or **404** | **This is the class_type resolver.** 200 keys: `id`, `publisher.id`, `latest_version.version`, `name`, `repository`. 404 for core nodes (`KSamplerAdvanced`) and some unpublished names (`SeedVR2LoadDiTModel`). |
| GET | `https://api.comfy.org/nodes/{nodeId}` | **200** | Pack by registry id (`comfyui-kjnodes` → publisher `kijai`, latest `1.5.0`). |
| GET | `https://api.comfy.org/comfy-nodes?comfy_node_name=` | **200** | `comfy_nodes[]` with `comfy_node_name` — listing, not AIR. |

Construct:

```
urn:air:comfy:nodepack:comfyregistry:{publisher.id}/{id}@{latest_version.version}
```

Live examples:

| class_type | Registry 200 | Constructed AIR | GetResource |
|---|---|---|---|
| `Power Lora Loader (rgthree)` | `publisher.id=rgthree`, `id=rgthree-comfy`, `version=1.0.2608210019` | `urn:air:comfy:nodepack:comfyregistry:rgthree/rgthree-comfy@1.0.2608210019` | **200** (`availability.status=unavailable`, `canGenerate=true`, `downloadUrls[0]=https://cdn.comfy.org/rgthree/rgthree-comfy/…/node.zip`, `hashes={}`) |
| `UltralyticsDetectorProvider` | `drltdata` / `comfyui-impact-subpack` / `1.3.5` | `urn:air:comfy:nodepack:comfyregistry:drltdata/comfyui-impact-subpack@1.3.5` | (constructed; not all variants probed) |
| OpenAPI example | `kijai` / `comfyui-kjnodes` / `1.4.0` | `urn:air:comfy:nodepack:comfyregistry:kijai/comfyui-kjnodes@1.4.0` | **200**; `@1.5.0` also 200 |
| `SeedVR2VideoUpscaler` | `ainvfx` / `seedvr2_videoupscaler` / `2.5.24` | `…ainvfx/seedvr2_videoupscaler@2.5.24` | **200** |
| `SeedVR2` (short) | **different pack** `assa/alex-seedvr-node@1.0.1` | ambiguous | Registry is not unique by fuzzy name |
| `KSamplerAdvanced` | **404** | core node — **no nodepack** | — |

**GetResource encoding:** do **not** percent-encode `/` in `{publisher}/{pack}`. Fully encoded AIR (`%2F`) → **400** `{"air":["AIR is in an invalid format."]}`. Leave `/`, `:`, `@` unencoded, or `quote(air, safe="/:@")`.

Nodepack `availability.status` was `unavailable` on every live pack probe (not a weight on the model fleet). That does **not** prove customComfy cannot install it; it only means GetResource’s worker-count view is empty. `canGenerate` was `true`.

**Conclusion:** there is **no Civitai nodepack catalog**. Ship a **local map** for core nodes (skip) + known ambiguous names (SeedVR2 family, rgthree titles with spaces/parens). For the rest, call Comfy Registry `GET /comfy-nodes/{class_type}/node` at import time and build the AIR. Optionally `GET /v2/resources/{air}` to confirm the URN parses.

---

## 5. Orchestration OpenAPI / services (GET)

| GET | Status |
|---|---|
| `/v2/consumer/recipes/customComfy/openapi.yaml` | **200** YAML |
| `/v2/consumer/recipes/comfyNodepackSnapshot/openapi.yaml` | **200** YAML |
| `/v2/services?limit=1` | **200** `{items,totalCount,limit,offset}` |
| `/v2/consumer/openapi.json`, `/openapi.json`, `/swagger/v1/swagger.json`, `/v2-consumers.json` | **404** |
| Developer `GetResource` | https://developer.civitai.com/orchestration/reference/operations/GetResource — path `GET /v2/resources/{air}`, pattern `"^(?!huggingface/).*$"` (rejects `huggingface/` prefix). Schema playground JSON not dumped (page is OpenAPI widget). |

Local OpenAPI files under `docs/_raw/` contain the AIR regex everywhere a resource is accepted. **No GET filename/hash/nodepack-list operation** in those YAMLs. Recipe files are POST-only (`customComfy`, `comfyNodepackSnapshot`, `prepareResource`, `modelHash`). `modelHash` hashes a file **given an AIR** — it does not resolve filename → AIR.

---

## 6. Gaps / 404s / 400s (do not invent)

| Probe | Status | Meaning |
|---|---|---|
| `GET /api/v1/model-versions/by-filename/{name}` | **404** | No filename endpoint |
| `GET /api/v1/models/by-filename/{name}` | **404** | |
| `GET /api/v1/model-versions?filename=` | **404** | |
| `GET /v2/nodepacks`, `/v2/consumer/nodepacks` | **404** | No Civitai nodepack list |
| `GET /v2/consumer/resources` | **404** | |
| `GET /v2/resources` without path AIR | **400** | `{air}` path required |
| `GET /v2/resources?air=` | **400** | query `air` is not the path param |
| Fully URL-encoded nodepack AIR (`%2F`) | **400** | invalid AIR format |
| `GET /v2/resources/{nodepack}` unauthenticated | **401** | use `Authorization: Bearer <token>` |
| `GET /v2/consumer/recipes/customComfy` | **405** | POST-only |
| `GET /models?query=` AIR field | absent | list/detail models omit `air`; only version-by-id/hash/mini |
| Exact `files[].name` search | **does not exist** | `query=` is full-text, not filename equality |
| class_type catalog on Civitai | **does not exist** | use Comfy Registry or a local map |

`GET /api/v1/enums` **200** `ModelType` includes Checkpoint, LORA, VAE, Controlnet, Upscaler, UNet, TextEncoder, Workflows, … — useful for `types=` on model search, not AIR.

---

## 7. Practical import pipeline (no generation POST)

1. Scan graph for loader widgets (filenames) and `class_type`.
2. **Weights:** if hash known → `GET /api/v1/model-versions/by-hash/{hash}` → `air`. Else fuzzy `GET /models?query={stem}` + match `files[].name` (expect misses) → `GET /model-versions/{id}` → `air`. Put strings in `resources`.
3. **Custom nodes:** skip core (registry 404). For others `GET https://api.comfy.org/comfy-nodes/{class_type}/node` → `urn:air:comfy:nodepack:comfyregistry:{publisher.id}/{id}@{version}`. Keep a **local override map** for collisions. Deduplicate packs.
4. Optional: `GET /v2/resources/{air}` (Bearer, do not encode `/`) to canonicalize AIR / confirm parse.
5. customComfy body: `{ "resources": [...airs], "workflow": <graph>, "trace": "none" }`. Do not submit here.
