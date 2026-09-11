#!/usr/bin/env node
// o61: unused fal/comfy/nano groups must be hideable and the hide script must be on the page.
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const html = fs.readFileSync(path.join(root, "static/storyboard.html"), "utf8");
const adapt = fs.readFileSync(path.join(root, "static/composer-field-adapt.js"), "utf8");
const hide = fs.readFileSync(path.join(root, "static/o61-group-hide.js"), "utf8");
const fails = [];
function check(ok, name) { if (!ok) fails.push(name); }
check(html.includes("o61-group-hide.js"), "storyboard.html loads o61-group-hide.js");
check(!html.includes("o59prompt"), "storyboard.html cache query is not o59prompt");
check(html.includes("20260912-o61groups"), "storyboard.html cache query is o61groups");
check(hide.includes('classList.toggle("hidden", !showFal)'), "o61 toggles fal hidden");
check(adapt.includes("showFalGroup") || hide.includes("showFal"), "fal group predicate exists");
check(/\.param-group\.hidden/.test(fs.readFileSync(path.join(root, "static/composer-field-adapt.css"), "utf8")), "css hides .param-group.hidden");
if (fails.length) {
  console.error("FAIL\n" + fails.map((f) => " - " + f).join("\n"));
  process.exit(1);
}
console.log("PASS o61 group-hide wired + cache bust");
