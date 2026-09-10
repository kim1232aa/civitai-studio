#!/usr/bin/env python3
"""o46: pending job register/clear + apply to storyboard graph shot.url."""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

def main():
    td = tempfile.mkdtemp(prefix="o46-")
    os.environ["PENDING_JOBS_PATH"] = str(Path(td) / "pending_jobs.json")
    os.environ["STORYBOARD_GRAPH_PATH"] = str(Path(td) / "storyboard_graph.json")

    # re-import with env
    import importlib
    import providers.pending_jobs as pj
    importlib.reload(pj)
    import server
    importlib.reload(server)

    pj.register_pending("job-abc", "shot-1", "modelscope-ai")
    assert pj.get_pending("job-abc")["shotId"] == "shot-1"
    jobs = pj.list_pending()
    assert any(j["jobId"] == "job-abc" for j in jobs)

    graph = {
        "cam": {"x": 0, "y": 0, "s": 1},
        "nodes": [
            {"id": "shot-1", "kind": "shot", "title": "t", "url": "/out/old.png", "x": 0, "y": 0},
        ],
        "edges": [],
    }
    server.write_storyboard_graph(graph)
    applied = server.apply_pending_job_to_graph("job-abc", "/out/new-2ad94576.png")
    assert applied and applied["updated"] is True
    assert applied["url"] == "/out/new-2ad94576.png"
    g2 = server.read_storyboard_graph()
    assert g2["nodes"][0]["url"] == "/out/new-2ad94576.png"
    assert pj.get_pending("job-abc") is None

    # no double-apply
    pj.register_pending("job-abc", "shot-1", "modelscope-ai")
    applied2 = server.apply_pending_job_to_graph("job-abc", "/out/new-2ad94576.png")
    assert applied2 and applied2["updated"] is False  # same url

    html = (ROOT / "static" / "storyboard.html").read_text()
    js = (ROOT / "static" / "storyboard.js").read_text()
    assert "v0821o46-resume-job-writeback" in html
    assert "20260911-o46resumejobwriteback" in html
    assert "PENDING_JOBS_KEY" in js and "resumePendingJobs" in js
    assert "registerPendingJob" in js

    print("PASS o46_resume_writeback")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
