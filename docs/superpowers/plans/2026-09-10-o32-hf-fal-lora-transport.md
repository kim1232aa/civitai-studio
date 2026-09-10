# o32 HF Fal LoRA transport

## Symptom
`28216105` HF↑: serviceId=`fal-ai/flux-lora` (o31 pin OK) → 400 `Model not supported by provider fal-ai`, jobId=null.

## Root
`POST https://router.huggingface.co/fal-ai/fal-ai/flux-lora` — HF Inference Providers does not list Fal `/lora` apps (same as `_maybe_lora_pid` docstring).

## Fix
When `backend=huggingface` and `serviceId` is official Fal LoRA (`fal-ai/flux-lora`, `fal-ai/krea-2/turbo/lora`, …):
- Prefer call Fal queue with Fal key; meta `backend=huggingface`, `submittedInput.transport=fal`.
- Else honest Composer: HF Router 不托管 → 换家 Fal; keep chips.
Never Hub krea turbo; never drop LoRA; never invent strength.

## Acceptance
o32 tip hash + selfcheck; then new unused AIImageStudio sample for HF page↑ (28216105 = wiring only). Closed-loop 0.
