# Comfy cloud providers for arbitrary workflow JSON

Research date: 2026-09-01 (UTC+8). Fresh overwrite of a prior draft that wrongly recommended hourly RunComfy. No generation POSTs, no API keys, `server.py` untouched.

**Goal:** pick a 5th Civitai Studio provider that can run **arbitrary ComfyUI workflow JSON (API format)** over REST, similar to Civitai `customComfy` / unlike Fal–Hugging Face–ModelScope single-model T2I endpoints.

**Hard billing constraint:** hourly / GPU-hour / machine-hour / rented-session billing is **not viable** (`不考虑按时计费`). Only per-run, per-job, per-workflow, or credit-per-generation. Hourly vendors are listed in section 4 (Excluded: hourly) and are **not** the recommendation.

**Do not invent:** every URL, auth header, price, and MCP name below is copied from a fetched official page. HTTP 404 is written as 404.

**Already known (not 5th-provider candidates):**

- Civitai `POST https://orchestration.civitai.com/v2/consumer/recipes/customComfy` — `resources` (AIR URNs, including `comfy:nodepack`) + opaque `workflow`. Local OpenAPI: `/workspace/civitai-studio/docs/_raw/customComfy.openapi.yaml`.
- Fal / Hugging Face / ModelScope = single endpoint, not arbitrary Comfy graphs.
- Cursor plugin catalog `SearchPlugins "comfy"` = **0 plugins**. Official MCP servers below live **outside** that catalog (vendor-hosted HTTP MCP).

Community graphs like **Moody Krea2 4K HD** (~85 nodes, rgthree / Impact / SeedVR2, local filenames) are hard on every managed runtime. See section 5.

## 1. Recommendation (per-run / credit billing only)

**5th provider: Comfy.org Cloud (`cloud.comfy.org`).**

**Runner-up: ComfyICU.**

Why Comfy.org Cloud first:

1. Official Comfy API v2 accepts the **API-format workflow graph verbatim**: `POST https://cloud.comfy.org/api/v2/jobs` with `{"workflow": {...}}`. Same shape as exporting File to Export Workflow (API). No AIR remapping, no deployment_id required on the multi-tenant Cloud surface.
2. Billing is **credits spent only while a job is running** (idle canvas time is free). Plans start at **$20/month Standard / 4,200 monthly credits**. Not GPU-hour machine rental.
3. First-party REST **and** first-party MCP (`https://cloud.comfy.org/mcp`) — relevant because the Cursor plugin catalog has zero Comfy plugins.
4. Closest Studio fit to Civitai `customComfy`: submit graph, poll job, download assets.

Why not the only pick: Comfy Cloud **does not** let you install arbitrary custom nodes (no Manager). rgthree / Impact / SeedVR2 only work if they are already on the Cloud allowlist.

**Runner-up ComfyICU** if you need cheaper credit-per-second GPU (`10,000 credits = $1`, L4 = 9 credits/s = **$0.0009/s**) and can live inside a frozen 95+ extension catalog. Request body is `{workflow_id, prompt}` where `prompt` is ComfyUI API JSON. Custom node **install is not supported**.

**CN-region alternative (still per-run coins, not hourly):** RunningHub shared/consumer API. Optional body field `workflow` is a **full API-format JSON string that overrides `workflowId`**. Consumer keys spend RH coins; Shared enterprise is billed per second based on GPU usage during API calls, no calls no charges. Dedicated GPU subscription is hourly-like and belongs in section 4.

Hourly vendors with a better custom-node story (RunComfy Cloud Save snapshot, ViewComfy environments, ThinkDiffusion machines, ComfyDeploy git clone) are capability-rich and billing-disqualified.

## 2. Comparison table

| name | arbitrary JSON | custom nodes | billingUnit | sourced price | REST | MCP | studioFit |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Comfy.org Cloud | yes — workflow API graph verbatim | preinstall / allowlist only; no Manager | per_credit | Standard $20/mo, 4,200 credits; 5s Wan 2.2 I2V template about 11 credits | yes | official https://cloud.comfy.org/mcp | good |
| ComfyICU | yes — prompt is ComfyUI API JSON | no user install; 95+ frozen extensions; Discord request | per_credit | 10k credits = $1; L4 9 cr/s ($0.0009/s); Basic $10/mo 100k credits | yes | none in official docs | good |
| RunningHub (CN+EN) | yes — optional workflow JSON string overrides workflowId | platform packs, latest node plugins updated daily; not per-request git | per_credit (shared/consumer); dedicated = hourly | official: RH coins / per-second GPU on API calls; USD table not on fetched docs | yes | none in official docs | good (shared/consumer only) |
| Replicate any-comfyui-workflow | yes — workflow_json string | preinstall list; request via GitHub issue / fork Cog | per_run | public model billed per prediction-second; playground ~$0.014/run on L40S (varies) | yes | official mcp.replicate.com | maybe (catalog nodes only) |
| Civitai customComfy | yes — opaque workflow + required AIR resources | runtime comfy:nodepack AIR URNs | per_credit | post-paid GPU-seconds; apps guide roughly ~1 Buzz per GPU-second; infra failures do not charge | yes | none in official docs | good (already a Studio provider; AIR+filenames are the pain) |
| ComfyDeploy | no at request time — deployment_id + inputs | Manager picker + git clone / commit hash / Docker | unknown (GPU credits; public $ table login-gated) | app.comfydeploy.com/pricing HTTP 200 login wall; www.comfydeploy.com/pricing 404 | yes | not in official API docs | no |
| RunComfy Serverless (ComfyUI) | yes — workflow_api_json | Manager + Cloud Save snapshot | hourly (instance uptime incl. keep-warm) | Medium $0.99/h to 3X-Large $8.75/h | yes | official https://mcp.runcomfy.com/mcp | no (hourly) |
| ViewComfy | yes — override_workflow_api on a deployment | install on deployment / Custom Comfy Environments (Studio+) | hourly (per active GPU second, listed $/hour) | T4 $0.65/h to B200 $13.32/h; Developer $0 + compute | yes | none in official docs | no (hourly) |
| ThinkDiffusion | no public ComfyUI REST job API | install any in the machine | hourly | Quick 16GB $0.99/h; Turbo 24GB $1.75/h; Ultra 48GB $2.50/h | A1111 machine API only | none in official docs | no |
| Fal / HF / ModelScope | no | n/a | per_run (Fal) | out of scope | yes | n/a | no |

studioFit = capability (arbitrary API-format JSON over REST) AND per-run / per-credit billing.

## 3. Per-vendor sections

### 3.1 Comfy.org Cloud

- site: https://comfy.org/cloud/
- docs: https://docs.comfy.org/api-reference/v2/overview HTTP 200
- submit docs: https://docs.comfy.org/api-reference/v2/jobs/submit-a-workflow-for-execution HTTP 200
- status docs: https://docs.comfy.org/api-reference/v2/jobs/job-status-the-polling-workhorse HTTP 200
- pricing: https://comfy.org/cloud/pricing/ HTTP 200
- MCP docs: https://docs.comfy.org/agent-tools/mcp HTTP 200
- Arbitrary workflow JSON? Yes. Accepts the API-format workflow graph verbatim. UI-format (nodes/links) is rejected as workflow_format_ui. Cloud: Create an API key and you can submit any workflow.
- Request shape: POST /api/v2/jobs body {"workflow": {API graph}, "extra_data": {"api_key_comfy_org": "..."}}. Header Idempotency-Key optional.
- Custom nodes: pre-installed popular community nodes; expanding by demand. Knowledge base: Custom Nodes Manager is not available on Comfy Cloud. No git-install API.
- Auth: Cloud/serverless Authorization: Bearer <api-key> (v2). v1 Cloud also documents X-API-Key. MCP on Cursor uses X-API-Key (keys start with comfyui-).
- Submit URL: https://cloud.comfy.org/api/v2/jobs (also https://{deployment}.run.comfy.app/api/v2/jobs for a pinned serverless deployment).
- Status URL: GET https://cloud.comfy.org/api/v2/jobs/{id} (follow urls.self from the 201 Job object).
- Official MCP? Yes. Hosted https://cloud.comfy.org/mcp (HTTP 401 without auth — endpoint exists). Local pip install comfy-mcp is for self-hosted ComfyUI, not Cloud GPUs.
- billingUnit: per_credit. Credits spent on active GPU time while a workflow is running plus Partner Nodes. Idle edit time is free. Monthly credits do not roll over; top-ups last 1 year.
- Sourced price: Standard $20/month, 4,200 credits, 30 min max runtime, 1 concurrent API job. Creator $35/mo 7,400 credits (BYO models). Pro $100/mo 21,100 credits, 1 hour max. A five-second video uses roughly 11 credits (Wan 2.2 I2V template defaults). 5 free runs, no card. API access requires a paid subscription — a credit top-up alone is not enough.
- studioFit: good.

### 3.2 ComfyICU

- site: https://comfy.icu/
- docs: https://comfy.icu/docs/api HTTP 200
- FAQ: https://comfy.icu/docs/faq HTTP 200
- pricing: https://comfy.icu/serverless/ HTTP 200
- Arbitrary workflow JSON? Yes. Body field prompt is ComfyUI API JSON. You still create a workflow_id in the UI first; each run sends the graph as prompt.
- Request shape: POST /api/v1/workflows/{workflow_id}/runs JSON {workflow_id, prompt, files?, accelerator?, webhook?}. files maps Comfy paths to download URLs (inputs, LoRAs, checkpoints).
- Custom nodes: custom node installation is not supported. Shared executor: 95+ extensions, 4,000+ nodes, 2,000+ models. User install blocked. Paid users can Discord-request nodes (#model-node-request). No Manager. One frozen version per node.
- Auth: authorization: Bearer $COMFYICU_API_KEY.
- Submit URL: https://comfy.icu/api/v1/workflows/{workflow_id}/runs
- Status URL: GET https://comfy.icu/api/v1/workflows/{workflow_id}/runs/{run_id} (poll until COMPLETED / ERROR).
- Official MCP? Not documented on fetched pages.
- billingUnit: per_credit. Credits are spent only while a workflow is running. Never charged for idle.
- Sourced price: 10,000 credits = $1. Per-second: L4 9 cr ($0.0009), L40S 32 cr ($0.0032), H100 64 cr ($0.0064) on serverless page. FAQ also lists A100 40GB 32 cr, A100 80GB 47 cr. New accounts 5,000 free credits. Plans: Basic $10/mo 100k credits; Standard $30/mo 315k; Pro $60/mo 660k. Credits do not roll over. Dedicated GPUs (idle billed) are a separate sales path — treat as hourly if used.
- studioFit: good (credit-per-run + arbitrary prompt JSON). Moody Krea2-class graphs fail unless every class_type is in the frozen catalog.

### 3.3 RunningHub (EN runninghub.ai + CN runninghub.cn)

- EN create: https://www.runninghub.ai/runninghub-api-doc-en/api-425761093 HTTP 200
- EN intro: https://www.runninghub.ai/runninghub-api-doc-en/doc-8287463 HTTP 200
- EN enterprise: https://www.runninghub.ai/runninghub-api-doc-en/doc-8287465 HTTP 200
- EN query v2: https://www.runninghub.ai/runninghub-api-doc-en/api-425767807 HTTP 200
- CN create: https://www.runninghub.cn/runninghub-api-doc-en/api-425761093 HTTP 200
- CN intro: https://www.runninghub.cn/runninghub-api-doc-en/doc-8287463 HTTP 200
- stale status doc: https://www.runninghub.ai/runninghub-api-doc-en/api-276642707 HTTP 404
- stale output doc: https://www.runninghub.ai/runninghub-api-doc-en/api-276642708 HTTP 404
- Arbitrary workflow JSON? Yes. Optional body field workflow: Custom full workflow in JSON string format. If provided, it overrides workflowId. Example is API-format node map. Typical path is still: import on site, run once, then workflowId + nodeInfoList overrides. Docs also: The workflow ID called by the API must have successfully run at least once.
- Request shape: POST /task/openapi/create JSON {apiKey, workflowId, nodeInfoList?, workflow?, webhookUrl?, instanceType?, usePersonalQueue?}. nodeInfoList: {nodeId, fieldName, fieldValue}.
- Custom nodes: no per-request git URL. Enterprise copy: latest and most comprehensive node plugins updated daily. You import the graph into their Comfy and they resolve packs. Not a snapshot API.
- Auth: header Authorization: Bearer [Your API KEY] and body apiKey. Header Host must match www.runninghub.ai or www.runninghub.cn.
- Submit URL EN: https://www.runninghub.ai/task/openapi/create
- Submit URL CN: https://www.runninghub.cn/task/openapi/create
- Status URL: POST https://www.runninghub.ai/openapi/v2/query body {taskId}. ComfyUI samples also poll POST /task/openapi/outputs with {apiKey, taskId}. Linked Check Task Status doc IDs 404.
- Official MCP? Not on fetched RunningHub API docs.
- billingUnit: per_credit for Consumer-Member (RH coins, same as website) and Enterprise-Shared (billed per second based on GPU usage during API calls; no calls, no charges). Enterprise-Dedicated = prepaid GPU x duration = hourly / excluded.
- Sourced price: official docs say for detailed pricing refer to the website / RH coins. No official USD or RH-coin public table was on the fetched API docs. Free users cannot use the API; Consumer-Member or higher required.
- studioFit: good for shared/consumer. no if the account is Dedicated.

### 3.4 Replicate

- guide: https://replicate.com/docs/guides/extend/comfyui HTTP 200
- model page: https://replicate.com/comfyui/any-comfyui-workflow HTTP 200
- HTTP API: https://replicate.com/docs/reference/http HTTP 200
- pricing: https://replicate.com/pricing HTTP 200
- MCP docs: https://replicate.com/docs/reference/mcp HTTP 200
- MCP host: https://mcp.replicate.com HTTP 200
- stale MCP path: https://replicate.com/docs/topics/mcp HTTP 404
- nodes list: https://github.com/replicate/cog-comfyui HTTP 200
- Arbitrary workflow JSON? Yes. Input workflow_json is API-format graph as a JSON string. Guide model fofr/any-comfyui-workflow:latest.
- Custom nodes: preinstalled popular packs. Request more via GitHub issue or fork cog-comfyui.
- Auth: Authorization Bearer per Replicate HTTP API docs.
- Submit URL documented at replicate.com/docs/reference/http : api.replicate.com/v1/predictions
- billingUnit: per_run for public models.
- Sourced price: model page about $0.014/run on L40S (varies). replicate.com/pricing is per-second hardware.
- studioFit: maybe (catalog nodes only).


### 3.5 Civitai customComfy (already a Studio provider)
- Local OpenAPI: /workspace/civitai-studio/docs/_raw/customComfy.openapi.yaml
- recipe docs: developer.civitai.com/orchestration/reference/operations/InvokeCustomComfyStepTemplate HTTP 200
- GetWorkflow: developer.civitai.com/orchestration/reference/operations/GetWorkflow HTTP 200
- apps guide: developer.civitai.com/apps/guide/comfy-cloud HTTP 200
- orchestration.civitai.com recipe path GET HTTP 405 (POST-only).
- Arbitrary workflow JSON? Yes. workflow forwarded opaquely. Orchestrator does not scan the graph.
- Request: required resources (AIR URNs, min 1), workflow, trace. Optional sessionId, comfyImage, minVramGb, useSageAttention, minimumDurationSeconds.
- Custom nodes: comfy:nodepack AIR URNs in resources, or baked into comfyImage. Missing pack fails at load.
- Auth: Authorization Bearer (OpenAPI http bearer).
- Submit: orchestration.civitai.com/v2/consumer/recipes/customComfy
- Status: orchestration.civitai.com/v2/consumer/workflows/{workflowId}
- Official MCP: not in fetched Civitai developer docs.
- billingUnit: per_credit (Buzz). After-execution runtime; infra failures do not charge. Floor 1 Buzz. Apps guide roughly ~1 Buzz per GPU-second.
- studioFit: good as existing provider. Local filenames plus undeclared packs fail.


### 3.6 ComfyDeploy
- API: docs.comfydeploy.com/docs/api HTTP 200
- Queue Run: docs.comfydeploy.com/docs/api/queueRun HTTP 200
- Get Run: docs.comfydeploy.com/docs/api/getRun HTTP 200
- import JSON: docs.comfydeploy.com/docs/workflows/import HTTP 200
- custom nodes: docs.comfydeploy.com/docs/machines/environment HTTP 200
- pricing UI: app.comfydeploy.com/pricing HTTP 200 login wall
- public pricing: www.comfydeploy.com/pricing HTTP 404
- Arbitrary JSON at request time? No. Queue body is deployment_id plus inputs. Import JSON is a dashboard machine-build step.
- Custom nodes: Manager picker, git clone plus commit hash, Docker RUN.
- Auth: Authorization Bearer YOUR_API_KEY
- Submit: api.comfydeploy.com/api/run/deployment/queue
- Status: api.comfydeploy.com/api/run/{run_id}
- Official MCP: not on fetched docs.comfydeploy.com API pages (GitHub comfydeploy-mcp not copied as official).
- billingUnit: unknown. Public dollar table not sourced. Persistent machines may be hourly.
- studioFit: no (not arbitrary JSON per call).

### 3.7 RunComfy Serverless API (ComfyUI)
- async queue: docs.runcomfy.com/serverless/async-queue-endpoints HTTP 200
- billing: docs.runcomfy.com/serverless/about-billing HTTP 200
- custom workflows: docs.runcomfy.com/serverless/custom-workflows HTTP 200
- MCP tools: docs.runcomfy.com/mcp/tool-reference HTTP 200
- MCP quickstart: docs.runcomfy.com/mcp/quickstart HTTP 200
- pricing page: www.runcomfy.com/pricing HTTP 200
- MCP endpoint mcp.runcomfy.com/mcp HTTP 401 unauthenticated (alive)
- Arbitrary workflow JSON? Yes (advanced). Body workflow_api_json runs that graph instead of the stored workflow. Common path is overrides only.
- Custom nodes: ComfyUI Manager then Cloud Save snapshot (graph plus runtime container). Dynamic JSON still needs those class_types on the snapshot.
- Auth: Authorization Bearer token
- Submit: api.runcomfy.net/prod/v2/deployments/{deployment_id}/inference
- Status: .../requests/{request_id}/status
- Official MCP: yes. mcp.runcomfy.com/mcp Cursor name runcomfy. Tool submit_request accepts workflow_api_json.
- billingUnit: hourly. Serverless API is GPU instance uptime billed per second including cold start and keep-warm. Model API is per-request but not arbitrary Comfy graphs.
- Sourced price: Medium $0.99/h, Large $1.75/h, XL $2.50/h, XL+ $2.99/h, 2XL $4.99/h, 2XL+ $7.49/h, 3XL $8.75/h. Pro 20-30 percent off.
- studioFit: no (hourly). Capability would otherwise be good.

### 3.8 ViewComfy
- quick start: docs.viewcomfy.com/viewcomfy_api/quick_start HTTP 200
- inference: docs.viewcomfy.com/viewcomfy_cloud/inference HTTP 200
- override docs: docs.viewcomfy.com/viewcomfy_api/updating_workflows HTTP 200
- pricing: www.viewcomfy.com/pricing HTTP 200
- Arbitrary JSON? Yes on an existing deployment via override_workflow_api. New workflow must already run on that deployment (nodes/models installed).
- Request: copy view_comfy_api_url from dashboard. Status GET api.viewcomfy.com/api/workflow/infer/?prompt_ids=... Headers client_id and client_secret (not Bearer).
- Custom nodes: installed on the Comfy environment. Studio+ Custom Comfy Environments.
- Official MCP: not on fetched docs.
- billingUnit: hourly. Compute billed per active GPU second, listed as dollars per hour.
- Sourced price: Developer $0 + compute. T4 $0.65/h, L4 $1.16/h, A10G $2.20/h, L40S $3.51/h, A100 $4.10/h, A100-80GB $6.15/h, H100 $8.42/h, H200 $9.65/h, B200 $13.32/h.
- studioFit: no (hourly).

### 3.9 ThinkDiffusion
- docs home: docs.thinkdiffusion.com HTTP 200
- ComfyUI page: docs.thinkdiffusion.com/ai-art-video-models-and-apps/comfyui-in-the-cloud HTTP 200
- FAQ: learn.thinkdiffusion.com/thinkdiffusion-faqs/ HTTP 200
- pricing: www.thinkdiffusion.com/pricing HTTP 200
- Arbitrary Comfy REST job API? No. Dedicated browser machine. FAQ covers Automatic1111 /docs on the machine URL, not a Comfy cloud job API.
- Custom nodes: install any in the machine; persistent on Pro. Hobby: deleted after 48h inactivity.
- Official MCP: none in fetched docs.
- billingUnit: hourly. Pay the hourly rate for launching a machine.
- Sourced price: Hobby 15 min free. Quick 16GB $0.99/hr, Turbo 24GB $1.75/hr, Ultra 48GB $2.50/hr. TD-PRO $19.99/mo yearly or $29.99/mo, 20 percent off machines.
- studioFit: no.

### 3.10 Fal / Hugging Face / ModelScope
Single-model HTTP APIs. They do not accept arbitrary ComfyUI API-format graphs. Out of scope for the 5th provider. Already covered by existing Studio providers.

## 4. Excluded: hourly

Do not use these as the 5th provider under the billing rule (no GPU-hour / machine-hour / rented-session).

| vendor | why excluded | still useful |
| --- | --- | --- |
| RunComfy Serverless (ComfyUI) | GPU instance uptime dollars/hour including keep-warm | Best arbitrary-JSON REST plus official MCP if billing rule is relaxed |
| ViewComfy | Compute table is dollars/hour GPU (per active GPU second) | Override workflow_api on a deployment; custom environments |
| ThinkDiffusion | Hourly dedicated machine; no Comfy job REST | Full custom nodes in a session |
| RunningHub Enterprise-Dedicated | Prepaid GPU x duration, unlimited calls | Shared/consumer RH-coin path is not in this table |
| ComfyICU dedicated GPUs | FAQ: dedicated GPUs billed for idle time | Shared serverless credits stay eligible |
| Replicate private deployments | Pay for instance online / idle | Public any-comfyui-workflow predictions stay eligible |
| ComfyDeploy persistent machines | machine can sit billed; public price 404 | Queue-run credits might be OK; still no per-call arbitrary JSON |

RunComfy Model API is per-request and is not an arbitrary Comfy graph API.

## 5. Moody Krea2-like graph feasibility

Target: about 85 nodes, rgthree, Impact Pack, SeedVR2, local filenames for checkpoints/LoRAs/VAEs.

| provider | likely outcome | why (from docs, not a live run) |
| --- | --- | --- |
| Civitai customComfy | hard fail unless rewritten | Must declare every ckpt/lora and comfy:nodepack as AIR. Local ckpt_name is not an AIR. Orchestrator does not scan the graph. |
| Comfy.org Cloud | fail if any class_type is off the allowlist | No Manager. SeedVR2 / rgthree / Impact only if Comfy already shipped them. Filenames must match Cloud library (or Creator+ BYO LoRA). |
| ComfyICU | fail unless all class_types are in the frozen 95-ext catalog | Cannot git-install. files can fetch models by URL but not new node packs. |
| RunningHub | best chance among per-run vendors | Daily node updates plus import-then-run. Still need their disk names, not laptop paths. workflow string override does not install a missing pack. |
| Replicate any-comfyui-workflow | fail for SeedVR2-class packs unless already in cog-comfyui | Preinstall list plus GitHub issue. Rewrite local paths to supported names or URLs. |
| RunComfy / ViewComfy / ComfyDeploy / ThinkDiffusion | technically feasible (Manager / git / snapshot) | Disqualified by hourly, or by ComfyDeploy non-arbitrary request shape. |

Practical rewrite for a per-run 5th provider:
1. Export API format (not UI JSON).
2. Replace local filenames with URLs or platform library names.
3. Drop or replace rgthree / Impact / SeedVR2 with core or Partner nodes, or pick RunningHub after a successful on-site run.
4. On Civitai, emit AIR plus comfy:nodepack URNs. Do not send a raw community PNG/JSON.

There is no per-run vendor that both git-installs arbitrary node packs at request time and bills like Fal.
Closest API shape: Comfy.org Cloud, ComfyICU, RunningHub workflow string, Replicate workflow_json, Civitai workflow.
Closest for nasty community graphs: RunComfy Cloud Save / ComfyDeploy machine / ViewComfy environment / ThinkDiffusion — all hourly except RunningHub import-on-platform.

## 6. HTTP 404s (fetched)

| URL | status |
| --- | --- |
| https://www.comfydeploy.com/pricing | 404 |
| https://www.runninghub.ai/runninghub-api-doc-en/api-276642707 | 404 (old Check Task Status) |
| https://www.runninghub.ai/runninghub-api-doc-en/api-276642708 | 404 (old Check Task Output) |
| https://replicate.com/docs/topics/mcp | 404 (real MCP docs: /docs/reference/mcp) |

Related non-404 notes: unauthenticated MCP roots returned 401 (mcp.runcomfy.com/mcp, cloud.comfy.org/mcp, mcp.replicate.com/sse). Civitai recipe path returned 405 on GET (POST-only).

## 7. Cursor plugins

Catalog search comfy = 0. Wire Studio via vendor REST, or add remote MCP by URL (Comfy Cloud, RunComfy, Replicate) — not via Cursor plugin marketplace.

