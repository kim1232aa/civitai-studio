// Run in an isolated storyboard tab after loading storyboard-ui.css:
// agent-browser --cdp 9333 eval "$(cat scripts/test_storyboard_ui.js)"
// Run at desktop/tablet/phone sizes, expanded and collapsed; never generates.
// Source-level catalog/fixture anchors live in test_storyboard_graph.py:
// loadCatalog is `function loadCatalog` (not `async function loadCatalog`);
// Magao fixture copy is `魔搭模型（不预置 LoRA）` (not `魔搭 LoRA夹具`).
(() => {
  const $ = (s) => document.querySelector(s);
  const passed = [];
  const check = (ok, name) => {
    if (!ok) throw new Error("Storyboard UI: " + name);
    passed.push(name);
  };
  const rect = (s) => $(s).getBoundingClientRect();
  const visible = (s) => $(s) && rect(s).width > 0 && rect(s).height > 0;
  const separate = (a, b) => {
    if (!visible(a) || !visible(b)) return true;
    const x = rect(a), y = rect(b);
    return x.right <= y.left + 1 || y.right <= x.left + 1 ||
      x.bottom <= y.top + 1 || y.bottom <= x.top + 1;
  };
  const within = (s) => {
    if (!visible(s)) return true;
    const r = rect(s);
    return r.left >= -1 && r.top >= -1 && r.right <= innerWidth + 1 && r.bottom <= innerHeight + 1;
  };
  check(location.origin === "http://127.0.0.1:18832" && location.pathname === "/storyboard.html", "correct cloud canvas");
  check([...document.styleSheets].some(s => s.href && s.href.includes("/static/storyboard-ui.css")), "visual stylesheet loaded");
  check($(".stamp") && /^v0821o\d+/.test($(".stamp").textContent.trim()), "version stamp preserved");
  check(document.documentElement.scrollWidth <= innerWidth + 1, "no document horizontal overflow");
  check(Math.abs(rect(".stage").bottom - innerHeight) < 2, "canvas fills remaining screen");
  check(separate("#btnGroupRun", "#assetRail"), "group run clear of asset rail");
  const shotLabel = $(".shot .label");
  // Ruling (o136seko): Seko canvas node titles render at ~12px at 100% and scale with
  // the canvas (no counter-scaling) — verified in recon/seko/22-dblclick-node.png.
  // Our explicit 13px (.card.shot .label) matches Seko; the old ≥16px guard predates
  // Seko alignment and is superseded. Semantic preserved: label must be deliberately
  // styled and legible at full zoom (≥12px), never browser-default-tiny.
  check(!shotLabel || parseFloat(getComputedStyle(shotLabel).fontSize) >= 12, "shot labels match Seko canvas scale (≥12px, styled deliberately)");
  if ($(".dock.expanded")) {
    check(rect("#dock").height <= innerHeight - 40 + 1 &&
      rect("#dock").top >= -1 && rect("#dock").bottom <= innerHeight + 1,
      "Composer is capped inside the viewport");
  }
  for (const [a, b] of [
    [".tools", ".rail"], [".tools", ".minimap"], [".minimap", ".zoom"],
    [".dock", ".zoom"], [".dock", ".minimap"], [".dock", ".rail"], [".dock", ".selbar"],
  ]) check(separate(a, b), a + " clear of " + b);
  for (const s of [".tools", ".rail", ".minimap", ".zoom", ".dock", ".selbar"])
    check(within(s), s + " inside viewport");
  check($(".tools").scrollWidth <= $(".tools").clientWidth + 1, "all toolbar controls fit horizontally");
  check(getComputedStyle($(".grid")).backgroundImage !== "none", "dot grid retained");
  check(getComputedStyle(document.documentElement).colorScheme === "dark", "dark native controls");
  if ($(".dock.expanded")) {
    // Ruling (o136seko): Composer 改为「高度跟内容走，不裁切」—— positionDock 内联
    // max-height:none 并按 bottomReserve 夹进视口（见 storyboard.js positionDock 注释）。
    // 旧契约「dockBody 拥有内部滚动条」作废；新语义：展开态永不裁切内容（overflowY 非
    // hidden 且 max-height 无封顶），dockScroll 不得成为竞争性垂直滚动容器。
    const bodyCS = getComputedStyle($("#dockBody"));
    check(bodyCS.overflowY !== "hidden" && bodyCS.maxHeight === "none", "expanded Composer never clips content");
    check(getComputedStyle($("#dockScroll")).overflowY === "visible", "no competing Composer scroller");
    check($("#dockBody").scrollWidth <= $("#dockBody").clientWidth + 1, "Composer fields fit horizontally");
    // Ruling (o19/o136seko): 单↑ 契约 —— .dock.show 下 #send 刻意 display:none
    // （shell.css .dock.show #send），#sendCap 是唯一生成入口；语义保留：生成按钮
    // 必须不被遮挡、无需先点击别的东西即可触达。
    const sendBtn = $("#sendCap");
    const sr2 = rect("#sendCap");
    check(sendBtn.contains(document.elementFromPoint(sr2.x + sr2.width / 2, sr2.y + sr2.height / 2)), "send reachable without clicking");
  }
  for (const card of document.querySelectorAll(".card")) {
    const s = getComputedStyle(card), shot = card.classList.contains("shot");
    // Chromium rounds fractional CSS pixels at non-100% browser zoom.
    check(Math.abs(parseFloat(s.width) - (shot ? 640 : 132)) < .1 &&
      Math.abs(parseFloat(s.height) - (shot ? 360 : 208)) < .1, "node geometry matches graph " + card.dataset.id);
  }
  for (const media of document.querySelectorAll(".card.shot .face img, .card.shot .face video, .card.asset img.thumb, .card.asset video.thumb"))
    check(getComputedStyle(media).objectFit === "cover", "card media fills face without letterbox bars");
  for (const edge of document.querySelectorAll("path.edge"))
    check(getComputedStyle(edge).vectorEffect === "non-scaling-stroke", "wire remains legible on zoom");
  for (const group of document.querySelectorAll(".param-group.hidden"))
    check(getComputedStyle(group).display === "none", "parameter visibility gate preserved");
  const sends = performance.getEntriesByType("resource").filter(e => /\/api\/generate(?:[/?]|$)/.test(e.name));
  check(sends.length === 0, "no generation requests");
  return {passed: passed.length, viewport: [innerWidth, innerHeight], dock: $("#dock").className, checks: passed};
})()
