"""Serve-time UI patch: v0737 → v0738 click/hash → v0739 storage/cost/nsfw."""
from __future__ import annotations


def _patch_v0738(html: str) -> str:
    if not html:
        return html
    html = html.replace("v0737", "v0738")
    old_go = """window.__studioGo = function (ev) {
  try { if (ev) { ev.preventDefault(); ev.stopPropagation(); if (ev.stopImmediatePropagation) ev.stopImmediatePropagation(); } } catch (e) {}
  if (window.__goOnce && (Date.now() - window.__goOnce) < 500) return false;
  window.__goOnce = Date.now();
  try { setDock('已点到生成'); } catch (e) {}
  if (typeof onGenerate === 'function') {"""
    new_go = """window.__studioGo = function (ev) {
  try { if (ev) { ev.preventDefault(); ev.stopPropagation(); if (ev.stopImmediatePropagation) ev.stopImmediatePropagation(); } } catch (e) {}
  try { lastGoClick = Date.now(); } catch (e) {}
  try { fetch('/api/go?t=' + Date.now()); } catch (e) {}
  try {
    const d = document.getElementById('dockStatus');
    if (d) { d.className = ''; d.textContent = '已点到生成'; }
  } catch (e) {}
  try { if (typeof setDock === 'function') setDock('已点到生成'); } catch (e) {}
  if (window.__goOnce && (Date.now() - window.__goOnce) < 400) return false;
  window.__goOnce = Date.now();
  if (typeof onGenerate === 'function') {"""
    if old_go in html:
        html = html.replace(old_go, new_go, 1)
    old_after = """  return false;
};
function isModelscope(b) {"""
    new_after = """  return false;
};
if (!window.__goBound) {
  window.__goBound = true;
  document.addEventListener('click', function (ev) {
    const t = ev.target && ev.target.closest && ev.target.closest('#go');
    if (!t) return;
    window.__studioGo(ev);
  }, true);
}
function isModelscope(b) {"""
    if old_after in html and "window.__goBound" not in html:
        html = html.replace(old_after, new_after, 1)
    old_boot = "let backend = savedBackend() || 'civitai';\nlet selected = null;"
    new_boot = "let backend = savedBackend() || 'civitai';\ntry { persistBackend(backend); } catch (e) {}\nlet selected = null;"
    if old_boot in html and "try { persistBackend(backend); }" not in html:
        html = html.replace(old_boot, new_boot, 1)
    old_vars = "let goBusy = false;\nlet lastGoFail = 0;\nlet noToken = false;"
    new_vars = "let goBusy = false;\nlet lastGoFail = 0;\nlet lastGoClick = 0;\nlet noToken = false;"
    if old_vars in html and "let lastGoClick" not in html:
        html = html.replace(old_vars, new_vars, 1)
    old_hold = """    if (lastGoFail && (Date.now() - lastGoFail) < 8000) return true;
  } catch (e) {}
  return false;
}"""
    new_hold = """    if (lastGoFail && (Date.now() - lastGoFail) < 8000) return true;
    if (lastGoClick && (Date.now() - lastGoClick) < 8000) return true;
  } catch (e) {}
  return false;
}"""
    if old_hold in html and "lastGoClick && (Date.now() - lastGoClick)" not in html:
        html = html.replace(old_hold, new_hold, 1)
    old_fail = """    lastGoFail = Date.now();
    setDock(msg, 'bad');"""
    new_fail = """    lastGoFail = Date.now();
    lastGoClick = Date.now();
    setDock(msg, 'bad');"""
    if old_fail in html and "lastGoClick = Date.now();\n    setDock(msg, 'bad')" not in html:
        html = html.replace(old_fail, new_fail, 1)
    old_end = """  const go = $('go');
  if (go) {
    const fire = (ev) => { window.__studioGo(ev); };
    go.addEventListener('click', fire, true);
  }
})();"""
    new_end = """  const go = $('go');
  if (go) {
    const fire = (ev) => { window.__studioGo(ev); };
    go.addEventListener('click', fire, true);
  }
  window.addEventListener('hashchange', () => {
    try {
      const h = (location.hash || '').replace(/^#/, '').split('&')[0];
      if (!/^(civitai|fal|huggingface|modelscope-ai|modelscope-cn)$/.test(h)) {
        persistBackend(backend);
        return;
      }
      if (h === backend) return;
      backend = h;
      persistBackend(h);
      const box = $('backendSwitch');
      if (box) box.querySelectorAll('button').forEach(x => x.classList.toggle('on', x.dataset.backend === h));
      userPickedId = null;
      selected = null;
      if ($('svcFilter')) $('svcFilter').value = '';
      syncBackendChrome();
      syncImportChrome();
      loadCatalog().catch(() => setStatus(((window._providerLabel || {})[h] || h) + ' 目录失败', 'bad'));
    } catch (e) {}
  });
})();"""
    if old_end in html and "window.addEventListener('hashchange'" not in html:
        html = html.replace(old_end, new_end, 1)
    return html


def _patch_v0739(html: str) -> str:
    if not html:
        return html
    html = html.replace("v0738", "v0739").replace("v0737", "v0739")
    old_save = """function saveGallery() {
  localStorage.setItem(GAL_KEY, JSON.stringify(galleryItems.slice(0, 200)));
}"""
    new_save = """function saveGallery() {
  try { localStorage.setItem(GAL_KEY, JSON.stringify(galleryItems.slice(0, 200))); } catch (e) {}
}"""
    if old_save in html:
        html = html.replace(old_save, new_save, 1)
    old_load = """function loadGallery() {
  try { galleryItems = JSON.parse(localStorage.getItem(GAL_KEY) || '[]'); }
  catch (e) { galleryItems = []; }"""
    new_load = """function loadGallery() {
  try { galleryItems = JSON.parse((function(){ try { return localStorage.getItem(GAL_KEY) || '[]'; } catch (e) { return '[]'; } })()); }
  catch (e) { galleryItems = []; }"""
    if old_load in html:
        html = html.replace(old_load, new_load, 1)
    old_onerror = "window.onerror = (m) => setStatus('页面出错: ' + m, 'bad');"
    new_onerror = """window.onerror = (m) => {
  const s = String(m || '');
  if (/localStorage|sessionStorage|sandboxed|allow-same-origin/i.test(s)) return;
  setStatus('页面出错: ' + m, 'bad');
};"""
    if old_onerror in html:
        html = html.replace(old_onerror, new_onerror, 1)
    old_whatif = """  setStatus('预估中…');
  try {
    const j = await api('/api/whatif', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload()) });
    const total = (j.cost || {}).total ?? ((j.transactions || {}).list || []).reduce((s, x) => s + (x.amount || 0), 0);
    $('cost').textContent = `预估 ${total} yellow buzz` + (j.transactions && j.transactions.insufficientBuzz ? ' · Buzz 不够' : '');
    setStatus('预估完成');
  } catch (e) { setStatus('预估失败 ' + (e.data ? JSON.stringify(e.data).slice(0, 200) : e.message), 'bad'); }
};"""
    new_whatif = """  if ($('cost')) $('cost').textContent = '预估中…';
  setStatus('预估中…');
  try {
    const j = await api('/api/whatif', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload()) });
    const note = (j.cost || {}).note || j.note || '';
    const listed = ((j.transactions || {}).list || []).reduce((s, x) => s + (x.amount || 0), 0);
    const total = (j.cost || {}).total;
    const n = (total == null || total === '') ? listed : total;
    let line;
    if (n !== 0 && n != null && n !== '') line = '预估 ' + n + ' yellow buzz';
    else if (note) line = note;
    else line = '预估 ' + (n == null ? '?' : n) + ' yellow buzz';
    if (j.transactions && j.transactions.insufficientBuzz) line += ' · Buzz 不够';
    if ($('cost')) $('cost').textContent = line;
    setStatus('预估完成');
  } catch (e) {
    const msg = (e.data && (e.data.error || e.data.detail)) || e.message || '预估失败';
    if ($('cost')) $('cost').textContent = '预估失败';
    setStatus('预估失败 ' + (e.data ? JSON.stringify(e.data).slice(0, 200) : msg), 'bad');
  }
};"""
    if old_whatif in html:
        html = html.replace(old_whatif, new_whatif, 1)
    old_search = "const j = await api('/api/search?type=LORA&q=' + encodeURIComponent(q));"
    new_search = "const j = await api('/api/search?type=LORA&q=' + encodeURIComponent(q) + '&nsfw=' + ($('mature') && $('mature').checked ? 'true' : 'false'));"
    if old_search in html:
        html = html.replace(old_search, new_search, 1)
    return html


def patch_index(html: str) -> str:
    if not html:
        return html
    if any(v in html for v in ("v0739", "v0740", "v0741", "v0742", "v0743", "v0744", "v0745")) and "sandboxed" in html:
        return html
    if "v0737" in html or ("v0738" not in html):
        html = _patch_v0738(html)
    return _patch_v0739(html)


if __name__ == "__main__":
    from pathlib import Path
    target = Path(__file__).resolve().parent / "static" / "index.html"
    raw = target.read_text(encoding="utf-8")
    out = patch_index(raw)
    if out != raw:
        target.write_text(out, encoding="utf-8")
        print("patched", target, "v0739" if "v0739" in out else "unknown")
    else:
        print("already current", target)
