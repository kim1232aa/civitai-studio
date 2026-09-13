/* smart-family-match.js
 * Civitai 帖智能匹配：按当前家 + 底模家族选模型。
 * 对不上就空着并说明，不许跨家，不许用 Krea2 顶 SDXL/Pony/Flux。
 */
(function (root) {
  "use strict";

  function inferModelFamily(text) {
    const s = String(text || "").toLowerCase();
    if (!s) return "";
    if (/pony/.test(s)) return "pony";
    if (/sdxl|xl[-_ ]?base|juggernaut|realvisxl|dreamshaper.?xl|ponyxl/.test(s)) return "sdxl";
    if (/\bsd-?1[.-]?5\b|\bv1-5\b|\bv1_5\b|anything.?v3|dreamshaper(?!.*xl)/.test(s)) return "sd15";
    if (/krea\s*2|krea2|krea-2|krea_2|\/krea\/|comfy\/krea/.test(s)) return "krea2";
    if (/klein/.test(s)) return "klein";
    if (/z-?image|zimage/.test(s)) return "zimage";
    if (/qwen/.test(s)) return "qwen";
    if (/hunyuan|hy[-_\s]?video/.test(s)) return "hunyuan";
    if (/wan2|\/wan\/|wan-ai|wan_ai|wan\s*2/.test(s)) return "wan";
    if (/flux[\s._-]*2|flux2/.test(s)) return "flux2";
    if (/flux/.test(s)) return "flux";
    if (/minimax|hailuo/.test(s)) return "minimax";
    if (/kling/.test(s)) return "kling";
    if (/ltx/.test(s)) return "ltx";
    if (/sd\s*3|sd3|stable[- ]diffusion[- ]3/.test(s)) return "sd3";
    return "";
  }

  function familyFromAir(air) {
    const raw = String(air || "");
    const m = raw.match(/urn:air:([^:]+):/i);
    if (m) {
      const eco = inferModelFamily(m[1]) || inferModelFamily(raw);
      if (eco) return eco;
    }
    return inferModelFamily(raw);
  }

  function familyFromShot(shot, extra) {
    const parts = [];
    if (extra) parts.push(extra);
    if (!shot) return inferModelFamily(parts.join(" "));
    ["ecosystem", "checkpointName", "diffusionModel", "serviceId", "service", "model"].forEach(function (k) {
      if (shot[k]) parts.push(shot[k]);
    });
    if (shot.composer) {
      if (shot.composer.service) parts.push(shot.composer.service);
      if (shot.composer.ecosystem) parts.push(shot.composer.ecosystem);
    }
    const joined = parts.join(" ");
    let fam = inferModelFamily(joined);
    if (!fam && shot.diffusionModel) fam = familyFromAir(shot.diffusionModel);
    if (!fam && Array.isArray(shot.loras) && shot.loras[0] && shot.loras[0].air) {
      fam = familyFromAir(shot.loras[0].air);
    }
    return fam;
  }

  function familyFromImport(j) {
    j = j || {};
    const parts = [j.serviceId, j.serviceName, j.model, j.checkpointName, j.ecosystem, j.diffusionModel];
    let fam = inferModelFamily(parts.filter(Boolean).join(" "));
    if (!fam && j.diffusionModel) fam = familyFromAir(j.diffusionModel);
    if (!fam && Array.isArray(j.loras)) {
      for (let i = 0; i < j.loras.length; i++) {
        fam = familyFromAir((j.loras[i] && (j.loras[i].air || j.loras[i].name)) || "");
        if (fam) break;
      }
    }
    return fam;
  }

  function itemFamily(it) {
    if (!it) return "";
    return inferModelFamily([it.id, it.name, it.ecosystem, it.baseModel, it.task].filter(Boolean).join(" "));
  }

  function familyCompatible(want, got) {
    if (!want) return true;
    if (!got) return false;
    if (want === got) return true;
    if ((want === "flux" && got === "flux2") || (want === "flux2" && got === "flux")) return true;
    if ((want === "sdxl" && got === "pony") || (want === "pony" && got === "sdxl")) return true;
    return false;
  }

  const HOUSE_FAMILY_PREF = {
    civitai: {
      krea2: { t2i: "image/comfy/krea2/turbo/createImage", i2i: "image/comfy/krea2/edit/editImage", i2v: "" },
      flux: { t2i: "image/sdcpp/flux1/createImage", i2i: "image/sdcpp/flux1/createImage", i2v: "" },
      flux2: { t2i: "image/flux2/klein/createImage/9b", i2i: "image/flux2/klein/editImage/9b", i2v: "" },
      sdxl: { t2i: "image/sdcpp/sdxl/createImage", i2i: "image/sdcpp/sdxl/createVariant", i2v: "" },
      zimage: { t2i: "image/sdcpp/zImage/turbo/createImage", i2i: "image/sdcpp/zImage/turbo/createVariant", i2v: "" },
      wan: { t2i: "", i2i: "image/wan/v2.7/fal/editImage", i2v: "video/wan/v2.2/fal/image-to-video" },
      minimax: { t2i: "", i2i: "", i2v: "video/minimax-h3-comfy/imageToVideo" },
      ltx: { t2i: "", i2i: "", i2v: "video/ltx2.3/firstLastFrameToVideo" }
    },
    fal: {
      krea2: { t2i: "fal-ai/krea-2/turbo", i2i: "fal-ai/krea-2/image-to-image", i2v: "" },
      flux: { t2i: "fal-ai/flux/schnell", i2i: "fal-ai/flux-pro/kontext", i2v: "" },
      flux2: { t2i: "fal-ai/flux-2/flash", i2i: "fal-ai/flux-2/edit", i2v: "" },
      zimage: { t2i: "fal-ai/z-image/turbo", i2i: "fal-ai/z-image/turbo/image-to-image", i2v: "" },
      wan: { t2i: "", i2i: "", i2v: "fal-ai/wan-25-preview/image-to-video" },
      minimax: { t2i: "", i2i: "", i2v: "fal-ai/minimax/video-01/image-to-video" },
      kling: { t2i: "", i2i: "", i2v: "fal-ai/kling-video/v3/pro/image-to-video" },
      sdxl: { t2i: "", i2i: "", i2v: "" },
      pony: { t2i: "", i2i: "", i2v: "" }
    },
    huggingface: {
      krea2: { t2i: "krea/Krea-2-Turbo", i2i: "", i2v: "" },
      flux: { t2i: "black-forest-labs/FLUX.1-schnell", i2i: "", i2v: "" },
      qwen: { t2i: "", i2i: "Qwen/Qwen-Image-Edit", i2v: "" },
      wan: { t2i: "", i2i: "", i2v: "Wan-AI/Wan2.2-TI2V-5B" },
      sdxl: { t2i: "", i2i: "", i2v: "" }
    },
    "modelscope-ai": {
      krea2: { t2i: "krea/Krea-2-Turbo", i2i: "", i2v: "" },
      zimage: { t2i: "Tongyi-MAI/Z-Image-Turbo", i2i: "", i2v: "" },
      qwen: { t2i: "", i2i: "Qwen/Qwen-Image-Edit", i2v: "" },
      wan: { t2i: "", i2i: "", i2v: "Wan-AI/Wan2.1-I2V-14B-720P" },
      sdxl: { t2i: "", i2i: "", i2v: "" }
    },
    "modelscope-cn": {
      krea2: { t2i: "krea/Krea-2-Turbo", i2i: "", i2v: "" },
      zimage: { t2i: "Tongyi-MAI/Z-Image-Turbo", i2i: "", i2v: "" },
      qwen: { t2i: "", i2i: "Qwen/Qwen-Image-Edit", i2v: "" },
      wan: { t2i: "", i2i: "", i2v: "Wan-AI/Wan2.1-I2V-14B-720P" },
      sdxl: { t2i: "", i2i: "", i2v: "" }
    },
    "nano-gpt": {
      krea2: { t2i: "wavespeed-ai/krea-v2/turbo-lora", i2i: "", i2v: "" },
      zimage: { t2i: "z-image-turbo", i2i: "z-image-turbo-image-to-image", i2v: "" },
      flux: { t2i: "", i2i: "", i2v: "" },
      sdxl: { t2i: "", i2i: "", i2v: "" },
      minimax: { t2i: "", i2i: "", i2v: "minimax/h3-max/multi-angle/image-to-video" }
    }
  };

  function preferredId(be, fam, op) {
    const house = HOUSE_FAMILY_PREF[be] || {};
    const row = house[fam] || {};
    return String(row[op] || "").trim();
  }

  function pickByFamily(opts) {
    opts = opts || {};
    const be = String(opts.backend || "").trim();
    const op = opts.op || "t2i";
    const fam = String(opts.family || "").trim();
    const pool = Array.isArray(opts.pool) ? opts.pool : [];
    const fits = typeof opts.fits === "function" ? opts.fits : function () { return true; };
    const belongs = typeof opts.belongs === "function" ? opts.belongs : function () { return true; };

    function ok(id, it) {
      if (!id || !belongs(id, be)) return false;
      if (it && !fits(it, op)) return false;
      if (fam && it && !familyCompatible(fam, itemFamily(it) || inferModelFamily(id))) return false;
      if (fam && !it && !familyCompatible(fam, inferModelFamily(id))) return false;
      return true;
    }

    const pref = preferredId(be, fam, op);
    if (pref) {
      const hit = pool.filter(function (r) { return String(r.id || r.name || "") === pref; })[0];
      if (ok(pref, hit || { id: pref, name: pref })) return pref;
      if (!pool.length && familyCompatible(fam, inferModelFamily(pref))) return pref;
    }
    for (let i = 0; i < pool.length; i++) {
      const it = pool[i];
      const id = String(it.id || it.name || "").trim();
      if (ok(id, it)) return id;
    }
    if (fam) return "";
    return String(opts.fallback || "").trim();
  }

  function keepCurrent(opts) {
    opts = opts || {};
    const curId = String(opts.currentId || "").trim();
    if (!curId) return false;
    if (opts.foreign) return false;
    const it = opts.item;
    const op = opts.op || "t2i";
    const fits = typeof opts.fits === "function" ? opts.fits : function () { return true; };
    if (it && !fits(it, op)) return false;
    const fam = String(opts.family || "").trim();
    if (!fam) return !!(it && fits(it, op));
    const got = (it && itemFamily(it)) || inferModelFamily(curId);
    return familyCompatible(fam, got);
  }

  const api = {
    inferModelFamily: inferModelFamily,
    familyFromAir: familyFromAir,
    familyFromShot: familyFromShot,
    familyFromImport: familyFromImport,
    itemFamily: itemFamily,
    familyCompatible: familyCompatible,
    preferredId: preferredId,
    pickByFamily: pickByFamily,
    keepCurrent: keepCurrent,
    HOUSE_FAMILY_PREF: HOUSE_FAMILY_PREF
  };
  root.SmartFamilyMatch = api;
  if (typeof module !== "undefined" && module.exports) module.exports = api;
})(typeof window !== "undefined" ? window : globalThis);
