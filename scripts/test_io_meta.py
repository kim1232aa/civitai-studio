#!/usr/bin/env python3
"""Local-only PNG / sidecar parse. No cloud."""
import struct
import zlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from providers import io_meta


def _chunk(ctype: bytes, data: bytes) -> bytes:
    crc = zlib.crc32(ctype + data) & 0xFFFFFFFF
    return struct.pack(">I", len(data)) + ctype + data + struct.pack(">I", crc)


def make_png_with_text(keyword: str, text: str) -> bytes:
    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    raw = zlib.compress(b"\x00\xff\x00\x00")
    text_chunk = keyword.encode("latin-1") + b"\x00" + text.encode("utf-8")
    return (
        sig
        + _chunk(b"IHDR", ihdr)
        + _chunk(b"tEXt", text_chunk)
        + _chunk(b"IDAT", raw)
        + _chunk(b"IEND", b"")
    )


fails = []
a1111 = (
    "a girl in neon rain, cinematic\n"
    "Negative prompt: blurry, lowres\n"
    "Steps: 28, Sampler: Euler a, CFG scale: 5.5, Seed: 12345, Size: 768x1152, Model: foo"
)
png = make_png_with_text("parameters", a1111)
parsed = io_meta.parse_media_bytes(png, "t.png")
if parsed.get("source") != "png-a1111":
    fails.append(f"source {parsed.get('source')}")
if "neon rain" not in (parsed.get("prompt") or ""):
    fails.append(f"prompt {parsed.get('prompt')!r}")
if parsed.get("negativePrompt") != "blurry, lowres":
    fails.append(f"neg {parsed.get('negativePrompt')!r}")
if parsed.get("steps") != 28:
    fails.append(f"steps {parsed.get('steps')}")
if parsed.get("width") != 768 or parsed.get("height") != 1152:
    fails.append(f"size {parsed.get('width')}x{parsed.get('height')}")
if parsed.get("empty"):
    fails.append("empty should be false")

empty = io_meta.parse_media_bytes(b"not a png", "x.jpg")
if not empty.get("empty"):
    fails.append("non-png must be empty")

comfy = '{"1":{"class_type":"CLIPTextEncode","inputs":{"text":"comfy prompt here"}},"2":{"class_type":"EmptyLatentImage","inputs":{"width":512,"height":768}}}'
cpng = make_png_with_text("prompt", comfy)
cparsed = io_meta.parse_media_bytes(cpng, "c.png")
if cparsed.get("source") != "png-comfy":
    fails.append(f"comfy source {cparsed.get('source')}")
if cparsed.get("prompt") != "comfy prompt here":
    fails.append(f"comfy prompt {cparsed.get('prompt')!r}")
if cparsed.get("width") != 512:
    fails.append(f"comfy w {cparsed.get('width')}")

side = io_meta.sidecar_to_import({
    "backend": "fal",
    "serviceId": "fal-ai/z-image/turbo",
    "prompt": "from sidecar",
    "submittedInput": {"prompt": "from sidecar", "num_inference_steps": 8, "image_size": {"width": 960, "height": 1440}},
})
if side.get("prompt") != "from sidecar" or side.get("steps") != 8 or side.get("width") != 960:
    fails.append(f"sidecar {side}")

if fails:
    print("FAIL")
    for f in fails:
        print(" -", f)
    sys.exit(1)
print("PASS io_meta local parse")
sys.exit(0)
