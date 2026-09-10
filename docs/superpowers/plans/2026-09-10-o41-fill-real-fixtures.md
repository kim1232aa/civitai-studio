# o41 fillRefSlotsToCap real fixtures

**Goal:** 「灌满测试」must attach **readable** local refs. Today it invents `/out/o40-fill-{n}-{uid}.png` with no file on disk → Nano/server: `无法读取本地参考图`.

**Evidence:** audit `2026-09-10T14:38:14` — `无法读取本地参考图 /out/o40-fill-1-69mi.png`；`ls out/o40-fill*` empty. Real fixtures already at `docs/review-shots/closed-loop/fal-refs-fill-9/ref-{1..9}.jpg` and copies under `out/ref-*_*.jpg`.

**Fix (stamp `v0821o41-fill-real-fixtures`):**
1. On 灌满, for each needed slot `i=1..remain`: ensure a file exists under `ROOT/out/` (prefer copy from `docs/review-shots/closed-loop/fal-refs-fill-9/ref-{i}.jpg` into a stable name e.g. `out/fill-cap-{i}.jpg`, or reuse existing).
2. Point character node `url` at that **existing** `/out/...` path (same extension as file).
3. Keep o40 exact-cap: stop at `countRefUrls==maxRefs`; never invent phantom URLs.
4. Optional tiny server helper `/api/ensure-fill-fixtures` OR pure client assuming files pre-copied at startup — prefer **pre-copy in fill button via fetch-to-blob only if already served**; simplest: hardcode URLs to `/out/fill-cap-1.jpg` … `/out/fill-cap-9.jpg` and add a one-shot ensure in `server.py` on boot or first generate that copies fixtures if missing.

**Verify:** click 灌满 → 参考 5/5 → Nano `openai/gpt-image-2.5/flare/edit` ↑ → no 文件不存在; audit shows 5 local image paths readable; jobId non-null.

**Do not:** invent LoRA; curl generate as acceptance; shorten prompts for closed-loop scoring (this knife is fill-cap smoke with `slight color grade` OK).
