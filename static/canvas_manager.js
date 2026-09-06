/* Project/canvas management. It deliberately contains no demo assets or prompts. */
(function (global) {
  "use strict";

  const API_ROOT = "/api/canvas-projects";
  const ACTIVE_PROJECT_KEY = "civitai-studio-active-project";
  const ACTIVE_WORKSPACE_KEY = "civitai-studio-active-workspace";

  function clone(value) {
    if (typeof structuredClone === "function") return structuredClone(value);
    return JSON.parse(JSON.stringify(value));
  }

  function escapeHtml(value) {
    return String(value == null ? "" : value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function projectPath(apiRoot, projectId, ...parts) {
    return [apiRoot, encodeURIComponent(String(projectId)), ...parts.map((part) => encodeURIComponent(String(part)))].join("/");
  }

  class CanvasManager {
    constructor(options) {
      const config = options || {};
      this.root = config.root || null;
      this.apiRoot = config.apiRoot || API_ROOT;
      this.fetchImpl = config.fetchImpl || (global.fetch && global.fetch.bind(global));
      if (!this.fetchImpl) throw new Error("当前环境没有 fetch");
      this.projects = [];
      this.activeProject = null;
      this.activeCanvasId = null;
      this.workspace = "canvas";
      this.loading = false;
      this.error = "";
      this.onChange = typeof config.onChange === "function" ? config.onChange : null;
    }

    async request(path, options) {
      const response = await this.fetchImpl(path, {
        ...options,
        headers: { "Content-Type": "application/json", ...(options && options.headers) },
      });
      let body = null;
      try {
        body = await response.json();
      } catch (_) {
        body = null;
      }
      if (!response.ok) {
        const message = body && body.error ? body.error : `请求失败（${response.status}）`;
        throw new Error(message);
      }
      return body;
    }

    async load() {
      this.loading = true;
      this.error = "";
      this.render();
      try {
        const body = await this.request(this.apiRoot);
        this.projects = Array.isArray(body && body.items) ? body.items : [];
        const remembered = this.readStorage(ACTIVE_PROJECT_KEY);
        const selected = this.projects.find((item) => item.id === remembered) || this.projects[0];
        if (selected && selected.id) {
          await this.selectProject(selected.id, false);
        } else {
          this.activeProject = null;
          this.activeCanvasId = null;
          this.render();
          this.emitChange();
        }
      } catch (error) {
        this.error = error.message || "项目列表加载失败";
        this.render();
      } finally {
        this.loading = false;
        this.render();
      }
      return this.activeProject;
    }

    async selectProject(projectId, persist) {
      if (!projectId) return null;
      const body = await this.request(`${this.apiRoot}/${encodeURIComponent(projectId)}`);
      this.activeProject = body && body.project ? body.project : null;
      this.activeCanvasId = this.activeProject && this.activeProject.activeCanvasId;
      if (persist !== false) this.writeStorage(ACTIVE_PROJECT_KEY, projectId);
      this.render();
      this.emitChange();
      return this.activeProject;
    }

    async createProject(name) {
      const body = await this.request(this.apiRoot, {
        method: "POST",
        body: JSON.stringify(name == null ? {} : { name }),
      });
      const project = body && body.project;
      if (!project) throw new Error("服务端没有返回项目");
      this.projects = [project, ...this.projects.filter((item) => item.id !== project.id)];
      this.activeProject = project;
      this.activeCanvasId = project.activeCanvasId;
      this.writeStorage(ACTIVE_PROJECT_KEY, project.id);
      this.render();
      this.emitChange();
      return project;
    }

    async duplicateProject(projectId, name) {
      const id = projectId || (this.activeProject && this.activeProject.id);
      if (!id) throw new Error("请先选择项目");
      const body = await this.request(`${this.apiRoot}/${encodeURIComponent(id)}/duplicate`, {
        method: "POST",
        body: JSON.stringify(name == null ? {} : { name }),
      });
      const project = body && body.project;
      if (!project) throw new Error("服务端没有返回副本");
      this.projects = [project, ...this.projects.filter((item) => item.id !== project.id)];
      this.activeProject = project;
      this.activeCanvasId = project.activeCanvasId;
      this.writeStorage(ACTIVE_PROJECT_KEY, project.id);
      this.render();
      this.emitChange();
      return project;
    }

    async renameProject(projectId, name) {
      const id = projectId || (this.activeProject && this.activeProject.id);
      if (!id) throw new Error("请先选择项目");
      const body = await this.request(`${this.apiRoot}/${encodeURIComponent(id)}`, {
        method: "PATCH",
        body: JSON.stringify({ name }),
      });
      await this.acceptProject(body && body.project);
      return this.activeProject;
    }

    async deleteProject(projectId) {
      const id = projectId || (this.activeProject && this.activeProject.id);
      if (!id) throw new Error("请先选择项目");
      await this.request(`${this.apiRoot}/${encodeURIComponent(id)}`, { method: "DELETE" });
      this.projects = this.projects.filter((item) => item.id !== id);
      if (this.activeProject && this.activeProject.id === id) {
        const next = this.projects[0];
        if (next) await this.selectProject(next.id);
        else {
          this.activeProject = null;
          this.activeCanvasId = null;
          this.removeStorage(ACTIVE_PROJECT_KEY);
          this.render();
          this.emitChange();
        }
      } else {
        this.render();
      }
    }

    async createCanvas(name) {
      const project = this.requireProject();
      const body = await this.request(projectPath(this.apiRoot, project.id, "canvases"), {
        method: "POST",
        body: JSON.stringify(name == null ? {} : { name }),
      });
      await this.refreshProject(body && body.canvas && body.canvas.id);
      return body && body.canvas;
    }

    async renameCanvas(canvasId, name) {
      const project = this.requireProject();
      const body = await this.request(projectPath(this.apiRoot, project.id, "canvases", canvasId), {
        method: "PATCH",
        body: JSON.stringify({ name }),
      });
      await this.refreshProject(canvasId);
      return body && body.canvas;
    }

    async deleteCanvas(canvasId) {
      const project = this.requireProject();
      await this.request(projectPath(this.apiRoot, project.id, "canvases", canvasId), { method: "DELETE" });
      await this.refreshProject();
    }

    async setActiveCanvas(canvasId) {
      const project = this.requireProject();
      if (!project.canvases.some((canvas) => canvas.id === canvasId)) throw new Error("画布不存在");
      await this.saveState({ activeCanvasId: canvasId });
      return this.activeProject;
    }

    async saveState(state) {
      // PUT = 整状态替换：服务端要求 body 正好是 assets/canvases/activeCanvasId 三件套。
      // 局部入参在此补全为当前项目快照，禁止向服务端发半截状态。
      const project = this.requireProject();
      const partial = state || {};
      const full = {
        assets: clone(Array.isArray(partial.assets) ? partial.assets : project.assets || []),
        canvases: clone(Array.isArray(partial.canvases) ? partial.canvases : project.canvases || []),
        activeCanvasId: partial.activeCanvasId || project.activeCanvasId || "",
      };
      const body = await this.request(projectPath(this.apiRoot, project.id, "state"), {
        method: "PUT",
        body: JSON.stringify(full),
      });
      await this.acceptProject(body && body.project);
      return this.activeProject;
    }

    async addAsset(asset, canvasId) {
      const project = this.requireProject();
      if (!asset || typeof asset !== "object") throw new Error("资产必须是对象");
      const body = await this.request(projectPath(this.apiRoot, project.id, "assets"), {
        method: "POST",
        body: JSON.stringify({ asset }),
      });
      const saved = body && body.asset;
      if (!saved || !saved.id) throw new Error("服务端没有返回资产");
      await this.refreshProject();
      await this.bindAsset(saved.id, canvasId || this.activeCanvasId);
      return saved;
    }

    async bindAsset(assetId, canvasId) {
      const project = this.requireProject();
      const id = canvasId || this.activeCanvasId || project.activeCanvasId;
      const canvases = clone(project.canvases || []);
      const canvas = canvases.find((item) => item.id === id);
      if (!canvas) throw new Error("画布不存在");
      if (!(project.assets || []).some((asset) => asset.id === assetId)) throw new Error("资产不存在");
      canvas.assetIds = Array.from(new Set([...(canvas.assetIds || []), assetId]));
      await this.saveState({ canvases, activeCanvasId: id });
      return this.activeProject;
    }

    async unbindAsset(assetId, canvasId) {
      const project = this.requireProject();
      const id = canvasId || this.activeCanvasId || project.activeCanvasId;
      const canvases = clone(project.canvases || []);
      const canvas = canvases.find((item) => item.id === id);
      if (!canvas) throw new Error("画布不存在");
      canvas.assetIds = (canvas.assetIds || []).filter((value) => value !== assetId);
      await this.saveState({ canvases, activeCanvasId: id });
      return this.activeProject;
    }

    async removeAsset(assetId) {
      const project = this.requireProject();
      await this.request(projectPath(this.apiRoot, project.id, "assets", assetId), { method: "DELETE" });
      await this.refreshProject();
    }

    requireProject() {
      if (!this.activeProject || !this.activeProject.id) throw new Error("请先选择项目");
      return this.activeProject;
    }

    async refreshProject(preferredCanvasId) {
      const project = this.requireProject();
      await this.selectProject(project.id);
      if (preferredCanvasId && this.activeProject.canvases.some((item) => item.id === preferredCanvasId)) {
        this.activeCanvasId = preferredCanvasId;
      }
      this.render();
    }

    async acceptProject(project) {
      if (!project || !project.id) throw new Error("服务端没有返回项目");
      this.activeProject = project;
      this.activeCanvasId = project.activeCanvasId;
      this.projects = [project, ...this.projects.filter((item) => item.id !== project.id)];
      this.writeStorage(ACTIVE_PROJECT_KEY, project.id);
      this.render();
      this.emitChange();
    }

    setWorkspace(workspace) {
      const value = ["story", "canvas", "editor"].includes(workspace) ? workspace : "canvas";
      this.workspace = value;
      this.writeStorage(ACTIVE_WORKSPACE_KEY, value);
      this.renderWorkspaceTabs();
      this.emitChange();
    }

    readStorage(key) {
      try {
        return global.localStorage && global.localStorage.getItem(key);
      } catch (_) {
        return null;
      }
    }

    writeStorage(key, value) {
      try {
        if (global.localStorage) global.localStorage.setItem(key, value);
      } catch (_) {}
    }

    removeStorage(key) {
      try {
        if (global.localStorage) global.localStorage.removeItem(key);
      } catch (_) {}
    }

    emitChange() {
      if (this.onChange) this.onChange(this.activeProject, this.activeCanvasId, this.workspace);
      if (this.root && typeof global.CustomEvent === "function") {
        this.root.dispatchEvent(new CustomEvent("canvas-manager:change", {
          bubbles: true,
          detail: { project: this.activeProject, canvasId: this.activeCanvasId, workspace: this.workspace },
        }));
      }
    }

    renderWorkspaceTabs() {
      if (!this.root) return;
      const buttons = global.document
        ? global.document.querySelectorAll("[data-workspace]")
        : this.root.querySelectorAll("[data-workspace]");
      buttons.forEach((button) => {
        const active = button.dataset.workspace === this.workspace;
        button.classList.toggle("on", active);
        button.setAttribute("aria-selected", active ? "true" : "false");
      });
    }

    render() {
      if (!this.root) return;
      const project = this.activeProject;
      const canvases = project && Array.isArray(project.canvases) ? project.canvases : [];
      const assets = project && Array.isArray(project.assets) ? project.assets : [];
      const currentCanvasId = this.activeCanvasId || (project && project.activeCanvasId) || "";
      const projectOptions = this.projects
        .map((item) => `<option value="${escapeHtml(item.id)}"${project && item.id === project.id ? " selected" : ""}>${escapeHtml(item.name)}</option>`)
        .join("");
      const canvasRows = canvases.length
        ? canvases.map((canvas) => `
          <li class="cm-row${canvas.id === currentCanvasId ? " on" : ""}">
            <button type="button" data-action="select-canvas" data-id="${escapeHtml(canvas.id)}">${escapeHtml(canvas.name)}</button>
            <button type="button" class="cm-icon" data-action="rename-canvas" data-id="${escapeHtml(canvas.id)}" aria-label="重命名画布">⋯</button>
          </li>`).join("")
        : `<li class="cm-empty">暂无画布</li>`;
      const assetRows = assets.length
        ? assets.map((asset) => {
            const currentCanvas = canvases.find((canvas) => canvas.id === currentCanvasId);
            const bound = !!currentCanvas && (currentCanvas.assetIds || []).includes(asset.id);
            const label = asset.title || asset.name || asset.id;
            const media = asset.url ? `<img src="${escapeHtml(asset.url)}" alt="" loading="lazy">` : `<span class="cm-thumb-empty">—</span>`;
            return `<li class="cm-asset${bound ? " bound" : ""}">
              ${media}<span title="${escapeHtml(label)}">${escapeHtml(label)}</span>
              <button type="button" data-action="toggle-asset" data-id="${escapeHtml(asset.id)}">${bound ? "解绑" : "绑定"}</button>
            </li>`;
          }).join("")
        : `<li class="cm-empty">暂无资产</li>`;
      const status = this.loading ? "加载中…" : this.error ? escapeHtml(this.error) : "";
      const title = global.document && global.document.getElementById("projTitle");
      if (title) title.textContent = project ? project.name : "未命名项目";
      this.root.innerHTML = `
        <div class="cm-head">
          <nav class="cm-tabs" role="tablist" aria-label="工作区">
            <button type="button" role="tab" data-workspace="story" aria-selected="${this.workspace === "story" ? "true" : "false"}">剧本策划</button>
            <button type="button" role="tab" data-workspace="canvas" aria-selected="${this.workspace === "canvas" ? "true" : "false"}">画布</button>
            <button type="button" role="tab" data-workspace="editor" aria-selected="${this.workspace === "editor" ? "true" : "false"}">编辑器</button>
          </nav>
          <button type="button" class="cm-close" data-action="close" aria-label="关闭项目面板">×</button>
        </div>
        <div class="cm-controls">
          <label>项目<select data-action="select-project"><option value="">${project ? "选择项目" : "暂无项目"}</option>${projectOptions}</select></label>
          <button type="button" data-action="create-project">新建</button>
          <button type="button" data-action="duplicate-project"${project ? "" : " disabled"}>副本</button>
          <button type="button" data-action="rename-project"${project ? "" : " disabled"}>重命名</button>
          <button type="button" data-action="delete-project"${project ? "" : " disabled"}>删除</button>
        </div>
        <div class="cm-status" role="status">${status}</div>
        <div class="cm-columns">
          <section><h3>画布</h3><button type="button" class="cm-add" data-action="create-canvas"${project ? "" : " disabled"}>+ 新建画布</button><ul>${canvasRows}</ul></section>
          <section><h3>资产 <small>当前项目</small></h3><ul>${assetRows}</ul><p class="cm-note">资产必须先由真实导入或生成结果提供。</p></section>
        </div>`;
      this.bindEvents();
      this.renderWorkspaceTabs();
    }

    bindEvents() {
      if (!this.root || this.root.dataset.bound === "true") return;
      this.root.dataset.bound = "true";
      this.root.addEventListener("click", async (event) => {
        const target = event.target.closest("[data-action], [data-workspace]");
        if (!target) return;
        try {
          if (target.dataset.workspace) return this.setWorkspace(target.dataset.workspace);
          const action = target.dataset.action;
          if (action === "close") return this.root.classList.remove("show");
          if (action === "select-project") return;
          if (action === "create-project") return this.createProject(global.prompt("项目名称（可留空）") || undefined);
          if (action === "duplicate-project") return this.duplicateProject(null, global.prompt("副本名称（可留空）") || undefined);
          if (action === "rename-project") return this.renameProject(null, global.prompt("新项目名称") || "");
          if (action === "delete-project") {
            if (global.confirm("确认删除当前项目？")) return this.deleteProject();
            return;
          }
          if (action === "create-canvas") return this.createCanvas(global.prompt("画布名称（可留空）") || undefined);
          if (action === "select-canvas") return this.setActiveCanvas(target.dataset.id);
          if (action === "rename-canvas") return this.renameCanvas(target.dataset.id, global.prompt("新画布名称") || "");
          if (action === "toggle-asset") {
            const project = this.requireProject();
            const canvas = (project.canvases || []).find((item) => item.id === (this.activeCanvasId || project.activeCanvasId));
            const bound = !!canvas && (canvas.assetIds || []).includes(target.dataset.id);
            return bound ? this.unbindAsset(target.dataset.id) : this.bindAsset(target.dataset.id);
          }
        } catch (error) {
          this.error = error.message || "操作失败";
          this.render();
        }
      });
      this.root.addEventListener("change", (event) => {
        const target = event.target.closest('[data-action="select-project"]');
        if (target && target.value) this.selectProject(target.value).catch((error) => {
          this.error = error.message || "项目切换失败";
          this.render();
        });
      });
    }
  }

  function mountCanvasManager(root, options) {
    const target = root || (global.document && global.document.getElementById("canvasManager"));
    if (!target) return null;
    const manager = new CanvasManager({ ...(options || {}), root: target });
    const rememberedWorkspace = manager.readStorage(ACTIVE_WORKSPACE_KEY);
    if (rememberedWorkspace) manager.workspace = rememberedWorkspace;
    target.classList.add("canvas-manager");
    target.addEventListener("canvas-manager:open", () => target.classList.add("show"));
    manager.load();
    return manager;
  }

  global.CanvasManager = CanvasManager;
  global.mountCanvasManager = mountCanvasManager;

  function boot() {
    const root = global.document && global.document.getElementById("canvasManager");
    if (root) {
      global.canvasManager = mountCanvasManager(root);
      const toggle = global.document.getElementById("canvasManagerToggle");
      if (toggle) toggle.addEventListener("click", () => root.classList.toggle("show"));
      global.document.querySelectorAll("header [data-workspace]").forEach((button) => {
        button.addEventListener("click", () => {
          global.canvasManager.setWorkspace(button.dataset.workspace);
          root.classList.add("show");
        });
      });
    }
  }

  if (global.document) {
    if (global.document.readyState === "loading") global.document.addEventListener("DOMContentLoaded", boot);
    else boot();
  }
})(typeof window !== "undefined" ? window : globalThis);
