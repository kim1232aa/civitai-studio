# o25 sdcpp sampler allowlist map Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Map import/post sampler `dpmpp_2m` (and honest siblings) onto sdcpp official `sampleMethod` enum so page ↑ for sample 19201654 does not 400 with `sampleMethod=dpmpp_2m 不在允许列表`.

**Architecture:** Keep studio/import canon as Comfy-style names (`dpmpp_2m`). Only at outbound `_assign_choice` for enum fields (`sampleMethod` / `schedule`), resolve raw → exact allowlisted token via fold/compact-fold + explicit honest aliases. Locked: `dpmpp_2m` → `dpm++2m`. Scheduler `karras` already allowlisted as `schedule=karras`. Do not touch o23 serviceId stick or o24 capsule.

**Tech Stack:** Python providers (`io_meta.py`, `civitai.py`), unittest contract tests.

**Spec:** Knife from 开发 + LOCKED mapping from api对接助手; iron rules docs/00-IRON-RULES.md; allowlist from docs/capabilities.json sdcpp sampleMethod enum.

## Global Constraints

- NEVER invent strength / LoRA / silent krea2 fallback
- NEVER curl /api/generate as acceptance
- closed-loop remains 0; NEVER 可交付
- Prefer exact official enum names only
- Keep o23 serviceId + o24 capsule untouched unless necessary

---

### Task 1: Failing contract test for 19201654 sampler map

**Files:**
- Modify: `scripts/test_civitai_parameter_contract.py`
- Modify: `providers/io_meta.py` (helper)
- Modify: `providers/civitai.py` (`_assign_choice`)

**Interfaces:**
- Consumes: `civ.build_workflow`, sdcpp sdxl serviceId, import sampler/scheduler
- Produces: outbound `sampleMethod=dpm++2m`, `schedule=karras`

- [x] **Step 1: Write the failing test**

```python
def test_sdcpp_sdxl_maps_dpmpp_2m_karras_from_import(self):
    payload = {
        "serviceId": "image/sdcpp/sdxl/createImage",
        "prompt": "score_9 …",
        "width": 1024,
        "height": 1024,
        "steps": 30,
        "cfgScale": 7.0,
        "seed": 3436905144,
        "sampler": "dpmpp_2m",
        "scheduler": "karras",
        "diffusionModel": "urn:air:sdxl:checkpoint:civitai:317902@593760",
        "loras": [{"air": "urn:air:sdxl:lycoris:civitai:518563@633865", "strength": 0.7}],
    }
    inp = step_input(civ.build_workflow(payload))
    self.assertEqual(inp["sampleMethod"], "dpm++2m")
    self.assertEqual(inp["schedule"], "karras")
    self.assertNotIn("sampler", inp)
```

- [x] **Step 2: Run test to verify it fails**

Run: `python -m unittest scripts.test_civitai_parameter_contract.CivitaiParameterContractTest.test_sdcpp_sdxl_maps_dpmpp_2m_karras_from_import -v`
Expected: FAIL with `sampleMethod=dpmpp_2m 不在允许列表`

- [x] **Step 3: Implement match_allowed_choice + wire _assign_choice**

In `io_meta.py`: compact fold + aliases including locked `dpmpp_2m`→`dpm++2m`, `euler_ancestral`→`euler_a`, `dpm_2`→`dpm2`, `dpmpp_2s_ancestral`→`dpm++2s_a`. In `civitai._assign_choice`: resolve via helper before `_check_range`.

- [x] **Step 4: Run tests pass**

- [x] **Step 5: Stamp o25 + commit + push + report under /workspace/projects/**
