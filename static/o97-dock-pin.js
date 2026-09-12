/* v0821o97-dock-pin — collapsed composer attaches to the selected card.
 * Never center a 420px island over neighboring shots.
 * Load AFTER storyboard.js.
 */
(function () {
  var STAMP = "v0821o97-dock-pin";
  var lastKey = "";

  function $(id) { return document.getElementById(id); }

  function stageOf(dock) {
    return (dock && dock.closest && dock.closest(".stage")) || $("stage") || document.querySelector(".stage");
  }

  function selectedCard() {
    var dock = $("dock");
    var id = dock && dock.getAttribute("data-shot");
    if (!id && window.state && window.state.selected) id = window.state.selected;
    var card = id ? document.querySelector('.card.shot[data-id="' + id + '"]') : null;
    if (card) return card;
    card = document.querySelector(".card.shot.sel, .card.shot.on, .card.shot.active");
    if (card) return card;
    var cards = document.querySelectorAll(".card.shot");
    return cards.length ? cards[0] : null;
  }

  function stripCapsuleLabel() {
    var title = $("dockTitle");
    if (!title) return;
    var t = String(title.textContent || "");
    var cleaned = t.replace(/\s*[（(]胶囊[）)]/g, "").replace(/\s+/g, " ").trim();
    if (cleaned && cleaned !== t) title.textContent = cleaned;
  }

  function clamp(v, lo, hi) { return Math.max(lo, Math.min(hi, v)); }

  function pinDock() {
    var dock = $("dock");
    if (!dock || !dock.classList.contains("show")) return;
    stripCapsuleLabel();
    var card = selectedCard();
    if (!card) return;
    var stage = stageOf(dock) || dock.offsetParent || document.body;
    var sr = stage.getBoundingClientRect();
    var cr = card.getBoundingClientRect();
    var x = cr.left - sr.left;
    var y = cr.top - sr.top;
    var nw = cr.width;
    var nh = cr.height;
    var expanded = dock.classList.contains("expanded");
    var areaL = 72;
    var areaT = 8;
    var areaR = sr.width - 12;
    var areaB = sr.height - 12;
    var gap = 10;
    var left, top, dockW, dockH;
    if (expanded) {
      dockW = Math.min(400, Math.max(280, areaR - areaL));
      var side = areaR - (x + nw + gap);
      if (side >= 280) {
        left = x + nw + gap;
        top = y;
        dockW = Math.min(400, side);
      } else if (x - gap - 280 >= areaL) {
        dockW = Math.min(400, x - gap - areaL);
        left = x - gap - dockW;
        top = y;
      } else {
        left = clamp(x, areaL, areaR - dockW);
        top = y + nh + gap;
      }
      if (top + 200 > areaB) top = Math.max(areaT, areaB - 220);
    } else {
      var preferSide = nh < 220 || (nw < 260);
      dockW = preferSide ? 280 : Math.min(Math.max(nw, 240), 280);
      dockH = 96;
      if (preferSide && x + nw + gap + dockW <= areaR) {
        left = x + nw + gap;
        top = y;
      } else if (preferSide && x - gap - dockW >= areaL) {
        left = x - gap - dockW;
        top = y;
      } else {
        left = x;
        top = y + nh + gap;
        if (top + dockH > areaB) {
          if (x + nw + gap + dockW <= areaR) {
            left = x + nw + gap;
            top = y;
          } else {
            top = Math.max(areaT, y - dockH - gap);
          }
        }
      }
    }
    left = clamp(left, areaL, areaR - dockW);
    top = clamp(top, areaT, areaB - 72);
    var key = [expanded ? "e" : "c", Math.round(left), Math.round(top), Math.round(dockW)].join(":");
    if (key === lastKey) return;
    lastKey = key;
    dock.style.setProperty("left", left + "px", "important");
    dock.style.setProperty("top", top + "px", "important");
    dock.style.setProperty("width", dockW + "px", "important");
    dock.style.setProperty("max-width", dockW + "px", "important");
    dock.style.setProperty("right", "auto", "important");
    dock.style.setProperty("bottom", "auto", "important");
    dock.style.setProperty("transform", "none", "important");
    if (!expanded) {
      dock.style.setProperty("height", "auto", "important");
      dock.style.setProperty("max-height", "96px", "important");
    }
  }

  function schedule() {
    requestAnimationFrame(function () {
      requestAnimationFrame(pinDock);
    });
  }

  function install() {
    if (document.documentElement._o97pin) return;
    document.documentElement._o97pin = true;
    var dock = $("dock");
    if (dock) {
      var obs = new MutationObserver(schedule);
      obs.observe(dock, { attributes: true, attributeFilter: ["class"] });
    }
    document.addEventListener("click", schedule, true);
    window.addEventListener("resize", schedule);
    setInterval(stripCapsuleLabel, 800);
    schedule();
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", install);
  else install();
  window.__o97DockPin = { stamp: STAMP, pin: pinDock };
})();
