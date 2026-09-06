#!/usr/bin/env python3
"""Regression test for the direct storyboard page route."""

from __future__ import annotations

import http.client
import sys
import threading
import time
import urllib.parse
from http.server import ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def get(base: str, path: str):
    parsed = urllib.parse.urlsplit(base)
    last_error = None
    for _ in range(20):
        connection = http.client.HTTPConnection(
            parsed.hostname, parsed.port, timeout=10
        )
        try:
            connection.request(
                "GET", path, headers={"User-Agent": "storyboard-route-test"}
            )
            response = connection.getresponse()
            return response.status, response.headers.get_content_type(), response.read()
        except (TimeoutError, ConnectionRefusedError) as error:
            last_error = error
            time.sleep(0.02)
        finally:
            connection.close()
    raise AssertionError(f"local test server did not become ready: {last_error}")


def main() -> int:
    server = __import__("server")
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{httpd.server_address[1]}"
    try:
        status, content_type, body = get(base, "/storyboard.html")
        assert status == 200, (status, body[:200])
        assert content_type == "text/html", content_type
        assert b"storyboard.js" in body, "storyboard page did not load its script"

        status, _, body = get(base, "/storyboard.html?from=route-test")
        assert status == 200, (status, body[:200])
    finally:
        httpd.shutdown()
        thread.join(timeout=5)
        httpd.server_close()

    print("ok storyboard-route")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
