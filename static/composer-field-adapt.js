/*! v0821o47-composer-board-sync
 * Continues o28. Board sync: Magao maxRefs ceiling 3; seed int32 clamp hint.
 * Composer field adapt from docs/api-usage/composer-field-board.md §硬规则 1–6.
 * unsupported/none → disable + plain「不支持」(never hide as-complete).
 * strength/scale null →「未填」; never invent 0.8/1.0.
 * Live caps from GET /api/providers + catalog may only tighten.
 * Parallel-safe: Composer field visibility only (Fal endpoint pin owned by o29).
 * o30: filled unsupported (sampler/…) warn-only — hard-block only i2v unsupported.
 */
(function (root) {
  "use strict";

  const STAMP = "v0821o47-composer-board-sync";
  const BOARD_SRC = "docs/api-usage/composer-field-board.md";

  // Values: supported | catalog | unsupported | unknown
  // Aligned to authoritative board (not skeleton).
  const COMPOSER_FIELD_BOARD = {
    _meta: { source: BOARD_SRC, status: "board", stamp: STAMP },
    civitai: {
      negative: "supported", seed: "supported",
      width: "supported", height: "supported",
      steps: "supported", cfg: "supported",
      sampler: "supported", scheduler: "supported",
      duration: "supported", aspect: "supported", res: "supported",
      nanoRes: "unsupported",
      resolutionMode: "free_wh", lora: "air",
      i2v: "supported", progress: "supported", cancel: "supported"
    },
    fal: {
      negative: "catalog", seed: "supported",
      width: "supported", height: "supported",
      steps: "catalog", cfg: "catalog",
      sampler: "unsupported", scheduler: "catalog",
      duration: "supported", aspect: "supported", res: "supported",
      nanoRes: "unsupported",
      resolutionMode: "free_wh", lora: "path",
      i2v: "supported", progress: "supported", cancel: "supported"
    },
    huggingface: {
      negative: "catalog", seed: "supported",
      width: "supported", height: "supported",
      steps: "catalog", cfg: "catalog",
      sampler: "unsupported", scheduler: "catalog",
      duration: "unsupported", aspect: "unsupported", res: "unsupported",
      nanoRes: "unsupported",
      resolutionMode: "free_wh", lora: "path",
      loraConfidence: "unverified",
      i2v: "unsupported", progress: "unsupported", cancel: "unsupported"
    },
    "modelscope-ai": {
      negative: "supported", seed: "supported",
      width: "supported", height: "supported",
      steps: "supported", cfg: "supported",
      sampler: "unsupported", scheduler: "unsupported",
      duration: "unsupported", aspect: "supported", res: "unsupported",
      nanoRes: "unsupported",
      resolutionMode: "free_wh", lora: "hub_repo",
      i2v: "supported", progress: "catalog", cancel: "unsupported"
    },
    "modelscope-cn": {
      negative: "supported", seed: "supported",
      width: "supported", height: "supported",
      steps: "supported", cfg: "supported",
      sampler: "unsupported", scheduler: "unsupported",
      duration: "unsupported", aspect: "supported", res: "unsupported",
      nanoRes: "unsupported",
      resolutionMode: "free_wh", lora: "hub_repo",
      i2v: "supported", progress: "catalog", cancel: "unsupported"
    },
    "nano-gpt": {
      negative: "supported", seed: "supported",
      width: "unsupported", height: "unsupported",
      steps: "supported", cfg: "supported",
      sampler: "unsupported", scheduler: "unsupported",
      duration: "catalog", aspect: "supported", res: "unsupported",
      nanoRes: "supported",
      resolutionMode: "catalog_token", lora: "path",
      i2v: "supported", progress: "unsupported", cancel: "unsupported"
    }
  };

  const FIELD_SUPPORT_REASONS = {
    supported: "",
    catalog: "视模型 schema · 无对应字段则出站省略（不发明默认）",
    unsupported: "本家不支持 · 出站不会带上（不静默改值）",
    unknown: "field board 未确认 · 不发明默认"
  };

  const LORA_SHAPE_HINT = {
    air: "形态 air+strength · null→未填（不发明）",
    path: "形态 path/downloadUrl+scale · null→未填（不发明）",
    hub_repo: "形态 Hub owner/repo · 单条无 weight 出站字符串",
    none: "本家 LoRA 不支持",
    unknown: "LoRA 形态未确认"
  };

  const LABEL_BASE = {
    width: "宽", height: "高", steps: "步数", cfg: "CFG",
    sampler: "采样器", scheduler: "调度器", seed: "种子",
    duration: "时长", aspect: "比例", res: "分辨率", nanoRes: "分辨率",
    negative: "负面提示"
  };

  function fieldBoardFor(be) {
    const id = String(be || "").trim();
    if (COMPOSER_FIELD_BOARD[id]) return COMPOSER_FIELD_BOARD[id];
    return {
      negative: "unknown", seed: "unknown",
      width: "unknown", height: "unknown",
      steps: "unknown", cfg: "unknown",
      sampler: "unknown", scheduler: "unknown",
      duration: "unknown", aspect: "unknown", res: "unknown",
      nanoRes: "unknown",
      resolutionMode: "unknown", lora: "unknown",
      i2v: "unknown", progress: "unknown", cancel: "unknown"
    };
  }

  function tighten(support, next) {
    const rank = { unsupported: 0, unknown: 1, catalog: 2, supported: 3 };
    const a = rank[support] != null ? rank[support] : 1;
    const b = rank[next] != null ? rank[next] : 1;
    return b < a ? next : support;
  }

  /** Live caps may only tighten (supported→catalog/unsupported). */
  function resolveFieldSupport(field, ctx) {
    ctx = ctx || {};
    const be = ctx.backend || "";
    const board = fieldBoardFor(be);
    let support = board[field] || "unknown";
    const caps = ctx.caps || {};

    if (field === "negative" && caps.negative === false) support = tighten(support, "unsupported");
    if (field === "sampler") {
      if (caps.sampler === false) support = tighten(support, "unsupported");
      // civitai board already supported; catalog true cannot raise unsupported→supported for other houses
      if (caps.sampler === true && be === "civitai") support = "supported";
    }
    if (field === "duration" && caps.videoDuration === false) support = tighten(support, "unsupported");
    if (field === "aspect" && caps.videoAspect === false && ctx.mode === "video") {
      support = tighten(support, "unsupported");
    }
    if ((field === "width" || field === "height") &&
        (caps.resolution === "catalog_token" || board.resolutionMode === "catalog_token")) {
      support = tighten(support, "unsupported");
    }
    if (field === "nanoRes" &&
        (caps.resolution === "catalog_token" || board.resolutionMode === "catalog_token")) {
      support = "supported";
    }
    if (field === "i2v" && (caps.i2v === "none" || board.i2v === "unsupported")) {
      support = "unsupported";
    }
    if (field === "progress" && (caps.progress === "none" || board.progress === "unsupported")) {
      support = "unsupported";
    }
    if (field === "cancel" && (caps.cancel === false || board.cancel === "unsupported")) {
      support = "unsupported";
    }
    return support;
  }

  function wrapFor(el) {
    if (!el) return null;
    return (el.closest && el.closest(".param-field")) || el.parentElement || el;
  }

  function setLabelBadge(wrap, field, support) {
    if (!wrap || !wrap.querySelector) return;
    const span = wrap.querySelector(":scope > span");
    if (!span) return;
    const base = LABEL_BASE[field] || (span.getAttribute("data-label-base") || span.textContent.replace(/\s*·\s*不支持.*$/, "").trim() || field);
    span.setAttribute("data-label-base", base);
    if (support === "unsupported") span.textContent = base + " · 不支持";
    else if (support === "catalog") span.textContent = base + " · schema";
    else if (support === "unknown") span.textContent = base + " · 未确认";
    else span.textContent = base;
  }

  /**
   * modeHide: mode-conditional hide (e.g. duration when not video) — OK to hide.
   * unsupported: NEVER hide as-complete — disable + plain「不支持」.
   */
  function applyFieldSupport(el, field, modeHide, ctx) {
    if (!el) return;
    const wrap = wrapFor(el);
    const support = resolveFieldSupport(field, ctx);
    const reason = FIELD_SUPPORT_REASONS[support] || FIELD_SUPPORT_REASONS.unknown;

    if (modeHide) {
      el.classList.add("hidden");
      el.disabled = true;
      el.setAttribute("aria-disabled", "true");
      if (wrap && wrap.classList) {
        wrap.classList.remove("param-unsupported", "param-unknown", "param-catalog");
        wrap.classList.add("param-mode-hide");
      }
      return;
    }

    el.classList.remove("hidden");
    if (wrap && wrap.classList) wrap.classList.remove("param-mode-hide");
    setLabelBadge(wrap, field, support);

    if (support === "supported") {
      el.disabled = false;
      el.removeAttribute("aria-disabled");
      if (wrap && wrap.classList) wrap.classList.remove("param-unsupported", "param-unknown", "param-catalog");
      if (reason) el.title = reason;
      else if (field === "width") el.title = "宽";
      else if (field === "height") el.title = "高";
      else if (!el.title || /本家不支持|field board|视模型|不支持/.test(String(el.title))) el.title = "";
    } else if (support === "catalog") {
      el.disabled = false;
      el.removeAttribute("aria-disabled");
      if (wrap && wrap.classList) {
        wrap.classList.add("param-catalog");
        wrap.classList.remove("param-unsupported", "param-unknown");
      }
      el.title = reason;
    } else if (support === "unsupported") {
      el.disabled = true;
      el.setAttribute("aria-disabled", "true");
      if (wrap && wrap.classList) {
        wrap.classList.add("param-unsupported");
        wrap.classList.remove("param-unknown", "param-catalog");
      }
      el.title = reason;
    } else {
      el.disabled = false;
      el.removeAttribute("aria-disabled");
      if (wrap && wrap.classList) {
        wrap.classList.add("param-unknown");
        wrap.classList.remove("param-unsupported", "param-catalog");
      }
      el.title = reason;
    }
  }

  function applyNegative(el, ctx) {
    if (!el) return;
    const support = resolveFieldSupport("negative", ctx);
    const reason = FIELD_SUPPORT_REASONS[support] || FIELD_SUPPORT_REASONS.unknown;
    // Keep visible always — hard rule 2: 禁止藏掉当已齐
    el.classList.remove("hidden");
    el.classList.toggle("param-unsupported-control", support === "unsupported");
    if (support === "unsupported") {
      el.disabled = true;
      el.setAttribute("aria-disabled", "true");
      el.title = reason;
      el.placeholder = "不支持 · 本家出站不会带负面提示";
    } else {
      el.disabled = false;
      el.removeAttribute("aria-disabled");
      el.title = support === "catalog" ? reason : (support === "unknown" ? reason : "");
      if (/不支持/.test(String(el.placeholder || ""))) {
        el.placeholder = "负面提示（不想出现的内容，可空）";
      }
    }
  }

  function fieldSupportStripText(ctx) {
    const be = (ctx && ctx.backend) || "?";
    const meta = COMPOSER_FIELD_BOARD._meta || {};
    const board = fieldBoardFor(be);
    const bits = [];
    bits.push(meta.stamp || STAMP);
    bits.push(be);
    if (board.resolutionMode && board.resolutionMode !== "unknown") bits.push("分辨率=" + board.resolutionMode);
    if (board.lora && board.lora !== "unknown") {
      let loraBit = "LoRA=" + board.lora;
      if (board.loraConfidence === "unverified") loraBit += "(unverified)";
      bits.push(loraBit);
    }
    const caps = (ctx && ctx.caps) || {};
    const mr = Number(caps.maxRefs || caps.maxImages || 0);
    if (mr > 0) bits.push("maxRefs=" + mr);
    const unsupported = ["sampler", "scheduler", "steps", "cfg", "width", "height", "nanoRes", "i2v"]
      .filter(function (f) { return resolveFieldSupport(f, ctx) === "unsupported"; });
    if (unsupported.length) bits.push("不支持:" + unsupported.join("/"));
    return bits.join(" · ");
  }

  function syncParamSupportStrip(ctx) {
    const $ = ctx && ctx.$;
    if (!$) return;
    const el = $("paramSupportStrip");
    if (!el) return;
    el.textContent = fieldSupportStripText(ctx);
    el.hidden = false;
  }

  function loraShape(be) {
    const board = fieldBoardFor(be);
    return board.lora || "unknown";
  }

  function loraShapeHintText(be) {
    const board = fieldBoardFor(be);
    const shape = board.lora || "unknown";
    let t = LORA_SHAPE_HINT[shape] || LORA_SHAPE_HINT.unknown;
    if (board.loraConfidence === "unverified") t += " · unverified（发出≠加载）";
    return t;
  }

  function strengthPlaceholder() {
    return "未填";
  }

  function strengthTitle() {
    return "strength 未填：出站省略数值（不写 1.0/0.8）";
  }

  /**
   * Warn-only: filled unsupported fields that outbound simply omits.
   * o30: NEVER hard-block ↑ for these (铁律8 禁止多余门阀) — surface in strip/paramWarn.
   */
  function filledUnsupportedWarnings(ctx) {
    const $ = ctx && ctx.$;
    if (!$) return [];
    const msgs = [];
    const filledUnsupported = [];
    [
      ["sampler", $("sampler") && $("sampler").value],
      ["scheduler", $("scheduler") && $("scheduler").value],
      ["steps", $("steps") && $("steps").value],
      ["cfg", $("cfg") && $("cfg").value],
      ["width", $("width") && $("width").value],
      ["height", $("height") && $("height").value]
    ].forEach(function (row) {
      if (!row[1]) return;
      if (resolveFieldSupport(row[0], ctx) === "unsupported") filledUnsupported.push(row[0]);
    });
    if (filledUnsupported.length) {
      msgs.push("本家不支持 " + filledUnsupported.join("/") + " · 出站不会带上（不静默改值）");
    }
    return msgs;
  }

  /** Hard-block only (capability truly unavailable). */
  function blockingUnsupportedMessages(ctx) {
    const msgs = [];
    if (ctx && ctx.mode === "video" && resolveFieldSupport("i2v", ctx) === "unsupported") {
      msgs.push("本家不支持 i2v · Composer 已禁用该能力（明文不支持）");
    }
    return msgs;
  }

  /** @deprecated o30: prefer filledUnsupportedWarnings + blockingUnsupportedMessages */
  function filledUnsupportedMessages(ctx) {
    return blockingUnsupportedMessages(ctx).concat(filledUnsupportedWarnings(ctx));
  }

  /**
   * Drive Composer show/disable from board + live caps.
   * ctx: { $, backend, mode, caps, fillNanoResOptions }
   */
  function applyToSurface(ctx) {
    ctx = ctx || {};
    const $ = ctx.$;
    if (!$) return;
    const be = ctx.backend || "";
    const nano = be === "nano-gpt";
    const vid = ctx.mode === "video";
    const textish = ctx.mode === "text" || ctx.mode === "audio";

    const falBox = $("falParams");
    const comfyBox = $("comfyParams");
    const nanoBox = $("nanoParams");

    // Keep groups mounted: hide only when every child is mode-hidden (text/audio).
    const showFalGroup = !textish;
    const showComfyGroup = true;
    const showNanoGroup = nano || resolveFieldSupport("nanoRes", ctx) === "supported";
    if (falBox) falBox.classList.toggle("hidden", !showFalGroup);
    if (comfyBox) comfyBox.classList.toggle("hidden", !showComfyGroup);
    if (nanoBox) nanoBox.classList.toggle("hidden", !showNanoGroup);

    applyFieldSupport($("sampler"), "sampler", false, ctx);
    applyFieldSupport($("scheduler"), "scheduler", false, ctx);
    applyFieldSupport($("steps"), "steps", false, ctx);
    applyFieldSupport($("cfg"), "cfg", false, ctx);
    applyFieldSupport($("width"), "width", false, ctx);
    applyFieldSupport($("height"), "height", false, ctx);
    applyFieldSupport($("seed"), "seed", false, ctx);
    // o47: HF / Magao / Nano seed mod int32 — honest clamp hint (board)
    (function () {
      const seedEl = $("seed");
      if (!seedEl) return;
      const be = String(ctx.backend || "");
      const needsClamp = be === "huggingface" || be === "modelscope-ai" || be === "modelscope-cn" || be === "nano-gpt";
      if (needsClamp) {
        const prev = String(seedEl.title || "");
        const hint = "本家 seed 出站 mod int32（不发明默认；超范围按适配器 clamp/reject）";
        if (!/mod int32/.test(prev)) seedEl.title = prev ? (prev + " · " + hint) : hint;
      }
    })();
    applyNegative($("negative"), ctx);

    applyFieldSupport($("duration"), "duration", !vid, ctx);
    applyFieldSupport($("aspect"), "aspect", textish, ctx);
    applyFieldSupport($("res"), "res", textish || nano, ctx);
    applyFieldSupport($("nanoRes"), "nanoRes", !showNanoGroup, ctx);

    if (typeof ctx.fillNanoResOptions === "function" &&
        (nano || resolveFieldSupport("nanoRes", ctx) === "supported")) {
      ctx.fillNanoResOptions();
    }

    syncParamSupportStrip(ctx);
  }

  const api = {
    STAMP: STAMP,
    BOARD: COMPOSER_FIELD_BOARD,
    fieldBoardFor: fieldBoardFor,
    resolveFieldSupport: resolveFieldSupport,
    applyFieldSupport: applyFieldSupport,
    applyToSurface: applyToSurface,
    filledUnsupportedMessages: filledUnsupportedMessages,
    filledUnsupportedWarnings: filledUnsupportedWarnings,
    blockingUnsupportedMessages: blockingUnsupportedMessages,
    fieldSupportStripText: fieldSupportStripText,
    syncParamSupportStrip: syncParamSupportStrip,
    loraShape: loraShape,
    loraShapeHintText: loraShapeHintText,
    strengthPlaceholder: strengthPlaceholder,
    strengthTitle: strengthTitle,
    REASONS: FIELD_SUPPORT_REASONS
  };

  root.ComposerFieldAdapt = api;
})(typeof window !== "undefined" ? window : this);
