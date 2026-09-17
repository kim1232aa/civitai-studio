# GOAL — finish line (boss 原话优先)

**Authority:** 老板原件 — 群里长消息 + `docs/REQUIREMENTS-20260910.md` 照抄段。  
`docs/00-IRON-RULES.md` = 工作备忘，**不当老板原话**。  
eggbot / agent 缩写（含今日 API·匹配复述）**作废**，不作准。

## Boss locked outcome (2026-09-16)
Product not done until **all three** advance with page evidence (no curl generate):

### A. 六家 API 完整能力
Providers: Civitai / Fal / Hugging Face / 魔搭 AI / 魔搭 CN / NanoGPT.  
Investigate official docs → integrate **full** model capabilities.  
Each house must page-↑ walk **文生图 / 图生图 / 图生视频**; media saves locally.  
Model + LoRA search; LoRA must match current base model.  
「API 真支持」= official capabilities must be selectable/sendable/verifiable (gaps = debt).  
null strength：**匹配没有就是没有** (do **not** invent 0.75/1.0). 魔搭/HF **matching：禁止近似** — improve search/match; match base+LoRA when possible; else say so. Self-provision real LoRA+multi-param models = capability, not fake match.

### B. Civitai 帖智能匹配（六家都能做）
Import link/id → full recipe on screen (prompt/negative/base/LoRA/weights/size/steps/CFG/seed…).  
**Recognize the house the user selected first**, then match a runnable model **inside that house**.  
If none: say so plainly. Forbidden: shorten prompt; default Krea2; cross-house swap; silent provider jump to Fal.

### C. Seko 无限画布真能力
Replicate Seko infinite-canvas **real features**, not skin-only rounds.  
配方台 is separate surface but API/smart-match there must also be completed.

## Scoreboard (Looper)
`HANDOFF-20260914` / verifier UI绿 / tip合码 **≠ 验收**。交付证据仍看本机 `verify.sh` + 同次画布写回包；verify PASS tip 现为 **14**（**≠产品验收**）：上列 13 + `hf-119393356-t2i-reburn-seko-live`（HF t2i reburn：seko-01 `bf6e4e26…` 独包 · baseline=seko-04 · promptLen=1451≡import · LoRA cleared 诚实 · 卡+硬刷 OK · visdiff≈20.87）。

## Scoreboard (Looper)
`bash .cursor/loops/hard-gate-closed-loop/verify.sh` exit 0 still requires an honest same-burn pack under `docs/review-shots/closed-loop/<id>/` (canvas page ↑, original-post params, writeback to original card after hard refresh, non-empty Seko same-flow).  
HANDOFF ✅ / green tests ≠ Pass. Closed-loop tip count **14** (Civitai t2i+i2i+i2v + 魔搭CN t2i+i2i + 魔搭AI t2i+i2i + Nano t2i+i2i+i2v + Fal t2i+i2i+i2v + HF t2i; HF tip 1). Product 验收 / 闭环 still **0** until iron hard gate + six-provider pillars.

## Boss locks (2026-09-17, corrected twice)
- Civitai `strength=null`：**匹配没有就是没有** — do not invent 0.75/1.0.
- 魔搭/HF **matching 禁止近似**：完善搜索/匹配；底模·LoRA 能配就配，配不上如实说。自挂真 LoRA+多参模型 = 能力补齐，≠ 假匹配。

## Anti-jobs
No invent Pass; no feature cuts; no gallery-as-canvas; no empty Seko baseline; no selling agent paraphrase as 老板原话.

## Owners
Looper = finish line · 开发 = ship/burns · api = outbound · Grok Build = knives · Critiquito/UI = shots after hard gate
