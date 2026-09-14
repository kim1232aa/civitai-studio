#!/usr/bin/env python3
"""ASTRA 3-bug gates: mixed LoRA, unknown ref cap, model-switch LoRA residual.

Run: python3 scripts/test_astra3_gates.py
Offline. Executes the real pack/gate helpers in node.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from providers.graph_compile import compile_graph  # noqa: E402
from providers.ref_images import declared_max_refs, enforce_ref_cap, max_refs  # noqa: E402
from providers.capabilities import get_provider_capabilities as gc  # noqa: E402

JS = (ROOT / "static" / "storyboard.js").read_text(encoding="utf-8")
HTML = (ROOT / "static" / "storyboard.html").read_text(encoding="utf-8")
COMPILE = (ROOT / "providers" / "graph_compile.py").read_text(encoding="utf-8")


def ok(cond, msg):
    if not cond:
        raise AssertionError(msg)
    print("ok  -", msg)


def source_contracts():
    ok("function packLoraRow" in JS, "packLoraRow")
    ok("function loraRowCanOutbound" in JS, "loraRowCanOutbound")
    ok("function catalogItemSupportsLora" in JS, "catalogItemSupportsLora")
    ok("function revalidateLorasForService" in JS, "revalidateLorasForService")
    ok("function declaredRefCap" in JS, "declaredRefCap")
    ok("urls.slice(0, cap)" not in JS, "attachExtraImages does not slice")
    ok("payload.images = urls" in JS, "attach packs full url list")
    ok("上限未知" in JS, "unknown ref-cap copy")
    ok("不能只带走其余条" in JS, "mixed LoRA copy")
    ok("当前模型不支持 LoRA" in JS, "unsupported model copy")
    ok("packed.length !== list.length" in JS, "chipsLack compares packed vs list")
    ok("modelId: modelId" in JS or "modelId: l.modelId" in JS, "pack keeps modelId")
    ok("function loraModelId" in JS, "loraModelId parses air")
    ok('payload.pop("loras", None)' not in COMPILE, "compile does not silent-pop loras")
    ok("已选 LoRA 不能静默丢掉" in COMPILE, "compile refuses residual LoRA")
    ok(re.search(r'storyboard\.js\?v=[\w-]+', HTML) is not None, "cache stamp (versioned bust present)")
    ok("revalidateLorasForService()" in JS, "syncParamChrome revalidates")


def node_pack_cases():
    start = JS.find("  function packLoraRow(")
    end = JS.find("  async function searchLoras(")
    helpers_start = JS.find("  function clampLoraScale(")
    helpers_end = JS.find("  function loraTypeUsable(")
    ok(start >= 0 and end > start and helpers_start >= 0, "extract LoRA helpers")
    chunk = JS[helpers_start:helpers_end] + JS[start:end]
    harness = r"""
const state = { loras: [] };
let BE = "civitai";
globalThis.ITEM = null;
function currentBackend() { return BE; }
function catalogItemForService() { return globalThis.ITEM; }
function catalogItemSupportsLora() {
  const it = globalThis.ITEM;
  if (it && it.supportsLora === false) return false;
  if (it && it.supportsLora === true) return true;
  return true;
}
function isModelscopeBe() { return BE === "modelscope-ai" || BE === "modelscope-cn"; }
function isNanogptBe() { return BE === "nano-gpt"; }
function isHttpUrl(s) { return /^https?:\/\//i.test(String(s || "")); }
function isHfRepo(s) { return /^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/.test(String(s || "").trim()); }
function looksAir(s) {
  const t = String(s || "");
  return t.toLowerCase().startsWith("urn:air:") || t.toLowerCase().indexOf(":lora:") >= 0;
}
function loraVersionId(l) {
  if (!l) return "";
  if (l.versionId) return String(l.versionId);
  const air = String(l.air || "");
  const m = air.match(/@(\d+)\s*$/) || air.match(/civitai:\d+@(\d+)/i);
  return m ? m[1] : "";
}
function loraModelId(l) {
  if (!l) return "";
  if (l.modelId != null && String(l.modelId).trim()) return String(l.modelId).trim();
  const air = String(l.air || "");
  const m = air.match(/civitai:(\d+)@/i) || air.match(/civitai:(\d+)\s*$/i);
  return m ? m[1] : "";
}
function $(id) { return null; }
function persist() {}
function renderLoras() {}
function setLoraNote() {}
function falLoraUnsupportedMsg() { return ""; }
""" + chunk + r"""
function run(be, rows, item, supportsOverride) {
  BE = be;
  globalThis.ITEM = item || null;
  if (supportsOverride === false) {
    globalThis.ITEM = Object.assign({}, item || {}, { supportsLora: false });
  }
  state.loras = rows;
  const packed = packLorasForPayload();
  return {
    packed: packed,
    lack: chipsLackAirForOutbound(),
    msg: outboundLoraBlockMsg(),
    supports: catalogItemSupportsLora(),
    fields: packed && packed[0] ? Object.keys(packed[0]).sort() : [],
  };
}
const AIR = { air: "urn:air:krea2:lora:civitai:2323765@3071582", modelId: "2323765", versionId: "3071582", strength: 0.8, name: "A" };
const AIR_PARSE = { air: "urn:air:krea2:lora:civitai:2323765@3071582", strength: 0.8, name: "parse" };
const AIR_NO_STRENGTH = { air: "urn:air:krea2:lora:civitai:2323765@3071582", modelId: "2323765", versionId: "3071582", strength: null, name: "nullStr" };
const AIR_ONLY = { air: "urn:air:sdxl:lora:civitai:1", strength: 0.8, name: "AIR" };
const PATH = { path: "https://civitai.com/api/download/models/1", strength: 0.8, name: "B" };
const HUB = { path: "owner/repo", strength: 0.8, name: "C" };
const out = {
  civitaiOk: run("civitai", [AIR]),
  civitaiFromAir: run("civitai", [AIR_PARSE]),
  civitaiNoStrength: run("civitai", [AIR_NO_STRENGTH]),
  civitaiMixedStrength: run("civitai", [AIR, AIR_NO_STRENGTH]),
  civitaiBad: run("civitai", [PATH]),
  civitaiMixed: run("civitai", [AIR, PATH]),
  falOk: run("fal", [PATH], { id: "fal-ai/krea-2/turbo/lora", supportsLora: true }),
  falMixed: run("fal", [AIR_ONLY, PATH], { id: "fal-ai/krea-2/turbo/lora", supportsLora: true }),
  msMixed: run("modelscope-ai", [PATH, HUB], { id: "krea/Krea-2-Turbo" }),
  unsupported: run("fal", [PATH], { id: "fal-ai/flux/dev", supportsLora: false }),
};
console.log(JSON.stringify(out));
"""
    proc = subprocess.run(["node", "-e", harness], capture_output=True, text=True, cwd=str(ROOT))
    ok(proc.returncode == 0, "node pack harness: %s" % (proc.stderr.strip()[-400:] if proc.returncode else "ok"))
    data = json.loads(proc.stdout.strip().splitlines()[-1])
    ok(data["civitaiOk"]["packed"] and data["civitaiOk"]["packed"][0]["air"].startswith("urn:air:"), "civitai air ships")
    ok("modelId" in data["civitaiOk"]["fields"], "packed row keeps modelId")
    ok("versionId" in data["civitaiOk"]["fields"], "packed row keeps versionId")
    ok("strength" in data["civitaiOk"]["fields"], "packed row keeps strength")
    packed_parse = data["civitaiFromAir"]["packed"]
    ok(packed_parse and packed_parse[0]["modelId"] == "2323765" and packed_parse[0]["versionId"] == "3071582",
       "civitai parses modelId/versionId from air")
    ok(data["civitaiNoStrength"]["lack"] is True and data["civitaiNoStrength"]["packed"] is None,
       "civitai missing strength blocked, no default 1.0")
    ok("strength" in data["civitaiNoStrength"]["msg"], "missing strength message")
    ok(data["civitaiMixedStrength"]["lack"] is True and data["civitaiMixedStrength"]["packed"] is None,
       "civitai mixed strength blocked whole pack")
    ok("其余条" in data["civitaiMixedStrength"]["msg"], "mixed strength message")
    ok(data["civitaiBad"]["lack"] is True and data["civitaiBad"]["packed"] is None, "civitai path-only blocked")
    ok(data["civitaiMixed"]["lack"] is True and data["civitaiMixed"]["packed"] is None, "civitai mixed blocked")
    ok("其余条" in data["civitaiMixed"]["msg"], "mixed message")
    ok(data["falOk"]["packed"] and data["falOk"]["packed"][0]["path"].startswith("http"), "fal http ships")
    ok(data["falMixed"]["lack"] is True and data["falMixed"]["packed"] is None, "fal mixed blocked")
    ok(data["msMixed"]["lack"] is True and data["msMixed"]["packed"] is None, "modelscope mixed blocked")
    ok(data["unsupported"]["lack"] is True, "unsupported model blocks residual LoRA")
    ok(data["unsupported"]["packed"] is None, "unsupported model does not pack LoRA")
    ok("不支持 LoRA" in data["unsupported"]["msg"], "unsupported model message")


def python_ref_and_compile():
    unknown = {"id": "fal-ai/mystery-i2v", "category": "video"}
    ok(declared_max_refs(unknown) is None, "undeclared video row has no cap")
    ok(max_refs("fal", gc("fal"), item=unknown) is None, "unknown cap is not provider 9")
    raised = False
    try:
        enforce_ref_cap(["https://ex/a.png", "https://ex/b.png"], backend="fal", caps=gc("fal"), item=unknown)
    except ValueError as exc:
        raised = "上限未知" in str(exc)
    ok(raised, "unknown cap enforce fails")
    civ = {
        "raw": {"id": "image/comfy/boogu/edit/editImage"},
        "frameFields": ["images"],
        "constraints": {"images": {"type": "array", "maxItems": 2}},
    }
    ok(declared_max_refs(civ) == 2, "frameFields maxItems is the catalog cap")
    ok(max_refs("civitai", gc("civitai"), item=civ) == 2, "civitai uses maxItems=2 not 9")
    over = False
    try:
        enforce_ref_cap(
            ["https://ex/a.png", "https://ex/b.png", "https://ex/c.png"],
            backend="civitai",
            caps=gc("civitai"),
            item=civ,
        )
    except ValueError as exc:
        over = "超过上限" in str(exc)
    ok(over, "over maxItems fails instead of slicing")
    ok('payload.pop("loras", None)' not in COMPILE, "no silent pop")
    r = compile_graph(
        {
            "backend": "fal",
            "nodes": [
                {"id": "p", "op": "prompt", "params": {"text": "x"}},
                {"id": "g", "op": "t2i", "params": {"serviceId": "fal-ai/flux/schnell"}},
            ],
            "edges": [{"from": "p", "fromPort": "prompt", "to": "g", "toPort": "prompt"}],
        }
    )
    ok(r.get("ok") is True, "t2i without LoRA still compiles")
    ok("loras" not in (r.get("payload") or {}), "no leftover loras key")


def main():
    source_contracts()
    node_pack_cases()
    python_ref_and_compile()
    print("\nall ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
