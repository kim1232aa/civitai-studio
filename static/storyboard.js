(() => {
  const $ = (id) => document.getElementById(id);
  const STORE = "nl-storyboard-v0794";
  const STORE_OLD = "nl-storyboard-v0793";
  const STALE_SHARED_DEMO =
    "/out/fal_fal-ai_flux_schnell_01a05be2-19bd-75e1-8053-0a6f8de59915_0.jpg";
  const vp = $("viewport");
  const world = $("world");
  const wires = $("wires");
  const dock = $("dock");

  const state = {
    cam: { x: 90, y: 36, s: 0.3 },
    nodes: [],
    edges: [],
    selected: null,
    selectedEdge: null,
    drag: null,
    pan: null,
    link: null,
    railDrag: null,
    mode: "image",
    catalog: [],
    history: [],
    railTab: "assets",
    atFilter: "",
    _atTarget: null,
    _pendingService: "",
    capabilities: [],
    catalogItems: [],
    catalogById: {},
    _capabilitiesPromise: null,
    _catalogSeq: 0,
  };

  function uid(prefix) {
    return prefix + "-" + Math.random().toString(36).slice(2, 8);
  }
  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&" + "amp;")
      .replace(/</g, "&" + "lt;")
      .replace(/"/g, "&" + "quot;");
  }
  function isVideoUrl(u) {
    return /\.(mp4|webm|mov)(\?|$)/i.test(u || "");
  }
  function isImageSource(n) {
    return !!(n && n.url && !isVideoUrl(n.url));
  }
  function nodeById(id) {
    return state.nodes.find((n) => n.id === id);
  }
  function box(n) {
    if (n.kind === "shot") return { w: 640, h: 360 };
    if (n.kind === "text") return { w: 320, h: 280 };
    return { w: 132, h: 208 };
  }
  function assets() {
    return state.nodes.filter((n) => n.kind !== "shot" && n.kind !== "text");
  }
  function shots() {
    return state.nodes.filter((n) => n.kind === "shot");
  }
  function connectedNodes(id) {
    return state.edges
      .filter((e) => e.to === id)
      .map((e) => nodeById(e.from))
      .filter(Boolean);
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
  function promptOf(node) {
    if (!node) return "";
    return node.kind === "text" ? node.text || "" : node.prompt || "";
  }

  function describePrompt(asset, caption) {
    if (!asset || !asset.url) return "";
    return String(caption || "")
      .split("\n")
      .map((part) => part.trim())
      .filter(Boolean)
      .join("\n");
  }

  async function captionFromAsset(asset) {
    if (!asset || !asset.url) return "";
    try {
      const r = await fetch("/api/caption", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: asset.url }),
      });
      if (r.ok) {
        const j = await r.json();
        const cap = j && (j.caption || j.text || j.prompt);
        if (cap) return String(cap);
      }
    } catch (_) {}
    try {
      const sidecar = asset.url.replace(/\.[a-zA-Z0-9]+(\?|$)/, ".json$1");
      if (sidecar !== asset.url) {
        const r2 = await fetch(sidecar);
        if (r2.ok) {
          const j2 = await r2.json();
          const cap2 = j2 && (j2.caption || j2.text || j2.prompt);
          if (cap2) return String(cap2);
        }
      }
    } catch (_) {}
    return "";
  }

  async function reverseFromImage(asset) {
    if (!asset || !asset.url) return null;
    let node = state.nodes.find(
      (n) =>
        n.kind === "text" &&
        state.edges.some((e) => e.from === asset.id && e.to === n.id),
    );
    const userCaption = node ? String(node.text || "").trim() : "";
    let visualCaption = "";
    try {
      visualCaption = await captionFromAsset(asset);
    } catch (_) {
      visualCaption = "";
    }
    const text = describePrompt(
      asset,
      [userCaption, visualCaption].filter(Boolean).join("\n"),
    );
    if (!text) {
      setMsg("未能从真实资产取得描述，请先填写提示词", "warn");
      return null;
    }
    if (node) {
      node.text = text;
    } else {
      node = {
        id: uid("text"),
        kind: "text",
        title: "反推·" + sourceTitle(asset),
        x: asset.x + 220,
        y: asset.y,
        text: text,
      };
      state.nodes.push(node);
      state.edges.push({ from: asset.id, to: node.id });
    }
    selectNode(node.id);
    renderCards();
    drawWires();
    renderDock();
    persist();
    return node;
  }

  async function generateFromText(node) {
    if (!node || node.kind !== "text") return;
    let shot = shots().find((s) =>
      state.edges.some((e) => e.from === node.id && e.to === s.id),
    );
    if (!shot) {
      const i = shots().length;
      shot = {
        id: uid("shot"),
        kind: "shot",
        title: "分镜" + (i + 1),
        x: node.x + 420,
        y: node.y,
        url: "",
        firstFrameId: "",
        prompt: "",
      };
      state.nodes.push(shot);
      state.edges.push({ from: node.id, to: shot.id });
    }
    shot.prompt = node.text || "";
    connectedNodes(node.id)
      .filter(isImageSource)
      .forEach((img) => {
        if (!state.edges.some((e) => e.from === img.id && e.to === shot.id)) {
          state.edges.push({ from: img.id, to: shot.id });
        }
        if (!shot.firstFrameId) shot.firstFrameId = img.id;
      });
    // Blank shots classify as text; keep this path on the image catalog.
    // Do not selectNode() here — applySelectionDefaults would flip mode back.
    // loadCatalog wrapper no-ops while story is on; drop it before fetching image models.
    toolUi.story = false;
    state.mode = "image";
    state.selected = shot.id;
    if (toolUi.prevBackend && $("backend")) {
      $("backend").value = toolUi.prevBackend;
      toolUi.prevBackend = "";
    }
    renderCards();
    drawWires();
    persist();
    await loadCatalog();
    if (!$("service") || !$("service").value) {
      setMsg("生图必须显式选择图片模型，不会用默认假值", "bad");
      renderDock();
      return;
    }
    await generate();
  }

  function persist() {
    try {
      localStorage.setItem(
        STORE,
        JSON.stringify({
          cam: state.cam,
          nodes: state.nodes,
          edges: state.edges,
          mode: state.mode,
          railTab: state.railTab,
          backend: $("backend") && $("backend").value,
          service: $("service") && $("service").value,
          duration: $("duration") && $("duration").value,
          aspect: $("aspect") && $("aspect").value,
          res: $("res") && $("res").value,
        }),
      );
    } catch (_) {}
  }
  function restore() {
    try {
      const raw =
        localStorage.getItem(STORE) ||
        sessionStorage.getItem(STORE) ||
        localStorage.getItem(STORE_OLD) ||
        sessionStorage.getItem(STORE_OLD) ||
        "null";
      const p = JSON.parse(raw);
      if (!p || !p.nodes || !p.nodes.length) return false;
      if (
        p.nodes.some((n) => {
          const url = String((n && n.url) || "");
          return url === STALE_SHARED_DEMO || url.startsWith("/static/demo-");
        })
      )
        return false;
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
    } catch (_) {
      return false;
    }
  }

  function applyCam() {
    world.style.transform =
      "translate(" +
      state.cam.x +
      "px," +
      state.cam.y +
      "px) scale(" +
      state.cam.s +
      ")";
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
    return (
      "M " +
      x1 +
      " " +
      y1 +
      " C " +
      (x1 + dx) +
      " " +
      y1 +
      " " +
      (x2 - dx) +
      " " +
      y2 +
      " " +
      x2 +
      " " +
      y2
    );
  }
  function portPos(n, side) {
    const b = box(n);
    const y = n.y + b.h / 2;
    return side === "out" ? { x: n.x + b.w, y: y } : { x: n.x, y: y };
  }
  function drawWires() {
    const parts = ["<defs></defs>"];
    state.edges.forEach((e) => {
      const a = nodeById(e.from),
        b = nodeById(e.to);
      if (!a || !b) return;
      const p1 = portPos(a, "out"),
        p2 = portPos(b, "in"),
        d = bezier(p1.x, p1.y, p2.x, p2.y),
        selected =
          state.selectedEdge &&
          state.selectedEdge.from === e.from &&
          state.selectedEdge.to === e.to;
      parts.push(
        '<path class="wire-hit" data-edge-from="' +
          esc(e.from) +
          '" data-edge-to="' +
          esc(e.to) +
          '" d="' +
          d +
          '" />',
        '<path class="wire-line' +
          (selected ? " sel" : "") +
          '" data-edge-from="' +
          esc(e.from) +
          '" data-edge-to="' +
          esc(e.to) +
          '" d="' +
          d +
          '" />',
      );
    });
    if (state.link && state.link.x2 != null) {
      parts.push(
        '<path d="' +
          bezier(state.link.x1, state.link.y1, state.link.x2, state.link.y2) +
          '" style="opacity:1;stroke:#fff" />',
      );
    }
    wires.innerHTML = parts.join("");
    const maxX = Math.max(
      2400,
      ...state.nodes.map((n) => n.x + box(n).w + 400),
    );
    const maxY = Math.max(
      2400,
      ...state.nodes.map((n) => n.y + box(n).h + 400),
    );
    wires.setAttribute("width", String(maxX));
    wires.setAttribute("height", String(maxY));
  }

  function cardHTML(n) {
    const sel = state.selected === n.id ? " sel" : "";
    if (n.kind === "text") {
      return (
        '<div class="card text' +
        sel +
        '" data-id="' +
        esc(n.id) +
        '" style="left:' +
        n.x +
        "px;top:" +
        n.y +
        'px">' +
        '<div class="label">✎ ' +
        esc(n.title || "提示词") +
        "</div>" +
        '<textarea class="editor" data-text data-id="' +
        esc(n.id) +
        '" placeholder="反推或手写提示词…">' +
        esc(n.text || "") +
        "</textarea>" +
        '<div class="acts">' +
        '<button type="button" data-textact="rev" data-id="' +
        esc(n.id) +
        '">反推</button>' +
        '<button type="button" data-textact="gen" data-id="' +
        esc(n.id) +
        '">生图</button>' +
        "</div>" +
        '<button class="port in" data-side="in" type="button">+</button>' +
        '<button class="port out" data-side="out" type="button">+</button></div>'
      );
    }
    if (n.kind === "shot") {
      const media = n.url
        ? isVideoUrl(n.url)
          ? '<video src="' + esc(n.url) + '" muted></video>'
          : '<img src="' + esc(n.url) + '" alt="">'
        : '<div class="face"><div style="font-size:22px">▢</div><div class="hint">点击查看或编辑提示词</div></div>';
      return (
        '<div class="card shot' +
        sel +
        '" data-id="' +
        esc(n.id) +
        '" style="left:' +
        n.x +
        "px;top:" +
        n.y +
        'px">' +
        '<div class="label">▢ ' +
        esc(n.title) +
        "</div>" +
        '<div class="face">' +
        media +
        "</div>" +
        '<button class="port in" data-side="in" type="button">+</button>' +
        '<button class="port out" data-side="out" type="button">+</button></div>'
      );
    }
    const thumb = n.url
      ? '<img class="thumb" src="' + esc(n.url) + '" alt="">'
      : '<div class="ph">▣</div>';
    return (
      '<div class="card asset' +
      sel +
      '" data-id="' +
      esc(n.id) +
      '" style="left:' +
      n.x +
      "px;top:" +
      n.y +
      'px">' +
      thumb +
      '<div class="name">' +
      esc(n.title) +
      "</div>" +
      '<button class="port out" data-side="out" type="button">+</button></div>'
    );
  }
  function renderCards() {
    world.querySelectorAll(".card").forEach((el) => el.remove());
    state.nodes.forEach((n) =>
      world.insertAdjacentHTML("beforeend", cardHTML(n)),
    );
  }
  function moveCardEl(n) {
    const el = world.querySelector('.card[data-id="' + n.id + '"]');
    if (el) {
      el.style.left = n.x + "px";
      el.style.top = n.y + "px";
    }
  }
  function markSelected(id) {
    world
      .querySelectorAll(".card.sel")
      .forEach((el) => el.classList.remove("sel"));
    const el = world.querySelector('.card[data-id="' + id + '"]');
    if (el) el.classList.add("sel");
  }

  function renderRail() {
    const rail = $("assetRail");
    if (!rail) return;
    const shot = nodeById(state.selected);
    const canPin = shot && shot.kind === "shot";
    const tabAssets = state.railTab !== "history";
    const tabs =
      '<div class="rail-tabs">' +
      '<button type="button" data-tab="assets"' +
      (tabAssets ? ' class="on"' : "") +
      ">资产</button>" +
      '<button type="button" data-tab="history"' +
      (tabAssets ? "" : ' class="on"') +
      ">历史</button></div>";
    let body;
    if (tabAssets) {
      const list = assets();
      body =
        '<div class="rail-h">画布资产 · 可拖出</div>' +
        list
          .map((a) => {
            const on = state.selected === a.id ? " on" : "";
            return (
              '<div class="rail-item' +
              on +
              '" data-rail="' +
              esc(a.id) +
              '">' +
              (a.url ? '<img src="' + esc(a.url) + '" alt="">' : "") +
              "<span>" +
              esc(a.title) +
              "</span>" +
              (canPin
                ? '<button class="pin" type="button" data-pin="' +
                  esc(a.id) +
                  '" title="接到此镜">＋</button>'
                : "") +
              "</div>"
            );
          })
          .join("") +
        '<button class="rail-item add" type="button" data-act="upload">+ 上传</button>';
    } else {
      const list = state.history;
      body =
        '<div class="rail-h">生成历史 · 拖到画布</div>' +
        (list.length
          ? list
              .map((it, i) => {
                return (
                  '<div class="rail-item" data-hist="' +
                  i +
                  '">' +
                  (it.url ? '<img src="' + esc(it.url) + '" alt="">' : "") +
                  "<span>" +
                  esc(it.title) +
                  "</span>" +
                  (canPin
                    ? '<button class="pin" type="button" data-hist-pin="' +
                      i +
                      '" title="接到此镜">＋</button>'
                    : "") +
                  "</div>"
                );
              })
              .join("")
          : "<div class='rail-h'>还没有成片</div>");
    }
    rail.innerHTML = tabs + body;
  }

  function renderDock() {
    const n = nodeById(state.selected);
    if (!n || (n.kind !== "shot" && n.kind !== "text")) {
      dock.classList.remove("show");
      renderRail();
      return;
    }
    dock.classList.add("show");
    $("prompt").value = promptOf(n);
    if ($("modeTxt"))
      $("modeTxt").classList.toggle(
        "on",
        n.kind === "text" || state.mode === "text",
      );
    $("modeVid").classList.toggle(
      "on",
      n.kind === "shot" && state.mode === "video",
    );
    $("modeImg").classList.toggle(
      "on",
      n.kind === "shot" && state.mode === "image",
    );
    syncSamplerChrome(n);
    syncParamChrome(n);
    if (n.kind === "text") {
      if ($("send")) $("send").disabled = false;
      setTextDockRefs(n);
      renderRail();
      return;
    }
    const list = assets();
    const linked = connectedAssets(n.id);
    const frame = frameAsset(n);
    const needFrame = state.mode === "video" && !frame;
    if ($("send")) $("send").disabled = needFrame;
    let frameHtml = "";
    if (state.mode === "video") {
      if (frame) {
        frameHtml =
          '<div class="frame-slot">首帧 <img src="' +
          esc(frame.url) +
          '" alt="">' +
          esc(sourceTitle(frame)) +
          linked
            .filter((a) => a.url && a.id !== frame.id)
            .map((a) => {
              return (
                '<button class="frame-chip" type="button" data-frame="' +
                esc(a.id) +
                '" title="设为首帧">' +
                (a.url ? '<img src="' + esc(a.url) + '" alt="">' : "") +
                esc(sourceTitle(a)) +
                "</button>"
              );
            })
            .join("") +
          "</div>";
      } else {
        frameHtml =
          '<div class="frame-slot missing">视频需要先连一张首帧图</div>';
      }
    }
    const promoteBtn =
      n.url && !isVideoUrl(n.url)
        ? '<button class="chip-btn" type="button" data-act="promote" title="收进资产库">入库</button>'
        : "";
    $("refs").innerHTML =
      frameHtml +
      '<button class="chip-btn" type="button" data-act="upload">上传</button>' +
      '<button class="chip-btn" type="button" data-act="pick">选择</button>' +
      promoteBtn +
      linked
        .concat(list.filter((a) => !linked.includes(a)))
        .slice(0, 8)
        .map((a) => {
          const on = linked.some((x) => x.id === a.id) ? " on" : "";
          return (
            '<button class="chip' +
            on +
            '" type="button" data-asset="' +
            esc(a.id) +
            '" title="' +
            esc(sourceTitle(a)) +
            '">' +
            (a.url
              ? '<img src="' + esc(a.url) + '" alt="">'
              : esc(sourceTitle(a).slice(0, 2))) +
            "</button>"
          );
        })
        .join("");
    renderRail();
  }

  function setTextDockRefs(n) {
    const linked = connectedNodes(n.id).filter(isImageSource);
    const list = assets();
    $("refs").innerHTML =
      '<button class="chip-btn" type="button" data-act="upload">上传</button>' +
      '<button class="chip-btn" type="button" data-act="pick">选择</button>' +
      linked
        .concat(list.filter((a) => !linked.includes(a)))
        .slice(0, 8)
        .map((a) => {
          const on = linked.some((x) => x.id === a.id) ? " on" : "";
          return (
            '<button class="chip' +
            on +
            '" type="button" data-asset="' +
            esc(a.id) +
            '" title="' +
            esc(sourceTitle(a)) +
            '">' +
            (a.url
              ? '<img src="' + esc(a.url) + '" alt="">'
              : esc(sourceTitle(a).slice(0, 2))) +
            "</button>"
          );
        })
        .join("");
  }

  function selectNode(id) {
    state.selected = id;
    state.selectedEdge = null;
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
      if (wx >= n.x && wx <= n.x + b.w && wy >= n.y && wy <= n.y + b.h)
        return n;
    }
    return null;
  }

  function syncPrompt(node, value, sourceEl) {
    if (!node) return;
    if (node.kind === "text") node.text = value;
    else node.prompt = value;
    if (state.selected === node.id) {
      const dockTa = $("prompt");
      if (dockTa && dockTa !== sourceEl) dockTa.value = value;
      const cardTa = world.querySelector(
        'textarea[data-text][data-id="' + node.id + '"]',
      );
      if (cardTa && cardTa !== sourceEl) cardTa.value = value;
    }
    persist();
  }

  function mention(asset, target) {
    target = target || nodeById(state.selected);
    if (!target || (target.kind !== "shot" && target.kind !== "text")) return;
    const tag = "@" + sourceTitle(asset);
    const cur = promptOf(target);
    if (!cur.includes(tag)) syncPrompt(target, (cur ? cur + " " : "") + tag);
  }
  function unmention(asset, target) {
    if (!target) return;
    const tag = "@" + sourceTitle(asset);
    const cur = promptOf(target);
    if (cur.includes(tag)) {
      const next = cur
        .split(tag)
        .join("")
        .replace(/[ \t]{2,}/g, " ")
        .replace(/\n{3,}/g, "\n\n");
      syncPrompt(target, next);
    }
  }
  function linkAssetToShot(asset, shot) {
    if (!asset || !shot || shot.kind !== "shot" || asset.id === shot.id) return;
    if (asset.kind === "shot" && !isImageSource(asset)) return;
    if (!state.edges.some((e) => e.from === asset.id && e.to === shot.id)) {
      state.edges.push({ from: asset.id, to: shot.id });
    }
    if (asset.kind === "text") {
      syncPrompt(shot, asset.text || "");
    } else {
      mention(asset, shot);
      if (shot && !shot.firstFrameId && isImageSource(asset))
        shot.firstFrameId = asset.id;
    }
  }
  function unlinkAssetFromShot(asset, shot) {
    if (!asset || !shot) return;
    state.edges = state.edges.filter(
      (e) => !(e.from === asset.id && e.to === shot.id),
    );
    unmention(asset, shot);
    if (shot && shot.firstFrameId === asset.id) shot.firstFrameId = "";
  }
  function toggleAssetOnShot(asset, shot) {
    if (!asset || !shot || shot.kind !== "shot") return;
    if (state.edges.some((e) => e.from === asset.id && e.to === shot.id))
      unlinkAssetFromShot(asset, shot);
    else linkAssetToShot(asset, shot);
  }
  function toggleAssetOnText(asset, text) {
    if (!asset || !text || text.kind !== "text" || !isImageSource(asset))
      return;
    if (state.edges.some((e) => e.from === asset.id && e.to === text.id)) {
      state.edges = state.edges.filter(
        (e) => !(e.from === asset.id && e.to === text.id),
      );
      unmention(asset, text);
    } else {
      state.edges.push({ from: asset.id, to: text.id });
      mention(asset, text);
    }
  }

  function promoteResult(shot, url) {
    if (!shot || !url || isVideoUrl(url)) return null;
    const aid = "out-" + shot.id;
    let asset = nodeById(aid) || assets().find((a) => a.url === url);
    if (asset) {
      asset.url = url;
      asset.title = (shot.title || "分镜") + "成片";
      asset.fromShot = shot.id;
    } else {
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
    }
    return asset;
  }

  function spawnHistoryAt(item, x, y) {
    if (!item || !item.url) return null;
    const existing = assets().find((a) => a.url === item.url);
    if (existing) {
      if (x != null) {
        existing.x = x;
        existing.y = y;
      }
      return existing;
    }
    const node = {
      id: uid("hist"),
      kind: "character",
      title: item.title || "历史成片",
      x: x == null ? 220 : x,
      y: y == null ? 24 + assets().length * 40 : y,
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
      if (text.indexOf(tag) >= 0)
        text = text.split(tag).join("@图片" + (i + 1));
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
    const list = pool.filter(
      (a) => !q || sourceTitle(a).toLowerCase().indexOf(q) >= 0,
    );
    box.innerHTML =
      list
        .map(
          (a) =>
            '<button type="button" data-at="' +
            esc(a.id) +
            '">' +
            (a.url ? '<img src="' + esc(a.url) + '" alt="">' : "") +
            esc(sourceTitle(a)) +
            "</button>",
        )
        .join("") || "<div style='color:#888;padding:8px'>没有匹配的资产</div>";
    box.classList.add("show");
  }

  function handlePromptInput(ta, node) {
    if (node) syncPrompt(node, ta.value, ta);
    const v = ta.value || "";
    const caret = ta.selectionStart == null ? v.length : ta.selectionStart;
    const before = v.slice(0, caret);
    const at = before.lastIndexOf("@");
    if (at >= 0 && !/[\s\n]/.test(before.slice(at + 1))) {
      state._atTarget = ta;
      showAtbox(before.slice(at + 1));
    } else hideAtbox();
  }

  function insertMention(asset) {
    const target = nodeById(state.selected);
    if (!target || (target.kind !== "shot" && target.kind !== "text")) return;
    const ta = state._atTarget || $("prompt");
    const tag = "@" + sourceTitle(asset);
    if (ta) {
      const v = ta.value || "";
      const caret = ta.selectionStart == null ? v.length : ta.selectionStart;
      const before = v.slice(0, caret);
      const at = before.lastIndexOf("@");
      let next;
      if (at >= 0 && !/[\s\n]/.test(before.slice(at + 1))) {
        next = v.slice(0, at) + tag + " " + v.slice(caret);
      } else if (v.indexOf(tag) < 0) {
        next = (v ? v + " " : "") + tag;
      } else next = v;
      ta.value = next;
      syncPrompt(target, next, ta);
    }
    if (target.kind === "shot") {
      linkAssetToShot(asset, target);
    } else if (
      isImageSource(asset) &&
      !state.edges.some((e) => e.from === asset.id && e.to === target.id)
    ) {
      state.edges.push({ from: asset.id, to: target.id });
    }
    hideAtbox();
    state._atTarget = null;
    drawWires();
    renderDock();
    persist();
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
    if (g) {
      g.classList.remove("show");
      g.innerHTML = "";
    }
  }
  function showGhost(url, cx, cy) {
    const g = $("ghost");
    if (!g) return;
    g.innerHTML = url ? '<img src="' + esc(url) + '" alt="">' : "";
    g.style.left = cx - 36 + "px";
    g.style.top = cy - 36 + "px";
    g.classList.add("show");
  }

  vp.addEventListener("pointerdown", (e) => {
    if (e.button === 2) return;
    if (
      e.target.closest(".dock,.tools,.zoom,.picker,.rail,.atbox,header,.ghost")
    )
      return;
    const edge = e.target.closest(".wire-hit[data-edge-from][data-edge-to]");
    if (edge) {
      e.preventDefault();
      e.stopPropagation();
      selectEdge(edge.dataset.edgeFrom, edge.dataset.edgeTo);
      return;
    }
    const port = e.target.closest(".port");
    const card = e.target.closest(".card");
    if (port && card) {
      const n = nodeById(card.dataset.id);
      const p = portPos(n, port.dataset.side === "in" ? "in" : "out");
      state.link = {
        from: n.id,
        side: port.dataset.side,
        x1: p.x,
        y1: p.y,
        x2: p.x,
        y2: p.y,
      };
      vp.setPointerCapture(e.pointerId);
      return;
    }
    if (e.target.closest("textarea[data-text],.text .acts")) {
      if (card) {
        const id = card.dataset.id;
        if (state.selected !== id) {
          state.selected = id;
          markSelected(id);
          drawWires();
          renderDock();
        }
      }
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
      state.link.x2 = w.x;
      state.link.y2 = w.y;
      drawWires();
      return;
    }
    if (state.drag) {
      const w = clientToWorld(e.clientX, e.clientY);
      const n = nodeById(state.drag.id);
      n.x = w.x - state.drag.dx;
      n.y = w.y - state.drag.dy;
      moveCardEl(n);
      drawWires();
      return;
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
        let dst = null,
          src = null;
        if (target.kind === "shot" && a.kind !== "shot") {
          dst = target;
          src = a;
        } else if (a.kind === "shot" && target.kind !== "shot") {
          dst = a;
          src = target;
        } else if (target.kind === "text" && isImageSource(a)) {
          dst = target;
          src = a;
        } else if (a.kind === "text" && isImageSource(target)) {
          dst = a;
          src = target;
        }
        if (
          dst &&
          src &&
          src.id !== dst.id &&
          (src.kind !== "shot" || isImageSource(src))
        ) {
          if (dst.kind === "shot") {
            linkAssetToShot(src, dst);
          } else if (
            !state.edges.some((e2) => e2.from === src.id && e2.to === dst.id)
          ) {
            state.edges.push({ from: src.id, to: dst.id });
          }
          selectNode(dst.id);
        }
      }
      state.link = null;
      drawWires();
      persist();
    }
    if (state.drag) {
      renderCards();
      persist();
    }
    state.drag = null;
    state.pan = null;
    vp.classList.remove("grabbing");
  });
  vp.addEventListener(
    "wheel",
    (e) => {
      e.preventDefault();
      const w0 = clientToWorld(e.clientX, e.clientY);
      const next = Math.min(
        1.5,
        Math.max(0.16, state.cam.s * (e.deltaY > 0 ? 0.92 : 1.08)),
      );
      const r = vp.getBoundingClientRect();
      state.cam.s = next;
      state.cam.x = e.clientX - r.left - w0.x * next;
      state.cam.y = e.clientY - r.top - w0.y * next;
      applyCam();
      persist();
    },
    { passive: false },
  );

  world.addEventListener("input", (e) => {
    const ta = e.target.closest("textarea[data-text]");
    if (!ta) return;
    handlePromptInput(ta, nodeById(ta.dataset.id));
  });
  world.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-textact]");
    if (!btn) return;
    const n = nodeById(btn.dataset.id);
    if (!n) return;
    if (btn.dataset.textact === "gen") generateFromText(n);
    else if (btn.dataset.textact === "rev") {
      const src = connectedNodes(n.id).find(isImageSource);
      if (src) {
        setMsg("正在反推…");
        reverseFromImage(src).then(() =>
          setMsg("反推完成，提示词已更新", "ok"),
        );
      } else setMsg("这张提示词卡还没连图片", "warn");
    }
  });

  $("refs").addEventListener("click", (e) => {
    const frameBtn = e.target.closest("[data-frame]");
    if (frameBtn) {
      const shot = nodeById(state.selected);
      if (shot && shot.kind === "shot") {
        shot.firstFrameId = frameBtn.dataset.frame;
        renderDock();
        persist();
      }
      return;
    }
    const assetBtn = e.target.closest("[data-asset]");
    if (assetBtn) {
      const asset = nodeById(assetBtn.dataset.asset);
      const target = nodeById(state.selected);
      if (asset && target) {
        if (target.kind === "shot") toggleAssetOnShot(asset, target);
        else if (target.kind === "text") toggleAssetOnText(asset, target);
        renderCards();
        drawWires();
        renderDock();
        persist();
      }
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
        if (asset) {
          selectNode(asset.id);
          persist();
          setMsg("已收进资产库，可拖到下一镜", "ok");
        }
      }
    }
    if (act.dataset.act === "gen-text") {
      const n = nodeById(state.selected);
      if (n) generateFromText(n);
    }
    if (act.dataset.act === "rev-text") {
      const n = nodeById(state.selected);
      const src = n && connectedNodes(n.id).find(isImageSource);
      if (src) {
        setMsg("正在反推…");
        reverseFromImage(src).then(() =>
          setMsg("反推完成，提示词已更新", "ok"),
        );
      } else setMsg("这张提示词卡还没连图片", "warn");
    }
  });

  function dropRailOnCanvas(payload, cx, cy) {
    const w = clientToWorld(cx, cy);
    const hit = hitNode(w.x, w.y);
    let node = payload.node || null;
    if (!node && payload.item)
      node = spawnHistoryAt(payload.item, w.x - 66, w.y - 40);
    if (node && (!hit || (hit.kind !== "shot" && hit.kind !== "text"))) {
      node.x = w.x - 66;
      node.y = w.y - 40;
    }
    if (node && hit && hit.kind === "shot") {
      linkAssetToShot(node, hit);
      selectNode(hit.id);
    } else if (node && hit && hit.kind === "text" && isImageSource(node)) {
      if (!state.edges.some((e) => e.from === node.id && e.to === hit.id)) {
        state.edges.push({ from: node.id, to: hit.id });
      }
      selectNode(hit.id);
    } else if (node) {
      selectNode(node.id);
    }
    renderCards();
    drawWires();
    renderDock();
    persist();
  }

  if ($("assetRail")) {
    $("assetRail").addEventListener("pointerdown", (e) => {
      if (e.target.closest("[data-act],[data-tab],[data-pin],[data-hist-pin]"))
        return;
      const railBtn = e.target.closest("[data-rail]");
      const histBtn = e.target.closest("[data-hist]");
      if (railBtn) {
        const asset = nodeById(railBtn.dataset.rail);
        if (!asset) return;
        state.railDrag = {
          kind: "asset",
          id: asset.id,
          url: asset.url,
          title: asset.title,
          x: e.clientX,
          y: e.clientY,
          moved: false,
        };
        railBtn.setPointerCapture(e.pointerId);
      } else if (histBtn) {
        const item = state.history[Number(histBtn.dataset.hist)];
        if (!item) return;
        state.railDrag = {
          kind: "hist",
          item: item,
          url: item.url,
          title: item.title,
          x: e.clientX,
          y: e.clientY,
          moved: false,
        };
        histBtn.setPointerCapture(e.pointerId);
      }
    });
    $("assetRail").addEventListener("pointermove", (e) => {
      if (!state.railDrag) return;
      const dx = e.clientX - state.railDrag.x,
        dy = e.clientY - state.railDrag.y;
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
            drag.kind === "hist"
              ? { item: drag.item }
              : { node: nodeById(drag.id) },
            e.clientX,
            e.clientY,
          );
        }
        return;
      }
      if (drag.kind === "asset") {
        const asset = nodeById(drag.id);
        if (asset) {
          selectNode(asset.id);
          panTo(asset);
          persist();
        }
      } else if (drag.kind === "hist" && drag.item) {
        const node = spawnHistoryAt(drag.item);
        if (node) {
          selectNode(node.id);
          panTo(node);
          persist();
        }
      }
    });
    $("assetRail").addEventListener("click", (e) => {
      const tab = e.target.closest("[data-tab]");
      if (tab) {
        state.railTab = tab.dataset.tab;
        renderRail();
        persist();
        return;
      }
      const up = e.target.closest("[data-act]");
      if (up && up.dataset.act === "upload") {
        $("file").click();
        return;
      }
      const pin = e.target.closest("[data-pin]");
      if (pin) {
        const asset = nodeById(pin.dataset.pin);
        const shot = nodeById(state.selected);
        if (asset && shot && shot.kind === "shot") {
          toggleAssetOnShot(asset, shot);
          renderCards();
          drawWires();
          renderDock();
          persist();
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
          renderCards();
          drawWires();
          renderDock();
          persist();
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
    const node = {
      id: id,
      kind: "character",
      title: f.name.replace(/\.[^.]+$/, ""),
      x: 220,
      y: 24 + n * 40,
      url: url,
    };
    state.nodes.push(node);
    const shot = nodeById(state.selected);
    if (shot && shot.kind === "shot") linkAssetToShot(node, shot);
    else selectNode(id);
    renderCards();
    drawWires();
    renderDock();
    persist();
    if (url.indexOf("/out/") === 0) setMsg("已上传到资产库", "ok");
    $("file").value = "";
  });

  function togglePicker() {
    const box = $("picker");
    box.classList.toggle("show");
    hideAtbox();
    const list = assets().concat(shots().filter(isImageSource));
    box.innerHTML =
      list
        .map(
          (a) =>
            '<button type="button" data-asset="' +
            esc(a.id) +
            '">' +
            (a.url ? '<img src="' + esc(a.url) + '" alt="">' : "") +
            esc(sourceTitle(a)) +
            "</button>",
        )
        .join("") || "<div style='color:#888;padding:8px'>还没有资产</div>";
  }
  $("picker").addEventListener("click", (e) => {
    const btn = e.target.closest("[data-asset]");
    if (!btn) return;
    const asset = nodeById(btn.dataset.asset);
    const shot = nodeById(state.selected);
    if (asset && shot) toggleAssetOnShot(asset, shot);
    $("picker").classList.remove("show");
    renderCards();
    drawWires();
    renderDock();
    persist();
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
    handlePromptInput($("prompt"), nodeById(state.selected));
  });
  $("modeImg").onclick = () => {
    state.mode = "image";
    if (toolUi.prevBackend && $("backend")) {
      $("backend").value = toolUi.prevBackend;
      toolUi.prevBackend = "";
    }
    resetScopedMsg();
    renderDock();
    loadCatalog();
    persist();
  };
  $("modeVid").onclick = () => {
    state.mode = "video";
    if (toolUi.prevBackend && $("backend")) {
      $("backend").value = toolUi.prevBackend;
      toolUi.prevBackend = "";
    }
    resetScopedMsg();
    renderDock();
    loadCatalog();
    persist();
  };
  if ($("modeTxt"))
    $("modeTxt").onclick = () => {
      state.mode = "text";
      if ($("backend") && $("backend").value !== "nano-gpt") {
        if (!toolUi.prevBackend) toolUi.prevBackend = $("backend").value;
        $("backend").value = "nano-gpt";
      }
      resetScopedMsg();
      renderDock();
      loadCatalog();
      persist();
    };
  ["backend", "service", "duration", "aspect", "res"].forEach((id) => {
    if ($(id)) $(id).addEventListener("change", persist);
  });

  function setMsg(t, cls, source) {
    if (!$("msg")) return;
    const el = $("msg");
    el.textContent = t || "";
    el.className = "msg" + (cls ? " " + cls : "");
    el.dataset.source = source || (t ? "general" : "");
  }
  function clearMsgFrom(source) {
    const el = $("msg");
    if (el && el.dataset.source === source) setMsg("");
  }
  function resetScopedMsg() {
    const el = $("msg");
    if (!el) return;
    if (el.textContent || el.dataset.source) setMsg("");
  }

  // ===== A2: sampler/scheduler 画布接线（值源 /api/defaults，禁手抄；仅 civitai 图片生图可见/随请求）=====
  // B 线 storyboard.html 提供 <span id="samplerChrome" hidden> 内两下拉（id=sampler/scheduler）。
  // 控件不在时全部 no-op（防批未合批的中间态）；enrich/buildGraph 的 key 只在真值下透传，
  // graph_compile 白名单对缺席 key 不发明默认（grok bdb0a87 已验）。
  function samplerEnabled(n) {
    if (!n || n.kind !== "shot") return false;
    const backend = $("backend");
    if (!backend || backend.value !== "civitai") return false;
    return state.mode === "image";
  }
  function syncSamplerChrome(n) {
    const wrap = $("samplerChrome");
    if (!wrap) return;
    wrap.hidden = !samplerEnabled(n || nodeById(state.selected));
  }
  function fillSamplerOptions(select, values, wanted) {
    if (!select || !Array.isArray(values) || !values.length) return;
    select.replaceChildren();
    values.forEach((value) => {
      const option = document.createElement("option");
      option.value = String(value);
      option.textContent = String(value);
      select.appendChild(option);
    });
    if (wanted != null && values.indexOf(wanted) >= 0)
      select.value = String(wanted);
  }
  async function loadSamplerDefaults() {
    const sampler = $("sampler");
    const scheduler = $("scheduler");
    if (!sampler || !scheduler) return;
    try {
      const response = await fetch("/api/defaults");
      if (!response.ok) throw new Error("HTTP " + response.status);
      const j = await response.json();
      const defs = (j && j.defaults) || {};
      fillSamplerOptions(sampler, j.samplers || [], defs.sampler);
      fillSamplerOptions(scheduler, j.schedulers || [], defs.scheduler);
    } catch (_) {
      // 拉不到默认参数就禁用并说明，禁死 UI 假装可选。
      [sampler, scheduler].forEach((el) => {
        el.disabled = true;
        el.title = "默认参数加载失败";
      });
    }
  }
  // 仅 civitai 的 t2i/i2i 随请求带所选 sampler/scheduler；其它后端/视频/文本不加 key。
  function samplerGraphParams(op, backend) {
    if (op !== "t2i" && op !== "i2i") return {};
    if (backend !== "civitai") return {};
    const out = {};
    const sampler = $("sampler");
    const scheduler = $("scheduler");
    if (sampler && sampler.value) out.sampler = sampler.value;
    if (scheduler && scheduler.value) out.scheduler = scheduler.value;
    return out;
  }

  // ===== 工作台同款参数上画布：LoRA / 步数 / CFG / 种子 =====
  // 框架照搬 static/index.html 工作台（#loraBlock / #steps / #cfg / #seed / #hits），
  // 不另造机制；能力口径一律取 GET /api/providers[].capabilities（禁前端手抄表）：
  //   lora: air|path|hub_repo|none   loraPath: http|civitai_download|hub_owner_repo|none
  //   seed: {min,max,clamp}
  // compile 对 seed/loras 是 wire-only：seed 走 seed 节点，LoRA 走 lora_apply→loras 端口；
  // params 旁路会被 graph_compile 显式驳回（providers/graph_compile.py:352 / :397）。
  // steps/cfgScale 只在 t2i/i2i 白名单（graph_compile.py:386-387），视频/文本不露出，禁假支持。
  state.loras = [];
  state.providerCaps = {};
  state._providerCapsPromise = null;

  async function loadProviderCaps() {
    if (!state._providerCapsPromise) {
      state._providerCapsPromise = fetch("/api/providers")
        .then((response) => (response.ok ? response.json() : { items: [] }))
        .then((payload) => {
          ((payload && payload.items) || []).forEach((item) => {
            if (item && item.id)
              state.providerCaps[item.id] = item.capabilities || null;
          });
          return state.providerCaps;
        })
        .catch(() => state.providerCaps);
    }
    return state._providerCapsPromise;
  }
  function backendCaps() {
    const el = $("backend");
    return (el && state.providerCaps[el.value]) || null;
  }
  function stepsEnabled(n) {
    return !!n && n.kind === "shot" && state.mode === "image";
  }
  function seedEnabled(n) {
    return !!n && n.kind === "shot" && state.mode !== "text" && !!backendCaps();
  }
  function loraEnabled(n) {
    const caps = backendCaps();
    if (
      !n ||
      n.kind !== "shot" ||
      state.mode === "text" ||
      !caps ||
      caps.lora === "none"
    )
      return false;
    // W2：civitai 模型级门——constraints 未声明 loras 键的模型不支持 LoRA
    return modelAllowsLoRA(selectedCatalogItem());
  }
  function isHttpUrl(value) {
    return /^https?:\/\//i.test(String(value == null ? "" : value));
  }
  function isHubRepo(value) {
    return /^[\w.-]+\/[\w.-]+$/.test(String(value == null ? "" : value).trim());
  }
  // 能力表说什么就收什么；收不了的条目当场说明理由，不静默丢也不塞假值。
  function loraRowUsable(row, caps) {
    if (!caps || !row) return false;
    if (caps.lora === "air") return !!(row.air || row.versionId);
    if (caps.loraPath === "http" || caps.loraPath === "civitai_download")
      return isHttpUrl(row.path);
    if (caps.loraPath === "hub_owner_repo") return isHubRepo(row.path);
    return false;
  }
  function loraModeHint(caps) {
    if (!caps || caps.lora === "none") return "当前后端不支持 LoRA";
    if (caps.lora === "air") return "认名字搜索 / version id / urn:air:…";
    if (caps.loraPath === "http") return "只认 http(s) LoRA 直链";
    if (caps.loraPath === "civitai_download")
      return "只认 civitai 下载直链或 version id（换成直链后带走）";
    if (caps.loraPath === "hub_owner_repo") return "只认 owner/repo 形式的 Hub 仓库";
    return "";
  }
  function clampLoraScale(value) {
    const n = Number(value);
    if (!Number.isFinite(n) || n <= 0) return 0.8;
    return Math.min(3, Math.max(0.05, n));
  }
  function normalizeLoraRow(src) {
    const v = src || {};
    const versionId = String(v.versionId || v.modelVersionId || v.id || "");
    const path = String(v.path || v.downloadUrl || v.url || "");
    const air = String(v.air || "");
    const scale = clampLoraScale(v.scale != null ? v.scale : v.strength);
    return {
      air: air,
      path: path,
      versionId: versionId,
      // 名字口径同工作台 normalizeLora：先模型名再版本名，别把版本号当名字显示。
      name: String(
        (typeof v.model === "string" && v.model) ||
          v.name ||
          air ||
          path ||
          versionId ||
          "LoRA",
      ),
      scale: scale,
      strength: scale,
    };
  }
  function setLoraNote(text, bad) {
    const el = $("loraNote");
    if (!el) return;
    el.textContent = text || loraModeHint(backendCaps());
    el.style.color = bad ? "var(--coral)" : "var(--muted)";
  }
  function renderLoraList() {
    const list = $("loraList");
    if (!list) return;
    list.replaceChildren();
    state.loras.forEach((row, index) => {
      const line = document.createElement("div");
      line.className = "lora-row";
      const name = document.createElement("span");
      name.className = "lora-name";
      name.textContent = row.name;
      name.title = row.air || row.path || row.versionId;
      const weight = document.createElement("input");
      weight.type = "number";
      weight.min = "0.05";
      weight.max = "3";
      weight.step = "0.05";
      weight.value = String(row.scale);
      weight.title = "权重";
      weight.oninput = () => {
        const next = clampLoraScale(weight.value);
        row.scale = next;
        row.strength = next;
      };
      const drop = document.createElement("button");
      drop.type = "button";
      drop.textContent = "×";
      drop.title = "移除";
      drop.onclick = () => {
        state.loras.splice(index, 1);
        renderLoraList();
      };
      line.append(name, weight, drop);
      list.appendChild(line);
    });
    setLoraNote("");
  }
  function addLora(raw) {
    const caps = backendCaps();
    const row = normalizeLoraRow(raw);
    if (!loraRowUsable(row, caps)) {
      setLoraNote("这条在当前后端用不了：" + loraModeHint(caps), true);
      return false;
    }
    const key = row.air || row.path || row.versionId;
    if (
      state.loras.some((it) => (it.air || it.path || it.versionId) === key)
    ) {
      setLoraNote("已经加过这条 LoRA 了", true);
      return false;
    }
    state.loras.push(row);
    renderLoraList();
    return true;
  }
  async function fetchLoraVersion(versionId) {
    const response = await fetch(
      "/api/model-version/" + encodeURIComponent(versionId),
    );
    const payload = await response.json();
    if (!response.ok || payload.error)
      throw new Error(payload.error || "HTTP " + response.status);
    return payload;
  }
  function acceptsVersionId(caps) {
    return !!caps && (caps.lora === "air" || caps.loraPath === "civitai_download");
  }
  async function searchLora() {
    const caps = backendCaps();
    const hits = $("loraHits");
    const box = $("loraQ");
    const q = box ? box.value.trim() : "";
    if (!hits || !q) return;
    if (!caps) {
      setLoraNote("后端能力还没加载出来，先别加 LoRA", true);
      return;
    }
    hits.replaceChildren();
    if (isHttpUrl(q) || (caps.loraPath === "hub_owner_repo" && isHubRepo(q))) {
      addLora({ path: q, name: q });
      return;
    }
    if (/^urn:air:/i.test(q) || q.indexOf(":lora:") >= 0) {
      addLora({ air: q, name: q.split(":").pop() });
      return;
    }
    if (/^\d+$/.test(q) && acceptsVersionId(caps)) {
      hits.textContent = "查 version…";
      try {
        const data = await fetchLoraVersion(q);
        hits.replaceChildren();
        addLora(data);
      } catch (_) {
        hits.textContent = "没找到这个 version id";
      }
      return;
    }
    hits.textContent = "搜…";
    const backend = ($("backend") && $("backend").value) || "";
    try {
      const response = await fetch(
        "/api/search?type=LORA&q=" +
          encodeURIComponent(q) +
          "&backend=" +
          encodeURIComponent(backend),
      );
      const payload = await response.json();
      const rows = (payload && payload.items) || [];
      hits.replaceChildren();
      if (!rows.length) {
        hits.textContent = (payload && payload.note) || "没有结果";
        return;
      }
      rows.forEach((item) => {
        const version = (item.versions || [])[0] || {};
        const line = document.createElement("div");
        line.textContent =
          String(item.name || item.path || version.name || "") +
          (version.baseModel ? " · " + version.baseModel : "");
        line.onclick = () => pickLoraHit(item, version);
        hits.appendChild(line);
      });
    } catch (_) {
      hits.textContent = "搜索失败";
    }
  }
  async function pickLoraHit(item, version) {
    const caps = backendCaps();
    const hits = $("loraHits");
    const path = String((item && item.path) || "");
    if (path && (isHttpUrl(path) || isHubRepo(path))) {
      if (hits) hits.replaceChildren();
      addLora({ path: path, name: item.name || path });
      return;
    }
    if (version && version.id && acceptsVersionId(caps)) {
      try {
        const data = await fetchLoraVersion(version.id);
        if (hits) hits.replaceChildren();
        addLora(data);
      } catch (_) {
        if (hits) hits.textContent = "这条取不到 version 详情";
      }
      return;
    }
    if (hits) hits.replaceChildren();
    addLora(item);
  }
  // 出参形状对齐工作台 buildPayload 的 loras（server/provider 侧已按这套字段吃）。
  function loraPayloadRows() {
    return state.loras.map((row) => ({
      air: row.air,
      path: row.path,
      url: row.path,
      downloadUrl: row.path,
      versionId: row.versionId,
      name: row.name,
      scale: row.scale,
      strength: row.strength,
    }));
  }
  function paramFieldValue(id) {
    const el = $(id);
    if (!el || el.disabled) return null;
    const raw = String(el.value == null ? "" : el.value).trim();
    if (raw === "") return null;
    const value = Number(raw);
    return Number.isFinite(value) ? value : null;
  }
  // steps/cfgScale：只有 t2i/i2i 收，填了才带 key，空着不发明默认。
  function samplingGraphParams(op, shot) {
    if (op !== "t2i" && op !== "i2i") return {};
    if (!stepsEnabled(shot)) return {};
    const out = {};
    const steps = paramFieldValue("steps");
    const cfg = paramFieldValue("cfg");
    if (steps != null) out.steps = steps;
    if (cfg != null) out.cfgScale = cfg;
    return out;
  }
  function seedFieldRaw(shot) {
    if (!seedEnabled(shot)) return "";
    const el = $("seed");
    return el ? String(el.value == null ? "" : el.value).trim() : "";
  }
  // 越界种子直接拦下并说明，不替用户静默取模（clamp=mod 是上游行为，不代表前端可以改数）。
  function seedIssue(shot) {
    const raw = seedFieldRaw(shot || nodeById(state.selected));
    if (!raw) return "";
    if (!/^-?\d+$/.test(raw)) return "种子只认整数，别填别的";
    const rule = effectiveSeedRule(); // W2：模型级 seed 约束优先，其次 provider 级
    const value = Number(raw);
    if (rule.min != null && value < rule.min)
      return "当前选择种子下限 " + rule.min + "，不替你静默改数";
    if (rule.max != null && value > rule.max)
      return "当前选择种子上限 " + rule.max + "，不替你静默取模";
    return "";
  }
  function syncParamChrome(node) {
    const n = node || nodeById(state.selected);
    const paramWrap = $("paramChrome");
    const seedWrap = $("seedChrome");
    const toggle = $("loraToggle");
    const pane = $("loraPane");
    if (paramWrap) paramWrap.hidden = !stepsEnabled(n);
    if (seedWrap) seedWrap.hidden = !seedEnabled(n);
    const seed = $("seed");
    if (seed) {
      const rule = effectiveSeedRule(); // W2：模型级 seed 约束优先，其次 provider 级
      seed.title =
        rule.max == null && rule.min == null
          ? "种子 seed，空则随机"
          : "种子 seed，空则随机（" +
            (rule.min == null ? "" : rule.min) +
            "…" +
            (rule.max == null ? "" : rule.max) +
            "）";
      seed.classList.toggle("bad", !!seedIssue(n));
    }
    if (toggle) toggle.hidden = !loraEnabled(n);
    if (pane && !loraEnabled(n)) {
      pane.hidden = true;
      if (toggle) toggle.classList.remove("on");
    }
    if (pane && !pane.hidden) renderLoraList();
    applyModelParamRules(); // W2：每次 dock 刷新同步模型级参数规则（显隐变化后选项/范围也要对）
  }
  // 换后端＝换能力面：留不住的 LoRA 当场清掉并报数，不装作还带着。
  function pruneLorasForBackend() {
    const caps = backendCaps();
    const before = state.loras.length;
    state.loras = state.loras.filter((row) => loraRowUsable(row, caps));
    const dropped = before - state.loras.length;
    renderLoraList();
    if (dropped)
      setLoraNote(
        "换后端后有 " + dropped + " 条 LoRA 用不了，已移除：" + loraModeHint(caps),
        true,
      );
    return dropped;
  }
  function bindParamChrome() {
    const toggle = $("loraToggle");
    const pane = $("loraPane");
    if (toggle && pane)
      toggle.onclick = () => {
        pane.hidden = !pane.hidden;
        toggle.classList.toggle("on", !pane.hidden);
        if (!pane.hidden) {
          renderLoraList();
          setLoraNote("");
        }
      };
    const search = $("loraSearch");
    if (search) search.onclick = () => searchLora();
    const box = $("loraQ");
    if (box)
      box.onkeydown = (e) => {
        if (e.key === "Enter") {
          e.preventDefault();
          searchLora();
        }
      };
    const seed = $("seed");
    if (seed)
      seed.oninput = () => {
        const issue = seedIssue();
        seed.classList.toggle("bad", !!issue);
        if (issue) setMsg(issue, "bad");
      };
  }

  function buildGraph(shot) {
    const frame = frameAsset(shot);
    const linked = connectedAssets(shot.id);
    const nodes = [
      {
        id: "p-" + shot.id,
        op: "prompt",
        params: { text: normalizePrompt(shot) },
      },
    ];
    const edges = [
      {
        from: "p-" + shot.id,
        fromPort: "prompt",
        to: shot.id,
        toPort: "prompt",
      },
    ];
    linked.forEach((a) =>
      nodes.push({ id: a.id, op: "image", params: { url: a.url } }),
    );
    let op = "t2i";
    if (state.mode === "video") op = "i2v";
    else if (state.mode !== "text" && linked[0]) op = "i2i";
    const aspect = $("aspect").value || "16:9";
    const selectedResolution = $("res").value || "";
    const selectedModel = selectedCatalogItem();
    const modelResolutions = (selectedModel && selectedModel.resolutions) || [];
    const res =
      modelResolutions.length &&
      resolutionMatches(selectedResolution, modelResolutions)
        ? selectedResolution
        : selectedResolution === "1080P"
          ? aspect === "9:16"
            ? "1080x1920"
            : "1920x1080"
          : aspect === "9:16"
            ? "720x1280"
            : "1280x720";
    const backend = ($("backend") && $("backend").value) || "";
    nodes.push({
      id: shot.id,
      op: op,
      params: Object.assign(
        {
          serviceId: $("service").value,
          resolution: res,
          duration: parseInt($("duration").value, 10) || 5,
        },
        samplerGraphParams(op, backend),
        samplingGraphParams(op, shot),
      ),
    });
    const seedRaw = seedFieldRaw(shot);
    if (/^-?\d+$/.test(seedRaw)) {
      nodes.push({
        id: "sd-" + shot.id,
        op: "seed",
        params: { value: Number(seedRaw) },
      });
      edges.push({
        from: "sd-" + shot.id,
        fromPort: "seed",
        to: shot.id,
        toPort: "seed",
      });
    }
    const loraRows = loraEnabled(shot) ? loraPayloadRows() : [];
    if (loraRows.length) {
      nodes.push({
        id: "lr-" + shot.id,
        op: "lora_apply",
        params: { loras: loraRows },
      });
      edges.push({
        from: "lr-" + shot.id,
        fromPort: "loras",
        to: shot.id,
        toPort: "loras",
      });
    }
    const ref = op === "i2v" ? frame : linked[0];
    if (ref && op !== "t2i")
      edges.push({
        from: ref.id,
        fromPort: "image",
        to: shot.id,
        toPort: "image",
      });
    return { backend: backend, nodes: nodes, edges: edges };
  }

  function pickUrl(data) {
    if (!data) return "";
    if (typeof data.url === "string") return data.url;
    const first = (arr) =>
      arr && arr[0] && (arr[0].url || arr[0].path || arr[0]);
    return (
      first(data.saved) ||
      first(data.files) ||
      first(data.urls) ||
      first(data.images) ||
      first(data.videos) ||
      ""
    );
  }

  async function generate() {
    const shot = nodeById(state.selected);
    if (!shot || shot.kind !== "shot") return;
    if (state.mode === "video" && !frameAsset(shot)) {
      setMsg("视频需要先连一张首帧图，不能偷配方台", "bad");
      return;
    }
    if (!$("service") || !$("service").value) {
      setMsg("没有选中真实模型，不会用默认假值生成", "bad");
      return;
    }
    const seedProblem = seedIssue(shot);
    if (seedProblem) {
      setMsg(seedProblem, "bad");
      return;
    }
    // W2：发送前按模型能力拦截——参考图超上限、steps/cfg 越界（compile 层同样兜底，前端先给明确原因）
    const svcItem = selectedCatalogItem();
    if (state.mode === "image" && svcItem && svcItem.referenceLimit != null) {
      const usedRefs = connectedAssets(shot.id).length;
      if (usedRefs > svcItem.referenceLimit) {
        setMsg(
          "该模型最多接 " +
            svcItem.referenceLimit +
            " 张参考图，当前已连 " +
            usedRefs +
            " 张",
          "bad",
        );
        return;
      }
    }
    if (svcItem && civitaiModel(svcItem)) {
      const checkNum = (input, rule, label) => {
        if (!input || !rule.defined) return "";
        const raw = String(input.value || "").trim();
        if (raw === "") return "";
        const v = Number(raw);
        if (!Number.isFinite(v)) return "";
        if (rule.min != null && v < rule.min)
          return label + " 下限 " + rule.min + "，当前 " + v;
        if (rule.max != null && v > rule.max)
          return label + " 上限 " + rule.max + "，当前 " + v;
        return "";
      };
      const stepsProblem = checkNum(
        $("steps"),
        modelFieldRule(svcItem, "steps"),
        "该模型步数",
      );
      if (stepsProblem) {
        setMsg(stepsProblem + "，不替你静默改数", "bad");
        return;
      }
      const cfgProblem = checkNum(
        $("cfg"),
        modelFieldRule(svcItem, "cfgScale"),
        "该模型 CFG",
      );
      if (cfgProblem) {
        setMsg(cfgProblem + "，不替你静默改数", "bad");
        return;
      }
    }
    $("send").disabled = true;
    setMsg("校验连线…");
    let compiled;
    try {
      const r = await fetch("/api/graph/compile", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(buildGraph(shot)),
      });
      compiled = await r.json();
    } catch (e) {
      setMsg(String(e), "bad");
      $("send").disabled = false;
      return;
    }
    if (!compiled.ok) {
      setMsg(compiled.error || "校验未通过", "bad");
      $("send").disabled = false;
      return;
    }
    const payload =
      compiled.payload ||
      (compiled.stages && compiled.stages[0] && compiled.stages[0].payload);
    if (!payload) {
      setMsg("没有 payload", "bad");
      $("send").disabled = false;
      return;
    }
    setMsg("正在请求云 API…");
    try {
      const r = await fetch("/api/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      let j = await r.json();
      if (!r.ok || j.error) throw new Error(j.error || "HTTP " + r.status);
      const jobId = j.id || j.jobId || j.workflowId;
      let pollTimedOut = false;
      if (jobId && !pickUrl(j)) {
        const st = await pollJob(jobId, (n) =>
          setMsg("云端进行中 " + n + "/" + POLL_TICKS),
        );
        if (st) j = st;
        else pollTimedOut = true;
      }
      const url = pickUrl(j);
      if (url) {
        shot.url = url;
        if (!isVideoUrl(url)) promoteResult(shot, url);
        renderCards();
        drawWires();
        persist();
        setMsg(
          isVideoUrl(url) ? "此镜视频完成" : "此镜完成，成片已收进资产库",
          "ok",
        );
      } else if (pollTimedOut)
        setMsg(
          "任务还在云端跑，这轮没取回图（job " + jobId + "），别重复付费，稍后再看",
          "warn",
        );
      else setMsg("云端已返回，没有可预览地址", "warn");
    } catch (e) {
      setMsg(String(e), "bad");
    }
    $("send").disabled = false;
    renderDock();
  }
  $("send").onclick = () => {
    const n = nodeById(state.selected);
    if (n && n.kind === "text") generateFromText(n);
    else generate();
  };

  $("btnAdd").onclick = () => {
    const n = shots().length;
    const id = uid("shot");
    state.nodes.push({
      id: id,
      kind: "shot",
      title: "分镜" + (n + 1),
      x: 560 + (n % 2) * 720,
      y: 80 + Math.floor(n / 2) * 430,
      url: "",
      firstFrameId: "",
      prompt: "【镜头" + (n + 1) + "】\n场景：\n画面：\n运镜：固定镜头。",
    });
    selectNode(id);
    persist();
  };
  if ($("btnText")) {
    $("btnText").onclick = () => {
      const base = nodeById(state.selected);
      const id = uid("text");
      state.nodes.push({
        id: id,
        kind: "text",
        title: "提示词",
        x: base ? base.x + 200 : 220,
        y: base ? base.y : 24,
        text: "",
      });
      selectNode(id);
      persist();
    };
  }
  if ($("btnRev")) {
    $("btnRev").onclick = () => {
      const n = nodeById(state.selected);
      const src =
        n && isImageSource(n)
          ? n
          : n && n.kind === "shot"
            ? frameAsset(n)
            : null;
      if (!src) {
        setMsg("先选中一张图片资产再反推", "warn");
        return;
      }
      setMsg("正在反推…");
      reverseFromImage(src).then((node) => {
        if (node) setMsg("反推完成，提示词已写入文本节点", "ok");
      });
    };
  }
  $("btnAuto").onclick = () => {
    assets().forEach((n, i) => {
      n.x = 220;
      n.y = 24 + i * 236;
    });
    shots().forEach((n, i) => {
      n.x = 560 + (i % 2) * 720;
      n.y = 80 + Math.floor(i / 2) * 430;
    });
    renderCards();
    drawWires();
    persist();
  };
  $("btnFit").onclick = () => {
    state.cam = { x: 90, y: 36, s: 0.3 };
    applyCam();
    persist();
  };
  if ($("btnUpscale")) $("btnUpscale").onclick = () => upscaleShot();

  async function upscaleShot() {
    const shot = nodeById(state.selected);
    if (!shot || shot.kind !== "shot" || !shot.url || isVideoUrl(shot.url)) {
      setMsg("先选中一张已出图的分镜再做超清", "warn");
      return;
    }
    const backend = $("backend").value;
    $("btnUpscale").disabled = true;
    setMsg("正在挑选超清模型…");
    let serviceId;
    try {
      const r = await fetch(
        "/api/catalog?backend=" +
          encodeURIComponent(backend) +
          "&category=upscale",
      );
      const j = await r.json();
      const it = (j.items || j.models || [])[0];
      serviceId = it && (it.id || it.name);
    } catch (_) {}
    if (!serviceId) {
      setMsg("当前后端 " + backend + " 目录里没有超清模型", "bad");
      $("btnUpscale").disabled = false;
      return;
    }
    const graph = {
      backend: backend,
      nodes: [
        { id: "src-" + shot.id, op: "image", params: { url: shot.url } },
        { id: shot.id, op: "upscale", params: { serviceId: serviceId } },
      ],
      edges: [
        {
          from: "src-" + shot.id,
          fromPort: "image",
          to: shot.id,
          toPort: "image",
        },
      ],
    };
    setMsg("校验连线…");
    let compiled;
    try {
      const r = await fetch("/api/graph/compile", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(graph),
      });
      compiled = await r.json();
    } catch (e) {
      setMsg(String(e), "bad");
      $("btnUpscale").disabled = false;
      return;
    }
    if (!compiled.ok) {
      setMsg(compiled.error || "校验未通过", "bad");
      $("btnUpscale").disabled = false;
      return;
    }
    const payload =
      compiled.payload ||
      (compiled.stages && compiled.stages[0] && compiled.stages[0].payload);
    setMsg("正在请求云 API…");
    try {
      const r = await fetch("/api/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      let j = await r.json();
      if (!r.ok || j.error) throw new Error(j.error || "HTTP " + r.status);
      const jobId = j.id || j.jobId || j.workflowId;
      let pollTimedOut = false;
      if (jobId && !pickUrl(j)) {
        const st = await pollJob(jobId, (n) =>
          setMsg("云端进行中 " + n + "/" + POLL_TICKS),
        );
        if (st) j = st;
        else pollTimedOut = true;
      }
      const url = pickUrl(j);
      if (url) {
        shot.url = url;
        promoteResult(shot, url);
        renderCards();
        drawWires();
        persist();
        setMsg("超清完成", "ok");
      } else if (pollTimedOut)
        setMsg(
          "任务还在云端跑，这轮没取回图（job " + jobId + "），别重复付费，稍后再看",
          "warn",
        );
      else setMsg("云端已返回，没有可预览地址", "warn");
    } catch (e) {
      setMsg(String(e), "bad");
    }
    $("btnUpscale").disabled = false;
  }
  $("zIn").onclick = () => {
    state.cam.s = Math.min(1.5, state.cam.s * 1.12);
    applyCam();
    persist();
  };
  $("zOut").onclick = () => {
    state.cam.s = Math.max(0.16, state.cam.s * 0.9);
    applyCam();
    persist();
  };

  function catalogCategory() {
    if (state.mode === "text" || toolUi.story) return "text";
    if (state.mode === "audio") return "audio";
    return state.mode === "video" ? "video" : "image";
  }
  function selectDefaultBackendForCategory(category) {
    const el = $("backend");
    if (!el) return "";
    const wanted = category === "text" ? "nano-gpt" : "";
    if (wanted && el.value !== wanted) {
      if (!toolUi.prevBackend && el.value) toolUi.prevBackend = el.value;
      el.value = wanted;
    }
    return el.value;
  }
  function dedupeCatalogItems(items) {
    const seen = {};
    return (items || []).filter((it) => {
      const key = String((it && (it.id || it.name)) || "").trim();
      if (!key || seen[key]) return false;
      seen[key] = true;
      return true;
    });
  }
  function capabilityForCatalogItem(item) {
    const id = String((item && item.id) || "");
    if (!id) return null;
    return (
      state.capabilities.find(
        (cap) => String(cap && cap.raw && cap.raw.id) === id,
      ) || null
    );
  }
  function uniqueValues(values) {
    const seen = new Set();
    return (values || []).filter((value) => {
      if (value == null || value === "") return false;
      const key = String(value);
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });
  }
  function constraintEnum(cap, names) {
    const constraints = (cap && cap.constraints) || {};
    for (const name of names) {
      const value = constraints[name];
      if (value && Array.isArray(value.enum)) return value.enum;
    }
    return [];
  }
  function resolutionScore(value) {
    const text = String(value == null ? "" : value)
      .trim()
      .toLowerCase();
    const k = text.match(/^(\d+(?:\.\d+)?)k$/);
    if (k) return Number(k[1]) * 1000;
    const p = text.match(/^(\d+)p$/);
    if (p) return Number(p[1]);
    const dimensions = text.match(/(\d+)\s*x\s*(\d+)/);
    if (dimensions)
      return Math.max(Number(dimensions[1]), Number(dimensions[2]));
    const number = Number(text);
    return Number.isFinite(number) ? number : 0;
  }
  function resolutionMatches(option, supported) {
    const left = String(option || "")
      .trim()
      .toLowerCase();
    return (supported || []).some((value) => {
      const right = String(value || "")
        .trim()
        .toLowerCase();
      return (
        left === right ||
        (resolutionScore(left) > 0 &&
          resolutionScore(left) === resolutionScore(right))
      );
    });
  }
  function enrichCatalogItem(item) {
    const cap = capabilityForCatalogItem(item);
    const params = (item && item.supported_parameters) || {};
    const resolutions = uniqueValues(
      (item && item.resolutions) ||
        params.resolutions ||
        constraintEnum(cap, ["resolution"]),
    );
    const aspectRatios = uniqueValues(
      (item && (item.aspectRatios || item.aspect_ratio_values)) ||
        constraintEnum(cap, ["aspectRatio", "aspect_ratio"]),
    );
    const frameFields = uniqueValues((cap && cap.frameFields) || []);
    const constraints = (cap && cap.constraints) || {};
    // P1：capabilities.json 只属 civitai 键域（raw.id=image/comfy/...）；其它后端按
    // api-capability-落地 §3.1 走条目自带字段（operation/supportedOperations/referenceLimit/
    // supported_parameters overlay），禁止拿 civitai id 模糊蹭。服务端已吐的字段不得被前端清零。
    let referenceLimit = frameFields.reduce((limit, field) => {
      const rule = constraints[field];
      if (!rule || rule.type !== "array") return limit;
      const value = rule.maxItems == null ? rule.maxLength : rule.maxItems;
      return value == null ? limit : Math.max(limit || 0, Number(value));
    }, null);
    if (referenceLimit == null && item && item.referenceLimit != null)
      referenceLimit = item.referenceLimit;
    if (referenceLimit == null && params.max_images != null)
      referenceLimit = Number(params.max_images);
    else if (referenceLimit == null && params.max_output_images != null)
      referenceLimit = Number(params.max_output_images);
    const supportedOperations = uniqueValues(
      (cap && cap.operation ? [cap.operation] : [])
        .concat(constraintEnum(cap, ["operation"]))
        .concat(item && item.operation ? [item.operation] : [])
        .concat(
          item && item.supportedOperations ? item.supportedOperations : [],
        ),
    );
    const maxResolution =
      resolutions
        .slice()
        .sort((a, b) => resolutionScore(b) - resolutionScore(a))[0] || "";
    return Object.assign({}, item, {
      capability: cap
        ? {
            status: cap.status || "",
            constraints: constraints,
            frameFields: frameFields,
            extraFlags: cap.extraFlags || {},
            resolutions: resolutions,
            maxResolution: maxResolution,
            referenceLimit: referenceLimit,
            supportedOperations: supportedOperations,
          }
        : null,
      resolutions: resolutions,
      maxResolution: maxResolution,
      referenceLimit: referenceLimit,
      supportedOperations: supportedOperations,
      aspectRatios: aspectRatios,
    });
  }
  async function loadCapabilities() {
    if (!state._capabilitiesPromise) {
      state._capabilitiesPromise = fetch("/api/capabilities")
        .then((response) =>
          response.ok ? response.json() : { capabilities: [] },
        )
        .then((payload) => {
          state.capabilities = Array.isArray(payload && payload.capabilities)
            ? payload.capabilities
            : [];
          return state.capabilities;
        })
        .catch(() => {
          state.capabilities = [];
          return state.capabilities;
        });
    }
    return state._capabilitiesPromise;
  }
  function serviceBadges(item) {
    if (!item) return [];
    const labels = [];
    const highRes = (item.resolutions || []).filter((value) =>
      /^([24])k$/i.test(String(value).trim()),
    );
    if (highRes.length) labels.push(highRes.join(" / ").toUpperCase());
    // P1：catalog_token（nano 原样 token，如 square_hd/1024x1024）不是分辨率徽标，
    // 禁止画 SQUARE_HD/1024X1024 冒充；2K/4K 命中不受影响。
    else if (
      item.resolutionMode !== "catalog_token" &&
      item.maxResolution
    )
      labels.push(String(item.maxResolution));
    if (item.referenceLimit != null)
      labels.push("支持 " + item.referenceLimit + " 个参考");
    return labels;
  }
  function ensureServiceMeta() {
    const service = $("service");
    if (!service) return null;
    let meta = $("serviceMeta");
    if (meta) return meta;
    meta = document.createElement("span");
    meta.id = "serviceMeta";
    meta.style.cssText =
      "display:inline-flex;gap:4px;align-items:center;flex-wrap:wrap;font-size:10px;";
    service.insertAdjacentElement("afterend", meta);
    return meta;
  }
  function renderServiceMeta(item) {
    const meta = ensureServiceMeta();
    if (!meta) return;
    meta.replaceChildren();
    serviceBadges(item).forEach((label) => {
      const badge = document.createElement("span");
      badge.className = "service-badge";
      badge.textContent = label;
      badge.style.cssText =
        "border:1px solid rgba(255,255,255,.25);border-radius:999px;padding:2px 5px;color:#ddd;white-space:nowrap;";
      meta.appendChild(badge);
    });
  }
  // ===== W2: 逐模型能力门控 =====
  // 层级：model(cap.constraints / 通用逐模型字段) > provider(/api/providers[].capabilities) > HTML 静态默认。
  // civitai 每模型在 /api/capabilities 有独立 constraints 块（raw.id 匹配）；
  // 其余后端无逐模型富约束 → 走通用字段或维持 provider 级，注释标明层级，不发明约束。
  // 模型不声明的参数=不支持 → 禁用并写明原因，禁假值、禁死路按钮。
  function civitaiModel(item) {
    const backend = $("backend");
    return !!backend && backend.value === "civitai" && !!item;
  }
  function modelConstraint(item, name) {
    const itemCap = item && item.capability;
    const c = (itemCap && itemCap.constraints) || {};
    return c[name] != null ? c[name] : null;
  }
  function modelAllowsLoRA(item) {
    if (!civitaiModel(item)) return true; // 非 civitai：LoRA 形态由 provider 级 caps.lora 门控
    // civitai：constraints 声明 loras 键的模型才收 LoRA（image 144 块中 comfy 系才声明）
    return modelConstraint(item, "loras") != null;
  }
  function effectiveSeedRule() {
    // 模型级 constraints.seed 带 min/max 时优先（civitai 少数模型如 int32/uint32 范围）；
    // 否则回退 provider 级 caps.seed；都没有则不限制（空=随机）。
    const item = selectedCatalogItem();
    const m = modelConstraint(item, "seed");
    if (m && (m.min != null || m.max != null)) return m;
    const caps = backendCaps();
    return (caps && caps.seed) || {};
  }
  function modelFieldRule(item, name) {
    // civitai 逐模型规则；无声明（defined=false）→ 调用方维持 provider 级现状并注明
    if (!civitaiModel(item)) {
      return { defined: false, min: null, max: null, enum: null };
    }
    const rule = modelConstraint(item, name);
    if (rule == null) {
      return { defined: false, min: null, max: null, enum: null };
    }
    return {
      defined: true,
      min: rule.min != null ? Number(rule.min) : null,
      max: rule.max != null ? Number(rule.max) : null,
      enum:
        Array.isArray(rule.enum) && rule.enum.length
          ? rule.enum.map(String)
          : null,
    };
  }
  function applyModelParamRules(item) {
    const svcItem = item || selectedCatalogItem() || null;
    const civitai = civitaiModel(svcItem);
    const hintKey = svcItem ? String(svcItem.id || svcItem.name) : "";
    if (state._w2HintItem !== hintKey) state._w2HintItem = hintKey;
    // 1) sampler/scheduler：仅 civitai 且模型声明 enum 才可选；未声明=不支持，禁用写明原因
    if (civitai) {
      const sampler = $("sampler");
      const scheduler = $("scheduler");
      const sameOptions = (sel, list) =>
        !!sel &&
        sel.options.length === list.length &&
        [...sel.options].every((o, i) => o.value === list[i]);
      if (sampler) {
        const rule = modelFieldRule(svcItem, "sampler");
        const cur = sampler.value;
        if (rule.defined && rule.enum) {
          if (!sameOptions(sampler, rule.enum)) {
            fillSamplerOptions(
              sampler,
              rule.enum,
              rule.enum.includes(cur) ? cur : "",
            );
            if (cur && !rule.enum.includes(cur)) sampler.value = "";
          }
          sampler.disabled = false;
          sampler.title = "采样器（该模型支持 " + rule.enum.length + " 项）";
        } else if (rule.defined) {
          sampler.value = "";
          sampler.disabled = true;
          sampler.title = "该模型不声明 sampler，不支持自定义采样器";
        }
      }
      if (scheduler) {
        const rule = modelFieldRule(svcItem, "scheduler");
        const cur = scheduler.value;
        if (rule.defined && rule.enum) {
          if (!sameOptions(scheduler, rule.enum)) {
            fillSamplerOptions(
              scheduler,
              rule.enum,
              rule.enum.includes(cur) ? cur : "",
            );
            if (cur && !rule.enum.includes(cur)) scheduler.value = "";
          }
          scheduler.disabled = false;
          scheduler.title = "调度器（该模型支持 " + rule.enum.length + " 项）";
        } else if (rule.defined) {
          scheduler.value = "";
          scheduler.disabled = true;
          scheduler.title = "该模型不声明 scheduler，不支持自定义调度器";
        }
      }
    }
    // 2) steps/cfg 数值范围：模型声明 min/max 就动态收紧，未声明维持 HTML 默认(1..150 / 0..30)
    const applyRange = (input, rule, htmlMin, htmlMax, label) => {
      if (!input) return;
      if (!rule.defined) return; // provider 级默认，代码注释为层级说明
      input.min = rule.min != null ? rule.min : htmlMin;
      input.max = rule.max != null ? rule.max : htmlMax;
      const raw = String(input.value || "").trim();
      const v = Number(raw);
      const rangeText =
        input.min + "…" + input.max;
      input.title =
        label + "（该模型范围 " + rangeText + "）";
      const bad =
        raw !== "" && Number.isFinite(v) && v !== 0 && (v < Number(input.min) || v > Number(input.max));
      input.classList.toggle("bad", bad);
    };
    const steps = $("steps");
    if (steps) applyRange(steps, modelFieldRule(svcItem, "steps"), 1, 150, "步数 steps");
    const cfg = $("cfg");
    if (cfg) applyRange(cfg, modelFieldRule(svcItem, "cfgScale"), 0, 30, "CFG scale");
    // 3) duration 档位：仅 civitai 视频模型声明 duration 约束时才重排，未声明不动
    if (civitai && state.mode === "video") {
      const durSel = $("duration");
      const d = modelConstraint(svcItem, "duration");
      if (durSel && d) {
        const now = Number.parseInt(String(durSel.value || ""), 10) || 0;
        const en =
          Array.isArray(d.enum) && d.enum.length ? d.enum.map(Number) : null;
        const inRange = (v) =>
          en
            ? en.includes(v)
            : (d.min == null || v >= Number(d.min)) &&
              (d.max == null || v <= Number(d.max));
        const values = en ? en : [5, 12, 16].filter(inRange);
        if (values.length) {
          const opts = values.map((v) => v + "s");
          const same =
            durSel.options.length === opts.length &&
            [...durSel.options].every((o, i) => o.value === opts[i]);
          if (!same) {
            const keep = inRange(now) ? durSel.value : "";
            durSel.replaceChildren();
            opts.forEach((t) => durSel.add(new Option(t, t)));
            if (keep) durSel.value = keep;
            else durSel.value = opts[0];
            if (!keep && state._w2HintItem === hintKey) {
              setMsg(
                "该模型支持时长 " +
                  opts.join("/") +
                  "，已把时长切到 " +
                  durSel.value +
                  "（原档不在能力内，不替你做假请求）",
                "warn",
              );
              state._w2HintItem = "";
            }
          }
          durSel.disabled = false;
          durSel.title =
            "该模型时长 " +
            (en ? en.join("/") + "s" : (d.min == null ? "" : d.min) + "…" + (d.max == null ? "" : d.max) + "s");
        } else {
          durSel.disabled = true;
          durSel.title = "该模型没有可用时长档位";
        }
      }
    }
  }
  function applyServiceConstraints() {
    const service = $("service");
    if (!service) return null;
    const item = state.catalogById[service.value] || null;
    renderServiceMeta(item);
    const supportedResolutions = (item && item.resolutions) || [];
    const res = $("res");
    if (res) {
      if (supportedResolutions.length) {
        supportedResolutions.forEach((value) => {
          if ([...res.options].some((option) => option.value === String(value)))
            return;
          const option = document.createElement("option");
          option.value = String(value);
          option.textContent = String(value);
          res.appendChild(option);
        });
      }
      [...res.options].forEach((option) => {
        option.disabled =
          supportedResolutions.length > 0 &&
          !resolutionMatches(option.value, supportedResolutions);
      });
      if (res.selectedOptions[0] && res.selectedOptions[0].disabled) {
        const next = [...res.options].find((option) => !option.disabled);
        if (next) res.value = next.value;
      }
    }
    const supportedAspects = (item && item.aspectRatios) || [];
    const aspect = $("aspect");
    if (aspect) {
      supportedAspects.forEach((value) => {
        if (
          [...aspect.options].some((option) => option.value === String(value))
        )
          return;
        const option = document.createElement("option");
        option.value = String(value);
        option.textContent = String(value);
        aspect.appendChild(option);
      });
      [...aspect.options].forEach((option) => {
        option.disabled =
          supportedAspects.length > 0 &&
          !supportedAspects.some((value) => String(value) === option.value);
      });
      if (aspect.selectedOptions[0] && aspect.selectedOptions[0].disabled) {
        const next = [...aspect.options].find((option) => !option.disabled);
        if (next) aspect.value = next.value;
      }
    }
    applyModelParamRules(item); // W2：sampler/steps/cfg/duration 随模型能力刷新
    return item;
  }
  function selectedCatalogItem() {
    const service = $("service");
    return state.catalogById[(service && service.value) || ""] || null;
  }
  async function loadCatalog() {
    const seq = ++state._catalogSeq;
    const category = catalogCategory();
    const backend = selectDefaultBackendForCategory(category);
    $("service").innerHTML = '<option value="">选择模型</option>';
    try {
      const [response, capabilities] = await Promise.all([
        fetch(
          "/api/catalog?backend=" +
            encodeURIComponent(backend) +
            "&category=" +
            encodeURIComponent(category),
        ),
        loadCapabilities(),
      ]);
      const j = await response.json();
      state.capabilities = capabilities;
      if (seq !== state._catalogSeq) return;
      const items = dedupeCatalogItems(j.items || j.models || []).map(
        enrichCatalogItem,
      );
      state.catalog = items;
      state.catalogItems = items;
      state.catalogById = {};
      items.forEach((item) => {
        const id = item.id || item.name || "";
        if (id) state.catalogById[id] = item;
      });
      items.slice(0, 60).forEach((it) => {
        const id = it.id || it.name || "";
        if (!id) return;
        const o = document.createElement("option");
        o.value = id;
        const badges = serviceBadges(it);
        o.textContent = [it.name || id, badges.join(" · ")]
          .filter(Boolean)
          .join(" · ");
        $("service").appendChild(o);
      });
      if (state._pendingService) {
        $("service").value = state._pendingService;
        state._pendingService = "";
      }
      // Each provider ships a different model roster per category — never leave
      // serviceId blank, or generate() would fall back across providers.
      if (!$("service").value && $("service").options.length > 1) {
        $("service").selectedIndex = 1;
      }
      applyServiceConstraints();
      if (items.length === 0) {
        $("service").innerHTML = '<option value="">无可用模型</option>';
        renderServiceMeta(null);
        setMsg(
          backend +
            " 的 " +
            category +
            " 目录为空" +
            (category === "text" ? "，文本/故事请用 nano-gpt" : ""),
          "warn",
        );
      } else if (
        $("msg") &&
        /目录为空|圈选消除|发送走/.test($("msg").textContent || "")
      ) {
        setMsg("");
      }
    } catch (_) {
      renderServiceMeta(null);
    }
  }
  if ($("service") && !$("service").dataset.capabilityBound) {
    $("service").dataset.capabilityBound = "1";
    $("service").addEventListener("change", () => {
      resetScopedMsg();
      applyServiceConstraints();
      persist();
    });
  }
  async function loadOuts() {
    try {
      const r = await fetch("/api/outs");
      const j = await r.json();
      const items = (j.items || []).filter(
        (it) => it.kind === "image" || (it.url && !isVideoUrl(it.url)),
      );
      state.history = items
        .slice(0, 24)
        .map((it) => ({
          url: it.url || it.path,
          title: String(it.file || it.name || "历史成片").replace(
            /\.[^.]+$/,
            "",
          ),
        }))
        .filter((it) => it.url);
      renderRail();
    } catch (_) {}
  }
  $("backend").onchange = () => {
    resetScopedMsg();
    loadProviderCaps().then(() => {
      pruneLorasForBackend();
      syncParamChrome();
    });
    loadCatalog();
  };

  // ===== grok: 多角度 + 画面切分（末尾新区块，勿改上方 Claude 打光/消除笔/故事） =====
  // 源站 UI：四 tab 共用三滑杆。旋转 -90..180 / 倾斜 ±30 / 镜头 特写-中景-广角。
  // fal-ai/qwen-image-edit-2511-multiple-angles（只作对照，禁止写死 serviceId）：
  //   horizontal_angle 0..360（0 正面 90 右 180 背 270 左）
  //   vertical_angle -30..90（源站滑杆已限 ±30，直接透传，不抬到 90）
  //   zoom 0..10：0=wide 广角 / 5=medium 中景（默认） / 10=close-up 特写  —— 三档钉死
  // 提交的 horizontalAngle 已是 fal 0–360，后端不要再 +360。
  // 画面切分 = 本地 canvas 切块（下拉含「九宫格 3×3」只是切已有图）。
  // 工具栏独立「九宫格」：POST /api/grid/plan 拆 N 条子提示词，再 N 次 t2i，
  // canvas 拼成一张卡内多画面。catalog 无 grid 分类，禁止 pickCatalogService(..., "grid")。

  function mapSekoYawToFal(yaw) {
    const y = Math.max(-90, Math.min(180, Number(yaw) || 0));
    return (y + 360) % 360;
  }
  function mapSekoPitchToFal(pitch) {
    const p = Number(pitch) || 0;
    return Math.max(-30, Math.min(30, p));
  }
  function mapSekoZoomToFal(slot) {
    const s = Number(slot);
    if (s <= 0) return 10; // 特写
    if (s >= 2) return 0; // 广角
    return 5;
  }

  const CAM_TABS = [
    { id: "custom", label: "自定义", yaw: 0, pitch: 0, zoom: 1, prompt: "" },
    {
      id: "fisheye",
      label: "鱼眼镜头",
      yaw: 0,
      pitch: 30,
      zoom: 1,
      prompt: "fisheye lens, ultra wide",
    },
    {
      id: "reverse",
      label: "反打镜头",
      yaw: 180,
      pitch: 0,
      zoom: 1,
      prompt: "over-the-shoulder reverse shot",
    },
    {
      id: "dutch",
      label: "荷兰角镜头",
      yaw: 45,
      pitch: -30,
      zoom: 1,
      prompt: "dutch angle",
    },
  ];
  const GRID_OPTS = [
    { n: 2, name: "四宫格", cells: "2 × 2" },
    { n: 3, name: "九宫格", cells: "3 × 3" },
    { n: 4, name: "十六宫格", cells: "4 × 4" },
    { n: 5, name: "二十五宫格", cells: "5 × 5" },
  ];
  const camUi = { tab: "custom", yaw: 0, pitch: 0, zoom: 1, prompt: "" };

  const LIGHT_DIRS = [
    {
      id: "left",
      label: "左侧",
      x: 0.16,
      y: 0.42,
      latent: "Left",
      prompt: "light from the left",
    },
    {
      id: "top",
      label: "顶部",
      x: 0.5,
      y: 0.14,
      latent: "Top",
      prompt: "overhead light",
    },
    {
      id: "right",
      label: "右侧",
      x: 0.84,
      y: 0.42,
      latent: "Right",
      prompt: "light from the right",
    },
    {
      id: "front",
      label: "前方",
      x: 0.5,
      y: 0.56,
      latent: "",
      prompt: "front light",
    },
    {
      id: "bottom",
      label: "底部",
      x: 0.5,
      y: 0.86,
      latent: "Bottom",
      prompt: "light from below",
    },
    {
      id: "back",
      label: "后方",
      x: 0.5,
      y: 0.3,
      latent: "",
      prompt: "back light",
    },
  ];
  const LIGHT_PRESETS = [
    {
      label: "伦勃朗光",
      swatch: "linear-gradient(135deg,#2a2118,#c9a06a)",
      prompt: "rembrandt lighting, triangle under the eye",
      kelvin: 3200,
      dir: "left",
    },
    {
      label: "黄金时刻",
      swatch: "linear-gradient(135deg,#e09a3e,#f3d5a0)",
      prompt: "golden hour, warm low sun",
      kelvin: 3500,
      dir: "right",
    },
    {
      label: "蓝调时刻",
      swatch: "linear-gradient(135deg,#1a2a44,#6ea0d4)",
      prompt: "blue hour, cool twilight",
      kelvin: 7500,
      dir: "left",
    },
    {
      label: "暖调光斑",
      swatch: "linear-gradient(135deg,#5a3a20,#f0c48a)",
      prompt: "warm bokeh, golden speckles",
      kelvin: 2800,
      dir: "left",
    },
    {
      label: "过曝胶片",
      swatch: "linear-gradient(135deg,#d8c8b0,#ffffff)",
      prompt: "overexposed film, blown highlights",
      kelvin: 5500,
      dir: "front",
    },
    {
      label: "教父暗影",
      swatch: "linear-gradient(135deg,#0c0c0e,#4a4036)",
      prompt: "godfather shadows, chiaroscuro",
      kelvin: 2800,
      dir: "left",
    },
    {
      label: "布达佩斯大饭店",
      swatch: "linear-gradient(135deg,#c46a6a,#f2d6c9)",
      prompt: "wes anderson palettes, pastel symmetric lighting",
      kelvin: 4800,
      dir: "front",
    },
    {
      label: "沙丘救赎",
      swatch: "linear-gradient(135deg,#6b4a22,#d7b07a)",
      prompt: "dune desert rim light, dusty shafts",
      kelvin: 4000,
      dir: "right",
    },
    {
      label: "商业蝴蝶光",
      swatch: "linear-gradient(135deg,#cfc8c0,#ffffff)",
      prompt: "butterfly lighting, beauty dish",
      kelvin: 5600,
      dir: "front",
    },
    {
      label: "产品聚光",
      swatch: "linear-gradient(135deg,#111,#888)",
      prompt: "product spotlight, dark studio",
      kelvin: 5000,
      dir: "top",
    },
    {
      label: "香槟金高光",
      swatch: "linear-gradient(135deg,#8a6a3a,#f3e0b8)",
      prompt: "champagne gold highlights",
      kelvin: 3200,
      dir: "right",
    },
    {
      label: "光学焦散",
      swatch: "linear-gradient(135deg,#1a3344,#8fd0e8)",
      prompt: "caustics, water light patterns",
      kelvin: 6500,
      dir: "top",
    },
  ];
  const NINE_TYPES = [
    { id: "storm", label: "灵感风暴" },
    { id: "story", label: "故事叙述" },
    { id: "fight", label: "武打分镜" },
    { id: "pano", label: "全景机位" },
  ];
  const lightUi = {
    view: "persp",
    soft: true,
    brightness: 50,
    colorMode: "hex",
    hex: "#FFFFFF",
    kelvin: 5000,
    dir: "left",
    rim: false,
    desc: "",
    preset: -1,
  };
  const inpaintUi = {
    on: false,
    tool: "brush",
    size: 24,
    drawing: false,
    mask: null,
    overlay: null,
    undo: [],
    redo: [],
    shotId: "",
  };
  const toolUi = {
    story: false,
    nine: false,
    nineCrop: false,
    nineType: "storm",
    nineText: "",
    storyText: "",
    prevBackend: "",
  };
  const storyUi = {
    backward: 5,
    forward: 0,
    aspect: "16:9",
    modelType: "pro",
  };
  const STORY_ASPECTS = ["9:16", "16:9", "3:4", "4:3"];
  const STORY_MODEL_TYPES = [
    { id: "pro", label: "专业模型" },
    { id: "general", label: "通用模型" },
  ];
  const STORY_PLAN_ENDPOINT = "/api/story/plan";
  const NINE_SHEET_GAP = 8;
  const PH_DEFAULT = "点击查看或编辑提示词";
  const PH_STORY = "输入你的故事、场景或角色设定";
  const PH_NINE = "请输入九宫格生成提示词...";
  const PH_IMAGE = "描述你想要生成的图片，或输入 @ 引用角色";
  const PH_VIDEO = "结合图片，描述你想生成的角色动作和画面动态";
  const PH_AUDIO = "输入要转换为语音的文字...";
  const SHOTBAR_IMAGE_ITEMS = [
    { id: "btnPanoBar", label: "全景", skip: true, reason: "本版不做全景" },
    { id: "btnCameraAngleBar", label: "多角度" },
    { id: "btnNineGridBar", label: "九宫格" },
    { id: "btnGridSplitBar", label: "画面切分" },
    { id: "btnRelightBar", label: "打光" },
    { id: "btnStoryBar", label: "故事推演" },
    { id: "btnLipBar", label: "对口型", skip: true, reason: "本版不对口型" },
    { id: "btnInpaintBar", label: "消除笔" },
    { id: "btnUpscaleBar", label: "图片超清" },
    { id: "btnVideoBar", label: "合成视频" },
  ];
  const SHOTBAR_VIDEO_ITEMS = [
    { id: "btnExtractFrameBar", label: "截取帧" },
    {
      id: "btnVideoEnhanceBar",
      label: "视频增强",
      skip: true,
      reason: "本版不做视频增强（无模型、不接商汤）",
    },
    {
      id: "btnUnsubBar",
      label: "去字幕",
      skip: true,
      reason: "本版不去做字幕（无模型、不接商汤）",
    },
    {
      id: "btnAudioSplitBar",
      label: "音频分离",
      skip: true,
      reason: "本版不做音频分离（无模型、不接商汤）",
    },
    { id: "btnVideoBar", label: "合成视频" },
  ];
  const SHOTBAR_NINE_ITEMS = [{ id: "btnNineCropBar", label: "局部摘取" }];
  const SHOTBAR_GROUP_ITEMS = [
    { id: "btnGroupDownloadBar", label: "下载" },
    { id: "btnGroupRunBar", label: "整组执行" },
    { id: "btnGroupLayoutBar", label: "自动布局" },
    { id: "btnGroupUngroupBar", label: "解组" },
  ];
  let sekoSelKey = "";
  let nodeClipboard = null;
  let nodeMenuPoint = null;

  function ensureSekoCss() {
    if ($("sekoCamCss")) return;
    const st = document.createElement("style");
    st.id = "sekoCamCss";
    st.textContent = [
      ".shot-bar{position:absolute;z-index:21;display:none;align-items:center;gap:2px;height:36px;max-width:min(520px,calc(100vw - 32px));padding:3px 6px;overflow-x:auto;scrollbar-width:none;",
      "background:#141416;border:1px solid rgba(255,255,255,.1);border-radius:999px;box-shadow:0 8px 24px rgba(0,0,0,.35)}",
      ".shot-bar::-webkit-scrollbar{display:none}",
      ".shot-bar button{border:0;background:transparent;color:#ddd;font-size:12px;padding:4px 10px;border-radius:999px;white-space:nowrap}",
      ".shot-bar button:hover,.shot-bar button.on{background:rgba(255,255,255,.08);color:#fff}",
      ".shot-bar button.skip{opacity:.38;color:#8b8b94;cursor:not-allowed}",
      ".shot-bar button.skip:hover{background:transparent;color:#8b8b94}",
      ".split-menu{position:absolute;z-index:23;display:none;min-width:168px;padding:6px;background:#141416;",
      "border:1px solid rgba(255,255,255,.1);border-radius:12px;box-shadow:0 12px 32px rgba(0,0,0,.45)}",
      ".split-menu button{display:flex;justify-content:space-between;gap:16px;width:100%;border:0;background:transparent;",
      "color:#e8e8ec;font-size:12px;padding:8px 10px;border-radius:8px}",
      ".split-menu button:hover{background:rgba(255,255,255,.08)}",
      ".split-menu button:disabled{opacity:.35;cursor:not-allowed}",
      ".split-menu button:disabled:hover{background:transparent}",
      ".split-menu button span:last-child{color:#8b8b94}",
      ".node-menu{position:absolute;z-index:30;min-width:132px}",
      ".node-menu button{justify-content:flex-start}",
      ".node-menu button.danger{color:#ff8d83}",
      ".cam-panel,.light-panel,.nine-picker{position:absolute;z-index:22;display:none;padding:14px 16px 12px;",
      "background:#141415;border:1px solid rgba(255,255,255,.1);border-radius:16px;box-shadow:0 20px 50px rgba(0,0,0,.5);color:#ececec}",
      ".cam-panel{width:min(640px,calc(100vw - 48px))}",
      ".light-panel{width:min(920px,calc(100vw - 36px))}",
      ".cam-head,.light-head,.nine-head{display:flex;align-items:center;justify-content:space-between;margin-bottom:10px}",
      ".cam-head h2,.light-head h2,.nine-head h2{margin:0;font-size:14px;font-weight:600}",
      ".cam-head .x,.light-head .x,.nine-head .x,.erase-x{width:28px;height:28px;border:0;background:transparent;color:#aaa;font-size:18px;border-radius:8px}",
      ".cam-tabs{display:flex;gap:2px;background:#1b1b1c;border-radius:10px;padding:3px;margin-bottom:12px}",
      ".cam-tabs button{flex:1;border:0;background:transparent;color:rgba(255,255,255,.6);border-radius:8px;padding:6px 8px;font-size:12px}",
      ".cam-tabs button.on{background:rgba(255,255,255,.1);color:#fff}",
      ".cam-body,.light-body{display:flex;gap:18px;align-items:stretch}",
      ".cam-orb-wrap,.light-orb-wrap{position:relative;width:220px;height:220px;flex-shrink:0}",
      ".cam-orb,.light-orb{width:220px;height:220px;border-radius:50%;background:radial-gradient(circle at 50% 42%,#2a2a30 0%,#151518 70%,#0e0e10 100%);",
      "border:1px solid rgba(255,255,255,.08);overflow:hidden;position:relative}",
      ".cam-orb svg,.light-orb svg{position:absolute;inset:0;width:100%;height:100%;pointer-events:none}",
      ".cam-thumb,.light-thumb{position:absolute;left:50%;top:50%;width:88px;height:88px;margin:-44px 0 0 -44px;border-radius:10px;overflow:hidden;",
      "border:1px solid rgba(255,255,255,.18);background:#111;box-shadow:0 8px 20px rgba(0,0,0,.45);transform-style:preserve-3d}",
      ".cam-thumb img,.light-thumb img{width:100%;height:100%;object-fit:cover;display:block}",
      ".cam-cross{position:absolute;inset:0;pointer-events:none}",
      ".cam-cross:before,.cam-cross:after{content:'';position:absolute;background:rgba(255,255,255,.16)}",
      ".cam-cross:before{left:50%;top:18px;bottom:18px;width:1px;transform:translateX(-50%)}",
      ".cam-cross:after{top:50%;left:18px;right:18px;height:1px;transform:translateY(-50%)}",
      ".cam-arr{position:absolute;width:22px;height:22px;border:0;background:transparent;color:rgba(255,255,255,.55);font-size:11px;padding:0}",
      ".cam-arr:hover{color:#fff}",
      ".cam-arr.n{left:50%;top:4px;transform:translateX(-50%)}",
      ".cam-arr.s{left:50%;bottom:4px;transform:translateX(-50%)}",
      ".cam-arr.w{left:4px;top:50%;transform:translateY(-50%)}",
      ".cam-arr.e{right:4px;top:50%;transform:translateY(-50%)}",
      ".cam-sliders{flex:1;display:flex;flex-direction:column;justify-content:center;gap:14px;min-width:0;padding-top:4px}",
      ".cam-sl-h,.light-row-h{display:flex;justify-content:space-between;align-items:baseline;font-size:12px;color:#cfcfd6;margin-bottom:4px}",
      ".cam-sl-h b,.light-row-h b{font-size:13px;color:#fff;font-weight:600}",
      ".cam-sliders input[type=range],.light-params input[type=range]{-webkit-appearance:none;appearance:none;width:100%;height:18px;background:transparent;margin:0}",
      ".cam-sliders input[type=range]::-webkit-slider-runnable-track,.light-params input[type=range]::-webkit-slider-runnable-track{height:4px;background:#3a3a42;border-radius:99px}",
      "#lightKelvin::-webkit-slider-runnable-track{height:4px;background:linear-gradient(90deg,#ffb36a,#fff,#9ec8ff);border-radius:99px}",
      ".cam-sliders input[type=range]::-webkit-slider-thumb,.light-params input[type=range]::-webkit-slider-thumb{-webkit-appearance:none;width:14px;height:14px;border-radius:50%;",
      "background:#fff;border:0;margin-top:-5px;box-shadow:0 0 0 3px rgba(255,255,255,.08)}",
      ".cam-ticks{position:relative;height:16px;margin-top:2px;font-size:10px;color:#8b8b94}",
      ".cam-ticks span{position:absolute;top:0;transform:translateX(-50%)}",
      ".cam-ticks span:first-child{transform:none}",
      ".cam-ticks span:last-child{transform:translateX(-100%)}",
      ".cam-panel,.light-panel,.nine-picker{max-height:calc(100% - 168px);overflow:auto}",
      ".cam-foot,.light-foot{display:flex;align-items:center;margin-top:16px;padding-top:12px;gap:8px;",
      "border-top:1px solid rgba(255,255,255,.08);position:relative;z-index:2}",
      ".cam-reset,.light-reset{border:0;background:transparent;color:#cfcfd6;font-size:12px;padding:4px 0}",
      ".cam-reset:hover,.light-reset:hover{color:#fff}",
      ".cam-msg,.light-msg{flex:1;font-size:11px;color:#8b8b94;min-height:1.2em}",
      ".cam-msg.bad,.light-msg.bad{color:var(--coral)}.cam-msg.ok,.light-msg.ok{color:var(--ok)}.cam-msg.warn,.light-msg.warn{color:var(--buzz)}",
      ".cam-send,.light-send{width:36px;height:36px;border:0;border-radius:50%;background:#fff;color:#111;font-size:16px}",
      ".cam-send:disabled,.light-send:disabled{opacity:.4}",
      ".cam-cost,.light-cost,.dock-cost{font-size:12px;color:#8b8b94;padding:0 6px;white-space:nowrap}",
      ".grid-split-ov{position:absolute;inset:0;display:grid;gap:3px;padding:3px;pointer-events:none;border-radius:15px;z-index:2}",
      ".grid-split-ov i{border:1px solid rgba(255,255,255,.22);border-radius:2px;display:block}",
      ".grid-split-ov.pick{pointer-events:auto;cursor:pointer;background:rgba(0,0,0,.18)}",
      ".grid-split-ov.pick i{pointer-events:auto;background:rgba(255,255,255,.04)}",
      ".grid-split-ov.pick i:hover{background:rgba(94,224,197,.24);border-color:#5ee0c5}",
      ".shot .face{position:relative}",
      ".light-view{display:flex;gap:4px;background:#1b1b1c;border-radius:10px;padding:4px;margin-bottom:10px;width:160px}",
      ".light-view button{flex:1;border:0;background:transparent;color:rgba(255,255,255,.6);border-radius:8px;padding:4px 0;font-size:12px}",
      ".light-view button.on{background:rgba(255,255,255,.1);color:#fff}",
      ".light-dot{position:absolute;width:14px;height:14px;margin:-7px 0 0 -7px;border-radius:50%;background:#111;border:2px solid #fff;box-shadow:0 0 10px rgba(255,255,255,.35);z-index:3}",
      ".light-params{flex:1.1;min-width:220px;display:flex;flex-direction:column;gap:10px}",
      ".light-side{width:240px;flex-shrink:0;display:flex;flex-direction:column;gap:8px}",
      ".seg{display:flex;gap:2px;background:#1b1b1c;border-radius:10px;padding:3px}",
      ".seg button{flex:1;border:0;background:transparent;color:rgba(255,255,255,.6);border-radius:8px;padding:5px 8px;font-size:12px}",
      ".seg button.on{background:rgba(255,255,255,.8);color:#1b1b1c}",
      ".light-dirs{display:grid;grid-template-columns:repeat(3,1fr);gap:6px}",
      ".light-dirs button{border:1px solid rgba(255,255,255,.1);background:transparent;color:rgba(255,255,255,.6);border-radius:8px;padding:7px 0;font-size:12px}",
      ".light-dirs button.on{background:rgba(255,255,255,.12);color:#fff;border-color:rgba(255,255,255,.28)}",
      ".light-dirs button:disabled,.light-dirs button.unsupported{opacity:.32;cursor:not-allowed;color:rgba(255,255,255,.28)}",
      ".light-hex{display:flex;align-items:center;gap:8px}",
      ".light-hex input[type=color]{width:28px;height:28px;border:0;background:transparent;padding:0}",
      ".light-hex input[type=text],.light-bright input[type=number]{width:84px;background:#1a1a1f;border:1px solid #2e2e36;border-radius:8px;padding:4px 8px}",
      ".light-kelvin-track{background:linear-gradient(90deg,#ffb36a,#fff,#9ec8ff);border-radius:99px;height:4px;position:relative;top:7px}",
      ".light-desc{width:100%;min-height:64px;resize:vertical;background:#121214;border:1px solid #2a2a30;border-radius:10px;padding:8px;color:#e8e8ec}",
      ".light-presets{display:grid;grid-template-columns:repeat(4,1fr);gap:6px}",
      ".light-presets button{border:1px solid rgba(255,255,255,.1);background:#1a1a1f;border-radius:8px;padding:0;overflow:hidden;color:#ddd}",
      ".light-presets button img{display:block;width:100%;height:44px;object-fit:cover}",
      ".light-presets button .lp0{filter:contrast(1.12) sepia(.2) saturate(1.15)}",
      ".light-presets button .lp1{filter:sepia(.35) saturate(1.25) brightness(1.08)}",
      ".light-presets button .lp2{filter:hue-rotate(190deg) saturate(1.15) brightness(.9)}",
      ".light-presets button .lp3{filter:sepia(.45) brightness(1.08)}",
      ".light-presets button .lp4{filter:brightness(1.35) contrast(.9)}",
      ".light-presets button .lp5{filter:contrast(1.35) brightness(.72)}",
      ".light-presets button .lp6{filter:saturate(1.35) hue-rotate(320deg)}",
      ".light-presets button .lp7{filter:sepia(.35) saturate(1.4)}",
      ".light-presets button .lp8{filter:grayscale(.25) contrast(1.45)}",
      ".light-presets button .lp9{filter:sepia(.55) saturate(1.25) brightness(1.08)}",
      ".light-presets button .lp10{filter:hue-rotate(170deg) saturate(1.45)}",
      ".light-presets button span{display:block;font-size:10px;padding:4px 3px 6px;line-height:1.25;white-space:normal}",
      ".light-presets button.on{border-color:#fff}",
      ".light-toggle{display:flex;align-items:center;justify-content:space-between;font-size:12px;color:#cfcfd6}",
      ".light-toggle input{accent-color:#5ee0c5}",
      ".erase-bar{position:absolute;z-index:24;display:none;align-items:center;gap:8px;height:44px;padding:4px 10px;",
      "background:#141416;border:1px solid rgba(255,255,255,.1);border-radius:999px;box-shadow:0 8px 24px rgba(0,0,0,.4);color:#ddd}",
      ".erase-bar .lab{font-size:12px;padding:0 6px}",
      ".erase-bar button.icon{width:32px;height:32px;border:0;border-radius:50%;background:transparent;color:#ddd}",
      ".erase-bar button.icon.on{background:#1f6f63;color:#fff}",
      ".erase-bar input[type=range]{width:88px}",
      ".erase-go{border:0;border-radius:999px;background:#fff;color:#111;padding:6px 14px;font-size:12px;font-weight:600}",
      ".inpaint-cv{position:absolute;inset:0;width:100%;height:100%;z-index:5;border-radius:15px;touch-action:none}",
      ".inpaint-cursor{position:fixed;border:1px solid #5ee0c5;border-radius:50%;pointer-events:none;z-index:45;display:none}",
      ".nine-picker{width:min(560px,calc(100vw - 48px));padding:10px 12px}",
      ".nine-types{display:flex;flex-wrap:wrap;gap:6px;align-items:center}",
      ".nine-types .lab{color:#8b8b94;font-size:12px}",
      ".nine-types button{border:1px solid rgba(255,255,255,.1);background:#1b1b1c;color:rgba(255,255,255,.7);border-radius:999px;padding:6px 12px;font-size:12px}",
      ".nine-types button.on{background:rgba(255,255,255,.12);color:#fff}",
      ".story-skill{display:inline-flex;align-items:center;height:28px;padding:0 10px;border-radius:999px;border:1px solid #2e2e36;",
      "background:#1a1a1f;color:#9a9aa3;font-size:11px}",
      ".story-controls{display:none;gap:10px;align-items:center;flex-wrap:wrap;margin:6px 0 8px;color:#cfcfd6;font-size:12px}",
      ".story-controls.show{display:flex}",
      ".story-controls label{display:flex;align-items:center;gap:6px;background:#1a1a1f;border:1px solid #2e2e36;border-radius:999px;padding:4px 8px}",
      ".story-controls input[type=range]{width:86px}",
      ".story-seg{display:flex;gap:2px;background:#1b1b1c;border-radius:999px;padding:3px}",
      ".story-seg button{border:0;background:transparent;color:rgba(255,255,255,.65);border-radius:999px;padding:5px 8px;font-size:12px}",
      ".story-seg button.on{background:rgba(255,255,255,.14);color:#fff}",
      "#dock.story-mode .send{width:auto;min-width:82px;border-radius:999px;font-size:12px;font-weight:600;padding:0 12px}",
      ".modes button.off{opacity:.4;cursor:not-allowed}",
      ".shot-bar button.skip{opacity:.38}",
      ".blank-pill{min-width:72px;justify-content:center;padding:4px 14px;height:32px;cursor:pointer}",
      ".dock.node-attached{transform:none;bottom:auto}",
      ".card.group{position:absolute;border:1px dashed rgba(255,255,255,.28);background:rgba(18,18,22,.32);border-radius:18px;z-index:0;box-shadow:none}",
      ".card.group .label{position:absolute;top:-22px;left:0;font-size:11px;color:#9a9aa3}",
      ".card.group.sel{border-color:#fff;box-shadow:0 0 0 1px rgba(255,255,255,.35)}",
    ].join("");
    document.head.appendChild(st);
  }

  function ensureSekoDom() {
    ensureSekoCss();
    const stage = document.querySelector(".stage");
    if (!stage) return;
    if (!$("shotBar")) {
      const bar = document.createElement("div");
      bar.id = "shotBar";
      bar.className = "shot-bar";
      bar.innerHTML = "";
      bar.dataset.variant = "";
      stage.appendChild(bar);
      bar.addEventListener("pointerdown", (e) => e.stopPropagation());
    }
    if (!$("blankPill")) {
      const pill = document.createElement("div");
      pill.id = "blankPill";
      pill.className = "shot-bar blank-pill";
      pill.style.display = "none";
      stage.appendChild(pill);
      pill.addEventListener("pointerdown", (e) => e.stopPropagation());
      pill.addEventListener("click", () => {
        if (pill.dataset.act === "upload") $("file") && $("file").click();
        else if ($("prompt")) $("prompt").focus();
      });
    }
    if (!$("gridSplitMenu")) {
      const menu = document.createElement("div");
      menu.id = "gridSplitMenu";
      menu.className = "split-menu";
      menu.innerHTML = GRID_OPTS.map(
        (g) =>
          '<button type="button" data-grid="' +
          g.n +
          '"><span>' +
          g.name +
          "</span><span>" +
          g.cells +
          "</span></button>",
      ).join("");
      stage.appendChild(menu);
      menu.addEventListener("pointerdown", (e) => e.stopPropagation());
    }
    if (!$("nodeContextMenu")) {
      const menu = document.createElement("div");
      menu.id = "nodeContextMenu";
      menu.className = "split-menu node-menu";
      menu.setAttribute("role", "menu");
      menu.innerHTML =
        '<button type="button" data-nodeact="copy">复制</button>' +
        '<button type="button" data-nodeact="paste">粘贴</button>' +
        '<button type="button" class="danger" data-nodeact="delete">删除</button>';
      stage.appendChild(menu);
      menu.addEventListener("pointerdown", (e) => e.stopPropagation());
    }
    if (!$("camPanel")) {
      const p = document.createElement("div");
      p.id = "camPanel";
      p.className = "cam-panel";
      p.innerHTML =
        '<div class="cam-head"><h2>多角度</h2><button type="button" class="x" id="camClose">×</button></div>' +
        '<div class="cam-tabs" id="camTabs">' +
        CAM_TABS.map(
          (t) =>
            '<button type="button" data-camtab="' +
            t.id +
            '">' +
            t.label +
            "</button>",
        ).join("") +
        "</div>" +
        '<div class="cam-body">' +
        '<div class="cam-orb-wrap">' +
        '<div class="cam-orb" id="camOrb">' +
        '<svg viewBox="0 0 220 220" aria-hidden="true">' +
        '<ellipse cx="110" cy="110" rx="96" ry="96" fill="none" stroke="rgba(255,255,255,.14)" />' +
        '<ellipse cx="110" cy="110" rx="96" ry="32" fill="none" stroke="rgba(255,255,255,.12)" />' +
        '<ellipse cx="110" cy="110" rx="96" ry="62" fill="none" stroke="rgba(255,255,255,.1)" />' +
        '<ellipse cx="110" cy="110" rx="32" ry="96" fill="none" stroke="rgba(255,255,255,.12)" />' +
        '<ellipse cx="110" cy="110" rx="62" ry="96" fill="none" stroke="rgba(255,255,255,.1)" />' +
        '<line x1="14" y1="110" x2="206" y2="110" stroke="rgba(255,255,255,.1)" />' +
        '<line x1="110" y1="14" x2="110" y2="206" stroke="rgba(255,255,255,.1)" />' +
        "</svg>" +
        '<div class="cam-cross"></div>' +
        '<div class="cam-thumb" id="camThumb"><img alt=""></div>' +
        "</div>" +
        '<button type="button" class="cam-arr n" data-camdir="n" title="上">▲</button>' +
        '<button type="button" class="cam-arr s" data-camdir="s" title="下">▼</button>' +
        '<button type="button" class="cam-arr w" data-camdir="w" title="左">◀</button>' +
        '<button type="button" class="cam-arr e" data-camdir="e" title="右">▶</button>' +
        "</div>" +
        '<div class="cam-sliders">' +
        '<label><div class="cam-sl-h"><span>旋转角度 ±90°</span><b id="camYawVal">0</b></div>' +
        '<input id="camYaw" type="range" min="-90" max="180" step="1" value="0">' +
        '<div class="cam-ticks">' +
        '<span style="left:0%">-90</span><span style="left:16.67%">-45</span><span style="left:33.33%">0</span>' +
        '<span style="left:50%">45</span><span style="left:66.67%">90</span><span style="left:100%">180</span>' +
        "</div></label>" +
        '<label><div class="cam-sl-h"><span>倾斜角度 ±30°</span><b id="camPitchVal">0</b></div>' +
        '<input id="camPitch" type="range" min="-30" max="30" step="1" value="0">' +
        '<div class="cam-ticks">' +
        '<span style="left:0%">-30</span><span style="left:50%">0</span><span style="left:100%">30</span>' +
        "</div></label>" +
        '<label><div class="cam-sl-h"><span>镜头</span><b id="camZoomVal">中景</b></div>' +
        '<input id="camZoom" type="range" min="0" max="2" step="1" value="1">' +
        '<div class="cam-ticks">' +
        '<span style="left:0%">特写</span><span style="left:50%">中景</span><span style="left:100%">广角</span>' +
        "</div></label>" +
        "</div></div>" +
        '<div class="cam-foot">' +
        '<button type="button" class="cam-reset" id="camReset">↺ 重置参数</button>' +
        '<div class="cam-msg" id="camMsg"></div>' +
        '<span class="cam-cost" title="源站积分标注">1</span>' +
        '<button type="button" class="cam-send" id="camSend" title="生成">↑</button>' +
        "</div>";
      stage.appendChild(p);
      p.addEventListener("pointerdown", (e) => e.stopPropagation());
    }
    if (!$("lightPanel")) {
      const p = document.createElement("div");
      p.id = "lightPanel";
      p.className = "light-panel";
      p.innerHTML =
        '<div class="light-head"><h2>打光效果</h2><button type="button" class="x" id="lightClose">×</button></div>' +
        '<div class="light-body">' +
        "<div>" +
        '<div class="light-view" id="lightView">' +
        '<button type="button" data-lview="persp">透视</button>' +
        '<button type="button" data-lview="front">正面</button></div>' +
        '<div class="light-orb-wrap">' +
        '<div class="light-orb" id="lightOrb">' +
        '<svg viewBox="0 0 220 220" aria-hidden="true">' +
        '<ellipse cx="110" cy="110" rx="96" ry="96" fill="none" stroke="rgba(255,255,255,.14)" />' +
        '<ellipse cx="110" cy="110" rx="96" ry="36" fill="none" stroke="rgba(255,255,255,.1)" />' +
        '<ellipse cx="110" cy="110" rx="36" ry="96" fill="none" stroke="rgba(255,255,255,.1)" />' +
        "</svg>" +
        '<div class="light-thumb" id="lightThumb"><img alt=""></div>' +
        '<div class="light-dot" id="lightDot"></div>' +
        "</div></div></div>" +
        '<div class="light-params">' +
        '<div><div class="light-row-h"><span>灯光类型</span></div>' +
        '<div class="seg" id="lightSoft">' +
        '<button type="button" data-lsoft="1">柔光</button>' +
        '<button type="button" data-lsoft="0">硬光</button></div></div>' +
        '<div><div class="light-row-h"><span>亮度</span><b><span id="lightBrightVal">50</span> %</b></div>' +
        '<div class="light-bright" style="display:flex;align-items:center;gap:8px">' +
        '<input id="lightBright" type="range" min="0" max="100" step="1" value="50">' +
        '<input id="lightBrightNum" type="number" min="0" max="100" value="50"></div></div>' +
        '<div><div class="light-row-h"><span>光源颜色</span></div>' +
        '<div class="seg" id="lightColorMode">' +
        '<button type="button" data-lcmode="hex">颜色</button>' +
        '<button type="button" data-lcmode="kelvin">色温</button></div>' +
        '<div class="light-hex" id="lightHexRow">' +
        '<input id="lightColor" type="color" value="#FFFFFF">' +
        '<span>#</span><input id="lightHex" type="text" value="#FFFFFF" maxlength="7"></div>' +
        '<div id="lightKelvinRow" style="display:none">' +
        '<input id="lightKelvin" type="range" min="2000" max="10000" step="50" value="5000" style="background:transparent">' +
        '<div class="light-row-h"><span></span><b id="lightKelvinVal">5000 K</b></div></div></div>' +
        '<div><div class="light-row-h"><span>主光源</span></div>' +
        '<div class="light-dirs" id="lightDirs">' +
        LIGHT_DIRS.map((d) => {
          return (
            '<button type="button" data-ldir="' +
            d.id +
            '"' +
            (d.latent ? "" : ' title="该方向 fal 不支持"') +
            ">" +
            d.label +
            "</button>"
          );
        }).join("") +
        "</div></div>" +
        '<label class="light-toggle">轮廓光 <input id="lightRim" type="checkbox"></label>' +
        "</div>" +
        '<div class="light-side">' +
        '<div class="light-row-h"><span>光源描述 (选填)</span></div>' +
        '<textarea class="light-desc" id="lightDesc" placeholder="简单描述你想实现的灯光效果，或情绪风格"></textarea>' +
        '<div class="light-row-h"><span>预设</span></div>' +
        '<div class="light-presets" id="lightPresets">' +
        LIGHT_PRESETS.map((pr, i) => {
          const vis =
            '<img class="lp' + (i % 11) + '" data-light-thumb alt="" hidden>';
          return (
            '<button type="button" data-lpreset="' +
            i +
            '">' +
            vis +
            "<span>" +
            pr.label +
            "</span></button>"
          );
        }).join("") +
        "</div></div></div>" +
        '<div class="light-foot">' +
        '<button type="button" class="light-reset" id="lightReset">↺ 重置参数</button>' +
        '<div class="light-msg" id="lightMsg"></div>' +
        '<span class="light-cost" title="源站积分标注">5</span>' +
        '<button type="button" class="light-send" id="lightSend" title="生成">↑</button>' +
        "</div>";
      stage.appendChild(p);
      p.addEventListener("pointerdown", (e) => e.stopPropagation());
    }
    if (!$("eraseBar")) {
      const bar = document.createElement("div");
      bar.id = "eraseBar";
      bar.className = "erase-bar";
      bar.innerHTML =
        '<span class="lab">消除笔</span>' +
        '<button type="button" class="icon" id="eraseBrush" title="画笔">✎</button>' +
        '<button type="button" class="icon" id="eraseEraser" title="橡皮">⌫</button>' +
        '<span style="opacity:.45">·</span>' +
        '<input id="eraseSize" type="range" min="6" max="72" value="24">' +
        '<button type="button" class="icon" id="eraseUndo" title="撤销">↶</button>' +
        '<button type="button" class="icon" id="eraseRedo" title="重做">↷</button>' +
        '<button type="button" class="icon" id="eraseClear" title="重置">↺</button>' +
        '<button type="button" class="erase-go" id="eraseGo">消除 ◆1</button>' +
        '<button type="button" class="erase-x" id="eraseClose">×</button>';
      stage.appendChild(bar);
      bar.addEventListener("pointerdown", (e) => e.stopPropagation());
    }
    if (!$("inpaintCursor")) {
      const c = document.createElement("div");
      c.id = "inpaintCursor";
      c.className = "inpaint-cursor";
      document.body.appendChild(c);
    }
    if (!$("ninePicker")) {
      const p = document.createElement("div");
      p.id = "ninePicker";
      p.className = "nine-picker";
      p.innerHTML =
        '<div class="nine-head"><h2>九宫格</h2><button type="button" class="x" id="nineClose">×</button></div>' +
        '<div class="nine-types" id="nineTypes">' +
        '<span class="lab">选择类型：</span>' +
        NINE_TYPES.map(
          (t) =>
            '<button type="button" data-ninetype="' +
            t.id +
            '">' +
            t.label +
            "</button>",
        ).join("") +
        "</div>";
      stage.appendChild(p);
      p.addEventListener("pointerdown", (e) => e.stopPropagation());
    }
    if (!$("modeAud")) {
      const modes = document.querySelector("#dock .modes");
      if (modes) {
        const b = document.createElement("button");
        b.type = "button";
        b.id = "modeAud";
        b.className = "off";
        b.disabled = true;
        b.title = "本版不做音频精细化";
        b.textContent = "音频生成";
        modes.appendChild(b);
      }
    }
    if (!$("dockCost") && $("send")) {
      const sp = document.createElement("span");
      sp.id = "dockCost";
      sp.className = "dock-cost";
      $("send").parentNode.insertBefore(sp, $("send"));
    }
    if (!$("storySkill")) {
      const sp = document.createElement("span");
      sp.id = "storySkill";
      sp.className = "story-skill";
      sp.textContent = "skill · 故事导演";
      sp.style.display = "none";
      const refs = $("refs");
      if (refs && refs.parentNode) refs.parentNode.insertBefore(sp, refs);
    }
    if (!$("storyControls")) {
      const box = document.createElement("div");
      box.id = "storyControls";
      box.className = "story-controls";
      box.innerHTML =
        '<label>向后推演 <input id="storyBack" type="range" min="0" max="8" step="1" value="5"><b id="storyBackVal">5s</b></label>' +
        '<label>向前推演 <input id="storyForward" type="range" min="0" max="8" step="1" value="0"><b id="storyForwardVal">0s</b></label>' +
        '<div class="story-seg" id="storyAspectBtns">' +
        STORY_ASPECTS.map(
          (a) =>
            '<button type="button" data-story-aspect="' +
            a +
            '">' +
            a +
            "</button>",
        ).join("") +
        "</div>" +
        '<div class="story-seg" id="storyModelBtns">' +
        STORY_MODEL_TYPES.map(
          (m) =>
            '<button type="button" data-story-model="' +
            m.id +
            '">' +
            m.label +
            "</button>",
        ).join("") +
        "</div>";
      const refs = $("refs");
      if (refs && refs.parentNode) refs.parentNode.insertBefore(box, refs);
    }
    // da28a0d 把打光/多角度/消除/故事/切分写进左侧常驻 .tools。
    // 源站这些入口只在选中节点的 shot-bar 上，常驻轨会破坏未选中应收起。
    [
      "btnRelight",
      "btnCameraAngle",
      "btnInpaint",
      "btnStory",
      "btnGridSplit",
      "btnNineGrid",
      "btnUpscale",
    ].forEach((id) => {
      const el = $(id);
      if (el) el.style.display = "none";
    });
  }

  function panelOpen(id) {
    const el = $(id);
    return !!(el && el.style.display && el.style.display !== "none");
  }
  function closeAllToolPanels() {
    closeCamPanel();
    closeLightPanel();
    closeInpaintBar();
    hideGridMenu();
    closeNinePicker();
  }

  function hideNodeMenu() {
    const menu = $("nodeContextMenu");
    if (menu) menu.style.display = "none";
  }

  function clearNodeTransientUi() {
    state.drag = null;
    state.pan = null;
    state.link = null;
    state.railDrag = null;
    state._atTarget = null;
    toolUi.story = false;
    toolUi.nine = false;
    toolUi.nineCrop = false;
    inpaintUi.on = false;
    inpaintUi.drawing = false;
    inpaintUi.mask = null;
    inpaintUi.overlay = null;
    inpaintUi.undo = [];
    inpaintUi.redo = [];
    inpaintUi.shotId = "";
    hideGhost();
    const picker = $("picker");
    const atbox = $("atbox");
    if (picker) picker.classList.remove("show");
    if (atbox) atbox.classList.remove("show");
    closeAllToolPanels();
    hideNodeMenu();
  }

  function clearEdgeReferences(edge, removedIds) {
    const source = nodeById(edge.from);
    const target = nodeById(edge.to);
    if (!target || removedIds.has(target.id)) return;
    if (
      source &&
      isImageSource(source) &&
      (target.kind === "shot" || target.kind === "text")
    )
      unmention(source, target);
    if (target.kind === "shot") {
      if (target.firstFrameId === edge.from) target.firstFrameId = "";
      if (target.lastFrameId === edge.from) target.lastFrameId = "";
    }
  }

  function selectEdge(from, to) {
    if (!from || !to) return false;
    if (!state.edges.some((e) => e.from === from && e.to === to)) return false;
    state.selected = null;
    state.selectedEdge = { from: from, to: to };
    renderCards();
    drawWires();
    renderDock();
    return true;
  }

  function deleteEdge(from, to) {
    if (!from || !to) return false;
    const removed = state.edges.filter((e) => e.from === from && e.to === to);
    if (!removed.length) return false;
    const removedIds = new Set();
    removed.forEach((edge) => clearEdgeReferences(edge, removedIds));
    state.edges = state.edges.filter((e) => !(e.from === from && e.to === to));
    state.selectedEdge = null;
    renderCards();
    drawWires();
    renderDock();
    persist();
    setMsg("已删除连线", "ok");
    return true;
  }

  function deleteNode(id) {
    const target = nodeById(id);
    if (!target) return false;
    const removedIds = new Set([id]);
    const pending = [target];
    while (pending.length) {
      const node = pending.pop();
      if (node.kind !== "group" || !Array.isArray(node.memberIds)) continue;
      node.memberIds.forEach((memberId) => {
        const member = nodeById(memberId);
        if (member && !removedIds.has(member.id)) {
          removedIds.add(member.id);
          pending.push(member);
        }
      });
    }
    state.selected = null;
    state.selectedEdge = null;
    sekoSelKey = "";
    clearNodeTransientUi();
    state.edges
      .filter((e) => removedIds.has(e.from) || removedIds.has(e.to))
      .forEach((edge) => clearEdgeReferences(edge, removedIds));
    state.nodes = state.nodes.filter((n) => !removedIds.has(n.id));
    const incidentEdges = state.edges.filter(
      (e) => e.from !== id && e.to !== id,
    );
    state.edges = incidentEdges.filter(
      (e) => !removedIds.has(e.from) && !removedIds.has(e.to),
    );
    state.nodes.forEach((n) => {
      if (n.kind === "group" && Array.isArray(n.memberIds)) {
        n.memberIds = n.memberIds.filter((memberId) => memberId !== id);
        n.memberIds = n.memberIds.filter(
          (memberId) => !removedIds.has(memberId),
        );
        fitGroupBox(n);
      }
      if (removedIds.has(n.firstFrameId)) n.firstFrameId = "";
      if (removedIds.has(n.lastFrameId)) n.lastFrameId = "";
      if (removedIds.has(n.gridFrom)) n.gridFrom = "";
      if (removedIds.has(n.fromGrid)) n.fromGrid = "";
    });
    renderCards();
    drawWires();
    renderDock();
    persist();
    const memberCount = removedIds.size - 1;
    setMsg(
      memberCount > 0 ? "已删除分组及" + memberCount + "个成员" : "已删除节点",
      "ok",
    );
    return true;
  }

  function copyNode(id) {
    const node = nodeById(id);
    if (!node) return false;
    nodeClipboard = JSON.parse(JSON.stringify(node));
    setMsg("已复制节点", "ok");
    return true;
  }

  function pasteNode(point) {
    if (!nodeClipboard) return null;
    const node = JSON.parse(JSON.stringify(nodeClipboard));
    const prefix =
      node.kind === "group"
        ? "group"
        : node.kind === "text"
          ? "text"
          : node.kind === "shot"
            ? "shot"
            : "asset";
    node.id = uid(prefix);
    node.x = point && point.x != null ? point.x : Number(node.x || 0) + 48;
    node.y = point && point.y != null ? point.y : Number(node.y || 0) + 48;
    delete node._offX;
    delete node._offY;
    if (node.kind === "group") node.memberIds = [];
    if (node.firstFrameId) node.firstFrameId = "";
    if (node.lastFrameId) node.lastFrameId = "";
    if (node.gridFrom) node.gridFrom = "";
    if (node.fromGrid) node.fromGrid = "";
    state.nodes.push(node);
    selectNode(node.id);
    persist();
    setMsg("已粘贴节点", "ok");
    return node;
  }

  function showNodeMenu(e) {
    const menu = $("nodeContextMenu");
    const stage = document.querySelector(".stage");
    if (!menu || !stage) return;
    const card = e.target.closest(".card");
    const edge = e.target.closest(".wire-hit[data-edge-from][data-edge-to]");
    const targetId = card ? card.dataset.id : "";
    const targetEdge = edge
      ? { from: edge.dataset.edgeFrom, to: edge.dataset.edgeTo }
      : null;
    if (targetEdge) selectEdge(targetEdge.from, targetEdge.to);
    else if (targetId && state.selected !== targetId) selectNode(targetId);
    nodeMenuPoint = {
      targetId: targetId,
      targetEdge: targetEdge,
      world: clientToWorld(e.clientX, e.clientY),
    };
    menu.querySelector('[data-nodeact="copy"]').disabled = !targetId;
    const deleteButton = menu.querySelector('[data-nodeact="delete"]');
    deleteButton.disabled = !targetId && !targetEdge;
    deleteButton.textContent = targetEdge ? "删除连线" : "删除";
    menu.querySelector('[data-nodeact="paste"]').disabled = !nodeClipboard;
    const sr = stage.getBoundingClientRect();
    menu.style.display = "block";
    const left = Math.max(
      6,
      Math.min(e.clientX - sr.left, sr.width - menu.offsetWidth - 6),
    );
    const top = Math.max(
      6,
      Math.min(e.clientY - sr.top, sr.height - menu.offsetHeight - 6),
    );
    menu.style.left = left + "px";
    menu.style.top = top + "px";
  }

  function shotImageUrl(shot) {
    if (!shot || shot.kind !== "shot") return "";
    if (shot.url && !isVideoUrl(shot.url)) return shot.url;
    const fr = frameAsset(shot);
    if (fr && isImageSource(fr)) return fr.url;
    const linked = connectedAssets(shot.id).find(isImageSource);
    return linked ? linked.url : "";
  }
  function selectedShotImage() {
    const n = nodeById(state.selected);
    if (!n || n.kind !== "shot") return null;
    if (n.url && !isVideoUrl(n.url)) return n;
    return null;
  }

  function isNineGridNode(n) {
    if (!n || n.kind !== "shot") return false;
    if (n.gridFrom) return false;
    if (n.nineType) return true;
    if (n.gridCells && n.gridCells.length) return true;
    return n.title === "九宫格" && !!n.gridN;
  }
  function nineCellRect(sheetW, sheetH, n, index, gap) {
    gap = gap == null ? NINE_SHEET_GAP : Number(gap);
    n = Math.max(1, Number(n) || 3);
    const i = Math.max(0, Number(index) || 0);
    const cellW = (Number(sheetW) - (n + 1) * gap) / n;
    const cellH = (Number(sheetH) - (n + 1) * gap) / n;
    const col = i % n;
    const row = Math.floor(i / n);
    return {
      x: gap + col * (cellW + gap),
      y: gap + row * (cellH + gap),
      w: cellW,
      h: cellH,
    };
  }
  function classifySelected() {
    const n = nodeById(state.selected);
    if (!n) return { kind: "none", node: null };
    if (n.kind === "text") return { kind: "text", node: n };
    if (n.kind === "group") return { kind: "group", node: n };
    if (n.kind !== "shot") return { kind: "asset", node: n };
    if (isNineGridNode(n)) return { kind: "nine_grid", node: n };
    if (n.url && isVideoUrl(n.url)) return { kind: "video", node: n };
    if (n.url && !isVideoUrl(n.url)) return { kind: "image", node: n };
    return { kind: "blank", node: n };
  }

  function fillShotBar(kind) {
    const bar = $("shotBar");
    if (!bar) return;
    const items =
      kind === "video"
        ? SHOTBAR_VIDEO_ITEMS
        : kind === "nine_grid"
          ? SHOTBAR_NINE_ITEMS
          : kind === "group"
            ? SHOTBAR_GROUP_ITEMS
            : kind === "image"
              ? SHOTBAR_IMAGE_ITEMS
              : [];
    if (bar.dataset.variant === kind && bar.childElementCount === items.length)
      return;
    bar.dataset.variant = kind || "";
    bar.innerHTML = items
      .map((it) => {
        return (
          '<button type="button" id="' +
          it.id +
          '"' +
          (it.skip
            ? ' class="skip" title="' + esc(it.reason || "") + '"'
            : "") +
          ">" +
          it.label +
          "</button>"
        );
      })
      .join("");
  }

  function placeBlankPill(node) {
    const pill = $("blankPill");
    const stage = document.querySelector(".stage");
    if (!pill || !stage || !node) return;
    const label = state.mode === "text" ? "编辑文本" : "上传";
    pill.textContent = label;
    pill.dataset.act = state.mode === "text" ? "edit-text" : "upload";
    const el = world.querySelector('.card[data-id="' + node.id + '"]');
    if (!el) {
      pill.style.display = "none";
      return;
    }
    const r = el.getBoundingClientRect();
    const s = stage.getBoundingClientRect();
    pill.style.display = "flex";
    pill.style.left = Math.max(8, r.left - s.left) + "px";
    pill.style.top = Math.max(8, r.top - s.top - 42) + "px";
  }

  function placeShotBar() {
    const bar = $("shotBar");
    const pill = $("blankPill");
    if (!bar) return;
    if (
      panelOpen("camPanel") ||
      panelOpen("lightPanel") ||
      inpaintUi.on ||
      panelOpen("ninePicker")
    ) {
      bar.style.display = "none";
      if (pill) pill.style.display = "none";
      return;
    }
    const cls = classifySelected();
    const stage = document.querySelector(".stage");
    if (pill) pill.style.display = "none";
    const showBar =
      cls.kind === "image" ||
      cls.kind === "video" ||
      cls.kind === "nine_grid" ||
      cls.kind === "group";
    if (!stage || !showBar) {
      bar.style.display = "none";
      if (cls.kind === "blank") placeBlankPill(cls.node);
      return;
    }
    fillShotBar(cls.kind);
    const el = world.querySelector('.card[data-id="' + cls.node.id + '"]');
    if (!el) {
      bar.style.display = "none";
      return;
    }
    const r = el.getBoundingClientRect();
    const s = stage.getBoundingClientRect();
    bar.style.display = "flex";
    const bw = Math.min(bar.offsetWidth || 0, Math.max(0, s.width - 16));
    const cx = r.left - s.left + r.width / 2;
    bar.style.left =
      Math.max(8, Math.min(cx - bw / 2, s.width - bw - 8)) + "px";
    bar.style.top = Math.max(8, r.top - s.top - 42) + "px";
  }

  function placeDock() {
    const d = $("dock");
    const stage = document.querySelector(".stage");
    if (!d || !stage) return;
    if (!d.classList.contains("show")) {
      d.classList.remove("node-attached");
      d.style.left = "";
      d.style.top = "";
      d.style.bottom = "";
      d.style.transform = "";
      return;
    }
    const cls = classifySelected();
    const el =
      cls.node && world.querySelector('.card[data-id="' + cls.node.id + '"]');
    if (!el) {
      d.classList.remove("node-attached");
      d.style.left = "";
      d.style.top = "";
      d.style.bottom = "";
      d.style.transform = "";
      return;
    }
    const r = el.getBoundingClientRect();
    const s = stage.getBoundingClientRect();
    const dw = Math.min(820, Math.max(360, s.width - 80));
    let left = r.left - s.left + (r.width - dw) / 2;
    left = Math.max(12, Math.min(left, s.width - dw - 12));
    let top = r.bottom - s.top + 10;
    const maxTop = Math.max(8, s.height - Math.max(d.offsetHeight, 120) - 12);
    if (top > maxTop) top = maxTop;
    if (top < 8) top = 8;
    d.classList.add("node-attached");
    d.style.transform = "none";
    d.style.bottom = "auto";
    d.style.width = dw + "px";
    d.style.left = left + "px";
    d.style.top = top + "px";
  }

  function preferDockModel() {
    const sel = $("service");
    if (!sel || sel.options.length < 2) return;
    const cls = classifySelected();
    let keys = [];
    if (state.mode === "image" || cls.kind === "image")
      keys = ["即梦", "jimeng", "seedream", "dreamina"];
    else if (state.mode === "video" || cls.kind === "video")
      keys = ["可灵", "kling", "vidu", "Vidu"];
    else if (state.mode === "text") keys = ["Qwen", "qwen"];
    if (!keys.length) return;
    for (let i = 0; i < sel.options.length; i++) {
      const t = sel.options[i].textContent || sel.options[i].value || "";
      if (keys.some((k) => t.indexOf(k) >= 0)) {
        sel.selectedIndex = i;
        return;
      }
    }
  }

  function applySelectionDefaults() {
    const cls = classifySelected();
    const key = String(state.selected || "") + ":" + cls.kind;
    if (key === sekoSelKey) return;
    sekoSelKey = key;
    resetScopedMsg();
    const keepStory =
      toolUi.story && (cls.kind === "text" || cls.kind === "blank");
    closeAllToolPanels();
    toolUi.nine = false;
    toolUi.nineCrop = false;
    if (!keepStory && cls.kind !== "text") toolUi.story = false;
    if (cls.kind === "image") {
      state.mode = "image";
      if ($("aspect") && !$("aspect").querySelector('option[value="3:4"]')) {
        const o = document.createElement("option");
        o.value = "3:4";
        o.textContent = "3:4";
        $("aspect").appendChild(o);
      }
      if ($("aspect")) $("aspect").value = "16:9";
      if ($("res")) $("res").value = "720P";
    } else if (cls.kind === "video") {
      state.mode = "video";
      if ($("duration")) $("duration").value = "5s";
      if ($("res")) $("res").value = "720P";
    } else if (cls.kind === "text" || cls.kind === "blank") {
      state.mode = "text";
    } else if (cls.kind === "group" || cls.kind === "nine_grid") {
      closeAllToolPanels();
    }
    if (typeof loadCatalog === "function") loadCatalog();
  }

  function decorateVideoDock() {
    const refs = $("refs");
    if (!refs) return;
    if (state.mode !== "video") {
      const tail = refs.querySelector(".frame-slot-tail");
      if (tail) tail.remove();
      return;
    }
    refs.querySelectorAll(".frame-slot").forEach((el) => {
      if (el.classList.contains("frame-slot-tail")) return;
      if (el.innerHTML.indexOf("首帧") >= 0)
        el.innerHTML = el.innerHTML.replace("首帧", "图片1");
    });
    if (!refs.querySelector(".frame-slot-tail")) {
      const n = nodeById(state.selected);
      const tail = n && n.lastFrameId ? nodeById(n.lastFrameId) : null;
      const html =
        tail && tail.url
          ? '<div class="frame-slot frame-slot-tail">尾帧 <img src="' +
            esc(tail.url) +
            '" alt="">' +
            esc(sourceTitle(tail)) +
            "</div>"
          : '<div class="frame-slot frame-slot-tail">尾帧</div>';
      const first = refs.querySelector(".frame-slot");
      if (first) first.insertAdjacentHTML("afterend", html);
      else refs.insertAdjacentHTML("afterbegin", html);
    }
  }

  function syncDockVisibility() {
    const cls = classifySelected();
    if (
      cls.kind === "none" ||
      cls.kind === "nine_grid" ||
      cls.kind === "group" ||
      cls.kind === "asset"
    ) {
      dock.classList.remove("show");
    } else if (
      cls.kind === "blank" ||
      cls.kind === "image" ||
      cls.kind === "video" ||
      cls.kind === "text"
    ) {
      dock.classList.add("show");
    }
  }

  function hideGridMenu() {
    const m = $("gridSplitMenu");
    if (m) m.style.display = "none";
  }
  function toggleGridMenu(ev) {
    const menu = $("gridSplitMenu");
    const stage = document.querySelector(".stage");
    if (!menu || !stage) return;
    const on = menu.style.display === "block";
    if (on) {
      hideGridMenu();
      return;
    }
    if (!selectedShotImage()) {
      setMsg("先选中一张已出图的分镜再切分", "warn");
      return;
    }
    closeCamPanel();
    closeLightPanel();
    closeInpaintBar();
    closeNinePicker();
    const src =
      (ev && ev.currentTarget) || $("btnGridSplitBar") || $("btnGridSplit");
    const r = src.getBoundingClientRect();
    const s = stage.getBoundingClientRect();
    menu.style.display = "block";
    menu.style.left = r.left - s.left + "px";
    menu.style.top = r.bottom - s.top + 6 + "px";
    setMsg("画面切分：请选择 2×2 / 3×3 / 4×4 / 5×5", "ok", "gridSplit");
  }

  function zoomLabel(slot) {
    if (Number(slot) <= 0) return "特写";
    if (Number(slot) >= 2) return "广角";
    return "中景";
  }

  function setCamMsg(t, cls) {
    const el = $("camMsg");
    if (!el) return;
    el.textContent = t || "";
    el.className = "cam-msg" + (cls ? " " + cls : "");
  }

  function syncCamControls() {
    if ($("camYaw")) $("camYaw").value = String(camUi.yaw);
    if ($("camPitch")) $("camPitch").value = String(camUi.pitch);
    if ($("camZoom")) $("camZoom").value = String(camUi.zoom);
    if ($("camYawVal")) $("camYawVal").textContent = String(camUi.yaw);
    if ($("camPitchVal")) $("camPitchVal").textContent = String(camUi.pitch);
    if ($("camZoomVal")) $("camZoomVal").textContent = zoomLabel(camUi.zoom);
    document.querySelectorAll("#camTabs [data-camtab]").forEach((b) => {
      b.classList.toggle("on", b.dataset.camtab === camUi.tab);
    });
    const thumb = document.querySelector("#camThumb img");
    const shot = selectedShotImage();
    if (thumb) thumb.src = shot ? shotImageUrl(shot) : "";
    const wrap = $("camThumb");
    if (wrap) {
      const ry = camUi.yaw * 0.35;
      const rx = -camUi.pitch * 0.6;
      const sc = camUi.zoom <= 0 ? 1.18 : camUi.zoom >= 2 ? 0.82 : 1;
      wrap.style.transform =
        "rotateY(" + ry + "deg) rotateX(" + rx + "deg) scale(" + sc + ")";
    }
  }

  function resetCamParams() {
    camUi.tab = "custom";
    camUi.yaw = 0;
    camUi.pitch = 0;
    camUi.zoom = 1;
    camUi.prompt = "";
    syncCamControls();
    setCamMsg("");
  }

  function applyCamTab(id) {
    const t = CAM_TABS.find((x) => x.id === id) || CAM_TABS[0];
    camUi.tab = t.id;
    camUi.yaw = t.yaw;
    camUi.pitch = t.pitch;
    camUi.zoom = t.zoom;
    camUi.prompt = t.prompt;
    syncCamControls();
  }

  function dockReservePx() {
    const d = $("dock");
    if (d && d.classList.contains("show")) {
      return Math.max(132, d.getBoundingClientRect().height + 28);
    }
    return 48;
  }
  function placeFloating(id, preferBelow) {
    const p = $(id);
    const stage = document.querySelector(".stage");
    if (!p || !stage) return;
    const shot = selectedShotImage();
    const el = shot && world.querySelector('.card[data-id="' + shot.id + '"]');
    const s = stage.getBoundingClientRect();
    p.style.display = "block";
    const reserve = dockReservePx();
    p.style.maxHeight = Math.max(160, s.height - reserve - 8) + "px";
    const maxTop = Math.max(8, s.height - p.offsetHeight - reserve);
    let left = 80;
    let top = 72;
    if (el) {
      const r = el.getBoundingClientRect();
      left = Math.min(
        Math.max(12, r.left - s.left),
        Math.max(12, s.width - p.offsetWidth - 12),
      );
      top = preferBelow ? r.bottom - s.top + 10 : r.top - s.top;
    }
    if (top > maxTop) top = maxTop;
    if (top < 8) top = 8;
    p.style.left = left + "px";
    p.style.top = top + "px";
  }

  function placeCamPanel() {
    placeFloating("camPanel", true);
  }

  function openCamPanel() {
    const shot = selectedShotImage();
    if (!shot) {
      setMsg("先选中一张已出图的分镜再换机位", "warn");
      return;
    }
    closeLightPanel();
    closeInpaintBar();
    hideGridMenu();
    closeNinePicker();
    ensureSekoDom();
    if (camUi.tab === "custom" && camUi.yaw === 0 && camUi.pitch === 0)
      resetCamParams();
    placeCamPanel();
    syncCamControls();
    setCamMsg("");
    clearMsgFrom("inpaint");
    setMsg("多角度：调整镜头后点击面板生成", "ok", "cameraAngle");
    placeShotBar();
  }

  function closeCamPanel() {
    const p = $("camPanel");
    if (p) p.style.display = "none";
    placeShotBar();
  }

  function nudgeCam(dir) {
    if (dir === "w") camUi.yaw = Math.max(-90, camUi.yaw - 15);
    if (dir === "e") camUi.yaw = Math.min(180, camUi.yaw + 15);
    if (dir === "n") camUi.pitch = Math.min(30, camUi.pitch + 5);
    if (dir === "s") camUi.pitch = Math.max(-30, camUi.pitch - 5);
    camUi.tab = "custom";
    syncCamControls();
  }

  function paintGridOverlays() {
    world.querySelectorAll(".card.shot").forEach((el) => {
      el.querySelectorAll(".grid-split-ov").forEach((x) => x.remove());
      const n = nodeById(el.dataset.id);
      const g = n && n.gridN;
      if (!g) return;
      const host = el.querySelector(".face") || el;
      const ov = document.createElement("div");
      ov.className = "grid-split-ov";
      ov.style.gridTemplateColumns = "repeat(" + g + ",1fr)";
      ov.style.gridTemplateRows = "repeat(" + g + ",1fr)";
      const picking =
        toolUi.nineCrop && state.selected === n.id && isNineGridNode(n);
      if (picking) ov.classList.add("pick");
      for (let i = 0; i < g * g; i++) {
        const cell = document.createElement("i");
        if (picking) cell.dataset.ninecell = String(i);
        ov.appendChild(cell);
      }
      if (picking) {
        ov.addEventListener("pointerdown", (e) => {
          e.preventDefault();
          e.stopPropagation();
          const cell = e.target.closest("[data-ninecell]");
          if (!cell) return;
          extractNineGridCell(n, Number(cell.dataset.ninecell));
        });
      }
      host.appendChild(ov);
    });
  }

  function loadShotImage(url) {
    return new Promise((resolve, reject) => {
      const img = new Image();
      img.crossOrigin = "anonymous";
      img.onload = () => resolve(img);
      img.onerror = () => reject(new Error("切分读图失败"));
      img.src = url;
    });
  }

  function drawGridCard(img, n) {
    const gap = NINE_SHEET_GAP;
    const tw = Math.floor(img.naturalWidth / n);
    const th = Math.floor(img.naturalHeight / n);
    const cw = n * tw + (n + 1) * gap;
    const ch = n * th + (n + 1) * gap;
    const cv = document.createElement("canvas");
    cv.width = cw;
    cv.height = ch;
    const ctx = cv.getContext("2d");
    ctx.fillStyle = "#121214";
    ctx.fillRect(0, 0, cw, ch);
    for (let r = 0; r < n; r++) {
      for (let c = 0; c < n; c++) {
        ctx.drawImage(
          img,
          c * tw,
          r * th,
          tw,
          th,
          gap + c * (tw + gap),
          gap + r * (th + gap),
          tw,
          th,
        );
      }
    }
    return cv.toDataURL("image/jpeg", 0.92);
  }

  async function splitShotGrid(n) {
    hideGridMenu();
    const shot = selectedShotImage();
    if (!shot) {
      setMsg("先选中一张已出图的分镜再切分", "warn");
      return;
    }
    const spec = GRID_OPTS.find((g) => g.n === n) || GRID_OPTS[0];
    setMsg("正在本地切分 " + spec.name + "…");
    try {
      const img = await loadShotImage(shotImageUrl(shot));
      const dataUrl = drawGridCard(img, n);
      const id = uid("shot");
      const card = {
        id: id,
        kind: "shot",
        title: spec.name,
        x: shot.x + 720,
        y: shot.y,
        url: dataUrl,
        firstFrameId: "",
        prompt:
          (shot.prompt || "") +
          "\n【" +
          spec.name +
          " " +
          spec.cells +
          " 本地切分】",
        gridN: n,
        gridGap: NINE_SHEET_GAP,
        gridFrom: shot.id,
      };
      state.nodes.push(card);
      selectNode(id);
      persist();
      setMsg(spec.name + "已落成宫格卡（本地切分，未调用 generate）", "ok");
    } catch (e) {
      shot.gridN = n;
      renderCards();
      drawWires();
      persist();
      setMsg(
        "画布已标 " + spec.cells + " 宫格；像素导出被跨域挡住，未写新图",
        "warn",
      );
    }
  }

  async function pickCatalogService(backend, category) {
    const r = await fetch(
      "/api/catalog?backend=" +
        encodeURIComponent(backend) +
        "&category=" +
        encodeURIComponent(category),
    );
    const j = await r.json();
    const items = j.items || j.models || [];
    const selected = $("service") && $("service").value;
    if (selected && items.some((it) => (it.id || it.name) === selected))
      return selected;
    const it = items[0];
    return (it && (it.id || it.name)) || "";
  }
  async function pickCameraAngleService(backend) {
    return pickCatalogService(backend, "cameraAngle");
  }

  // 一次瞬时 502/504/读超时不能把已付费的任务丢掉（画布 civitai 实测复现：
  // job 12100372-20260906140244995 四次 200 后一次 502 → 轮询整个中断，钱扣了图不取）。
  // 口径同工作台 static/index.html poll()：硬错（404/401/403）立即抛，其余退避重试 8 次。
  async function fetchJobState(jobId) {
    const response = await fetch("/api/jobs/" + encodeURIComponent(jobId));
    let body = null;
    try {
      body = await response.json();
    } catch (_) {
      body = null;
    }
    if (!response.ok) {
      const err = new Error((body && body.error) || "HTTP " + response.status);
      err.status = response.status;
      err.hard =
        response.status === 404 ||
        response.status === 401 ||
        response.status === 403;
      throw err;
    }
    return body || {};
  }
  // 上限对齐工作台 poll()（180 轮 × 2.5s）：画布原来 40 轮 ≈100 秒就撒手，
  // civitai 排队稍久就把已付费的任务丢在云上（实测 job 12100372-20260906140958223 即此）。
  const POLL_TICKS = 180;
  async function pollJob(jobId, onTick) {
    let fails = 0;
    for (let i = 0; i < POLL_TICKS; i++) {
      await new Promise((res) => setTimeout(res, 2500));
      let st;
      try {
        st = await fetchJobState(jobId);
        fails = 0;
      } catch (e) {
        if (e.hard) throw e;
        fails += 1;
        if (fails >= 8) throw e;
        setMsg(
          "任务查询失败，重连中 " +
            fails +
            "/8 · " +
            String(e.message || e).slice(0, 60),
          "warn",
        );
        await new Promise((res) => setTimeout(res, Math.min(3000 * fails, 15000)));
        continue;
      }
      if (st.error || st.status === "failed")
        throw new Error(st.error || "任务失败");
      if (
        pickUrl(st) ||
        st.status === "done" ||
        st.status === "succeeded" ||
        st.status === "completed"
      )
        return st;
      if (onTick) onTick(i + 1);
    }
    return null;
  }

  function buildCameraAngleGraph(shot, serviceId) {
    const falH = mapSekoYawToFal(camUi.yaw);
    const falV = mapSekoPitchToFal(camUi.pitch);
    const falZ = mapSekoZoomToFal(camUi.zoom);
    return {
      backend: $("backend").value,
      nodes: [
        {
          id: "src-" + shot.id,
          op: "image",
          params: { url: shotImageUrl(shot) },
        },
        {
          id: shot.id,
          op: "camera-angle",
          params: {
            serviceId: serviceId,
            horizontalAngle: falH,
            verticalAngle: falV,
            zoom: falZ,
            additionalPrompt: camUi.prompt || "",
            sekoYaw: camUi.yaw,
            sekoPitch: camUi.pitch,
            sekoZoom: camUi.zoom,
            sekoTab: camUi.tab,
          },
        },
      ],
      edges: [
        {
          from: "src-" + shot.id,
          fromPort: "image",
          to: shot.id,
          toPort: "image",
        },
      ],
    };
  }

  async function runCompiledGenerate(graph, onMsg) {
    onMsg("校验连线…");
    const r = await fetch("/api/graph/compile", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(graph),
    });
    const compiled = await r.json();
    if (!compiled.ok) throw new Error(compiled.error || "校验未通过");
    const payload =
      compiled.payload ||
      (compiled.stages && compiled.stages[0] && compiled.stages[0].payload);
    if (!payload) throw new Error("没有 payload");
    onMsg("正在请求云 API…");
    const g = await fetch("/api/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    let j = await g.json();
    if (!g.ok || j.error) throw new Error(j.error || "HTTP " + g.status);
    const jobId = j.id || j.jobId || j.workflowId;
    if (jobId && !pickUrl(j)) {
      const st = await pollJob(jobId, (n) =>
        onMsg("云端进行中 " + n + "/" + POLL_TICKS),
      );
      if (st) j = st;
    }
    return pickUrl(j);
  }

  async function generateCameraAngle() {
    const shot = selectedShotImage();
    if (!shot) {
      setCamMsg("先选中一张已出图的分镜", "bad");
      return;
    }
    const backend = $("backend").value;
    const sendBtn = $("camSend");
    if (sendBtn) sendBtn.disabled = true;
    setCamMsg("正在挑选多角度模型…");
    let serviceId = "";
    try {
      serviceId = await pickCameraAngleService(backend);
    } catch (_) {}
    if (!serviceId) {
      setCamMsg(
        "当前后端 " +
          backend +
          " 目录里没有多角度模型（category=cameraAngle）。未选模型不会回退硬编码 fal id。",
        "bad",
      );
      if (sendBtn) sendBtn.disabled = false;
      return;
    }
    try {
      const url = await runCompiledGenerate(
        buildCameraAngleGraph(shot, serviceId),
        (t) => setCamMsg(t),
      );
      if (url) {
        shot.url = url;
        promoteResult(shot, url);
        renderCards();
        drawWires();
        persist();
        syncCamControls();
        setCamMsg("多角度完成", "ok");
        setMsg("多角度完成", "ok");
      } else setCamMsg("云端已返回，没有可预览地址", "warn");
    } catch (e) {
      setCamMsg(String(e), "bad");
    }
    if (sendBtn) sendBtn.disabled = false;
  }

  function setLightMsg(t, cls) {
    const el = $("lightMsg");
    if (!el) return;
    el.textContent = t || "";
    el.className = "light-msg" + (cls ? " " + cls : "");
  }
  function lightDirSpec() {
    return LIGHT_DIRS.find((d) => d.id === lightUi.dir) || LIGHT_DIRS[0];
  }
  function lightDirSupported(d) {
    return !!(d && d.latent);
  }
  function fallbackLightPrompt() {
    const desc = String(lightUi.desc || "").trim();
    const d = lightDirSpec();
    const parts = [];
    if (desc) parts.push(desc);
    else parts.push(d.prompt);
    parts.push(lightUi.soft ? "soft light" : "hard light");
    parts.push("brightness " + lightUi.brightness + "%");
    if (lightUi.colorMode === "kelvin")
      parts.push("color temperature " + lightUi.kelvin + " K");
    else parts.push("light color " + lightUi.hex);
    if (lightUi.rim) parts.push("rim light");
    if (lightUi.preset >= 0 && LIGHT_PRESETS[lightUi.preset])
      parts.push(LIGHT_PRESETS[lightUi.preset].prompt);
    return parts.join(", ");
  }
  function syncLightControls() {
    const shot = selectedShotImage();
    document
      .querySelectorAll("#lightView [data-lview]")
      .forEach((b) =>
        b.classList.toggle("on", b.dataset.lview === lightUi.view),
      );
    document
      .querySelectorAll("#lightSoft [data-lsoft]")
      .forEach((b) =>
        b.classList.toggle("on", (b.dataset.lsoft === "1") === lightUi.soft),
      );
    document.querySelectorAll("#lightColorMode [data-lcmode]").forEach((b) => {
      b.classList.toggle("on", b.dataset.lcmode === lightUi.colorMode);
    });
    document.querySelectorAll("#lightDirs [data-ldir]").forEach((b) => {
      b.classList.toggle("on", b.dataset.ldir === lightUi.dir);
    });
    if ($("lightSend"))
      $("lightSend").disabled = !lightDirSupported(lightDirSpec());
    if (!lightDirSupported(lightDirSpec()))
      setLightMsg("该方向 fal 不支持", "warn");
    document.querySelectorAll("#lightPresets [data-lpreset]").forEach((b) => {
      b.classList.toggle("on", Number(b.dataset.lpreset) === lightUi.preset);
    });
    if ($("lightBright")) $("lightBright").value = String(lightUi.brightness);
    if ($("lightBrightNum"))
      $("lightBrightNum").value = String(lightUi.brightness);
    if ($("lightBrightVal"))
      $("lightBrightVal").textContent = String(lightUi.brightness);
    if ($("lightColor")) $("lightColor").value = lightUi.hex;
    if ($("lightHex")) $("lightHex").value = lightUi.hex;
    if ($("lightKelvin")) $("lightKelvin").value = String(lightUi.kelvin);
    if ($("lightKelvinVal"))
      $("lightKelvinVal").textContent = lightUi.kelvin + " K";
    if ($("lightRim")) $("lightRim").checked = !!lightUi.rim;
    const imageUrl = shot ? shotImageUrl(shot) : "";
    document.querySelectorAll("#lightPresets img").forEach((img) => {
      img.src = imageUrl;
      img.hidden = !imageUrl;
    });
    if ($("lightDesc") && $("lightDesc") !== document.activeElement)
      $("lightDesc").value = lightUi.desc;
    if ($("lightHexRow"))
      $("lightHexRow").style.display =
        lightUi.colorMode === "hex" ? "flex" : "none";
    if ($("lightKelvinRow"))
      $("lightKelvinRow").style.display =
        lightUi.colorMode === "kelvin" ? "block" : "none";
    const d = lightDirSpec();
    const dot = $("lightDot");
    if (dot) {
      dot.style.left = d.x * 100 + "%";
      dot.style.top = d.y * 100 + "%";
    }
    const thumb = document.querySelector("#lightThumb img");
    if (thumb) {
      thumb.src = imageUrl;
      thumb.hidden = !imageUrl;
    }
    const wrap = $("lightThumb");
    if (wrap) {
      wrap.style.transform =
        lightUi.view === "persp" ? "rotateX(18deg) rotateY(-12deg)" : "none";
    }
  }
  function resetLightParams() {
    lightUi.view = "persp";
    lightUi.soft = true;
    lightUi.brightness = 50;
    lightUi.colorMode = "hex";
    lightUi.hex = "#FFFFFF";
    lightUi.kelvin = 5000;
    lightUi.dir = "left";
    lightUi.rim = false;
    lightUi.desc = "";
    lightUi.preset = -1;
    syncLightControls();
    setLightMsg("");
  }
  function applyLightPreset(i) {
    const pr = LIGHT_PRESETS[i];
    if (!pr) return;
    lightUi.preset = i;
    lightUi.kelvin = pr.kelvin;
    lightUi.dir = pr.dir;
    lightUi.desc = pr.label;
    lightUi.colorMode = "kelvin";
    syncLightControls();
    if (!lightDirSupported(lightDirSpec()))
      setLightMsg("该方向 fal 不支持", "warn");
  }
  function snapLightDir(px, py) {
    let best = LIGHT_DIRS[0],
      bestD = 9;
    LIGHT_DIRS.forEach((d) => {
      if (!lightDirSupported(d)) return;
      const dd = (d.x - px) * (d.x - px) + (d.y - py) * (d.y - py);
      if (dd < bestD) {
        bestD = dd;
        best = d;
      }
    });
    lightUi.dir = best.id;
    lightUi.preset = -1;
    syncLightControls();
  }
  function placeLightPanel() {
    placeFloating("lightPanel", true);
  }
  function openLightPanel() {
    const shot = selectedShotImage();
    if (!shot) {
      setMsg("先选中一张已出图的分镜再打光", "warn");
      return;
    }
    closeCamPanel();
    closeInpaintBar();
    hideGridMenu();
    closeNinePicker();
    ensureSekoDom();
    placeLightPanel();
    setLightMsg("");
    syncLightControls();
    clearMsgFrom("inpaint");
    setMsg("打光：选择光源方向、预设后点击面板生成", "ok", "relight");
    placeShotBar();
  }
  function closeLightPanel() {
    const p = $("lightPanel");
    if (p) p.style.display = "none";
    placeShotBar();
  }
  function buildRelightGraph(shot, serviceId) {
    const d = lightDirSpec();
    const prompt = fallbackLightPrompt();
    const params = {
      serviceId: serviceId,
      lightDirection: d.id,
      lightColor: lightUi.hex,
      colorTemperature: lightUi.kelvin,
      brightness: lightUi.brightness,
      lightType: lightUi.soft ? "soft" : "hard",
      rimLight: !!lightUi.rim,
      perspective: lightUi.view,
      additionalPrompt: prompt,
      prompt: prompt,
    };
    if (d.latent) params.initialLatent = d.latent;
    return {
      backend: $("backend").value,
      nodes: [
        {
          id: "src-" + shot.id,
          op: "image",
          params: { url: shotImageUrl(shot) },
        },
        { id: shot.id, op: "relight", params: params },
      ],
      edges: [
        {
          from: "src-" + shot.id,
          fromPort: "image",
          to: shot.id,
          toPort: "image",
        },
      ],
    };
  }
  async function generateRelight() {
    const shot = selectedShotImage();
    if (!shot) {
      setLightMsg("先选中一张已出图的分镜", "bad");
      return;
    }
    if (!lightDirSupported(lightDirSpec())) {
      setLightMsg("该方向 fal 不支持", "bad");
      return;
    }
    const backend = $("backend").value;
    const sendBtn = $("lightSend");
    if (sendBtn) sendBtn.disabled = true;
    setLightMsg("正在挑选打光模型…");
    let serviceId = "";
    try {
      serviceId = await pickCatalogService(backend, "relight");
    } catch (_) {}
    if (!serviceId) {
      setLightMsg(
        "当前后端 " +
          backend +
          " 目录里没有打光模型（category=relight）。未选模型不会回退硬编码 fal id。",
        "bad",
      );
      if (sendBtn) sendBtn.disabled = false;
      return;
    }
    try {
      const url = await runCompiledGenerate(
        buildRelightGraph(shot, serviceId),
        (t) => setLightMsg(t),
      );
      if (url) {
        shot.url = url;
        promoteResult(shot, url);
        renderCards();
        drawWires();
        persist();
        syncLightControls();
        setLightMsg("打光完成", "ok");
        setMsg("打光完成", "ok");
      } else setLightMsg("云端已返回，没有可预览地址", "warn");
    } catch (e) {
      setLightMsg(String(e), "bad");
    }
    if (sendBtn) sendBtn.disabled = !lightDirSupported(lightDirSpec());
  }

  function ensureMaskCanvas(w, h) {
    if (
      !inpaintUi.mask ||
      inpaintUi.mask.width !== w ||
      inpaintUi.mask.height !== h
    ) {
      const cv = document.createElement("canvas");
      cv.width = w;
      cv.height = h;
      const ctx = cv.getContext("2d");
      ctx.fillStyle = "#000";
      ctx.fillRect(0, 0, w, h);
      inpaintUi.mask = cv;
      inpaintUi.undo = [];
      inpaintUi.redo = [];
    }
  }
  function snapshotMask() {
    if (!inpaintUi.mask) return;
    try {
      const ctx = inpaintUi.mask.getContext("2d");
      inpaintUi.undo.push(
        ctx.getImageData(0, 0, inpaintUi.mask.width, inpaintUi.mask.height),
      );
      if (inpaintUi.undo.length > 24) inpaintUi.undo.shift();
      inpaintUi.redo = [];
    } catch (_) {}
  }
  function restoreMask(data) {
    if (!inpaintUi.mask || !data) return;
    inpaintUi.mask.getContext("2d").putImageData(data, 0, 0);
    paintOverlayFromMask();
  }
  function paintOverlayFromMask() {
    const ov = inpaintUi.overlay;
    if (!ov || !inpaintUi.mask) return;
    const ctx = ov.getContext("2d");
    ctx.clearRect(0, 0, ov.width, ov.height);
    ctx.drawImage(inpaintUi.mask, 0, 0, ov.width, ov.height);
    ctx.globalCompositeOperation = "source-in";
    ctx.fillStyle = "rgba(255,255,255,.55)";
    ctx.fillRect(0, 0, ov.width, ov.height);
    ctx.globalCompositeOperation = "source-over";
  }
  function attachInpaintOverlay() {
    if (!inpaintUi.on) return;
    const shot = selectedShotImage();
    if (!shot) return;
    const face = world.querySelector('.card[data-id="' + shot.id + '"] .face');
    if (!face) return;
    face.querySelectorAll(".inpaint-cv").forEach((x) => x.remove());
    const img = face.querySelector("img");
    const w = (img && img.naturalWidth) || 640;
    const h = (img && img.naturalHeight) || 360;
    ensureMaskCanvas(w, h);
    const ov = document.createElement("canvas");
    ov.className = "inpaint-cv";
    ov.width = w;
    ov.height = h;
    face.appendChild(ov);
    inpaintUi.overlay = ov;
    inpaintUi.shotId = shot.id;
    paintOverlayFromMask();
    ov.addEventListener("pointerdown", onInpaintDown);
    ov.addEventListener("pointermove", onInpaintMove);
    ov.addEventListener("pointerup", onInpaintUp);
    ov.addEventListener("pointerleave", onInpaintUp);
  }
  function canvasPos(cv, e) {
    const r = cv.getBoundingClientRect();
    return {
      x: (e.clientX - r.left) * (cv.width / Math.max(1, r.width)),
      y: (e.clientY - r.top) * (cv.height / Math.max(1, r.height)),
    };
  }
  function strokeMask(x, y) {
    if (!inpaintUi.mask) return;
    const ctx = inpaintUi.mask.getContext("2d");
    ctx.lineCap = "round";
    ctx.lineJoin = "round";
    ctx.lineWidth = inpaintUi.size * (inpaintUi.mask.width / 640);
    if (inpaintUi.tool === "eraser") {
      ctx.globalCompositeOperation = "source-over";
      ctx.strokeStyle = "#000";
    } else {
      ctx.globalCompositeOperation = "source-over";
      ctx.strokeStyle = "#fff";
    }
    if (inpaintUi._last) {
      ctx.beginPath();
      ctx.moveTo(inpaintUi._last.x, inpaintUi._last.y);
      ctx.lineTo(x, y);
      ctx.stroke();
    } else {
      ctx.beginPath();
      ctx.arc(x, y, ctx.lineWidth / 2, 0, Math.PI * 2);
      ctx.fillStyle = ctx.strokeStyle;
      ctx.fill();
    }
    inpaintUi._last = { x: x, y: y };
    paintOverlayFromMask();
  }
  function onInpaintDown(e) {
    e.stopPropagation();
    e.preventDefault();
    if (!inpaintUi.on) return;
    inpaintUi.drawing = true;
    snapshotMask();
    inpaintUi._last = null;
    const p = canvasPos(inpaintUi.overlay, e);
    strokeMask(p.x, p.y);
    try {
      inpaintUi.overlay.setPointerCapture(e.pointerId);
    } catch (_) {}
  }
  function onInpaintMove(e) {
    const cur = $("inpaintCursor");
    if (cur && inpaintUi.on) {
      const s = inpaintUi.size * (state.cam.s || 1);
      cur.style.display = "block";
      cur.style.width = s + "px";
      cur.style.height = s + "px";
      cur.style.left = e.clientX - s / 2 + "px";
      cur.style.top = e.clientY - s / 2 + "px";
    }
    if (!inpaintUi.drawing) return;
    e.stopPropagation();
    const p = canvasPos(inpaintUi.overlay, e);
    strokeMask(p.x, p.y);
  }
  function onInpaintUp(e) {
    if (e && e.type === "pointerup") e.stopPropagation();
    inpaintUi.drawing = false;
    inpaintUi._last = null;
  }
  function exportInpaintMaskPng() {
    if (!inpaintUi.mask) return "";
    const cv = document.createElement("canvas");
    cv.width = inpaintUi.mask.width;
    cv.height = inpaintUi.mask.height;
    const ctx = cv.getContext("2d");
    ctx.fillStyle = "#000";
    ctx.fillRect(0, 0, cv.width, cv.height);
    ctx.drawImage(inpaintUi.mask, 0, 0);
    return cv.toDataURL("image/png");
  }
  async function sekoCommitMask(maskDataUrl) {
    if (typeof window.__sekoUploadMask === "function") {
      const uploaded = await window.__sekoUploadMask(maskDataUrl);
      return uploaded || maskDataUrl;
    }
    return maskDataUrl;
  }
  function placeEraseBar() {
    const bar = $("eraseBar");
    if (!bar) return;
    if (!inpaintUi.on) {
      bar.style.display = "none";
      return;
    }
    const shot = selectedShotImage();
    const stage = document.querySelector(".stage");
    if (!shot || !stage) {
      bar.style.display = "none";
      return;
    }
    const el = world.querySelector('.card[data-id="' + shot.id + '"]');
    if (!el) {
      bar.style.display = "none";
      return;
    }
    const r = el.getBoundingClientRect();
    const s = stage.getBoundingClientRect();
    bar.style.display = "flex";
    bar.style.left = Math.max(8, r.left - s.left) + "px";
    bar.style.top = Math.max(8, r.top - s.top - 50) + "px";
    $("eraseBrush").classList.toggle("on", inpaintUi.tool === "brush");
    $("eraseEraser").classList.toggle("on", inpaintUi.tool === "eraser");
    $("eraseSize").value = String(inpaintUi.size);
  }
  function openInpaintBar() {
    const shot = selectedShotImage();
    if (!shot) {
      setMsg("先选中一张已出图的分镜再消除", "warn");
      return;
    }
    closeCamPanel();
    closeLightPanel();
    hideGridMenu();
    closeNinePicker();
    ensureSekoDom();
    inpaintUi.on = true;
    inpaintUi.tool = "brush";
    attachInpaintOverlay();
    placeEraseBar();
    placeShotBar();
    setMsg(
      "在图上圈选要消除的区域，再点「消除 ◆1」。未点发送。",
      "ok",
      "inpaint",
    );
  }
  function closeInpaintBar() {
    inpaintUi.on = false;
    inpaintUi.drawing = false;
    world.querySelectorAll(".inpaint-cv").forEach((x) => x.remove());
    inpaintUi.overlay = null;
    if ($("eraseBar")) $("eraseBar").style.display = "none";
    if ($("inpaintCursor")) $("inpaintCursor").style.display = "none";
    placeShotBar();
  }
  function buildInpaintGraph(shot, serviceId, maskUrl) {
    return {
      backend: $("backend").value,
      nodes: [
        {
          id: "src-" + shot.id,
          op: "image",
          params: { url: shotImageUrl(shot) },
        },
        {
          id: shot.id,
          op: "inpaint",
          params: { serviceId: serviceId, maskUrl: maskUrl },
        },
      ],
      edges: [
        {
          from: "src-" + shot.id,
          fromPort: "image",
          to: shot.id,
          toPort: "image",
        },
      ],
    };
  }
  async function generateInpaint() {
    const shot = selectedShotImage();
    if (!shot) {
      setMsg("先选中一张已出图的分镜", "bad");
      return;
    }
    const dataUrl = exportInpaintMaskPng();
    if (!dataUrl) {
      setMsg("先圈选要消除的区域", "warn");
      return;
    }
    const backend = $("backend").value;
    const go = $("eraseGo");
    if (go) go.disabled = true;
    setMsg("正在导出 mask…");
    let maskUrl;
    try {
      maskUrl = await sekoCommitMask(dataUrl);
    } catch (e) {
      setMsg("mask 导出失败：" + e, "bad");
      if (go) go.disabled = false;
      return;
    }
    setMsg("正在挑选消除模型…");
    let serviceId = "";
    try {
      serviceId = await pickCatalogService(backend, "inpaint");
    } catch (_) {}
    if (!serviceId) {
      setMsg(
        "当前后端 " +
          backend +
          " 目录里没有消除模型（category=inpaint）。未选模型不会回退硬编码 fal id。",
        "bad",
      );
      if (go) go.disabled = false;
      return;
    }
    try {
      const url = await runCompiledGenerate(
        buildInpaintGraph(shot, serviceId, maskUrl),
        (t) => setMsg(t),
      );
      if (url) {
        shot.url = url;
        promoteResult(shot, url);
        inpaintUi.mask = null;
        renderCards();
        drawWires();
        persist();
        attachInpaintOverlay();
        setMsg("消除完成", "ok");
      } else setMsg("云端已返回，没有可预览地址", "warn");
    } catch (e) {
      setMsg(String(e), "bad");
    }
    if (go) go.disabled = false;
  }

  function storyResolution() {
    const a = storyUi.aspect || "16:9";
    if (a === "9:16") return "720x1280";
    if (a === "3:4") return "768x1024";
    if (a === "4:3") return "1024x768";
    return "1280x720";
  }
  function syncStoryControls() {
    if ($("storyBack")) $("storyBack").value = String(storyUi.backward);
    if ($("storyForward")) $("storyForward").value = String(storyUi.forward);
    if ($("storyBackVal"))
      $("storyBackVal").textContent = storyUi.backward + "s";
    if ($("storyForwardVal"))
      $("storyForwardVal").textContent = storyUi.forward + "s";
    document.querySelectorAll("[data-story-aspect]").forEach((b) => {
      b.classList.toggle("on", b.dataset.storyAspect === storyUi.aspect);
    });
    document.querySelectorAll("[data-story-model]").forEach((b) => {
      b.classList.toggle("on", b.dataset.storyModel === storyUi.modelType);
    });
  }
  function storyFramePrompt(storyText, spec) {
    const modelLabel = storyUi.modelType === "pro" ? "专业模型" : "通用模型";
    return [
      "故事导演分镜：" + spec.label + " " + spec.seconds + "s",
      "画面比例：" + storyUi.aspect,
      "模型档位：" + modelLabel,
      "根据下面故事推演生成一个连续分镜画面，保持角色、场景、光线一致。",
      storyText,
    ].join("\n");
  }
  function buildStoryFrameGraph(
    backend,
    serviceId,
    promptText,
    frameId,
    seedShot,
  ) {
    const source = seedShot && shotImageUrl(seedShot);
    const nodes = [
      { id: "p-" + frameId, op: "prompt", params: { text: promptText } },
      {
        id: frameId,
        op: source ? "i2i" : "t2i",
        params: { serviceId: serviceId, resolution: storyResolution() },
      },
    ];
    const edges = [
      {
        from: "p-" + frameId,
        fromPort: "prompt",
        to: frameId,
        toPort: "prompt",
      },
    ];
    if (source) {
      nodes.push({
        id: "src-" + frameId,
        op: "image",
        params: { url: source },
      });
      edges.push({
        from: "src-" + frameId,
        fromPort: "image",
        to: frameId,
        toPort: "image",
      });
    }
    return { backend: backend, nodes: nodes, edges: edges };
  }
  function buildStoryGraph(seedShot, storyText, backend, serviceId) {
    return storySpecs().map((spec, i) =>
      buildStoryFrameGraph(
        backend,
        serviceId,
        storyFramePrompt(storyText, spec),
        "story-frame-" + i,
        seedShot,
      ),
    );
  }
  function storySpecs() {
    const out = [];
    if (storyUi.backward > 0)
      out.push({
        id: "backward",
        label: "向后推演",
        seconds: storyUi.backward,
      });
    if (storyUi.forward > 0)
      out.push({ id: "forward", label: "向前推演", seconds: storyUi.forward });
    if (!out.length)
      out.push({ id: "backward", label: "向后推演", seconds: 5 });
    return out;
  }
  async function planStoryText(model, text) {
    const r = await fetch(STORY_PLAN_ENDPOINT, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ backend: "nano-gpt", model: model, text: text }),
    });
    const j = await r.json();
    if (!r.ok || j.error) throw new Error(j.error || "HTTP " + r.status);
    return j.text || j.story || j.content || j.message || "";
  }
  async function generateStoryFrames(seedShot, storyText, textNode) {
    setMsg("故事推演：挑选图片模型…");
    const svc = await pickNineT2i();
    if (!svc.serviceId)
      throw new Error("故事推演找不到图片模型，不能只写文本空壳");
    // buildGraph → compile → generate → poll: each story frame uses runCompiledGenerate().
    const graphs = buildStoryGraph(
      seedShot,
      storyText,
      svc.backend,
      svc.serviceId,
    );
    const made = [];
    for (let i = 0; i < graphs.length; i++) {
      const spec = storySpecs()[i];
      const id = uid("shot");
      const graph = buildStoryFrameGraph(
        svc.backend,
        svc.serviceId,
        storyFramePrompt(storyText, spec),
        id,
        seedShot,
      );
      const url = await runCompiledGenerate(graph, (t) =>
        setMsg(spec.label + " " + t),
      );
      if (!url) throw new Error(spec.label + " 没有可预览地址");
      const base = seedShot || textNode;
      const node = {
        id: id,
        kind: "shot",
        title: spec.label + " " + spec.seconds + "s",
        x: base ? base.x + 720 * (i + 1) : 560 + 720 * i,
        y: base ? base.y + 40 * i : 80,
        url: url,
        firstFrameId: "",
        prompt: storyFramePrompt(storyText, spec),
        storyFrom: (seedShot && seedShot.id) || (textNode && textNode.id) || "",
      };
      state.nodes.push(node);
      if (seedShot) state.edges.push({ from: seedShot.id, to: id });
      if (textNode) state.edges.push({ from: textNode.id, to: id });
      promoteResult(node, url);
      made.push(node);
      renderCards();
      drawWires();
      persist();
    }
    return made;
  }

  function applyDockChrome() {
    const ta = $("prompt");
    if (ta) {
      if (toolUi.story) {
        ta.placeholder = PH_STORY;
        if (ta !== document.activeElement) ta.value = toolUi.storyText || "";
      } else if (toolUi.nine) {
        ta.placeholder = PH_NINE;
        if (ta !== document.activeElement) ta.value = toolUi.nineText || "";
      } else if (state.mode === "text") {
        ta.placeholder = PH_STORY;
        if (ta !== document.activeElement) {
          const n = nodeById(state.selected);
          ta.value =
            n && n.kind === "text" ? n.text || "" : toolUi.storyText || "";
        }
      } else if (state.mode === "image") {
        ta.placeholder = PH_IMAGE;
      } else if (state.mode === "video") {
        ta.placeholder = PH_VIDEO;
      } else if (state.mode === "audio") {
        ta.placeholder = PH_AUDIO;
      } else {
        ta.placeholder = PH_DEFAULT;
      }
    }
    const isText = toolUi.story || state.mode === "text";
    if (dock) dock.classList.toggle("story-mode", !!toolUi.story);
    if ($("storyControls"))
      $("storyControls").classList.toggle("show", !!toolUi.story);
    if (toolUi.story) syncStoryControls();
    const isVid = state.mode === "video";
    const isImg = state.mode === "image";
    if ($("duration"))
      $("duration").style.display = isVid && !toolUi.nine ? "" : "none";
    if ($("res"))
      $("res").style.display = (isImg || isVid) && !toolUi.nine ? "" : "none";
    if ($("aspect"))
      $("aspect").style.display =
        (isImg || isVid) && !toolUi.story && !isText ? "" : "none";
    if ($("service")) $("service").style.display = toolUi.nine ? "none" : "";
    if ($("backend")) $("backend").style.display = toolUi.nine ? "none" : "";
    if ($("dockCost")) {
      $("dockCost").textContent = toolUi.nine
        ? "18"
        : isVid
          ? "10"
          : isImg
            ? "7"
            : isText
              ? toolUi.story
                ? "10"
                : "1"
              : "";
    }
    if ($("storySkill"))
      $("storySkill").style.display = toolUi.story ? "inline-flex" : "none";
    if (toolUi.nine && $("aspect")) $("aspect").value = "16:9";
    if ($("send")) {
      $("send").title = "发送 (Cmd/Ctrl + Enter)";
      $("send").textContent = toolUi.story ? "生成 ◆10" : "↑";
    }
    decorateVideoDock();
    placeDock();
    placeShotBar();
  }
  function openStoryDock() {
    closeCamPanel();
    closeLightPanel();
    closeInpaintBar();
    hideGridMenu();
    closeNinePicker();
    toolUi.nine = false;
    toolUi.story = true;
    if ($("backend") && $("backend").value !== "nano-gpt") {
      toolUi.prevBackend = $("backend").value;
      $("backend").value = "nano-gpt";
    }
    state.mode = "text";
    const n = nodeById(state.selected);
    if (!n || (n.kind !== "shot" && n.kind !== "text")) {
      const id = uid("text");
      state.nodes.push({
        id: id,
        kind: "text",
        title: "故事推演",
        x: 220,
        y: 24,
        text: "",
      });
      selectNode(id);
    } else {
      dock.classList.add("show");
      renderDock();
    }
    applyDockChrome();
    loadStoryCatalog();
    setMsg(
      "故事推演：LLM 写故事，再 buildGraph → compile → generate → poll 回填分镜",
      "ok",
    );
  }
  function closeStoryDock() {
    toolUi.story = false;
    if (toolUi.prevBackend && $("backend")) {
      $("backend").value = toolUi.prevBackend;
      toolUi.prevBackend = "";
    }
    applyDockChrome();
  }
  async function loadStoryCatalog() {
    if (!$("service")) return;
    const seq = ++state._catalogSeq;
    $("service").innerHTML = '<option value="">选择故事模型</option>';
    try {
      const r = await fetch(
        "/api/catalog?backend=" +
          encodeURIComponent("nano-gpt") +
          "&category=text",
      );
      const j = await r.json();
      if (seq !== state._catalogSeq) return;
      dedupeCatalogItems(j.items || j.models || [])
        .slice(0, 60)
        .forEach((it) => {
          const id = it.id || it.name || "";
          const o = document.createElement("option");
          o.value = id;
          o.textContent = it.name || id;
          $("service").appendChild(o);
        });
      if (!$("service").value && $("service").options.length > 1)
        $("service").selectedIndex = 1;
    } catch (_) {}
  }
  async function generateStory() {
    const text = (
      toolUi.storyText ||
      ($("prompt") && $("prompt").value) ||
      ""
    ).trim();
    if (!text) {
      setMsg("先输入故事、场景或角色设定", "warn");
      return;
    }
    const model = $("service") && $("service").value;
    if (!model) {
      setMsg("故事推演必须显式选择模型，不会写死模型 id", "bad");
      return;
    }
    const seed = nodeById(state.selected);
    const seedShot = seed && seed.kind === "shot" ? seed : null;
    $("send").disabled = true;
    setMsg("故事导演撰写中…");
    try {
      const out = await planStoryText(model, text);
      if (!out) {
        setMsg("故事接口没有返回文本", "warn");
        $("send").disabled = false;
        return;
      }
      let node = seed && seed.kind === "text" ? seed : null;
      if (node) {
        node.text = out;
      } else {
        node = {
          id: uid("text"),
          kind: "text",
          title: "故事推演",
          x: seed ? seed.x + 360 : 220,
          y: seed ? seed.y : 24,
          text: out,
        };
        state.nodes.push(node);
        if (seed) state.edges.push({ from: seed.id, to: node.id });
      }
      const frames = await generateStoryFrames(seedShot, out, node);
      const last = frames[frames.length - 1] || node;
      selectNode(last.id);
      persist();
      setMsg(
        "故事推演完成：LLM 故事 + buildGraph → compile → generate → poll，已生成 " +
          frames.length +
          " 个分镜",
        "ok",
      );
    } catch (e) {
      setMsg(String(e && e.message ? e.message : e), "bad");
    }
    $("send").disabled = false;
  }

  function closeNinePicker() {
    const p = $("ninePicker");
    if (p) p.style.display = "none";
    placeShotBar();
  }
  function openNineGrid() {
    closeCamPanel();
    closeLightPanel();
    closeInpaintBar();
    hideGridMenu();
    ensureSekoDom();
    toolUi.story = false;
    toolUi.nine = true;
    placeFloating("ninePicker", false);
    document.querySelectorAll("#nineTypes [data-ninetype]").forEach((b) => {
      b.classList.toggle("on", b.dataset.ninetype === toolUi.nineType);
    });
    state.mode = "image";
    const n = nodeById(state.selected);
    if (n && (n.kind === "shot" || n.kind === "text")) {
      dock.classList.add("show");
      renderDock();
    } else {
      dock.classList.add("show");
    }
    applyDockChrome();
    placeShotBar();
    setMsg(
      "九宫格：选类型后在底栏输入提示词。拆解走 /api/grid/plan，再 N 次文生图拼一张卡。",
      "ok",
    );
  }
  function pickNineType(id) {
    toolUi.nineType = id;
    toolUi.nine = true;
    document.querySelectorAll("#nineTypes [data-ninetype]").forEach((b) => {
      b.classList.toggle("on", b.dataset.ninetype === id);
    });
    applyDockChrome();
  }
  async function pickNinePlannerModel() {
    const r = await fetch(
      "/api/catalog?backend=" +
        encodeURIComponent("nano-gpt") +
        "&category=text",
    );
    const j = await r.json();
    const items = j.items || j.models || [];
    const it = items[0];
    return (it && (it.id || it.name)) || "";
  }

  async function pickNineT2i() {
    const backends = [];
    const cur = $("backend") && $("backend").value;
    if (cur) backends.push(cur);
    ["fal", "nano-gpt", "modelscope-ai", "modelscope-cn"].forEach((b) => {
      if (backends.indexOf(b) < 0) backends.push(b);
    });
    for (let i = 0; i < backends.length; i++) {
      const b = backends[i];
      let serviceId = "";
      try {
        serviceId = await pickCatalogService(b, "image");
      } catch (_) {}
      if (serviceId) return { backend: b, serviceId: serviceId };
    }
    return { backend: "", serviceId: "" };
  }

  async function planNineGridPrompts(text, kind, count) {
    const model = await pickNinePlannerModel();
    if (!model) {
      throw new Error("九宫格拆解必须显式有 chat 模型，不会写死模型 id");
    }
    const r = await fetch("/api/grid/plan", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        model: model,
        text: text,
        kind: kind,
        count: count,
      }),
    });
    const j = await r.json();
    if (!r.ok || j.error) {
      throw new Error(j.error || "HTTP " + r.status);
    }
    const prompts = (j.prompts || [])
      .map((p) => String(p || "").trim())
      .filter(Boolean);
    if (!prompts.length) {
      throw new Error("九宫格拆解未返回可用子提示词");
    }
    if (prompts.length < count) {
      throw new Error(
        "拆解只返回 " + prompts.length + "/" + count + " 条，不足不静默补空",
      );
    }
    return prompts.slice(0, count);
  }

  async function loadGridCellImage(url) {
    try {
      return await loadShotImage(url);
    } catch (_) {}
    const r = await fetch(url);
    if (!r.ok) throw new Error("子图无法读取");
    const blob = await r.blob();
    return await loadShotImage(URL.createObjectURL(blob));
  }

  function composeNineGridSheet(imgs, n) {
    const gap = NINE_SHEET_GAP;
    let cellW = 0;
    let cellH = 0;
    imgs.forEach((img) => {
      cellW = Math.max(cellW, img.naturalWidth || img.width || 0);
      cellH = Math.max(cellH, img.naturalHeight || img.height || 0);
    });
    if (!cellW || !cellH) {
      cellW = 1280;
      cellH = 720;
    }
    const maxCellW = 640;
    if (cellW > maxCellW) {
      const s = maxCellW / cellW;
      cellW = maxCellW;
      cellH = Math.round(cellH * s);
    }
    const cv = document.createElement("canvas");
    cv.width = n * cellW + (n + 1) * gap;
    cv.height = n * cellH + (n + 1) * gap;
    const ctx = cv.getContext("2d");
    ctx.fillStyle = "#121214";
    ctx.fillRect(0, 0, cv.width, cv.height);
    for (let i = 0; i < n * n; i++) {
      const img = imgs[i];
      if (!img) continue;
      const row = Math.floor(i / n);
      const col = i % n;
      ctx.drawImage(
        img,
        gap + col * (cellW + gap),
        gap + row * (cellH + gap),
        cellW,
        cellH,
      );
    }
    return cv.toDataURL("image/jpeg", 0.92);
  }

  function buildNineCellGraph(backend, serviceId, promptText, cellId) {
    return {
      backend: backend,
      nodes: [
        { id: "p-" + cellId, op: "prompt", params: { text: promptText } },
        {
          id: cellId,
          op: "t2i",
          params: { serviceId: serviceId, resolution: "1280x720" },
        },
      ],
      edges: [
        {
          from: "p-" + cellId,
          fromPort: "prompt",
          to: cellId,
          toPort: "prompt",
        },
      ],
    };
  }

  async function generateNineGrid() {
    const text = (
      toolUi.nineText ||
      ($("prompt") && $("prompt").value) ||
      ""
    ).trim();
    if (!text) {
      setMsg("请输入九宫格生成提示词", "warn");
      return;
    }
    const type = NINE_TYPES.find((t) => t.id === toolUi.nineType);
    const kind = (type && type.label) || "灵感风暴";
    const gridN = 3;
    const count = gridN * gridN;
    setMsg("正在挑选文生图模型（不查 grid 分类）…");
    const t2i = await pickNineT2i();
    if (!t2i.serviceId) {
      setMsg(
        "没有可用的文生图模型，无法跑九宫格子图。未伪造 grid 分类，也未写死 fal id。",
        "bad",
      );
      return;
    }
    $("send").disabled = true;
    const sel = nodeById(state.selected);
    const id = uid("shot");
    const card = {
      id: id,
      kind: "shot",
      title: "九宫格",
      x: sel ? sel.x + 720 : 560,
      y: sel ? sel.y : 80,
      url: "",
      firstFrameId: "",
      prompt: "【九宫格 · " + kind + "】\n" + text,
      gridN: gridN,
      gridGap: NINE_SHEET_GAP,
      nineType: toolUi.nineType,
    };
    state.nodes.push(card);
    if (sel) state.edges.push({ from: sel.id, to: id });
    selectNode(id);
    persist();
    try {
      setMsg("正在拆解九宫格子提示词…");
      const prompts = await planNineGridPrompts(text, kind, count);
      card.gridPrompts = prompts;
      persist();
      const urls = [];
      for (let i = 0; i < count; i++) {
        const cellId = id + "-c" + i;
        const url = await runCompiledGenerate(
          buildNineCellGraph(t2i.backend, t2i.serviceId, prompts[i], cellId),
          (t) => setMsg("子图 " + (i + 1) + "/" + count + " " + t),
        );
        if (!url) throw new Error("子图 " + (i + 1) + " 没有可预览地址");
        urls.push(url);
      }
      card.gridCells = urls;
      setMsg("正在把 " + count + " 张子图拼成一张卡…");
      const imgs = [];
      for (let i = 0; i < urls.length; i++) {
        imgs.push(await loadGridCellImage(urls[i]));
      }
      const sheet = composeNineGridSheet(imgs, gridN);
      card.url = sheet;
      promoteResult(card, sheet);
      renderCards();
      drawWires();
      persist();
      setMsg("九宫格完成（" + count + " 次 t2i 拼成一张卡）", "ok");
    } catch (e) {
      persist();
      setMsg(String(e && e.message ? e.message : e), "bad");
    }
    $("send").disabled = false;
  }

  function rejectVideoTool(name) {
    setMsg(
      name +
        "：当前后端没有对应模型，禁止空跑、禁止静默降级。本版也不接商汤网关。",
      "warn",
    );
  }

  function groupMembers(g) {
    if (!g || !g.memberIds) return [];
    return g.memberIds.map(nodeById).filter(Boolean);
  }
  function memberBox(n) {
    if (!n) return { w: 0, h: 0 };
    if (n.kind === "shot") return { w: 640, h: 360 };
    if (n.kind === "text") return { w: 320, h: 280 };
    if (n.kind === "group") return { w: n.w || 400, h: n.h || 280 };
    return { w: 132, h: 208 };
  }
  function fitGroupBox(g) {
    if (!g) return;
    const ms = groupMembers(g);
    const pad = 28;
    if (!ms.length) {
      g.w = g.w || 400;
      g.h = g.h || 280;
      return;
    }
    let minX = Infinity,
      minY = Infinity,
      maxX = -Infinity,
      maxY = -Infinity;
    ms.forEach((m) => {
      const b = memberBox(m);
      minX = Math.min(minX, m.x);
      minY = Math.min(minY, m.y);
      maxX = Math.max(maxX, m.x + b.w);
      maxY = Math.max(maxY, m.y + b.h);
    });
    g.x = minX - pad;
    g.y = minY - pad - 18;
    g.w = Math.max(160, maxX - minX + pad * 2);
    g.h = Math.max(120, maxY - minY + pad * 2 + 18);
  }
  function ensureGroupWith(ids) {
    const unique = [];
    (ids || []).forEach((id) => {
      if (id && unique.indexOf(id) < 0) unique.push(id);
    });
    const nodes = unique.map(nodeById).filter(Boolean);
    const groups = nodes.filter((n) => n.kind === "group");
    const members = nodes.filter((n) => n.kind !== "group");
    groups.forEach((g) => {
      (g.memberIds || []).forEach((id) => {
        const m = nodeById(id);
        if (m && m.kind !== "group" && members.indexOf(m) < 0) members.push(m);
      });
    });
    if (members.length < 2) {
      setMsg("至少选两个节点再编组（Shift+点击另一个节点）", "warn");
      return null;
    }
    let g = groups[0];
    const memberIds = members.map((m) => m.id);
    if (g) {
      g.memberIds = memberIds;
      g.title = g.title || "分组";
    } else {
      g = {
        id: uid("group"),
        kind: "group",
        title: "分组",
        x: 0,
        y: 0,
        w: 400,
        h: 280,
        memberIds: memberIds,
      };
      state.nodes.unshift(g);
    }
    fitGroupBox(g);
    renderCards();
    drawWires();
    selectNode(g.id);
    persist();
    setMsg(
      "已编组 " + memberIds.length + " 个节点。Shift+点击可继续加入。",
      "ok",
    );
    return g;
  }
  function downloadGroup() {
    const cls = classifySelected();
    if (cls.kind !== "group") return;
    const files = groupMembers(cls.node).filter((n) => n.url);
    if (!files.length) {
      setMsg("分组里没有可下载的成片", "warn");
      return;
    }
    files.forEach((n, i) => {
      const a = document.createElement("a");
      a.href = n.url;
      a.download =
        (n.title || "group-" + (i + 1)) + (isVideoUrl(n.url) ? ".mp4" : ".png");
      document.body.appendChild(a);
      a.click();
      a.remove();
    });
    setMsg("已开始下载 " + files.length + " 项", "ok");
  }
  async function runGroup() {
    const cls = classifySelected();
    if (cls.kind !== "group") return;
    const gid = cls.node.id;
    const shotsToRun = groupMembers(cls.node).filter((n) => n.kind === "shot");
    if (!shotsToRun.length) {
      setMsg("分组里没有可执行的分镜", "warn");
      return;
    }
    for (let i = 0; i < shotsToRun.length; i++) {
      selectNode(shotsToRun[i].id);
      setMsg("整组执行 " + (i + 1) + "/" + shotsToRun.length);
      await generate();
    }
    selectNode(gid);
    setMsg("整组执行完成（" + shotsToRun.length + " 个分镜）", "ok");
  }
  function layoutGroup() {
    const cls = classifySelected();
    if (cls.kind !== "group") return;
    const g = cls.node;
    const ms = groupMembers(g);
    if (!ms.length) return;
    const gap = 40;
    const startX = g.x + 28;
    let x = startX;
    let y = g.y + 36;
    let rowH = 0;
    const wrapAt = Math.max(startX + 640, (g.x || 0) + (g.w || 900) - 28);
    ms.forEach((m) => {
      const b = memberBox(m);
      if (x > startX && x + b.w > wrapAt) {
        x = startX;
        y += rowH + gap;
        rowH = 0;
      }
      m.x = x;
      m.y = y;
      x += b.w + gap;
      rowH = Math.max(rowH, b.h);
    });
    fitGroupBox(g);
    renderCards();
    drawWires();
    persist();
    placeShotBar();
    setMsg("已自动布局组成员", "ok");
  }
  function ungroup() {
    const cls = classifySelected();
    if (cls.kind !== "group") return;
    const first = (cls.node.memberIds || [])[0];
    state.nodes = state.nodes.filter((n) => n.id !== cls.node.id);
    renderCards();
    drawWires();
    selectNode(first || null);
    persist();
    setMsg("已解组", "ok");
  }

  async function extractVideoFrame() {
    const n = nodeById(state.selected);
    if (!n || n.kind !== "shot" || !n.url || !isVideoUrl(n.url)) {
      setMsg("先选中一个视频节点再截取帧", "warn");
      return;
    }
    const cardVid = world.querySelector('.card[data-id="' + n.id + '"] video');
    const video = cardVid || document.createElement("video");
    try {
      if (!cardVid) {
        video.src = n.url;
        video.muted = true;
        video.crossOrigin = "anonymous";
        await new Promise((res, rej) => {
          video.onloadeddata = res;
          video.onerror = () => rej(new Error("视频无法加载"));
        });
      }
      const cv = document.createElement("canvas");
      cv.width = video.videoWidth || 1280;
      cv.height = video.videoHeight || 720;
      if (!cv.width || !cv.height) throw new Error("没有可截取的帧");
      cv.getContext("2d").drawImage(video, 0, 0, cv.width, cv.height);
      const dataUrl = cv.toDataURL("image/png");
      const id = uid("shot");
      state.nodes.push({
        id: id,
        kind: "shot",
        title: (n.title || "视频") + "·截取帧",
        x: n.x + 680,
        y: n.y,
        url: dataUrl,
        firstFrameId: "",
        prompt: n.prompt || "",
      });
      state.edges.push({ from: n.id, to: id });
      selectNode(id);
      persist();
      setMsg("已从当前视频截取一帧（本地 canvas，未走 generate）", "ok");
    } catch (e) {
      setMsg("截取帧失败：" + String(e && e.message ? e.message : e), "bad");
    }
  }

  function cancelNineCrop() {
    if (!toolUi.nineCrop) return;
    toolUi.nineCrop = false;
    paintGridOverlays();
  }
  function startNineCrop() {
    const cls = classifySelected();
    if (cls.kind !== "nine_grid") {
      setMsg("先选中九宫格成品卡再摘取", "warn");
      return;
    }
    const n = cls.node;
    if (!n.url && !(n.gridCells && n.gridCells.length)) {
      setMsg("先有九宫格成片再摘取", "warn");
      return;
    }
    toolUi.nineCrop = true;
    paintGridOverlays();
    setMsg("点宫格中的一格摘取。Esc 取消。", "ok");
  }
  async function extractNineGridCell(node, index) {
    cancelNineCrop();
    if (!node) return;
    const g = node.gridN || 3;
    const i = Number(index);
    if (!(i >= 0 && i < g * g)) {
      setMsg("格序号超出宫格", "warn");
      return;
    }
    const finish = (url) => {
      const id = uid("shot");
      state.nodes.push({
        id: id,
        kind: "shot",
        title: "局部摘取 · " + (i + 1) + "/" + g * g,
        x: node.x + 680,
        y: node.y + (i % g) * 24,
        url: url,
        firstFrameId: "",
        prompt: node.prompt || "",
        fromGrid: node.id,
        fromCell: i,
      });
      state.edges.push({ from: node.id, to: id });
      selectNode(id);
      persist();
      setMsg("已摘取第 " + (i + 1) + " 格（本地 canvas，未走 generate）", "ok");
    };
    const cellUrl = node.gridCells && node.gridCells[i];
    if (cellUrl) {
      finish(cellUrl);
      return;
    }
    if (!node.url || isVideoUrl(node.url)) {
      setMsg("先有九宫格成片再摘取", "warn");
      return;
    }
    try {
      const img = await loadShotImage(node.url);
      const rect = nineCellRect(
        img.naturalWidth,
        img.naturalHeight,
        g,
        i,
        node.gridGap,
      );
      if (rect.w < 2 || rect.h < 2) throw new Error("格尺寸无效");
      const cv = document.createElement("canvas");
      cv.width = Math.max(1, Math.round(rect.w));
      cv.height = Math.max(1, Math.round(rect.h));
      cv.getContext("2d").drawImage(
        img,
        rect.x,
        rect.y,
        rect.w,
        rect.h,
        0,
        0,
        cv.width,
        cv.height,
      );
      finish(cv.toDataURL("image/png"));
    } catch (e) {
      setMsg(
        "九宫格摘取失败：" + String(e && e.message ? e.message : e),
        "bad",
      );
    }
  }

  function openComposeVideo() {
    closeAllToolPanels();
    if ($("modeVid")) $("modeVid").click();
    else {
      state.mode = "video";
      renderDock();
      loadCatalog();
      persist();
    }
    setMsg("已切到底栏「视频生成」（合成视频入口）。未点发送。", "ok");
  }

  function onShotBarClick(e) {
    const btn = e.target.closest("button");
    if (!btn) return;
    const id = btn.id;
    if (btn.classList.contains("skip")) {
      setMsg(btn.title || "本版不做此项", "warn");
      return;
    }
    if (id === "btnCameraAngleBar") openCamPanel();
    else if (id === "btnGridSplitBar") {
      e.stopPropagation();
      toggleGridMenu(e);
    } else if (id === "btnRelightBar") openLightPanel();
    else if (id === "btnInpaintBar") openInpaintBar();
    else if (id === "btnStoryBar") openStoryDock();
    else if (id === "btnNineGridBar") openNineGrid();
    else if (id === "btnUpscaleBar") upscaleShot();
    else if (id === "btnVideoBar") openComposeVideo();
    else if (id === "btnExtractFrameBar") extractVideoFrame();
    else if (id === "btnVideoEnhanceBar") rejectVideoTool("视频增强");
    else if (id === "btnUnsubBar") rejectVideoTool("去字幕");
    else if (id === "btnAudioSplitBar") rejectVideoTool("音频分离");
    else if (id === "btnNineCropBar") startNineCrop();
    else if (id === "btnGroupDownloadBar") downloadGroup();
    else if (id === "btnGroupRunBar") runGroup();
    else if (id === "btnGroupLayoutBar") layoutGroup();
    else if (id === "btnGroupUngroupBar") ungroup();
  }

  function bindClaudeToolbar() {
    const pairs = [
      [
        "btnCameraAngle",
        () => {
          openCamPanel();
        },
      ],
      [
        "btnGridSplit",
        (e) => {
          e.stopPropagation();
          toggleGridMenu(e);
        },
      ],
      [
        "btnRelight",
        () => {
          openLightPanel();
        },
      ],
      [
        "btnInpaint",
        () => {
          openInpaintBar();
        },
      ],
      [
        "btnStory",
        () => {
          openStoryDock();
        },
      ],
      [
        "btnNineGrid",
        () => {
          openNineGrid();
        },
      ],
    ];
    pairs.forEach((pair) => {
      const el = $(pair[0]);
      if (el && !el._grokBound) {
        el._grokBound = true;
        el.addEventListener("click", pair[1]);
      }
    });
  }

  function bindCamOnce() {
    ensureSekoDom();
    bindClaudeToolbar();
    const bar = $("shotBar");
    if (bar && !bar._grokDelegated) {
      bar._grokDelegated = true;
      bar.addEventListener("click", onShotBarClick);
    }
    if (vp && !vp._sekoDeselect) {
      vp._sekoDeselect = true;
      vp.addEventListener(
        "pointerdown",
        (e) => {
          if (
            e.target.closest(
              ".dock,.tools,.zoom,.picker,.rail,.atbox,header,.ghost,.shot-bar,.cam-panel,.light-panel,.erase-bar,.split-menu,.node-menu,.nine-picker,.blank-pill",
            )
          )
            return;
          const card = e.target.closest(".card");
          if (e.shiftKey && card && !e.target.closest("textarea,input,.port")) {
            e.stopPropagation();
            const id = card.dataset.id;
            const cur = state.selected;
            if (!cur || cur === id) selectNode(id);
            else ensureGroupWith([cur, id]);
            return;
          }
          if (e.target.closest(".card,.port,.wire-hit")) return;
          if (state.selected) selectNode(null);
        },
        true,
      );
    }
    if (vp && !vp._sekoGroupDrag) {
      vp._sekoGroupDrag = true;
      vp.addEventListener("pointerdown", (e) => {
        const card = e.target.closest(".card");
        if (!card) return;
        const n = nodeById(card.dataset.id);
        if (!n || n.kind !== "group") return;
        groupMembers(n).forEach((m) => {
          m._offX = m.x - n.x;
          m._offY = m.y - n.y;
        });
      });
      vp.addEventListener("pointerup", () => {
        const n = nodeById(state.selected);
        if (!n) return;
        const host =
          n.kind === "group"
            ? n
            : state.nodes.find(
                (x) =>
                  x.kind === "group" && (x.memberIds || []).indexOf(n.id) >= 0,
              );
        if (!host) return;
        fitGroupBox(host);
        const el = world.querySelector('.card[data-id="' + host.id + '"]');
        if (el) {
          el.style.left = host.x + "px";
          el.style.top = host.y + "px";
          el.style.width = host.w + "px";
          el.style.height = host.h + "px";
        }
        persist();
      });
    }
    if (!document._sekoGroupHotkey) {
      document._sekoGroupHotkey = true;
      document.addEventListener("keydown", (e) => {
        if (!(e.ctrlKey || e.metaKey) || e.key.toLowerCase() !== "g") return;
        if (e.target && e.target.closest && e.target.closest("textarea,input"))
          return;
        e.preventDefault();
        const n = nodeById(state.selected);
        if (!n) return;
        const g = state.nodes.find(
          (x) => x.kind === "group" && (x.memberIds || []).indexOf(n.id) >= 0,
        );
        if (g) ensureGroupWith([g.id, n.id]);
        else setMsg("先 Shift+点击另一个节点再 Ctrl/Cmd+G 编组", "warn");
      });
    }
    const menu = $("gridSplitMenu");
    if (menu && !menu._bound) {
      menu._bound = true;
      menu.addEventListener("click", (e) => {
        const btn = e.target.closest("[data-grid]");
        if (!btn) return;
        splitShotGrid(parseInt(btn.dataset.grid, 10));
      });
    }
    const panel = $("camPanel");
    if (panel && !panel._bound) {
      panel._bound = true;
      $("camClose").onclick = closeCamPanel;
      $("camReset").onclick = resetCamParams;
      $("camSend").onclick = () => generateCameraAngle();
      $("camTabs").addEventListener("click", (e) => {
        const b = e.target.closest("[data-camtab]");
        if (b) applyCamTab(b.dataset.camtab);
      });
      $("camYaw").addEventListener("input", () => {
        camUi.yaw = parseInt($("camYaw").value, 10) || 0;
        camUi.tab = "custom";
        syncCamControls();
      });
      $("camPitch").addEventListener("input", () => {
        camUi.pitch = parseInt($("camPitch").value, 10) || 0;
        camUi.tab = "custom";
        syncCamControls();
      });
      $("camZoom").addEventListener("input", () => {
        camUi.zoom = parseInt($("camZoom").value, 10);
        if (isNaN(camUi.zoom)) camUi.zoom = 1;
        camUi.tab = "custom";
        syncCamControls();
      });
      panel.querySelectorAll("[data-camdir]").forEach((b) => {
        b.onclick = () => nudgeCam(b.dataset.camdir);
      });
      const orb = $("camOrb");
      let drag = null;
      orb.addEventListener("pointerdown", (e) => {
        if (e.target.closest(".cam-arr")) return;
        drag = {
          x: e.clientX,
          y: e.clientY,
          yaw: camUi.yaw,
          pitch: camUi.pitch,
        };
        orb.setPointerCapture(e.pointerId);
      });
      orb.addEventListener("pointermove", (e) => {
        if (!drag) return;
        camUi.yaw = Math.max(
          -90,
          Math.min(180, drag.yaw + (e.clientX - drag.x) * 0.4),
        );
        camUi.pitch = Math.max(
          -30,
          Math.min(30, drag.pitch - (e.clientY - drag.y) * 0.15),
        );
        camUi.yaw = Math.round(camUi.yaw);
        camUi.pitch = Math.round(camUi.pitch);
        camUi.tab = "custom";
        syncCamControls();
      });
      orb.addEventListener("pointerup", () => {
        drag = null;
      });
    }
    const lp = $("lightPanel");
    if (lp && !lp._bound) {
      lp._bound = true;
      $("lightClose").onclick = closeLightPanel;
      $("lightReset").onclick = resetLightParams;
      $("lightSend").onclick = () => generateRelight();
      $("lightView").addEventListener("click", (e) => {
        const b = e.target.closest("[data-lview]");
        if (!b) return;
        lightUi.view = b.dataset.lview;
        syncLightControls();
      });
      $("lightSoft").addEventListener("click", (e) => {
        const b = e.target.closest("[data-lsoft]");
        if (!b) return;
        lightUi.soft = b.dataset.lsoft === "1";
        syncLightControls();
      });
      $("lightColorMode").addEventListener("click", (e) => {
        const b = e.target.closest("[data-lcmode]");
        if (!b) return;
        lightUi.colorMode = b.dataset.lcmode;
        syncLightControls();
      });
      $("lightDirs").addEventListener("click", (e) => {
        const b = e.target.closest("[data-ldir]");
        if (!b) return;
        lightUi.dir = b.dataset.ldir;
        lightUi.preset = -1;
        setLightMsg("");
        syncLightControls();
      });
      $("lightPresets").addEventListener("click", (e) => {
        const b = e.target.closest("[data-lpreset]");
        if (!b) return;
        applyLightPreset(parseInt(b.dataset.lpreset, 10));
      });
      $("lightBright").addEventListener("input", () => {
        lightUi.brightness = Math.max(
          0,
          Math.min(100, parseInt($("lightBright").value, 10) || 0),
        );
        syncLightControls();
      });
      $("lightBrightNum").addEventListener("input", () => {
        lightUi.brightness = Math.max(
          0,
          Math.min(100, parseInt($("lightBrightNum").value, 10) || 0),
        );
        syncLightControls();
      });
      $("lightColor").addEventListener("input", () => {
        lightUi.hex = $("lightColor").value.toUpperCase();
        lightUi.colorMode = "hex";
        syncLightControls();
      });
      $("lightHex").addEventListener("change", () => {
        let v = $("lightHex").value.trim();
        if (v.charAt(0) !== "#") v = "#" + v;
        if (/^#[0-9A-Fa-f]{6}$/.test(v)) lightUi.hex = v.toUpperCase();
        lightUi.colorMode = "hex";
        syncLightControls();
      });
      $("lightKelvin").addEventListener("input", () => {
        lightUi.kelvin = parseInt($("lightKelvin").value, 10) || 5000;
        lightUi.colorMode = "kelvin";
        syncLightControls();
      });
      $("lightRim").addEventListener("change", () => {
        lightUi.rim = $("lightRim").checked;
      });
      $("lightDesc").addEventListener("input", () => {
        lightUi.desc = $("lightDesc").value;
      });
      const orb = $("lightOrb");
      orb.addEventListener("pointerdown", (e) => {
        const r = orb.getBoundingClientRect();
        snapLightDir(
          (e.clientX - r.left) / r.width,
          (e.clientY - r.top) / r.height,
        );
        orb.setPointerCapture(e.pointerId);
      });
      orb.addEventListener("pointermove", (e) => {
        if (!(e.buttons & 1)) return;
        const r = orb.getBoundingClientRect();
        snapLightDir(
          (e.clientX - r.left) / r.width,
          (e.clientY - r.top) / r.height,
        );
      });
    }
    const eb = $("eraseBar");
    if (eb && !eb._bound) {
      eb._bound = true;
      $("eraseBrush").onclick = () => {
        inpaintUi.tool = "brush";
        placeEraseBar();
      };
      $("eraseEraser").onclick = () => {
        inpaintUi.tool = "eraser";
        placeEraseBar();
      };
      $("eraseSize").oninput = () => {
        inpaintUi.size = parseInt($("eraseSize").value, 10) || 24;
      };
      $("eraseUndo").onclick = () => {
        const last = inpaintUi.undo.pop();
        if (!last || !inpaintUi.mask) return;
        const ctx = inpaintUi.mask.getContext("2d");
        inpaintUi.redo.push(
          ctx.getImageData(0, 0, inpaintUi.mask.width, inpaintUi.mask.height),
        );
        restoreMask(last);
      };
      $("eraseRedo").onclick = () => {
        const next = inpaintUi.redo.pop();
        if (!next || !inpaintUi.mask) return;
        snapshotMask();
        restoreMask(next);
      };
      $("eraseClear").onclick = () => {
        if (!inpaintUi.mask) return;
        snapshotMask();
        const ctx = inpaintUi.mask.getContext("2d");
        ctx.fillStyle = "#000";
        ctx.fillRect(0, 0, inpaintUi.mask.width, inpaintUi.mask.height);
        paintOverlayFromMask();
      };
      $("eraseGo").onclick = () => generateInpaint();
      $("eraseClose").onclick = closeInpaintBar;
    }
    const sc = $("storyControls");
    if (sc && !sc._bound) {
      sc._bound = true;
      $("storyBack").addEventListener("input", () => {
        storyUi.backward = parseInt($("storyBack").value, 10) || 0;
        syncStoryControls();
      });
      $("storyForward").addEventListener("input", () => {
        storyUi.forward = parseInt($("storyForward").value, 10) || 0;
        syncStoryControls();
      });
      $("storyAspectBtns").addEventListener("click", (e) => {
        const b = e.target.closest("[data-story-aspect]");
        if (!b) return;
        storyUi.aspect = b.dataset.storyAspect;
        syncStoryControls();
      });
      $("storyModelBtns").addEventListener("click", (e) => {
        const b = e.target.closest("[data-story-model]");
        if (!b) return;
        storyUi.modelType = b.dataset.storyModel;
        syncStoryControls();
      });
    }
    const np = $("ninePicker");
    if (np && !np._bound) {
      np._bound = true;
      $("nineClose").onclick = () => {
        toolUi.nine = false;
        closeNinePicker();
        applyDockChrome();
      };
      $("nineTypes").addEventListener("click", (e) => {
        const b = e.target.closest("[data-ninetype]");
        if (b) pickNineType(b.dataset.ninetype);
      });
    }
    const nodeMenu = $("nodeContextMenu");
    if (nodeMenu && !nodeMenu._bound) {
      nodeMenu._bound = true;
      nodeMenu.addEventListener("click", (e) => {
        const btn = e.target.closest("[data-nodeact]");
        if (!btn || btn.disabled) return;
        const point = nodeMenuPoint;
        hideNodeMenu();
        if (btn.dataset.nodeact === "copy") copyNode(point && point.targetId);
        else if (btn.dataset.nodeact === "paste")
          pasteNode(point && point.world);
        else if (btn.dataset.nodeact === "delete")
          if (point && point.targetEdge)
            deleteEdge(point.targetEdge.from, point.targetEdge.to);
          else deleteNode(point && point.targetId);
      });
    }
    if (vp && !vp._sekoNodeMenu) {
      vp._sekoNodeMenu = true;
      vp.addEventListener("contextmenu", (e) => {
        e.preventDefault();
        e.stopPropagation();
        showNodeMenu(e);
      });
    }
    document.addEventListener("pointerdown", (e) => {
      if (!e.target.closest("#gridSplitMenu,#btnGridSplitBar,#btnGridSplit"))
        hideGridMenu();
      if (!e.target.closest("#nodeContextMenu")) hideNodeMenu();
    });
    if (!document._sekoNodeHotkeys) {
      document._sekoNodeHotkeys = true;
      document.addEventListener("keydown", (e) => {
        if (e.key !== "Delete" && e.key !== "Backspace") return;
        if (
          e.target &&
          e.target.closest &&
          (e.target.isContentEditable ||
            e.target.closest("textarea,input,select,[contenteditable]"))
        )
          return;
        if (state.selectedEdge) {
          e.preventDefault();
          deleteEdge(state.selectedEdge.from, state.selectedEdge.to);
          return;
        }
        if (!state.selected) return;
        e.preventDefault();
        deleteNode(state.selected);
      });
    }
    if (!document._sekoEscNine) {
      document._sekoEscNine = true;
      document.addEventListener("keydown", (e) => {
        if (e.key !== "Escape" || !toolUi.nineCrop) return;
        cancelNineCrop();
        setMsg("已取消局部摘取");
      });
    }
    const prevSend = $("send").onclick;
    $("send").onclick = function () {
      if (toolUi.story) {
        generateStory();
        return;
      }
      if (toolUi.nine) {
        generateNineGrid();
        return;
      }
      if (prevSend) return prevSend.apply(this, arguments);
    };
    ["modeImg", "modeVid", "modeTxt"].forEach((id) => {
      const el = $(id);
      if (!el || el._sekoWrap) return;
      el._sekoWrap = true;
      const prev = el.onclick;
      el.onclick = function () {
        if (id !== "modeTxt") closeStoryDock();
        if (toolUi.nine && id !== "modeImg") {
          toolUi.nine = false;
          closeNinePicker();
        }
        if (prev) prev.apply(this, arguments);
        applyDockChrome();
      };
    });
  }

  const _renderCards = renderCards;
  renderCards = () => {
    _renderCards();
    paintGridOverlays();
    if (inpaintUi.on) attachInpaintOverlay();
    placeShotBar();
    placeEraseBar();
    bindClaudeToolbar();
  };
  const _selectNode = selectNode;
  selectNode = (id) => {
    const prev = state.selected;
    if (prev !== id) toolUi.nineCrop = false;
    _selectNode(id);
    if (prev !== id) {
      applySelectionDefaults();
      _renderDock();
    }
    syncDockVisibility();
    placeShotBar();
    if (panelOpen("camPanel")) {
      if (selectedShotImage()) {
        placeCamPanel();
        syncCamControls();
      } else closeCamPanel();
    }
    if (panelOpen("lightPanel")) {
      if (selectedShotImage()) {
        placeLightPanel();
        syncLightControls();
      } else closeLightPanel();
    }
    if (inpaintUi.on) {
      if (selectedShotImage()) {
        attachInpaintOverlay();
        placeEraseBar();
      } else closeInpaintBar();
    }
    applyDockChrome();
    placeDock();
  };
  const _applyCam = applyCam;
  applyCam = () => {
    _applyCam();
    placeShotBar();
    placeEraseBar();
    placeDock();
    if (panelOpen("camPanel")) placeCamPanel();
    if (panelOpen("lightPanel")) placeLightPanel();
    if (panelOpen("ninePicker")) placeFloating("ninePicker", false);
  };
  const _moveCardEl = moveCardEl;
  moveCardEl = (n) => {
    _moveCardEl(n);
    if (n && n.kind === "group") {
      groupMembers(n).forEach((m) => {
        if (m._offX == null || m._offY == null) return;
        m.x = n.x + m._offX;
        m.y = n.y + m._offY;
        const el = world.querySelector('.card[data-id="' + m.id + '"]');
        if (el) {
          el.style.left = m.x + "px";
          el.style.top = m.y + "px";
        }
      });
    }
    placeShotBar();
    placeEraseBar();
    placeDock();
  };
  const _renderDock = renderDock;
  renderDock = () => {
    const cls = classifySelected();
    if (
      cls.kind === "none" ||
      cls.kind === "nine_grid" ||
      cls.kind === "group" ||
      cls.kind === "asset"
    ) {
      dock.classList.remove("show");
      renderRail();
      applyDockChrome();
      placeShotBar();
      return;
    }
    _renderDock();
    syncDockVisibility();
    applyDockChrome();
    placeDock();
  };
  const _loadCatalog = loadCatalog;
  loadCatalog = async function loadCatalog() {
    if (toolUi.story) return;
    await _loadCatalog();
    preferDockModel();
    syncSamplerChrome();
    syncParamChrome();
  };
  const _catalogCategory = catalogCategory;
  catalogCategory = function catalogCategory() {
    if (state.mode === "text" || toolUi.story) return "text";
    if (state.mode === "audio") return "audio";
    return _catalogCategory();
  };
  const _handlePromptInput = handlePromptInput;
  handlePromptInput = (ta, node) => {
    if (toolUi.nine) {
      toolUi.nineText = ta.value;
      return;
    }
    if (toolUi.story) {
      toolUi.storyText = ta.value;
      return;
    }
    return _handlePromptInput(ta, node);
  };

  const _box = box;
  box = function box(n) {
    if (n && n.kind === "group") return { w: n.w || 400, h: n.h || 280 };
    return _box(n);
  };
  const _assets = assets;
  assets = function assets() {
    return _assets().filter((n) => n.kind !== "group");
  };
  const _cardHTML = cardHTML;
  cardHTML = function cardHTML(n) {
    if (n && n.kind === "group") {
      const sel = state.selected === n.id ? " sel" : "";
      return (
        '<div class="card group' +
        sel +
        '" data-id="' +
        esc(n.id) +
        '" style="left:' +
        n.x +
        "px;top:" +
        n.y +
        "px;width:" +
        (n.w || 400) +
        "px;height:" +
        (n.h || 280) +
        'px">' +
        '<div class="label">' +
        esc(n.title || "分组") +
        "</div></div>"
      );
    }
    return _cardHTML(n);
  };

  bindCamOnce();
  window.__sekoSelect = selectNode;
  window.__sekoSelectEdge = selectEdge;
  window.__sekoClassify = classifySelected;
  window.__sekoIsNineGrid = isNineGridNode;
  window.__sekoNineCellRect = nineCellRect;
  window.__sekoPanTo = panTo;
  window.__sekoDeleteNode = deleteNode;
  window.__sekoDeleteEdge = deleteEdge;
  window.__sekoCopyNode = copyNode;
  window.__sekoPasteNode = pasteNode;
  window.__sekoState = state;
  window.__sekoCam = (x, y, s) => {
    if (x != null) state.cam.x = x;
    if (y != null) state.cam.y = y;
    if (s != null) state.cam.s = s;
    applyCam();
  };
  window.__sekoPatchNode = (id, patch) => {
    const n = nodeById(id);
    if (!n) return false;
    Object.assign(n, patch || {});
    sekoSelKey = "";
    renderCards();
    drawWires();
    if (state.selected === id) {
      applySelectionDefaults();
      renderDock();
    }
    placeShotBar();
    placeDock();
    return true;
  };

  if (!restore()) {
    state.nodes = [];
    state.edges = [];
  }
  applyCam();
  renderCards();
  drawWires();
  if (state.selected) {
    selectNode(state.selected);
  } else {
    state.mode = "text";
    selectDefaultBackendForCategory("text");
    renderDock();
    loadCatalog();
  }
  loadOuts();
  loadSamplerDefaults();
  bindParamChrome();
  loadProviderCaps().then(() => syncParamChrome());
})();
