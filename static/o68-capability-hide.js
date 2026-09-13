/* v0821o68-capability-hide — load AFTER composer-field-adapt.js + storyboard.js
 * If this model supports LoRA/seed/sampler/wh/duration, show the input.
 * If not, the input must not appear.
 */
(function () {
  function hide(el) {
    if (!el) return;
    el.classList.add("hidden");
    if (el.style) el.style.display = "none";
  }
  function show(el) {
    if (!el) return;
    el.classList.remove("hidden");
    if (el.style && el.style.display === "none") el.style.display = "";
  }
  function wrapOf(el) {
    if (!el) return null;
    return (el.closest && el.closest(".param-field")) || el.parentElement || el;
  }
  function install() {
    var api = typeof window !== "undefined" ? window.ComposerFieldAdapt : null;
    if (!api || typeof api.applyToSurface !== "function" || api._o68) return;
    var orig = api.applyToSurface;
    api.applyToSurface = function (ctx) {
      orig(ctx);
      if (!ctx || typeof ctx.$ !== "function") return;
      var be = ctx.backend || "";
      var item = (ctx.item && typeof ctx.item === "object") ? ctx.item : {};
      var caps = (item.capabilities && typeof item.capabilities === "object") ? item.capabilities : (ctx.caps || {});
      var supportsLora = caps.supportsLora;
      if (supportsLora == null) supportsLora = item.supportsLora;

      ["sampler", "scheduler", "steps", "cfg", "width", "height", "nanoRes", "duration", "aspect", "res", "seed"].forEach(function (field) {
        var el = ctx.$(field);
        if (!el || typeof api.resolveFieldSupport !== "function") return;
        var support = api.resolveFieldSupport(field, ctx);
        var wrap = wrapOf(el);
        if (support === "unsupported") hide(wrap);
        else if (wrap && wrap.classList && wrap.classList.contains("param-mode-hide")) hide(wrap);
        else show(wrap);
      });

      if (be !== "civitai") {
        hide(wrapOf(ctx.$("sampler")));
        hide(wrapOf(ctx.$("scheduler")));
      }

      var loraBox = ctx.$("loraBox") || ctx.$("loraParams") || ctx.$("loras");
      var loraBlock = ctx.$("loraBlock") || (loraBox && loraBox.closest && loraBox.closest(".lora-block")) || document.getElementById("loraBlock");
      var svcEl = ctx.$("service");
      var svcVal = (ctx.serviceId || (svcEl && svcEl.value) || (item && item.id) || "").trim();
      var hasModel = !!(item.id || svcVal);
      var showLora = (be === "civitai" && hasModel) || (hasModel && supportsLora === true);
      if (showLora) {
        show(loraBlock);
        if (loraBlock && loraBlock.classList) loraBlock.classList.remove("param-lora-off");
      } else {
        hide(loraBlock);
        if (loraBlock && loraBlock.classList) loraBlock.classList.add("param-lora-off");
      }

      var strip = ctx.$("paramSupportStrip");
      if (strip) {
        var text = String(strip.textContent || "").trim();
        if (text) {
          strip.hidden = false;
          show(strip);
        } else {
          strip.hidden = true;
          hide(strip);
        }
      }
    };
    api._o68 = true;
    api.STAMP = "v0821o68-capability-hide";
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", install);
  else install();
})();
