/* v0821o65-group-hide — load AFTER composer-field-adapt.js
 * Civitai image must not keep #falParams visible.
 * Fal width is supported, so the width!=unsupported fallback must NOT open #comfyParams.
 */
(function () {
  function install() {
    var api = typeof window !== "undefined" ? window.ComposerFieldAdapt : null;
    if (!api || typeof api.applyToSurface !== "function" || api._o61) return;
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
      var showFal = !textish && (be === "fal" || (vid && hasDurationEnum));
      var showComfy = !textish && !nano && be !== "fal" && (
        be === "civitai" || be === "huggingface" ||
        be === "modelscope-ai" || be === "modelscope-cn" ||
        (typeof api.resolveFieldSupport === "function" && api.resolveFieldSupport("width", ctx) !== "unsupported")
      );
      var showNano = nano;
      var fal = ctx.$("falParams");
      var comfy = ctx.$("comfyParams");
      var nanoBox = ctx.$("nanoParams");
      if (fal && fal.classList) fal.classList.toggle("hidden", !showFal);
      if (comfy && comfy.classList) comfy.classList.toggle("hidden", !showComfy);
      if (nanoBox && nanoBox.classList) nanoBox.classList.toggle("hidden", !showNano);
    };
    api._o61 = true;
    api.STAMP = "v0821o65-group-hide";
  }
  install();
})();
