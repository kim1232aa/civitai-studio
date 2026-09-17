#!/usr/bin/env node
/** o166: 故事推演沿用原家原模型；故事边不当参考；禁止队列偷换成 krea2。 */
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("path");

const root = path.resolve(__dirname, "..");
const js = fs.readFileSync(path.join(root, "static/storyboard.js"), "utf8");
const html = fs.readFileSync(path.join(root, "static/storyboard.html"), "utf8");

assert.ok(js.includes("v0821o166"), "js stamp o166");
assert.ok(html.includes("o166story"), "html cache-bust o166");
assert.ok(html.includes("故事推演"), "story tool stays");
assert.ok(js.includes("function storyAdvanceFromShot"), "story fn stays");
assert.ok(js.includes("function stripStoryBeats"), "strip stacked beats");
assert.ok(js.includes("function storyBeatLine"), "named beat line");
assert.ok(js.includes('linkRole: "story"'), "story edge is timeline, not i2i ref");
assert.ok(js.includes('e.role !== "story"'), "connectedNodes skips story edges");
assert.ok(js.includes("skipSelect: true"), "story spawn does not expand desk");
assert.ok(js.includes("n.storyAdvance"), "queue sees story flag");
assert.ok(js.includes("selectNode(n.id, { expand: !n.storyAdvance"), "story queue stays collapsed");
assert.ok(js.includes("!n.storyAdvance && refs.length"), "krea2/edit swap skipped for story");
assert.ok(js.includes("!n.storyAdvance && sid === \"image/textToImage\""), "Civitai pref swap skipped for story");
assert.ok(js.includes("diffusionModel"), "spawn copies diffusionModel");
assert.ok(/["']width["'], ["']height["'], ["']steps["']/.test(js), "spawn copies size/steps");
assert.ok(js.includes("else if (Array.isArray(n.loras))"), "queue copies node.loras");
assert.ok(!/function storyAdvanceFromShot[\s\S]{0,900}firstFrameFromSource: !!shot\.url/.test(js),
  "image story must not firstFrameFromSource (would i2i/unused-ref)");
assert.ok(js.includes("video && !!shot.url"), "video story still can first-frame");
assert.ok(js.includes("故事边不当参考，但视频推演仍认 firstFrameId"), "video firstFrame survives story edge");
assert.ok(js.includes("图生图/视频才把角色参考跟到下一镜"), "copy inbound assets only when model eats refs");
assert.ok(js.includes("沿用原家原模型"), "honest copy");
assert.ok(!/function generateShotQueue[\s\S]{0,2200}fetch\("\/api\/generate"/.test(js),
  "queue still goes runShotUntilDone, no extra generate stack");

console.log("PASS o166_story_advance");
