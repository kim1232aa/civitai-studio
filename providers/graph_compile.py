"""Linear cloud-node graph compile (feat/cloud-nodes-poc).

Truth: edges are data deps. compile(graph) only reads ports via edges.
Unconnected required ports → error. Never steal leftover form/global bags.
Form mode can call compile_form → same outbound shape later; this module is graph-only.
"""
from __future__ import annotations

from collections import defaultdict, deque
from copy import deepcopy
from typing import Any

from .capabilities import get_provider_capabilities

# Port types for linear POC
PORT_TYPES = {"prompt": "prompt", "image": "image", "seed": "seed", "negative": "prompt", "loras": "loras"}

# op → required input ports / output ports
OP_SPEC = {
    "prompt": {"ins": [], "outs": ["prompt"], "required": []},
    "negative": {"ins": [], "outs": ["negative"], "required": []},
    "seed": {"ins": [], "outs": ["seed"], "required": []},
    "t2i": {"ins": ["prompt", "seed", "negative", "loras"], "outs": ["image"], "required": ["prompt"]},
    "i2i": {"ins": ["prompt", "image", "seed", "negative", "loras"], "outs": ["image"], "required": ["prompt", "image"]},
    # lora_apply emits a loras bag for t2i/i2i; may also pass image through for i2i chains
    "lora_apply": {"ins": ["image"], "outs": ["loras", "image"], "required": []},
}


def _err(msg: str, **extra) -> dict:
    out = {"ok": False, "error": msg, "code": "graph_compile"}
    out.update(extra)
    return out


def _topo(nodes: list[dict], edges: list[dict]) -> tuple[list[str] | None, str | None]:
    ids = {n["id"] for n in nodes if n.get("id")}
    indeg = {i: 0 for i in ids}
    adj = defaultdict(list)
    for e in edges:
        a, b = e.get("from"), e.get("to")
        if a not in ids or b not in ids:
            return None, f"边端点不存在: {a}→{b}"
        adj[a].append(b)
        indeg[b] += 1
    q = deque([i for i, d in indeg.items() if d == 0])
    order = []
    while q:
        u = q.popleft()
        order.append(u)
        for v in adj[u]:
            indeg[v] -= 1
            if indeg[v] == 0:
                q.append(v)
    if len(order) != len(ids):
        return None, "图有环或未连通组件无法拓扑排序"
    return order, None


def _unwrap_image(v: Any) -> tuple[Any, list]:
    """Image wire may carry bundled loras from lora_apply pass-through."""
    if isinstance(v, dict) and v.get("__wire__") == "image":
        return v.get("value"), list(v.get("loras") or [])
    return v, []


def _merge_loras(*bags: Any) -> list:
    out: list = []
    for b in bags:
        if not b:
            continue
        if isinstance(b, list):
            out.extend(deepcopy(b))
        else:
            out.append(deepcopy(b))
    return out


def compile_graph(graph: dict | None) -> dict:
    """Compile a linear-capable cloud graph into one generate payload (single sink).

    Returns {ok, payload?, steps?, error?, blocked?}.
    Never mutates the caller's graph dict.
    """
    g = graph or {}
    backend = (g.get("backend") or "").strip()
    if not backend:
        return _err("缺少 backend")
    caps = get_provider_capabilities(backend)
    nodes = g.get("nodes") or []
    edges = g.get("edges") or []
    if not isinstance(nodes, list) or not nodes:
        return _err("nodes 为空")
    if not isinstance(edges, list):
        return _err("edges 必须是数组")

    by_id = {}
    for n in nodes:
        if not isinstance(n, dict) or not n.get("id"):
            return _err("节点缺少 id")
        op = n.get("op")
        if op not in OP_SPEC:
            return _err(f"未知 op: {op}", nodeId=n.get("id"))
        if n["id"] in by_id:
            return _err(f"重复节点 id: {n['id']}")
        by_id[n["id"]] = n

    incoming = defaultdict(list)
    for e in edges:
        if not isinstance(e, dict):
            return _err("边格式错误")
        fr, to = e.get("from"), e.get("to")
        fp, tp = e.get("fromPort"), e.get("toPort")
        if not fr or not to or not fp or not tp:
            return _err("边缺少 from/to/fromPort/toPort")
        if fr not in by_id or to not in by_id:
            return _err(f"边端点不存在: {fr}→{to}")
        src_op = by_id[fr].get("op")
        dst_op = by_id[to].get("op")
        if fp not in OP_SPEC[src_op]["outs"]:
            return _err(f"节点 {fr}({src_op}) 无输出口 {fp}", blocked=True)
        if tp not in OP_SPEC[dst_op]["ins"]:
            return _err(f"节点 {to}({dst_op}) 无输入口 {tp}", blocked=True)
        if PORT_TYPES.get(fp) != PORT_TYPES.get(tp):
            return _err(f"类型不兼容: {fr}.{fp} → {to}.{tp}", blocked=True)
        incoming[to].append(e)

    order, terr = _topo(nodes, edges)
    if terr:
        return _err(terr, blocked=True)

    values: dict[tuple[str, str], Any] = {}
    sinks: list[tuple[str, dict]] = []  # (nodeId, payload) — exactly one allowed

    for nid in order:
        n = by_id[nid]
        op = n["op"]
        params = n.get("params") if isinstance(n.get("params"), dict) else {}
        inputs: dict[str, Any] = {}
        seen_ports: set[str] = set()
        for e in incoming.get(nid, []):
            tp = e["toPort"]
            if tp in seen_ports:
                return _err(f"节点 {nid} 输入口 {tp} 多条入边", blocked=True)
            seen_ports.add(tp)
            key = (e["from"], e["fromPort"])
            if key not in values:
                return _err(f"上游 {e['from']}.{e['fromPort']} 无值", blocked=True)
            inputs[tp] = values[key]

        for req in OP_SPEC[op]["required"]:
            if req not in inputs:
                return _err(
                    f"节点 {nid}({op}) 未连线输入口 `{req}`，禁止偷用左侧残留",
                    blocked=True,
                    nodeId=nid,
                    port=req,
                )

        if op in ("prompt", "negative", "seed"):
            if op == "seed":
                if "value" not in params and "seed" not in params:
                    return _err(f"seed 节点 {nid} 缺少 params.value", nodeId=nid)
                val = params.get("value", params.get("seed"))
            else:
                val = params.get("text", params.get("prompt"))
                if val in (None, ""):
                    return _err(f"{op} 节点 {nid} 缺少文本", nodeId=nid)
            out_port = OP_SPEC[op]["outs"][0]
            values[(nid, out_port)] = val
            continue

        if op == "lora_apply":
            if "loras" not in params:
                return _err(f"lora_apply {nid} 缺少 params.loras", nodeId=nid)
            if caps.get("lora") == "none":
                return _err(f"后端 {backend} 不支持 LoRA", blocked=True)
            loras = deepcopy(params["loras"])
            values[(nid, "loras")] = loras
            # Optional image pass-through: bundle loras so a lone image→i2i edge still carries them
            if "image" in inputs:
                img, prior = _unwrap_image(inputs["image"])
                values[(nid, "image")] = {
                    "__wire__": "image",
                    "value": img,
                    "loras": _merge_loras(prior, loras),
                }
            continue

        if op in ("t2i", "i2i"):
            payload = {
                "backend": backend,
                "serviceId": params.get("serviceId") or g.get("serviceId"),
                "prompt": inputs.get("prompt"),
            }
            if not payload["serviceId"]:
                return _err(f"节点 {nid} 缺少 serviceId", nodeId=nid)

            # seed: ONLY from wired seed port — no params.seed bypass on generator
            if "seed" in inputs:
                payload["seed"] = inputs["seed"]

            if "negative" in inputs:
                payload["negativePrompt"] = inputs["negative"]
            elif "negativePrompt" in params:
                payload["negativePrompt"] = params["negativePrompt"]

            bundled_loras: list = []
            if op == "i2i":
                img, bundled_loras = _unwrap_image(inputs["image"])
                payload["sourceImage"] = img

            for k in ("resolution", "width", "height", "steps", "cfgScale", "quantity"):
                if k in params:
                    payload[k] = deepcopy(params[k])

            # loras: wired loras port + image-bundled + node-local params (merged, not dropped)
            wired_loras = inputs.get("loras")
            param_loras = params.get("loras")
            merged = _merge_loras(bundled_loras, wired_loras, param_loras)
            if merged:
                payload["loras"] = merged

            if caps.get("resolution") == "catalog_token":
                payload.pop("width", None)
                payload.pop("height", None)
            if caps.get("lora") == "none":
                payload.pop("loras", None)
            if caps.get("promptMax") and isinstance(payload.get("prompt"), str):
                mx = int(caps["promptMax"])
                if len(payload["prompt"]) > mx:
                    return _err(f"提示词超过 promptMax={mx}", blocked=True, nodeId=nid)

            values[(nid, "image")] = {"__pending__": True, "from": nid}
            sinks.append((nid, payload))
            continue

        return _err(f"未实现 op: {op}", nodeId=nid)

    if not sinks:
        return _err("图中没有可生成的 t2i/i2i 汇点")
    if len(sinks) > 1:
        ids = [s[0] for s in sinks]
        return _err(
            f"线性 POC 只允许一个生成汇点，当前 {len(sinks)} 个: {', '.join(ids)}",
            blocked=True,
            sinks=ids,
        )

    sink_id, payload = sinks[0]
    return {
        "ok": True,
        "payload": payload,
        "sink": sink_id,
        "backend": backend,
        "capabilities": caps,
    }
