#!/usr/bin/env node
/** o140: nano-gpt video duration from UI must enter page↑ genParams. */
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "..");
const source = fs.readFileSync(path.join(root, "static/storyboard.js"), "utf8");

assert.ok(
  /else if \(be === "nano-gpt"\)[\s\S]*?genParams\.duration = durN/.test(source),
  "nano-gpt branch must assign genParams.duration"
);
assert.ok(
  source.includes("o140: UI duration must enter page↑ payload for nano video"),
  "o140 comment present"
);

// Extract buildShotRequest / graph builder by locating nano-gpt duration pack snippet
// and running a minimal harness around the packing logic.
const start = source.indexOf('} else if (be === "nano-gpt") {');
assert.ok(start > 0, "nano branch");
const end = source.indexOf("} else {", start);
assert.ok(end > start, "else after nano");
const nanoBlock = source.slice(start + "} else if (be === \"nano-gpt\") {".length, end);

function runCase(opts) {
  const state = { mode: opts.mode || "video" };
  const els = {
    nanoRes: { value: opts.nanoRes || "720p" },
    duration: {
      value: opts.durationVal || "5s",
      classList: { contains: () => false },
    },
    falParams: {
      classList: { contains: (c) => c === "hidden" && !!opts.falHidden },
    },
  };
  function $(id) { return els[id] || null; }
  function catalogCaps() { return { videoDuration: opts.videoDuration == null ? "string_seconds" : opts.videoDuration }; }
  function durationGateMessage() { return opts.gate || ""; }
  function parseDurationSeconds(raw) {
    return Number.parseInt(String(raw == null ? "" : raw).replace(/s$/i, "").trim(), 10);
  }
  const genParams = {};
  const op = opts.op || "t2v";
  const res = "1280x720";
  const aspect = "16:9";
  const be = "nano-gpt";
  eval(nanoBlock); // eslint-disable-line no-eval
  return genParams;
}

const packed = runCase({ falHidden: false, durationVal: "5s" });
assert.equal(packed.duration, 5, "visible duration packs as seconds");
assert.equal(packed.resolution, "720p");

const hidden = runCase({ falHidden: true, durationVal: "5s" });
assert.equal(hidden.duration, undefined, "hidden falParams group must not invent duration");

const imageMode = runCase({ mode: "image", op: "t2i", falHidden: false });
assert.equal(imageMode.duration, undefined, "image mode does not pack duration");

console.log("PASS o140_nano_duration_outbound");
