/* v0821o69-group-hide — load AFTER composer-field-adapt.js
 * Civitai image must not keep #falParams visible.
 * Fal T2I uses comfy group (w/h/seed); video duration group only when mode=video.
 * Unsupported fields hide. LoRA only when supportsLora===true,
 * except Civitai AIR which always shows LoRA after a model is selected.
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
    if (!api || typeof api.applyToSurface !== "function" || api._o69) return;
    var orig = api.applyToSurface;
    api.applyToSurface = function (ctx) {
      orig(ctx);
      if (!ctx || typeof ctx.$ !== "function") return;
      var be = ctx.backend || "";
      var nano = be === "nano-gpt";
      var vid = ctx.mode === "video";
      var textish = ctx.mode === "text" || ctx.mode === "audio";
      var ic = typeof api.itemCaps === "function" ? api.itemCaps(ctx) : {};
      var hasDurationEnum = Array.isArray(ic.durationEnum) && ic.durationEnum.length > 0;
      var showFal = !textish && vid && (be === "fal" || hasDurationEnum);
      var showComfy = !textish && !nano && (
        be === "civitai" || be === "huggingface" ||
        be === "modelscope-ai" || be === "modelscope-cn" ||
        (be === "fal" && !vid)
      );
      var showNano = nano;
      var fal = ctx.$("falParams");
      var comfy = ctx.$("comfyParams");
      var nanoBox = ctx.$("nanoParams");
      if (fal && fal.classList) fal.classList.toggle("hidden", !showFal);
      if (comfy && comfy.classList) comfy.classList.toggle("hidden", !showComfy);
      if (nanoBox && nanoBox.classList) nanoBox.classList.toggle("hidden", !showNano);

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
      var loraBlock = ctx.$("loraBlock") || (loraBox && loraBox.closest && loraBox.closest(".lora-block")) || loraBox;
      var hasModel = !!(item.id || ctx.serviceId);
      var showLora = be === "civitai" ? hasModel : (hasModel && supportsLora === true);
      if (showLora) {
        show(loraBlock);
        if (loraBlock && loraBlock.classList) loraBlock.classList.remove("param-lora-off");
      } else {
        hide(loraBlock);
        if (loraBlock && loraBlock.classList) loraBlock.classList.add("param-lora-off");
      }

      var strip = ctx.$("paramSupportStrip");
      if (strip) {
        strip.hidden = true;
        hide(strip);
      }
    };
    api._o61 = true;
    api._o69 = true;
    api.STAMP = "v0821o69-group-hide";
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", install);
  else install();
})();
