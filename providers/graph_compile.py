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
PORT_TYPES = {"prompt": "prompt", "image": "image", "seed": "seed", "negative": "prompt"}

# op → required input ports / output ports
OP_SPEC = {
    "prompt": {"ins": [], "outs": ["prompt"], "required": []},
    "negative": {"ins": [], "outs": ["negative"], "required": []},
    "seed": {"ins": [], "outs": ["seed"], "required": []},
    "t2i": {"ins": ["prompt", "seed", "negative"], "outs": ["image"], "required": ["prompt"]},  # seed/negative optional
    "i2i": {"ins": ["prompt", "image", "seed", "negative"], "outs": ["image"], "required": ["prompt", "image"]},
    "lora_apply": {"ins": ["image"], "outs": ["image"], "required": ["image"]},  # params hold loras; linear stub
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


def compile_graph(graph: dict | None) -> dict:
    """Compile a linear-capable cloud graph into one generate payload (single sink t2i/i2i for POC).

    Returns {ok, payload?, steps?, error?, blocked?}.
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

    # Validate edge port types roughly
    incoming = defaultdict(list)  # to_id -> list of edges
    outgoing = defaultdict(list)
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
        # type match: port name family
        if PORT_TYPES.get(fp) != PORT_TYPES.get(tp):
            return _err(f"类型不兼容: {fr}.{fp} → {to}.{tp}", blocked=True)
        incoming[to].append(e)
        outgoing[fr].append(e)

    order, terr = _topo(nodes, edges)
    if terr:
        return _err(terr, blocked=True)

    # Produce values only along edges / node params for source nodes
    values = {}  # (nodeId, port) -> value

    for nid in order:
        n = by_id[nid]
        op = n["op"]
        params = n.get("params") if isinstance(n.get("params"), dict) else {}
        # Collect inputs strictly from edges
        inputs = {}
        seen_ports = set()
        for e in incoming.get(nid, []):
            tp = e["toPort"]
            if tp in seen_ports:
                return _err(f"节点 {nid} 输入口 {tp} 多条入边", blocked=True)
            seen_ports.add(tp)
            key = (e["from"], e["fromPort"])
            if key not in values:
                return _err(f"上游 {e['from']}.{e['fromPort']} 无值", blocked=True)
            inputs[tp] = values[key]

        # Required ports must be wired — NEVER fall back to form leftovers
        for req in OP_SPEC[op]["required"]:
            if req not in inputs:
                return _err(f"节点 {nid}({op}) 未连线输入口 `{req}`，禁止偷用左侧残留", blocked=True, nodeId=nid, port=req)

        if op in ("prompt", "negative", "seed"):
            # source: value from params only
            field = "text" if op != "seed" else "value"
            if field not in params and op != "seed":
                # allow params.prompt for prompt node
                field = "prompt" if "prompt" in params else field
            if op == "seed":
                if "value" not in params and "seed" not in params:
                    return _err(f"seed 节点 {nid} 缺少 params.value", nodeId=nid)
                val = params.get("value", params.get("seed"))
            else:
                val = params.get(field, params.get("text", params.get("prompt")))
                if val in (None, ""):
                    return _err(f"{op} 节点 {nid} 缺少文本", nodeId=nid)
            out_port = OP_SPEC[op]["outs"][0]
            values[(nid, out_port)] = val
            continue

        if op in ("t2i", "i2i"):
            # Build generate payload — only wired + explicit node params (serviceId, loras, resolution…)
            # Do NOT merge an external form bag.
            payload = {
                "backend": backend,
                "serviceId": params.get("serviceId") or g.get("serviceId"),
                "prompt": inputs.get("prompt"),
            }
            if not payload["serviceId"]:
                return _err(f"节点 {nid} 缺少 serviceId", nodeId=nid)
            if "seed" in inputs:
                payload["seed"] = inputs["seed"]
            elif "seed" in params:
                # seed only from THIS node params if not wired — still node-local, not left panel
                payload["seed"] = params["seed"]
            if "negative" in inputs:
                payload["negativePrompt"] = inputs["negative"]
            elif "negativePrompt" in params:
                payload["negativePrompt"] = params["negativePrompt"]
            if op == "i2i":
                payload["sourceImage"] = inputs["image"]
            # optional node-local params allowed by capabilities
            for k in ("loras", "resolution", "width", "height", "steps", "cfgScale", "quantity"):
                if k in params:
                    payload[k] = deepcopy(params[k])
            # Strip by capabilities (Nano no WxH)
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
            # POC: single sink — return this payload (last t2i/i2i in topo wins if multiple)
            g["_last_payload"] = payload
            g["_last_sink"] = nid
            continue

        if op == "lora_apply":
            # Linear stub: must have image edge; loras on params; still no form steal
            if "loras" not in params:
                return _err(f"lora_apply {nid} 缺少 params.loras", nodeId=nid)
            if caps.get("lora") == "none":
                return _err(f"后端 {backend} 不支持 LoRA", blocked=True)
            values[(nid, "image")] = inputs["image"]
            continue

        return _err(f"未实现 op: {op}", nodeId=nid)

    payload = g.get("_last_payload")
    if not payload:
        return _err("图中没有可生成的 t2i/i2i 汇点")
    return {
        "ok": True,
        "payload": payload,
        "sink": g.get("_last_sink"),
        "backend": backend,
        "capabilities": caps,
    }
