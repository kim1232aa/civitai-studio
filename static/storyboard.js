(function () {
  const $ = (id) => document.getElementById(id);
  const STORE = "nl-storyboard-v0821o2";
  const STORE_OLDS = ["nl-storyboard-v0821o", "nl-storyboard-v0821n5", "nl-storyboard-v0821n4", "nl-storyboard-v0821n3", "nl-storyboard-v0821n2", "nl-storyboard-v0821n", "nl-storyboard-v0821m2", "nl-storyboard-v0821m", "nl-storyboard-v0821l", "nl-storyboard-v0821k", "nl-storyboard-v0821j", "nl-storyboard-v0821i", "nl-storyboard-v0821h", "nl-storyboard-v0821g", "nl-storyboard-v0821f", "nl-storyboard-v0821e", "nl-storyboard-v0821d", "nl-storyboard-v0821c", "nl-storyboard-v0821b", "nl-storyboard-v0821", "nl-storyboard-v0820c", "nl-storyboard-v0820b", "nl-storyboard-v0820", "nl-storyboard-v0819b", "nl-storyboard-v0819", "nl-storyboard-v0818", "nl-storyboard-v0817c", "nl-storyboard-v0817b", "nl-storyboard-v0817", "nl-storyboard-v0816b", "nl-storyboard-v0816", "nl-storyboard-v0815c", "nl-storyboard-v0815b", "nl-storyboard-v0815", "nl-storyboard-v0814", "nl-storyboard-v0813", "nl-storyboard-v0812", "nl-storyboard-v0811", "nl-storyboard-v0810", "nl-storyboard-v0809", "nl-storyboard-v0808", "nl-storyboard-v0807", "nl-storyboard-v0806", "nl-storyboard-v0805", "nl-storyboard-v0804", "nl-storyboard-v0803", "nl-storyboard-v0802", "nl-storyboard-v0798", "nl-storyboard-v0797", "nl-storyboard-v0796", "nl-storyboard-v0793", "nl-storyboard-v0791", "nl-storyboard-v0790"];
  const CIVITAI_PREF_SERVICE = "image/comfy/krea2/turbo/createImage";
  // v0821o2: pin fal-ai/z-image/turbo/lora on fixture+generate — never flux-lora / 默认模型 drift
  // v0821o: fal image+LoRA hardgate — pack requires http path; mount z-image/turbo/lora fixture 3231694
  // v0821n5: single Composer scrollbar (port from ui/seko-css-align dock-scroll)
  // v0821n4: cache-bust storyboard.js query to stamp
  // v0821n3: import air — chip subtitle prefers air URN (was path||downloadUrl hiding it); applyImport keeps air
  // v0821n2: LoRA chips without air → red block (no silent omit loras[]); some-with-air still filter
  // v0821n: krea2 import hardgate — packLoras skip no-air; attach negativePrompt; empty #service red
  // v0821m: i2v poll ≥9min (40×2.5s=100s timed out while Fal still IN_PROGRESS; success ~7min)
  // v0821l: fireSend once-per-event; blocking gates before 已点生成 ack (empty↑ keeps red)
  // v0821k: fal i2v empty-prompt hard gate; sticky 已点生成 · …; surface job.error; no wipe bad
  // v0821j: renderDock must not wipe msg while busy; fireSend entry 已点生成; dockFoot+Ctrl/Cmd+Enter
  // v0821i: i2v writeback — shot.url video preview; promote/history keep mp4; pickUrl prefer /out saved
  // v0821h: send gate via aria-disabled (not disabled=true) so click always fires setMsg
  // v0821g: always 首帧已就绪; bind send click+pointerdown; larger hit/z-index; missing-frame bad
  // v0821f: send ↑ no-op — clear stale needFrame warn; never silent-return; disabled gray
  // v0821e: POST /api/upload-out → /out (no blob soft-fallback)
  // v0821d: new-shot / loadDemo prompt stays empty (no 【镜头 shell)
  // v0821c: fal i2v preview writeback + local /out → data URL
  // v0821b: real i2v endpoint (plain video-01 is t2v and drops first frame)
  const FAL_I2V_DEFAULT = "fal-ai/minimax/video-01/image-to-video";
  const FAL_T2I_DEFAULT = "fal-ai/flux/schnell";
  const FAL_LORA_PREF_SERVICE = "fal-ai/z-image/turbo/lora";
  const FAL_LORA_FIXTURE_VERSION = "3231694";
  const FAL_LORA_FIXTURE_PATH = "https://civitai.com/api/download/models/3231694";
  const COMFY_PARAM_IDS = ["width", "height", "steps", "cfg", "sampler", "scheduler", "seed"];
  const FAL_PARAM_IDS = ["duration", "aspect", "res"];
  const SNAP_PX = 36;
  const vp = $("viewport");
  const world = $("world");
  const wires = $("wires");
  const dock = $("dock");
  const ROBOT_DEMO_IDS = { "a-bot": 1, "a-home": 1, "a-work": 1, "a-vac": 1, "s-bed": 1, "s-bath": 1 };
  const ROBOT_DEMO_TITLES = { "家用机器人": 1, "大白-居家装": 1, "大白-职场装": 1, "扫地机器人": 1, "温馨现代卧室": 1, "现代感洗手间": 1 };

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
    catalogById: {},
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
    dockMode: "collapsed",
    lastComposerShot: null,
    loras: [],
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
      // orphan firstFrameId (edge gone / asset deleted): heal to linked[0] or clear
      shot.firstFrameId = linked[0] ? linked[0].id : "";
    }
    return linked[0] || null;
  }
  function sourceTitle(n) {
    if (!n) return "";
    if (n.kind === "shot") return (n.title || "分镜") + "成片";
    return n.title || "资产";
  }
  /** Raw outs / provider file ids — must never land in the prompt textarea. */
  function isRawFileTitle(t) {
    const s = String(t || "").trim();
    if (!s) return true;
    // provider / pipeline file-id prefixes (never dump into prompt)
    if (/^(nano[-_]?gpt|modelscope|fal[_-]|comfy|out[_-]|seedream|kling|runway|luma|minimax|ideogram|flux[_-]|wan[_-]|vidu)/i.test(s)) return true;
    // long hex / uuid fragments without CJK (e.g. nano-gpt_img_ef80f1b1f425_0)
    if (!/[\u4e00-\u9fff]/.test(s) && /[0-9a-f]{8,}/i.test(s) && /[_-]/.test(s)) return true;
    if (!/[\u4e00-\u9fff]/.test(s) && /^[a-z0-9]+(?:[_-][a-z0-9]+){2,}_?\d*$/i.test(s) && s.length >= 20) return true;
    return false;
  }
  /** Legacy display helper (human @title or @图片N). Not used to write prompt anymore. */
  function mentionDisplayTag(asset, shot) {
    const linked = connectedAssets(shot.id);
    let idx = linked.findIndex((a) => a.id === asset.id);
    if (idx < 0) idx = linked.length;
    const title = sourceTitle(asset);
    if (title && !isRawFileTitle(title)) return "@" + title;
    return "@图片" + (idx + 1);
  }
  /** Legacy @+sourceTitle only — cleanup old canvases. Never invent @图片N for strip or insert. */
  function tagsForAsset(asset, shot) {
    const tags = [];
    const title = sourceTitle(asset);
    if (title) {
      const legacy = "@" + title;
      if (tags.indexOf(legacy) < 0) tags.push(legacy);
    }
    return tags;
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
      return d || "5s";
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

  function isClassicRobotDemo(nodes) {
    if (!nodes || !nodes.length) return false;
    for (let i = 0; i < nodes.length; i++) {
      const n = nodes[i];
      if (ROBOT_DEMO_IDS[n.id] || ROBOT_DEMO_TITLES[n.title]) return true;
    }
    return false;
  }

  /** Seko-aligned empty canvas: one blank shot, no cast assets. */
  function loadDemo() {
    state.nodes = [{
      id: "shot-1",
      kind: "shot",
      title: "分镜1",
      x: 560,
      y: 80,
      url: "",
      firstFrameId: "",
      prompt: "",
    }];
    state.edges = [];
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
        width: $("width") && $("width").value,
        height: $("height") && $("height").value,
        steps: $("steps") && $("steps").value,
        cfg: $("cfg") && $("cfg").value,
        sampler: $("sampler") && $("sampler").value,
        scheduler: $("scheduler") && $("scheduler").value,
        seed: $("seed") && $("seed").value,
        loras: Array.isArray(state.loras) ? state.loras : [],
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
      if (p.width != null && $("width")) $("width").value = p.width;
      if (p.height != null && $("height")) $("height").value = p.height;
      if (p.steps != null && $("steps")) $("steps").value = p.steps;
      if (p.cfg != null && $("cfg")) $("cfg").value = p.cfg;
      if (p.cfgScale != null && $("cfg") && (p.cfg == null || p.cfg === "")) $("cfg").value = p.cfgScale;
      if (p.sampler && $("sampler")) ensureSelectOpt($("sampler"), p.sampler);
      if (p.scheduler && $("scheduler")) ensureSelectOpt($("scheduler"), p.scheduler);
      if (p.seed != null && $("seed")) {
        $("seed").value = p.seed;
        $("seed").title = String(p.seed);
      }
      state._pendingService = p.service || "";
      state.loras = Array.isArray(p.loras) ? p.loras.map(function (x) { return Object.assign({}, x); }) : (state.loras || []);
      if (isClassicRobotDemo(state.nodes)) {
        // Old robot fixtures / dead DEMO thumbs — discard and empty-boot instead.
        state.nodes = [];
        state.edges = [];
        state.groups = [];
        return false;
      }
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
            ? '<video src="' + esc(n.url) + '" muted playsinline preload="metadata"></video>'
            : '<img src="' + esc(n.url) + '" alt="">')
        : '<div class="face"><div style="font-size:28px;opacity:.55">+</div><div class="hint">点击查看或编辑提示词</div></div>';
      const dur = shotDurationLabel(n);
      const busy = n._busy ? " busy" : "";
      return '<div class="card shot' + sel + multi + busy + '" data-id="' + esc(n.id) + '" style="left:' + n.x + 'px;top:' + n.y + 'px">' +
        '<div class="label">▢ ' + esc(n.title) + (dur ? '<span class="dur">' + esc(dur) + '</span>' : '') + '</div>' +
        badge +
        '<div class="face">' + media + '</div>' +
        '<button class="port in" data-side="in" type="button" aria-label="输入"></button>' +
        '<button class="port out" data-side="out" type="button" aria-label="输出"></button></div>';
    }
    const thumb = n.url
      ? (isVideoUrl(n.url)
          ? '<video class="thumb" src="' + esc(n.url) + '" muted playsinline preload="metadata"></video>'
          : '<img class="thumb" src="' + esc(n.url) + '" alt="">')
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

  function setDockMode(mode) {
    if (mode !== "collapsed" && mode !== "expanded" && mode !== "closed") mode = "collapsed";
    state.dockMode = mode;
    renderDock();
    if (mode === "expanded") {
      // First paint of expanded dock: show modes+#prompt at top of dock-scroll.
      requestAnimationFrame(() => {
        const sc = $("dockScroll");
        if (sc) sc.scrollTop = 0;
      });
    }
  }

  function positionDock() {
    if (!dock) return;
    const stage = dock.parentElement;
    if (!stage) return;
    const sr = stage.getBoundingClientRect();
    // Leave minimap + zoom clear by real geometry (not z-index alone).
    // minimap: left 14 / w 160 → right ~174; zoom: left 188 / ~270 wide → right ~458.
    const gap = 12;
    let clearL = 14;
    const mm = $("minimap");
    const zoomEl = stage.querySelector(".zoom");
    if (mm) {
      const r = mm.getBoundingClientRect();
      if (r.width > 0) clearL = Math.max(clearL, r.right - sr.left + gap);
    }
    if (zoomEl) {
      const r = zoomEl.getBoundingClientRect();
      if (r.width > 0) clearL = Math.max(clearL, r.right - sr.left + gap);
    }
    // Fallback before layout: zoom right edge ~458 + gap
    if (clearL < 100) clearL = 470;
    const clearR = 24;
    let dockW = Math.min(720, Math.max(280, sr.width - clearL - clearR));
    let left = (sr.width - dockW) / 2;
    if (left < clearL) left = Math.min(clearL, Math.max(12, sr.width - dockW - clearR));
    if (left + dockW > sr.width - clearR) {
      dockW = Math.max(280, sr.width - clearR - left);
    }
    dock.style.width = dockW + "px";
    dock.style.left = left + "px";
    dock.style.top = "auto";
    dock.style.bottom = "14px";
    dock.style.transform = "none";
    dock.classList.remove("near");
    const visible = dock.classList.contains("show");
    const dh = visible ? (dock.offsetHeight || (state.dockMode === "expanded" ? 220 : 44)) : 0;
    const lift = Math.max(210, dh + 28) + "px";
    ["skillbox", "atbox", "picker"].forEach((id) => {
      const el = $(id);
      if (el) el.style.bottom = lift;
    });
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
          const thumb = a.url
            ? (isVideoUrl(a.url)
                ? '<video src="' + esc(a.url) + '" muted playsinline preload="metadata"></video>'
                : '<img src="' + esc(a.url) + '" alt="">')
            : "";
          return '<div class="rail-item' + on + '" data-rail="' + esc(a.id) + '">' +
            thumb +
            "<span>" + esc(a.title) + "</span>" +
            (canPin ? '<button class="pin" type="button" data-pin="' + esc(a.id) + '" title="接到此镜">＋</button>' : "") +
            "</div>";
        }).join("") +
        '<button class="rail-item add" type="button" data-act="upload">+ 上传</button>';
    } else {
      const list = state.history;
      body = '<div class="rail-h">生成历史 · 拖到画布</div>' +
        (list.length ? list.map((it, i) => {
          const thumb = it.url
            ? (isVideoUrl(it.url)
                ? '<video src="' + esc(it.url) + '" muted playsinline preload="metadata"></video>'
                : '<img src="' + esc(it.url) + '" alt="">')
            : "";
          return '<div class="rail-item" data-hist="' + i + '">' +
            thumb +
            "<span>" + esc(it.title) + "</span>" +
            (canPin ? '<button class="pin" type="button" data-hist-pin="' + i + '" title="接到此镜">＋</button>' : "") +
            "</div>";
        }).join("") : "<div class='rail-h'>还没有成片</div>");
    }
    rail.innerHTML = tabs + body;
  }


  function syncCanvasTip() {
    const tip = $("canvasTip");
    if (!tip) return;
    // Show onboarding when Composer is not expanded — canvas is the main stage.
    const hide = state.dockMode === "expanded" && dock && dock.classList.contains("show");
    tip.hidden = !!hide;
    tip.classList.toggle("show", !hide);
  }

  function syncComposerChip() {
    const chip = $("composerChip");
    if (!chip) return;
    const sel = nodeById(state.selected);
    const remembered = nodeById(state.lastComposerShot);
    const shot = (sel && sel.kind === "shot") ? sel : (remembered && remembered.kind === "shot" ? remembered : null);
    const show = state.dockMode === "closed" && !!shot;
    chip.classList.toggle("show", show);
    chip.hidden = !show;
    if (show) {
      chip.title = "重新打开 · " + (shot.title || "分镜");
    }
  }

  function renderDock() {
    const n = nodeById(state.selected);
    if (!n || n.kind !== "shot") {
      dock.classList.remove("show");
      dock.classList.remove("near");
      dock.classList.remove("collapsed");
      dock.classList.remove("expanded");
      hideSkillbox();
      hideAtbox();
      const picker = $("picker");
      if (picker) picker.classList.remove("show");
      syncComposerChip(); syncCanvasTip();
      renderRail();
      requestAnimationFrame(positionDock);
      return;
    }
    state.lastComposerShot = n.id;
    if (state.dockMode === "closed") {
      dock.classList.remove("show");
      dock.classList.remove("collapsed");
      dock.classList.remove("expanded");
      dock.classList.remove("near");
      hideSkillbox();
      hideAtbox();
      const picker = $("picker");
      if (picker) picker.classList.remove("show");
      syncComposerChip(); syncCanvasTip();
      renderRail();
      requestAnimationFrame(positionDock);
      return;
    }
    const expanded = state.dockMode === "expanded";
    dock.classList.add("show");
    dock.classList.toggle("collapsed", !expanded);
    dock.classList.toggle("expanded", expanded);
    dock.classList.remove("near");
    if ($("dockTitle")) {
      $("dockTitle").textContent = (n.title || "分镜") + (expanded ? " · Composer" : " · Composer（已折叠）");
    }
    $("prompt").value = n.prompt || "";
    applyComfyParamsToUi(n);
    syncParamSurface();
    ["text", "image", "video", "audio"].forEach((m) => {
      const el = $("mode" + (m === "image" ? "Img" : m === "video" ? "Vid" : m === "text" ? "Text" : "Aud"));
      if (el) el.classList.toggle("on", state.mode === m);
    });
    const list = assets();
    const linked = connectedAssets(n.id);
    const frame = frameAsset(n);
    const needFrame = state.mode === "video" && !frame;
    const stub = isStubMode();
    syncSendGate(needFrame, stub);
    if (stub) {
      setMsg((state.mode === "text" ? "文本生成" : "音频生成") + " · 本版未接", "warn");
    } else if (needFrame) {
      // v0821g: missing-frame is hard stop (red), not yellow warn
      setMsg("缺首帧 · 视频需要先连一张首帧图", "bad");
    } else if (state.mode === "video" && frame) {
      // v0821j: do NOT reset to 首帧已就绪 while generate/busy/group in-flight (wipes 校验连线/已点生成)
      // v0821k: also keep bad/warn (Fal job.error / 此模型需要提示词) — empty card must not be silent
      if (!fireSend._busy && !state.runningGroup) {
        const msgEl = $("msg");
        const cls = (msgEl && msgEl.className) || "";
        if (!/\bbad\b|\bwarn\b/.test(cls)) {
          setMsg("首帧已就绪 · 可生成");
        }
      }
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
        frameHtml = '<div class="frame-slot missing">缺首帧</div>';
      }
    }
    const promoteBtn = n.url
      ? '<button class="chip-btn" type="button" data-act="promote" title="收进资产库">入库</button>'
      : "";
    const refCap = maxRefCount(catalogItemForService());
    // v0821: always show capacity; show ALL linked chips (even over-cap) so user can unlink;
    // fill remaining slots with unlinked suggestions up to maxRefs.
    const remain = Math.max(0, refCap - linked.length);
    const refHint = linked.length > refCap
      ? '<span class="ref-cap-hint" title="参考图上限">参考 ' + linked.length + '/' + refCap + ' · 超出，请减少连线</span>'
      : '<span class="ref-cap-hint" title="参考图上限">参考 ' + linked.length + '/' + refCap +
          (remain ? (' · 还可 ' + remain) : '') + '</span>';
    const suggest = list.filter((a) => !linked.some((x) => x.id === a.id)).slice(0, remain);
    const chipNodes = linked.concat(suggest);
    $("refs").innerHTML = frameHtml +
      '<button class="chip-btn" type="button" data-act="upload">上传</button>' +
      '<button class="chip-btn" type="button" data-act="pick">选择</button>' +
      promoteBtn + refHint +
      chipNodes.map((a) => {
        const on = linked.some((x) => x.id === a.id) ? " on" : "";
        return '<button class="chip' + on + '" type="button" data-asset="' + esc(a.id) + '" title="' + esc(sourceTitle(a)) + '">' +
          (a.url ? '<img src="' + esc(a.url) + '" alt="">' : esc(sourceTitle(a).slice(0, 2))) + "</button>";
      }).join("");
    syncComposerChip(); syncCanvasTip();
    renderRail();
    requestAnimationFrame(() => {
      positionDock();
      // Expand path (selectNode / setDockMode): keep #prompt in first paint, not scrolled under foot.
      if (expanded) {
        const sc = $("dockScroll");
        if (sc) sc.scrollTop = 0;
      }
    });
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
    const n = nodeById(id);
    if (n && n.kind === "shot") {
      state.lastComposerShot = n.id;
      // v0819b-expand-prompt: boot/first paint stays collapsed (canvas = stage);
      // intentional shot click expands; {collapsed:true} keeps bottom bar; expand capsule still works.
      if (opts.keepClosed) {
        /* leave dockMode (closed/chip path) */
      } else if (opts.collapsed) {
        state.dockMode = "collapsed";
      } else if (opts.expand || !opts.keepClosed) {
        state.dockMode = "expanded";
      }
    }
    renderCards();
    drawWires();
    renderDock();
    syncLoraUi();
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

  // v0817c-no-at-in-prompt: atbox / insertMention / 画布引用 / link → edge + chip only.
  // Never write @图片N / @标题 / @sourceTitle into prompt. Images via edges → attachExtraImages → images[].
  function mention(asset, shot) {
    return;
  }
  // Optional legacy cleanup for old canvases that still have @ aliases in prompt.
  function unmention(asset, shot) {
    if (!shot || !asset) return;
    const tags = tagsForAsset(asset, shot);
    let text = shot.prompt || "";
    let changed = false;
    for (let i = 0; i < tags.length; i++) {
      const tag = tags[i];
      if (tag && text.indexOf(tag) >= 0) {
        text = text.split(tag).join("");
        changed = true;
      }
    }
    if (changed) {
      shot.prompt = text.replace(/[ \t]{2,}/g, " ").replace(/\n{3,}/g, "\n\n");
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
    // legacy @ cleanup while edge still present; new flows write no @ so this is a no-op
    unmention(asset, shot);
    state.edges = state.edges.filter((e) => !(e.from === asset.id && e.to === shot.id));
    if (shot && shot.firstFrameId === asset.id) shot.firstFrameId = "";
    if (had) invalidateStageProgress(shot);
  }
  function toggleAssetOnShot(asset, shot) {
    if (!asset || !shot || shot.kind !== "shot") return;
    if (state.edges.some((e) => e.from === asset.id && e.to === shot.id)) unlinkAssetFromShot(asset, shot);
    else linkAssetToShot(asset, shot);
  }

  function promoteResult(shot, url) {
    // v0821i: promote images AND videos into outs/assets (history/drag survive refresh)
    if (!shot || !url) return null;
    const aid = "out-" + shot.id;
    let asset = nodeById(aid) || assets().find((a) => a.url === url);
    if (!asset) {
      asset = {
        id: aid,
        kind: "character",
        title: (shot.title || "分镜") + (isVideoUrl(url) ? "视频" : "成片"),
        x: shot.x + 680,
        y: shot.y + 20,
        url: url,
        fromShot: shot.id,
        mediaKind: mediaKindOf(url),
      };
      state.nodes.push(asset);
    } else {
      asset.url = url;
      asset.title = (shot.title || "分镜") + (isVideoUrl(url) ? "视频" : "成片");
      asset.fromShot = shot.id;
      asset.mediaKind = mediaKindOf(url);
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
    // v0817c-no-at-in-prompt: link edge + chip only — never append @图片N / @标题 into prompt.
    linkAssetToShot(asset, shot);
    const ta = $("prompt");
    if (ta) {
      const v = ta.value || "";
      const caret = ta.selectionStart || v.length;
      const before = v.slice(0, caret);
      const at = before.lastIndexOf("@");
      // Clear partial @query typed to open atbox; do not replace with a tag.
      if (at >= 0 && !/[\s\n]/.test(before.slice(at + 1))) {
        const next = (v.slice(0, at) + v.slice(caret)).replace(/[ \t]{2,}/g, " ");
        shot.prompt = next;
        ta.value = next;
      }
    }
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
    // Must land under /out so Fal materialize can read it. Never soft-fall to blob:.
    try {
      const dataUrl = await readFileAsDataUrl(f);
      const r = await fetch("/api/upload-out", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ dataUrl: dataUrl, filename: f.name }),
      });
      let j = null;
      try { j = await r.json(); } catch (_) {}
      if (r.ok && j && j.url && String(j.url).indexOf("/out/") === 0) return j.url;
      setMsg((j && j.error) || ("上传失败 HTTP " + r.status), "bad");
      return "";
    } catch (e) {
      setMsg("上传失败：" + ((e && e.message) || e), "bad");
      return "";
    }
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
    // empty canvas: clear multi + start pan; collapse Composer only on true click (not drag)
    if (!e.shiftKey) {
      setMulti(state.selected ? [state.selected] : []);
      syncGroupRunBtn();
      renderCards();
    }
    state.pan = {
      x: e.clientX - state.cam.x,
      y: e.clientY - state.cam.y,
      sx: e.clientX,
      sy: e.clientY,
      collapse: state.dockMode === "expanded",
    };
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
    if (state.pan && state.pan.collapse) {
      const dx = e.clientX - state.pan.sx;
      const dy = e.clientY - state.pan.sy;
      // true click = pointerdown→up with movement ≤5px (not a pan/drag)
      if (Math.hypot(dx, dy) <= 5) {
        hideSkillbox();
        hideAtbox();
        const picker = $("picker");
        if (picker) picker.classList.remove("show");
        setDockMode("collapsed");
      }
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
    if (!url || String(url).indexOf("/out/") !== 0) {
      $("file").value = "";
      return;
    }
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
      // 画布引用：真实 edge + chips only（v0817: 不往 prompt 塞 @filename）
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
  if ($("dockExpand")) {
    $("dockExpand").onclick = (e) => {
      e.stopPropagation();
      setDockMode("expanded");
      requestAnimationFrame(() => { if ($("prompt")) $("prompt").focus(); });
    };
  }
  if ($("dockCollapse")) {
    $("dockCollapse").onclick = (e) => {
      e.stopPropagation();
      hideSkillbox();
      hideAtbox();
      setDockMode("collapsed");
    };
  }
  if ($("dockClose")) {
    $("dockClose").onclick = (e) => {
      e.stopPropagation();
      hideSkillbox();
      hideAtbox();
      const picker = $("picker");
      if (picker) picker.classList.remove("show");
      const cur = nodeById(state.selected);
      if (cur && cur.kind === "shot") state.lastComposerShot = cur.id;
      setDockMode("closed");
    };
  }
  if ($("composerChip")) {
    $("composerChip").onclick = (e) => {
      e.stopPropagation();
      const id = (nodeById(state.selected) && nodeById(state.selected).kind === "shot")
        ? state.selected
        : state.lastComposerShot;
      const shot = nodeById(id);
      if (!shot || shot.kind !== "shot") return;
      if (state.selected !== shot.id) selectNode(shot.id, { keepClosed: true });
      setDockMode("expanded");
    };
  }
  if ($("dockHd")) {
    $("dockHd").addEventListener("click", (e) => {
      if (e.target.closest("button")) return;
      if (state.dockMode === "collapsed") {
        setDockMode("expanded");
        requestAnimationFrame(() => { if ($("prompt")) $("prompt").focus(); });
      }
    });
  }
  if ($("btnSkill")) {
    $("btnSkill").onclick = () => {
      if (state.dockMode !== "expanded") setDockMode("expanded");
      const box = $("skillbox");
      if (box && box.classList.contains("show")) hideSkillbox();
      else showSkillbox("", { filter: false });
    };
  }
  if ($("btnAttach")) {
    $("btnAttach").onclick = () => {
      if (state.dockMode !== "expanded") setDockMode("expanded");
      openImportModal();
    };
  }
  if ($("btnCanvasRef")) {
    $("btnCanvasRef").onclick = () => {
      if (state.dockMode !== "expanded") setDockMode("expanded");
      openCanvasPicker(true);
    };
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
    // v0821: refresh service list for image vs i2v; drop silent t2i/flux when video.
    const be = ($("backend") && $("backend").value) || "fal";
    const sid = ($("service") && $("service").value) || "";
    if (typeof loadCatalog === "function") {
      loadCatalog().then(function () {
        if (mode === "video" && sid) {
          const it = state.catalogById && state.catalogById[sid];
          if (it && !catalogItemSupportsI2v(it)) {
            if ($("service")) $("service").value = "";
            if (be === "fal" && $("service")) {
              ensureSelectOpt($("service"), FAL_I2V_DEFAULT);
              $("service").value = FAL_I2V_DEFAULT;
            }
          }
        }
        renderCards();
        drawWires();
        renderDock();
        persist();
      });
      return;
    }
    renderCards();
    drawWires();
    renderDock();
    persist();
  }
  if ($("modeText")) $("modeText").onclick = () => setMode("text");
  if ($("modeImg")) $("modeImg").onclick = () => setMode("image");
  if ($("modeVid")) $("modeVid").onclick = () => setMode("video");
  if ($("modeAud")) $("modeAud").onclick = () => setMode("audio");
  ["backend", "service", "duration", "aspect", "res"].concat(COMFY_PARAM_IDS).forEach((id) => {
    if ($(id)) $(id).addEventListener("change", () => {
      if (COMFY_PARAM_IDS.indexOf(id) >= 0) writeComfyParamsToShot(nodeById(state.selected));
      persist();
      if (id === "duration" && state.mode === "video") {
        renderCards(); drawWires(); positionDock();
      }
      if (id === "backend" || id === "service") syncParamSurface();
    });
    if ($(id) && COMFY_PARAM_IDS.indexOf(id) >= 0) {
      $(id).addEventListener("input", () => {
        if (id === "seed" && $("seed")) $("seed").title = String($("seed").value || "");
        writeComfyParamsToShot(nodeById(state.selected));
        persist();
      });
    }
  });

  function setMsg(t, cls) {
    if (!$("msg")) return;
    $("msg").textContent = t;
    $("msg").className = "msg" + (cls ? " " + cls : "");
  }

  // v0821k: sticky click-ack — successors keep「已点生成」visible (never wipe bare)
  function setAckMsg(rest, cls) {
    const body = String(rest == null ? "" : rest).replace(/^已点生成(\s*·\s*)?/, "");
    setMsg(body ? ("已点生成 · " + body) : "已点生成", cls);
  }

  function formatErr(e) {
    if (e == null || e === "") return "未知错误";
    if (typeof e === "string") return e;
    if (e instanceof Error) return e.message || String(e);
    if (typeof e === "object") {
      if (e.error != null && e.error !== e) return formatErr(e.error);
      if (e.message != null) return String(e.message);
      if (e.detail != null) {
        if (typeof e.detail === "string") return e.detail;
        try { return JSON.stringify(e.detail); } catch (_) {}
      }
      try { return JSON.stringify(e); } catch (_) { return String(e); }
    }
    return String(e);
  }

  function readComposerPrompt() {
    const n = nodeById(state.selected);
    const ta = $("prompt");
    if (ta && n && n.kind === "shot" && state.selected === n.id) {
      n.prompt = ta.value;
      return String(ta.value || "").trim();
    }
    return String((n && n.prompt) || "").trim();
  }

  function catalogRequiresPrompt(it) {
    if (!it) return false;
    const caps = (it.capabilities && typeof it.capabilities === "object") ? it.capabilities : {};
    const req = [].concat(it.required || caps.required || []);
    const pf = String(it.promptField || caps.promptField || "prompt");
    return req.map(String).some(function (r) {
      return r === "prompt" || r === pf || r.indexOf("prompt") >= 0;
    });
  }

  // v0821k: hard client gate — fal video / minimax i2v / catalog-required prompt; no silent soft-fill
  function needsPromptBeforeGenerate() {
    const empty = !readComposerPrompt();
    if (!empty) return false;
    if (state.mode === "video" && currentBackend() === "fal") return true;
    const it = catalogItemForService();
    if (catalogRequiresPrompt(it)) return true;
    const sid = (($("service") && $("service").value) || "").toLowerCase();
    if (currentBackend() === "fal" && (sid.indexOf("image-to-video") >= 0 || sid.indexOf("minimax") >= 0)) return true;
    return false;
  }

  // --- v0817c-no-at-in-prompt (+ no @ from atbox; legacy unmention cleanup; v0816b LoRA) ---
  function currentBackend() {
    return ($("backend") && $("backend").value) || "fal";
  }
  function isModelscopeBe() {
    const b = currentBackend();
    return b === "modelscope-ai" || b === "modelscope-cn";
  }
  function isNanogptBe() {
    return currentBackend() === "nano-gpt";
  }
  function clampLoraScale(v, fallback) {
    const n = parseFloat(v);
    const x = Number.isFinite(n) ? n : (fallback == null ? 0.8 : fallback);
    return Math.max(0, Math.min(4, x));
  }
  function isHttpUrl(s) { return /^https?:\/\//i.test(String(s || "")); }
  function isHfRepo(s) { return /^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/.test(String(s || "").trim()); }
  function looksAir(s) {
    const t = String(s || "");
    return /^urn:air:/i.test(t) || /:lora:/i.test(t);
  }
  function loraDownloadUrl(v) {
    if (!v) return "";
    if (v.path && !looksAir(v.path)) return v.path;
    if (v.downloadUrl && !looksAir(v.downloadUrl)) return v.downloadUrl;
    if (v.url && !looksAir(v.url) && isHttpUrl(v.url)) return v.url;
    const files = v.files || [];
    for (let i = 0; i < files.length; i++) {
      const f = files[i];
      if (f && f.downloadUrl && !looksAir(f.downloadUrl)) return f.downloadUrl;
    }
    if (v.id && /^\d+$/.test(String(v.id))) return "https://civitai.com/api/download/models/" + v.id;
    if (v.versionId && /^\d+$/.test(String(v.versionId))) return "https://civitai.com/api/download/models/" + v.versionId;
    return "";
  }
  function loraVersionId(l) {
    if (!l) return "";
    if (l.versionId) return String(l.versionId);
    if (l.modelVersionId) return String(l.modelVersionId);
    const air = String(l.air || "");
    const m = air.match(/@(\d+)\s*$/) || air.match(/civitai:\d+@(\d+)/i);
    return m ? m[1] : "";
  }
  function loraHasDirectPath(l) {
    if (!l) return false;
    if (l.path && !looksAir(l.path)) return true;
    if (l.downloadUrl && !looksAir(l.downloadUrl)) return true;
    if (l.versionId && /^\d+$/.test(String(l.versionId))) return true;
    return false;
  }
  function loraDisplayName(v) {
    // Prefer human model name over raw AIR / version id crumbs (v0821).
    v = v || {};
    const cands = [];
    if (typeof v.model === "string" && v.model) cands.push(v.model);
    if (v.model && typeof v.model === "object" && v.model.name) cands.push(v.model.name);
    if (v.modelName) cands.push(v.modelName);
    if (v.name) cands.push(v.name);
    for (let i = 0; i < cands.length; i++) {
      const s = String(cands[i] || "").trim();
      if (!s) continue;
      if (looksAir(s)) continue;
      if (/^civitai:\d+/i.test(s)) continue;
      if (/^\d+@\d+$/.test(s)) continue;
      if (/:lora:/i.test(s)) continue;
      return s;
    }
    return "LoRA";
  }
  function normalizeLora(v) {
    v = v || {};
    const air = v.air || "";
    const path = (v.path && !looksAir(v.path) ? v.path : "") || loraDownloadUrl(v) || "";
    const name = loraDisplayName(v);
    const strength = clampLoraScale(v.strength != null ? v.strength : v.scale, 0.8);
    return {
      air: air,
      path: path,
      downloadUrl: v.downloadUrl || path,
      versionId: v.versionId || loraVersionId(v) || (v.id && /^\d+$/.test(String(v.id)) ? String(v.id) : ""),
      strength: strength,
      scale: strength,
      name: name,
      status: v.status || "",
    };
  }
  function showLoraBlock() {
    const be = currentBackend();
    if (Array.isArray(state.loras) && state.loras.length) return true;
    // Prefer show for fal / civitai / nano; modelscope+hf show with hint.
    if (be === "fal" || be === "civitai" || be === "nano-gpt") return true;
    if (isModelscopeBe() || be === "huggingface") return true;
    return false;
  }
  function syncLoraPlaceholders() {
    const be = currentBackend();
    const q = $("loraQ");
    const lbl = $("loraQLbl");
    const hint = $("loraHint");
    if (be === "fal" || isNanogptBe() || be === "huggingface") {
      if (q) q.placeholder = "URL、HF owner/name、名字或 version id";
      if (lbl) lbl.textContent = "LoRA · 搜索名字 / URL / HF / version id";
    } else if (isModelscopeBe()) {
      if (q) q.placeholder = "魔搭 owner/repo，例如 Qwen/Qwen-Image";
      if (lbl) lbl.textContent = "LoRA · 魔搭 Hub owner/repo";
    } else {
      if (q) q.placeholder = "名字 / version id / AIR";
      if (lbl) lbl.textContent = "LoRA · 搜索名字 / version id / AIR";
    }
    if (hint) {
      if (isModelscopeBe()) {
        hint.textContent = "魔搭需要 Hub owner/repo；Civitai 下载链不能用（不会做 remap）";
        hint.classList.add("show");
      } else if (be === "huggingface") {
        hint.textContent = "HF 路由会带上 loras[]；上游是否加载取决于映射端点";
        hint.classList.add("show");
      } else {
        hint.textContent = "";
        hint.classList.remove("show");
      }
    }
  }
  // v0821n3: prefer air URN in chip subtitle so civitai outbound id is visible (path hid it)
  function loraChipSubtitle(l) {
    l = l || {};
    const air = String(l.air || "").trim();
    if (air) return air;
    return l.path || l.downloadUrl || l.url || "";
  }
  function renderLoras() {
    const box = $("loras");
    if (!box) return;
    const be = currentBackend();
    const list = Array.isArray(state.loras) ? state.loras : [];
    box.innerHTML = list.map(function (l, i) {
      const sub = loraChipSubtitle(l);
      const tip = String(l.air || sub || "");
      const needUrl = (be === "fal" || isNanogptBe()) && !loraHasDirectPath(l);
      const st = needUrl ? (l.status || "无直链") : (l.status || "");
      const stCls = needUrl || st === "无直链" ? "lora-status bad" : "lora-status";
      return '<div class="lora' + (needUrl ? " need-url" : "") + '" data-lora-i="' + i + '"><div class="top">' +
        '<div class="lora-info"><div class="lora-name">' + esc(l.name || "LoRA") + '</div>' +
        '<div class="lora-air" title="' + esc(tip) + '">' + esc(sub) + '</div>' +
        (st ? '<div class="' + stCls + '">' + esc(st) + '</div>' : '') +
        '</div>' +
        '<input class="lora-str" type="number" step="0.05" min="0" max="2" value="' +
          clampLoraScale(l.strength != null ? l.strength : l.scale, 0.8) +
          '" data-lora-str="' + i + '" title="strength">' +
        '<button type="button" class="lora-del" data-lora-del="' + i + '">删</button>' +
        '</div></div>';
    }).join("");
  }
  function syncLoraUi() {
    const block = $("loraBlock");
    if (!block) return;
    const show = showLoraBlock();
    block.classList.toggle("hidden", !show);
    syncLoraPlaceholders();
    renderLoras();
  }
  function addLora(v) {
    const row = normalizeLora(v);
    if (!row.air && !row.path && !row.versionId) return;
    const be = currentBackend();
    if ((be === "fal" || isNanogptBe()) && !loraHasDirectPath(row)) row.status = "无直链";
    if (!Array.isArray(state.loras)) state.loras = [];
    state.loras.push(row);
    renderLoras();
    if ($("loraHits")) $("loraHits").innerHTML = "";
    persist();
    if ((be === "fal" || isNanogptBe()) && row.air && !row.path) resolveLorasForBackend();
  }
  async function resolveOneLora(i) {
    const l = state.loras[i];
    if (!l || l.path) return;
    const vid = loraVersionId(l);
    if (!vid) { l.status = "无直链"; return; }
    try {
      const r = await fetch("/api/model-version/" + encodeURIComponent(vid));
      const v = await r.json();
      const url = loraDownloadUrl(v);
      if (url) {
        l.path = url;
        l.downloadUrl = url;
        if (!l.name || l.name === "LoRA") l.name = v.model || v.name || l.name;
        l.status = "";
      } else {
        l.status = "无直链";
      }
    } catch (_) {
      l.status = "无直链";
    }
  }
  async function resolveLorasForBackend() {
    const be = currentBackend();
    if (be !== "fal" && !isNanogptBe()) { renderLoras(); return; }
    for (let i = 0; i < state.loras.length; i++) await resolveOneLora(i);
    renderLoras();
    persist();
  }
  function ensureSelectOpt(sel, value) {
    if (!sel || value == null || value === "") return;
    const v = String(value);
    let found = false;
    for (let i = 0; i < sel.options.length; i++) {
      if (sel.options[i].value === v) { found = true; break; }
    }
    if (!found) {
      const o = document.createElement("option");
      o.value = v; o.textContent = v;
      sel.appendChild(o);
    }
    sel.value = v;
  }
  function fillSelectOpts(sel, arr, cur) {
    if (!sel) return;
    const want = cur != null && cur !== "" ? String(cur) : (sel.value || "");
    sel.innerHTML = "";
    (arr || []).forEach(function (x) {
      const o = document.createElement("option");
      o.value = String(x); o.textContent = String(x);
      sel.appendChild(o);
    });
    if (want) ensureSelectOpt(sel, want);
  }
  function usesCivitaiComfyParams() {
    return currentBackend() === "civitai";
  }
  function syncParamSurface() {
    const civ = usesCivitaiComfyParams();
    const falBox = $("falParams");
    const comfyBox = $("comfyParams");
    if (falBox) falBox.classList.toggle("hidden", !!civ);
    if (comfyBox) comfyBox.classList.toggle("hidden", !civ);
  }
  function readComfyParamsFromUi() {
    const width = $("width") ? parseInt($("width").value, 10) : NaN;
    const height = $("height") ? parseInt($("height").value, 10) : NaN;
    const steps = $("steps") ? parseInt($("steps").value, 10) : NaN;
    const cfgRaw = $("cfg") ? String($("cfg").value).trim() : "";
    const cfg = cfgRaw === "" ? NaN : parseFloat(cfgRaw);
    const sampler = $("sampler") ? String($("sampler").value || "").trim() : "";
    const scheduler = $("scheduler") ? String($("scheduler").value || "").trim() : "";
    const seedRaw = $("seed") ? String($("seed").value || "").trim() : "";
    const out = {};
    if (Number.isFinite(width)) out.width = width;
    if (Number.isFinite(height)) out.height = height;
    if (Number.isFinite(steps)) out.steps = steps;
    if (Number.isFinite(cfg)) { out.cfgScale = cfg; out.cfg = cfg; }
    if (sampler) out.sampler = sampler;
    if (scheduler) out.scheduler = scheduler;
    if (seedRaw !== "" && seedRaw !== "random") {
      const seedNum = Number(seedRaw);
      out.seed = Number.isFinite(seedNum) ? seedNum : seedRaw;
    }
    return out;
  }
  function writeComfyParamsToShot(shot) {
    if (!shot || shot.kind !== "shot") return;
    const p = readComfyParamsFromUi();
    ["width", "height", "steps", "cfgScale", "cfg", "sampler", "scheduler", "seed"].forEach(function (k) {
      if (p[k] != null) shot[k] = p[k];
      else delete shot[k];
    });
    // keep cfg mirror on shot for STORE hang / fixture
    if (p.cfgScale != null && shot.cfg == null) shot.cfg = p.cfgScale;
  }
  function applyComfyParamsToUi(src) {
    if (!src) return;
    if (src.width != null && $("width")) $("width").value = src.width;
    if (src.height != null && $("height")) $("height").value = src.height;
    if (src.steps != null && $("steps")) $("steps").value = src.steps;
    const cfgVal = src.cfg != null ? src.cfg : src.cfgScale;
    if (cfgVal != null && $("cfg")) $("cfg").value = cfgVal;
    if (src.sampler && $("sampler")) ensureSelectOpt($("sampler"), src.sampler);
    if (src.scheduler && $("scheduler")) ensureSelectOpt($("scheduler"), src.scheduler);
    if (src.seed != null && $("seed")) {
      $("seed").value = src.seed;
      $("seed").title = String(src.seed);
    }
  }
  // Pack civitai comfy params onto generate payload — never silently drop.
  function packComfyParamsForPayload() {
    if (!usesCivitaiComfyParams()) return null;
    const p = readComfyParamsFromUi();
    if (!Object.keys(p).length) return null;
    return p;
  }
  async function loadComfyDefaults() {
    try {
      const r = await fetch("/api/defaults");
      const j = await r.json();
      const d = j.defaults || {};
      fillSelectOpts($("sampler"), j.samplers || [], ($("sampler") && $("sampler").value) || d.sampler || "er_sde");
      fillSelectOpts($("scheduler"), j.schedulers || [], ($("scheduler") && $("scheduler").value) || d.scheduler || "sgm_uniform");
      // Only fill empty UI slots so STORE/shot restore wins.
      if ($("width") && !$("width").value && d.width != null) $("width").value = d.width;
      if ($("height") && !$("height").value && d.height != null) $("height").value = d.height;
      if ($("steps") && !$("steps").value && d.steps != null) $("steps").value = d.steps;
      if ($("cfg") && !$("cfg").value && d.cfgScale != null) $("cfg").value = d.cfgScale;
      if (d.sampler && $("sampler") && !$("sampler").value) ensureSelectOpt($("sampler"), d.sampler);
      if (d.scheduler && $("scheduler") && !$("scheduler").value) ensureSelectOpt($("scheduler"), d.scheduler);
      // Catalog ordering hint only — never soft-fill into generate/buildGraph.
      state._civitaiDefaultService = (d.serviceId || CIVITAI_PREF_SERVICE);
    } catch (_) {
      fillSelectOpts($("sampler"), ["er_sde", "euler", "euler_ancestral", "dpmpp_2m", "dpmpp_sde", "ddim"], "er_sde");
      fillSelectOpts($("scheduler"), ["sgm_uniform", "simple", "normal", "karras", "exponential", "ddim_uniform", "beta"], "sgm_uniform");
      if ($("width") && !$("width").value) $("width").value = 960;
      if ($("height") && !$("height").value) $("height").value = 1440;
      if ($("steps") && !$("steps").value) $("steps").value = 8;
      if ($("cfg") && !$("cfg").value) $("cfg").value = 1;
      // Catalog ordering hint only — never soft-fill into generate/buildGraph.
      state._civitaiDefaultService = CIVITAI_PREF_SERVICE;
    }
    syncParamSurface();
  }

  // Pack like index.html base.loras (~2231) + slimPayload (~2302): path/url/versionId/air/scale.
  function packLorasForPayload() {
    const list = Array.isArray(state.loras) ? state.loras : [];
    if (!list.length) return null;
    const be = currentBackend();
    // v0821n: civitai lora_map skips no-air — path-only must not ship empty air entries
    const mapped = list.map(function (l) {
      let path = l.path || l.downloadUrl || l.url || "";
      const versionId = l.versionId || loraVersionId(l) || "";
      if ((!path || looksAir(path)) && versionId && /^\d+$/.test(String(versionId))) {
        path = "https://civitai.com/api/download/models/" + versionId;
      }
      const scale = clampLoraScale(l.scale != null ? l.scale : l.strength, 0.8);
      const strength = clampLoraScale(l.strength != null ? l.strength : l.scale, 0.8);
      return {
        air: l.air || "",
        path: path,
        url: path,
        downloadUrl: l.downloadUrl || path,
        versionId: versionId,
        scale: scale,
        strength: strength,
        name: l.name || "LoRA",
      };
    }).filter(function (row) {
      if (be === "civitai") return !!(row.air && String(row.air).trim());
      // v0821o: fal outbound needs http path (AIR-only chips would silent-drop in providers/fal.py)
      if (be === "fal") {
        const p = String(row.path || "").trim();
        return !!(p && isHttpUrl(p) && !looksAir(p));
      }
      return true;
    });
    return mapped.length ? mapped : null;
  }
  // v0821n2: UI chips present but pack empty (all lack air on civitai) → must not POST without loras[]
  // v0821o: same helper for fal — chips present but no http path → pack empty → red block
  function chipsLackAirForOutbound() {
    const list = Array.isArray(state.loras) ? state.loras : [];
    if (!list.length) return false;
    const packed = packLorasForPayload();
    return !packed || !packed.length;
  }
  function outboundLoraBlockMsg() {
    if (currentBackend() === "fal") return "LoRA 缺 http path，无法出站";
    return "LoRA 缺 air，无法出站";
  }
  async function searchLoras() {
    const qEl = $("loraQ");
    const hits = $("loraHits");
    if (!qEl || !hits) return;
    const q = qEl.value.trim();
    if (!q) return;
    const be = currentBackend();
    hits.textContent = "搜…";
    if ((be === "fal" || be === "huggingface" || isModelscopeBe() || isNanogptBe()) && (isHttpUrl(q) || isHfRepo(q))) {
      addLora({ path: q, name: q, strength: 0.8 });
      hits.textContent = "";
      return;
    }
    if (be === "civitai" && /^\d+$/.test(q)) {
      try {
        const r = await fetch("/api/model-version/" + encodeURIComponent(q));
        const v = await r.json();
        if (v && !v.error) addLora(v);
        else hits.textContent = "没找到这个 version";
      } catch (_) { hits.textContent = "没找到这个 version"; }
      return;
    }
    if (q.startsWith("urn:air:") || q.includes(":lora:")) {
      addLora({ air: q, name: q.split(":").pop(), strength: 0.8 });
      hits.textContent = "";
      return;
    }
    try {
      const r = await fetch("/api/search?type=LORA&q=" + encodeURIComponent(q) + "&backend=" + encodeURIComponent(be));
      const j = await r.json();
      const rows = j.items || [];
      if (!rows.length) { hits.textContent = (j.note || "没有结果"); return; }
      hits.innerHTML = rows.map(function (it) {
        const v = (it.versions || [])[0] || {};
        const path = it.path || "";
        const extra = v.baseModel || v.name || path || "";
        return '<div data-path="' + esc(path) + '" data-vid="' + esc(v.id || "") + '" data-name="' + esc(it.name || "") + '"><b>' +
          esc(it.name) + '</b>' + (extra ? (" · " + esc(extra)) : "") + "</div>";
      }).join("");
      Array.prototype.forEach.call(hits.children, function (el) {
        el.onclick = async function () {
          const path = el.getAttribute("data-path");
          const name = el.getAttribute("data-name") || "";
          const vid = el.getAttribute("data-vid");
          if (path && (isHttpUrl(path) || isHfRepo(path))) {
            addLora({ path: path, name: name || path, strength: 0.8 });
            return;
          }
          if (be === "civitai" && vid) {
            try {
              const rr = await fetch("/api/model-version/" + encodeURIComponent(vid));
              addLora(await rr.json());
            } catch (_) {}
            return;
          }
          if (vid && /^\d+$/.test(String(vid))) {
            addLora({
              path: "https://civitai.com/api/download/models/" + vid,
              versionId: String(vid),
              name: name || ("LoRA " + vid),
              strength: 0.8,
            });
            return;
          }
          if (path || name) addLora({ path: path || name, name: name || path, strength: 0.8 });
        };
      });
    } catch (_) {
      hits.textContent = "搜索失败";
    }
  }
  function bindLoraUi() {
    if ($("searchLora")) $("searchLora").onclick = function () { searchLoras(); };
    if ($("loraQ")) {
      $("loraQ").addEventListener("keydown", function (e) {
        if (e.key === "Enter") { e.preventDefault(); searchLoras(); }
      });
    }
    if ($("loras")) {
      $("loras").addEventListener("click", function (e) {
        const del = e.target.closest("[data-lora-del]");
        if (!del) return;
        const i = +del.getAttribute("data-lora-del");
        if (!Number.isFinite(i)) return;
        state.loras.splice(i, 1);
        renderLoras();
        persist();
      });
      $("loras").addEventListener("change", function (e) {
        const inp = e.target.closest("[data-lora-str]");
        if (!inp) return;
        const i = +inp.getAttribute("data-lora-str");
        if (!Number.isFinite(i) || !state.loras[i]) return;
        const s = clampLoraScale(inp.value, 0.8);
        state.loras[i].strength = s;
        state.loras[i].scale = s;
        persist();
      });
    }
  }

  function catalogItemForService() {
    const sid = $("service") && $("service").value;
    if (!sid) return null;
    if (state.catalogById && state.catalogById[sid]) return state.catalogById[sid];
    const list = state.catalog || [];
    for (let i = 0; i < list.length; i++) {
      const it = list[i];
      if ((it.id || it.name) === sid) return it;
    }
    return null;
  }

  // v0821b: prefer catalog supportsI2v / needsFirstFrame; never category=video alone.
  // Pure t2v (fal-ai/minimax/video-01, falCategory=text-to-video, empty imageFields) → false.
  function catalogItemSupportsI2v(it) {
    if (!it) return false;
    const id = String(it.id || it.name || "").toLowerCase();
    const cat = String(it.category || it.kind || "").toLowerCase();
    const fcat = String(it.falCategory || "").toLowerCase();
    const caps = (it.capabilities && typeof it.capabilities === "object") ? it.capabilities : {};
    const fields = catalogImageFields(it);
    const hasFirst = fields.some(function (f) {
      const n = String(f || "").toLowerCase();
      return SINGULAR_FIRST_FIELDS.indexOf(n) >= 0 || n === "image_urls" || n === "images" ||
             n === "start_image" || n === "first_frame";
    });
    // Exact/plain MiniMax t2v — never i2v (no /image-to-video suffix).
    if (id === "fal-ai/minimax/video-01" || /\/video-01$/.test(id)) return false;
    if (id.indexOf("text-to-video") >= 0 || id.indexOf("/t2v") >= 0) return false;
    if (fcat.indexOf("text-to-video") >= 0 && id.indexOf("image-to-video") < 0) return false;

    // 1) Prefer explicit catalog flags from Fal overlay (supportsI2v / needsFirstFrame).
    const flag = (it.supportsI2v !== undefined) ? it.supportsI2v
      : (caps.supportsI2v !== undefined) ? caps.supportsI2v
      : undefined;
    if (flag === true || it.needsFirstFrame === true) return true;
    if (flag === false) return false;

    // 2) Id path markers for real i2v endpoints.
    if (id.indexOf("image-to-video") >= 0 || id.indexOf("start-end") >= 0 ||
        id.indexOf("reference-to-video") >= 0 || id.indexOf("first-last") >= 0 ||
        id.indexOf("/i2v") >= 0) return true;

    // 3) Catalog imageFields declare first-frame / start_image / image_url for video.
    if (hasFirst && (cat === "video" || cat.indexOf("video") >= 0 || fcat.indexOf("video") >= 0 ||
        it.kind === "video" || id.indexOf("video") >= 0)) return true;

    // NEVER: category=video && !text-to-video substring — that let video-01 through.
    return false;
  }
  function catalogItemSupportsImage(it) {
    if (!it) return true;
    const id = String(it.id || it.name || "").toLowerCase();
    const cat = String(it.category || it.falCategory || it.kind || "").toLowerCase();
    if (cat === "video" || it.kind === "video") return false;
    if (id.indexOf("image-to-video") >= 0 || id.indexOf("text-to-video") >= 0) return false;
    return true;
  }
  function filterCatalogForMode(items) {
    const list = Array.isArray(items) ? items : [];
    if (state.mode === "video") return list.filter(catalogItemSupportsI2v);
    if (state.mode === "image" || state.mode === "text" || state.mode === "audio") {
      return list.filter(catalogItemSupportsImage);
    }
    return list;
  }

    // Provider defaults (capabilities): catalog may only tighten, never raise.
  // Civitai/Fal/HF=9; Nano=5+input_references; Modelscope=1+image_url.
  const PROVIDER_REF_CAPS = {
    civitai: { maxRefs: 9, refImagesField: "images" },
    fal: { maxRefs: 9, refImagesField: "image_urls" },
    huggingface: { maxRefs: 9, refImagesField: "image_urls" },
    "nano-gpt": { maxRefs: 5, refImagesField: "input_references" },
    "modelscope-ai": { maxRefs: 1, refImagesField: "image_url" },
    "modelscope-cn": { maxRefs: 1, refImagesField: "image_url" },
  };

  function providerRefDefaults() {
    const backend = ($("backend") && $("backend").value) || "fal";
    return PROVIDER_REF_CAPS[backend] || { maxRefs: 9, refImagesField: "images" };
  }

  // Multi-ref bag names vs singular FIRST slots (Fal image_url / start_image_url / …).
  const MULTI_REF_FIELDS = ["image_urls", "images", "input_references"];
  const SINGULAR_FIRST_FIELDS = ["image_url", "start_image_url", "first_frame_url", "image"];

  function catalogImageFields(it) {
    if (!it) return [];
    const caps = (it.capabilities && typeof it.capabilities === "object") ? it.capabilities : {};
    const raw = caps.imageFields || it.imageFields || [];
    return Array.isArray(raw) ? raw.map(String) : [];
  }

  // Resolve caps from catalog item.capabilities (or top-level), clamped to provider default.
  // Catalog may only tighten. If imageFields has NO multi bag and only singular FIRST,
  // force maxRefs=1 so Fal single-image endpoints cannot silently drop N-1 refs.
  function resolveRefCaps(it) {
    const prov = providerRefDefaults();
    const caps = (it && it.capabilities && typeof it.capabilities === "object") ? it.capabilities : {};
    const raw = caps.maxRefs || caps.maxImages || (it && (it.maxRefs || it.maxImages));
    let max = Number(raw);
    if (!(max > 0 && max < 99)) max = Number(prov.maxRefs) || 9;
    const ceil = Number(prov.maxRefs) || 9;
    if (max > ceil) max = ceil; // catalog may only tighten
    if (!(max > 0)) max = 1; // slice(0, caps.maxRefs||caps.maxImages||1)
    const fields = catalogImageFields(it);
    if (fields.length) {
      const hasMulti = fields.some((f) => MULTI_REF_FIELDS.indexOf(f) >= 0);
      const hasSingularFirst = fields.some((f) => SINGULAR_FIRST_FIELDS.indexOf(f) >= 0);
      // No multi bag + singular FIRST (or any non-multi schema) → maxRefs=1 (catalog tighten).
      if (!hasMulti && (hasSingularFirst || fields.length > 0)) max = Math.min(max, 1);
    }
    const field = (caps.refImagesField || (it && it.refImagesField) || prov.refImagesField || "images");
    return { maxRefs: max, refImagesField: String(field) };
  }

  function maxRefCount(it) {
    return resolveRefCaps(it).maxRefs;
  }

  // Deduped linked+primary URLs (same order as attachExtraImages) for over-cap hard gate.
  function countRefUrls(payload, shot) {
    if (!shot) return [];
    const linked = connectedAssets(shot.id);
    const primaryNode = frameAsset(shot);
    const primary = (payload && (payload.firstFrame || payload.sourceImage)) || (primaryNode && primaryNode.url) || "";
    const urls = [];
    if (primary) urls.push(primary);
    linked.forEach((a) => {
      if (a && a.url && urls.indexOf(a.url) < 0) urls.push(a.url);
    });
    return urls;
  }

  // After compile: pack [primary, ...other linked] onto studio-inbound images[]
  // ALWAYS (capped by maxRefs||maxImages). Keep ONE compile image wire
  // (firstFrame/sourceImage). Optionally mirror onto capabilities.refImagesField
  // for backends that only look there — never sole-write image_urls /
  // input_references / image_url as the only multi-ref bag.
  function attachExtraImages(payload, shot) {
    if (!payload || !shot) return payload;
    const linked = connectedAssets(shot.id);
    const primaryNode = frameAsset(shot);
    const primary = payload.firstFrame || payload.sourceImage || (primaryNode && primaryNode.url) || "";
    const urls = [];
    if (primary) urls.push(primary);
    linked.forEach((a) => {
      if (a && a.url && urls.indexOf(a.url) < 0) urls.push(a.url);
    });
    if (!urls.length) return payload;
    const resolved = resolveRefCaps(catalogItemForService());
    const cap = resolved.maxRefs;
    const field = resolved.refImagesField || "images";
    const sliced = urls.slice(0, cap);
    // Do NOT infer "always 1" from field name alone — honor cap.
    // Studio inbound: always images[] so collectors see multi-ref (N>0).
    payload.images = sliced;
    // Keep/ensure primary wires when present.
    if (primary) {
      if (!payload.firstFrame) payload.firstFrame = primary;
      if (!payload.sourceImage) payload.sourceImage = primary;
    }
    // Optional mirror onto provider-native field (not the sole bag).
    if (field && field !== "images") {
      if (field === "image_url") {
        // modelscope singular: BOTH images=[url] and image_url=url
        payload.image_url = sliced[0];
      } else {
        payload[field] = sliced;
      }
    }
    // v0821: also stamp provider-correct singular FIRST (Fal start_image_url / image_url / …)
    // so packed inbound keeps first-frame even when compile default was t2v-ish.
    if (primary || sliced[0]) {
      const firstUrl = primary || sliced[0];
      const imgFields = catalogImageFields(catalogItemForService());
      let stamped = false;
      imgFields.forEach(function (f) {
        if (SINGULAR_FIRST_FIELDS.indexOf(f) >= 0) {
          if (!payload[f]) payload[f] = firstUrl;
          stamped = true;
        }
      });
      // Fal i2v common aliases when catalog row lacks imageFields
      if (!stamped && state.mode === "video") {
        if (!payload.start_image_url && !payload.image_url && !payload.first_frame_url) {
          payload.start_image_url = firstUrl;
          payload.image_url = firstUrl;
        }
      }
    }
    return payload;
  }

  function setShotBusy(shot, on) {
    if (!shot) return;
    shot._busy = !!on;
    const card = world.querySelector('.card[data-id="' + shot.id + '"]');
    if (card) card.classList.toggle("busy", !!on);
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
    const aspect = ($("aspect") && $("aspect").value) || "16:9";
    const res = ($("res") && $("res").value === "1080P") ? (aspect === "9:16" ? "1080x1920" : "1920x1080") : (aspect === "9:16" ? "720x1280" : "1280x720");
    const be = ($("backend") && $("backend").value) || "fal";
    // v0820c-hard-service: civitai must not invent Krea2 when #service is empty.
    // Fal empty-service defaults stay for fal backends only.
    const pickedService = ($("service") && $("service").value) || "";
    let serviceId = pickedService;
    if (!serviceId && be !== "civitai") {
      // v0821: i2v must use image-to-video endpoint — plain video-01 drops the frame.
      // v0821o2: LoRAs present → pin turbo/lora (never empty→flux/schnell→flux-lora sibling)
      if (op !== "i2v" && falHasLoras()) serviceId = FAL_LORA_PREF_SERVICE;
      else serviceId = (op === "i2v" ? FAL_I2V_DEFAULT : FAL_T2I_DEFAULT);
    }
    if (be === "fal" && op !== "i2v") {
      serviceId = pinFalLoraServiceId(serviceId);
    }
    const genParams = {
      serviceId: serviceId,
    };
    if (be === "civitai") {
      // width/height/steps/cfgScale/sampler/scheduler — seed packed in runShotStep (wire-only compile rule)
      const comfy = readComfyParamsFromUi();
      ["width", "height", "steps", "cfgScale", "cfg", "sampler", "scheduler"].forEach(function (k) {
        if (comfy[k] != null) genParams[k] = comfy[k];
      });
    } else {
      genParams.resolution = res;
      genParams.duration = parseInt(($("duration") && $("duration").value) || "5", 10) || 5;
      genParams.aspectRatio = aspect;
    }
    nodes.push({
      id: shot.id, op: op,
      params: genParams,
    });
    const ref = (op === "i2v") ? frame : linked[0];
    if (ref) edges.push({ from: ref.id, fromPort: "image", to: shot.id, toPort: "image" });
    return { backend: $("backend").value, nodes: nodes, edges: edges };
  }

  function pushHistoryItem(url, title) {
    if (!url) return;
    const item = {
      url: url,
      title: title || (isVideoUrl(url) ? "视频成片" : "历史成片"),
      kind: mediaKindOf(url),
    };
    state.history = [item].concat((state.history || []).filter((h) => h && h.url !== url)).slice(0, 24);
  }
  function writebackResult(shot, url) {
    // v0821i: persist shot.url (caller), promote to assets, push 生成历史 — images + videos
    if (!shot || !url) return;
    promoteResult(shot, url);
    pushHistoryItem(url, (shot.title || "分镜") + (isVideoUrl(url) ? "视频" : "成片"));
    renderRail();
  }

    function pickUrl(data) {
    // v0821i/v0821c: prefer local saved[] /out/*.mp4 over ephemeral CDN result.video.url.
    if (!data) return "";
    const first = (arr) => {
      if (!arr || !arr[0]) return "";
      const x = arr[0];
      if (typeof x === "string") return x;
      return (x && (x.url || x.path)) || "";
    };
    // 1) materialized /out (or any saved/files) — survives refresh
    const savedHit = first(data.saved) || first(data.files);
    if (savedHit) return savedHit;
    if (data.result && typeof data.result === "object") {
      const rs = first(data.result.saved) || first(data.result.files);
      if (rs) return rs;
    }
    // 2) video / image bags (CDN ok as fallback)
    const fromList = first(data.urls) || first(data.videos) || first(data.images);
    if (fromList) return fromList;
    if (data.video) return data.video.url || (typeof data.video === "string" ? data.video : "");
    if (data.image) return data.image.url || (typeof data.image === "string" ? data.image : "");
    // v0821m: bare video_url / image_url (some fal/provider shapes)
    if (typeof data.video_url === "string" && data.video_url) return data.video_url;
    if (typeof data.image_url === "string" && data.image_url) return data.image_url;
    const res = data.result;
    if (res && typeof res === "object") {
      if (res.video) return res.video.url || (typeof res.video === "string" ? res.video : "");
      if (res.image) return res.image.url || (typeof res.image === "string" ? res.image : "");
      const nested = first(res.videos) || first(res.images);
      if (nested) return nested;
      if (typeof res.video_url === "string" && res.video_url) return res.video_url;
      if (typeof res.image_url === "string" && res.image_url) return res.image_url;
      if (typeof res.url === "string") return res.url;
    }
    if (typeof data.url === "string") return data.url;
    return "";
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
    const prefix = opts.progressPrefix ? (opts.progressPrefix + " · ") : "";
    if (!shot || shot.kind !== "shot") {
      // v0821f: never silent — asset/empty selection was a CLICK_NOOP with no msg
      setMsg(prefix + "请先选中分镜再生成", "bad");
      return { status: "blocked" };
    }
    if (state.groupRunAbort) {
      setMsg(prefix + "已中止", "warn");
      return { status: "aborted" };
    }
    if (isStubMode()) {
      setMsg(prefix + (state.mode === "text" ? "文本生成" : "音频生成") + " · 本版未接", "warn");
      return { status: "blocked" };
    }
    if (state.mode === "video" && !frameAsset(shot)) {
      setMsg(prefix + "视频需要先连一张首帧图，不能偷配方台", "bad");
      return { status: "blocked" };
    }
    // v0821b: do not silently run i2v on t2i flux / pure t2v that drops the frame.
    if (state.mode === "video") {
      const sidVid = ($("service") && $("service").value) || "";
      const itVid = catalogItemForService() || (sidVid ? { id: sidVid } : null);
      if (sidVid && !catalogItemSupportsI2v(itVid)) {
        setMsg(prefix + "当前服务不吃首帧（非 i2v），请改选视频/图生视频模型", "bad");
        return { status: "blocked" };
      }
    }
    // v0821k: before POST — fal i2v / catalog-required prompt; hard red, no soft-fill
    if (needsPromptBeforeGenerate()) {
      setMsg(prefix + "此模型需要提示词", "bad");
      return { status: "blocked" };
    }
    // v0820c-hard-service: empty civitai #service → hard error, abort (no Krea2 soft-fill).
    if (currentBackend() === "civitai") {
      const civSid = ($("service") && $("service").value) || "";
      if (!civSid) {
        setMsg(prefix + "请先选择 Civitai 服务（不会默认填入 Krea2）", "bad");
        return { status: "blocked" };
      }
    }
    // v0821n2: LoRA chips in UI but none ship with air → hard red, do not generate/POST
    if (chipsLackAirForOutbound()) {
      setMsg(prefix + outboundLoraBlockMsg(), "bad");
      return { status: "blocked" };
    }
    if (!opts.keepSend) markSendBusy(true);
    // v0821k/i: sticky ack — keep 已点生成 in successor (group uses progressPrefix)
    if (prefix) setMsg(prefix + "校验连线…");
    else setAckMsg("校验连线…");
    let compiled;
    try {
      const r = await fetch("/api/graph/compile", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify(buildGraph(shot)),
      });
      compiled = await r.json();
    } catch (e) {
      setMsg(prefix + String(e), "bad");
      if (!opts.keepSend) markSendBusy(false);
      return { status: "error" };
    }
    if (state.groupRunAbort) {
      if (!opts.keepSend) markSendBusy(false);
      return { status: "aborted" };
    }
    if (!compiled.ok) {
      setMsg(prefix + (compiled.error || "校验未通过"), "bad");
      if (!opts.keepSend) markSendBusy(false);
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
        if (!opts.keepSend) markSendBusy(false);
        return { status: "blocked", stageOp: stage && stage.op };
      }
      payload = fillStageRefs(stage.payload, shot.stageUrls);
      if (hasUnresolvedStageOut(payload)) {
        setMsg(prefix + "上游还没有成片地址，不能偷配方台图 · 禁止一次假跑通", "bad");
        if (!opts.keepSend) markSendBusy(false);
        return { status: "blocked", stageOp: stage.op };
      }
    } else {
      // single-step only — never stage-zero payload fallback
      payload = compiled.payload;
      if (!payload) {
        setMsg(prefix + "没有 payload", "bad");
        if (!opts.keepSend) markSendBusy(false);
        return { status: "blocked" };
      }
    }
    const stageOp = stage ? stage.op : "";
    // Hard gate: over-cap refs must block — never silent-drop N-1 on single-slot endpoints.
    const refUrls = countRefUrls(payload, shot);
    const refCap = maxRefCount(catalogItemForService());
    if (refUrls.length > refCap) {
      setMsg(prefix + "参考图 " + refUrls.length + "/" + refCap + " · 超过上限，请减少连线后再生成（不静默丢弃）", "bad");
      if (!opts.keepSend) markSendBusy(false);
      return { status: "blocked", stageOp: stageOp };
    }
    attachExtraImages(payload, shot);
    // v0816-sb-lora: attach selected LoRAs (index.html base.loras shape)
    // v0821n2: chips without air already gated above; some-with-air still ship filtered rows
    {
      const packedLoras = packLorasForPayload();
      const list = Array.isArray(state.loras) ? state.loras : [];
      if (list.length && (!packedLoras || !packedLoras.length)) {
        setMsg(prefix + outboundLoraBlockMsg(), "bad");
        if (!opts.keepSend) markSendBusy(false);
        return { status: "blocked", stageOp: stageOp };
      }
      if (packedLoras && packedLoras.length) {
        payload.loras = packedLoras;
        // v0821o2: outbound serviceId must stay turbo/lora — block flux-lora swap
        if (currentBackend() === "fal") {
          const pinned = pinFalLoraServiceId(payload.serviceId || ($("service") && $("service").value) || "");
          payload.serviceId = pinned;
          payload.endpoint = pinned;
          ensureFalLoraServiceSelected();
        }
      }
    }
    // v0820-civitai-comfy-params: merge steps/cfg/sampler/scheduler/seed/size — no silent drop
    {
      const packedComfy = packComfyParamsForPayload();
      if (packedComfy) {
        Object.keys(packedComfy).forEach(function (k) {
          if (packedComfy[k] != null && packedComfy[k] !== "") payload[k] = packedComfy[k];
        });
      }
      if (usesCivitaiComfyParams()) {
        // Explicit UI selection only — never CIVITAI_PREF / _civitaiDefaultService soft-fill.
        const sid = ($("service") && $("service").value) || "";
        if (!sid) {
          setMsg(prefix + "请先选择 Civitai 服务（不会默认填入 Krea2）", "bad");
          if (!opts.keepSend) markSendBusy(false);
          return { status: "blocked", stageOp: stageOp };
        }
        payload.serviceId = sid;
        // v0821n: Composer has no negative wire — attach import/shot negativePrompt (may be "")
        if (shot && shot.negativePrompt != null) payload.negativePrompt = shot.negativePrompt;
        else if (payload.negativePrompt == null) payload.negativePrompt = "";
        // seed: keep full numeric (no int32 clamp) — Civitai seeds can exceed 2^31-1
      }
    }
    if (prefix) setMsg(prefix + (stage ? (stage.op + "…") : "请求中…"));
    else setAckMsg(stage ? ("逐步跑 · " + stage.op + "…") : "正在请求云 API…");
    setShotBusy(shot, true);
    try {
      const r = await fetch("/api/generate", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      let j = await r.json();
      if (!r.ok || j.error) throw new Error(formatErr(j.error || j.message || j.detail || ("HTTP " + r.status)));
      const jobId = j.id || j.jobId || j.workflowId;
      if (jobId && !pickUrl(j)) {
        // v0821m: MiniMax i2v success ~7min; old 40×2.5s=100s → false「没有可预览地址」while Fal IN_PROGRESS.
        const pollMax = (state.mode === "video" || (payload && payload.kind === "video") || (stageOp === "i2v")) ? 180 : 40;
        const pollMs = (state.mode === "video" || (payload && payload.kind === "video") || (stageOp === "i2v")) ? 3000 : 2500;
        for (let i = 0; i < pollMax; i++) {
          if (state.groupRunAbort) {
            setShotBusy(shot, false);
            if (!opts.keepSend) markSendBusy(false);
            return { status: "aborted", stageOp: stageOp };
          }
          await new Promise((res) => setTimeout(res, pollMs));
          const st = await (await fetch("/api/jobs/" + encodeURIComponent(jobId))).json();
          if (st.error || st.status === "failed") {
            const detail = formatErr(st.error || (st.wait && st.wait.log) || st.message || "任务失败");
            throw new Error(detail);
          }
          // v0821i: never break on succeeded alone — wait for saved[]/video.url (pickUrl) or keep polling.
          j = st;
          if (pickUrl(st)) break;
          const doneish = st.status === "done" || st.status === "succeeded" || st.status === "completed";
          const tick = (i + 1) + "/" + pollMax;
          if (prefix) setMsg(prefix + (doneish ? "成片落盘中 " : "云端进行中 ") + tick);
          else setAckMsg((doneish ? "成片落盘中 " : "云端进行中 ") + tick);
        }
      }
      if (state.groupRunAbort) {
        setShotBusy(shot, false);
        if (!opts.keepSend) markSendBusy(false);
        return { status: "aborted", stageOp: stageOp };
      }
      const url = pickUrl(j);
      if (url && stage) {
        shot.stageUrls[String(stage.id)] = url;
        const nxt = nextRunnableStage(compiled, shot.stageUrls);
        if (nxt) {
          persist();
          setShotBusy(shot, false);
          setMsg(prefix + "完成 " + stage.op + " · 多步链：按 stages 逐步跑，不假装一次出片（禁止一次假跑通）", "warn");
          if (!opts.keepSend) markSendBusy(false);
          renderDock();
          return { status: "more", stageOp: stage.op };
        }
        shot.url = url;
        writebackResult(shot, url);
        renderCards(); drawWires(); persist();
        setMsg(prefix + (isVideoUrl(url) ? "此镜视频完成，已写入卡片/历史" : "此镜完成，成片已收进资产库"), "ok");
      } else if (url) {
        shot.url = url;
        writebackResult(shot, url);
        renderCards(); drawWires(); persist();
        setMsg(prefix + (isVideoUrl(url) ? "此镜视频完成，已写入卡片/历史" : "此镜完成，成片已收进资产库"), "ok");
      } else {
        setShotBusy(shot, false);
        // v0821m: poll budget exhausted while Fal still IN_PROGRESS ≠ 「已返回无媒体」
        const stillGoing = !!(j && (
          j.status === "pending" || j.status === "processing" || j.status === "running" || !j.status
        ));
        if (stillGoing) {
          setMsg(prefix + "等待超时，云端任务仍在进行中（视频约需数分钟，可稍后用任务 id 再查）", "warn");
        } else {
          setMsg(prefix + "云端已返回，没有可预览地址", "warn");
        }
        if (!opts.keepSend) markSendBusy(false);
        renderDock();
        return { status: "blocked", stageOp: stageOp };
      }
    } catch (e) {
      setShotBusy(shot, false);
      // v0821k: surface Fal/job.error onto Composer (renderDock must not wipe bad)
      setMsg(prefix + formatErr(e), "bad");
      if (!opts.keepSend) markSendBusy(false);
      renderDock();
      return { status: "error", stageOp: stageOp };
    }
    setShotBusy(shot, false);
    if (!opts.keepSend) markSendBusy(false);
    renderDock();
    return { status: "done", stageOp: stageOp };
  }

  function setSendVisual(blocked, reason) {
    const btn = $("send");
    if (!btn) return;
    // v0821h P0: NEVER native disabled for gate — browser swallows clicks → no setMsg
    btn.disabled = false;
    const on = !!blocked;
    btn.setAttribute("aria-disabled", on ? "true" : "false");
    btn.classList.toggle("is-blocked", on);
    const why = reason || (on ? "blocked" : "enabled");
    btn.title = on ? ("不可生成 · " + why) : "生成 · enabled";
    btn.setAttribute("data-testid", "composer-send");
    btn.setAttribute("data-enabled", on ? "0" : "1");
    btn.setAttribute("data-reason", why);
  }

  function markSendBusy(on) {
    fireSend._busy = !!on;
    const btn = $("send");
    if (!btn) return;
    if (on) {
      setSendVisual(true, "busy");
      return;
    }
    if (state.runningGroup) {
      setSendVisual(true, "group-running");
      return;
    }
    const n = nodeById(state.selected);
    if (!n || n.kind !== "shot") {
      setSendVisual(true, "no-shot");
      return;
    }
    const needFrame = state.mode === "video" && !frameAsset(n);
    syncSendGate(needFrame, isStubMode());
  }

  function syncSendGate(needFrame, stub) {
    const btn = $("send");
    if (!btn) return;
    if (fireSend._busy) {
      setSendVisual(true, "busy");
      return;
    }
    if (state.runningGroup) {
      setSendVisual(true, "group-running");
      return;
    }
    const blocked = !!(needFrame || stub);
    let reason = "enabled";
    if (stub) reason = "stub-mode";
    else if (needFrame) reason = "need-frame";
    setSendVisual(blocked, reason);
  }

  function fireSend(e) {
    const btn = $("send");
    if (!btn) return;
    if (e && e.type === "pointerdown" && e.button != null && e.button !== 0) return;
    // v0821l: same DOM event handled once (#send + #dockFoot both wired)
    if (e) {
      if (e._nlSendHandled) return;
      e._nlSendHandled = true;
    }
    // in-flight / group: clicks still fire → show 进行中… (not silent)
    if (fireSend._busy || state.runningGroup || btn.getAttribute("data-reason") === "busy") {
      if (e) { try { e.preventDefault(); e.stopPropagation(); } catch (_) {} }
      setAckMsg("进行中…", "warn");
      return;
    }
    const now = Date.now();
    // v0821j/l: debounce must NOT wipe a prior gate msg — only bump 进行中 if busy raced in
    if (fireSend._at && (now - fireSend._at) < 450) {
      if (e) { try { e.preventDefault(); e.stopPropagation(); } catch (_) {} }
      if (fireSend._busy || state.runningGroup) setAckMsg("进行中…", "warn");
      return;
    }
    fireSend._at = now;
    if (e) {
      try { e.preventDefault(); e.stopPropagation(); } catch (_) {}
    }
    // v0821l: blocking gates BEFORE 已点生成 — empty↑ must stay on red, not get re-acked
    const n = nodeById(state.selected);
    if (!n || n.kind !== "shot") {
      setMsg("请先选中分镜再生成", "bad");
      return;
    }
    if (isStubMode()) {
      setMsg((state.mode === "text" ? "文本生成" : "音频生成") + " · 本版未接", "bad");
      return;
    }
    if (state.mode === "video" && !frameAsset(n)) {
      setMsg("缺首帧 · 视频需要先连一张首帧图", "bad");
      return;
    }
    // v0821k: prefer client gate in fireSend (video+fal / catalog-required) — abort before generate
    if (needsPromptBeforeGenerate()) {
      setMsg("此模型需要提示词", "bad");
      return;
    }
    // v0821n2: LoRA chips without air → red before 已点生成 / generate
    if (chipsLackAirForOutbound()) {
      setMsg(outboundLoraBlockMsg(), "bad");
      return;
    }
    // v0821l: only ack when proceeding to generate()
    setMsg("已点生成");
    generate();
  }

  function bindSendButton() {
    const btn = $("send");
    if (!btn || btn.dataset.nlSendBound === "1") return;
    btn.dataset.nlSendBound = "1";
    btn.type = "button";
    btn.disabled = false;
    btn.setAttribute("data-testid", "composer-send");
    btn.onclick = null;
    // capture click + pointerdown fallback (index #go lesson: elevate hit; avoid silent noop)
    btn.addEventListener("click", fireSend, true);
    btn.addEventListener("pointerdown", fireSend);
    // v0821j: event delegation on #dockFoot for [data-testid=composer-send] (undeniable hit)
    const foot = $("dockFoot");
    if (foot && foot.dataset.nlSendDelegate !== "1") {
      foot.dataset.nlSendDelegate = "1";
      const onFoot = function (ev) {
        const t = ev.target && ev.target.closest && ev.target.closest("[data-testid=\"composer-send\"]");
        if (!t) return;
        // v0821l: skip if #send already marked this event
        if (ev._nlSendHandled) return;
        fireSend(ev);
      };
      foot.addEventListener("click", onFoot, true);
      foot.addEventListener("pointerdown", onFoot, true);
    }
  }

  function bindComposerSendKeys() {
    if (bindComposerSendKeys._done) return;
    bindComposerSendKeys._done = true;
    // v0821j: Ctrl/Cmd+Enter in Composer → generate (undeniable when click miss-hits)
    document.addEventListener("keydown", function (e) {
      if (e.key !== "Enter" || !(e.metaKey || e.ctrlKey)) return;
      const dockEl = $("dock");
      if (!dockEl || !dockEl.classList.contains("show")) return;
      const ae = document.activeElement;
      const inComposer = !!(ae && dockEl.contains(ae));
      if (!inComposer) return;
      try { e.preventDefault(); e.stopPropagation(); } catch (_) {}
      fireSend(e);
    }, true);
  }

  async function generate() {
    // v0821k: sticky 已点生成 · 校验连线… (never wipe click ack without successor)
    if (needsPromptBeforeGenerate()) {
      setMsg("此模型需要提示词", "bad");
      return;
    }
    setAckMsg("校验连线…");
    markSendBusy(true);
    try {
      await runShotStep(state.selected, {});
    } finally {
      markSendBusy(false);
    }
  }
  bindSendButton();
  bindComposerSendKeys();

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
    markSendBusy(true);
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
    markSendBusy(false);
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
  if ($("selAuto")) $("selAuto").onclick = () => { autoLayout({ fromSelBar: true }); };
  syncSelBar();

  $("btnAdd").onclick = () => {
    const n = shots().length;
    const id = uid("shot");
    state.nodes.push({
      id: id, kind: "shot", title: "分镜" + (n + 1),
      x: 560 + (n % 2) * 720, y: 80 + Math.floor(n / 2) * 430,
      url: "", firstFrameId: "",
      prompt: "",
    });
    selectNode(id); persist();
  };
  function resolveLayoutScope(fromSelBar) {
    pruneGroups();
    const multiIds = (state.multi || []).filter((id) => !!nodeById(id));
    // P0: multi≥2 (shots and/or assets) → exact selection. Never expand to covering group.
    if (multiIds.length >= 2) return multiIds.slice();
    // Exact group match on multi shots (length may be 0–1 here already handled above for ≥2)
    const multiShotIds = multiIds.map(nodeById).filter((n) => n && n.kind === "shot").map((n) => n.id);
    if (multiShotIds.length) {
      const exact = (state.groups || []).find((g) => {
        const m = g.memberIds || [];
        if (m.length !== multiShotIds.length) return false;
        return multiShotIds.every((id) => m.indexOf(id) >= 0);
      });
      if (exact) return (exact.memberIds || []).slice();
      // P1: do NOT cover-expand a multi subset to a larger group
    }
    // Group chrome / single select inside a group (selBar shows via !!g)
    if (state.selected) {
      const g = groupOf(state.selected);
      if (g && multiIds.length <= 1) return (g.memberIds || []).slice();
    }
    // selBar must never wash the full canvas
    if (fromSelBar) {
      if (multiIds.length) return multiIds.slice();
      if (state.selected) return [state.selected];
    }
    return null;
  }
  function autoLayout(opts) {
    opts = opts || {};
    const fromSelBar = !!opts.fromSelBar;
    const scopeIds = resolveLayoutScope(fromSelBar);
    if (fromSelBar && !scopeIds) {
      setMsg("先多选卡片或选中组再布局", "warn");
      return;
    }
    let shotList = shots().filter((n) => !scopeIds || scopeIds.indexOf(n.id) >= 0);
    // Scoped (selBar / group): ONLY nodes in scopeIds move. Never yank exclusive
    // linked assets that sit outside the selection — UI contract: unselected stay put.
    // Full-canvas (#btnAuto, scopeIds=null): all assets still follow shots as before.
    const assetList = scopeIds
      ? assets().filter((n) => scopeIds.indexOf(n.id) >= 0)
      : assets().slice();
    if (scopeIds && scopeIds.length) {
      const order = {};
      scopeIds.forEach((id, i) => { order[id] = i; });
      shotList = shotList.slice().sort((a, b) => {
        const oa = order[a.id];
        const ob = order[b.id];
        if (oa == null && ob == null) return (a.x - b.x) || (a.y - b.y);
        if (oa == null) return 1;
        if (ob == null) return -1;
        return oa - ob;
      });
    } else {
      shotList = shotList.slice().sort((a, b) => (a.x - b.x) || (a.y - b.y));
    }
    // P1: group / selection with 0 shots — warn or layout scoped assets
    if (!shotList.length) {
      if (scopeIds) {
        const onlyAssets = assetList.slice().sort((a, b) => {
          const oa = scopeIds.indexOf(a.id);
          const ob = scopeIds.indexOf(b.id);
          if (oa < 0 && ob < 0) return (a.x - b.x) || (a.y - b.y);
          if (oa < 0) return 1;
          if (ob < 0) return -1;
          return oa - ob;
        });
        if (!onlyAssets.length) {
          setMsg("选区没有可布局的分镜或资产", "warn");
          return;
        }
        const ax = Math.min.apply(null, onlyAssets.map((a) => a.x));
        const ay = Math.min.apply(null, onlyAssets.map((a) => a.y));
        onlyAssets.forEach((a, i) => {
          a.x = ax;
          a.y = ay + i * 236;
        });
        setMsg("选区无分镜 · 已排布 " + onlyAssets.length + " 个资产", "warn");
        renderCards(); drawWires(); persist();
        syncSelBar();
        return;
      }
      // full canvas, no shots — nothing to do
      setMsg("画布上没有分镜可布局", "warn");
      return;
    }
    const startX = scopeIds
      ? Math.min.apply(null, shotList.map((s) => s.x))
      : 560;
    const startY = scopeIds
      ? Math.min.apply(null, shotList.map((s) => s.y))
      : 80;
    const gapX = 720;
    const gapY = 430;
    const EPS = 12;
    function planRow() {
      return shotList.map((_, i) => ({ x: startX + i * gapX, y: startY }));
    }
    function planCol() {
      return shotList.map((_, i) => ({ x: startX, y: startY + i * gapY }));
    }
    function planGrid2() {
      return shotList.map((_, i) => ({
        x: startX + (i % 2) * gapX,
        y: startY + Math.floor(i / 2) * gapY,
      }));
    }
    function nearlySame(plan) {
      if (!shotList.length) return true;
      return shotList.every((n, i) => {
        const t = plan[i];
        return Math.abs(n.x - t.x) < EPS && Math.abs(n.y - t.y) < EPS;
      });
    }
    // Prefer row; if already there, try column; then 2-col grid; finally nudge Y so chrome moves
    let plan = planRow();
    if (nearlySame(plan)) plan = planCol();
    if (nearlySame(plan)) plan = planGrid2();
    if (nearlySame(plan)) {
      plan = planRow().map((t) => ({ x: t.x, y: t.y + gapY }));
    }
    shotList.forEach((n, i) => {
      n.x = plan[i].x;
      n.y = plan[i].y;
    });
    const placed = {};
    const assetAllowed = {};
    assetList.forEach((a) => { assetAllowed[a.id] = true; });
    shotList.forEach((shot) => {
      const linked = connectedNodes(shot.id);
      linked.forEach((a, j) => {
        if (!a || a.kind === "shot") return;
        // Scoped: only move assets whose id is in scopeIds (no exclusive-link expansion)
        if (scopeIds && !assetAllowed[a.id]) return;
        if (placed[a.id]) return;
        a.x = shot.x - 180;
        a.y = shot.y + j * 220;
        placed[a.id] = true;
      });
    });
    // Place scoped assets not yet placed (e.g. selected but unlinked)
    if (scopeIds) {
      let orphan = 0;
      const baseY = shotList.length
        ? Math.min.apply(null, shotList.map((s) => s.y))
        : 80;
      const baseX = shotList.length
        ? Math.min.apply(null, shotList.map((s) => s.x)) - 180
        : 48;
      assetList.forEach((a) => {
        if (placed[a.id]) return;
        a.x = baseX;
        a.y = baseY + orphan * 236;
        orphan++;
        placed[a.id] = true;
      });
    } else {
      let orphan = 0;
      assets().forEach((a) => {
        if (placed[a.id]) return;
        a.x = 48;
        a.y = 24 + orphan * 236;
        orphan++;
        placed[a.id] = true;
      });
    }
    // Preserve multi-select + group chrome (state.multi / groups untouched)
    renderCards(); drawWires(); persist();
    syncSelBar();
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

  function looksCivitaiServiceId(id) {
    const s = String(id || "");
    return /^(image|video|audio|3d|utility)\//.test(s) || /\/comfy\//.test(s);
  }
  function looksFalServiceId(id) {
    const s = String(id || "").trim();
    return /^fal-ai\//i.test(s) || /^fal\.ai\//i.test(s);
  }

  // v0821o2: when LoRAs ship, keep z-image/turbo/lora — never empty→flux/schnell→sibling flux-lora
  function falHasLoras() {
    return Array.isArray(state.loras) && state.loras.length > 0;
  }
  function isFalFluxLoraDrift(sid) {
    const s = String(sid || "").trim();
    return s === "fal-ai/flux-lora" || s === "fal-ai/flux/schnell" || s === FAL_T2I_DEFAULT;
  }
  function pinFalLoraServiceId(sid) {
    const s = String(sid || "").trim();
    if (!falHasLoras()) return s;
    // Explicit turbo → turbo/lora sibling only; never fuzzy to flux-lora
    if (s === "fal-ai/z-image/turbo") return FAL_LORA_PREF_SERVICE;
    if (s === FAL_LORA_PREF_SERVICE) return s;
    if (!s || isFalFluxLoraDrift(s)) return FAL_LORA_PREF_SERVICE;
    return s;
  }
  function ensureFalLoraServiceSelected() {
    if (!falHasLoras()) return;
    const be = ($("backend") && $("backend").value) || "";
    if (be !== "fal") return;
    const sel = $("service");
    if (!sel) return;
    const want = pinFalLoraServiceId(sel.value);
    // Visible label: never leave 「默认模型」 when LoRAs mounted
    ensureSelectOpt(sel, want);
    // Prefer a clear option label for the pinned id
    for (let i = 0; i < sel.options.length; i++) {
      if (sel.options[i].value === want) {
        const t = sel.options[i].textContent || "";
        if (!t || t === want || t === "默认模型") {
          sel.options[i].textContent = "Z-Image Turbo LoRA · " + want;
        }
        break;
      }
    }
    sel.value = want;
    if (!state.catalogById) state.catalogById = {};
    if (!state.catalogById[want]) {
      state.catalogById[want] = { id: want, name: "Z-Image Turbo LoRA", category: "image", tags: ["lora"] };
    }
  }

  function falLoraFixtureImport() {
    // Hard-pin — never omit / never fal-ai/flux-lora
    return {
      backend: "fal",
      serviceId: "fal-ai/z-image/turbo/lora",
      serviceName: "Z-Image Turbo LoRA",
      kind: "image",
      prompt: "portrait, soft light, detailed face, cinematic",
      loras: [{
        versionId: Number(FAL_LORA_FIXTURE_VERSION),
        path: FAL_LORA_FIXTURE_PATH,
        downloadUrl: FAL_LORA_FIXTURE_PATH,
        url: FAL_LORA_FIXTURE_PATH,
        scale: 0.8,
        strength: 0.8,
        name: "Asian Mix fixture " + FAL_LORA_FIXTURE_VERSION,
      }],
    };
  }
  async function mountFalLoraFixture() {
    closeImportModal();
    await applyImport(falLoraFixtureImport());
    // Survive subsequent loadCatalog races — re-pin visible #service
    ensureFalLoraServiceSelected();
    state._pendingService = FAL_LORA_PREF_SERVICE;
    state._pinFalLoraService = FAL_LORA_PREF_SERVICE;
  }
  function ensureActiveShotForImport() {
    let shot = nodeById(state.selected);
    if (shot && shot.kind === "shot") return shot;
    const list = shots();
    if (list.length) {
      selectNode(list[0].id, { expand: true });
      return nodeById(list[0].id);
    }
    const id = uid("shot");
    const n = {
      id: id, kind: "shot", title: "分镜1",
      x: 560, y: 80, url: "", firstFrameId: "",
      prompt: "",
    };
    state.nodes.push(n);
    selectNode(id, { expand: true });
    return n;
  }
  // v0820b-apply-import: port index.html applyImport onto storyboard Composer.
  // Never silent-fall back to fal/flux/schnell after a civitai import.
  async function applyImport(j) {
    j = j || {};
    const civitaiSid = looksCivitaiServiceId(j.serviceId);
    const falSid = looksFalServiceId(j.serviceId);
    // Explicit backend wins; never treat fal-ai/… as civitai image/… drift
    const wantCivitai = (j.backend === "civitai") || (civitaiSid && j.backend !== "fal");
    const wantFal = (j.backend === "fal") || (falSid && j.backend !== "civitai" && !wantCivitai);
    const shot = ensureActiveShotForImport();
    let hardErr = "";

    if (wantCivitai) {
      if ($("backend")) $("backend").value = "civitai";
      syncParamSurface();
      const sid = String(j.serviceId || "").trim();
      state._pendingService = sid || "";
      await loadCatalog();
      if (!sid) {
        if ($("service")) $("service").value = "";
        hardErr = "Civitai 导入缺少 serviceId，无法挂载（不会回退 fal/flux/schnell）";
      } else {
        ensureSelectOpt($("service"), sid);
        if ($("service")) $("service").value = sid;
        if (!$("service") || $("service").value !== sid) {
          hardErr = "无法挂载服务 " + sid + "（不会回退 fal/flux/schnell）";
        }
        if (!state.catalogById) state.catalogById = {};
        if (!state.catalogById[sid]) {
          state.catalogById[sid] = { id: sid, name: j.serviceName || sid };
        }
      }
    } else if (wantFal) {
      if ($("backend")) $("backend").value = "fal";
      syncParamSurface();
      let sid = String(j.serviceId || "").trim() || FAL_LORA_PREF_SERVICE;
      // Pin fal-ai/z-image/turbo(/lora) — never drift to Civitai image/comfy/…
      if (looksCivitaiServiceId(sid)) {
        hardErr = "Fal 导入拒绝 Civitai serviceId " + sid;
      } else {
        // v0821o2: pin turbo/lora; reject flux-lora drift on fixture/import
        if (Array.isArray(j.loras) && j.loras.length && isFalFluxLoraDrift(sid)) {
          sid = FAL_LORA_PREF_SERVICE;
        }
        if (Array.isArray(j.loras) && j.loras.length && (sid === "fal-ai/z-image/turbo" || !sid)) {
          sid = FAL_LORA_PREF_SERVICE;
        }
        state._pendingService = sid;
        state._pinFalLoraService = (Array.isArray(j.loras) && j.loras.length) ? sid : (state._pinFalLoraService || "");
        await loadCatalog();
        ensureSelectOpt($("service"), sid);
        if ($("service")) {
          // Clear visible label for pinned turbo/lora
          for (let oi = 0; oi < $("service").options.length; oi++) {
            if ($("service").options[oi].value === sid) {
              $("service").options[oi].textContent = (j.serviceName || "Z-Image Turbo LoRA") + " · " + sid;
              break;
            }
          }
          $("service").value = sid;
        }
        if (!$("service") || $("service").value !== sid) {
          hardErr = "无法挂载 Fal 服务 " + sid;
        }
        if (!state.catalogById) state.catalogById = {};
        if (!state.catalogById[sid]) {
          state.catalogById[sid] = { id: sid, name: j.serviceName || sid };
        }
        ensureFalLoraServiceSelected();
      }
    }

    // Prompt only — never inject @filename from import media (v0817c)
    if (j.prompt != null) {
      const p = String(j.prompt);
      if ($("prompt")) $("prompt").value = p;
      if (shot) shot.prompt = p;
    }
    if (shot && j.negativePrompt != null) shot.negativePrompt = j.negativePrompt || "";

    applyComfyParamsToUi(j);
    if (shot) {
      ["width", "height", "steps", "sampler", "scheduler", "seed"].forEach(function (k) {
        if (j[k] != null) shot[k] = j[k];
        else delete shot[k];
      });
      const cfgVal = j.cfg != null ? j.cfg : j.cfgScale;
      if (cfgVal != null) { shot.cfg = cfgVal; shot.cfgScale = cfgVal; }
      else { delete shot.cfg; delete shot.cfgScale; }
    }

    if (Array.isArray(j.loras)) {
      // v0821n3-import-air: copy air/name/strength/versionId/path onto chips (normalizeLora + reaffirm air)
      state.loras = j.loras.map(function (row) {
        const n = normalizeLora(row || {});
        if (row && row.air) n.air = String(row.air).trim();
        if (row && row.versionId != null && String(row.versionId).trim() !== "") {
          n.versionId = String(row.versionId);
        }
        if (row && (row.path || row.downloadUrl) && !n.path) {
          n.path = row.path || row.downloadUrl || n.path;
          n.downloadUrl = row.downloadUrl || n.path;
        }
        return n;
      });
    } else if (wantCivitai) {
      state.loras = [];
    }
    syncLoraUi();

    if (j.kind === "video") state.mode = "video";
    else if (j.kind === "image") state.mode = "image";

    setDockMode("expanded");
    renderCards();
    drawWires();
    renderDock();
    persist();

    const nLora = Array.isArray(state.loras) ? state.loras.length : 0;
    if (hardErr) {
      setMsg(hardErr, "bad");
      return;
    }
    if (j.empty && j.error) {
      setMsg(j.error, "bad");
      return;
    }
    const extra = [];
    if (j.comfyNodeCount) extra.push(j.comfyNodeCount + " 节点 Comfy");
    if (j.importSource) extra.push(j.importSource);
    const extraTxt = extra.length ? " · " + extra.join(" · ") : "";
    setMsg("已导入参数" + (nLora ? (" · " + nLora + " 个 LoRA") : " · 未识别 LoRA") + extraTxt + "，自己点生成。", "ok");
  }
  async function runImportFromUrl(raw) {
    raw = String(raw || "").trim();
    if (!raw) { setMsg("请填 Civitai 图 id 或完整网址", "bad"); return; }
    const civ = raw.match(/\/images\/(\d+)/i)
      || raw.match(/[?&](?:imageId|id)=(\d+)/i)
      || (/^\d+$/.test(raw) ? [null, raw] : null);
    const body = civ
      ? { backend: "civitai", q: String(civ[1]) }
      : { backend: "civitai", q: raw };
    const btn = $("importUrlBtn");
    if (btn) { btn.disabled = true; btn.textContent = "导入中"; }
    try {
      const r = await fetch("/api/import", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      let j = null;
      try { j = await r.json(); } catch (_) { j = null; }
      if (!r.ok || !j || j.error) {
        setMsg("导入失败 " + ((j && j.error) || r.statusText || ("HTTP " + r.status)), "bad");
        return;
      }
      closeImportModal();
      await applyImport(j);
    } catch (e) {
      setMsg("导入失败 " + (e && e.message ? e.message : String(e)), "bad");
    } finally {
      if (btn) { btn.disabled = false; btn.textContent = "导入参数"; }
    }
  }

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
    if ($("importUrlBtn")) {
      $("importUrlBtn").onclick = () => {
        const v = ($("importUrl") && $("importUrl").value) || "";
        runImportFromUrl(v);
      };
    }
    if ($("btnFalLoraFix")) {
      $("btnFalLoraFix").onclick = function () { mountFalLoraFixture(); };
    }
    if ($("importUrl")) {
      $("importUrl").addEventListener("keydown", (e) => {
        if (e.key === "Enter") {
          e.preventDefault();
          runImportFromUrl(($("importUrl") && $("importUrl").value) || "");
        }
      });
    }
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
    // v0821o2: remember selection before wipe — boot loadCatalog must not blank fixture pin to 「默认模型」
    const prevService = ($("service") && $("service").value) || "";
    $("service").innerHTML = '<option value="">默认模型</option>';
    state.catalogById = state.catalogById || {};
    try {
      const be = $("backend").value;
      const r = await fetch("/api/catalog?backend=" + encodeURIComponent(be));
      const j = await r.json();
      let items = (j.items || j.models || []).slice();
      // v0821: mode-filter so video Composer lists i2v services (not silent t2i flux).
      items = filterCatalogForMode(items);
      // CIVITAI_PREF / _civitaiDefaultService = catalog ordering hint only (not generate fallback).
      const pref = (be === "civitai" && state.mode !== "video")
        ? (state._civitaiDefaultService || CIVITAI_PREF_SERVICE)
        : "";
      // Keep preferred service in the option list even when catalog is capped.
      const CAP = 60;
      if (pref) {
        const prefItem = items.find(function (it) { return (it.id || it.name) === pref; });
        let head = items.slice(0, CAP);
        if (prefItem && !head.some(function (it) { return (it.id || it.name) === pref; })) {
          head = [prefItem].concat(head.filter(function (it) { return (it.id || it.name) !== pref; })).slice(0, CAP);
        }
        items = head;
      } else {
        items = items.slice(0, CAP);
      }
      // Fal video empty-service: ensure i2v default is listed (never plain video-01 t2v).
      if (be === "fal" && state.mode === "video") {
        const hasI2v = items.some(function (it) { return (it.id || it.name) === FAL_I2V_DEFAULT; });
        if (!hasI2v) {
          items = [{ id: FAL_I2V_DEFAULT, name: "MiniMax Video-01 Image to Video", category: "video",
            needsFirstFrame: true, imageFields: ["image_url"] }].concat(items).slice(0, CAP);
        }
      }
      // v0821o2: when LoRAs / fixture pin — keep turbo/lora in the capped list (visible, not 默认模型)
      const pinWant = state._pendingService || state._pinFalLoraService || prevService || "";
      const needLoraPin = (be === "fal" && state.mode !== "video" && (
        falHasLoras() || pinWant === FAL_LORA_PREF_SERVICE || pinWant === "fal-ai/z-image/turbo"
      ));
      if (needLoraPin) {
        const pinId = FAL_LORA_PREF_SERVICE;
        let pinItem = items.find(function (it) { return (it.id || it.name) === pinId; });
        if (!pinItem) {
          pinItem = { id: pinId, name: "Z-Image Turbo LoRA", category: "image", tags: ["lora"] };
        } else {
          pinItem = Object.assign({}, pinItem, { name: pinItem.name || "Z-Image Turbo LoRA" });
        }
        items = [pinItem].concat(items.filter(function (it) { return (it.id || it.name) !== pinId; })).slice(0, CAP);
      }
      state.catalog = items;
      // Preserve catalog fields used by multi-ref packing (capabilities.maxRefs/maxImages/refImagesField, imageFields).
      const byId = {};
      items.forEach((it) => {
        const id = it.id || it.name || "";
        if (id) {
          byId[id] = it;
          // keep maxImages / maxRefs / imageFields on the catalog row when present
        }
        const o = document.createElement("option");
        o.value = id;
        // Clear label for pinned turbo/lora (not bare id-only / not 默认模型)
        if (id === FAL_LORA_PREF_SERVICE) o.textContent = (it.name && it.name !== id ? it.name + " · " + id : "Z-Image Turbo LoRA · " + id);
        else o.textContent = it.name || id;
        $("service").appendChild(o);
      });
      state.catalogById = byId;
      if (state._pendingService) {
        // applyImport may SELECT an explicit j.serviceId (intentional, not soft-fill).
        ensureSelectOpt($("service"), state._pendingService);
        $("service").value = state._pendingService;
        state._pendingService = "";
      } else if (state._pinFalLoraService && be === "fal") {
        ensureSelectOpt($("service"), state._pinFalLoraService);
        $("service").value = state._pinFalLoraService;
      } else if (prevService) {
        // Preserve prior selection across catalog refresh (fixture race fix)
        ensureSelectOpt($("service"), prevService);
        $("service").value = prevService;
      }
      if (be === "fal" && falHasLoras()) ensureFalLoraServiceSelected();
      // Do NOT auto-select CIVITAI_PREF when empty — empty stays empty until user/import picks.
      syncParamSurface();
      syncLoraUi();
    } catch (_) {}
  }
  async function loadOuts() {
    try {
      const r = await fetch("/api/outs");
      const j = await r.json();
      // v0821i: keep videos in 生成历史 (kind===video or .mp4) — do not filter them out
      const items = (j.items || []).filter((it) => {
        const u = it.url || it.path || "";
        if (!u) return false;
        const k = it.kind || mediaKindOf(u);
        return k === "image" || k === "video";
      });
      state.history = items.slice(0, 24).map((it) => ({
        url: it.url || it.path,
        title: String(it.file || it.name || "历史成片").replace(/\.[^.]+$/, ""),
        kind: it.kind || mediaKindOf(it.url || it.path || ""),
      })).filter((it) => it.url);
      renderRail();
    } catch (_) {}
  }
  $("backend").onchange = function () {
    syncParamSurface();
    loadCatalog();
    syncLoraUi();
  };
  if ($("service")) {
    $("service").addEventListener("change", function () { syncLoraUi(); });
  }

  window.addEventListener("resize", () => { drawMinimap(); positionDock(); });

  if (!restore()) loadDemo();
  // v0821o2: mount fixture AFTER first catalog fill so #service stays turbo/lora (not 默认模型)
  let _wantFalLoraFixture = false;
  try {
    const q = String(location.search || "");
    const h = String(location.hash || "");
    if (/[?&]fixture=fal-lora\b/.test(q) || h === "#fal-lora" || h === "#fal-lora-fixture") {
      _wantFalLoraFixture = true;
    }
  } catch (_) {}
  applyCam();
  syncZoomPresets();
  renderCards();
  drawWires();
  bindLoraUi();
  syncLoraUi();
  syncParamSurface();
  loadComfyDefaults().then(function () { return loadCatalog(); }).then(function () {
    if (_wantFalLoraFixture) return mountFalLoraFixture();
  }).then(function () {
    if (_wantFalLoraFixture) ensureFalLoraServiceSelected();
  });
  loadOuts();
  selectNode(state.selected || "shot-1", { collapsed: true });
})();
