#!/usr/bin/env node
/** o167: Seko 故事推演 panel — slider ±5s, aspect, keep house/model, Generate. */
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("path");

const root = path.resolve(__dirname, "..");
const js = fs.readFileSync(path.join(root, "static/storyboard.js"), "utf8");
const html = fs.readFileSync(path.join(root, "static/storyboard.html"), "utf8");
const css = fs.readFileSync(path.join(root, "static/storyboard-ui.css"), "utf8");

assert.ok(js.includes("v0821o167"), "js stamp o167");
assert.ok(html.includes("o167story"), "html cache-bust o167");
assert.ok(html.includes('href="/static/storyboard-ui.css?v=o167story"'), "css link o167");
assert.ok(html.includes("故事推演"), "story tool stays");
assert.ok(js.includes("function showStoryPop"), "showStoryPop");
assert.ok(js.includes("function fillStoryPop"), "fillStoryPop");
assert.ok(js.includes("data-story-slider"), "slider");
assert.ok(js.includes("向后推演") && js.includes("向前推演"), "dir labels");
assert.ok(js.includes('data-story-sec="-5"') && js.includes('data-story-sec="5"'), "±5s ticks");
assert.ok(js.includes("['9:16', '16:9', '3:4', '4:3']"), "seko aspects");
assert.ok(js.includes("data-story-aspect"), "aspect buttons");
assert.ok(js.includes('if (a === "3:4")') && js.includes('if (a === "4:3")'), "sizeFromAspectRes 3:4/4:3");
assert.ok(js.includes('["3:4", 3 / 4]') && js.includes('["4:3", 4 / 3]'), "ASPECT_CHOICES 3:4 4:3");
assert.ok(js.includes("function storyModelLabel"), "model label from shot");
assert.ok(!/fillStoryPop[\s\S]{0,1600}专业模型/.test(js), "do not invent 专业模型");
assert.ok(!/fillStoryPop[\s\S]{0,1600}通用模型/.test(js), "do not invent 通用模型");
assert.ok(js.includes("不编专业/通用"), "honest no-invent copy");
assert.ok(js.includes("data-story-go"), "Generate button");
assert.ok(js.includes("先把滑条拨离 0"), "0 does not generate");
assert.ok(!js.includes('data-story="3" data-dir="next">往后 3 秒'), "old 4-button pop gone");
assert.ok(js.includes("storyAdvanceFromShot(selectedShot(), st.seconds, st.dir"), "Generate calls advance");
assert.ok(js.includes("{ aspect: st.aspect }"), "aspect passed");
assert.ok(css.includes(".story-pop-seko"), "panel css");
assert.ok(js.includes('e.role !== "story"'), "story edge still not i2i ref");
assert.ok(js.includes("!n.storyAdvance && refs.length"), "still no krea2 steal");
assert.ok(js.includes("go.disabled = !(Math.abs(Number(value)) > 0)"), "Generate disabled at 0");
assert.ok(js.includes("故事推演-") && js.includes("向前推演 "), "node title matches Seko 故事推演-向前推演 N 帧");
assert.ok(js.includes("故事推演任务已提交"), "toast matches Seko");

console.log("PASS o167_story_panel");
