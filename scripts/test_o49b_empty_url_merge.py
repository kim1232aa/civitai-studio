#!/usr/bin/env python3
"""o49b: write_storyboard_graph empty url does not wipe existing non-empty."""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> int:
    td = tempfile.mkdtemp(prefix="o49b-empty-")
    os.environ["STORYBOARD_GRAPH_PATH"] = str(Path(td) / "storyboard_graph.json")
    os.environ["PENDING_JOBS_PATH"] = str(Path(td) / "pending_jobs.json")

    import importlib
    import server

    importlib.reload(server)

    server.write_storyboard_graph(
        {
            "cam": {"x": 0, "y": 0, "s": 1},
            "nodes": [
                {
                    "id": "shot-1",
                    "kind": "shot",
                    "title": "t",
                    "url": "/out/keep-me.png",
                    "urlUpdatedAt": 111,
                    "_urlUpdatedAt": 111,
                    "x": 0,
                    "y": 0,
                }
            ],
            "edges": [],
        }
    )

    # Incoming empty url for same id must preserve existing
    server.write_storyboard_graph(
        {
            "cam": {"x": 0, "y": 0, "s": 1},
            "nodes": [
                {"id": "shot-1", "kind": "shot", "title": "t", "url": "", "x": 1, "y": 1},
            ],
            "edges": [],
        }
    )
    g = server.read_storyboard_graph()
    assert g["nodes"][0]["url"] == "/out/keep-me.png", g["nodes"][0]
    assert g["nodes"][0].get("urlUpdatedAt") == 111 or g["nodes"][0].get("_urlUpdatedAt") == 111

    # Missing url key likewise
    server.write_storyboard_graph(
        {
            "cam": {"x": 0, "y": 0, "s": 1},
            "nodes": [
                {"id": "shot-1", "kind": "shot", "title": "t2", "x": 2, "y": 2},
            ],
            "edges": [],
        }
    )
    g2 = server.read_storyboard_graph()
    assert g2["nodes"][0]["url"] == "/out/keep-me.png", g2["nodes"][0]

    # Non-empty incoming still replaces
    server.write_storyboard_graph(
        {
            "cam": {"x": 0, "y": 0, "s": 1},
            "nodes": [
                {"id": "shot-1", "kind": "shot", "title": "t3", "url": "/out/new.png", "x": 3, "y": 3},
            ],
            "edges": [],
        }
    )
    g3 = server.read_storyboard_graph()
    assert g3["nodes"][0]["url"] == "/out/new.png"

    js = (ROOT / "static" / "storyboard.js").read_text()
    assert "prefer not sending blank" in js or "delete n.url" in js

    print("PASS o49b_empty_url_merge")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
