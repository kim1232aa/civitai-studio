#!/usr/bin/env python3
"""o91: 1×1 / tiny PNG is blank — not a gallery card."""
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from providers.http import is_blank_image
from providers.media_io import upload_out_request

PNG_1X1 = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000d4944415478da63f8cfc000000101010018dd8d180000000049454e44ae426082"
)


def main():
    assert is_blank_image(raw=PNG_1X1), "1x1 png must be blank"
    assert is_blank_image(raw=b""), "empty is blank"
    assert is_blank_image(raw=b"\x89PNG" + b"\x00" * 20), "tiny png is blank"
    house = ROOT / "out" / "house-fal.jpg"
    if house.is_file() and house.stat().st_size > 1000:
        assert not is_blank_image(path=house), "real house-fal.jpg is not blank"
    import base64
    data_url = "data:image/png;base64," + base64.b64encode(PNG_1X1).decode("ascii")
    code, data = upload_out_request({"dataUrl": data_url, "filename": "ref.png"})
    assert code == 400, data
    assert data.get("code") == "blank_image", data
    src = (ROOT / "server.py").read_text(encoding="utf-8")
    assert 'path in ("/", "/storyboard.html"' in src, "preview / is canvas"
    assert '"/index.html", "/desk"' in src, "配方台 stays at /index.html"
    js = (ROOT / "static" / "storyboard.js").read_text(encoding="utf-8")
    assert "function nineGridFromShot" in js
    assert "function storyAdvanceFromShot" in js
    assert "function beginCrop" in js
    html = (ROOT / "static" / "storyboard.html").read_text(encoding="utf-8")
    assert "九宫格" in html and "故事推演" in html
    assert "空白节点" in html and "上传本地文件" in html
    css = (ROOT / "static" / "o76-dock-right.css").read_text(encoding="utf-8")
    assert "right: 16px !important" not in css, "no right inspector"
    print("PASS o91_blank_outs")


if __name__ == "__main__":
    main()
