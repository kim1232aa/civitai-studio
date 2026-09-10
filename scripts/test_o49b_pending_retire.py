#!/usr/bin/env python3
"""o49b: register new job retires old same-shot; apply old jobId does not overwrite."""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> int:
    td = tempfile.mkdtemp(prefix="o49b-pend-")
    os.environ["PENDING_JOBS_PATH"] = str(Path(td) / "pending_jobs.json")
    os.environ["STORYBOARD_GRAPH_PATH"] = str(Path(td) / "storyboard_graph.json")

    import importlib
    import providers.pending_jobs as pj
    import server

    importlib.reload(pj)
    importlib.reload(server)

    pj.register_pending("job-old", "shot-1", "fal")
    assert pj.get_pending("job-old")["shotId"] == "shot-1"

    pj.register_pending("job-new", "shot-1", "fal")
    assert pj.get_pending("job-old") is None, "old same-shot pending must be retired"
    assert pj.get_pending("job-new")["shotId"] == "shot-1"

    # Different shot unaffected
    pj.register_pending("job-other", "shot-2", "fal")
    assert pj.get_pending("job-new") is not None
    assert pj.get_pending("job-other") is not None

    # apply retired job → no-op
    server.write_storyboard_graph(
        {
            "cam": {"x": 0, "y": 0, "s": 1},
            "nodes": [
                {"id": "shot-1", "kind": "shot", "title": "t", "url": "/out/fresh.png", "_jobId": "job-new", "x": 0, "y": 0},
            ],
            "edges": [],
        }
    )
    applied = server.apply_pending_job_to_graph("job-old", "/out/stale.png")
    assert applied is None, "retired pending apply must no-op"
    g = server.read_storyboard_graph()
    assert g["nodes"][0]["url"] == "/out/fresh.png"

    # apply with job_mismatch when shot._jobId differs
    pj.register_pending("job-stale", "shot-1", "fal")  # retires job-new from pending store
    # Re-set graph with _jobId=job-new and non-empty url; pending is job-stale
    server.write_storyboard_graph(
        {
            "cam": {"x": 0, "y": 0, "s": 1},
            "nodes": [
                {
                    "id": "shot-1",
                    "kind": "shot",
                    "title": "t",
                    "url": "/out/fresh.png",
                    "_jobId": "job-new",
                    "x": 0,
                    "y": 0,
                },
            ],
            "edges": [],
        }
    )
    skipped = server.apply_pending_job_to_graph("job-stale", "/out/stale-2.png")
    assert skipped and skipped.get("updated") is False and skipped.get("skipped") == "job_mismatch"
    assert pj.get_pending("job-stale") is None
    g2 = server.read_storyboard_graph()
    assert g2["nodes"][0]["url"] == "/out/fresh.png"

    js = (ROOT / "static" / "storyboard.js").read_text()
    assert "retire" in js.lower() or "same shotId" in js or "shotId === sid" in js
    assert "shot._jobId" in js and "clearPendingJob(jid)" in js

    print("PASS o49b_pending_retire")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
