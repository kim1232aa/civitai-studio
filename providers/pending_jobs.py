"""Pending generate jobs: jobId ↔ shotId for resume writeback after tab death.

Client + server share data/pending_jobs.json so clean-profile hydrate can resume.
"""
from __future__ import annotations

import json
import os
import tempfile
import threading
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PENDING_PATH = Path(
    os.environ.get("PENDING_JOBS_PATH", str(ROOT / "data" / "pending_jobs.json"))
)
PENDING_PATH.parent.mkdir(parents=True, exist_ok=True)
_lock = threading.Lock()


def _read() -> dict[str, Any]:
    with _lock:
        if not PENDING_PATH.exists():
            return {"jobs": {}}
        try:
            data = json.loads(PENDING_PATH.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {"jobs": {}}
        if not isinstance(data, dict):
            return {"jobs": {}}
        jobs = data.get("jobs")
        if not isinstance(jobs, dict):
            data["jobs"] = {}
        return data


def _write(data: dict[str, Any]) -> None:
    PENDING_PATH.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    with _lock:
        fd, tmp_name = tempfile.mkstemp(
            prefix=f".{PENDING_PATH.name}.",
            suffix=".tmp",
            dir=PENDING_PATH.parent,
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(raw)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp_name, PENDING_PATH)
        except Exception:
            try:
                os.unlink(tmp_name)
            except OSError:
                pass
            raise


def list_pending() -> list[dict[str, Any]]:
    jobs = _read().get("jobs") or {}
    out = []
    for jid, rec in jobs.items():
        if not isinstance(rec, dict):
            continue
        row = dict(rec)
        row["jobId"] = jid
        out.append(row)
    return out


def get_pending(job_id: str) -> dict[str, Any] | None:
    jid = (job_id or "").strip()
    if not jid:
        return None
    rec = (_read().get("jobs") or {}).get(jid)
    if not isinstance(rec, dict):
        return None
    out = dict(rec)
    out["jobId"] = jid
    return out


def register_pending(job_id: str, shot_id: str, backend: str = "", **extra: Any) -> dict[str, Any]:
    jid = (job_id or "").strip()
    sid = (shot_id or "").strip()
    if not jid or not sid:
        raise ValueError("jobId and shotId required")
    data = _read()
    jobs = data.setdefault("jobs", {})
    rec = {
        "shotId": sid,
        "backend": (backend or "").strip(),
        "startedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    for k, v in extra.items():
        if v is not None and k not in rec:
            rec[k] = v
    jobs[jid] = rec
    _write(data)
    out = dict(rec)
    out["jobId"] = jid
    return out


def clear_pending(job_id: str) -> bool:
    jid = (job_id or "").strip()
    if not jid:
        return False
    data = _read()
    jobs = data.get("jobs") or {}
    if jid not in jobs:
        return False
    del jobs[jid]
    data["jobs"] = jobs
    _write(data)
    return True


def first_saved_url(data: dict | None) -> str:
    if not isinstance(data, dict):
        return ""
    def first(arr):
        if not arr:
            return ""
        x = arr[0]
        if isinstance(x, str):
            return x.strip()
        if isinstance(x, dict):
            return str(x.get("url") or x.get("path") or x.get("previewUrl") or "").strip()
        return ""
    hit = first(data.get("saved")) or first(data.get("files"))
    if hit:
        return hit
    result = data.get("result")
    if isinstance(result, dict):
        hit = first(result.get("saved")) or first(result.get("files"))
        if hit:
            return hit
    return ""
