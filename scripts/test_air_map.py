#!/usr/bin/env python3
"""GET-only AIR mapper tests. Moody sample is a fixture, not hardcoded in the mapper."""
from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path("/workspace/civitai-studio")
sys.path.insert(0, str(ROOT))

FORBIDDEN = (
    "/v2/consumer/workflows",
    "/v2/consumer/recipes/customComfy",
    "/v2/consumer/recipes/comfyNodepackSnapshot",
    "/api/generate",
    "comfyNodepackSnapshot",
)

_real_urlopen = urllib.request.urlopen


def _guard_urlopen(req, *args, **kwargs):
    url = getattr(req, "full_url", None) or getattr(req, "get_full_url", lambda: str(req))()
    method = (getattr(req, "get_method", lambda: "GET")() or "GET").upper()
    data = getattr(req, "data", None)
    if method != "GET" or data is not None:
        low = str(url).lower()
        if any(x.lower() in low for x in FORBIDDEN) or method == "POST":
            # Allow POST only if it is clearly not generate/customComfy/snapshot.
            if any(x.lower() in low for x in FORBIDDEN) or "orchestration.civitai.com" in low:
                raise RuntimeError(f"FORBIDDEN {method} {url}")
    return _real_urlopen(req, *args, **kwargs)


urllib.request.urlopen = _guard_urlopen

from providers import civitai_workflows as cw  # noqa: E402

SAMPLE = ROOT / "docs/samples/moodyKrea24KHD_v20.json"
FAKE = "zzzx_not_a_civitai_file_9f3aabb.safetensors"


def dump(title, mapped):
    files_ok = [x for x in mapped.get("files") or [] if x.get("status") == "matched"]
    packs = [x for x in mapped.get("nodepacks") or [] if x.get("status") == "matched"]
    print("==", title)
    print("resources", len(mapped.get("resources") or []))
    print("matched files", len(files_ok), "/", len(mapped.get("files") or []))
    for x in files_ok:
        print("  FILE", x.get("filename"), "->", x.get("air"))
    print("unmatchedFiles", mapped.get("unmatchedFiles") or [])
    print("matched packs", len(packs))
    for x in packs:
        print("  PACK", x.get("nodes"), "->", x.get("air"))
    print("unmatchedNodes", mapped.get("unmatchedNodes") or [])
    n_ok = len(files_ok) + sum(len(x.get("nodes") or []) for x in packs)
    n_miss = len(mapped.get("unmatchedFiles") or []) + len(mapped.get("unmatchedNodes") or [])
    print("warning", f"{n_ok} matched / {n_miss} unmatched")


def main():
    wf = json.loads(SAMPLE.read_text())
    mapped = cw.resolve_resources(wf)
    dump("Moody fixture", mapped)

    # Synthetic unmatched filename injected into a copy of the graph.
    wf2 = json.loads(SAMPLE.read_text())
    nodes = wf2.setdefault("nodes", [])
    nodes.append({
        "id": 999001,
        "type": "UNETLoader",
        "widgets_values": [FAKE, "default"],
        "inputs": [],
    })
    mapped2 = cw.resolve_resources(wf2)
    if FAKE not in (mapped2.get("unmatchedFiles") or []):
        print("FAIL synthetic file was not unmatched:", mapped2.get("unmatchedFiles"))
        sys.exit(1)
    print("OK synthetic unmatched stays unmatched:", FAKE)

    core = {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": FAKE}},
        "2": {"class_type": "CLIPTextEncode", "inputs": {"text": "hi"}},
        "3": {"class_type": "KSampler", "inputs": {}},
        "4": {"class_type": "KSamplerAdvanced", "inputs": {}},
        "5": {"class_type": "VAEDecode", "inputs": {}},
        "6": {"class_type": "SaveImage", "inputs": {}},
        "7": {"class_type": "ImageScale", "inputs": {}},
        "8": {"class_type": "LoadImage", "inputs": {}},
        "9": {"class_type": "Reroute", "inputs": {}},
        "10": {"class_type": "EmptyLatentImage", "inputs": {}},
    }
    mapped3 = cw.resolve_resources(core)
    dump("core-only graph", mapped3)
    if mapped3.get("unmatchedNodes"):
        print("FAIL core-only unmatchedNodes", mapped3["unmatchedNodes"])
        sys.exit(1)
    if mapped3.get("nodepacks"):
        print("FAIL core-only should have no nodepacks", mapped3["nodepacks"])
        sys.exit(1)
    if FAKE not in (mapped3.get("unmatchedFiles") or []):
        print("FAIL core-only fake ckpt should stay unmatched")
        sys.exit(1)
    print("OK core-only: no nodepacks, fake file unmatched, no POST generate")
    print("OK no POST generate / customComfy / comfyNodepackSnapshot")


if __name__ == "__main__":
    main()
