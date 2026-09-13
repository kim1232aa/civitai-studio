/* node scripts/test_o134_lora_house_remap.js */
const path = require("path");
const api = require(path.join(__dirname, "..", "static", "lora-house-remap.js"));

function assert(cond, msg) {
  if (!cond) throw new Error(msg || "assert failed");
}

const airRow = {
  air: "urn:air:sdxl:lora:civitai:614515@686955",
  name: "Alya",
  strength: 0.6,
  versionId: "686955",
  modelId: "614515"
};

const civ = api.remapRow("civitai", airRow);
assert(civ.outbound, "civitai should outbound AIR");
assert(api.isAir(civ.air), "civitai keeps AIR");
assert(civ.strength === 0.6, "strength kept");

const fal = api.remapRow("fal", airRow);
assert(fal.outbound, "fal outbound");
assert(fal.path === "https://civitai.com/api/download/models/686955", "fal uses download URL");
assert(!api.isAir(fal.path), "fal path is not AIR");

const nano = api.remapRow("nano-gpt", airRow);
assert(nano.outbound && nano.path.indexOf("/686955") >= 0, "nano path from versionId");

const ms = api.remapRow("modelscope-ai", airRow);
assert(!ms.outbound, "ms rejects AIR");
assert(ms.path === "", "ms clears path");
assert(ms.chipReason.indexOf("Hub") >= 0, "ms asks Hub search");

const msOk = api.remapRow("modelscope-cn", { path: "DiffSynth-Studio/Z-Image-Turbo-DistillPatch", strength: null });
assert(msOk.outbound, "ms hub ok");
assert(msOk.strength === null, "null strength kept");

const hf = api.remapRow("huggingface", airRow);
assert(hf.outbound, "hf can send path");
assert(hf.chipReason.indexOf("HF") >= 0, "hf unverified copy");

const airOnly = { air: "urn:air:sdxl:lora:civitai:1@2" };
const fal2 = api.remapRow("fal", airOnly);
assert(fal2.path.endsWith("/2"), "version from AIR suffix");

const civBad = api.remapRow("civitai", { name: "x", path: "https://civitai.com/api/download/models/1" });
assert(!civBad.outbound, "http is not AIR for civitai");

const packed = api.packOutbound("fal", [airRow, { name: "dead" }]);
assert(packed.length === 1, "pack drops non-outbound");

console.log("PASS o134 lora-house-remap");
