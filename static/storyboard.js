(function () {
  const $ = (id) => document.getElementById(id);
  const STORE = "nl-storyboard-v0821o7";
  const STORE_OLDS = ["nl-storyboard-v0821o6b", "nl-storyboard-v0821o6", "nl-storyboard-v0821o5", "nl-storyboard-v0821o4", "nl-storyboard-v0821o3", "nl-storyboard-v0821o2", "nl-storyboard-v0821o", "nl-storyboard-v0821n5", "nl-storyboard-v0821n4", "nl-storyboard-v0821n3", "nl-storyboard-v0821n2", "nl-storyboard-v0821n", "nl-storyboard-v0821m2", "nl-storyboard-v0821m", "nl-storyboard-v0821l", "nl-storyboard-v0821k", "nl-storyboard-v0821j", "nl-storyboard-v0821i", "nl-storyboard-v0821h", "nl-storyboard-v0821g", "nl-storyboard-v0821f", "nl-storyboard-v0821e", "nl-storyboard-v0821d", "nl-storyboard-v0821c", "nl-storyboard-v0821b", "nl-storyboard-v0821", "nl-storyboard-v0820c", "nl-storyboard-v0820b", "nl-storyboard-v0820", "nl-storyboard-v0819b", "nl-storyboard-v0819", "nl-storyboard-v0818", "nl-storyboard-v0817c", "nl-storyboard-v0817b", "nl-storyboard-v0817", "nl-storyboard-v0816b", "nl-storyboard-v0816", "nl-storyboard-v0815c", "nl-storyboard-v0815b", "nl-storyboard-v0815", "nl-storyboard-v0814", "nl-storyboard-v0813", "nl-storyboard-v0812", "nl-storyboard-v0811", "nl-storyboard-v0810", "nl-storyboard-v0809", "nl-storyboard-v0808", "nl-storyboard-v0807", "nl-storyboard-v0806", "nl-storyboard-v0805", "nl-storyboard-v0804", "nl-storyboard-v0803", "nl-storyboard-v0802", "nl-storyboard-v0798", "nl-storyboard-v0797", "nl-storyboard-v0796", "nl-storyboard-v0793", "nl-storyboard-v0791", "nl-storyboard-v0790"];
  const CIVITAI_PREF_SERVICE = "image/comfy/krea2/turbo/createImage";
  // v0821o7: Composer params for all backends; full catalog roster; import does not silent-swap Turbo
  // v0821o6b: Magao outbound loras [{model, weight}] even for one; fixture force modelscope-ai
  // v0821o6: Magao ② mount Tongyi-MAI/Z-Image-Turbo + Hub LoRA; skip Civitai http; no AI↔CN drift
  // v0821o5: HF Z-Image turbo pins fal-ai; skip wavespeed; fal-ai error is final
  // v0821o4: HF ② mount Tongyi-MAI/Z-Image-Turbo + http LoRA; never fal /lora sibling
  // v0821o3: Fal import without loras[] clears stale chips (was wantCivitai-only)
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
  const FAL_LORA_PREF_SERVICE = "fal-ai/krea-2/turbo/lora";
  const FAL_LORA_FIXTURE_VERSION = "3231694";
  const FAL_LORA_FIXTURE_PATH = "https://civitai.com/api/download/models/3231694";
  const HF_LORA_PREF_SERVICE = "krea/Krea-2-Turbo";
  const MS_LORA_PREF_SERVICE = "krea/Krea-2-Turbo";
  const COMFY_PARAM_IDS = ["width", "height", "steps", "cfg", "sampler", "scheduler", "seed"];
  const FAL_PARAM_IDS = ["duration", "aspect", "res"];
  const SERVICE_SYNC_BUDGET = 300;
  const SERVICE_CHUNK_SIZE = 400;
  const CATALOG_FETCH_TIMEOUT_MS = 20000;
  const CATALOG_MODELSCOPE_TIMEOUT_MS = 60000;
  const CATALOG_PAGE_SIZE = 50;
  let _svcChunkHandle = 0;
  let _svcChunkToken = 0;
  let _catalogToken = 0;
  let _catalogFlight = null;
  let _importToken = 0;
  let _composerShotId = null;
  const SHOT_COMPOSER_FIELDS = ["prompt", "negative", "duration", "aspect", "res", "nanoRes"].concat(COMFY_PARAM_IDS);
  const SNAP_PX = 36;
  const vp = $("viewport");
  const world = $("world");
  const stage = document.querySelector(".stage");
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
    catalogPaging: { key: "", page: 0, pageSize: CATALOG_PAGE_SIZE, hasMore: false, nextPage: null,
      partial: false, warning: "", retryPage: null, hubTotals: null, hubCoverage: null, loading: false },
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
    uploading: 0,
    dockMode: "collapsed",
    workspace: "canvas",
    script: { title: "未命名故事", logline: "", scenes: [] },
    editor: { activeShotId: null, playing: false, playIndex: 0, timer: null },
    lastComposerShot: null,
    loras: [],
    _serviceItems: [],
    _providerCaps: {},
  };
  const minimapImages = new WeakMap();

  function uid(prefix) { return prefix + "-" + Math.random().toString(36).slice(2, 8); }
  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&" + "amp;")
      .replace(/</g, "&" + "lt;")
      .replace(/"/g, "&" + "quot;");
  }
  function isVideoUrl(u) { return /\.(mp4|webm|mov)(\?|$)/i.test(u || ""); }
  function isImageSource(n) {
    if (!n || !n.url) return false;
    const u = String(n.url);
    // Studio uploads are /out/<file>; treat as image unless the path is clearly video/audio.
    if (u.indexOf("/out/") === 0 && !isVideoUrl(u) && !/\.(mp3|wav|ogg|m4a)(\?|$)/i.test(u)) return true;
    return mediaKindOf(u, n.kind === "shot" ? n.mode : (n.mediaKind || n.kind)) === "image";
  }
  function nodeById(id) { return state.nodes.find((n) => n.id === id); }
  function box(n) { return n.kind === "shot" ? { w: 640, h: 360 } : { w: 132, h: 208 }; }
  function assets() { return state.nodes.filter((n) => n.kind !== "shot"); }
  function shots() { return state.nodes.filter((n) => n.kind === "shot"); }
  function sceneById(id) {
    return (state.script && Array.isArray(state.script.scenes))
      ? state.script.scenes.find((scene) => scene.id === id) || null
      : null;
  }
  function shotScene(shotId) {
    const shot = nodeById(shotId);
    return sceneById(shot && shot.sceneId) ||
      ((state.script && state.script.scenes || []).find((scene) => (scene.shotIds || []).indexOf(shotId) >= 0)) ||
      null;
  }
  function createScriptScene(index) {
    return {
      id: uid("scene"),
      title: "场次 " + (index + 1),
      location: "",
      time: "",
      beat: "",
      shotIds: [],
    };
  }
  function ensureWorkspaceModel() {
    if (!state.script || typeof state.script !== "object") {
      state.script = { title: "未命名故事", logline: "", scenes: [] };
    }
    if (!Array.isArray(state.script.scenes)) state.script.scenes = [];
    state.script.title = state.script.title || "未命名故事";
    state.script.logline = state.script.logline || "";
    const live = new Set(shots().map((shot) => shot.id));
    const claimed = new Set();
    state.script.scenes = state.script.scenes.map((scene, i) => {
      const next = Object.assign(createScriptScene(i), scene || {});
      next.id = scene && scene.id ? String(scene.id) : uid("scene");
      next.title = next.title || ("场次 " + (i + 1));
      next.shotIds = (Array.isArray(scene && scene.shotIds) ? scene.shotIds : [])
        .filter((id) => live.has(id) && !claimed.has(id));
      next.shotIds.forEach((id) => claimed.add(id));
      next.location = next.location || "";
      next.time = next.time || "";
      next.beat = next.beat || "";
      return next;
    });
    if (!state.script.scenes.length) state.script.scenes.push(createScriptScene(0));
    const first = state.script.scenes[0];
    shots().forEach((shot) => {
      if (claimed.has(shot.id)) {
        shot.sceneId = state.script.scenes.find((scene) => scene.shotIds.indexOf(shot.id) >= 0).id;
        return;
      }
      // Existing canvases had no script model; keep every shot editable in the first scene.
      first.shotIds.push(shot.id);
      shot.sceneId = first.id;
    });
    state.script.scenes.forEach((scene) => {
      scene.shotIds.forEach((id) => {
        const shot = nodeById(id);
        if (shot) shot.sceneId = scene.id;
      });
    });
    if (!state.editor || typeof state.editor !== "object") state.editor = {};
    if (!state.editor.activeShotId || !nodeById(state.editor.activeShotId)) {
      state.editor.activeShotId = shots()[0] ? shots()[0].id : null;
    }
    return state.script;
  }
  function assignShotToScene(shotId, sceneId) {
    ensureWorkspaceModel();
    const shot = nodeById(shotId);
    const target = sceneById(sceneId);
    if (!shot || shot.kind !== "shot" || !target) return false;
    state.script.scenes.forEach((scene) => {
      scene.shotIds = (scene.shotIds || []).filter((id) => id !== shotId);
    });
    target.shotIds.push(shotId);
    shot.sceneId = target.id;
    return true;
  }
  function shotDurationSeconds(shot) {
    const n = Number(String(shot && shot.duration != null ? shot.duration : "").replace(/s$/i, ""));
    return Number.isFinite(n) && n > 0 ? n : 5;
  }
  function formatDuration(seconds) {
    const n = Math.max(0, Number(seconds) || 0);
    const mins = Math.floor(n / 60);
    const secs = Math.round((n - mins * 60) * 10) / 10;
    return mins ? (mins + "m " + String(secs).padStart(4, "0") + "s") : (secs + "s");
  }
  function workspaceMedia(n) {
    if (!n || !n.url) return '<div class="placeholder"><strong>尚未生成</strong><span>打开画布编辑提示词并生成</span></div>';
    return isVideoUrl(n.url)
      ? '<video src="' + esc(n.url) + '" controls muted playsinline></video>'
      : '<img src="' + esc(n.url) + '" alt="">';
  }
  function workspaceShotRow(shot, extra) {
    const cls = state.selected === shot.id || (state.editor && state.editor.activeShotId === shot.id) ? " on" : "";
    return '<div class="script-shot-row' + cls + '">' +
      '<button type="button" class="script-shot-main" data-workspace-shot="' + esc(shot.id) + '">' +
      (shot.url ? '<img src="' + esc(shot.url) + '" alt="">' : '<span class="workspace-shot-empty">＋</span>') +
      '<span class="script-shot-copy"><strong>' + esc(shot.title || "分镜") + '</strong><small>' +
      esc(shot.prompt ? shot.prompt.slice(0, 80) : "还没有画面提示词") + '</small></span></button>' +
      (extra || "") + '</div>';
  }
  function renderScriptWorkspace() {
    const panel = $("scriptWorkspace");
    if (!panel) return;
    const script = ensureWorkspaceModel();
    const scenes = script.scenes;
    if (!state._scriptSceneId || !sceneById(state._scriptSceneId)) state._scriptSceneId = scenes[0] && scenes[0].id;
    const active = sceneById(state._scriptSceneId) || scenes[0];
    const allShots = shots();
    if (!state._scriptShotId || !nodeById(state._scriptShotId)) {
      state._scriptShotId = active && active.shotIds[0] || allShots[0] && allShots[0].id || "";
    }
    const activeShot = nodeById(state._scriptShotId);
    panel.innerHTML =
      '<div class="workspace-shell">' +
      '<div class="workspace-top"><div>' +
      '<div class="workspace-kicker">SCRIPT PLANNER</div>' +
      '<h1 class="workspace-title" id="scriptWorkspaceTitle">剧本策划</h1>' +
      '<p class="workspace-subtitle">把故事目标、场次节拍和画布分镜放在同一份可持续编辑的工作稿里。</p>' +
      '</div><div class="workspace-actions">' +
      '<button type="button" class="workspace-btn primary" data-script-act="add-scene">＋ 新建场次</button>' +
      '<button type="button" class="workspace-btn" data-script-act="add-shot">＋ 新建分镜</button>' +
      '<button type="button" class="workspace-btn" data-script-act="open-canvas">打开画布</button>' +
      '</div></div>' +
      '<div class="workspace-grid">' +
      '<section class="workspace-card"><div class="workspace-card-hd"><h2>场次结构</h2><span class="muted">' + scenes.length + ' 场</span></div>' +
      '<div class="script-scenes">' + scenes.map((scene, i) =>
        '<div class="script-scene' + (scene.id === active.id ? ' on' : '') + '">' +
        '<button type="button" class="script-scene-main" data-script-scene="' + esc(scene.id) + '">' +
        '<strong>' + esc(scene.title || ("场次 " + (i + 1))) + '</strong><small>' +
        esc((scene.location || "未定地点") + " · " + (scene.time || "未定时间") + " · " + scene.shotIds.length + " 镜头") +
        '</small></button><span class="script-scene-actions">' +
        '<button type="button" class="workspace-icon-btn" data-script-act="delete-scene" data-scene-id="' + esc(scene.id) + '" title="删除场次"' +
        (scenes.length <= 1 ? ' disabled' : '') + '>×</button></span></div>'
      ).join("") + '</div></section>' +
      '<section class="workspace-card"><div class="workspace-card-hd"><h2>故事工作稿</h2><span class="muted">自动保存到当前浏览器</span></div>' +
      '<div class="workspace-card-body">' +
      '<div class="workspace-form">' +
      '<div class="workspace-field full"><label for="scriptTitle">项目标题</label><input id="scriptTitle" data-script-field="title" value="' + esc(script.title) + '" placeholder="例如：雨夜回声"></div>' +
      '<div class="workspace-field full"><label for="scriptLogline">一句话梗概</label><textarea id="scriptLogline" data-script-field="logline" placeholder="主角想要什么，什么阻止了他？">' + esc(script.logline) + '</textarea></div>' +
      '<div class="workspace-field"><label for="sceneTitle">当前场次标题</label><input id="sceneTitle" data-scene-field="title" value="' + esc(active.title) + '"></div>' +
      '<div class="workspace-field"><label for="sceneLocation">地点</label><input id="sceneLocation" data-scene-field="location" value="' + esc(active.location) + '" placeholder="室内 / 外景"></div>' +
      '<div class="workspace-field"><label for="sceneTime">时间</label><input id="sceneTime" data-scene-field="time" value="' + esc(active.time) + '" placeholder="清晨 / 夜"></div>' +
      '<div class="workspace-field"><label for="sceneBeat">本场目标</label><input id="sceneBeat" data-scene-field="beat" value="' + esc(active.beat) + '" placeholder="这一场必须发生什么"></div>' +
      '</div>' +
      '<div class="workspace-section"><h3>场次分镜</h3><span class="muted">' + active.shotIds.length + ' 个分镜</span></div>' +
      '<div class="script-shot-list">' +
      (active.shotIds.length ? active.shotIds.map((id) => {
        const shot = nodeById(id);
        if (!shot) return "";
        return workspaceShotRow(shot,
          '<input class="workspace-shot-title" data-shot-title="' + esc(shot.id) + '" value="' + esc(shot.title || "分镜") + '" aria-label="分镜标题">');
      }).join("") : '<div class="workspace-empty">这场还没有分镜。可以新建分镜，或把已有分镜加入这里。</div>') +
      '</div>' +
      '<div class="workspace-inline"><select data-script-shot-select aria-label="选择已有分镜"><option value="">选择已有分镜</option>' +
      allShots.map((shot) => '<option value="' + esc(shot.id) + '"' + (shot.id === state._scriptShotId ? ' selected' : '') + '>' + esc(shot.title || "分镜") + '</option>').join("") +
      '</select><button type="button" class="workspace-btn" data-script-act="assign-shot"' + (activeShot ? '' : ' disabled') + '>加入当前场次</button></div>' +
      '<div class="workspace-note">选择已有分镜后加入当前场次；点分镜卡会回到画布并保留当前故事结构。删除场次只会把镜头转移到其他场次，不会删除画布内容。</div>' +
      '</div></section></div></div>';
  }
  function editorSequence() {
    ensureWorkspaceModel();
    const result = [];
    state.script.scenes.forEach((scene) => {
      (scene.shotIds || []).forEach((id) => {
        const shot = nodeById(id);
        if (shot) result.push({ scene: scene, shot: shot });
      });
    });
    return result;
  }
  function renderEditorWorkspace() {
    const panel = $("editorWorkspace");
    if (!panel) return;
    const sequence = editorSequence();
    if (!state.editor.activeShotId && sequence[0]) state.editor.activeShotId = sequence[0].shot.id;
    if (state.editor.activeShotId && !nodeById(state.editor.activeShotId)) state.editor.activeShotId = sequence[0] ? sequence[0].shot.id : null;
    const active = nodeById(state.editor.activeShotId);
    const total = sequence.reduce((n, item) => n + shotDurationSeconds(item.shot), 0);
    const grouped = state.script.scenes.map((scene) => {
      const rows = (scene.shotIds || []).map((id, i) => {
        const shot = nodeById(id);
        if (!shot) return "";
        const pos = sequence.findIndex((item) => item.shot.id === id);
        const selected = active && active.id === shot.id ? " on" : "";
        return '<div class="editor-row' + selected + '">' +
          '<span class="editor-index">' + String(pos + 1).padStart(2, "0") + '</span>' +
          '<button type="button" class="editor-shot-btn" data-editor-shot="' + esc(shot.id) + '">' +
          (shot.url ? '<img src="' + esc(shot.url) + '" alt="">' : '<span class="workspace-shot-empty">＋</span>') +
          '<span class="editor-shot-copy"><strong>' + esc(shot.title || "分镜") + '</strong><small>' + esc(scene.title) + '</small></span></button>' +
          '<select data-editor-scene="' + esc(shot.id) + '" aria-label="所属场次">' +
          state.script.scenes.map((target) => '<option value="' + esc(target.id) + '"' + (target.id === scene.id ? ' selected' : '') + '>' + esc(target.title) + '</option>').join("") +
          '</select><input type="number" min="1" max="999" step="1" data-editor-duration="' + esc(shot.id) + '" value="' + esc(shotDurationSeconds(shot)) + '" aria-label="时长秒数">' +
          '<span class="editor-row-actions">' +
          '<button type="button" class="workspace-icon-btn" data-editor-move="up" data-shot-id="' + esc(shot.id) + '" title="上移"' + (i === 0 ? ' disabled' : '') + '>↑</button>' +
          '<button type="button" class="workspace-icon-btn" data-editor-move="down" data-shot-id="' + esc(shot.id) + '" title="下移"' + (i === scene.shotIds.length - 1 ? ' disabled' : '') + '>↓</button>' +
          '</span></div>';
      }).join("");
      return '<div class="workspace-section"><h3>' + esc(scene.title) + '</h3><span class="muted">' + scene.shotIds.length + ' 镜头</span></div>' +
        (rows || '<div class="editor-empty">本场暂无分镜</div>');
    }).join("");
    panel.innerHTML =
      '<div class="workspace-shell"><div class="workspace-top"><div>' +
      '<div class="workspace-kicker">EDIT TIMELINE</div><h1 class="workspace-title" id="editorWorkspaceTitle">编辑器</h1>' +
      '<p class="workspace-subtitle">把已生成的分镜按场次编排，调整顺序与时长；这里不会偷偷触发生成。</p></div>' +
      '<div class="workspace-actions"><button type="button" class="workspace-btn primary" data-editor-act="play">' + (state.editor.playing ? '暂停播放' : '播放序列') + '</button>' +
      '<button type="button" class="workspace-btn" data-editor-act="next">下一镜</button><button type="button" class="workspace-btn" data-editor-act="open-canvas">打开画布</button></div></div>' +
      '<div class="editor-layout"><div class="workspace-card editor-timeline"><div class="workspace-card-hd"><h2>时间线</h2><span class="muted">' + sequence.length + ' 镜头</span></div>' +
      '<div class="workspace-card-body"><div class="editor-stats"><span>总时长 <strong>' + esc(formatDuration(total)) + '</strong></span><span>已生成 <strong>' + sequence.filter((item) => !!item.shot.url).length + '/' + sequence.length + '</strong></span></div>' +
      '<div class="editor-rows">' + (grouped || '<div class="editor-empty">先在剧本策划中创建分镜。</div>') + '</div></div></div>' +
      '<div class="editor-preview"><div class="editor-preview-head"><strong>' + esc(active ? active.title : "未选择分镜") + '</strong><span class="muted">' + (active ? formatDuration(shotDurationSeconds(active)) : "") + '</span></div>' +
      '<div class="editor-preview-media">' + workspaceMedia(active) + '</div>' +
      '<div class="workspace-note">' + esc(active && active.prompt ? active.prompt : "选择时间线中的分镜查看画面提示词。") + '</div></div></div></div>';
  }
  function renderWorkspace() {
    ensureWorkspaceModel();
    const script = $("scriptWorkspace");
    const editor = $("editorWorkspace");
    if (script) script.hidden = state.workspace !== "script";
    if (editor) editor.hidden = state.workspace !== "editor";
    document.querySelectorAll("[data-workspace]").forEach((btn) => {
      const on = btn.dataset.workspace === state.workspace;
      btn.classList.toggle("on", on);
      if (on) btn.setAttribute("aria-current", "page");
      else btn.removeAttribute("aria-current");
    });
    if (stage) stage.classList.toggle("workspace-mode", state.workspace !== "canvas");
    if (state.workspace === "script") renderScriptWorkspace();
    if (state.workspace === "editor") renderEditorWorkspace();
  }
  function setWorkspace(next) {
    if (next !== "canvas" && next !== "script" && next !== "editor") next = "canvas";
    if (next !== "editor" && state.editor && state.editor.playing) stopEditorPlayback();
    state.workspace = next;
    renderWorkspace();
    if (next === "canvas") {
      renderCards();
      drawWires();
      renderDock();
    }
    persist();
  }
  function addWorkspaceShot() {
    const pos = newShotPosition(shots().length);
    const shot = { id: uid("shot"), kind: "shot", title: "分镜" + (shots().length + 1), x: pos.x, y: pos.y, url: "", firstFrameId: "", prompt: "" };
    state.nodes.push(shot);
    ensureWorkspaceModel();
    const scene = sceneById(state._scriptSceneId) || state.script.scenes[0];
    assignShotToScene(shot.id, scene.id);
    state._scriptShotId = shot.id;
    state.editor.activeShotId = shot.id;
    selectNode(shot.id, { collapsed: true });
    persist();
    renderWorkspace();
  }
  function addWorkspaceScene() {
    ensureWorkspaceModel();
    const scene = createScriptScene(state.script.scenes.length);
    state.script.scenes.push(scene);
    state._scriptSceneId = scene.id;
    persist();
    renderWorkspace();
  }
  function deleteWorkspaceScene(sceneId) {
    ensureWorkspaceModel();
    if (state.script.scenes.length <= 1) {
      setMsg("至少保留一个场次", "warn");
      return;
    }
    const index = state.script.scenes.findIndex((scene) => scene.id === sceneId);
    if (index < 0) return;
    const fallback = state.script.scenes[index === 0 ? 1 : 0];
    const doomed = state.script.scenes[index];
    (doomed.shotIds || []).slice().forEach((id) => assignShotToScene(id, fallback.id));
    state.script.scenes = state.script.scenes.filter((scene) => scene.id !== sceneId);
    state._scriptSceneId = fallback.id;
    persist();
    renderWorkspace();
  }
  function moveEditorShot(shotId, direction) {
    const shot = nodeById(shotId);
    const scene = shot && shotScene(shotId);
    if (!shot || !scene) return;
    const at = scene.shotIds.indexOf(shotId);
    const to = direction === "up" ? at - 1 : at + 1;
    if (at < 0 || to < 0 || to >= scene.shotIds.length) return;
    const row = scene.shotIds.splice(at, 1)[0];
    scene.shotIds.splice(to, 0, row);
    persist();
    renderWorkspace();
  }
  function stopEditorPlayback() {
    if (state.editor && state.editor.timer) clearTimeout(state.editor.timer);
    if (state.editor) {
      state.editor.timer = null;
      state.editor.playing = false;
    }
  }
  function scheduleEditorPlayback() {
    if (!state.editor.playing) return;
    const sequence = editorSequence();
    if (!sequence.length) {
      stopEditorPlayback();
      renderWorkspace();
      return;
    }
    const at = Math.max(0, sequence.findIndex((item) => item.shot.id === state.editor.activeShotId));
    state.editor.playIndex = at < 0 ? 0 : at;
    state.editor.activeShotId = sequence[state.editor.playIndex].shot.id;
    renderWorkspace();
    state.editor.timer = setTimeout(() => {
      if (!state.editor.playing) return;
      state.editor.playIndex = (state.editor.playIndex + 1) % sequence.length;
      scheduleEditorPlayback();
    }, shotDurationSeconds(sequence[state.editor.playIndex].shot) * 1000);
  }
  function toggleEditorPlayback() {
    if (state.editor.playing) stopEditorPlayback();
    else {
      state.editor.playing = true;
      state.editor.playIndex = 0;
      scheduleEditorPlayback();
      return;
    }
    renderWorkspace();
  }
  function nextEditorShot() {
    const sequence = editorSequence();
    if (!sequence.length) return;
    const at = sequence.findIndex((item) => item.shot.id === state.editor.activeShotId);
    state.editor.activeShotId = sequence[(at + 1 + sequence.length) % sequence.length].shot.id;
    renderWorkspace();
    persist();
  }
  function bindWorkspace() {
    document.querySelectorAll("[data-workspace]").forEach((btn) => {
      btn.addEventListener("click", () => setWorkspace(btn.dataset.workspace));
    });
    const script = $("scriptWorkspace");
    if (script) script.addEventListener("click", (e) => {
      const sceneBtn = e.target.closest("[data-script-scene]");
      if (sceneBtn) {
        state._scriptSceneId = sceneBtn.dataset.scriptScene;
        renderWorkspace();
        return;
      }
      const shotBtn = e.target.closest("[data-workspace-shot]");
      if (shotBtn) {
        state._scriptShotId = shotBtn.dataset.workspaceShot;
        state.editor.activeShotId = state._scriptShotId;
        selectNode(state._scriptShotId, { keepClosed: true });
        return;
      }
      const act = e.target.closest("[data-script-act]");
      if (!act) return;
      if (act.dataset.scriptAct === "add-scene") addWorkspaceScene();
      else if (act.dataset.scriptAct === "add-shot") addWorkspaceShot();
      else if (act.dataset.scriptAct === "delete-scene") deleteWorkspaceScene(act.dataset.sceneId);
      else if (act.dataset.scriptAct === "open-canvas") setWorkspace("canvas");
      else if (act.dataset.scriptAct === "assign-shot") {
        const id = script.querySelector("[data-script-shot-select]") && script.querySelector("[data-script-shot-select]").value;
        const scene = sceneById(state._scriptSceneId);
        if (id && scene && assignShotToScene(id, scene.id)) {
          state._scriptShotId = id;
          persist();
          renderWorkspace();
        }
      }
    });
    if (script) script.addEventListener("input", (e) => {
      const field = e.target.closest("[data-script-field]");
      if (field) {
        state.script[field.dataset.scriptField] = field.value;
        persist();
        return;
      }
      const sceneField = e.target.closest("[data-scene-field]");
      const scene = sceneById(state._scriptSceneId);
      if (sceneField && scene) {
        scene[sceneField.dataset.sceneField] = sceneField.value;
        persist();
        return;
      }
      const title = e.target.closest("[data-shot-title]");
      const shot = title && nodeById(title.dataset.shotTitle);
      if (shot) {
        shot.title = title.value || "分镜";
        state._scriptShotId = shot.id;
        renderCards();
        persist();
      }
    });
    if (script) script.addEventListener("change", (e) => {
      if (e.target.matches("[data-script-shot-select]")) state._scriptShotId = e.target.value;
    });
    const editor = $("editorWorkspace");
    if (editor) editor.addEventListener("click", (e) => {
      const shotBtn = e.target.closest("[data-editor-shot]");
      if (shotBtn) {
        state.editor.activeShotId = shotBtn.dataset.editorShot;
        state.selected = state.editor.activeShotId;
        renderWorkspace();
        persist();
        return;
      }
      const act = e.target.closest("[data-editor-act]");
      if (act) {
        if (act.dataset.editorAct === "play") toggleEditorPlayback();
        else if (act.dataset.editorAct === "next") nextEditorShot();
        else if (act.dataset.editorAct === "open-canvas") setWorkspace("canvas");
        return;
      }
      const move = e.target.closest("[data-editor-move]");
      if (move) moveEditorShot(move.dataset.shotId, move.dataset.editorMove);
    });
    if (editor) editor.addEventListener("change", (e) => {
      const sceneSelect = e.target.closest("[data-editor-scene]");
      if (sceneSelect) {
        assignShotToScene(sceneSelect.dataset.editorScene, sceneSelect.value);
        persist();
        renderWorkspace();
        return;
      }
      const duration = e.target.closest("[data-editor-duration]");
      const shot = duration && nodeById(duration.dataset.editorDuration);
      if (shot) {
        shot.duration = duration.value;
        persist();
        renderWorkspace();
      }
    });
  }
  function connectedNodes(shotId) {
    return state.edges.filter((e) => e.to === shotId).map((e) => nodeById(e.from)).filter(Boolean);
  }
  function connectedAssets(shotId) {
    return connectedNodes(shotId).filter(isImageSource);
  }
  function connectedPending(shotId) {
    // A blank shot is an upstream generation dependency, not an upload in flight.
    return connectedNodes(shotId).filter((n) => n && n.kind !== "shot" && !n.url);
  }
  function refReadyMessage(shot) {
    if ((state.uploading || 0) > 0) return "参考图上传中，请稍等";
    if (!shot) return "";
    const pending = connectedPending(shot.id);
    if (pending.length) return "参考图上传中，请稍等";
    return "";
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
      saveDisplayedComposer();
      sessionStorage.setItem(STORE, JSON.stringify({
        cam: state.cam, nodes: state.nodes, edges: state.edges, mode: state.mode,
        railTab: state.railTab,
        groups: state.groups || [],
        workspace: state.workspace || "canvas",
        script: state.script || { title: "未命名故事", logline: "", scenes: [] },
        editor: {
          activeShotId: state.editor && state.editor.activeShotId || null,
          playIndex: state.editor && Number.isFinite(state.editor.playIndex) ? state.editor.playIndex : 0,
        },
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
        nanoRes: $("nanoRes") && $("nanoRes").value,
        negative: $("negative") && $("negative").value,
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
      state.workspace = p.workspace === "script" || p.workspace === "editor" ? p.workspace : "canvas";
      state.script = p.script && typeof p.script === "object"
        ? p.script
        : { title: "未命名故事", logline: "", scenes: [] };
      state.editor = Object.assign(state.editor || {}, p.editor || {});
      state.editor.timer = null;
      state.editor.playing = false;
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
      if ($("width") && $("height")) syncAspectFromSize(Number($("width").value), Number($("height").value));
      if (p.steps != null && $("steps")) $("steps").value = p.steps;
      if (p.cfg != null && $("cfg")) $("cfg").value = p.cfg;
      if (p.cfgScale != null && $("cfg") && (p.cfg == null || p.cfg === "")) $("cfg").value = p.cfgScale;
      if (p.sampler && $("sampler")) ensureSelectOpt($("sampler"), p.sampler);
      if (p.scheduler && $("scheduler")) ensureSelectOpt($("scheduler"), p.scheduler);
      if (p.seed != null && $("seed")) {
        $("seed").value = p.seed;
        $("seed").title = String(p.seed);
      }
      if (p.nanoRes && $("nanoRes")) ensureSelectOpt($("nanoRes"), p.nanoRes);
      if (p.negative != null && $("negative")) $("negative").value = p.negative;
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
    // Blank image shots are real upstream dependencies, not fake image assets.
    // Video/audio results cannot feed an image port.
    if (!isImageSource(src) && !(src.kind === "shot" && !src.url &&
        (src.mode || (src.composer && src.composer.mode) || "image") === "image")) return false;
    const seen = new Set();
    const todo = [dst.id];
    while (todo.length) {
      const id = todo.pop();
      if (id === src.id) return false;
      if (seen.has(id)) continue;
      seen.add(id);
      state.edges.forEach((edge) => { if (edge.from === id) todo.push(edge.to); });
    }
    return true;
  }

  function snapshotComposer() {
    const fields = {};
    SHOT_COMPOSER_FIELDS.forEach((id) => { if ($(id)) fields[id] = $(id).value; });
    return {
      backend: $("backend").value, service: state._pendingService != null ? state._pendingService : $("service").value,
      mode: state.mode, fields: fields,
      loras: JSON.parse(JSON.stringify(state.loras || [])),
    };
  }

  function saveDisplayedComposer() {
    const shot = nodeById(_composerShotId);
    if (!shot || shot.kind !== "shot") return;
    shot.composer = snapshotComposer();
    shot.mode = state.mode;
    shot.prompt = $("prompt").value;
    shot.negativePrompt = $("negative") ? $("negative").value : "";
    writeComfyParamsToShot(shot);
  }

  function activateShotComposer(shot) {
    const id = shot && shot.kind === "shot" ? shot.id : null;
    if (_composerShotId === id) return;
    saveDisplayedComposer();
    _composerShotId = id;
    if (!id || !shot.composer) return;
    const recipe = shot.composer;
    const key = recipe.backend + ":" + recipe.mode;
    state.mode = recipe.mode;
    $("backend").value = recipe.backend;
    state.loras = JSON.parse(JSON.stringify(recipe.loras || []));
    Object.keys(recipe.fields || {}).forEach((field) => {
      const el = $(field);
      if (!el || SHOT_COMPOSER_FIELDS.indexOf(field) < 0) return;
      if (el.tagName === "SELECT") ensureSelectOpt(el, recipe.fields[field]);
      el.value = recipe.fields[field];
    });
    if (state._catalogKey !== key || _catalogFlight) {
      state._pendingService = recipe.service || "";
      loadCatalog();
    } else {
      $("service").value = "";
      if (recipe.service && state.catalogById[recipe.service]) {
        ensureSelectOpt($("service"), recipe.service);
      }
    }
  }

  function createLinkedShot(link, point) {
    const origin = nodeById(link.from);
    if (!origin || !Number.isFinite(point.x) || !Number.isFinite(point.y)) return null;
    const recipe = snapshotComposer();
    const titleSet = new Set(shots().map((shot) => shot.title));
    let number = 1;
    while (titleSet.has("分镜" + number)) number++;
    const shot = Object.assign({}, readComfyParamsFromUi(), {
      id: uid("shot"), kind: "shot", title: "分镜" + number,
      x: point.x - (link.side === "in" ? 640 : 0), y: point.y - 180,
      url: "", firstFrameId: "", prompt: recipe.fields.prompt || "",
      negativePrompt: recipe.fields.negative || "", mode: recipe.mode,
      composer: recipe,
    });
    const src = link.side === "in" ? shot : origin;
    const dst = link.side === "in" ? origin : shot;
    if (!canLink(src, dst)) {
      setMsg("无法建连线：图片输入只接受图片或待生成的图片分镜，不接受视频/音频", "bad");
      return null;
    }
    // Commit node + edge together; no copied output, first frame, job or stage state.
    state.nodes.push(shot);
    if (!linkAssetToShot(src, dst)) {
      state.nodes = state.nodes.filter((n) => n.id !== shot.id);
      return null;
    }
    selectNode(shot.id);
    persist();
    setMsg("已创建 " + shot.title + " 并连线" + (!isImageSource(src) ? " · 上游分镜需先生成图片" : ""), "ok");
    return shot;
  }

  function isBlankCanvasDrop(event, link) {
    const r = vp.getBoundingClientRect();
    if (event.clientX < r.left || event.clientX >= r.right ||
        event.clientY < r.top || event.clientY >= r.bottom) return false;
    if (Math.hypot(event.clientX - link.clientX, event.clientY - link.clientY) < 6) return false;
    const el = document.elementFromPoint(event.clientX, event.clientY);
    return !!(el && vp.contains(el) && !el.closest(
      ".card,.dock,.tools,.zoom,.picker,.rail,.atbox,.skillbox,header,.ghost,.minimap,.import-backdrop,.selbar,.group-bound,path.edge"));
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
        : n._error
          ? '<div class="result-error"><strong>生成失败</strong><span>' + esc(n._error) + '</span></div>'
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
    world.querySelectorAll(".card.shot img,.card.shot video").forEach((el) => {
      const card = el.closest(".card");
      const shot = card && nodeById(card.dataset.id);
      if (!shot) return;
      const sync = () => {
        const w = el.naturalWidth || el.videoWidth || 0;
        const h = el.naturalHeight || el.videoHeight || 0;
        if (!w || !h || (shot.mediaWidth === w && shot.mediaHeight === h)) return;
        shot.mediaWidth = w;
        shot.mediaHeight = h;
        if (state.selected === shot.id) {
          if ($("width")) $("width").value = String(w);
          if ($("height")) $("height").value = String(h);
          syncAspectFromSize(w, h);
          writeComfyParamsToShot(shot);
          persist();
        }
        drawMinimap();
      };
      if (el.complete) sync();
      else el.addEventListener("load", sync, { once: true });
    });
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
      const preview = minimapImages.get(n);
      if (n.url && preview && preview.complete && preview.naturalWidth) {
        ctx.drawImage(preview, x, y, w, h);
      } else {
        ctx.fillStyle = n.kind === "shot" ? "#3a3a48" : "#2a3a36";
        ctx.fillRect(x, y, w, h);
        if (n.url && !preview) {
          const image = new Image();
          image.onload = drawMinimap;
          image.src = n.url;
          minimapImages.set(n, image);
        }
      }
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

  function canvasArea() {
    const r = vp.getBoundingClientRect();
    const narrow = r.width <= 900;
    const area = { left: 12, top: 48, right: r.width - 12, bottom: r.height - (narrow ? 68 : 16) };
    vp.parentElement.querySelectorAll(".tools,.rail,.minimap,.zoom,.selbar").forEach((el) => {
      const b = el.getBoundingClientRect();
      if (!b.width || !b.height) return;
      if (el.classList.contains("selbar") || (narrow && !el.classList.contains("zoom"))) {
        area.top = Math.max(area.top, b.bottom - r.top + 12);
      } else if (!narrow) {
        area.left = Math.max(area.left, b.right - r.left + 12);
      }
    });
    return area;
  }

  function positionDock() {
    const n = nodeById(state.selected);
    if (!dock || !n || n.kind !== "shot" || !dock.classList.contains("show")) return;
    const area = canvasArea(), b = box(n), gap = 18;
    const x = state.cam.x + n.x * state.cam.s, y = state.cam.y + n.y * state.cam.s;
    const nw = b.w * state.cam.s, nh = b.h * state.cam.s;
    const width = Math.min(640, area.right - area.left);
    const height = state.dockMode === "expanded" ? 520 : $("dockHd").offsetHeight + 2;
    const above = y - 34 * state.cam.s - gap - area.top;
    const below = area.bottom - y - nh - gap;
    const right = area.right - x - nw - gap, leftRoom = x - gap - area.left;
    const minHeight = Math.min(height, 260);
    let dockW = width, maxH, left, top;
    // Seko's input follows below the selected node; flip only at viewport edges.
    if (below >= minHeight || (above < minHeight && Math.max(right, leftRoom) < 360 && below >= above)) {
      maxH = Math.min(height, below);
      left = x + (nw - dockW) / 2;
      top = y + nh + gap;
    } else if (above >= minHeight || Math.max(right, leftRoom) < 360) {
      maxH = Math.min(height, above);
      left = x + (nw - dockW) / 2;
      top = y - 34 * state.cam.s - gap - maxH;
    } else {
      const onRight = right >= 360;
      dockW = Math.min(400, onRight ? right : leftRoom);
      maxH = Math.min(height, area.bottom - area.top);
      left = onRight ? x + nw + gap : x - gap - dockW;
      top = y;
    }
    maxH = Math.min(area.bottom - area.top, Math.max(Math.min(height, 112), maxH));
    left = Math.max(area.left, Math.min(left, area.right - dockW));
    top = Math.max(area.top, Math.min(top, area.bottom - maxH));
    Object.assign(dock.style, {
      width: dockW + "px", maxHeight: maxH + "px", left: left + "px", top: top + "px",
      right: "auto", bottom: "auto", transform: "none",
      visibility: x + nw < 0 || y + nh < 0 || x > vp.clientWidth || y > vp.clientHeight ? "hidden" : "",
    });
    dock.classList.add("near");
    ["skillbox", "atbox", "picker"].forEach((id) => {
      const el = $(id);
      if (!el) return;
      const w = Math.min(400, dockW);
      const px = left + dockW + gap + w <= area.right ? left + dockW + gap
        : left - w - gap >= area.left ? left - w - gap : left;
      Object.assign(el.style, {
        left: px + "px", right: "auto", top: top + "px", bottom: "auto",
        width: w + "px", maxHeight: Math.min(320, area.bottom - top) + "px", transform: "none",
      });
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
    activateShotComposer(n);
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
    if ($("negative")) $("negative").value = n.negativePrompt || "";
    applyComfyParamsToUi(n);
    syncParamSurface._skipDock = true;
    try { syncParamSurface(); }
    finally { syncParamSurface._skipDock = false; }
    ["text", "image", "video", "audio"].forEach((m) => {
      const el = $("mode" + (m === "image" ? "Img" : m === "video" ? "Vid" : m === "text" ? "Text" : "Aud"));
      if (el) el.classList.toggle("on", state.mode === m);
    });
    const list = assets();
    const linked = connectedAssets(n.id);
    const frame = frameAsset(n);
    const needFrame = state.mode === "video" && !frame;
    const stub = isStubMode();
    const capMsg = refCapGateMessage(n);
    const unusedMsg = refUnusedGateMessage(n);
    syncSendGate(needFrame, stub);
    if (stub) {
      setMsg((state.mode === "text" ? "文本生成" : "音频生成") + " · 本版未接", "warn");
    } else if (needFrame) {
      // v0821g: missing-frame is hard stop (red), not yellow warn
      setMsg("缺首帧 · 视频需要先连一张首帧图", "bad");
    } else if (unusedMsg) {
      setMsg(unusedMsg, "bad");
    } else if (capMsg) {
      setMsg(capMsg, "bad");
    } else if (state.mode !== "video") {
      const msgEl = $("msg");
      const t = (msgEl && msgEl.textContent) || "";
      if (t.indexOf("缺首帧") >= 0) setMsg("");
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
    // Hint numerator uses the same URL set as the send gate (countRefUrls), not a stale default cap.
    const refCount = countRefUrls(null, n).length;
    const remain = Math.max(0, refCap - linked.length);
    const refHint = refCount > refCap
      ? '<span class="ref-cap-hint" title="参考图上限">参考 ' + refCount + '/' + refCap + ' · 超出，请减少连线</span>'
      : '<span class="ref-cap-hint" title="参考图上限">参考 ' + refCount + '/' + refCap +
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
      state._scriptShotId = n.id;
      if (state.editor) state.editor.activeShotId = n.id;
      if (state.cam.s >= 1) {
        if (constrainShotsToViewport()) renderCards();
        constrainCameraToShots(n);
        applyCam();
      }
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
    if (state.workspace !== "canvas") renderWorkspace();
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
    if (!canLink(asset, shot)) return false;
    if (!state.edges.some((e) => e.from === asset.id && e.to === shot.id)) {
      state.edges.push({ from: asset.id, to: shot.id });
      invalidateStageProgress(shot);
    }
    mention(asset, shot);
    if (shot && !shot.firstFrameId && isImageSource(asset)) shot.firstFrameId = asset.id;
    return true;
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
        userPromoted: true,
        mediaKind: mediaKindOf(url),
      };
      state.nodes.push(asset);
    } else {
      asset.url = url;
      asset.title = (shot.title || "分镜") + (isVideoUrl(url) ? "视频" : "成片");
      asset.fromShot = shot.id;
      asset.userPromoted = true;
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
    const n = nodeById(state.selected), b = n && box(n);
    // Toolbar zoom keeps the selection, not the unrelated viewport centre, in view.
    const cx = n ? state.cam.x + (n.x + b.w / 2) * state.cam.s : r.width / 2;
    const cy = n ? state.cam.y + (n.y + b.h / 2) * state.cam.s : r.height / 2;
    const w0 = clientToWorld(r.left + cx, r.top + cy);
    state.cam.s = next;
    state.cam.x = cx - w0.x * next;
    state.cam.y = cy - w0.y * next;
    if (constrainShotsToViewport()) renderCards();
    constrainCameraToShots(n);
    applyCam(); persist();
    syncZoomPresets();
  }

  function constrainCameraToShots(focus) {
    const area = canvasArea();
    const list = shots();
    if (!list.length) return;
    const pad = 12;
    const left = area.left + pad, right = area.right - pad;
    const top = area.top + pad, bottom = area.bottom - pad;
    const scale = state.cam.s;
    const bounds = list.reduce((out, item) => {
      const b = box(item);
      out.minX = Math.min(out.minX, item.x);
      out.minY = Math.min(out.minY, item.y);
      out.maxX = Math.max(out.maxX, item.x + b.w);
      out.maxY = Math.max(out.maxY, item.y + b.h);
      return out;
    }, { minX: Infinity, minY: Infinity, maxX: -Infinity, maxY: -Infinity });
    const axis = (min, max, lo, hi, current, target, size) => {
      const span = (max - min) * scale;
      if (span <= hi - lo) return (lo + hi - span) / 2 - min * scale;
      const targetPos = current + target * scale;
      const targetSize = size * scale;
      const kept = targetSize > hi - lo
        ? (lo + hi - targetSize) / 2
        : Math.max(lo, Math.min(targetPos, hi - targetSize));
      return kept - target * scale;
    };
    const target = focus || list[0];
    const tb = box(target);
    state.cam.x = axis(bounds.minX, bounds.maxX, left, right, state.cam.x, target.x, tb.w);
    state.cam.y = axis(bounds.minY, bounds.maxY, top, bottom, state.cam.y, target.y, tb.h);
  }

  function constrainShotsToViewport() {
    if (state.cam.s < 1) return false;
    const area = canvasArea(), pad = 12, scale = state.cam.s;
    const minX = (area.left + pad - state.cam.x) / scale;
    const maxX = (area.right - pad - state.cam.x) / scale - 640;
    const minY = (area.top + pad - state.cam.y) / scale;
    const maxY = (area.bottom - pad - state.cam.y) / scale - 360;
    const list = shots();
    if (!list.length) return false;
    const bounds = list.reduce((out, n) => {
      out.minX = Math.min(out.minX, n.x);
      out.minY = Math.min(out.minY, n.y);
      out.maxX = Math.max(out.maxX, n.x + 640);
      out.maxY = Math.max(out.maxY, n.y + 360);
      return out;
    }, { minX: Infinity, minY: Infinity, maxX: -Infinity, maxY: -Infinity });
    const shift = (min, max, lo, hi) => {
      if (hi < lo) return 0;
      let d = min < lo ? lo - min : 0;
      if (max + d > hi) d = hi - max;
      return d;
    };
    const dx = shift(bounds.minX, bounds.maxX, minX, maxX + 640);
    const dy = shift(bounds.minY, bounds.maxY, minY, maxY + 360);
    let changed = false;
    list.forEach((n) => {
      const oldX = n.x, oldY = n.y;
      n.x += dx;
      n.y += dy;
      // ponytail: if several cards exceed the 100% viewport, clamp individually;
      // upgrade to a layout pass only when non-overlapping placement is required.
      if (maxX >= minX) n.x = Math.max(minX, Math.min(n.x, maxX));
      if (maxY >= minY) n.y = Math.max(minY, Math.min(n.y, maxY));
      changed = changed || n.x !== oldX || n.y !== oldY;
    });
    return changed;
  }

  function newShotPosition(index) {
    const area = canvasArea();
    const scale = state.cam.s || 1;
    const b = { w: 640, h: 360 };
    const pad = 16;
    const minX = (area.left + pad - state.cam.x) / scale;
    const maxX = (area.right - pad - state.cam.x) / scale - b.w;
    const minY = (area.top + pad - state.cam.y) / scale;
    const maxY = (area.bottom - pad - state.cam.y) / scale - b.h;
    const selected = nodeById(state.selected);
    const baseX = selected && selected.kind === "shot"
      ? selected.x + b.w + 24 / scale
      : ((area.left + area.right) / 2 - state.cam.x) / scale - b.w / 2;
    const baseY = selected && selected.kind === "shot"
      ? selected.y
      : ((area.top + area.bottom) / 2 - state.cam.y) / scale - b.h / 2;
    const clamp = (v, lo, hi) => hi < lo ? (lo + hi) / 2 : Math.max(lo, Math.min(v, hi));
    return {
      x: clamp(baseX + (index % 2) * (24 / scale), minX, maxX),
      y: clamp(baseY + Math.floor(index / 2) * (24 / scale), minY, maxY),
    };
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
    if (e.button !== 0 || e.isPrimary === false) return;
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
      saveDisplayedComposer();
      state.link = { from: n.id, side: port.dataset.side, x1: p.x, y1: p.y, x2: p.x, y2: p.y,
        pointerId: e.pointerId, clientX: e.clientX, clientY: e.clientY };
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
      if (e.pointerId !== state.link.pointerId) return;
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
      if (e.pointerId !== state.link.pointerId) return;
      const link = state.link;
      const w = clientToWorld(e.clientX, e.clientY);
      const snap = nearestCompatiblePort(w.x, w.y, link.from, link.side);
      const target = snap ? nodeById(snap.id) : hitNode(w.x, w.y);
      state.link = null;
      state.snapTarget = null;
      const releaseEl = document.elementFromPoint(e.clientX, e.clientY);
      const onCanvas = releaseEl && vp.contains(releaseEl) && !releaseEl.closest(
        ".dock,.tools,.zoom,.picker,.rail,.atbox,.skillbox,header,.ghost,.minimap,.import-backdrop,.selbar");
      if (onCanvas && target && target.id !== link.from) {
        const a = nodeById(link.from);
        const src = link.side === "in" ? target : a;
        const dst = link.side === "in" ? a : target;
        if (linkAssetToShot(src, dst)) {
          selectNode(dst.id);
        } else {
          setMsg("连线被拒绝：需连接图片输出到分镜输入，且不能形成循环", "bad");
        }
      } else if (!target && !snap && isBlankCanvasDrop(e, link)) {
        createLinkedShot(link, w);
      }
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
  function cancelCanvasGesture(e) {
    if (state.link && e && e.pointerId != null && e.pointerId !== state.link.pointerId) return;
    const pointerId = state.link && state.link.pointerId;
    state.link = null; state.snapTarget = null; state.drag = null; state.pan = null;
    vp.classList.remove("grabbing");
    if (pointerId != null && vp.hasPointerCapture(pointerId)) vp.releasePointerCapture(pointerId);
    drawWires();
  }
  vp.addEventListener("pointercancel", cancelCanvasGesture);
  vp.addEventListener("lostpointercapture", (e) => { if (state.link) cancelCanvasGesture(e); });
  document.addEventListener("keydown", (e) => { if (e.key === "Escape" && state.link) cancelCanvasGesture(); });
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
    const input = $("file");
    const files = input && input.files;
    if (!files || !files.length) return;
    const list = [];
    for (let i = 0; i < files.length; i++) list.push(files[i]);
    input.value = "";
    state.uploading = (state.uploading || 0) + list.length;
    setMsg(list.length > 1 ? ("正在上传 " + list.length + " 个文件…") : "正在上传…");
    const created = [];
    try {
      for (let i = 0; i < list.length; i++) {
        const f = list[i];
        try {
          const url = await uploadOut(f);
          if (!url || String(url).indexOf("/out/") !== 0) continue;
          const id = uid("asset");
          const n = assets().length;
          const node = { id: id, kind: "character", title: f.name.replace(/\.[^.]+$/, ""), x: 220, y: 24 + n * 40, url: url };
          state.nodes.push(node);
          created.push(node);
        } finally {
          state.uploading = Math.max(0, (state.uploading || 1) - 1);
        }
      }
      const shot = nodeById(state.selected);
      if (shot && shot.kind === "shot") {
        created.forEach(function (node) { linkAssetToShot(node, shot); });
      } else if (created.length) {
        selectNode(created[created.length - 1].id);
      }
      renderCards(); drawWires(); renderDock(); persist();
      if (created.length) {
        setMsg("已上传到资产库" + (created.length > 1 ? (" · " + created.length + " 张") : ""), "ok");
      }
      if ($("importModal") && $("importModal").classList.contains("show")) {
        refreshImportLibrary().then(() => renderImportModal());
      }
    } catch (e) {
      setMsg("上传失败：" + ((e && e.message) || e), "bad");
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
    // video→image/text/audio: withdraw leftover 缺首帧 (renderDock would otherwise keep it).
    if (mode !== "video") {
      const msgEl = $("msg");
      const t = (msgEl && msgEl.textContent) || "";
      if (t.indexOf("缺首帧") >= 0) setMsg("");
    }
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
      if (id === "aspect" || id === "res") applyAspectToSize();
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
    if (v == null || v === "") return (fallback === undefined ? null : fallback);
    const n = parseFloat(v);
    if (!Number.isFinite(n)) return (fallback === undefined ? null : fallback);
    return Math.max(0, Math.min(4, n));
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
    const rawStr = (v.strength != null ? v.strength : v.scale);
    const strengthMissing = (rawStr == null || rawStr === "");
    const strength = strengthMissing ? null : clampLoraScale(rawStr, null);
    return {
      air: air,
      path: path,
      downloadUrl: v.downloadUrl || path,
      versionId: v.versionId || loraVersionId(v) || (v.id && /^\d+$/.test(String(v.id)) ? String(v.id) : ""),
      strength: strength,
      scale: strength,
      strengthMissing: strengthMissing,
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
  function loraStrengthInputValue(l) {
    if (!l || l.strengthMissing || (l.strength == null && l.scale == null)) return "";
    const s = clampLoraScale(l.strength != null ? l.strength : l.scale, null);
    return s == null ? "" : String(s);
  }
  function renderLoras() {
    const box = $("loras");
    if (!box) return;
    const be = currentBackend();
    const list = Array.isArray(state.loras) ? state.loras : [];
    box.innerHTML = list.map(function (l, i) {
      const sub = loraChipSubtitle(l);
      const tip = String(l.air || sub || "");
      const needUrl = ((be === "fal" || be === "huggingface" || isNanogptBe()) && !loraHasDirectPath(l))
        || ((be === "modelscope-ai" || be === "modelscope-cn") && !isHfRepo(String(l.path || "").trim()));
      const st = needUrl ? (l.status || "无直链") : (l.status || "");
      const stCls = needUrl || st === "无直链" ? "lora-status bad" : "lora-status";
      const strVal = l.strengthMissing ? "" : loraStrengthInputValue(l);
      return '<div class="lora' + (needUrl ? " need-url" : "") + '" data-lora-i="' + i + '"><div class="top">' +
        '<div class="lora-info"><div class="lora-name">' + esc(l.name || "LoRA") + '</div>' +
        '<div class="lora-air" title="' + esc(tip) + '">' + esc(sub) + '</div>' +
        (st ? '<div class="' + stCls + '">' + esc(st) + '</div>' : '') +
        '</div>' +
        '<input class="lora-str" type="number" step="0.05" min="0" max="2" value="' +
          esc(strVal) +
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
  function providerCaps() {
    const be = currentBackend();
    const fromProv = state._providerCaps && state._providerCaps[be];
    if (fromProv && typeof fromProv === "object") return fromProv;
    return PROVIDER_REF_CAPS[be] || {};
  }
  function catalogCaps() {
    const it = catalogItemForService();
    const caps = (it && it.capabilities && typeof it.capabilities === "object") ? it.capabilities : {};
    const paramCaps = (it && it.parameterCapabilities && typeof it.parameterCapabilities === "object")
      ? it.parameterCapabilities
      : ((caps.parameterCapabilities && typeof caps.parameterCapabilities === "object") ? caps.parameterCapabilities : {});
    const merged = Object.assign({}, providerCaps(), caps, paramCaps);
    if (it) {
      if (it.resolutions && !merged.resolutionTokens) merged.resolutionTokens = it.resolutions;
      if (it.supported_parameters && it.supported_parameters.resolutions && !merged.resolutionTokens) {
        merged.resolutionTokens = it.supported_parameters.resolutions;
      }
    }
    return merged;
  }
  function markOver(el, on) {
    if (!el) return;
    el.classList.toggle("is-over", !!on);
  }
  function setParamWarn(text, bad) {
    const el = $("paramWarn");
    if (!el) return;
    el.textContent = text || "";
    el.className = "param-warn" + (bad && text ? " bad" : "");
  }
  function paramGateMessage() {
    const caps = catalogCaps();
    const msgs = [];
    if ($("service") && $("service").getAttribute("aria-busy") === "true") msgs.push("模型目录加载中，请稍候");
    const selectedShot = nodeById(state.selected);
    const dependency = upstreamImageBlock(selectedShot);
    if (dependency) msgs.push(dependency);
    const needRef = requiredRefMessage(selectedShot);
    if (needRef) msgs.push(needRef);
    const unusedMsg = refUnusedGateMessage(selectedShot);
    if (unusedMsg) msgs.push(unusedMsg);
    const capMsg = refCapGateMessage(selectedShot);
    if (capMsg) msgs.push(capMsg);
    const promptEl = $("prompt");
    const prompt = promptEl ? String(promptEl.value || "") : "";
    const pmax = caps.promptMax;
    if (pmax != null && Number(pmax) > 0 && prompt.length > Number(pmax)) {
      msgs.push("提示词 " + prompt.length + "/" + pmax + " · 超过上限，请缩短后再生成");
      markOver(promptEl, true);
    } else {
      markOver(promptEl, false);
    }
    const seedEl = $("seed");
    const seedRaw = seedEl ? String(seedEl.value || "").trim() : "";
    const seedSpec = caps.seed || {};
    if (seedRaw && seedRaw !== "random" && seedSpec && (seedSpec.min != null || seedSpec.max != null)) {
      const n = Number(seedRaw);
      if (Number.isFinite(n)) {
        const lo = seedSpec.min;
        const hi = seedSpec.max;
        const over = (lo != null && n < lo) || (hi != null && n > hi);
        markOver(seedEl, over);
        if (over) {
          if (seedSpec.clamp === "reject" || seedSpec.clamp === "none") {
            msgs.push("种子 " + n + " 超出范围 " + (lo == null ? "-∞" : lo) + "…" + (hi == null ? "∞" : hi) + "，请改值后再生成（不静默取模）");
          } else {
            msgs.push("种子 " + n + " 超出范围，发送前会按官方规则处理");
          }
        }
      }
    } else {
      markOver(seedEl, false);
    }
    ["width", "height", "steps", "cfg"].forEach(function (id) {
      const el = $(id);
      if (!el || !el.value) { markOver(el, false); return; }
      const n = Number(el.value);
      const lo = el.min !== "" ? Number(el.min) : NaN;
      const hi = el.max !== "" ? Number(el.max) : NaN;
      const over = Number.isFinite(n) && ((Number.isFinite(lo) && n < lo) || (Number.isFinite(hi) && n > hi));
      markOver(el, over);
      if (over) msgs.push(id + " " + n + " 超出 " + (Number.isFinite(lo) ? lo : "") + "…" + (Number.isFinite(hi) ? hi : ""));
    });
    const nano = $("nanoRes");
    if (isNanogptBe() && nano && !nano.value) {
      msgs.push("Nano 需要目录分辨率 token，不能自拼宽高");
      markOver(nano, true);
    } else {
      markOver(nano, false);
    }
    setParamWarn(msgs[0] || "", !!msgs.length);
    return msgs[0] || "";
  }
  function fillNanoResOptions() {
    const sel = $("nanoRes");
    if (!sel) return;
    const caps = catalogCaps();
    const tokens = [].concat(caps.resolutionTokens || caps.resolutions || []);
    const keep = sel.value || "";
    if (!tokens.length) {
      if (keep) ensureSelectOpt(sel, keep);
      return;
    }
    fillSelectOpts(sel, tokens, keep);
  }
  function syncParamSurface() {
    const be = currentBackend();
    const civ = be === "civitai";
    const nano = be === "nano-gpt";
    const vid = state.mode === "video";
    const caps = catalogCaps();
    const falBox = $("falParams");
    const comfyBox = $("comfyParams");
    const nanoBox = $("nanoParams");
    if (falBox) falBox.classList.toggle("hidden", !!civ || !!nano);
    if (comfyBox) comfyBox.classList.toggle("hidden", be === "fal");
    if (nanoBox) nanoBox.classList.toggle("hidden", !nano);
    const sampler = $("sampler");
    const scheduler = $("scheduler");
    const steps = $("steps");
    const cfg = $("cfg");
    const width = $("width");
    const height = $("height");
    const seed = $("seed");
    const neg = $("negative");
    const duration = $("duration");
    const aspect = $("aspect");
    const res = $("res");
    if (sampler) sampler.classList.toggle("hidden", !civ && !caps.sampler);
    if (scheduler) scheduler.classList.toggle("hidden", !civ);
    if (steps) steps.classList.toggle("hidden", !civ);
    if (cfg) cfg.classList.toggle("hidden", !civ);
    if (width) {
      width.disabled = !!nano;
      width.title = nano ? "Nano 提交用目录 resolution token" : "宽";
      width.classList.toggle("hidden", !!nano && !civ);
    }
    if (height) {
      height.disabled = !!nano;
      height.title = nano ? "Nano 提交用目录 resolution token" : "高";
      height.classList.toggle("hidden", !!nano && !civ);
    }
    if (seed) seed.classList.toggle("hidden", false);
    if (neg) {
      const showNeg = caps.negative !== false;
      neg.classList.toggle("hidden", !showNeg);
    }
    if (duration) duration.classList.toggle("hidden", !vid || caps.videoDuration === false);
    if (aspect) aspect.classList.toggle("hidden", caps.videoAspect === false && !vid);
    if (res) res.classList.toggle("hidden", !!nano);
    if (nano) fillNanoResOptions();
    paramGateMessage();
    if (!syncParamSurface._skipDock) renderDock();
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
  // Pack UI params onto generate payload — never silently drop. Civitai keeps
  // sampler/steps/cfg; other backends still ship seed / size / token.
  function packComfyParamsForPayload() {
    const p = readComfyParamsFromUi();
    const be = currentBackend();
    if (be === "nano-gpt") {
      delete p.width;
      delete p.height;
      const token = $("nanoRes") && $("nanoRes").value;
      if (token) p.resolution = token;
    } else if (be === "fal") {
      delete p.sampler;
      delete p.scheduler;
      delete p.steps;
      delete p.cfg;
      delete p.cfgScale;
      delete p.width;
      delete p.height;
    } else if (be !== "civitai") {
      delete p.sampler;
      delete p.scheduler;
      delete p.steps;
      delete p.cfg;
      delete p.cfgScale;
    }
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
      const rawScale = (l.scale != null ? l.scale : l.strength);
      const rawStrength = (l.strength != null ? l.strength : l.scale);
      const missing = !!(l.strengthMissing) || (rawScale == null && rawStrength == null) || rawScale === "" || rawStrength === "";
      const scale = missing ? null : clampLoraScale(rawScale, null);
      const strength = missing ? null : clampLoraScale(rawStrength, null);
      return {
        air: l.air || "",
        path: path,
        url: path,
        downloadUrl: l.downloadUrl || path,
        versionId: versionId,
        scale: scale,
        strength: strength,
        strengthMissing: missing,
        name: l.name || "LoRA",
      };
    }).filter(function (row) {
      if (be === "civitai") return !!(row.air && String(row.air).trim());
      // v0821o: fal outbound needs http path (AIR-only chips would silent-drop in providers/fal.py)
      // v0821o4: huggingface same — _fal_lora_path / _force_loras drop AIR-only
      if (be === "fal" || be === "huggingface") {
        const p = String(row.path || "").trim();
        return !!(p && isHttpUrl(p) && !looksAir(p));
      }
      // v0821o6: Magao outbound is Hub owner/repo only — skip Civitai http / 3231694 / AIR
      if (be === "modelscope-ai" || be === "modelscope-cn") {
        const p = String(row.path || "").trim();
        if (isHttpUrl(p) || looksAir(p) || p.indexOf("3231694") >= 0) return false;
        return isHfRepo(p);
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
    const be = currentBackend();
    if (be === "modelscope-ai" || be === "modelscope-cn") {
      return "魔搭 LoRA 只要 Hub owner/repo，Civitai 下载链不能用";
    }
    if (be === "fal" || be === "huggingface") return "LoRA 缺 http path，无法出站";
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
    if (isModelscopeBe() && isHfRepo(q) && !isHttpUrl(q)) {
      addLora({ path: q, name: q, strength: 0.8 });
      hits.textContent = "";
      return;
    }
    if ((be === "fal" || be === "huggingface" || isNanogptBe()) && (isHttpUrl(q) || isHfRepo(q))) {
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
        const s = clampLoraScale(inp.value, null);
        state.loras[i].strength = s;
        state.loras[i].scale = s;
        state.loras[i].strengthMissing = (s == null);
        persist();
      });
    }
  }

  function svcOptionText(it) {
    const id = (it && (it.id || it.name)) || "";
    const name = (it && it.name) || id;
    if (id === FAL_LORA_PREF_SERVICE) return (name && name !== id ? name + " · " + id : "Krea 2 Turbo LoRA · " + id);
    if (id === HF_LORA_PREF_SERVICE) return (name && name !== id ? name + " · " + id : id);
    if (id === MS_LORA_PREF_SERVICE) return (name && name !== id ? name + " · " + id : "Krea 2 Turbo · " + id);
    return name || id;
  }
  function isModelScopeCatalog() {
    const be = $("backend") && $("backend").value;
    return be === "modelscope-ai" || be === "modelscope-cn";
  }
  function isPagedCatalog() {
    const be = $("backend") && $("backend").value;
    return isModelScopeCatalog() || be === "huggingface";
  }
  function catalogFetchTimeoutMs() {
    return isModelScopeCatalog() ? CATALOG_MODELSCOPE_TIMEOUT_MS : CATALOG_FETCH_TIMEOUT_MS;
  }
  function modelScopeCatalogKey(be, mode, q) {
    return be + ":" + mode + ":" + (q || "");
  }
  function modelScopePageItemId(it) {
    return String((it && (it.id || it.name)) || "");
  }
  function modelScopeWarning(j) {
    const warning = String((j && j.warning) || "").trim();
    const totals = j && j.hubTotals;
    const errors = totals && Number(totals.errors);
    if (warning) return warning;
    if (errors > 0) return "部分 Hub 目录暂时不可用，请重试本页；收录不代表可调用。";
    if (j && j.partial) return "Hub 目录尚未加载完；收录不代表可调用。";
    return "Hub 目录仅表示收录，调用能力以模型契约为准。";
  }
  function syncCatalogPagingUi() {
    const status = $("catalogStatus");
    const hint = $("catalogHint");
    const more = $("catalogMore");
    const retry = $("catalogRetry");
    const p = state.catalogPaging || {};
    if (!status) return;
    const visible = isPagedCatalog() && (p.key || p.loading || p.warning || p.page > 0);
    status.hidden = !visible;
    if (!visible) return;
    const totals = p.hubTotals || {};
    const counts = Number.isFinite(Number(totals.fetched)) ? " · 已取 " + Number(totals.fetched) : "";
    if (hint) {
      hint.textContent = p.loading
        ? "正在加载目录…"
        : (p.warning || "目录已加载 · Hub 收录仅表示目录收录，调用能力以模型契约为准。") + counts;
    }
    if (more) {
      more.hidden = !!p.loading || p.retryPage != null || !p.hasMore;
      more.disabled = !!p.loading;
      more.textContent = p.loading && p.page > 1 ? "加载中…" : "加载更多";
    }
    if (retry) {
      retry.hidden = !!p.loading || p.retryPage == null;
      retry.disabled = !!p.loading;
    }
  }
  function mergeModelScopeItems(items, append) {
    const incoming = filterCatalogForMode(Array.isArray(items) ? items : []);
    const existing = append && Array.isArray(state.catalog) ? state.catalog.slice() : [];
    const seen = {};
    existing.forEach(function (it) { const id = modelScopePageItemId(it); if (id) seen[id] = true; });
    incoming.forEach(function (it) {
      const id = modelScopePageItemId(it);
      // The existing select is ID-valued; collapse same-ID Hub rows even when task differs.
      if (id && !seen[id]) { existing.push(it); seen[id] = true; }
    });
    state.catalog = existing;
    state.catalogById = {};
    existing.forEach(function (it) {
      const id = modelScopePageItemId(it);
      if (id && !state.catalogById[id]) state.catalogById[id] = it;
    });
  }
  function promotePagedCatalogPref(items) {
    const be = $("backend") && $("backend").value;
    const pinId = be === "huggingface"
      ? (state._pinHfLoraService || HF_LORA_PREF_SERVICE)
      : (be === "modelscope-ai" || be === "modelscope-cn")
        ? (state._pinMsLoraService || MS_LORA_PREF_SERVICE)
        : "";
    const list = Array.isArray(items) ? items : [];
    if (!pinId) return list;
    const pinItem = list.find(function (it) { return modelScopePageItemId(it) === pinId; });
    if (!pinItem) return list;
    return [pinItem].concat(list.filter(function (it) { return modelScopePageItemId(it) !== pinId; }));
  }
  function loadPagedCatalog(page, append) {
    const be = $("backend").value;
    const mode = state.mode;
    const category = mode === "video" ? "video" : "image";
    const q = (( $("serviceFilter") && $("serviceFilter").value) || "").trim();
    const baseKey = be + ":" + mode;
    const key = modelScopeCatalogKey(be, mode, q);
    page = Number.isInteger(page) && page > 0 ? page : 1;
    append = !!append;
    const flightKey = key + ":page=" + page;
    if (_catalogFlight && _catalogFlight.key === flightKey) return _catalogFlight.promise;
    const token = ++_catalogToken;
    if (_catalogFlight) _catalogFlight.controller.abort();
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), catalogFetchTimeoutMs());
    const sel = $("service");
    const contextSame = state.catalogPaging && state.catalogPaging.key === key;
    const retrying = contextSame && state.catalogPaging.retryPage === page;
    if (!contextSame || (!append && !retrying)) {
      state.catalog = [];
      state.catalogById = {};
      state._serviceItems = [];
      state.catalogPaging = Object.assign({}, state.catalogPaging, {
        key: key, page: 0, pageSize: CATALOG_PAGE_SIZE, hasMore: false, nextPage: null,
        partial: false, warning: "", retryPage: null, hubTotals: null, hubCoverage: null,
      });
      sel.innerHTML = '<option value="">加载模型目录…</option>';
    }
    state.catalogPaging.key = key;
    state.catalogPaging.loading = true;
    // Keep already loaded rows selectable while a continuation is in flight.
    sel.disabled = !state.catalog.length;
    sel.setAttribute("aria-busy", "true");
    syncCatalogPagingUi();
    const current = () => token === _catalogToken && $("backend").value === be && state.mode === mode &&
      ((($("serviceFilter") && $("serviceFilter").value) || "").trim() === q);
    const params = new URLSearchParams({
      backend: be, category: category, q: q, page: String(page), pageSize: String(CATALOG_PAGE_SIZE),
    });
    const flight = { key: flightKey, promise: null, controller: controller };
    _catalogFlight = flight;
    flight.promise = (async function () {
      try {
        const r = await fetch("/api/catalog?" + params.toString(), { signal: controller.signal });
        if (!r.ok) throw new Error("HTTP " + r.status);
        const j = await r.json();
        if (!current()) return false;
        const rows = Array.isArray(j.items) ? j.items : [];
        mergeModelScopeItems(rows, append || contextSame);
        state.catalog = promotePagedCatalogPref(state.catalog);
        const byId = {};
        state.catalog.forEach(function (it) {
          const id = modelScopePageItemId(it);
          if (id && !byId[id]) byId[id] = it;
        });
        state.catalogById = byId;
        const next = Number.isInteger(j.nextPage) ? j.nextPage : null;
        const retryPage = Number.isInteger(j.retryPage) ? j.retryPage : null;
        state._catalogKey = baseKey;
        state.catalogPaging = Object.assign({}, state.catalogPaging, {
          key: key, page: Number.isInteger(j.page) ? j.page : page,
          pageSize: Number.isInteger(j.pageSize) ? j.pageSize : CATALOG_PAGE_SIZE,
          hasMore: retryPage == null && !!j.hasMore, nextPage: next,
          partial: !!j.partial, warning: modelScopeWarning(j), retryPage: retryPage,
          hubTotals: j.hubTotals || null, hubCoverage: j.hubCoverage || null, loading: false,
        });
        if (!append) {
          const pending = state._pendingService;
          if (pending && byId[pending]) {
            appendServiceOption(sel, byId[pending]);
            sel.value = pending;
          }
          delete state._pendingService;
        }
        renderServiceOptions(state.catalog, "选择模型");
        syncCatalogPagingUi();
        syncParamSurface();
        syncLoraUi();
        return true;
      } catch (e) {
        if (!current()) return false;
        state.catalogPaging = Object.assign({}, state.catalogPaging, {
          loading: false, hasMore: false, nextPage: null, retryPage: page,
          warning: "目录第 " + page + " 页加载失败 · 请重试本页。",
        });
        if (!state.catalog.length) sel.innerHTML = '<option value="">目录加载失败 · 请重试</option>';
        renderServiceOptions(state.catalog, "选择模型");
        syncCatalogPagingUi();
        setMsg("目录加载失败 · " + (e.name === "AbortError" ? "请求超时，请重试本页" : formatErr(e)), "bad");
        return false;
      } finally {
        clearTimeout(timeout);
        if (current()) {
          state.catalogPaging.loading = false;
          sel.disabled = false;
          sel.setAttribute("aria-busy", "false");
          syncCatalogPagingUi();
          paramGateMessage();
        }
        if (_catalogFlight === flight) _catalogFlight = null;
      }
    })();
    return flight.promise;
  }
  function svcMatchBlob(it) {
    const parts = [
      it && it.name, it && it.id, it && it.engine, it && it.operation,
      Array.isArray(it && it.tags) ? it.tags.join(" ") : (it && it.tags),
    ];
    return String(parts.filter(Boolean).join(" ")).toLowerCase();
  }
  function svcAlnum(s) {
    return String(s || "").toLowerCase().replace(/[^a-z0-9\u4e00-\u9fff]+/g, "");
  }
  function appendServiceOption(sel, it) {
    const o = document.createElement("option");
    o.value = (it && (it.id || it.name)) || "";
    o.textContent = svcOptionText(it);
    sel.appendChild(o);
  }
  function renderServiceOptions(items, placeholder) {
    const sel = $("service");
    if (!sel) return;
    const roster = Array.isArray(items) ? items : [];
    state._serviceItems = roster;
    // Hub search is server-paged; filtering a page again hides valid hits.
    const q = isPagedCatalog() ? "" : (($("serviceFilter") && $("serviceFilter").value) || "").trim().toLowerCase();
    const tokens = q ? q.split(/\s+/).filter(Boolean) : [];
    const alnumQ = tokens.map(svcAlnum).filter(function (t) { return t.length >= 2; });
    let shown = roster;
    if (tokens.length) {
      shown = roster.filter(function (it) {
        const blob = svcMatchBlob(it);
        const alnum = svcAlnum(blob);
        return tokens.every(function (t) { return blob.indexOf(t) >= 0; })
          || (alnumQ.length && alnumQ.every(function (t) { return alnum.indexOf(t) >= 0; }));
      });
    }
    const keep = sel.value || "";
    if (_svcChunkHandle) {
      try { cancelAnimationFrame(_svcChunkHandle); } catch (_) {}
      _svcChunkHandle = 0;
    }
    const token = ++_svcChunkToken;
    sel.innerHTML = "";
    const ph = document.createElement("option");
    ph.value = "";
    ph.textContent = placeholder || "选择模型";
    sel.appendChild(ph);
    if (!shown.length && tokens.length) {
      const none = document.createElement("option");
      none.value = "";
      none.disabled = true;
      none.textContent = "无匹配模型：清空搜索后可见全量";
      sel.appendChild(none);
    }
    // Put a real selected row in the synchronous batch, even if it is row 100000.
    // Later rAF chunks must not restore an old selection over an import/user change.
    const pinned = keep && roster.find(function (it) { return (it.id || it.name) === keep; });
    if (pinned) {
      appendServiceOption(sel, pinned);
      shown = shown.filter(function (it) { return (it.id || it.name) !== keep; });
      sel.value = keep;
    }
    function pump(start) {
      if (token !== _svcChunkToken) return;
      const end = Math.min(shown.length, start + (start === 0 ? SERVICE_SYNC_BUDGET : SERVICE_CHUNK_SIZE));
      for (let i = start; i < end; i++) appendServiceOption(sel, shown[i]);
      if (end < shown.length) {
        _svcChunkHandle = requestAnimationFrame(function () { pump(end); });
      } else {
        _svcChunkHandle = 0;
      }
    }
    pump(0);
  }

  function catalogItemForService() {
    const sid = $("service") && $("service").value;
    if (!sid) return null;
    if (state.catalogById && state.catalogById[sid]) return state.catalogById[sid];
    const list = state.catalog || state._serviceItems || [];
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
    // text/audio are stub modes — do not list image models (looks like they work).
    if (state.mode === "text" || state.mode === "audio") return [];
    if (state.mode === "video") return list.filter(catalogItemSupportsI2v);
    if (state.mode === "image") {
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

  function catalogMinInputImages(it) {
    if (!it) return 0;
    if (it.needsSource) return 1;
    const sp = it.supported_parameters || {};
    const maxIn = Number(sp.max_input_images);
    if (!(maxIn > 0)) return 0;
    const id = String(it.id || "").toLowerCase();
    const name = String(it.name || "").toLowerCase();
    if (/(^|\/|-)edit(\/|$)/.test(id) || /(^|[\s\-])edit(\s|$)/.test(name)) return 1;
    return 0;
  }
  function requiredRefMessage(shot) {
    const it = catalogItemForService();
    const minIn = catalogMinInputImages(it);
    if (!minIn) return "";
    const n = countRefUrls(null, shot).length;
    if (n >= minIn) return "";
    const maxIn = Number((it && it.supported_parameters && it.supported_parameters.max_input_images) || 0);
    return "此模型需要 " + minIn + (maxIn ? ("–" + maxIn) : "") + " 张参考图，当前 " + n + " 张。请先连线或上传，不能静默发 0 张";
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
    connectedNodes(shot.id).forEach((n) => {
      if (n && n.url && urls.indexOf(n.url) < 0 && !isVideoUrl(n.url)) urls.push(n.url);
    });
    return urls;
  }

  function refCapGateMessage(shot) {
    if (!shot || shot.kind !== "shot") return "";
    // t2i-with-refs is a different failure (unused), not "cap=1".
    if (refUnusedGateMessage(shot)) return "";
    const nRefs = countRefUrls(null, shot).length;
    const cap = maxRefCount(catalogItemForService());
    if (nRefs > cap) {
      return "参考图 " + nRefs + "/" + cap + " · 超过上限，请减少连线后再生成（不静默丢弃）";
    }
    return "";
  }

  // Explicit catalog.image_to_image === false (Flare/Sunburst t2i): connected
  // refs must hard-block. Never attach them onto a text-to-image body and
  // write back a green "此镜完成" that ignored the product photos.
  // 魔搭 pins ship task/tags even when capabilities is null — Krea-2-Raw is
  // text-to-image. Treating that as maxRefs=1 made「参考图 5/1」look like a
  // provider-wide one-image cut.
  function catalogEatsRefs(it) {
    if (!it) return true;
    const caps = (it.capabilities && typeof it.capabilities === "object") ? it.capabilities : {};
    if (caps.image_to_image === true || caps.inpainting === true) return true;
    if (it.needsSource) return true;
    if (caps.image_to_image === false) return false;
    const backend = String(it.backend || (typeof currentBackend === "function" ? currentBackend() : "") || "").toLowerCase();
    if (backend === "modelscope-ai" || backend === "modelscope-cn" || backend === "modelscope") {
      const task = String(it.task || it.hubTask || "").toLowerCase();
      const tags = Array.isArray(it.tags) ? it.tags.map((t) => String(t).toLowerCase()) : [];
      if (task === "image-to-image" || task === "image-to-video" || tags.indexOf("i2i") >= 0 || tags.indexOf("i2v") >= 0) return true;
      if (task === "text-to-image" || task === "text-to-video" || tags.indexOf("t2i") >= 0 || tags.indexOf("t2v") >= 0) return false;
    }
    return true;
  }
  function editSiblingHint(it) {
    const id = String((it && it.id) || "");
    const editId = id.replace(/\/text-to-image$/, "/edit");
    if (editId !== id && state.catalogById && state.catalogById[editId]) {
      const sib = state.catalogById[editId];
      return "请改选 " + (sib.name || editId) + "，或断开参考连线";
    }
    return "请改选带 Edit 的图生图模型，或断开参考连线";
  }
  function refUnusedGateMessage(shot) {
    if (!shot || shot.kind !== "shot") return "";
    const nRefs = countRefUrls(null, shot).length;
    if (!nRefs) return "";
    const it = catalogItemForService();
    if (catalogEatsRefs(it)) return "";
    const name = (it && (it.name || it.id)) || "当前模型";
    return name + " 是文生图，不吃已连的 " + nRefs + " 张参考图。" + editSiblingHint(it) + "（不静默忽略）";
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
    // Also pick up connected nodes that isImageSource missed (empty kind, odd path).
    connectedNodes(shot.id).forEach((n) => {
      if (n && n.url && urls.indexOf(n.url) < 0 && !isVideoUrl(n.url)) urls.push(n.url);
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

  function sizeFromAspectRes(aspect, resLevel) {
    const p1080 = String(resLevel || "") === "1080P";
    const a = String(aspect || "16:9").replace(/\s/g, "");
    if (a === "1:1") return p1080 ? { width: 1080, height: 1080 } : { width: 720, height: 720 };
    if (a === "9:16") return p1080 ? { width: 1080, height: 1920 } : { width: 720, height: 1280 };
    if (a === "21:9") return p1080 ? { width: 2016, height: 864 } : { width: 1680, height: 720 };
    return p1080 ? { width: 1920, height: 1080 } : { width: 1280, height: 720 };
  }

  function applyAspectToSize() {
    const aspectEl = $("aspect");
    const resEl = $("res");
    if (!aspectEl || !resEl) return;
    const size = sizeFromAspectRes(aspectEl.value, resEl.value);
    if ($("width")) $("width").value = String(size.width);
    if ($("height")) $("height").value = String(size.height);
    writeComfyParamsToShot(nodeById(state.selected));
  }

  function syncAspectFromSize(width, height) {
    const aspectEl = $("aspect");
    const w = Number(width), h = Number(height);
    if (!aspectEl || !Number.isFinite(w) || !Number.isFinite(h) || h <= 0) return;
    const ratio = w / h;
    const choices = [["1:1", 1], ["9:16", 9 / 16], ["21:9", 21 / 9], ["16:9", 16 / 9]];
    let best = choices[0];
    choices.forEach((item) => {
      if (Math.abs(item[1] - ratio) < Math.abs(best[1] - ratio)) best = item;
    });
    if (Math.abs(best[1] - ratio) <= 0.04) aspectEl.value = best[0];
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
    const size = sizeFromAspectRes(aspect, ($("res") && $("res").value) || "720P");
    const comfy = readComfyParamsFromUi();
    const w = Number.isFinite(comfy.width) ? comfy.width : size.width;
    const h = Number.isFinite(comfy.height) ? comfy.height : size.height;
    const res = w + "x" + h;
    const be = ($("backend") && $("backend").value) || "fal";
    // v0820c-hard-service: civitai must not invent Krea2 when #service is empty.
    // Fal empty-service defaults stay for fal backends only.
    const pickedService = ($("service") && $("service").value) || "";
    let serviceId = pickedService;
    if (!serviceId && be === "huggingface") {
      // v0821o4: HF empty → Hub turbo; never fal-ai/.../turbo/lora sibling
      serviceId = HF_LORA_PREF_SERVICE;
    } else if (!serviceId && (be === "modelscope-ai" || be === "modelscope-cn")) {
      // v0821o6: Magao empty → Hub turbo; never fal sibling / 默认模型
      serviceId = MS_LORA_PREF_SERVICE;
    } else if (!serviceId && be !== "civitai") {
      // v0821: i2v must use image-to-video endpoint — plain video-01 drops the frame.
      // v0821o2: LoRAs present → pin turbo/lora (never empty→flux/schnell→flux-lora sibling)
      if (op !== "i2v" && falHasLoras()) serviceId = FAL_LORA_PREF_SERVICE;
      else serviceId = (op === "i2v" ? FAL_I2V_DEFAULT : FAL_T2I_DEFAULT);
    }
    if (be === "huggingface") {
      serviceId = pinHfLoraServiceId(serviceId);
    }
    if (be === "modelscope-ai" || be === "modelscope-cn") {
      serviceId = pinMsLoraServiceId(serviceId);
    }
    if (be === "fal" && op !== "i2v") {
      serviceId = pinFalLoraServiceId(serviceId);
    }
    const genParams = {
      serviceId: serviceId,
    };
    if (be === "civitai") {
      // width/height/steps/cfgScale/sampler/scheduler — seed packed in runShotStep (wire-only compile rule)
      ["width", "height", "steps", "cfgScale", "cfg", "sampler", "scheduler"].forEach(function (k) {
        if (comfy[k] != null) genParams[k] = comfy[k];
      });
      if (genParams.width == null) genParams.width = w;
      if (genParams.height == null) genParams.height = h;
    } else if (be === "nano-gpt") {
      const token = ($("nanoRes") && $("nanoRes").value) || "";
      if (token) genParams.resolution = token;
      else {
        genParams.resolution = res;
        genParams.aspectRatio = aspect;
      }
    } else {
      // Image APIs take width/height. Do not pack canvas duration/aspect/resolution
      // into Fal/HF/MS t2i — those keys 400 when the endpoint schema has no such field.
      if (be === "modelscope-ai" || be === "modelscope-cn" || be === "fal" || be === "huggingface") {
        genParams.width = w;
        genParams.height = h;
      } else {
        genParams.resolution = res;
      }
      if (op === "i2v" || state.mode === "video") {
        const durEl = $("duration");
        if (durEl && !durEl.classList.contains("hidden")) {
          genParams.duration = parseInt(durEl.value || "5", 10) || 5;
        }
        const aspectEl = $("aspect");
        if (aspectEl && !aspectEl.classList.contains("hidden")) {
          genParams.aspectRatio = aspect;
        }
      }
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
    // A generated result belongs to its shot. Only an explicit “入库” click
    // creates a separate canvas asset; normal generation must not duplicate cards.
    if (!shot || !url) return;
    const removed = new Set(state.nodes
      .filter((n) => n.kind !== "shot" && n.fromShot === shot.id && !n.userPromoted)
      .map((n) => n.id));
    if (removed.size) {
      state.nodes = state.nodes.filter((n) => !removed.has(n.id));
      state.edges = state.edges.filter((e) => !removed.has(e.from) && !removed.has(e.to));
    }
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
  function upstreamImageBlock(shot) {
    const ready = refReadyMessage(shot);
    if (ready) return ready;
    if (!shot || shot.kind !== "shot") return "";
    const pending = connectedNodes(shot.id).filter((n) => !isImageSource(n) && (n.kind === "shot" || n.url));
    return pending.length ? ("上游尚无可用图片：" + pending.map((n) => n.title || n.id).join("、") + "，请先生成图片或断开连线") : "";
  }

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
    const dependency = upstreamImageBlock(shot);
    if (dependency) {
      setMsg(prefix + dependency, "bad");
      return { status: "blocked", error: dependency };
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
    const gate = paramGateMessage();
    if (gate) {
      setMsg(prefix + gate, "bad");
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
    const unusedMsg = refUnusedGateMessage(shot);
    if (unusedMsg) {
      setMsg(prefix + unusedMsg, "bad");
      if (!opts.keepSend) markSendBusy(false);
      return { status: "blocked", stageOp: stageOp };
    }
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
        } else if (currentBackend() === "huggingface") {
          const pinned = pinHfLoraServiceId(payload.serviceId || ($("service") && $("service").value) || "");
          payload.serviceId = pinned;
          payload.endpoint = pinned;
          ensureHfLoraServiceSelected();
        } else if (currentBackend() === "modelscope-ai" || currentBackend() === "modelscope-cn") {
          const pinned = pinMsLoraServiceId(payload.serviceId || ($("service") && $("service").value) || "");
          payload.serviceId = pinned;
          payload.endpoint = pinned;
          ensureMsLoraServiceSelected();
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
        // seed: keep full numeric (no int32 clamp) — Civitai seeds can exceed 2^31-1
      }
      // Composer has no negative wire — attach #negative / shot.negativePrompt for every backend.
      const negEl = $("negative");
      const negVal = negEl ? String(negEl.value || "") : "";
      if (shot) shot.negativePrompt = negVal;
      if (negVal) payload.negativePrompt = negVal;
      else if (shot && shot.negativePrompt != null) payload.negativePrompt = shot.negativePrompt;
      else if (payload.negativePrompt == null) payload.negativePrompt = "";
    }
    if (prefix) setMsg(prefix + (stage ? (stage.op + "…") : "请求中…"));
    else setAckMsg(stage ? ("逐步跑 · " + stage.op + "…") : "正在请求云 API…");
    setShotBusy(shot, true);
    shot._error = "";
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
        // Hub image (魔搭 AI) routinely exceeds 100s — keep "? 180 : 40" then extend Hub ticks.
        const isVideoPoll = (state.mode === "video" || (payload && payload.kind === "video") || (stageOp === "i2v"));
        let pollMax = isVideoPoll ? 180 : 40;
        const pollMs = isVideoPoll ? 3000 : 2500;
        const bePoll = currentBackend() || (payload && payload.backend) || "";
        if (!isVideoPoll && (bePoll === "modelscope-ai" || bePoll === "modelscope-cn" || bePoll === "huggingface" || bePoll === "fal")) {
          pollMax = 120;
        }
        for (let i = 0; i < pollMax; i++) {
          if (state.groupRunAbort) {
            setShotBusy(shot, false);
            if (!opts.keepSend) markSendBusy(false);
            return { status: "aborted", stageOp: stageOp };
          }
          await new Promise((res) => setTimeout(res, pollMs));
          const st = await (await fetch("/api/jobs/" + encodeURIComponent(jobId))).json();
          const stStatus = String((st && st.status) || "").toUpperCase();
          const inFlight = stStatus === "IN_QUEUE" || stStatus === "IN_PROGRESS"
            || stStatus === "PENDING" || stStatus === "PROCESSING" || stStatus === "RUNNING";
          if ((st.error || st.status === "failed") && !inFlight) {
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
        shot._error = "";
        shot.url = url;
        writebackResult(shot, url);
        renderCards(); drawWires(); persist();
        setMsg(prefix + (isVideoUrl(url) ? "此镜视频完成，已写入卡片/历史" : "此镜完成，成片已收进资产库"), "ok");
      } else if (url) {
        shot._error = "";
        shot.url = url;
        writebackResult(shot, url);
        renderCards(); drawWires(); persist();
        setMsg(prefix + (isVideoUrl(url) ? "此镜视频完成，已写入卡片/历史" : "此镜完成，成片已收进资产库"), "ok");
      } else {
        setShotBusy(shot, false);
        // v0821m: poll budget exhausted while Fal still IN_PROGRESS ≠ 「已返回无媒体」
        const stillGoing = !!(j && (
          /^(pending|processing|running|in_queue|in_progress)$/i.test(String(j.status || ""))
          || j.status === "IN_QUEUE" || j.status === "IN_PROGRESS"
          || !j.status
        ));
        shot._error = stillGoing
          ? "等待超时，云端任务仍在进行中"
          : "云端已返回，没有可预览地址";
        if (stillGoing) {
          setMsg(prefix + "等待超时，云端任务仍在进行中（可稍后用任务 id 再查）", "warn");
        } else {
          setMsg(prefix + "云端已返回，没有可预览地址", "warn");
        }
        if (!opts.keepSend) markSendBusy(false);
        renderCards();
        renderDock();
        return { status: "blocked", stageOp: stageOp };
      }
    } catch (e) {
      setShotBusy(shot, false);
      shot._error = formatErr(e);
      // v0821k: surface Fal/job.error onto Composer (renderDock must not wipe bad)
      setMsg(prefix + formatErr(e), "bad");
      if (!opts.keepSend) markSendBusy(false);
      renderCards();
      renderDock();
      return { status: "error", stageOp: stageOp, error: formatErr(e) };
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
    const shot = nodeById(state.selected);
    const unusedMsg = refUnusedGateMessage(shot);
    const capMsg = refCapGateMessage(shot);
    const blocked = !!(needFrame || stub || unusedMsg || capMsg);
    let reason = "enabled";
    if (stub) reason = "stub-mode";
    else if (needFrame) reason = "need-frame";
    else if (unusedMsg) reason = "ref-unused";
    else if (capMsg) reason = "ref-over-cap";
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
    const gate = paramGateMessage();
    if (gate) {
      setMsg(gate, "bad");
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
        const errTxt = r.error || r.message || "";
        setMsg(prefix + " · 已停在此镜" + (r.stageOp ? (" · " + r.stageOp) : "") + (errTxt ? (" · " + errTxt) : ""), r.status === "error" ? "bad" : "warn");
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
    const pos = newShotPosition(n);
    state.nodes.push({
      id: id, kind: "shot", title: "分镜" + (n + 1),
      x: pos.x, y: pos.y,
      url: "", firstFrameId: "",
      prompt: "",
    });
    constrainShotsToViewport();
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
  function looksHfServiceId(id) {
    const s = String(id || "").trim();
    if (!s) return false;
    if (looksCivitaiServiceId(s) || looksFalServiceId(s)) return false;
    if (/^hf\//i.test(s) || /^huggingface\//i.test(s)) return true;
    return isHfRepo(s);
  }
  function pinHfLoraServiceId(sid) {
    const s = String(sid || "").trim();
    // Empty / Fal sibling / Civitai image/… → Hub turbo. Never rewrite Hub → fal-ai/.../lora.
    if (!s || looksFalServiceId(s) || looksCivitaiServiceId(s)) return HF_LORA_PREF_SERVICE;
    return s;
  }
  function ensureHfLoraServiceSelected() {
    const be = ($("backend") && $("backend").value) || "";
    if (be !== "huggingface") return;
    const sel = $("service");
    if (!sel) return;
    const want = pinHfLoraServiceId(sel.value || state._pinHfLoraService || "");
    ensureSelectOpt(sel, want);
    for (let i = 0; i < sel.options.length; i++) {
      if (sel.options[i].value === want) {
        const t = sel.options[i].textContent || "";
        if (!t || t === want || t === "默认模型" || t.indexOf(want) < 0) {
          sel.options[i].textContent = "Krea 2 Turbo · " + want;
        }
        break;
      }
    }
    sel.value = want;
    // Do not fabricate a fake catalog row — only pin a real / already-listed id.
    if (state.catalogById && state.catalogById[want]) return;
  }
  function hfLoraFixtureImport() {
    return {
      backend: "huggingface",
      serviceId: "krea/Krea-2-Turbo",
      serviceName: "Krea 2 Turbo",
      kind: "image",
      prompt: "portrait, soft light, detailed face, cinematic",
      loras: [{
        versionId: 3231694,
        path: "https://civitai.com/api/download/models/3231694",
        downloadUrl: "https://civitai.com/api/download/models/3231694",
        url: "https://civitai.com/api/download/models/3231694",
        scale: 0.8,
        strength: 0.8,
        name: "Asian Mix fixture 3231694",
      }],
    };
  }
  async function mountHfLoraFixture() {
    closeImportModal();
    return applyImport(hfLoraFixtureImport());
  }

  function pinMsLoraServiceId(sid) {
    const s = String(sid || "").trim();
    // Empty / Fal sibling / Civitai image/… → Hub turbo. Never rewrite Hub → fal-ai/.../lora.
    if (!s || looksFalServiceId(s) || looksCivitaiServiceId(s)) return MS_LORA_PREF_SERVICE;
    return s;
  }
  function ensureMsLoraServiceSelected() {
    const be = ($("backend") && $("backend").value) || "";
    if (be !== "modelscope-ai" && be !== "modelscope-cn") return;
    const sel = $("service");
    if (!sel) return;
    const want = pinMsLoraServiceId(sel.value || state._pinMsLoraService || "");
    ensureSelectOpt(sel, want);
    for (let i = 0; i < sel.options.length; i++) {
      if (sel.options[i].value === want) {
        const t = sel.options[i].textContent || "";
        if (!t || t === want || t === "默认模型" || t.indexOf(want) < 0) {
          sel.options[i].textContent = "Krea 2 Turbo · " + want;
        }
        break;
      }
    }
    sel.value = want;
    // Do not fabricate a fake catalog row — only pin a real / already-listed id.
    if (state.catalogById && state.catalogById[want]) return;
  }
  function msLoraFixtureImport() {
    // No verified Krea-compatible Hub LoRA is provided by this fixture.
    // Never replace it with an unrelated Z-Image patch or invent a weight.
    return {
      backend: "modelscope-ai",
      serviceId: "krea/Krea-2-Turbo",
      serviceName: "Krea 2 Turbo",
      kind: "image",
      prompt: ($("prompt") && $("prompt").value) || "",
      loras: [],
    };
  }
  async function mountMsLoraFixture() {
    closeImportModal();
    if (!await applyImport(msLoraFixtureImport())) return;
    setMsg("已选择魔搭 Krea 2 Turbo · 未预置 LoRA，请填写与底模兼容的真实 Hub 仓库和权重", "warn");
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
    if (s === "fal-ai/krea-2/turbo" || s === "fal-ai/z-image/turbo" || s === "fal-ai/z-image/turbo/lora") return FAL_LORA_PREF_SERVICE;
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
          sel.options[i].textContent = "Krea 2 Turbo LoRA · " + want;
        }
        break;
      }
    }
    sel.value = want;
    // Do not fabricate a fake catalog row for a missing Krea / Z-Image id.
    if (state.catalogById && state.catalogById[want]) return;
  }

  function falLoraFixtureImport() {
    // Hard-pin — never omit / never fal-ai/flux-lora
    return {
      backend: "fal",
      serviceId: "fal-ai/krea-2/turbo/lora",
      serviceName: "Krea 2 Turbo LoRA",
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
    return applyImport(falLoraFixtureImport());
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
    const pos = newShotPosition(shots().length);
    const n = {
      id: id, kind: "shot", title: "分镜1",
      x: pos.x, y: pos.y, url: "", firstFrameId: "",
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
    const importToken = ++_importToken;
    const civitaiSid = looksCivitaiServiceId(j.serviceId);
    const falSid = looksFalServiceId(j.serviceId);
    const hfSid = looksHfServiceId(j.serviceId);
    const msBe = String(j.backend || "").trim();
    const wantMs = j.backend === "modelscope-ai" || j.backend === "modelscope-cn"
      || msBe === "modelscope" || msBe === "ms" || msBe === "魔搭" || msBe === "魔搭ai" || msBe === "魔搭cn";
    // Explicit backend wins; Magao Hub ids must not steal HF; HF must not fall through to Fal.
    const wantHf = !wantMs && ((j.backend === "huggingface" || j.backend === "hf")
      || (hfSid && j.backend !== "fal" && j.backend !== "civitai"));
    const wantCivitai = !wantMs && !wantHf && ((j.backend === "civitai") || (civitaiSid && j.backend !== "fal"));
    const wantFal = !wantMs && !wantHf && ((j.backend === "fal") || (falSid && j.backend !== "civitai" && !wantCivitai));
    const shot = ensureActiveShotForImport();
    let hardErr = "";
    let heightAligned = false;
    setDockMode("expanded");
    setMsg("正在加载模型目录，目录就绪后才会完成参数导入…");
    // Filter this fetch using the imported mode, not the previous video Composer.
    if (j.kind === "image" || j.kind === "video") state.mode = j.kind;

    if (wantCivitai) {
      if ($("backend")) $("backend").value = "civitai";
      syncParamSurface();
      const sid = String(j.serviceId || "").trim();
      state._pendingService = sid || "";
      if (!await loadCatalog() || importToken !== _importToken) return false;
      if (sid && !importServiceAvailable(sid)) return false;
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
        if (Array.isArray(j.loras) && j.loras.length && (sid === "fal-ai/krea-2/turbo" || sid === "fal-ai/z-image/turbo" || !sid)) {
          sid = FAL_LORA_PREF_SERVICE;
        }
        state._pendingService = sid;
        state._pinFalLoraService = (Array.isArray(j.loras) && j.loras.length) ? sid : (state._pinFalLoraService || "");
        if (!await loadCatalog() || importToken !== _importToken) return false;
        if (!importServiceAvailable(sid)) return false;
        ensureSelectOpt($("service"), sid);
        if ($("service")) {
          // Clear visible label for pinned turbo/lora
          for (let oi = 0; oi < $("service").options.length; oi++) {
            if ($("service").options[oi].value === sid) {
              $("service").options[oi].textContent = (j.serviceName || sid) + " · " + sid;
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
    } else if (wantHf) {
      if ($("backend")) $("backend").value = "huggingface";
      syncParamSurface();
      let sid = String(j.serviceId || "").trim() || HF_LORA_PREF_SERVICE;
      // Forbid drift to Civitai image/… or fal-ai/… (Router has no /lora sibling)
      if (looksCivitaiServiceId(sid) || looksFalServiceId(sid)) {
        hardErr = "Hugging Face 导入拒绝 Fal/Civitai serviceId " + sid + "（请选 krea/Krea-2-Turbo）";
        sid = "";
        state._pinHfLoraService = "";
      }
      state._pendingService = sid;
      if (sid) state._pinHfLoraService = sid;
      if (!await loadCatalog() || importToken !== _importToken) return false;
      if (sid && !importServiceAvailable(sid)) return false;
      if (sid) {
        ensureSelectOpt($("service"), sid);
        if ($("service")) {
          for (let oi = 0; oi < $("service").options.length; oi++) {
            if ($("service").options[oi].value === sid) {
              $("service").options[oi].textContent = (j.serviceName || sid) + " · " + sid;
              break;
            }
          }
          $("service").value = sid;
        }
        if (!$("service") || $("service").value !== sid) {
          hardErr = hardErr || ("无法挂载 Hugging Face 服务 " + sid);
        }
        if (!state.catalogById) state.catalogById = {};
        if (!state.catalogById[sid]) {
          state.catalogById[sid] = { id: sid, name: j.serviceName || sid };
        }
        ensureHfLoraServiceSelected();
      } else if ($("service")) {
        $("service").value = "";
      }
    } else if (wantMs) {
      // AI and CN are separate products — never cross (token/base).
      if (msBe === "modelscope-cn" || msBe === "魔搭cn") {
        if ($("backend")) $("backend").value = "modelscope-cn";
      } else {
        if ($("backend")) $("backend").value = "modelscope-ai";
      }
      syncParamSurface();
      let sid = String(j.serviceId || "").trim() || MS_LORA_PREF_SERVICE;
      if (looksCivitaiServiceId(sid) || looksFalServiceId(sid)) {
        hardErr = "魔搭 导入拒绝 Fal/Civitai serviceId " + sid + "（请选 krea/Krea-2-Turbo）";
        sid = "";
        state._pinMsLoraService = "";
      }
      state._pendingService = sid;
      if (sid) state._pinMsLoraService = sid;
      if (!await loadCatalog() || importToken !== _importToken) return false;
      if (sid && !importServiceAvailable(sid)) return false;
      if (sid) {
        ensureSelectOpt($("service"), sid);
        if ($("service")) {
          for (let oi = 0; oi < $("service").options.length; oi++) {
            if ($("service").options[oi].value === sid) {
              $("service").options[oi].textContent = (j.serviceName || sid) + " · " + sid;
              break;
            }
          }
          $("service").value = sid;
        }
        if (!$("service") || $("service").value !== sid) {
          hardErr = hardErr || ("无法挂载 魔搭 服务 " + sid);
        }
        if (!state.catalogById) state.catalogById = {};
        if (!state.catalogById[sid]) {
          state.catalogById[sid] = { id: sid, name: j.serviceName || sid };
        }
        ensureMsLoraServiceSelected();
      } else if ($("service")) {
        $("service").value = "";
      }
    }

    // Prompt only — never inject @filename from import media (v0817c)
    if (j.prompt != null) {
      const p = String(j.prompt);
      if ($("prompt")) $("prompt").value = p;
      if (shot) shot.prompt = p;
    }
    if (shot && j.negativePrompt != null) shot.negativePrompt = j.negativePrompt || "";
    if ($("negative")) $("negative").value = (j.negativePrompt != null ? j.negativePrompt : (shot && shot.negativePrompt) || "") || "";

    applyComfyParamsToUi(j);
    if ($("width") && $("height")) syncAspectFromSize(Number($("width").value), Number($("height").value));
    if (shot) {
      ["width", "height", "steps", "sampler", "scheduler", "seed"].forEach(function (k) {
        if (j[k] != null) shot[k] = j[k];
        else delete shot[k];
      });
      const cfgVal = j.cfg != null ? j.cfg : j.cfgScale;
      if (cfgVal != null) { shot.cfg = cfgVal; shot.cfgScale = cfgVal; }
      else { delete shot.cfg; delete shot.cfgScale; }
    }
    // Backend may silently align 1672→1664 ((h//16)*16). Surface it; never treat as success-ok.
    {
      const srcH = j.originalHeight != null ? Number(j.originalHeight)
        : (j.sourceHeight != null ? Number(j.sourceHeight)
        : (j.meta && j.meta.height != null ? Number(j.meta.height) : NaN));
      const uiH = ($("height") && $("height").value !== "") ? Number($("height").value)
        : (j.height != null ? Number(j.height) : NaN);
      const alignedH = (j.alignedHeight != null) ? Number(j.alignedHeight)
        : ((Number.isFinite(srcH) && srcH % 16 !== 0) ? Math.floor(srcH / 16) * 16 : NaN);
      const aligned = (j.aligned === true)
        || (Number.isFinite(srcH) && Number.isFinite(uiH) && srcH !== uiH)
        || (Number.isFinite(srcH) && Number.isFinite(alignedH) && alignedH !== srcH)
        || (Number.isFinite(uiH) && uiH === 1664 && Number.isFinite(srcH) && srcH === 1672);
      if (aligned) {
        const fromH = Number.isFinite(srcH) ? srcH : 1672;
        const toH = Number.isFinite(uiH) ? uiH : (Number.isFinite(alignedH) ? alignedH : 1664);
        heightAligned = true;
        setParamWarn("导入高 " + fromH + " 已按 /16 对齐成 " + toH + "，不是原值成功", true);
      }
    }

    // v0821o3: missing loras[] clears chips for Fal and all backends (was wantCivitai-only; reviewer ~3589)
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
    } else {
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
    setMsg("已导入参数" + (nLora ? (" · " + nLora + " 个 LoRA") : " · 未识别 LoRA") + extraTxt + "，自己点生成。", heightAligned ? "warn" : "ok");
    return true;
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
    if ($("btnHfLoraFix")) {
      $("btnHfLoraFix").onclick = function () { mountHfLoraFixture(); };
    }
    if ($("btnMsLoraFix")) {
      $("btnMsLoraFix").onclick = function () { mountMsLoraFixture(); };
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
  bindWorkspace();

  function importServiceAvailable(sid) {
    if (state.catalogById && state.catalogById[sid]) return true;
    setMsg("导入未完成：当前真实目录没有模型 " + sid + "（不会伪造模型行）", "bad");
    return false;
  }

  function loadCatalog() {
    if (isPagedCatalog()) return loadPagedCatalog(1, false);
    const be = $("backend").value;
    const mode = state.mode;
    const key = be + ":" + mode;
    // Boot/import calling the same catalog share the fetch and its completion.
    if (_catalogFlight && _catalogFlight.key === key) return _catalogFlight.promise;
    const token = ++_catalogToken;
    if (_catalogFlight) _catalogFlight.controller.abort();
    const controller = new AbortController();
    // One-shot backends are local/fast; still bound a hung request (same 20s as Hub pages).
    const timeout = setTimeout(() => controller.abort(), catalogFetchTimeoutMs());
    const sel = $("service");
    const sameCatalog = state._catalogKey === key;
    const prevService = sameCatalog ? sel.value : "";
    const current = () => token === _catalogToken && $("backend").value === be && state.mode === mode;
    if (_svcChunkHandle) cancelAnimationFrame(_svcChunkHandle);
    _svcChunkHandle = 0;
    ++_svcChunkToken;
    if (state._catalogKey !== key) {
      state._catalogKey = "";
      state.catalog = [];
      state.catalogById = {};
      state._serviceItems = [];
      sel.innerHTML = '<option value="">加载模型目录…</option>';
      if ($("serviceFilter")) $("serviceFilter").value = "";
    }
    sel.disabled = true;
    sel.setAttribute("aria-busy", "true");
    if (state.catalogPaging) {
      state.catalogPaging.loading = false;
      state.catalogPaging.hasMore = false;
      state.catalogPaging.retryPage = null;
      state.catalogPaging.key = "";
    }
    syncCatalogPagingUi();
    const flight = { key: key, promise: null, controller: controller };
    _catalogFlight = flight;
    flight.promise = (async function () {
      try {
        const r = await fetch("/api/catalog?backend=" + encodeURIComponent(be), { signal: controller.signal });
        if (!r.ok) throw new Error("HTTP " + r.status);
        const j = await r.json();
        if (!current()) return false;
        const roster = j.items || j.models;
        if (!Array.isArray(roster)) throw new Error("目录响应缺少模型列表");
        let items = roster.slice();
      // v0821: mode-filter so video Composer lists i2v services (not silent t2i flux).
      items = filterCatalogForMode(items);
      // CIVITAI_PREF / _civitaiDefaultService = catalog ordering hint only (not generate fallback).
      const pref = (be === "civitai" && state.mode !== "video")
        ? (state._civitaiDefaultService || CIVITAI_PREF_SERVICE)
        : "";
      if (pref) {
        const prefItem = items.find(function (it) { return (it.id || it.name) === pref; });
        if (prefItem) {
          items = [prefItem].concat(items.filter(function (it) { return (it.id || it.name) !== pref; }));
        }
      }
      // Fixture / pending pin stays visible in the FULL roster (no slice(0,60)).
      const providerPin = mode === "video" ? "" : (
        be === "fal" ? state._pinFalLoraService :
        be === "huggingface" ? state._pinHfLoraService :
        (be === "modelscope-ai" || be === "modelscope-cn") ? state._pinMsLoraService : "");
      const pinWant = state._pendingService != null ? state._pendingService
        : (sameCatalog ? prevService : (providerPin || ""));
      const needLoraPin = (be === "fal" && state.mode !== "video" && (
        falHasLoras() || pinWant === FAL_LORA_PREF_SERVICE || pinWant === "fal-ai/krea-2/turbo"
      ));
      if (needLoraPin) {
        const pinId = FAL_LORA_PREF_SERVICE;
        const pinItem = items.find(function (it) { return (it.id || it.name) === pinId; });
        if (pinItem) {
          items = [pinItem].concat(items.filter(function (it) { return (it.id || it.name) !== pinId; }));
        }
      }
      const needHfPin = (be === "huggingface" && mode !== "video" && (
        (Array.isArray(state.loras) && state.loras.length)
        || pinWant === HF_LORA_PREF_SERVICE
        || state._pinHfLoraService
      ));
      if (needHfPin) {
        const pinId = state._pinHfLoraService || HF_LORA_PREF_SERVICE;
        const pinItem = items.find(function (it) { return (it.id || it.name) === pinId; });
        if (pinItem) {
          items = [pinItem].concat(items.filter(function (it) { return (it.id || it.name) !== pinId; }));
        }
      }
      const needMsPin = (mode !== "video" && (be === "modelscope-ai" || be === "modelscope-cn") && (
        (Array.isArray(state.loras) && state.loras.length)
        || pinWant === MS_LORA_PREF_SERVICE
        || state._pinMsLoraService
      ));
      if (needMsPin) {
        const pinId = state._pinMsLoraService || MS_LORA_PREF_SERVICE;
        const pinItem = items.find(function (it) { return (it.id || it.name) === pinId; });
        if (pinItem) {
          items = [pinItem].concat(items.filter(function (it) { return (it.id || it.name) !== pinId; }));
        }
      }
      state.catalog = items;
      const byId = {};
      items.forEach((it) => {
        const id = it.id || it.name || "";
        if (id) byId[id] = it;
      });
      state.catalogById = byId;
      state._catalogKey = key;
      // Select only an actual row, before chunk rendering captures the selection.
      // A missing model is not a one-row synthetic catalog.
      sel.innerHTML = '<option value="">选择模型</option>';
      if (pinWant && byId[pinWant]) appendServiceOption(sel, byId[pinWant]);
      sel.value = byId[pinWant] ? pinWant : "";
      renderServiceOptions(items, "选择模型");
      delete state._pendingService;
      // Do NOT auto-select CIVITAI_PREF when empty — empty stays empty until user/import picks.
      syncParamSurface();
      syncLoraUi();
      if (pinWant && !byId[pinWant]) setMsg("当前目录/模式没有模型 " + pinWant + "，请重新选择（不会替换模型）", "warn");
      return true;
      } catch (e) {
        if (!current()) return false;
        if (state._catalogKey !== key) sel.innerHTML = '<option value="">目录加载失败 · 请重试</option>';
        setMsg("目录加载失败 · " + (e.name === "AbortError" ? "请求超时，请切换 Provider 后重试" : formatErr(e)), "bad");
        return false;
      } finally {
        clearTimeout(timeout);
        if (current()) {
          sel.disabled = false;
          sel.setAttribute("aria-busy", "false");
          paramGateMessage();
        }
        if (_catalogFlight === flight) _catalogFlight = null;
      }
    })();
    return flight.promise;
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
    delete state._pendingService;
    if ($("serviceFilter")) $("serviceFilter").value = "";
    syncParamSurface();
    loadCatalog();
    syncLoraUi();
  };
  if ($("catalogMore")) {
    $("catalogMore").addEventListener("click", function () {
      const p = state.catalogPaging || {};
      if (!isPagedCatalog() || p.loading || p.retryPage != null || !p.hasMore) return;
      loadPagedCatalog(p.nextPage || (p.page + 1), true);
    });
  }
  if ($("catalogRetry")) {
    $("catalogRetry").addEventListener("click", function () {
      const p = state.catalogPaging || {};
      if (!isPagedCatalog() || p.loading || p.retryPage == null) return;
      loadPagedCatalog(p.retryPage, p.retryPage > 1);
    });
  }
  if ($("service")) {
    $("service").addEventListener("change", function () {
      syncLoraUi();
      syncParamSurface();
    });
  }
  if ($("serviceFilter")) {
    let _svcFilterTimer = 0;
    $("serviceFilter").addEventListener("input", function () {
      clearTimeout(_svcFilterTimer);
      _svcFilterTimer = setTimeout(function () {
        if (isPagedCatalog()) loadCatalog();
        else renderServiceOptions(state._serviceItems || state.catalog || [], "选择模型");
      }, 120);
    });
  }
  if ($("negative")) {
    $("negative").addEventListener("input", function () {
      const n = nodeById(state.selected);
      if (n && n.kind === "shot") n.negativePrompt = $("negative").value;
      persist();
    });
  }
  if ($("prompt")) {
    $("prompt").addEventListener("input", function () { paramGateMessage(); });
  }
  if ($("nanoRes")) {
    $("nanoRes").addEventListener("change", function () { persist(); paramGateMessage(); });
  }
  async function loadProviderCaps() {
    try {
      const r = await fetch("/api/providers");
      const j = await r.json();
      const map = {};
      (j.items || []).forEach(function (it) {
        if (it && it.id) map[it.id] = it.capabilities || {};
      });
      state._providerCaps = map;
    } catch (_) {}
  }

  window.addEventListener("resize", () => { drawMinimap(); positionDock(); });

  if (!restore()) loadDemo();
  ensureWorkspaceModel();
  // v0821o2: mount fixture AFTER first catalog fill so #service stays turbo/lora (not 默认模型)
  let _wantFalLoraFixture = false;
  let _wantHfLoraFixture = false;
  let _wantMsLoraFixture = false;
  try {
    const q = String(location.search || "");
    const h = String(location.hash || "");
    if (/[?&]fixture=fal-lora\b/.test(q) || h === "#fal-lora" || h === "#fal-lora-fixture") {
      _wantFalLoraFixture = true;
    }
    if (/[?&]fixture=hf-lora\b/.test(q) || h === "#hf-lora" || h === "#hf-lora-fixture") {
      _wantHfLoraFixture = true;
    }
    if (/[?&]fixture=ms-lora\b/.test(q) || h === "#ms-lora" || h === "#modelscope-lora") {
      _wantMsLoraFixture = true;
    }
  } catch (_) {}
  applyCam();
  syncZoomPresets();
  renderCards();
  drawWires();
  bindLoraUi();
  syncLoraUi();
  syncParamSurface();
  loadProviderCaps().then(function () { return loadComfyDefaults(); }).then(function () { return loadCatalog(); }).then(function () {
    if (_wantFalLoraFixture) return mountFalLoraFixture();
    if (_wantHfLoraFixture) return mountHfLoraFixture();
    if (_wantMsLoraFixture) return mountMsLoraFixture();
  }).then(function () {
    // Imports select after their own catalog completion; no late boot re-pinning.
  });
  loadOuts();
  selectNode(state.selected || "shot-1", { collapsed: true });
  renderWorkspace();
  if (/[?&]probe=1\b/.test(String(location.search || ""))) {
    window.__sbProbe = {
      buildGraph: function () {
        const n = nodeById(state.selected);
        return (n && n.kind === "shot") ? buildGraph(n) : null;
      },
      paramGate: paramGateMessage,
      refCap: function () {
        const n = nodeById(state.selected);
        const hint = document.querySelector(".ref-cap-hint");
        return {
          n: countRefUrls(null, n).length,
          cap: maxRefCount(catalogItemForService()),
          msg: refCapGateMessage(n),
          hint: hint ? String(hint.textContent || "") : "",
          sendReason: $("send") ? $("send").getAttribute("data-reason") : "",
        };
      },
    };
  }
})();
