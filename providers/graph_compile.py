"""Cloud-node graph compile (feat/cloud-nodes-poc).

Truth: edges are data deps. compile(graph) only reads ports via edges.
Unconnected required ports → error. Never steal leftover form/global bags.
negative / seed / loras on generators: wire-only (no params bypass).

Real image edges may chain t2i/i2i → i2i/i2v. Intermediate generators become
explicit stages (multi-step plan); pending image is a stage-out ref, never a
fake one-shot single generate that invents gallery/form pixels.
"""
from __future__ import annotations

import re
from collections import defaultdict, deque
from copy import deepcopy
from typing import Any

from .capabilities import get_provider_capabilities

WH_TOKEN = re.compile(r"^\s*(\d{2,5})\s*[x\u00d7*]\s*(\d{2,5})\s*$", re.I)


def split_free_wh(payload: dict) -> None:
    """free_wh 服务只认 width/height，`720x1280` 令牌原样透传会被下游整个丢掉。

    显式 width/height 优先；非 WxH 的值（视频的 `720p` 等令牌）一律不动。
    """
    tok = payload.get("resolution")
    m = WH_TOKEN.match(str(tok or ""))
    if not m:
        return
    if not payload.get("width") and not payload.get("height"):
        payload["width"] = int(m.group(1))
        payload["height"] = int(m.group(2))
    payload.pop("resolution", None)


PORT_TYPES = {
    "prompt": "prompt",
    "image": "image",
    "mask": "mask",
    "seed": "seed",
    "negative": "prompt",
    "loras": "loras",
    "video": "video",
}

OP_SPEC = {
    "prompt": {"ins": [], "outs": ["prompt"], "required": []},
    "negative": {"ins": [], "outs": ["negative"], "required": []},
    "seed": {"ins": [], "outs": ["seed"], "required": []},
    # image source for i2i (url / dataUrl in params)
    "image": {"ins": [], "outs": ["image"], "required": []},
    # mask source for inpaint (brush-drawn or uploaded url / dataUrl in params)
    "mask": {"ins": [], "outs": ["mask"], "required": []},
    "t2i": {"ins": ["prompt", "seed", "negative", "loras"], "outs": ["image"], "required": ["prompt"]},
    "i2i": {"ins": ["prompt", "image", "seed", "negative", "loras"], "outs": ["image"], "required": ["prompt", "image"]},
    # image→video main path; prompt optional; may chain from upstream image out
    "i2v": {"ins": ["prompt", "image", "seed", "negative", "loras"], "outs": ["video"], "required": ["image"]},
    "lora_apply": {"ins": ["image"], "outs": ["loras", "image"], "required": []},
    # image→image, no prompt required (超清/放大)
    "upscale": {"ins": ["prompt", "image"], "outs": ["image"], "required": ["image"]},
    # image→image, direction/temperature params live in node params (打光)
    "relight": {"ins": ["prompt", "image"], "outs": ["image"], "required": ["image"]},
    # image→image, rotation/tilt/zoom params live in node params (多角度)
    "camera-angle": {"ins": ["image"], "outs": ["image"], "required": ["image"]},
    # image→image, real brush mask required (消除笔)。蒙版走 params.maskUrl（单节点方案）,
    # mask 入口仅为兼容旧图的 op:mask 节点保留, 不作必连线口。
    "inpaint": {"ins": ["prompt", "image", "mask"], "outs": ["image"], "required": ["image"]},
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
    if isinstance(v, dict) and v.get("__wire__") == "image":
        return v.get("value"), list(v.get("loras") or [])
    return v, []


def _merge_loras(*bags: Any) -> list:
    out: list = []
    for b in bags:
        if not b:
            continue
        if isinstance(b, dict):
            out.append(deepcopy(b))
        elif isinstance(b, list):
            for x in b:
                if x:
                    out.append(deepcopy(x))
    return out



def _is_pending_image(v: Any) -> bool:
    return isinstance(v, dict) and bool(v.get("__pending__"))


def _stage_image_ref(from_nid: str, loras: list | None = None) -> dict:
    """Image wire value produced by an upstream generator not yet materialized."""
    return {
        "__wire__": "image",
        "__pending__": True,
        "from": from_nid,
        "value": {"__stageOut__": from_nid},
        "loras": list(loras or []),
    }


def _image_payload_value(img: Any) -> Any:
    """Pass through stage-out refs; unwrap plain urls."""
    if isinstance(img, dict) and img.get("__stageOut__"):
        return {"__stageOut__": img["__stageOut__"]}
    return img


def _map_i2v_image_fields(payload: dict, img: Any, backend: str, caps: dict) -> dict:
    """Stamp provider-correct outbound image fields onto Studio payload.

    Unified inbound aliases (sourceImage/firstFrame) stay for provider generate().
    Returns a wiring preview dict for compile UI / tests.
    """
    mode = caps.get("i2v") or "none"
    wiring: dict[str, Any] = {
        "i2v": mode,
        "inbound": {"sourceImage": img, "firstFrame": img},
        "out": {},
    }
    if mode == "sourceImage":
        # Civitai official video frame field
        wiring["out"] = {"sourceImage": img}
    elif mode == "fal_endpoint":
        sid = (payload.get("serviceId") or "").strip()
        fields: list = []
        try:
            from .fal import FIRST_IMAGE_FIELDS, find_model, infer_image_fields

            spec = find_model(sid) or {}
            fields = list(spec.get("imageFields") or infer_image_fields(sid))
        except Exception:
            fields = []
        wiring["imageFields"] = fields
        first = None
        for name in fields:
            if name in FIRST_IMAGE_FIELDS:
                payload[name] = img
                first = name
                break
        if first is None and "image_urls" in fields:
            payload["image_urls"] = [img]
            first = "image_urls"
        wiring["out"] = {first: img} if first else {"firstFrame": img}
    elif mode == "image_url":
        if backend == "nano-gpt":
            if isinstance(img, str) and str(img).startswith("data:"):
                payload["imageDataUrl"] = img
                wiring["out"] = {"imageDataUrl": "(dataUrl)", "mode": "image-to-video"}
            else:
                payload["imageUrl"] = img
                payload["image_url"] = img
                wiring["out"] = {"imageUrl": img, "mode": "image-to-video"}
            payload["mode"] = "image-to-video"
        else:
            # modelscope-ai / modelscope-cn Hub i2v
            payload["image_url"] = img
            wiring["out"] = {"image_url": img}
    elif mode == "first_frame":
        wiring["out"] = {"firstFrame": img}
    return wiring


def compile_graph(graph: dict | None) -> dict:
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

    by_id: dict[str, dict] = {}
    for n in nodes:
        if not isinstance(n, dict) or not n.get("id"):
            return _err("节点缺少 id")
        op = n.get("op")
        if op not in OP_SPEC:
            return _err(f"未知 op: {op}", nodeId=n.get("id"))
        if n["id"] in by_id:
            return _err(f"重复节点 id: {n['id']}")
        by_id[n["id"]] = n

    incoming: dict[str, list] = defaultdict(list)
    outgoing: dict[str, list] = defaultdict(list)
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
        outgoing[fr].append(e)

    order, terr = _topo(nodes, edges)
    if terr:
        return _err(terr, blocked=True)

    values: dict[tuple[str, str], Any] = {}
    candidate_sinks: list[tuple[str, dict]] = []
    sink_wiring: dict[str, dict] = {}
    stages: list[dict] = []

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
                val = params.get("text", params.get("prompt", params.get("negativePrompt")))
                if val in (None, ""):
                    return _err(f"{op} 节点 {nid} 缺少文本", nodeId=nid)
            values[(nid, OP_SPEC[op]["outs"][0])] = val
            continue

        if op == "image":
            url = params.get("url") or params.get("value") or params.get("sourceImage") or params.get("image")
            if not url:
                return _err(f"image 节点 {nid} 缺少 params.url", nodeId=nid, blocked=True)
            values[(nid, "image")] = {"__wire__": "image", "value": url, "loras": []}
            continue

        if op == "mask":
            url = params.get("url") or params.get("value") or params.get("maskUrl") or params.get("mask")
            if not url:
                return _err(f"mask 节点 {nid} 缺少 params.url", nodeId=nid, blocked=True)
            values[(nid, "mask")] = url
            continue

        if op == "lora_apply":
            if "loras" not in params:
                return _err(f"lora_apply {nid} 缺少 params.loras", nodeId=nid)
            if caps.get("lora") == "none":
                return _err(f"后端 {backend} 不支持 LoRA", blocked=True)
            loras = deepcopy(params["loras"])
            values[(nid, "loras")] = loras
            if "image" in inputs:
                img, prior = _unwrap_image(inputs["image"])
                wire = {
                    "__wire__": "image",
                    "value": img,
                    "loras": _merge_loras(prior, loras),
                }
                if _is_pending_image(inputs["image"]):
                    wire["__pending__"] = True
                    wire["from"] = inputs["image"].get("from")
                values[(nid, "image")] = wire
            # Must feed a sink — silent orphan is P1→block
            outs_used = {e["fromPort"] for e in outgoing.get(nid, [])}
            if not outs_used.intersection({"loras", "image"}):
                return _err(
                    f"lora_apply {nid} 未连到汇点（loras/image），禁止静默无效",
                    blocked=True,
                    nodeId=nid,
                )
            continue

        if op in ("t2i", "i2i"):
            payload = {
                "backend": backend,
                "serviceId": params.get("serviceId") or g.get("serviceId"),
                "prompt": inputs.get("prompt"),
            }
            if not payload["serviceId"]:
                return _err(f"节点 {nid} 缺少 serviceId", nodeId=nid)

            # wire-only for seed / negative / loras on generator
            if "seed" in inputs:
                payload["seed"] = inputs["seed"]
            if "negative" in inputs:
                payload["negativePrompt"] = inputs["negative"]
            # reject params bypass if present without wire (honest error)
            if "seed" in params and "seed" not in inputs:
                return _err(
                    f"节点 {nid} 的 seed 只认连线，请用 seed 节点接入；禁止 params.seed 旁路",
                    blocked=True,
                    nodeId=nid,
                )
            if ("negativePrompt" in params or "negative" in params) and "negative" not in inputs:
                return _err(
                    f"节点 {nid} 的负面词只认连线，请用 negative 节点接入",
                    blocked=True,
                    nodeId=nid,
                )
            if "loras" in params and "loras" not in inputs:
                # also allow image-bundled loras without separate loras port
                pass  # checked after unwrap

            bundled_loras: list = []
            needs: list[str] = []
            if op == "i2i":
                img, bundled_loras = _unwrap_image(inputs["image"])
                if _is_pending_image(inputs["image"]):
                    # Real edge from upstream generator → stage-out ref (multi-step plan)
                    up = inputs["image"].get("from")
                    if up:
                        needs.append(up)
                    img = _image_payload_value(img)
                if not img:
                    return _err(f"i2i {nid} 的 image 口无有效图", blocked=True, nodeId=nid)
                payload["sourceImage"] = img

            for k in ("resolution", "width", "height", "steps", "cfgScale", "quantity"):
                if k in params:
                    payload[k] = deepcopy(params[k])

            wired_loras = inputs.get("loras")
            merged = _merge_loras(bundled_loras, wired_loras)
            if "loras" in params and "loras" not in inputs and not bundled_loras:
                return _err(
                    f"节点 {nid} 的 LoRA 只认连线（lora_apply→loras 或 image 打包），禁止 params.loras 旁路",
                    blocked=True,
                    nodeId=nid,
                )
            if merged:
                payload["loras"] = merged

            if caps.get("resolution") == "catalog_token":
                payload.pop("width", None)
                payload.pop("height", None)
            elif caps.get("resolution") == "free_wh":
                split_free_wh(payload)
            if caps.get("lora") == "none":
                payload.pop("loras", None)
            if caps.get("promptMax") and isinstance(payload.get("prompt"), str):
                mx = int(caps["promptMax"])
                if len(payload["prompt"]) > mx:
                    return _err(f"提示词超过 promptMax={mx}", blocked=True, nodeId=nid)

            # Propagate pending image wire so downstream i2i/i2v can chain via real edges
            values[(nid, "image")] = _stage_image_ref(nid, merged if merged else [])
            image_wired_on = any(e.get("fromPort") == "image" for e in outgoing.get(nid, []))
            stage = {"id": nid, "op": op, "payload": deepcopy(payload), "produces": "image"}
            if needs:
                stage["needs"] = needs
            stages.append(stage)
            if image_wired_on:
                # Intermediate in a real-edge chain — not a terminal sink
                continue
            candidate_sinks.append((nid, payload))
            continue

        if op == "upscale":
            if not caps.get("upscale"):
                return _err(f"后端 {backend} 不支持图片超清", blocked=True, nodeId=nid)
            payload = {
                "backend": backend,
                "serviceId": params.get("serviceId") or g.get("serviceId"),
            }
            if not payload["serviceId"]:
                return _err(f"节点 {nid} 缺少 serviceId", nodeId=nid)
            img, _ = _unwrap_image(inputs["image"])
            needs: list[str] = []
            if _is_pending_image(inputs["image"]):
                up = inputs["image"].get("from")
                if up:
                    needs.append(up)
                img = _image_payload_value(img)
            if not img:
                return _err(f"upscale {nid} 的 image 口无有效图", blocked=True, nodeId=nid)
            payload["sourceImage"] = img
            if inputs.get("prompt"):
                payload["prompt"] = inputs["prompt"]
            for k in ("scale", "resolution", "width", "height"):
                if k in params:
                    payload[k] = deepcopy(params[k])

            values[(nid, "image")] = _stage_image_ref(nid, [])
            image_wired_on = any(e.get("fromPort") == "image" for e in outgoing.get(nid, []))
            stage = {"id": nid, "op": op, "payload": deepcopy(payload), "produces": "image"}
            if needs:
                stage["needs"] = needs
            stages.append(stage)
            if image_wired_on:
                continue
            candidate_sinks.append((nid, payload))
            continue

        if op in ("relight", "camera-angle", "inpaint"):
            cap_key = {"relight": "relight", "camera-angle": "cameraAngle", "inpaint": "inpaint"}[op]
            label = {"relight": "打光", "camera-angle": "多角度", "inpaint": "消除笔"}[op]
            if not caps.get(cap_key):
                return _err(f"后端 {backend} 不支持{label}", blocked=True, nodeId=nid)
            payload = {
                "backend": backend,
                "serviceId": params.get("serviceId") or g.get("serviceId"),
            }
            if not payload["serviceId"]:
                return _err(f"节点 {nid} 缺少 serviceId", nodeId=nid)
            img, _ = _unwrap_image(inputs["image"])
            needs: list[str] = []
            if _is_pending_image(inputs["image"]):
                up = inputs["image"].get("from")
                if up:
                    needs.append(up)
                img = _image_payload_value(img)
            if not img:
                return _err(f"{op} {nid} 的 image 口无有效图", blocked=True, nodeId=nid)
            payload["sourceImage"] = img
            if inputs.get("prompt"):
                payload["prompt"] = inputs["prompt"]
            if op == "inpaint":
                # 单节点契约: 前端把画笔蒙版写进 params.maskUrl (已上传则是 URL,
                # 未上传则是 dataURL)。inputs["mask"] 只是旧 op:mask 图的回退。
                mask = params.get("maskUrl") or inputs.get("mask")
                if isinstance(mask, dict):
                    mask = mask.get("url") or mask.get("value")
                if not isinstance(mask, str) or not mask.strip():
                    return _err(
                        f"inpaint {nid} 缺少蒙版: params.maskUrl 为空",
                        blocked=True,
                        nodeId=nid,
                    )
                payload["maskUrl"] = mask.strip()
            if op == "relight":
                # 打光面板的每个控件都要落到 payload。fal iclight 只吃
                # image_url/prompt/initial_latent, 其余在 build_fal_input 里显式
                # 降级进 prompt —— 收都不收才是静默丢弃。
                for k in (
                    "lightDirection",
                    "lightColor",
                    "colorTemperature",
                    "brightness",
                    "initialLatent",
                    "lightQuality",
                    "rimLight",
                    "lightPreset",
                    "perspective",
                ):
                    if k in params:
                        payload[k] = deepcopy(params[k])
            if op == "camera-angle":
                for k in ("horizontalAngle", "verticalAngle", "zoom"):
                    if k in params:
                        payload[k] = deepcopy(params[k])

            values[(nid, "image")] = _stage_image_ref(nid, [])
            image_wired_on = any(e.get("fromPort") == "image" for e in outgoing.get(nid, []))
            stage = {"id": nid, "op": op, "payload": deepcopy(payload), "produces": "image"}
            if needs:
                stage["needs"] = needs
            stages.append(stage)
            if image_wired_on:
                continue
            candidate_sinks.append((nid, payload))
            continue

        if op == "i2v":
            if caps.get("i2v") in (None, "none"):
                return _err(
                    f"后端 {backend} 不支持图生视频（i2v）",
                    blocked=True,
                    nodeId=nid,
                )
            raw_img = inputs.get("image")
            img, bundled_loras = _unwrap_image(raw_img)
            needs: list[str] = []
            if _is_pending_image(raw_img):
                # Real edge from upstream t2i/i2i → multi-step stage ref (not gallery steal)
                up = raw_img.get("from") if isinstance(raw_img, dict) else None
                if up:
                    needs.append(up)
                img = _image_payload_value(img)
            if not img:
                return _err(f"i2v {nid} 的 image 口无有效图，禁止偷成片栏", blocked=True, nodeId=nid)

            payload = {
                "backend": backend,
                "serviceId": params.get("serviceId") or g.get("serviceId"),
                "kind": "video",
                "recipe": "video",
                "sourceImage": img,
                "firstFrame": img,
            }
            if not payload["serviceId"]:
                return _err(f"节点 {nid} 缺少 serviceId", nodeId=nid)
            wiring = _map_i2v_image_fields(payload, img, backend, caps)
            if needs:
                wiring["stageNeeds"] = list(needs)
                wiring["pendingImage"] = True
            if "prompt" in inputs:
                payload["prompt"] = inputs["prompt"]
            elif params.get("prompt") or params.get("text"):
                return _err(
                    f"节点 {nid} 的 prompt 只认连线，请用 prompt 节点接入",
                    blocked=True,
                    nodeId=nid,
                )
            if "seed" in inputs:
                payload["seed"] = inputs["seed"]
            if "seed" in params and "seed" not in inputs:
                return _err(
                    f"节点 {nid} 的 seed 只认连线，请用 seed 节点接入；禁止 params.seed 旁路",
                    blocked=True,
                    nodeId=nid,
                )
            if "negative" in inputs:
                payload["negativePrompt"] = inputs["negative"]
            if ("negativePrompt" in params or "negative" in params) and "negative" not in inputs:
                return _err(
                    f"节点 {nid} 的负面词只认连线，请用 negative 节点接入",
                    blocked=True,
                    nodeId=nid,
                )
            for k in ("resolution", "duration", "aspectRatio", "width", "height"):
                if k in params:
                    payload[k] = deepcopy(params[k])
            wired_loras = inputs.get("loras")
            merged = _merge_loras(bundled_loras, wired_loras)
            if "loras" in params and "loras" not in inputs and not bundled_loras:
                return _err(
                    f"节点 {nid} 的 LoRA 只认连线，禁止 params.loras 旁路",
                    blocked=True,
                    nodeId=nid,
                )
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
            values[(nid, "video")] = {"__pending__": True, "from": nid, "media": "video"}
            video_wired_on = any(e.get("fromPort") == "video" for e in outgoing.get(nid, []))
            if video_wired_on:
                return _err(
                    f"POC 暂不支持把 i2v {nid} 的 video 再接到下游；请只留一个视频汇点",
                    blocked=True,
                    nodeId=nid,
                )
            stage = {"id": nid, "op": "i2v", "payload": deepcopy(payload), "produces": "video"}
            if needs:
                stage["needs"] = needs
            stages.append(stage)
            sink_wiring[nid] = wiring
            candidate_sinks.append((nid, payload))
            continue

        return _err(f"未实现 op: {op}", nodeId=nid)

    if not candidate_sinks:
        return _err("图中没有可生成的 t2i/i2i/i2v 汇点")
    if len(candidate_sinks) > 1:
        ids = [s[0] for s in candidate_sinks]
        return _err(
            f"只允许一个终端生成汇点（并行未连汇点禁止），当前 {len(candidate_sinks)} 个: {', '.join(ids)}",
            blocked=True,
            sinks=ids,
        )

    sink_id, payload = candidate_sinks[0]
    multi = len(stages) > 1
    out = {
        "ok": True,
        "payload": payload,
        "sink": sink_id,
        "backend": backend,
        "capabilities": caps,
        "stages": stages,
        "multiStep": multi,
    }
    if sink_id in sink_wiring:
        out["wiring"] = sink_wiring[sink_id]
    if multi:
        # Honest: one generate call must not pretend to run the whole chain
        out["execute"] = "staged"
        out["note"] = "多步链已按真边编译为 stages；请按序物化上游成片后再跑下游（禁止一次假跑通）"
    else:
        out["execute"] = "single"
    return out


def payload_has_stage_out(obj: Any) -> bool:
    """True if obj (nested dict/list) still carries unresolved __stageOut__ refs."""
    if isinstance(obj, dict):
        if "__stageOut__" in obj:
            return True
        return any(payload_has_stage_out(v) for v in obj.values())
    if isinstance(obj, list):
        return any(payload_has_stage_out(v) for v in obj)
    return False


def reject_staged_generate(payload: Any) -> dict | None:
    """Hard-block one-shot /api/generate for staged plans or unresolved stage-outs.

    Returns an error dict for the HTTP handler, or None if the payload may proceed.
    Accepts either a sink payload or a full compile result body.
    """
    if not isinstance(payload, dict):
        return None
    if payload.get("execute") == "staged" or payload.get("multiStep") is True:
        return {
            "error": "多步链（execute=staged / multiStep）禁止一次提交假跑通；请按 stages 顺序物化上游后再生成下游（step runner 尚未接入）",
            "blocked": True,
            "execute": "staged",
            "multiStep": True,
        }
    if payload_has_stage_out(payload):
        return {
            "error": "payload 含未物化的 __stageOut__ 占位，禁止假跑通；请先跑上游 stage（step runner 尚未接入）",
            "blocked": True,
            "stageOut": True,
        }
    return None
