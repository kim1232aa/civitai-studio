/* o133: after /api/import, pin the model to the post family in the current house.
 * Does not call /api/generate. Does not change house. */
(function () {
  if (typeof window === "undefined") return;

  function loadSibling(src, after) {
    if (document.querySelector('script[src^="' + src.split("?")[0] + '"]')) {
      if (after) after();
      return;
    }
    const s = document.createElement("script");
    s.src = src;
    s.onload = after || function () {};
    document.head.appendChild(s);
  }
  function loadCss(href) {
    if (document.querySelector('link[href^="' + href.split("?")[0] + '"]')) return;
    const l = document.createElement("link");
    l.rel = "stylesheet";
    l.href = href;
    document.head.appendChild(l);
  }
  loadCss("/static/o134-name-wrap.css?v=o134name");
  if (!window.LoraHouseRemap) {
    loadSibling("/static/lora-house-remap.js?v=o134lora", function () {
      loadSibling("/static/o134-lora-remap-hook.js?v=o134");
    });
  } else {
    loadSibling("/static/o134-lora-remap-hook.js?v=o134");
  }

  const Fam = window.SmartFamilyMatch;
  if (!Fam) return;

  const OP_LABEL = { t2i: "文生图", i2i: "图生图", i2v: "图生视频", t2v: "文生视频" };

  function currentHouse() {
    const el = document.getElementById("backend");
    return el ? String(el.value || "").trim() : "";
  }
  function currentOp() {
    const vid = document.getElementById("modeVid");
    if (vid && vid.classList.contains("on")) return "i2v";
    return "t2i";
  }
  function applyImportMatch(j) {
    if (!j || typeof j !== "object") return;
    const house = currentHouse() || String(j.backend || "").trim() || "civitai";
    const op = j.kind === "video" ? "i2v" : currentOp();
    const fam = Fam.familyFromImport(j) || Fam.inferModelFamily([j.ecosystem, j.checkpointName, j.diffusionModel, j.serviceId].filter(Boolean).join(" "));
    const sel = document.getElementById("service");
    const curId = sel ? String(sel.value || "").trim() : "";
    const keep = Fam.keepCurrent({
      currentId: curId,
      item: { id: curId, name: curId },
      op: op,
      family: fam,
      foreign: false,
      fits: function () { return true; }
    });
    if (!keep) {
      const want = Fam.pickByFamily({
        backend: house,
        op: op,
        family: fam,
        pool: curId ? [{ id: curId, name: curId }] : [],
        fits: function () { return true; },
        belongs: function (id, be) { return be === house; }
      }) || Fam.preferredId(house, fam, op);
      const msg = document.getElementById("msg");
      if (!want) {
        if (sel) sel.value = "";
        if (msg && fam) {
          msg.textContent = "这家没有可匹配的" + (OP_LABEL[op] || op) + "模型（" + fam + "），请换模型或换家";
          msg.className = "msg warn";
        }
      } else if (sel) {
        let hit = false;
        for (let i = 0; i < sel.options.length; i++) {
          if (sel.options[i].value === want) { hit = true; break; }
        }
        if (!hit) {
          const opt = document.createElement("option");
          opt.value = want;
          opt.textContent = want;
          sel.appendChild(opt);
        }
        sel.value = want;
        try { sel.dispatchEvent(new Event("change", { bubbles: true })); } catch (_) {}
        if (msg && fam) {
          msg.textContent = "已智能匹配" + (OP_LABEL[op] || op) + " · " + fam + " · " + want;
          msg.className = "msg ok";
        }
      }
    }
    try {
      if (typeof window.applyHouseLoraRemap === "function") window.applyHouseLoraRemap();
    } catch (_) {}
  }

  const rawFetch = window.fetch;
  if (typeof rawFetch === "function" && !window.__o133FetchWrapped) {
    window.__o133FetchWrapped = true;
    window.fetch = function (url, opts) {
      const req = String(url || "");
      return rawFetch.apply(this, arguments).then(function (res) {
        if (req.indexOf("/api/import") >= 0 && res && res.ok) {
          res.clone().json().then(function (j) {
            window.__lastImportRecipe = j;
            setTimeout(function () { applyImportMatch(j); }, 50);
            setTimeout(function () { applyImportMatch(j); }, 400);
            setTimeout(function () { applyImportMatch(j); }, 1200);
          }).catch(function () {});
        }
        return res;
      });
    };
  }
})();
