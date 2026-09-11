#!/usr/bin/env python3
"""o58 T9: completed job writes media onto the originating card.

History-only success is a Fail. No live POST /api/generate.
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> int:
    td = tempfile.mkdtemp(prefix="o58-wb-")
    os.environ["PENDING_JOBS_PATH"] = str(Path(td) / "pending_jobs.json")
    os.environ["STORYBOARD_GRAPH_PATH"] = str(Path(td) / "storyboard_graph.json")

    import importlib
    import providers.pending_jobs as pj

    importlib.reload(pj)

    graph = {
        "cam": {"x": 0, "y": 0, "s": 1},
        "nodes": [
            {"id": "shot-7", "kind": "shot", "title": "hinablue", "url": "", "x": 0, "y": 0},
        ],
        "edges": [],
    }
    pj.write_storyboard_graph(graph)

    try:
        pj.register_pending("job-orphan", "", "fal")
        raise AssertionError("register without node id must fail")
    except ValueError:
        pass

    orphan = pj.apply_job_media_to_graph(
        graph, "job-orphan", "/out/history-only.png", pending={"backend": "fal"}
    )
    assert orphan.get("incomplete") is True
    assert orphan.get("updated") is False
    assert orphan.get("skipped") == "no_node"

    pj.register_pending("job-7", "shot-7", "fal", nodeId="shot-7")
    done = pj.complete_pending_job("job-7", "/out/hinablue-shot-7.png")
    assert done.get("updated") is True
    assert done.get("nodeId") == "shot-7"
    assert done.get("incomplete") is False

    reloaded = pj.read_storyboard_graph()
    node = reloaded["nodes"][0]
    assert node["id"] == "shot-7"
    assert node["url"] == "/out/hinablue-shot-7.png"
    assert node["mediaUrl"] == "/out/hinablue-shot-7.png"
    assert pj.get_pending("job-7") is None, "pending must clear after writeback"

    history_only = {"saved": [{"url": "/out/gallery.png"}], "nodes": []}
    fake = pj.apply_job_media_to_graph(
        {"nodes": [{"id": "shot-7", "url": ""}]},
        "job-x",
        "",
        pending={"shotId": "shot-7", "nodeId": "shot-7"},
    )
    assert fake.get("incomplete") is True
    assert history_only["saved"][0]["url"] == "/out/gallery.png"

    print("PASS o58_writeback_node")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
