(function () {
  const $ = (id) => document.getElementById(id);
  const STORE = "nl-storyboard-v0794";
  const STORE_OLD = "nl-storyboard-v0793";
  // v0791-v0793 shared this single URL across all six demo nodes. If a restored
  // session still carries it, the cache predates the prompt-node contract — drop it.
  const STALE_SHARED_DEMO = "/out/fal_fal-ai_flux_schnell_01a05be2-19bd-75e1-8053-0a6f8de59915_0.jpg";
  const DEMO_BOT = "/static/demo-bot.jpg";
  const DEMO_WORK = "/static/demo-work.jpg";
  const DEMO_BED = "/static/demo-bed.jpg";
  const DEMO_BATH = "/static/demo-bath.jpg";
  const vp = $("viewport");
  const world = $("world");
  const wires = $("wires");
  const dock = $("dock");

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
    _atTarget: null,
    _pendingService: "",
  };

  const CHAR_LIB = {
    "家用机器人": {
      subject: "一台白色圆润的家用陪伴机器人",
      look: "哑光白外壳，圆润流线造型，胸口有柔光屏幕",
      outfit: "无服装，机身自带浅蓝色反光饰条",
      scene: "现代家居室内",
      light: "柔和顶光，暖色补光",
      composition: "居中偏左，留白给人物",
      frame: "中景",
      camera: "固定镜头",
      constraints: "外壳造型与反光饰条保持一致，禁止更改机身比例",
      negative: "生锈，破损，多余肢体，畸变，水印",
    },
    "大白-居家装": {
      subject: "机器人管家「大白」，居家便服造型",
      look: "圆润白色外壳，佩戴米色围裙式外装甲",
      outfit: "居家围裙外装甲，脚踝处有软垫轮",
      scene: "温馨现代卧室",
      light: "自然窗光，暖黄补光",
      composition: "三分法构图，靠近窗边",
      frame: "中近景",
      camera: "缓慢推进",
      constraints: "围裙颜色与家居风格统一，禁止更换材质",
      negative: "模糊，畸变，多余肢体，水印",
    },
    "大白-职场装": {
      subject: "机器人管家「大白」，职场西装造型",
      look: "圆润白色外壳，佩戴深灰色简约职场装甲",
      outfit: "简约西装式装甲，胸前佩戴身份牌",
      scene: "现代办公室",
      light: "冷白顶光，专业感强",
      composition: "居中构图，背景虚化",
      frame: "中景",
      camera: "固定镜头",
      constraints: "装甲版型不变，保持职场感配色",
      negative: "模糊，畸变，多余肢体，水印，卡通化",
    },
    "扫地机器人": {
      subject: "小型圆盘状扫地机器人",
      look: "黑色哑光圆盘，顶部一圈激光雷达",
      outfit: "无服装，机身贴有品牌反光条",
      scene: "室内地面视角",
      light: "低角度自然光",
      composition: "低机位特写",
      frame: "特写",
      camera: "固定镜头",
      constraints: "圆盘比例与雷达位置保持一致",
      negative: "模糊，畸变，多余部件，水印",
    },
    "温馨现代卧室": {
      subject: "一间温馨现代风格卧室",
      look: "原木色家具，米白色墙面，绿植点缀",
      outfit: "—",
      scene: "卧室内景，靠窗床铺",
      light: "清晨自然光透过纱帘",
      composition: "对称构图，床铺居中",
      frame: "全景",
      camera: "固定镜头，轻微横摇",
      constraints: "家具摆位与色调保持一致",
      negative: "杂乱，畸变家具，水印",
    },
    "现代感洗手间": {
      subject: "一间现代简约风格洗手间",
      look: "灰白瓷砖，黑色金属五金件",
      outfit: "—",
      scene: "洗手间内景，台盆与镜面",
      light: "顶部射灯，冷白光",
      composition: "居中对称，镜面反射",
      frame: "中景",
      camera: "固定镜头",
      constraints: "瓷砖纹理与五金件保持一致",
      negative: "潮湿污渍，畸变，水印",
    },
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
  function box(n) {
    if (n.kind === "shot") return { w: 640, h: 360 };
    if (n.kind === "text") return { w: 320, h: 280 };
    return { w: 132, h: 208 };
  }
  function assets() { return state.nodes.filter((n) => n.kind !== "shot" && n.kind !== "text"); }
  function shots() { return state.nodes.filter((n) => n.kind === "shot"); }
  function connectedNodes(id) {
    return state.edges.filter((e) => e.to === id).map((e) => nodeById(e.from)).filter(Boolean);
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
    return node.kind === "text" ? (node.text || "") : (node.prompt || "");
  }

  function describePrompt(asset, caption) {
    const bible = CHAR_LIB[(asset && asset.title) || ""] || {};
    const subject = (caption && String(caption).trim()) || bible.subject || (asset ? asset.title : "主体");
    return [
      "主体：" + subject,
      "外观：" + (bible.look || "参照参考图"),
      "服装：" + (bible.outfit || "参照参考图"),
      "场景：" + (bible.scene || "参照参考图"),
      "光线：" + (bible.light || "自然光"),
      "构图：" + (bible.composition || "居中"),
      "画面：" + (bible.frame || "中景"),
      "运镜：" + (bible.camera || "固定镜头"),
      "约束：" + (bible.constraints || "保持一致性，禁止畸变"),
      "负面：" + (bible.negative || "模糊，畸变，多余肢体，水印"),
    ].join("\n");
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
    if (!asset) return null;
    let caption = "";
    try { caption = await captionFromAsset(asset); } catch (_) { caption = ""; }
    const text = describePrompt(asset, caption);
    let node = state.nodes.find((n) => n.kind === "text" && state.edges.some((e) => e.from === asset.id && e.to === n.id));
    if (!node) {
      node = { id: uid("text"), kind: "text", title: "反推·" + sourceTitle(asset), x: asset.x + 220, y: asset.y, text: text };
      state.nodes.push(node);
      state.edges.push({ from: asset.id, to: node.id });
    } else {
      node.text = text;
    }
    selectNode(node.id);
    renderCards(); drawWires(); renderDock(); persist();
    return node;
  }

  async function generateFromText(node) {
    if (!node || node.kind !== "text") return;
    let shot = shots().find((s) => state.edges.some((e) => e.from === node.id && e.to === s.id));
    if (!shot) {
      const i = shots().length;
      shot = {
        id: uid("shot"), kind: "shot", title: "分镜" + (i + 1),
        x: node.x + 420, y: node.y, url: "", firstFrameId: "", prompt: "",
      };
      state.nodes.push(shot);
      state.edges.push({ from: node.id, to: shot.id });
    }
    shot.prompt = node.text || "";
    connectedNodes(node.id).filter(isImageSource).forEach((img) => {
      if (!state.edges.some((e) => e.from === img.id && e.to === shot.id)) {
        state.edges.push({ from: img.id, to: shot.id });
      }
      if (!shot.firstFrameId) shot.firstFrameId = img.id;
    });
    state.mode = "text";
    selectNode(shot.id);
    renderCards(); drawWires(); renderDock(); persist();
    await generate();
  }

  function loadDemo() {
    const assetsSeed = [
      { id: "a-bot", kind: "character", title: "家用机器人", x: 48, y: 24, url: DEMO_BOT },
      { id: "a-home", kind: "character", title: "大白-居家装", x: 48, y: 260, url: DEMO_BOT },
      { id: "a-work", kind: "character", title: "大白-职场装", x: 48, y: 496, url: DEMO_WORK },
      { id: "a-vac", kind: "character", title: "扫地机器人", x: 48, y: 732, url: DEMO_BOT },
      { id: "s-bed", kind: "scene", title: "温馨现代卧室", x: 48, y: 992, url: DEMO_BED },
      { id: "s-bath", kind: "scene", title: "现代感洗手间", x: 48, y: 1228, url: DEMO_BATH },
    ];
    const shotSeeds = [
      { assets: ["a-bot", "a-home", "s-bed"] },
      { assets: ["a-bot", "s-bed"] },
      { assets: ["a-work"] },
      { assets: ["a-vac"] },
      { assets: ["s-bed"] },
      { assets: ["s-bath"] },
    ];
    const textNodes = [];
    const shotNodes = [];
    const edges = [];
    shotSeeds.forEach((seed, i) => {
      const shotId = "shot-" + (i + 1);
      const textId = "text-" + (i + 1);
      const col = i % 2, row = Math.floor(i / 2);
      const textX = 560 + col * 900;
      const textY = 80 + row * 430;
      const primary = assetsSeed.find((a) => a.id === seed.assets[0]);
      const text = describePrompt(primary, "");
      textNodes.push({ id: textId, kind: "text", title: "分镜" + (i + 1) + "提示词", x: textX, y: textY, text: text });
      shotNodes.push({
        id: shotId, kind: "shot", title: "分镜" + (i + 1),
        x: textX + 380, y: textY, url: "", firstFrameId: seed.assets[0], prompt: text,
      });
      seed.assets.forEach((aid) => edges.push({ from: aid, to: shotId }));
      edges.push({ from: seed.assets[0], to: textId });
      edges.push({ from: textId, to: shotId });
    });
    state.nodes = assetsSeed.concat(textNodes, shotNodes);
    state.edges = edges;
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
      const raw = sessionStorage.getItem(STORE) || sessionStorage.getItem(STORE_OLD) || "null";
      const p = JSON.parse(raw);
      if (!p || !p.nodes || !p.nodes.length) return false;
      if (p.nodes.some((n) => n.url === STALE_SHARED_DEMO)) return false;
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
    if (n.kind === "text") {
      return '<div class="card text' + sel + '" data-id="' + esc(n.id) + '" style="left:' + n.x + 'px;top:' + n.y + 'px">' +
        '<div class="label">✎ ' + esc(n.title || "提示词") + '</div>' +
        '<textarea class="editor" data-text data-id="' + esc(n.id) + '" placeholder="反推或手写提示词…">' + esc(n.text || "") + '</textarea>' +
        '<div class="acts">' +
        '<button type="button" data-textact="rev" data-id="' + esc(n.id) + '">反推</button>' +
        '<button type="button" data-textact="gen" data-id="' + esc(n.id) + '">生图</button>' +
        '</div>' +
        '<button class="port in" data-side="in" type="button">+</button>' +
        '<button class="port out" data-side="out" type="button">+</button></div>';
    }
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
  function moveCardEl(n) {
    const el = world.querySelector('.card[data-id="' + n.id + '"]');
    if (el) { el.style.left = n.x + "px"; el.style.top = n.y + "px"; }
  }
  function markSelected(id) {
    world.querySelectorAll(".card.sel").forEach((el) => el.classList.remove("sel"));
    const el = world.querySelector('.card[data-id="' + id + '"]');
    if (el) el.classList.add("sel");
  }

  function renderRail() {
    const rail = $("assetRail");
    if (!rail) return;
    const shot = nodeById(state.selected);
    const canPin = shot && shot.kind === "shot";
    const tabAssets = state.railTab !== "history";
    const tabs = '<div class="rail-tabs">' +
      '<button type="button" data-tab="assets"' + (tabAssets ? ' class="on"' : "") + '>资产</button>' +
      '<button type="button" data-tab="history"' + (!tabAssets ? ' class="on"' : "") + '>历史</button></div>';
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
    if (!n || (n.kind !== "shot" && n.kind !== "text")) {
      dock.classList.remove("show");
      renderRail();
      return;
    }
    dock.classList.add("show");
    $("prompt").value = promptOf(n);
    if ($("modeTxt")) $("modeTxt").classList.toggle("on", n.kind === "text" || state.mode === "text");
    $("modeVid").classList.toggle("on", n.kind === "shot" && state.mode === "video");
    $("modeImg").classList.toggle("on", n.kind === "shot" && state.mode === "image");
    if (n.kind === "text") {
      if ($("send")) $("send").disabled = false;
      $("refs").innerHTML =
        '<button class="chip-btn wide" type="button" data-act="gen-text">生图</button>' +
        '<button class="chip-btn wide" type="button" data-act="rev-text">反推</button>';
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

  function syncPrompt(node, value, sourceEl) {
    if (!node) return;
    if (node.kind === "text") node.text = value; else node.prompt = value;
    if (state.selected === node.id) {
      const dockTa = $("prompt");
      if (dockTa && dockTa !== sourceEl) dockTa.value = value;
      const cardTa = world.querySelector('textarea[data-text][data-id="' + node.id + '"]');
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
      const next = cur.split(tag).join("").replace(/[ \t]{2,}/g, " ").replace(/\n{3,}/g, "\n\n");
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
      if (shot && !shot.firstFrameId && isImageSource(asset)) shot.firstFrameId = asset.id;
    }
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

  function handlePromptInput(ta, node) {
    if (node) syncPrompt(node, ta.value, ta);
    const v = ta.value || "";
    const caret = ta.selectionStart != null ? ta.selectionStart : v.length;
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
      const caret = ta.selectionStart != null ? ta.selectionStart : v.length;
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
    } else if (isImageSource(asset) && !state.edges.some((e) => e.from === asset.id && e.to === target.id)) {
      state.edges.push({ from: asset.id, to: target.id });
    }
    hideAtbox();
    state._atTarget = null;
    drawWires(); renderDock(); persist();
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
      state.link.x2 = w.x; state.link.y2 = w.y; drawWires(); return;
    }
    if (state.drag) {
      const w = clientToWorld(e.clientX, e.clientY);
      const n = nodeById(state.drag.id);
      n.x = w.x - state.drag.dx; n.y = w.y - state.drag.dy;
      moveCardEl(n); drawWires(); return;
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
        let dst = null, src = null;
        if (target.kind === "shot" && a.kind !== "shot") { dst = target; src = a; }
        else if (a.kind === "shot" && target.kind !== "shot") { dst = a; src = target; }
        else if (target.kind === "text" && isImageSource(a)) { dst = target; src = a; }
        else if (a.kind === "text" && isImageSource(target)) { dst = a; src = target; }
        if (dst && src && src.id !== dst.id && (src.kind !== "shot" || isImageSource(src))) {
          if (dst.kind === "shot") {
            linkAssetToShot(src, dst);
          } else if (!state.edges.some((e2) => e2.from === src.id && e2.to === dst.id)) {
            state.edges.push({ from: src.id, to: dst.id });
          }
          selectNode(dst.id);
        }
      }
      state.link = null;
      drawWires(); persist();
    }
    if (state.drag) { renderCards(); persist(); }
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
      if (src) { setMsg("正在反推…"); reverseFromImage(src).then(() => setMsg("反推完成，提示词已更新", "ok")); }
      else setMsg("这张提示词卡还没连图片", "warn");
    }
  });

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
    if (act.dataset.act === "gen-text") {
      const n = nodeById(state.selected);
      if (n) generateFromText(n);
    }
    if (act.dataset.act === "rev-text") {
      const n = nodeById(state.selected);
      const src = n && connectedNodes(n.id).find(isImageSource);
      if (src) { setMsg("正在反推…"); reverseFromImage(src).then(() => setMsg("反推完成，提示词已更新", "ok")); }
      else setMsg("这张提示词卡还没连图片", "warn");
    }
  });

  function dropRailOnCanvas(payload, cx, cy) {
    const w = clientToWorld(cx, cy);
    const hit = hitNode(w.x, w.y);
    let node = payload.node || null;
    if (!node && payload.item) node = spawnHistoryAt(payload.item, w.x - 66, w.y - 40);
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
    handlePromptInput($("prompt"), nodeById(state.selected));
  });
  $("modeImg").onclick = () => { state.mode = "image"; renderDock(); loadCatalog(); persist(); };
  $("modeVid").onclick = () => { state.mode = "video"; renderDock(); loadCatalog(); persist(); };
  if ($("modeTxt")) $("modeTxt").onclick = () => { state.mode = "text"; renderDock(); loadCatalog(); persist(); };
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
    else if (state.mode !== "text" && linked[0]) op = "i2i";
    const aspect = $("aspect").value || "16:9";
    const res = $("res").value === "1080P" ? (aspect === "9:16" ? "1080x1920" : "1920x1080") : (aspect === "9:16" ? "720x1280" : "1280x720");
    nodes.push({
      id: shot.id, op: op,
      params: {
        serviceId: $("service").value,
        resolution: res,
        duration: parseInt($("duration").value, 10) || 5,
      },
    });
    const ref = (op === "i2v") ? frame : linked[0];
    if (ref && op !== "t2i") edges.push({ from: ref.id, fromPort: "image", to: shot.id, toPort: "image" });
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
  $("send").onclick = () => {
    const n = nodeById(state.selected);
    if (n && n.kind === "text") generateFromText(n);
    else generate();
  };

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
  if ($("btnText")) {
    $("btnText").onclick = () => {
      const base = nodeById(state.selected);
      const id = uid("text");
      state.nodes.push({
        id: id, kind: "text", title: "提示词",
        x: base ? base.x + 200 : 220, y: base ? base.y : 24, text: "",
      });
      selectNode(id); persist();
    };
  }
  if ($("btnRev")) {
    $("btnRev").onclick = () => {
      const n = nodeById(state.selected);
      const src = n && isImageSource(n) ? n : (n && n.kind === "shot" ? frameAsset(n) : null);
      if (!src) { setMsg("先选中一张图片资产再反推", "warn"); return; }
      setMsg("正在反推…");
      reverseFromImage(src).then((node) => {
        if (node) setMsg("反推完成，提示词已写入文本节点", "ok");
      });
    };
  }
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

  function catalogCategory() {
    return state.mode === "video" ? "video" : "image";
  }
  async function loadCatalog() {
    $("service").innerHTML = '<option value="">默认模型</option>';
    try {
      const r = await fetch(
        "/api/catalog?backend=" + encodeURIComponent($("backend").value) +
        "&category=" + encodeURIComponent(catalogCategory())
      );
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
      // Each provider ships a different model roster per category — never leave
      // serviceId blank, or generate() would fall back across providers.
      if (!$("service").value && $("service").options.length > 1) {
        $("service").selectedIndex = 1;
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
