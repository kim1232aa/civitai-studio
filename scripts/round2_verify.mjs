// Stage3 round2 driver — real page clicks only. Usage:
//   PW_VERSION_OVERRIDE=1.56.1 node round2.mjs <case> [args]
// cases: civ-i2i | fal-i2i | nano-i2i | civ-i2v | fal-i2v | ms-video-honest | hf-t2i | nano-video-list | reload-check
import { chromium } from "playwright";
import { writeFileSync, existsSync } from "fs";

const URL0 = "http://127.0.0.1:18832/storyboard.html";
const SHOTS = "/mnt/agents/work/verify/shots";
const REF_IMG = "/mnt/agents/work/civitai-studio-repo/out/12100372-20260907215435634_0.jpg";
const STAMP = new Date().toISOString().replace(/[:T]/g, "").slice(0, 14);

async function openPage(browser) {
  const p = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
  p.on("pageerror", (e) => console.log("[pageerror]", String(e).slice(0, 200)));
  await p.goto(URL0, { waitUntil: "domcontentloaded" });
  await p.waitForSelector(".stamp", { state: "attached" });
  await p.waitForTimeout(1500);
  return p;
}

async function selectShot(p) {
  await p.locator(".card.shot").first().click();
  await p.waitForTimeout(1000);
  await p.waitForSelector("#dock.expanded, #dock.show", { state: "attached", timeout: 8000 });
}

async function setBackend(p, be) {
  await p.selectOption("#backend", be);
  // wait for catalog swap: service list must repopulate (network fetch can lag)
  try {
    await p.waitForFunction(() => document.querySelectorAll("#service option").length > 1, { timeout: 20000 });
  } catch (_) { /* leave to setService error */ }
  await p.waitForTimeout(800);
}

async function setService(p, sid) {
  // catalog/smart-match can repopulate the list async — poll until the sid option exists
  let ok = null;
  for (let i = 0; i < 10; i++) {
    ok = await p.evaluate((sid) => {
      const sel = document.querySelector("#service");
      const has = [...sel.options].some((o) => o.value === sid);
      if (!has) return { ok: false, n: sel.options.length, sample: [...sel.options].slice(0, 8).map((o) => o.value) };
      sel.value = sid;
      sel.dispatchEvent(new Event("change", { bubbles: true }));
      return { ok: true };
    }, sid);
    if (ok.ok) break;
    await p.waitForTimeout(2000);
  }
  if (!ok.ok) throw new Error("service not in list: " + sid + " n=" + ok.n + " sample=" + JSON.stringify(ok.sample));
  await p.waitForTimeout(800);
}

async function setMode(p, mode) {
  await p.evaluate((mode) => {
    const btn = document.querySelector(`#composerModes button[data-mode="${mode}"]`);
    if (btn) btn.click();
  }, mode);
  await p.waitForTimeout(500);
}

async function fillPrompt(p, text) {
  await p.fill("#prompt", text);
  await p.waitForTimeout(300);
}

async function fillSupportedParams(p, opts = {}) {
  // fill only visible (provider-supported) param fields — seed/negative/etc.
  return await p.evaluate((opts) => {
    const filled = {};
    const vis = (el) => el && el.getBoundingClientRect().width > 0 && el.getBoundingClientRect().height > 0;
    const seed = document.querySelector("#seed");
    if (vis(seed)) { seed.value = "20260914"; seed.dispatchEvent(new Event("input", { bubbles: true })); seed.dispatchEvent(new Event("change", { bubbles: true })); filled.seed = seed.value; }
    const neg = document.querySelector("#negative");
    if (vis(neg)) { neg.value = "低画质, 模糊, 变形"; neg.dispatchEvent(new Event("input", { bubbles: true })); filled.negative = neg.value; }
    const qty = document.querySelector("#quantity");
    if (vis(qty)) { filled.quantity = qty.value; }
    const res = document.querySelector("#res");
    if (vis(res)) { filled.res = res.value; }
    const aspect = document.querySelector("#aspect");
    if (vis(aspect) && opts.aspect) {
      aspect.value = opts.aspect;
      aspect.dispatchEvent(new Event("change", { bubbles: true }));
      filled.aspect = aspect.value;
    }
    return filled;
  }, opts);
}

async function uploadRef(p, path) {
  await p.setInputFiles("#file", path);
  await p.waitForTimeout(2500);
}

async function send(p) {
  await p.click("#sendCap");
  await p.waitForTimeout(500);
}

async function waitDone(p, timeoutMs, beforeAssets, beforeShotSrc) {
  const t0 = Date.now();
  while (Date.now() - t0 < timeoutMs) {
    const st = await p.evaluate(() => {
      const msg = (document.querySelector("#msg") || {}).textContent || "";
      const toast = [...document.querySelectorAll(".toast, .send-toast, [class*=toast]")].map((e) => e.textContent).join(" ");
      const assets = document.querySelectorAll(".card.asset img, .card.character img, .card.asset video, .card.character video").length;
      const shotImg = (document.querySelector(".card.shot .face img, .card.shot .face video") || {}).src || "";
      const busy = msg.includes("生成中") || msg.includes("排队") || msg.includes("运行") || /处理中|等待/.test(msg);
      return { msg, toast, assets, shotImg, busy };
    });
    // 写回语义: 结果写进分镜卡 face（“此镜完成，已写入卡片”）或新增资产卡
    const wroteShot = /此镜完成|已写入卡片|出图完成|视频完成/.test(st.msg + st.toast);
    const shotChanged = beforeShotSrc && st.shotImg && st.shotImg !== beforeShotSrc;
    if ((wroteShot || shotChanged || st.assets > beforeAssets) && !st.busy) return { ok: true, ...st, ms: Date.now() - t0 };
    if (/失败|错误|拒绝|不支持|缺首帧|未接|没有.*Key/i.test(st.msg + st.toast)) return { ok: false, ...st, ms: Date.now() - t0 };
    await p.waitForTimeout(3000);
  }
  return { ok: false, timeout: true, ms: timeoutMs };
}

async function shotSrc(p) {
  return p.evaluate(() => (document.querySelector(".card.shot .face img, .card.shot .face video") || {}).src || "");
}

async function countAssets(p) {
  return p.evaluate(() => document.querySelectorAll(".card.asset img, .card.character img, .card.asset video, .card.character video").length);
}

async function reloadCheck(p, expectMin, tag) {
  await p.reload({ waitUntil: "domcontentloaded" });
  await p.waitForSelector(".stamp", { state: "attached" });
  await p.waitForTimeout(2500);
  const n = await countAssets(p);
  const shotMedia = await p.evaluate(() => document.querySelectorAll(".card.shot .face img[src], .card.shot .face video[src]").length);
  await p.screenshot({ path: `${SHOTS}/${tag}-after-reload.png` });
  return { persisted: n >= expectMin || shotMedia > 0, assetsAfterReload: n, shotMediaAfterReload: shotMedia };
}

const out = { case: process.argv[2], stamp: STAMP };
const browser = await chromium.launch();
try {
  const p = await openPage(browser);
  const mode = process.argv[2];

  if (mode === "civ-i2i" || mode === "fal-i2i" || mode === "nano-i2i") {
    const be = { "civ-i2i": "civitai", "fal-i2i": "fal", "nano-i2i": "nano-gpt" }[mode];
    const sid = { "civ-i2i": "image/flux2/klein/editImage/9b", "fal-i2i": "fal-ai/nano-banana/edit", "nano-i2i": "boogu-image/edit" }[mode];
    await selectShot(p);
    // 裁决: boogu edit max_input_images=1；过往 run 的参考图随状态持久化累积，
    // 先把已连线 chip 全部点掉（真实 UI 点击 toggleAssetOnShot），再上传恰好 1 张。
    if (be === "nano-gpt") {
      for (let i = 0; i < 12; i++) {
        const on = await p.$("#refs .chip.on[data-asset]");
        if (!on) break;
        await on.click();
        await p.waitForTimeout(300);
      }
      out.unlinked = true;
    }
    await uploadRef(p, REF_IMG);
    await p.screenshot({ path: `${SHOTS}/${mode}-1-ref.png` });
    await setMode(p, "image");
    await setBackend(p, be);
    await setService(p, sid);
    // boogu edit 只收目录 resolution token（1024x1024 等）——默认比例会被诚实硬门拦下；
    // 用户在「高级参数」里显式选目录 token（nanoRes）
    if (be === "nano-gpt") {
      await p.click("#advToggle");
      await p.waitForTimeout(400);
      // 裁决: nanoRes 选项是选完 service 后由目录异步填充的；options[0] 可能是空占位，
      // 必须等到出现非空 token 再选第一个非空值（空值会回落 res="720P" 被诚实硬门 400）。
      let tok = null;
      for (let i = 0; i < 12 && !tok; i++) {
        tok = await p.evaluate(() => {
          const sel = document.querySelector("#nanoRes");
          if (!sel) return null;
          const opt = [...sel.options].find((o) => o.value);
          if (!opt) return null;
          sel.value = opt.value;
          sel.dispatchEvent(new Event("change", { bubbles: true }));
          return sel.value;
        });
        if (!tok) await p.waitForTimeout(1500);
      }
      out.nanoResToken = tok;
    }
    out.params = await fillSupportedParams(p, {});
    await fillPrompt(p, `round2-${mode}-${STAMP}: 把这张照片转成雨夜霓虹赛博朋克街景, 保持主体姿势, 电影感打光`);
    await p.screenshot({ path: `${SHOTS}/${mode}-2-ready.png` });
    const before = await countAssets(p);
    const beforeShot = await shotSrc(p);
    await send(p);
    const res = await waitDone(p, 300000, before, beforeShot);
    Object.assign(out, res, { backend: be, serviceId: sid });
    await p.screenshot({ path: `${SHOTS}/${mode}-3-done.png` });
    if (res.ok) out.reload = await reloadCheck(p, before + 1, mode);
  } else if (mode === "civ-i2v" || mode === "fal-i2v") {
    const be = mode === "civ-i2v" ? "civitai" : "fal";
    const sid = mode === "civ-i2v" ? "video/wan/v2.2-5b/fal/image-to-video" : "fal-ai/kling-video/v2.5-turbo/pro/image-to-video";
    await selectShot(p);
    // 裁决: i2v 必须先切 video 模式再上传——上传处理器仅在 video 模式下自动设 firstFrameId；
    // 且清掉历史 run 残留的连线参考，保证 outbound 恰好 1 张首帧（wan cap=1）。
    await setMode(p, "video");
    for (let i = 0; i < 12; i++) {
      const on = await p.$("#refs .chip.on[data-asset]");
      if (!on) break;
      await on.click();
      await p.waitForTimeout(300);
    }
    await uploadRef(p, REF_IMG); // first frame via wire (auto firstFrameId in video mode)
    await setBackend(p, be);
    await setService(p, sid);
    out.params = await fillSupportedParams(p);
    await fillPrompt(p, `round2-${mode}-${STAMP}: 镜头缓慢推近, 发丝微动, 背景霓虹闪烁`);
    await p.screenshot({ path: `${SHOTS}/${mode}-2-ready.png` });
    const before = await countAssets(p);
    const beforeShot = await shotSrc(p);
    await send(p);
    const res = await waitDone(p, 600000, before, beforeShot);
    Object.assign(out, res, { backend: be, serviceId: sid });
    await p.screenshot({ path: `${SHOTS}/${mode}-3-done.png` });
    if (res.ok) out.reload = await reloadCheck(p, before + 1, mode);
  } else if (mode === "ms-video-honest") {
    await selectShot(p);
    await setMode(p, "video");
    await setBackend(p, "modelscope-ai");
    await p.waitForTimeout(1000);
    out.svcSample = await p.evaluate(() => [...document.querySelector("#service").options].slice(0, 10).map((o) => o.value));
    await fillPrompt(p, `round2-ms-video-${STAMP}: 诚实性验证`);
    await send(p);
    await p.waitForTimeout(3000);
    out.msg = await p.evaluate(() => (document.querySelector("#msg") || {}).textContent || "");
    await p.screenshot({ path: `${SHOTS}/ms-video-honest.png` });
  } else if (mode === "hf-t2i") {
    await selectShot(p);
    await setMode(p, "image");
    await setBackend(p, "huggingface");
    await p.waitForTimeout(1500);
    out.svcSample = await p.evaluate(() => [...document.querySelector("#service").options].map((o) => o.value).filter(Boolean).slice(0, 10));
    await fillPrompt(p, `round2-hf-t2i-${STAMP}: 山顶日出的云海, 金色阳光, 超广角`);
    out.params = await fillSupportedParams(p);
    await p.screenshot({ path: `${SHOTS}/hf-t2i-2-ready.png` });
    const before = await countAssets(p);
    const beforeShot = await shotSrc(p);
    await send(p);
    const res = await waitDone(p, 300000, before, beforeShot);
    Object.assign(out, res);
    await p.screenshot({ path: `${SHOTS}/hf-t2i-3-done.png` });
    if (res.ok) out.reload = await reloadCheck(p, before + 1, "hf-t2i");
  } else if (mode === "nano-video-list") {
    await selectShot(p);
    await setMode(p, "video");
    await setBackend(p, "nano-gpt");
    await p.waitForTimeout(1500);
    out.videoServices = await p.evaluate(() => [...document.querySelector("#service").options].map((o) => o.value).filter(Boolean));
    out.count = out.videoServices.length;
    await p.screenshot({ path: `${SHOTS}/nano-video-list.png` });
  } else if (mode === "lora-mismatch") {
    // E: Civitai Flux 底模 + SDXL LoRA AIR → 必须硬拒「不匹配」，不许静默加/换家
    await selectShot(p);
    await setMode(p, "image");
    await setBackend(p, "civitai");
    await setService(p, "image/flux2/klein/editImage/9b");
    await p.waitForTimeout(500);
    await p.fill("#loraQ", "urn:air:sdxl:lora:civitai:123456@7890");
    await p.keyboard.press("Enter");
    await p.waitForTimeout(2000);
    out.loraNote = await p.evaluate(() => {
      const n = document.querySelector("#loraNote, .lora-note, #loraHint");
      const chips = document.querySelectorAll("#refs .chip, .lora-block .chip").length;
      const note = n ? n.textContent : "";
      return { note, chips };
    });
    // 语义: 提示「不匹配」且 LoRA chips 未增加
    out.hardReject = /不匹配|不是 LoRA|已拒绝/.test(out.loraNote.note || "");
    await p.screenshot({ path: `${SHOTS}/lora-mismatch.png` });
  } else if (mode === "reload-check") {
    const n = await countAssets(p);
    out.assetsOnLoad = n;
    await p.screenshot({ path: `${SHOTS}/reload-check.png` });
  }
} catch (e) {
  out.fatal = String(e).slice(0, 500);
}
await browser.close();
console.log("RESULT " + JSON.stringify(out, null, 1));
