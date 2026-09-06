#!/usr/bin/env python3
"""H6: civitai find_service miss must 400, never silent krea2."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from providers.civitai import (  # noqa: E402
    CivitaiProvider,
    DEFAULTS,
    UnknownServiceError,
    build_workflow,
)
from providers import resolve_from_payload  # noqa: E402

fails = []


def check(name, cond, detail=""):
    if cond:
        print(f"  ok   {name}")
    else:
        fails.append(name)
        print(f"  FAIL {name} {detail}")


KREA2 = DEFAULTS["serviceId"]

raised = None
try:
    build_workflow({"serviceId": "image/does-not-exist-xyz", "prompt": "a cat"})
except UnknownServiceError as e:
    raised = e
check("未知 serviceId 抛 UnknownServiceError", isinstance(raised, UnknownServiceError), str(raised))
check("错误码 unknown_service", raised is not None and raised.code == "unknown_service", str(getattr(raised, "code", None)))

prov = CivitaiProvider()
code, data = prov.whatif({"serviceId": "image/does-not-exist-xyz", "prompt": "a cat"})
check("whatif 未知服务 400", code == 400, str((code, data)))
check("whatif 不偷换 krea2", KREA2 not in str(data.get("service")), str(data))
check("whatif 文案点名目录没有", "没有" in str(data.get("error") or ""), str(data.get("error")))

code, data = prov.generate({"serviceId": "image/not-a-real-service", "prompt": "a cat"})
check("generate 未知服务 400", code == 400 and data.get("code") == "unknown_service", str((code, data)))

body = build_workflow({"serviceId": KREA2, "prompt": "a cat"})
check("真 krea2 仍可用", (body.get("_meta") or {}).get("serviceId") == KREA2, str(body.get("_meta")))
inp = body["steps"][0]["input"]
check("payload t2i 不覆盖 native operation", inp.get("operation") in (None, "createImage"), str(inp.get("operation")))

body2 = build_workflow({"serviceId": KREA2, "prompt": "a cat", "operation": "t2i"})
check("canvas op 不写进 civitai input", body2["steps"][0]["input"].get("operation") != "t2i", str(body2["steps"][0]["input"].get("operation")))

check("未知 backend 不再默认 civitai", resolve_from_payload({"backend": "no-such-cloud", "serviceId": "zzz"}) is None)

print("PASS h6-no-krea" if not fails else f"FAIL h6-no-krea {len(fails)}: {fails}")
sys.exit(1 if fails else 0)
