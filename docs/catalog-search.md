# Catalog search (svcFilter vs vendor GET)

**Implemented 2026-09-01 (after this probe):** UI `loadCatalog` now sends `q` for Fal / Hugging Face / 魔搭. Civitai stays local on the 304 dump. Fal live `GET https://api.fal.ai/v1/models?q=`. HF Hub `GET https://huggingface.co/api/models?search=`. 魔搭 typeahead is one `search=` GET (no 4×2 task loop). Hyphen-insensitive `alnum` match on all four. Hub list ≠ inference-callable.

Below is the GET-only probe that justified that wiring. Some "search today" rows are stale.


Probed **2026-09-01 06:49–07:00 CST** (UTC+8). GET-only. No generate POSTs. No tokens in this file.

Studio: `http://127.0.0.1:8765`. Live `GET /api/catalog` counts used below.

## How Studio searches today

`#svcFilter` (`static/index.html`) is a client box labeled 筛选服务.

| Path | What happens |
|---|---|
| `loadCatalog(q)` | `GET /api/catalog?backend={backend}`. **Only `backend=modelscope` appends `&q=`**. Then `catalog = cat.items` and `setRecipe` → `renderServiceList`. |
| `onSvcFilter` | **魔搭:** debounce 280ms → `loadCatalog()` (server Hub round-trip). **Everyone else:** no network; `renderServiceList` only. |
| `renderServiceList` | Local filter of the in-memory `catalog` array. `alnum(name+id+engine+operation+tags)` contains `alnum(svcFilter)`. Then `matchRecipe` by category. |
| Server `/api/catalog` | `prov.catalog(q, category, status)`. UI never sends `q` except ModelScope. `refresh=1` is a no-op for non-civitai. |

### Per-backend `catalog()`

**Civitai** (`providers/civitai.py`): in-memory `docs/catalog.json` (built by paginating `GET {ORCH}/v2/services?limit=200&offset=` until `totalCount`). Local substring on `name|id|engine`. Does **not** call orchestration `query=` on each keystroke.

**Fal** (`providers/fal.py`): reads `docs/fal-models.json` only. Local substring on `name|id`. `MODELS_API = https://api.fal.ai/v1/models` is unused for listing (used for request-by-endpoint). Dump is produced by `scripts/fetch_fal_models.py`.

**Hugging Face** (`providers/huggingface.py`): reads `docs/hf-models.json` (8-id whitelist). Local substring on `name|id`. `HUB = https://huggingface.co/api/models` is used for **per-id** `?expand[]=inferenceProviderMapping`, never for search/list. Typing `krea` in the UI only hits `black-forest-labs/FLUX.1-Krea-dev`.

**ModelScope** (`providers/modelscope.py`): `fetch_hub(search=q)` **always** loops `HUB_TASKS` (4 tasks) × `_HUB_PAGES=2` × `page_size=50`, even when `search` is set. Then merges `docs/ms-models.json` pins, then a second **local** alnum filter. Empty-q result is cached 300s (`_HUB_CACHE`). Live empty catalog: **398** rows vs Hub totals t2i **94,191** / i2i 824 / t2v 3,069 / i2v 552.

## Is search only a local filter on a truncated dump?

| Backend | Dump | Truncated? | Search today |
|---|---|---|---|
| civitai | **304** in `docs/catalog.json` (live orch **309**) | Almost full. Missing 5 new **chat/** rows vs live. Generation services (incl. all 8 krea ids) present. | Local filter of dump. UI never sends `q`. |
| fal | **1492** in `docs/fal-models.json` (`total: 1492`). Gallery `GET https://fal.ai/api/models` reports **1491**. | Effectively full. Live `q=krea` found 1 extra not in dump: `fal-ai/flux-krea-trainer`. | Local filter of dump. UI never sends `q`. Server would local-filter if `q` were passed. |
| huggingface | **8** in `docs/hf-models.json` | Yes. Hard whitelist. Hub t2i is ~109k. | Local filter of those 8. |
| modelscope | Disk pins **7**; live empty catalog **398** = 4×2 Hub pages + pins | Yes. Search already hits Hub, but still only 2 pages/task. `q=krea` Studio **107** vs Hub `total_count` t2i **4,690**. | UI sends `q` → Hub (slow 4×2) + local alnum. |

Civitai dump vs live orch (GET, no key needed this run): live not in dump = `chat/deepseek/deepseek-chat`, `chat/google/gemini-2.5-flash`, `chat/google/gemini-2.5-flash-lite`, `chat/meta/muse-spark-1.2-contributor`, `chat/x-ai/grok-4.5`. Dump-not-live: none.

## Vendor search APIs (GET, real URLs)

### Civitai

1. **Orchestration services** (what Studio catalog is):  
   `GET https://orchestration.civitai.com/v2/services?limit=200&offset=0`  
   Working query params (live): `limit`, `offset`, **`query=`** (not `q` / `search` / `name` — those are ignored), `category=image`, `status=available`.  
   `?query=krea` → `totalCount=8` (same 8 ids as local dump filter). Live `totalCount` unfiltered = **309**. Auth optional this run (200 unauthenticated).

2. **Site model search** (LoRAs / checkpoints, **not** generation services):  
   `GET https://civitai.com/api/v1/models?query=krea&limit=5`  
   Studio already uses this in `fetch_models()` for the LoRA picker (`search_models`), not `#svcFilter`.

### Fal

Official OpenAPI: `GET https://api.fal.ai/v1/models`  
Docs: https://fal.ai/docs/platform-apis/v1/models  
Auth **optional** (key only raises rate limits). Modes: list / `endpoint_id=` find / **`q=` search**. Also `limit`, `cursor`, `category` (e.g. `text-to-image`), `status=active|deprecated`, `expand=openapi-3.0`.

- List: `GET https://api.fal.ai/v1/models?limit=100&cursor=` → `{models[], next_cursor, has_more}` (no `total`).
- Search: `GET https://api.fal.ai/v1/models?q=krea&limit=10` — **real search**, 200, no key.
- Gallery HTML API `GET https://fal.ai/api/models` has `total=1491` but **`q` is ignored** (same featured page). Do not use gallery for typeahead.

Dump **1492** ≈ gallery **1491** ≈ previous authenticated crawl **1491**. Complete enough for local filter; search API exists if dump goes stale.

### Hugging Face Hub

```
GET https://huggingface.co/api/models?search={q}&pipeline_tag=text-to-image&limit=10
GET https://huggingface.co/api/models?search={q}&filter=text-to-image&limit=10
GET https://huggingface.co/api/models?search={q}&pipeline_tag=text-to-video&limit=10
```

Anonymous 200. Paginate `Link: rel="next"` (no `X-Total-Count`; max `limit` 1000). `filter=` and `pipeline_tag=` both work for t2i. Do **not** use `router.huggingface.co/v1/models` (LLM router).

### ModelScope Hub

```
GET https://www.modelscope.cn/openapi/v1/models?search={q}&page_size=50&sort=downloads
GET https://www.modelscope.cn/openapi/v1/models?search={q}&filter.task=text-to-image-synthesis&page_size=50&page_number=1&sort=downloads
```

`page_size` max 50. Shape `{success, data:{models, total_count, page_number, page_size}}`.

**Confirmed:** `search=` **without** `filter.task` is faster and still returns `krea/Krea-2-Turbo`.

| Call | Time (this run) | `total_count` | `krea/Krea-2-Turbo` in first page? |
|---|---|---|---|
| `search=krea2` no task, `page_size=50` | **1.28s** | 4373 | yes (3rd of first 8) |
| `search=krea2` + `filter.task=text-to-image-synthesis` | 1.39s | 4301 | yes (1st) |
| Studio `fetch_hub` 4 tasks × 2 pages (`q=krea2`) | **5.45s** | 101 returned | yes, after 8 Hub GETs |
| Studio `q=krea` same 4×2 | **5.77s** | 107 | yes |

Wrong slug `filter.task=text-to-image` is empty (see `docs/hf-modelscope-listing.md`). Inference `GET {api-inference}/v1/models` is still the chat list — catalog no longer uses it for listing.

## Uniform UX recommendation

Rule: **local filter when the full (or near-full) catalog is already in memory; vendor GET when the dump cannot cover the query.**

- **Civitai (~304, live 309):** keep local `renderServiceList`. Optional periodic `refresh=1` to pick up the 5 new chat rows. Do not typeahead-hit orchestration unless dump is empty. `query=` exists if needed.
- **Fal (~1492 ≈ live 1491):** keep local filter. Optionally debounce-call `GET https://api.fal.ai/v1/models?q=` if zero local hits (e.g. brand-new `fal-ai/flux-krea-trainer`).
- **Hugging Face (8 vs ~109k):** local filter **cannot** suffice. Mirror 魔搭: debounce `#svcFilter` → `GET /api/catalog?backend=huggingface&q=` → Hub `search=` + `pipeline_tag` from current recipe (image → `text-to-image` / `image-to-image`, video → `text-to-video` / `image-to-video`). Keep `hf-models.json` as pins/fallback only.
- **ModelScope (398 vs 94k t2i):** already wires typeahead, but **stop the 4×2 loop on search**. One GET: `?search={q}&page_size=50` (no `filter.task`) is enough and finds Krea-2-Turbo; optionally add `filter.task` from the active recipe only. Keep empty-q browse as the 4-task top-N dump.

UI change: `loadCatalog` should send `q` for **huggingface** and **modelscope** (and Fal only on zero local hits). Civitai/Fal default path stays `oninput → renderServiceList`.

Do not dump entire HF/MS hubs into memory. Hub listing ≠ inference-callable.

## Table

| backend | dump size | search today | vendor search API (real URL) | can local filter suffice? | what to wire |
|---|---|---|---|---|---|
| civitai | 304 (`docs/catalog.json`); live orch 309 | Local `renderServiceList` on dump. Server can filter `q` but UI does not send it. | `GET https://orchestration.civitai.com/v2/services?query={q}&limit=200&offset=0` (use **`query`**, not `q`). Also LoRA: `GET https://civitai.com/api/v1/models?query={q}` (already LoRA picker). | **Yes** for gen services (all 8 krea ids in dump). Refresh to 309. | Keep local. `refresh=1` on load/interval. |
| fal | 1492 (`docs/fal-models.json`); gallery 1491 | Local filter of dump. `catalog()` never calls Fal list/search. | `GET https://api.fal.ai/v1/models?q={q}&limit=20` (auth optional). List: `?limit=100&cursor=`. Gallery `fal.ai/api/models` **ignores** `q`. | **Yes** (≈complete). One live krea id missing from dump. | Keep local. If 0 hits, debounce vendor `q=`. |
| huggingface | **8** whitelist `docs/hf-models.json` | Local filter of those 8. `q=krea` → only `FLUX.1-Krea-dev`. | `GET https://huggingface.co/api/models?search={q}&pipeline_tag=text-to-image&limit=10` (also `filter=text-to-image`; paginate `Link`). | **No.** | Debounce svcFilter → Hub `search=` like 魔搭. Pins stay fallback. |
| modelscope | Pins 7; live browse **398** (4 tasks × 2 pages). Hub t2i 94,191. | UI already sends `q`; `fetch_hub` still **4 tasks × 2 pages** (~5.5–8s). | `GET https://www.modelscope.cn/openapi/v1/models?search={q}&page_size=50` (**no** `filter.task`; ~1.3s, returns Krea-2-Turbo). Optional `filter.task=text-to-image-synthesis`. | **No** for browse dump. Search is already vendor, but truncated + slow. | On type: one `search=` GET, skip 4×2. Browse: keep capped dump. |

## Sample ids (live GET, 2026-09-01)

### Hugging Face `pipeline_tag=text-to-image&limit=10`

`search=krea`:
`krea/Krea-2-Turbo`, `krea/Krea-2-Raw`, `ifmylove2011/girlslike-krea2`, `lvladikov/Krea2-Turbo-Distill-4step-LoRA`, `F16/krea2-turbo-sda`, `RudySen/Krea2-realism-V2`, `Omnico/Krea2_turbo_diff_loras`, `UntMods/Krea2_Chars_LoRA`, `vantagewithai/Krea-2-Turbo-GGUF`, `AliveAi/Krea-2-Edit-Outfit-Transfer`

`search=flux`:
`black-forest-labs/FLUX.1-dev`, `ponpoke/flux2-klein-9b-uncensored-text-encoder`, `black-forest-labs/FLUX.1-schnell`, `ponpoke/flux2-klein-4b-uncensored-text-encoder`, `city96/FLUX.1-dev-gguf`, `wikeeyang/Flux2-Klein-9B-True-V3`, `remyxai/hrdit-flux-modular`, `wikeeyang/Flux2-Klein-9B-True-V2`, `Heartsync/Flux-NSFW-uncensored`, `black-forest-labs/FLUX.1-Krea-dev`

Studio HF `q=krea` today: only `black-forest-labs/FLUX.1-Krea-dev`.

### ModelScope `search=` without `filter.task`, first 8 ids

`search=krea2` (`total_count=4373`, 1.02–1.28s):
`Comfy-Org/Krea-2`, `ilkerzgi/fal-Krea-2-Style-LoRAs`, **`krea/Krea-2-Turbo`**, `krea/Krea-2-Raw`, `junlebao/Krea2-Turbo-fp16`, `yan303145427/krea2-Cc-TM-GreatFigure`, `jonathanfu/Krea-2-Turbo-zishi`, `yan303145427/krea2-Cc-FQWZ-ArtStyle`

`search=krea` first 8:
`Comfy-Org/Krea-2`, `ilkerzgi/fal-Krea-2-Style-LoRAs`, `black-forest-labs/FLUX.1-Krea-dev`, `krea/Krea-2-Turbo`, `krea/krea-realtime-video`, `krea/Krea-2-Raw`, `nunchaku-tech/nunchaku-flux.1-krea-dev`, `junlebao/Krea2-Turbo-fp16`

`search=flux` first 8:
`black-forest-labs/FLUX.2-klein-9B`, `gpustack/FLUX.1-Fill-dev-GGUF`, `muse/flux_vae`, `MusePublic/489_ckpt_FLUX_1`, `black-forest-labs/FLUX.1-dev`, `licyks/flux_controlnet`, `black-forest-labs/FLUX.2-klein-4B`, `gpustack/FLUX.1-lite-GGUF`

### Fal `GET https://api.fal.ai/v1/models?q=` (no key)

`q=krea` first 8: `fal-ai/krea-2/turbo/style`, `fal-ai/krea-2-trainer`, `fal-ai/krea-2/turbo`, `fal-ai/krea-2/turbo/lora`, `krea/v2/medium/turbo/text-to-image`, `krea/v2/large/text-to-image`, `krea/v2/medium/text-to-image`, `fal-ai/krea-wan-14b/text-to-video` (20 total, `has_more=false`; dump missing `fal-ai/flux-krea-trainer`)

`q=flux` first 8: `blackforestlabs/flux-video-upscale`, `blackforestlabs/flux-3/text-to-video`, `blackforestlabs/flux-3/image-to-video`, `blackforestlabs/flux-3/first-last-frame-to-video`, `blackforestlabs/flux-3/keyframes-to-video`, `blackforestlabs/flux-3/extend-video`, `blackforestlabs/flux-3/text-to-video/draft`, `blackforestlabs/flux-3/image-to-video/draft`

### Civitai dump / orch `query=krea` (identical 8)

`image/comfy/krea2/turbo/createImage`, `image/comfy/krea2/edit/editImage`, `image/comfy/krea2/raw/createImage`, `image/fal/krea2/createImage`, `model/ai-toolkit/krea2`, `image/krea/createImage/krea2-large`, `image/krea/createImage/krea2-medium`, `image/krea/createImage/krea2-medium-turbo`
