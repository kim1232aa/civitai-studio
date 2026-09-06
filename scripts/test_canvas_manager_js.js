// Pure-method contract test for static/canvas_manager.js (no DOM, no boot).
// Run: node scripts/test_canvas_manager_js.js
"use strict";

const fs = require("fs");
const path = require("path");

const ROOT = path.resolve(__dirname, "..");
const SCRIPT = fs.readFileSync(path.join(ROOT, "static", "canvas_manager.js"), "utf8");

class FakeStorage {
  constructor() { this.map = new Map(); }
  getItem(k) { return this.map.has(k) ? this.map.get(k) : null; }
  setItem(k, v) { this.map.set(k, String(v)); }
  removeItem(k) { this.map.delete(k); }
}

function mkProject(name, id) {
  const now = new Date().toISOString();
  const canvas = {
    id: id + "-canvas", name: "主画布", nodes: [], edges: [], assetIds: [],
    viewport: { x: 0, y: 0, zoom: 1 }, createdAt: now, updatedAt: now,
  };
  return { id, name, createdAt: now, updatedAt: now, activeCanvasId: canvas.id, canvases: [canvas], assets: [] };
}

function FakeServer(projects) {
  this.projects = projects;
  this.requests = [];
}
FakeServer.prototype.handle = async function (url, options) {
  const method = (options && options.method) || "GET";
  this.requests.push(`${method} ${url}`);
  const rest = url.split("?")[0].split("/").filter(Boolean).slice(2);
  const body = options && options.body ? JSON.parse(options.body) : {};
  const find = (id) => this.projects.find((p) => p.id === id);
  const respond = (payload, status) => ({ status: status || 200, data: payload });
  if (method === "GET") {
    if (rest.length === 0) return respond({ items: JSON.parse(JSON.stringify(this.projects)) });
    const project = find(rest[0]);
    return project ? respond({ project: JSON.parse(JSON.stringify(project)) }) : respond({ error: "项目不存在" }, 404);
  }
  if (method === "POST") {
    if (rest.length === 0) {
      const project = mkProject(body.name || "未命名项目", "project-" + Math.random().toString(36).slice(2, 10));
      this.projects.unshift(project);
      return respond({ project }, 201);
    }
    if (rest[1] === "duplicate") {
      const source = find(rest[0]);
      const project = JSON.parse(JSON.stringify(source));
      project.id = "project-dup-" + Math.random().toString(36).slice(2, 8);
      project.name = body.name || source.name + " 副本";
      const assetMap = {};
      project.assets = project.assets.map((a) => { const nid = "asset-dup-" + Math.random().toString(36).slice(2, 8); assetMap[a.id] = nid; return { ...a, id: nid }; });
      project.canvases = project.canvases.map((c, i) => ({ ...c, id: "canvas-dup-" + i, assetIds: (c.assetIds || []).map((x) => assetMap[x] || x) }));
      project.activeCanvasId = project.canvases[0].id;
      this.projects.unshift(project);
      return respond({ project }, 201);
    }
    if (rest[1] === "canvases") {
      const project = find(rest[0]);
      const canvas = { id: "canvas-new-" + Math.random().toString(36).slice(2, 8), name: body.name || "主画布", nodes: [], edges: [], assetIds: [], viewport: { x: 0, y: 0, zoom: 1 }, createdAt: "", updatedAt: "" };
      project.canvases.push(canvas);
      project.activeCanvasId = canvas.id;
      return respond({ canvas }, 201);
    }
    if (rest[1] === "assets") {
      const project = find(rest[0]);
      const asset = { ...(body.asset || {}), id: "asset-new-" + Math.random().toString(36).slice(2, 8) };
      project.assets.push(asset);
      return respond({ asset }, 201);
    }
  }
  if (method === "PUT" && rest[1] === "state") {
    const project = find(rest[0]);
    // 与真实 server.py 同口径：PUT = 整状态替换，三件套缺一不可。
    const required = ["assets", "canvases", "activeCanvasId"];
    const missing = required.filter((key) => !(key in body));
    if (missing.length) return respond({ error: "missing " + missing.join(",") }, 400);
    project.assets = body.assets;
    project.canvases = body.canvases;
    project.activeCanvasId = body.activeCanvasId;
    return respond({ project: JSON.parse(JSON.stringify(project)) });
  }
  if (method === "PATCH" && rest.length === 1) {
    const project = find(rest[0]);
    if (body.name !== undefined) project.name = body.name;
    return respond({ project: JSON.parse(JSON.stringify(project)) });
  }
  if (method === "DELETE" && rest.length === 1) {
    this.projects = this.projects.filter((p) => p.id !== rest[0]);
    return respond({ deleted: rest[0] });
  }
  return respond({ error: "not found " + url }, 404);
};

(async () => {
  const server = new FakeServer([mkProject("镜头A", "project-a"), mkProject("镜头B", "project-b")]);
  global.window = global;
  global.localStorage = new FakeStorage();
  global.sessionStorage = new FakeStorage();
  global.fetch = (url, options) => Promise.resolve(server.handle(url, options)).then((result) => ({ ok: !result.status || (result.status >= 200 && result.status < 300), status: result.status || 200, json: async () => result.data }));
  eval(SCRIPT);

  const Manager = global.CanvasManager;
  if (typeof Manager !== "function") throw new Error("CanvasManager not exported");
  const probe = await global.fetch("/api/canvas-projects").then(async (r) => ({ ok: r.ok, status: r.status, data: await r.json() }));
  console.log("probe:", JSON.stringify(probe).slice(0, 300));
  const manager = new Manager({ fetchImpl: global.fetch }); // root null => render() no-ops
  await manager.load();
  console.log("load selects first project:", manager.activeProject && manager.activeProject.name, "| error:", JSON.stringify(manager.error), "| count:", manager.projects.length);
  if (!manager.activeProject || manager.activeProject.name !== "镜头A") throw new Error("load() did not select first project");
  if (manager.projects.length !== 2) throw new Error("project list not hydrated");

  const created = await manager.createProject("新项目C");
  console.log("createProject empty start:", created.canvases[0].nodes.length === 0 && created.canvases[0].assetIds.length === 0);
  if (created.canvases[0].nodes.length !== 0 || created.canvases[0].assetIds.length !== 0) throw new Error("new project seeded");

  const asset = await manager.addAsset({ kind: "image", title: "导入素材", url: "/out/real.jpg" });
  const active = manager.activeProject.canvases.find((c) => c.id === manager.activeCanvasId);
  console.log("addAsset auto-binds to active canvas:", active.assetIds.includes(asset.id));
  if (!active.assetIds.includes(asset.id)) throw new Error("asset not bound");

  // 副本 remap 断言放在新增画布之前：此时资产绑在唯一画布（主画布）上，
  // duplicate 后 active 画布必须携带同一批资产的新 id（服务端 remap 语义）。
  const dup = await manager.duplicateProject(created.id, "副本");
  const dupActive = dup.canvases.find((c) => c.id === dup.activeCanvasId);
  const remaps =
    dup.id !== created.id &&
    dup.assets.length === 1 &&
    dup.assets[0].id !== asset.id &&
    !!dupActive &&
    dupActive.assetIds[0] === dup.assets[0].id &&
    dupActive.assetIds.length === dup.assets.length;
  console.log("duplicate remaps ids:", remaps, "| assets:", dup.assets.map((a) => a.id), "| active canvas assetIds:", dupActive && dupActive.assetIds);
  if (dup.id === created.id) throw new Error("duplicate kept project id");
  if (!remaps) throw new Error("duplicate did not remap assetIds on active canvas");

  const canvas = await manager.createCanvas("第二画布");
  console.log("createCanvas empty start:", canvas.nodes.length === 0 && canvas.assetIds.length === 0);
  if (canvas.nodes.length !== 0 || canvas.assetIds.length !== 0) throw new Error("new canvas seeded");

  await manager.selectProject(created.id);
  await manager.unbindAsset(asset.id);
  const afterUnbind = manager.activeProject.canvases.find((c) => c.id === manager.activeCanvasId);
  console.log("unbind removes from canvas:", !afterUnbind.assetIds.includes(asset.id));
  if (afterUnbind.assetIds.includes(asset.id)) throw new Error("unbind failed");

  await manager.renameProject(null, "改名后");
  console.log("renameProject:", manager.activeProject.name);
  if (manager.activeProject.name !== "改名后") throw new Error("rename failed");

  await manager.deleteProject(created.id);
  console.log("deleteProject removes:", !manager.projects.some((p) => p.id === created.id));
  if (manager.projects.some((p) => p.id === created.id)) throw new Error("delete failed");

  manager.setWorkspace("story");
  console.log("setWorkspace persists:", global.localStorage.getItem("civitai-studio-active-workspace"));
  if (global.localStorage.getItem("civitai-studio-active-workspace") !== "story") throw new Error("workspace not persisted");

  const source = SCRIPT + JSON.stringify(server.projects);
  if (/机器人|扫地|demo-|DEMO_BOT|light-preset|CHAR_LIB|loadDemo/i.test(source)) throw new Error("seed/robot content found");
  console.log("no robot/demo/seed content");
  console.log("OK canvas-manager-js-contract");
})().catch((error) => { console.error("FAIL", error); process.exit(1); });
