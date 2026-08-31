#!/usr/bin/env python3
import json
from pathlib import Path
data=json.loads(Path("/workspace/civitai-studio/docs/capabilities.json").read_text())
caps=data["capabilities"]
print("n", len(caps), "keys0", sorted(caps[0].keys()))
want = []
for c in caps:
    eng=str(c.get("engine") or "")
    op=str(c.get("operation") or "")
    key=f"{eng}|{op}|{c.get('version')}|{c.get('provider')}"
    if any(x in key.lower() for x in ("wan|image-to-video","ltx2.5|first","ltx2.3|first","hunyuan","happyhorse|imagetovideo","minimax-h3-comfy","flux2|create","sdcpp|create","seedream","qwen|create","editimage","sourceimage")):
        want.append(c)
# print unique interesting
seen=set()
for c in caps:
    ident=(c.get("engine"), c.get("operation"), c.get("version"), c.get("provider"))
    if ident in seen: continue
    frames=c.get("frameFields")
    req=c.get("required")
    if c.get("engine") in ("wan","ltx2.5","ltx2.3","hunyuan","happyHorse","minimax-h3-comfy","kling","sora","seedance","veo3","vidu") or (c.get("operation") in ("editImage","createVariant","image-to-video","firstLastFrameToVideo","imageToVideo","text-to-video","referenceToVideo","reference-to-video")):
        seen.add(ident)
        print(f"{c.get('engine'):18} {str(c.get('operation')):24} v={c.get('version')} p={c.get('provider')} req={req} frames={frames}")
