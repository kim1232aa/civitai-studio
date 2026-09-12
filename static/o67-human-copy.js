/* v0821o67-human-copy + o97 pin inline
 * v0821o105-adapt v0821o104-seko-attach v0821o103-wide-desk v0821o102-seko v0821o101-shell v0821o100-desk v0821o99-capsule-row
 * Product copy scrub + attach composer above/below selected shot. Box follows the shot.
 * Inlined because storyboard.html on main (o96) does not load o97-dock-pin.js.
 */
(function () {
  var ROBOT = /不发明|点胶囊|灌满测试|path\/downloadUrl|air\+strength|发出≠加载|field board|unverified|null→未填|\/ \+ skill|使用 Skill/;

  function humanLoraHint(shape) {
    if (shape === "air") return "填写编号和强度，可留空";
    if (shape === "hub_repo") return "填写仓库名，可留空";
    if (shape === "none") return "这个模型不用 LoRA";
    if (shape === "path") return "填写 LoRA 地址或名称，可留空";
    return "";
  }

  function patchApi() {
    var api = typeof window !== "undefined" ? window.ComposerFieldAdapt : null;
    if (!api || api._o67) return;
    api.LORA_SHAPE_HINT = {
      air: humanLoraHint("air"),
      path: humanLoraHint("path"),
      hub_repo: humanLoraHint("hub_repo"),
      none: humanLoraHint("none"),
      unknown: ""
    };
    if (typeof api.applyLoraUi === "function") {
      var orig = api.applyLoraUi;
      api.applyLoraUi = function (ctx) {
        orig(ctx);
        var $ = ctx && ctx.$;
        var hint = $ && ($("loraHint") || $("loraShapeHint"));
        if (hint) {
          var state = typeof api.loraUiState === "function" ? api.loraUiState(ctx) : {};
          hint.textContent = humanLoraHint(state && state.shape) || "";
        }
        var strip = $ && $("paramSupportStrip");
        if (strip) {
          strip.hidden = true;
          strip.textContent = "";
        }
      };
    }
    if (typeof api.syncParamSupportStrip === "function") {
      api.syncParamSupportStrip = function (ctx) {
        var $ = ctx && ctx.$;
        var el = $ && $("paramSupportStrip");
        if (el) {
          el.hidden = true;
          el.textContent = "";
        }
      };
    }
    api._o67 = true;
    api.STAMP = "v0821o67-human-copy";
  }

  function scrubNode(el) {
    if (!el || el.nodeType !== 1) return;
    if (el.id === "prompt" || el.id === "negative") {
      var ph = String(el.getAttribute("placeholder") || "");
      if (ROBOT.test(ph) || /skill/i.test(ph)) {
        el.setAttribute("placeholder", el.id === "negative" ? "不想出现的内容，可留空" : "描述你想生成的画面");
      }
      return;
    }
    var text = (el.childNodes && el.childNodes.length === 1 && el.childNodes[0].nodeType === 3)
      ? String(el.textContent || "").trim()
      : "";
    if (!text) return;
    if (text === "灌满测试" || text.indexOf("灌满测试") >= 0) {
      el.hidden = true;
      el.style.display = "none";
      return;
    }
    if (/^未接$/.test(text) && el.classList && el.classList.contains("mode-tag")) {
      el.hidden = true;
      el.style.display = "none";
      return;
    }
    if (/ · schema/.test(text)) {
      el.textContent = text.replace(/\s*·\s*schema/g, "");
      return;
    }
    if (/点胶囊|选服务后点|选分镜 →/.test(text)) {
      el.hidden = true;
      el.textContent = "";
      return;
    }
    if (ROBOT.test(text)) {
      if (el.id === "loraQLbl") {
        el.textContent = "LoRA";
        return;
      }
      if (el.id === "loraHint" || (el.classList && el.classList.contains("lora-hint"))) {
        el.textContent = "填写 LoRA 地址或名称，可留空";
        return;
      }
      if (/参考/.test(text)) el.textContent = text.replace(/·\s*还可\s*\d+/, "").replace(/参考\s*/, "参考图 ");
      else el.textContent = "";
    }
  }

  function scrubTree(root) {
    if (!root || !root.querySelectorAll) return;
    var strip = root.querySelector("#paramSupportStrip");
    if (strip) {
      strip.hidden = true;
      strip.textContent = "";
    }
    var hint = root.querySelector("#loraHint, #loraShapeHint");
    if (hint && ROBOT.test(String(hint.textContent || ""))) {
      hint.textContent = "填写 LoRA 地址或名称，可留空";
    }
    var nodes = root.querySelectorAll("button, a, span, p, label, small, .mode-tag, .dock-hint, .ref-cap-hint, .chat-rail, .cm-note, [placeholder]");
    for (var i = 0; i < nodes.length; i++) scrubNode(nodes[i]);
    var title = root.querySelector(".title, #title, header .title, #projTitle");
    if (title) {
      var raw = String(title.textContent || "").trim();
      var cleaned = raw.replace(/\s*[（(]胶囊[)）]/g, "").replace(/\s*[·•]\s*[0-9a-f]{6,10}\s*$/i, "").trim();
      if (cleaned && cleaned !== raw) title.textContent = cleaned;
    }
    var dockTitle = root.querySelector("#dockTitle");
    if (dockTitle) {
      var dt = String(dockTitle.textContent || "");
      var dc = dt.replace(/\s*[（(]胶囊[)）]/g, "").replace(/\s+/g, " ").trim();
      if (dc && dc !== dt) dockTitle.textContent = dc;
    }
  }

  function installScrub() {
    patchApi();
    if (typeof document === "undefined") return;
    scrubTree(document);
    if (document.documentElement && !document.documentElement._o67obs) {
      var obs = new MutationObserver(function () {
        patchApi();
        scrubTree(document);
      });
      obs.observe(document.documentElement, { childList: true, subtree: true, characterData: true });
      document.documentElement._o67obs = obs;
    }
  }

  var PIN = "v0821o105-adapt";
  var pinning = false;
  var lastKey = "";
  function $(id) { return document.getElementById(id); }

  function injectPinCss() {
    if (document.getElementById("o97PinCss")) return;
    var css = document.createElement("style");
    css.id = "o97PinCss";
    css.textContent = [
      ".chip{width:44px !important;height:44px !important;overflow:hidden !important}",
      ".chip img,.chip video{width:44px !important;height:44px !important;object-fit:cover !important}",
      ".dock.show,.dock.show.collapsed,.dock.show.expanded{right:auto !important;width:auto !important;min-width:0 !important;max-width:none !important;transform:none !important;height:auto !important;max-height:none !important;}",
      ".dock.show #dockExpand,.dock.show #dockCollapse,.dock.show #dockHint,.dock.show .expand-only,.dock.show .collapse-only{display:none !important}"
    ].join("");
    document.head.appendChild(css);
  }

  function stageOf(dock) {
    return (dock && dock.closest && dock.closest(".stage")) || document.querySelector(".stage");
  }

  function selectedCard() {
    var dock = $("dock");
    var id = dock && dock.getAttribute("data-shot");
    if (!id && window.state && window.state.selected) id = window.state.selected;
    var card = null;
    if (id) {
      try { card = document.querySelector('.card.shot[data-id="' + CSS.escape(String(id)) + '"]'); }
      catch (e) { card = document.querySelector('.card.shot[data-id="' + String(id) + '"]'); }
    }
    if (card) return card;
    return document.querySelector(".card.shot.sel") || document.querySelector(".card.shot.on") || document.querySelector(".card.shot.active") || document.querySelector(".card.shot");
  }

  function clamp(v, lo, hi) { return Math.max(lo, Math.min(hi, v)); }

  function relRect(el, sr) {
    var r = el.getBoundingClientRect();
    return { l: r.left - sr.left, t: r.top - sr.top, r: r.right - sr.left, b: r.bottom - sr.top, w: r.width, h: r.height };
  }

  function neighborRects(card, sr) {
    var all = document.querySelectorAll(".card.shot");
    var out = [];
    for (var i = 0; i < all.length; i++) if (all[i] !== card) out.push(relRect(all[i], sr));
    return out;
  }

  function hitsOthers(left, top, w, h, others, pad) {
    pad = pad == null ? 6 : pad;
    var R = left + w, B = top + h;
    for (var i = 0; i < others.length; i++) {
      var o = others[i];
      if (!(R <= o.l + pad || left >= o.r - pad || B <= o.t + pad || top >= o.b - pad)) return true;
    }
    return false;
  }

  function tallNeighbors(card, sr) {
    var others = neighborRects(card, sr);
    var cr = relRect(card, sr);
    for (var i = 0; i < others.length; i++) {
      if (others[i].h >= cr.h + 40 && others[i].l < cr.r + 40 && others[i].r > cr.l - 40) return true;
    }
    return others.length > 0 && cr.h < 220;
  }

  function belowBand(x, w, cardBottom, others) {
    var bottom = cardBottom, L = x, R = x + w;
    for (var i = 0; i < others.length; i++) {
      var o = others[i];
      if (o.r > L + 8 && o.l < R - 8) bottom = Math.max(bottom, o.b);
    }
    return bottom;
  }

  function pinDock() {
    if (pinning) return;
    var dock = $("dock");
    if (!dock || !dock.classList.contains("show")) return;
    stripCapsuleLabel();
    pinning = true;
    if (typeof window.positionDock === "function") {
      try { window.positionDock(); } catch (e) {}
    } else {
      // fallback bottom desk
      dock.style.setProperty("left", "72px", "important");
      dock.style.setProperty("bottom", "12px", "important");
      dock.style.setProperty("top", "auto", "important");
      dock.style.setProperty("right", "auto", "important");
      dock.style.setProperty("width", "480px", "important");
      dock.style.setProperty("max-width", "480px", "important");
      dock.style.setProperty("transform", "none", "important");
    }
    pinning = false;
  }

  function schedulePin() {
    requestAnimationFrame(function () { requestAnimationFrame(pinDock); });
  }

  function installPin() {
    if (document.documentElement._o97pin) return;
    document.documentElement._o97pin = true;
    injectPinCss();
    var dock = $("dock");
    if (dock) {
      var obs = new MutationObserver(function () { if (!pinning) schedulePin(); });
      obs.observe(dock, { attributes: true, attributeFilter: ["class", "data-shot"] });
    }
    document.addEventListener("click", schedulePin, true);
    window.addEventListener("resize", schedulePin);
    setInterval(pinDock, 800);
    schedulePin();
    window.__o97DockPin = { stamp: PIN, pin: pinDock };
  }

  function boot() {
    installScrub();
    installPin();
  }
  if (typeof document !== "undefined" && document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
