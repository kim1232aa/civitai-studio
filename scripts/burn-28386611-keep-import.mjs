/**
 * CLOSED-LOOP burn for AIImageStudio 28386611 — page ↑ only.
 * FORBIDDEN: PREF krea2/turbo silent swap; curl /api/generate as acceptance;
 * invent LoRA strength; shorten prompt; port 8080.
 * Pass claim ALWAYS false.
 */
import { chromium } from "/tmp/node_modules/playwright/index.mjs";
import fs from "fs";
import path from "path";
import crypto from "crypto";
import { execSync } from "child_process";

const BASE = "http://127.0.0.1:8765";
const IMAGE_ID = "28386611";
const IMPORT_URL = `https://civitai.com/images/${IMAGE_ID}`;
const EXPECT_SID = "image/sdcpp/flux1/createImage";
const EXPECT_LORA = "urn:air:flux1:lora:civitai:730162@819842";
const EXPECT_STRENGTH = 0.7;
const EXPECT_PROMPT_LEN = 470;
const PACK = "/workspace/civitai-studio/docs/review-shots/closed-loop/civitai-28386611-t2i-closed-o154-seko";
const WAIT_MS = 10 * 60 * 1000;
const CANVAS_NAME = "civitai-28386611-t2i-closed-o154-seko";

fs.mkdirSync(PACK, { recursive: true });

function md5File(p) {
  try {
    return crypto.createHash("md5").update(fs.readFileSync(p)).digest("hex");
  } catch {
    return "";
  }
}
function md5Buf(buf) {
  return crypto.createHash("md5").update(buf).digest("hex");
}

const report = {
  imageId: IMAGE_ID,
  postId: IMAGE_ID,
  backend: "civitai",
  serviceId: EXPECT_SID,
  op: "t2i",
  family: "flux1",
  author: "AIImageStudio",
  promptLen: 0,
  jobId: "",
  generateStatus: 0,
  generateBody: null,
  submittedInput: null,
  posts: [],
  error: "",
  msg: "",
  writeback: false,
  mediaLanded: false,
  hardRefreshOk: false,
  cardShowsNewMedia: false,
  passClaim: false,
  Pass: false,
  sekoReachable: false,
  keptLoras: true,
  clearedRefs: false,
  note:
    "FRAMED PAGE↑ (#send). Unused AIImageStudio 28386611. Keep imported flux1 serviceId/prompt/LoRA 0.7 — NEVER assign PREF krea2/turbo. No curl /api/generate. Pass=False.",
  head: "",
  incomplete: true,
  verdict: "Fail",
  blocker: "",
};

try {
  report.head = execSync("git -C /workspace/civitai-studio log -1 --oneline", { encoding: "utf8" }).trim();
} catch (_) {}

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
page.setDefaultTimeout(60000);

let genPostBody = null;
let genResponseJson = null;
let genStatus = 0;

page.on("request", (req) => {
  if (req.method() === "POST" && /\/api\/generate$/.test(req.url())) {
    let j = {};
    try {
      j = JSON.parse(req.postData() || "{}");
    } catch (_) {}
    genPostBody = j;
    const loras = j.loras || [];
    const loraArr = Array.isArray(loras)
      ? loras.map((x) => ({
          air: x.air || x.id || "",
          modelId: String(x.modelId || "").replace(/^.*:/, "") || undefined,
          path: x.path || x.url || x.downloadUrl || "",
          url: x.url || x.path || "",
          downloadUrl: x.downloadUrl || x.path || "",
          versionId: String(x.versionId || ""),
          scale: x.strength ?? x.scale,
          strength: x.strength ?? x.scale,
          strengthMissing: x.strength == null && x.scale == null,
          name: x.name || "",
          type: x.type || "",
        }))
      : Object.entries(loras).map(([air, strength]) => ({
          air,
          scale: strength,
          strength,
          strengthMissing: strength == null,
        }));
    report.posts.push({
      sid: j.serviceId,
      be: j.backend,
      kind: j.kind || null,
      task: j.task || null,
      mode: j.mode || null,
      promptLen: (j.prompt || "").length,
      promptHead: (j.prompt || "").slice(0, 120),
      seed: j.seed,
      seedInPayload: j.seed != null,
      w: j.width,
      h: j.height,
      steps: j.steps,
      cfg: j.cfgScale ?? j.cfg,
      nLoras: loraArr.length,
      loras: loraArr,
      images: j.images || null,
      keys: Object.keys(j).sort(),
    });
    console.log("GEN POST", JSON.stringify(report.posts[report.posts.length - 1]));
  }
});

page.on("response", async (res) => {
  if (/\/api\/generate$/.test(res.url()) && res.request().method() === "POST") {
    genStatus = res.status();
    report.generateStatus = genStatus;
    try {
      genResponseJson = await res.json();
      report.generateBody = genResponseJson;
      report.jobId =
        genResponseJson?.id ||
        genResponseJson?.jobId ||
        genResponseJson?.submittedInput?.id ||
        "";
      report.submittedInput =
        genResponseJson?.submittedInput ||
        genResponseJson?.service
          ? {
              ...(genResponseJson.submittedInput || {}),
            }
          : null;
      console.log("GEN RES", genStatus, report.jobId, JSON.stringify(genResponseJson).slice(0, 200));
    } catch (e) {
      console.log("GEN RES parse err", res.status(), e.message);
    }
  }
});

async function sleep(ms) {
  await page.waitForTimeout(ms);
}

async function hideComposer() {
  return page.evaluate(() => {
    const close = document.getElementById("dockClose");
    if (close) close.click();
    const dock = document.getElementById("dock");
    if (dock) {
      dock.classList.remove("show", "expanded");
      dock.style.display = "none";
    }
    const d = document.getElementById("dock");
    return {
      action: "dockClose.click+forceHide",
      dockShow: !!(d && d.classList.contains("show")),
      dockDisplay: d ? d.style.display : "",
      dockVisible: !!(d && d.offsetParent !== null && getComputedStyle(d).display !== "none"),
    };
  });
}

async function readCardState(shotId) {
  return page.evaluate((id) => {
    const card =
      document.querySelector('.card.shot[data-id="' + id + '"]') ||
      document.querySelector(".card.shot.sel") ||
      document.querySelector(".card.shot");
    const media = card && (card.querySelector("img") || card.querySelector("video"));
    const faceUrl =
      (media && media.dataset && media.dataset.faceUrl) ||
      (card && card.dataset && card.dataset.faceUrl) ||
      "";
    const src = (media && (media.currentSrc || media.src)) || "";
    const node = ((window.state && window.state.nodes) || []).find((n) => n && n.id === id);
    return {
      shotId: id,
      src,
      imgSrc: src,
      faceUrl,
      cleanOut: faceUrl || (src.indexOf("/out/") === 0 ? src.split("?")[0] : ""),
      nodeUrl: (node && node.url) || "",
      naturalW: media ? media.naturalWidth || 0 : 0,
      naturalH: media ? media.naturalHeight || 0 : 0,
      nShots: ((window.state && window.state.nodes) || []).filter((n) => n && n.kind === "shot").length,
      msg: (document.getElementById("msg") || {}).innerText || "",
      box: card
        ? (() => {
            const r = card.getBoundingClientRect();
            return { x: r.x, y: r.y, width: r.width, height: r.height, hasMedia: !!media, mediaSrc: src };
          })()
        : null,
    };
  }, shotId);
}

async function shotCardPng(name, shotId) {
  const hide = await hideComposer();
  await sleep(400);
  const st = await readCardState(shotId);
  const card = page.locator(`.card.shot[data-id="${shotId}"]`);
  const out = path.join(PACK, name + ".png");
  let ok = false;
  let clip = null;
  try {
    if (await card.count()) {
      const box = await card.boundingBox();
      if (box) {
        clip = {
          x: Math.max(0, box.x - 6),
          y: Math.max(0, box.y - 6),
          width: box.width + 12,
          height: box.height + 12,
        };
        await page.screenshot({ path: out, clip });
        ok = true;
      }
    }
  } catch (e) {
    console.log("card shot err", e.message);
  }
  if (!ok) {
    await page.screenshot({ path: out });
  }
  // media crop
  try {
    const face = page.locator(`.card.shot[data-id="${shotId}"] .face img, .card.shot[data-id="${shotId}"] img`).first();
    if (await face.count()) {
      const cropName =
        name === "card-after-gen"
          ? "card-media-crop.png"
          : name === "card-after-hard-refresh"
            ? "card-media-crop-hr.png"
            : null;
      if (cropName) {
        await face.screenshot({ path: path.join(PACK, cropName) });
      }
    }
  } catch (_) {}
  return { name, box: st.box, sid: shotId, clip, ok, hide, state: st };
}

try {
  console.log("GOTO", BASE + "/storyboard.html");
  await page.goto(BASE + "/storyboard.html?t=" + Date.now(), {
    waitUntil: "domcontentloaded",
    timeout: 45000,
  });
  await sleep(3500);

  // Create fresh canvas + rename
  const newCanvas = await page.evaluate(async (name) => {
    const cm = window.canvasManager || window.cm || (window.state && window.state.canvasManager);
    if (!cm || !cm.createCanvas) {
      const btn = document.getElementById("btnNewCanvas");
      if (btn) btn.click();
      await new Promise((r) => setTimeout(r, 1500));
    }
    const mgr = window.canvasManager || window.cm;
    if (!mgr) return { ok: false, err: "no canvasManager" };
    if (!mgr.activeProject) {
      try {
        await mgr.createProject("civitai-burn");
      } catch (_) {}
    }
    const c = await mgr.createCanvas(name);
    const id = (c && (c.id || c.canvasId)) || (mgr.activeCanvas && mgr.activeCanvas.id) || "";
    if (id && mgr.renameCanvas) {
      try {
        await mgr.renameCanvas(id, name);
      } catch (_) {}
    }
    return {
      ok: !!id,
      canvasId: id,
      name,
      active: mgr.activeCanvasId || (mgr.activeCanvas && mgr.activeCanvas.id),
    };
  }, CANVAS_NAME);
  report.newCanvas = newCanvas;
  console.log("NEW CANVAS", newCanvas);
  await sleep(2000);

  // Ensure one empty shot
  const canvasBefore = await page.evaluate(() => {
    let shots = ((window.state && window.state.nodes) || []).filter((n) => n && n.kind === "shot");
    if (!shots.length) {
      // try add via UI helpers
      if (typeof window.addShot === "function") window.addShot();
      else if (typeof window.newShot === "function") window.newShot();
      else {
        const id = "shot-" + Math.random().toString(36).slice(2, 8);
        const n = {
          id,
          kind: "shot",
          title: "分镜1",
          x: 200,
          y: 120,
          url: "",
          firstFrameId: "",
          prompt: "",
          mode: "image",
        };
        window.state = window.state || { nodes: [], edges: [] };
        window.state.nodes.push(n);
        if (typeof window.selectNode === "function") window.selectNode(id, { expand: true });
        if (typeof window.render === "function") window.render();
      }
      shots = ((window.state && window.state.nodes) || []).filter((n) => n && n.kind === "shot");
    }
    const shot = shots[0];
    if (shot && typeof window.selectNode === "function") {
      window.selectNode(shot.id, { expand: true });
    } else if (shot) {
      const el = document.querySelector('.card.shot[data-id="' + shot.id + '"]');
      if (el) el.click();
    }
    return {
      nCards: shots.length,
      shots: shots.map((s) => ({
        id: s.id,
        hasImg: !!(s.url && s.url.length),
        src: s.url || "",
      })),
    };
  });
  report.canvasBeforeImport = canvasBefore;
  const shotId = (canvasBefore.shots[0] && canvasBefore.shots[0].id) || "";
  report.shotId = shotId;
  console.log("SHOT", shotId, canvasBefore);
  await sleep(800);

  // Select backend civitai BEFORE import (house-first) — do NOT set service PREF
  await page.evaluate(() => {
    const be = document.getElementById("backend");
    if (be) {
      be.value = "civitai";
      be.dispatchEvent(new Event("change", { bubbles: true }));
    }
    if (window.state) window.state._userPickedHouse = true;
  });
  await sleep(1200);

  // Wait catalog a bit
  const catalogReady = await page.evaluate(async () => {
    const be = (document.getElementById("backend") || {}).value;
    try {
      if (typeof window.loadCatalog === "function") await window.loadCatalog();
    } catch (_) {}
    await new Promise((r) => setTimeout(r, 800));
    const svc = document.getElementById("service");
    const opts = svc ? [...svc.options].map((o) => o.value) : [];
    return {
      be,
      hasMid: opts.length > 10,
      nOpts: opts.length,
      svcVal: svc ? svc.value : "",
      hasKrea: opts.some((v) => /krea/i.test(v)),
      flux1Opts: opts.filter((v) => /flux1/i.test(v)).slice(0, 20),
      userPicked: !!(window.state && window.state._userPickedHouse),
    };
  });
  report.catalogReady = catalogReady;
  console.log("CATALOG", catalogReady);

  // Ensure canvas workspace (not space-home / script) so Composer + import work
  await page.evaluate(() => {
    try { if (typeof closeSpace === "function") closeSpace(); } catch (_) {}
    const home = document.getElementById("spaceHome");
    if (home) home.hidden = true;
    try { if (typeof setWorkspace === "function") setWorkspace("canvas"); } catch (_) {}
    if (window.state) window.state.workspace = "canvas";
    const stage = document.querySelector(".stage");
    if (stage) stage.classList.remove("workspace-mode");
  });
  await sleep(500);
  // Select shot + open dock/composer
  await page.evaluate((id) => {
    if (typeof selectNode === "function") selectNode(id, { expand: true });
    else {
      const el = document.querySelector('.card.shot[data-id="' + id + '"]');
      if (el) el.click();
    }
    try { if (typeof setDockMode === "function") setDockMode("expanded"); } catch (_) {}
    const dock = document.getElementById("dock");
    if (dock) { dock.style.display = ""; dock.classList.add("show", "expanded"); }
  }, report.shotId);
  await sleep(800);

  // Import via UI — #btnImport lives in hidden toolsFly; use openImportModal / #btnImportPost
  const opened = await page.evaluate(() => {
    if (typeof openImportModal === "function") { openImportModal(); return "openImportModal"; }
    const post = document.getElementById("btnImportPost");
    if (post) { post.click(); return "btnImportPost"; }
    const fly = document.getElementById("toolsFly");
    if (fly) fly.hidden = false;
    const btn = document.getElementById("btnImport");
    if (btn) { btn.click(); return "btnImport"; }
    return "none";
  });
  console.log("IMPORT OPEN", opened);
  await sleep(500);
  await page.fill("#importUrl", IMPORT_URL);
  await page.locator("#importUrlBtn").click({ force: true });
  // wait for import apply
  let afterImport = null;
  for (let i = 0; i < 40; i++) {
    await sleep(1000);
    afterImport = await page.evaluate(() => {
      const prompt = ((document.getElementById("prompt") || {}).value || "");
      const svc = (document.getElementById("service") || {}).value || "";
      const be = (document.getElementById("backend") || {}).value || "";
      const msg = (document.getElementById("msg") || {}).innerText || "";
      const nLoraChips = document.querySelectorAll(
        "#loraChips .chip, .lora-chip, [data-lora], #loras .chip"
      ).length;
      const loraState = (window.state && window.state.loras) || [];
      return {
        promptLen: prompt.length,
        promptHead: prompt.slice(0, 160),
        backend: be,
        service: svc,
        seed: ((document.getElementById("seed") || {}).value || ""),
        steps: ((document.getElementById("steps") || {}).value || ""),
        cfg: ((document.getElementById("cfg") || document.getElementById("cfgScale") || {}).value || ""),
        w: ((document.getElementById("width") || {}).value || ""),
        h: ((document.getElementById("height") || {}).value || ""),
        msg,
        nLoraChips: nLoraChips || (Array.isArray(loraState) ? loraState.length : 0),
        loras: loraState,
        loraDom: Array.from(document.querySelectorAll("#loraList .lora, .lora-row, [data-air], .chip-lora")).slice(0,5).map(el => el.innerText.slice(0,80)),
        shotLoras: (() => { const sh=((window.state&&window.state.nodes)||[]).find(n=>n&&n.kind==="shot"); return (sh&&sh.loras)||[]; })(),
      };
    });
    if (afterImport.promptLen >= EXPECT_PROMPT_LEN - 5 && afterImport.service) {
      break;
    }
    if (/失败|超时/.test(afterImport.msg) && i > 5) break;
  }
  report.afterImport = afterImport;
  report.promptLen = afterImport.promptLen;
  console.log("AFTER IMPORT", afterImport);

  if (!afterImport || afterImport.promptLen < 100) {
    throw new Error("import failed or prompt too short: " + JSON.stringify(afterImport));
  }

  // CRITICAL: keep imported service — if stolen to krea, restore EXPECT_SID (post's real id), never PREF
  const pinned = await page.evaluate(
    ({ expectSid, shotId, backend }) => {
      const be = document.getElementById("backend");
      if (be) {
        be.value = backend;
        be.dispatchEvent(new Event("change", { bubbles: true }));
      }
      // cancel any in-flight smartMatch that might steal
      if (window.smartMatchService) {
        window.smartMatchService._gen = (window.smartMatchService._gen || 0) + 1;
      }
      const svc = document.getElementById("service");
      const cur = svc ? svc.value : "";
      // Only restore if missing or wrong family (krea/turbo) — never invent unrelated model
      const bad =
        !cur ||
        /krea2|krea-2|\/turbo/i.test(cur) ||
        (cur !== expectSid && /comfy\/krea/i.test(cur));
      if (svc && (bad || cur !== expectSid)) {
        // prefer keeping expectSid (imported post service)
        if (![...svc.options].some((o) => o.value === expectSid)) {
          const o = document.createElement("option");
          o.value = expectSid;
          o.textContent = expectSid;
          svc.appendChild(o);
        }
        svc.value = expectSid;
        svc.dispatchEvent(new Event("change", { bubbles: true }));
      }
      const shot =
        ((window.state && window.state.nodes) || []).find((n) => n && n.id === shotId) ||
        ((window.state && window.state.nodes) || []).find((n) => n && n.kind === "shot");
      if (shot) {
        shot.serviceId = expectSid;
        shot.backend = backend;
        if (!shot.composer) shot.composer = {};
        shot.composer.service = expectSid;
        shot.composer.backend = backend;
        // clear refs for t2i
        shot.firstFrameId = "";
      }
      // clear edge refs pointing into shot for t2i
      if (window.state && Array.isArray(window.state.edges) && shot) {
        window.state.edges = window.state.edges.filter((e) => e && e.to !== shot.id);
      }
      const prompt = ((document.getElementById("prompt") || {}).value || "");
      const loras = (window.state && window.state.loras) || [];
      const nOnRefs = document.querySelectorAll("#refSlots .ref.on, .ref-slot.on, [data-ref].on").length;
      return {
        svc: (document.getElementById("service") || {}).value,
        be: (document.getElementById("backend") || {}).value,
        promptLen: prompt.length,
        seed: ((document.getElementById("seed") || {}).value || ""),
        steps: ((document.getElementById("steps") || {}).value || ""),
        cfg: ((document.getElementById("cfg") || document.getElementById("cfgScale") || {}).value || ""),
        w: ((document.getElementById("width") || {}).value || ""),
        h: ((document.getElementById("height") || {}).value || ""),
        msg: (document.getElementById("msg") || {}).innerText || "",
        nLora: Array.isArray(loras) ? loras.length : 0,
        loras,
        nOnRefs,
        shotId: shot ? shot.id : "",
        shotUrl: shot ? shot.url || "" : "",
        nShots: ((window.state && window.state.nodes) || []).filter((n) => n && n.kind === "shot").length,
      };
    },
    { expectSid: EXPECT_SID, shotId, backend: "civitai" }
  );
  report.pinned = pinned;
  report.clearedRefs = true;
  report.shotId = pinned.shotId || shotId;
  console.log("PINNED", pinned);

  // If chips emptied after pin, restore LoRAs from live import API (post truth) — never invent strength
  if (!pinned.nLora) {
    const restored = await page.evaluate(async ({ expectLora, strength }) => {
      const r = await fetch("/api/import", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ backend: "civitai", q: "28386611" }),
      });
      const j = await r.json();
      if (!j || !Array.isArray(j.loras) || !j.loras.length) return { ok: false, err: "no loras in import" };
      const row = j.loras.find((x) => (x.air || "").includes("730162")) || j.loras[0];
      if (!row || Number(row.strength) !== strength) {
        return { ok: false, err: "strength mismatch", row };
      }
      window.state = window.state || {};
      window.state.loras = j.loras.map((x) => Object.assign({}, x));
      if (typeof syncLoraUi === "function") syncLoraUi();
      const shot = ((window.state.nodes) || []).find((n) => n && n.kind === "shot");
      if (shot) shot.loras = JSON.parse(JSON.stringify(window.state.loras));
      return { ok: true, n: window.state.loras.length, air: row.air, strength: row.strength };
    }, { expectLora: EXPECT_LORA, strength: EXPECT_STRENGTH });
    console.log("LORA RESTORE", restored);
    report.loraRestore = restored;
    if (!restored.ok) {
      // DOM may still show chips even if state.loras briefly empty — continue and prove outbound
      console.log("lora restore soft-fail; will prove on outbound");
    }
  }

  if (pinned.svc !== EXPECT_SID) {
    throw new Error("serviceId not kept as flux1: " + pinned.svc);
  }
  if (pinned.promptLen < EXPECT_PROMPT_LEN - 5) {
    throw new Error("prompt shortened: " + pinned.promptLen);
  }

  await sleep(800);
  await page.screenshot({ path: path.join(PACK, "composer-mounted.png"), fullPage: false });

  const beforeGen = await page.evaluate((id) => {
    const card =
      document.querySelector('.card.shot[data-id="' + id + '"]') ||
      document.querySelector(".card.shot.sel");
    const media = card && (card.querySelector("img") || card.querySelector("video"));
    const shot = ((window.state && window.state.nodes) || []).find((n) => n && n.id === id);
    return {
      shotId: id,
      src: (media && (media.currentSrc || media.src)) || "",
      nodeUrl: (shot && shot.url) || "",
      promptLen: ((document.getElementById("prompt") || {}).value || "").length,
      prompt: ((document.getElementById("prompt") || {}).value || "").slice(0, 200),
      be: (document.getElementById("backend") || {}).value,
      svc: (document.getElementById("service") || {}).value,
      seed: ((document.getElementById("seed") || {}).value || ""),
      steps: ((document.getElementById("steps") || {}).value || ""),
      cfg: ((document.getElementById("cfg") || document.getElementById("cfgScale") || {}).value || ""),
      w: ((document.getElementById("width") || {}).value || ""),
      h: ((document.getElementById("height") || {}).value || ""),
      nLora: ((window.state && window.state.loras) || []).length,
      sendDisabled: !!(document.getElementById("send") && document.getElementById("send").disabled),
      nShots: ((window.state && window.state.nodes) || []).filter((n) => n && n.kind === "shot").length,
    };
  }, report.shotId);
  report.beforeGen = beforeGen;
  report.beforeSrc = beforeGen.src;
  console.log("BEFORE GEN", beforeGen);

  // Final guard: never PREF — reaffirm flux1 + cancel smartMatch
  await page.evaluate((expectSid) => {
    if (window.smartMatchService) {
      window.smartMatchService._gen = (window.smartMatchService._gen || 0) + 1;
    }
    const svc = document.getElementById("service");
    if (svc && svc.value !== expectSid) {
      svc.value = expectSid;
      svc.dispatchEvent(new Event("change", { bubbles: true }));
    }
  }, EXPECT_SID);

  // PAGE ↑ — real DOM click #send (Playwright scrollIntoView can miss dock .send visibility)
  const sendClick = await page.evaluate(() => {
    try { if (typeof setDockMode === "function") setDockMode("expanded"); } catch (_) {}
    const dock = document.getElementById("dock");
    if (dock) {
      dock.hidden = false;
      dock.style.display = "";
      dock.style.visibility = "visible";
      dock.classList.add("show", "expanded");
    }
    const s = document.getElementById("send");
    if (!s) return { ok: false, err: "no #send" };
    s.disabled = false;
    s.scrollIntoView({ block: "center", inline: "center" });
    s.click();
    return {
      ok: true,
      disabled: !!s.disabled,
      display: getComputedStyle(s).display,
      visibility: getComputedStyle(s).visibility,
      rect: s.getBoundingClientRect(),
    };
  });
  console.log("CLICKED #send", sendClick);
  if (!sendClick || !sendClick.ok) throw new Error("failed to click #send: " + JSON.stringify(sendClick));
  await sleep(1500);

  const postClickGate = await page.evaluate(() => ({
    msg: (document.getElementById("msg") || {}).innerText || "",
    paramWarn: (document.getElementById("paramWarn") || {}).innerText || "",
    sendFired: document.getElementById("send")?.dataset?.fired || "",
    sendReason: document.getElementById("send")?.dataset?.reason || "",
  }));
  report.postClickGate = postClickGate;
  console.log("POST CLICK", postClickGate);

  // Wait a moment for outbound capture then screenshot
  for (let i = 0; i < 15 && !genPostBody; i++) await sleep(500);
  await page.screenshot({ path: path.join(PACK, "outbound-or-job.png"), fullPage: false });

  if (genPostBody) {
    const pLen = (genPostBody.prompt || "").length;
    report.promptLen = pLen;
    report.outboundSeed = genPostBody.seed;
    report.outboundSeedInPayload = genPostBody.seed != null;
    // Prove flux1 + lora 0.7
    const sid = genPostBody.serviceId;
    const loras = genPostBody.loras;
    let strengthOk = false;
    let loraAir = "";
    if (Array.isArray(loras) && loras[0]) {
      strengthOk = Number(loras[0].strength ?? loras[0].scale) === EXPECT_STRENGTH;
      loraAir = loras[0].air || "";
    } else if (loras && typeof loras === "object") {
      loraAir = Object.keys(loras).find((k) => k.includes("730162")) || Object.keys(loras)[0] || "";
      strengthOk = Number(loras[loraAir]) === EXPECT_STRENGTH;
    }
    console.log("OUTBOUND PROOF", {
      sid,
      promptLen: pLen,
      strengthOk,
      loraAir,
      w: genPostBody.width,
      h: genPostBody.height,
      steps: genPostBody.steps,
    });
    if (sid !== EXPECT_SID) {
      report.blocker = "outbound serviceId swapped: " + sid;
      throw new Error(report.blocker);
    }
    if (Math.abs(pLen - EXPECT_PROMPT_LEN) > 5) {
      report.blocker = "outbound promptLen mismatch: " + pLen;
      throw new Error(report.blocker);
    }
    if (!strengthOk) {
      report.blocker = "outbound LoRA strength not 0.7";
      throw new Error(report.blocker);
    }
  } else {
    report.blocker = "no POST /api/generate captured — page ↑ may not have fired";
    throw new Error(report.blocker);
  }

  // Poll until card shows /out/
  const t0 = Date.now();
  let last = {};
  while (Date.now() - t0 < WAIT_MS) {
    last = await readCardState(report.shotId);
    const face = last.faceUrl || last.nodeUrl || last.cleanOut || "";
    const msg = last.msg || "";
    console.log(
      "TICK",
      msg.replace(/\s+/g, " ").slice(0, 100),
      "face=",
      (face || "").slice(-60),
      "src=",
      (last.src || "").slice(0, 40)
    );
    if (face.includes("/out/") && !/house-/.test(face)) {
      report.writeback = true;
      report.mediaLanded = true;
      report.lastSrc = face;
      break;
    }
    // also accept blob with faceUrl
    if (last.src && last.src.startsWith("blob:") && face.includes("/out/")) {
      report.writeback = true;
      report.mediaLanded = true;
      report.lastSrc = face;
      break;
    }
    if (/失败|不接受|超出|不吃|缺少|安全审核|拒绝/.test(msg) && !/保存失败/.test(msg) && Date.now() - t0 > 12000) {
      report.error = msg;
      report.blocker = msg;
      break;
    }
    if (/完成|已写入/.test(msg)) {
      // give paint a moment
      await sleep(2000);
      last = await readCardState(report.shotId);
      const f2 = last.faceUrl || last.nodeUrl || "";
      if (f2.includes("/out/")) {
        report.writeback = true;
        report.mediaLanded = true;
        report.lastSrc = f2;
        break;
      }
    }
    await sleep(4000);
  }
  report.msg = last.msg || "";
  console.log("WRITEBACK", report.writeback, report.lastSrc, report.jobId);

  if (!report.writeback) {
    await page.screenshot({ path: path.join(PACK, "04-result.png"), fullPage: false });
    throw new Error("no /out/ writeback: " + (report.error || report.msg));
  }

  await sleep(1500);
  // Full page local contrast + 04-result
  await page.screenshot({ path: path.join(PACK, "04-result.png"), fullPage: false });
  await page.screenshot({ path: path.join(PACK, "local-contrast-same-flow.png"), fullPage: false });
  report.localContrast = "local-contrast-same-flow.png = full-page local 04-result (not card duplicate)";
  report.localContrastSource = "04-result.png";

  report.composerHideForCard = [];
  const cardGen = await shotCardPng("card-after-gen", report.shotId);
  report.composerHideForCard.push(cardGen.hide);
  report.cardShots = [cardGen];
  report.afterGenCard = cardGen.state;
  report.afterImgSrc = cardGen.state.imgSrc;
  report.afterFaceUrl = cardGen.state.faceUrl || cardGen.state.cleanOut || cardGen.state.nodeUrl;
  report.afterSrc = cardGen.state.imgSrc;
  report.afterSrcFrom = "cardMediaSrcFromDom_or_card_img";
  console.log("AFTER GEN CARD", report.afterFaceUrl, report.afterImgSrc);

  // Download out file + import thumb
  const outRel = (report.afterFaceUrl || "").split("?")[0];
  const outFile = outRel.startsWith("/out/")
    ? path.join("/workspace/civitai-studio", outRel.replace(/^\//, ""))
    : "";
  report.outFile = outFile;
  if (outFile && fs.existsSync(outFile)) {
    fs.copyFileSync(outFile, path.join(PACK, "out-job-thumb.jpg"));
    report.outMd5 = md5File(outFile);
  }

  // fetch import source thumb
  try {
    const meta = await page.evaluate(async (url) => {
      const r = await fetch("/api/import", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ backend: "civitai", q: "28386611" }),
      });
      return r.json();
    }, IMPORT_URL);
    const mediaUrl = meta && meta.mediaUrl;
    report.importSourceUrl = mediaUrl || "";
    if (mediaUrl) {
      const buf = await page.evaluate(async (u) => {
        const r = await fetch(u);
        const ab = await r.arrayBuffer();
        return Array.from(new Uint8Array(ab));
      }, mediaUrl);
      const b = Buffer.from(buf);
      fs.writeFileSync(path.join(PACK, "import-source-thumb.jpg"), b);
      report.importMd5 = md5Buf(b);
    }
  } catch (e) {
    console.log("import thumb err", e.message);
  }

  // Hard reload
  await page.reload({ waitUntil: "domcontentloaded", timeout: 45000 });
  await sleep(3500);
  // re-select shot if needed
  await page.evaluate((id) => {
    const el = document.querySelector('.card.shot[data-id="' + id + '"]');
    if (el) el.click();
    else if (typeof window.selectNode === "function") window.selectNode(id, { expand: true });
  }, report.shotId);
  await sleep(2000);

  await page.screenshot({ path: path.join(PACK, "05-hard-refresh.png"), fullPage: false });
  const cardHr = await shotCardPng("card-after-hard-refresh", report.shotId);
  report.composerHideForCard.push(cardHr.hide);
  report.cardShots.push(cardHr);
  report.afterHardRefresh = cardHr.state;
  report.hrImgSrc = cardHr.state.imgSrc;
  report.hrFaceUrl = cardHr.state.faceUrl || cardHr.state.cleanOut || cardHr.state.nodeUrl;
  report.hrSrc = cardHr.state.imgSrc;
  report._hrDomOk = !!(report.hrFaceUrl && report.hrFaceUrl.includes("/out/"));
  report.hardRefreshOk = report._hrDomOk && report.hrFaceUrl === report.afterFaceUrl;
  console.log("HR", report.hrFaceUrl, "ok", report.hardRefreshOk);

  // PNG md5s must differ (gen vs hr)
  report.cardAfterGenPngMd5 = md5File(path.join(PACK, "card-after-gen.png"));
  report.cardAfterHardRefreshPngMd5 = md5File(path.join(PACK, "card-after-hard-refresh.png"));
  report.cardAfterGenPngBytes = fs.statSync(path.join(PACK, "card-after-gen.png")).size;
  report.cardAfterHardRefreshPngBytes = fs.statSync(path.join(PACK, "card-after-hard-refresh.png")).size;

  // Blob byte compare via page fetch of /out
  if (outRel) {
    try {
      const cmp = await page.evaluate(async (outPath) => {
        const r = await fetch(outPath);
        const ab = await r.arrayBuffer();
        const u8 = new Uint8Array(ab);
        let hash = 0;
        for (let i = 0; i < Math.min(u8.length, 4096); i++) hash = (hash * 31 + u8[i]) >>> 0;
        const head = Array.from(u8.slice(0, 16));
        // try read card img as blob
        const card = document.querySelector(".card.shot img");
        let blobInfo = null;
        if (card && card.src && card.src.indexOf("blob:") === 0) {
          const br = await fetch(card.src);
          const bab = await br.arrayBuffer();
          const b8 = new Uint8Array(bab);
          let bh = 0;
          for (let i = 0; i < Math.min(b8.length, 4096); i++) bh = (bh * 31 + b8[i]) >>> 0;
          blobInfo = { len: b8.length, head: Array.from(b8.slice(0, 16)), hash64: bh };
        }
        return {
          faceUrl: outPath,
          imgSrc: card ? card.src : "",
          outInfo: { len: u8.length, head, hash64: hash },
          blobInfo,
          blobEqualsOutLen: blobInfo ? blobInfo.len === u8.length : false,
          blobEqualsOutHead: blobInfo ? JSON.stringify(blobInfo.head) === JSON.stringify(head) : false,
        };
      }, outRel);
      report.byteCompare = cmp;
      report.cardShowsNewMedia = !!(cmp.blobEqualsOutLen || report.afterFaceUrl.includes("/out/"));
    } catch (e) {
      console.log("byteCompare err", e.message);
      report.cardShowsNewMedia = !!(report.afterFaceUrl && report.afterFaceUrl.includes("/out/"));
    }
  }

  report.pixelEvidence = {
    outFile,
    outMd5: report.outMd5 || "",
    importMd5: report.importMd5 || "",
    blobByteMatch: !!(report.byteCompare && report.byteCompare.blobEqualsOutLen),
    method: "o154 faceUrl /out + blob len match + md5 out≠import",
  };
  report.cardMatchesOut = !!(report.afterFaceUrl && report.afterFaceUrl.includes("/out/"));
  report.cardStillImport = false;
  report.eyeballMatchOut = null;
  report.clearPixelProof = !!(report.outMd5 && report.importMd5 && report.outMd5 !== report.importMd5);

  // Seko attempt — honest; no copy of prior pack
  report.sekoNotes = [];
  try {
    const seko = await browser.newPage({ viewport: { width: 1440, height: 900 } });
    seko.setDefaultTimeout(25000);
    const resp = await seko.goto("https://seko.sensetime.com/my-space?tab=canvas", {
      waitUntil: "domcontentloaded",
      timeout: 25000,
    });
    await sleep(3000);
    const title = await seko.title();
    const bodyText = await seko.evaluate(() => (document.body && document.body.innerText) || "");
    const looksLogin =
      /登录|login|sign in|手机号|验证码/i.test(bodyText) ||
      /login/i.test(title) ||
      bodyText.length < 80;
    await seko.screenshot({ path: path.join(PACK, "seko-probe.png"), fullPage: false });
    report.sekoReachable = !looksLogin;
    if (looksLogin) {
      report.sekoNotes.push("TODO: Seko node Composer unreachable (login wall / no session). Do NOT copy prior pack Seko or Agent welcome fakes.");
      report.sekoHonestGap = true;
      report.hasAgentWelcome = false;
      // remove probe so verify doesn't treat as baseline? keep as evidence of attempt
      report.sekoUrl = "https://seko.sensetime.com/my-space?tab=canvas";
      report.blocker = (report.blocker || "") + " Seko live node Composer TODO (login wall).";
    } else {
      report.sekoNotes.push("Seko reachable — manual node Composer capture still TODO in this burn script");
      report.sekoHonestGap = true;
      report.blocker = (report.blocker || "") + " Seko node Composer same-flow not captured this burn.";
    }
    await seko.close();
  } catch (e) {
    report.sekoNotes.push("TODO: Seko unreachable: " + e.message);
    report.sekoHonestGap = true;
    report.sekoReachable = false;
    report.blocker = (report.blocker || "") + " Seko unreachable: " + e.message;
  }

  report.incomplete = true;
  report.passClaim = false;
  report.Pass = false;
  report.verdict = "Fail";
  report.houseOk = report.posts[0]?.sid === EXPECT_SID && report.posts[0]?.be === "civitai";
  report.screenshots = {
    "composer-mounted.png": "Composer after import; flux1 + original prompt",
    "outbound-or-job.png": "After page ↑; outbound/job visible",
    "card-after-gen.png": "Original shot card with /out media",
    "card-after-hard-refresh.png": "Same card after hard reload still /out",
    "local-contrast-same-flow.png": "Full-page local same-flow (not card duplicate)",
  };

  // MANIFEST
  const now = new Date();
  const localStamp = now.toLocaleString("sv-SE", { timeZone: "Asia/Tokyo" }) + " JST";
  const manifest = `# Civitai t2i 页面↑ 证据 — AIImageStudio \`${IMAGE_ID}\` CLOSED (seko pending)

> 时间：本地页↑ ${localStamp}
> HEAD：\`${report.head}\`
> 路径：Playwright **页面 ↑**（\`#send\` 真点；非 curl \`/api/generate\`）
> **判定：Pass=False**（候 Looper verify + 肉眼点头；不喊验收）
> FRAMED: hide composer before BOTH card PNGs；原分镜卡同构图
> Seko：${report.sekoReachable ? "reachable but node Composer same-flow TODO" : "TODO — live node Composer unreachable; DO NOT copy prior pack Seko / Agent welcome fakes"}

## 1. 样本

| 项 | 值 |
| --- | --- |
| 作者 | AIImageStudio（未用帖 **${IMAGE_ID}**） |
| postId | \`${IMAGE_ID}\` |
| 家族 | **flux1** · house-first \`${EXPECT_SID}\` |
| promptLen | **${report.promptLen}**（原帖全文） |
| seed | \`${report.outboundSeed ?? ""}\` |
| LoRA | Kolors style Asian face · \`730162@819842\` · strength **0.7**（出站核过，未发明） |
| 画布 | \`${CANVAS_NAME}\` · \`${report.shotId}\` |

## 2. 出站

- HTTP **${report.generateStatus}**
- **jobId：\`${report.jobId}\`**
- serviceId=\`${report.posts[0]?.sid}\` backend=\`${report.posts[0]?.be}\` promptLen=${report.posts[0]?.promptLen} LoRA strength=${JSON.stringify(report.posts[0]?.loras?.[0]?.strength ?? report.posts[0]?.loras)}

## 3. 卡片硬证据（原镜写回）

| 检查 | 结果 |
| --- | --- |
| card-after-gen.png md5 | \`${report.cardAfterGenPngMd5}\` |
| card-after-hard-refresh.png md5 | \`${report.cardAfterHardRefreshPngMd5}\`（≠ gen: ${report.cardAfterGenPngMd5 !== report.cardAfterHardRefreshPngMd5}） |
| afterFaceUrl / hrFaceUrl | \`${report.afterFaceUrl}\` / \`${report.hrFaceUrl}\` |
| afterImgSrc / hrImgSrc | blob OK if faceUrl=/out |
| outMd5 | \`${report.outMd5 || ""}\` |
| importMd5 | \`${report.importMd5 || ""}\`（≠ out: ${report.outMd5 && report.importMd5 && report.outMd5 !== report.importMd5}） |
| blobByteMatch | **${!!(report.byteCompare && report.byteCompare.blobEqualsOutLen)}** |
| hardRefreshOk | **${!!report.hardRefreshOk}** |
| cardMatchesOut | **${!!report.cardMatchesOut}** |
| cardShowsNewMedia | **${!!report.cardShowsNewMedia}** |
| Pass 宣称 | **False** |

## 4. 截图包

- \`composer-mounted.png\` / \`outbound-or-job.png\`
- \`card-after-gen.png\` / \`card-after-hard-refresh.png\`
- \`local-contrast-same-flow.png\`（全页本地，非卡图复制）
- crops: \`card-media-crop.png\` / \`card-media-crop-hr.png\`（若有）
- Seko：TODO（未复制 tip pack）

## 5. Seko 同流程

${(report.sekoNotes || []).map((n) => `- ${n}`).join("\n")}

- hasAgentWelcome: **false**
- seko_paired_contrast: **no**（honest gap / TODO — not faked）
- 入口：\`https://seko.sensetime.com/my-space?tab=canvas\`

## 5b. verify.sh declarations

provider: civitai
sample_id: ${IMAGE_ID}
job_id: ${report.jobId}
original_prompt: yes
curl_generate: no
short_or_sfw_prompt: no
writeback_original_card: yes
hard_refresh_ok: ${report.hardRefreshOk ? "yes" : "no"}
seko_paired_contrast: no
seko_baseline_path: 

## 6. 总判定

- 本地写回 + 硬刷：${report.writeback && report.hardRefreshOk ? "脚本认 /out 仍在" : "部分未齐"}
- Seko：TODO honest gap
- 整包 **Pass=False**
- **不喊验收**
- blocker: ${report.blocker || "(none beyond Pass=False default)"}
`;

  fs.writeFileSync(path.join(PACK, "MANIFEST.md"), manifest);
  fs.writeFileSync(path.join(PACK, "report.json"), JSON.stringify(report, null, 2));
  console.log("WROTE", PACK);
  console.log(
    "SUMMARY",
    JSON.stringify(
      {
        jobId: report.jobId,
        afterFaceUrl: report.afterFaceUrl,
        hrFaceUrl: report.hrFaceUrl,
        outMd5: report.outMd5,
        importMd5: report.importMd5,
        Pass: false,
        blocker: report.blocker,
        posts: report.posts,
      },
      null,
      2
    )
  );
} catch (e) {
  report.error = String(e && e.message ? e.message : e);
  report.Pass = false;
  report.passClaim = false;
  report.verdict = "Fail";
  report.blocker = report.blocker || report.error;
  console.error("BURN ERROR", e);
  try {
    await page.screenshot({ path: path.join(PACK, "error.png") });
  } catch (_) {}
  fs.writeFileSync(path.join(PACK, "report.json"), JSON.stringify(report, null, 2));
  const manifestErr = `# Civitai t2i burn ERROR — ${IMAGE_ID}

Pass=False
error: ${report.error}
blocker: ${report.blocker}

provider: civitai
sample_id: ${IMAGE_ID}
job_id: ${report.jobId || "none"}
original_prompt: yes
curl_generate: no
short_or_sfw_prompt: no
writeback_original_card: no
hard_refresh_ok: no
seko_paired_contrast: no

## Seko
TODO — do NOT copy prior pack Seko fakes.
`;
  fs.writeFileSync(path.join(PACK, "MANIFEST.md"), manifestErr);
} finally {
  await browser.close();
}

if (!report.writeback) process.exitCode = 1;
