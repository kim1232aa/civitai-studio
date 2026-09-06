#!/usr/bin/env python3
"""E5: /api/caption and /api/upload-out are real handlers, not 404 shells."""
from __future__ import annotations

import base64
import json
import sys
import threading
import time
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from providers import civitai as civitai_mod  # noqa: E402
from providers import media_io  # noqa: E402
from providers import nanogpt as nano_mod  # noqa: E402

fails = []


def check(name, cond, detail=""):
    if cond:
        print(f"  ok   {name}")
    else:
        fails.append(name)
        print(f"  FAIL {name} {detail}")


PNG_1x1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+ip1sAAAAASUVORK5CYII="
)


print("upload-out unit")
with TemporaryDirectory() as tmp:
    tmp_path = Path(tmp)
    code, data = media_io.upload_out_request({"filename": "x.png"}, out_dir=tmp_path)
    check("缺 dataUrl 400", code == 400 and data.get("code") == "invalid_data_url", str((code, data)))
    code, data = media_io.upload_out_request(
        {"dataUrl": "not-a-data-url", "filename": "x.png"}, out_dir=tmp_path
    )
    check("非法 dataUrl 400", code == 400, str((code, data)))
    data_url = "data:image/png;base64," + base64.b64encode(PNG_1x1).decode("ascii")
    code, data = media_io.upload_out_request(
        {"dataUrl": data_url, "filename": "dot.png"}, out_dir=tmp_path
    )
    check("合法上传 200", code == 200 and (data.get("url") or "").startswith("/out/"), str((code, data)))
    dest = tmp_path / data["file"]
    check("文件落盘", dest.is_file() and dest.read_bytes() == PNG_1x1, str(dest))
    check("禁止 blob 冒充", "blob:" not in str(data.get("url")))

print("caption unit")
nano_mod.nano_key = lambda: ""
civitai_mod.has_key = lambda: False
code, data = media_io.caption_request({})
check("缺 url 400", code == 400 and data.get("code") == "missing_url", str((code, data)))
code, data = media_io.caption_request({"url": "/out/no-such-file.png"})
check("无 key 时 503 不是假 caption", code == 503 and not data.get("caption"), str((code, data)))
check("503 文案诚实", "视觉打标" in str(data.get("error") or ""), str(data.get("error")))

print("http")
import server  # noqa: E402

with TemporaryDirectory() as tmp:
    media_io.OUT = Path(tmp)
    server.OUT = Path(tmp)
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{httpd.server_address[1]}"
    try:
        def post(path, body):
            raw = json.dumps(body).encode()
            req = urllib.request.Request(
                base + path,
                data=raw,
                method="POST",
                headers={"Content-Type": "application/json"},
            )
            for attempt in range(80):
                try:
                    with urllib.request.urlopen(req, timeout=5) as resp:
                        return resp.status, json.loads(resp.read().decode())
                except urllib.error.HTTPError as exc:
                    payload = json.loads(exc.read().decode())
                    return exc.code, payload
                except urllib.error.URLError:
                    if attempt == 79:
                        raise
                    time.sleep(0.05)

        st, payload = post("/api/upload-out", {"dataUrl": "data:image/png;base64," + base64.b64encode(PNG_1x1).decode(), "filename": "http.png"})
        check("HTTP upload-out 不是 404", st != 404, str((st, payload)))
        check("HTTP upload-out 200 落盘", st == 200 and payload.get("url", "").startswith("/out/"), str((st, payload)))
        if st == 200:
            saved = Path(tmp) / payload["file"]
            check("HTTP 文件存在", saved.is_file() and saved.stat().st_size == len(PNG_1x1), str(saved))
        st, payload = post("/api/caption", {})
        check("HTTP caption 路由存在", payload.get("error") != "not found", str((st, payload)))
        check("HTTP caption 缺 url 400", st == 400 and payload.get("code") == "missing_url", str((st, payload)))
        st, payload = post("/api/caption", {"url": "/out/missing.png"})
        check("HTTP caption 失败非 2xx 且无假 caption", st >= 400 and not payload.get("caption"), str((st, payload)))
        st, payload = post("/api/generate", {"backend": "nope", "serviceId": "zzz", "prompt": "x"})
        check("未知后端 generate 400", st == 400 and payload.get("code") == "unknown_backend", str((st, payload)))
    finally:
        httpd.shutdown()

print("PASS e5-media-io" if not fails else f"FAIL e5-media-io {len(fails)}: {fails}")
sys.exit(1 if fails else 0)
