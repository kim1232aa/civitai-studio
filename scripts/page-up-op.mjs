import { chromium } from "playwright";
import fs from "fs";

const backend = process.env.QA_BACKEND || "civitai";
const op = process.env.QA_OP || "t2i"; // t2i | i2i | i2v
const imageId = process.env.QA_IMAGE_ID || "";
const shotId = process.env.QA_SHOT || "";
const waitMs = Number(process.env.QA_WAIT_MS || 8 * 60 * 1000);
const outDir = "/workspace/civitai-studio/docs/review-shots";
fs.mkdirSync(outDir, { recursive: true });
const tag = `${backend}-${op}-${imageId}`;
const report = { backend, op, imageId, shotId, promptLen: 0, service: "", generate: false, writeback: false, error: "", posts: [] };

const HOUSE = {
  civitai: "shot-civitai",
  fal: "shot-fal",
  huggingface: "shot-hf",
  "modelscope-ai": "shot-msai",
  "modelscope-cn": "shot-mscn",
  "nano-gpt": "shot-nano",
};
const PREF = {
  civitai: {
    t2i: "image/comfy/krea2/turbo/createImage",
    i2i: "image/comfy/krea2/edit/editImage",
    i2v: "video/minimax-h3-comfy/imageToVideo",
  },
  fal: {
    t2i: "fal-ai/krea-2/turbo",
    i2i: "fal-ai/flux-pro/kontext",
    i2v: "fal-ai/minimax/video-01/image-to-video",
  },
  huggingface: {
    t2i: "krea/Krea-2-Turbo",
    i2i: "Qwen/Qwen-Image-Edit",
    i2v: "Wan-AI/Wan2.2-TI2V-5B",
  },
  "modelscope-ai": {
    t2i: "krea/Krea-2-Turbo",
    i2i: "Qwen/Qwen-Image-Edit",
    i2v: "Wan-AI/Wan2.1-I2V-14B-720P",
  },
  "modelscope-cn": {
    t2i: "krea/Krea-2-Turbo",
    i2i: "Qwen/Qwen-Image-Edit",
    i2v: "Wan-AI/Wan2.1-I2V-14B-720P",
  },
  "nano-gpt": {
    t2i: "z-image-turbo",
    i2i: "z-image-turbo-image-to-image",
    i2v: "bytedance/seedance-2.5-spicy",
  },
};

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
page.setDefaultTimeout(45000);
page.on("request", (req) => {
  if (req.method() === "POST" && /\/api\/generate$/.test(req.url())) {
    let j = {};
    try { j = JSON.parse(req.postData() || "{}"); } catch (_) {}
    report.posts.push({
      sid: j.serviceId, be: j.backend, kind: j.kind,
      promptLen: (j.prompt || "").length, promptHead: (j.prompt || "").slice(0, 80),
      seed: j.seed, steps: j.steps, w: j.width, h: j.height,
      loras: j.loras, images: j.images || j.image_url || j.firstFrame,
    });
    console.log("GEN POST", JSON.stringify(report.posts[report.posts.length - 1]));
  }
});
page.on("response", async (res) => {
  if (/\/api\/generate$/.test(res.url()) && res.request().method() === "POST") {
    try { console.log("GEN RES", res.status(), JSON.stringify(await res.json()).slice(0, 280)); }
    catch (e) { console.log("GEN RES", res.status(), e.message); }
  }
});

function shotPath(step) { return `${outDir}/${tag}-${step}.png`; }

try {
  await page.goto("http://127.0.0.1:8080/storyboard?t=" + Date.now(), { waitUntil: "domcontentloaded", timeout: 30000 });
  await page.waitForTimeout(2800);
  const targetId = shotId || HOUSE[backend];
  await page.evaluate((id) => {
    const card = document.querySelector('.card.shot[data-id="' + id + '"]');
    if (card) card.click();
    else {
      const first = document.querySelector(".card.shot");
      if (first) first.click();
    }
  }, targetId);
  await page.waitForTimeout(400);

  await page.locator("#btnImport").click();
  await page.waitForTimeout(300);
  await page.fill("#importUrl", "https://civitai.red/images/" + imageId);
  await page.locator("#importUrlBtn").click({ force: true });
  await page.waitForTimeout(5000);
  await page.screenshot({ path: shotPath("import") });

  const afterImport = await page.evaluate((args) => {
    const { backend, op, pref } = args;
    const be = document.getElementById("backend");
    if (be) be.value = backend;
    be && be.dispatchEvent(new Event("change", { bubbles: true }));
    const modeBtn = document.querySelector(op === "i2v" ? '#composerModes [data-mode="video"]' : '#composerModes [data-mode="image"]');
    if (modeBtn) modeBtn.click();
    const svc = document.getElementById("service");
    if (svc && pref) {
      const opt = [...svc.options].find((o) => o.value === pref);
      if (!opt) {
        const o = document.createElement("option");
        o.value = pref; o.textContent = pref;
        svc.appendChild(o);
      }
      svc.value = pref;
      svc.dispatchEvent(new Event("change", { bubbles: true }));
    }
    return {
      promptLen: ((document.getElementById("prompt") || {}).value || "").length,
      prompt: ((document.getElementById("prompt") || {}).value || "").slice(0, 100),
      backend: (document.getElementById("backend") || {}).value,
      service: (document.getElementById("service") || {}).value,
      seed: (document.getElementById("seed") || {}).value,
      msg: (document.getElementById("msg") || {}).innerText || "",
    };
  }, { backend, op, pref: (PREF[backend] || {})[op] });
  report.promptLen = afterImport.promptLen;
  report.service = afterImport.service;
  console.log("IMPORT", afterImport);
  await page.waitForTimeout(2500);
  await page.evaluate((args) => {
    const { backend, op, pref, shotId } = args;
    const be = document.getElementById("backend");
    if (be) { be.value = backend; be.dispatchEvent(new Event("change", { bubbles: true })); }
    const svc = document.getElementById("service");
    if (svc && pref) {
      if (![...svc.options].some((o) => o.value === pref)) {
        const o = document.createElement("option");
        o.value = pref; o.textContent = pref; svc.appendChild(o);
      }
      svc.value = pref;
      svc.dispatchEvent(new Event("change", { bubbles: true }));
    }
    if (window.smartMatchService) window.smartMatchService._gen = (window.smartMatchService._gen || 0) + 1;
    const nodes = (window.state && window.state.nodes) || [];
    const live = nodes.find((n) => n && n.id === shotId) || nodes.find((n) => n && n.kind === "shot");
    if (live && pref) {
      live.serviceId = pref;
      live.backend = backend;
      if (!live.composer) live.composer = {};
      live.composer.service = pref;
      live.composer.backend = backend;
      live.mode = op === "i2v" ? "video" : "image";
    }
  }, { backend, op, pref: (PREF[backend] || {})[op], shotId: targetId });
  await page.screenshot({ path: shotPath("composer") });

  if (report.promptLen < 60) {
    report.error = "prompt too short";
    throw new Error(report.error);
  }

  if (op === "i2i" || op === "i2v") {
    await page.evaluate((args) => {
      const shot = (window.state && window.state.nodes || []).find((n) => n && n.id === args.shotId) ||
        (window.state && window.state.nodes || []).find((n) => n && n.kind === "shot" && n.id && n.id.indexOf(args.backend) >= 0);
      const live = shot || (window.state && window.state.nodes || []).find((n) => n && n.kind === "shot");
      if (!live || !live.url) return;
      const id = "ref-" + Date.now().toString(36);
      const asset = { id, kind: "image", title: "参考", x: live.x - 80, y: live.y, url: live.url };
      window.state.nodes.push(asset);
      window.state.edges = window.state.edges || [];
      window.state.edges.push({ from: id, to: live.id });
      if (args.op === "i2v") live.firstFrameId = id;
    }, { op, backend, shotId: targetId });
    await page.waitForTimeout(400);
  }

  const beforeSrc = await page.evaluate((id) => {
    const card = document.querySelector('.card.shot[data-id="' + id + '"]') || document.querySelector(".card.shot.sel");
    const media = card && (card.querySelector("img") || card.querySelector("video"));
    return (media && (media.currentSrc || media.src)) || "";
  }, targetId);
  report.beforeSrc = beforeSrc;

  await page.evaluate((args) => {
    const { backend, op, pref } = args;
    const be = document.getElementById("backend");
    if (be) { be.value = backend; be.dispatchEvent(new Event("change", { bubbles: true })); }
    const modeBtn = document.querySelector(op === "i2v" ? '#composerModes [data-mode="video"]' : '#composerModes [data-mode="image"]');
    if (modeBtn) modeBtn.click();
    const svc = document.getElementById("service");
    if (svc && pref) {
      if (![...svc.options].some((o) => o.value === pref)) {
        const o = document.createElement("option");
        o.value = pref; o.textContent = pref; svc.appendChild(o);
      }
      svc.value = pref;
      svc.dispatchEvent(new Event("change", { bubbles: true }));
    }
    if (window.smartMatchService) window.smartMatchService._gen = (window.smartMatchService._gen || 0) + 1;
    const s = document.getElementById("send");
    if (s) { s.scrollIntoView({ block: "center" }); s.click(); }
  }, { backend, op, pref: (PREF[backend] || {})[op] });
  report.generate = true;
  await page.waitForTimeout(1500);
  await page.screenshot({ path: shotPath("sending") });

  const start = Date.now();
  let last = {};
  while (Date.now() - start < waitMs) {
    last = await page.evaluate((id) => {
      const card = document.querySelector('.card.shot[data-id="' + id + '"]') || document.querySelector(".card.shot.sel");
      const media = card && (card.querySelector("img") || card.querySelector("video"));
      return {
        msg: (document.getElementById("msg") || {}).innerText || "",
        src: (media && (media.currentSrc || media.src)) || "",
      };
    }, targetId);
    console.log("TICK", last.msg.replace(/\s+/g, " ").slice(0, 120), (last.src || "").slice(-48));
    if (last.src && last.src !== beforeSrc && last.src.includes("/out/") && !/house-/.test(last.src)) {
      report.writeback = true;
      break;
    }
    if (/失败|不接受|超出|不吃|缺少|安全审核/.test(last.msg) && !/保存失败/.test(last.msg) && Date.now() - start > 8000) {
      report.error = last.msg;
      break;
    }
    if (/完成|已写入/.test(last.msg) && last.src && last.src !== beforeSrc && last.src.includes("/out/")) {
      report.writeback = true;
      break;
    }
    await page.waitForTimeout(4000);
  }
  report.msg = last.msg;
  report.src = last.src;
  await page.screenshot({ path: shotPath("result") });
  await page.reload({ waitUntil: "domcontentloaded" });
  await page.waitForTimeout(2500);
  await page.screenshot({ path: shotPath("reload") });
} catch (e) {
  report.error = String(e && e.message ? e.message : e);
  await page.screenshot({ path: shotPath("error") }).catch(() => {});
} finally {
  fs.writeFileSync("/tmp/" + tag + ".json", JSON.stringify(report, null, 2));
  console.log("REPORT", JSON.stringify(report, null, 2));
  await browser.close();
  if (!report.writeback) process.exitCode = 1;
}
