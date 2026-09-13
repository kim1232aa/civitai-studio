"""Pending generate jobs: jobId ↔ shotId for resume writeback after tab death.

Client + server share data/pending_jobs.json so clean-profile hydrate can resume.
o58: completing a job without a node/shot id is incomplete, not success.
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
GRAPH_PATH = Path(
    os.environ.get("STORYBOARD_GRAPH_PATH", str(ROOT / "data" / "storyboard_graph.json"))
)
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
    sid = (shot_id or "").strip() or str(extra.get("nodeId") or "").strip()
    if not jid or not sid:
        raise ValueError("jobId and shotId required")
    data = _read()
    jobs = data.setdefault("jobs", {})
    for old_jid in list(jobs.keys()):
        if old_jid == jid:
            continue
        rec_old = jobs.get(old_jid)
        if isinstance(rec_old, dict) and str(rec_old.get("shotId") or rec_old.get("nodeId") or "").strip() == sid:
            del jobs[old_jid]
    rec = {
        "shotId": sid,
        "nodeId": str(extra.get("nodeId") or sid).strip(),
        "backend": (backend or "").strip(),
        "startedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    for k, v in extra.items():
        if v is not None and k not in rec:
            rec[k] = v
    jobs[jid] = rec
    data["jobs"] = jobs
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


def find_local_out_saved(job_id: str, out_dir: Path | None = None) -> list[dict]:
    """If upstream poll fails but materialize already wrote /out, rebuild saved[]."""
    from .http import DEFAULT_OUT, parse_job_id

    jid = (job_id or "").strip()
    if not jid:
        return []
    out = Path(out_dir or DEFAULT_OUT)
    if not out.is_dir():
        return []
    backend, opaque = parse_job_id(jid)
    stem = jid.replace("|", "_").replace("/", "_")
    opaque_stem = str(opaque or "").replace("|", "_").replace("/", "_")
    patterns = [f"{stem}_*"]
    if backend and opaque_stem:
        patterns.append(f"{backend}_{opaque_stem}_*")
    if opaque_stem and len(opaque_stem) >= 8:
        patterns.append(f"*{opaque_stem}_*")
    media_ext = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".mp4", ".webm"}
    found: dict[str, Path] = {}
    for pat in patterns:
        for fp in out.glob(pat):
            if not fp.is_file():
                continue
            if fp.suffix.lower() not in media_ext:
                continue
            key = fp.name
            if key not in found:
                found[key] = fp
    if not found:
        return []

    def sort_key(name: str):
        import re
        m = re.search(r"_(\d+)\.[^.]+$", name)
        return (int(m.group(1)) if m else 9999, name)

    ordered = sorted(found.keys(), key=sort_key)
    saved = []
    for name in ordered:
        saved.append({
            "file": name,
            "url": f"/out/{name}",
            "bytes": found[name].stat().st_size,
            "kind": "video" if found[name].suffix.lower() in (".mp4", ".webm") else "image",
            "source": "local-out",
        })
    return saved


def node_id_of(rec: dict[str, Any] | None) -> str:
    if not isinstance(rec, dict):
        return ""
    return str(rec.get("nodeId") or rec.get("shotId") or "").strip()


def read_storyboard_graph(path: Path | None = None) -> dict[str, Any]:
    fp = Path(path or GRAPH_PATH)
    if not fp.exists():
        return {"cam": {"x": 0, "y": 0, "s": 1}, "nodes": [], "edges": []}
    try:
        data = json.loads(fp.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"cam": {"x": 0, "y": 0, "s": 1}, "nodes": [], "edges": []}
    if not isinstance(data, dict):
        return {"cam": {"x": 0, "y": 0, "s": 1}, "nodes": [], "edges": []}
    data.setdefault("nodes", [])
    data.setdefault("edges", [])
    return data


def write_storyboard_graph(graph: dict[str, Any], path: Path | None = None) -> None:
    fp = Path(path or GRAPH_PATH)
    fp.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(graph, ensure_ascii=False, indent=2) + "\n"
    fd, tmp_name = tempfile.mkstemp(prefix=f".{fp.name}.", suffix=".tmp", dir=fp.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, fp)
    except Exception:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def apply_job_media_to_graph(
    graph: dict[str, Any],
    job_id: str,
    media_url: str,
    pending: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Write media onto the originating node. No node id → incomplete, not Pass."""
    rec = pending if isinstance(pending, dict) else get_pending(job_id)
    if not rec:
        return {"updated": False, "skipped": "no_pending", "incomplete": True}
    nid = node_id_of(rec)
    if not nid:
        return {"updated": False, "skipped": "no_node", "incomplete": True}
    url = (media_url or "").strip()
    if not url:
        return {"updated": False, "skipped": "no_media", "incomplete": True}
    nodes = graph.get("nodes") if isinstance(graph.get("nodes"), list) else []
    hit = None
    for node in nodes:
        if isinstance(node, dict) and str(node.get("id") or "") == nid:
            hit = node
            break
    if hit is None:
        jid = (job_id or "").strip()
        for node in nodes:
            if isinstance(node, dict) and str(node.get("_jobId") or "").strip() == jid:
                hit = node
                nid = str(node.get("id") or "")
                break
    if hit is None:
        return {"updated": False, "skipped": "node_missing", "incomplete": True, "nodeId": nid}
    hit["url"] = url
    hit["mediaUrl"] = url
    hit["_jobId"] = (job_id or "").strip()
    now_ms = int(time.time() * 1000)
    hit["_urlUpdatedAt"] = now_ms
    hit["urlUpdatedAt"] = now_ms
    submitted = rec.get("submittedInput")
    if submitted is not None:
        hit["submittedInput"] = submitted
    backend = str(rec.get("backend") or "").strip()
    service = str(rec.get("serviceId") or rec.get("service") or rec.get("endpoint") or "").strip()
    if not backend:
        raw_jid = str(job_id or "")
        backend = raw_jid.split("|", 1)[0].strip() if "|" in raw_jid else ""
    if backend:
        hit["_backend"] = backend
        composer = hit.get("composer") if isinstance(hit.get("composer"), dict) else {}
        composer = dict(composer)
        composer.setdefault("backend", backend)
        composer.setdefault("mode", hit.get("mode") or "image")
        if service:
            composer["service"] = service
        fields = composer.get("fields") if isinstance(composer.get("fields"), dict) else {}
        fields = dict(fields)
        if hit.get("prompt") and not fields.get("prompt"):
            fields["prompt"] = hit.get("prompt")
        composer["fields"] = fields
        hit["composer"] = composer
        if service:
            hit["serviceId"] = service
    hit["_error"] = ""
    hit["error"] = ""
    return {"updated": True, "nodeId": nid, "url": url, "mediaUrl": url, "incomplete": False}


def complete_pending_job(job_id: str, media_url: str) -> dict[str, Any]:
    """Apply media to the persisted storyboard graph and drop the pending row on success."""
    rec = get_pending(job_id)
    if not rec:
        return {"updated": False, "skipped": "no_pending", "incomplete": True}
    if not node_id_of(rec):
        return {"updated": False, "skipped": "no_node", "incomplete": True}
    graph = read_storyboard_graph()
    result = apply_job_media_to_graph(graph, job_id, media_url, pending=rec)
    if result.get("updated"):
        write_storyboard_graph(graph)
        clear_pending(job_id)
    return result
