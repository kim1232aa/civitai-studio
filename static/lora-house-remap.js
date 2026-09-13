/* lora-house-remap.js
 * Import / switch-house: rewrite LoRA chips to the current house API shape.
 * Civitai = AIR. Fal/Nano = http path. ModelScope = Hub owner/repo.
 * HF = path if any, mark unverified. Never invent strength. Never silent-drop chips.
 */
(function (root) {
  "use strict";

  function isAir(s) {
    return /^urn:air:/i.test(String(s || ""));
  }
  function isHttp(s) {
    return /^https?:\/\//i.test(String(s || ""));
  }
  function isHubRepo(s) {
    const t = String(s || "").trim();
    if (!t || isAir(t) || isHttp(t)) return false;
    return /^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/.test(t);
  }
  function versionIdOf(row) {
    if (!row) return "";
    if (row.versionId) return String(row.versionId);
    if (row.modelVersionId) return String(row.modelVersionId);
    const m = String(row.air || "").match(/@(\d+)/);
    return m ? m[1] : "";
  }
  function modelIdOf(row) {
    if (!row) return "";
    if (row.modelId) return String(row.modelId);
    const m = String(row.air || "").match(/:civitai:(\d+)@/i);
    return m ? m[1] : "";
  }
  function ecoOf(row, family) {
    const m = String((row && row.air) || "").match(/urn:air:([^:]+):/i);
    if (m) return m[1];
    return String(family || "sdxl");
  }
  function downloadUrl(vid) {
    return vid ? ("https://civitai.com/api/download/models/" + vid) : "";
  }
  function keepStrength(row) {
    if (!row) return null;
    if (Object.prototype.hasOwnProperty.call(row, "strength")) return row.strength;
    if (Object.prototype.hasOwnProperty.call(row, "scale")) return row.scale;
    return null;
  }

  function remapRow(backend, row, family) {
    row = row || {};
    const be = String(backend || "").trim();
    const air = String(row.air || "");
    const rawPath = String(row.path || row.url || row.downloadUrl || "");
    const strength = keepStrength(row);
    const vid = versionIdOf(row);
    const mid = modelIdOf(row);
    const out = {
      name: row.name || "",
      air: air,
      path: rawPath,
      url: row.url || "",
      downloadUrl: row.downloadUrl || "",
      versionId: vid,
      modelId: mid,
      strength: strength,
      scale: strength,
      outbound: false,
      canOutbound: false,
      chipReason: "",
      shape: ""
    };

    if (be === "civitai") {
      out.shape = "air";
      if (isAir(air)) {
        out.outbound = true;
        out.chipReason = "Civitai AIR 可出站";
      } else if (vid && mid) {
        out.air = "urn:air:" + ecoOf(row, family) + ":lora:civitai:" + mid + "@" + vid;
        out.outbound = true;
        out.chipReason = "已补 AIR";
      } else {
        out.chipReason = "缺 AIR，Civitai 出不了这张 LoRA";
      }
      out.canOutbound = !!out.outbound;
      out.status = out.chipReason || "";
      return out;
    }

    if (be === "fal" || be === "nano-gpt") {
      out.shape = "path";
      let p = rawPath;
      if (isAir(p)) p = "";
      if (!isHttp(p) && vid) p = downloadUrl(vid);
      if (isHttp(p)) {
        out.path = p;
        out.url = p;
        if (p.indexOf("civitai.com/api/download") >= 0) out.downloadUrl = p;
        out.outbound = true;
        out.chipReason = be === "fal" ? "直链 URL 可出站" : "已转成可下载路径";
      } else {
        out.path = "";
        out.outbound = false;
        out.chipReason = isAir(air)
          ? "这家 LoRA 要直链 URL，当前是 Civitai AIR"
          : "没有可下载的 LoRA 地址";
      }
      out.canOutbound = !!out.outbound;
      out.status = out.chipReason || "";
      return out;
    }

    if (be === "huggingface") {
      out.shape = "path";
      let p = isHttp(rawPath) ? rawPath : (vid ? downloadUrl(vid) : "");
      if (isHubRepo(rawPath)) p = rawPath;
      if (isHttp(p) || isHubRepo(p)) {
        out.path = p;
        out.outbound = true;
        out.chipReason = "HF 通道 LoRA 未官方确认，发出≠加载";
      } else {
        out.path = "";
        out.outbound = false;
        out.chipReason = "HF 官方多数端点没有 LoRA 键，请换模型或换家";
      }
      out.canOutbound = !!out.outbound;
      out.status = out.chipReason || "";
      return out;
    }

    if (be === "modelscope-ai" || be === "modelscope-cn") {
      out.shape = "hub_repo";
      let cand = "";
      if (isHubRepo(rawPath)) cand = rawPath;
      else if (isHubRepo(row.name)) cand = String(row.name).trim();
      if (cand) {
        out.path = cand;
        out.outbound = true;
        out.chipReason = "Hub owner/repo 可出站";
      } else {
        out.path = "";
        out.outbound = false;
        out.chipReason = "魔搭只要 Hub owner/repo，请搜本家 LoRA，不能用 Civitai 下载链";
      }
      out.canOutbound = !!out.outbound;
      out.status = out.chipReason || "";
      return out;
    }

    out.chipReason = "未知供应商";
    out.canOutbound = false;
    out.status = out.chipReason;
    return out;
  }

  function remapLorasForHouse(backend, loras, family) {
    const list = Array.isArray(loras) ? loras : [];
    return list.map(function (row) {
      const mapped = remapRow(backend, row, family);
      return Object.assign({}, row, mapped);
    });
  }

  // Test/inspect helper only. Generate path must not use this to drop chips.
  function packOutbound(backend, loras, family) {
    return remapLorasForHouse(backend, loras, family).filter(function (r) { return r.outbound; });
  }

  const api = {
    isAir: isAir,
    looksAir: isAir,
    isHttp: isHttp,
    isHttpUrl: isHttp,
    isHubRepo: isHubRepo,
    versionIdOf: versionIdOf,
    versionId: versionIdOf,
    modelId: modelIdOf,
    downloadUrl: downloadUrl,
    remapRow: remapRow,
    remapOne: remapRow,
    remapLorasForHouse: remapLorasForHouse,
    packOutbound: packOutbound
  };
  root.LoraHouseRemap = api;
  if (typeof module !== "undefined" && module.exports) module.exports = api;
})(typeof window !== "undefined" ? window : globalThis);
