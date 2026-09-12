#!/usr/bin/env node
// o59: expanded Composer must keep the prompt textarea usable.
// Source-level so it fails before a browser pass. Never generates.
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const html = fs.readFileSync(path.join(root, "static/storyboard.html"), "utf8");
const css = fs.readFileSync(path.join(root, "static/storyboard-ui.css"), "utf8")
  + fs.readFileSync(path.join(root, "static/storyboard-shell.css"), "utf8");
const js = fs.readFileSync(path.join(root, "static/storyboard.js"), "utf8");
const fails = [];
function check(ok, name) {
  if (!ok) fails.push(name);
}
const pos = js.match(/function positionDock\(\)[\s\S]*?window\.positionDock/);
check(!!pos, "positionDock found");
check(!!(pos && !/expanded \? 380/.test(pos[0])), "expanded dock is not hard-capped at 380px");
check(!!(pos && /Math\.min\(720/.test(pos[0]) && /dw/.test(pos[0])), "expanded dock sizes from the selected card, cap 720");
check(!!(pos && /attach = "below"/.test(pos[0])), "composer prefers below the selected shot");
check(!!(pos && !/const stage = /.test(pos[0])), "positionDock does not shadow outer stage");
check(html.includes('id="prompt"'), "prompt textarea exists");
check(html.includes('class="dock-prompt"'), "prompt lives in a non-shrinking dock-prompt slot");
check(/\.dock-prompt[\s\S]{0,280}min-height:\s*(?:5[6-9]|[6-9]\d|1[0-9]{2})px/.test(css + html), "prompt slot has a usable min-height");
check(/max-width:\s*min\(720px/.test(css) || /Math\.min\(720/.test(js), "expanded composer can be wider than 560");
if (fails.length) {
  console.error("FAIL\n" + fails.map((f) => " - " + f).join("\n"));
  process.exit(1);
}
console.log("PASS o59 composer prompt layout no-380 dock-prompt min-height wider");
