// Offline VM checks only: no browser, live API, generation or user storage access.
// Run: node scripts/test_storyboard_catalog_paging.js
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const root = path.resolve(__dirname, "..");
const source = fs.readFileSync(path.join(root, "static/storyboard.js"), "utf8");
const html = fs.readFileSync(path.join(root, "static/storyboard.html"), "utf8");

function section(from, to) {
  const start = source.indexOf(from);
  const end = source.indexOf(to, start + from.length);
  assert.ok(start >= 0 && end > start, "VM seam exists: " + from);
  return source.slice(start, end);
}

// Native select semantics matter: rebuilding options must not lose the selected ID.
class Element {
  constructor(tag, attrs) {
    this.tagName = tag.toUpperCase();
    this.attrs = attrs || {};
    this.children = [];
    this.handlers = {};
    this.hidden = "hidden" in this.attrs;
    this.disabled = "disabled" in this.attrs;
    this.textContent = "";
    this._value = "";
    this.classList = { toggle() {}, add() {}, remove() {} };
  }
  get options() { return this.children; }
  get value() { return this._value; }
  set value(value) {
    const v = String(value);
    this._value = this.tagName !== "SELECT" || this.children.some(o => o.value === v) ? v : "";
  }
  set innerHTML(value) {
    this.children = [];
    this._value = "";
    for (const row of value.matchAll(/<option\b[^>]*value="([^"]*)"[^>]*>([^<]*)<\/option>/g)) {
      const option = new Element("option");
      option.value = row[1];
      option.textContent = row[2];
      this.appendChild(option);
    }
  }
  appendChild(child) {
    this.children.push(child);
    if (this.tagName === "SELECT" && this.children.length === 1) this._value = child.value;
    return child;
  }
  setAttribute(key, value) { this.attrs[key] = String(value); }
  getAttribute(key) { return this.attrs[key]; }
  addEventListener(event, fn) { (this.handlers[event] ||= []).push(fn); }
  fire(event) {
    for (const fn of this.handlers[event] || []) fn({ target: this });
    if (this["on" + event]) return this["on" + event]({ target: this });
  }
}

function harness(backend = "modelscope-ai") {
  const elements = {};
  // Only IDs actually mounted in the live HTML are available to the production code.
  for (const match of html.matchAll(/<([a-z][\w-]*)\b([^>]*\bid="[^"]+"[^>]*)>/gi)) {
    const attrs = {};
    for (const attr of match[2].matchAll(/([\w-]+)(?:="([^"]*)")?/g)) attrs[attr[1]] = attr[2] || "";
    elements[attrs.id] = new Element(match[1], attrs);
  }
  for (const id of [backend, "modelscope-ai", "modelscope-cn", "fal", "huggingface", "civitai"]) {
    const option = new Element("option");
    option.value = id;
    elements.backend.appendChild(option);
  }
  elements.backend.value = backend;
  const requests = [], timers = new Map(), frames = new Map();
  let clock = 0;
  const sandbox = {
    console, AbortController, URLSearchParams,
    document: {
      getElementById: id => elements[id] || null,
      createElement: tag => new Element(tag),
    },
    setTimeout(fn, delay) { const id = ++clock; timers.set(id, { fn, delay }); return id; },
    clearTimeout(id) { timers.delete(id); },
    requestAnimationFrame(fn) { const id = ++clock; frames.set(id, fn); return id; },
    cancelAnimationFrame(id) { frames.delete(id); },
    fetch(url, options) {
      assert.ok(url.startsWith("/api/catalog?"), "only offline catalog requests are allowed");
      let resolve, reject;
      const promise = new Promise((yes, no) => { resolve = yes; reject = no; });
      requests.push({ url, signal: options.signal, resolve, reject });
      // Intentionally ignore abort: token/context guards must reject a late response too.
      return promise;
    },
    syncParamSurface() {}, syncLoraUi() {}, paramGateMessage() {},
    renderCards() {}, drawWires() {}, renderDock() {}, persist() {},
    falHasLoras() { return false; },
    formatErr(e) { return e.message || String(e); },
    setMsg(text) { elements.msg.textContent = text; },
    ensureSelectOpt(el, value) {
      if (!el.options.some(o => o.value === value)) {
        const option = new Element("option"); option.value = value; el.appendChild(option);
      }
      el.value = value;
    },
  };
  vm.createContext(sandbox);
  // Run the actual catalog/select functions and handlers, not a second implementation.
  // Unrelated canvas boot, generation, storage and provider calls are deliberately excluded.
  const code = [
    'const $ = id => document.getElementById(id);',
    section('  const CIVITAI_PREF_SERVICE =', '  const SNAP_PX ='),
    section('  const state = {', '  function uid('),
    section('  function isStubMode()', '  function isMulti('),
    section('  function svcOptionText(', '  function catalogItemForService('),
    section('  function catalogItemSupportsI2v(', '    // Provider defaults'),
    section('  const MULTI_REF_FIELDS =', '  // Resolve caps'),
    section('  function importServiceAvailable(', '  async function loadOuts('),
    section('  $("backend").onchange =', '  if ($("negative"))'),
    section('  function setMode(', '  ["backend", "service", "duration"'),
    'globalThis.api = { state, loadCatalog, setMode };',
  ].join('\n');
  vm.runInContext(code, sandbox, { filename: "storyboard-catalog.vm.js" });
  const flush = async () => { for (let i = 0; i < 12; i++) await Promise.resolve(); };
  return {
    ...sandbox.api, elements, requests, frames,
    async respond(index, body, status = 200) {
      requests[index].resolve({ ok: status < 400, status, json: async () => body });
      await flush();
    },
    async reject(index, message = "offline upstream failure") {
      const err = message instanceof Error ? message : new Error(message);
      requests[index].reject(err); await flush();
    },
    timeoutDelays() { return Array.from(timers.values()).map(timer => timer.delay); },
    async timers(delay) {
      for (const [id, timer] of Array.from(timers)) if (timer.delay === delay) {
        timers.delete(id); timer.fn();
      }
      await flush();
    },
    async framesAll() {
      while (frames.size) {
        const batch = Array.from(frames); frames.clear(); batch.forEach(([, fn]) => fn());
      }
      await flush();
    },
    async click(id) {
      assert.ok(elements[id], "live HTML mounts #" + id);
      assert.equal(elements[id].hidden, false, id + " is visible");
      assert.equal(elements[id].disabled, false, id + " is enabled");
      elements[id].fire("click"); await flush();
    },
    ids() { return elements.service.options.map(o => o.value).filter(Boolean); },
  };
}

function page(items, extra) {
  return Object.assign({
    items, page: 1, pageSize: 50, hasMore: true, nextPage: 2,
    partial: true, warning: "Hub 目录尚未加载完；收录不代表可调用。", retryPage: null,
    hubTotals: { complete: false, fetched: items.length, errors: 0 },
    hubCoverage: { callability: "unknown" },
  }, extra);
}
function item(id, task = "text-to-image") { return { id, name: id, task, category: "image" }; }
const tests = [];
function test(name, fn) { tests.push({ name, fn }); }

test("initial ModelScope request sends category/query/page and waits for a click", async () => {
  const h = harness();
  h.elements.serviceFilter.value = "Krea & 新模型";
  const loading = h.loadCatalog();
  const q = new URL(h.requests[0].url, "http://offline.invalid").searchParams;
  assert.equal(q.get("backend"), "modelscope-ai");
  assert.equal(q.get("category"), "image");
  assert.equal(q.get("q"), "Krea & 新模型");
  assert.equal(q.get("page"), "1");
  assert.equal(q.get("pageSize"), "50");
  assert.ok(h.timeoutDelays().includes(60000), "ModelScope cold Hub list is 60s not 180s");
  assert.ok(!h.timeoutDelays().includes(180000));
  await h.respond(0, page([item("Hub/Model-A")]));
  assert.equal(await loading, true);
  assert.deepEqual(h.ids(), ["Hub/Model-A"], "server search rows are not filtered a second time");
  assert.equal(h.elements.service.value, "", "do not auto-select a model");
  assert.equal(h.requests.length, 1, "no automatic next-page fetch");
  assert.match(h.elements.catalogHint.textContent, /Hub/);
  assert.match(h.elements.catalogHint.textContent, /未验证|未知|不代表可调用/);
  assert.equal(h.elements.catalogMore.hidden, false);
  assert.equal(h.elements.catalogRetry.hidden, true, "partial coverage alone is not a retryable error");
});

test("ModelScope search input starts a fresh first-page request after debounce", async () => {
  const h = harness();
  h.loadCatalog();
  await h.respond(0, page([item("Hub/Initial")], { hasMore: false, nextPage: null }));
  h.elements.serviceFilter.value = "new query";
  h.elements.serviceFilter.fire("input");
  await h.timers(120);
  assert.equal(h.requests.length, 2);
  const q = new URL(h.requests[1].url, "http://offline.invalid").searchParams;
  assert.equal(q.get("q"), "new query");
  assert.equal(q.get("page"), "1");
  await h.respond(1, page([item("Hub/New")], { hasMore: false, nextPage: null }));
  assert.deepEqual(h.ids(), ["Hub/New"]);
});

test("manual next page appends IDs once and retains a user selection made in flight", async () => {
  const h = harness();
  h.loadCatalog();
  await h.respond(0, page([item("Hub/A"), item("Hub/B")]));
  h.elements.service.value = "Hub/A";
  await h.click("catalogMore");
  assert.equal(new URL(h.requests[1].url, "http://offline.invalid").searchParams.get("page"), "2");
  assert.equal(h.elements.service.disabled, false, "loaded models remain interactive");
  h.elements.service.value = "Hub/B";
  h.elements.service.fire("change");
  await h.respond(1, page([item("Hub/A"), item("Hub/A", "image-to-image"), item("Hub/C")], {
    page: 2, hasMore: false, nextPage: null, partial: false, warning: "",
    hubTotals: { complete: true, fetched: 53, errors: 0 },
  }));
  assert.deepEqual(h.ids().slice().sort(), ["Hub/A", "Hub/B", "Hub/C"]);
  assert.equal(h.elements.service.value, "Hub/B");
  assert.equal(h.elements.catalogMore.hidden, true);
  assert.match(h.elements.catalogHint.textContent, /目录|Hub/);
  assert.doesNotMatch(h.elements.catalogHint.textContent, /可生成全量|全量可生成/);
});

test("failed continuation preserves loaded rows and retries the same page", async () => {
  const h = harness("modelscope-cn");
  h.loadCatalog();
  await h.respond(0, page([item("Hub/A")]));
  h.elements.service.value = "Hub/A";
  await h.click("catalogMore");
  await h.reject(1);
  assert.deepEqual(h.ids(), ["Hub/A"]);
  assert.equal(h.elements.service.value, "Hub/A");
  assert.equal(h.elements.service.disabled, false);
  assert.match(h.elements.catalogHint.textContent, /失败/);
  await h.click("catalogRetry");
  assert.equal(new URL(h.requests[2].url, "http://offline.invalid").searchParams.get("page"), "2");
  await h.respond(2, page([item("Hub/B")], { page: 2, nextPage: 3 }));
  assert.deepEqual(h.ids().slice().sort(), ["Hub/A", "Hub/B"]);
  assert.equal(h.elements.service.value, "Hub/A");
});

test("late response from an old query cannot replace the current query rows", async () => {
  const h = harness();
  h.loadCatalog();
  h.elements.serviceFilter.value = "old";
  h.elements.serviceFilter.fire("input");
  h.loadCatalog();
  assert.equal(h.requests.length, 2);
  assert.equal(h.requests[0].signal.aborted, true, "superseded request is aborted");
  await h.respond(1, page([item("Hub/New")], { hasMore: false, nextPage: null }));
  await h.respond(0, page([item("Hub/Old")], { hasMore: false, nextPage: null }));
  assert.deepEqual(h.ids(), ["Hub/New"]);
  assert.equal(h.state.catalogPaging.key, "modelscope-ai:image:old");
});

test("mode switch requests the matching category and ignores a late old-mode page", async () => {
  const h = harness();
  h.loadCatalog();
  h.setMode("video");
  assert.equal(h.requests.length, 2);
  const q = new URL(h.requests[1].url, "http://offline.invalid").searchParams;
  assert.equal(q.get("category"), "video");
  await h.respond(1, page([{ id: "Hub/Video/image-to-video", name: "video", task: "image-to-video", category: "video" }], {
    page: 1, hasMore: false, nextPage: null,
  }));
  await h.respond(0, page([item("Hub/Old")], { hasMore: false, nextPage: null }));
  assert.deepEqual(h.ids(), ["Hub/Video/image-to-video"]);
  assert.equal(h.state.catalogPaging.key, "modelscope-ai:video:");
});

test("retryPage takes precedence over nextPage without discarding partial page rows", async () => {
  const h = harness();
  h.loadCatalog();
  await h.respond(0, page([item("Hub/A")], {
    retryPage: 1, warning: "部分上游目录暂时不可用，请重试本页。",
    hubTotals: { complete: false, fetched: 1, errors: 1 },
  }));
  assert.equal(h.elements.catalogMore.hidden, true, "do not skip a failed page");
  h.elements.service.value = "Hub/A";
  await h.click("catalogRetry");
  assert.equal(new URL(h.requests[1].url, "http://offline.invalid").searchParams.get("page"), "1");
  await h.respond(1, page([item("Hub/A"), item("Hub/B")]));
  assert.deepEqual(h.ids().slice().sort(), ["Hub/A", "Hub/B"]);
  assert.equal(h.elements.service.value, "Hub/A");
  assert.equal(h.elements.catalogRetry.hidden, true);
  assert.equal(h.elements.catalogMore.hidden, false);
});

test("loadCatalog stays a function declaration and catalog abort is 20s", () => {
  assert.match(source, /function loadCatalog\s*\(/);
  assert.doesNotMatch(source, /(?:const|let)\s+loadCatalog\s*=/);
  assert.match(source, /CATALOG_FETCH_TIMEOUT_MS = 20000/);
  assert.match(source, /CATALOG_MODELSCOPE_TIMEOUT_MS = 60000/);
  assert.doesNotMatch(source, /abort\(\),\s*180000/);
  assert.match(source, /function isPagedCatalog\s*\(/);
  assert.match(source, /be === "huggingface"/);
});

test("HuggingFace first page sends page/pageSize and shows Hub paging chrome", async () => {
  const h = harness("huggingface");
  h.elements.serviceFilter.value = "Krea";
  const loading = h.loadCatalog();
  const q = new URL(h.requests[0].url, "http://offline.invalid").searchParams;
  assert.equal(q.get("backend"), "huggingface");
  assert.equal(q.get("category"), "image");
  assert.equal(q.get("q"), "Krea");
  assert.equal(q.get("page"), "1");
  assert.equal(q.get("pageSize"), "50");
  assert.ok(h.timeoutDelays().includes(20000));
  assert.ok(!h.timeoutDelays().includes(180000));
  await h.respond(0, page([item("krea/Krea-2-Turbo"), item("org/Other")]));
  assert.equal(await loading, true);
  assert.equal(h.ids()[0], "krea/Krea-2-Turbo", "pin stays visible when present in the page");
  assert.ok(h.ids().includes("org/Other"));
  assert.equal(h.elements.service.value, "", "do not auto-select a model");
  assert.equal(h.requests.length, 1, "no automatic next-page fetch");
  assert.equal(h.elements.catalogStatus.hidden, false);
  assert.doesNotMatch(h.elements.catalogHint.textContent, /ModelScope/);
  assert.equal(h.elements.catalogMore.hidden, false);
  assert.equal(h.elements.catalogRetry.hidden, true);
});

test("HuggingFace load-more appends and missing pin is not synthesized", async () => {
  const h = harness("huggingface");
  h.state._pinHfLoraService = "krea/Krea-2-Turbo";
  h.loadCatalog();
  await h.respond(0, page([item("org/Page-A")]));
  assert.deepEqual(h.ids(), ["org/Page-A"]);
  assert.ok(!h.ids().includes("krea/Krea-2-Turbo"), "do not fabricate a pin row");
  assert.equal(h.elements.service.value, "");
  h.elements.service.value = "org/Page-A";
  await h.click("catalogMore");
  assert.equal(new URL(h.requests[1].url, "http://offline.invalid").searchParams.get("page"), "2");
  assert.equal(new URL(h.requests[1].url, "http://offline.invalid").searchParams.get("pageSize"), "50");
  await h.respond(1, page([item("krea/Krea-2-Turbo"), item("org/Page-B")], {
    page: 2, hasMore: false, nextPage: null, partial: false, warning: "",
    hubTotals: { complete: true, fetched: 2, errors: 0 },
  }));
  assert.ok(h.ids().includes("org/Page-A"));
  assert.ok(h.ids().includes("org/Page-B"));
  assert.ok(h.ids().includes("krea/Krea-2-Turbo"), "pin appears when the page actually contains it");
  assert.equal(h.elements.service.value, "org/Page-A");
  assert.equal(h.elements.catalogMore.hidden, true);
});

test("HuggingFace retry keeps loaded rows; AbortError stays 人话", async () => {
  const h = harness("huggingface");
  h.loadCatalog();
  await h.respond(0, page([item("org/A")]));
  h.elements.service.value = "org/A";
  await h.click("catalogMore");
  const aborted = new Error("The operation was aborted.");
  aborted.name = "AbortError";
  await h.reject(1, aborted);
  assert.deepEqual(h.ids(), ["org/A"]);
  assert.equal(h.elements.service.value, "org/A");
  assert.match(h.elements.msg.textContent, /请求超时，请重试本页/);
  assert.doesNotMatch(h.elements.msg.textContent, /AbortError|The operation was aborted/);
  assert.equal(h.elements.catalogRetry.hidden, false);
  await h.click("catalogRetry");
  assert.equal(new URL(h.requests[2].url, "http://offline.invalid").searchParams.get("page"), "2");
  await h.respond(2, page([item("org/B")], { page: 2, nextPage: 3 }));
  assert.deepEqual(h.ids().slice().sort(), ["org/A", "org/B"]);
});

test("Fal and Civitai stay one-shot with the same 20s timeout", async () => {
  for (const backend of ["fal", "civitai"]) {
    const h = harness(backend);
    const loading = h.loadCatalog();
    const q = new URL(h.requests[0].url, "http://offline.invalid").searchParams;
    assert.equal(q.get("backend"), backend);
    assert.equal(q.get("page"), null);
    assert.equal(q.get("pageSize"), null);
    assert.ok(h.timeoutDelays().includes(20000), backend + " first fetch is 20s");
    assert.ok(!h.timeoutDelays().includes(180000), backend + " must not wait 180s");
    await h.respond(0, { items: [item(backend === "fal" ? "fal-ai/flux/schnell" : "image/comfy/demo")] });
    assert.equal(await loading, true);
    assert.equal(h.elements.catalogStatus.hidden, true, backend + " has no Hub paging chrome");
    assert.equal(h.elements.service.value, "", "one-shot empty stays empty");
  }
});

test("switching backend cancels in-flight HuggingFace catalog", async () => {
  const h = harness("huggingface");
  h.loadCatalog();
  assert.equal(h.requests.length, 1);
  h.elements.backend.value = "fal";
  h.elements.backend.fire("change");
  assert.equal(h.requests[0].signal.aborted, true);
  assert.equal(h.requests.length, 2);
  const q = new URL(h.requests[1].url, "http://offline.invalid").searchParams;
  assert.equal(q.get("backend"), "fal");
  assert.equal(q.get("page"), null);
  await h.respond(1, { items: [item("fal-ai/flux/schnell")] });
  assert.equal(h.elements.catalogStatus.hidden, true);
});

test("one-shot AbortError is 人话", async () => {
  const h = harness("fal");
  const loading = h.loadCatalog();
  const aborted = new Error("The operation was aborted.");
  aborted.name = "AbortError";
  await h.reject(0, aborted);
  assert.equal(await loading, false);
  assert.match(h.elements.msg.textContent, /请求超时，请切换 Provider 后重试/);
  assert.doesNotMatch(h.elements.msg.textContent, /AbortError|The operation was aborted/);
});

(async () => {
  let failed = 0;
  for (const entry of tests) {
    try { await entry.fn(); console.log("PASS " + entry.name); }
    catch (error) { failed++; console.error("FAIL " + entry.name + "\n" + error.stack); }
  }
  console.log(`${tests.length - failed}/${tests.length} offline VM checks passed (not live integration acceptance)`);
  if (failed) process.exitCode = 1;
})();
