/* v0821o67-human-copy — product UI is for people, not agents.
 * Hide test playbook / field-board jargon that leaked onto the canvas.
 * Load AFTER composer-field-adapt.js and storyboard.js.
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
    if (/点胶囊|选服务后点|选分镜 →/.test(text)) {
      el.hidden = true;
      el.textContent = "";
      return;
    }
    if (ROBOT.test(text)) {
      if (/LoRA|lora/.test(text)) el.textContent = "填写 LoRA 地址或名称，可留空";
      else if (/参考/.test(text)) el.textContent = text.replace(/·\s*还可\s*\d+/, "").replace(/参考\s*/, "参考图 ");
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
    var title = root.querySelector(".title, #title, header .title");
    if (title && /^qa-/i.test(String(title.textContent || "").trim())) {
      title.textContent = "未命名画布";
    }
  }

  function install() {
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
  if (typeof document !== "undefined" && document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", install);
  } else {
    install();
  }
})();
