(function () {
  const $ = (id) => document.getElementById(id);
  const STORE = "nl-storyboard-v0791";
  const STORE_OLD = "nl-storyboard-v0790";
  const vp = $("viewport");
  const world = $("world");
  const wires = $("wires");
  const dock = $("dock");
  const DEMO = "/out/fal_fal-ai_flux_schnell_01a05be2-19bd-75e1-8053-0a6f8de59915_0.jpg";

  const state = {
    cam: { x: 90, y: 36, s: 0.3 },
    nodes: [],
    edges: [],
    selected: null,
    drag: null,
    pan: null,
    link: null,
    railDrag: null,
    mode: "image",
    catalog: [],
    history: [],
    railTab: "assets",
    atFilter: "",
  };

  function uid(prefix) { return prefix + "-" + Math.random().toString(36).slice(2, 8); }
  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&" + "amp;")
      .replace(/</g, "&" + "lt;")
      .replace(/"/g, "&" + "quot;");
  }
  function isVideoUrl(u) { return /\.(mp4|webm|mov)(\?|$)/i.test(u || ""); }
  function isImageSource(n) { return !!(n && n.url && !isVideoUrl(n.url)); }
  function nodeById(id) { return state.nodes.find((n) => n.id === id); }
  function box(n) { return n.kind === "shot" ? { w: 640, h: 360 } : { w: 132, h: 208 }; }
  function assets() { return state.nodes.filter((n) => n.kind !== "shot"); }
  function shots() { return state.nodes.filter((n) => n.kind === "shot"); }
  function connectedNodes(shotId) {
    return state.edges.filter((e) => e.to === shotId).map((e) => nodeById(e.from)).filter(Boolean);
  }
  function connectedAssets(shotId) {
    return connectedNodes(shotId).filter(isImageSource);
  }
  function frameAsset(shot) {
    const linked = connectedAssets(shot.id);
    if (shot.firstFrameId) {
      const hit = linked.find((a) => a.id === shot.firstFrameId);
      if (hit) return hit;
    }
    return linked[0] || null;
  }
  function sourceTitle(n) {
    if (!n) return "";
    if (n.kind === "shot") return (n.title || "分镜") + "成片";
    return n.title || "资产";
  }

  function loadDemo() {
    const list = [
      { id: "a-bot", kind: "character", title: "家用机器人", x: 48, y: 24, url: DEMO },
      { id: "a-home", kind: "character", title: "大白-居家装", x: 48, y: 260, url: DEMO },
      { id: "a-work", kind: "character", title: "大白-职场装", x: 48, y: 496, url: DEMO },
      { id: "a-vac", kind: "character", title: "扫地机器人", x: 48, y: 732, url: DEMO },
      { id: "s-bed", kind: "scene", title: "温馨现代卧室", x: 48, y: 992, url: DEMO },
      { id: "s-bath", kind: "scene", title: "现代感洗手间", x: 48, y: 1228, url: DEMO },
    ];
    const shotNodes = [];
    for (let i = 0; i < 6; i++) {
      shotNodes.push({
        id: "shot-" + (i + 1),
        kind: "shot",
        title: "分镜" + (i + 1),
        x: 560 + (i % 2) * 720,
        y: 80 + Math.floor(i / 2) * 430,
        url: "",
        firstFrameId: "",
        prompt: "【镜头" + (i + 1) + "】\n场景：@温馨现代卧室\n画面：室内固定镜头，人物与家用机器人同框，晨光从窗帘缝里进来。\n运镜：固定镜头。",
      });
    }
    state.nodes = list.concat(shotNodes);
    state.edges = [
      { from: "a-bot", to: "shot-1" }, { from: "a-home", to: "shot-1" }, { from: "s-bed", to: "shot-1" },
      { from: "a-bot", to: "shot-2" }, { from: "s-bed", to: "shot-2" },
      { from: "a-work", to: "shot-3" }, { from: "a-vac", to: "shot-4" },
      { from: "s-bed", to: "shot-5" }, { from: "s-bath", to: "shot-6" },
    ];
    const s1 = nodeById("shot-1");
    if (s1) s1.firstFrameId = "a-bot";
  }

  function persist() {
    try {
      sessionStorage.setItem(STORE, JSON.stringify({
        cam: state.cam, nodes: state.nodes, edges: state.edges, mode: state.mode,
        railTab: state.railTab,
        backend: $("backend") && $("backend").value,
        service: $("service") && $("service").value,
        duration: $("duration") && $("duration").value,
        aspect: $("aspect") && $("aspect").value,
        res: $("res") && $("res").value,
      }));
    } catch (_) {}
  }
  function restore() {
    try {
      const p = JSON.parse(sessionStorage.getItem(STORE) || sessionStorage.getItem(STORE_OLD) || "null");
      if (!p || !p.nodes || !p.nodes.length) return false;
      state.cam = p.cam || state.cam;
      state.nodes = p.nodes;
      state.edges = p.edges || [];
      state.mode = p.mode || "image";
      state.railTab = p.railTab || "assets";
      if (p.backend && $("backend")) $("backend").value = p.backend;
      if (p.duration && $("duration")) $("duration").value = p.duration;
      if (p.aspect && $("aspect")) $("aspect").value = p.aspect;
      if (p.res && $("res")) $("res").value = p.res;
      state._pendingService = p.service || "";
      return true;
    } catch (_) { return false; }
  }

  function applyCam() {
    world.style.transform = "translate(" + state.cam.x + "px," + state.cam.y + "px) scale(" + state.cam.s + ")";
    $("zPct").textContent = Math.round(state.cam.s * 100) + "%";
  }
  function panTo(n) {
    if (!n) return;
    const b = box(n);
    const r = vp.getBoundingClientRect();
    state.cam.x = r.width * 0.38 - (n.x + b.w / 2) * state.cam.s;
    state.cam.y = r.height * 0.42 - (n.y + b.h / 2) * state.cam.s;
    applyCam();
  }
  function bezier(x1, y1, x2, y2) {
    const dx = Math.max(90, Math.abs(x2 - x1) * 0.5);
    return "M " + x1 + " " + y1 + " C " + (x1 + dx) + " " + y1 + " " + (x2 - dx) + " " + y2 + " " + x2 + " " + y2;
  }
  function portPos(n, side) {
    const b = box(n);
    const y = n.y + b.h / 2;
    return side === "out" ? { x: n.x + b.w, y: y } : { x: n.x, y: y };
  }
  function drawWires() {
    const parts = ["<defs></defs>"];
    state.edges.forEach((e) => {
      const a = nodeById(e.from), b = nodeById(e.to);
      if (!a || !b) return;
      const p1 = portPos(a, "out"), p2 = portPos(b, "in");
      parts.push('<path d="' + bezier(p1.x, p1.y, p2.x, p2.y) + '" />');
    });
    if (state.link && state.link.x2 != null) {
      parts.push('<path d="' + bezier(state.link.x1, state.link.y1, state.link.x2, state.link.y2) + '" style="opacity:1;stroke:#fff" />');
    }
    wires.innerHTML = parts.join("");
    const maxX = Math.max(2400, ...state.nodes.map((n) => n.x + box(n).w + 400));
    const maxY = Math.max(2400, ...state.nodes.map((n) => n.y + box(n).h + 400));
    wires.setAttribute("width", String(maxX));
    wires.setAttribute("height", String(maxY));
  }

  function cardHTML(n) {
    const sel = state.selected === n.id ? " sel" : "";
    if (n.kind === "shot") {
      const media = n.url
        ? (isVideoUrl(n.url)
            ? '<video src="' + esc(n.url) + '" muted></video>'
            : '<img src="' + esc(n.url) + '" alt="">')
        : '<div class="face"><div style="font-size:22px">▢</div><div class="hint">点击查看或编辑提示词</div></div>';
      return '<div class="card shot' + sel + '" data-id="' + esc(n.id) + '" style="left:' + n.x + 'px;top:' + n.y + 'px">' +
        '<div class="label">▢ ' + esc(n.title) + '</div>' +
        '<div class="face">' + media + '</div>' +
        '<button class="port in" data-side="in" type="button">+</button>' +
        '<button class="port out" data-side="out" type="button">+</button></div>';
    }
    const thumb = n.url
      ? '<img class="thumb" src="' + esc(n.url) + '" alt="">'
      : '<div class="ph">▣</div>';
    return '<div class="card asset' + sel + '" data-id="' + esc(n.id) + '" style="left:' + n.x + 'px;top:' + n.y + 'px">' +
      thumb + '<div class="name">' + esc(n.title) + '</div>' +
      '<button class="port out" data-side="out" type="button">+</button></div>';
  }
  function renderCards() {
    world.querySelectorAll(".card").forEach((el) => el.remove());
    state.nodes.forEach((n) => world.insertAdjacentHTML("beforeend", cardHTML(n)));
  }

  function renderRail() {
    const rail = $("assetRail");
    if (!rail) return;
    const shot = nodeById(state.selected);
    const canPin = shot && shot.kind === "shot";
    const tabAssets = state.railTab !== "history";
    const tabs = '<div class="rail-tabs">' +
      '<button type="button" data-tab="assets"' + (tabAssets ? ' class="on"' : "") + ">资产</button>' +
      '<button type="button" data-tab="history"' + (!tabAssets ? ' class="on"' : "") + ">历史</button></div>';
    let body;
    if (tabAssets) {
      const list = assets();
      body = '<div class="rail-h">画布资产 · 可拖出</div>' +
        list.map((a) => {
          const on = state.selected === a.id ? " on" : "";
          return '<div class="rail-item' + on + '" data-rail="' + esc(a.id) + '">' +
            (a.url ? '<img src="' + esc(a.url) + '" alt="">' : "") +
            "<span>" + esc(a.title) + "</span>" +
            (canPin ? '<button class="pin" type="button" data-pin="' + esc(a.id) + '" title="接到此镜">＋</button>' : "") +
            "</div>";
        }).join("") +
        '<button class="rail-item add" type="button" data-act="upload">+ 上传</button>';
    } else {
      const list = state.history;
      body = '<div class="rail-h">生成历史 · 拖到画布</div>' +
        (list.length ? list.map((it, i) => {
          return '<div class="rail-item" data-hist="' + i + '">' +
            (it.url ? '<img src="' + esc(it.url) + '" alt="">' : "") +
            "<span>" + esc(it.title) + "</span>" +
            (canPin ? '<button class="pin" type="button" data-hist-pin="' + i + '" title="接到此镜">＋</button>' : "") +
            "</div>";
        }).join("") : "<div class='rail-h'>还没有成片</div>");
    }
    rail.innerHTML = tabs + body;
  }

  function renderDock() {
    const n = nodeById(state.selected);
    if (!n || n.kind !== "shot") {
      dock.classList.remove("show");
      renderRail();
      return;
    }
    dock.classList.add("show");
    $("prompt").value = n.prompt || "";
    $("modeVid").classList.toggle("on", state.mode === "video");
    $("modeImg").classList.toggle("on", state.mode === "image");
    const list = assets();
    const linked = connectedAssets(n.id);
    const frame = frameAsset(n);
    const needFrame = state.mode === "video" && !frame;
    if ($("send")) $("send").disabled = needFrame;
    let frameHtml = "";
    if (state.mode === "video") {
      if (frame) {
        frameHtml = '<div class="frame-slot">首帧 <img src="' + esc(frame.url) + '" alt="">' + esc(sourceTitle(frame)) +
          linked.filter((a) => a.url && a.id !== frame.id).map((a) => {
            return '<button class="frame-chip" type="button" data-frame="' + esc(a.id) + '" title="设为首帧">' +
              (a.url ? '<img src="' + esc(a.url) + '" alt="">' : "") + esc(sourceTitle(a)) + "</button>";
          }).join("") + "</div>";
      } else {
        frameHtml = '<div class="frame-slot missing">视频需要先连一张首帧图</div>';
      }
    }
    const promoteBtn = n.url && !isVideoUrl(n.url)
      ? '<button class="chip-btn" type="button" data-act="promote" title="收进资产库">入库</button>'
      : "";
    $("refs").innerHTML = frameHtml +
      '<button class="chip-btn" type="button" data-act="upload">上传</button>' +
      '<button class="chip-btn" type="button" data-act="pick">选择</button>' +
      promoteBtn +
      linked.concat(list.filter((a) => !linked.includes(a))).slice(0, 8).map((a) => {
        const on = linked.some((x) => x.id === a.id) ? " on" : "";
        return '<button class="chip' + on + '" type="button" data-asset="' + esc(a.id) + '" title="' + esc(sourceTitle(a)) + '">' +
          (a.url ? '<img src="' + esc(a.url) + '" alt="">' : esc(sourceTitle(a).slice(0, 2))) + "</button>";
      }).join("");
    renderRail();
  }

  function selectNode(id) {
    state.selected = id;
    renderCards();
    drawWires();
    renderDock();
  }
  function clientToWorld(cx, cy) {
    const r = vp.getBoundingClientRect();
    return {
      x: (cx - r.left - state.cam.x) / state.cam.s,
      y: (cy - r.top - state.cam.y) / state.cam.s,
    };
  }
  function hitNode(wx, wy) {
    for (let i = state.nodes.length - 1; i >= 0; i--) {
      const n = state.nodes[i];
      const b = box(n);
      if (wx >= n.x && wx <= n.x + b.w && wy >= n.y && wy <= n.y + b.h) return n;
    }
    return null;
  }

  function mention(asset, shot) {
    shot = shot || nodeById(state.selected);
    if (!shot || shot.kind !== "shot") return;
    const tag = "@" + sourceTitle(asset);
    if (!(shot.prompt || "").includes(tag)) {
      shot.prompt = (shot.prompt ? shot.prompt + " " : "") + tag;
      if ($("prompt") && state.selected === shot.id) $("prompt").value = shot.prompt;
    }
  }
  function unmention(asset, shot) {
    if (!shot) return;
    const tag = "@" + sourceTitle(asset);
    if ((shot.prompt || "").includes(tag)) {
      shot.prompt = shot.prompt.split(tag).join("").replace(/[ \t]{2,}/g, " ").replace(/\n{3,}/g, "\n\n");
      if ($("prompt") && state.selected === shot.id) $("prompt").value = shot.prompt;
    }
  }
  function linkAssetToShot(asset, shot) {
    if (!asset || !shot || shot.kind !== "shot" || asset.id === shot.id) return;
    if (asset.kind === "shot" && !isImageSource(asset)) return;
    if (!state.edges.some((e) => e.from === asset.id && e.to === shot.id)) {
      state.edges.push({ from: asset.id, to: shot.id });
    }
    mention(asset, shot);
    if (shot && !shot.firstFrameId && isImageSource(asset)) shot.firstFrameId = asset.id;
  }
  function unlinkAssetFromShot(asset, shot) {
    if (!asset || !shot) return;
    state.edges = state.edges.filter((e) => !(e.from === asset.id && e.to === shot.id));
    unmention(asset, shot);
    if (shot && shot.firstFrameId === asset.id) shot.firstFrameId = "";
  }
  function toggleAssetOnShot(asset, shot) {
    if (!asset || !shot || shot.kind !== "shot") return;
    if (state.edges.some((e) => e.from === asset.id && e.to === shot.id)) unlinkAssetFromShot(asset, shot);
    else linkAssetToShot(asset, shot);
  }

  function promoteResult(shot, url) {
    if (!shot || !url || isVideoUrl(url)) return null;
    const aid = "out-" + shot.id;
    let asset = nodeById(aid) || assets().find((a) => a.url === url);
    if (!asset) {
      asset = {
        id: aid,
        kind: "character",
        title: (shot.title || "分镜") + "成片",
        x: shot.x + 680,
        y: shot.y + 20,
        url: url,
        fromShot: shot.id,
      };
      state.nodes.push(asset);
    } else {
      asset.url = url;
      asset.title = (shot.title || "分镜") + "成片";
      asset.fromShot = shot.id;
    }
    return asset;
  }

  function spawnHistoryAt(item, x, y) {
    if (!item || !item.url) return null;
    const existing = assets().find((a) => a.url === item.url);
    if (existing) {
      if (x != null) { existing.x = x; existing.y = y; }
      return existing;
    }
    const node = {
      id: uid("hist"),
      kind: "character",
      title: item.title || "历史成片",
      x: x != null ? x : 220,
      y: y != null ? y : 24 + assets().length * 40,
      url: item.url,
    };
    state.nodes.push(node);
    return node;
  }

  function normalizePrompt(shot) {
    const linked = connectedAssets(shot.id);
    let text = shot.prompt || "";
    linked.forEach((a, i) => {
      const tag = "@" + sourceTitle(a);
      if (text.indexOf(tag) >= 0) text = text.split(tag).join("@图片" + (i + 1));
    });
    return text;
  }

  function hideAtbox() {
    const box = $("atbox");
    if (box) box.classList.remove("show");
  }
  function showAtbox(query) {
    const box = $("atbox");
    if (!box) return;
    const q = String(query || "").toLowerCase();
    const pool = assets().concat(shots().filter(isImageSource));
    const list = pool.filter((a) => !q || sourceTitle(a).toLowerCase().indexOf(q) >= 0);
    box.innerHTML = list.map((a) =>
      '<button type="button" data-at="' + esc(a.id) + '">' +
      (a.url ? '<img src="' + esc(a.url) + '" alt="">' : "") + esc(sourceTitle(a)) + "</button>"
    ).join("") || "<div style='color:#888;padding:8px'>没有匹配的资产</div>";
    box.classList.add("show");
  }

  function insertMention(asset) {
    const shot = nodeById(state.selected);
    if (!shot || shot.kind !== "shot") return;
    const ta = $("prompt");
    const tag = "@" + sourceTitle(asset);
    if (ta) {
      const v = ta.value || "";
      const caret = ta.selectionStart || v.length;
      const before = v.slice(0, caret);
      const at = before.lastIndexOf("@");
      let next;
      if (at >= 0 && !/[\s\n]/.test(before.slice(at + 1))) {
        next = v.slice(0, at) + tag + " " + v.slice(caret);
      } else if (v.indexOf(tag) < 0) {
        next = (v ? v + " " : "") + tag;
      } else next = v;
      shot.prompt = next;
      ta.value = next;
    }
    linkAssetToShot(asset, shot);
    hideAtbox();
    renderCards(); drawWires(); renderDock(); persist();
  }

  function readFileAsDataUrl(f) {
    return new Promise((resolve, reject) => {
      const r = new FileReader();
      r.onload = () => resolve(r.result);
      r.onerror = () => reject(r.error);
      r.readAsDataURL(f);
    });
  }
  async function uploadOut(f) {
    try {
      const dataUrl = await readFileAsDataUrl(f);
      const r = await fetch("/api/upload-out", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ dataUrl: dataUrl, filename: f.name }),
      });
      const j = await r.json();
      if (r.ok && j && j.url) return j.url;
      setMsg((j && j.error) || "上传未成功，改用本地预览", "warn");
    } catch (e) {
      setMsg("上传失败，改用本地预览", "warn");
    }
    return URL.createObjectURL(f);
  }

  function hideGhost() {
    const g = $("ghost");
    if (g) { g.classList.remove("show"); g.innerHTML = ""; }
  }
  function showGhost(url, cx, cy) {
    const g = $("ghost");
    if (!g) return;
    g.innerHTML = url ? '<img src="' + esc(url) + '" alt="">' : "";
    g.style.left = (cx - 36) + "px";
    g.style.top = (cy - 36) + "px";
    g.classList.add("show");
  }

  vp.addEventListener("pointerdown", (e) => {
    if (e.target.closest(".dock,.tools,.zoom,.picker,.rail,.atbox,header,.ghost")) return;
    const port = e.target.closest(".port");
    const card = e.target.closest(".card");
    if (port && card) {
      const n = nodeById(card.dataset.id);
      const p = portPos(n, port.dataset.side === "in" ? "in" : "out");
      state.link = { from: n.id, side: port.dataset.side, x1: p.x, y1: p.y, x2: p.x, y2: p.y };
      vp.setPointerCapture(e.pointerId);
      return;
    }
    if (card) {
      const n = nodeById(card.dataset.id);
      selectNode(n.id);
      const w = clientToWorld(e.clientX, e.clientY);
      state.drag = { id: n.id, dx: w.x - n.x, dy: w.y - n.y };
      vp.setPointerCapture(e.pointerId);
      return;
    }
    state.pan = { x: e.clientX - state.cam.x, y: e.clientY - state.cam.y };
    vp.classList.add("grabbing");
    vp.setPointerCapture(e.pointerId);
  });
  vp.addEventListener("pointermove", (e) => {
    if (state.link) {
      const w = clientToWorld(e.clientX, e.clientY);
      state.link.x2 = w.x; state.link.y2 = w.y; drawWires(); return;
    }
    if (state.drag) {
      const w = clientToWorld(e.clientX, e.clientY);
      const n = nodeById(state.drag.id);
      n.x = w.x - state.drag.dx; n.y = w.y - state.drag.dy;
      renderCards(); drawWires(); return;
    }
    if (state.pan) {
      state.cam.x = e.clientX - state.pan.x;
      state.cam.y = e.clientY - state.pan.y;
      applyCam();
    }
  });
  vp.addEventListener("pointerup", (e) => {
    if (state.link) {
      const w = clientToWorld(e.clientX, e.clientY);
      const target = hitNode(w.x, w.y);
      if (target && target.id !== state.link.from) {
        const a = nodeById(state.link.from);
        const dst = target.kind === "shot" ? target : (a.kind === "shot" ? a : null);
        const src = dst === target ? a : target;
        if (src && dst && dst.kind === "shot" && src.id !== dst.id && (src.kind !== "shot" || isImageSource(src))) {
          linkAssetToShot(src, dst);
          selectNode(dst.id);
        }
      }
      state.link = null;
      drawWires(); persist();
    }
    if (state.drag) persist();
    state.drag = null; state.pan = null;
    vp.classList.remove("grabbing");
  });
  vp.addEventListener("wheel", (e) => {
    e.preventDefault();
    const w0 = clientToWorld(e.clientX, e.clientY);
    const next = Math.min(1.5, Math.max(0.16, state.cam.s * (e.deltaY > 0 ? 0.92 : 1.08)));
    const r = vp.getBoundingClientRect();
    state.cam.s = next;
    state.cam.x = e.clientX - r.left - w0.x * next;
    state.cam.y = e.clientY - r.top - w0.y * next;
    applyCam(); persist();
  }, { passive: false });

  $("refs").addEventListener("click", (e) => {
    const frameBtn = e.target.closest("[data-frame]");
    if (frameBtn) {
      const shot = nodeById(state.selected);
      if (shot && shot.kind === "shot") {
        shot.firstFrameId = frameBtn.dataset.frame;
        renderDock(); persist();
      }
      return;
    }
    const assetBtn = e.target.closest("[data-asset]");
    if (assetBtn) {
      const asset = nodeById(assetBtn.dataset.asset);
      const shot = nodeById(state.selected);
      if (asset && shot) { toggleAssetOnShot(asset, shot); renderCards(); drawWires(); renderDock(); persist(); }
      return;
    }
    const act = e.target.closest("[data-act]");
    if (!act) return;
    if (act.dataset.act === "upload") $("file").click();
    if (act.dataset.act === "pick") togglePicker();
    if (act.dataset.act === "promote") {
      const shot = nodeById(state.selected);
      if (shot && shot.url) {
        const asset = promoteResult(shot, shot.url);
        if (asset) { selectNode(asset.id); persist(); setMsg("已收进资产库，可拖到下一镜", "ok"); }
      }
    }
  });

  function dropRailOnCanvas(payload, cx, cy) {
    const w = clientToWorld(cx, cy);
    const hit = hitNode(w.x, w.y);
    let node = payload.node || null;
    if (!node && payload.item) node = spawnHistoryAt(payload.item, w.x - 66, w.y - 40);
    if (node && (!hit || hit.kind !== "shot")) {
      node.x = w.x - 66;
      node.y = w.y - 40;
    }
    if (node && hit && hit.kind === "shot") {
      linkAssetToShot(node, hit);
      selectNode(hit.id);
    } else if (node) {
      selectNode(node.id);
    }
    renderCards(); drawWires(); renderDock(); persist();
  }

  if ($("assetRail")) {
    $("assetRail").addEventListener("pointerdown", (e) => {
      if (e.target.closest("[data-act],[data-tab],[data-pin],[data-hist-pin]")) return;
      const railBtn = e.target.closest("[data-rail]");
      const histBtn = e.target.closest("[data-hist]");
      if (railBtn) {
        const asset = nodeById(railBtn.dataset.rail);
        if (!asset) return;
        state.railDrag = { kind: "asset", id: asset.id, url: asset.url, title: asset.title, x: e.clientX, y: e.clientY, moved: false };
        railBtn.setPointerCapture(e.pointerId);
      } else if (histBtn) {
        const item = state.history[Number(histBtn.dataset.hist)];
        if (!item) return;
        state.railDrag = { kind: "hist", item: item, url: item.url, title: item.title, x: e.clientX, y: e.clientY, moved: false };
        histBtn.setPointerCapture(e.pointerId);
      }
    });
    $("assetRail").addEventListener("pointermove", (e) => {
      if (!state.railDrag) return;
      const dx = e.clientX - state.railDrag.x, dy = e.clientY - state.railDrag.y;
      if (!state.railDrag.moved && dx * dx + dy * dy < 36) return;
      state.railDrag.moved = true;
      showGhost(state.railDrag.url, e.clientX, e.clientY);
    });
    $("assetRail").addEventListener("pointerup", (e) => {
      const drag = state.railDrag;
      state.railDrag = null;
      hideGhost();
      if (!drag) return;
      if (drag.moved) {
        const rail = $("assetRail").getBoundingClientRect();
        if (e.clientX > rail.right + 8) {
          dropRailOnCanvas(
            drag.kind === "hist" ? { item: drag.item } : { node: nodeById(drag.id) },
            e.clientX, e.clientY
          );
        }
        return;
      }
      if (drag.kind === "asset") {
        const asset = nodeById(drag.id);
        if (asset) { selectNode(asset.id); panTo(asset); persist(); }
      } else if (drag.kind === "hist" && drag.item) {
        const node = spawnHistoryAt(drag.item);
        if (node) { selectNode(node.id); panTo(node); persist(); }
      }
    });
    $("assetRail").addEventListener("click", (e) => {
      const tab = e.target.closest("[data-tab]");
      if (tab) { state.railTab = tab.dataset.tab; renderRail(); persist(); return; }
      const up = e.target.closest("[data-act]");
      if (up && up.dataset.act === "upload") { $("file").click(); return; }
      const pin = e.target.closest("[data-pin]");
      if (pin) {
        const asset = nodeById(pin.dataset.pin);
        const shot = nodeById(state.selected);
        if (asset && shot && shot.kind === "shot") {
          toggleAssetOnShot(asset, shot); renderCards(); drawWires(); renderDock(); persist();
        }
        return;
      }
      const histPin = e.target.closest("[data-hist-pin]");
      if (histPin) {
        const item = state.history[Number(histPin.dataset.histPin)];
        const shot = nodeById(state.selected);
        if (item && shot && shot.kind === "shot") {
          const node = spawnHistoryAt(item, shot.x - 180, shot.y + 40);
          linkAssetToShot(node, shot);
          renderCards(); drawWires(); renderDock(); persist();
        }
      }
    });
  }

  $("file").addEventListener("change", async () => {
    const f = $("file").files && $("file").files[0];
    if (!f) return;
    setMsg("正在上传…");
    const url = await uploadOut(f);
    const id = uid("asset");
    const n = assets().length;
    const node = { id: id, kind: "character", title: f.name.replace(/\.[^.]+$/, ""), x: 220, y: 24 + n * 40, url: url };
    state.nodes.push(node);
    const shot = nodeById(state.selected);
    if (shot && shot.kind === "shot") linkAssetToShot(node, shot);
    else selectNode(id);
    renderCards(); drawWires(); renderDock(); persist();
    if (url.indexOf("/out/") === 0) setMsg("已上传到资产库", "ok");
    $("file").value = "";
  });

  function togglePicker() {
    const box = $("picker");
    box.classList.toggle("show");
    hideAtbox();
    const list = assets().concat(shots().filter(isImageSource));
    box.innerHTML = list.map((a) =>
      '<button type="button" data-asset="' + esc(a.id) + '">' +
      (a.url ? '<img src="' + esc(a.url) + '" alt="">' : "") + esc(sourceTitle(a)) + "</button>"
    ).join("") || "<div style='color:#888;padding:8px'>还没有资产</div>";
  }
  $("picker").addEventListener("click", (e) => {
    const btn = e.target.closest("[data-asset]");
    if (!btn) return;
    const asset = nodeById(btn.dataset.asset);
    const shot = nodeById(state.selected);
    if (asset && shot) toggleAssetOnShot(asset, shot);
    $("picker").classList.remove("show");
    renderCards(); drawWires(); renderDock(); persist();
  });
  if ($("atbox")) {
    $("atbox").addEventListener("click", (e) => {
      const btn = e.target.closest("[data-at]");
      if (!btn) return;
      const asset = nodeById(btn.dataset.at);
      if (asset) insertMention(asset);
    });
  }

  $("prompt").addEventListener("input", () => {
    const n = nodeById(state.selected);
    if (n) { n.prompt = $("prompt").value; persist(); }
    const ta = $("prompt");
    const v = ta.value || "";
    const caret = ta.selectionStart || v.length;
    const before = v.slice(0, caret);
    const at = before.lastIndexOf("@");
    if (at >= 0 && !/[\s\n]/.test(before.slice(at + 1))) {
      showAtbox(before.slice(at + 1));
    } else hideAtbox();
  });
  $("modeImg").onclick = () => { state.mode = "image"; renderDock(); persist(); };
  $("modeVid").onclick = () => { state.mode = "video"; renderDock(); persist(); };
  ["backend", "service", "duration", "aspect", "res"].forEach((id) => {
    if ($(id)) $(id).addEventListener("change", persist);
  });

  function setMsg(t, cls) {
    if (!$("msg")) return;
    $("msg").textContent = t;
    $("msg").className = "msg" + (cls ? " " + cls : "");
  }

  function buildGraph(shot) {
    const frame = frameAsset(shot);
    const linked = connectedAssets(shot.id);
    const nodes = [{ id: "p-" + shot.id, op: "prompt", params: { text: normalizePrompt(shot) } }];
    const edges = [{ from: "p-" + shot.id, fromPort: "prompt", to: shot.id, toPort: "prompt" }];
    linked.forEach((a) => nodes.push({ id: a.id, op: "image", params: { url: a.url } }));
    let op = "t2i";
    if (state.mode === "video") op = "i2v";
    else if (linked[0]) op = "i2i";
    const aspect = $("aspect").value || "16:9";
    const res = $("res").value === "1080P" ? (aspect === "9:16" ? "1080x1920" : "1920x1080") : (aspect === "9:16" ? "720x1280" : "1280x720");
    nodes.push({
      id: shot.id, op: op,
      params: {
        serviceId: $("service").value || (op === "i2v" ? "fal-ai/minimax/video-01" : "fal-ai/flux/schnell"),
        resolution: res,
        duration: parseInt($("duration").value, 10) || 5,
      },
    });
    const ref = (op === "i2v") ? frame : linked[0];
    if (ref) edges.push({ from: ref.id, fromPort: "image", to: shot.id, toPort: "image" });
    return { backend: $("backend").value, nodes: nodes, edges: edges };
  }

  function pickUrl(data) {
    if (!data) return "";
    if (typeof data.url === "string") return data.url;
    const first = (arr) => arr && arr[0] && (arr[0].url || arr[0].path || arr[0]);
    return first(data.saved) || first(data.files) || first(data.urls) || first(data.images) || first(data.videos) || "";
  }

  async function generate() {
    const shot = nodeById(state.selected);
    if (!shot || shot.kind !== "shot") return;
    if (state.mode === "video" && !frameAsset(shot)) {
      setMsg("视频需要先连一张首帧图，不能偷配方台", "bad"); return;
    }
    $("send").disabled = true;
    setMsg("校验连线…");
    let compiled;
    try {
      const r = await fetch("/api/graph/compile", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify(buildGraph(shot)),
      });
      compiled = await r.json();
    } catch (e) {
      setMsg(String(e), "bad"); $("send").disabled = false; return;
    }
    if (!compiled.ok) { setMsg(compiled.error || "校验未通过", "bad"); $("send").disabled = false; return; }
    const payload = compiled.payload || (compiled.stages && compiled.stages[0] && compiled.stages[0].payload);
    if (!payload) { setMsg("没有 payload", "bad"); $("send").disabled = false; return; }
    setMsg("正在请求云 API…");
    try {
      const r = await fetch("/api/generate", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      let j = await r.json();
      if (!r.ok || j.error) throw new Error(j.error || ("HTTP " + r.status));
      const jobId = j.id || j.jobId || j.workflowId;
      if (jobId && !pickUrl(j)) {
        for (let i = 0; i < 40; i++) {
          await new Promise((res) => setTimeout(res, 2500));
          const st = await (await fetch("/api/jobs/" + encodeURIComponent(jobId))).json();
          if (st.error || st.status === "failed") throw new Error(st.error || "任务失败");
          if (pickUrl(st) || st.status === "done" || st.status === "succeeded" || st.status === "completed") { j = st; break; }
          setMsg("云端进行中 " + (i + 1) + "/40");
        }
      }
      const url = pickUrl(j);
      if (url) {
        shot.url = url;
        if (!isVideoUrl(url)) promoteResult(shot, url);
        renderCards(); drawWires(); persist();
        setMsg(isVideoUrl(url) ? "此镜视频完成" : "此镜完成，成片已收进资产库", "ok");
      } else setMsg("云端已返回，没有可预览地址", "warn");
    } catch (e) { setMsg(String(e), "bad"); }
    $("send").disabled = false;
    renderDock();
  }
  $("send").onclick = generate;

  $("btnAdd").onclick = () => {
    const n = shots().length;
    const id = uid("shot");
    state.nodes.push({
      id: id, kind: "shot", title: "分镜" + (n + 1),
      x: 560 + (n % 2) * 720, y: 80 + Math.floor(n / 2) * 430,
      url: "", firstFrameId: "",
      prompt: "【镜头" + (n + 1) + "】\n场景：\n画面：\n运镜：固定镜头。",
    });
    selectNode(id); persist();
  };
  $("btnAuto").onclick = () => {
    assets().forEach((n, i) => { n.x = 220; n.y = 24 + i * 236; });
    shots().forEach((n, i) => { n.x = 560 + (i % 2) * 720; n.y = 80 + Math.floor(i / 2) * 430; });
    renderCards(); drawWires(); persist();
  };
  $("btnFit").onclick = () => {
    state.cam = { x: 90, y: 36, s: 0.3 }; applyCam(); persist();
  };
  $("zIn").onclick = () => { state.cam.s = Math.min(1.5, state.cam.s * 1.12); applyCam(); persist(); };
  $("zOut").onclick = () => { state.cam.s = Math.max(0.16, state.cam.s * 0.9); applyCam(); persist(); };

  async function loadCatalog() {
    $("service").innerHTML = '<option value="">默认模型</option>';
    try {
      const r = await fetch("/api/catalog?backend=" + encodeURIComponent($("backend").value));
      const j = await r.json();
      (j.items || j.models || []).slice(0, 60).forEach((it) => {
        const id = it.id || it.name || "";
        const o = document.createElement("option");
        o.value = id; o.textContent = it.name || id;
        $("service").appendChild(o);
      });
      if (state._pendingService) {
        $("service").value = state._pendingService;
        state._pendingService = "";
      }
    } catch (_) {}
  }
  async function loadOuts() {
    try {
      const r = await fetch("/api/outs");
      const j = await r.json();
      const items = (j.items || []).filter((it) => it.kind === "image" || (it.url && !isVideoUrl(it.url)));
      state.history = items.slice(0, 24).map((it) => ({
        url: it.url || it.path,
        title: String(it.file || it.name || "历史成片").replace(/\.[^.]+$/, ""),
      })).filter((it) => it.url);
      renderRail();
    } catch (_) {}
  }
  $("backend").onchange = loadCatalog;

  if (!restore()) loadDemo();
  applyCam();
  renderCards();
  drawWires();
  loadCatalog();
  loadOuts();
  selectNode(state.selected || "shot-1");
})();
