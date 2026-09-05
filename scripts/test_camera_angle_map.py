#!/usr/bin/env python3
"""Seko 多角度滑杆 → fal 字段。与 static/storyboard.js mapSeko* 保持同公式。"""


def map_seko_yaw_to_fal(yaw):
    y = max(-90, min(180, float(yaw or 0)))
    return (y + 360) % 360


def map_seko_pitch_to_fal(pitch):
    return max(-30, min(30, float(pitch or 0)))


def map_seko_zoom_to_fal(slot):
    s = float(slot)
    if s <= 0:
        return 10  # 特写 close-up
    if s >= 2:
        return 0  # 广角 wide
    return 5  # 中景 medium


def main():
    assert map_seko_yaw_to_fal(0) == 0
    assert map_seko_yaw_to_fal(-90) == 270
    assert map_seko_yaw_to_fal(90) == 90
    assert map_seko_yaw_to_fal(180) == 180
    assert map_seko_yaw_to_fal(-45) == 315
    assert map_seko_pitch_to_fal(0) == 0
    assert map_seko_pitch_to_fal(-30) == -30
    assert map_seko_pitch_to_fal(30) == 30
    assert map_seko_pitch_to_fal(90) == 30
    assert map_seko_pitch_to_fal(120) == 30
    assert map_seko_pitch_to_fal(-40) == -30
    assert map_seko_zoom_to_fal(0) == 10
    assert map_seko_zoom_to_fal(1) == 5
    assert map_seko_zoom_to_fal(2) == 0
    # 源站四 tab 预设 → fal（deepseek 2026-09-06 DOM）
    assert map_seko_yaw_to_fal(0) == 0 and map_seko_pitch_to_fal(30) == 30 and map_seko_zoom_to_fal(1) == 5  # 鱼眼
    assert map_seko_yaw_to_fal(180) == 180 and map_seko_pitch_to_fal(0) == 0  # 反打
    assert map_seko_yaw_to_fal(45) == 45 and map_seko_pitch_to_fal(-30) == -30  # 荷兰角
    print("ok camera-angle-map")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
