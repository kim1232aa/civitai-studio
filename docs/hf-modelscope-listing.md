# Hugging Face / 魔搭 (ModelScope) listing diagnosis

Probed **2026-09-01 05:47 CST** (UTC+8). Running Studio: `http://127.0.0.1:8765`. Tokens were used only as `Authorization: Bearer` on GET list calls; they are **not** written here. No generate/inference POSTs. No weight downloads. `server.py` was **not** modified.

Tokens present (chmod `600`, contents not echoed): `/home/box/.config/huggingface/token` (len 37), `/home/box/.config/modelscope/token` (len 39). Studio `hasKey` is true for both. This is **not** a 401-fallback-stub problem.

---

## 1. Current counts in Studio

Live `GET /api/catalog` against the running server:

| Backend | HTTP | `count` / `total` | `hasKey` | What the UI actually paints |
|---|---|---|---|---|
| `huggingface` | 200 | **8 / 8** | true | Image recipe: **6** (`category=image`). Video recipe: **2**. |
| `modelscope` (魔搭) | 200 | **4 / 4** | true | Image recipe: **4**. Video recipe: **0** (`categories()` is hard-wired `["image"]`). |
| `fal` (control) | 200 | 1491 | true | — |
| `civitai` (control) | 200 | 304 | — | — |

Studio Hugging Face ids (all from disk whitelist):

```
black-forest-labs/FLUX.1-schnell
black-forest-labs/FLUX.1-dev
black-forest-labs/FLUX.1-Krea-dev
Qwen/Qwen-Image
Tongyi-MAI/Z-Image-Turbo
stabilityai/stable-diffusion-xl-base-1.0
tencent/HunyuanVideo
Lightricks/LTX-Video-0.9.8-13B-distilled
```

Studio 魔搭 ids (all from disk whitelist; live merge added **0** new):

```
Qwen/Qwen-Image
Qwen/Qwen-Image-Edit
MusePublic/Qwen-Image-Edit
Tongyi-MAI/Z-Image-Turbo
```

`GET /api/providers` labels: Hugging Face (`huggingface`), 魔搭 (`modelscope`). UI loads them via `loadCatalog()` → `GET /api/catalog?backend=…` and filters rows by `category` (`static/index.html` `matchRecipe`). No extra client-side cap.

---

## 2. How listing is implemented

### Hugging Face — hardcoded JSON, never the Hub API

`providers/huggingface.py` `catalog()` only reads `docs/hf-models.json`. There is no `huggingface.co/api/models` call, no pagination, no `pipeline_tag` filter, no inference-provider probe.

```27:71:providers/huggingface.py
def load_items():
    fp = DOCS / "hf-models.json"
    if not fp.exists():
        return []
    try:
        return json.loads(fp.read_text()).get("items") or []
    except Exception:
        return []
...
    def catalog(self, q, category, status) -> dict:
        qn = (q or "").lower()
        items = list(load_items())
        if category:
            items = [x for x in items if x.get("category") == category]
        if status:
            items = [x for x in items if x.get("status") == status]
        if qn:
            items = [x for x in items if qn in (x.get("name") or "").lower() or qn in (x.get("id") or "").lower()]
        return {
            "total": len(items),
            "count": len(items),
            "backend": "huggingface",
            "items": items,
            "hasKey": self.has_key(),
        }
```

Generation (not listing) POSTs to `https://router.huggingface.co/hf-inference/models/{id}`. That router is unrelated to the catalog path.

### 魔搭 — tiny JSON plus a live merge against the **wrong** API

Disk stub: `docs/ms-models.json` (4 items). If a key exists, `catalog()` GETs `{base_url()}/models` (OpenAI-compatible inference list) and keeps ids whose lowercase form contains `image|flux|kolors|z-image|sdxl`.

```16:17:providers/modelscope.py
PREFERRED = "https://api.modelscope.ai/v1"
FALLBACK = "https://api-inference.modelscope.cn/v1"
```

```41:51:providers/modelscope.py
def base_url() -> str:
    preferred = PREFERRED
    try:
        t = BASE_PATH.read_text().strip().rstrip("/")
        if t:
            preferred = t
    except Exception:
        pass
    if _host_ok(preferred):
        return preferred
    return FALLBACK
```

`/home/box/.config/modelscope/base_url` is `https://api.modelscope.ai/v1`. That host **does not resolve** (`getaddrinfo` → `Name or service not known`), so `_host_ok` fails and Studio uses the fallback.

```95:132:providers/modelscope.py
    def catalog(self, q, category, status) -> dict:
        items = list(load_disk())
        # merge live image-ish models if key works
        if self.has_key():
            code, data = json_call(f"{base_url()}/models", headers=auth_headers())
            live = []
            if code == 200 and isinstance(data, dict):
                for it in data.get("data") or []:
                    mid = (it.get("id") if isinstance(it, dict) else str(it)) or ""
                    low = mid.lower()
                    if any(k in low for k in ("image", "flux", "kolors", "z-image", "sdxl")):
                        live.append({...})
            known = {x.get("id") for x in items}
            items.extend(x for x in live if x.get("id") not in known)
        ...
```

Live merge this session: `GET https://api-inference.modelscope.cn/v1/models` → **200**, OpenAI `{object: list, data: [50 chat-ish models]}`. Query params `limit` / `page_size` / `PageSize` do **not** paginate (still 50). Keyword filter hit **2** ids (`Qwen/Qwen-Image-Edit`, `MusePublic/Qwen-Image-Edit`), both already in the stub → net **+0**.

`categories()` is hardcoded `return ["image"]` (line 92–93), so even a video model would not get a 魔搭 video tab.

### HTTP routing — refresh is a no-op for HF/MS

```695:706:server.py
        if path == "/api/catalog":
            backend = (qs.get("backend") or ["civitai"])[0]
            prov = providers.get(backend) or providers.get("civitai")
            if backend != "civitai" and (qs.get("refresh") or ["0"])[0] in ("1", "true"):
                pass
            elif backend == "civitai" and (qs.get("refresh") or ["0"])[0] in ("1", "true"):
                ...
            body = prov.catalog(...)
```

UI: `static/index.html` ~1276–1310 (`loadCatalog` / `loadProviders`). Displays whatever the provider returns.

---

## 3. Live API sample counts (GET only, no tokens in this report)

### Hugging Face Hub

`GET https://huggingface.co/api/models` — **200** with and without the token. No `X-Total-Count` header (Hub now paginates with a `Link: rel="next"` cursor). Default page when `limit` is omitted: **1000** (API max page). Website totals (same filters) are the real catalog sizes:

| Query | Status | Hits |
|---|---|---|
| `pipeline_tag=text-to-image&sort=downloads&limit=10` | 200 | 10 (one page) |
| `…&limit=100` | 200 | 100 |
| `…` (no limit) | 200 | 1000 (page max; `Link` has next) |
| `pipeline_tag=text-to-image` **website total** | 200 | **109,222** |
| `pipeline_tag=text-to-video` website | 200 | **2,546** |
| `pipeline_tag=image-to-video` website | 200 | **1,544** |
| `pipeline_tag=image-to-image` website | 200 | **3,532** |
| `pipeline_tag=text-to-image&library=diffusers&limit=100` | 200 | 100 (page; not the bug) |
| `pipeline_tag=text-to-image&inference_provider=hf-inference` | 200 | **1** (`stabilityai/stable-diffusion-3-medium-diffusers`) |
| `GET https://router.huggingface.co/v1/models` | 200 | **136** (OpenAI router / mostly LLMs; 0 image-ish ids) |

First Hub t2i page (sort=downloads) includes `stabilityai/stable-diffusion-xl-base-1.0`, `FLUX.1-dev`, `Z-Image-Turbo`, `FLUX.1-schnell` — overlapping the whitelist — plus thousands of others the Studio never loads.

**What current HF code would return: 8. Broader Hub t2i query: 109,222.** Plus 2,546 t2v and 1,544 i2v if video is in scope.

### ModelScope / 魔搭 Hub

The URL Studio uses is **not** the community catalog.

| Endpoint | Status | Hits / notes |
|---|---|---|
| `GET https://api.modelscope.ai/v1/models` (Studio preferred) | DNS fail | `api.modelscope.ai` NXDOMAIN |
| `GET https://api-inference.modelscope.cn/v1/models` (Studio fallback, OpenAI list) | 200 | **50** chat/multimodal ids, no pagination |
| `GET https://www.modelscope.cn/api/v1/models?PageSize=30&PageNumber=1` | 404 | `404 page not found` |
| `GET https://www.modelscope.cn/api/v1/dolphin/models?PageSize=30` | 404 | dolphin search is historically **PUT**, not GET |
| `GET https://www.modelscope.cn/openapi/v1/models?sort=downloads&page_size=5` | 200 | Hub list; `data.total_count` = **248,740** (all tasks) |
| `…?filter.task=text-to-image` | 200 | **0** (wrong task slug) |
| `…?filter.task=text-to-image-synthesis&sort=downloads&page_size=50` | 200 | **`total_count` = 94,189**; page_size max 50; `page_number` works |
| `…?filter.task=image-to-image` | 200 | **824** |
| `…?filter.task=text-to-video-synthesis` | 200 | **3,069** |
| `…?filter.task=image-to-video` | 200 | **552** |
| `…?filter.library=diffusers` | 200 | **14,523** |

OpenAPI response shape: `{success, data: {models: [{id, tasks, downloads, …}], total_count, page_number, page_size}}`. Sample t2i-synthesis ids: `Qwen/Qwen-Image`, `black-forest-labs/FLUX.1-dev`, `Tongyi-MAI/Z-Image-Turbo`.

**What current 魔搭 code returns: 4. Broader Hub t2i-synthesis query: 94,189.**

---

## 4. The bug / limitation (one paragraph)

The lists are tiny because Studio never talks to the Hub catalog APIs. Hugging Face is a **hand-written 8-id whitelist** in `docs/hf-models.json`; `HuggingFaceProvider.catalog()` never calls `huggingface.co/api/models`, so Hub’s ~109k text-to-image models (and video tags) cannot appear. 魔搭 starts from a **4-id whitelist** in `docs/ms-models.json` and then “merges live” from `{inference_base}/models` — the OpenAI-compatible **chat model list** (50 rows, no pagination), not `openapi/v1/models`. The preferred host `api.modelscope.ai` does not resolve here; the fallback returns LLMs; a substring filter (`image|flux|kolors|z-image|sdxl`) keeps two ids already in the stub. Tokens work (`hasKey: true`); this is not a 401 stub. `GET /api/catalog?refresh=1` is a no-op for both backends. Wrong-filter footnote: ModelScope `filter.task=text-to-image` is empty; the real slug is `text-to-image-synthesis`.

---

## 5. What to change (do not apply here)

Do **not** treat Hub dump size as “every id is callable on the inference router.” Listing should still come from the catalog APIs, then optionally intersect with inference-capable ids.

### Hugging Face (`providers/huggingface.py`)

1. Stop using `docs/hf-models.json` as the only source (keep it as a pin/fallback).
2. GET `https://huggingface.co/api/models?pipeline_tag={text-to-image|text-to-video|image-to-video|image-to-image}&sort=downloads&limit=100`.
3. Paginate via the `Link: rel="next"` cursor (there is no `X-Total-Count`; max `limit` is 1000). Do not assume `limit=10` or a single page.
4. Map `pipeline_tag` → Studio `category`/`task` (`text-to-image` → image/t2i, `text-to-video` → video/t2v, etc.).
5. Optional tighter slice for the generate button: models with an inference provider, **not** `inference_provider=hf-inference` alone (that filter is currently 1 model). `router.huggingface.co/v1/models` is the LLM router (136 ids) and is the wrong catalog for t2i.
6. Auth: send `Authorization: Bearer` from the existing token path; Hub list also works anonymously.

### 魔搭 (`providers/modelscope.py`)

1. List from Hub GET `https://www.modelscope.cn/openapi/v1/models?filter.task=text-to-image-synthesis&sort=downloads&page_size=50&page_number=N` until `page_number * page_size >= total_count` (or cap, e.g. top 200). `page_size` max is 50.
2. Also pull `image-to-image` (824), and if video is wanted `text-to-video-synthesis` (3069) / `image-to-video` (552). **Do not** use `filter.task=text-to-image` (0 hits).
3. Stop merging `GET {api-inference}/v1/models`. That is the OpenAI chat list, not AIGC. Do not keyword-filter LLM ids.
4. Do not depend on `api.modelscope.ai` for listing (NXDOMAIN here). Keep that host only as a generate `base_url` fallback after DNS check.
5. `GET https://www.modelscope.cn/api/v1/models` and `…/dolphin/models` return 404 on GET; dolphin search is PUT (not used — listing can stay GET via openapi).
6. Expand `categories()` beyond `["image"]` if video rows are added.
7. Wire `refresh=1` in `server.py` `/api/catalog` so HF/MS can refetch instead of `pass`.

A proposed diff (not applied) is in `docs/hf-modelscope-listing.proposed.patch`.
