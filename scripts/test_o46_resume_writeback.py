#!/usr/bin/env python3
"""o46/o46b: pending resume + local /out rebuild when upstream failed."""
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

    import importlib
    import providers.pending_jobs as pj
    importlib.reload(pj)
    import server
    importlib.reload(server)

    pj.register_pending("job-abc", "shot-1", "modelscope-ai")
    assert pj.get_pending("job-abc")["shotId"] == "shot-1"

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
    g2 = server.read_storyboard_graph()
    assert g2["nodes"][0]["url"] == "/out/new-2ad94576.png"
    assert pj.get_pending("job-abc") is None

    local = pj.find_local_out_saved(
        "modelscope-ai|2ad94576-35b7-47c4-8765-f19f6cf1fbe2",
        out_dir=ROOT / "out",
    )
    assert local and "/out/" in local[0]["url"] and local[0]["url"].endswith("_0.png"), local

    html = (ROOT / "static" / "storyboard.html").read_text()
    js = (ROOT / "static" / "storyboard.js").read_text()
    assert "v0821o46b-local-out-resume" in html
    assert "20260911-o46blocaloutresume" in html
    assert "find_local_out_saved" in (ROOT / "server.py").read_text()
    assert "上游失败但本地成片已写回原卡" in js
    assert "localOutResume" in (ROOT / "server.py").read_text()

    print("PASS o46_resume_writeback")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
