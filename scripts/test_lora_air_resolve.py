#!/usr/bin/env python3
"""LoRA air 解析契约（D 门 P2 挂账）。Run: python3 scripts/test_lora_air_resolve.py

盯的是「界面收了、请求里悄悄丢了」这条：civitai 生成链只认 air，
行里只有 version id 时必须换成 air；换不出来要报错，不能静默丢，
更不能把 modelId 当 versionId 解析成别的资源。全离线，不打网络。
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from providers import civitai as civ  # noqa: E402

JS = (ROOT / "static" / "storyboard.js").read_text(encoding="utf-8")

# 假的版本库：135867 是真 version，122359 只是别人的 modelId 撞到的 version
FAKE = {
    "135867": {"id": 135867, "modelId": 122359, "air": "urn:air:sdxl:lora:civitai:122359@135867"},
    "122359": {"id": 122359, "modelId": 96429, "air": "urn:air:sd1:checkpoint:civitai:96429@122359"},
    "999999": {},
}


def fake_fetch(vid, timeout=20):
    return FAKE.get(str(vid), {})


def ok(cond, msg):
    if not cond:
        raise AssertionError(msg)
    print("ok  -", msg)


def raises(payload, msg):
    try:
        civ.lora_map(payload)
    except civ.LoraResolveError:
        print("ok  -", msg)
        return
    raise AssertionError(msg)


def main():
    civ.fetch_version_air = fake_fetch  # 只在本进程内替身

    got = civ.lora_map({"loras": [{"air": "urn:air:sdxl:lora:civitai:1@2", "strength": 0.8}]})
    ok(got == {"urn:air:sdxl:lora:civitai:1@2": 0.8}, "带 air 的行原样带走，强度不变")

    got = civ.lora_map({"loras": [{"versionId": "135867", "strength": 0.7}]})
    ok(
        got == {"urn:air:sdxl:lora:civitai:122359@135867": 0.7},
        "只有 version id 的行换成 air 带走（旧行为是静默丢）",
    )

    got = civ.lora_map({"loras": [{"versionId": "135867", "modelId": "122359"}]})
    ok(len(got) == 1, "modelId 对得上时正常带走，默认强度 1")

    raises(
        {"loras": [{"versionId": "122359", "modelId": "122359", "name": "撞号行"}]},
        "modelId 被当 versionId（两个 id 空间撞号）时报错，不发别人的资源",
    )
    raises({"loras": [{"versionId": "999999", "name": "查不到"}]}, "version 查不到时报错，不静默丢")
    raises({"loras": [{"name": "光有名字"}]}, "既无 air 又无 version id 时报错，不静默丢")
    ok(civ.lora_map({"loras": []}) == {}, "空列表不报错")

    err = civ.LoraResolveError("x", row_name="n")
    ok(err.code == "lora_unresolved" and isinstance(err, ValueError), "错误类型带 code，走 400 而不是 500")

    # 前端侧契约：行没换出 air 就不算可用，且不能把命中项的 id 当 versionId
    ok(
        'if (caps.lora === "air") return !!row.air;' in JS,
        "loraRowUsable：civitai 只认换出 air 的行",
    )
    ok("async function resolveLoraAir(" in JS and "await resolveLoraAir(" in JS,
       "addLora 入列前先把 version id 换成 air")
    ok("换不出 air，civitai 生成链带不走这条" in JS, "换不出 air 时前端给出原因，不静默丢")
    ok(
        "modelId: item && item.id" in JS and "addLora(item);" not in JS,
        "搜索命中兜底不把 modelId 当 versionId 塞进去",
    )
    ok(
        "if (svcItem && svcItem.referenceLimit != null) {" in JS,
        "参考图上限对 image/video 两个模式都拦（P3）",
    )
    ok("该模型不支持 " in JS and "时长（" in JS, "时长发送前校验存在（P4：禁用档位不许发旧值）")
    ok("v !== 0 &&" not in JS, "steps=0 低于下限也标红，视觉与拦截口径一致（P4）")

    print("OK lora-air-resolve")


if __name__ == "__main__":
    main()
