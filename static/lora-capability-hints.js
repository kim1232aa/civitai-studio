/*! v0821o57-six-lora-hints
 * Per-backend LoRA rematch hints. Official API is the iron rule:
 * never NANO.concat(FAL) for Civitai / HF / 魔搭.
 * IDs only from that vendor catalog / inventory.
 * HF: Hub mids only, never fal-ai/*lora; confidence=unverified.
 * Nano *-lora list is heuristic (not official supported_parameters.loras).
 */
(function (root) {
  "use strict";

  const STAMP = "v0821o57-six-lora-hints";

  const LORA_HINTS_BY_BACKEND = {
    "nano-gpt": [
      "flux-lora",
      "flux-2-dev-lora",
      "z-image-turbo-lora",
      "wavespeed-ai/krea-v2/turbo-lora"
    ],
    fal: [
      "fal-ai/flux-lora",
      "fal-ai/flux-lora/image-to-image",
      "fal-ai/krea-2/turbo/lora",
      "fal-ai/flux-2/lora"
    ],
    civitai: [
      "image/comfy/krea2/turbo/createImage"
    ],
    huggingface: [
      "black-forest-labs/FLUX.1-dev",
      "black-forest-labs/FLUX.1-schnell",
      "black-forest-labs/FLUX.1-Krea-dev"
    ],
    "modelscope-ai": [
      "Tongyi-MAI/Z-Image-Turbo",
      "krea/Krea-2-Turbo",
      "Qwen/Qwen-Image"
    ],
    "modelscope-cn": [
      "Tongyi-MAI/Z-Image-Turbo",
      "krea/Krea-2-Turbo",
      "Qwen/Qwen-Image"
    ]
  };

  const LORA_SHAPE_BY_BACKEND = {
    civitai: "air",
    fal: "path",
    huggingface: "path",
    "modelscope-ai": "hub_repo",
    "modelscope-cn": "hub_repo",
    "nano-gpt": "path"
  };

  const LORA_CONFIDENCE_BY_BACKEND = {
    civitai: "official",
    fal: "official",
    huggingface: "unverified",
    "modelscope-ai": "official",
    "modelscope-cn": "official",
    "nano-gpt": "heuristic"
  };

  function hintsFor(backend) {
    const be = String(backend || "").trim();
    if (!be) return [];
    return (LORA_HINTS_BY_BACKEND[be] || []).slice();
  }

  function isForbiddenCrossHint(backend, id) {
    const be = String(backend || "");
    const s = String(id || "");
    if (!s) return false;
    if (be === "huggingface" && /^fal-ai\//.test(s)) return true;
    if ((be === "modelscope-ai" || be === "modelscope-cn") && (/^fal-ai\//.test(s) || s === "flux-lora" || s.indexOf("flux-2-dev-lora") >= 0)) return true;
    if (be === "civitai" && (/^fal-ai\//.test(s) || s === "flux-lora" || s === "z-image-turbo-lora")) return true;
    return false;
  }

  function pickHintFromPool(backend, pool) {
    const hints = hintsFor(backend);
    const items = Array.isArray(pool) ? pool : [];
    const byId = {};
    items.forEach(function (it) {
      if (it && it.id) byId[String(it.id)] = it;
    });
    for (let i = 0; i < hints.length; i++) {
      const id = hints[i];
      if (isForbiddenCrossHint(backend, id)) continue;
      const hit = byId[id];
      if (!hit) continue;
      if (hit.supportsLora === false) continue;
      return hit.id;
    }
    return "";
  }

  function loraBoxState(ctx) {
    ctx = ctx || {};
    const be = String(ctx.backend || "");
    const item = ctx.item || {};
    const caps = (item.capabilities && typeof item.capabilities === "object") ? item.capabilities : {};
    let supports = caps.supportsLora;
    if (supports == null && item.supportsLora != null) supports = item.supportsLora;
    const confidence = caps.loraConfidence || LORA_CONFIDENCE_BY_BACKEND[be] || "unknown";
    const channel = String(caps.loraChannel || ctx.loraChannel || "");
    const shape = caps.loraShape || LORA_SHAPE_BY_BACKEND[be] || "unknown";

    if (be === "huggingface" && channel && channel !== "fal") {
      return {
        support: "unsupported",
        reason: "本通道未接入 LoRA",
        confidence: "none",
        shape: shape,
        showBox: true,
        enabled: false
      };
    }
    if (supports === true) {
      const unverified = confidence === "unverified" || confidence === "heuristic";
      return {
        support: "supported",
        reason: confidence === "unverified"
          ? "发出≠加载 / 无官方 /lora sibling"
          : (confidence === "heuristic" ? "supportsLora 为 *-lora 启发式，非官方字段" : ""),
        confidence: confidence,
        shape: shape,
        showBox: true,
        enabled: true,
        badge: unverified ? "unverified" : ""
      };
    }
    if (supports === false) {
      return {
        support: "unsupported",
        reason: "本模型官方不接 LoRA",
        confidence: "none",
        shape: shape,
        showBox: true,
        enabled: false
      };
    }
    return {
      support: "unknown",
      reason: "未确认",
      confidence: "unknown",
      shape: shape,
      showBox: true,
      enabled: true
    };
  }

  root.LoraCapabilityHints = {
    STAMP: STAMP,
    LORA_HINTS_BY_BACKEND: LORA_HINTS_BY_BACKEND,
    LORA_SHAPE_BY_BACKEND: LORA_SHAPE_BY_BACKEND,
    LORA_CONFIDENCE_BY_BACKEND: LORA_CONFIDENCE_BY_BACKEND,
    hintsFor: hintsFor,
    pickHintFromPool: pickHintFromPool,
    isForbiddenCrossHint: isForbiddenCrossHint,
    loraBoxState: loraBoxState
  };
})(typeof window !== "undefined" ? window : globalThis);
