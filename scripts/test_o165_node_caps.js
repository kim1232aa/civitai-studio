#!/usr/bin/env node
/** o165: click node → on-node capability strip (collapsed), not a covering desk. */
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("path");

const root = path.resolve(__dirname, "..");
const js = fs.readFileSync(path.join(root, "static/storyboard.js"), "utf8");
const html = fs.readFileSync(path.join(root, "static/storyboard.html"), "utf8");
const shell = fs.readFileSync(path.join(root, "static/storyboard-shell.css"), "utf8");
const pin = fs.readFileSync(path.join(root, "static/o97-dock-pin.css"), "utf8");
const o67 = fs.readFileSync(path.join(root, "static/o67-human-copy.js"), "utf8");
const ui = fs.readFileSync(path.join(root, "static/storyboard-ui.css"), "utf8");

assert.ok(js.includes("v0821o165"), "js stamp o165");
assert.ok(html.includes("o165nodecaps"), "html cache-bust o165");

const setDock = js.slice(js.indexOf("function setDockMode"), js.indexOf("function setDockMode") + 500);
assert.ok(!/if \(mode === "collapsed"\) mode = "expanded"/.test(setDock),
  "setDockMode must keep collapsed");

const render = js.slice(js.indexOf("function renderDock"), js.indexOf("function selectNode"));
assert.ok(!/if \(state\.dockMode === "collapsed"\) state\.dockMode = "expanded"/.test(render),
  "renderDock must not promote collapsed to expanded");

const select = js.slice(js.indexOf("function selectNode"), js.indexOf("function clientToWorld"));
assert.ok(select.includes('state.dockMode = "collapsed"'), "selectNode opens collapsed caps");
assert.ok(!/no toy collapsed bar/.test(select) || select.includes("opts.expand"),
  "selectNode no longer always expands desk");

assert.ok(js.includes("collapsed = 贴节点窄条") || js.includes("collapsed = state.dockMode === \"collapsed\""),
  "positionDock distinguishes collapsed width");

assert.ok(shell.includes(".dock.show.collapsed .dock-prompt"), "shell hides prompt on collapsed");
assert.ok(shell.includes("display: none !important") && /collapsed \.lora-block/.test(shell),
  "shell hides lora on collapsed");
assert.ok(pin.includes("max-width: 420px") || pin.includes("max-width:420px"),
  "pin css collapsed max 420");
assert.ok(o67.includes(".dock.show.collapsed{"), "o67 pin css collapsed branch");
assert.ok(ui.includes(".dock.collapsed .modes { display: flex !important; }")
  || ui.includes(".dock.collapsed .modes{display:flex !important}"),
  "collapsed still shows mode tabs");

console.log("PASS o165_node_caps");
