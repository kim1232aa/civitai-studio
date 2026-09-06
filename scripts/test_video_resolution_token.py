#!/usr/bin/env python3
"""视频/枚举分辨率服务只认令牌（`720p` / `1080p` / `1K`），不认 `720x1280`。

storyboard 的 buildGraph 对视频也发 `resolution:"720x1280"`（WxH），
但 catalog 里 wan/seedance/grok/sora/nano-banana 这类服务的 resolution 是
字符串枚举令牌 —— WxH 落地就是非法值，云端会打回或悄悄按默认档渲染，
而且竖屏 9:16 的意图整个丢掉（这些服务的朝向靠 aspectRatio）。

红→绿：补丁前 1-6 全红（resolution 仍是 `720x1280`、aspectRatio 缺失），
7-9 是护栏，补丁前后都必须绿（WxH 家族服务与图片链不受影响）。

Run: python3 scripts/test_video_resolution_token.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from providers.civitai import build_workflow  # noqa: E402

FAILED = []

WAN25_I2V = "video/wan/v2.5/fal/image-to-video"  # enum 480p/720p/1080p + aspectRatio
WAN22_T2V = "video/wan/v2.2/fal/text-to-video"  # enum 480p/720p（无 1080p）
WAN26_I2V = "video/wan/v2.6/fal/image-to-video"  # enum 720p/1080p，cap 无 aspectRatio
WAN22_COMFY = "video/wan/v2.2/comfy"  # WxH 家族，无 resolution 字段
SEEDANCE = "video/seedance"  # 非 wan，resolution 为 required
NANO2 = "image/google/nano-banana-2"  # 图片枚举 1K/2K/4K
KREA2 = "image/comfy/krea2/turbo/createImage"


def ok(cond, msg):
   if cond:
      print("ok " + msg)
   else:
      print("FAIL " + msg)
      FAILED.append(msg)


def inp_of(**payload):
   body = build_workflow(payload)
   return body["steps"][0]["input"]


def vid(sid, **kw):
   p = {
      "backend": "civitai",
      "serviceId": sid,
      "kind": "video",
      "prompt": "a cat",
      "sourceImage": "https://example.invalid/a.jpg",
      "duration": 5,
   }
   p.update(kw)
   return inp_of(**p)


def test_wan25_portrait_720():
   i = vid(WAN25_I2V, resolution="720x1280")
   ok(
      i.get("resolution") == "720p",
      f"wan2.5 i2v 720x1280 -> 720p，实际 {i.get('resolution')!r}",
   )
   ok(
      i.get("aspectRatio") == "9:16",
      f"wan2.5 i2v 竖屏 -> aspectRatio 9:16，实际 {i.get('aspectRatio')!r}",
   )


def test_wan25_landscape_1080():
   i = vid(WAN25_I2V, resolution="1920x1080")
   ok(
      i.get("resolution") == "1080p",
      f"wan2.5 i2v 1920x1080 -> 1080p，实际 {i.get('resolution')!r}",
   )
   ok(
      i.get("aspectRatio") == "16:9",
      f"wan2.5 i2v 横屏 -> aspectRatio 16:9，实际 {i.get('aspectRatio')!r}",
   )


def test_wan22_snaps_down_to_enum_max():
   i = vid(WAN22_T2V, resolution="1080x1920")
   ok(
      i.get("resolution") == "720p",
      f"wan2.2 t2v 枚举只到 720p，1080x1920 必须降档到 720p，实际 {i.get('resolution')!r}",
   )
   ok(
      i.get("aspectRatio") == "9:16",
      f"wan2.2 t2v 竖屏 -> 9:16，实际 {i.get('aspectRatio')!r}",
   )


def test_wan26_no_aspect_field_still_gets_token():
   i = vid(WAN26_I2V, resolution="720x1280")
   ok(
      i.get("resolution") == "720p", f"wan2.6 i2v -> 720p，实际 {i.get('resolution')!r}"
   )
   ok(
      "aspectRatio" not in i,
      f"wan2.6 i2v cap 不收 aspectRatio，不该塞，实际 {i.get('aspectRatio')!r}",
   )


def test_seedance_required_resolution():
   i = vid(SEEDANCE, resolution="720x1280")
   ok(
      i.get("resolution") == "720p",
      f"seedance required resolution -> 720p，实际 {i.get('resolution')!r}",
   )


def test_nano_banana_k_tokens():
   i = inp_of(backend="civitai", serviceId=NANO2, prompt="a cat", resolution="720x1280")
   ok(
      i.get("resolution") in ("1K", "2K", "4K"),
      f"nano-banana 枚举 1K/2K/4K，不该收到 WxH，实际 {i.get('resolution')!r}",
   )


# ---- 护栏：补丁前后都必须绿 ----


def test_valid_token_untouched():
   i = vid(WAN22_T2V, resolution="480p")
   ok(i.get("resolution") == "480p", f"合法令牌不动，实际 {i.get('resolution')!r}")


def test_explicit_aspect_wins():
   i = vid(WAN25_I2V, resolution="720x1280", aspectRatio="1:1")
   ok(
      i.get("aspectRatio") == "1:1",
      f"显式 aspectRatio 优先，实际 {i.get('aspectRatio')!r}",
   )
   ok(
      i.get("resolution") == "720p",
      f"显式 aspect 不影响档位，实际 {i.get('resolution')!r}",
   )


def test_wh_family_video_still_splits():
   i = vid(WAN22_COMFY, resolution="720x1280")
   ok(
      i.get("width") == 720 and i.get("height") == 1280,
      f"WxH 家族视频服务仍按 width/height 拆，实际 {i.get('width')}x{i.get('height')}",
   )
   ok("resolution" not in i, f"WxH 家族不该留 resolution，实际 {i.get('resolution')!r}")


def test_image_free_wh_unchanged():
   i = inp_of(backend="civitai", serviceId=KREA2, prompt="a cat", resolution="720x1280")
   ok(
      i.get("width") == 720 and i.get("height") == 1280,
      f"free_wh 图片链不受影响，实际 {i.get('width')}x{i.get('height')}",
   )


for fn in list(globals().values()):
   if callable(fn) and getattr(fn, "__name__", "").startswith("test_"):
      fn()

if FAILED:
   print(f"result {len(FAILED)} failed")
   sys.exit(1)
print("video-resolution-token ok")
