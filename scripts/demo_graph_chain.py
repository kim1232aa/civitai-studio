#!/usr/bin/env python3
"""Shell demo: real-edge multi-node chains for t2i/i2i/i2v (feat/cloud-nodes-poc).

Prints compile summaries for allowed staged chains and still-blocked fakes.
Does not call /api/generate (staged plans must not one-shot fake-run).

UI (static/cloud-nodes.html) loads the same graphs via:
  /cloud-nodes.html?demo=chain   → t2i→i2v (multiStep / execute=staged)
  /cloud-nodes.html?demo=chain3  → t2i→i2i→i2v
  /cloud-nodes.html?demo=i2v     → single-step image→i2v
Or dock buttons 「链式 demo」 / 「单步 demo」.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from providers.graph_compile import compile_graph  # noqa: E402


def brief(name: str, g: dict) -> None:
    r = compile_graph(g)
    print(f"\n=== {name} ===")
    if not r.get("ok"):
        print("BLOCKED:", r.get("error"))
        print("blocked=", r.get("blocked"))
        return
    print("ok execute=", r.get("execute"), "multiStep=", r.get("multiStep"), "sink=", r.get("sink"))
    stages = r.get("stages") or []
    print("stages:", " → ".join(f"{s['id']}({s['op']}" + (f" needs={s.get('needs')}" if s.get("needs") else "") + ")" for s in stages))
    si = (r.get("payload") or {}).get("sourceImage")
    if si is not None:
        print("sink.sourceImage:", json.dumps(si, ensure_ascii=False))
    if r.get("note"):
        print("note:", r["note"])


def main() -> int:
    brief("t2i→i2v", {
        "backend": "nano-gpt",
        "nodes": [
            {"id": "p", "op": "prompt", "params": {"text": "hi"}},
            {"id": "g", "op": "t2i", "params": {"serviceId": "z"}},
            {"id": "v", "op": "i2v", "params": {"serviceId": "vidu-q2-pro"}},
        ],
        "edges": [
            {"from": "p", "fromPort": "prompt", "to": "g", "toPort": "prompt"},
            {"from": "g", "fromPort": "image", "to": "v", "toPort": "image"},
        ],
    })
    brief("t2i→i2i", {
        "backend": "nano-gpt",
        "nodes": [
            {"id": "p", "op": "prompt", "params": {"text": "hi"}},
            {"id": "p2", "op": "prompt", "params": {"text": "refine"}},
            {"id": "g", "op": "t2i", "params": {"serviceId": "z"}},
            {"id": "g2", "op": "i2i", "params": {"serviceId": "z2"}},
        ],
        "edges": [
            {"from": "p", "fromPort": "prompt", "to": "g", "toPort": "prompt"},
            {"from": "p2", "fromPort": "prompt", "to": "g2", "toPort": "prompt"},
            {"from": "g", "fromPort": "image", "to": "g2", "toPort": "image"},
        ],
    })
    brief("i2i→i2v", {
        "backend": "civitai",
        "nodes": [
            {"id": "img", "op": "image", "params": {"url": "https://example.com/frame.png"}},
            {"id": "p", "op": "prompt", "params": {"text": "pan"}},
            {"id": "g", "op": "i2i", "params": {"serviceId": "ckpt"}},
            {"id": "v", "op": "i2v", "params": {"serviceId": "video/x"}},
        ],
        "edges": [
            {"from": "img", "fromPort": "image", "to": "g", "toPort": "image"},
            {"from": "p", "fromPort": "prompt", "to": "g", "toPort": "prompt"},
            {"from": "g", "fromPort": "image", "to": "v", "toPort": "image"},
        ],
    })
    brief("t2i→i2i→i2v", {
        "backend": "nano-gpt",
        "nodes": [
            {"id": "p", "op": "prompt", "params": {"text": "hi"}},
            {"id": "p2", "op": "prompt", "params": {"text": "refine"}},
            {"id": "g", "op": "t2i", "params": {"serviceId": "z"}},
            {"id": "g2", "op": "i2i", "params": {"serviceId": "z2"}},
            {"id": "v", "op": "i2v", "params": {"serviceId": "vidu-q2-pro", "resolution": "1280x720"}},
        ],
        "edges": [
            {"from": "p", "fromPort": "prompt", "to": "g", "toPort": "prompt"},
            {"from": "p2", "fromPort": "prompt", "to": "g2", "toPort": "prompt"},
            {"from": "g", "fromPort": "image", "to": "g2", "toPort": "image"},
            {"from": "g2", "fromPort": "image", "to": "v", "toPort": "image"},
        ],
    })
    brief("BLOCK: parallel sinks no chain edge", {
        "backend": "nano-gpt",
        "nodes": [
            {"id": "p", "op": "prompt", "params": {"text": "hi"}},
            {"id": "g", "op": "t2i", "params": {"serviceId": "z"}},
            {"id": "img", "op": "image", "params": {"url": "https://example.com/frame.png"}},
            {"id": "v", "op": "i2v", "params": {"serviceId": "vid"}},
        ],
        "edges": [
            {"from": "p", "fromPort": "prompt", "to": "g", "toPort": "prompt"},
            {"from": "img", "fromPort": "image", "to": "v", "toPort": "image"},
        ],
    })
    brief("BLOCK: i2v missing image edge (no gallery steal)", {
        "backend": "civitai",
        "nodes": [{"id": "v", "op": "i2v", "params": {"serviceId": "video/x"}}],
        "edges": [],
    })
    brief("BLOCK: HF i2v=none", {
        "backend": "huggingface",
        "nodes": [
            {"id": "img", "op": "image", "params": {"url": "https://example.com/frame.png"}},
            {"id": "v", "op": "i2v", "params": {"serviceId": "x"}},
        ],
        "edges": [{"from": "img", "fromPort": "image", "to": "v", "toPort": "image"}],
    })
    print("\nok: demo_graph_chain")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
