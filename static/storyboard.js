(function () {
  const $ = (id) => document.getElementById(id);
  const STORE = "nl-storyboard-v0806";
  const STORE_OLDS = ["nl-storyboard-v0805", "nl-storyboard-v0804", "nl-storyboard-v0803", "nl-storyboard-v0802", "nl-storyboard-v0798", "nl-storyboard-v0797", "nl-storyboard-v0796", "nl-storyboard-v0793", "nl-storyboard-v0791", "nl-storyboard-v0790"];
  const SNAP_PX = 36;
  const vp = $("viewport");
  const world = $("world");
  const wires = $("wires");
  const dock = $("dock");
  const DEMO = "/out/fal_fal-ai_flux_schnell_01a05be2-19bd-75e1-8053-0a6f8de59915_0.jpg";

  const SKILL_CATS = ["官方精选", "成片工作流", "短剧", "剧本策划", "美术资产", "营销广告"];
  const SKILLS = [
    { id: "one-take", title: "一镜到底", category: "官方精选",
      template: "请描述你的一镜到底创意：\n场景：\n主体：@角色\n运镜：缓推 / 跟拍 / 环绕\n情绪：" },
    { id: "storyboard-shot", title: "分镜镜头卡", category: "官方精选",
      template: "【镜头】\n场景：@场景\n画面：\n角色：@角色\n运镜：固定镜头\n对白：" },
    { id: "i2i-restyle", title: "图生图·风格重绘", category: "官方精选",
      template: "基于 @图片1 重新绘制：保持构图与角色身份，强化光影与材质细节。风格：" },
    { id: "i2v-motion", title: "图生视频·运镜", category: "成片工作流",
      template: "以首帧 @图片1 生成视频。\n动作：\n运镜：缓慢推进\n时长提示：自然流畅，避免跳切。" },
    { id: "multi-shot", title: "多镜连贯成片", category: "成片工作流",
      template: "请按镜头顺序描述成片：\n镜1（建立）：@场景\n镜2（人物）：@角色\n镜3（反应）：\n转场：硬切 / 叠化" },
    { id: "drama-hook", title: "短剧开场钩子", category: "短剧",
      template: "短剧第1集开场（3秒钩子）：\n冲突：\n角色：@角色\n台词（一句）：\n画面冲击点：" },
    { id: "drama-twist", title: "反转分镜", category: "短剧",
      template: "反转镜头：前半误导，后半揭晓。\n角色：@角色\n误导信息：\n真相：\n表情特写：" },
    { id: "script-beat", title: "场次节拍", category: "剧本策划",
      template: "场次节拍表：\n目标：\n障碍：\n转折：\n收束：\n出场角色：@角色" },
    { id: "script-outline", title: "三幕大纲", category: "剧本策划",
      template: "三幕大纲：\n第一幕（建置）：\n第二幕（对抗）：\n第三幕（解决）：\n主题：" },
    { id: "char-sheet", title: "角色设定图", category: "美术资产",
      template: "角色设定三视图：正面 / 侧面 / 背面。\n角色：@角色\n服装：\n配色：\n关键道具：" },
    { id: "scene-concept", title: "场景概念图", category: "美术资产",
      template: "场景概念图：@场景\n时间：晨 / 黄昏 / 夜\n氛围：\n镜头：广角建立镜头\n细节道具：" },
    { id: "ad-hook", title: "广告前3秒", category: "营销广告",
      template: "广告前3秒钩子：产品出镜 + 痛点一句话。\n产品：\n受众：\n画面：@角色 使用产品\nCTA：" },
  ];

  const state = {
    cam: { x: 90, y: 36, s: 0.5 },
    nodes: [],
    edges: [],
    selected: null,
    multi: [],
    groups: [],
    drag: null,
    pan: null,
    link: null,
    railDrag: null,
    mode: "image",
    catalog: [],
    history: [],
    railTab: "assets",
    atFilter: "",
    snapTarget: null,
    importTab: "project",
    importFilter: "all",
    importSelected: {},
    importLibrary: [],
    skillCat: "官方精选",
    runningGroup: false,
    groupRunAbort: false,
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
  function mediaBadge(n) {
    if (!n || !n.url) return "";
    if (isVideoUrl(n.url)) return '<span class="badge vid">视频</span>';
    return '<span class="badge">图片</span>';
  }

  function mediaKindOf(url, kindHint) {
    if (kindHint === "video" || kindHint === "image" || kindHint === "audio") return kindHint;
    const u = url || "";
    if (isVideoUrl(u)) return "video";
    if (/\.(mp3|wav|ogg|m4a)(\?|$)/i.test(u)) return "audio";
    return "image";
  }
  function kindBadgeLabel(kind) {
    if (kind === "video") return "视频";
    if (kind === "audio") return "音频";
    return "图片";
  }
  function shotDurationLabel(n) {
    if (!n || n.kind !== "shot") return "";
    if (n.duration != null && n.duration !== "") {
      const raw = String(n.duration);
      return /s$/i.test(raw) ? raw : raw + "s";
    }
    if (state.mode === "video") {
      const d = $("duration") && $("duration").value;
      return d || "12s";
    }
    return "";
  }
  function isStubMode() { return state.mode === "text" || state.mode === "audio"; }

  function isMulti(id) { return state.multi.indexOf(id) >= 0; }
  function setMulti(ids) {
    const seen = {};
    state.multi = (ids || []).filter((id) => {
      if (!id || seen[id] || !nodeById(id)) return false;
      seen[id] = true;
      return true;
    });
    syncSelBar();
  }
  function toggleMulti(id) {
    if (!id || !nodeById(id)) return;
    if (isMulti(id)) state.multi = state.multi.filter((x) => x !== id);
    else state.multi = state.multi.concat([id]);
    syncSelBar();
  }
  function pruneGroups() {
    const alive = {};
    state.nodes.forEach((n) => { alive[n.id] = true; });
    state.groups = (state.groups || []).map((g) => ({
      id: g.id,
      name: g.name || "组",
      memberIds: (g.memberIds || []).filter((id) => alive[id]),
    })).filter((g) => g.memberIds.length >= 2);
  }
  function groupOf(id) {
    return (state.groups || []).find((g) => (g.memberIds || []).indexOf(id) >= 0) || null;
  }
  function findActiveGroup() {
    pruneGroups();
    const multiShots = state.multi.map(nodeById).filter((n) => n && n.kind === "shot").map((n) => n.id);
    if (multiShots.length) {
      const exact = state.groups.find((g) => {
        const m = g.memberIds || [];
        if (m.length !== multiShots.length) return false;
        return multiShots.every((id) => m.indexOf(id) >= 0);
      });
      if (exact) return exact;
      const cover = state.groups.find((g) => multiShots.every((id) => (g.memberIds || []).indexOf(id) >= 0));
      if (cover) return cover;
    }
    if (state.selected) return groupOf(state.selected);
    return null;
  }
  function groupRunTargets() {
    const g = findActiveGroup();
    if (g) {
      return (g.memberIds || []).map(nodeById).filter((n) => n && n.kind === "shot");
    }
    const multiShots = state.multi.map(nodeById).filter((n) => n && n.kind === "shot");
    if (multiShots.length) return multiShots;
    return [];
  }

  function syncSelBar() {
    const bar = $("selBar");
    if (!bar) return;
    const g = findActiveGroup();
    const n = (state.multi && state.multi.length) ? state.multi.length : (state.selected ? 1 : 0);
    const countEl = $("selCount");
    if (countEl) {
      countEl.textContent = g ? ((g.name || "组") + " · " + n) : String(n);
    }
    const show = n >= 2 || !!g;
    bar.classList.toggle("on", show);
    const targets = groupRunTargets();
    const why = state.runningGroup
      ? "整组执行中…"
      : (!targets.length ? "组内/多选需要分镜才能 ▶整组逐步跑" : "按拓扑逐步跑组内分镜");
    ["selGroupRun", "btnGroupRun"].forEach((id) => {
      const el = $(id);
      if (!el) return;
      el.disabled = !targets.length || state.runningGroup;
      el.title = why;
    });
  }
  function syncGroupRunBtn() {
    const btn = $("btnGroupRun");
    if (!btn) return;
    const targets = groupRunTargets();
    btn.disabled = !targets.length || state.runningGroup;
  }
  function selectGroupMembers(g) {
    if (!g) return;
    const ids = (g.memberIds || []).filter((id) => nodeById(id));
    setMulti(ids);
    const firstShot = ids.map(nodeById).find((n) => n && n.kind === "shot");
    state.selected = firstShot ? firstShot.id : (ids[0] || null);
    renderCards();
    drawWires();
    renderDock();
    syncGroupRunBtn();
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
        groups: state.groups || [],
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
      let raw = sessionStorage.getItem(STORE);
      if (!raw) {
        for (let i = 0; i < STORE_OLDS.length; i++) {
          raw = sessionStorage.getItem(STORE_OLDS[i]);
          if (raw) break;
        }
      }
      const p = JSON.parse(raw || "null");
      if (!p || !p.nodes || !p.nodes.length) return false;
      state.cam = p.cam || state.cam;
      if (state.cam && (state.cam.s == null || state.cam.s < 0.16)) state.cam.s = 0.5;
      state.nodes = p.nodes;
      state.edges = p.edges || [];
      state.mode = p.mode === "video" || p.mode === "image" || p.mode === "text" || p.mode === "audio" ? p.mode : "image";
      state.railTab = p.railTab || "assets";
      state.groups = Array.isArray(p.groups) ? p.groups.map((g) => ({
        id: g.id || uid("grp"),
        name: g.name || "组",
        memberIds: Array.isArray(g.memberIds) ? g.memberIds.slice() : [],
      })).filter((g) => g.memberIds.length) : [];
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
    if ($("zPct")) $("zPct").textContent = Math.round(state.cam.s * 100) + "%";
    drawMinimap();
    positionDock();
    if (typeof syncZoomPresets === "function") syncZoomPresets();
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

  function canLink(src, dst) {
    if (!src || !dst || src.id === dst.id) return false;
    if (dst.kind !== "shot") return false;
    if (src.kind === "shot" && !isImageSource(src)) return false;
    return true;
  }

  function nearestCompatiblePort(wx, wy, fromId, fromSide) {
    const from = nodeById(fromId);
    if (!from) return null;
    let best = null;
    let bestD = SNAP_PX;
    state.nodes.forEach((n) => {
      if (n.id === fromId) return;
      let side = null;
      let src = null;
      let dst = null;
      if (fromSide === "out") {
        if (n.kind !== "shot") return;
        side = "in";
        src = from;
        dst = n;
      } else {
        side = "out";
        src = n;
        dst = from;
      }
      if (!canLink(src, dst)) return;
      const p = portPos(n, side);
      const d = Math.hypot(p.x - wx, p.y - wy);
      if (d <= bestD) {
        bestD = d;
        best = { id: n.id, side: side, x: p.x, y: p.y, dist: d };
      }
    });
    return best;
  }

  function drawWires() {
    const parts = ["<defs></defs>"];
    state.edges.forEach((e, i) => {
      const a = nodeById(e.from), b = nodeById(e.to);
      if (!a || !b) return;
      const p1 = portPos(a, "out"), p2 = portPos(b, "in");
      parts.push('<path class="edge" data-ei="' + i + '" d="' + bezier(p1.x, p1.y, p2.x, p2.y) + '" />');
    });
    if (state.link && state.link.x2 != null) {
      const snap = state.snapTarget;
      const cls = snap ? "snap" : "live";
      const x2 = snap ? snap.x : state.link.x2;
      const y2 = snap ? snap.y : state.link.y2;
      parts.push('<path class="' + cls + '" d="' + bezier(state.link.x1, state.link.y1, x2, y2) + '" />');
    }
    wires.innerHTML = parts.join("");
    const maxX = Math.max(2400, ...state.nodes.map((n) => n.x + box(n).w + 400));
    const maxY = Math.max(2400, ...state.nodes.map((n) => n.y + box(n).h + 400));
    wires.setAttribute("width", String(maxX));
    wires.setAttribute("height", String(maxY));
    updatePortHot();
  }

  function updatePortHot() {
    world.querySelectorAll(".port.snap-hot").forEach((el) => el.classList.remove("snap-hot"));
    if (!state.snapTarget) return;
    const card = world.querySelector('.card[data-id="' + state.snapTarget.id + '"]');
    if (!card) return;
    const port = card.querySelector('.port[data-side="' + state.snapTarget.side + '"]');
    if (port) port.classList.add("snap-hot");
  }

  function cardHTML(n) {
    const sel = state.selected === n.id ? " sel" : "";
    const multi = isMulti(n.id) ? " multi" : "";
    const badge = mediaBadge(n);
    if (n.kind === "shot") {
      const media = n.url
        ? (isVideoUrl(n.url)
            ? '<video src="' + esc(n.url) + '" muted></video>'
            : '<img src="' + esc(n.url) + '" alt="">')
        : '<div class="face"><div style="font-size:22px">▢</div><div class="hint">点击查看或编辑提示词</div></div>';
      const dur = shotDurationLabel(n);
      return '<div class="card shot' + sel + multi + '" data-id="' + esc(n.id) + '" style="left:' + n.x + 'px;top:' + n.y + 'px">' +
        '<div class="label">▢ ' + esc(n.title) + (dur ? '<span class="dur">' + esc(dur) + '</span>' : '') + '</div>' +
        badge +
        '<div class="face">' + media + '</div>' +
        '<button class="port in" data-side="in" type="button" aria-label="输入"></button>' +
        '<button class="port out" data-side="out" type="button" aria-label="输出"></button></div>';
    }
    const thumb = n.url
      ? '<img class="thumb" src="' + esc(n.url) + '" alt="">'
      : '<div class="ph">▣</div>';
    return '<div class="card asset' + sel + multi + '" data-id="' + esc(n.id) + '" style="left:' + n.x + 'px;top:' + n.y + 'px">' +
      badge + thumb + '<div class="name">' + esc(n.title) + '</div>' +
      '<button class="port out" data-side="out" type="button" aria-label="输出"></button></div>';
  }
  function renderGroupBounds() {
    world.querySelectorAll(".group-bound").forEach((el) => el.remove());
    pruneGroups();
    (state.groups || []).forEach((g) => {
      const members = (g.memberIds || []).map(nodeById).filter(Boolean);
      if (members.length < 2) return;
      let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
      members.forEach((n) => {
        const b = box(n);
        minX = Math.min(minX, n.x);
        minY = Math.min(minY, n.y);
        maxX = Math.max(maxX, n.x + b.w);
        maxY = Math.max(maxY, n.y + b.h);
      });
      const pad = 40;
      const left = minX - pad;
      const top = minY - pad - 10;
      const w = maxX - minX + pad * 2;
      const h = maxY - minY + pad * 2 + 12;
      const shotN = members.filter((n) => n.kind === "shot").length;
      const label = (g.name || "组") + " · " + members.length + "项" + (shotN ? (" · " + shotN + "分镜") : " · 无分镜");
      world.insertAdjacentHTML("beforeend",
        '<div class="group-bound" data-gid="' + esc(g.id) + '" style="left:' + left + 'px;top:' + top +
        'px;width:' + w + 'px;height:' + h + 'px"><span class="gname">' + esc(label) + '</span></div>');
    });
  }
  function renderCards() {
    world.querySelectorAll(".card,.group-bound").forEach((el) => el.remove());
    renderGroupBounds();
    state.nodes.forEach((n) => world.insertAdjacentHTML("beforeend", cardHTML(n)));
    drawMinimap();
    syncGroupRunBtn();
    syncSelBar();
  }

  function worldBounds() {
    if (!state.nodes.length) return { minX: 0, minY: 0, maxX: 1600, maxY: 1000 };
    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
    state.nodes.forEach((n) => {
      const b = box(n);
      minX = Math.min(minX, n.x);
      minY = Math.min(minY, n.y);
      maxX = Math.max(maxX, n.x + b.w);
      maxY = Math.max(maxY, n.y + b.h);
    });
    const pad = 120;
    return { minX: minX - pad, minY: minY - pad, maxX: maxX + pad, maxY: maxY + pad };
  }

  function drawMinimap() {
    const cv = $("minimapCv");
    if (!cv) return;
    const ctx = cv.getContext("2d");
    const W = cv.width, H = cv.height;
    ctx.clearRect(0, 0, W, H);
    ctx.fillStyle = "#121216";
    ctx.fillRect(0, 0, W, H);
    const b = worldBounds();
    const bw = Math.max(1, b.maxX - b.minX);
    const bh = Math.max(1, b.maxY - b.minY);
    const scale = Math.min(W / bw, H / bh);
    const ox = (W - bw * scale) / 2;
    const oy = (H - bh * scale) / 2;
    state._mmap = { b: b, scale: scale, ox: ox, oy: oy, W: W, H: H };
    state.nodes.forEach((n) => {
      const nb = box(n);
      const x = ox + (n.x - b.minX) * scale;
      const y = oy + (n.y - b.minY) * scale;
      const w = Math.max(2, nb.w * scale);
      const h = Math.max(2, nb.h * scale);
      ctx.fillStyle = n.kind === "shot" ? "#3a3a48" : "#2a3a36";
      ctx.fillRect(x, y, w, h);
      if (state.selected === n.id) {
        ctx.strokeStyle = n.kind === "shot" ? "#fff" : "#5ee0c5";
        ctx.lineWidth = 1;
        ctx.strokeRect(x, y, w, h);
      }
    });
    const r = vp.getBoundingClientRect();
    const wx0 = -state.cam.x / state.cam.s;
    const wy0 = -state.cam.y / state.cam.s;
    const ww = r.width / state.cam.s;
    const wh = r.height / state.cam.s;
    const fx = ox + (wx0 - b.minX) * scale;
    const fy = oy + (wy0 - b.minY) * scale;
    const fw = ww * scale;
    const fh = wh * scale;
    ctx.strokeStyle = "rgba(94,224,197,.85)";
    ctx.lineWidth = 1.2;
    ctx.strokeRect(fx, fy, fw, fh);
    ctx.fillStyle = "rgba(94,224,197,.08)";
    ctx.fillRect(fx, fy, fw, fh);
  }

  function panFromMinimap(cx, cy) {
    const mm = $("minimap");
    const meta = state._mmap;
    if (!mm || !meta) return;
    const r = mm.getBoundingClientRect();
    const mx = ((cx - r.left) / r.width) * meta.W;
    const my = ((cy - r.top) / r.height) * meta.H;
    const wx = meta.b.minX + (mx - meta.ox) / meta.scale;
    const wy = meta.b.minY + (my - meta.oy) / meta.scale;
    const vr = vp.getBoundingClientRect();
    state.cam.x = vr.width / 2 - wx * state.cam.s;
    state.cam.y = vr.height / 2 - wy * state.cam.s;
    applyCam();
    persist();
  }

  function positionDock() {
    if (!dock || !dock.classList.contains("show")) return;
    const n = nodeById(state.selected);
    if (!n || n.kind !== "shot") {
      dock.classList.remove("near");
      dock.style.left = "";
      dock.style.top = "";
      dock.style.bottom = "";
      dock.style.transform = "";
      return;
    }
    const stage = dock.parentElement;
    if (!stage) return;
    const sr = stage.getBoundingClientRect();
    const vr = vp.getBoundingClientRect();
    const b = box(n);
    const sx = vr.left + state.cam.x + (n.x + b.w / 2) * state.cam.s;
    const syBottom = vr.top + state.cam.y + (n.y + b.h) * state.cam.s;
    const syTop = vr.top + state.cam.y + n.y * state.cam.s;
    const dockW = Math.min(860, Math.max(320, sr.width - 80));
    dock.style.width = dockW + "px";
    const dw = dock.offsetWidth || dockW;
    const dh = dock.offsetHeight || 260;
    let left = sx - sr.left - dw / 2;
    left = Math.max(16, Math.min(left, sr.width - dw - 16));
    let top = syBottom - sr.top + 14;
    if (top + dh > sr.height - 12) {
      top = syTop - sr.top - dh - 28;
    }
    if (top < 56) top = Math.max(56, sr.height - dh - 16);
    dock.classList.add("near");
    dock.style.left = left + "px";
    dock.style.top = top + "px";
    dock.style.bottom = "auto";
    dock.style.transform = "none";
  }

  function renderRail() {
    const rail = $("assetRail");
    if (!rail) return;
    const shot = nodeById(state.selected);
    const canPin = shot && shot.kind === "shot";
    const tabAssets = state.railTab !== "history";
    const tabs = '<div class="rail-tabs">' +
      '<button type="button" data-tab="assets"' + (tabAssets ? ' class="on"' : "") + ">资产</button>" +
      '<button type="button" data-tab="history"' + (!tabAssets ? ' class="on"' : "") + ">历史</button></div>";
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
      dock.classList.remove("near");
      hideSkillbox();
      hideAtbox();
      const picker = $("picker");
      if (picker) picker.classList.remove("show");
      renderRail();
      return;
    }
    dock.classList.add("show");
    $("prompt").value = n.prompt || "";
    ["text", "image", "video", "audio"].forEach((m) => {
      const el = $("mode" + (m === "image" ? "Img" : m === "video" ? "Vid" : m === "text" ? "Text" : "Aud"));
      if (el) el.classList.toggle("on", state.mode === m);
    });
    const list = assets();
    const linked = connectedAssets(n.id);
    const frame = frameAsset(n);
    const needFrame = state.mode === "video" && !frame;
    const stub = isStubMode();
    if ($("send")) $("send").disabled = needFrame || stub;
    if (stub) {
      setMsg((state.mode === "text" ? "文本生成" : "音频生成") + " · 本版未接", "warn");
    } else if (needFrame) {
      setMsg("视频需要先连一张首帧图", "warn");
    }
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
    requestAnimationFrame(positionDock);
  }

  function selectNode(id, opts) {
    opts = opts || {};
    if (opts.shift && id) {
      toggleMulti(id);
      state.selected = id;
    } else {
      state.selected = id;
      setMulti(id ? [id] : []);
    }
    renderCards();
    drawWires();
    renderDock();
    syncGroupRunBtn();
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

  function invalidateStageProgress(shot, reason) {
    if (!shot || shot.kind !== "shot") return;
    shot.stageUrls = {};
    if (state.runningGroup) state.groupRunAbort = true;
    if (reason) setMsg(reason, "warn");
  }

  function linkAssetToShot(asset, shot) {
    if (!asset || !shot || shot.kind !== "shot" || asset.id === shot.id) return;
    if (asset.kind === "shot" && !isImageSource(asset)) return;
    if (!state.edges.some((e) => e.from === asset.id && e.to === shot.id)) {
      state.edges.push({ from: asset.id, to: shot.id });
      invalidateStageProgress(shot);
    }
    mention(asset, shot);
    if (shot && !shot.firstFrameId && isImageSource(asset)) shot.firstFrameId = asset.id;
  }
  function unlinkAssetFromShot(asset, shot) {
    if (!asset || !shot) return;
    const had = state.edges.some((e) => e.from === asset.id && e.to === shot.id);
    state.edges = state.edges.filter((e) => !(e.from === asset.id && e.to === shot.id));
    unmention(asset, shot);
    if (shot && shot.firstFrameId === asset.id) shot.firstFrameId = "";
    if (had) invalidateStageProgress(shot);
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
    hideSkillbox();
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
    hideSkillbox();
    renderCards(); drawWires(); renderDock(); persist();
  }

  function slashQueryAt(before) {
    const slash = before.lastIndexOf("/");
    if (slash < 0) return null;
    if (slash > 0 && !/[\s\n]/.test(before.charAt(slash - 1))) return null;
    const q = before.slice(slash + 1);
    if (/[\s\n]/.test(q)) return null;
    return { slash: slash, query: q };
  }
  function hideSkillbox() {
    const box = $("skillbox");
    if (box) box.classList.remove("show");
    const btn = $("btnSkill");
    if (btn) btn.classList.remove("on");
  }
  function showSkillbox(query, opts) {
    const box = $("skillbox");
    if (!box) return;
    hideAtbox();
    const picker = $("picker");
    if (picker) picker.classList.remove("show");
    const q = String(query || "").trim().toLowerCase();
    const filterMode = !!(opts && opts.filter);
    let cat = state.skillCat || SKILL_CATS[0];
    if (filterMode && q) {
      const hit = SKILLS.find((s) =>
        s.title.toLowerCase().indexOf(q) >= 0 || s.id.toLowerCase().indexOf(q) >= 0);
      if (hit) cat = hit.category;
    }
    if (SKILL_CATS.indexOf(cat) < 0) cat = SKILL_CATS[0];
    state.skillCat = cat;
    const catsHtml = SKILL_CATS.map((c) =>
      '<button type="button" class="sk-cat' + (c === cat ? " on" : "") + '" data-skcat="' + esc(c) + '">' + esc(c) + "</button>"
    ).join("");
    let list = SKILLS.filter((s) => s.category === cat);
    if (filterMode && q) {
      list = SKILLS.filter((s) =>
        s.title.toLowerCase().indexOf(q) >= 0 ||
        s.id.toLowerCase().indexOf(q) >= 0 ||
        s.category.toLowerCase().indexOf(q) >= 0
      );
    }
    let body;
    if (!list.length) {
      body = '<div class="sk-empty">' + (filterMode && q ? "没有匹配的 Skill" : "该分类暂无 Skill") + "</div>";
    } else {
      body = list.map((s) =>
        '<button type="button" class="sk-item" data-skill="' + esc(s.id) + '">' +
        '<span class="sk-title">' + esc(s.title) + "</span>" +
        '<span class="sk-preview">' + esc(String(s.template || "").split("\n").join(" ")) + "</span>" +
        "</button>"
      ).join("");
    }
    box.innerHTML = '<div class="sk-hd">' + catsHtml + '</div><div class="sk-list">' + body + "</div>";
    box.classList.add("show");
    const btn = $("btnSkill");
    if (btn) btn.classList.add("on");
  }
  function applySkill(skill) {
    if (!skill) return;
    const shot = nodeById(state.selected);
    if (!shot || shot.kind !== "shot") return;
    const ta = $("prompt");
    const tpl = skill.template || "";
    let next = tpl;
    if (ta) {
      const v = ta.value || "";
      const caret = ta.selectionStart != null ? ta.selectionStart : v.length;
      const before = v.slice(0, caret);
      const sq = slashQueryAt(before);
      if (sq) {
        next = v.slice(0, sq.slash) + tpl + v.slice(caret);
      } else {
        next = tpl;
      }
      shot.prompt = next;
      ta.value = next;
      try {
        const pos = next.length;
        ta.focus();
        ta.setSelectionRange(pos, pos);
      } catch (_) {}
    } else {
      shot.prompt = next;
    }
    hideSkillbox();
    hideAtbox();
    renderCards(); drawWires(); renderDock(); persist();
    setMsg("已插入 Skill「" + skill.title + "」· 不会触发生成", "ok");
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


  function importKey(it) {
    return String((it && (it.key || it.url || it.id)) || "");
  }
  function collectImportLibrary() {
    const seen = {};
    const out = [];
    function push(it) {
      if (!it || !it.url) return;
      const key = importKey(it);
      if (!key || seen[key]) return;
      seen[key] = true;
      out.push({
        key: key,
        url: it.url,
        title: it.title || "素材",
        kind: mediaKindOf(it.url, it.kind),
        nodeId: it.nodeId || "",
        source: it.source || "project",
      });
    }
    assets().forEach((a) => push({
      url: a.url, title: sourceTitle(a), kind: mediaKindOf(a.url), nodeId: a.id, source: "canvas", key: "node:" + a.id,
    }));
    state.history.forEach((h, i) => push({
      url: h.url, title: h.title || "历史成片", kind: mediaKindOf(h.url, h.kind), source: "history", key: "hist:" + (h.url || i),
    }));
    (state.importLibrary || []).forEach((it) => push(Object.assign({ source: "outs" }, it)));
    return out;
  }
  function filteredImportItems() {
    const tab = state.importTab || "project";
    let list = collectImportLibrary();
    if (tab === "story" || tab === "avatar") return [];
    if (tab === "canvas") list = list.filter((it) => it.source === "canvas" || it.nodeId);
    const f = state.importFilter || "all";
    if (f !== "all") list = list.filter((it) => it.kind === f);
    return list;
  }
  function renderImportModal() {
    const body = $("importBody");
    const modal = $("importModal");
    if (!body || !modal || !modal.classList.contains("show")) return;
    document.querySelectorAll("#importTabs [data-itab]").forEach((btn) => {
      btn.classList.toggle("on", btn.dataset.itab === state.importTab);
    });
    document.querySelectorAll(".import-filters [data-ifilter]").forEach((btn) => {
      btn.classList.toggle("on", btn.dataset.ifilter === state.importFilter);
    });
    const tab = state.importTab || "project";
    if (tab === "story" || tab === "avatar") {
      body.innerHTML = '<div class="import-empty">' +
        (tab === "story" ? "故事素材库尚未接入" : "数字人素材库尚未接入") +
        "<br><span style='color:#555'>本版不做 SenseTime / 云端拉取</span></div>";
      const all = $("importSelectAll");
      if (all) { all.checked = false; all.disabled = true; }
      updateImportConfirm();
      return;
    }
    const list = filteredImportItems();
    if (!list.length) {
      body.innerHTML = '<div class="import-empty">暂无素材 · 可用「本地上传」加入</div>';
    } else {
      body.innerHTML = '<div class="import-grid">' + list.map((it) => {
        const on = !!state.importSelected[it.key];
        const badge = kindBadgeLabel(it.kind);
        const media = it.kind === "video"
          ? '<video src="' + esc(it.url) + '" muted></video>'
          : (it.kind === "audio"
            ? '<div class="ph">♪</div>'
            : '<img src="' + esc(it.url) + '" alt="">');
        return '<button type="button" class="import-card' + (on ? " on" : "") + '" data-ikey="' + esc(it.key) + '" title="' + esc(it.title) + '">' +
          '<span class="ibadge">' + esc(badge) + "</span>" +
          '<span class="icheck"></span>' + media + "</button>";
      }).join("") + "</div>";
    }
    const visibleKeys = list.map((it) => it.key);
    const allOn = visibleKeys.length > 0 && visibleKeys.every((k) => state.importSelected[k]);
    const all = $("importSelectAll");
    if (all) { all.disabled = !visibleKeys.length; all.checked = allOn; }
    updateImportConfirm();
  }
  function updateImportConfirm() {
    const n = Object.keys(state.importSelected).length;
    const btn = $("importConfirm");
    if (!btn) return;
    btn.textContent = "确认导入(" + n + ")";
    btn.disabled = n === 0;
  }
  function openImportModal() {
    const modal = $("importModal");
    if (!modal) return;
    state.importSelected = {};
    state.importTab = "project";
    state.importFilter = "all";
    modal.classList.add("show");
    modal.setAttribute("aria-hidden", "false");
    hideAtbox();
    hideSkillbox();
    const picker = $("picker");
    if (picker) picker.classList.remove("show");
    renderImportModal();
    refreshImportLibrary().then(() => renderImportModal());
  }
  function closeImportModal() {
    const modal = $("importModal");
    if (!modal) return;
    modal.classList.remove("show");
    modal.setAttribute("aria-hidden", "true");
    state.importSelected = {};
  }
  async function refreshImportLibrary() {
    try {
      const r = await fetch("/api/outs");
      const j = await r.json();
      state.importLibrary = (j.items || []).slice(0, 60).map((it) => ({
        key: "out:" + (it.url || it.file),
        url: it.url || it.path,
        title: String(it.file || it.name || "素材").replace(/\.[^.]+$/, ""),
        kind: it.kind || mediaKindOf(it.url),
        source: "outs",
      })).filter((it) => it.url);
    } catch (_) {
      /* keep prior library; assets+history still available */
    }
  }
  function confirmImportSelection() {
    const keys = Object.keys(state.importSelected);
    if (!keys.length) return;
    const lib = collectImportLibrary();
    const byKey = {};
    lib.forEach((it) => { byKey[it.key] = it; });
    const shot = nodeById(state.selected);
    let placed = 0;
    let baseY = 24 + assets().length * 40;
    keys.forEach((k, i) => {
      const it = byKey[k] || state.importSelected[k];
      if (!it || !it.url) return;
      if (it.nodeId && nodeById(it.nodeId)) {
        const existing = nodeById(it.nodeId);
        if (shot && shot.kind === "shot") linkAssetToShot(existing, shot);
        placed++;
        return;
      }
      const node = spawnHistoryAt({ url: it.url, title: it.title || "导入素材" }, 220 + (i % 3) * 24, baseY + i * 40);
      if (node) {
        placed++;
        if (shot && shot.kind === "shot") linkAssetToShot(node, shot);
      }
    });
    closeImportModal();
    renderCards(); drawWires(); renderDock(); persist();
    setMsg(placed ? ("已导入 " + placed + " 个素材到画布") : "没有可导入的素材", placed ? "ok" : "warn");
  }
  function setZoomScale(s) {
    const next = Math.min(1.5, Math.max(0.16, s));
    const r = vp.getBoundingClientRect();
    const cx = r.width / 2, cy = r.height / 2;
    const w0 = clientToWorld(r.left + cx, r.top + cy);
    state.cam.s = next;
    state.cam.x = cx - w0.x * next;
    state.cam.y = cy - w0.y * next;
    applyCam(); persist();
    syncZoomPresets();
  }
  function fitCam() {
    state.cam = { x: 90, y: 36, s: 0.5 };
    applyCam(); persist();
    syncZoomPresets();
  }
  function syncZoomPresets() {
    const box = $("zPresets");
    if (!box) return;
    const s = state.cam.s;
    box.querySelectorAll("button[data-z]").forEach((btn) => {
      const v = btn.dataset.z;
      if (v === "fit") { btn.classList.remove("on"); return; }
      const num = Number(v);
      btn.classList.toggle("on", Math.abs(s - num) < 0.02);
    });
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

  function disconnectEdgeAt(index) {
    const e = state.edges[index];
    if (!e) return;
    const src = nodeById(e.from);
    const dst = nodeById(e.to);
    if (src && dst) unlinkAssetFromShot(src, dst);
    else {
      state.edges.splice(index, 1);
      if (dst) invalidateStageProgress(dst);
      if (src) invalidateStageProgress(src);
    }
    drawWires();
    renderDock();
    persist();
    setMsg("已断开连线 · 多步成片进度已清空，请重新校验", "warn");
  }

  wires.addEventListener("click", (e) => {
    const path = e.target.closest("path.edge");
    if (!path) return;
    e.stopPropagation();
    const ei = Number(path.getAttribute("data-ei"));
    if (!Number.isFinite(ei)) return;
    disconnectEdgeAt(ei);
  });

  if ($("minimap")) {
    $("minimap").addEventListener("pointerdown", (e) => {
      e.preventDefault();
      panFromMinimap(e.clientX, e.clientY);
      const move = (ev) => panFromMinimap(ev.clientX, ev.clientY);
      const up = () => {
        window.removeEventListener("pointermove", move);
        window.removeEventListener("pointerup", up);
      };
      window.addEventListener("pointermove", move);
      window.addEventListener("pointerup", up);
    });
  }

  vp.addEventListener("pointerdown", (e) => {
    if (e.target.closest(".dock,.tools,.zoom,.picker,.rail,.atbox,.skillbox,header,.ghost,.minimap,.import-backdrop")) return;
    if (e.target.closest("path.edge")) return;
    const gchrome = e.target.closest(".group-bound");
    if (gchrome && !e.target.closest(".card")) {
      const g = (state.groups || []).find((x) => x.id === gchrome.dataset.gid);
      if (g) {
        selectGroupMembers(g);
        e.preventDefault();
        return;
      }
    }
    const port = e.target.closest(".port");
    const card = e.target.closest(".card");
    if (port && card) {
      const n = nodeById(card.dataset.id);
      const p = portPos(n, port.dataset.side === "in" ? "in" : "out");
      state.link = { from: n.id, side: port.dataset.side, x1: p.x, y1: p.y, x2: p.x, y2: p.y };
      state.snapTarget = null;
      vp.setPointerCapture(e.pointerId);
      return;
    }
    if (card) {
      const n = nodeById(card.dataset.id);
      selectNode(n.id, { shift: !!(e.shiftKey) });
      if (e.shiftKey) {
        // multi-toggle only — skip drag start to avoid accidental moves
        return;
      }
      const w = clientToWorld(e.clientX, e.clientY);
      state.drag = { id: n.id, dx: w.x - n.x, dy: w.y - n.y };
      vp.setPointerCapture(e.pointerId);
      return;
    }
    // empty canvas click clears multi
    if (!e.shiftKey) {
      setMulti(state.selected ? [state.selected] : []);
      syncGroupRunBtn();
      renderCards();
    }
    state.pan = { x: e.clientX - state.cam.x, y: e.clientY - state.cam.y };
    vp.classList.add("grabbing");
    vp.setPointerCapture(e.pointerId);
  });
  vp.addEventListener("pointermove", (e) => {
    if (state.link) {
      const w = clientToWorld(e.clientX, e.clientY);
      state.snapTarget = nearestCompatiblePort(w.x, w.y, state.link.from, state.link.side);
      state.link.x2 = w.x;
      state.link.y2 = w.y;
      drawWires();
      return;
    }
    if (state.drag) {
      const w = clientToWorld(e.clientX, e.clientY);
      const n = nodeById(state.drag.id);
      n.x = w.x - state.drag.dx; n.y = w.y - state.drag.dy;
      renderCards(); drawWires(); positionDock(); return;
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
      const snap = state.snapTarget || nearestCompatiblePort(w.x, w.y, state.link.from, state.link.side);
      let target = snap ? nodeById(snap.id) : hitNode(w.x, w.y);
      if (target && target.id !== state.link.from) {
        const a = nodeById(state.link.from);
        const dst = target.kind === "shot" ? target : (a.kind === "shot" ? a : null);
        const src = dst === target ? a : target;
        if (src && dst && canLink(src, dst)) {
          linkAssetToShot(src, dst);
          selectNode(dst.id);
        }
      }
      state.link = null;
      state.snapTarget = null;
      drawWires(); persist();
    }
    if (state.drag) { persist(); positionDock(); }
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
    if (act.dataset.act === "pick") openImportModal();
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
      if (up && up.dataset.act === "upload") { openImportModal(); return; }
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
    if ($("importModal") && $("importModal").classList.contains("show")) {
      refreshImportLibrary().then(() => renderImportModal());
    }
  });

  function togglePicker() {
    openCanvasPicker(true);
  }
  function openCanvasPicker(toggle) {
    const box = $("picker");
    if (!box) return;
    hideAtbox();
    hideSkillbox();
    if (toggle && box.classList.contains("show")) {
      box.classList.remove("show");
      const cref = $("btnCanvasRef");
      if (cref) cref.classList.remove("on");
      return;
    }
    const list = assets().concat(shots().filter(isImageSource));
    box.innerHTML = list.map((a) =>
      '<button type="button" data-asset="' + esc(a.id) + '">' +
      (a.url ? '<img src="' + esc(a.url) + '" alt="">' : "") + esc(sourceTitle(a)) + "</button>"
    ).join("") || "<div style='color:#888;padding:8px'>还没有资产</div>";
    box.classList.add("show");
    const cref = $("btnCanvasRef");
    if (cref) cref.classList.add("on");
  }
  $("picker").addEventListener("click", (e) => {
    const btn = e.target.closest("[data-asset]");
    if (!btn) return;
    const asset = nodeById(btn.dataset.asset);
    const shot = nodeById(state.selected);
    if (asset && shot) {
      // 画布引用：确保 @ + 真实 edge（已连则保持/再次 mention）
      linkAssetToShot(asset, shot);
    }
    $("picker").classList.remove("show");
    const cref = $("btnCanvasRef");
    if (cref) cref.classList.remove("on");
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
  if ($("skillbox")) {
    $("skillbox").addEventListener("click", (e) => {
      const cat = e.target.closest("[data-skcat]");
      if (cat) {
        state.skillCat = cat.dataset.skcat;
        showSkillbox("", { filter: false });
        return;
      }
      const item = e.target.closest("[data-skill]");
      if (!item) return;
      const skill = SKILLS.find((s) => s.id === item.dataset.skill);
      if (skill) applySkill(skill);
    });
  }
  if ($("btnSkill")) {
    $("btnSkill").onclick = () => {
      const box = $("skillbox");
      if (box && box.classList.contains("show")) hideSkillbox();
      else showSkillbox("", { filter: false });
    };
  }
  if ($("btnAttach")) {
    $("btnAttach").onclick = () => openImportModal();
  }
  if ($("btnCanvasRef")) {
    $("btnCanvasRef").onclick = () => openCanvasPicker(true);
  }

  $("prompt").addEventListener("input", () => {
    const n = nodeById(state.selected);
    if (n) { n.prompt = $("prompt").value; persist(); }
    const ta = $("prompt");
    const v = ta.value || "";
    const caret = ta.selectionStart || v.length;
    const before = v.slice(0, caret);
    const at = before.lastIndexOf("@");
    const atOpen = at >= 0 && !/[\s\n]/.test(before.slice(at + 1));
    const sq = slashQueryAt(before);
    if (atOpen && (!sq || at > sq.slash)) {
      hideSkillbox();
      showAtbox(before.slice(at + 1));
    } else if (sq && (!atOpen || sq.slash > at)) {
      hideAtbox();
      showSkillbox(sq.query, { filter: true });
    } else {
      hideAtbox();
      hideSkillbox();
    }
  });

  function setMode(mode) {
    state.mode = mode;
    renderCards();
    drawWires();
    renderDock();
    persist();
  }
  if ($("modeText")) $("modeText").onclick = () => setMode("text");
  if ($("modeImg")) $("modeImg").onclick = () => setMode("image");
  if ($("modeVid")) $("modeVid").onclick = () => setMode("video");
  if ($("modeAud")) $("modeAud").onclick = () => setMode("audio");
  ["backend", "service", "duration", "aspect", "res"].forEach((id) => {
    if ($(id)) $(id).addEventListener("change", () => {
      persist();
      if (id === "duration" && state.mode === "video") {
        renderCards(); drawWires(); positionDock();
      }
    });
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

  function hasUnresolvedStageOut(obj) {
    if (Array.isArray(obj)) return obj.some(hasUnresolvedStageOut);
    if (obj && typeof obj === "object") {
      if (obj.__stageOut__) return true;
      return Object.keys(obj).some((k) => hasUnresolvedStageOut(obj[k]));
    }
    return false;
  }

  function fillStageRefs(payload, urls) {
    const p = JSON.parse(JSON.stringify(payload || {}));
    function walk(v) {
      if (Array.isArray(v)) return v.map(walk);
      if (v && typeof v === "object") {
        if (v.__stageOut__) {
          const u = urls[String(v.__stageOut__)];
          return u || v;
        }
        const out = {};
        Object.keys(v).forEach((k) => { out[k] = walk(v[k]); });
        return out;
      }
      return v;
    }
    return walk(p);
  }

  function nextRunnableStage(j, urls) {
    const stages = (j && j.stages) || [];
    for (let i = 0; i < stages.length; i++) {
      const s = stages[i];
      if (urls[String(s.id)]) continue;
      const needs = s.needs || [];
      if (needs.every((id) => urls[String(id)])) return s;
    }
    return null;
  }

  // Per-shot step runner — same path as Composer send (compile → nextRunnableStage → fillStageRefs → /api/generate).
  // Never one-shot a multi-step graph. Returns { status, stageOp } where status is:
  // done | more | blocked | error | aborted
  async function runShotStep(shotId, opts) {
    opts = opts || {};
    const shot = nodeById(shotId);
    if (!shot || shot.kind !== "shot") return { status: "blocked" };
    if (state.groupRunAbort) return { status: "aborted" };
    const prefix = opts.progressPrefix ? (opts.progressPrefix + " · ") : "";
    if (isStubMode()) {
      setMsg(prefix + (state.mode === "text" ? "文本生成" : "音频生成") + " · 本版未接", "warn");
      return { status: "blocked" };
    }
    if (state.mode === "video" && !frameAsset(shot)) {
      setMsg(prefix + "视频需要先连一张首帧图，不能偷配方台", "bad");
      return { status: "blocked" };
    }
    if (!opts.keepSend) $("send").disabled = true;
    setMsg(prefix + "校验连线…");
    let compiled;
    try {
      const r = await fetch("/api/graph/compile", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify(buildGraph(shot)),
      });
      compiled = await r.json();
    } catch (e) {
      setMsg(prefix + String(e), "bad");
      if (!opts.keepSend) $("send").disabled = false;
      return { status: "error" };
    }
    if (state.groupRunAbort) {
      if (!opts.keepSend) $("send").disabled = false;
      return { status: "aborted" };
    }
    if (!compiled.ok) {
      setMsg(prefix + (compiled.error || "校验未通过"), "bad");
      if (!opts.keepSend) $("send").disabled = false;
      return { status: "blocked" };
    }
    // Never one-shot a multi-step plan via stage-zero payload or whole compile body.
    var staged = !!(compiled.multiStep || compiled.execute === "staged" ||
      (Array.isArray(compiled.stages) && compiled.stages.length > 1));
    let payload = null;
    let stage = null;
    if (staged) {
      if (!shot.stageUrls) shot.stageUrls = {};
      stage = nextRunnableStage(compiled, shot.stageUrls);
      if (!stage || !stage.payload) {
        setMsg(prefix + (compiled.note || "多步链需按序物化上游") + " · 禁止一次假跑通", "warn");
        if (!opts.keepSend) $("send").disabled = false;
        return { status: "blocked", stageOp: stage && stage.op };
      }
      payload = fillStageRefs(stage.payload, shot.stageUrls);
      if (hasUnresolvedStageOut(payload)) {
        setMsg(prefix + "上游还没有成片地址，不能偷配方台图 · 禁止一次假跑通", "bad");
        if (!opts.keepSend) $("send").disabled = false;
        return { status: "blocked", stageOp: stage.op };
      }
    } else {
      // single-step only — never stage-zero payload fallback
      payload = compiled.payload;
      if (!payload) {
        setMsg(prefix + "没有 payload", "bad");
        if (!opts.keepSend) $("send").disabled = false;
        return { status: "blocked" };
      }
    }
    const stageOp = stage ? stage.op : "";
    if (prefix) setMsg(prefix + (stage ? (stage.op + "…") : "请求中…"));
    else setMsg(stage ? ("逐步跑 · " + stage.op + "…") : "正在请求云 API…");
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
          if (state.groupRunAbort) {
            if (!opts.keepSend) $("send").disabled = false;
            return { status: "aborted", stageOp: stageOp };
          }
          await new Promise((res) => setTimeout(res, 2500));
          const st = await (await fetch("/api/jobs/" + encodeURIComponent(jobId))).json();
          if (st.error || st.status === "failed") throw new Error(st.error || "任务失败");
          if (pickUrl(st) || st.status === "done" || st.status === "succeeded" || st.status === "completed") { j = st; break; }
          setMsg(prefix + "云端进行中 " + (i + 1) + "/40");
        }
      }
      if (state.groupRunAbort) {
        if (!opts.keepSend) $("send").disabled = false;
        return { status: "aborted", stageOp: stageOp };
      }
      const url = pickUrl(j);
      if (url && stage) {
        shot.stageUrls[String(stage.id)] = url;
        const nxt = nextRunnableStage(compiled, shot.stageUrls);
        if (nxt) {
          persist();
          setMsg(prefix + "完成 " + stage.op + " · 多步链：按 stages 逐步跑，不假装一次出片（禁止一次假跑通）", "warn");
          if (!opts.keepSend) $("send").disabled = false;
          renderDock();
          return { status: "more", stageOp: stage.op };
        }
        shot.url = url;
        if (!isVideoUrl(url)) promoteResult(shot, url);
        renderCards(); drawWires(); persist();
        setMsg(prefix + (isVideoUrl(url) ? "此镜视频完成" : "此镜完成，成片已收进资产库"), "ok");
      } else if (url) {
        shot.url = url;
        if (!isVideoUrl(url)) promoteResult(shot, url);
        renderCards(); drawWires(); persist();
        setMsg(prefix + (isVideoUrl(url) ? "此镜视频完成" : "此镜完成，成片已收进资产库"), "ok");
      } else {
        setMsg(prefix + "云端已返回，没有可预览地址", "warn");
        if (!opts.keepSend) $("send").disabled = false;
        renderDock();
        return { status: "blocked", stageOp: stageOp };
      }
    } catch (e) {
      setMsg(prefix + String(e), "bad");
      if (!opts.keepSend) $("send").disabled = false;
      renderDock();
      return { status: "error", stageOp: stageOp };
    }
    if (!opts.keepSend) $("send").disabled = false;
    renderDock();
    return { status: "done", stageOp: stageOp };
  }

  async function generate() {
    await runShotStep(state.selected, {});
  }
  $("send").onclick = generate;

  async function runShotUntilDone(shotId, progressPrefix) {
    // Loop nextRunnableStage for one shot via the same step runner — do not skip gates.
    let guard = 0;
    while (guard++ < 24) {
      if (state.groupRunAbort) return { status: "aborted" };
      const r = await runShotStep(shotId, { progressPrefix: progressPrefix, keepSend: true });
      if (r.status === "more") continue;
      return r;
    }
    return { status: "blocked" };
  }

  async function runGroupSequential() {
    const targets = groupRunTargets();
    if (!targets.length || state.runningGroup) return;
    state.runningGroup = true;
    state.groupRunAbort = false;
    $("send").disabled = true;
    syncGroupRunBtn();
    const total = targets.length;
    let stopped = false;
    for (let i = 0; i < targets.length; i++) {
      if (state.groupRunAbort) {
        setMsg("整组已中止 · 拓扑变更清空了 stageUrls", "warn");
        stopped = true;
        break;
      }
      const shot = targets[i];
      state.selected = shot.id;
      setMulti(targets.map((t) => t.id));
      renderCards();
      drawWires();
      renderDock();
      const prefix = "整组 " + (i + 1) + "/" + total + " · " + (shot.title || "镜头");
      setMsg(prefix + " · 准备…");
      const r = await runShotUntilDone(shot.id, prefix);
      if (state.groupRunAbort || r.status === "aborted") {
        setMsg("整组已中止 · 拓扑变更清空了 stageUrls", "warn");
        stopped = true;
        break;
      }
      if (r.status === "blocked" || r.status === "error") {
        setMsg(prefix + " · 已停在此镜" + (r.stageOp ? (" · " + r.stageOp) : ""), r.status === "error" ? "bad" : "warn");
        stopped = true;
        break;
      }
    }
    if (!stopped && !state.groupRunAbort) {
      setMsg("整组完成 · " + total + " 镜", "ok");
    }
    state.runningGroup = false;
    $("send").disabled = false;
    syncGroupRunBtn();
    syncSelBar();
    renderDock();
  }

  function createGroupFromSelection() {
    pruneGroups();
    let ids = state.multi.slice();
    if (ids.length < 2 && state.selected) ids = [state.selected].concat(ids.filter((x) => x !== state.selected));
    ids = ids.filter((id) => nodeById(id));
    // prefer shots; allow mixed but need >=2
    if (ids.length < 2) {
      setMsg("成组需要至少 2 个已选卡片（Shift+点击多选）", "warn");
      return;
    }
    // remove overlapping memberships from other groups
    state.groups.forEach((g) => {
      g.memberIds = (g.memberIds || []).filter((id) => ids.indexOf(id) < 0);
    });
    pruneGroups();
    const name = "组" + (state.groups.length + 1);
    const g = { id: uid("grp"), name: name, memberIds: ids.slice() };
    state.groups.push(g);
    setMulti(ids);
    renderCards(); drawWires(); persist();
    syncGroupRunBtn();
    syncSelBar();
    const bound = world.querySelector('.group-bound[data-gid="' + g.id + '"]');
    if (bound) {
      bound.classList.add("flash");
      setTimeout(() => bound.classList.remove("flash"), 800);
    }
    const shotN = ids.map(nodeById).filter((n) => n && n.kind === "shot").length;
    if (shotN < 1) {
      setMsg("已成组 · " + name + "（虚线框「" + name + "」）· ▶整组需组内有分镜", "warn");
    } else {
      setMsg("已成组 · " + name + "（虚线框已标）· 可用「▶ 整组」逐步跑", "ok");
    }
  }
  function ungroupSelection() {
    pruneGroups();
    const ids = state.multi.length ? state.multi.slice() : (state.selected ? [state.selected] : []);
    if (!ids.length) {
      setMsg("先选择组内卡片再解组", "warn");
      return;
    }
    let removed = 0;
    state.groups = state.groups.filter((g) => {
      const hit = (g.memberIds || []).some((id) => ids.indexOf(id) >= 0);
      if (hit) { removed++; return false; }
      return true;
    });
    renderCards(); drawWires(); persist();
    syncGroupRunBtn();
    syncSelBar();
    setMsg(removed ? ("已解组 · " + removed) : "选中项不在任何组内", removed ? "ok" : "warn");
  }
  if ($("btnGroup")) $("btnGroup").onclick = createGroupFromSelection;
  if ($("btnUngroup")) $("btnUngroup").onclick = ungroupSelection;
  if ($("btnGroupRun")) $("btnGroupRun").onclick = () => { runGroupSequential(); };
  if ($("selGroup")) $("selGroup").onclick = createGroupFromSelection;
  if ($("selUngroup")) $("selUngroup").onclick = ungroupSelection;
  if ($("selGroupRun")) $("selGroupRun").onclick = () => { runGroupSequential(); };
  syncSelBar();

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
  function autoLayout() {
    const g = findActiveGroup();
    const scopeIds = g ? (g.memberIds || []).slice() : null;
    const shotList = shots().filter((n) => !scopeIds || scopeIds.indexOf(n.id) >= 0);
    const assetList = assets().filter((n) => {
      if (!scopeIds) return true;
      return state.edges.some((e) => e.from === n.id && scopeIds.indexOf(e.to) >= 0);
    });
    const startX = scopeIds ? (shotList[0] ? shotList[0].x : 560) : 560;
    const startY = scopeIds ? (shotList[0] ? Math.min.apply(null, shotList.map((s) => s.y)) : 80) : 80;
    const gapX = 720;
    shotList.forEach((n, i) => {
      n.x = startX + i * gapX;
      n.y = startY;
    });
    const placed = {};
    shotList.forEach((shot) => {
      const linked = connectedNodes(shot.id);
      linked.forEach((a, j) => {
        if (!a || a.kind === "shot") return;
        if (scopeIds && scopeIds.indexOf(a.id) < 0 && assetList.indexOf(a) < 0) {
          // still place assets linked into scoped shots
        }
        if (placed[a.id]) return;
        a.x = shot.x - 180;
        a.y = shot.y + j * 220;
        placed[a.id] = true;
      });
    });
    if (!scopeIds) {
      let orphan = 0;
      assets().forEach((a) => {
        if (placed[a.id]) return;
        a.x = 48;
        a.y = 24 + orphan * 236;
        orphan++;
        placed[a.id] = true;
      });
    }
    renderCards(); drawWires(); persist();
  }
  $("btnAuto").onclick = () => { autoLayout(); };
  $("btnFit").onclick = () => { fitCam(); };
  $("zIn").onclick = () => { setZoomScale(state.cam.s * 1.12); };
  $("zOut").onclick = () => { setZoomScale(state.cam.s * 0.9); };
  if ($("zPresets")) {
    $("zPresets").addEventListener("click", (e) => {
      const btn = e.target.closest("button[data-z]");
      if (!btn) return;
      if (btn.dataset.z === "fit") fitCam();
      else setZoomScale(Number(btn.dataset.z));
    });
  }
  if ($("btnImport")) $("btnImport").onclick = () => openImportModal();

  function bindImportModal() {
    const modal = $("importModal");
    if (!modal) return;
    modal.addEventListener("click", (e) => {
      if (e.target === modal) closeImportModal();
    });
    if ($("importClose")) $("importClose").onclick = closeImportModal;
    if ($("importCancel")) $("importCancel").onclick = closeImportModal;
    if ($("importConfirm")) $("importConfirm").onclick = confirmImportSelection;
    if ($("importLocalBtn")) $("importLocalBtn").onclick = () => $("file").click();
    if ($("importTabs")) {
      $("importTabs").addEventListener("click", (e) => {
        const btn = e.target.closest("[data-itab]");
        if (!btn) return;
        state.importTab = btn.dataset.itab;
        renderImportModal();
      });
    }
    const filters = document.querySelector(".import-filters");
    if (filters) {
      filters.addEventListener("click", (e) => {
        const pill = e.target.closest("[data-ifilter]");
        if (!pill) return;
        state.importFilter = pill.dataset.ifilter;
        renderImportModal();
      });
    }
    if ($("importSelectAll")) {
      $("importSelectAll").addEventListener("change", () => {
        const list = filteredImportItems();
        const on = $("importSelectAll").checked;
        if (on) list.forEach((it) => { state.importSelected[it.key] = it; });
        else list.forEach((it) => { delete state.importSelected[it.key]; });
        renderImportModal();
      });
    }
    if ($("importBody")) {
      $("importBody").addEventListener("click", (e) => {
        const card = e.target.closest("[data-ikey]");
        if (!card) return;
        const key = card.dataset.ikey;
        const list = filteredImportItems();
        const it = list.find((x) => x.key === key);
        if (!it) return;
        if (state.importSelected[key]) delete state.importSelected[key];
        else state.importSelected[key] = it;
        renderImportModal();
      });
    }
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && modal.classList.contains("show")) closeImportModal();
    });
  }
  bindImportModal();

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

  window.addEventListener("resize", () => { drawMinimap(); positionDock(); });

  if (!restore()) loadDemo();
  applyCam();
  syncZoomPresets();
  renderCards();
  drawWires();
  loadCatalog();
  loadOuts();
  selectNode(state.selected || "shot-1");
})();
