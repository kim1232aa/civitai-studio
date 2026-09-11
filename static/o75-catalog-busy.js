/* o75: don't block ↑ with "模型目录加载中" when a model is already selected. */
(function () {
  function clearBusyIfReady() {
    var s = document.getElementById("service");
    if (!s) return;
    var val = String(s.value || "").trim();
    if (val && s.getAttribute("aria-busy") === "true") s.setAttribute("aria-busy", "false");
    var w = document.getElementById("paramWarn");
    if (w && val && /模型目录加载中|请稍候/.test(String(w.textContent || ""))) {
      w.textContent = "";
      w.className = "param-warn";
    }
    var send = document.getElementById("send");
    if (send && val && send.getAttribute("aria-disabled") === "true") {
      var msg = String((document.getElementById("msg") || {}).textContent || "");
      if (/模型目录加载中|请稍候/.test(msg)) {
        send.removeAttribute("aria-disabled");
        send.disabled = false;
        send.classList.remove("is-blocked");
      }
    }
  }
  setInterval(clearBusyIfReady, 400);
  document.addEventListener("change", function (e) {
    if (e.target && (e.target.id === "service" || e.target.id === "backend")) clearBusyIfReady();
  }, true);
})();
