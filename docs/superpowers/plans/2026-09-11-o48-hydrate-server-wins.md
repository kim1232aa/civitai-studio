# o48 — hydrate server url wins

**Stamp:** `v0821o48-hydrate-server-wins`

o46b belt wrote graph shot-1 to new /out; hard refresh kept old localStorage url.
Fix: hydrateFromServer — same shot id + server url non-empty → adopt server (overwrite local).
