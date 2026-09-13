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
# 非空白 16×16 渐变图(过 is_blank_image 闸门, lead 裁决对齐 o91)
PNG_REAL = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAIAAACQkWg2AAACb0lEQVR4nAXBIai0MBwA8H88eElOnu3gbI8dFh9cfDBc+eCioLAmGC0LYjcMi3m2BcuSUVg3CWLXqs1gH36/HwCABV8ufPvwDOAVwjsFnMOHQyQgUZBpKEYoV6gPaC5oAZwvy/l2nafvvALnHTo4dT65E3EnEU6mnEI75ejUq9McTns5HYD3bXlP13v53jvwcOh9Ui/KvYR7mfAK5ZXaq0evWb328LrL0wDkaZGXS94+wQH5hCRKSZKTjJNCkFKRWpNmJO1KuoPoiwwA9GXRt0uxTz8BjUKapDTLacFpKWitaKNpO9Jupfqgw0VnAPa2GHbZx2dRwJKQZSkrclZyVgvWKNZq1o1Mr2w42HyxBaDCVvVxq8ivkqDKwqpIqzKval41ompV1elKj9WwVvNRLVe1A8iPJSNXJr7MAlmEskxlncuGy1bITkmt5TDKeZXLIfdLngB9ZPWJ22d+XwR9GfZ12jd53/K+E71W/aD7eeyXtd+P/rx6AzAl1pS5U+FPZTDV4dSkU5tPHZ+0mAY1zXpaxmlfp/OYzDXdALbM2gp3K/2tDrYm3Np06/JN820Q26y2RW/7uJ3rZo7tdm13AFNYpnRN7ZsmMG1outTo3AzczMIsyuzanKMxq7kd5n6ZB4BdWnbt2o1vt4HdhbZO7SG3Z24vwt6VfWrbjPZtte+H/bjsHwBUW6hxUeujLkA6REOK5hwtHO0CnQoZjW4juq/ocaCfC/0C4MbCrYs7H+sADyGeU7zkeOf4FNgofNP4PuLHin8O/HvhP4C4teLOjbUfD0E8h/GSxnsenzw2Ir6p+K7jxxj/rPHvEf9d8b//xR51EHIN1akAAAAASUVORK5CYII="
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
    # lead 裁决(对齐 o91 空图不入库): 1×1 空白图必须 400; 合法上传改用非空白 16×16 渐变图
    data_url = "data:image/png;base64," + base64.b64encode(PNG_1x1).decode("ascii")
    code, data = media_io.upload_out_request(
        {"dataUrl": data_url, "filename": "dot.png"}, out_dir=tmp_path
    )
    check("1×1 空白图 400 不入库", code == 400 and data.get("code") == "blank_image", str((code, data)))
    data_url = "data:image/png;base64," + base64.b64encode(PNG_REAL).decode("ascii")
    code, data = media_io.upload_out_request(
        {"dataUrl": data_url, "filename": "dot.png"}, out_dir=tmp_path
    )
    check("合法上传 200", code == 200 and (data.get("url") or "").startswith("/out/"), str((code, data)))
    dest = tmp_path / data["file"]
    check("文件落盘", dest.is_file() and dest.read_bytes() == PNG_REAL, str(dest))
    check("禁止 blob 冒充", "blob:" not in str(data.get("url")))

print("caption unit")
check("nano caption_image 存在", callable(getattr(nano_mod, "caption_image", None)))
check("civitai caption_media 存在", callable(getattr(civitai_mod, "caption_media", None)))
nano_mod.nano_key = lambda: ""
civitai_mod.has_key = lambda: False
code, data = nano_mod.caption_image("data:image/png;base64,xx")
check("nano 无 key 401 不是 AttributeError", code == 401 and data.get("code") == "no_key" and not data.get("caption"), str((code, data)))
code, data = civitai_mod.caption_media("")
check("civitai 缺 url 400", code == 400 and data.get("code") == "missing_url" and not data.get("caption"), str((code, data)))
code, data = civitai_mod.caption_media("https://example.invalid/x.png")
check("civitai 无 key 401", code == 401 and data.get("code") == "no_key" and not data.get("caption"), str((code, data)))
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

        st, payload = post("/api/upload-out", {"dataUrl": "data:image/png;base64," + base64.b64encode(PNG_REAL).decode(), "filename": "http.png"})
        check("HTTP upload-out 不是 404", st != 404, str((st, payload)))
        check("HTTP upload-out 200 落盘", st == 200 and payload.get("url", "").startswith("/out/"), str((st, payload)))
        if st == 200:
            saved = Path(tmp) / payload["file"]
            check("HTTP 文件存在", saved.is_file() and saved.stat().st_size == len(PNG_REAL), str(saved))
        st, payload = post("/api/caption", {})
        check("HTTP caption 路由存在", payload.get("error") != "not found", str((st, payload)))
        check("HTTP caption 缺 url 400", st == 400 and payload.get("code") == "missing_url", str((st, payload)))
        st, payload = post("/api/caption", {"url": "/out/missing.png"})
        check("HTTP caption 失败非 2xx 且无假 caption", st >= 400 and not payload.get("caption"), str((st, payload)))
        st, payload = post("/api/generate", {"backend": "nope", "serviceId": "zzz", "prompt": "x"})
        check("未知后端 generate 400", st == 400 and "未知" in str(payload.get("error", "")), str((st, payload)))
    finally:
        httpd.shutdown()

print("PASS e5-media-io" if not fails else f"FAIL e5-media-io {len(fails)}: {fails}")
sys.exit(1 if fails else 0)
