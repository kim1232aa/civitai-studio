#!/usr/bin/env node
"use strict";
const fs = require("fs");
const path = require("path");
const vm = require("vm");
const ROOT = path.resolve(__dirname, "..");
const src = fs.readFileSync(path.join(ROOT, "static/storyboard.js"), "utf8");
function slice(startNeedle, endNeedle) {
  const a = src.indexOf(startNeedle);
  if (a < 0) throw new Error("missing start " + startNeedle.slice(0, 60));
  const b = src.indexOf(endNeedle, a + startNeedle.length);
  if (b < 0) throw new Error("missing end " + endNeedle.slice(0, 60));
  return src.slice(a, b);
}
const extracted = [
  "const FAL_T2I_DEFAULT = \"fal-ai/flux/schnell\";",
  "const FAL_I2V_DEFAULT = \"fal-ai/minimax/video-01/image-to-video\";",
  "const HF_LORA_PREF_SERVICE = \"krea/Krea-2-Turbo\";",
  "const HF_I2I_PREF_SERVICE = \"Qwen/Qwen-Image-Edit\";",
  "const MS_LORA_PREF_SERVICE = \"krea/Krea-2-Turbo\";",
  "const CATALOG_PAGE_SIZE = 50;",
  slice("  const SMART_PREF = {", "  let _svcChunkHandle"),
  slice("  function catalogItemSupportsI2v(it) {", "  function catalogItemSupportsImage(it) {"),
  slice("  function catalogItemSupportsImage(it) {", "  function catalogItemSupportsI2i(it) {"),
  slice("  function catalogItemSupportsI2i(it) {", "  function selectedShotWantsI2i() {"),
  slice("  function catalogItemSupportsT2i(it) {", "  function filterCatalogForMode(items) {"),
  slice("  function catalogEatsRefs(it) {", "  function editSiblingId(it) {"),
  slice("  function pinHfLoraServiceId(sid, op) {", "  function ensureHfLoraServiceSelected() {"),
  slice("  function pinMsLoraServiceId(sid, op) {", "  function msLoraOptionLabel(want, currentText) {")
].join("\n");
console.log("extracted", extracted.length);
