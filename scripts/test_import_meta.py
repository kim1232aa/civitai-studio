#!/usr/bin/env python3
"""Sampler/scheduler normalize + local PNG parse + live public import of 136863587."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from providers import io_meta
from providers import civitai as civ

fails = []


def check(cond, msg):
    if not cond:
        fails.append(msg)


check(io_meta.normalize_sampler("ER_SDE", civ.SAMPLERS) == "er_sde", "ER_SDE")
check(io_meta.normalize_scheduler("SGM_UNIFORM", civ.SCHEDULERS) == "sgm_uniform", "SGM_UNIFORM")
samp, sched = io_meta.split_sampler_scheduler("er_sde_simple", "")
check(io_meta.normalize_sampler(samp, civ.SAMPLERS) == "er_sde", f"split samp {samp}")
check(io_meta.normalize_scheduler(sched, civ.SCHEDULERS) == "simple", f"split sched {sched}")
a, b = civ._normalize_pair("ER_SDE", "SGM_UNIFORM")
check(a == "er_sde" and b == "sgm_uniform", f"pair {a} {b}")
a, b = civ._normalize_pair("ER_SDE", "")
check(a == "er_sde" and b == "sgm_uniform", f"missing sched defaulted to {b} not sgm_uniform")

png = Path("/tmp/civitai-img/136863587.jpg")
if png.exists():
    parsed = io_meta.parse_media_bytes(png.read_bytes(), "136863587.png")
    check(parsed.get("source") == "png-comfy", f"source {parsed.get('source')}")
    check(parsed.get("sampler") == "er_sde", f"png sampler {parsed.get('sampler')}")
    check(parsed.get("scheduler") == "sgm_uniform", f"png scheduler {parsed.get('scheduler')}")
    check(parsed.get("steps") == 8, f"png steps {parsed.get('steps')}")
    check(parsed.get("width") == 960 and parsed.get("height") == 1440, "png size")
    check(parsed.get("seed") == 885241235067319, f"png seed {parsed.get('seed')}")
    check(parsed.get("denoise") == 1 or parsed.get("denoise") == 1.0, f"png denoise {parsed.get('denoise')}")
    check("hinaKrea2" in str(parsed.get("checkpointName") or parsed.get("Model") or ""), f"png model {parsed.get('checkpointName')}")
    check(parsed.get("comfyNodeCount") and parsed.get("comfyNodeCount") >= 10, f"nodes {parsed.get('comfyNodeCount')}")
else:
    fails.append("fixture png missing")

try:
    imported = civ.import_image("https://civitai.red/images/136863587")
    Path("/tmp/civitai-img/import_136863587.json").write_text(json.dumps({
        k: imported.get(k) for k in (
            "sampler", "scheduler", "steps", "cfgScale", "width", "height", "seed",
            "denoise", "diffusionModel", "checkpointName", "serviceId", "ecosystem",
            "loras", "unmatched", "comfyNodeCount", "importSource", "empty",
            "prompt",
        )
    }, ensure_ascii=False, indent=2, default=str))
    check(imported.get("sampler") == "er_sde", f"imp sampler {imported.get('sampler')}")
    check(imported.get("scheduler") == "sgm_uniform", f"imp scheduler {imported.get('scheduler')}")
    check(imported.get("steps") == 8, f"imp steps {imported.get('steps')}")
    check(imported.get("width") == 960 and imported.get("height") == 1440, "imp size")
    check(str(imported.get("seed")) == "885241235067319", f"imp seed {imported.get('seed')}")
    air = imported.get("diffusionModel") or ""
    check("2782456" in air and "3133872" in air, f"imp air {air}")
    check("Krea2" in (imported.get("checkpointName") or "") or "1125" in (imported.get("checkpointName") or ""), f"imp ckpt {imported.get('checkpointName')}")
    check(imported.get("prompt"), "imp prompt empty")
    check(imported.get("scheduler") != "simple", "scheduler must not fall back to simple")
except Exception as e:
    fails.append(f"import_image raised {type(e).__name__}: {e}")

if fails:
    print("FAIL")
    for f in fails:
        print(" -", f)
    sys.exit(1)
print("PASS import meta mapping")
sys.exit(0)
