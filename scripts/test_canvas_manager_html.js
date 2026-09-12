// Live storyboard.html must actually mount canvas manager: toggle, panel, script, CSS, real API.
// The JS module already exists; this test fails while HTML never loads it.
// Run: node scripts/test_canvas_manager_html.js
"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const root = path.resolve(__dirname, "..");
const html = fs.readFileSync(path.join(root, "static/storyboard.html"), "utf8");
const css = fs.readFileSync(path.join(root, "static/storyboard-ui.css"), "utf8");
const manager = fs.readFileSync(path.join(root, "static/canvas_manager.js"), "utf8");

const tests = [];
function test(name, fn) { tests.push({ name, fn }); }

test("HTML has #canvasManager panel", () => {
  assert.match(html, /id="canvasManager"/);
});

test("HTML has visible new-canvas control", () => {
  assert.match(html, /id="btnNewCanvas"/);
  assert.match(html, /id="canvasSelect"/);
});

test("HTML has visible 项目 toggle #canvasManagerToggle", () => {
  assert.match(html, /id="canvasManagerToggle"/);
  assert.match(html, /<button[^>]*id="canvasManagerToggle"[^>]*>\s*项目\s*<\/button>/);
});

test("HTML loads /static/canvas_manager.js", () => {
  assert.match(html, /<script[^>]+src="\/static\/canvas_manager\.js/);
});

test("CSS shows .canvas-manager only when .show", () => {
  assert.match(css, /\.canvas-manager/);
  assert.match(css, /\.canvas-manager\.show/);
});

test("manager still talks to real /api/canvas-projects", () => {
  assert.match(manager, /API_ROOT\s*=\s*"\/api\/canvas-projects"/);
});

test("boot binds toggle, does not steal live header script/editor tabs", () => {
  const start = manager.indexOf("function boot()");
  assert.ok(start >= 0, "boot() exists");
  const end = manager.indexOf("if (global.document)", start + 10);
  const boot = manager.slice(start, end > start ? end : start + 800);
  assert.match(boot, /canvasManagerToggle/);
  assert.doesNotMatch(boot, /header \[data-workspace\]/);
});

test("renderWorkspaceTabs only scopes panel tabs, not live header", () => {
  const start = manager.indexOf("renderWorkspaceTabs()");
  assert.ok(start >= 0, "renderWorkspaceTabs exists");
  const end = manager.indexOf("async saveWorkspace", start);
  const body = manager.slice(start, end > start ? end : start + 600);
  assert.match(body, /this\.root\.querySelectorAll\("\[data-workspace\]"\)/);
  assert.doesNotMatch(body, /document\.querySelectorAll\("\[data-workspace\]"\)/);
});

test("live workspace tabs stay script/canvas/editor", () => {
  assert.match(html, /data-workspace="script"/);
  assert.match(html, /data-workspace="canvas"/);
  assert.match(html, /data-workspace="editor"/);
});

(async () => {
  let failed = 0;
  for (const t of tests) {
    try {
      await t.fn();
      console.log("  ok   " + t.name);
    } catch (err) {
      failed += 1;
      console.log("  FAIL " + t.name);
      console.log("       " + (err && err.message ? err.message.split("\n")[0] : err));
    }
  }
  if (failed) {
    console.log("FAIL canvas-manager-html " + failed);
    process.exit(1);
  }
  console.log("PASS canvas-manager-html");
})();
