#!/usr/bin/env python3
"""LoRA air 解析契约（D 门 P2）。Run: python3 scripts/test_lora_air_resolve.py

civitai 生成链只认 air。行里只有 version id 时必须换成 air；换不出来要报错，
不能静默丢，更不能把 modelId 当 versionId 解析成别的资源。
缺 strength 保持 None，不发明 1.0。全离线，不打网络。
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from providers import civitai as civ  # noqa: E402

JS = (ROOT / "static" / "storyboard.js").read_text(encoding="utf-8")
SERVER = (ROOT / "server.py").read_text(encoding="utf-8")

FAKE = {
    "135867": {
        "id": 135867,
        "modelId": 122359,
        "air": "urn:air:sdxl:lora:civitai:122359@135867",
        "model": {"type": "LORA", "name": "Real LoRA"},
    },
    "122359": {
        "id": 122359,
        "modelId": 96429,
        "air": "urn:air:sd1:checkpoint:civitai:96429@122359",
        "model": {"type": "Checkpoint", "name": "Gap_mix"},
    },
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
    civ.fetch_version_air = fake_fetch

    got = civ.lora_map({"loras": [{"air": "urn:air:sdxl:lora:civitai:1@2", "strength": 0.8}]})
    ok(got == {"urn:air:sdxl:lora:civitai:1@2": 0.8}, "带 air 的行原样带走，强度不变")

    got = civ.lora_map({"loras": [{"versionId": "135867", "strength": 0.7}]})
    ok(
        got == {"urn:air:sdxl:lora:civitai:122359@135867": 0.7},
        "只有 version id 的行换成 air 带走（旧行为是静默丢）",
    )

    got = civ.lora_map({"loras": [{"versionId": "135867", "modelId": "122359"}]})
    ok(
        got == {"urn:air:sdxl:lora:civitai:122359@135867": None},
        "modelId 对得上时正常带走，缺 strength 保持 None（不发明 1.0）",
    )

    raises(
        {"loras": [{"versionId": "122359", "modelId": "122359", "name": "撞号行"}]},
        "modelId 被当 versionId（两个 id 空间撞号）时报错，不发别人的资源",
    )
    raises(
        {"loras": [{"versionId": "122359", "name": "Checkpoint 真身"}]},
        "裸 version 122359 是 Checkpoint，服务端拒绝当 LoRA 发出去",
    )
    raises(
        {"loras": [{"air": "urn:air:sd1:checkpoint:civitai:96429@122359", "strength": 0.8}]},
        "已带 Checkpoint AIR 也拒绝，不因 air 已提供就 fail-open",
    )
    raises(
        {
            "loras": [
                {
                    "air": "urn:air:sd1:checkpoint:civitai:96429@122359",
                    "type": "LORA",
                    "name": "伪装",
                }
            ]
        },
        "Checkpoint AIR 即使 type 写成 LORA 也拒绝",
    )
    raises({"loras": [{"versionId": "999999", "name": "查不到"}]}, "version 查不到时报错，不静默丢")
    raises({"loras": [{"name": "光有名字"}]}, "既无 air 又无 version id 时报错，不静默丢")
    raises(
        {"loras": [{"path": "https://civitai.com/api/download/models/3184845", "strength": 0.8}]},
        "只有 path 没有 air/versionId 时报错，不静默丢",
    )
    ok(civ.lora_map({"loras": []}) == {}, "空列表不报错")

    err = civ.LoraResolveError("x", row_name="n")
    ok(err.code == "lora_unresolved" and isinstance(err, ValueError), "错误类型带 code，走 400 而不是 500")

    ok("civitai_prov.fetch_version_air" in SERVER, "/api/model-version 走 fetch_version_air")
    ok('"modelId"' in SERVER and "airError" in SERVER, "/api/model-version 返回 modelId 与 airError")

    ok("async function resolveLoraAir(" in JS and "await resolveLoraAir(" in JS,
       "addLora 入列前先把 version id 换成 air")
    ok("换不出 air，civitai 生成链带不走这条" in JS, "换不出 air 时前端给出原因，不静默丢")
    ok("data-mid=" in JS, "搜索命中带着 modelId，不把命中项 id 当 versionId")
    ok("该模型不支持 " in JS and "时长（" in JS, "时长发送前校验存在")
    ok("function durationGateMessage(" in JS, "paramGateMessage 有 duration 闸")
    ok("durationGateMessage()" in JS, "paramGateMessage 调用 duration 闸")

    print("OK lora-air-resolve")


if __name__ == "__main__":
    main()
