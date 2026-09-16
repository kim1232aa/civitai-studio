/* o134 + o143: after import / house change, remap LoRA chips to this house.
 * Does not call /api/generate. Does not hide chips. Does not strip LoRAs on send.
 */
(function () {
  if (typeof window === "undefined") return;
  const Remap = window.LoraHouseRemap;
  if (!Remap) return;

  function currentHouse() {
    const el = document.getElementById("backend");
    return el ? String(el.value || "").trim() : "";
  }
  function currentFamily() {
    const Fam = window.SmartFamilyMatch;
    const j = window.__lastImportRecipe || {};
    if (Fam && Fam.familyFromImport) return Fam.familyFromImport(j) || "";
    return "";
  }
  function readChips() {
    if (typeof window.applyHouseLoraRemap === "function") {
      try { window.applyHouseLoraRemap(); } catch (_) {}
    }
    if (window.state && Array.isArray(window.state.loras) && window.state.loras.length) {
      return window.state.loras.slice();
    }
    const j = window.__lastImportRecipe || {};
    if (Array.isArray(j.loras)) return j.loras.slice();
    return [];
  }
  // o143: Magao Hub-only / house-shape warnings stay in #loraHint — not canvas #msg error sticker.
  function paintHint(rows) {
    const hint = document.getElementById("loraHint");
    if (!hint) return;
    const blocked = (rows || []).filter(function (r) { return !r.outbound && !r.canOutbound; });
    const bits = (rows || []).map(function (r) {
      return (r.name || r.air || r.path || "LoRA") + " · " + (r.chipReason || "");
    });
    if (blocked.length) {
      // Keep capability honest (Hub owner/repo) but scoped to LoRA block.
      hint.textContent = blocked[0].chipReason || bits.join(" ； ") || "这家不能用当前 LoRA 形态";
      hint.classList.add("show", "bad");
    } else {
      hint.textContent = bits.join(" ； ") || hint.textContent;
      hint.classList.remove("bad");
      if (bits.length) hint.classList.add("show");
    }
  }
  function applyRemap() {
    const house = currentHouse();
    if (!house) return;
    const rows = Remap.remapLorasForHouse(house, readChips(), currentFamily());
    window.__remappedLoras = rows;
    paintHint(rows);
    // Do not stamp #msg — canvas sticker looked like a gen error (o143).
    try {
      window.dispatchEvent(new CustomEvent("lora-house-remap", { detail: { house: house, rows: rows } }));
    } catch (_) {}
  }

  const rawFetch = window.fetch;
  if (typeof rawFetch === "function" && !window.__o134FetchWrapped) {
    window.__o134FetchWrapped = true;
    window.fetch = function (url, opts) {
      const req = String(url || "");
      return rawFetch.apply(this, arguments).then(function (res) {
        if (req.indexOf("/api/import") >= 0 && res && res.ok) {
          res.clone().json().then(function (j) {
            window.__lastImportRecipe = j;
            setTimeout(applyRemap, 80);
            setTimeout(applyRemap, 500);
          }).catch(function () {});
        }
        return res;
      });
    };
  }

  document.addEventListener("change", function (ev) {
    const t = ev && ev.target;
    if (!t) return;
    if (t.id === "backend" || t.id === "service") applyRemap();
  });
  document.addEventListener("click", function (ev) {
    const t = ev && ev.target;
    if (!t || !t.closest) return;
    if (t.closest("#send") || t.closest("#sendCap")) {
      const rows = window.__remappedLoras || [];
      const blocked = rows.filter(function (r) { return !r.outbound && !r.canOutbound; });
      if (blocked.length) {
        const hint = document.getElementById("loraHint");
        if (hint) {
          hint.textContent = (blocked[0].chipReason || "LoRA 不能出站") + " · 先换 LoRA 或换家再点 ↑";
          hint.classList.add("show", "bad");
        }
      }
    }
  }, true);
  setTimeout(applyRemap, 800);
})();
