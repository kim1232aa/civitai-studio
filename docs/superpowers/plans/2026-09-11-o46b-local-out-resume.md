# o46b — local /out resume when upstream failed

**Stamp:** `v0821o46b-local-out-resume`

**Why:** Edit-2509 job later polls FAILED (`invalid response format`) with empty `saved[]`, but `/out/modelscope-ai_<uuid>_0.png` already exists. o46 cleared pending on failed → hard-refresh never writeback.

**Fix:** `find_local_out_saved(jobId)` rebuilds saved[]; GET `/api/jobs` injects it + applies pending graph writeback; client resume writebacks before clear; clear pending on failed only when no local out.
