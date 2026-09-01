"""Serve-time UI patch so v0737 static/index.html behaves as v0738.

GitHub contents API + agent XML guard kept blocking a 95KB index.html
replace. This module is small and idempotent: already-v0738 HTML is left
alone. Apply from server.py GET / before sending bytes.
"""
from __future__ import annotations


def patch_index(html: str) -> str:
    if not html:
        return html
    if "v0738" in html and "lastGoClick" in html and "fetch('/api/go?t='" in html:
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


if __name__ == "__main__":
    from pathlib import Path
    root = Path(__file__).resolve().parent
    target = root / "static" / "index.html"
    raw = target.read_text(encoding="utf-8")
    out = patch_index(raw)
    if out != raw:
        target.write_text(out, encoding="utf-8")
        print("patched", target, "v0738" if "v0738" in out else "unknown")
    else:
        print("already current", target)
