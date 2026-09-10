// Run in an isolated storyboard tab after loading storyboard-ui.css:
// agent-browser --cdp 9333 eval "$(cat scripts/test_storyboard_ui.js)"
// Run at desktop/tablet/phone sizes, expanded and collapsed; never generates.
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
  check($(".stamp").textContent.trim() === "v0821o12-civitai-writeback", "C1 stamp preserved");
  check(document.documentElement.scrollWidth <= innerWidth + 1, "no document horizontal overflow");
  check(Math.abs(rect(".stage").bottom - innerHeight) < 2, "canvas fills remaining screen");
  check(separate("#btnGroupRun", "#assetRail"), "group run clear of asset rail");
  const shotLabel = $(".shot .label");
  check(!shotLabel || parseFloat(getComputedStyle(shotLabel).fontSize) >= 16, "shot labels remain readable at 50%");
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
    check(getComputedStyle($("#dockBody")).overflowY === "auto", "Composer body owns vertical scroll");
    check(getComputedStyle($("#dockScroll")).overflowY === "visible", "no competing Composer scroller");
    check($("#dockBody").scrollWidth <= $("#dockBody").clientWidth + 1, "Composer fields fit horizontally");
    const old = $("#dockBody").scrollTop;
    $("#send").scrollIntoView({block: "center"});
    const r = rect("#send");
    check($("#send").contains(document.elementFromPoint(r.x + r.width / 2, r.y + r.height / 2)), "send reachable without clicking");
    $("#dockBody").scrollTop = old;
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
