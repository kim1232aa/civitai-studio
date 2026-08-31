# Fal OpenAPI field-gap retry

Fetched `2026-08-31 21:34 UTC` / `2026-09-01 05:34 CST`, extra I2V `2026-08-31 21:52 UTC` / `2026-09-01 05:52 CST`. GET only — no POST to fal.run or queue.fal.run. Token not stored here.

Auth: platform list/search **HTTP 200**. No 401 this run.

## Results

| id | imageFields | promptField | durationField | aspectRatioField | schemaSource | http |
|---|---|---|---|---|---|---|
| `fal-ai/imagen4/preview` | — | — | — | — | none | find 404; fal.run 404; not_found |
| `fal-ai/imagen4/preview/fast` | — | — | — | — | none | find 404; fal.run 404; not_found |
| `fal-ai/imagen4/preview/ultra` | — | — | — | — | none | find 404; fal.run 404; not_found |
| `fal-ai/runway-gen3/turbo/image-to-video` | image_url, end_image_url | prompt | duration | — | fal.run/openapi.json | find 200; fal.run 404; expansion_failed |
| `fal-ai/runway-gen3/turbo/text-to-video` | — | — | — | — | none | find 200; fal.run 404; expansion_failed |
| `fal-ai/runway-gen3` | image_url, end_image_url | prompt | duration | — | fal.run/openapi.json | find 200; fal.run 200 |
| `fal-ai/kling-video/o3/pro/image-to-video` | end_image_url, image_url | prompt | duration | — | post-body | find 200 |
| `fal-ai/kling-video/o3/standard/image-to-video` | end_image_url, image_url | prompt | duration | — | post-body | find 200 |
| `fal-ai/kling-video/o3/pro/reference-to-video` | start_image_url, end_image_url, image_urls | prompt | duration | aspect_ratio | post-body | find 200 |
| `fal-ai/kling-video/o3/standard/reference-to-video` | start_image_url, end_image_url, image_urls | prompt | duration | aspect_ratio | post-body | find 200 |
| `fal-ai/kling-video/o3/pro/video-to-video/edit` | video_url, image_urls | prompt | — | — | post-body | find 200 |
| `fal-ai/kling-video/o3/4k/image-to-video` | end_image_url, image_url | prompt | duration | — | post-body | find 200 |
| `fal-ai/kling-video/o3/standard/text-to-video` | — | prompt | duration | aspect_ratio | post-body | find 200 |
| `fal-ai/minimax/hailuo-02/standard/image-to-video` | end_image_url, image_url | prompt | duration | — | post-body | find 200 |
| `fal-ai/minimax/hailuo-2.3/standard/image-to-video` | image_url | prompt | duration | — | post-body | find 200 |
| `fal-ai/minimax/hailuo-2.3-fast/standard/image-to-video` | image_url | prompt | duration | — | post-body | find 200 |
| `fal-ai/minimax/hailuo-02-fast/image-to-video` | image_url | prompt | duration | — | post-body | find 200 |
| `fal-ai/minimax/hailuo-02/pro/image-to-video` | end_image_url, image_url | prompt | — | — | post-body | find 200 |
| `fal-ai/minimax/hailuo-2.3/pro/image-to-video` | image_url | prompt | — | — | post-body | find 200 |
| `lightricks/ltx-2.5/image-to-video/pro` | image_url, end_image_url | prompt | duration | aspect_ratio | post-body | find 200 |
| `lightricks/ltx-2.5/image-to-video/fast` | image_url, end_image_url | prompt | duration | aspect_ratio | post-body | find 200 |
| `lightricks/ltx-2.5/text-to-video/fast` | — | prompt | duration | aspect_ratio | post-body | find 200 |
| `lightricks/ltx-2.5/audio-to-video/pro` | image_url | prompt | — | aspect_ratio | post-body | find 200 |
| `lightricks/ltx-2.5/audio-to-video/fast` | image_url | prompt | — | aspect_ratio | post-body | find 200 |
| `fal-ai/ltx-2.3/image-to-video/fast` | end_image_url, image_url | prompt | duration | aspect_ratio | post-body | find 200 |
| `fal-ai/ltx-2.3-22b/image-to-video` | end_image_url, image_url | prompt | — | — | post-body | find 200 |
| `fal-ai/ltx-2.3-quality/image-to-video` | image_url | prompt | — | — | post-body | find 200 |
| `fal-ai/kling-video/v2.1/standard/image-to-video` | image_url | prompt | duration | — | post-body | find 200 |
| `fal-ai/kling-video/v2.1/pro/image-to-video` | image_url, tail_image_url | prompt | duration | — | post-body | find 200 |
| `fal-ai/kling-video/v2.5-turbo/standard/image-to-video` | image_url | prompt | duration | — | post-body | find 200 |
| `fal-ai/kling-video/v3/turbo/pro/image-to-video` | image_url | prompt | duration | — | post-body | find 200 |
| `fal-ai/veo3.1/lite/image-to-video` | image_url | prompt | duration | aspect_ratio | post-body | find 200 |
| `fal-ai/veo3.1/fast/first-last-frame-to-video` | first_frame_url, last_frame_url | prompt | duration | aspect_ratio | post-body | find 200 |
| `fal-ai/veo3.1/lite/first-last-frame-to-video` | first_frame_url, last_frame_url | prompt | duration | aspect_ratio | post-body | find 200 |
| `fal-ai/veo3.1/reference-to-video` | image_urls | prompt | duration | aspect_ratio | post-body | find 200 |
| `fal-ai/kling-video/v3/4k/image-to-video` | start_image_url, end_image_url | prompt | duration | — | post-body | find 200; openapi 200 |
| `fal-ai/kling-video/v3/turbo/standard/image-to-video` | image_url | prompt | duration | — | post-body | find 200; openapi 200 |
| `fal-ai/kling-video/o3/4k/reference-to-video` | start_image_url, end_image_url, image_urls | prompt | duration | aspect_ratio | post-body | find 200; openapi 200 |
| `fal-ai/minimax/hailuo-2.3-fast/pro/image-to-video` | image_url | prompt | — | — | post-body | find 200; openapi 200 |

Verified already-filled (OpenAPI unchanged, not overwritten): `kling-video/o3/pro/image-to-video`, `minimax/hailuo-02/pro/image-to-video`, `minimax/hailuo-2.3/pro/image-to-video`, `lightricks/ltx-2.5/image-to-video/pro`.

## Aliases tried

| id | http | outcome |
|---|---|---|
| `fal-ai/imagen4` | find 404; fal.run 404; not_found | 404 all sources |
| `fal-ai/imagen-4` | find 404; fal.run 404; not_found | 404 all sources |
| `fal-ai/imagen4/fast` | find 404; fal.run 404; not_found | 404 all sources |
| `google/imagen-4` | find 404; fal.run 404; not_found | 404 all sources |
| `fal-ai/imagen4/ultra` | find 404; fal.run 404; not_found | 404 all sources |
| `fal-ai/runway/gen3/turbo/image-to-video` | find 404; fal.run 404; not_found | 404 all sources |
| `fal-ai/runway/gen3/turbo/text-to-video` | find 404; fal.run 404; not_found | 404 all sources |
| `runway/gen3/turbo/image-to-video` | find 404; fal.run 404; not_found | 404 all sources |
| `fal-ai/runway-gen-3/turbo/image-to-video` | find 404; fal.run 404; not_found | 404 all sources |
| `fal-ai/runway-gen-3/turbo/text-to-video` | find 404; fal.run 404; not_found | 404 all sources |
| `fal-ai/runway-gen3/turbo` | find 200; fal.run 404; expansion_failed | exists, no schema |

## Still empty after retry

- `fal-ai/imagen4/preview`
- `fal-ai/imagen4/preview/fast`
- `fal-ai/imagen4/preview/ultra`
- `fal-ai/runway-gen3/turbo/text-to-video`

No fields invented for these. Imagen4 docs pages and `llms.txt` also 404 (search still lists the three preview ids as **deprecated**). Runway T2V parent OpenAPI has only `/turbo/image-to-video`.

## Alias map

- `fal-ai/runway-gen3/turbo/image-to-video` → `fal-ai/runway-gen3` path `/turbo/image-to-video` via `GET https://fal.run/fal-ai/runway-gen3/openapi.json`. Aspect property is `ratio` (not `aspect_ratio`). `end_image_url` is deprecated in that schema.
- Imagen4: no working alias (`fal-ai/imagen4`, `fal-ai/imagen-4`, `fal-ai/imagen4/fast`, `fal-ai/imagen4/ultra`, `google/imagen-4` all find 404).

## Catalog

- `fal-models.json` **1492** items (`total=1492`). Field keys patched in place; other catalog fields preserved.
- `fal-openapi-models.json` models: **141** (was 137; appended 4 I2V schemas).
- `server.py` not modified.
