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
  try { setDock('already-clicked-placeholder'); } catch (e) {}
  if (typeof onGenerate === 'function') {"""
