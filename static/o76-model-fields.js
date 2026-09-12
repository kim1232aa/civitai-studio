/* o76: selecting a model must show only that model's supported fields. */
(function () {
  function $id(id) { return document.getElementById(id); }
  function run() {
    var adapt = window.ComposerFieldAdapt;
    if (!adapt || typeof adapt.applyToSurface !== "function") return;
    var be = ($id("backend") && $id("backend").value) || "";
    var modeBtn = document.querySelector("#composerModes button.on");
    var mode = (modeBtn && modeBtn.getAttribute("data-mode")) || "image";
    var svc = ($id("service") && $id("service").value) || "";
    var item = null;
    try {
      if (window.state && window.state.catalogById && svc) item = window.state.catalogById[svc] || null;
    } catch (_) {}
    adapt.applyToSurface({
      $: $id,
      backend: be,
      mode: mode,
      caps: (item && item.capabilities) || {},
      item: item,
      serviceId: svc
    });
    if (typeof window.__o68HideUnsupported === "function") {
      try { window.__o68HideUnsupported(); } catch (_) {}
    }
  }
  function bind() {
    var sel = $id("service");
    var be = $id("backend");
    if (sel && !sel.dataset.o76) { sel.dataset.o76 = "1"; sel.addEventListener("change", run); }
    if (be && !be.dataset.o76) { be.dataset.o76 = "1"; be.addEventListener("change", run); }
    run();
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", bind);
  else bind();
  setTimeout(bind, 800);
})();
