#!/usr/bin/env python3
"""Static JS/CSS must be served with charset=utf-8 so card titles/prompts don't mojibake."""
from __future__ import annotations

import sys
import threading
import time
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import server  # noqa: E402

fails = []


def check(name, cond, detail=""):
    if cond:
        print(f"  ok   {name}")
    else:
        fails.append(name)
        print(f"  FAIL {name} {detail}")


def get(base, path):
    req = urllib.request.Request(base + path, method="GET")
    for attempt in range(80):
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                return resp.status, dict(resp.headers), resp.read()
        except urllib.error.HTTPError as exc:
            return exc.code, dict(exc.headers), exc.read()
        except urllib.error.URLError:
            if attempt == 79:
                raise
            time.sleep(0.05)
    raise RuntimeError("unreachable")


httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
thread = threading.Thread(target=httpd.serve_forever, daemon=True)
thread.start()
base = f"http://127.0.0.1:{httpd.server_address[1]}"
try:
    st, headers, body = get(base, "/static/storyboard.js")
    ctype = headers.get("Content-Type") or headers.get("content-type") or ""
    check("storyboard.js 200", st == 200, str(st))
    check(
        "storyboard.js Content-Type 带 charset=utf-8",
        "javascript" in ctype.lower() and "charset=utf-8" in ctype.lower(),
        ctype,
    )
    check("storyboard.js 是合法 UTF-8", True)
    try:
        text = body.decode("utf-8")
    except UnicodeDecodeError as exc:
        check("storyboard.js 是合法 UTF-8", False, str(exc))
        text = ""
    else:
        check("storyboard.js 含中文卡片文案", "镜头" in text or "图生图" in text or "未命名" in text, text[200:280])

    st, headers, body = get(base, "/static/storyboard-ui.css")
    ctype = headers.get("Content-Type") or headers.get("content-type") or ""
    check("storyboard-ui.css 200", st == 200, str(st))
    check(
        "storyboard-ui.css Content-Type 带 charset=utf-8",
        "css" in ctype.lower() and "charset=utf-8" in ctype.lower(),
        ctype,
    )
finally:
    httpd.shutdown()

print("PASS static-js-charset" if not fails else f"FAIL static-js-charset {len(fails)}: {fails}")
sys.exit(1 if fails else 0)
