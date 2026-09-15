(function () {
  const $ = (id) => document.getElementById(id);
  const STORE = "nl-storyboard-v0821o77-fill";
  // v0821o136: structured reverse prompt + text↔shot sync; no invented character library
  const STORE_OLDS = ["nl-storyboard-v0821o16", "nl-storyboard-v0821o15", "nl-storyboard-v0821o14", "nl-storyboard-v0821o13", "nl-storyboard-v0821o12", "nl-storyboard-v0821o7", "nl-storyboard-v0821o6b", "nl-storyboard-v0821o6", "nl-storyboard-v0821o5", "nl-storyboard-v0821o4", "nl-storyboard-v0821o3", "nl-storyboard-v0821o2", "nl-storyboard-v0821o", "nl-storyboard-v0821n5", "nl-storyboard-v0821n4", "nl-storyboard-v0821n3", "nl-storyboard-v0821n2", "nl-storyboard-v0821n", "nl-storyboard-v0821m2", "nl-storyboard-v0821m", "nl-storyboard-v0821l", "nl-storyboard-v0821k", "nl-storyboard-v0821j", "nl-storyboard-v0821i", "nl-storyboard-v0821h", "nl-storyboard-v0821g", "nl-storyboard-v0821f", "nl-storyboard-v0821e", "nl-storyboard-v0821d", "nl-storyboard-v0821c", "nl-storyboard-v0821b", "nl-storyboard-v0821", "nl-storyboard-v0820c", "nl-storyboard-v0820b", "nl-storyboard-v0820", "nl-storyboard-v0819b", "nl-storyboard-v0819", "nl-storyboard-v0818", "nl-storyboard-v0817c", "nl-storyboard-v0817b", "nl-storyboard-v0817", "nl-storyboard-v0816b", "nl-storyboard-v0816", "nl-storyboard-v0815c", "nl-storyboard-v0815b", "nl-storyboard-v0815", "nl-storyboard-v0814", "nl-storyboard-v0813", "nl-storyboard-v0812", "nl-storyboard-v0811", "nl-storyboard-v0810", "nl-storyboard-v0809", "nl-storyboard-v0808", "nl-storyboard-v0807", "nl-storyboard-v0806", "nl-storyboard-v0805", "nl-storyboard-v0804", "nl-storyboard-v0803", "nl-storyboard-v0802", "nl-storyboard-v0798", "nl-storyboard-v0797", "nl-storyboard-v0796", "nl-storyboard-v0793", "nl-storyboard-v0791", "nl-storyboard-v0790"];
  const CIVITAI_PREF_SERVICE = "image/comfy/krea2/turbo/createImage";
  // v0821o123: 故事推演沿用原分镜的家，不再误匹配 qwen2+steps
  // v0821o122: 我的空间画廊；stamp v0821o122-space
  // v0821o117: 九宫格多机位真生成，故事推演出下一镜；stamp v0821o117-nine
  // v0821o116: 九宫/打光/编辑看得见结果；stamp v0821o116-tools
  // v0821o115: 顶栏工具贴着按钮弹出，不再空壳；stamp v0821o115-tools
  // v0821o114: 一个框完整显示，不裁切；stamp v0821o114-full
  // v0821o113: 写字台扁宽条贴分镜下，工具贴上；stamp v0821o113-seko
  // v0821o112: 写字台只贴选中分镜上下，宽跟分镜走；stamp v0821o112-attach
  // v0821o110: 剧本策划/编辑器不带写字台; stamp v0821o110-ws
  // v0821o107: 连线不挡、端口可见; stamp v0821o107-wires
  // v0821o106: 节点可拖，写字台不锁宽高、不改别人坐标; stamp v0821o106-drag
  // v0821o105: 写字台框自适应选中分镜; stamp v0821o105-adapt
  // v0821o104: 点分镜工具贴上、写字台贴下; stamp v0821o104-seko-attach
  // v0821o103: 大屏底栏书桌，↑=生成，无展开; stamp v0821o103-wide-desk
  // v0821o102: Seko 胶囊贴选中分镜，参考图小芯片; stamp v0821o102-seko
  // v0821o101: Composer 底栏重构，不再贴卡; stamp v0821o101-shell
  // v0821o100: 收起贴选中分镜底部；展开无侧位就沉到底栏（o93 desk）; stamp v0821o100-desk
  // v0821o99: 收起条含家+模型；展开高度跟视口；缩放条不再当左墙; stamp v0821o99-capsule-row
  // v0821o98: collapsed 280 + under selected shot, no 420 island, no 胶囊 wrap; stamp v0821o98-capsule-fit
  // v0821o96: 展开抽屉不盖成片、↑不压种子、LoRA 提示只留一行; stamp v0821o96-expand-clean
  // v0821o92: 打光/换机位/超清/消除/文生视频/尾帧 · 点选工具+目录重匹配，不自动生成; stamp v0821o92-seko-fill
  // v0821o91: capsule-on-node + tools-on-select + 九宫格/故事推演; stamp v0821o91-seko-tools
  // v0821o90: cross-house LoRA search + add-then-rematch; stamp v0821o90-cross-lora-search
  // v0821o54b: LoRA rematch pulls full /api/catalog roster like o53d; import chips auto-rematch; stamp v0821o54b-lora-roster-rematch
  // v0821o54: LoRA capability rematch via supportsLora (chips kept + 一键匹配); stamp v0821o54-lora-capability-match
  // v0821o53d: rematch pool = roster+catalog (not only paged catalogById); stamp v0821o53d-capacity-rematch-roster
  // v0821o53c: wire capacity-rematch click + keep pin on capacity-ok endpoint; stamp v0821o53c-capacity-rematch-click
  // v0821o53: capacity rematch when N>maxRefs (catalog eats+cap≥N; no silent unlink); stamp v0821o53-capacity-rematch
  // o53b: Fal empty imageFields→eats=false; editSibling +/image-to-image; link refuse over-cap; N=1 prefer */image-to-image
  // v0821o52: re-inject _pendingService after i2i catalog filter so import mounts t2i; stamp v0821o52-import-pending-survive-i2i
  // v0821o51: remove duplicate const expanded in positionDock (SyntaxError killed whole storyboard.js); stamp v0821o51-fix-expanded-redeclare
  // v0821o49b: hydrate freshness + empty-url merge + pending retire; stamp v0821o49b-hydrate-fresh-empty-url
  // v0821o50: nano LoRA omit null scale (never invent 1.0); tip with o49b
  // v0821o49: harness stamp align (persist/restore + graph); stamp v0821o49-harness-stamp-o48
  // v0821o48: hydrate server shot.url wins over stale localStorage; stamp v0821o48-hydrate-server-wins
  // o49b freshness supersedes blind o48 unconditional win
  // v0821o47: Composer board sync (Magao maxRefs/seed clamp strip) + adapt cache-bust; stamp v0821o47-composer-board-sync
  // v0821o46b: local /out resume when upstream failed (invalid response format); stamp v0821o46b-local-out-resume
  // v0821o46: resume writeback after tab death (pending jobId↔shotId + boot resume); stamp v0821o46-resume-job-writeback
  // v0821o45: Magao Edit-2509 maxRefs=3 (provider ceiling 3; catalog tightens); stamp v0821o45-magao-edit2509-refs3
  // v0821o44: civitai editImage materialize /out → data URL before POST; stamp v0821o44-civitai-edit-materialize-refs
  // v0821o43: fal flux-2/edit OpenAPI maxRefs=4 (siblings with official ≤4); stamp v0821o43-fal-flux2-edit-maxrefs4
  // v0821o42: nano edit refs → imageDataUrls on OAI/edit endpoints; stamp v0821o42-nano-edit-refs
  // v0821o41: fillRefSlotsToCap real /out/fill-cap-{i}.jpg (never phantom o40-fill); stamp v0821o41-fill-real-fixtures
  // v0821o40: 灌满+gate same outbound口径 countRefUrls; 成片 chip visual-only (no 6/5)
  // v0821o39: refs fill-to-cap (expose N==maxRefs empty slots + 灌满测试); t2i+refs one-click apply Edit sibling
  // v0821o38: packComfy prefer generate shot; force payload.diffusionModel from shot; applyImport keep dm/cn/eco when j omits; flux1 without dm hard-reject before POST
  // v0821o37: civitai preparing poll ≥720×2.5s≈30min; stillGoing mirrors inFlight (preparing/scheduled/queued/prepared); saved[]→writeback unchanged
  // v0821o36: checkpoint AIR must not enter loras[] — isLoraAir true only :lora:/:lycoris:/…; false :checkpoint:/:diffusionmodel:/:diffuser:; applyImport+pack drop non-LoRA; never invent strength
  // v0821o35: flux1 diffuser AIR — prefer REST air verbatim (flux1:checkpoint); never hand-roll flux:diffusionmodel; never rewrite checkpoint→diffuser; no companion VAE/CLIP/T5 invent
  // v0821o34: flux import match — pin image/sdcpp/flux1/createImage (flux→flux1); diffusionModel→diffuserModel|model; never keep zImage for Flux
  // v0821o33: HF+Fal /lora → Composer「HF Router 不托管该 Fal LoRA 端点，请换家 Fal」(Path A 不计 HF 分; debug HF_ALLOW_FAL_TRANSPORT only)
  // v0821o32: (superseded for score) Path A Fal key under HF — transport=fal; NOT HF closed-loop
  // v0821o31: HF LoRA AIR base map kept for Fal-sibling hint; o33 does not pin as HF outbound
  // v0821o30: send-gate — #send clickability (z-index/hit); failUi never silent in capsule; unsupported filled = warn-only (keep o28/o29)
  // v0821o29: Fal LoRA endpoint by AIR base (flux1→flux-lora; krea2→krea-2/turbo/lora; else 不支持 — never hard-pin wrong family)
  // v0821o28: Composer field adapt — board show/disable/「不支持」+ strength「未填」(static/composer-field-adapt.js; no Fal pin)
  // v0821o27: import strength — trpc null backfill from REST /api/generation/data (28533344→0.7; never invent)
  // v0821o26: Fal 换家 — pinFal rejects civitai/HF serviceId; #backend sync from /api/providers (all enabled)
  // v0821o25: sdcpp sampleMethod map — import dpmpp_2m → outbound dpm++2m (locked); schedule karras keep
  // v0821o24: capsule/Composer 锚底自适应 — full mode labels; bottom stick; no orphan empty refs
  // v0821o23: import sdxl serviceId sticks on shot + outbound (forbid silent krea2/turbo); prompt-tag LoRA file-stem dedupe
  // v0821o22: hinablue-generic diffusionModel outbound + CDN writeback honesty; UI 参考 count includes 成片 chip
  // v0821o21: outbound fail surfaces jobId+backend; send-path 参考 excludes own shot.url (visual chip aside)
  // v0821o20: selected image chip / compact 未接 / chatRail product copy (visual P0s ASIDE)
  // v0821o19: 双↑→单↑ (capsule #send only); persistServer keepalive; ensure first-frame edges paint
  // v0821o18: P1 chatRail video path on; collapsed keep #send; writeback+i2v first-frame harden
  // v0821o17: node capsule + right chat-rail skeleton; visible wires; i2v first-frame slot actions
  // v0821o16: persistServer skip empty + surface PUT fail; orphan reattach; poll wait saved[] not CDN
  // v0821o15: writeback also PUT /api/storyboard-graph; boot hydrate so clean-profile hard refresh keeps card
  // v0821o14: persist→localStorage + QuotaExceeded warn; restore merge prefer-url (session media not clobbered)
  // v0821o13: writebackResult persists shot.url to localStorage (hard refresh keeps card); dual-read session migrate
  // v0821o12: civitai writeback — pickUrl steps[].output.images; writebackResult sets shot.url; hist-pin applies to card
  // v0821o11: tighten humanizeFailText — drop bare missing&&body.; quoted type:"missing"; poll throws raw
  // v0821o9: Critiquito P1 — Fal fail 中文 humanize; Composer foot sync _error; LoRA 未填·出站按提供方默认
  // v0821o11: deleteNode + 右键菜单 + Delete/Backspace；组用 live pruneGroups
  // v0821o10: mixed LoRA no silent drop; ref cap single-source; model-switch LoRA revalidate
  // v0821o9: LoRA D/E — versionId→AIR, Checkpoint type gate, syncParamChrome, duration gate

  // v0821o8: v0794 caption reverse + 生图; HF catalog t2i+i2i
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
  // v0821n2: LoRA chips without air → red block (no silent omit loras[]); mixed chips also block
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
  // Official Fal LoRA family by Civitai AIR base (urn:air:{base}:lora:…). Never one-shot all chips to krea-2.
  const FAL_FLUX_LORA_SERVICE = "fal-ai/flux-lora";
  const FAL_LORA_BY_BASE = {
    flux1: FAL_FLUX_LORA_SERVICE,
    flux: FAL_FLUX_LORA_SERVICE,
    krea2: FAL_LORA_PREF_SERVICE,
    krea: FAL_LORA_PREF_SERVICE
  };
  const FAL_LORA_FIXTURE_VERSION = "3231694";
  const FAL_LORA_FIXTURE_PATH = "https://civitai.com/api/download/models/3231694";
  const HF_LORA_PREF_SERVICE = "krea/Krea-2-Turbo";
  const HF_I2I_PREF_SERVICE = "Qwen/Qwen-Image-Edit";
  // v0821o31 map kept as Fal-sibling hint only. v0821o33: do NOT pin as HF outbound / HF score.
  const HF_ROUTER_FAL_LORA_MSG = "HF Router 不托管该 Fal LoRA 端点，请换家 Fal";
  const HF_LORA_BY_BASE = {
    flux1: FAL_FLUX_LORA_SERVICE,
    flux: FAL_FLUX_LORA_SERVICE,
    krea2: FAL_LORA_PREF_SERVICE,
    krea: FAL_LORA_PREF_SERVICE
  };

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
  // v0821o136-seko: quantity (数量 1-4) persists per shot like other composer fields.
  const SHOT_COMPOSER_FIELDS = ["prompt", "negative", "duration", "aspect", "res", "nanoRes", "quantity"].concat(COMFY_PARAM_IDS);
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
    { id: "relight", title: "打光", category: "成片工作流", action: "light",
      template: "保持构图与角色，按所选灯位重打光。" },
    { id: "camera-move", title: "换机位", category: "成片工作流", action: "camera",
      template: "同一场同一角色，只换机位与构图。" },
    { id: "upscale-still", title: "超清", category: "成片工作流", action: "upscale",
      template: "upscale, keep identity and composition, no restyle" },
    { id: "erase-obj", title: "消除笔", category: "成片工作流", action: "erase",
      template: "remove the painted object, fill with coherent background" },
    { id: "t2v-plain", title: "文生视频", category: "成片工作流", action: "t2v",
      template: "text-to-video, no first frame required" },
  ];

  const LIGHT_PRESETS = [
    { id: "01", title: "蓝调暮色", prompt: "cinematic blue-hour lighting, cool rim light, dusk atmosphere" },
    { id: "02", title: "伦勃朗", prompt: "Rembrandt lighting, triangle cheek highlight, dramatic chiaroscuro" },
    { id: "03", title: "蝴蝶光", prompt: "butterfly lighting, beauty dish from above, soft glamour" },
    { id: "04", title: "分割光", prompt: "split lighting, half face in shadow, half in hard key" },
    { id: "05", title: "窗光", prompt: "soft window light from camera left, natural falloff, indoor daylight" },
    { id: "06", title: "逆光", prompt: "strong backlight, silhouette rim, volumetric haze" },
    { id: "07", title: "顶光", prompt: "top-down overhead lighting, short shadows, studio grid" },
    { id: "08", title: "侧光", prompt: "hard side light 90 degrees, texture-revealing, film noir" },
    { id: "09", title: "黄金时刻", prompt: "golden hour sunlight, warm low angle, long shadows" },
    { id: "10", title: "霓虹", prompt: "neon nightlife lighting, magenta and cyan practicals, wet street bounce" },
    { id: "11", title: "月光", prompt: "moonlight, cool silver key, low contrast night exterior" },
    { id: "12", title: "三点布光", prompt: "classic three-point lighting, key fill rim, studio portrait" },
  ];
  const CAMERA_PRESETS = [
    { id: "cu", title: "特写", prompt: "close-up shot, face fills the frame, shallow depth of field" },
    { id: "ms", title: "中景", prompt: "medium shot, waist-up, eye-level camera" },
    { id: "ws", title: "全景", prompt: "wide establishing shot, full environment visible" },
    { id: "high", title: "俯视", prompt: "high angle looking down, subject smaller in frame" },
    { id: "low", title: "仰视", prompt: "low angle looking up, heroic perspective" },
    { id: "ots", title: "过肩", prompt: "over-the-shoulder shot, foreground shoulder in frame" },
    { id: "profile", title: "侧拍", prompt: "profile side angle, 90-degree camera" },
    { id: "orbit", title: "环绕", prompt: "subtle orbiting camera, keep subject centered" },
  ];
  const NINE_SETS = {
    camera: [
      { title: "远景", prompt: "extreme wide establishing shot, same person and wardrobe, environment fully visible" },
      { title: "全景", prompt: "full-body long shot, same person and wardrobe, readable space" },
      { title: "中景", prompt: "medium shot waist-up, same person and wardrobe, eye-level" },
      { title: "近景", prompt: "medium close-up chest-up, same person and wardrobe" },
      { title: "特写", prompt: "close-up face fills the frame, same person, shallow depth of field" },
      { title: "仰视", prompt: "low angle looking up, same person and wardrobe, heroic" },
      { title: "俯视", prompt: "high angle looking down, same person and wardrobe" },
      { title: "过肩", prompt: "over-the-shoulder, same person, foreground shoulder in frame" },
      { title: "侧写", prompt: "profile side angle, same person and wardrobe, 90-degree camera" },
    ],
    story: [
      { title: "起幅", prompt: "the beat just before this moment, same person, wider context" },
      { title: "进入", prompt: "character enters the action, same wardrobe, continuous space" },
      { title: "对视", prompt: "eye-line exchange, same person, emotional beat" },
      { title: "动作", prompt: "the key action of this moment continuing, same person" },
      { title: "反应", prompt: "reaction shot, same person, face readable" },
      { title: "细节", prompt: "insert detail that belongs to this scene, keep identity" },
      { title: "环境", prompt: "environment plate of this scene, same lighting" },
      { title: "推进", prompt: "camera pushes in, same person, rising tension" },
      { title: "收幅", prompt: "the moment after, same person, breath and space" },
    ],
    storm: [
      { title: "荷兰角", prompt: "dutch angle, same person and wardrobe, uneasy staging" },
      { title: "鱼眼", prompt: "subtle fisheye, same person, exaggerated space" },
      { title: "剪影", prompt: "silhouette against bright background, same wardrobe" },
      { title: "背面", prompt: "from behind, same person walking into the space" },
      { title: "镜面", prompt: "seen in a reflective surface, same person" },
      { title: "遮挡", prompt: "foreground occlusion, same person, cinematic frame" },
      { title: "顶视", prompt: "top-down bird view, same person in the space" },
      { title: "贴地", prompt: "ground-level camera, same person, large foreground" },
      { title: "远切", prompt: "smash cut to a much wider view, same scene and wardrobe" },
    ],
  };

  const state = {
    cam: { x: 110, y: 28, s: 0.5 },
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
    dockMode: "expanded",
    _overview100: false,
    workspace: "canvas",
    script: { title: "未命名故事", logline: "", scenes: [] },
    editor: { activeShotId: null, playing: false, playIndex: 0, timer: null },
    lastComposerShot: null,
    selectedEdge: null,
    loras: [],
    _serviceItems: [],
    _providerCaps: {},
  };
  const minimapImages = new WeakMap();
  let nodeClipboard = null;
  let nodeMenuPoint = null;

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
  /** Painted result on the shot card itself — count as 参考 when it is an image. */
  function shotResultImageUrl(shot) {
    if (!shot || !shot.url) return "";
    const u = String(shot.url);
    if (isVideoUrl(u) || /\.(mp3|wav|ogg|m4a)(\?|$)/i.test(u)) return "";
    if (shot.kind === "shot" && !isImageSource(shot) && mediaKindOf(u, shot.mode || shot.mediaKind) === "video") return "";
    return u;
  }
  /** UI-only 参考 URLs: send-path refs + own painted card image (does NOT feed unused-ref / attach). */
  function displayRefUrls(shot) {
    const urls = countRefUrls(null, shot).slice();
    const own = shotResultImageUrl(shot);
    if (own && urls.indexOf(own) < 0) urls.push(own);
    return urls;
  }
  function nodeById(id) { return state.nodes.find((n) => n.id === id); }
  const SHOT_BOX_LONG = 640;
  const ASPECT_CHOICES = [["1:1", 1], ["9:16", 9 / 16], ["21:9", 21 / 9], ["16:9", 16 / 9]];
  function scaleShotBox(pw, ph) {
    let w = Number(pw), h = Number(ph);
    if (!Number.isFinite(w) || w <= 0) w = 16;
    if (!Number.isFinite(h) || h <= 0) h = 9;
    if (w >= h) return { w: SHOT_BOX_LONG, h: Math.max(1, Math.round(SHOT_BOX_LONG * h / w)) };
    return { w: Math.max(1, Math.round(SHOT_BOX_LONG * w / h)), h: SHOT_BOX_LONG };
  }
  function shotPixelSize(n) {
    let w = NaN, h = NaN;
    const take = (src) => {
      if (!src) return;
      const sw = Number(src.width);
      const sh = Number(src.height);
      if (Number.isFinite(sw) && sw > 0) w = sw;
      if (Number.isFinite(sh) && sh > 0) h = sh;
    };
    take(n && n.composer && n.composer.fields);
    take(n);
    if (Number.isFinite(w) && w > 0 && Number.isFinite(h) && h > 0) return { w: w, h: h };
    const fields = n && n.composer && n.composer.fields;
    const live = n && n.id === _composerShotId;
    const aspect = (fields && fields.aspect) || (n && n.aspect)
      || (live && $("aspect") && $("aspect").value) || "16:9";
    const res = (fields && fields.res) || (n && n.res)
      || (live && $("res") && $("res").value) || "720P";
    const size = sizeFromAspectRes(aspect, res);
    return { w: size.width, h: size.height };
  }
  function box(n) {
    if (n.kind === "shot") {
      const px = shotPixelSize(n);
      const scaled = scaleShotBox(px.w, px.h);
      if (state._overview100) {
        const cap = 300;
        const ratio = Math.min(1, cap / Math.max(scaled.w, scaled.h));
        return { w: Math.max(1, Math.round(scaled.w * ratio)), h: Math.max(1, Math.round(scaled.h * ratio)) };
      }
      return scaled;
    }
    if (n.kind === "text") return { w: 320, h: 280 };
    return { w: 132, h: 208 };
  }
  function railItemKey(it) {
    if (!it) return "";
    return String(it.url || it.path || it.file || it.name || it.title || "");
  }
  function isJunkRailItem(it) {
    if (!it) return true;
    const url = String(it.url || it.path || "");
    const title = String(it.title || it.file || it.name || "");
    const key = (url + " " + title).toLowerCase();
    if (!url) return true;
    if (it.bytes === 0 || it.size === 0) return true;
    if (/light-preset/i.test(key)) return true;
    if (/(^|\/)dot_[0-9a-f._-]+\.(png|jpe?g|webp|gif)(\?|$)/i.test(url)) return true;
    if (/^dot_/i.test(title)) return true;
    if (/(^|\/)artifact\.(jpe?g|png|webp)(\?|$)/i.test(url)) return true;
    if (/无图占位|尚未生成/.test(title)) return true;
    if (/\/static\/light-preset/i.test(url)) return true;
    return false;
  }
  function assets() { return state.nodes.filter((n) => n.kind !== "shot" && n.kind !== "text"); }
  function railAssets() {
    const seen = {};
    const out = [];
    assets().filter((n) => !isJunkRailItem(n)).forEach((n) => {
      out.push(n);
      if (n.url) seen[n.url] = true;
    });
    shots().forEach((s) => {
      if (!s.url || seen[s.url] || isJunkRailItem(s)) return;
      seen[s.url] = true;
      out.push({ id: s.id, kind: "shot", url: s.url, title: (s.title || "成片") });
    });
    return out;
  }
  function railHistory() { return (state.history || []).filter((h) => !isJunkRailItem(h)); }
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
    if (!state.editor.track) state.editor.track = "picture";
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
  function deleteWorkspaceShot(shotId) {
    const shot = nodeById(shotId);
    if (!shot || shot.kind !== "shot") return;
    if (!window.confirm("删除「" + (shot.title || "分镜") + "」？\n画布节点、所属场次和时间线记录都会删除。")) return;
    deleteNode(shotId);
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
          '<input class="workspace-shot-title" data-shot-title="' + esc(shot.id) + '" value="' + esc(shot.title || "分镜") + '" aria-label="分镜标题">' +
          '<button type="button" class="workspace-icon-btn danger" data-script-act="delete-shot" data-shot-id="' + esc(shot.id) + '" title="删除分镜">删除</button>');
      }).join("") : '<div class="workspace-empty">这场还没有分镜。可以新建分镜，或把已有分镜加入这里。</div>') +
      '</div>' +
      '<div class="workspace-inline"><select data-script-shot-select aria-label="选择已有分镜"><option value="">选择已有分镜</option>' +
      allShots.map((shot) => '<option value="' + esc(shot.id) + '"' + (shot.id === state._scriptShotId ? ' selected' : '') + '>' + esc(shot.title || "分镜") + '</option>').join("") +
      '</select><button type="button" class="workspace-btn" data-script-act="assign-shot"' + (allShots.length ? '' : ' disabled') + '>加入当前场次</button></div>' +
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
    const track = (state.editor && state.editor.track) || "picture";
    const trackTabs = '<div class="editor-tracks" role="tablist" aria-label="编辑器轨道">' +
      '<button type="button" data-editor-track="picture"' + (track === "picture" ? ' class="on"' : "") + '>画面</button>' +
      '<button type="button" data-editor-track="voice"' + (track === "voice" ? ' class="on"' : "") + '>配音</button>' +
      '<button type="button" data-editor-track="music"' + (track === "music" ? ' class="on"' : "") + '>音乐</button></div>';
    const activeFields = !active
      ? '<div class="editor-fields editor-fields-empty">选择一个分镜后，在这里编辑标题、画面提示词和负面提示。</div>'
      : (track === "voice"
        ? '<div class="editor-fields"><label><span>台词 / 配音提示</span><textarea data-editor-field="voicePrompt" placeholder="这一镜的对白、语气、声线">' + esc(active.voicePrompt || "") + '</textarea></label>' +
          (active.voiceUrl ? '<audio controls src="' + esc(active.voiceUrl) + '"></audio>' : '<div class="workspace-note">还没有配音文件。点「上传配音」挂上音频轨，不会偷偷触发生成。</div>') +
          '<button type="button" class="workspace-btn" data-editor-act="upload-voice">上传配音</button></div>'
        : (track === "music"
          ? '<div class="editor-fields"><label><span>音乐提示</span><textarea data-editor-field="musicPrompt" placeholder="这一镜的配乐风格、节奏、乐器">' + esc(active.musicPrompt || "") + '</textarea></label>' +
            (active.musicUrl ? '<audio controls src="' + esc(active.musicUrl) + '"></audio>' : '<div class="workspace-note">还没有音乐文件。点「上传音乐」挂上音频轨。</div>') +
            '<button type="button" class="workspace-btn" data-editor-act="upload-music">上传音乐</button></div>'
          : '<div class="editor-fields"><label><span>镜头标题</span><input data-editor-field="title" value="' + esc(active.title || "分镜") + '"></label>' +
            '<label><span>画面提示词</span><textarea data-editor-field="prompt" placeholder="描述这一镜的主体、动作、构图与光线">' + esc(active.prompt || "") + '</textarea></label>' +
            '<label><span>负面提示</span><textarea data-editor-field="negative" placeholder="可选：不希望出现的内容">' + esc(active.negativePrompt || "") + '</textarea></label></div>'));
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
          '<button type="button" class="workspace-icon-btn danger" data-editor-act="delete-shot" data-shot-id="' + esc(shot.id) + '" title="删除分镜">删除</button>' +
          '</span></div>';
      }).join("");
      return '<div class="workspace-section"><h3>' + esc(scene.title) + '</h3><span class="muted">' + scene.shotIds.length + ' 镜头</span></div>' +
        (rows || '<div class="editor-empty">本场暂无分镜</div>');
    }).join("");
    const editorContent = sequence.length
      ? grouped
      : '<div class="editor-empty editor-empty-action"><strong>时间线还没有分镜</strong><span>先创建一个分镜，再回到这里编排场次、时长和播放顺序。</span><button type="button" class="workspace-btn primary" data-editor-act="add-shot">＋ 新建分镜</button><button type="button" class="workspace-btn" data-editor-act="open-script">去剧本策划</button></div>';
    panel.innerHTML =
      '<div class="workspace-shell"><div class="workspace-top"><div>' +
      '<h1 class="workspace-title" id="editorWorkspaceTitle">编辑器</h1>' +
      '<p class="workspace-subtitle">画面 / 配音 / 音乐三条轨，按场次编排顺序与时长；这里不会偷偷触发生成。</p></div>' +
      '<div class="workspace-actions"><button type="button" class="workspace-btn primary" data-editor-act="play">' + (state.editor.playing ? '暂停播放' : '播放序列') + '</button>' +
      '<button type="button" class="workspace-btn" data-editor-act="next">下一镜</button><button type="button" class="workspace-btn" data-editor-act="open-canvas">打开画布</button></div></div>' +
      '<div class="editor-layout"><div class="workspace-card editor-timeline"><div class="workspace-card-hd"><h2>时间线</h2><span class="muted">' + sequence.length + ' 镜头</span></div>' +
      '<div class="workspace-card-body"><div class="editor-stats"><span>总时长 <strong>' + esc(formatDuration(total)) + '</strong></span><span>已生成 <strong>' + sequence.filter((item) => !!item.shot.url).length + '/' + sequence.length + '</strong></span></div>' +
      '<div class="editor-rows">' + editorContent + '</div></div></div>' +
      '<div class="editor-preview"><div class="editor-preview-head"><strong>' + esc(active ? active.title : "未选择分镜") + '</strong><span class="muted">' + (active ? formatDuration(shotDurationSeconds(active)) : "") + '</span></div>' +
      trackTabs +
      '<div class="editor-preview-media">' + workspaceMedia(active) + '</div>' +
      activeFields +
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
    if (state.workspace !== "canvas") hideShotBar();
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
    state.mode = "image";
    const shot = { id: uid("shot"), kind: "shot", title: "分镜" + (shots().length + 1), x: pos.x, y: pos.y, url: "", firstFrameId: "", prompt: "", mode: "image" };
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
    const shotCount = (doomed.shotIds || []).length;
    const moveNotice = shotCount
      ? "\n其中 " + shotCount + " 个分镜将移动到「" + (fallback.title || "场次") + "」。"
      : "";
    if (!window.confirm("删除「" + (doomed.title || "场次") + "」？" + moveNotice)) return;
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
        setWorkspace("canvas");
        selectNode(state._scriptShotId, { keepClosed: true });
        return;
      }
      const act = e.target.closest("[data-script-act]");
      if (!act) return;
      if (act.dataset.scriptAct === "add-scene") addWorkspaceScene();
      else if (act.dataset.scriptAct === "add-shot") addWorkspaceShot();
      else if (act.dataset.scriptAct === "delete-scene") deleteWorkspaceScene(act.dataset.sceneId);
      else if (act.dataset.scriptAct === "delete-shot") deleteWorkspaceShot(act.dataset.shotId);
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
      const trackBtn = e.target.closest("[data-editor-track]");
      if (trackBtn) {
        state.editor.track = trackBtn.dataset.editorTrack || "picture";
        renderWorkspace();
        persist();
        return;
      }
      const act = e.target.closest("[data-editor-act]");
      if (act) {
        if (act.dataset.editorAct === "play") toggleEditorPlayback();
        else if (act.dataset.editorAct === "next") nextEditorShot();
        else if (act.dataset.editorAct === "open-canvas") setWorkspace("canvas");
        else if (act.dataset.editorAct === "open-script") setWorkspace("script");
        else if (act.dataset.editorAct === "add-shot") addWorkspaceShot();
        else if (act.dataset.editorAct === "delete-shot") deleteWorkspaceShot(act.dataset.shotId);
        else if (act.dataset.editorAct === "upload-voice" || act.dataset.editorAct === "upload-music") {
          state._editorAudioField = act.dataset.editorAct === "upload-voice" ? "voiceUrl" : "musicUrl";
          if ($("file")) $("file").click();
        }
        return;
      }
      const move = e.target.closest("[data-editor-move]");
      if (move) moveEditorShot(move.dataset.shotId, move.dataset.editorMove);
    });
    if (editor) editor.addEventListener("input", (e) => {
      const field = e.target.closest("[data-editor-field]");
      const shot = field && nodeById(state.editor.activeShotId);
      if (!field || !shot) return;
      const key = field.dataset.editorField === "negative" ? "negativePrompt" : field.dataset.editorField;
      shot[key] = field.value;
      if (shot.id === _composerShotId) {
        if ($("prompt")) $("prompt").value = shot.prompt || "";
        if ($("negative")) $("negative").value = shot.negativePrompt || "";
      }
      if (key === "title") renderCards();
      persist();
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
    return connectedNodes(shotId).filter((n) => n && n.kind !== "shot" && n.kind !== "text" && !n.url);
  }
  function refReadyMessage(shot) {
    if ((state.uploading || 0) > 0) return "参考图上传中，请稍等";
    if (!shot) return "";
    const pending = connectedPending(shot.id);
    if (pending.length) return "参考图上传中，请稍等";
    return "";
  }
  function frameAsset(shot) {
    if (!shot) return null;
    const linked = connectedAssets(shot.id);
    if (!shot.firstFrameId) return null;
    const hit = linked.find((a) => a.id === shot.firstFrameId);
    if (hit) return hit;
    // v0821o136seko-healframe: 孤儿 firstFrameId（资产已删）愈合成当前连入的首张图——
    // 连线即引用；只有完全没连图时才清空并交给缺首帧硬门（fail-closed 不变）。
    if (linked.length) { shot.firstFrameId = linked[0].id; return linked[0]; }
    shot.firstFrameId = "";
    return null;
  }
  function lastFrameAsset(shot) {
    if (!shot || !shot.lastFrameId) return null;
    const n = nodeById(shot.lastFrameId);
    if (n && n.url && !isVideoUrl(n.url)) return n;
    return null;
  }
  function sourceTitle(n) {
    if (!n) return "";
    if (n.kind === "shot") return String(n.title || "分镜").replace(/成片$/, "") || "分镜";
    if (n.kind === "text") return n.title || "提示词";
    return n.title || "资产";
  }

  function describePrompt(asset, caption) {
    if (!asset || !asset.url) return "";
    const raw = String(caption || "")
      .split("\n")
      .map((part) => part.trim())
      .filter(Boolean)
      .join("\n");
    if (!raw) return "";
    try {
      if (typeof PromptBible !== "undefined" && PromptBible.formatReversePrompt) {
        return PromptBible.formatReversePrompt(raw);
      }
    } catch (_) {}
    return raw;
  }

  async function captionFromAsset(asset) {
    if (!asset || !asset.url) return "";
    try {
      const r = await fetch("/api/caption", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: asset.url }),
      });
      let j = null;
      try { j = await r.json(); } catch (_) { j = null; }
      if (r.ok) {
        const cap = j && (j.caption || j.text || j.prompt);
        if (cap) return String(cap);
      }
      const err = (j && (j.error || j.message)) || ("视觉打标失败 HTTP " + r.status);
      setMsg(err, "warn");
    } catch (e) {
      setMsg("视觉打标失败：" + ((e && e.message) || e), "warn");
    }
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
      (n) => n.kind === "text" && state.edges.some((e) => e.from === asset.id && e.to === n.id),
    );
    const userCaption = node ? String(node.text || "").trim() : "";
    let visualCaption = "";
    try {
      visualCaption = await captionFromAsset(asset);
    } catch (_) {
      visualCaption = "";
    }
    const text = describePrompt(asset, [userCaption, visualCaption].filter(Boolean).join("\n"));
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
    syncTextToShots(node);
    selectNode(node.id);
    persist();
    return node;
  }

  async function generateFromText(node) {
    if (!node || node.kind !== "text") return;
    const existing = shots();
    let shot = existing.find((s) => state.edges.some((e) => e.from === node.id && e.to === s.id) && !s.url);
    if (!shot) {
      const i = existing.length;
      const pos = typeof newShotPosition === "function" ? newShotPosition(i) : { x: node.x + 420, y: node.y };
      shot = {
        id: uid("shot"),
        kind: "shot",
        title: "分镜" + (i + 1),
        x: pos.x,
        y: pos.y,
        url: "",
        firstFrameId: "",
        prompt: "",
        mode: "image",
      };
      state.nodes.push(shot);
    }
    if (!state.edges.some((e) => e.from === node.id && e.to === shot.id)) {
      state.edges.push({ from: node.id, to: shot.id });
    }
    shot.prompt = node.text || "";
    connectedNodes(node.id).filter(isImageSource).forEach((img) => {
      if (!state.edges.some((e) => e.from === img.id && e.to === shot.id)) {
        state.edges.push({ from: img.id, to: shot.id });
      }
    });
    state.mode = "image";
    selectNode(shot.id, { preserveLayout: true });
    if (typeof fitShotsInView === "function") fitShotsInView();
    if ($("prompt")) $("prompt").value = shot.prompt || "";
    persist();
    if (!$("service") || !$("service").value) {
      await loadCatalog();
    }
    if (!$("service") || !$("service").value) {
      setMsg("生图必须显式选择图片模型，不会用默认假值", "bad");
      renderDock();
      return;
    }
    const item = catalogItemForService();
    const category = String((item && item.category) || "").toLowerCase();
    if (category === "text" || category === "chat") {
      setMsg("当前选中的是文本模型，不能拿去生图。请先切到图片模型", "bad");
      renderDock();
      return;
    }
    await generate();
  }
  function wiredShotsFromText(textId) {
    return state.edges
      .filter((e) => e.from === textId)
      .map((e) => nodeById(e.to))
      .filter((n) => n && n.kind === "shot");
  }
  function wiredTextFromShot(shotId) {
    return state.edges
      .filter((e) => e.to === shotId)
      .map((e) => nodeById(e.from))
      .filter((n) => n && n.kind === "text")[0] || null;
  }
  function syncTextToShots(textNode) {
    if (!textNode || textNode.kind !== "text") return;
    const body = textNode.text || "";
    wiredShotsFromText(textNode.id).forEach(function (shot) {
      shot.prompt = body;
    });
    const shot = typeof composerShot === "function" ? composerShot() : nodeById(state.lastComposerShot);
    if (shot && $("prompt") && wiredShotsFromText(textNode.id).some(function (s) { return s.id === shot.id; })) {
      $("prompt").value = body;
    }
  }
  function syncShotToText(shot) {
    if (!shot || shot.kind !== "shot") return;
    const t = wiredTextFromShot(shot.id);
    if (!t) return;
    t.text = shot.prompt || "";
    const ta = world.querySelector('textarea[data-text][data-id="' + t.id + '"]');
    if (ta && document.activeElement !== ta) ta.value = t.text;
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
    try { syncNodeTools(); } catch (_) {}
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

  // Old sessions could persist UTF-8 bytes decoded as latin1/cp1252 before the
  // static response charset was fixed. Repair only text that decodes to CJK;
  // ids, URLs, and graph references must never be rewritten.
  const CP1252_BYTES = {
    0x20ac: 0x80, 0x201a: 0x82, 0x192: 0x83, 0x201e: 0x84, 0x2026: 0x85,
    0x2020: 0x86, 0x2021: 0x87, 0x2c6: 0x88, 0x2030: 0x89, 0x160: 0x8a,
    0x2039: 0x8b, 0x152: 0x8c, 0x17d: 0x8e, 0x2018: 0x91, 0x2019: 0x92,
    0x201c: 0x93, 0x201d: 0x94, 0x2022: 0x95, 0x2013: 0x96, 0x2014: 0x97,
    0x2dc: 0x98, 0x2122: 0x99, 0x161: 0x9a, 0x203a: 0x9b, 0x153: 0x9c,
    0x17e: 0x9e, 0x178: 0x9f,
  };
  const STORED_ID_KEYS = new Set([
    "id", "from", "to", "url", "path", "key", "source", "kind", "mode",
    "backend", "service", "workspace", "railTab", "activeShotId", "firstFrameId",
    "memberIds", "shotIds", "assetIds", "selected", "selectedEdge",
  ]);

  function storedTextKeyCanChange(key) {
    const name = String(key || "");
    return !STORED_ID_KEYS.has(name) && !/(?:Id|Ids)$/.test(name);
  }

  function mojibakeScore(text) {
    const markers = "ÃÂâåæçèéêëìíîïð";
    let score = 0;
    for (let i = 0; i < text.length; i++) {
      const cp = text.charCodeAt(i);
      if (markers.indexOf(text[i]) >= 0) score += 1;
      if (cp >= 0x80 && cp <= 0x9f) score += 2;
    }
    return score;
  }

  function decodeUtf8Bytes(bytes) {
    try {
      if (typeof TextDecoder === "function") {
        return new TextDecoder("utf-8", { fatal: true }).decode(new Uint8Array(bytes));
      }
    } catch (_) {}
    return "";
  }

  function decodeMojibakeSegment(segment) {
    if (!segment || mojibakeScore(segment) === 0) return segment;
    const latinBytes = [];
    const cp1252Bytes = [];
    for (let i = 0; i < segment.length; i++) {
      const cp = segment.charCodeAt(i);
      if (cp > 0xff && CP1252_BYTES[cp] == null) return segment;
      latinBytes.push(cp);
      cp1252Bytes.push(cp <= 0xff ? cp : CP1252_BYTES[cp]);
    }
    const candidates = [decodeUtf8Bytes(latinBytes), decodeUtf8Bytes(cp1252Bytes)]
      .filter((candidate, index, all) => candidate && all.indexOf(candidate) === index && candidate !== segment)
      .filter((candidate) => /[\u3400-\u9fff]/.test(candidate))
      .sort((a, b) => mojibakeScore(a) - mojibakeScore(b));
    return candidates.length ? candidates[0] : segment;
  }

  function repairMojibakeText(value) {
    if (typeof value !== "string" || !value) return value;
    let output = "";
    let segment = "";
    let changed = false;
    const flush = () => {
      if (!segment) return;
      const repaired = decodeMojibakeSegment(segment);
      output += repaired;
      changed = changed || repaired !== segment;
      segment = "";
    };
    for (let i = 0; i < value.length; i++) {
      const cp = value.charCodeAt(i);
      if (cp <= 0xff || CP1252_BYTES[cp] != null) segment += value[i];
      else {
        flush();
        output += value[i];
      }
    }
    flush();
    return changed ? output : value;
  }

  function repairPersistedText(value, key) {
    if (typeof value === "string") return repairMojibakeText(value);
    if (!value || typeof value !== "object" || !storedTextKeyCanChange(key)) return false;
    let changed = false;
    if (Array.isArray(value)) {
      for (let i = 0; i < value.length; i++) {
        if (typeof value[i] !== "object" || value[i] === null) continue;
        if (repairPersistedText(value[i], key)) changed = true;
      }
      return changed;
    }
    Object.keys(value).forEach((name) => {
      if (!storedTextKeyCanChange(name)) return;
      const current = value[name];
      if (typeof current === "string") {
        const repaired = repairMojibakeText(current);
        if (repaired !== current) {
          value[name] = repaired;
          changed = true;
        }
      } else if (current && typeof current === "object" && repairPersistedText(current, name)) {
        changed = true;
      }
    });
    return changed;
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
      mode: "image",
    }];
    state.edges = [];
    state.mode = "image";
  }

  function isQuotaErr(e) {
    if (!e) return false;
    const name = e.name || "";
    return name === "QuotaExceededError" || name === "NS_ERROR_DOM_QUOTA_REACHED" || e.code === 22 || e.code === 1014;
  }
  function parseStoreRaw(raw) {
    try { return raw ? JSON.parse(raw) : null; } catch (_) { return null; }
  }
  /** Prefer local graph shape; fill missing shot.url from session so local cannot blank newer session media. */
  function mergePreferUrl(localRaw, sessionRaw) {
    const L = parseStoreRaw(localRaw);
    const S = parseStoreRaw(sessionRaw);
    if (!L || !Array.isArray(L.nodes) || !L.nodes.length) return sessionRaw || localRaw || null;
    if (!S || !Array.isArray(S.nodes) || !S.nodes.length) return localRaw || sessionRaw || null;
    const sessById = {};
    for (let i = 0; i < S.nodes.length; i++) {
      const n = S.nodes[i];
      if (n && n.id) sessById[n.id] = n;
    }
    const nodes = L.nodes.map((n) => {
      if (!n || !n.id) return n;
      const o = sessById[n.id];
      if (!o || !o.url || n.url) return n;
      return Object.assign({}, n, { url: o.url });
    });
    return JSON.stringify(Object.assign({}, L, { nodes: nodes }));
  }
  function readStorePair(key) {
    let local = null;
    let session = null;
    try { local = localStorage.getItem(key); } catch (_) {}
    try { session = sessionStorage.getItem(key); } catch (_) {}
    return { local: local, session: session };
  }
  function graphPayload() {
    return JSON.stringify({
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
    });
  }
  function persist() {
    try {
      saveDisplayedComposer();
      // v0821o14: localStorage durable; QuotaExceeded surfaces (not silent); session mirror best-effort.
      const payload = graphPayload();
      try {
        localStorage.setItem(STORE, payload);
      } catch (e) {
        if (isQuotaErr(e)) {
          try { setMsg("本地缓存已满，刷新后可能丢失成片", "warn"); } catch (_) {}
        }
      }
      try { sessionStorage.setItem(STORE, payload); } catch (_) {}
      persistActiveCanvasSoon();
    } catch (_) {}
  }
  /** Apply a parsed graph object into live state. Returns false if empty/robot-demo discarded. */
  function applyGraph(p) {
    if (!p || !p.nodes || !p.nodes.length) return false;
    state.cam = p.cam || state.cam;
    if (state.cam && (state.cam.s == null || state.cam.s < 0.16)) state.cam.s = 0.5;
    state.nodes = p.nodes;
    if (p.selected) state.selected = p.selected;
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
    removeUnpromotedFromShot();
    return true;
  }
  function restore() {
    try {
      let pair = readStorePair(STORE);
      let legacyStorage = false;
      if (!pair.local && !pair.session) {
        for (let i = 0; i < STORE_OLDS.length; i++) {
          pair = readStorePair(STORE_OLDS[i]);
          if (pair.local || pair.session) { legacyStorage = true; break; }
        }
      }
      const raw = mergePreferUrl(pair.local, pair.session);
      const p = parseStoreRaw(raw);
      if (!p || (!Array.isArray(p.nodes) && (!p.script || typeof p.script !== "object"))) return false;
      if (!Array.isArray(p.nodes)) p.nodes = [];
      let repairedStorageText = false;
      try {
        if (typeof repairPersistedText === "function") repairedStorageText = !!repairPersistedText(p);
      } catch (_) {}
      if (p.nodes.length) {
        if (!applyGraph(p)) return false;
      } else {
        // main planner: script-only restore
        state.workspace = p.workspace === "script" || p.workspace === "editor" ? p.workspace : "canvas";
        state.script = p.script && typeof p.script === "object"
          ? p.script
          : { title: "未命名故事", logline: "", scenes: [] };
        state.editor = Object.assign(state.editor || {}, p.editor || {});
        state.editor.timer = null;
        state.editor.playing = false;
        if (p.backend && $("backend")) $("backend").value = p.backend;
        if (p.negative != null && $("negative")) $("negative").value = p.negative;
        state._pendingService = p.service || "";
        state.loras = Array.isArray(p.loras) ? p.loras.map(function (x) { return Object.assign({}, x); }) : (state.loras || []);
      }
      // Re-save under current STORE in localStorage (migrate session/old keys → durable graph).
      try {
        localStorage.setItem(STORE, graphPayload());
      } catch (e) {
        if (isQuotaErr(e)) {
          try { setMsg("本地缓存已满，刷新后可能丢失成片", "warn"); } catch (_) {}
        }
      }
      if ((repairedStorageText || legacyStorage) && typeof persist === "function") {
        try { persist(); } catch (_) {}
      }
      return true;
    } catch (_) { return false; }
  }
  /** v0821o16: shared-studio writeback — skip empty nodes; surface PUT failures on Composer. */
  function persistServer() {
    try {
      const payload = graphPayload();
      let parsed = null;
      try { parsed = JSON.parse(payload); } catch (_) { return; }
      const nodes = parsed && parsed.nodes;
      if (!Array.isArray(nodes) || !nodes.length) {
        try { console.warn("persistServer: skip PUT — nodes empty/missing"); } catch (_) {}
        return;
      }
      // o49b: prefer not sending blank url overwrites (server merge is source of truth)
      const pendingIds = [];
      for (let i = 0; i < nodes.length; i++) {
        const n = nodes[i];
        if (!n || n.kind !== "shot") continue;
        const u = n.url != null ? String(n.url).trim() : "";
        if (!u) {
          try { delete n.url; } catch (_) { n.url = undefined; }
        } else {
          pendingIds.push(n.id);
        }
      }
      for (let i = 0; i < (state.nodes || []).length; i++) {
        const live = state.nodes[i];
        if (!live || live.kind !== "shot") continue;
        if (pendingIds.indexOf(live.id) >= 0) {
          live._pendingPut = true;
          live.pendingPut = true;
        }
      }
      const body = JSON.stringify(parsed);
      persistActiveCanvasSoon();
      if (!isMainHouseGraph()) {
        for (let i = 0; i < (state.nodes || []).length; i++) {
          const live = state.nodes[i];
          if (!live || pendingIds.indexOf(live.id) < 0) continue;
          try { delete live._pendingPut; } catch (_) { live._pendingPut = false; }
          try { delete live.pendingPut; } catch (_) { live.pendingPut = false; }
        }
        return;
      }
      fetch("/api/storyboard-graph", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: body,
        keepalive: true,
      }).then(async function (r) {
        for (let i = 0; i < (state.nodes || []).length; i++) {
          const live = state.nodes[i];
          if (!live || pendingIds.indexOf(live.id) < 0) continue;
          try { delete live._pendingPut; } catch (_) { live._pendingPut = false; }
          try { delete live.pendingPut; } catch (_) { live.pendingPut = false; }
        }
        if (r.ok) return;
        let errText = "";
        try { errText = await r.text(); } catch (_) {}
        try {
          setMsg("服务端保存失败 HTTP " + r.status + (errText ? ": " + errText : ""), "bad");
        } catch (_) {}
      }).catch(function (e) {
        for (let i = 0; i < (state.nodes || []).length; i++) {
          const live = state.nodes[i];
          if (!live || pendingIds.indexOf(live.id) < 0) continue;
          try { delete live._pendingPut; } catch (_) { live._pendingPut = false; }
          try { delete live.pendingPut; } catch (_) { live.pendingPut = false; }
        }
        try {
          setMsg("服务端保存失败: " + (e && e.message ? e.message : String(e || "network")), "bad");
        } catch (_) {}
      });
    } catch (_) {}
  }
  let _canvasAdopted = false;
  let _didFirstSeed = false;
  let _canvasSaveTimer = 0;
  function isMainHouseGraph() {
    return (state.nodes || []).some(function (n) { return n && n.id === "shot-civitai"; });
  }
  function persistActiveCanvasSoon() {
    try { clearTimeout(_canvasSaveTimer); } catch (_) {}
    _canvasSaveTimer = setTimeout(function () { persistActiveCanvas(); }, 450);
  }
  function persistActiveCanvas() {
    const cm = window.canvasManager;
    if (!cm || !cm.activeProject || !cm.activeCanvasId) return Promise.resolve();
    let parsed = { nodes: state.nodes || [], edges: state.edges || [] };
    try { parsed = JSON.parse(graphPayload()); } catch (_) {}
    const body = {
      nodes: parsed.nodes || state.nodes || [],
      edges: parsed.edges || state.edges || [],
      viewport: { x: state.cam.x, y: state.cam.y, zoom: state.cam.s },
    };
    return fetch("/api/canvas-projects/" + encodeURIComponent(cm.activeProject.id) + "/canvases/" + encodeURIComponent(cm.activeCanvasId), {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      keepalive: true,
    }).then(function (r) {
      if (!r || !r.ok) return;
      const canvas = (cm.activeProject.canvases || []).find(function (c) { return c.id === cm.activeCanvasId; });
      if (canvas) {
        canvas.nodes = body.nodes;
        canvas.edges = body.edges;
        canvas.viewport = body.viewport;
      }
    }).catch(function () {});
  }
  window.__sbPersistCanvas = persistActiveCanvas;
  function loadEmptyBoard() {
    state.nodes = [];
    state.edges = [];
    state.groups = [];
    state.selected = null;
    state.multi = [];
    state.script = { title: "未命名故事", logline: "", scenes: [] };
    if (typeof addBlankShot === "function") addBlankShot();
    else {
      const id = uid("shot");
      state.nodes.push({ id: id, kind: "shot", title: "分镜1", x: 560, y: 80, url: "", firstFrameId: "", prompt: "", mode: "image" });
      selectNode(id, { preserveLayout: true });
    }
    state.cam = { x: 110, y: 28, s: 0.5 };
    applyCam();
    renderCards(); drawWires(); renderDock();
    if (typeof renderWorkspace === "function") renderWorkspace();
    persist();
  }
  function syncCanvasChrome() {
    const cm = window.canvasManager;
    const sel = $("canvasSelect");
    const project = cm && cm.activeProject;
    const canvases = (project && project.canvases) || [];
    const cur = (cm && cm.activeCanvasId) || (project && project.activeCanvasId) || "";
    if (sel) {
      sel.innerHTML = canvases.length
        ? canvases.map(function (c) {
            return '<option value="' + esc(c.id) + '"' + (c.id === cur ? " selected" : "") + ">" + esc(c.name || "画布") + "</option>";
          }).join("")
        : '<option value="">暂无画布</option>';
    }
    const title = $("projTitle");
    if (title) {
      const canvas = canvases.find(function (c) { return c.id === cur; });
      title.textContent = (canvas && canvas.name) || (project && project.name) || "未命名故事";
    }
    renderSpaceGrid();
  }
  function canvasCoverUrl(canvas) {
    const nodes = (canvas && canvas.nodes) || [];
    for (let i = 0; i < nodes.length; i++) {
      const n = nodes[i];
      if (n && n.url && String(n.url).trim() && (typeof isVideoUrl !== "function" || !isVideoUrl(n.url))) return n.url;
    }
    return "";
  }
  function fmtSpaceDate(iso) {
    if (!iso) return "";
    const d = new Date(iso);
    if (isNaN(d.getTime())) return "";
    const p = function (n) { return (n < 10 ? "0" : "") + n; };
    return d.getFullYear() + "/" + p(d.getMonth() + 1) + "/" + p(d.getDate()) + " " + p(d.getHours()) + ":" + p(d.getMinutes());
  }
  function renderSpaceGrid() {
    const grid = $("spaceGrid");
    if (!grid) return;
    const cm = window.canvasManager;
    const tab = state._spaceTab === "story" ? "story" : "canvas";
    document.querySelectorAll("[data-space-tab]").forEach(function (btn) {
      btn.classList.toggle("on", btn.getAttribute("data-space-tab") === tab);
    });
    if (tab === "story") {
      const projects = (cm && cm.projects) || [];
      const activeId = cm && cm.activeProject && cm.activeProject.id;
      grid.innerHTML = '<button type="button" class="space-card new" data-space-act="new-project"><span class="space-ph plus">+</span><strong>新建故事</strong><small>一个故事可以有多张画布</small></button>' +
        projects.map(function (p) {
          const cover = ((p.canvases || []).map(canvasCoverUrl).filter(Boolean)[0]) || "";
          return '<button type="button" class="space-card' + (p.id === activeId ? " on" : "") + '" data-space-act="open-project" data-id="' + esc(p.id) + '">' +
            (cover ? '<img src="' + esc(cover) + '" alt="">' : '<span class="space-ph"></span>') +
            "<strong>" + esc(p.name || "未命名故事") + "</strong>" +
            "<small>" + esc(fmtSpaceDate(p.updatedAt || p.createdAt)) + "</small></button>";
        }).join("");
      return;
    }
    const canvases = (cm && cm.activeProject && cm.activeProject.canvases) || [];
    const cur = cm && cm.activeCanvasId;
    grid.innerHTML = '<button type="button" class="space-card new" data-space-act="new-canvas"><span class="space-ph plus">+</span><strong>新建画布</strong><small>空白分镜</small></button>' +
      canvases.map(function (c) {
        const cover = canvasCoverUrl(c);
        return '<article class="space-card' + (c.id === cur ? " on" : "") + '">' +
          '<button type="button" class="space-open" data-space-act="open-canvas" data-id="' + esc(c.id) + '">' +
          (cover ? '<img src="' + esc(cover) + '" alt="">' : '<span class="space-ph"></span>') +
          "</button><strong>" + esc(c.name || "未命名故事") + "</strong>" +
          "<small>" + esc(fmtSpaceDate(c.updatedAt || c.createdAt)) + "</small>" +
          '<span class="space-acts"><button type="button" data-space-act="rename-canvas" data-id="' + esc(c.id) + '">改名</button>' +
          '<button type="button" data-space-act="delete-canvas" data-id="' + esc(c.id) + '">删除</button></span></article>';
      }).join("");
  }
  function openSpace() {
    persistActiveCanvas();
    const home = $("spaceHome");
    const menu = $("titleMenu");
    if (menu) menu.hidden = true;
    if (home) home.hidden = false;
    renderSpaceGrid();
  }
  function closeSpace() {
    const home = $("spaceHome");
    if (home) home.hidden = true;
  }
  function placeTitleMenu() {
    const t = $("projTitle");
    const m = $("titleMenu");
    if (!t || !m) return;
    const r = t.getBoundingClientRect();
    m.style.left = Math.max(12, r.left) + "px";
    m.style.top = (r.bottom + 8) + "px";
  }
  function adoptCanvas(project, canvasId, fresh) {
    _canvasAdopted = true;
    const id = canvasId || (project && project.activeCanvasId) || "";
    const canvas = project && (project.canvases || []).find(function (c) { return c.id === id; });
    syncCanvasChrome();
    if (fresh) {
      _canvasAdopted = true;
      loadEmptyBoard();
      persistActiveCanvas();
      closeSpace();
      setMsg("已新建空白画布 · " + ((canvas && canvas.name) || "画布"), "ok");
      return;
    }
    const nodes = (canvas && canvas.nodes) || [];
    if (nodes.length) {
      _canvasAdopted = true;
      const vp = (canvas && canvas.viewport) || {};
      applyGraph({
        nodes: nodes,
        edges: (canvas && canvas.edges) || [],
        cam: { x: Number(vp.x) || 0, y: Number(vp.y) || 0, s: Number(vp.zoom) || 0.5 },
      });
      renderCards(); drawWires(); renderDock();
      if (typeof renderWorkspace === "function") renderWorkspace();
      persist();
      if (typeof fitShotsInView === "function") fitShotsInView();
      closeSpace();
      return;
    }
    if (!_didFirstSeed && shots().length) {
      _didFirstSeed = true;
      _canvasAdopted = true;
      persistActiveCanvas();
      return;
    }
    _canvasAdopted = true;
    loadEmptyBoard();
  }
  function bindCanvasBoard() {
    const root = $("canvasManager");
    if (root && !root._sbBound) {
      root._sbBound = true;
      root.addEventListener("canvas-manager:change", function (ev) {
        const d = (ev && ev.detail) || {};
        const cm = window.canvasManager;
        const fresh = !!(cm && cm._freshEmpty);
        if (cm) cm._freshEmpty = false;
        adoptCanvas(d.project, d.canvasId, fresh);
      });
    }
    if ($("btnNewCanvas") && !$("btnNewCanvas")._sbBound) {
      $("btnNewCanvas")._sbBound = true;
      $("btnNewCanvas").onclick = function () {
        const cm = window.canvasManager;
        if (!cm) { setMsg("画布管理还没就绪", "warn"); return; }
        Promise.resolve()
          .then(function () { return cm.activeProject ? null : cm.createProject("未命名项目"); })
          .then(function () { return cm.createCanvas(); })
          .catch(function (e) { setMsg((e && e.message) || "新建画布失败", "bad"); });
      };
    }
    if ($("canvasSelect") && !$("canvasSelect")._sbBound) {
      $("canvasSelect")._sbBound = true;
      $("canvasSelect").addEventListener("change", function (e) {
        const cm = window.canvasManager;
        if (!cm || !e.target.value) return;
        cm.setActiveCanvas(e.target.value).catch(function (err) {
          setMsg((err && err.message) || "切换画布失败", "bad");
        });
      });
    }
    if ($("projTitle") && !$("projTitle")._sbBound) {
      $("projTitle")._sbBound = true;
      const toggleTitleMenu = function (e) {
        e.stopPropagation();
        const menu = $("titleMenu");
        if (!menu) return;
        menu.hidden = !menu.hidden;
        if (!menu.hidden) placeTitleMenu();
      };
      $("projTitle").addEventListener("click", toggleTitleMenu);
      const logo = document.querySelector("header .logo");
      if (logo) logo.addEventListener("click", toggleTitleMenu);
    }
    if ($("btnOpenSpace") && !$("btnOpenSpace")._sbBound) {
      $("btnOpenSpace")._sbBound = true;
      $("btnOpenSpace").onclick = function (e) {
        e.stopPropagation();
        openSpace();
      };
    }
    document.addEventListener("click", function (e) {
      const menu = $("titleMenu");
      if (!menu || menu.hidden) return;
      if (e.target.closest && e.target.closest("#titleMenu, #projTitle")) return;
      menu.hidden = true;
    });
    const space = $("spaceHome");
    if (space && !space._sbBound) {
      space._sbBound = true;
      space.addEventListener("click", function (e) {
        const tab = e.target.closest && e.target.closest("[data-space-tab]");
        if (tab) {
          state._spaceTab = tab.getAttribute("data-space-tab") === "story" ? "story" : "canvas";
          renderSpaceGrid();
          return;
        }
        const actEl = e.target.closest && e.target.closest("[data-space-act]");
        if (!actEl) return;
        const act = actEl.getAttribute("data-space-act");
        const id = actEl.getAttribute("data-id");
        const cm = window.canvasManager;
        if (!cm) return;
        if (act === "new-canvas") {
          Promise.resolve(cm.activeProject ? null : cm.createProject("未命名故事"))
            .then(function () { return cm.createCanvas("未命名故事"); })
            .catch(function (err) { setMsg((err && err.message) || "新建画布失败", "bad"); });
          return;
        }
        if (act === "new-project") {
          cm.createProject("未命名故事").then(function () { renderSpaceGrid(); })
            .catch(function (err) { setMsg((err && err.message) || "新建故事失败", "bad"); });
          return;
        }
        if (act === "open-canvas" && id) {
          cm.setActiveCanvas(id).then(function () { closeSpace(); })
            .catch(function (err) { setMsg((err && err.message) || "打开画布失败", "bad"); });
          return;
        }
        if (act === "open-project" && id) {
          cm.selectProject(id).then(function () {
            state._spaceTab = "canvas";
            renderSpaceGrid();
          }).catch(function (err) { setMsg((err && err.message) || "打开故事失败", "bad"); });
          return;
        }
        if (act === "rename-canvas" && id) {
          const name = window.prompt("画布名称") || "";
          if (name) cm.renameCanvas(id, name).then(renderSpaceGrid)
            .catch(function (err) { setMsg((err && err.message) || "改名失败", "bad"); });
          return;
        }
        if (act === "delete-canvas" && id) {
          if (!window.confirm("删除这张画布？")) return;
          cm.deleteCanvas(id).then(renderSpaceGrid)
            .catch(function (err) { setMsg((err && err.message) || "删除失败", "bad"); });
        }
      });
    }
  }
  bindCanvasBoard();

  function shotsHaveMedia() {
    return (state.nodes || []).some(function (n) { return n && n.kind === "shot" && n.url; });
  }
  /** Clean profile / empty demo: adopt server graph.
   * o49b freshness supersedes blind o48 unconditional win:
   * keep local when pendingPut / newer urlUpdatedAt / local media newer than server;
   * adopt server when local url empty OR local clearly stale (no pending, older/missing mtime).
   * Server still wins when fresher (belt writeback survives hard refresh).
   */
  function shotUrlMtime(n) {
    if (!n) return 0;
    const v = (n._urlUpdatedAt != null && n._urlUpdatedAt !== "") ? n._urlUpdatedAt
      : ((n.urlUpdatedAt != null && n.urlUpdatedAt !== "") ? n.urlUpdatedAt : 0);
    if (v === 0 || v == null || v === "") return 0;
    const t = typeof v === "number" ? v : Date.parse(String(v));
    return Number.isFinite(t) ? t : 0;
  }
  async function hydrateFromServer() {
    try {
      const r = await fetch("/api/storyboard-graph");
      if (!r.ok) return false;
      const j = await r.json();
      const p = j && (j.graph || j);
      if (!p || !Array.isArray(p.nodes) || !p.nodes.length) return false;
      if (!shotsHaveMedia()) {
        if (!applyGraph(p)) return false;
        persist();
        return true;
      }
      const serverShotN = p.nodes.filter(function (n) { return n && n.kind === "shot"; }).length;
      if (serverShotN > shots().length) {
        if (!applyGraph(p)) return false;
        persist();
        return true;
      }
      const byId = {};
      for (let i = 0; i < p.nodes.length; i++) {
        const n = p.nodes[i];
        if (n && n.id) byId[n.id] = n;
      }
      let changed = false;
      for (let i = 0; i < state.nodes.length; i++) {
        const n = state.nodes[i];
        if (!n || n.kind !== "shot") continue;
        const o = byId[n.id];
        if (!o) continue;
        const serverUrl = o.url != null ? String(o.url).trim() : "";
        if (!serverUrl) continue;
        const localUrl = n.url != null ? String(n.url).trim() : "";
        if (!localUrl) {
          n.url = serverUrl;
          const stm = shotUrlMtime(o);
          if (stm) {
            n._urlUpdatedAt = o._urlUpdatedAt != null ? o._urlUpdatedAt : o.urlUpdatedAt;
            n.urlUpdatedAt = n._urlUpdatedAt;
          }
          changed = true;
          continue;
        }
        if (localUrl === serverUrl) continue;
        // Keep local: pending PUT in flight
        if (n._pendingPut || n.pendingPut) continue;
        const localTs = shotUrlMtime(n);
        const serverTs = shotUrlMtime(o);
        // Keep local when newer than server, or local has mtime and server looks older/missing
        if (localTs > serverTs) continue;
        if (localTs > 0 && serverTs === 0) continue;
        // Adopt server when fresher, or both missing mtime (stale LS → server wins when fresher/unknown)
        n.url = serverUrl;
        if (serverTs) {
          n._urlUpdatedAt = o._urlUpdatedAt != null ? o._urlUpdatedAt : o.urlUpdatedAt;
          n.urlUpdatedAt = n._urlUpdatedAt;
        }
        changed = true;
      }
      if (changed) persist();
      return changed;
    } catch (_) {
      return false;
    }
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
  function modeLabelOf(mode) {
    if (mode === "video") return "视频生成";
    if (mode === "text") return "文本生成";
    if (mode === "audio") return "音频生成";
    return "图片生成";
  }
  function portPos(n, side) {
    const b = box(n);
    const y = n.y + b.h / 2;
    return side === "out" ? { x: n.x + b.w, y: y } : { x: n.x, y: y };
  }

  function canLink(src, dst) {
    if (!src || !dst || src.id === dst.id) return false;
    if (dst.kind === "text") return isImageSource(src);
    if (dst.kind !== "shot") return false;
    if (src.kind === "text") return true;
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

  let _houseLock = { be: "", shotId: "", until: 0 };
  function lockHouse(be) {
    const shot = (typeof composerShot === "function" ? composerShot() : null) || nodeById(state.selected);
    _houseLock = { be: String(be || ""), shotId: (shot && shot.id) || "", until: Date.now() + 8000 };
  }
  function honorHouseLock() {
    if (!_houseLock.be || Date.now() > _houseLock.until) return false;
    const shot = (typeof composerShot === "function" ? composerShot() : null) || nodeById(state.selected);
    if (_houseLock.shotId && shot && shot.id && shot.id !== _houseLock.shotId) return false;
    if (shot && shot.kind === "shot") {
      shot.backend = _houseLock.be;
      if (!shot.composer) shot.composer = {};
      shot.composer.backend = _houseLock.be;
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
    persistShotFrame(shot);
  }

  function activateShotComposer(shot) {
    honorHouseLock();
    const id = shot && shot.kind === "shot" ? shot.id : null;
    const recipe = shot && shot.composer;
    const wantKey = recipe ? (recipe.backend + ":" + (state.mode === "video" || state.mode === "text" || state.mode === "audio" ? state.mode : (recipe.mode || "image"))) : "";
    if (_composerShotId === id) {
      if (id && $("backend") && $("backend").value) {
        const liveBe = $("backend").value;
        shot.backend = liveBe;
        if (!recipe) shot.composer = snapshotComposer();
        else recipe.backend = liveBe;
      }
      if (id && wantKey && (state._catalogKey !== wantKey)) {
        state._pendingService = (recipe && recipe.service) || shot.serviceId || "";
        loadCatalog();
      }
      return;
    }
    saveDisplayedComposer();
    _composerShotId = id;
    if (!id) return;
    if (shot.composer) {
      const recipe = shot.composer;
      const key = recipe.backend + ":" + recipe.mode;
      state.mode = recipe.mode;
      if (!(honorHouseLock() && _houseLock.be)) {
        $("backend").value = recipe.backend;
      }
      state.loras = JSON.parse(JSON.stringify(recipe.loras || []));
      Object.keys(recipe.fields || {}).forEach((field) => {
        const el = $(field);
        if (!el || SHOT_COMPOSER_FIELDS.indexOf(field) < 0) return;
        if (el.tagName === "SELECT") ensureSelectOpt(el, recipe.fields[field]);
        el.value = recipe.fields[field];
      });
      if (state._catalogKey !== key || _catalogFlight) {
        state._pendingService = recipe.service || shot.serviceId || "";
        loadCatalog();
      } else {
        $("service").value = "";
        if (recipe.service && state.catalogById[recipe.service]) {
          ensureSelectOpt($("service"), recipe.service);
        } else if (shot.serviceId && state.catalogById[shot.serviceId]) {
          ensureSelectOpt($("service"), shot.serviceId);
        }
      }
    } else {
      state.mode = (shot.mode === "video" || shot.mode === "text" || shot.mode === "audio") ? shot.mode : "image";
      state.loras = Array.isArray(shot.loras) ? JSON.parse(JSON.stringify(shot.loras)) : [];
      if ($("service")) $("service").value = shot.serviceId || "";
      applyComfyParamsToUi(shot);
      if (shot.aspect && $("aspect")) $("aspect").value = shot.aspect;
      if (shot.res && $("res")) $("res").value = shot.res;
      if (!(shot.serviceId || (shot.composer && shot.composer.service))) {
        try { Promise.resolve(smartMatchService({ announce: true })).catch(function () {}); } catch (_) {}
      }
    }
    const restoredW = $("width") ? parseInt($("width").value, 10) : NaN;
    const restoredH = $("height") ? parseInt($("height").value, 10) : NaN;
    if (Number.isFinite(restoredW) && restoredW > 0 && Number.isFinite(restoredH) && restoredH > 0) {
      syncAspectFromSize(restoredW, restoredH);
    } else {
      applyAspectToSize();
    }
  }

  function createLinkedShot(link, point) {
    const origin = nodeById(link.from);
    if (!origin || !Number.isFinite(point.x) || !Number.isFinite(point.y)) return null;
    const recipe = snapshotComposer();
    const titleSet = new Set(shots().map((shot) => shot.title));
    let number = 1;
    while (titleSet.has("分镜" + number)) number++;
    const comfy = readComfyParamsFromUi();
    const b = scaleShotBox(comfy.width, comfy.height);
    const shot = Object.assign({}, comfy, {
      id: uid("shot"), kind: "shot", title: "分镜" + number,
      x: point.x - (link.side === "in" ? b.w : 0), y: point.y - b.h / 2,
      url: "", firstFrameId: "", prompt: recipe.fields.prompt || "",
      negativePrompt: recipe.fields.negative || "", mode: recipe.mode,
      aspect: recipe.fields.aspect, res: recipe.fields.res,
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
      ".card,.dock,.tools,.zoom,.picker,.rail,.atbox,.skillbox,header,.ghost,.minimap,.import-backdrop,.selbar,.shot-bar,.group-bound,path.edge"));
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
        if (n.kind !== "shot" && n.kind !== "text") return;
        side = "in";
        src = from;
        dst = n;
      } else {
        if (from.kind !== "shot" && from.kind !== "text") return;
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
      const d = bezier(p1.x, p1.y, p2.x, p2.y);
      parts.push('<path class="edge-glow" d="' + d + '" fill="none" />');
      parts.push('<path class="edge" data-ei="' + i + '" d="' + d +
        '" fill="none" stroke="#e8edf4" stroke-width="2.6" vector-effect="non-scaling-stroke" />');
    });
    if (state.link && state.link.x2 != null) {
      const snap = state.snapTarget;
      const cls = snap ? "snap" : "live";
      const x2 = snap ? snap.x : state.link.x2;
      const y2 = snap ? snap.y : state.link.y2;
      parts.push('<path class="' + cls + '" d="' + bezier(state.link.x1, state.link.y1, x2, y2) +
        '" fill="none" stroke="#ffffff" stroke-width="2.6" />');
    }
    if (wires) {
      wires.style.overflow = "visible";
      wires.style.zIndex = "4";
      wires.innerHTML = parts.join("");
      const xs = state.nodes.map((n) => n.x + box(n).w + 400);
      const ys = state.nodes.map((n) => n.y + box(n).h + 400);
      wires.setAttribute("width", String(Math.max(2400, xs.length ? Math.max.apply(null, xs) : 2400)));
      wires.setAttribute("height", String(Math.max(2400, ys.length ? Math.max.apply(null, ys) : 2400)));
    }
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
    if (n.kind === "text") {
      return '<div class="card text' + sel + multi + '" data-id="' + esc(n.id) + '" style="left:' + n.x + 'px;top:' + n.y + 'px">' +
        '<div class="label">✎ ' + esc(n.title || "提示词") + "</div>" +
        '<textarea class="editor" data-text data-id="' + esc(n.id) + '" placeholder="反推或手写提示词…">' +
        esc(n.text || "") + "</textarea>" +
        '<div class="acts">' +
        '<button type="button" data-textact="rev" data-id="' + esc(n.id) + '">反推</button>' +
        '<button type="button" data-textact="gen" data-id="' + esc(n.id) + '">生图</button>' +
        "</div>" +
        '<button class="port in" data-side="in" type="button" aria-label="输入"></button>' +
        '<button class="port out" data-side="out" type="button" aria-label="输出"></button></div>';
    }
    if (n.kind === "shot") {
      const media = n.url
        ? (isVideoUrl(n.url)
            ? '<video src="' + esc(n.url) + '" muted playsinline preload="metadata"></video>'
            : '<img src="' + esc(n.url) + '" alt="">')
        : n._error
          ? '<div class="result-error"><strong>生成失败</strong><span>' + esc(n._error) + '</span>'
            + (n._errorDetail
              ? '<details class="result-error-more"><summary>详情</summary><pre>' + esc(n._errorDetail) + '</pre></details>'
              : '')
            + '</div>'
        : '<div class="face"><div style="font-size:28px;opacity:.55">+</div><div class="hint">点击查看或编辑提示词</div></div>';
      const dur = shotDurationLabel(n);
      const busy = n._busy ? " busy" : "";
      const crop = (state._cropShotId === n.id) ? " cropping" : "";
      const erase = (state._eraseShotId === n.id) ? " erasing" : "";
      const b = box(n);
      const acts = (state.selected === n.id)
        ? '<div class="node-acts">' +
          (n.url
            ? '<button type="button" data-node-act="download" data-id="' + esc(n.id) + '">下载</button>' +
              '<button type="button" data-node-act="edit" data-id="' + esc(n.id) + '">编辑</button>' +
              '<button type="button" data-node-act="crop" data-id="' + esc(n.id) + '">摘取</button>'
            : '<button type="button" data-node-act="edit" data-id="' + esc(n.id) + '">编辑</button>') +
          '<button type="button" data-node-act="more" data-id="' + esc(n.id) + '">更多</button>' +
          '</div>'
        : "";
      return '<div class="card shot' + sel + multi + busy + crop + erase + '" data-id="' + esc(n.id) + '" style="left:' + n.x + 'px;top:' + n.y + 'px;width:' + b.w + 'px;height:' + b.h + 'px">' +
        '<div class="label">▢ ' + esc(n.title) + (dur ? '<span class="dur">' + esc(dur) + '</span>' : '') + '</div>' +
        badge +
        '<div class="face">' + media + '</div>' +
        acts +
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
      const rawName = String(g.name || "").trim();
      const groupName = /^(group|groups?)$/i.test(rawName) ? "组" : (rawName || "组");
      const label = groupName + " · " + members.length + "项" + (shotN ? (" · " + shotN + "分镜") : " · 无分镜");
      world.insertAdjacentHTML("beforeend",
        '<div class="group-bound" data-gid="' + esc(g.id) + '" style="left:' + left + 'px;top:' + top +
        'px;width:' + w + 'px;height:' + h + 'px"><span class="gname">' + esc(label) + '</span></div>');
    });
  }
  function renderCards() {
    const active = document.activeElement;
    const keepText = (active && active.matches && active.matches("textarea[data-text]"))
      ? {
          id: active.dataset.id,
          start: active.selectionStart,
          end: active.selectionEnd,
          scroll: active.scrollTop,
        }
      : null;
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
        // A 16:9 UI screenshot must not reshape a portrait shot into a letterboxed landscape card.
        const wasPortrait = Number(shot.height) > Number(shot.width);
        if (state.selected === shot.id && !(wasPortrait && w > h)) {
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
    if (keepText) {
      const ta = world.querySelector('textarea[data-text][data-id="' + keepText.id + '"]');
      if (ta) {
        ta.focus();
        try { ta.setSelectionRange(keepText.start, keepText.end); } catch (_) {}
        ta.scrollTop = keepText.scroll;
      }
    }
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

  function minimapPreviewReady(preview) {
    if (!preview) return false;
    if (preview.tagName === "VIDEO") return preview.readyState >= 2 && preview.videoWidth > 0;
    return !!(preview.complete && preview.naturalWidth);
  }
  function ensureMinimapPreview(n) {
    if (!n || !n.url) return null;
    let preview = minimapImages.get(n);
    if (preview && preview._mmapUrl !== n.url) {
      minimapImages.delete(n);
      preview = null;
    }
    if (preview) return preview;
    if (isVideoUrl(n.url)) {
      preview = document.createElement("video");
      preview.muted = true;
      preview.playsInline = true;
      preview.preload = "metadata";
      preview.addEventListener("loadeddata", drawMinimap, { once: true });
    } else {
      preview = new Image();
      preview.onload = drawMinimap;
    }
    preview._mmapUrl = n.url;
    preview.src = n.url;
    minimapImages.set(n, preview);
    return preview;
  }
  function drawMinimap() {
    const cv = $("minimapCv");
    if (!cv) return;
    const ctx = cv.getContext("2d");
    const W = cv.width, H = cv.height;
    ctx.imageSmoothingEnabled = false;
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
      // Keep the overview useful when a large canvas compresses cards below a
      // visible pixel. The map is a navigation aid, not a second renderer.
      const w = Math.max(8, Math.min(28, nb.w * scale));
      const h = Math.max(6, Math.min(20, nb.h * scale));
      const preview = ensureMinimapPreview(n);
      if (n.url && minimapPreviewReady(preview)) {
        ctx.drawImage(preview, x, y, w, h);
      } else {
        ctx.fillStyle = n.kind === "shot" ? "#3a3a48" : "#2a3a36";
        ctx.fillRect(x, y, w, h);
      }
      ctx.strokeStyle = n.kind === "shot" ? "#777887" : "#5ee0c5";
      ctx.lineWidth = 1;
      ctx.strokeRect(x + .5, y + .5, Math.max(1, w - 1), Math.max(1, h - 1));
      if (n.kind === "shot" && w >= 12 && h >= 9) {
        ctx.strokeStyle = "rgba(255,255,255,.22)";
        ctx.beginPath();
        ctx.moveTo(x + w * .5, y + 1);
        ctx.lineTo(x + w * .5, y + h - 1);
        ctx.moveTo(x + 1, y + h * .5);
        ctx.lineTo(x + w - 1, y + h * .5);
        ctx.stroke();
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

  function keepComposerPromptVisible() {
    const reset = function () {
      const sc = $("dockScroll");
      const body = $("dockBody");
      if (sc) sc.scrollTop = 0;
      if (body) body.scrollTop = 0;
    };
    reset();
    if (typeof requestAnimationFrame === "function") requestAnimationFrame(reset);
  }
  function setDockMode(mode) {
    if (mode === "collapsed") mode = "expanded";
    if (mode !== "expanded" && mode !== "closed") mode = "expanded";
    state.dockMode = mode;
    renderDock();
    if (mode === "expanded") {
      requestAnimationFrame(function () {
        keepComposerPromptVisible();
        if (typeof fitShotsInView === "function") fitShotsInView();
        positionDock();
      });
    } else {
      requestAnimationFrame(function () { positionDock(); });
    }
  }

  function canvasArea() {
    const r = vp.getBoundingClientRect();
    const narrow = r.width <= 900;
    const area = { left: 12, top: 48, right: r.width - 12, bottom: r.height - (narrow ? 68 : 16) };
    vp.parentElement.querySelectorAll(".tools,.rail,.minimap,.zoom,.selbar,.chat-rail,.dock").forEach((el) => {
      const b = el.getBoundingClientRect();
      if (!b.width || !b.height) return;
      if (el.classList.contains("selbar")) {
        area.top = Math.max(area.top, b.bottom - r.top + 12);
      } else if (el.classList.contains("chat-rail")) {
        area.right = Math.min(area.right, b.left - r.left - 12);
      } else if (el.classList.contains("tools") && !narrow) {
        area.left = Math.max(area.left, b.right - r.left + 12);
      } else if (el.classList.contains("rail") || el.classList.contains("minimap") || el.classList.contains("zoom")) {
        area.bottom = Math.min(area.bottom, b.top - r.top - 8);
      }
    });
    return area;
  }

  function hideShotBar() {
    const bar = $("shotBar");
    if (!bar) return;
    bar.hidden = true;
    bar.classList.remove("show");
  }

  function openLaneForDock() {
    return false;
  }

  function positionDock() {
    if (stage && stage.classList.contains("workspace-mode")) {
      hideShotBar();
      return;
    }
    const n = nodeById(state.selected);
    if (!dock || !n || n.kind !== "shot" || !dock.classList.contains("show")) {
      hideShotBar();
      return;
    }
    const stageEl = dock.closest(".stage") || vp.parentElement;
    const sr = stageEl.getBoundingClientRect();
    const gap = 8;
    const barH = 36;
    const card = world.querySelector('.card.shot[data-id="' + n.id + '"]');
    if (!card) {
      hideShotBar();
      return;
    }
    const cr0 = card.getBoundingClientRect();
    const minTop = 52;
    if (cr0.top - sr.top < minTop) {
      state.cam.y += minTop - (cr0.top - sr.top);
      applyCam();
    }
    const cr = card.getBoundingClientRect();
    const cx = cr.left - sr.left;
    const cy = cr.top - sr.top;
    const cw = cr.width;
    const ch = cr.height;
    const others = [...world.querySelectorAll(".card")].filter(function (el) { return el !== card; })
      .map(function (el) {
        const r = el.getBoundingClientRect();
        return { l: r.left - sr.left, t: r.top - sr.top, r: r.right - sr.left, b: r.bottom - sr.top };
      });
    function gapBelow(L, W, fromY) {
      let nearest = sr.height - fromY - 12;
      others.forEach(function (o) {
        if (o.r <= L + 8 || o.l >= L + W - 8) return;
        if (o.b <= fromY + 4) return;
        if (o.t <= fromY + 4) nearest = 0;
        else nearest = Math.min(nearest, o.t - fromY);
      });
      return nearest;
    }
    function gapAbove(L, W, fromY) {
      let nearest = fromY - 44;
      others.forEach(function (o) {
        if (o.r <= L + 8 || o.l >= L + W - 8) return;
        if (o.t >= fromY - 4) return;
        if (o.b >= fromY - 4) nearest = 0;
        else nearest = Math.min(nearest, fromY - o.b);
      });
      return nearest;
    }

    // 一个框贴在分镜下，高度跟内容走，不裁切
    const maxW = Math.min(720, Math.max(560, sr.width - 72));
    const dw = Math.min(640, maxW);
    let left = cx + (cw - dw) / 2;
    const rail = $("assetRail");
    const railRight = (rail && rail.getBoundingClientRect().width > 40) ? 72 + 248 + 8 : 72;
    left = Math.max(railRight, Math.min(left, sr.width - dw - 12));

    dock.style.setProperty("width", dw + "px", "important");
    dock.style.setProperty("max-width", dw + "px", "important");
    dock.style.setProperty("min-width", Math.min(560, dw) + "px", "important");
    dock.style.setProperty("height", "auto", "important");
    dock.style.setProperty("max-height", "none", "important");
    dock.style.setProperty("overflow", "visible", "important");
    const naturalH = Math.max(180, dock.offsetHeight || 220);
    // v0821o136-seko: 底部居中的缩放底栏约占 56px，Composer 不压上去
    const bottomReserve = 56;
    const spaceBelow = sr.height - (cy + ch + gap) - bottomReserve;
    const spaceAbove = cy - gap - 44;
    let top;
    let attach = "below";
    if (spaceBelow >= Math.min(naturalH, 200)) {
      attach = "below";
      top = cy + ch + gap;
    } else if (spaceAbove >= Math.min(naturalH, 200)) {
      attach = "above";
      top = Math.max(44, cy - gap - naturalH);
    } else {
      attach = "below";
      top = cy + ch + gap;
    }
    if (top < 44) top = 44; // fallback bottom desk unused: box follows the shot
    if (top + naturalH > sr.height - bottomReserve) top = Math.max(44, sr.height - bottomReserve - naturalH);

    // v0821o136seko-ui: Composer 不许压左下角 minimap；垂直区间相交时向右让位
    const mmEl = document.querySelector(".minimap");
    if (mmEl) {
      const mr = mmEl.getBoundingClientRect();
      if (mr.width > 0) {
        const mmT = mr.top - sr.top, mmB = mr.bottom - sr.top, mmR = mr.right - sr.left;
        const dB = top + naturalH;
        if (dB > mmT + 4 && top < mmB - 4 && left < mmR + 8) {
          left = Math.min(Math.max(left, mmR + 8), Math.max(railRight, sr.width - dw - 12));
        }
      }
    }

    dock.style.setProperty("left", Math.round(left) + "px", "important");
    dock.style.setProperty("top", Math.round(top) + "px", "important");
    dock.style.setProperty("right", "auto", "important");
    dock.style.setProperty("bottom", "auto", "important");
    dock.style.setProperty("width", dw + "px", "important");
    dock.style.setProperty("max-width", dw + "px", "important");
    dock.style.setProperty("min-width", Math.min(560, dw) + "px", "important");
    dock.style.setProperty("height", "auto", "important");
    dock.style.setProperty("min-height", "0", "important");
    dock.style.setProperty("max-height", "none", "important");
    dock.style.setProperty("transform", "none", "important");
    dock.style.setProperty("overflow", "visible", "important");
    dock.style.visibility = "";
    dock.classList.add("near");
    dock.dataset.attach = attach;

    const bar = $("shotBar");
    if (bar) {
      bar.hidden = false;
      bar.classList.add("show");
      bar.style.maxWidth = Math.min(720, Math.max(280, sr.width - 80)) + "px";
      bar.style.width = "max-content";
      bar.style.flexWrap = "wrap";
      bar.style.whiteSpace = "normal";
      bar.style.overflow = "visible";
      const bw = Math.min(Math.max(bar.offsetWidth || 480, 280), sr.width - 80);
      let bx = cx + (cw - bw) / 2;
      bx = Math.max(64, Math.min(bx, sr.width - bw - 12));
      const actualBarH = Math.max(36, bar.offsetHeight || 36);
      let by = cy - 10 - actualBarH;
      if (attach === "above") by = Math.max(8, top - 10 - actualBarH);
      if (by < 8) by = 8;
      if (by + actualBarH > cy - 4) by = Math.max(8, cy - 4 - actualBarH);
      Object.assign(bar.style, {
        left: Math.round(bx) + "px",
        top: Math.round(by) + "px",
        right: "auto",
        bottom: "auto",
        width: "max-content",
        maxWidth: Math.min(720, sr.width - 80) + "px",
        overflow: "visible",
        transform: "none",
      });
    }

    const area = canvasArea();
    ["skillbox", "atbox", "picker"].forEach(function (id) {
      const el = $(id);
      if (!el) return;
      const px = left + dw + gap + 360 <= sr.width - 16 ? left + dw + gap : left;
      Object.assign(el.style, {
        left: Math.round(px) + "px",
        right: "auto",
        top: Math.round(top) + "px",
        bottom: "auto",
        width: "360px",
        maxHeight: Math.min(320, area.bottom - top) + "px",
        transform: "none",
      });
    });
  }
  window.positionDock = positionDock;

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
      const list = railAssets();
      body = '<div class="rail-h">画布资产 · 可拖出</div>' +
        list.map((a) => {
          const on = state.selected === a.id ? " on" : "";
          const name = sourceTitle(a);
          const thumb = a.url
            ? (isVideoUrl(a.url)
                ? '<video src="' + esc(a.url) + '" muted playsinline preload="metadata"></video>'
                : '<img src="' + esc(a.url) + '" alt="">')
            : "";
          const pin = (canPin && a.url)
            ? '<button class="pin" type="button" data-pin="' + esc(a.id) + '" title="接到此镜">接到此镜</button>'
            : "";
          return '<div class="rail-item' + on + '" data-rail="' + esc(a.id) + '" title="' + esc(name) + '">' +
            thumb +
            '<span title="' + esc(name) + '">' + esc(name) + "</span>" +
            pin +
            "</div>";
        }).join("") +
        '<button class="rail-item add" type="button" data-act="upload">上传</button>';
    } else {
      const list = railHistory();
      body = '<div class="rail-h">生成历史 · 拖到画布</div>' +
        (list.length ? list.map((it, i) => {
          const name = String(it.title || "");
          const thumb = it.url
            ? (isVideoUrl(it.url)
                ? '<video src="' + esc(it.url) + '" muted playsinline preload="metadata"></video>'
                : '<img src="' + esc(it.url) + '" alt="">')
            : "";
          const pin = (canPin && it.url)
            ? '<button class="pin" type="button" data-hist-pin="' + i + '" title="接到此镜">接到此镜</button>'
            : "";
          return '<div class="rail-item" data-hist="' + i + '" title="' + esc(name) + '">' +
            thumb +
            '<span title="' + esc(name) + '">' + esc(name) + "</span>" +
            pin +
            "</div>";
        }).join("") : "<div class='rail-h'>还没有成片</div>");
    }
    rail.innerHTML = tabs + body;
  }

  function renderChatRail() {
    const rail = $("chatRail");
    if (!rail) return;
    const shot = nodeById(state.selected);
    const shotOk = !!(shot && shot.kind === "shot");
    const stub = isStubMode();
    const frame = shotOk ? frameAsset(shot) : null;
    const needFrame = state.mode === "video" && (typeof currentGraphOp !== "function" || currentGraphOp() !== "t2v") && !frame;
    const ml = modeLabelOf(state.mode);
    const modeEl = $("chatRailMode");
    const tagEl = $("chatRailTag");
    const pathEl = $("chatRailPath");
    const copyEl = $("chatRailCopy");
    const actsEl = $("chatRailActs");
    if (modeEl) {
      modeEl.textContent = ml;
      modeEl.classList.toggle("stub", stub);
    }
    if (tagEl) tagEl.textContent = stub ? "未接" : (state.mode === "image" ? "默认" : "路径");
    const sid = ($("service") && $("service").value) || "";
    let svcLabel = "";
    if (sid) {
      const it = (typeof catalogItemForService === "function") ? catalogItemForService() : null;
      if (it && it.name) svcLabel = String(it.name);
      else {
        const sel = $("service");
        const t = (sel && sel.selectedIndex >= 0 && sel.options[sel.selectedIndex])
          ? String(sel.options[sel.selectedIndex].textContent || "") : "";
        svcLabel = (t && t !== sid) ? t.split(" · ")[0] : sid;
      }
    }
    const steps = [
      { on: shotOk, warn: !shotOk, text: shotOk ? ("分镜 · " + (shot.title || "")) : "请先选中分镜" },
      { on: !stub && (state.mode === "image" || state.mode === "video"), warn: stub, text: stub ? (ml + " · 未接") : ("模式 · " + ml) },
      { on: !!sid && !stub, warn: false, text: sid ? ("服务 · " + svcLabel) : "选服务后点胶囊 ↑" },
    ];
    if (state.mode === "video") {
      const t2v = (typeof currentGraphOp === "function" && currentGraphOp() === "t2v");
      steps.push({ on: !!frame || t2v, warn: needFrame, text: frame ? "首帧已就绪" : (t2v ? "文生视频 · 不需要首帧" : "缺首帧 · 上传或选择") });
    }
    if (pathEl) {
      pathEl.innerHTML = steps.map((s) =>
        "<li class=\"" + (s.warn ? "warn" : (s.on ? "on" : "")) + "\">" + esc(s.text) + "</li>"
      ).join("");
    }
    if (copyEl) {
      if (stub) copyEl.textContent = ml + " · 本版未接";
      else if (needFrame) copyEl.textContent = "缺首帧：切到图片生成，或上传/选择首帧";
      else copyEl.textContent = "选分镜 → " + ml + " → 选服务 → 胶囊 ↑";
    }
    if (actsEl) {
      // v0821o19 双↑: right rail must NOT mint a second ↑ — only capsule #send is the generate entry.
      let acts = "";
      if (needFrame) {
        acts += '<button class="chip-btn" type="button" data-act="upload">上传首帧</button>' +
          '<button class="chip-btn" type="button" data-act="pick">选择首帧</button>';
      }
      actsEl.innerHTML = acts;
    }
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
    const selected = nodeById(state.selected);
    let n = selected;
    // Keep Composer on the last shot when the user clicks a canvas image source to pin it as 参考.
    if ((!n || n.kind !== "shot") && selected && isImageSource(selected)) {
      const remembered = nodeById(state.lastComposerShot);
      if (remembered && remembered.kind === "shot") n = remembered;
    }
    activateShotComposer(n && n.kind === "shot" ? n : selected);
    if (!n || n.kind !== "shot") {
      dock.classList.remove("show");
      dock.classList.remove("near");
      dock.classList.remove("collapsed");
      dock.classList.remove("expanded");
      hideShotBar();
      hideSkillbox();
      hideAtbox();
      const picker = $("picker");
      if (picker) picker.classList.remove("show");
      syncComposerChip(); syncCanvasTip();
      renderRail();
      renderChatRail();
      requestAnimationFrame(positionDock);
      return;
    }
    state.lastComposerShot = n.id;
    if (state.dockMode === "closed") {
      dock.classList.remove("show");
      dock.classList.remove("collapsed");
      dock.classList.remove("expanded");
      dock.classList.remove("near");
      hideShotBar();
      hideSkillbox();
      hideAtbox();
      const picker = $("picker");
      if (picker) picker.classList.remove("show");
      syncComposerChip(); syncCanvasTip();
      renderRail();
      renderChatRail();
      requestAnimationFrame(positionDock);
      return;
    }
    if (state.dockMode === "collapsed") state.dockMode = "expanded";
    const expanded = state.dockMode === "expanded";
    dock.classList.add("show");
    dock.classList.toggle("collapsed", !expanded);
    dock.classList.toggle("expanded", expanded);
    dock.classList.remove("near");
    try { dock.setAttribute("data-shot", n.id); } catch (_) {}
    if ($("dockTitle")) {
      const op = (typeof currentGraphOp === "function") ? currentGraphOp() : "";
      const opLabel = (typeof graphOpLabel === "function" && graphOpLabel(op)) || modeLabelOf(state.mode);
      const ml = opLabel + (isStubMode() ? " · 未接" : "");
      $("dockTitle").textContent = (n.title || "分镜") + " · " + ml;
    }
    if (typeof syncOpChip === "function") syncOpChip();
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
    const opNow = (typeof currentGraphOp === "function") ? currentGraphOp() : "";
    const needFrame = state.mode === "video" && opNow !== "t2v" && !frame;
    const stub = isStubMode();
    const capMsg = refCapGateMessage(n);
    const unusedMsg = refUnusedGateMessage(n);
    const liveMsg = ($("msg") && $("msg").textContent) || "";
    const keepSmart = liveMsg.indexOf("已智能匹配") >= 0;
    syncSendGate(needFrame, stub);
    if (stub) {
      setMsg((state.mode === "text" ? "文本生成" : "音频生成") + " · 本版未接", "warn");
    } else if (needFrame) {
      // v0821g/o17: missing-frame is hard stop (red); offer 图片生成 or attach frame
      if (!keepSmart) setMsg("缺首帧 · 切到图片生成，或先上传/选择首帧", "bad");
    } else if (unusedMsg) {
      if (!keepSmart) setMsg(unusedMsg, "bad");
    } else if (capMsg) {
      if (!keepSmart) setMsg(capMsg, "bad");
    } else if (n._error) {
      // v0821o9: card 生成失败 + reason must mirror on Composer foot (not card-only)
      if (!keepSmart) setMsg(n._error, "bad", n._errorDetail || "");
    } else if (state.mode !== "video") {
      const msgEl = $("msg");
      const t = (msgEl && msgEl.textContent) || "";
      if (t.indexOf("缺首帧") >= 0) setMsg("");
    } else if (state.mode === "video" && frame) {
      // v0821j: do NOT reset to 首帧已就绪 while generate/busy/group in-flight (wipes 校验连线/已点生成)
      // v0821k: also keep bad/warn (Fal job.error / 此模型需要提示词) — empty card must not be silent
      if (!fireSend._busy && !state.runningGroup && !keepSmart) {
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
        const last = lastFrameAsset(n);
        frameHtml = '<div class="frame-slot">首帧 <img src="' + esc(frame.url) + '" alt="">' + esc(sourceTitle(frame)) +
          linked.filter((a) => a.url && a.id !== frame.id && a.id !== (n.lastFrameId || "")).map((a) => {
            return '<button class="frame-chip" type="button" data-frame="' + esc(a.id) + '" title="设为首帧">' +
              (a.url ? '<img src="' + esc(a.url) + '" alt="">' : "") + esc(sourceTitle(a)) + "</button>";
          }).join("") + "</div>";
        frameHtml += last
          ? '<div class="frame-slot">尾帧 <img src="' + esc(last.url) + '" alt="">' + esc(sourceTitle(last)) +
            '<button class="chip-btn" type="button" data-act="clear-last">去掉</button></div>'
          : '<div class="frame-slot missing">尾帧（可选）' +
            '<button class="chip-btn" type="button" data-act="upload-last">上传</button>' +
            '<button class="chip-btn" type="button" data-act="pick-last">选择</button></div>';
      } else if (opNow === "t2v") {
        frameHtml = '<div class="frame-slot t2v-no-frame">文生视频 · 不需要首帧</div>';
      } else {
        frameHtml = '<div class="frame-slot missing">缺首帧' +
          '<button class="chip-btn" type="button" data-act="upload">上传</button>' +
          '<button class="chip-btn" type="button" data-act="pick">选择</button></div>';
      }
    }
    const promoteBtn = n.url
      ? '<button class="chip-btn" type="button" data-act="promote" title="收进资产库">入库</button>'
      : "";
    const refCap = maxRefCount(catalogItemForService());
    // v0821: always show capacity; show ALL linked chips (even over-cap) so user can unlink.
    // v0821o40: 参考 N/cap + 灌满 + hard-gate share outbound口径 countRefUrls.
    // 成片 chip stays visual-only (data-self-ref) — must NOT inflate numerator to 6/5 after 灌满.
    const refCount = countRefUrls(null, n).length;
    const remain = Math.max(0, refCap - refCount);
    const eats = catalogEatsRefs(catalogItemForService());
    const refHint = (refCount > refCap)
      ? '<span class="ref-cap-hint">参考 ' + refCount + '/' + refCap + '</span>'
      : "";
    // Unlinked thumbnails are selectable suggestions, not sent references.
    // Keep them out of this row so the visible count cannot claim 0/n beside
    // a thumbnail that will not be sent.
    const chipNodes = linked;
    const ownUrl = shotResultImageUrl(n);
    const ownChip = ownUrl
      ? '<button class="chip on" type="button" data-self-ref="1" title="成片">' +
          '<img src="' + esc(ownUrl) + '" alt=""></button>'
      : "";
    const refsEl = $("refs");
    const emptySlots = [];
    if (eats && remain > 0 && expanded) {
      for (let si = 0; si < remain; si++) {
        emptySlots.push(
          '<button class="chip ref-slot-empty" type="button" data-act="upload" title="空槽 ' +
            (refCount + si + 1) + '/' + refCap + ' · 上传参考" aria-label="空参考槽"></button>'
        );
      }
    }
    const sibId = (!eats && refCount > 0) ? editSiblingId(catalogItemForService()) : "";
    const smartBtn = sibId
      ? '<button class="chip-btn smart-edit" type="button" data-act="apply-edit-sibling" title="一键改选图生图 Edit">一键改选 Edit</button>'
      : "";
    // v0821o53: over-cap → 一键匹配 eats+maxRefs≥N (never silent unlink)
    const rematchId = (refCount > refCap) ? capacityRematchId(refCount, catalogItemForService()) : "";
    const rematchBtn = (refCount > refCap)
      ? '<button class="chip-btn capacity-rematch" type="button" data-act="capacity-rematch" title="' +
          (rematchId ? ("一键匹配 maxRefs≥" + refCount) : "目录无足够容量的图生图模型") +
          '">一键匹配</button>'
      : "";
    // 灌满测试: only when current model eats refs and still has remain capacity
    const fillBtn = ""; // 灌满测试 hidden; data-act="fill-refs-cap" not shown
    const hasChips = !!(ownChip || chipNodes.length || frameHtml || emptySlots.length || smartBtn || rematchBtn || fillBtn);
    // v0821o24: collapsed + no chips/frame → hide refs (no orphan empty slots).
    // v0821o39: empty capacity slots count as chips so cap is always visible when dock open.
    // Expanded always keeps 上传/选择; collapsed keeps them when pinned or video needs frame.
    if (!expanded && !hasChips && !needFrame) {
      refsEl.innerHTML = "";
      refsEl.classList.add("refs-empty");
    } else {
      refsEl.classList.remove("refs-empty");
      refsEl.innerHTML = frameHtml +
        '<button class="chip-btn" type="button" data-act="upload">上传</button>' +
        '<button class="chip-btn" type="button" data-act="pick">选择</button>' +
        promoteBtn + smartBtn + rematchBtn + fillBtn + refHint + ownChip +
        chipNodes.map((a) => {
          const on = linked.some((x) => x.id === a.id) ? " on" : "";
          return '<button class="chip' + on + '" type="button" data-asset="' + esc(a.id) + '" title="' + esc(sourceTitle(a)) + '">' +
            (a.url ? '<img src="' + esc(a.url) + '" alt="">' : esc(sourceTitle(a).slice(0, 2))) + "</button>";
        }).join("") + emptySlots.join("");
    }
    syncComposerChip(); syncCanvasTip();
    renderRail();
    renderChatRail();
    if (typeof syncSvcCaps === "function") syncSvcCaps();
    if (typeof scheduleCostRefresh === "function") scheduleCostRefresh();
    requestAnimationFrame(() => {
      positionDock();
      if (expanded) keepComposerPromptVisible();
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
    const composer = nodeById(state.lastComposerShot);
    const dockOpen = state.dockMode === "expanded" || state.dockMode === "collapsed";
    if (dockOpen && composer && composer.kind === "shot" && n && n.id !== composer.id
        && !opts.shift && isImageSource(n) && n.kind !== "shot") {
      try { linkAssetToShot(n, composer); } catch (_) {}
      state.selected = composer.id;
      setMulti([composer.id]);
    }
    if (n && n.kind === "shot") {
      state.lastComposerShot = n.id;
      state._scriptShotId = n.id;
      if (state.editor) state.editor.activeShotId = n.id;
      if (state.cam.s >= 1 && !opts.preserveLayout) {
        if (constrainShotsToViewport()) renderCards();
        constrainCameraToShots(n);
        applyCam();
      }
      // v0821o103-wide-desk: large screen always writes on the desk; no toy collapsed bar.
      if (opts.keepClosed) {
        /* leave dockMode (closed/chip path) */
      } else {
        state.dockMode = "expanded";
      }
    }
    renderCards();
    drawWires();
    renderDock();
    syncLoraUi();
    syncGroupRunBtn();
    syncNodeTools();
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
      // o53b: refuse NEW ref link when at/over current maxRefs — never cut old links.
      if (shot && shot.kind === "shot" && typeof isImageSource === "function" && isImageSource(asset)) {
        const it = (typeof catalogItemForService === "function") ? catalogItemForService() : null;
        const cap = (typeof maxRefCount === "function") ? maxRefCount(it) : null;
        if (cap != null && Number(cap) >= 0) {
          const urls = (typeof countRefUrls === "function") ? countRefUrls(null, shot) : [];
          const n = urls.length;
          const u = asset && asset.url ? String(asset.url) : "";
          if (u && urls.indexOf(u) < 0 && n >= Number(cap)) {
            try { setMsg("参考已满 " + n + "/" + cap + " · 拒新连线（不砍旧线）", "bad"); } catch (_) {}
            return false;
          }
        }
      }
      state.edges.push({ from: asset.id, to: shot.id });
      invalidateStageProgress(shot);
    }
    mention(asset, shot);
    if (shot && shot.kind === "shot" && !shot.firstFrameId && isImageSource(asset)
        && (state.mode === "video" || shot.mode === "video")) {
      shot.firstFrameId = asset.id;
      shot.wantT2v = false;
    }
    // v0821o18: explicit attach only — never steal recipe-desk history; announce when video first frame lands
    if (shot && shot.kind === "shot" && state.mode === "video" && isImageSource(asset) && shot.firstFrameId === asset.id) {
      try { setMsg("首帧已就绪 · 可生成", "ok"); } catch (_) {}
      try { if (typeof renderChatRail === "function") renderChatRail(); } catch (_) {}
    }
    try { Promise.resolve(smartMatchService({ announce: true })).catch(function () {}); } catch (_) {}
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
    try { Promise.resolve(smartMatchService({ announce: true })).catch(function () {}); } catch (_) {}
  }

  function hideNodeMenu() {
    const menu = $("nodeContextMenu");
    if (menu) menu.style.display = "none";
  }

  function deleteNode(id) {
    const target = nodeById(id);
    if (!target) return false;
    if (target.kind === "shot" && state.editor && state.editor.playing) stopEditorPlayback();
    const removedId = id;
    state.selected = null;
    state.selectedEdge = null;
    state.multi = (state.multi || []).filter((x) => x !== removedId);
    if (state.lastComposerShot === removedId) state.lastComposerShot = null;
    if (state._scriptShotId === removedId) state._scriptShotId = null;
    hideNodeMenu();
    state.edges.filter((e) => e.from === removedId || e.to === removedId).forEach((edge) => {
      const src = nodeById(edge.from);
      const dst = nodeById(edge.to);
      if (src && dst) unlinkAssetFromShot(src, dst);
    });
    state.edges = state.edges.filter((e) => e.from !== removedId && e.to !== removedId);
    state.nodes = state.nodes.filter((n) => n.id !== removedId);
    state.nodes.forEach((n) => {
      if (n.firstFrameId === removedId) n.firstFrameId = "";
      if (n.lastFrameId === removedId) n.lastFrameId = "";
    });
    if (state.editor && state.editor.activeShotId === removedId) state.editor.activeShotId = null;
    pruneGroups();
    if (state.script && Array.isArray(state.script.scenes)) {
      state.script.scenes.forEach((scene) => {
        scene.shotIds = (scene.shotIds || []).filter((sid) => sid !== removedId);
      });
    }
    renderCards();
    drawWires();
    renderDock();
    renderWorkspace();
    persist();
    setMsg("已删除节点", "ok");
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
    const prefix = node.kind === "text" ? "text" : node.kind === "shot" ? "shot" : "asset";
    node.id = uid(prefix);
    node.x = point && point.x != null ? point.x : Number(node.x || 0) + 48;
    node.y = point && point.y != null ? point.y : Number(node.y || 0) + 48;
    if (node.firstFrameId) node.firstFrameId = "";
    if (node.lastFrameId) node.lastFrameId = "";
    delete node._busy;
    delete node._error;
    delete node._errorDetail;
    state.nodes.push(node);
    selectNode(node.id);
    persist();
    setMsg("已粘贴节点", "ok");
    return node;
  }

  function showNodeMenu(e) {
    const menu = $("nodeContextMenu");
    if (!menu || !stage) return;
    const card = e.target.closest(".card");
    const edgePath = e.target.closest("path.edge");
    const ei = edgePath ? Number(edgePath.getAttribute("data-ei")) : NaN;
    const edge = Number.isFinite(ei) ? state.edges[ei] : null;
    const targetId = card ? card.dataset.id : "";
    const targetEdge = edge ? { from: edge.from, to: edge.to, ei: ei } : null;
    if (targetEdge) {
      state.selectedEdge = { from: targetEdge.from, to: targetEdge.to, ei: targetEdge.ei };
      state.selected = null;
    } else if (targetId && state.selected !== targetId) {
      state.selectedEdge = null;
      selectNode(targetId);
    } else if (!targetId) {
      state.selectedEdge = null;
    }
    nodeMenuPoint = {
      targetId: targetId,
      targetEdge: targetEdge,
      world: clientToWorld(e.clientX, e.clientY),
    };
    const copyBtn = menu.querySelector('[data-nodeact="copy"]');
    const pasteBtn = menu.querySelector('[data-nodeact="paste"]');
    const deleteButton = menu.querySelector('[data-nodeact="delete"]');
    if (copyBtn) copyBtn.disabled = !targetId;
    if (deleteButton) {
      deleteButton.disabled = !targetId && !targetEdge;
      deleteButton.textContent = targetEdge ? "删除连线" : "删除";
    }
    if (pasteBtn) pasteBtn.disabled = !nodeClipboard;
    const sr = stage.getBoundingClientRect();
    menu.style.display = "block";
    const left = Math.max(6, Math.min(e.clientX - sr.left, sr.width - menu.offsetWidth - 6));
    const top = Math.max(6, Math.min(e.clientY - sr.top, sr.height - menu.offsetHeight - 6));
    menu.style.left = left + "px";
    menu.style.top = top + "px";
  }

  function ensureNodeContextMenu() {
    if ($("nodeContextMenu") || !stage) return;
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

  function bindNodeMenuUi() {
    ensureNodeContextMenu();
    const nodeMenu = $("nodeContextMenu");
    if (nodeMenu && !nodeMenu._bound) {
      nodeMenu._bound = true;
      nodeMenu.addEventListener("click", (e) => {
        const btn = e.target.closest("[data-nodeact]");
        if (!btn || btn.disabled) return;
        const point = nodeMenuPoint;
        hideNodeMenu();
        if (btn.dataset.nodeact === "copy") copyNode(point && point.targetId);
        else if (btn.dataset.nodeact === "paste") pasteNode(point && point.world);
        else if (btn.dataset.nodeact === "delete") {
          if (point && point.targetEdge) {
            const ei = Number.isFinite(point.targetEdge.ei)
              ? point.targetEdge.ei
              : state.edges.findIndex((ed) => ed.from === point.targetEdge.from && ed.to === point.targetEdge.to);
            if (ei >= 0) disconnectEdgeAt(ei);
          } else deleteNode(point && point.targetId);
        }
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
    if (!document._sekoNodeMenuHide) {
      document._sekoNodeMenuHide = true;
      document.addEventListener("pointerdown", (e) => {
        if (!e.target.closest("#nodeContextMenu")) hideNodeMenu();
      });
    }
    if (!document._sekoNodeHotkeys) {
      document._sekoNodeHotkeys = true;
      document.addEventListener("keydown", (e) => {
        if (e.key !== "Delete" && e.key !== "Backspace") return;
        if (e.target && e.target.closest &&
            (e.target.isContentEditable ||
             e.target.closest("textarea,input,select,[contenteditable]")))
          return;
        if (state.selectedEdge) {
          e.preventDefault();
          const edge = state.selectedEdge;
          const ei = Number.isFinite(edge.ei)
            ? edge.ei
            : state.edges.findIndex((ed) => ed.from === edge.from && ed.to === edge.to);
          state.selectedEdge = null;
          if (ei >= 0) disconnectEdgeAt(ei);
          return;
        }
        if (!state.selected) return;
        e.preventDefault();
        deleteNode(state.selected);
      });
    }
  }

  function toggleAssetOnShot(asset, shot) {
    if (!asset || !shot || shot.kind !== "shot") return;
    if (state.edges.some((e) => e.from === asset.id && e.to === shot.id)) unlinkAssetFromShot(asset, shot);
    else linkAssetToShot(asset, shot);
  }

  function promoteResult(shot, url) {
    // Explicit 入库 only. Generation writeback must not call this.
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
      existing.userPromoted = true;
      return existing;
    }
    const node = {
      id: uid("hist"),
      kind: "character",
      title: item.title || "历史成片",
      x: x != null ? x : 220,
      y: y != null ? y : 24 + assets().length * 40,
      url: item.url,
      userPromoted: true,
      mediaKind: mediaKindOf(item.url),
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
    if (!asset) return;
    const textTa = (document.activeElement && document.activeElement.matches &&
      document.activeElement.matches("textarea[data-text]"))
      ? document.activeElement : null;
    const selected = nodeById(state.selected);
    const textNode = textTa
      ? nodeById(textTa.dataset.id)
      : (selected && selected.kind === "text" ? selected : null);
    if (textNode && textNode.kind === "text") {
      const ta = textTa || world.querySelector('textarea[data-text][data-id="' + textNode.id + '"]');
      const v = ta ? ta.value : String(textNode.text || "");
      const caret = ta && ta.selectionStart != null ? ta.selectionStart : v.length;
      const before = v.slice(0, caret);
      const at = before.lastIndexOf("@");
      const tag = "@" + sourceTitle(asset);
      let next;
      let caret2;
      if (at >= 0 && !/[\s\n]/.test(before.slice(at + 1))) {
        next = v.slice(0, at) + tag + " " + v.slice(caret);
        caret2 = at + tag.length + 1;
      } else {
        const pad = v && !/\s$/.test(v) ? " " : "";
        next = v + pad + tag + " ";
        caret2 = next.length;
      }
      textNode.text = next;
      if (isImageSource(asset) && !state.edges.some((e) => e.from === asset.id && e.to === textNode.id)) {
        state.edges.push({ from: asset.id, to: textNode.id });
      }
      syncTextToShots(textNode);
      hideAtbox();
      hideSkillbox();
      renderCards(); drawWires(); persist();
      const ta2 = world.querySelector('textarea[data-text][data-id="' + textNode.id + '"]');
      if (ta2) {
        ta2.focus();
        try { ta2.setSelectionRange(caret2, caret2); } catch (_) {}
      }
      return;
    }
    const shot = selected;
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
    if (skill.action) {
      hideSkillbox();
      const shot = selectedShot();
      if (skill.action === "light") showLightPop();
      else if (skill.action === "camera") showCamPop();
      else if (skill.action === "upscale") upscaleFromShot(shot);
      else if (skill.action === "erase") beginErase(shot);
      else if (skill.action === "t2v") t2vFromShot(shot);
      return;
    }
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
        placed++;
        return;
      }
      const node = spawnHistoryAt({ url: it.url, title: it.title || "导入素材" }, 220 + (i % 3) * 24, baseY + i * 40);
      if (node) placed++;
    });
    closeImportModal();
    renderCards(); drawWires(); renderDock(); persist();
    setMsg(placed ? ("已导入 " + placed + " 个素材到画布") : "没有可导入的素材", placed ? "ok" : "warn");
  }
  function setZoomScale(s) {
    const next = Math.min(1.5, Math.max(0.16, s));
    state._overview100 = next === 1;
    const r = vp.getBoundingClientRect();
    const n = nodeById(state.selected), b = n && box(n);
    // Toolbar zoom keeps the selection, not the unrelated viewport centre, in view.
    const cx = n ? state.cam.x + (n.x + b.w / 2) * state.cam.s : r.width / 2;
    const cy = n ? state.cam.y + (n.y + b.h / 2) * state.cam.s : r.height / 2;
    const w0 = clientToWorld(r.left + cx, r.top + cy);
    state.cam.s = next;
    state.cam.x = cx - w0.x * next;
    state.cam.y = cy - w0.y * next;
    constrainCameraToShots(n);
    applyCam(); persist();
    syncZoomPresets();
  }

  function constrainCameraToShots(focus) {
    const area = canvasArea();
    const list = shots();
    if (!list.length) return;
    const pad = 12;
    let left = area.left + pad, right = area.right - pad;
    let top = area.top + pad, bottom = area.bottom - pad;
    const scale = state.cam.s;
    if (focus && scale >= 1) {
      // At 100%, keep the selected card inside the actual canvas viewport;
      // controls reduce the safe area below a card's physical 360px height.
      const vr = vp.getBoundingClientRect();
      const narrow = vr.width <= 900;
      left = narrow ? 76 : 2; right = vr.width - (narrow ? 12 : 2); top = 38; bottom = vr.height - 2;
      const fb = box(focus);
      const fw = fb.w * scale, fh = fb.h * scale;
      state.cam.x = fw > right - left
        ? left - focus.x * scale
        : Math.max(left - focus.x * scale, Math.min(right - fw - focus.x * scale, state.cam.x));
      state.cam.y = fh > bottom - top
        ? top - focus.y * scale
        : Math.max(top - focus.y * scale, Math.min(bottom - fh - focus.y * scale, state.cam.y));
      return;
    }
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

  function fitShotsInView() {
    const list = shots();
    if (!list.length) return;
    const area = canvasArea();
    const pad = 16;
    const vw = Math.max(1, area.right - area.left - pad * 2);
    const vh = Math.max(1, area.bottom - area.top - pad * 2);
    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
    list.forEach(function (n) {
      const b = box(n);
      minX = Math.min(minX, n.x);
      minY = Math.min(minY, n.y);
      maxX = Math.max(maxX, n.x + b.w);
      maxY = Math.max(maxY, n.y + b.h);
    });
    const bw = Math.max(1, maxX - minX);
    const bh = Math.max(1, maxY - minY);
    const fitS = Math.min(vw / bw, vh / bh);
    if (state.cam.s > fitS) state.cam.s = Math.max(0.16, fitS);
    constrainCameraToShots(list[0]);
    applyCam();
  }

  function separateOverlappingShots() {
    const list = shots();
    let changed = false;
    const gap = 48;
    const overlapRatio = (a, b) => {
      const ab = box(a), bb = box(b);
      const w = Math.max(0, Math.min(a.x + ab.w, b.x + bb.w) - Math.max(a.x, b.x));
      const h = Math.max(0, Math.min(a.y + ab.h, b.y + bb.h) - Math.max(a.y, b.y));
      return (w * h) / Math.max(1, Math.min(ab.w * ab.h, bb.w * bb.h));
    };
    list.forEach((n, i) => {
      if (!list.slice(0, i).some((prev) => overlapRatio(prev, n) > 0.25)) return;
      const anchor = list[0];
      const ab = box(anchor);
      for (let slot = 0; slot < list.length * 2; slot++) {
        n.x = anchor.x + (slot % 2) * (ab.w + gap);
        n.y = anchor.y + Math.floor(slot / 2) * (ab.h + gap);
        if (!list.slice(0, i).some((prev) => overlapRatio(prev, n) > 0.25)) {
          changed = true;
          return;
        }
      }
    });
    if (changed) persist();
    return changed;
  }

  function constrainShotsToViewport() {
    if (state.cam.s < 1) return false;
    const area = canvasArea(), pad = 12, scale = state.cam.s;
    const list = shots();
    if (!list.length) return false;
    const loX = (area.left + pad - state.cam.x) / scale;
    const hiX = (area.right - pad - state.cam.x) / scale;
    const loY = (area.top + pad - state.cam.y) / scale;
    const hiY = (area.bottom - pad - state.cam.y) / scale;
    const bounds = list.reduce((out, n) => {
      const b = box(n);
      out.minX = Math.min(out.minX, n.x);
      out.minY = Math.min(out.minY, n.y);
      out.maxX = Math.max(out.maxX, n.x + b.w);
      out.maxY = Math.max(out.maxY, n.y + b.h);
      return out;
    }, { minX: Infinity, minY: Infinity, maxX: -Infinity, maxY: -Infinity });
    const shift = (min, max, lo, hi) => {
      if (hi < lo) return 0;
      let d = min < lo ? lo - min : 0;
      if (max + d > hi) d = hi - max;
      return d;
    };
    const dx = shift(bounds.minX, bounds.maxX, loX, hiX);
    const dy = shift(bounds.minY, bounds.maxY, loY, hiY);
    let changed = false;
    // A multi-card layout can be larger than the viewport at 100%. Shift the
    // collection once, but do not clamp each card to the same edge (that
    // collapses the minimap into a stack).
    const fitX = bounds.maxX - bounds.minX <= hiX - loX;
    const fitY = bounds.maxY - bounds.minY <= hiY - loY;
    list.forEach((n) => {
      const b = box(n);
      const oldX = n.x, oldY = n.y;
      n.x += dx;
      n.y += dy;
      const maxX = hiX - b.w;
      const maxY = hiY - b.h;
      if (fitX && maxX >= loX) n.x = Math.max(loX, Math.min(n.x, maxX));
      if (fitY && maxY >= loY) n.y = Math.max(loY, Math.min(n.y, maxY));
      changed = changed || n.x !== oldX || n.y !== oldY;
    });
    return changed;
  }

  function newShotPosition(index) {
    const area = canvasArea();
    const scale = state.cam.s || 1;
    const selected = nodeById(state.selected);
    const existing = shots();
    const comfy = readComfyParamsFromUi();
    const bNew = scaleShotBox(comfy.width, comfy.height);
    const pad = 16;
    const gap = 48;
    const minX = (area.left + pad - state.cam.x) / scale;
    const maxX = (area.right - pad - state.cam.x) / scale - bNew.w;
    const minY = (area.top + pad - state.cam.y) / scale;
    const maxY = (area.bottom - pad - state.cam.y) / scale - bNew.h;
    const clamp = (v, lo, hi) => hi < lo ? lo : Math.max(lo, Math.min(v, hi));
    // First card stays in the viewport. Later cards go to the right of the
    // rightmost shot with a full card gap — never a 24px nudge that stacks
    // 360×640 cards, and never clamp them onto the same viewport edge.
    if (!existing.length) {
      const cx = ((area.left + area.right) / 2 - state.cam.x) / scale - bNew.w / 2;
      const cy = ((area.top + area.bottom) / 2 - state.cam.y) / scale - bNew.h / 2;
      return { x: clamp(cx, minX, maxX), y: clamp(cy, minY, maxY) };
    }
    const rightmost = existing.reduce((a, n) => (n.x + box(n).w > a.x + box(a).w ? n : a), existing[0]);
    const anchor = (selected && selected.kind === "shot") ? selected : rightmost;
    return {
      x: rightmost.x + box(rightmost).w + gap,
      y: anchor.y,
    };
  }
  function fitCam() {
    state.cam = { x: 110, y: 28, s: 0.5 };
    applyCam(); persist();
    syncZoomPresets();
  }
  function compactShotsAt100() {
    const list = shots();
    state._overview100 = state.cam.s >= 1;
    if (state.cam.s < 1 || list.length < 2) return false;
    const area = canvasArea();
    const cols = Math.min(list.length, 4);
    const rows = Math.ceil(list.length / cols);
    const gap = 24;
    const widths = list.map((n) => box(n).w);
    const heights = list.map((n) => box(n).h);
    const colW = Array.from({ length: cols }, (_, col) =>
      Math.max(...list.filter((_, i) => i % cols === col).map((_, i) => widths[col + i * cols] || 1)));
    const rowH = Array.from({ length: rows }, (_, row) =>
      Math.max(...list.slice(row * cols, (row + 1) * cols).map((_, i) => heights[row * cols + i] || 1)));
    const totalW = colW.reduce((sum, w) => sum + w, 0) + gap * (cols - 1);
    const startX = Math.max(area.left, area.left + (area.right - area.left - totalW) / 2);
    const colX = colW.map((_, i) => startX + colW.slice(0, i).reduce((sum, w) => sum + w, 0) + gap * i);
    const rowY = rowH.map((_, i) => area.top + rowH.slice(0, i).reduce((sum, h) => sum + h, 0) + gap * i);
    list.forEach((n, i) => {
      const col = i % cols, row = Math.floor(i / cols);
      n.x = colX[col] + (colW[col] - widths[i]) / 2;
      n.y = rowY[row] + (rowH[row] - heights[i]) / 2;
    });
    state.cam.x = 0;
    state.cam.y = 0;
    persist();
    return true;
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
      if (e.target.closest("textarea,[data-textact],[data-node-act],.acts,.node-acts")) {
        if (state.selected !== n.id || e.shiftKey) {
          selectNode(n.id, { shift: !!(e.shiftKey) });
        }
        return;
      }
      e.preventDefault();
      if (state.selected !== n.id || e.shiftKey) {
        selectNode(n.id, { shift: !!(e.shiftKey) });
      }
      if (e.shiftKey) {
        return;
      }
      const w = clientToWorld(e.clientX, e.clientY);
      state.drag = { id: n.id, dx: w.x - n.x, dy: w.y - n.y };
      vp.setPointerCapture(e.pointerId);
      return;
    }
    // empty canvas: 框选 mode starts a marquee instead of panning.
    if (state.canvasTool === "select") {
      state.marquee = { x0: e.clientX, y0: e.clientY, x1: e.clientX, y1: e.clientY };
      vp.setPointerCapture(e.pointerId);
      drawMarquee();
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
    if (state.marquee) {
      state.marquee.x1 = e.clientX;
      state.marquee.y1 = e.clientY;
      drawMarquee();
      return;
    }
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
      if (!n) return;
      n.x = w.x - state.drag.dx;
      n.y = w.y - state.drag.dy;
      const el = world.querySelector('.card[data-id="' + n.id + '"]');
      if (el) {
        el.style.left = n.x + "px";
        el.style.top = n.y + "px";
      }
      drawWires();
      if (n.id === state.selected) positionDock();
      return;
    }
    if (state.pan) {
      state.cam.x = e.clientX - state.pan.x;
      state.cam.y = e.clientY - state.pan.y;
      applyCam();
    }
  });
  vp.addEventListener("pointerup", (e) => {
    if (state.marquee) {
      const m = state.marquee;
      state.marquee = null;
      drawMarquee();
      const x0 = Math.min(m.x0, m.x1), x1 = Math.max(m.x0, m.x1);
      const y0 = Math.min(m.y0, m.y1), y1 = Math.max(m.y0, m.y1);
      if (x1 - x0 > 4 && y1 - y0 > 4) {
        const ids = [];
        world.querySelectorAll(".card").forEach(function (el) {
          const r = el.getBoundingClientRect();
          if (r.left < x1 && r.right > x0 && r.top < y1 && r.bottom > y0) ids.push(el.dataset.id);
        });
        if (ids.length) {
          state.selected = ids[0];
          setMulti(ids);
          renderCards();
          syncSelBar();
          syncGroupRunBtn();
          renderDock();
          setMsg("已框选 " + ids.length + " 个节点", "ok");
        }
      }
      return;
    }
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
        ".dock,.tools,.zoom,.picker,.rail,.atbox,.skillbox,header,.ghost,.minimap,.import-backdrop,.selbar,.shot-bar");
      if (onCanvas && target && target.id !== link.from) {
        const a = nodeById(link.from);
        const src = link.side === "in" ? target : a;
        const dst = link.side === "in" ? a : target;
        if (linkAssetToShot(src, dst)) {
          selectNode(dst.id);
        } else {
          setMsg("连线被拒绝：需连接图片到分镜或提示词卡，且不能形成循环", "bad");
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
    state.link = null; state.snapTarget = null; state.drag = null; state.pan = null; state.marquee = null;
    vp.classList.remove("grabbing");
    drawMarquee();
    if (pointerId != null && vp.hasPointerCapture(pointerId)) vp.releasePointerCapture(pointerId);
    drawWires();
  }
  function drawMarquee() {
    let el = vp.querySelector(".marquee");
    const m = state.marquee;
    if (!m) {
      if (el) el.remove();
      return;
    }
    if (!el) {
      el = document.createElement("div");
      el.className = "marquee";
      vp.appendChild(el);
    }
    const r = vp.getBoundingClientRect();
    const x0 = Math.min(m.x0, m.x1) - r.left, y0 = Math.min(m.y0, m.y1) - r.top;
    el.style.left = Math.round(x0) + "px";
    el.style.top = Math.round(y0) + "px";
    el.style.width = Math.round(Math.abs(m.x1 - m.x0)) + "px";
    el.style.height = Math.round(Math.abs(m.y1 - m.y0)) + "px";
  }
  vp.addEventListener("pointercancel", cancelCanvasGesture);
  vp.addEventListener("lostpointercapture", (e) => { if (state.link) cancelCanvasGesture(e); });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      hideNodeMenu();
      if (state.link) cancelCanvasGesture();
    }
  });
  bindNodeMenuUi();
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

  // v0821o136-seko: double-click blank canvas → create 空白节点 there + open Composer bound to it.
  function createBlankShotAt(wx, wy) {
    const n = shots().length;
    const id = uid("shot");
    state.mode = "image";
    const shot = {
      id: id, kind: "shot", title: "分镜" + (n + 1),
      x: wx, y: wy,
      url: "", firstFrameId: "",
      prompt: "",
      mode: "image",
      composer: { backend: ($("backend") && $("backend").value) || "civitai", service: "", mode: "image", fields: {}, loras: [] },
    };
    state.nodes.push(shot);
    const b = box(shot);
    shot.x = Math.round(wx - b.w / 2);
    shot.y = Math.round(wy - b.h / 2);
    renderCards();
    drawWires();
    selectNode(id, { preserveLayout: true });
    state.dockMode = "expanded";
    renderDock();
    persist();
    setMsg("已创建 " + shot.title + " · 在 Composer 写提示词后点 ↑", "ok");
    const p = $("prompt");
    if (p) { try { p.focus(); } catch (_) {} }
    return shot;
  }
  vp.addEventListener("dblclick", (e) => {
    if (e.button != null && e.button !== 0) return;
    // pointer capture retargets dblclick to #viewport after a card pointerdown —
    // hit-test with elementFromPoint instead of trusting e.target.
    const hit = document.elementFromPoint(e.clientX, e.clientY);
    const t = (hit && hit.closest) ? hit : e.target;
    if (t && t.closest && t.closest(".dock,.tools,.zoom,.picker,.rail,.atbox,.skillbox,header,.ghost,.minimap,.import-backdrop,.selbar,.shot-bar,.card,.group-bound,path.edge,.composer-chip,.canvas-tip,.marquee")) return;
    const w = clientToWorld(e.clientX, e.clientY);
    if (!Number.isFinite(w.x) || !Number.isFinite(w.y)) return;
    if (hitNode(w.x, w.y)) return;
    e.preventDefault();
    createBlankShotAt(w.x, w.y);
  });

  world.addEventListener("input", (e) => {
    const ta = e.target.closest("textarea[data-text]");
    if (!ta) return;
    const n = nodeById(ta.dataset.id);
    if (n && n.kind === "text") {
      n.text = ta.value;
      if (state.selected !== n.id) {
        state.selected = n.id;
        if (typeof setMulti === "function") setMulti([n.id]);
      }
      syncTextToShots(n);
      persist();
      const caret = ta.selectionStart || ta.value.length;
      const before = String(ta.value || "").slice(0, caret);
      const at = before.lastIndexOf("@");
      if (at >= 0 && !/[\s\n]/.test(before.slice(at + 1))) {
        showAtbox(before.slice(at + 1));
      } else {
        hideAtbox();
      }
    }
  });
  world.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-textact]");
    if (!btn) return;
    e.preventDefault();
    e.stopPropagation();
    const n = nodeById(btn.dataset.id);
    if (!n) return;
    if (btn.dataset.textact === "gen") {
      generateFromText(n);
    } else if (btn.dataset.textact === "rev") {
      const src = connectedNodes(n.id).find(isImageSource);
      if (src) {
        setMsg("正在反推…");
        reverseFromImage(src).then((node) => {
          if (node) setMsg("反推完成，提示词已更新", "ok");
        });
      } else setMsg("这张提示词卡还没连图片", "warn");
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
    if (act.dataset.act === "pick") openImportModal();
    if (act.dataset.act === "upload-last") {
      state._uploadLastFrame = true;
      if ($("file")) $("file").click();
      return;
    }
    if (act.dataset.act === "pick-last") {
      showLastPop();
      return;
    }
    if (act.dataset.act === "clear-last") {
      const shot = nodeById(state.selected);
      if (shot) { shot.lastFrameId = ""; renderDock(); persist(); }
      return;
    }
    if (act.dataset.act === "apply-edit-sibling") {
      if (!applyEditSibling()) {
        setMsg(refUnusedGateMessage(nodeById(state.selected)) || "目录无 Edit 兄弟模型，请改选图生图或断开参考（不静默忽略）", "bad");
      }
      return;
    }
    if (act.dataset.act === "capacity-rematch") {
      if (!applyCapacityRematch()) {
        /* applyCapacityRematch already setMsg */
      }
      try { persist(); } catch (_) {}
      return;
    }
    if (act.dataset.act === "lora-capability-rematch") {
      applyLoraCapabilityRematch();
      try { persist(); } catch (_) {}
      return;
    }
    if (act.dataset.act === "fill-refs-cap") {
      const shot = nodeById(state.selected);
      if (!shot || shot.kind !== "shot") return;
      if (!catalogEatsRefs(catalogItemForService())) {
        setMsg(refUnusedGateMessage(shot) || "文生图不吃参考，请先一键改选 Edit", "bad");
        return;
      }
      const added = fillRefSlotsToCap(shot);
      renderCards(); drawWires(); renderDock(); persist();
      const cap = maxRefCount(catalogItemForService());
      const n = countRefUrls(null, shot).length;
      setMsg("灌满参考 " + n + "/" + cap + (added ? (" · 新加 " + added) : " · 已满"), n > cap ? "bad" : (n >= cap ? "ok" : "warn"));
      return;
    }
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
    if (node && (!hit || (hit.kind !== "shot" && hit.kind !== "text"))) {
      node.x = w.x - 66;
      node.y = w.y - 40;
    }
    if (node && hit && (hit.kind === "shot" || hit.kind === "text")) {
      linkAssetToShot(node, hit);
      selectNode(hit.id);
    } else if (node) {
      selectNode(node.id);
    }
    renderCards(); drawWires(); renderDock(); persist();
  }

  if ($("chatRail")) {
    $("chatRail").addEventListener("click", (e) => {
      const act = e.target.closest("[data-act]");
      if (!act) return;
      if (act.dataset.act === "upload") {
        if ($("file")) $("file").click();
        return;
      }
      if (act.dataset.act === "pick") {
        openImportModal();
      }
    });
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
        const item = railHistory()[Number(histBtn.dataset.hist)];
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
      if (up && up.dataset.act === "upload") { if ($("file")) $("file").click(); return; }
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
        const item = railHistory()[Number(histPin.dataset.histPin)];
        const shot = nodeById(state.selected);
        if (item && item.url && shot && shot.kind === "shot") {
          // 接到此镜 → write media onto the selected shot card (same as auto writeback).
          // Keep History row; do not require a canvas clone for the card face.
          writebackResult(shot, item.url);
          renderCards(); drawWires(); renderDock(); persist();
        }
      }
    });
  }

  $("file").addEventListener("change", async () => {
    const input = $("file");
    const files = input && input.files;
    if (!files || !files.length) return;
    if (state._uploadLastFrame) {
      state._uploadLastFrame = false;
      const shot = nodeById(state.selected);
      if (!shot || shot.kind !== "shot") { setMsg("先点一个分镜再挂尾帧", "warn"); return; }
      const f = files[0];
      input.value = "";
      setMsg("正在上传尾帧…");
      uploadOut(f).then(function (url) {
        if (!url) return;
        const id = uid("asset");
        const node = { id: id, kind: "character", title: (f.name || "尾帧").replace(/\.[^.]+$/, ""), x: shot.x - 160, y: shot.y + 48, url: url };
        state.nodes.push(node);
        linkAssetToShot(node, shot);
        shot.lastFrameId = id;
        persist(); persistServer();
        renderCards(); drawWires(); renderDock();
        setMsg("尾帧已挂上 · 确认后点 ↑", "ok");
      }).catch(function (e) {
        setMsg("上传失败：" + ((e && e.message) || e), "bad");
      });
      return;
    }
    if (state._editorAudioField) {
      const field = state._editorAudioField;
      state._editorAudioField = "";
      const shot = nodeById(state.editor && state.editor.activeShotId) || nodeById(state.selected);
      if (!shot) { setMsg("先选一个分镜再上传音轨", "warn"); return; }
      const f = files[0];
      input.value = "";
      setMsg("正在上传音轨…");
      uploadOut(f).then(function (url) {
        if (!url) return;
        shot[field] = url;
        persist();
        renderWorkspace();
        setMsg("音轨已挂上这一镜", "ok");
      }).catch(function (e) {
        setMsg("上传失败：" + ((e && e.message) || e), "bad");
      });
      return;
    }
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
      if (shot && shot.kind === "shot" && !state._uploadFree) {
        created.forEach(function (node) { linkAssetToShot(node, shot); });
        try { await smartMatchService({ announce: true }); } catch (_) {}
      } else if (created.length) {
        selectNode(created[created.length - 1].id);
      }
      state._uploadFree = false;
      renderCards(); drawWires(); renderDock();
      if (typeof renderChatRail === "function") renderChatRail();
      persist();
      persistServer();
      if (created.length) {
        const live = nodeById(state.selected);
        const frameReady = !!(live && live.kind === "shot" && state.mode === "video" && typeof frameAsset === "function" && frameAsset(live));
        const already = ($("msg") && $("msg").textContent) || "";
        if (already.indexOf("已智能匹配") >= 0) { /* keep rematch copy */ }
        else if (frameReady) setMsg("首帧已就绪 · 可生成", "ok");
        else setMsg("已上传到资产库" + (created.length > 1 ? (" · " + created.length + " 张") : ""), "ok");
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
    const n = (typeof composerShot === "function" && composerShot()) || nodeById(state.selected);
    if (n && n.kind === "shot") {
      n.prompt = $("prompt").value;
      syncShotToText(n);
      persist();
    } else if (n && n.kind === "text") {
      n.text = $("prompt").value;
      syncTextToShots(n);
      persist();
    }
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
    if (typeof loadCatalog === "function") {
      return loadCatalog().then(async function () {
        try { await smartMatchService({ announce: true }); } catch (_) {}
        renderCards();
        drawWires();
        renderDock();
        persist();
      });
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
      if (id === "aspect" || id === "res") applyAspectToSize();
      else if (id === "width" || id === "height") {
        syncAspectFromSize($("width") && $("width").value, $("height") && $("height").value);
        persistShotFrame(nodeById(state.selected));
      } else if (COMFY_PARAM_IDS.indexOf(id) >= 0) {
        writeComfyParamsToShot(nodeById(state.selected));
      }
      persist();
      if (id === "duration" && state.mode === "video") {
        renderCards(); drawWires(); positionDock();
      }
      if (id === "aspect" || id === "res" || id === "width" || id === "height") {
        renderCards(); drawWires(); positionDock();
      }
      if (id === "backend" || id === "service") applyServiceConstraints();
      if (id === "duration") paramGateMessage();
    });
    if ($(id) && COMFY_PARAM_IDS.indexOf(id) >= 0) {
      $(id).addEventListener("input", () => {
        if (id === "seed" && $("seed")) $("seed").title = String($("seed").value || "");
        if (id === "width" || id === "height") {
          syncAspectFromSize($("width") && $("width").value, $("height") && $("height").value);
          persistShotFrame(nodeById(state.selected));
          renderCards(); drawWires(); positionDock();
        } else {
          writeComfyParamsToShot(nodeById(state.selected));
        }
        persist();
      });
    }
  });

  function setMsg(t, cls, excerpt) {
    const el = $("msg");
    if (!el) return;
    el.className = "msg" + (cls ? " " + cls : "");
    const text = t == null ? "" : String(t);
    const extra = excerpt == null || excerpt === "" ? "" : String(excerpt);
    el.textContent = "";
    if (!text && !extra) return;
    const main = document.createElement("span");
    main.className = "msg-main";
    main.textContent = text;
    el.appendChild(main);
    if (extra && extra !== text) {
      const d = document.createElement("details");
      d.className = "msg-more";
      const s = document.createElement("summary");
      s.textContent = "详情";
      const pre = document.createElement("pre");
      pre.className = "msg-excerpt";
      pre.textContent = extra;
      d.appendChild(s);
      d.appendChild(pre);
      el.appendChild(d);
    }
  }

  // v0821k: sticky click-ack — successors keep「已点生成」visible (never wipe bare)
  function setAckMsg(rest, cls) {
    const body = String(rest == null ? "" : rest).replace(/^已点生成(\s*·\s*)?/, "");
    setMsg(body ? ("已点生成 · " + body) : "已点生成", cls);
  }

  function shortErrExcerpt(s, max) {
    const t = String(s || "").replace(/\s+/g, " ").trim();
    const n = max == null ? 180 : max;
    if (!t) return "";
    return t.length <= n ? t : (t.slice(0, n) + "…");
  }
  function isBillingErrText(s) {
    const t = String(s || "");
    if (!t) return false;
    if (/额度不足|账单错误|账单失败/.test(t)) return true;
    return /\b(402)\b/.test(t)
      || /\b(payment|billing|invoice|quota|credit|credits)\b/i.test(t)
      || /insufficient(?:\s+\w+){0,4}\s+(funds|credit|quota)/i.test(t)
      || /exceeded.{0,32}(quota|limit|credit)/i.test(t)
      || /card(?:\s+was)?\s+declined/i.test(t)
      || /past[\s_-]?due/i.test(t);
  }
  function unwrapErrText(e, depth) {
    if (depth > 6) return "";
    if (e == null || e === "") return "";
    if (typeof e === "string") return e;
    if (typeof e === "number" || typeof e === "boolean") return String(e);
    if (e instanceof Error) {
      if (e.message) return e.message;
      return String(e);
    }
    if (typeof e === "object") {
      if (e.status === 402 || e.statusCode === 402 || e.code === 402) {
        const inner402 = unwrapErrText(e.error || e.message || e.detail, depth + 1);
        return inner402 || "HTTP 402";
      }
      const keys = ["error", "message", "detail", "msg", "reason", "description", "body"];
      for (let i = 0; i < keys.length; i++) {
        const v = e[keys[i]];
        if (v == null || v === e) continue;
        const inner = unwrapErrText(v, depth + 1);
        if (inner) return inner;
      }
      try {
        const s = JSON.stringify(e);
        if (s && s !== "{}" && s !== "null") return s;
      } catch (_) {}
      return String(e);
    }
    return String(e);
  }
  function humanizeFailText(raw) {
    const t = String(raw == null ? "" : raw).replace(/\s+/g, " ").trim();
    if (!t) return "";
    // Already short Chinese user copy — keep.
    if (/^[\u4e00-\u9fff]/.test(t) && !/[A-Za-z]{4,}/.test(t)) return t;
    const lower = t.toLowerCase();
    // Fal content_policy_violation / content checker (often "body.prompt: …")
    if (/content_policy_violation/.test(lower)
        || /flagged by a content checker/.test(lower)
        || /contained material flagged/.test(lower)
        || (/content.?policy/.test(lower) && /violat/.test(lower))) {
      return "内容未通过安全审核";
    }
    if (/no_media_generated/.test(lower)
        || /did not generate the expected output/.test(lower)) {
      return "模型未产出可用结果";
    }
    if (/file_download_error/.test(lower) || /\bfile download error\b/.test(lower)) {
      return "资源下载失败（链接不可达）";
    }
    if (/image_load_error/.test(lower) || /\bimage load error\b/.test(lower)) {
      return "图片加载失败";
    }
    if (/image_too_large/.test(lower) || /\bimage too large\b/.test(lower)) {
      return "图片尺寸过大";
    }
    if (/image_too_small/.test(lower) || /\bimage too small\b/.test(lower)) {
      return "图片尺寸过小";
    }
    if (/face_detection_error/.test(lower) || /could not detect face/.test(lower)) {
      return "未检测到人脸";
    }
    if (/generation_timeout/.test(lower) || /\bgeneration timeout\b/.test(lower)) {
      return "生成超时";
    }
    if (/downstream_service_unavailable/.test(lower)) {
      return "下游服务暂不可用";
    }
    if (/downstream_service_error/.test(lower)) {
      return "下游服务错误";
    }
    if (/internal_server_error/.test(lower) || /\binternal server error\b/.test(lower)) {
      return "服务端内部错误";
    }
    if (/feature_not_supported/.test(lower) || /\bfeature not supported\b/.test(lower)) {
      return "当前端点不支持该功能";
    }
    // Field required / pydantic "type":"missing" / Fal loc body.<field>: Field required.
    // Do NOT use bare \bmissing\b + body. — false-positives prose like
    // "missing dependency in body.build" or "The type: missing widget in body.build".
    if (/\bfield required\b/.test(lower)
        || /\btype["']?\s*:\s*["']missing["']/.test(lower)
        || /is required but was not provided/.test(lower)
        || /\bbody\.\w+\s*:\s*field required\b/.test(lower)) {
      if (/prompt/.test(lower)) return "缺少提示词（服务端校验）";
      if (/image|frame|start_image|first_frame/.test(lower)) return "缺少图片输入（服务端校验）";
      return "请求字段缺失（服务端校验）";
    }
    // Strip body.loc noise when remaining msg is still English noise
    const locm = t.match(/^body(?:\.[A-Za-z0-9_]+)*:\s*(.+)$/i);
    if (locm) {
      const rest = locm[1].trim();
      const mapped = humanizeFailText(rest);
      if (mapped && mapped !== rest) return mapped;
      if (/^field required$/i.test(rest)) return "请求字段缺失（服务端校验）";
    }
    return t;
  }
  function formatErrInfo(e) {
    const raw = unwrapErrText(e, 0) || "未知错误";
    const billing = isBillingErrText(raw) || (e && typeof e === "object" && (e.status === 402 || e.statusCode === 402));
    if (billing) {
      return { text: "额度不足或账单错误", excerpt: shortErrExcerpt(raw, 180), billing: true };
    }
    const mapped = humanizeFailText(raw);
    const text = (mapped && mapped !== raw) ? mapped : (raw.length > 240 ? (raw.slice(0, 240) + "…") : raw);
    let excerpt = "";
    if (mapped && mapped !== raw) excerpt = shortErrExcerpt(raw, 220);
    else if (raw.length > 240) excerpt = shortErrExcerpt(raw, 180);
    return { text: text || "未知错误", excerpt: excerpt, billing: false };
  }
  function formatErr(e) {
    return formatErrInfo(e).text;
  }
  function clearShotError(shot) {
    if (!shot) return;
    shot._error = "";
    delete shot._errorDetail;
  }
  function paintShotFail(shot, err, cls) {
    const info = formatErrInfo(err);
    const tone = cls || "bad";
    if (shot && shot.kind === "shot") {
      shot._error = info.text;
      if (info.excerpt) shot._errorDetail = info.excerpt;
      else delete shot._errorDetail;
    }
    setMsg(info.text, tone, info.excerpt);
    state.dockMode = "expanded";
    renderCards();
    renderDock();
    if (typeof keepComposerPromptVisible === "function") keepComposerPromptVisible();
    return info.text;
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
  // v0821o36: LoRA-family AIR only. Checkpoint / diffusionmodel / diffuser never count as LoRA chips.
  function isLoraAir(air) {
    const s = String(air || "").trim();
    if (!s) return false;
    const low = s.toLowerCase();
    // Mirror providers/civitai._LORA_TYPES resource tokens in AIR (urn:air:{eco}:{type}:…).
    if (/:(lora|lycoris|locon|loha|lokr|dora)(:|\||$)/i.test(low)) return true;
    if (/:(textualinversion|embedding)(:|\||$)/i.test(low)) return true;
    return false;
  }
  function isNonLoraModelAir(air) {
    const s = String(air || "").trim();
    if (!s) return false;
    return /:(checkpoint|diffusionmodel|diffuser)(:|\||$)/i.test(s);
  }
  /** True when an AIR-shaped string must not live in state.loras / outbound loras[]. */
  function shouldDropNonLoraAir(air, diffusionModel) {
    const a = String(air || "").trim();
    if (!a) return false;
    const dm = String(diffusionModel || "").trim();
    if (dm && a === dm) return true;
    if (isNonLoraModelAir(a)) return true;
    if ((/^urn:air:/i.test(a) || looksAir(a)) && !isLoraAir(a)) return true;
    return false;
  }
  function loraDownloadUrl(v) {
    if (!v) return "";
    const vid = loraVersionId(v);
    function reconcile(url) {
      const u = String(url || "");
      const m = u.match(/^(https?:\/\/(?:www\.)?civitai\.com\/api\/download\/models\/)(\d+)(.*)$/i);
      // Prefer AIR/versionId over a stale sibling download path (2653078 vs 3071582).
      if (m && vid && String(m[2]) !== String(vid)) return m[1] + vid + m[3];
      return u;
    }
    if (v.path && !looksAir(v.path)) return reconcile(v.path);
    if (v.downloadUrl && !looksAir(v.downloadUrl)) return reconcile(v.downloadUrl);
    if (v.url && !looksAir(v.url) && isHttpUrl(v.url)) return reconcile(v.url);
    const files = v.files || [];
    for (let i = 0; i < files.length; i++) {
      const f = files[i];
      if (f && f.downloadUrl && !looksAir(f.downloadUrl)) return reconcile(f.downloadUrl);
    }
    // versionId / AIR @version before bare id (search-hit id is modelId).
    if (vid && /^\d+$/.test(String(vid))) return "https://civitai.com/api/download/models/" + vid;
    if (v.id && /^\d+$/.test(String(v.id))) return "https://civitai.com/api/download/models/" + v.id;
    return "";
  }
  function loraVersionId(l) {
    if (!l) return "";
    // Prefer AIR @version over stale sibling versionId/path (2653078 vs 3071582).
    const air = String(l.air || "");
    const m = air.match(/@(\d+)\s*$/) || air.match(/civitai:\d+@(\d+)/i);
    if (m) return m[1];
    if (l.versionId != null && /^\d+$/.test(String(l.versionId).trim())) return String(l.versionId).trim();
    if (l.modelVersionId != null && /^\d+$/.test(String(l.modelVersionId).trim())) return String(l.modelVersionId).trim();
    return "";
  }
  function loraModelId(l) {
    if (!l) return "";
    if (l.modelId != null && String(l.modelId).trim()) return String(l.modelId).trim();
    const air = String(l.air || "");
    const m = air.match(/civitai:(\d+)@/i) || air.match(/civitai:(\d+)\s*$/i);
    return m ? m[1] : "";
  }
  function loraHasDirectPath(l) {
    if (!l) return false;
    if (l.path && !looksAir(l.path)) return true;
    if (l.downloadUrl && !looksAir(l.downloadUrl)) return true;
    if (l.versionId && /^\d+$/.test(String(l.versionId))) return true;
    return false;
  }
  // Keep in lockstep with providers/civitai.py _LORA_TYPES. Checkpoint is not here.
  const LORA_TYPES = new Set([
    "LORA",
    "LORAS",
    "LOCON",
    "LOHA",
    "LOKR",
    "DORA",
    "LYCORIS",
    "TEXTUALINVERSION",
  ]);
  function normalizeLoraType(value) {
    return String(value == null ? "" : value)
      .toUpperCase()
      .replace(/[\s_]/g, "");
  }
  // Keep in lockstep with providers/civitai.py _parse_civitai_air.
  function airKind(air) {
    const s = String(air || "").trim();
    const m = s.match(/(?:urn:)?(?:air:)?[^:]+:([^:]+):civitai:\d+/i);
    return m ? normalizeLoraType(m[1]) : "";
  }
  // Missing type is allowed for URL / hub repo. AIR kind is still checked, so
  // a Checkpoint URN cannot skip the gate just because type was omitted.
  function loraTypeUsable(type, air) {
    const t = normalizeLoraType(type);
    if (t && !LORA_TYPES.has(t)) return false;
    const kind = airKind(air);
    if (kind && !LORA_TYPES.has(kind)) return false;
    return true;
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
    // modelId only from the explicit field — search-hit `id` is a modelId and
    // collides with versionId space (122359 is both). type comes from
    // /api/model-version (model.type = LORA / Checkpoint / …).
    const modelId = String(v.modelId || "");
    const type = String(
      v.type ||
        (v.model && typeof v.model === "object" && v.model.type) ||
        ""
    );
    return {
      air: air,
      path: path,
      downloadUrl: v.downloadUrl || path,
      versionId: v.versionId || loraVersionId(v) || (v.id && /^\d+$/.test(String(v.id)) ? String(v.id) : ""),
      modelId: modelId,
      type: type,
      strength: strength,
      scale: strength,
      strengthMissing: strengthMissing,
      name: name,
      status: v.status || "",
    };
  }
  function falEndpointTakesLora(item) {
    item = item || {};
    const eid = String(item.id || item.name || "").toLowerCase();
    const name = String(item.name || "").toLowerCase();
    const fcat = String(item.falCategory || "").toLowerCase();
    const tags = (item.tags || []).map(function (t) { return String(t).toLowerCase(); });
    const fields = [].concat(item.required || [], item.optional || []).map(function (x) {
      return String(x).toLowerCase();
    });
    if (eid.indexOf("lora") >= 0 || name.indexOf("lora") >= 0) return true;
    if (fields.some(function (k) {
      return k === "loras" || k === "lora" || k === "lora_url" || k === "lora_path";
    })) return true;
    if (fcat.indexOf("lora") >= 0 || tags.some(function (t) { return t.indexOf("lora") >= 0; })) return true;
    return false;
  }
  function catalogItemSupportsLora(it) {
    const hasArg = arguments.length > 0;
    it = (hasArg ? it : catalogItemForService());
    const be = currentBackend();
    const caps = catalogCaps();
    // o54: when scoring another catalog row, honor that row's supportsLora (ignore current service caps deny).
    if (hasArg && it) {
      if (it.supportsLora === false) return false;
      if (it.capabilities && it.capabilities.supportsLora === false) return false;
      if (it.capabilities && it.capabilities.lora === "none") return false;
      if (it.supportsLora === true) return true;
      if (it.capabilities && it.capabilities.supportsLora === true) return true;
    }
    if (caps && caps.lora === "none") return false;
    if (it && it.supportsLora === false) return false;
    if (caps && caps.supportsLora === false) return false;
    if (it && it.supportsLora === true) return true;
    const sid = String((it && (it.id || it.name)) || ($("service") && $("service").value) || "");
    if (be === "fal") {
      if (falEndpointTakesLora(it || { id: sid })) return true;
      if (sid === "fal-ai/krea-2/turbo" || sid === "fal-ai/z-image/turbo") return true;
      if (!sid) return true;
      return false;
    }
    if (be === "huggingface") {
      if (it && Object.prototype.hasOwnProperty.call(it, "supportsLora")) return !!it.supportsLora;
      if (/lora/i.test(sid) || /lora/i.test(String((it && it.name) || ""))) return true;
      return true;
    }
    if (isNanogptBe()) {
      if (it && Object.prototype.hasOwnProperty.call(it, "supportsLora")) return !!it.supportsLora;
      return true;
    }
    return true;
  }
  function showLoraBlock() {
    const be = currentBackend();
    const chips = Array.isArray(state.loras) && state.loras.length > 0;
    // o54: chips always visible (rematch UI) even when !supportsLora — never silent-drop
    if (chips) return true;
    if (!catalogItemSupportsLora()) return false;
    if (be === "fal" || be === "civitai" || be === "nano-gpt") return true;
    if (isModelscopeBe() || be === "huggingface") return true;
    return false;
  }
  function syncLoraPlaceholders() {
    const be = currentBackend();
    const q = $("loraQ");
    const lbl = $("loraQLbl");
    const hint = $("loraHint");
    const filt = $("serviceFilter");
    if (filt) {
      filt.placeholder = ({
        civitai: "搜索 Civitai 模型",
        fal: "搜索 Fal 模型",
        huggingface: "搜索 HF 模型",
        "modelscope-ai": "搜索魔搭 AI 模型",
        "modelscope-cn": "搜索魔搭 CN 模型",
        "nano-gpt": "搜索 Nano 模型",
      })[be] || "搜索当前家的模型";
    }
    const adapt = (typeof window !== "undefined") ? window.ComposerFieldAdapt : null;
    const shape = adapt && typeof adapt.loraShape === "function" ? adapt.loraShape(be) : "";
    if (be === "fal" || isNanogptBe() || be === "huggingface") {
      if (q) q.placeholder = "URL、HF owner/name、名字或 version id";
      if (lbl) lbl.textContent = "LoRA";
    } else if (isModelscopeBe()) {
      if (q) q.placeholder = "魔搭 owner/repo，例如 Qwen/Qwen-Image";
      if (lbl) lbl.textContent = "LoRA";
    } else {
      if (q) q.placeholder = "名字 / version id / AIR";
      if (lbl) lbl.textContent = "LoRA";
    }
    if (hint) {
      if (isModelscopeBe()) {
        hint.textContent = "请填写魔搭仓库名，例如 Qwen/Qwen-Image";
        hint.classList.add("show");
        hint.classList.remove("lora-unverified");
      } else if (be === "huggingface") {
        const shapeHint = adapt && adapt.loraShapeHintText ? adapt.loraShapeHintText(be) : "";
        hint.textContent = shapeHint || "可搜索模型名，或粘贴 Hugging Face 仓库 / 直链 · unverified";
        hint.classList.add("show");
        hint.classList.add("lora-unverified");
      } else if (adapt && typeof adapt.loraShapeHintText === "function") {
        hint.textContent = adapt.loraShapeHintText(be);
        hint.classList.add("show");
        hint.classList.remove("lora-unverified");
      } else {
        hint.textContent = "";
        hint.classList.remove("show");
        hint.classList.remove("lora-unverified");
      }
    }
  }
  // v0821n3: prefer air URN in chip subtitle so civitai outbound id is visible (path hid it)
  function loraChipSubtitle(l) {
    l = l || {};
    const name = String(l.name || "").trim();
    const air = String(l.air || "").trim();
    const vid = String(l.versionId || loraVersionId(l) || "").trim();
    let sub = air || String(l.path || l.downloadUrl || l.url || "").trim();
    if (!sub || sub === name) {
      if (air && air !== name) return air;
      if (vid) return "versionId " + vid;
      return "无 AIR";
    }
    return sub;
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
          '" placeholder="' +
          ((typeof window !== "undefined" && window.ComposerFieldAdapt &&
            typeof window.ComposerFieldAdapt.strengthPlaceholder === "function")
            ? window.ComposerFieldAdapt.strengthPlaceholder() : "未填") +
          '" data-lora-str="' + i + '" title="' +
          ((typeof window !== "undefined" && window.ComposerFieldAdapt &&
            typeof window.ComposerFieldAdapt.strengthTitle === "function")
            ? window.ComposerFieldAdapt.strengthTitle() : "strength 未填：出站省略数值（不写 1.0/0.8）") +
          '" aria-label="strength">' +
        '<button type="button" class="lora-del" data-lora-del="' + i + '">删</button>' +
        '</div></div>';
    }).join("");
  }
  // v0915seko-align-lorafold: LoRA 面板默认收起对齐 Seko 的紧凑 Composer；
  // 有芯片或不匹配告警时自动展开（不藏状态）；手动开关优先级最高（会话级）。
  let loraFoldOpen = null;
  function applyLoraFold(block, chips) {
    const open = (loraFoldOpen !== null) ? loraFoldOpen : !!chips;
    block.classList.toggle("lora-mini", !open);
    const fold = $("loraFold");
    if (fold) {
      fold.textContent = open ? "▾" : "▸";
      fold.setAttribute("aria-expanded", open ? "true" : "false");
    }
  }
  function syncLoraUi() {
    const block = $("loraBlock");
    if (!block) return;
    const show = showLoraBlock();
    block.classList.toggle("hidden", !show);
    const chips = Array.isArray(state.loras) && state.loras.length > 0;
    const support = catalogItemSupportsLora();
    block.classList.toggle("lora-unsupported", !!(chips && !support));
    applyLoraFold(block, chips);
    const row = block.querySelector(".lora-row");
    if (row) {
      // Keep search usable so 跨家检索 → 加芯片 → 一键匹配 can run on a non-LoRA model.
      row.classList.remove("hidden");
      row.removeAttribute("aria-hidden");
      if ($("loraQ")) $("loraQ").disabled = false;
      if ($("searchLora")) $("searchLora").disabled = false;
    }
    const hd = block.querySelector(".lora-hd");
    let btn = block.querySelector('[data-act="lora-capability-rematch"]');
    if (chips && !support) {
      if (!btn && hd) {
        btn = document.createElement("button");
        btn.type = "button";
        btn.className = "chip-btn lora-capability-rematch";
        btn.setAttribute("data-act", "lora-capability-rematch");
        btn.textContent = "一键匹配";
        btn.title = "改选同后端支持 LoRA 的模型（不静默丢芯片）";
        hd.appendChild(btn);
      }
      if (btn) btn.hidden = false;
    } else if (btn) {
      btn.hidden = true;
    }
    syncLoraPlaceholders();
    renderLoras();
  }
  function setLoraNote(text, bad) {
    const el = $("loraHint");
    if (!el) return;
    if (!text) {
      el.classList.remove("bad");
      syncLoraPlaceholders();
      return;
    }
    el.textContent = text;
    el.classList.add("show");
    el.classList.toggle("bad", !!bad);
  }
  async function fetchLoraVersion(versionId) {
    const response = await fetch("/api/model-version/" + encodeURIComponent(versionId));
    const payload = await response.json();
    if (!response.ok || payload.error)
      throw new Error(payload.error || "HTTP " + response.status);
    return payload;
  }
  // Civitai generate only accepts air. Rows that only have versionId must
  // resolve before they enter the list; failure is a visible reject, not a drop.
  async function resolveLoraAir(row) {
    if (!row || row.air || !row.versionId) return row;
    if (currentBackend() !== "civitai") return row;
    try {
      const data = await fetchLoraVersion(row.versionId);
      const air = String((data && data.air) || "");
      const type = String((data && data.type) || row.type || "");
      const modelId = String((data && data.modelId) || row.modelId || "");
      const name = row.name && row.name !== "LoRA"
        ? row.name
        : (data && (data.model || data.name)) || row.name;
      return Object.assign({}, row, {
        air: air || row.air,
        type: type,
        modelId: modelId,
        name: name,
        airError: (data && data.airError) || "",
      });
    } catch (_) {
      return row;
    }
  }
  async function addLora(v) {
    const needRematch = !catalogItemSupportsLora();
    const draft = normalizeLora(v);
    if (!loraTypeUsable(draft.type, draft.air)) {
      const kind = normalizeLoraType(draft.type) || airKind(draft.air) || "非 LoRA";
      setLoraNote(
        "version " +
          (draft.versionId || draft.name) +
          " 是 " +
          kind +
          "（" +
          (draft.name || "无名") +
          "），不是 LoRA，没加进来",
        true
      );
      return false;
    }
    const row = await resolveLoraAir(draft);
    if (!loraTypeUsable(row.type, row.air)) {
      const kind = normalizeLoraType(row.type) || airKind(row.air) || "非 LoRA";
      setLoraNote(
        "version " +
          (row.versionId || row.name) +
          " 是 " +
          kind +
          "（" +
          (row.name || "无名") +
          "），不是 LoRA，没加进来",
        true
      );
      return false;
    }
    if (currentBackend() === "civitai" && row.versionId && !row.air) {
      setLoraNote(
        "version " +
          row.versionId +
          " 换不出 air，civitai 生成链带不走这条，没加进来",
        true
      );
      return false;
    }
    if (!row.air && !row.path && !row.versionId) return false;
    if (shouldDropNonLoraAir(row.air)) {
      setLoraNote("已拒绝非 LoRA AIR（checkpoint/diffuser 不进 loras[]）", true);
      return false;
    }

    const be = currentBackend();
    // v0821o135: Civitai 有底模概念——LoRA 底模家族与当前 checkpoint 家族不符时硬拒，不静默加。
    // Fal/Nano 走 http 直链、无 baseModel 概念，保持现有"无直链/重映射"逻辑，不在此发明校验。
    if (be === "civitai" && typeof SmartFamilyMatch !== "undefined" && SmartFamilyMatch.familyFromAir) {
      const loraFam = SmartFamilyMatch.familyFromAir(row.air)
        || SmartFamilyMatch.inferModelFamily([(v && v.baseModel), row.baseModel, row.name].filter(Boolean).join(" ")) || "";
      const ckptFam = currentCheckpointFamily();
      if (loraFam && ckptFam && !SmartFamilyMatch.familyCompatible(ckptFam, loraFam)) {
        setLoraNote("该 LoRA 底模是 " + loraFam + "，当前模型是 " + ckptFam + "，不匹配", true);
        return false;
      }
    }
    if ((be === "fal" || isNanogptBe()) && !loraHasDirectPath(row)) row.status = "无直链";
    if (v && v.source && !row.source) row.source = v.source;
    if (v && v.backend && !row.backend) row.backend = v.backend;
    if (!Array.isArray(state.loras)) state.loras = [];
    const key = row.air || row.path || row.versionId;
    if (state.loras.some(function (it) { return (it.air || it.path || it.versionId) === key; })) {
      setLoraNote("已经加过这条 LoRA 了", true);
      return false;
    }
    state.loras.push(row);
    setLoraNote(needRematch ? "当前模型不支持 LoRA，已加芯片 · 正在匹配能吃 LoRA 的端点" : "");
    renderLoras();
    if ($("loraHits")) $("loraHits").innerHTML = "";
    persist();
    if ((be === "fal" || isNanogptBe()) && row.air && !row.path) resolveLorasForBackend();
    if (needRematch) {
      try { applyLoraCapabilityRematch(); } catch (_) {}
    }
    return true;
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
  function capabilityForCatalogItem(item) {
    const list = state._capabilities || [];
    if (!item) return null;
    const sid = String(item.id || item.name || "");
    if (!sid) return null;
    for (let i = 0; i < list.length; i++) {
      const cap = list[i];
      const rid = cap && cap.raw && cap.raw.id;
      if (rid && String(rid) === sid) return cap;
    }
    return null;
  }
  function modelConstraint(item, name) {
    const cap = capabilityForCatalogItem(item) || (item && item.capability) || null;
    const c = (cap && cap.constraints) || {};
    if (c[name] != null && typeof c[name] === "object") return c[name];
    const extra = cap && cap.extraFlags && cap.extraFlags[name];
    if (extra && typeof extra === "object") return extra;
    return null;
  }
  function durationConstraint() {
    const sid = $("service") && $("service").value;
    const it = catalogItemForService() || (sid ? { id: sid } : null);
    const fromModel = modelConstraint(it, "duration");
    if (fromModel) return fromModel;
    const sp = (it && it.supported_parameters) || {};
    const param = (sp.parameters && sp.parameters.duration) || sp.duration;
    if (param && typeof param === "object") return param;
    if (Array.isArray(param) && param.length) return { enum: param };
    const caps = catalogCaps();
    if (caps.duration && typeof caps.duration === "object") return caps.duration;
    const pc = (it && it.parameterCapabilities) || {};
    if (pc.duration && typeof pc.duration === "object") return pc.duration;
    return null;
  }
  function parseDurationSeconds(raw) {
    return Number.parseInt(String(raw == null ? "" : raw).replace(/s$/i, "").trim(), 10);
  }
  function durationGateMessage() {
    const el = $("duration");
    if (!el || el.classList.contains("hidden")) {
      markOver(el, false);
      return "";
    }
    if (state.mode !== "video") {
      markOver(el, false);
      return "";
    }
    const rule = durationConstraint();
    if (!rule) {
      markOver(el, false);
      return "";
    }
    const raw = String(el.value || "").trim();
    const n = parseDurationSeconds(raw);
    let enumVals = null;
    if (Array.isArray(rule.enum) && rule.enum.length) {
      enumVals = rule.enum.map(parseDurationSeconds).filter(Number.isFinite);
    } else if (Array.isArray(rule.options) && rule.options.length) {
      enumVals = rule.options.map(function (x) {
        const v = (x && typeof x === "object") ? (x.value != null ? x.value : x) : x;
        return parseDurationSeconds(v);
      }).filter(Number.isFinite);
    }
    const lo = rule.min != null ? Number(rule.min) : null;
    const hi = rule.max != null ? Number(rule.max) : null;
    const hasBound = (enumVals && enumVals.length) || Number.isFinite(lo) || Number.isFinite(hi);
    if (!hasBound) {
      markOver(el, false);
      return "";
    }
    const ok = Number.isFinite(n) && (
      enumVals && enumVals.length
        ? enumVals.indexOf(n) >= 0
        : (lo == null || !Number.isFinite(lo) || n >= lo) && (hi == null || !Number.isFinite(hi) || n <= hi)
    );
    markOver(el, !ok);
    if (ok) return "";
    const allowText = enumVals && enumVals.length
      ? "只收 " + enumVals.join("/") + "s"
      : "范围 " + (Number.isFinite(lo) ? lo : "") + "…" + (Number.isFinite(hi) ? hi : "") + "s";
    return "该模型不支持 " + (raw || "空") + " 时长（" + allowText + "），不替你静默改数";
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
          msgs.push("种子 " + n + " 超出范围 " + (lo == null ? "-∞" : lo) + "…" + (hi == null ? "∞" : hi) + "，请改值后再生成（不静默取模）");
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
    const durMsg = durationGateMessage();
    if (durMsg) msgs.push(durMsg);
    // v0821o28/o30: unsupported filled fields — warn-only for omitable (sampler/…);
    // hard-block only true capability gaps (i2v). 铁律8: no silent / no 多余门阀.
    let adaptWarn = "";
    try {
      const adapt = (typeof window !== "undefined") ? window.ComposerFieldAdapt : null;
      const ctxAdapt = {
        $: $,
        backend: currentBackend(),
        mode: state.mode,
        caps: caps
      };
      if (adapt && typeof adapt.blockingUnsupportedMessages === "function") {
        const blocks = adapt.blockingUnsupportedMessages(ctxAdapt) || [];
        blocks.forEach(function (m) { if (m) msgs.push(m); });
      } else if (adapt && typeof adapt.filledUnsupportedMessages === "function") {
        // legacy: only keep i2v-ish as block
        (adapt.filledUnsupportedMessages(ctxAdapt) || []).forEach(function (m) {
          if (m && /不支持 i2v/.test(m)) msgs.push(m);
        });
      }
      if (adapt && typeof adapt.filledUnsupportedWarnings === "function") {
        const warns = adapt.filledUnsupportedWarnings(ctxAdapt) || [];
        if (warns[0]) adaptWarn = warns[0];
      } else if (adapt && typeof adapt.filledUnsupportedMessages === "function") {
        const all = adapt.filledUnsupportedMessages(ctxAdapt) || [];
        const w = all.filter(function (m) { return m && !/不支持 i2v/.test(m); })[0];
        if (w) adaptWarn = w;
      }
    } catch (_) {}
    setParamWarn(msgs[0] || adaptWarn || "", !!(msgs.length || adaptWarn));
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
    // v0821o28: delegate show/disable/「不支持」to ComposerFieldAdapt (board + live caps tighten-only).
    const adapt = (typeof window !== "undefined") ? window.ComposerFieldAdapt : null;
    const ctx = {
      $: $,
      backend: currentBackend(),
      mode: state.mode,
      caps: catalogCaps(),
      item: (typeof catalogItemForService === "function") ? catalogItemForService() : null,
      serviceId: ($("service") && $("service").value) || "",
      fillNanoResOptions: fillNanoResOptions
    };
    if (adapt && typeof adapt.applyToSurface === "function") {
      adapt.applyToSurface(ctx);
    } else {
      // Fallback if adapt script missing — keep fields visible; never pretend supported by hiding.
      const be = currentBackend();
      const nano = be === "nano-gpt";
      const vid = state.mode === "video";
      const falBox = $("falParams");
      const comfyBox = $("comfyParams");
      const nanoBox = $("nanoParams");
      if (falBox) falBox.classList.toggle("hidden", state.mode === "text" || state.mode === "audio");
      if (comfyBox) comfyBox.classList.toggle("hidden", false);
      if (nanoBox) nanoBox.classList.toggle("hidden", !nano);
      if (nano) fillNanoResOptions();
    }
    paramGateMessage();
    if (!syncParamSurface._skipDock) renderDock();
  }
  function syncParamChrome() {
    // Model/backend switch must refresh LoRA visibility and param gates
    // without requiring a second click on the shot card.
    syncLoraUi();
    revalidateLorasForService();
    syncParamSurface();
  }
  function applyServiceConstraints() {
    // v0821o53: over-cap → try rematch from catalog (never silent unlink).
    if (typeof tryCapacityRematchAfterServiceChange === "function") {
      try {
        if (tryCapacityRematchAfterServiceChange()) {
          /* rematched — fall through to chrome sync on new service */
        }
      } catch (_) {}
    }
    // v0821o54: chips + !supportsLora → rematch same-backend LoRA-capable (never silent drop).
    if (typeof tryLoraCapabilityRematchAfterServiceChange === "function") {
      try {
        if (tryLoraCapabilityRematchAfterServiceChange()) {
          /* rematched */
        }
      } catch (_) {}
    }
    syncParamChrome();
    try { renderDock(); } catch (_) {}
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
      if (Number.isFinite(seedNum) && seedNum >= 0) out.seed = Math.floor(seedNum);
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
  function persistShotFrame(shot) {
    if (!shot || shot.kind !== "shot") return;
    writeComfyParamsToShot(shot);
    if ($("aspect")) shot.aspect = $("aspect").value;
    if ($("res")) shot.res = $("res").value;
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
  function packComfyParamsForPayload(shotOpt) {
    const p = readComfyParamsFromUi();
    const be = currentBackend();
    const sid = String(($("service") && $("service").value) || (shotOpt && (shotOpt.serviceId || (shotOpt.composer && shotOpt.composer.service))) || "");
    const falSid = be === "fal" || /\/fal\//.test(sid) || /^fal[-.]/i.test(sid);
    if (be === "nano-gpt") {
      delete p.width;
      delete p.height;
      const token = $("nanoRes") && $("nanoRes").value;
      if (token) p.resolution = token;
    } else if (falSid) {
      delete p.sampler;
      delete p.scheduler;
      delete p.steps;
      delete p.cfg;
      delete p.cfgScale;
      delete p.width;
      delete p.height;
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
    // v0821o22: civitai checkpoint AIR from imported shot (fresh hinablue) — never invent default AIR.
    // v0821o38: prefer generate shot (runShotStepWork) over selected/lastComposerShot — selected can be wrong/empty.
    if (be === "civitai") {
      const shot = (shotOpt && shotOpt.kind === "shot" ? shotOpt : null)
        || nodeById(state.selected) || nodeById(state.lastComposerShot);
      const dm = shot && shot.diffusionModel ? String(shot.diffusionModel).trim() : "";
      if (dm) p.diffusionModel = dm;
      const cn = shot && shot.checkpointName ? String(shot.checkpointName).trim() : "";
      if (cn) p.checkpointName = cn;
      const eco = shot && shot.ecosystem ? String(shot.ecosystem).trim() : "";
      if (eco) p.ecosystem = eco;
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
      // Width/height follow #aspect/#res. Never fill Civitai 960×1440 into empty boxes.
      if ($("steps") && !$("steps").value && d.steps != null) $("steps").value = d.steps;
      if ($("cfg") && !$("cfg").value && d.cfgScale != null) $("cfg").value = d.cfgScale;
      if (d.sampler && $("sampler") && !$("sampler").value) ensureSelectOpt($("sampler"), d.sampler);
      if (d.scheduler && $("scheduler") && !$("scheduler").value) ensureSelectOpt($("scheduler"), d.scheduler);
      // Catalog ordering hint only — never soft-fill into generate/buildGraph.
      state._civitaiDefaultService = (d.serviceId || CIVITAI_PREF_SERVICE);
    } catch (_) {
      fillSelectOpts($("sampler"), ["er_sde", "euler", "euler_ancestral", "dpmpp_2m", "dpmpp_sde", "ddim"], "er_sde");
      fillSelectOpts($("scheduler"), ["sgm_uniform", "simple", "normal", "karras", "exponential", "ddim_uniform", "beta"], "sgm_uniform");
      if ($("steps") && !$("steps").value) $("steps").value = 8;
      if ($("cfg") && !$("cfg").value) $("cfg").value = 1;
      // Catalog ordering hint only — never soft-fill into generate/buildGraph.
      state._civitaiDefaultService = CIVITAI_PREF_SERVICE;
    }
    syncParamSurface();
    ensureComposerSize();
  }

  // Pack like index.html base.loras (~2231) + slimPayload (~2302): path/url/versionId/air/scale.
  // Keep air/modelId/versionId/strength on every row. Never silent-filter mixed chips.
  function packLoraRow(l) {
    l = l || {};
    let path = l.path || l.downloadUrl || l.url || "";
    const versionId = l.versionId || loraVersionId(l) || "";
    const modelId = l.modelId || loraModelId(l) || "";
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
      modelId: modelId,
      path: path,
      url: path,
      downloadUrl: l.downloadUrl || path,
      versionId: versionId,
      scale: scale,
      strength: strength,
      strengthMissing: missing,
      name: l.name || "LoRA",
      type: l.type || "",
    };
  }
  function loraRowCanOutbound(row, be) {
    be = be || currentBackend();
    row = row || {};
    if (be === "civitai") {
      const airOk = !!(row.air && String(row.air).trim());
      const modelOk = !!(row.modelId && String(row.modelId).trim());
      const verOk = !!(row.versionId && String(row.versionId).trim());
      const strOk = !row.strengthMissing && row.strength != null && row.strength !== "";
      return airOk && modelOk && verOk && strOk;
    }
    if (be === "fal" || be === "huggingface") {
      const p = String(row.path || "").trim();
      return !!(p && isHttpUrl(p) && !looksAir(p));
    }
    if (be === "modelscope-ai" || be === "modelscope-cn") {
      const p = String(row.path || "").trim();
      if (isHttpUrl(p) || looksAir(p) || p.indexOf("3231694") >= 0) return false;
      return isHfRepo(p);
    }
    return true;
  }
  function packLorasForPayload() {
    const list = Array.isArray(state.loras) ? state.loras : [];
    if (!list.length) return null;
    if (!catalogItemSupportsLora()) return null;
    const be = currentBackend();
    const mapped = list.map(packLoraRow);
    for (let i = 0; i < mapped.length; i++) {
      if (shouldDropNonLoraAir(mapped[i].air)) return null;
      if (!loraRowCanOutbound(mapped[i], be)) return null;
    }
    return mapped.length ? mapped : null;
  }
  // chips present but any row cannot ship → red block. Mixed must not drop the bad row.
  function chipsLackAirForOutbound() {
    const list = Array.isArray(state.loras) ? state.loras : [];
    if (!list.length) return false;
    if (!catalogItemSupportsLora()) return true;
    const packed = packLorasForPayload();
    return !packed || packed.length !== list.length;
  }
  function outboundLoraBlockMsg() {
    const list = Array.isArray(state.loras) ? state.loras : [];
    if (list.length && !catalogItemSupportsLora()) {
      return "当前模型暂不支持 LoRA · 将自动匹配同后端 LoRA 端点（也可点「一键匹配」或删除芯片，不静默丢掉）";
    }
    const be = currentBackend();
    const mapped = list.map(packLoraRow);
    const bad = mapped.filter(function (row) { return !loraRowCanOutbound(row, be); });
    if (bad.length && bad.length < mapped.length) {
      return "有 " + bad.length + " 条 LoRA 缺 air/modelId/versionId/strength 或无法出站，不能只带走其余条";
    }
    if (be === "civitai" && bad.length) {
      const missStr = bad.some(function (row) { return row.strengthMissing || row.strength == null || row.strength === ""; });
      if (missStr) return "LoRA 缺 strength，无法出站（不发明 1.0）";
      return "LoRA 缺 air/modelId/versionId，无法出站";
    }
    if (be === "modelscope-ai" || be === "modelscope-cn") {
      return "魔搭 LoRA 只要 Hub owner/repo，Civitai 下载链不能用";
    }
    if (be === "fal") {
      const baseMsg = falLoraUnsupportedMsg();
      if (baseMsg) return baseMsg;
      return "LoRA 缺 http path，无法出站";
    }
    if (be === "huggingface") return "LoRA 缺 http path，无法出站";
    return "LoRA 缺 air，无法出站";
  }
  function revalidateLorasForService() {
    const list = Array.isArray(state.loras) ? state.loras : [];
    if (!list.length) return;
    const be = currentBackend();
    if (!catalogItemSupportsLora()) {
      let rematched = false;
      try {
        if (typeof tryLoraCapabilityRematchAfterServiceChange === "function") {
          rematched = !!tryLoraCapabilityRematchAfterServiceChange();
        }
      } catch (_) {}
      if (rematched && catalogItemSupportsLora()) {
        /* sync rematch applied — fall through */
      } else if (rematched) {
        // o54b: async roster fetch started — soft note, prefer auto path over red hard gate
        setLoraNote("正在拉取官方目录匹配 LoRA…（芯片保留，不静默丢掉）", false);
        renderLoras();
        try { syncLoraUi(); } catch (_) {}
        return;
      } else {
        list.forEach(function (l) { l.status = "当前模型不支持"; });
        setLoraNote("当前模型不支持 LoRA，已选芯片还在 · 点「一键匹配」改选同后端 LoRA 端点（不会静默丢掉）", true);
        renderLoras();
        try { syncLoraUi(); } catch (_) {}
        return;
      }
    }
    let bad = 0;
    list.forEach(function (l) {
      if (!loraRowCanOutbound(packLoraRow(l), be)) {
        if (l.status !== "无直链") l.status = "无法出站";
        bad += 1;
      } else if (l.status === "当前模型不支持" || l.status === "无法出站") {
        l.status = "";
      }
    });
    if (bad) setLoraNote("有 " + bad + " 条 LoRA 无法按当前后端出站，不能只带走其余条", true);
    else setLoraNote("");
    renderLoras();
  }
  function loraHouseLabel(src) {
    const s = String(src || "").toLowerCase();
    if (s === "civitai") return "Civitai";
    if (s === "fal") return "Fal";
    if (s === "huggingface" || s === "hf") return "HF";
    if (s === "modelscope-ai" || s === "modelscope") return "魔搭AI";
    if (s === "modelscope-cn") return "魔搭CN";
    if (s === "nano-gpt" || s === "nanogpt" || s === "nano") return "Nano";
    return src || "";
  }
  // v0821o135: 当前选中模型(checkpoint)的底模家族。供 LoRA 搜索按底模过滤/标灰。
  function currentCheckpointFamily() {
    if (typeof SmartFamilyMatch === "undefined" || !SmartFamilyMatch.inferModelFamily) return "";
    const shot = (typeof composerShot === "function" ? composerShot() : null) || nodeById(state.selected);
    let fam = "";
    try { fam = (shot && SmartFamilyMatch.familyFromShot) ? (SmartFamilyMatch.familyFromShot(shot, "") || "") : ""; } catch (_) { fam = ""; }
    if (fam) return fam;
    const it = (typeof catalogItemForService === "function") ? catalogItemForService() : null;
    const sid = ($("service") && $("service").value) || "";
    return SmartFamilyMatch.inferModelFamily([it && it.baseModel, it && it.ecosystem, it && it.name, sid].filter(Boolean).join(" ")) || "";
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
      addLora({ path: q, name: q, strength: null });
      hits.textContent = "";
      return;
    }
    if ((be === "fal" || be === "huggingface" || isNanogptBe()) && (isHttpUrl(q) || isHfRepo(q))) {
      addLora({ path: q, name: q, strength: null });
      hits.textContent = "";
      return;
    }
    if (be === "civitai" && /^\d+$/.test(q)) {
      try {
        const r = await fetch("/api/model-version/" + encodeURIComponent(q));
        const v = await r.json();
        if (v && !v.error) {
          const ok = await addLora(v);
          if (!ok) hits.textContent = "";
        } else hits.textContent = "没找到这个 version";
      } catch (_) { hits.textContent = "没找到这个 version"; }
      return;
    }
    if (q.startsWith("urn:air:") || q.includes(":lora:") || q.includes(":lycoris:")) {
      // v0821o36: checkpoint/diffuser AIR paste must not become a LoRA chip
      if (shouldDropNonLoraAir(q) || (q.startsWith("urn:air:") && !isLoraAir(q))) {
        hits.textContent = "不是 LoRA AIR（checkpoint/diffuser 请走底模）";
        try { setMsg("已拒绝非 LoRA AIR（checkpoint/diffuser 不进 loras[]）", "warn"); } catch (_) {}
        return;
      }
      addLora({ air: q, name: q.split(":").pop(), strength: null });
      hits.textContent = "";
      return;
    }
    try {
      // v0821o135: 默认只在当前家搜(cross=0)；用户显式勾选"跨家搜"才混入别家结果。
      const crossOn = !!($("loraCross") && $("loraCross").checked);
      // v0821o135: 当前家有底模概念时(Civitai baseModel)，带上当前选中模型的底模家族，结果按家族优先/标灰。
      const curFam = currentCheckpointFamily();
      const r = await fetch("/api/search?type=LORA&q=" + encodeURIComponent(q) + "&backend=" + encodeURIComponent(be) + (crossOn ? "&cross=1" : "&cross=0") + (curFam ? "&baseFamily=" + encodeURIComponent(curFam) : ""));
      const j = await r.json();
      const rows = j.items || [];
      if (!rows.length) { hits.textContent = (j.note || "没有结果"); return; }
      const decorated = rows.map(function (it) {
        const v = (it.versions || [])[0] || {};
        const loraFam = (typeof SmartFamilyMatch !== "undefined" && SmartFamilyMatch.inferModelFamily)
          ? (SmartFamilyMatch.inferModelFamily([v.baseModel, it.baseModel, it.ecosystem].filter(Boolean).join(" ")) || "")
          : "";
        const mismatch = !!(curFam && loraFam && typeof SmartFamilyMatch !== "undefined" && !SmartFamilyMatch.familyCompatible(curFam, loraFam));
        return { it: it, v: v, fam: loraFam, mismatch: mismatch };
      });
      // 底模匹配的排前，不符的标灰沉底（不藏，只注明）
      decorated.sort(function (a, b) { return (a.mismatch ? 1 : 0) - (b.mismatch ? 1 : 0); });
      hits.innerHTML = decorated.map(function (d) {
        const it = d.it;
        const v = d.v;
        const path = it.path || "";
        const extra = v.baseModel || v.name || path || "";
        const src = it.source || it.backend || be;
        const badge = loraHouseLabel(src);
        return '<div class="lora-hit' + (d.mismatch ? " lora-baseMismatch" : "") + '"' +
          (d.mismatch ? ' style="opacity:.45" title="该 LoRA 底模是 ' + esc(d.fam) + '，当前模型是 ' + esc(curFam) + '，不匹配"' : "") +
          ' data-path="' + esc(path) + '" data-vid="' + esc(v.id || "") +
          '" data-mid="' + esc(it.id || "") + '" data-type="' + esc(it.type || "") +
          '" data-name="' + esc(it.name || "") + '" data-src="' + esc(src) + '"><b>' +
          esc(it.name) + '</b>' +
          (badge ? ('<span class="lora-src">' + esc(badge) + '</span>') : "") +
          (d.mismatch ? '<span class="lora-src lora-mismatch">底模不符</span>' : "") +
          (extra ? (" · " + esc(extra)) : "") + "</div>";
      }).join("");
      Array.prototype.forEach.call(hits.children, function (el) {
        el.onclick = async function () {
          const path = el.getAttribute("data-path");
          const name = el.getAttribute("data-name") || "";
          const vid = el.getAttribute("data-vid");
          const mid = el.getAttribute("data-mid") || "";
          const typ = el.getAttribute("data-type") || "";
          const src = el.getAttribute("data-src") || be;
          if (path && (isHttpUrl(path) || isHfRepo(path))) {
            addLora({ path: path, name: name || path, strength: null, type: typ, modelId: mid, source: src });
            return;
          }
          if ((src === "civitai" || be === "civitai") && vid) {
            try {
              const rr = await fetch("/api/model-version/" + encodeURIComponent(vid));
              const data = await rr.json();
              if (!data.modelId && mid) data.modelId = mid;
              if (!data.type && typ) data.type = typ;
              data.source = src;
              await addLora(data);
            } catch (_) {}
            return;
          }
          if (vid && /^\d+$/.test(String(vid))) {
            addLora({
              path: "https://civitai.com/api/download/models/" + vid,
              versionId: String(vid),
              modelId: mid,
              type: typ,
              name: name || ("LoRA " + vid),
              strength: null,
              source: src,
            });
            return;
          }
          if (path || name) addLora({ path: path || name, name: name || path, strength: null, type: typ, modelId: mid, source: src });
        };
      });
    } catch (_) {
      hits.textContent = "搜索失败";
    }
  }
  function bindLoraUi() {
    if ($("loraFold")) $("loraFold").onclick = function () {
      const block = $("loraBlock");
      const nowOpen = !(block && block.classList.contains("lora-mini"));
      loraFoldOpen = !nowOpen;
      syncLoraUi();
    };
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
    if (id === FAL_FLUX_LORA_SERVICE) return (name && name !== id ? name + " · " + id : "Flux LoRA · " + id);
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
      ? (state._pinHfLoraService || (selectedShotWantsI2i() ? HF_I2I_PREF_SERVICE : HF_LORA_PREF_SERVICE))
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
        applyServiceConstraints();
        try {
          const shotNow = (typeof composerShot === "function" ? composerShot() : null) || nodeById(state.selected);
          const own = shotNow && (shotNow.serviceId || (shotNow.composer && shotNow.composer.service));
          if (!own) await smartMatchService({ announce: true });
        } catch (_) {}
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
    const beNow = (typeof currentBackend === "function") ? currentBackend() : (($("backend") && $("backend").value) || "");
    if (beNow && typeof serviceBelongsToBackend === "function") {
      shown = shown.filter(function (it) {
        const id = String((it && (it.id || it.name)) || "");
        return !id || serviceBelongsToBackend(id, beNow);
      });
    }
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
        id.indexOf("/i2v") >= 0 || id.indexOf("ti2v") >= 0 || /(?:^|[-_/])i2v(?:$|[-_/])/.test(id) ||
        id.indexOf("imagetovideo") >= 0 || id.indexOf("flf2v") >= 0) return true;
    const task = String(it.task || it.hubTask || "").toLowerCase();
    if (task === "image-to-video") return true;

    // 3) Catalog imageFields declare first-frame / start_image / image_url for video.
    if (hasFirst && (cat === "video" || cat.indexOf("video") >= 0 || fcat.indexOf("video") >= 0 ||
        it.kind === "video" || id.indexOf("video") >= 0)) return true;

    // NEVER: category=video && !text-to-video substring — that let video-01 through.
    return false;
  }
  function catalogItemSupportsT2v(it) {
    if (!it) return false;
    if (catalogItemSupportsI2v(it)) return false;
    const id = String(it.id || it.name || "").toLowerCase();
    const cat = String(it.category || it.kind || it.falCategory || "").toLowerCase();
    const fcat = String(it.falCategory || "").toLowerCase();
    const task = String(it.task || it.hubTask || it.operation || "").toLowerCase();
    if (id.indexOf("text-to-video") >= 0 || id.indexOf("/t2v") >= 0 || /(?:^|[-_/])t2v(?:$|[-_/])/.test(id)) return true;
    if (fcat.indexOf("text-to-video") >= 0) return true;
    if (task === "text-to-video") return true;
    if (id === "fal-ai/minimax/video-01" || /\/video-01$/.test(id)) return true;
    if ((cat.indexOf("video") >= 0 || it.kind === "video") && !catalogItemSupportsI2v(it) &&
        id.indexOf("upscal") < 0 && id.indexOf("inpaint") < 0) return true;
    return false;
  }
  function catalogItemSupportsUpscale(it) {
    if (!it) return false;
    const blob = [it.id, it.name, it.category, it.operation, it.task, it.step, it.kind]
      .map(function (x) { return String(x || "").toLowerCase(); }).join(" ");
    return /upscal|esrgan|realesrgan|aura-sr|clarity-upscaler|imageupscaler|superscale|seedvr\/upscale/.test(blob);
  }
  function catalogItemSupportsInpaint(it) {
    if (!it) return false;
    const blob = [it.id, it.name, it.category, it.operation, it.task, it.step, it.kind]
      .map(function (x) { return String(x || "").toLowerCase(); }).join(" ");
    return /inpaint|eraser|object-removal|\/erase(?:$|\/)|finegrain-eraser/.test(blob);
  }
  function catalogItemSupportsImage(it) {
    if (!it) return true;
    const id = String(it.id || it.name || "").toLowerCase();
    const cat = String(it.category || it.falCategory || it.kind || "").toLowerCase();
    if (cat === "video" || it.kind === "video") return false;
    if (id.indexOf("image-to-video") >= 0 || id.indexOf("text-to-video") >= 0) return false;
    return true;
  }
  function catalogItemSupportsI2i(it) {
    if (!it || !catalogItemSupportsImage(it)) return false;
    const caps = (it.capabilities && typeof it.capabilities === "object") ? it.capabilities : {};
    if (caps.image_to_image === true || caps.inpainting === true) return true;
    if (it.needsSource) return true;
    if (caps.image_to_image === false) return false;
    const task = String(it.task || it.hubTask || "").toLowerCase();
    const tags = Array.isArray(it.tags) ? it.tags.map(function (t) { return String(t).toLowerCase(); }) : [];
    const id = String(it.id || it.name || "").toLowerCase();
    const op = String(it.operation || "").toLowerCase();
    if (task === "image-to-image" || tags.indexOf("i2i") >= 0) return true;
    if (op === "editimage" || op === "createvariant" || op === "proeditimage") return true;
    if (task === "text-to-image" || tags.indexOf("t2i") >= 0) {
      if (/editimage|\/edit(?:$|\/)/.test(id)) return true;
      return false;
    }
    if (id.indexOf("image-to-image") >= 0 || /(?:^|\/|-)edit(?:$|\b|\/)/.test(id) || id.indexOf("editimage") >= 0) return true;
    return false;
  }
  function composerShot() {
    const n = nodeById(state.selected);
    if (n && n.kind === "shot") return n;
    const remembered = nodeById(state.lastComposerShot);
    if (remembered && remembered.kind === "shot") return remembered;
    return (n && n.kind === "shot") ? n : null;
  }
  function selectedShotWantsI2i() {
    if (state.mode === "video" || state.mode === "text" || state.mode === "audio") return false;
    const shot = (typeof composerShot === "function" ? composerShot() : null)
      || nodeById(state.selected)
      || (typeof shots === "function" ? shots()[0] : null);
    if (!shot || shot.kind !== "shot") return false;
    return connectedAssets(shot.id).length > 0;
  }
  function currentGraphOp() {
    const shot = (typeof composerShot === "function" ? composerShot() : null) || nodeById(state.selected);
    if (state.mode === "video") {
      // frameAsset lives outside the smart-match seam; guard it so a seam-less VM (o79) treats video as i2v (never invent a frame).
      if (typeof frameAsset === "function") {
        if (!shot || !frameAsset(shot) || (shot.wantT2v && !frameAsset(shot))) return "t2v";
        return "i2v";
      }
      return "i2v";
    }
    if (shot && shot.wantUpscale) return "upscale";
    if (shot && shot.wantInpaint) return "inpaint";
    if (selectedShotWantsI2i()) return "i2i";
    return "t2i";
  }
  function graphOpLabel(op) {
    return ({ t2i: "文生图", i2i: "图生图", i2v: "图生视频", t2v: "文生视频", upscale: "超清", inpaint: "消除" })[op] || "";
  }
  function syncOpChip() {
    const el = $("opChip");
    if (!el) return;
    if (state.mode === "text" || state.mode === "audio") {
      el.hidden = true;
      el.textContent = "";
      el.removeAttribute("data-op");
      return;
    }
    const op = currentGraphOp();
    el.hidden = false;
    el.textContent = graphOpLabel(op) || modeLabelOf(state.mode);
    el.setAttribute("data-op", op);
  }

  const SMART_PREF = {
    civitai: {
      t2i: ["image/comfy/krea2/turbo/createImage", "image/sdcpp/zImage/turbo/createImage"],
      i2i: ["image/flux2/klein/editImage/9b", "image/wan/v2.7/fal/editImage", "image/sdcpp/sdxl/createVariant", "image/comfy/krea2/edit/editImage"],
      i2v: ["video/minimax-h3-comfy/imageToVideo", "video/wan/v2.2/fal/image-to-video", "video/ltx2.3/firstLastFrameToVideo"],
      t2v: ["video/wan/v2.2/fal/text-to-video", "video/wan/v3.0/text-to-video", "video/sora/text-to-video"],
      upscale: ["image/imageUpscaler"],
      inpaint: []
    },
    fal: {
      t2i: ["fal-ai/krea-2/turbo/lora", "fal-ai/krea-2/turbo", "fal-ai/flux/schnell"],
      i2i: ["fal-ai/flux-pro/kontext", "fal-ai/nano-banana-2/edit", "fal-ai/z-image/turbo/image-to-image", "fal-ai/flux/dev/image-to-image"],
      i2v: ["fal-ai/kling-video/v3/pro/image-to-video", "bytedance/seedance-2.5/image-to-video", "fal-ai/minimax/video-01/image-to-video", "minimax/h3-max/image-to-video"],
      t2v: ["fal-ai/kling-video/v3/pro/text-to-video", "bytedance/seedance-2.5/text-to-video", "minimax/h3-max/text-to-video", "fal-ai/minimax/video-01"],
      upscale: ["fal-ai/esrgan", "fal-ai/clarity-upscaler", "fal-ai/seedvr/upscale/image"],
      inpaint: ["fal-ai/bria/eraser", "fal-ai/image-editing/object-removal", "fal-ai/qwen-image-edit/inpaint"]
    },
    "nano-gpt": {
      t2i: ["wavespeed-ai/krea-v2/turbo-lora", "z-image-turbo", "nvidia/cosmos-3-super/text-to-image", "openai/gpt-image-2.5/flare/text-to-image"],
      i2i: ["z-image-turbo-image-to-image", "openai/gpt-image-2.5/flare/edit", "bernini-r/edit-image", "pruna-ai/p-image/edit-lora"],
      i2v: ["minimax/h3-max/multi-angle/image-to-video", "infinitetalk", "bytedance/seedance-2.5-spicy"],
      // 裁决(2026-09-15): nano 目录 t2v 真实 id 无 /text-to-video 后缀（task 字段标注）——
      // 旧 pref「minimax/h3-max/text-to-video」不在目录，pickSmartServiceId 永远落空。
      t2v: ["minimax/h3-max", "bytedance/seedance-2.5"],
      upscale: [],
      inpaint: []
    },
    huggingface: {
      t2i: ["krea/Krea-2-Turbo", "black-forest-labs/FLUX.1-schnell"],
      i2i: ["Qwen/Qwen-Image-Edit"],
      i2v: ["Wan-AI/Wan2.2-TI2V-5B"],
      t2v: ["tencent/HunyuanVideo", "Lightricks/LTX-Video-0.9.8-13B-distilled"],
      upscale: [],
      inpaint: []
    },
    "modelscope-ai": {
      t2i: ["krea/Krea-2-Turbo", "Tongyi-MAI/Z-Image-Turbo"],
      i2i: ["MusePublic/Qwen-Image-Edit", "Qwen/Qwen-Image-Edit"],
      i2v: ["Wan-AI/Wan2.1-I2V-14B-720P"],
      t2v: ["krea/krea-realtime-video"],
      upscale: [],
      inpaint: []
    },
    "modelscope-cn": {
      t2i: ["krea/Krea-2-Turbo", "Tongyi-MAI/Z-Image-Turbo"],
      i2i: ["MusePublic/Qwen-Image-Edit", "Qwen/Qwen-Image-Edit"],
      i2v: ["Wan-AI/Wan2.1-I2V-14B-720P"],
      t2v: ["krea/krea-realtime-video"],
      upscale: [],
      inpaint: []
    }
  };
  function serviceFitsOp(it, op) {
    if (!it) return false;
    if (op === "i2v") return catalogItemSupportsI2v(it);
    if (op === "t2v") return catalogItemSupportsT2v(it);
    if (op === "upscale") return catalogItemSupportsUpscale(it);
    if (op === "inpaint") return catalogItemSupportsInpaint(it) || catalogItemSupportsI2i(it);
    if (op === "i2i") return !catalogItemSupportsI2v(it) && catalogItemSupportsI2i(it);
    return catalogItemSupportsImage(it) && !catalogItemSupportsI2v(it) && !catalogItemSupportsI2i(it) && !catalogItemSupportsUpscale(it);
  }
  function pickSmartServiceId(op) {
    const be = (typeof currentBackend === "function" ? currentBackend() : "") || ($("backend") && $("backend").value) || "";
    const pool = (typeof rematchCandidatePool === "function") ? rematchCandidatePool() : (state.catalogById || {});
    const prefs = (SMART_PREF[be] && SMART_PREF[be][op]) || [];
    for (let i = 0; i < prefs.length; i++) {
      const id = prefs[i];
      const row = pool[id] || (state.catalogById && state.catalogById[id]);
      if (row && serviceBelongsToBackend(id, be) && serviceFitsOp(row, op)) return id;
    }
    const keys = Object.keys(pool);
    for (let i = 0; i < keys.length; i++) {
      const row = pool[keys[i]];
      if (row && serviceBelongsToBackend(String(row.id || keys[i]), be) && serviceFitsOp(row, op)) return String(row.id || keys[i]);
    }
    return "";
  }
  function injectCatalogRow(row) {
    if (!row || typeof row !== "object") return;
    const id = String(row.id || row.name || "").trim();
    if (!id) return;
    if (!state.catalogById) state.catalogById = {};
    state.catalogById[id] = row;
    function push(arr) {
      if (!Array.isArray(arr)) return;
      if (!arr.some(function (x) { return String((x && (x.id || x.name)) || "") === id; })) arr.unshift(row);
    }
    if (!state.catalog) state.catalog = [];
    push(state.catalog);
    if (!state._catalogRoster) state._catalogRoster = [];
    push(state._catalogRoster);
    if (!state._serviceItems) state._serviceItems = [];
    push(state._serviceItems);
  }
  async function fetchCatalogId(be, id, category) {
    const size = String((typeof CATALOG_PAGE_SIZE === "number" && CATALOG_PAGE_SIZE) || 50);
    const params = new URLSearchParams({
      backend: be, q: id, category: category || "", page: "1", pageSize: size
    });
    const r = await fetch("/api/catalog?" + params.toString());
    if (!r.ok) return null;
    const j = await r.json();
    const items = Array.isArray(j.items) ? j.items : [];
    for (let i = 0; i < items.length; i++) {
      if (String(items[i].id || items[i].name || "") === id) return items[i];
    }
    return null;
  }
  async function ensureSmartPrefInPool(op) {
    const be = (typeof currentBackend === "function" ? currentBackend() : "") || ($("backend") && $("backend").value) || "";
    const prefs = (SMART_PREF[be] && SMART_PREF[be][op]) || [];
    const cat = (op === "i2v" || op === "t2v") ? "video" : "image";
    for (let i = 0; i < prefs.length; i++) {
      const id = prefs[i];
      const pool = rematchCandidatePool();
      const hit = pool[id];
      if (hit && serviceFitsOp(hit, op)) return id;
      let row = null;
      try { row = await fetchCatalogId(be, id, cat); } catch (_) { row = null; }
      if (row && String(row.id || row.name) === id && serviceFitsOp(row, op)) {
        injectCatalogRow(row);
        return id;
      }
    }
    return "";
  }
  function writeSmartMatchToShot(shot, want) {
    if (!shot || shot.kind !== "shot") return;
    const house = String(shot.backend || (shot.composer && shot.composer.backend) || "").trim();
    const be = house
      || (typeof currentBackend === "function" ? currentBackend() : "")
      || ($("backend") && $("backend").value)
      || "";
    shot.serviceId = want || "";
    if (be) shot.backend = be;
    shot.mode = state.mode;
    if (!shot.composer || typeof shot.composer !== "object") shot.composer = { fields: {}, loras: [] };
    shot.composer.service = want || "";
    if (be) shot.composer.backend = be;
    shot.composer.mode = state.mode;
    delete shot._error;
    delete shot._errorDetail;
  }
  function serviceBelongsToBackend(sid, be) {
    const s = String(sid || "").trim();
    const b = String(be || "").trim();
    if (!s || !b) return true;
    const fal = /^fal-ai\//i.test(s) || /^fal\.ai\//i.test(s);
    const civ = /^(image|video|audio|3d|utility)\//.test(s) || /\/comfy\//.test(s);
    if (b === "civitai") return civ && !fal;
    if (b === "fal") return !civ;
    if (b === "huggingface" || b === "modelscope-ai" || b === "modelscope-cn" || b === "nano-gpt") return !fal && !civ;
    return true;
  }
  const HOUSE_LABEL = {
    civitai: "Civitai", fal: "Fal", "nano-gpt": "Nano",
    huggingface: "HF", "modelscope-ai": "魔搭AI", "modelscope-cn": "魔搭CN",
  };
  function smartSearchQuery(op) {
    const names = (state.loras || []).map(function (l) {
      return String((l && (l.name || l.path)) || "").trim();
    }).filter(Boolean);
    const opQ = ({ t2i: "text-to-image", i2i: "edit", i2v: "image-to-video", t2v: "text-to-video", upscale: "upscale", inpaint: "inpaint" })[op] || "";
    return (names.slice(0, 2).join(" ") + " " + opQ).trim();
  }
  function loraSourceHouses() {
    const out = [];
    (state.loras || []).forEach(function (l) {
      const s = String((l && (l.source || l.backend)) || "").trim();
      if (s && out.indexOf(s) < 0) out.push(s);
    });
    return out;
  }
  async function searchModelsForOp(be, op, cross) {
    const q = smartSearchQuery(op);
    const cat = (op === "i2v" || op === "t2v") ? "video" : "image";
    const params = new URLSearchParams({
      type: "MODEL",
      backend: be || "",
      op: op || "",
      category: cat,
      q: q,
      cross: cross ? "1" : "0",
    });
    const r = await fetch("/api/search?" + params.toString());
    if (!r.ok) return [];
    const j = await r.json();
    const items = Array.isArray(j.items) ? j.items : [];
    items.forEach(function (it) { try { injectCatalogRow(it); } catch (_) {} });
    return items;
  }
  function pickFitFromSearch(items, op, preferBe) {
    const list = Array.isArray(items) ? items : [];
    function ok(it) { return it && serviceFitsOp(it, op); }
    if (preferBe) {
      for (let i = 0; i < list.length; i++) {
        const it = list[i];
        const id = String((it && (it.id || it.name)) || "");
        const hb = String((it && (it.backend || it.source)) || "");
        if (hb && hb !== preferBe && !serviceBelongsToBackend(id, preferBe)) continue;
        if (ok(it)) return it;
      }
    }
    for (let i = 0; i < list.length; i++) {
      if (ok(list[i])) return list[i];
    }
    return null;
  }
  async function smartMatchService(opts) {
    opts = opts || {};
    if (state.mode === "text" || state.mode === "audio") return false;
    const sel = $("service");
    if (!sel) return false;
    const gen = (smartMatchService._gen = (smartMatchService._gen || 0) + 1);
    if (smartMatchService._inflight) {
      try { await smartMatchService._inflight; } catch (_) {}
    }
    if (gen !== smartMatchService._gen) return false;
    const shot = (typeof composerShot === "function" ? composerShot() : null) || nodeById(state.selected);
    if (typeof honorHouseLock === "function") honorHouseLock();
    const liveBe = ($("backend") && $("backend").value) || "";
    if (shot && shot.kind === "shot" && liveBe) {
      shot.backend = liveBe;
      if (!shot.composer) shot.composer = {};
      shot.composer.backend = liveBe;
    }
    const op = currentGraphOp();
    const cur = catalogItemForService();
    const be = (typeof currentBackend === "function" ? currentBackend() : "") || ($("backend") && $("backend").value) || "";
    const foreign = !serviceBelongsToBackend(sel.value, be);
    const labels = { t2i: "文生图", i2i: "图生图", i2v: "图生视频", t2v: "文生视频", upscale: "超清", inpaint: "消除" };
    const fam = (typeof SmartFamilyMatch !== "undefined" && SmartFamilyMatch.familyFromShot)
      ? SmartFamilyMatch.familyFromShot(shot, (shot && (shot.checkpointName || shot.diffusionModel)) || "")
      : "";
    // v0821o136seko-uservspick: 无底模家族信息时（普通手选/新建分镜，非帖子导入），
    // 显式已选且适配当前 op 的模型必须保留——否则任何手选都会被重匹配偷换
    // （实测：fal-t2v 手选 minimax/video-01 被换成 flux-3，违反「不许偷偷换模型」）。
    // 家族严格判定只用于 fam 非空（帖子导入 D3：SDXL 帖不许留 Krea2）；
    // 有导入底模标记但家族识别失败（fam==""）→ 维持 766fefe 的不可信方向：照常重匹配。
    const hasImportModel = !!(shot && (shot.diffusionModel || shot.checkpointName));
    const curForFit = cur || (sel.value ? { id: sel.value, name: sel.value } : null);
    const keepNow = fam
      ? ((typeof SmartFamilyMatch !== "undefined" && SmartFamilyMatch.keepCurrent)
          ? SmartFamilyMatch.keepCurrent({
              currentId: sel.value, item: cur, op: op, family: fam, foreign: foreign,
              fits: serviceFitsOp
            })
          : (!foreign && serviceFitsOp(cur, op)))
      : (!hasImportModel && !foreign && !!sel.value && serviceFitsOp(curForFit, op));
    // 异步搜索起跑时的选择快照——应用重匹配结果前据此再判一次用户是否已改选。
    const sidAtStart = String(sel.value || "").trim();
    if (keepNow) {
      writeSmartMatchToShot(shot, sel.value);
      if (typeof syncOpChip === "function") syncOpChip();
      if (opts.announce !== false) {
        const name = (cur && cur.name) || sel.value;
        const wantMsg = "已智能匹配" + (labels[op] || op) + " · " + name;
        const live = ($("msg") && $("msg").textContent) || "";
        if (live.indexOf("已智能匹配" + (labels[op] || op)) < 0) {
          try { setMsg(wantMsg, "ok"); } catch (_) {}
        }
      }
      try { if (typeof renderDock === "function") renderDock(); } catch (_) {}
      return false;
    }
    const run = (async function () {
      try {
        if (gen !== smartMatchService._gen) return false;
        let row = null;
        let crossHit = false;
        const fam2 = state._importFamily
          || ((typeof SmartFamilyMatch !== "undefined" && SmartFamilyMatch.familyFromShot)
            ? SmartFamilyMatch.familyFromShot(shot, "")
            : "");
        if (typeof SmartFamilyMatch !== "undefined" && SmartFamilyMatch.pickByFamily && fam2) {
          const poolObj = (typeof rematchCandidatePool === "function") ? rematchCandidatePool() : (state.catalogById || {});
          const poolArr = Array.isArray(poolObj) ? poolObj : Object.keys(poolObj).map(function (k) { return poolObj[k]; });
          const picked = SmartFamilyMatch.pickByFamily({
            backend: be, op: op, family: fam2, pool: poolArr,
            fits: serviceFitsOp, belongs: serviceBelongsToBackend
          });
          if (picked) {
            row = poolObj[picked] || (state.catalogById && state.catalogById[picked]) || { id: picked, name: picked, backend: be };
          }
        } else {
          try {
            const local = await searchModelsForOp(be, op, false);
            row = pickFitFromSearch(local, op, be);
          } catch (_) {}
          if (!row) {
            const wantPref = (await ensureSmartPrefInPool(op)) || pickSmartServiceId(op);
            if (wantPref) {
              const pool = (typeof rematchCandidatePool === "function") ? rematchCandidatePool() : (state.catalogById || {});
              row = pool[wantPref] || (state.catalogById && state.catalogById[wantPref]) || null;
            }
          }
        }
        if (!row) {
          // v0821o136seko-uservspick: 搜索无果且用户在异步期间已改选到适配模型 → 保留，不得清空。
          const nowId0 = String(sel.value || "").trim();
          if (nowId0 && nowId0 !== sidAtStart && serviceBelongsToBackend(nowId0, be)
              && serviceFitsOp(catalogItemForService() || { id: nowId0, name: nowId0 }, op)) {
            writeSmartMatchToShot(shot, nowId0);
            return false;
          }
          sel.value = "";
          writeSmartMatchToShot(shot, "");
          if (typeof syncOpChip === "function") syncOpChip();
          if (opts.announce !== false) {
            try { setMsg("搜索没有可匹配的" + (labels[op] || op) + "模型，请换关键词或换家", "warn"); } catch (_) {}
          }
          try { if (typeof renderDock === "function") renderDock(); } catch (_) {}
          return false;
        }
        const want = String(row.id || row.name || "");
        const rowBe = String(row.backend || row.source || be);
        if (!want) return false;
        // v0821o136seko-uservspick: 异步搜索期间用户可能已显式改选——应用前再判一次：
        // 当前值较起跑时有变化、适配 op、不跨家 → 保留用户选择，放弃本次重匹配（不许偷换）。
        const nowId = String(sel.value || "").trim();
        if (nowId && nowId !== sidAtStart && nowId !== want && serviceBelongsToBackend(nowId, be)
            && serviceFitsOp(catalogItemForService() || { id: nowId, name: nowId }, op)) {
          writeSmartMatchToShot(shot, nowId);
          try { if (typeof syncOpChip === "function") syncOpChip(); } catch (_) {}
          try { if (typeof renderDock === "function") renderDock(); } catch (_) {}
          return false;
        }
        // v0821o135: 匹配只发生在用户当前选中的家内部——任何时候导入/匹配都不许改用户选的 backend。
        injectCatalogRow(row);
        if (typeof ensureSelectOpt === "function") ensureSelectOpt(sel, want);
        sel.value = want;
        writeSmartMatchToShot(shot, want);
        if (typeof syncOpChip === "function") syncOpChip();
        if (opts.announce !== false) {
          const house = HOUSE_LABEL[rowBe] || rowBe;
          const head = crossHit ? ("跨家搜到 " + house + " · ") : "已搜索匹配";
          try { setMsg(head + (labels[op] || op) + " · " + ((row && row.name) || want) + " · 确认后点 ↑", "ok"); } catch (_) {}
        }
        try { if (typeof syncParamChrome === "function") syncParamChrome(); } catch (_) {}
        try { if (typeof renderDock === "function") renderDock(); } catch (_) {}
        return true;
      } finally {
        if (smartMatchService._inflight && smartMatchService._gen === gen) smartMatchService._inflight = null;
      }
    })();
    smartMatchService._inflight = run;
    return run;
  }

  function filterCatalogForMode(items) {
    const list = Array.isArray(items) ? items : [];
    // text/audio are stub modes — do not list image models (looks like they work).
    if (state.mode === "text" || state.mode === "audio") return [];
    if (state.mode === "video") {
      const op = (typeof currentGraphOp === "function") ? currentGraphOp() : "i2v";
      if (op === "t2v") {
        const t2v = list.filter(catalogItemSupportsT2v);
        return t2v.length ? t2v : list.filter(function (it) {
          const id = String((it && (it.id || it.name)) || "").toLowerCase();
          return id.indexOf("video") >= 0 && !catalogItemSupportsI2v(it);
        });
      }
      return list.filter(catalogItemSupportsI2v);
    }
    if (state.mode === "image") {
      const op = (typeof currentGraphOp === "function") ? currentGraphOp() : "t2i";
      if (op === "upscale") {
        const ups = list.filter(catalogItemSupportsUpscale);
        return ups.length ? ups : list.filter(catalogItemSupportsImage);
      }
      if (op === "inpaint") {
        const inp = list.filter(catalogItemSupportsInpaint);
        if (inp.length) return inp;
        const i2i = list.filter(catalogItemSupportsI2i);
        return i2i.length ? i2i : list.filter(catalogItemSupportsImage);
      }
      const imgs = list.filter(catalogItemSupportsImage);
      if (!selectedShotWantsI2i()) return imgs;
      const i2i = imgs.filter(catalogItemSupportsI2i);
      return i2i.length ? i2i : imgs;
    }
    return list;
  }

    // Provider defaults (capabilities): catalog may only tighten, never raise.
  // Civitai/Fal/HF=9; Nano=5+input_references; Modelscope ceiling=3+image_url (catalog tightens; 2509=3).
  const PROVIDER_REF_CAPS = {
    civitai: { maxRefs: 9, refImagesField: "images" },
    fal: { maxRefs: 9, refImagesField: "image_urls" },
    huggingface: { maxRefs: 9, refImagesField: "image_urls" },
    "nano-gpt": { maxRefs: 5, refImagesField: "input_references" },
    "modelscope-ai": { maxRefs: 3, refImagesField: "image_url" },
    "modelscope-cn": { maxRefs: 3, refImagesField: "image_url" },
  };

  function providerRefDefaults() {
    const fromProv = providerCaps();
    const max = Number(fromProv && (fromProv.maxRefs || fromProv.maxImages));
    const field = fromProv && fromProv.refImagesField;
    if (max > 0 && max < 99) {
      return { maxRefs: max, refImagesField: field || "images" };
    }
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

  function _positiveRefCap(raw) {
    const n = Number(raw);
    return (n > 0 && n < 99) ? n : null;
  }
  function declaredRefCap(it) {
    if (!it) return null;
    const caps = (it.capabilities && typeof it.capabilities === "object") ? it.capabilities : {};
    const sp = it.supported_parameters || {};
    const direct = [
      caps.maxRefs, caps.maxImages, caps.maxRefImages,
      it.maxRefs, it.maxImages, it.referenceLimit,
      sp.max_input_images, sp.max_images,
    ];
    for (let i = 0; i < direct.length; i++) {
      const n = _positiveRefCap(direct[i]);
      if (n != null) return n;
    }
    const cap = capabilityForCatalogItem(it) || it.capability || null;
    if (cap) {
      const fromLimit = _positiveRefCap(cap.referenceLimit);
      if (fromLimit != null) return fromLimit;
      const cons = cap.constraints || {};
      const frameFields = cap.frameFields || [];
      let best = null;
      function consider(rule) {
        if (!rule || typeof rule !== "object") return;
        if (rule.type && rule.type !== "array") return;
        const n = _positiveRefCap(rule.maxItems != null ? rule.maxItems : rule.maxLength);
        if (n != null) best = (best == null) ? n : Math.max(best, n);
      }
      frameFields.forEach(function (f) { consider(cons[f]); });
      Object.keys(cons).forEach(function (k) { consider(cons[k]); });
      if (best != null) return best;
      const multiFrames = { images: 1, referenceImages: 1 };
      const singularFrames = {
        firstFrame: 1, sourceImage: 1, startImage: 1, lastFrame: 1, endImage: 1,
        sourceImageUrl: 1, firstFrameImage: 1, lastFrameImage: 1, endSourceImage: 1,
        image: 1,
      };
      const hasMultiFrame = frameFields.some(function (f) { return multiFrames[f]; });
      const hasSingularFrame = frameFields.some(function (f) { return singularFrames[f]; });
      if (!hasMultiFrame && hasSingularFrame) return 1;
    }
    return null;
  }

  // Resolve caps from catalog item.capabilities (or top-level), clamped to provider default.
  // Catalog may only tighten. Unknown model cap → known=false (do not silent-slice to 9).
  // If imageFields has NO multi bag and only singular FIRST, force maxRefs=1.
  function resolveRefCaps(it) {
    const prov = providerRefDefaults();
    const caps = (it && it.capabilities && typeof it.capabilities === "object") ? it.capabilities : {};
    let declared = declaredRefCap(it);
    const fields = catalogImageFields(it);
    if (fields.length) {
      const hasMulti = fields.some((f) => MULTI_REF_FIELDS.indexOf(f) >= 0);
      const hasSingularFirst = fields.some((f) => SINGULAR_FIRST_FIELDS.indexOf(f) >= 0);
      // No multi bag + singular FIRST → maxRefs=1, unless catalog already says maxRefs>1
      // (Magao Edit-2509: official image_url list 1–3 — same field name, multi values).
      const catalogAllowsList = Number(caps.maxRefs) > 1 || Number(caps.maxImages) > 1;
      if (!hasMulti && (hasSingularFirst || fields.length > 0) && !catalogAllowsList) {
        declared = (declared == null) ? 1 : Math.min(declared, 1);
      }
    }
    const field = (caps.refImagesField || (it && it.refImagesField) || prov.refImagesField || "images");
    if (declared == null) {
      const capRow = (typeof capabilityForCatalogItem === "function") ? capabilityForCatalogItem(it) : null;
      const frameFields = (capRow && capRow.frameFields) || (it && it.frameFields) || [];
      const hasMultiFrame = frameFields.some(function (f) { return f === "images" || f === "referenceImages"; });
      const hasMulti = fields.some((f) => MULTI_REF_FIELDS.indexOf(f) >= 0) || hasMultiFrame;
      if (hasMulti) {
        return { maxRefs: Number(prov.maxRefs) || 9, known: true, refImagesField: String(field) };
      }
      const blob = [it && it.id, it && it.name, it && it.category, it && it.kind, it && it.falCategory, it && it.task]
        .map(function (x) { return String(x || "").toLowerCase(); }).join(" ");
      const looksVideo = blob.indexOf("video") >= 0 || blob.indexOf("image-to-video") >= 0 || blob.indexOf("/i2v") >= 0;
      if (looksVideo && !fields.length && !frameFields.length) {
        return { maxRefs: null, known: false, refImagesField: String(field) };
      }
      return { maxRefs: Number(prov.maxRefs) || 9, known: true, refImagesField: String(field), fromProvider: true };
    }
    const ceil = Number(prov.maxRefs) || 9;
    let max = declared;
    if (max > ceil) max = ceil;
    if (!(max > 0)) max = 1;
    return { maxRefs: max, known: true, refImagesField: String(field) };
  }

  function maxRefCount(it) {
    const resolved = resolveRefCaps(it);
    return resolved.known ? resolved.maxRefs : null;
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
    // Send-path refs are inbound edges only. Own painted card url is display-only
    // (成片 chip) — counting it here would trip t2i unused-ref and block page ↑.
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
    const resolved = resolveRefCaps(catalogItemForService());
    if (nRefs && !resolved.known) {
      return "当前模型参考图上限未知，不能按通用上限截断。请减少连线或改选已声明上限的模型";
    }
    if (resolved.known && nRefs > resolved.maxRefs) {
      const mid = capacityRematchId(nRefs, catalogItemForService());
      if (mid) {
        return "参考图 " + nRefs + "/" + resolved.maxRefs + " · 超过上限，可一键匹配 " + mid + "（不静默丢弃连线）";
      }
      return "参考图 " + nRefs + "/" + resolved.maxRefs + " · 超过上限，请减少连线或改选 maxRefs≥" + nRefs + " 的图生图（不静默丢弃）";
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
    if (typeof catalogItemSupportsI2v === "function" && catalogItemSupportsI2v(it)) return true;
    const caps = (it.capabilities && typeof it.capabilities === "object") ? it.capabilities : {};
    if (caps.image_to_image === true || caps.inpainting === true) return true;
    if (it.needsSource || it.needsFirstFrame) return true;
    if (caps.image_to_image === false) return false;
    const backend = String(it.backend || (typeof currentBackend === "function" ? currentBackend() : "") || "").toLowerCase();
    if (backend === "civitai") {
      const id = String(it.id || "").toLowerCase();
      const op = String(it.operation || "").toLowerCase();
      if (op === "editimage" || op === "createvariant" || id.indexOf("editimage") >= 0 || /\/edit(?:$|\/)/.test(id)) return true;
      if (op === "createimage" || id.indexOf("createimage") >= 0) return false;
    }
    if (backend === "fal") {
      const rawFields = caps.imageFields || it.imageFields || [];
      const fields = Array.isArray(rawFields) ? rawFields : [];
      const id = String(it.id || "").toLowerCase();
      if (/(?:^|\/)image-to-image(?:$|\/)/.test(id) || /(?:^|\/)edit(?:$|\/)/.test(id)) return true;
      if (!fields.length) return false;
    }
    if (backend === "modelscope-ai" || backend === "modelscope-cn" || backend === "modelscope"
        || backend === "huggingface") {
      const task = String(it.task || it.hubTask || "").toLowerCase();
      const tags = Array.isArray(it.tags) ? it.tags.map((t) => String(t).toLowerCase()) : [];
      if (task === "image-to-image" || task === "image-to-video" || tags.indexOf("i2i") >= 0 || tags.indexOf("i2v") >= 0) return true;
      if (task === "text-to-image" || task === "text-to-video" || tags.indexOf("t2i") >= 0 || tags.indexOf("t2v") >= 0) return false;
    }
    return true;
  }
  // Resolve catalog Edit/i2i sibling for a t2i service (no invent — must exist in catalogById).
  function editSiblingId(it) {
    const id = String((it && it.id) || "");
    if (!id || !state.catalogById) return "";
    const candidates = [];
    const slashEdit = id.replace(/\/text-to-image$/, "/edit");
    if (slashEdit !== id) candidates.push(slashEdit);
    // o53b: Fal flux-lora → flux-lora/image-to-image (must exist in catalog)
    if (id && state.catalogById[id + "/image-to-image"]) candidates.push(id + "/image-to-image");
    if (id && state.catalogById[id + "/edit"]) candidates.push(id + "/edit");
    // Nano / common: Foo → Foo Edit, or trailing -edit
    const name = String((it && it.name) || "");
    Object.keys(state.catalogById).forEach(function (cid) {
      const row = state.catalogById[cid];
      if (!row || !catalogEatsRefs(row)) return;
      const rid = String(row.id || cid);
      if (rid === id) return;
      // same family: id prefix match or name "X Edit" for "X"
      if (slashEdit !== id && rid === slashEdit) return; // already in candidates
      if (name && String(row.name || "") === name + " Edit") candidates.push(rid);
      if (id && rid === id + "/edit") candidates.push(rid);
      if (id && rid === id + "/image-to-image") candidates.push(rid);
    });
    for (let i = 0; i < candidates.length; i++) {
      if (state.catalogById[candidates[i]]) return candidates[i];
    }
    return "";
  }
  function editSiblingHint(it) {
    const editId = editSiblingId(it);
    if (editId) {
      const sib = state.catalogById[editId];
      return "可一键改选 " + ((sib && sib.name) || editId) + "，或断开参考连线";
    }
    return "请改选带 Edit 的图生图模型，或断开参考连线";
  }
  // One-click apply Edit sibling (catalog must already have it — never invent).
  function applyEditSibling() {
    const it = catalogItemForService();
    const editId = editSiblingId(it);
    if (!editId) return false;
    const sel = $("service");
    if (!sel) return false;
    ensureSelectOpt(sel, editId);
    if (!state.catalogById) state.catalogById = {};
    if (!state.catalogById[editId]) {
      // should already exist; refuse invent
      return false;
    }
    sel.value = editId;
    try { sel.dispatchEvent(new Event("change", { bubbles: true })); } catch (_) {}
    const shot = nodeById(state.selected);
    if (shot && shot.kind === "shot") shot.serviceId = editId;
    renderDock();
    syncParamSurface();
    const sib = state.catalogById[editId];
    setMsg("已改选图生图：" + ((sib && sib.name) || editId), "ok");
    return true;
  }
  // v0821o53d: rematch candidates from full roster + catalog — not only filtered catalogById.
  // Never invent ids outside official roster / catalog / live /api/catalog.
  const FAL_CAPACITY_HINTS = [
    "fal-ai/flux-2/edit",
    "fal-ai/flux-2-pro/edit",
    "fal-ai/flux-2-flex/edit",
    "fal-ai/flux-lora/image-to-image",
  ];
  function rematchCandidatePool() {
    const byId = {};
    function add(it) {
      if (!it || typeof it !== "object") return;
      const id = String(it.id || it.name || "").trim();
      if (!id) return;
      if (!byId[id]) byId[id] = it;
    }
    Object.keys(state.catalogById || {}).forEach(function (k) { add(state.catalogById[k]); });
    (state.catalog || []).forEach(add);
    (state._serviceItems || []).forEach(add);
    (state._catalogRoster || []).forEach(add);
    return byId;
  }
  function capacityRematchId(nRefs, currentIt, poolOpt) {
    const need = Number(nRefs) || 0;
    const pool = poolOpt || rematchCandidatePool();
    if (!(need > 0) || !pool || !Object.keys(pool).length) return "";
    const curId = String((currentIt && currentIt.id) || ($("service") && $("service").value) || "");
    const curBe = String((currentIt && currentIt.backend) || (typeof currentBackend === "function" ? currentBackend() : "") || ($("backend") && $("backend").value) || "").toLowerCase();
    const curName = String((currentIt && currentIt.name) || "");
    const curFamily = curId.split("/").slice(0, 2).join("/");
    const scored = [];
    Object.keys(pool).forEach(function (cid) {
      const row = pool[cid];
      if (!row) return;
      if (!catalogEatsRefs(row)) return;
      const cap = maxRefCount(row);
      if (!(cap != null && cap >= need)) return;
      const rid = String(row.id || cid);
      if (rid === curId) return;
      const be = String(row.backend || curBe || "").toLowerCase();
      let score = 0;
      if (be && curBe && be === curBe) score += 100;
      else if (curBe === "fal" && (be === "fal" || !row.backend)) score += 100;
      else return;
      if (curFamily && rid.indexOf(curFamily) === 0) score += 40;
      if (curName && String(row.name || "").indexOf(curName.split(" ")[0]) === 0) score += 20;
      if (catalogItemSupportsI2i && catalogItemSupportsI2i(row)) score += 10;
      if (need === 1 && /\/image-to-image$/.test(rid)) score += 80;
      if (need === 1 && rid.indexOf("flux-lora/image-to-image") >= 0) score += 40;
      if (need > 1 && (/\/edit$/.test(rid) || rid.indexOf("flux-2/edit") >= 0)) score += 80;
      scored.push({ id: rid, score: score, cap: cap });
    });
    if (!scored.length) return "";
    scored.sort(function (a, b) {
      if (b.score !== a.score) return b.score - a.score;
      return a.cap - b.cap;
    });
    return scored[0].id;
  }
  function applyCapacityRematchFromWant(want, nRefs, shot) {
    if (!want) return false;
    const pool = rematchCandidatePool();
    let row = pool[want] || (state.catalogById && state.catalogById[want]);
    if (!row) {
      setMsg("参考图 " + nRefs + " · 候选 " + want + " 不在官方目录（不伪造、不静默丢线）", "bad");
      return false;
    }
    if (!state.catalogById) state.catalogById = {};
    if (!state.catalogById[want]) state.catalogById[want] = row;
    const sel = $("service");
    if (!sel) return false;
    ensureSelectOpt(sel, want);
    sel.value = want;
    shot.serviceId = want;
    if ((typeof currentBackend === "function" ? currentBackend() : "") === "fal" || ($("backend") && $("backend").value === "fal")) {
      state._pinFalLoraService = want;
      state._pendingService = want;
      state._capacityRematchLock = want;
    }
    try { sel.dispatchEvent(new Event("change", { bubbles: true })); } catch (_) {}
    if (sel.value !== want && state.catalogById[want]) {
      sel.value = want;
      shot.serviceId = want;
      state._pinFalLoraService = want;
    }
    renderDock();
    syncParamSurface();
    setMsg("已匹配容量：" + ((row && row.name) || want) + " · 参考 " + nRefs + "/" + maxRefCount(row), "ok");
    return true;
  }
  function applyCapacityRematch() {
    const shot = nodeById(state.selected);
    if (!shot || shot.kind !== "shot") return false;
    const nRefs = countRefUrls(null, shot).length;
    const it = catalogItemForService();
    const resolved = resolveRefCaps(it);
    if (!(resolved.known && nRefs > resolved.maxRefs)) {
      setMsg("当前未超上限（" + nRefs + "/" + (resolved.known ? resolved.maxRefs : "?") + "），无需匹配", "warn");
      return false;
    }
    let pool = rematchCandidatePool();
    let want = capacityRematchId(nRefs, it, pool);
    // Prefer known Fal edit hints only if present in pool (never invent)
    if (!want && (($("backend") && $("backend").value) === "fal")) {
      for (let hi = 0; hi < FAL_CAPACITY_HINTS.length; hi++) {
        const hid = FAL_CAPACITY_HINTS[hi];
        if (pool[hid] && catalogEatsRefs(pool[hid]) && maxRefCount(pool[hid]) >= nRefs) {
          want = hid;
          break;
        }
      }
    }
    if (want) return applyCapacityRematchFromWant(want, nRefs, shot);
    // Live refresh Fal/Civitai roster once — still only official /api/catalog rows
    const be = ($("backend") && $("backend").value) || "";
    setMsg("参考图 " + nRefs + "/" + resolved.maxRefs + " · 正在拉取官方目录匹配…", "warn");
    fetch("/api/catalog?backend=" + encodeURIComponent(be || "fal"))
      .then(function (r) { return r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status)); })
      .then(function (j) {
        const roster = j.items || j.models;
        if (!Array.isArray(roster) || !roster.length) {
          setMsg("参考图 " + nRefs + "/" + resolved.maxRefs + " · 官方目录为空，无法匹配（不静默丢线）", "bad");
          return;
        }
        state._catalogRoster = roster.slice();
        state._catalogRosterBackend = be;
        roster.forEach(function (row) {
          const id = row && (row.id || row.name);
          if (!id) return;
          if (!state.catalogById) state.catalogById = {};
          if (!state.catalogById[id]) state.catalogById[id] = row;
        });
        pool = rematchCandidatePool();
        want = capacityRematchId(nRefs, it, pool);
        if (!want && be === "fal") {
          for (let hi = 0; hi < FAL_CAPACITY_HINTS.length; hi++) {
            const hid = FAL_CAPACITY_HINTS[hi];
            if (pool[hid] && catalogEatsRefs(pool[hid]) && maxRefCount(pool[hid]) >= nRefs) {
              want = hid;
              break;
            }
          }
        }
        if (!want) {
          setMsg("参考图 " + nRefs + "/" + resolved.maxRefs + " · 目录无 maxRefs≥" + nRefs + " 的图生图可匹配（不静默丢线）", "bad");
          return;
        }
        applyCapacityRematchFromWant(want, nRefs, shot);
        try { persist(); } catch (_) {}
      })
      .catch(function (err) {
        setMsg("参考图 " + nRefs + "/" + resolved.maxRefs + " · 拉目录失败：" + (err && err.message || err) + "（不静默丢线）", "bad");
      });
    return true; // async in flight — not silent
  }

  function tryCapacityRematchAfterServiceChange() {
    const shot = nodeById(state.selected);
    if (!shot || shot.kind !== "shot") return false;
    const nRefs = countRefUrls(null, shot).length;
    if (!nRefs) return false;
    const it = catalogItemForService();
    const resolved = resolveRefCaps(it);
    if (!(resolved.known && nRefs > resolved.maxRefs)) return false;
    const pool = rematchCandidatePool();
    const want = capacityRematchId(nRefs, it, pool);
    if (!want) return false;
    const row = pool[want] || (state.catalogById && state.catalogById[want]);
    if (!row) return false;
    if (String(it && it.id) === want) return false;
    if (!state.catalogById) state.catalogById = {};
    if (!state.catalogById[want]) state.catalogById[want] = row;
    const sel = $("service");
    if (!sel) return false;
    // Avoid change-event loop: set value then sync without re-entering via change.
    ensureSelectOpt(sel, want);
    sel.value = want;
    shot.serviceId = want;
    state._capacityRematchLock = want;
    state._pinFalLoraService = want;
    return true;
  }

  // v0821o54: same-backend LoRA-capable rematch (Nano prefer flux-lora / *-lora; never invent ids).
  function loraCapabilityRematchId(currentIt, poolOpt) {
    const pool = poolOpt || rematchCandidatePool();
    if (!pool || !Object.keys(pool).length) return "";
    const curId = String((currentIt && currentIt.id) || ($("service") && $("service").value) || "");
    const curBe = String((currentIt && currentIt.backend) || (typeof currentBackend === "function" ? currentBackend() : "") || ($("backend") && $("backend").value) || "").toLowerCase();
    const scored = [];
    Object.keys(pool).forEach(function (cid) {
      const row = pool[cid];
      if (!row) return;
      const rid = String(row.id || cid);
      if (!rid || rid === curId) return;
      const be = String(row.backend || curBe || "").toLowerCase();
      let score = 0;
      if (be && curBe && be === curBe) score += 100;
      else if (curBe === "fal" && (be === "fal" || !row.backend)) score += 100;
      else if ((curBe === "nano-gpt" || curBe === "nanogpt") && (be === "nano-gpt" || be === "nanogpt" || !row.backend)) score += 100;
      else return;
      if (!catalogItemSupportsLora(row)) return;
      const ridL = rid.toLowerCase();
      const nameL = String(row.name || "").toLowerCase();
      if (curBe === "nano-gpt" || curBe === "nanogpt" || be === "nano-gpt" || be === "nanogpt") {
        if (ridL.indexOf("flux-lora") >= 0 || nameL.indexOf("flux-lora") >= 0) score += 100;
        else if (/\/?[\w.-]*lora\b/i.test(rid) || /-lora\b/i.test(rid) || /\/lora/i.test(rid)) score += 80;
      }
      if (curBe === "fal" || be === "fal") {
        if (typeof FAL_FLUX_LORA_SERVICE !== "undefined" && rid === FAL_FLUX_LORA_SERVICE) score += 90;
        else if (ridL.indexOf("flux-lora") >= 0) score += 88;
        if (typeof FAL_LORA_PREF_SERVICE !== "undefined" && rid === FAL_LORA_PREF_SERVICE) score += 85;
        if (/\/lora\b/i.test(rid) || (typeof falEndpointTakesLora === "function" && falEndpointTakesLora(row))) score += 50;
      }
      if (/lora/i.test(rid) || /lora/i.test(nameL)) score += 10;
      scored.push({ id: rid, score: score });
    });
    if (!scored.length) return "";
    scored.sort(function (a, b) {
      if (b.score !== a.score) return b.score - a.score;
      return String(a.id).localeCompare(String(b.id));
    });
    return scored[0].id;
  }

  const NANO_LORA_HINTS = ["flux-lora", "flux-2-dev-lora", "krea-v2/turbo-lora"];
  const FAL_LORA_CAPABILITY_HINTS = ["fal-ai/flux-lora", "fal-ai/flux-lora/image-to-image"];

  function pickLoraHintFromPool(pool, be) {
    const beL = String(be || "").toLowerCase();
    const hints = (beL === "fal")
      ? FAL_LORA_CAPABILITY_HINTS
      : ((beL === "nano-gpt" || beL === "nanogpt") ? NANO_LORA_HINTS : NANO_LORA_HINTS.concat(FAL_LORA_CAPABILITY_HINTS));
    for (let hi = 0; hi < hints.length; hi++) {
      const hid = hints[hi];
      if (pool[hid] && catalogItemSupportsLora(pool[hid])) return hid;
    }
    // Also try Nano/Fal hints when backend not strictly matched but present in pool
    if (beL !== "fal") {
      for (let hi = 0; hi < NANO_LORA_HINTS.length; hi++) {
        const hid = NANO_LORA_HINTS[hi];
        if (pool[hid] && catalogItemSupportsLora(pool[hid])) return hid;
      }
    }
    if (beL === "fal" || !beL) {
      for (let hi = 0; hi < FAL_LORA_CAPABILITY_HINTS.length; hi++) {
        const hid = FAL_LORA_CAPABILITY_HINTS[hi];
        if (pool[hid] && catalogItemSupportsLora(pool[hid])) return hid;
      }
    }
    return "";
  }

  function applyLoraCapabilityRematchFromWant(want, shot, opts) {
    if (!want || !shot) return false;
    const silent = !!(opts && opts.silentChange);
    const pool = rematchCandidatePool();
    let row = pool[want] || (state.catalogById && state.catalogById[want]);
    if (!row) {
      setMsg("候选 " + want + " 不在官方目录（不伪造、不静默丢芯片）", "bad");
      return false;
    }
    if (!state.catalogById) state.catalogById = {};
    if (!state.catalogById[want]) state.catalogById[want] = row;
    const sel = $("service");
    if (!sel) return false;
    ensureSelectOpt(sel, want);
    sel.value = want;
    shot.serviceId = want;
    if ((typeof currentBackend === "function" ? currentBackend() : "") === "fal" || ($("backend") && $("backend").value === "fal")) {
      state._pinFalLoraService = want;
      state._pendingService = want;
    }
    state._loraRematchLock = want;
    if (!silent) {
      try { sel.dispatchEvent(new Event("change", { bubbles: true })); } catch (_) {}
    }
    if (sel.value !== want && state.catalogById[want]) {
      sel.value = want;
      shot.serviceId = want;
    }
    // keep chips
    try { renderDock(); } catch (_) {}
    try { syncParamSurface(); } catch (_) {}
    try { syncLoraUi(); } catch (_) {}
    setMsg("已匹配 LoRA 能力：" + ((row && row.name) || want) + " · 芯片保留", "ok");
    return true;
  }

  function fillCatalogRosterFromApi(roster, be) {
    if (!Array.isArray(roster) || !roster.length) return false;
    state._catalogRoster = roster.slice();
    state._catalogRosterBackend = be;
    roster.forEach(function (row) {
      const id = row && (row.id || row.name);
      if (!id) return;
      if (!state.catalogById) state.catalogById = {};
      // only add missing — never invent ids
      if (!state.catalogById[id]) state.catalogById[id] = row;
    });
    return true;
  }

  function applyLoraCapabilityRematch() {
    if (state._importFamily === "sdxl" || state._importFamily === "pony" || state._importFamily === "sd15") return false;
    const shot = nodeById(state.selected);
    if (!shot || shot.kind !== "shot") {
      setMsg("请先选中分镜再匹配 LoRA 端点", "warn");
      return false;
    }
    const chips = Array.isArray(state.loras) ? state.loras : [];
    if (!chips.length) {
      setMsg("没有 LoRA 芯片，无需匹配", "warn");
      return false;
    }
    const it = catalogItemForService();
    if (catalogItemSupportsLora(it)) {
      setMsg("当前模型已支持 LoRA，无需匹配", "ok");
      return false;
    }
    let pool = rematchCandidatePool();
    let want = loraCapabilityRematchId(it, pool);
    const be = ($("backend") && $("backend").value) || (typeof currentBackend === "function" ? currentBackend() : "") || "";
    // Prefer known Nano/Fal LoRA hints only if present in pool (never invent)
    if (!want) want = pickLoraHintFromPool(pool, be);
    if (want) return applyLoraCapabilityRematchFromWant(want, shot);
    // o54b: live refresh full /api/catalog roster — same as o53d capacity rematch
    setMsg("正在拉取官方目录匹配 LoRA…", "warn");
    state._loraRematchInFlight = true;
    fetch("/api/catalog?backend=" + encodeURIComponent(be || "nano-gpt"))
      .then(function (r) { return r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status)); })
      .then(function (j) {
        state._loraRematchInFlight = false;
        const roster = j.items || j.models;
        if (!fillCatalogRosterFromApi(roster, be)) {
          setMsg("官方目录为空，无法匹配 LoRA（芯片保留，不静默丢掉）", "bad");
          return;
        }
        pool = rematchCandidatePool();
        want = loraCapabilityRematchId(it, pool);
        if (!want) want = pickLoraHintFromPool(pool, be);
        if (!want) {
          setMsg("目录无同后端支持 LoRA 的模型可匹配（芯片保留，不静默丢掉）", "bad");
          return;
        }
        applyLoraCapabilityRematchFromWant(want, shot);
        try { persist(); } catch (_) {}
      })
      .catch(function (err) {
        state._loraRematchInFlight = false;
        setMsg("拉目录匹配 LoRA 失败：" + (err && err.message || err) + "（芯片保留，不静默丢掉）", "bad");
      });
    return true; // async in flight — not silent
  }

  function tryLoraCapabilityRematchAfterServiceChange() {
    const chips = Array.isArray(state.loras) ? state.loras : [];
    if (!chips.length) return false;
    const shot = nodeById(state.selected);
    if (!shot || shot.kind !== "shot") return false;
    const it = catalogItemForService();
    if (catalogItemSupportsLora(it)) return false;
    // Avoid change-event / rematch loops
    if (state._loraRematchLock && String(it && it.id) === String(state._loraRematchLock)) {
      state._loraRematchLock = "";
      return false;
    }
    if (state._loraRematchInFlight) return true;
    let pool = rematchCandidatePool();
    let want = loraCapabilityRematchId(it, pool);
    const be = ($("backend") && $("backend").value) || (typeof currentBackend === "function" ? currentBackend() : "") || "";
    if (!want) want = pickLoraHintFromPool(pool, be);
    if (want) {
      const row = pool[want] || (state.catalogById && state.catalogById[want]);
      if (!row) return false;
      if (String(it && it.id) === want) return false;
      // Avoid change-event loop: set value then sync without re-entering via change.
      return applyLoraCapabilityRematchFromWant(want, shot, { silentChange: true });
    }
    // o54b: chips && !supportsLora && !want → kick async roster fetch (not silent forever)
    setMsg("正在拉取官方目录匹配 LoRA…", "warn");
    state._loraRematchInFlight = true;
    fetch("/api/catalog?backend=" + encodeURIComponent(be || "nano-gpt"))
      .then(function (r) { return r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status)); })
      .then(function (j) {
        state._loraRematchInFlight = false;
        const roster = j.items || j.models;
        if (!fillCatalogRosterFromApi(roster, be)) {
          setMsg("官方目录为空，无法匹配 LoRA（芯片保留，不静默丢掉）", "bad");
          return;
        }
        const it2 = catalogItemForService();
        if (catalogItemSupportsLora(it2)) return;
        pool = rematchCandidatePool();
        want = loraCapabilityRematchId(it2, pool);
        if (!want) want = pickLoraHintFromPool(pool, be);
        if (!want) {
          setMsg("目录无同后端支持 LoRA 的模型可匹配（芯片保留，不静默丢掉）", "bad");
          return;
        }
        // silentChange to avoid re-entrant infinite rematch on change
        applyLoraCapabilityRematchFromWant(want, shot, { silentChange: true });
        try { syncParamChrome(); } catch (_) {}
        try { persist(); } catch (_) {}
      })
      .catch(function (err) {
        state._loraRematchInFlight = false;
        setMsg("拉目录匹配 LoRA 失败：" + (err && err.message || err) + "（芯片保留，不静默丢掉）", "bad");
      });
    return true; // async started
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
  // Dev/acceptance: attach distinct local fixture refs until outbound N==cap (灌满).
  // v0821o40: same 口径 as UI hint + hard-gate = countRefUrls (excludes own shot.url).
  // 成片 chip is visual-only — never stuff into outbound; never let it make 灌满 look 6/5.
  // Page path still human-clickable.
  function fillRefSlotsToCap(shot) {
    shot = shot || nodeById(state.selected);
    if (!shot || shot.kind !== "shot") return 0;
    const it = catalogItemForService();
    if (!catalogEatsRefs(it)) return 0; // refuse fill on t2i — use Edit sibling first
    const cap = maxRefCount(it);
    let urls = countRefUrls(null, shot);
    let added = 0;
    let n = assets().length;
    // v0821o41: use real staged fixtures /out/fill-cap-{i}.jpg (never phantom o40-fill-*.png)
    while (urls.length < cap) {
      const idx = urls.length + 1;
      if (idx > 9) break; // only 9 staged fixtures
      const id = uid("fillref");
      const url = "/out/fill-cap-" + idx + ".jpg";
      const node = {
        id: id,
        kind: "character",
        title: "灌满" + idx,
        x: (shot.x || 0) - 160,
        y: (shot.y || 0) + n * 36,
        url: url,
        fillFixture: true,
      };
      state.nodes.push(node);
      linkAssetToShot(node, shot);
      n += 1;
      added += 1;
      urls = countRefUrls(null, shot);
      if (urls.length > cap) break; // never N>cap
    }
    return added;
  }

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
    const field = resolved.refImagesField || "images";
    // Never silent-slice. Over-cap / unknown cap is a hard gate before attach.
    // Do NOT infer "always 1" from field name alone — honor cap.
    payload.images = urls;
    // Keep/ensure primary wires when present.
    if (primary) {
      if (!payload.firstFrame) payload.firstFrame = primary;
      if (!payload.sourceImage) payload.sourceImage = primary;
    }
    // Optional mirror onto provider-native field (not the sole bag).
    if (field && field !== "images") {
      if (field === "image_url") {
        // modelscope singular: BOTH images=[url] and image_url=url
        payload.image_url = urls[0];
      } else {
        payload[field] = urls;
      }
    }
    // v0821: also stamp provider-correct singular FIRST (Fal start_image_url / image_url / …)
    // so packed inbound keeps first-frame even when compile default was t2v-ish.
    if (primary || urls[0]) {
      const firstUrl = primary || urls[0];
      const imgFields = catalogImageFields(catalogItemForService());
      let stamped = false;
      imgFields.forEach(function (f) {
        if (SINGULAR_FIRST_FIELDS.indexOf(f) >= 0) {
          if (!payload[f]) payload[f] = firstUrl;
          stamped = true;
        }
      });
      // Fal i2v common aliases when catalog row lacks imageFields
      // v0821o136seko-civfalfield: 只对 fal 后端补 Fal 别名——civitai 配方吃官方 sourceImage/firstFrame，
      // 混入 image_url 会被服务端诚实硬门拒（「Civitai 不接受 Fal 字段 image_url」），不许静默改名。
      const _beForAlias = (typeof currentBackend === "function") ? currentBackend() : "";
      if (!stamped && state.mode === "video" && _beForAlias === "fal") {
        if (!payload.start_image_url && !payload.image_url && !payload.first_frame_url) {
          payload.start_image_url = firstUrl;
          payload.image_url = firstUrl;
        }
      }
    }
    const last = lastFrameAsset(shot);
    if (last && last.url) {
      payload.lastFrame = last.url;
      payload.end_image_url = last.url;
      payload.last_frame_url = last.url;
      const lastFields = catalogImageFields(catalogItemForService());
      lastFields.forEach(function (f) {
        const n = String(f || "").toLowerCase();
        if (n === "last_frame_url" || n === "end_image_url" || n === "end_image" || n === "last_frame_image" || n === "lastframe") {
          if (!payload[f]) payload[f] = last.url;
        }
      });
    }
    if (shot.maskUrl) {
      payload.mask = shot.maskUrl;
      payload.mask_url = shot.maskUrl;
      payload.mask_image_url = shot.maskUrl;
      const maskFields = catalogImageFields(catalogItemForService());
      maskFields.forEach(function (f) {
        if (/mask/.test(String(f || "").toLowerCase()) && !payload[f]) payload[f] = shot.maskUrl;
      });
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
    persistShotFrame(nodeById(state.selected));
  }
  function closestAspectChoice(width, height) {
    const w = Number(width), h = Number(height);
    if (!Number.isFinite(w) || !Number.isFinite(h) || w <= 0 || h <= 0) return null;
    const ratio = w / h;
    let best = ASPECT_CHOICES[0];
    ASPECT_CHOICES.forEach(function (item) {
      if (Math.abs(item[1] - ratio) < Math.abs(best[1] - ratio)) best = item;
    });
    return { name: best[0], ratio: best[1], err: Math.abs(best[1] - ratio) };
  }
  function syncAspectFromSize(width, height) {
    const aspectEl = $("aspect");
    const hit = closestAspectChoice(width, height);
    if (!aspectEl || !hit || hit.err > 0.04) return;
    aspectEl.value = hit.name;
  }
  function isSilentSizeDefault(w, h) {
    const key = String(w) + "x" + String(h);
    return key === "960x1440" || key === "1440x960"
      || key === "2048x2048" || key === "1024x1024"
      || key === "512x768" || key === "768x512";
  }
  function ensureComposerSize() {
    const w = $("width") ? parseInt($("width").value, 10) : NaN;
    const h = $("height") ? parseInt($("height").value, 10) : NaN;
    const aspect = ($("aspect") && $("aspect").value) || "16:9";
    const res = ($("res") && $("res").value) || "720P";
    if (Number.isFinite(w) && w > 0 && Number.isFinite(h) && h > 0) {
      const mapped = sizeFromAspectRes(aspect, res);
      const mappedRatio = mapped.width / mapped.height;
      const ratio = w / h;
      if (Math.abs(ratio - mappedRatio) <= 0.04) {
        /* keep exact pixels (import 944×1672 + 9:16) */
      } else {
        const hit = closestAspectChoice(w, h);
        if (hit && hit.err <= 0.04) {
          if (isSilentSizeDefault(w, h) && hit.name !== aspect) applyAspectToSize();
          else $("aspect").value = hit.name;
        } else if (isSilentSizeDefault(w, h)) {
          applyAspectToSize();
        }
      }
    } else {
      applyAspectToSize();
    }
    persistShotFrame(nodeById(state.selected) || shots()[0]);
  }

  function buildGraph(shot) {
    const frame = frameAsset(shot);
    const linked = connectedAssets(shot.id);
    const nodes = [{ id: "p-" + shot.id, op: "prompt", params: { text: normalizePrompt(shot) } }];
    const edges = [{ from: "p-" + shot.id, fromPort: "prompt", to: shot.id, toPort: "prompt" }];
    linked.forEach((a) => nodes.push({ id: a.id, op: "image", params: { url: a.url } }));
    let op = "t2i";
    // v0821o136seko-t2vop: 与 currentGraphOp() 对齐——视频模式无首帧 = 文生视频(t2v)，
    // 不许硬编码 i2v 让图编译层报「未连线输入口 image」这种错层错误。
    if (state.mode === "video") op = frame ? "i2v" : "t2v";
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
    // v0821o23: civitai outbound prefers imported shot.serviceId / sdxl eco — never silent krea2.
    if (be === "civitai") {
      const opNow = (typeof currentGraphOp === "function") ? currentGraphOp() : op;
      const pickedFits = pickedService && (typeof catalogItemForService === "function")
        && serviceFitsOp(catalogItemForService(), opNow);
      if ((opNow === "i2i" || opNow === "i2v") && pickedFits) {
        serviceId = pickedService;
      } else if ((opNow === "i2i" || opNow === "i2v") && pickedService) {
        serviceId = pickedService;
      } else {
        serviceId = resolveCivitaiOutboundServiceId(shot);
      }
    } else if (!serviceId && be === "huggingface") {
      serviceId = (typeof pickSmartServiceId === "function" && pickSmartServiceId(op))
        || (op === "i2i" ? HF_I2I_PREF_SERVICE : op === "i2v" ? "Wan-AI/Wan2.2-TI2V-5B" : HF_LORA_PREF_SERVICE);
    } else if (!serviceId && (be === "modelscope-ai" || be === "modelscope-cn")) {
      serviceId = (typeof pickSmartServiceId === "function" && pickSmartServiceId(op))
        || (op === "t2i" ? MS_LORA_PREF_SERVICE : "");
    } else if (!serviceId && be === "nano-gpt") {
      serviceId = (typeof pickSmartServiceId === "function" && pickSmartServiceId(op)) || "";
    } else if (!serviceId && be === "fal") {
      // v0821o136seko-t2vop: t2v 不许走 LoRA 图像端点解析，也不许塞 t2i 默认（flux/schnell
      // 收视频 payload 是错层冒充）——只认目录里真 text-to-video 端点，找不到就空着硬门拦。
      if (op !== "i2v" && op !== "t2v" && falHasLoras()) {
        const resolved = resolveFalLoraEndpointFromChips();
        serviceId = resolved.endpoint || "";
      } else serviceId = (op === "i2v" ? FAL_I2V_DEFAULT
        : op === "t2v" ? ((typeof pickSmartServiceId === "function" && pickSmartServiceId("t2v")) || "")
        : FAL_T2I_DEFAULT);
    }
    if (be === "huggingface") {
      serviceId = pinHfLoraServiceId(serviceId, op);
    }
    if (be === "modelscope-ai" || be === "modelscope-cn") {
      serviceId = pinMsLoraServiceId(serviceId, op);
    }
    if (be === "fal" && op !== "i2v") {
      serviceId = pinFalLoraServiceId(serviceId);
    }
    const genParams = {
      serviceId: serviceId,
    };
    if (be === "civitai" && !/\/fal\//.test(String(serviceId || ""))) {
      // width/height/steps/cfgScale/sampler/scheduler — seed packed in runShotStep (wire-only compile rule)
      ["width", "height", "steps", "cfgScale", "cfg", "sampler", "scheduler"].forEach(function (k) {
        if (comfy[k] != null) genParams[k] = comfy[k];
      });
      if (genParams.width == null) genParams.width = w;
      if (genParams.height == null) genParams.height = h;
    } else if (be === "civitai") {
      // v0821o136seko-civrestoken: Civitai /fal/ videoGen 配方（wan 家族）的 resolution
      // 是档位枚举（480p/580p/720p），不是像素 WxH——发像素会撞「不在允许列表」诚实硬门。
      // 发 #res 原始档位 token（720P），由 io_meta fold 到官方枚举；1080P 不在枚举时硬门照常拒绝。
      genParams.resolution = ($("res") && $("res").value) || "720P";
      genParams.aspectRatio = aspect;
    } else if (be === "nano-gpt") {
      const token = ($("nanoRes") && $("nanoRes").value) || "";
      if (token) genParams.resolution = token;
      else {
        genParams.resolution = res;
        genParams.aspectRatio = aspect;
      }
    } else {
      // v0821o136seko-falschema: 发送边界同步判定——CSS 标记有异步时序，
      // 官方 schema 字段表（official_fields）在 payload 边界再拦一次，杜绝竞赛漏发 steps/aspect。
      const _ofItem = (typeof catalogItemForService === "function") ? catalogItemForService() : null;
      const _ofAllow = function (f) {
        const A = (typeof window !== "undefined") ? window.ComposerFieldAdapt : null;
        if (!A || typeof A.officialFieldAllowed !== "function") return true;
        const r = A.officialFieldAllowed(_ofItem, f);
        return r !== false; // null=无表不拦; false=官方没有该字段
      };
      // Image APIs take width/height. Do not pack canvas duration/aspect/resolution
      // into Fal/HF/MS t2i — those keys 400 when the endpoint schema has no such field.
      if (be === "modelscope-ai" || be === "modelscope-cn" || be === "fal" || be === "huggingface") {
        genParams.width = w;
        genParams.height = h;
        // stage3 fix: user-filled steps/cfg/sampler/scheduler must reach the
        // request when the field is usable for this backend (provider does
        // schema-checked forwarding / honest reject). Silent UI omission = 摆设.
        const _usable = function (id) {
          const el = $(id);
          if (!el || el.disabled) return false;
          const wrap = el.closest(".param-field");
          if (wrap && (wrap.classList.contains("param-unsupported") || wrap.classList.contains("hidden"))) return false;
          return true;
        };
        if (_usable("steps") && _ofAllow("steps") && comfy.steps != null) genParams.steps = comfy.steps;
        if (_usable("cfg") && _ofAllow("cfg") && comfy.cfgScale != null) { genParams.cfgScale = comfy.cfgScale; genParams.cfg = comfy.cfg; }
        if (_usable("sampler") && _ofAllow("sampler") && comfy.sampler) genParams.sampler = comfy.sampler;
        if (_usable("scheduler") && _ofAllow("scheduler") && comfy.scheduler) genParams.scheduler = comfy.scheduler;
      } else {
        genParams.resolution = res;
      }
      if (op === "i2v" || state.mode === "video") {
        const pc = (typeof catalogCaps === "function") ? catalogCaps() : {};
        const durEl = $("duration");
        if (pc.videoDuration && durEl && !durEl.classList.contains("hidden") && !durationGateMessage() && _ofAllow("duration")) {
          const durN = parseDurationSeconds(durEl.value);
          if (Number.isFinite(durN)) genParams.duration = durN;
        }
        const aspectEl = $("aspect");
        // Magao official AIGC key is size (width×height already packed). Do not also send aspect_ratio.
        // v0821o136seko-falschema: 官方 schema 无 aspect_ratio 的端点（kling i2v）不发，服务端诚实硬门实测 400。
        if (pc.videoAspect && aspectEl && !aspectEl.classList.contains("hidden")
            && be !== "modelscope-ai" && be !== "modelscope-cn" && _ofAllow("aspect")) {
          genParams.aspectRatio = aspect;
        }
      }
    }
    // v0821o136-seko: 数量 1-4 — 只在家/模型官方支持数量参数时才随请求发出。
    const qtyN = $("quantity") ? parseInt($("quantity").value, 10) : 1;
    if (Number.isFinite(qtyN) && qtyN > 1) {
      const itQ = (typeof catalogItemForService === "function") ? catalogItemForService() : null;
      const spQ = (itQ && itQ.supported_parameters) || {};
      const qtyOk = be === "civitai" || spQ.num_images != null || spQ.quantity != null || spQ.n != null;
      if (qtyOk) {
        genParams.quantity = qtyN;
      } else {
        setMsg("当前模型目录未标注数量支持 · 已按 1 张发送", "warn");
      }
    }
    nodes.push({
      id: shot.id, op: op,
      params: genParams,
    });
    // v0821o136seko-t2vop: t2v 无 image 输入口——连线资产不得偷接成 image 边（编译层会硬拒）。
    const ref = (op === "i2v") ? frame : (op === "t2v" ? null : linked[0]);
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
    if (isJunkRailItem(item)) return;
    state.history = [item].concat((state.history || []).filter((h) => h && h.url !== url && !isJunkRailItem(h))).slice(0, 24);
  }
  function removeUnpromotedFromShot(shotId) {
    const removed = new Set(state.nodes
      .filter((n) => n && n.kind !== "shot" && n.kind !== "text" && n.fromShot && !n.userPromoted && (!shotId || n.fromShot === shotId))
      .map((n) => n.id));
    if (!removed.size) return false;
    state.nodes = state.nodes.filter((n) => !removed.has(n.id));
    state.edges = state.edges.filter((e) => !removed.has(e.from) && !removed.has(e.to));
    state.nodes.forEach((n) => {
      if (n.kind === "shot" && removed.has(n.firstFrameId)) n.firstFrameId = "";
    });
    state.groups = (state.groups || []).map((g) => ({
      id: g.id,
      name: g.name,
      memberIds: (g.memberIds || []).filter((id) => !removed.has(id)),
    })).filter((g) => (g.memberIds || []).length);
    if (removed.has(state.selected)) state.selected = shotId || null;
    state.multi = (state.multi || []).filter((id) => !removed.has(id));
    return true;
  }

  // v0821o46: pending jobId↔shotId — survives tab OOM so boot can resume writeback
  const PENDING_JOBS_KEY = "nl-pending-jobs-v0821o46";
  function readLocalPending() {
    try {
      const raw = localStorage.getItem(PENDING_JOBS_KEY);
      const j = raw ? JSON.parse(raw) : {};
      return (j && typeof j === "object" && j.jobs && typeof j.jobs === "object") ? j.jobs : {};
    } catch (_) { return {}; }
  }
  function writeLocalPending(jobs) {
    try { localStorage.setItem(PENDING_JOBS_KEY, JSON.stringify({ jobs: jobs || {} })); } catch (_) {}
  }
  function registerPendingJob(jobId, shotId, backend) {
    const jid = String(jobId || "").trim();
    const sid = String(shotId || "").trim();
    if (!jid || !sid) return;
    const jobs = readLocalPending();
    // o49b: retire other jobIds mapped to same shotId (local + DELETE server)
    const retire = [];
    for (const oldId of Object.keys(jobs)) {
      if (oldId === jid) continue;
      const rec = jobs[oldId];
      if (rec && String(rec.shotId || "") === sid) retire.push(oldId);
    }
    for (let i = 0; i < retire.length; i++) {
      const oldId = retire[i];
      delete jobs[oldId];
      try {
        fetch("/api/pending-jobs/" + encodeURIComponent(oldId), { method: "DELETE", keepalive: true }).catch(function () {});
      } catch (_) {}
    }
    jobs[jid] = { shotId: sid, backend: String(backend || ""), startedAt: Date.now() };
    writeLocalPending(jobs);
    try {
      fetch("/api/pending-jobs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ jobId: jid, shotId: sid, backend: backend || "" }),
        keepalive: true,
      }).catch(function () {});
    } catch (_) {}
  }
  function clearPendingJob(jobId) {
    const jid = String(jobId || "").trim();
    if (!jid) return;
    const jobs = readLocalPending();
    if (jobs[jid]) {
      delete jobs[jid];
      writeLocalPending(jobs);
    }
    try {
      fetch("/api/pending-jobs/" + encodeURIComponent(jid), { method: "DELETE", keepalive: true }).catch(function () {});
    } catch (_) {}
  }
  async function mergeServerPending() {
    try {
      const r = await fetch("/api/pending-jobs");
      if (!r.ok) return readLocalPending();
      const j = await r.json();
      const list = (j && j.jobs) || [];
      const jobs = readLocalPending();
      for (let i = 0; i < list.length; i++) {
        const row = list[i];
        if (!row || !row.jobId || !row.shotId) continue;
        if (!jobs[row.jobId]) {
          jobs[row.jobId] = { shotId: row.shotId, backend: row.backend || "", startedAt: Date.now() };
        }
      }
      writeLocalPending(jobs);
      return jobs;
    } catch (_) {
      return readLocalPending();
    }
  }
  async function resumeOnePending(jobId, rec) {
    const jid = String(jobId || "").trim();
    const sid = rec && rec.shotId;
    if (!jid || !sid) return;
    let shot = nodeById(sid);
    if (!shot || shot.kind !== "shot") {
      // graph may have shot after hydrate; try again from state
      shot = (state.nodes || []).find(function (n) { return n && n.id === sid && n.kind === "shot"; });
    }
    if (!shot) {
      clearPendingJob(jid);
      return;
    }
    // o49b: do not write old /out onto a card that already moved on
    if (shot._jobId && String(shot._jobId) !== jid) {
      clearPendingJob(jid);
      return;
    }
    const existingUrl = shot.url != null ? String(shot.url).trim() : "";
    if (existingUrl && String(shot._jobId || "") !== jid) {
      clearPendingJob(jid);
      return;
    }
    const bePoll = String((rec && rec.backend) || shot._backend || "").trim();
    const materializing = bePoll === "civitai" || bePoll === "fal" || bePoll === "huggingface"
      || bePoll === "modelscope-ai" || bePoll === "modelscope-cn" || !bePoll;
    try {
      setShotBusy(shot, true);
      setMsg("恢复任务写回 · " + jid.slice(0, 12) + "…", "warn");
      let j = null;
      const pollMax = (bePoll === "civitai") ? 720 : 180;
      const pollMs = 2500;
      for (let i = 0; i < pollMax; i++) {
        const st = await (await fetch("/api/jobs/" + encodeURIComponent(jid))).json();
        j = st;
        const stStatus = String((st && st.status) || "").toUpperCase();
        const inFlight = stStatus === "IN_QUEUE" || stStatus === "IN_PROGRESS"
          || stStatus === "PENDING" || stStatus === "PROCESSING" || stStatus === "RUNNING"
          || stStatus === "PREPARING" || stStatus === "PREPARED" || stStatus === "QUEUED"
          || stStatus === "SCHEDULED";
        // o46b: upstream failed but local /out (server injects saved[] / localOutResume) → still writeback
        if ((st.error || st.status === "failed") && !inFlight) {
          const failSaved = (st && st.pendingWriteback && st.pendingWriteback.url)
            || pickSavedUrl(st);
          if (failSaved) {
            writebackResult(shot, failSaved);
            clearPendingJob(jid);
            setShotBusy(shot, false);
            setMsg("上游失败但本地成片已写回原卡", "ok");
            try { renderCards(); drawWires(); renderDock(); } catch (_) {}
            return;
          }
          clearPendingJob(jid);
          setShotBusy(shot, false);
          setMsg("恢复失败: " + (st.error || st.message || "任务失败"), "bad");
          return;
        }
        // Server belt may already have written shot.url via pendingWriteback
        if (st && st.pendingWriteback && st.pendingWriteback.url) {
          writebackResult(shot, st.pendingWriteback.url);
          clearPendingJob(jid);
          setShotBusy(shot, false);
          setMsg("已恢复写回原卡（服务端）", "ok");
          try { renderCards(); drawWires(); renderDock(); } catch (_) {}
          return;
        }
        const savedUrl = pickSavedUrl(st);
        if (savedUrl) {
          writebackResult(shot, savedUrl);
          clearPendingJob(jid);
          setShotBusy(shot, false);
          setMsg("已恢复写回原卡", "ok");
          try { renderCards(); drawWires(); renderDock(); } catch (_) {}
          return;
        }
        if (!materializing && pickUrl(st)) {
          writebackResult(shot, pickUrl(st));
          clearPendingJob(jid);
          setShotBusy(shot, false);
          setMsg("已恢复写回原卡", "ok");
          try { renderCards(); drawWires(); renderDock(); } catch (_) {}
          return;
        }
        if (i === 0) {
          // also check if hydrate already has newer url containing job fragment
          continue;
        }
        await new Promise(function (res) { setTimeout(res, pollMs); });
        setMsg("恢复写回轮询 " + (i + 1) + "/" + pollMax, "warn");
      }
      setShotBusy(shot, false);
      setMsg("恢复写回超时 · job 仍 pending: " + jid, "warn");
    } catch (e) {
      try { setShotBusy(shot, false); } catch (_) {}
      setMsg("恢复写回异常: " + (e && e.message ? e.message : String(e)), "bad");
    }
  }
  async function resumePendingJobs() {
    const jobs = await mergeServerPending();
    const ids = Object.keys(jobs || {});
    if (!ids.length) return;
    for (let i = 0; i < ids.length; i++) {
      await resumeOnePending(ids[i], jobs[ids[i]]);
    }
  }

  function writebackResult(shot, url) {
    // Hard gate: media lands on the originating shot card (shot.url). History stays;
    // canvas clones still require 入库 / 拖到画布 / explicit pin — never auto-promote.
    // v0821o16: re-attach orphan shot into state.nodes before persist/PUT (avoid empty nodes 400).
    // v0821o18: keep live.url even if a later hydrate races; always refresh dock/chat after card write.
    if (!shot || !url) return;
    let live = nodeById(shot.id);
    if (!live) {
      if (shot.kind === "shot") state.nodes.push(shot);
      live = shot;
    }
    live.url = url;
    shot.url = url; // keep caller reference in sync (poll path may hold stale shot obj)
    const nowTs = Date.now();
    live._urlUpdatedAt = nowTs;
    live.urlUpdatedAt = nowTs;
    shot._urlUpdatedAt = nowTs;
    shot.urlUpdatedAt = nowTs;
    removeUnpromotedFromShot(live.id);
    const frame = (typeof frameAsset === "function") ? frameAsset(live) : null;
    if (frame && frame.id && !(state.edges || []).some((e) => e.from === frame.id && e.to === live.id)) {
      state.edges.push({ from: frame.id, to: live.id });
    }
    pushHistoryItem(url, (live.title || "分镜") + (isVideoUrl(url) ? "视频" : "成片"));
    renderRail();
    if (typeof renderChatRail === "function") renderChatRail();
    try { renderCards(); drawWires(); renderDock(); } catch (_) {}
    persist();
    persistServer();
    if (typeof persistActiveCanvas === "function") persistActiveCanvas();
    if (live && live._jobId) clearPendingJob(live._jobId);
    else if (shot && shot._jobId) clearPendingJob(shot._jobId);
  }

  function pickSavedUrl(data) {
    // v0821o16: ONLY materialized saved[]/files (and result.saved/files) — never steps CDN.
    if (!data) return "";
    const first = (arr) => {
      if (!arr || !arr[0]) return "";
      const x = arr[0];
      if (typeof x === "string") return x;
      return (x && (x.url || x.path || x.previewUrl)) || "";
    };
    const savedHit = first(data.saved) || first(data.files);
    if (savedHit) return savedHit;
    if (data.result && typeof data.result === "object") {
      const rs = first(data.result.saved) || first(data.result.files);
      if (rs) return rs;
    }
    return "";
  }

    function pickUrl(data) {
    // v0821i/v0821c/v0821o12: prefer local saved[] /out; then civitai steps[].output; CDN fallback.
    if (!data) return "";
    const first = (arr) => {
      if (!arr || !arr[0]) return "";
      const x = arr[0];
      if (typeof x === "string") return x;
      // civitai blobs expose url and/or previewUrl
      return (x && (x.url || x.path || x.previewUrl)) || "";
    };
    // 1) materialized /out (or any saved/files) — survives refresh
    const savedHit = pickSavedUrl(data);
    if (savedHit) return savedHit;
    // pickSavedUrl already checked result.saved/files — keep CDN path below
    // 1b) civitai orchestration: steps[].output.images[].url (same class as i2v missing shape)
    if (Array.isArray(data.steps)) {
      for (let si = 0; si < data.steps.length; si++) {
        const out = data.steps[si] && data.steps[si].output;
        if (!out || typeof out !== "object") continue;
        const stepHit = first(out.images) || first(out.videos) || first(out.blobs) || first(out.files);
        if (stepHit) return stepHit;
        if (out.image) {
          const iu = out.image.url || out.image.previewUrl || (typeof out.image === "string" ? out.image : "");
          if (iu) return iu;
        }
        if (out.video) {
          const vu = out.video.url || (typeof out.video === "string" ? out.video : "");
          if (vu) return vu;
        }
      }
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
    try {
      return await runShotStepWork(shotId, opts);
    } finally {
      keepComposerPromptVisible();
    }
  }
  async function runShotStepWork(shotId, opts) {
    opts = opts || {};
    const shot = nodeById(shotId);
    const prefix = opts.progressPrefix ? (opts.progressPrefix + " · ") : "";
    function fail(err, status, cls, meta) {
      meta = meta || {};
      const info = formatErrInfo(err);
      const be = String(meta.backend || (typeof currentBackend === "function" ? currentBackend() : "") || "");
      const jid = String(meta.jobId || "");
      if (jid || be) {
        const tag = [be && ("backend=" + be), jid && ("jobId=" + jid)].filter(Boolean).join(" ");
        if (tag) {
          info.excerpt = (info.excerpt ? (info.excerpt + "\n") : "") + tag;
          try { console.warn("[outbound-fail]", { backend: be, jobId: jid, error: info.text }); } catch (_) {}
        }
      }
      const text = prefix + info.text;
      if (shot && shot.kind === "shot") {
        shot._error = info.text;
        if (jid) shot._jobId = jid;
        if (be) shot._backend = be;
        if (info.excerpt) shot._errorDetail = info.excerpt;
        else delete shot._errorDetail;
      }
      setMsg(text, cls || "bad", info.excerpt);
      if (shot) setShotBusy(shot, false);
      if (!opts.keepSend) markSendBusy(false);
      state.dockMode = "expanded";
      renderCards();
      renderDock();
      // o46: clear pending only on terminal fail — keep on wait-timeout/abort so boot can resume
      if (jid && (status === "error" || (cls || "bad") === "bad")) {
        try { clearPendingJob(jid); } catch (_) {}
      }
      const out = { status: status || "blocked", error: text };
      if (jid) out.jobId = jid;
      if (be) out.backend = be;
      return out;
    }
    if (!shot || shot.kind !== "shot") {
      return fail("请先选中分镜再生成", "blocked");
    }
    clearShotError(shot);
    if (state.groupRunAbort) {
      return fail("已中止", "aborted", "warn");
    }
    const dependency = upstreamImageBlock(shot);
    if (dependency) {
      return fail(dependency, "blocked");
    }
    if (isStubMode()) {
      return fail((state.mode === "text" ? "文本生成" : "音频生成") + " · 本版未接", "blocked", "warn");
    }
    if (state.mode === "video") {
      const opVid = (typeof currentGraphOp === "function") ? currentGraphOp() : "i2v";
      if (opVid === "i2v" && !frameAsset(shot)) {
        return fail("缺首帧 · 切到图片生成，或先上传/选择首帧（图生视频需要首帧；文生视频点「文生视频」）", "blocked");
      }
      const sidVid = ($("service") && $("service").value) || "";
      const itVid = catalogItemForService() || (sidVid ? { id: sidVid } : null);
      if (opVid === "i2v" && sidVid && !catalogItemSupportsI2v(itVid)) {
        return fail("当前服务不吃首帧（非 i2v），请改选视频/图生视频模型", "blocked");
      }
      if (opVid === "t2v" && sidVid && catalogItemSupportsI2v(itVid) && !catalogItemSupportsT2v(itVid)) {
        return fail("当前是图生视频模型，文生视频请改选 text-to-video 端点", "blocked");
      }
    }
    // v0821k: before POST — fal i2v / catalog-required prompt; hard red, no soft-fill
    if (needsPromptBeforeGenerate()) {
      return fail("此模型需要提示词", "blocked");
    }
    // v0820c-hard-service: empty civitai #service → hard error, abort (no Krea2 soft-fill).
    // v0821o23: resolve from shot.serviceId / ecosystem when #service drifted to krea2.
    if (currentBackend() === "civitai") {
      const civSid = resolveCivitaiOutboundServiceId(shot);
      if (!civSid) {
        return fail("请先选择 Civitai 服务（不会默认填入 Krea2）", "blocked");
      }
      syncCivitaiServiceSelect(civSid);
    }
    // v0821n2: LoRA chips in UI but none ship with air → hard red, do not generate/POST
    if (chipsLackAirForOutbound()) {
      return fail(outboundLoraBlockMsg(), "blocked");
    }
    const gate = paramGateMessage();
    if (gate) {
      return fail(gate, "blocked");
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
      return fail(e, "error");
    }
    if (state.groupRunAbort) {
      return fail("已中止", "aborted", "warn");
    }
    if (!compiled.ok) {
      return fail(compiled.error || "校验未通过", "blocked");
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
        return fail((compiled.note || "多步链需按序物化上游") + " · 禁止一次假跑通", "blocked", "warn");
      }
      payload = fillStageRefs(stage.payload, shot.stageUrls);
      if (hasUnresolvedStageOut(payload)) {
        return fail("上游还没有成片地址，不能偷配方台图 · 禁止一次假跑通", "blocked");
      }
    } else {
      // single-step only — never stage-zero payload fallback
      payload = compiled.payload;
      if (!payload) {
        return fail("没有 payload", "blocked");
      }
    }
    const stageOp = stage ? stage.op : "";
    // Hard gate: over-cap / unknown cap must block — never silent-drop N-1.
    const refUrls = countRefUrls(payload, shot);
    const resolvedRefs = resolveRefCaps(catalogItemForService());
    const unusedMsg = refUnusedGateMessage(shot);
    if (unusedMsg) {
      return fail(unusedMsg, "blocked");
    }
    if (refUrls.length && !resolvedRefs.known) {
      return fail("当前模型参考图上限未知，不能按通用上限截断。请减少连线或改选已声明上限的模型", "blocked");
    }
    if (resolvedRefs.known && refUrls.length > resolvedRefs.maxRefs) {
      return fail("参考图 " + refUrls.length + "/" + resolvedRefs.maxRefs + " · 超过上限，请减少连线后再生成（不静默丢弃）", "blocked");
    }
    attachExtraImages(payload, shot);
    // v0816-sb-lora: attach selected LoRAs (index.html base.loras shape)
    // v0821n2/o10: chips without air / mixed / unsupported already gated; never ship a filtered subset
    {
      const packedLoras = packLorasForPayload();
      const list = Array.isArray(state.loras) ? state.loras : [];
      if (list.length && (!packedLoras || !packedLoras.length)) {
        return fail(outboundLoraBlockMsg(), "blocked");
      }
      // v0821o22: partial drop honesty — some chips lack air/path; do not pretend full pack
      if (list.length && packedLoras && packedLoras.length && packedLoras.length < list.length) {
        const dropped = list.length - packedLoras.length;
        try {
          setMsg("LoRA 出站 " + packedLoras.length + "/" + list.length + " · 已丢 " + dropped + " 个无 air/path 的芯片（不静默）", "warn");
        } catch (_) {}
      }
      if (packedLoras && packedLoras.length) {
        payload.loras = packedLoras;
        // v0821o29: outbound Fal serviceId by LoRA AIR base (flux1→flux-lora; krea2→krea).
        if (currentBackend() === "fal") {
          const unsupported = falLoraUnsupportedMsg();
          if (unsupported) return fail(unsupported, "blocked");
          const pinned = pinFalLoraServiceId(payload.serviceId || ($("service") && $("service").value) || "");
          if (!pinned) return fail(falLoraUnsupportedMsg() || "Fal LoRA 端点不支持（不硬钉错误家族）", "blocked");
          payload.serviceId = pinned;
          payload.endpoint = pinned;
          ensureFalLoraServiceSelected();
        } else if (currentBackend() === "huggingface") {
          const unsupported = hfLoraUnsupportedMsg();
          if (unsupported) return fail(unsupported, "blocked");
          const pinned = pinHfLoraServiceId(payload.serviceId || ($("service") && $("service").value) || "", currentGraphOp());
          if (!pinned) return fail(hfLoraUnsupportedMsg() || "HF LoRA 端点不支持（不硬钉无 LoRA 的 Hub turbo）", "blocked");
          payload.serviceId = pinned;
          payload.endpoint = pinned;
          ensureHfLoraServiceSelected();
        } else if (currentBackend() === "modelscope-ai" || currentBackend() === "modelscope-cn") {
          const pinned = pinMsLoraServiceId(payload.serviceId || ($("service") && $("service").value) || "", currentGraphOp());
          payload.serviceId = pinned;
          payload.endpoint = pinned;
          ensureMsLoraServiceSelected();
        }
      }
    }
    // v0820-civitai-comfy-params: merge steps/cfg/sampler/scheduler/seed/size — no silent drop
    {
      // v0821o38: pack from generate shot (not only selected/lastComposerShot)
      const packedComfy = packComfyParamsForPayload(shot);
      if (packedComfy) {
        Object.keys(packedComfy).forEach(function (k) {
          if (packedComfy[k] != null && packedComfy[k] !== "") payload[k] = packedComfy[k];
        });
      }
      // v0821o38: after merge, force payload.diffusionModel from shot when set (no silent drop)
      if (shot && shot.diffusionModel != null && String(shot.diffusionModel).trim()) {
        payload.diffusionModel = String(shot.diffusionModel).trim();
      }
      if (usesCivitaiComfyParams()) {
        // v0821o23: imported sdxl serviceId wins over drifted #service / catalog krea2 pref.
        // Never CIVITAI_PREF / _civitaiDefaultService soft-fill when empty.
        // i2i/i2v: keep the live #service if it fits the op (import t2i recipe must not steal edit/video).
        const opNow = (typeof currentGraphOp === "function") ? currentGraphOp() : "";
        const uiSid = ($("service") && $("service").value) || "";
        let sid = resolveCivitaiOutboundServiceId(shot);
        if ((opNow === "i2i" || opNow === "i2v") && uiSid) sid = uiSid;
        if (!sid) {
          return fail("请先选择 Civitai 服务（不会默认填入 Krea2）", "blocked");
        }
        syncCivitaiServiceSelect(sid);
        payload.serviceId = sid;
        // seed: keep full numeric (no int32 clamp) — Civitai seeds can exceed 2^31-1
        // v0821o38: flux1 (or sid needing diffuser) without dm → hard reject before POST
        const sidL = String(sid || "").toLowerCase();
        const needsDm = /\/flux1\//.test(sidL) || /diffuser|diffusionmodel|sdcpp\/flux/.test(sidL);
        const dmOut = payload.diffusionModel != null ? String(payload.diffusionModel).trim() : "";
        if (needsDm && !dmOut) {
          return fail("缺少 diffusionModel（diffuserModel）· flux1 出站前必须有 checkpoint AIR，禁止假跑", "blocked");
        }
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
    const outSid = String((payload && payload.serviceId) || ($("service") && $("service").value) || "");
    // stage3 fix: do NOT silently strip steps/cfg for Fal — providers/fal.py
    // already forwards schema-supported fields and honestly rejects the rest.
    if (/\/fal\//.test(outSid) || /^fal[-.]ai\//i.test(outSid)) {
      // sampler/scheduler have no Fal schema home; keep the historical strip.
      delete payload.sampler;
      delete payload.scheduler;
    }
    if (outSid === "image/textToImage") {
      delete payload.sampler;
    }
    if (payload && payload.seed != null) {
      const seedNum = Number(payload.seed);
      if (!Number.isFinite(seedNum) || seedNum < 0) delete payload.seed;
    }
    setShotBusy(shot, true);
    shot._error = "";
    let jobId = "";
    let bePoll = "";
    try {
      const r = await fetch("/api/generate", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      let j = await r.json();
      jobId = String((j && (j.id || j.jobId || j.workflowId)) || "");
      bePoll = currentBackend() || (payload && payload.backend) || "";
      if (shot) {
        if (jobId) shot._jobId = jobId;
        if (bePoll) shot._backend = bePoll;
      }
      if (jobId && shot && shot.id) registerPendingJob(jobId, shot.id, bePoll);
      if (!r.ok || (j && j.error)) throw (j.error || j.message || j.detail || ("HTTP " + r.status));
      // Materializing backends download CDN → /out saved[]; do not treat steps CDN as done.
      const materializing = bePoll === "civitai" || bePoll === "fal" || bePoll === "huggingface"
        || bePoll === "modelscope-ai" || bePoll === "modelscope-cn";
      // Enter poll unless we already have saved[] (materializing) or any url (others).
      if (jobId && !(materializing ? pickSavedUrl(j) : pickUrl(j))) {
        // v0821m: MiniMax i2v success ~7min; old 40×2.5s=100s → false「没有可预览地址」while Fal IN_PROGRESS.
        // Hub image (魔搭 AI) routinely exceeds 100s — keep "? 180 : 40" then extend Hub ticks.
        const isVideoPoll = (state.mode === "video" || (payload && payload.kind === "video") || (stageOp === "i2v"));
        let pollMax = isVideoPoll ? 180 : 40;
        const pollMs = isVideoPoll ? 3000 : 2500;
        // v0821o12: civitai comfy (krea2) same class as fal/hub — allow materialize+download ticks
        if (!isVideoPoll && materializing) {
          pollMax = 120;
          // v0821o37: civitai image preparing can exceed 5min (sample ~29min) — ≥720 @ 2.5s ≈30min
          if (bePoll === "civitai") {
            pollMax = 720;
          }
        }
        for (let i = 0; i < pollMax; i++) {
          if (state.groupRunAbort) {
            return fail("已中止", "aborted", "warn");
          }
          await new Promise((res) => setTimeout(res, pollMs));
          const st = await (await fetch("/api/jobs/" + encodeURIComponent(jobId))).json();
          const stStatus = String((st && st.status) || "").toUpperCase();
          // civitai submit lands as preparing — not a terminal error
          const inFlight = stStatus === "IN_QUEUE" || stStatus === "IN_PROGRESS"
            || stStatus === "PENDING" || stStatus === "PROCESSING" || stStatus === "RUNNING"
            || stStatus === "PREPARING" || stStatus === "PREPARED" || stStatus === "QUEUED"
            || stStatus === "SCHEDULED";
          if ((st.error || st.status === "failed") && !inFlight) {
            // Throw raw so fail() → formatErrInfo keeps English in excerpt.
            throw (st.error || (st.wait && st.wait.log) || st.message || "任务失败");
          }
          // v0821o16: materializing → break only on saved[]; else CDN/pickUrl ok for early break.
          j = st;
          if (materializing) {
            if (pickSavedUrl(st)) break;
          } else if (pickSavedUrl(st) || pickUrl(st)) {
            break;
          }
          const doneish = st.status === "done" || st.status === "succeeded" || st.status === "completed";
          const tick = (i + 1) + "/" + pollMax;
          if (prefix) setMsg(prefix + (doneish ? "成片落盘中 " : "云端进行中 ") + tick);
          else setAckMsg((doneish ? "成片落盘中 " : "云端进行中 ") + tick);
        }
      }
      if (state.groupRunAbort) {
        return fail("已中止", "aborted", "warn");
      }
      // Materialized /out preferred; CDN (pickUrl) only as fallback after poll ends.
      const savedUrl = pickSavedUrl(j);
      const url = savedUrl || pickUrl(j);
      const durable = !!(savedUrl && String(savedUrl).indexOf("/out/") === 0);
      if (url && materializing && !durable) {
        try {
          setMsg((prefix || "") + "成片暂为 CDN 地址（尚未落 /out）· 硬刷可能丢 · jobId=" + (jobId || "?"), "warn");
        } catch (_) {}
      }
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
        clearShotError(shot);
        shot.url = url;
        writebackResult(shot, url);
        renderCards(); drawWires(); persist();
        if (!durable && materializing) {
          setMsg(prefix + "此镜完成（CDN 暂存，未落 /out）", "warn");
        } else {
          setMsg(prefix + "此镜完成，已写入卡片", "ok");
        }
      } else if (url) {
        clearShotError(shot);
        shot.url = url;
        writebackResult(shot, url);
        renderCards(); drawWires(); persist();
        if (!durable && materializing) {
          setMsg(prefix + "此镜完成（CDN 暂存，未落 /out）", "warn");
        } else {
          setMsg(prefix + "此镜完成，已写入卡片", "ok");
        }
      } else {
        // v0821o37: stillGoing must mirror inFlight (preparing/scheduled/queued/prepared)
        const stillGoing = !!(j && (
          /^(pending|processing|running|in_queue|in_progress|preparing|prepared|scheduled|queued)$/i.test(String(j.status || ""))
          || j.status === "IN_QUEUE" || j.status === "IN_PROGRESS"
          || !j.status
        ));
        return fail(stillGoing
          ? "等待超时，云端任务仍在进行中（可稍后用任务 id 再查）"
          : "云端已返回，没有可预览地址", "blocked", stillGoing ? "warn" : "bad",
          { jobId: jobId, backend: bePoll });
      }
    } catch (e) {
      return fail(e, "error", "bad", { jobId: jobId, backend: bePoll || (typeof currentBackend === "function" ? currentBackend() : "") });
    }
    setShotBusy(shot, false);
    if (!opts.keepSend) markSendBusy(false);
    renderDock();
    return { status: "done", stageOp: stageOp };
  }

  function showSendToast(text, cls) {
    const foot = $("dockFoot");
    if (!foot) return;
    let el = $("sendToast");
    if (!el) {
      el = document.createElement("div");
      el.id = "sendToast";
      el.className = "send-toast";
      el.setAttribute("role", "status");
      el.setAttribute("aria-live", "assertive");
      foot.insertBefore(el, foot.firstChild);
    }
    el.hidden = false;
    el.className = "send-toast" + (cls ? (" " + cls) : "");
    el.textContent = text == null ? "" : String(text);
    try { el.setAttribute("data-send-toast", "1"); } catch (_) {}
    if (showSendToast._timer) clearTimeout(showSendToast._timer);
    // Keep reject toasts until next success ack; soft acks auto-clear.
    if (cls !== "bad" && cls !== "warn") {
      showSendToast._timer = setTimeout(function () {
        if (el && el.className.indexOf("bad") < 0 && el.className.indexOf("warn") < 0) el.hidden = true;
      }, 4200);
    }
  }
  function surfaceSendReject(err, cls, shot) {
    const tone = cls || "bad";
    const text = err == null ? "无法生成" : String(err);
    try {
      const btn = $("send");
      if (btn) {
        btn.setAttribute("data-last-reject", text.slice(0, 180));
        btn.setAttribute("data-send-fired", "1");
      }
    } catch (_) {}
    if (shot && shot.kind === "shot" && typeof paintShotFail === "function") {
      paintShotFail(shot, text, tone);
    } else {
      setMsg(text, tone);
      state.dockMode = "expanded";
      try { renderDock(); } catch (_) {}
    }
    showSendToast(text, tone);
    try { setParamWarn(text, true); } catch (_) {}
    return text;
  }
  function setSendVisual(blocked, reason) {
    const on = !!blocked;
    const why = reason || (on ? "blocked" : "enabled");
    ["send", "sendCap"].forEach(function (id) {
      const btn = $(id);
      if (!btn) return;
      btn.disabled = false;
      btn.setAttribute("aria-disabled", on ? "true" : "false");
      btn.classList.toggle("is-blocked", on);
      btn.title = on ? ("不可生成 · " + why) : "生成 · enabled";
      btn.setAttribute("data-testid", "composer-send");
      btn.setAttribute("data-enabled", on ? "0" : "1");
      btn.setAttribute("data-reason", why);
    });
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
    const n = (typeof composerShot === "function" ? composerShot() : null) || nodeById(state.selected);
    if (!n || n.kind !== "shot") {
      setSendVisual(true, "no-shot");
      return;
    }
    const needFrame = state.mode === "video" && (typeof currentGraphOp !== "function" || currentGraphOp() !== "t2v") && !frameAsset(n);
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
    if (typeof keepComposerPromptVisible === "function") keepComposerPromptVisible();
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
    // v0821o30: prove click reached fireSend (even if a gate rejects next)
    try {
      btn.setAttribute("data-send-fired", "1");
      btn.setAttribute("data-send-fired-at", String(now));
    } catch (_) {}
    // v0821l: blocking gates BEFORE 已点生成 — empty↑ must stay on red, not get re-acked
    const n = (typeof composerShot === "function" ? composerShot() : null) || nodeById(state.selected);
    if (!n || n.kind !== "shot") {
      if (typeof surfaceSendReject === "function") surfaceSendReject("请先选中分镜再生成", "bad", null);
      else setMsg("请先选中分镜再生成", "bad");
      return;
    }
    const failUi = function (err) {
      // v0821o30: never silent — expand capsule, keep collapsed .msg.bad visible, toast near ↑
      if (typeof surfaceSendReject === "function") surfaceSendReject(err, "bad", n);
      else if (typeof paintShotFail === "function") paintShotFail(n, err, "bad");
      else setMsg(err, "bad");
    };
    if (isStubMode()) {
      failUi((state.mode === "text" ? "文本生成" : "音频生成") + " · 本版未接");
      return;
    }
    if (state.mode === "video" && (typeof currentGraphOp !== "function" || currentGraphOp() !== "t2v") && !frameAsset(n)) {
      failUi("缺首帧 · 切到图片生成，或先上传/选择首帧");
      return;
    }
    if (needsPromptBeforeGenerate()) {
      failUi("此模型需要提示词");
      return;
    }
    if (chipsLackAirForOutbound()) {
      failUi(outboundLoraBlockMsg());
      return;
    }
    if (currentBackend() === "fal" && falHasLoras()) {
      const falBaseGate = falLoraUnsupportedMsg();
      if (falBaseGate) { failUi(falBaseGate); return; }
      const pinnedNow = pinFalLoraServiceId(($("service") && $("service").value) || "");
      if (!pinnedNow) { failUi(falLoraUnsupportedMsg() || "Fal LoRA 端点不支持"); return; }
    }
    if (currentBackend() === "huggingface" && hfHasLoras()) {
      const hfBaseGate = hfLoraUnsupportedMsg();
      if (hfBaseGate) { failUi(hfBaseGate); return; }
      const pinnedHf = pinHfLoraServiceId(($("service") && $("service").value) || "");
      if (!pinnedHf) { failUi(hfLoraUnsupportedMsg() || "HF LoRA 端点不支持"); return; }
    }
    const gate = paramGateMessage();
    if (gate) {
      failUi(gate);
      return;
    }
    // v0821l: only ack when proceeding to generate()
    setMsg("已点生成");
    if (typeof showSendToast === "function") showSendToast("已点生成", "ok");
    try { btn.removeAttribute("data-last-reject"); } catch (_) {}
    generate();
  }

  function bindSendButton() {
    ["send", "sendCap"].forEach(function (id) {
      const btn = $(id);
      if (!btn || btn.dataset.nlSendBound === "1") return;
      btn.dataset.nlSendBound = "1";
      btn.type = "button";
      btn.disabled = false;
      btn.setAttribute("data-testid", "composer-send");
      btn.onclick = null;
      btn.addEventListener("click", fireSend, true);
      btn.addEventListener("pointerdown", fireSend);
    });
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

  function bindLoraCapabilityRematchClick() {
    if (bindLoraCapabilityRematchClick._done) return;
    bindLoraCapabilityRematchClick._done = true;
    function onAct(ev) {
      const act = ev.target && ev.target.closest && ev.target.closest('[data-act="lora-capability-rematch"]');
      if (!act) return;
      try { ev.preventDefault(); } catch (_) {}
      applyLoraCapabilityRematch();
      try { persist(); } catch (_) {}
    }
    const block = $("loraBlock");
    if (block) block.addEventListener("click", onAct);
    const foot = $("dockFoot");
    if (foot) foot.addEventListener("click", onAct);
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
    const shot = (typeof composerShot === "function" ? composerShot() : null) || nodeById(state.selected);
    if (!shot || shot.kind !== "shot") {
      setMsg("请先选中分镜再生成", "bad");
      return;
    }
    if (state.selected !== shot.id) state.selected = shot.id;
    if (needsPromptBeforeGenerate()) {
      paintShotFail(shot, "此模型需要提示词", "bad");
      return;
    }
    setAckMsg("校验连线…");
    markSendBusy(true);
    try {
      await runShotStep(state.selected, {});
    } catch (e) {
      paintShotFail(nodeById(state.selected), e, "bad");
    } finally {
      markSendBusy(false);
      if (typeof keepComposerPromptVisible === "function") keepComposerPromptVisible();
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
    const pop = $("addPop");
    if (!pop) { addBlankShot(); return; }
    pop.hidden = !pop.hidden;
  };
  if ($("addPop")) {
    $("addPop").addEventListener("click", (e) => {
      const btn = e.target.closest("[data-add]");
      if (!btn) return;
      $("addPop").hidden = true;
      if (btn.dataset.add === "upload") {
        state._uploadFree = true;
        if ($("file")) $("file").click();
        return;
      }
      addBlankShot();
    });
  }
  document.addEventListener("click", (e) => {
    const pop = $("addPop");
    if (!pop || pop.hidden) return;
    if (e.target.closest("#addPop,#btnAdd")) return;
    pop.hidden = true;
  });
  // v0821o136-seko: Seko 式竖排图标 rail — + / 生成历史 / 技能 / 资产。
  function syncRailToolState() {
    const rail = $("assetRail");
    const histOn = !!(rail && !rail.hidden && state.railTab === "history");
    const assetOn = !!(rail && !rail.hidden && state.railTab !== "history");
    if ($("btnRailHistory")) $("btnRailHistory").classList.toggle("on", histOn);
    if ($("btnHistoryTop")) $("btnHistoryTop").classList.toggle("on", histOn);
    if ($("btnRailAssets")) $("btnRailAssets").classList.toggle("on", assetOn);
    const tools = document.querySelector(".tools");
    const fly = $("toolsFly");
    const skillsOn = !!(fly && !fly.hidden);
    if (tools) tools.classList.toggle("skills-open", skillsOn);
    if ($("btnRailSkills")) {
      $("btnRailSkills").classList.toggle("on", skillsOn);
      $("btnRailSkills").setAttribute("aria-expanded", skillsOn ? "true" : "false");
    }
  }
  function toggleAssetRail(tab) {
    const rail = $("assetRail");
    if (!rail) return;
    if (!rail.hidden && state.railTab === tab) {
      rail.hidden = true;
    } else {
      state.railTab = tab;
      rail.hidden = false;
      renderRail();
      positionDock();
    }
    syncRailToolState();
  }
  if ($("btnRailHistory")) $("btnRailHistory").onclick = () => toggleAssetRail("history");
  if ($("btnHistoryTop")) $("btnHistoryTop").onclick = () => toggleAssetRail("history");
  if ($("btnRailAssets")) $("btnRailAssets").onclick = () => toggleAssetRail("assets");
  if ($("btnRailSkills")) $("btnRailSkills").onclick = () => {
    const fly = $("toolsFly");
    if (!fly) return;
    fly.hidden = !fly.hidden;
    syncRailToolState();
  };
  syncRailToolState();

  // v0821o136-seko: Composer 底行 — 能力徽标 / @引用 / 数量 / 费用预估 / 高级参数折叠。
  function syncSvcCaps() {
    const el = $("svcCaps");
    if (!el) return;
    const it = (typeof catalogItemForService === "function") ? catalogItemForService() : null;
    if (!it) { el.innerHTML = ""; return; }
    const badges = [];
    const caps = (it.capabilities && typeof it.capabilities === "object") ? it.capabilities : {};
    const sp = (it.supported_parameters && typeof it.supported_parameters === "object") ? it.supported_parameters : {};
    let resTok = "";
    if (Array.isArray(caps.resolutionTokens) && caps.resolutionTokens.length) resTok = String(caps.resolutionTokens[caps.resolutionTokens.length - 1]);
    else if (Array.isArray(sp.resolutions) && sp.resolutions.length) resTok = String(sp.resolutions[sp.resolutions.length - 1]);
    else if (typeof sp.resolution === "string") resTok = sp.resolution;
    if (resTok) badges.push('<span class="badge">' + esc(resTok) + "</span>");
    const maxRefs = (typeof maxRefCount === "function") ? maxRefCount(it) : null;
    if (Number.isFinite(maxRefs) && maxRefs > 0) badges.push('<span class="badge">支持 ' + maxRefs + ' 个参考</span>');
    if (caps.supportsLora === true) badges.push('<span class="badge">LoRA</span>');
    el.innerHTML = badges.join("");
  }
  let _costTimer = 0;
  let _costKey = "";
  function scheduleCostRefresh() {
    const el = $("costHint");
    if (!el) return;
    const shot = nodeById(state.selected);
    if (!shot || shot.kind !== "shot" || state.dockMode !== "expanded") { el.textContent = "✦—"; _costKey = ""; return; }
    const sid = ($("service") && $("service").value) || "";
    if (!sid) { el.textContent = "✦—"; _costKey = ""; return; }
    const key = [($("backend") && $("backend").value) || "", sid, state.mode,
      ($("width") && $("width").value) || "", ($("height") && $("height").value) || "",
      ($("quantity") && $("quantity").value) || ""].join("|");
    if (key === _costKey) return;
    _costKey = key;
    clearTimeout(_costTimer);
    el.textContent = "✦…";
    _costTimer = setTimeout(refreshCostHint, 650);
  }
  async function refreshCostHint() {
    const el = $("costHint");
    if (!el) return;
    const key = _costKey;
    try {
      const shot = nodeById(state.selected);
      if (!shot || shot.kind !== "shot") throw new Error("no shot");
      const rc = await fetch("/api/graph/compile", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify(buildGraph(shot)),
      });
      const compiled = await rc.json();
      if (!compiled || compiled.ok === false || !compiled.payload) throw new Error("compile");
      const rw = await fetch("/api/whatif", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify(compiled.payload),
      });
      const data = await rw.json();
      if (key !== _costKey) return; // stale response
      let n = null;
      const cost = data && data.cost;
      if (typeof cost === "number" && Number.isFinite(cost)) n = cost;
      else if (cost && typeof cost === "object") {
        ["total", "amount", "buzz", "points", "value"].forEach(function (k) {
          if (n == null && Number.isFinite(Number(cost[k]))) n = Number(cost[k]);
        });
      }
      if (n == null && data && Number.isFinite(Number(data.buzzCost))) n = Number(data.buzzCost);
      el.textContent = n != null ? ("✦" + n) : "✦—";
      el.title = n != null ? "费用预估" : "费用预估 · 该家暂无价格数据";
    } catch (_) {
      if (key === _costKey) el.textContent = "✦—";
    }
  }
  if ($("btnAt")) $("btnAt").onclick = () => {
    const p = $("prompt");
    if (p) { try { p.focus(); } catch (_) {} }
    showAtbox("");
  };
  if ($("advToggle")) $("advToggle").onclick = () => {
    const p = $("advParams");
    if (!p) return;
    p.hidden = !p.hidden;
    $("advToggle").setAttribute("aria-expanded", p.hidden ? "false" : "true");
    $("advToggle").textContent = p.hidden ? "高级参数 ▾" : "高级参数 ▴";
    requestAnimationFrame(positionDock);
  };
  const sekoRow = $("sekoRow");
  if (sekoRow) {
    sekoRow.addEventListener("change", (e) => {
      const id = e.target && e.target.id;
      if (id === "quantity" || id === "aspect" || id === "res" || id === "service" || id === "backend") {
        syncSvcCaps();
        scheduleCostRefresh();
      }
    });
  }
  function addBlankShot() {
    const n = shots().length;
    const id = uid("shot");
    const pos = newShotPosition(n);
    state.mode = "image";
    state.nodes.push({
      id: id, kind: "shot", title: "分镜" + (n + 1),
      x: pos.x, y: pos.y,
      url: "", firstFrameId: "",
      prompt: "",
      mode: "image",
      composer: { backend: ($("backend") && $("backend").value) || "civitai", service: "", mode: "image", fields: {}, loras: [] },
    });
    renderCards();
    drawWires();
    selectNode(id, { preserveLayout: true });
    persist();
  }
  function syncNodeTools() {
    const tools = document.querySelector(".tools");
    if (!tools) return;
    const shot = nodeById(state.selected);
    const hasShot = !!(shot && shot.kind === "shot");
    const multi = !!(state.multi && state.multi.length >= 2);
    tools.classList.toggle("has-shot", hasShot);
    tools.classList.toggle("has-multi", multi);
    tools.classList.toggle("has-group", multi);
    const needUrl = !!(hasShot && shot.url);
    ["btnDownload", "btnCrop", "btnNine", "btnPano", "btnLight", "btnCamera", "btnUpscale", "btnErase"].forEach(function (id) {
      const el = $(id);
      if (el) el.disabled = !needUrl;
    });
    if ($("btnEditNode")) $("btnEditNode").disabled = !hasShot;
    if ($("btnStory")) $("btnStory").disabled = !hasShot;
    if ($("btnT2v")) $("btnT2v").disabled = !hasShot;
    if ($("btnLast")) $("btnLast").disabled = !hasShot;
  }
  function selectedShot() {
    return (typeof composerShot === "function" ? composerShot() : null) || (function () {
      const n = nodeById(state.selected);
      return (n && n.kind === "shot") ? n : null;
    })();
  }
  function loadImageEl(url) {
    return new Promise(function (resolve, reject) {
      const img = new Image();
      img.crossOrigin = "anonymous";
      img.onload = function () { resolve(img); };
      img.onerror = function () { reject(new Error("读图失败")); };
      img.src = url;
    });
  }
  async function uploadDataUrl(dataUrl, filename) {
    const r = await fetch("/api/upload-out", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ dataUrl: dataUrl, filename: filename || "crop.jpg" }),
    });
    let j = null;
    try { j = await r.json(); } catch (_) {}
    if (r.ok && j && j.url) return j.url;
    throw new Error((j && j.error) || ("上传失败 HTTP " + r.status));
  }
  function downloadShot(shot) {
    if (!shot || !shot.url) { setMsg("这一镜还没有成片", "warn"); return; }
    const a = document.createElement("a");
    a.href = shot.url;
    a.download = (shot.title || "shot") + (isVideoUrl(shot.url) ? ".mp4" : ".jpg");
    a.target = "_blank";
    a.rel = "noopener";
    document.body.appendChild(a);
    a.click();
    a.remove();
  }
  function editSelectedShot() {
    const shot = selectedShot();
    if (!shot) { setMsg("先点一个分镜", "warn"); return; }
    state.dockMode = "expanded";
    selectNode(shot.id, { expand: true, preserveLayout: true });
    const p = $("prompt");
    if (p) {
      try { p.focus(); p.select(); } catch (_) {}
    }
    setMsg("在写字台改提示词，确认后点 ↑", "ok");
  }
  async function nineGridFromShot(shot, setId) {
    shot = shot || selectedShot();
    if (!shot || !shot.url) { setMsg("先有成片再做九宫格", "warn"); return; }
    const set = NINE_SETS[setId] || NINE_SETS.camera;
    const src = box(shot);
    const cellW = src.w + 36;
    const cellH = src.h + 36;
    const originX = shot.x + src.w + 72;
    const originY = shot.y;
    const created = [];
    set.forEach(function (cell, i) {
      const gx = i % 3;
      const gy = Math.floor(i / 3);
      const node = spawnLinkedShot(shot, {
        titleSuffix: " · " + cell.title,
        prompt: ((shot.prompt || "").trim() + "\n" + cell.prompt + "。keep identity, wardrobe, and lighting.").trim(),
        mode: "image",
        firstFrameFromSource: true,
        skipSelect: true,
        skipPan: true,
      });
      if (!node) return;
      node.x = originX + gx * cellW;
      node.y = originY + gy * cellH;
      created.push(node);
    });
    renderCards(); drawWires(); persist(); persistServer();
    const gridW = cellW * 3;
    const gridH = cellH * 3;
    const r = vp.getBoundingClientRect();
    const needS = Math.min(state.cam.s || 0.5, (r.width * 0.62) / gridW, (r.height * 0.62) / gridH);
    state.cam.s = Math.max(0.22, needS);
    state.cam.x = r.width * 0.52 - (originX + gridW / 2) * state.cam.s;
    state.cam.y = r.height * 0.46 - (originY + gridH / 2) * state.cam.s;
    applyCam();
    setMsg("九宫格 9 个机位已铺开 · 正在按成片生成", "ok");
    generateShotQueue(created, "九宫格");
  }
  function showNinePop(anchor) {
    const shot = selectedShot();
    if (!shot || !shot.url) { setMsg("先有成片再做九宫格", "warn"); return; }
    hideToolPops();
    let pop = $("ninePop");
    if (!pop) {
      pop = document.createElement("div");
      pop.id = "ninePop";
      pop.className = "story-pop";
      pop.innerHTML = '<button type="button" data-nine="camera">多机位</button>' +
        '<button type="button" data-nine="story">故事叙述</button>' +
        '<button type="button" data-nine="storm">灵感风暴</button>';
      document.body.appendChild(pop);
      pop.addEventListener("click", function (ev) {
        const b = ev.target.closest("[data-nine]");
        if (!b) return;
        pop.hidden = true;
        nineGridFromShot(selectedShot(), b.getAttribute("data-nine"));
      });
    }
    placePop(pop, anchor || document.querySelector('#shotBar [data-shot-tool="btnNine"]') || $("btnNine"));
  }
  function showSplitPop(anchor) {
    const shot = selectedShot();
    if (!shot || !shot.url) { setMsg("先有成片再切分画面", "warn"); return; }
    hideToolPops();
    let pop = $("splitPop");
    if (!pop) {
      pop = document.createElement("div");
      pop.id = "splitPop";
      pop.className = "story-pop";
      pop.innerHTML = '<button type="button" data-split="lr">左右切分</button>' +
        '<button type="button" data-split="tb">上下切分</button>';
      document.body.appendChild(pop);
      pop.addEventListener("click", function (ev) {
        const b = ev.target.closest("[data-split]");
        if (!b) return;
        pop.hidden = true;
        splitFromShot(selectedShot(), b.getAttribute("data-split"));
      });
    }
    placePop(pop, anchor || document.querySelector('#shotBar [data-shot-tool="btnSplit"]') || $("btnSplit"));
  }
  async function splitFromShot(shot, axis) {
    shot = shot || selectedShot();
    if (!shot || !shot.url) { setMsg("先有成片再切分画面", "warn"); return; }
    try {
      const img = await loadImageEl(shot.url);
      const w = img.naturalWidth, h = img.naturalHeight;
      const parts = axis === "tb"
        ? [{ title: "上", sx: 0, sy: 0, sw: w, sh: Math.floor(h / 2) }, { title: "下", sx: 0, sy: Math.floor(h / 2), sw: w, sh: h - Math.floor(h / 2) }]
        : [{ title: "左", sx: 0, sy: 0, sw: Math.floor(w / 2), sh: h }, { title: "右", sx: Math.floor(w / 2), sy: 0, sw: w - Math.floor(w / 2), sh: h }];
      const canvas = document.createElement("canvas");
      const created = [];
      for (let i = 0; i < parts.length; i++) {
        const p = parts[i];
        canvas.width = p.sw;
        canvas.height = p.sh;
        canvas.getContext("2d").drawImage(img, p.sx, p.sy, p.sw, p.sh, 0, 0, p.sw, p.sh);
        const url = await uploadDataUrl(canvas.toDataURL("image/jpeg", 0.92), (shot.title || "shot") + "-" + p.title + ".jpg");
        const node = spawnLinkedShot(shot, {
          titleSuffix: " · " + p.title,
          prompt: shot.prompt || "",
          mode: "image",
          skipSelect: true,
          skipPan: true,
        });
        if (!node) continue;
        node.url = url;
        node.x = shot.x + box(shot).w + 48;
        node.y = shot.y + i * (box(shot).h + 28);
        created.push(node);
      }
      renderCards(); drawWires(); persist(); persistServer();
      if (created[0]) panTo(created[0]);
      setMsg("画面已切成 " + created.length + " 张", "ok");
    } catch (e) {
      setMsg("切分失败：" + ((e && e.message) || e), "bad");
    }
  }
  function storyAdvanceFromShot(shot, seconds, dir) {
    shot = shot || selectedShot();
    if (!shot) { setMsg("先点一个分镜", "warn"); return; }
    dir = dir || "next";
    const goingBack = dir === "back";
    const beat = goingBack
      ? ("上一镜，时间往回 " + seconds + " 秒。同一角色同一场，拍这一动作开始之前的那一拍，空间和光线连续，不要跳切。")
      : ("下一镜，时间往后 " + seconds + " 秒。同一角色同一场，拍这一动作的下一拍，空间和光线连续，不要跳切。");
    const node = spawnLinkedShot(shot, {
      titleSuffix: goingBack ? (" · -" + seconds + "s") : (" · +" + seconds + "s"),
      prompt: ((shot.prompt || "").trim() + "\n" + beat).trim(),
      mode: "image",
      firstFrameFromSource: !!shot.url,
    });
    renderCards(); drawWires();
    if (node) panTo(node);
    setMsg((goingBack ? "往前 " : "往后 ") + seconds + " 秒已出分镜 · 正在生成", "ok");
    if (node) generateShotQueue([node], "故事推演");
  }
  function generateShotQueue(nodes, label) {
    if (!nodes || !nodes.length) return;
    if (state._genQueueBusy) {
      state._genQueue = (state._genQueue || []).concat(nodes.map(function (n) { return n; }));
      return;
    }
    state._genQueueBusy = true;
    (async function () {
      const list = nodes.slice();
      for (let i = 0; i < list.length; i++) {
        const n = list[i];
        if (!n || !n.id) continue;
        setMsg((label || "生成") + " " + (i + 1) + "/" + list.length + " · " + (n.title || ""), "ok");
        try {
          selectNode(n.id, { expand: true, preserveLayout: true });
          const refs = (typeof connectedAssets === "function") ? connectedAssets(n.id) : [];
          let op = "t2i";
          if (n.wantUpscale) op = "upscale";
          else if (n.wantInpaint) op = "inpaint";
          else if (n.mode === "video") op = (n.url || n.firstFrameId || refs.length) ? "i2v" : "t2v";
          else if (n.url || refs.length) {
            const sid = String(n.serviceId || (n.composer && n.composer.service) || "").toLowerCase();
            op = /editimage|createvariant|image-to-image/.test(sid) ? "i2i" : "t2i";
          }
          const keepHouse = !!(n.serviceId || (n.composer && n.composer.service) || n.backend);
          if (keepHouse) {
            smartMatchService._gen = (smartMatchService._gen || 0) + 1;
            if (n.backend && $("backend")) $("backend").value = n.backend;
            const sid0 = n.serviceId || (n.composer && n.composer.service) || "";
            let sid = sid0;
            if (refs.length && (n.backend === "civitai" || /^image\//.test(sid)) && !/editimage|createvariant/i.test(sid)) {
              sid = "image/comfy/krea2/edit/editImage";
              op = "i2i";
            } else if (sid === "image/textToImage") {
              sid = CIVITAI_PREF_SERVICE;
            }
            if (sid && $("service")) {
              ensureSelectOpt($("service"), sid);
              $("service").value = sid;
              n.serviceId = sid;
              if (n.composer) n.composer.service = sid;
            }
            if (n.composer && Array.isArray(n.composer.loras)) {
              state.loras = JSON.parse(JSON.stringify(n.composer.loras));
            }
          } else {
            await rematchAfterSpawn(n, op);
          }
          await runShotUntilDone(n.id, (label || "") + " " + (i + 1) + "/" + list.length);
        } catch (e) {
          setMsg((n.title || "分镜") + " 失败：" + ((e && e.message) || e), "bad");
        }
      }
      state._genQueueBusy = false;
      const extra = state._genQueue || [];
      state._genQueue = [];
      if (extra.length) generateShotQueue(extra, label);
    })();
  }
  function beginCrop(shot) {
    shot = shot || selectedShot();
    if (!shot || !shot.url) { setMsg("先有成片再局部摘取", "warn"); return; }
    state._cropShotId = shot.id;
    renderCards();
    setMsg("在成片上拖出要摘的区域", "ok");
  }
  async function finishCropRect(shot, nx, ny, nw, nh) {
    try {
      const img = await loadImageEl(shot.url);
      const sx = Math.max(0, Math.floor(nx * img.naturalWidth));
      const sy = Math.max(0, Math.floor(ny * img.naturalHeight));
      const sw = Math.max(8, Math.floor(nw * img.naturalWidth));
      const sh = Math.max(8, Math.floor(nh * img.naturalHeight));
      const canvas = document.createElement("canvas");
      canvas.width = sw;
      canvas.height = sh;
      canvas.getContext("2d").drawImage(img, sx, sy, sw, sh, 0, 0, sw, sh);
      const url = await uploadDataUrl(canvas.toDataURL("image/jpeg", 0.92), (shot.title || "shot") + "-crop.jpg");
      const id = uid("shot");
      const node = {
        id: id, kind: "shot", title: (shot.title || "分镜") + " · 摘取",
        x: shot.x + box(shot).w + 36, y: shot.y,
        url: url, prompt: shot.prompt || "", negativePrompt: shot.negativePrompt || "", mode: "image",
      };
      state.nodes.push(node);
      state.edges.push({ from: shot.id, to: id });
      renderCards(); drawWires(); persist(); persistServer();
      selectNode(id, { preserveLayout: true });
      setMsg("局部摘取已成新节点", "ok");
    } catch (e) {
      setMsg("摘取失败：" + ((e && e.message) || e), "bad");
    }
  }
  function panoFromShot(shot) {
    shot = shot || selectedShot();
    if (!shot) { setMsg("先点一个分镜", "warn"); return; }
    const prompt = ((shot.prompt || "").trim() + "\nwide establishing shot, panoramic environment, full surroundings visible, 720 look").trim();
    const node = spawnLinkedShot(shot, {
      titleSuffix: " · 全景",
      prompt: prompt,
      mode: "image",
      firstFrameFromSource: !!shot.url,
    });
    rematchAfterSpawn(node, shot.url ? "i2i" : "t2i");
    if (node) generateShotQueue([node], "全景");
  }
  function hideToolPops() {
    ["lightPop", "camPop", "lastPop", "storyPop", "morePop", "ninePop", "splitPop"].forEach(function (id) {
      const el = document.getElementById(id);
      if (!el) return;
      el.hidden = true;
      el.style.display = "none";
    });
  }
  function toolAnchor(preferred) {
    if (preferred && preferred.getBoundingClientRect) {
      const r = preferred.getBoundingClientRect();
      if (r.width > 4 && r.height > 4) return preferred;
    }
    const id = preferred && preferred.id;
    const fromBar = id && document.querySelector('#shotBar [data-shot-tool="' + id + '"]');
    if (fromBar) {
      const r = fromBar.getBoundingClientRect();
      if (r.width > 4 && r.height > 4) return fromBar;
    }
    return document.querySelector("#shotBar button")
      || document.querySelector(".card.shot.sel")
      || document.querySelector(".card.shot")
      || preferred;
  }
  function placePop(pop, anchor) {
    if (!pop) return;
    const a = toolAnchor(anchor);
    pop.style.position = "fixed";
    pop.style.zIndex = "50";
    pop.style.display = "";
    pop.hidden = false;
    const r = a ? a.getBoundingClientRect() : { left: 80, right: 80, top: 80, bottom: 120, width: 40 };
    let left = r.left;
    let top = r.bottom + 8;
    pop.style.left = Math.round(left) + "px";
    pop.style.top = Math.round(top) + "px";
    const pr = pop.getBoundingClientRect();
    if (left + pr.width > window.innerWidth - 8) left = Math.max(8, window.innerWidth - pr.width - 8);
    if (top + pr.height > window.innerHeight - 8) top = Math.max(8, r.top - pr.height - 8);
    if (left < 8) left = 8;
    if (top < 8) top = 8;
    pop.style.left = Math.round(left) + "px";
    pop.style.top = Math.round(top) + "px";
  }
  function showMorePop(anchor) {
    hideToolPops();
    let pop = $("morePop");
    if (!pop) {
      pop = document.createElement("div");
      pop.id = "morePop";
      pop.className = "story-pop";
      pop.innerHTML = [
        ["btnNine", "九宫"],
        ["btnStory", "推演"],
        ["btnLight", "打光"],
        ["btnCamera", "机位"],
        ["btnUpscale", "超清"],
        ["btnErase", "消除"],
        ["btnT2v", "视频"],
        ["btnLast", "尾帧"],
        ["btnPano", "全景"],
      ].map(function (it) {
        return '<button type="button" data-more="' + it[0] + '">' + it[1] + "</button>";
      }).join("");
      document.body.appendChild(pop);
      pop.addEventListener("click", function (ev) {
        const b = ev.target.closest("[data-more]");
        if (!b) return;
        pop.hidden = true;
        const id = b.getAttribute("data-more");
        const barBtn = document.querySelector('#shotBar [data-shot-tool="' + id + '"]')
          || document.querySelector('#shotBar [data-shot-act="more"]');
        runShotTool(id, barBtn);
      });
    }
    placePop(pop, anchor);
  }
  function spawnLinkedShot(source, opts) {
    opts = opts || {};
    if (!source) return null;
    const id = uid("shot");
    const node = {
      id: id,
      kind: "shot",
      title: (source.title || "分镜") + (opts.titleSuffix || ""),
      x: source.x + box(source).w + 48,
      y: source.y + (opts.yOff || 0),
      url: "",
      prompt: opts.prompt != null ? opts.prompt : (source.prompt || ""),
      negativePrompt: source.negativePrompt || "",
      mode: opts.mode || "image",
      backend: source.backend || (source.composer && source.composer.backend) || "",
      serviceId: source.serviceId || (source.composer && source.composer.service) || "",
    };
    if (source.composer) {
      try { node.composer = JSON.parse(JSON.stringify(source.composer)); } catch (_) { node.composer = source.composer; }
    }
    if (Array.isArray(source.loras)) {
      try { node.loras = JSON.parse(JSON.stringify(source.loras)); } catch (_) {}
    }
    if (opts.firstFrameFromSource && source.url && (opts.mode || "image") === "video") node.firstFrameId = source.id;
    if (opts.wantT2v) node.wantT2v = true;
    if (opts.wantUpscale) node.wantUpscale = true;
    if (opts.wantInpaint) node.wantInpaint = true;
    if (opts.maskUrl) node.maskUrl = opts.maskUrl;
    if (opts.lastFrameId) node.lastFrameId = opts.lastFrameId;
    state.nodes.push(node);
    state.edges.push({ from: source.id, to: id });
    if (opts.maskAssetId) state.edges.push({ from: opts.maskAssetId, to: id });
    ensureWorkspaceModel();
    const scene = sceneById(source.sceneId) || (state.script && state.script.scenes[0]);
    if (scene) assignShotToScene(id, scene.id);
    state.mode = node.mode;
    if (!opts.skipSelect) selectNode(id, { expand: true, preserveLayout: true });
    if (!opts.skipPan) panTo(node);
    persist(); persistServer();
    return node;
  }
  async function rematchAfterSpawn(shot, op) {
    if (!shot) return;
    try {
      if (typeof loadCatalog === "function") await loadCatalog();
    } catch (_) {}
    try { await smartMatchService({ announce: true }); } catch (_) {}
    const sid = ($("service") && $("service").value) || shot.serviceId || "";
    const it = catalogItemForService();
    if (op && it && !serviceFitsOp(it, op)) {
      setMsg("当前目录没有可匹配的" + (graphOpLabel(op) || op) + "端点（不装接）", "warn");
    } else if (sid) {
      setMsg("已匹配" + (graphOpLabel(op) || "") + (sid ? (" · " + sid) : ""), "ok");
    }
  }
  function showLightPop(anchor) {
    const shot = selectedShot();
    if (!shot || !shot.url) { setMsg("先有成片再打光", "warn"); return; }
    hideToolPops();
    let pop = $("lightPop");
    if (!pop) {
      pop = document.createElement("div");
      pop.id = "lightPop";
      pop.className = "light-pop";
      pop.innerHTML = LIGHT_PRESETS.map(function (p) {
        return '<button type="button" data-light="' + p.id + '"><img src="/static/light-preset-' + p.id + '.jpg" alt=""><span>' + esc(p.title) + "</span></button>";
      }).join("");
      document.body.appendChild(pop);
      pop.addEventListener("click", function (ev) {
        const b = ev.target.closest("[data-light]");
        if (!b) return;
        pop.hidden = true;
        lightFromShot(selectedShot(), b.getAttribute("data-light"));
      });
    }
    placePop(pop, anchor || document.querySelector('#shotBar [data-shot-tool="btnLight"]') || $("btnLight"));
  }
  function lightFromShot(shot, presetId) {
    shot = shot || selectedShot();
    const p = LIGHT_PRESETS.find(function (x) { return x.id === presetId; });
    if (!shot || !p) return;
    const prompt = ((shot.prompt || "").trim() + "\n打光：" + p.title + "。 " + p.prompt).trim();
    const node = spawnLinkedShot(shot, {
      titleSuffix: " · " + p.title,
      prompt: prompt,
      mode: "image",
      firstFrameFromSource: true,
    });
    rematchAfterSpawn(node, "i2i");
    if (node) generateShotQueue([node], "打光");
  }
  function showCamPop(anchor) {
    const shot = selectedShot();
    if (!shot || !shot.url) { setMsg("先有成片再换机位", "warn"); return; }
    hideToolPops();
    let pop = $("camPop");
    if (!pop) {
      pop = document.createElement("div");
      pop.id = "camPop";
      pop.className = "cam-pop";
      pop.innerHTML = CAMERA_PRESETS.map(function (p) {
        return '<button type="button" data-cam="' + p.id + '">' + esc(p.title) + "</button>";
      }).join("");
      document.body.appendChild(pop);
      pop.addEventListener("click", function (ev) {
        const b = ev.target.closest("[data-cam]");
        if (!b) return;
        pop.hidden = true;
        cameraFromShot(selectedShot(), b.getAttribute("data-cam"));
      });
    }
    placePop(pop, anchor || document.querySelector('#shotBar [data-shot-tool="btnCamera"]') || $("btnCamera"));
  }
  function cameraFromShot(shot, presetId) {
    shot = shot || selectedShot();
    const p = CAMERA_PRESETS.find(function (x) { return x.id === presetId; });
    if (!shot || !p) return;
    const prompt = ((shot.prompt || "").trim() + "\n机位：" + p.title + "。 " + p.prompt).trim();
    const node = spawnLinkedShot(shot, {
      titleSuffix: " · " + p.title,
      prompt: prompt,
      mode: "image",
      firstFrameFromSource: true,
    });
    rematchAfterSpawn(node, "i2i");
    if (node) generateShotQueue([node], "机位");
  }
  function upscaleFromShot(shot) {
    shot = shot || selectedShot();
    if (!shot || !shot.url) { setMsg("先有成片再超清", "warn"); return; }
    const node = spawnLinkedShot(shot, {
      titleSuffix: " · 超清",
      prompt: ((shot.prompt || "").trim() + "\nupscale, keep identity and composition, no restyle").trim(),
      mode: "image",
      firstFrameFromSource: true,
      wantUpscale: true,
    });
    rematchAfterSpawn(node, "upscale");
    if (node) generateShotQueue([node], "超清");
  }
  function t2vFromShot(shot) {
    shot = shot || selectedShot();
    if (!shot) { setMsg("先点一个分镜", "warn"); return; }
    if (!shot.url) {
      shot.mode = "video";
      state.mode = "video";
      selectNode(shot.id, { expand: true, preserveLayout: true });
      rematchAfterSpawn(shot, "t2v");
      generateShotQueue([shot], "合成视频");
      return;
    }
    const node = spawnLinkedShot(shot, {
      titleSuffix: " · 视频",
      prompt: shot.prompt || "",
      mode: "video",
      firstFrameFromSource: true,
    });
    rematchAfterSpawn(node, "i2v");
    if (node) generateShotQueue([node], "合成视频");
  }
  function showLastPop(anchor) {
    const shot = selectedShot();
    if (!shot) { setMsg("先点一个分镜", "warn"); return; }
    hideToolPops();
    const imgs = state.nodes.filter(function (n) {
      return n && n.id !== shot.id && isImageSource(n);
    });
    let pop = $("lastPop");
    if (!pop) {
      pop = document.createElement("div");
      pop.id = "lastPop";
      pop.className = "last-pop";
      document.body.appendChild(pop);
      pop.addEventListener("click", function (ev) {
        const up = ev.target.closest("[data-last-up]");
        if (up) {
          pop.hidden = true;
          state._uploadLastFrame = true;
          if ($("file")) $("file").click();
          return;
        }
        const b = ev.target.closest("[data-last]");
        if (!b) return;
        pop.hidden = true;
        const src = nodeById(b.getAttribute("data-last"));
        const live = selectedShot();
        if (!src || !live) return;
        live.lastFrameId = src.id;
        live.wantT2v = false;
        if (!state.edges.some(function (e) { return e.from === src.id && e.to === live.id; })) {
          state.edges.push({ from: src.id, to: live.id });
        }
        state.mode = "video";
        live.mode = "video";
        selectNode(live.id, { expand: true, preserveLayout: true });
        persist(); persistServer();
        rematchAfterSpawn(live, "i2v");
        setMsg("尾帧已挂上 · 确认后点 ↑", "ok");
      });
    }
    pop.innerHTML = '<button type="button" data-last-up="1">上传尾帧</button>' +
      (imgs.length
        ? imgs.map(function (n) {
            return '<button type="button" data-last="' + esc(n.id) + '">' + esc(sourceTitle(n) || n.title || n.id) + "</button>";
          }).join("")
        : '<button type="button" disabled>画布上还没有别的成片</button>');
    placePop(pop, anchor || document.querySelector('#shotBar [data-shot-tool="btnLast"]') || $("btnLast"));
  }
  function showStoryPop(anchor) {
    if (!selectedShot()) { setMsg("先点一个分镜", "warn"); return; }
    let pop = $("storyPop");
    if (!pop) {
      pop = document.createElement("div");
      pop.id = "storyPop";
      pop.className = "story-pop";
      pop.hidden = true;
      pop.innerHTML = '<button type="button" data-story="3" data-dir="next">往后 3 秒</button>' +
        '<button type="button" data-story="5" data-dir="next">往后 5 秒</button>' +
        '<button type="button" data-story="3" data-dir="back">往前 3 秒</button>' +
        '<button type="button" data-story="5" data-dir="back">往前 5 秒</button>';
      document.body.appendChild(pop);
      pop.addEventListener("click", function (ev) {
        const b = ev.target.closest("[data-story]");
        if (!b) return;
        pop.hidden = true;
        storyAdvanceFromShot(selectedShot(), Number(b.dataset.story) || 3, b.getAttribute("data-dir") || "next");
      });
    }
    if (!pop.hidden) { pop.hidden = true; return; }
    hideToolPops();
    placePop(pop, anchor || document.querySelector('#shotBar [data-shot-tool="btnStory"]') || $("btnStory"));
  }
  function runShotTool(id, anchor) {
    if (id === "btnPano") panoFromShot(selectedShot());
    else if (id === "btnCamera") showCamPop(anchor);
    else if (id === "btnNine") showNinePop(anchor);
    else if (id === "btnSplit") showSplitPop(anchor);
    else if (id === "btnLight") showLightPop(anchor);
    else if (id === "btnStory") showStoryPop(anchor);
    else if (id === "btnErase") beginErase(selectedShot());
    else if (id === "btnUpscale") upscaleFromShot(selectedShot());
    else if (id === "btnT2v") t2vFromShot(selectedShot());
    else if (id === "btnLast") showLastPop(anchor);
    else {
      const el = $(id);
      if (el) el.click();
    }
  }
  function beginErase(shot) {
    shot = shot || selectedShot();
    if (!shot || !shot.url) { setMsg("先有成片再消除", "warn"); return; }
    state._eraseShotId = shot.id;
    state._cropShotId = "";
    renderCards();
    const card = document.querySelector('.card.shot[data-id="' + shot.id + '"]');
    const face = card && card.querySelector(".face");
    if (!face) return;
    let cv = face.querySelector("canvas.erase-cv");
    if (!cv) {
      cv = document.createElement("canvas");
      cv.className = "erase-cv";
      face.appendChild(cv);
    }
    const r = face.getBoundingClientRect();
    cv.width = Math.max(8, Math.floor(r.width));
    cv.height = Math.max(8, Math.floor(r.height));
    const ctx = cv.getContext("2d");
    ctx.fillStyle = "#000";
    ctx.fillRect(0, 0, cv.width, cv.height);
    ctx.strokeStyle = "#fff";
    ctx.lineWidth = 22;
    ctx.lineCap = "round";
    ctx.lineJoin = "round";
    state._eraseCv = cv;
    setMsg("在成片上涂要消除的区域，松手后出遮罩并生成", "ok");
  }
  async function finishErase(shot, cv) {
    state._eraseShotId = "";
    state._eraseCv = null;
    if (!shot || !cv) { renderCards(); return; }
    try {
      const img = await loadImageEl(shot.url);
      const full = document.createElement("canvas");
      full.width = Math.max(8, img.naturalWidth || cv.width);
      full.height = Math.max(8, img.naturalHeight || cv.height);
      full.getContext("2d").drawImage(cv, 0, 0, full.width, full.height);
      const url = await uploadDataUrl(full.toDataURL("image/png"), (shot.title || "shot") + "-mask.png");
      const aid = uid("asset");
      const asset = { id: aid, kind: "character", title: (shot.title || "分镜") + " 遮罩", x: shot.x - 160, y: shot.y, url: url };
      state.nodes.push(asset);
      const node = spawnLinkedShot(shot, {
        titleSuffix: " · 消除",
        prompt: ((shot.prompt || "").trim() + "\nremove the painted object, fill with coherent background, keep identity").trim(),
        mode: "image",
        firstFrameFromSource: true,
        wantInpaint: true,
        maskUrl: url,
        maskAssetId: aid,
      });
      rematchAfterSpawn(node, "inpaint");
      if (node) generateShotQueue([node], "消除");
    } catch (e) {
      renderCards();
      setMsg("消除遮罩失败：" + ((e && e.message) || e), "bad");
    }
  }
  if ($("btnDownload")) $("btnDownload").onclick = function () { downloadShot(selectedShot()); };
  if ($("btnEditNode")) $("btnEditNode").onclick = function () { editSelectedShot(); };
  if ($("btnCrop")) $("btnCrop").onclick = function () { beginCrop(selectedShot()); };
  if ($("btnNine")) $("btnNine").onclick = function (e) { e.stopPropagation(); showNinePop(e.currentTarget); };
  if ($("btnSplit")) $("btnSplit").onclick = function (e) { e.stopPropagation(); showSplitPop(e.currentTarget); };
  if ($("btnStory")) {
    $("btnStory").onclick = function (e) {
      e.stopPropagation();
      showStoryPop(e.currentTarget);
    };
  }
  if ($("btnPano")) $("btnPano").onclick = function () { panoFromShot(selectedShot()); };
  if ($("shotBar")) {
    $("shotBar").addEventListener("click", function (e) {
      const tool = e.target.closest("[data-shot-tool]");
      if (tool) {
        e.preventDefault();
        e.stopPropagation();
        runShotTool(tool.getAttribute("data-shot-tool"), tool);
        return;
      }
      const act = e.target.closest("[data-shot-act]");
      if (!act) return;
      e.preventDefault();
      e.stopPropagation();
      const shot = selectedShot();
      if (!shot) return;
      const kind = act.getAttribute("data-shot-act");
      if (kind === "download") downloadShot(shot);
      else if (kind === "edit") { state.selected = shot.id; editSelectedShot(); }
      else if (kind === "crop") beginCrop(shot);
      else if (kind === "more") showMorePop(act);
    });
  }
  if ($("btnLight")) $("btnLight").onclick = function (e) { e.stopPropagation(); showLightPop(e.currentTarget); };
  if ($("btnCamera")) $("btnCamera").onclick = function (e) { e.stopPropagation(); showCamPop(e.currentTarget); };
  if ($("btnUpscale")) $("btnUpscale").onclick = function () { upscaleFromShot(selectedShot()); };
  if ($("btnErase")) $("btnErase").onclick = function () { beginErase(selectedShot()); };
  if ($("btnT2v")) $("btnT2v").onclick = function () { t2vFromShot(selectedShot()); };
  if ($("btnLast")) $("btnLast").onclick = function (e) { e.stopPropagation(); showLastPop(e.currentTarget); };
  document.addEventListener("click", function (e) {
    if (e.target.closest("#lightPop,#camPop,#lastPop,#storyPop,#morePop,#ninePop,#splitPop,#btnLight,#btnCamera,#btnLast,#btnStory,#btnNine,#btnSplit,[data-node-act],#shotBar")) return;
    hideToolPops();
  });
  world.addEventListener("click", function (e) {
    const act = e.target.closest("[data-node-act]");
    if (!act) return;
    e.preventDefault();
    e.stopPropagation();
    const shot = nodeById(act.getAttribute("data-id"));
    if (!shot) return;
    const kind = act.getAttribute("data-node-act");
    if (kind === "download") downloadShot(shot);
    else if (kind === "edit") { state.selected = shot.id; editSelectedShot(); }
    else if (kind === "crop") beginCrop(shot);
    else if (kind === "more") {
      const pop = $("morePop");
      if (pop && !pop.hidden) { hideToolPops(); return; }
      showMorePop(act);
    }
  });
  vp.addEventListener("pointerdown", function (e) {
    if (state._eraseShotId) {
      const card = e.target.closest(".card.shot");
      if (!card || card.dataset.id !== state._eraseShotId) return;
      const cv = state._eraseCv || (card.querySelector && card.querySelector("canvas.erase-cv"));
      if (!cv) return;
      e.stopPropagation();
      const r = cv.getBoundingClientRect();
      const ctx = cv.getContext("2d");
      const x = (e.clientX - r.left) * (cv.width / Math.max(1, r.width));
      const y = (e.clientY - r.top) * (cv.height / Math.max(1, r.height));
      state._erasePaint = true;
      ctx.beginPath();
      ctx.moveTo(x, y);
      ctx.lineTo(x + 0.1, y + 0.1);
      ctx.stroke();
      return;
    }
    if (!state._cropShotId) return;
    const card = e.target.closest(".card.shot");
    if (!card || card.dataset.id !== state._cropShotId) return;
    const face = card.querySelector(".face");
    if (!face) return;
    e.stopPropagation();
    const r = face.getBoundingClientRect();
    state._cropDrag = {
      id: state._cropShotId,
      x0: (e.clientX - r.left) / r.width,
      y0: (e.clientY - r.top) / r.height,
    };
  }, true);
  vp.addEventListener("pointermove", function (e) {
    if (state._erasePaint && state._eraseCv) {
      const cv = state._eraseCv;
      const r = cv.getBoundingClientRect();
      const ctx = cv.getContext("2d");
      const x = (e.clientX - r.left) * (cv.width / Math.max(1, r.width));
      const y = (e.clientY - r.top) * (cv.height / Math.max(1, r.height));
      ctx.lineTo(x, y);
      ctx.stroke();
      ctx.beginPath();
      ctx.moveTo(x, y);
      return;
    }
    if (!state._cropDrag) return;
    const drag = state._cropDrag;
    const card = document.querySelector('.card.shot[data-id="' + drag.id + '"]');
    const face = card && card.querySelector(".face");
    if (!face) return;
    const r = face.getBoundingClientRect();
    const x1 = (e.clientX - r.left) / r.width;
    const y1 = (e.clientY - r.top) / r.height;
    const nx = Math.max(0, Math.min(drag.x0, x1));
    const ny = Math.max(0, Math.min(drag.y0, y1));
    const nw = Math.abs(x1 - drag.x0);
    const nh = Math.abs(y1 - drag.y0);
    let boxEl = face.querySelector(".crop-rect");
    if (!boxEl) {
      boxEl = document.createElement("div");
      boxEl.className = "crop-rect";
      face.appendChild(boxEl);
    }
    boxEl.style.left = (nx * 100) + "%";
    boxEl.style.top = (ny * 100) + "%";
    boxEl.style.width = (nw * 100) + "%";
    boxEl.style.height = (nh * 100) + "%";
  }, true);
  vp.addEventListener("pointerup", function (e) {
    if (state._erasePaint) {
      state._erasePaint = false;
      const shot = nodeById(state._eraseShotId);
      const cv = state._eraseCv;
      finishErase(shot, cv);
      return;
    }
    if (!state._cropDrag) return;
    const drag = state._cropDrag;
    state._cropDrag = null;
    const shot = nodeById(drag.id);
    state._cropShotId = "";
    const card = document.querySelector('.card.shot[data-id="' + drag.id + '"]');
    const face = card && card.querySelector(".face");
    renderCards();
    if (!shot || !face) return;
    const r = face.getBoundingClientRect();
    const x1 = (e.clientX - r.left) / r.width;
    const y1 = (e.clientY - r.top) / r.height;
    const nx = Math.max(0, Math.min(drag.x0, x1));
    const ny = Math.max(0, Math.min(drag.y0, y1));
    const nw = Math.abs(x1 - drag.x0);
    const nh = Math.abs(y1 - drag.y0);
    if (nw < 0.05 || nh < 0.05) {
      setMsg("框太小，再拖一次", "warn");
      return;
    }
    finishCropRect(shot, nx, ny, nw, nh);
  }, true);
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
            : n && n.kind === "text"
              ? connectedNodes(n.id).find(isImageSource)
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
  $("btnFit").onclick = () => { fitShotsInView(); };
  $("zIn").onclick = () => { setZoomScale(state.cam.s * 1.12); };
  $("zOut").onclick = () => { setZoomScale(state.cam.s * 0.9); };
  // v0821o136-seko: 抓手/框选 tool toggle on the centered bottom bar.
  function setCanvasTool(tool) {
    state.canvasTool = tool === "select" ? "select" : "pan";
    if ($("zPan")) $("zPan").classList.toggle("on", state.canvasTool === "pan");
    if ($("zSelect")) $("zSelect").classList.toggle("on", state.canvasTool === "select");
    vp.classList.toggle("select-mode", state.canvasTool === "select");
    setMsg(state.canvasTool === "select" ? "框选模式 · 在空白处拖出选区多选节点" : "抓手模式 · 拖动空白处平移画布", "");
  }
  if ($("zPan")) $("zPan").onclick = () => setCanvasTool("pan");
  if ($("zSelect")) $("zSelect").onclick = () => setCanvasTool("select");
  if ($("zPresets")) {
    $("zPresets").addEventListener("click", (e) => {
      const btn = e.target.closest("button[data-z]");
      if (!btn) return;
      if (btn.dataset.z === "fit") fitCam();
      else setZoomScale(Number(btn.dataset.z));
    });
  }
  if ($("btnImport")) $("btnImport").onclick = () => openImportModal();


  // v0821o23: keep imported civitai serviceId honest on page↑ (live job 12100372 sent krea2 with sdxl dm).
  function isCivitaiKrea2TurboService(sid) {
    const s = String(sid || "").trim();
    return s === CIVITAI_PREF_SERVICE || s === "image/comfy/krea2/turbo/createImage";
  }
  function civitaiServiceIdFromImportShot(shot) {
    if (!shot) return "";
    const pinned = String(shot.serviceId || "").trim();
    if (pinned) return pinned;
    const eco = String(shot.ecosystem || "").trim();
    const ecoL = eco.toLowerCase();
    const dm = String(shot.diffusionModel || "").trim().toLowerCase();
    const blob = (ecoL + " " + dm).trim();
    // Mirror providers/civitai.py ~1395 — never invent krea2 for sdxl/pony/illustrious.
    if (ecoL === "sdxl" || /:sdxl:/.test(dm) || /\b(pony|illustrious|ilxl)\b/.test(blob)) {
      return "image/sdcpp/sdxl/createImage";
    }
    if (ecoL === "flux" || /:flux/.test(dm)) return "image/sdcpp/flux1/createImage";
    if (ecoL === "wan" || /:wan/.test(dm)) return "image/sdcpp/wan/createImage";
    if (ecoL === "zimage" || eco === "zImage" || /:zimage/.test(dm)) return "image/sdcpp/zImage/turbo/createImage";
    if (ecoL === "qwen" || /:qwen/.test(dm)) return "image/sdcpp/qwen/20b/createImage";
    return "";
  }
  function resolveCivitaiOutboundServiceId(shot) {
    const ui = ($("service") && $("service").value) || "";
    const fromShot = civitaiServiceIdFromImportShot(shot);
    if (fromShot) {
      // Imported sdxl must not silently ship krea2/turbo.
      if (!ui || (isCivitaiKrea2TurboService(ui) && fromShot !== ui)) return fromShot;
    }
    return ui || fromShot || "";
  }
  function syncCivitaiServiceSelect(sid) {
    const s = String(sid || "").trim();
    if (!s || !$("service")) return;
    ensureSelectOpt($("service"), s);
    if (!state.catalogById) state.catalogById = {};
    if (!state.catalogById[s]) state.catalogById[s] = { id: s, name: s };
    $("service").value = s;
  }

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
  function hfHasLoras() {
    return Array.isArray(state.loras) && state.loras.length > 0;
  }
  function hfLoraBasesFromChips() {
    return falLoraBasesFromChips();
  }
  function hfLoraEndpointLabel(ep) {
    // o33: Fal /lora under HF is not an HF score path — label as Fal sibling / 请换家.
    if (ep === FAL_FLUX_LORA_SERVICE) return "Flux LoRA · " + ep + " · 请换家 Fal（不计 HF 分）";
    if (ep === FAL_LORA_PREF_SERVICE) return "Krea 2 Turbo LoRA · " + ep + " · 请换家 Fal（不计 HF 分）";
    return ep;
  }
  /** @returns {{endpoint:string, reason:string, falSibling?:string, scoresAsHf?:boolean}} */
  function resolveHfLoraEndpointFromChips() {
    if (!hfHasLoras()) return { endpoint: "", reason: "", scoresAsHf: true };
    const bases = hfLoraBasesFromChips();
    if (!bases.length) {
      return {
        endpoint: "",
        reason: "LoRA 无 AIR base · 无法匹配 HF Hub 路径（不硬钉 Krea-2-Turbo；Civitai LoRA 请换家 Fal）",
        scoresAsHf: false
      };
    }
    if (bases.length > 1) {
      return {
        endpoint: "",
        reason: "多 LoRA base 不一致（" + bases.join("/") + "）· HF 不支持；请换家 Fal",
        scoresAsHf: false
      };
    }
    const base = bases[0];
    const ep = HF_LORA_BY_BASE[base];
    if (!ep) {
      return {
        endpoint: "",
        reason: "LoRA base=" + base + " 无 HF Hub LoRA 路径 · " + HF_ROUTER_FAL_LORA_MSG,
        scoresAsHf: false
      };
    }
    // v0821o33: Fal /lora sibling exists but HF Router does not host it — NOT HF closed-loop.
    // Keep chips; do not pin fal-ai/*lora as HF outbound. User must 换家 Fal (or Hub mid without Civitai LoRA).
    return {
      endpoint: "",
      reason: HF_ROUTER_FAL_LORA_MSG,
      falSibling: ep,
      scoresAsHf: false
    };
  }
  function hfLoraUnsupportedMsg() {
    const r = resolveHfLoraEndpointFromChips();
    return r.reason || "";
  }
  function isHfNoLoraHubDrift(sid) {
    // Hub mids that map to fal-ai/*/turbo or flux/dev without loras[] — never keep when chips present.
    const s = String(sid || "").trim();
    if (!s) return true;
    if (s === HF_LORA_PREF_SERVICE) return true;
    if (looksHfServiceId(s)) return true;
    return false;
  }
  function pinHfLoraServiceId(sid, op) {
    const s = String(sid || "").trim();
    const wantI2v = op === "i2v" || (op == null && typeof currentGraphOp === "function" && currentGraphOp() === "i2v");
    if (wantI2v) {
      if (!s || s === HF_LORA_PREF_SERVICE || looksFalServiceId(s) || looksCivitaiServiceId(s)) {
        return (typeof pickSmartServiceId === "function" && pickSmartServiceId("i2v")) || "Wan-AI/Wan2.2-TI2V-5B";
      }
      return s;
    }
    const wantI2i = op === "i2i" || (op == null && typeof currentGraphOp === "function" && currentGraphOp() === "i2i");
    // No LoRAs: foreign Fal/Civitai → Hub pref for this op (t2i turbo / i2i Qwen-Edit).
    // Never rewrite Hub → fal-ai/.../lora. Turbo is the t2i pref; rewrite only that to i2i pref.
    if (!hfHasLoras()) {
      const pref = wantI2i ? HF_I2I_PREF_SERVICE : HF_LORA_PREF_SERVICE;
      if (!s || looksFalServiceId(s) || looksCivitaiServiceId(s)) return pref;
      if (wantI2i && s === HF_LORA_PREF_SERVICE) return HF_I2I_PREF_SERVICE;
      return s;
    }
    const resolved = resolveHfLoraEndpointFromChips();
    state._hfLoraUnsupported = resolved.reason || "";
    if (resolved.reason) {
      // Honest 不支持 — never hard-pin Hub turbo / wrong family.
      return "";
    }
    const want = resolved.endpoint;
    // Empty / Civitai / Hub no-LoRA / Fal t2i drift / wrong Fal family → official LoRA endpoint for AIR base.
    if (!s || looksCivitaiServiceId(s) || isHfNoLoraHubDrift(s) || isFalFluxLoraDrift(s)) return want;
    if (looksFalServiceId(s) && s !== want) return want;
    if (s !== want) return want;
    return want;
  }
  function ensureHfLoraServiceSelected() {
    const be = ($("backend") && $("backend").value) || "";
    if (be !== "huggingface") return;
    const sel = $("service");
    if (!sel) return;
    if (!hfHasLoras()) {
      const want = pinHfLoraServiceId(sel.value || state._pinHfLoraService || "", currentGraphOp());
      ensureSelectOpt(sel, want);
      for (let i = 0; i < sel.options.length; i++) {
        if (sel.options[i].value === want) {
          const t = sel.options[i].textContent || "";
          if (want === HF_LORA_PREF_SERVICE && (!t || t === want || t === "默认模型" || t.indexOf(want) < 0)) {
            sel.options[i].textContent = "Krea 2 Turbo · " + want;
          }
          break;
        }
      }
      sel.value = want;
      if (state.catalogById && state.catalogById[want]) return;
      return;
    }
    const resolved = resolveHfLoraEndpointFromChips();
    state._hfLoraUnsupported = resolved.reason || "";
    if (resolved.reason) {
      try { setMsg(resolved.reason, "bad"); } catch (_) {}
      try { setParamWarn(resolved.reason, true); } catch (_) {}
      state._pinHfLoraService = "";
      // Keep chips — never delete LoRA on unsupported base.
      return;
    }
    const want = pinHfLoraServiceId(sel.value) || resolved.endpoint;
    if (!want) return;
    ensureSelectOpt(sel, want);
    for (let i = 0; i < sel.options.length; i++) {
      if (sel.options[i].value === want) {
        const t = sel.options[i].textContent || "";
        if (!t || t === want || t === "默认模型" || t.indexOf("Flux LoRA") === 0 || t.indexOf("Krea 2 Turbo LoRA") === 0) {
          sel.options[i].textContent = hfLoraEndpointLabel(want);
        }
        break;
      }
    }
    sel.value = want;
    state._pinHfLoraService = want;
    state._pendingService = want;
    if (state.catalogById && state.catalogById[want]) return;
  }
  function hfLoraFixtureImport() {
    return {
      backend: "huggingface",
      // v0821o136seko-hffix: 修正历史笔误——HF fixture 必须钉 HF 自家 pref，不是 Fal id
      serviceId: HF_LORA_PREF_SERVICE,
      serviceName: "Krea 2 Turbo LoRA",
      kind: "image",
      prompt: "portrait, soft light, detailed face, cinematic",
      loras: [{
        versionId: 3231694,
        air: "urn:air:krea2:lora:civitai:fixture@3231694",
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
    state._pinHfLoraService = HF_LORA_PREF_SERVICE;
    const ok = await applyImport(hfLoraFixtureImport());
    ensureHfLoraServiceSelected();
    return ok;
  }

  function pinMsLoraServiceId(sid, op) {
    op = op || (typeof currentGraphOp === "function" ? currentGraphOp() : "t2i");
    const s = String(sid || "").trim();
    if (op === "i2i" || op === "i2v") {
      if (!s || s === MS_LORA_PREF_SERVICE || (typeof looksFalServiceId === "function" && looksFalServiceId(s)) || (typeof looksCivitaiServiceId === "function" && looksCivitaiServiceId(s))) {
        return (typeof pickSmartServiceId === "function" && pickSmartServiceId(op)) || "";
      }
      return s;
    }
    if (s && !looksFalServiceId(s) && !looksCivitaiServiceId(s)) return s;
    return MS_LORA_PREF_SERVICE;
  }
  function msLoraOptionLabel(want, currentText) {
    const id = String(want || "").trim();
    const t = String(currentText || "");
    if (id !== MS_LORA_PREF_SERVICE) return t || id;
    if (!t || t === id || t === "默认模型" || t.indexOf(id) < 0) return "Krea 2 Turbo · " + id;
    return t;
  }
  function ensureMsLoraServiceSelected() {
    const be = ($("backend") && $("backend").value) || "";
    if (be !== "modelscope-ai" && be !== "modelscope-cn") return;
    const sel = $("service");
    if (!sel) return;
    const want = pinMsLoraServiceId(sel.value || state._pinMsLoraService || "", typeof currentGraphOp === "function" ? currentGraphOp() : "t2i");
    if (want) ensureSelectOpt(sel, want);
    for (let i = 0; i < sel.options.length; i++) {
      if (sel.options[i].value === want) {
        sel.options[i].textContent = msLoraOptionLabel(want, sel.options[i].textContent || "");
        break;
      }
    }
    sel.value = want;
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

  // v0821o29: Fal+LoRA endpoint from AIR base — flux1→flux-lora; krea2→krea-2/turbo/lora; else honest 不支持.
  function falHasLoras() {
    return Array.isArray(state.loras) && state.loras.length > 0;
  }
  function loraAirBase(l) {
    const air = String((l && (l.air || l.AIR || "")) || "").trim();
    const m = air.match(/^urn:air:([^:]+):lora:/i);
    return m ? String(m[1] || "").toLowerCase() : "";
  }
  function falLoraBasesFromChips() {
    const list = Array.isArray(state.loras) ? state.loras : [];
    const bases = [];
    list.forEach(function (l) {
      const b = loraAirBase(l);
      if (b && bases.indexOf(b) < 0) bases.push(b);
    });
    return bases;
  }
  function falLoraEndpointLabel(ep) {
    if (ep === FAL_FLUX_LORA_SERVICE) return "Flux LoRA · " + ep;
    if (ep === FAL_LORA_PREF_SERVICE) return "Krea 2 Turbo LoRA · " + ep;
    return ep;
  }
  /** @returns {{endpoint:string, reason:string}} */
  function resolveFalLoraEndpointFromChips() {
    if (!falHasLoras()) return { endpoint: "", reason: "" };
    const bases = falLoraBasesFromChips();
    if (!bases.length) {
      return {
        endpoint: "",
        reason: "LoRA 无 AIR base · 无法匹配官方 Fal 端点（不硬钉 krea-2）"
      };
    }
    if (bases.length > 1) {
      return {
        endpoint: "",
        reason: "多 LoRA base 不一致（" + bases.join("/") + "）· 不支持一锅端到 krea-2"
      };
    }
    const base = bases[0];
    const ep = FAL_LORA_BY_BASE[base];
    if (!ep) {
      return {
        endpoint: "",
        reason: "LoRA base=" + base + " 无官方 Fal LoRA 端点 · 不支持（不硬钉错误家族）"
      };
    }
    return { endpoint: ep, reason: "" };
  }
  function falLoraUnsupportedMsg() {
    const r = resolveFalLoraEndpointFromChips();
    return r.reason || "";
  }
  function isFalFluxLoraDrift(sid) {
    // Legacy name kept for tests: bare t2i / empty defaults that are NOT a LoRA family match.
    const s = String(sid || "").trim();
    return s === "fal-ai/flux/schnell" || s === FAL_T2I_DEFAULT || s === "fal-ai/flux/dev";
  }
  function pinFalLoraServiceId(sid) {
    const s = String(sid || "").trim();
    // No LoRAs: only rewrite foreign civitai/HF ids to Fal t2i default.
    if (!falHasLoras()) {
      if (looksCivitaiServiceId(s) || looksHfServiceId(s)) return FAL_T2I_DEFAULT;
      return s;
    }
    const resolved = resolveFalLoraEndpointFromChips();
    state._falLoraUnsupported = resolved.reason || "";
    if (resolved.reason) {
      // Honest 不支持 — never hard-pin krea-2 / flux-lora wrong family.
      return "";
    }
    const want = resolved.endpoint;
    // Foreign / empty / t2i drift → official LoRA family for this AIR base.
    if (!s || looksCivitaiServiceId(s) || looksHfServiceId(s) || isFalFluxLoraDrift(s)) return want;
    // Same-family turbo sibling → /lora
    if (want === FAL_LORA_PREF_SERVICE && (s === "fal-ai/krea-2/turbo" || s === "fal-ai/z-image/turbo" || s === "fal-ai/z-image/turbo/lora")) {
      return want;
    }
    if (want === FAL_FLUX_LORA_SERVICE && (s === FAL_FLUX_LORA_SERVICE || s.indexOf("flux-lora") >= 0)) {
      return FAL_FLUX_LORA_SERVICE;
    }
    // Wrong family selected (e.g. krea while chips are flux1) → correct endpoint.
    if (s !== want) return want;
    return want;
  }
  function ensureFalLoraServiceSelected() {
    if (state._importFamily === "sdxl" || state._importFamily === "pony" || state._importFamily === "sd15") return;
    if (!falHasLoras()) return;
    const be = ($("backend") && $("backend").value) || "";
    if (be !== "fal") return;
    const sel = $("service");
    if (!sel) return;
    // o53c: capacity rematch lock / already capacity-ok → do not re-pin flux-lora
    const lock = state._capacityRematchLock;
    if (lock && sel.value === lock) {
      state._pinFalLoraService = lock;
      return;
    }
    const shotOk = nodeById(state.selected);
    if (shotOk && shotOk.kind === "shot") {
      const nOk = countRefUrls(null, shotOk).length;
      const itOk = (state.catalogById && state.catalogById[sel.value]) || catalogItemForService();
      const resOk = resolveRefCaps(itOk);
      if (nOk && resOk.known && nOk <= resOk.maxRefs && catalogEatsRefs(itOk)) {
        state._pinFalLoraService = sel.value;
        return;
      }
    }
    const resolved = resolveFalLoraEndpointFromChips();
    state._falLoraUnsupported = resolved.reason || "";
    if (resolved.reason) {
      try { setMsg(resolved.reason, "bad"); } catch (_) {}
      try { setParamWarn(resolved.reason, true); } catch (_) {}
      state._pinFalLoraService = "";
      return;
    }
    const want = pinFalLoraServiceId(sel.value) || resolved.endpoint;
    if (!want) return;
    ensureSelectOpt(sel, want);
    for (let i = 0; i < sel.options.length; i++) {
      if (sel.options[i].value === want) {
        const t = sel.options[i].textContent || "";
        if (!t || t === want || t === "默认模型" || t.indexOf("Krea 2 Turbo LoRA") === 0 || t.indexOf("Flux LoRA") === 0) {
          sel.options[i].textContent = falLoraEndpointLabel(want);
        }
        break;
      }
    }
    sel.value = want;
    state._pinFalLoraService = want;
    state._pendingService = want;
    const shotPin = nodeById(state.selected);
    if (shotPin && shotPin.kind === "shot") shotPin.serviceId = want;
    // o53b: after LoRA pin, if over-cap rematch (same backend); else keep links + hard gate
    try {
      if (typeof tryCapacityRematchAfterServiceChange === "function" && tryCapacityRematchAfterServiceChange()) {
        /* rematched */
      } else if (shotPin && shotPin.kind === "shot") {
        const n = countRefUrls(null, shotPin).length;
        const it = catalogItemForService();
        const resolved = resolveRefCaps(it);
        if (resolved.known && n > resolved.maxRefs) {
          setMsg("参考图 " + n + "/" + resolved.maxRefs + " · pin 模型容量不足，保留连线（不静默丢线）", "bad");
        }
      }
    } catch (_) {}
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
    state._pinFalLoraService = FAL_LORA_PREF_SERVICE;
    const ok = await applyImport(falLoraFixtureImport());
    ensureFalLoraServiceSelected();
    return ok;
  }
  function ensureActiveShotForImport() {
    let shot = nodeById(state.selected);
    if (shot && shot.kind === "shot") return shot;
    shot = nodeById(state.lastComposerShot);
    if (shot && shot.kind === "shot") {
      selectNode(shot.id, { expand: true, preserveLayout: true });
      return shot;
    }
    const list = shots();
    if (list.length) {
      selectNode(list[0].id, { expand: true });
      return nodeById(list[0].id);
    }
    const id = uid("shot");
    const pos = newShotPosition(shots().length);
    state.mode = "image";
    const n = {
      id: id, kind: "shot", title: "分镜1",
      x: pos.x, y: pos.y, url: "", firstFrameId: "",
      prompt: "", mode: "image",
    };
    state.nodes.push(n);
    selectNode(id, { expand: true });
    return n;
  }
  function familyMatchImport(house, j) {
    const be = String(house || "").trim();
    const op = (j && j.kind === "video") ? "i2v" : "t2i";
    let fam = "";
    if (typeof SmartFamilyMatch !== "undefined") {
      fam = SmartFamilyMatch.familyFromImport(j) || "";
    }
    let sid = "";
    if (typeof SmartFamilyMatch !== "undefined" && be) {
      sid = SmartFamilyMatch.preferredId(be, fam, op) || "";
    }
    return { backend: be, op: op, family: fam, serviceId: sid };
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
    const wantMsPost = j.backend === "modelscope-ai" || j.backend === "modelscope-cn"
      || msBe === "modelscope" || msBe === "ms" || msBe === "魔搭" || msBe === "魔搭ai" || msBe === "魔搭cn";
    // Explicit backend wins; Magao Hub ids must not steal HF; HF must not fall through to Fal.
    let wantMs = wantMsPost;
    let wantHf = !wantMs && ((j.backend === "huggingface" || j.backend === "hf")
      || (hfSid && j.backend !== "fal" && j.backend !== "civitai"));
    let wantCivitai = !wantMs && !wantHf && ((j.backend === "civitai") || (civitaiSid && j.backend !== "fal"));
    let wantFal = !wantMs && !wantHf && ((j.backend === "fal") || (falSid && j.backend !== "civitai" && !wantCivitai));
    const shot = ensureActiveShotForImport();
    const uiHouse = String(($("backend") && $("backend").value) || (shot && (shot.backend || (shot.composer && shot.composer.backend))) || "").trim();
    const postFromCivitai = !!(wantCivitai || civitaiSid);
    let wantNano = j.backend === "nano-gpt";
    let famInfo = familyMatchImport(uiHouse || "civitai", j);
    state._importFamily = famInfo.family || "";
    // Stay on the house the user already picked. A Civitai 帖 is a recipe, not a house switch.
    if (uiHouse && uiHouse !== "civitai" && postFromCivitai) {
      j = Object.assign({}, j, { backend: uiHouse, serviceId: famInfo.serviceId || "", serviceName: famInfo.serviceId || j.serviceName });
      lockHouse(uiHouse);
      wantCivitai = false;
      wantFal = uiHouse === "fal";
      wantHf = uiHouse === "huggingface";
      wantMs = uiHouse === "modelscope-ai" || uiHouse === "modelscope-cn";
      wantNano = uiHouse === "nano-gpt";
      if (wantMs) {
        j.backend = uiHouse;
      }
    } else if (uiHouse === "civitai" && postFromCivitai && famInfo.serviceId) {
      j = Object.assign({}, j, { serviceId: famInfo.serviceId });
    }
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
        // v0821o23: persist imported serviceId on shot — #service alone is lost on catalog reload / reselect.
        if (shot && !hardErr) shot.serviceId = sid;
      }
    } else if (wantFal) {
      if ($("backend")) $("backend").value = "fal";
      syncParamSurface();
      let sid = String(j.serviceId || "").trim();
      // v0821o135: 认不出帖子底模家族时不许套 krea-2 写死默认；清空模型框，警告在导入收尾统一报。
      const falFamilyUnknown = !sid && !state._importFamily;
      // Pin fal-ai/z-image/turbo(/lora) — never drift to Civitai image/comfy/…
      if (looksCivitaiServiceId(sid)) {
        hardErr = "Fal 导入拒绝 Civitai serviceId " + sid;
        sid = "";
      } else if (falFamilyUnknown || state._importFamily === "sdxl" || state._importFamily === "pony" || state._importFamily === "sd15") {
        sid = "";
        state._pinFalLoraService = "";
        state._pendingService = "";
        try { await loadCatalog(); } catch (_) {}
        if ($("service")) $("service").value = "";
      } else {
        // v0821o29: if import carries LoRAs, prefer AIR-base endpoint (fixture krea stays krea).
        if (Array.isArray(j.loras) && j.loras.length) {
          // Temporarily mirror chips onto state for base resolve (applyImport sets chips later too).
          const prev = state.loras;
          state.loras = j.loras;
          const resolved = resolveFalLoraEndpointFromChips();
          state.loras = prev;
          if (resolved.reason) {
            hardErr = resolved.reason;
            sid = "";
            state._pinFalLoraService = "";
          } else if (resolved.endpoint) {
            if (!sid || isFalFluxLoraDrift(sid) || looksCivitaiServiceId(sid) || looksHfServiceId(sid)
                || sid === "fal-ai/krea-2/turbo" || sid === "fal-ai/z-image/turbo") {
              sid = resolved.endpoint;
            }
            // Wrong family vs AIR base → correct (never keep krea for flux1).
            if (sid !== resolved.endpoint) sid = resolved.endpoint;
          }
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
      let sid = String(j.serviceId || "").trim();
      // v0821o135: 认不出帖子底模家族时不许套 Krea-2 写死默认；sid 留空，收尾统一清空模型框+警告。
      if (state._importFamily === "sdxl" || state._importFamily === "pony" || state._importFamily === "sd15") sid = "";
      // v0821o31: allow official Fal LoRA endpoints (flux-lora / krea-2/turbo/lora) when import carries loras[].
      // Still reject Civitai image/… and bare no-LoRA fal-ai/*/turbo (Router must not silent-swap sibling).
      const importHasLoras = Array.isArray(j.loras) && j.loras.length > 0;
      const falLoraOk = looksFalServiceId(sid) && importHasLoras && (
        sid === FAL_FLUX_LORA_SERVICE || sid === FAL_LORA_PREF_SERVICE || /\/lora\b/i.test(sid) || sid.indexOf("flux-lora") >= 0
      );
      if (looksCivitaiServiceId(sid) || (looksFalServiceId(sid) && !falLoraOk)) {
        hardErr = "Hugging Face 导入拒绝 Fal/Civitai 无 LoRA serviceId " + sid + "（有 LoRA 时请用 fal-ai/flux-lora 等）";
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
      const msHouse = (uiHouse === "modelscope-cn" || uiHouse === "modelscope-ai")
        ? uiHouse
        : ((msBe === "modelscope-cn" || msBe === "魔搭cn") ? "modelscope-cn" : "modelscope-ai");
      if ($("backend")) $("backend").value = msHouse;
      syncParamSurface();
      let sid = String(j.serviceId || "").trim();
      // v0821o135: 认不出帖子底模家族时不许套 Krea-2 写死默认；sid 留空，收尾统一清空模型框+警告。
      if (state._importFamily === "sdxl" || state._importFamily === "pony" || state._importFamily === "sd15") sid = "";
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
    } else if (wantNano) {
      if ($("backend")) $("backend").value = "nano-gpt";
      syncParamSurface();
      let sid = String(j.serviceId || "").trim();
      if (looksCivitaiServiceId(sid) || looksFalServiceId(sid)) sid = "";
      if (!sid) sid = famInfo.serviceId || "";
      state._pendingService = sid;
      if (!await loadCatalog() || importToken !== _importToken) return false;
      if (sid) {
        ensureSelectOpt($("service"), sid);
        if ($("service")) $("service").value = sid;
        if (!state.catalogById) state.catalogById = {};
        if (!state.catalogById[sid]) state.catalogById[sid] = { id: sid, name: sid };
        if (shot) shot.serviceId = sid;
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
      // v0821o22: any hinablue/civitai import — keep checkpoint AIR on shot for outbound (never invent).
      // v0821o38: do NOT delete dm/cn/eco when j omits the key — only assign when present (prevent wipe races).
      if (j.diffusionModel != null && String(j.diffusionModel).trim()) {
        shot.diffusionModel = String(j.diffusionModel).trim();
      }
      if (j.checkpointName != null && String(j.checkpointName).trim()) {
        shot.checkpointName = String(j.checkpointName).trim();
      }
      if (j.ecosystem != null && String(j.ecosystem).trim()) {
        shot.ecosystem = String(j.ecosystem).trim();
      }
      // v0821o23: keep import serviceId even if #service later drifts to catalog pref (krea2).
      if (j.serviceId != null && String(j.serviceId).trim()) {
        shot.serviceId = String(j.serviceId).trim();
      }
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
      // v0821o36: drop non-LoRA AIRs (esp. equals j.diffusionModel); never invent strength
      const dmAir = (j.diffusionModel != null) ? String(j.diffusionModel).trim() : "";
      let droppedCkpt = 0;
      state.loras = j.loras.map(function (row) {
        const n = normalizeLora(row || {});
        if (row && row.air) n.air = String(row.air).trim();
        // AIR @version wins over wrong sibling versionId/path from import JSON.
        const vid = loraVersionId({
          air: n.air,
          versionId: row && row.versionId,
          modelVersionId: row && row.modelVersionId,
        }) || loraVersionId(n);
        if (vid) {
          n.versionId = String(vid);
          const reconciled = loraDownloadUrl(n);
          if (reconciled) {
            n.path = reconciled;
            n.downloadUrl = reconciled;
          }
        }
        return n;
      }).filter(function (n) {
        if (shouldDropNonLoraAir(n && n.air, dmAir)) {
          droppedCkpt++;
          return false;
        }
        return true;
      });
      if (droppedCkpt > 0) {
        try {
          setMsg("导入已丢弃 " + droppedCkpt + " 个非 LoRA AIR（checkpoint 只留 diffusionModel）", "warn");
        } catch (_) {}
      }
    } else {
      state.loras = [];
    }
    syncLoraUi();
    // o54b: imported LoRA chips on !supportsLora model → rematch (roster fetch OK)
    try {
      const famSkip = state._importFamily === "sdxl" || state._importFamily === "pony" || state._importFamily === "sd15";
      if (!famSkip && Array.isArray(state.loras) && state.loras.length && !catalogItemSupportsLora()) {
        applyLoraCapabilityRematch();
      }
    } catch (_) {}

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
    const liveHouse = ($("backend") && $("backend").value) || uiHouse || "";
    const labels = { t2i: "文生图", i2i: "图生图", i2v: "图生视频" };
    const famNow = famInfo.family || state._importFamily || "";
    const opNow = famInfo.op || "t2i";
    let matched = ($("service") && $("service").value) || "";
    if (typeof SmartFamilyMatch !== "undefined" && liveHouse) {
      if (!famNow) {
        // v0821o135: 认不出帖子底模家族。没挂上模型就清空模型框+明说，绝不播"已智能匹配"。
        if (!matched) {
          if ($("service")) $("service").value = "";
          if (shot) {
            shot.serviceId = "";
            shot.backend = liveHouse;
            if (!shot.composer) shot.composer = {};
            shot.composer.service = "";
            shot.composer.backend = liveHouse;
          }
          setMsg("认不出帖子底模家族，请手动选模型", "warn");
          return true;
        }
        // 已显式挂上模型但没认出家族：留着模型，只报导入，不冒充智能匹配。
        setMsg("已导入参数" + (nLora ? (" · " + nLora + " 个 LoRA") : " · 未识别 LoRA") + extraTxt + "，自己点生成。", heightAligned ? "warn" : "ok");
        return true;
      }
      // v0821o135: 智能匹配用活目录——已加载目录池里按家族+op 搜（pickByFamily），写死表 HOUSE_FAMILY_PREF 仅兜底。
      const poolObj = (typeof rematchCandidatePool === "function") ? rematchCandidatePool() : (state.catalogById || {});
      const poolArr = Array.isArray(poolObj) ? poolObj : Object.keys(poolObj).map(function (k) { return poolObj[k]; });
      let wantFam = (typeof SmartFamilyMatch.pickByFamily === "function") ? (SmartFamilyMatch.pickByFamily({
        backend: liveHouse, op: opNow, family: famNow, pool: poolArr,
        fits: serviceFitsOp, belongs: serviceBelongsToBackend
      }) || "") : "";
      if (!wantFam) wantFam = SmartFamilyMatch.preferredId(liveHouse, famNow, opNow) || "";
      if (wantFam) {
        ensureSelectOpt($("service"), wantFam);
        if ($("service")) $("service").value = wantFam;
        matched = wantFam;
        if (shot) {
          shot.serviceId = wantFam;
          shot.backend = liveHouse;
          if (!shot.composer) shot.composer = {};
          shot.composer.service = wantFam;
          shot.composer.backend = liveHouse;
        }
        setMsg("已智能匹配" + (labels[opNow] || opNow) + " · " + famNow + " · " + wantFam + extraTxt, heightAligned ? "warn" : "ok");
        return true;
      }
      if ($("service")) $("service").value = "";
      if (shot) {
        shot.serviceId = "";
        shot.backend = liveHouse;
        if (!shot.composer) shot.composer = {};
        shot.composer.service = "";
        shot.composer.backend = liveHouse;
      }
      setMsg("这家没有可匹配的" + (labels[opNow] || opNow) + "模型（" + famNow + "），请换模型或换家", "warn");
      return true;
    }
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
      // o53d: keep full official roster for capacity rematch (filter may drop flux-2/edit from UI list)
      state._catalogRoster = roster.slice();
      state._catalogRosterBackend = be;
      // v0821: mode-filter so video Composer lists i2v services (not silent t2i flux).
      items = filterCatalogForMode(items);
      // v0821o52: import _pendingService must survive i2i filter (t2i krea2 onto shot that still has refs).
      // Re-inject from official roster only — never invent a synthetic model row.
      if (state._pendingService) {
        const want = String(state._pendingService || "").trim();
        if (want && !items.some(function (it) { return (it.id || it.name) === want; })) {
          const raw = roster.find(function (it) { return (it.id || it.name) === want; });
          if (raw) items = [raw].concat(items);
        }
      }
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
      const falResolvedPin = (be === "fal" && falHasLoras()) ? resolveFalLoraEndpointFromChips() : null;
      const needLoraPin = (be === "fal" && state.mode !== "video" && (
        falHasLoras() || pinWant === FAL_LORA_PREF_SERVICE || pinWant === FAL_FLUX_LORA_SERVICE || pinWant === "fal-ai/krea-2/turbo"
      ));
      if (needLoraPin) {
        const pinId = (falResolvedPin && falResolvedPin.endpoint)
          || state._pinFalLoraService
          || pinWant
          || FAL_LORA_PREF_SERVICE;
        if (pinId) {
          const pinItem = items.find(function (it) { return (it.id || it.name) === pinId; });
          if (pinItem) {
            items = [pinItem].concat(items.filter(function (it) { return (it.id || it.name) !== pinId; }));
          }
        }
      }
      const hfPref = selectedShotWantsI2i() ? HF_I2I_PREF_SERVICE : HF_LORA_PREF_SERVICE;
      const hfResolvedPin = (be === "huggingface" && hfHasLoras()) ? resolveHfLoraEndpointFromChips() : null;
      const needHfPin = (be === "huggingface" && mode !== "video" && (
        (Array.isArray(state.loras) && state.loras.length)
        || pinWant === HF_LORA_PREF_SERVICE
        || pinWant === HF_I2I_PREF_SERVICE
        || pinWant === FAL_FLUX_LORA_SERVICE
        || pinWant === FAL_LORA_PREF_SERVICE
        || state._pinHfLoraService
      ));
      if (needHfPin) {
        // o33: with LoRA chips, do NOT inject fal-ai/*lora into HF catalog as if it scored HF.
        // Surface honest 请换家 Fal via ensureHfLoraServiceSelected / gates; Hub mid only when no chips.
        const pinId = (hfResolvedPin && hfResolvedPin.endpoint)
          || state._pinHfLoraService
          || (hfHasLoras() ? "" : hfPref);
        if (pinId && !(hfHasLoras() && looksFalServiceId(pinId))) {
          const pinItem = items.find(function (it) { return (it.id || it.name) === pinId; });
          if (pinItem) {
            items = [pinItem].concat(items.filter(function (it) { return (it.id || it.name) !== pinId; }));
          }
        }
        if (hfHasLoras() && hfResolvedPin && hfResolvedPin.reason) {
          try { setMsg(hfResolvedPin.reason, "bad"); } catch (_) {}
          try { setParamWarn(hfResolvedPin.reason, true); } catch (_) {}
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
      if (be === "fal") ensureFalLoraServiceSelected();
      if (be === "huggingface") ensureHfLoraServiceSelected();
      if (be === "modelscope-ai" || be === "modelscope-cn") ensureMsLoraServiceSelected();
      // Do NOT auto-select CIVITAI_PREF when empty — empty stays empty until user/import picks.
      applyServiceConstraints();
      try { await smartMatchService({ announce: true }); } catch (_) {}
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
        if (it.bytes === 0) return false;
        const k = it.kind || mediaKindOf(u);
        if (!(k === "image" || k === "video")) return false;
        return !isJunkRailItem({ url: u, title: it.file || it.name, bytes: it.bytes });
      });
      state.history = items.slice(0, 24).map((it) => ({
        url: it.url || it.path,
        title: String(it.file || it.name || "历史成片").replace(/\.[^.]+$/, ""),
        kind: it.kind || mediaKindOf(it.url || it.path || ""),
      })).filter((it) => it.url && !isJunkRailItem(it));
      renderRail();
    } catch (_) {}
  }
  $("backend").onchange = function () {
    delete state._pendingService;
    if ($("serviceFilter")) $("serviceFilter").value = "";
    const be = ($("backend") && $("backend").value) || "";
    lockHouse(be);
    const shot = (typeof composerShot === "function" ? composerShot() : null) || nodeById(state.selected);
    if (shot && shot.kind === "shot") {
      shot.backend = be;
      if (!shot.composer) shot.composer = snapshotComposer();
      shot.composer.backend = be;
      const sid = String((shot.composer && shot.composer.service) || shot.serviceId || "").trim();
      if (sid && typeof serviceBelongsToBackend === "function" && !serviceBelongsToBackend(sid, be)) {
        shot.serviceId = "";
        shot.composer.service = "";
        if ($("service")) $("service").value = "";
      }
    }
    // v0821o26: drop foreign #service when 换家 so catalog keep= does not re-select civitai/HF id on Fal.
    if ($("service")) {
      const cur = String($("service").value || "").trim();
      if (be === "fal" && (looksCivitaiServiceId(cur) || looksHfServiceId(cur))) $("service").value = "";
      if (be === "civitai" && (looksFalServiceId(cur) || looksHfServiceId(cur))) $("service").value = "";
      if (be === "huggingface" && (looksFalServiceId(cur) || looksCivitaiServiceId(cur))) $("service").value = "";
      if ((be === "modelscope-ai" || be === "modelscope-cn") && (looksFalServiceId(cur) || looksCivitaiServiceId(cur))) $("service").value = "";
    }
    if (be === "fal" && falHasLoras()) {
      const resolved = resolveFalLoraEndpointFromChips();
      state._falLoraUnsupported = resolved.reason || "";
      state._pendingService = resolved.endpoint || "";
      state._pinFalLoraService = resolved.endpoint || "";
      if (resolved.reason) {
        try { setMsg(resolved.reason, "bad"); } catch (_) {}
      }
    }
    if (be === "huggingface" && hfHasLoras()) {
      const resolved = resolveHfLoraEndpointFromChips();
      state._hfLoraUnsupported = resolved.reason || "";
      state._pendingService = resolved.endpoint || "";
      state._pinHfLoraService = resolved.endpoint || "";
      if (resolved.reason) {
        try { setMsg(resolved.reason, "bad"); } catch (_) {}
      }
    }
    syncParamSurface();
    const p = loadCatalog();
    // B1: 目录异步就绪后再跑一次 applyServiceConstraints(syncParamChrome)，不要求用户再点节点。
    loadCatalog().then(function () { applyServiceConstraints(); });
    Promise.resolve(p).then(async function () {
      if (be === "fal") ensureFalLoraServiceSelected();
      else if (be === "huggingface") ensureHfLoraServiceSelected();
      else if (be === "modelscope-ai" || be === "modelscope-cn") ensureMsLoraServiceSelected();
      try { await smartMatchService({ announce: true }); } catch (_) {}
      syncLoraUi();
    }).catch(function () { syncLoraUi(); });
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
      // stage3 fix: deliberate user model change must pin the selected shot,
      // otherwise resolveCivitaiOutboundServiceId() silently overrides the
      // pick with the shot's previously pinned serviceId (model never changes).
      const n = nodeById(state.selected);
      if (n && n.kind === "shot") {
        n.serviceId = String($("service").value || "");
        try { persist(); } catch (_) {}
      }
      applyServiceConstraints();
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
  // v0821o26: rebuild #backend from /api/providers — every registered provider, honest labels.
  // Never filter to hasKey-only (铁律: 禁止隐藏 API 已支持能力 / 禁止单家盯梢).
  function syncBackendOptionsFromProviders(items) {
    const sel = $("backend");
    if (!sel || !Array.isArray(items) || !items.length) return;
    const keep = String(sel.value || "").trim();
    const seen = {};
    const rows = [];
    items.forEach(function (it) {
      if (!it || !it.id || seen[it.id]) return;
      seen[it.id] = true;
      rows.push({ id: String(it.id), label: String(it.label || it.id) });
    });
    if (!rows.length) return;
    sel.innerHTML = "";
    rows.forEach(function (row) {
      const o = document.createElement("option");
      o.value = row.id;
      o.textContent = row.label;
      sel.appendChild(o);
    });
    if (keep && seen[keep]) sel.value = keep;
    honorHouseLock();
    if (!sel.value && rows[0]) sel.value = rows[0].id;
  }
  async function loadProviderCaps() {
    try {
      const r = await fetch("/api/providers");
      const j = await r.json();
      const map = {};
      const items = j.items || [];
      items.forEach(function (it) {
        if (it && it.id) map[it.id] = it.capabilities || {};
      });
      state._providerCaps = map;
      syncBackendOptionsFromProviders(items);
    } catch (_) {}
    try {
      const r = await fetch("/api/capabilities");
      const j = await r.json();
      state._capabilities = Array.isArray(j.capabilities) ? j.capabilities : [];
    } catch (_) {
      state._capabilities = state._capabilities || [];
    }
    applyServiceConstraints();
  }

  window.addEventListener("resize", () => { drawMinimap(); positionDock(); });

  if (!restore()) loadDemo();
  separateOverlappingShots();
  ensureWorkspaceModel();
  // v0821o15: server graph is shared-studio source of writeback when localStorage empty (clean profile).
  hydrateFromServer().then(function (changed) {
    if (_canvasAdopted) return resumePendingJobs();
    try {
      if (changed) {
        separateOverlappingShots();
        ensureWorkspaceModel();
        applyCam();
        renderCards();
        drawWires();
        renderRail();
        renderWorkspace();
      }
      const firstShot = (state.nodes || []).find(function (n) { return n && n.kind === "shot"; });
      const pick = state.selected || (firstShot && firstShot.id);
      if (pick) selectNode(pick, { collapsed: true });
      if (typeof renderDock === "function") renderDock();
      requestAnimationFrame(function () {
        if (typeof positionDock === "function") positionDock();
        if (typeof fitShotsInView === "function") fitShotsInView();
        if (typeof positionDock === "function") positionDock();
      });
    } catch (e) { try { console.warn("hydrate ui", e); } catch (_) {} }
    // v0821o46: always try resume pending jobs after hydrate (tab death / OOM mid-poll)
    return resumePendingJobs();
  }).catch(function () {});
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
  syncParamChrome();
  loadProviderCaps().then(function () { return loadComfyDefaults(); }).then(function () { return loadCatalog(); }).then(function () {
    if (_wantFalLoraFixture) return mountFalLoraFixture();
    if (_wantHfLoraFixture) return mountHfLoraFixture();
    if (_wantMsLoraFixture) return mountMsLoraFixture();
  }).then(function () {
    // Imports select after their own catalog completion; no late boot re-pinning.
  });
  loadOuts();
  selectNode(state.selected || "shot-1", { collapsed: true });
  requestAnimationFrame(function () {
    if (typeof positionDock === "function") positionDock();
    if (typeof fitShotsInView === "function") fitShotsInView();
    if (typeof positionDock === "function") positionDock();
  });
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
        const empties = document.querySelectorAll("#refs .ref-slot-empty");
        return {
          n: countRefUrls(null, n).length,
          displayN: n ? displayRefUrls(n).length : 0,
          cap: maxRefCount(catalogItemForService()),
          msg: refCapGateMessage(n),
          unused: refUnusedGateMessage(n),
          hint: hint ? String(hint.textContent || "") : "",
          emptySlots: empties ? empties.length : 0,
          siblingId: editSiblingId(catalogItemForService()),
          eatsRefs: catalogEatsRefs(catalogItemForService()),
          sendReason: $("send") ? $("send").getAttribute("data-reason") : "",
        };
      },
      fillRefsToCap: function () {
        const n = nodeById(state.selected);
        const added = fillRefSlotsToCap(n);
        renderCards(); drawWires(); renderDock();
        return {
          added: added,
          n: countRefUrls(null, n).length,
          displayN: displayRefUrls(n).length,
          cap: maxRefCount(catalogItemForService()),
        };
      },
      applyEditSibling: applyEditSibling,
      attachExtraImages: function (payload) {
        const n = nodeById(state.selected);
        return attachExtraImages(payload || {}, n);
      },
      selectShot: function (id) {
        selectNode(id, { expand: true, shift: true });
        const shot = nodeById(id);
        if (shot && shot.composer && $("backend")) {
          $("backend").value = shot.composer.backend || $("backend").value;
          if (shot.composer.mode && (shot.composer.mode === "image" || shot.composer.mode === "video")) {
            state.mode = shot.composer.mode;
          }
        }
        state._pendingService = (shot && ((shot.composer && shot.composer.service) || shot.serviceId)) || "";
        return loadCatalog();
      },
      attachQaRef: function (url) {
        const shot = nodeById(state.selected);
        if (!shot || shot.kind !== "shot") return false;
        let asset = nodeById("qa-ref");
        if (!asset) {
          asset = { id: "qa-ref", kind: "character", title: "qa-ref", x: 40, y: 40, url: url || "/out/house-civitai.jpg" };
          state.nodes.push(asset);
        }
        linkAssetToShot(asset, shot);
        return smartMatchService({ announce: true });
      },
      clearQaRef: function () {
        const shot = nodeById(state.selected);
        const asset = nodeById("qa-ref");
        if (shot && asset) unlinkAssetFromShot(asset, shot);
        return smartMatchService({ announce: true });
      },
      setMode: function (mode) {
        return setMode(mode);
      },
      smartMatch: function () {
        return smartMatchService({ announce: true });
      },
    };
  }
  window.__sekoDeleteNode = deleteNode;
})();
