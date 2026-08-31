# Job / progress fields for Civitai Studio `#waitPane`

Probed **2026-09-01T06:31:03+08:00**. **GET only.** No generate / whatif / recipes / fal.run POST / HF inference POST / ModelScope `images/generations` POST. Tokens stayed on disk; none are written here.

## Studio UI already wired (`static/index.html`)

`#waitPane` (`waitTitle`, `#waitBar`, `#waitMeta`):

| UI | Source today |
| --- | --- |
| Elapsed | Client `waitElapsed()` = `(Date.now() - waitStart) / 1000`. Always. |
| Queue | `job.queuePosition.precedingJobs` where `job = steps[0].jobs[0]`. `"前面还有 N"` / `"轮到了"`. |
| Remaining ETA | Only if the **job object** has `estimatedDurationSeconds` **or** `etaSeconds` **or** `queuePosition.estimatedWaitTime`. **None of those names exist** in Civitai OpenAPI or live GetWorkflow. |
| Bar `%` | Client fake: `processing` → 70; else `88 - 7*min(ahead,10)`. **Not** an API percent. |

`poll()` hits Studio `GET /api/jobs/{id}` every 3s. Wire real provider paths below; do not invent fields.

---

## Compact table (one row per provider)

| id | statusUrl | auth | statusEnum | progressPercentField | queuePositionField | eta / remainingSeconds | logs / metrics | http |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| civitai | `GET https://orchestration.civitai.com/v2/consumer/workflows/{workflowId}` | `Authorization: Bearer` | `unassigned`, `preparing`, `scheduled`, `processing`, `succeeded`, `failed`, `expired`, `canceled` | **no `percent`**. Use `steps[].jobs[].estimatedProgressRate` and `steps[].estimatedProgressRate` (**0.0–1.0**, null at terminal). Live preparing: `1`. | `steps[].jobs[].queuePosition.precedingJobs` (int\|null). Also `support`, `startAt`, `completeAt`. Omitted on succeeded jobs. | **none** named remaining. Closest: `queuePosition.completeAt` (datetime) and download-only `steps[].preparation.etaSeconds`. **No** `estimatedDuration` / `estimatedDurationSeconds` / `queuePosition.estimatedWaitTime`. | none on GetWorkflow | 200, 202 (`?wait=` timeout), 401, 404 |
| fal | `GET https://queue.fal.run/{model}/requests/{id}/status` and `...?logs=1`; result `GET .../requests/{id}` | `Authorization: Key` | `IN_QUEUE`, `IN_PROGRESS`, `COMPLETED`, `FAILED`, `CANCELED` | **none** (no `progress` in official queue OpenAPI / fal_client Status / live status JSON) | `queue_position` (int, **IN_QUEUE only**, requests ahead) | **none** | logs: field `logs[]` with `?logs=1` (**not** `GET .../logs` — live 405). metrics: field `metrics.inference_time` on COMPLETED (**not** `GET .../metrics` — live 405) | status 200; result 200 or 202 (still running) or 404; 401; 402; 422; 429; 500. Dummy `fal-ai/flux/schnell` UUID GET 405 this run |
| huggingface | **none** (sync generate) | `Authorization: Bearer` on generate POST only | Studio stub: `succeeded` | none | none | none | none | generate: 200 image bytes, 400, 401, 410/503 documented. `GET /v1/models` 200. `GET .../hf-inference/models/{id}` 410 on FLUX.1-schnell |
| modelscope | `GET {base}/tasks/{task_id}` + header `X-ModelScope-Task-Type: image_generation` | `Authorization: Bearer` | Studio maps `PENDING`/`QUEUED`→pending, `RUNNING`→processing, `SUCCEED`/`SUCCEEDED`/`SUCCESS`→succeeded, `FAILED`/`FAIL`→failed | **none** | none | none | none (result: `output_images` on SUCCEED) | dummy task GET **401** (inference token rejected; Hub GET 200). No stored task id. Did not create a task |
| comfy-cloud | `GET https://cloud.comfy.org/api/v2/jobs/{id}` | `Authorization: Bearer` | `queued`, `running`, `succeeded`, `canceling`, `canceled`, `failed`, `expired` | `progress.value` **0–1** (also `nodes_done`/`nodes_total`, `step`/`steps`) | `queue_position` int\|null | **none** remaining. `metrics.queue_ms` / `metrics.execution_ms` are elapsed ms, nullable | `logs` object **serverless only** (`{deployment}.run.comfy.app`); Cloud: field absent. `metrics` object | 200, 401, 403, 404, 429, 500. **Not a Studio provider.** |
| customComfy | **same as civitai GetWorkflow** | Bearer | same | same | same | same | same | same |

---

## 1. Civitai orchestration

- Status: `GET https://orchestration.civitai.com/v2/consumer/workflows/{workflowId}`
- Optional query: `wait` (int seconds, default 0), `hideMatureContent`.
- List (reuse ids, read-only): official **QueryWorkflows** `GET /v2/consumer/workflows?take={n}` (default take 100). Cursor `next`. **`limit` is not a documented param**; live `?limit=5` was ignored (32 items).
- Auth: `Authorization: Bearer`.
- Studio: `providers/civitai.py` `job_status` → same GET; `list_jobs` → `GET /v2/consumer/workflows` (no take).
- customComfy submit is a recipe POST (not done here). **Poll is the same workflow GET.**

### Status enum (`WorkflowStatus`, shared by workflow / step / job)

`unassigned` → `preparing` → `scheduled` → `processing` → terminal `succeeded` | `failed` | `expired` | `canceled`.

`preparing` / `scheduled` = queued, not started. `preparing` = worker still downloading resources.

### Progress — **not** a field named `percent`

OpenAPI `WorkflowStepJob.estimatedProgressRate` and `WorkflowStep.estimatedProgressRate`: **number 0.0–1.0 or null**. Orchestrator formula: `elapsed × worker_throughput / job.cost`, clamped. Hint only. Cleared to null once the step is terminal (OpenAPI). Wait bar: `Math.round(rate * 100)` when non-null.

**No `percent` property** in local OpenAPI (`docs/_raw/repeat.openapi.yaml` schemas `WorkflowStepJob`, `WorkflowStep`) or live GET.

### Queue

`steps[].jobs[].queuePosition` → `WorkflowStepJobQueuePosition`:

| path | type | meaning |
| --- | --- | --- |
| `support` | `unsupported` \| `unavailable` \| `available` | JobSupport |
| `precedingJobs` | int32 \| null | jobs ahead (**this is what waitPane already reads**) |
| `startAt` | date-time \| null | estimated start |
| `completeAt` | date-time \| null | estimated complete |

Maps to UI: `job.queuePosition.precedingJobs`.

### ETA / remaining seconds

| name waitPane looks for | in OpenAPI / live GET |
| --- | --- |
| `job.estimatedDurationSeconds` | **none** |
| `job.etaSeconds` | **none** (job-level) |
| `queuePosition.estimatedWaitTime` | **none** |
| `queuePosition.completeAt` | yes, date-time estimate |
| `steps[].preparation.etaSeconds` | yes, **download remaining only** while `status=preparing` |

### Preparation (download, only while preparing)

`steps[].preparation`: `resource` (AIR), `queuePosition` (downloads ahead; 0 = transferring), `progress` (0.0–1.0 or null), `etaSeconds`. Live in-flight preparing job this run had **`preparation: null`**.

### Live GET (this session)

List `?take=50` → 33 workflows: preparing 1, succeeded 28, canceled 3, failed 1.

**In-flight** `GET .../workflows/12100372-20260831222942861` HTTP 200:

```
status: preparing
steps[0].status: preparing
steps[0].estimatedProgressRate: 1
steps[0].startedAt / completedAt: null
steps[0].jobs[0]:
  status: preparing
  estimatedProgressRate: 1
  cost: 20
  queuePosition: { support: "unavailable", precedingJobs: 4,
    startAt: "2026-08-31T22:32:31.7038805Z",
    completeAt: "2026-08-31T22:32:56.3952385Z" }
```

(`startAt`/`completeAt` UTC = 2026-09-01 06:32:31 / 06:32:56 CST.)

**Terminal** `GET .../workflows/12100372-20260831222239992` HTTP 200 `succeeded`. Job keys only `id, status, startedAt, completedAt, cost`. `queuePosition` and `estimatedProgressRate` **omitted**. No `percent`.

Missing id HTTP **404** `{type, title: "Not Found", status, traceId}`.

Schema: `docs/_raw/repeat.openapi.yaml` (`WorkflowStepJob`, `WorkflowStepJobQueuePosition`, `WorkflowStepPreparation`, `WorkflowStatus`) + https://developer.civitai.com/orchestration/guide/workflows + GetWorkflow reference (200/202/401/404).

---

## 2. Fal queue

Studio `providers/fal.py` `job_status`: `GET {QUEUE}/{eid}/requests/{rid}/status` then on COMPLETED `GET .../requests/{rid}`. Maps IN_QUEUE→pending, IN_PROGRESS→processing, COMPLETED→succeeded, FAILED→failed, CANCELLED/CANCELED→canceled. **Does not copy `queue_position` into `queuePosition.precedingJobs`.** WaitPane will not show Fal queue until that mapping exists.

Official: https://fal.ai/docs/documentation/model-apis/inference/queue  
Client types: fal_client `Queued.position`, `InProgress.logs`, `Completed.logs` + `metrics` — **no progress field**.

| method | URL | fields |
| --- | --- | --- |
| GET | `.../requests/{id}/status` | `status`, `queue_position` (IN_QUEUE), `request_id`, `response_url`, `status_url`, `cancel_url` |
| GET | `.../status?logs=1` | same + `logs[]` `{timestamp, message, level?}` |
| GET | `.../status/stream?logs=1` | SSE, same JSON until COMPLETED |
| GET | `.../requests/{id}` | model result; **202** while running |
| GET | `.../requests/{id}/logs` | **not in OpenAPI**; live **405** |
| GET | `.../requests/{id}/metrics` | **not in OpenAPI**; live **405** |
| GET | `https://api.fal.ai/v1/serverless/metrics` | Prometheus **account** metrics, not per-request; this key HTTP **403** |

COMPLETED extra: `metrics.inference_time` (seconds, **elapsed**, not remaining), `error`, `error_type`.

**No `progress` JSON path** in official queue schema.

Live (no Studio-saved Fal ids on disk): dummy UUID on `fal-ai/fast-sdxl`  
`GET .../status` 200 `{status: "COMPLETED", request_id: "00000000-…", logs: null, metrics: {inference_time: 0.049886}}` — **no `queue_position`**, **no `progress`**. Result GET 404 `"Request not found"`. Same UUID on `fal-ai/flux/schnell` status GET **405**.

Auth: `Authorization: Key {id}:{secret}`. HTTP from OpenAPI: 200, 401, 404, 402, 422, 429, 500; result also 202.

---

## 3. Hugging Face Inference / router

Studio generate is **synchronous POST** `https://router.huggingface.co/hf-inference/models/{id}` (`Accept: image/png` or `video/mp4`). `job_status` returns `{id, status: "succeeded", backend: "huggingface"}` with **nothing to poll**.

Official text-to-image: response body is **image bytes**, not a job object. No progress poll URL.

Live GET-only: `GET https://router.huggingface.co/v1/models` **200** `{object, data}`. `GET .../hf-inference/models/black-forest-labs/FLUX.1-schnell` **410** deprecated. No job id stored.

Auth: `Authorization: Bearer`. progress / queue / eta / logs / metrics: **none**.

---

## 4. ModelScope (魔搭)

Studio `job_status`: `GET {base_url()}/tasks/{tid}` with `Authorization: Bearer` and `X-ModelScope-Task-Type: image_generation`.

`base_url()`: disk `/home/box/.config/modelscope/base_url` is `https://api.modelscope.ai/v1`. **DNS for `api.modelscope.ai` failed this run.** Fallback `https://api-inference.modelscope.cn/v1` **resolves** — that is the host Studio will use after DNS.

Did **not** POST `/images/generations`. No `task_id` stored under `/workspace`. Dummy `GET .../tasks/does-not-exist-probe` → **401** `{errors: {message: "Authentication failed, please make sure that a valid ModelScope token is supplied."}, request_id}` (same token **200** on Hub model list). Cannot confirm poll JSON from a live task.

Documented / Studio-mapped fields (do not invent progress):

| path | notes |
| --- | --- |
| `task_status` | `PENDING`, `RUNNING`, `SUCCEED`, `FAILED` in poll examples; Studio also accepts `SUCCEEDED`/`SUCCESS`/`QUEUED`/`FAIL` |
| `output_images` | URLs when SUCCEED |
| `errors` | `{message, code?}` on failure |

**No `progress` / `percent` / queue / ETA** in Studio code or poll examples. Official AIGC doc pages fetched as empty JS shells this run.

HTTP observed: 401 (dummy). Examples also use 200 while polling. Do not claim 404 without a live not-found.

---

## 5. Comfy Cloud (note only — fifth provider **not** being added)

`GET https://cloud.comfy.org/api/v2/jobs/{id}`  
Auth: `Authorization: Bearer`.  
OpenAPI: https://docs.comfy.org/api-reference/v2/jobs/job-status-the-polling-workhorse (HTTP 200 this run).

`Job`: `status`, `queue_position` (int\|null), `progress` (`value` 0–1, `nodes_done`, `nodes_total`, `current_node`, `step`, `steps`, `message`), `metrics` (`queue_ms`, `execution_ms`, nullable ints), `logs` (serverless only; **absent on Cloud**), `urls.self|events|cancel`.

**Civitai `customComfy` is not this API** — it is the Civitai workflow GET in §1.

No Comfy Cloud API key / job id on this box; schema-only.

---

## Wiring notes for waitPane

1. **Elapsed** — keep client timer for every backend.  
2. **Queue** — Civitai: `steps[0].jobs[0].queuePosition.precedingJobs` (already). Fal: map `queue_position` → same shape. HF/MS: none.  
3. **Bar** — Civitai: `estimatedProgressRate * 100` when not null (preparing **and** processing). Fal/HF/MS: keep indeterminate unless a real field appears. Comfy Cloud (if ever): `progress.value * 100`.  
4. **Remaining ETA** — only from real fields: Civitai `completeAt - now`, or `preparation.etaSeconds` during download. **Do not** keep reading `estimatedDurationSeconds` / `etaSeconds` / `estimatedWaitTime` — they are not on the job. Fal `metrics.inference_time` is **completed elapsed**, not remaining.  
5. customComfy = Civitai row.
