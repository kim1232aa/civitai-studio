#!/usr/bin/env python3
"""whatif() contract: fal / huggingface / modelscope must really validate.

Before this, those three returned a hardcoded 200 no matter what was sent —
no request, no check, never a rejection. Every case below asserts a rejection
that the old constant-return版 could not produce, plus that whatif never
submits (no network is stubbed for the queue/inference endpoints; any real
submit would blow up the run).

Network is not required: the Hub probes are monkeypatched, and API keys are
faked at the module level so the key gate does not short-circuit the test.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from providers import fal as fal_mod
from providers import huggingface as hf_mod
from providers import modelscope as ms_mod
from providers import nanogpt as nano_mod

_ORIG_NANO_TEXT = nano_mod.fetch_text_catalog
_ORIG_NANO_JSON = nano_mod.json_call

fails = []


def check(name, cond, detail=""):
    if cond:
        print(f"  ok   {name}")
    else:
        fails.append(name)
        print(f"  FAIL {name} {detail}")


def expect(name, got_code, got_data, want_code, want_err_code=None):
    ok = got_code == want_code
    if want_err_code is not None:
        ok = ok and got_data.get("code") == want_err_code
    check(
        name,
        ok,
        f"-> {got_code} code={got_data.get('code')} err={got_data.get('error')}",
    )


# --- no submit allowed ----------------------------------------------------
def _boom(*a, **k):
    raise AssertionError("whatif must not call the vendor submit endpoint")


fal_mod.fal_call = _boom
ms_mod.json_call = _boom  # only the Hub probe uses it, and that is stubbed below

print("fal")
fal_mod.has_key = lambda: True
fal_mod.fal_key = lambda: "test-key"
fp = fal_mod.FalProvider()

code, d = fp.whatif({})
expect("空 serviceId 打回", code, d, 400, "missing_service")

code, d = fp.whatif({"serviceId": "image/convertImage", "prompt": "x"})
expect("civitai 服务打回", code, d, 400, "wrong_backend")

code, d = fp.whatif({"serviceId": "totally-not-fal", "prompt": "x"})
expect("目录外 id 打回", code, d, 400, "unknown_service")

code, d = fp.whatif({"serviceId": "fal-ai/flux/schnell"})
expect("t2i 缺 prompt 打回", code, d, 400, "missing_required")
check(
    "缺的字段点名 prompt",
    "prompt" in (d.get("errors") or [{}])[0].get("fields", []),
    str(d.get("errors")),
)

code, d = fp.whatif(
    {"serviceId": "fal-ai/nano-banana-2/edit", "prompt": "make it night"}
)
expect("i2i 没接图打回", code, d, 400, "missing_input_media")

code, d = fp.whatif(
    {"serviceId": "fal-ai/kling-video/v2.5-turbo/pro/image-to-video", "prompt": "pan"}
)
check(
    "i2v 没接图打回",
    code == 400 and d.get("code") in ("missing_required", "missing_input_media"),
    str(d.get("error")),
)

code, d = fp.whatif(
    {
        "serviceId": "fal-ai/flux/schnell",
        "prompt": "a cat",
        "width": 1024,
        "height": 1024,
    }
)
expect("t2i 齐全放行", code, d, 200)
check(
    "放行带 operation", d.get("operation") == "text-to-image", str(d.get("operation"))
)
check(
    "放行带 submittedInput",
    (d.get("submittedInput") or {}).get("prompt") == "a cat",
    str(d.get("submittedInput")),
)
check(
    "放行带 cost 说明",
    "没有预估接口" in ((d.get("cost") or {}).get("note") or ""),
    str(d.get("cost")),
)

code, d = fp.whatif(
    {
        "serviceId": "fal-ai/nano-banana-2/edit",
        "prompt": "night",
        "images": ["https://x/a.jpg"],
    }
)
expect("i2i 接了图放行", code, d, 200)
check(
    "i2i 落到 image_urls",
    "image_urls" in (d.get("submittedInput") or {}),
    str(d.get("submittedInput")),
)

code, d = fp.whatif(
    {
        "serviceId": "fal-ai/flux/schnell",
        "prompt": "a cat",
        "images": ["https://x/a.jpg"],
    }
)
warn = [w["code"] for w in (d.get("warnings") or [])]
check("t2i 收到图要警告丢弃", code == 200 and "input_media_dropped" in warn, str(warn))

code, d = fp.whatif(
    {"serviceId": "fal-ai/some-unlisted-endpoint/v9", "prompt": "a cat"}
)
warn = [w["code"] for w in (d.get("warnings") or [])]
check("目录无字段表要如实说明", code == 200 and "no_schema" in warn, str(warn))

code, d = fp.whatif(
    {"serviceId": "fal-ai/esrgan", "prompt": "upscale", "images": ["https://x/a.jpg"]}
)
expect("目录没图片字段名的端点如实拒绝", code, d, 400, "no_input_field")

code, d = fp.whatif({"serviceId": "fal-ai/esrgan", "prompt": "upscale"})
expect("同端点没接图先报缺图", code, d, 400, "missing_input_media")

# 目录里每条吃图的端点, 纯文字 payload 必须被打回, 不许放行
need_ops = {"image-to-image", "image-to-video", "image-to-3d", "video-to-video"}
sweep = [x for x in fal_mod.load_catalog() if x.get("falCategory") in need_ops]
passed_through = [
    x["id"]
    for x in sweep
    if fp.whatif({"serviceId": x["id"], "prompt": "a cat"})[0] != 400
]
check(
    f"{len(sweep)} 条吃图端点纯文字全部打回",
    not passed_through,
    f"漏放 {len(passed_through)} 条，例：{passed_through[:5]}",
)

# 反过来: 文生图端点不许被误杀。目录里把路径写着 image-to-image 的端点错标成
# text-to-image, 那几条被拦是对的, 其余一条都不许拦。
t2i = [x for x in fal_mod.load_catalog() if x.get("falCategory") == "text-to-image"]
killed = [
    x["id"]
    for x in t2i
    if fp.whatif({"serviceId": x["id"], "prompt": "a cat"})[0] != 200
]
mislabeled = [i for i in killed if "image-to-image" in i or "/edit" in i]
check(
    f"{len(t2i)} 条 t2i 端点纯文字全部放行（目录错标的 {len(mislabeled)} 条除外）",
    set(killed) == set(mislabeled),
    f"误杀 {sorted(set(killed) - set(mislabeled))[:5]}",
)
check(
    "目录错标端点以路径为准判成吃图",
    all(
        fp.whatif({"serviceId": i, "prompt": "a cat"})[1].get("code")
        == "missing_input_media"
        for i in mislabeled
    ),
    str(mislabeled),
)

print("huggingface")
hf_mod.hf_key = lambda: "test-key"
hf = hf_mod.HFProvider() if hasattr(hf_mod, "HFProvider") else None
if hf is None:
    hf = next(
        obj()
        for name, obj in vars(hf_mod).items()
        if isinstance(obj, type)
        and name.endswith("Provider")
        and obj is not hf_mod.Provider
    )

HUB_T2I = {
    "pipeline_tag": "text-to-image",
    "inferenceProviderMapping": {
        "fal-ai": {"status": "live", "providerId": "fal-ai/flux/schnell"}
    },
}
HUB_I2I = {
    "pipeline_tag": "image-to-image",
    "inferenceProviderMapping": {
        "nscale": {"status": "live", "providerId": "some/edit-model"}
    },
}
HUB_NONE = {"pipeline_tag": "text-to-image", "inferenceProviderMapping": {}}


def stub_hub(mapping_by_id, code=200):
    def _probe(mid):
        return code, mapping_by_id.get(mid, HUB_T2I)

    hf_mod.hub_probe = _probe


stub_hub({})
code, d = hf.whatif({})
expect("空 serviceId 打回", code, d, 400, "missing_service")

code, d = hf.whatif({"serviceId": "image/convertImage", "prompt": "x"})
expect("civitai 服务打回", code, d, 400, "wrong_backend")

code, d = hf.whatif({"serviceId": "not-an-owner-slash-model", "prompt": "x"})
expect("非 owner/model 打回", code, d, 400, "missing_service")

hf_mod.hub_probe = lambda mid: (404, {})
code, d = hf.whatif({"serviceId": "ghost/model", "prompt": "x"})
expect("Hub 上不存在打回", code, d, 400, "unknown_service")

hf_mod.hub_probe = lambda mid: (200, HUB_NONE)
code, d = hf.whatif({"serviceId": "black-forest-labs/FLUX.1-schnell", "prompt": "x"})
expect("没有推理供应商打回", code, d, 400, "no_inference_provider")

hf_mod.hub_probe = lambda mid: (200, HUB_T2I)
code, d = hf.whatif({"serviceId": "black-forest-labs/FLUX.1-schnell"})
expect("缺 prompt 打回", code, d, 400, "missing_prompt")

code, d = hf.whatif(
    {"serviceId": "black-forest-labs/FLUX.1-schnell", "prompt": "a cat"}
)
expect("t2i 齐全放行", code, d, 200)
check(
    "放行报出实际供应商",
    (d.get("service") or {}).get("provider") == "fal-ai",
    str(d.get("service")),
)

hf_mod.hub_probe = lambda mid: (200, HUB_I2I)
code, d = hf.whatif({"serviceId": "some/edit-model", "prompt": "night"})
expect("i2i 没接图打回", code, d, 400, "missing_input_media")

code, d = hf.whatif(
    {"serviceId": "some/edit-model", "prompt": "night", "images": ["https://x/a.jpg"]}
)
expect("i2i 路由到不带图的通道要打回", code, d, 400, "input_media_dropped")

hf_mod.hub_probe = lambda mid: (0, {"error": "network down"})
code, d = hf.whatif(
    {"serviceId": "black-forest-labs/FLUX.1-schnell", "prompt": "a cat"}
)
warn = [w["code"] for w in (d.get("warnings") or [])]
check(
    "Hub 连不上要如实说没校验",
    code == 200 and d.get("verified") is False and "hub_unreachable" in warn,
    f"{code} {warn} {d.get('verified')}",
)

print("modelscope")
ms = ms_mod.ModelScopeProvider("ai")
ms._key = lambda: "test-key"
ms._reach_error = lambda: None
ms_mod.hub_model_probe = lambda mid: (200, {"id": mid})

code, d = ms.whatif({})
expect("空 serviceId 打回", code, d, 400, "missing_service")

code, d = ms.whatif({"serviceId": "image/convertImage", "prompt": "x"})
expect("civitai 服务打回", code, d, 400, "wrong_backend")

code, d = ms.whatif(
    {"serviceId": "Qwen/Qwen-Image", "model": "Other/Model", "prompt": "x"}
)
expect("serviceId 与 model 冲突打回", code, d, 400, "model_mismatch")

ms_mod.hub_model_probe = lambda mid: (404, {})
code, d = ms.whatif({"serviceId": "ghost/model", "prompt": "x"})
expect("Hub 上不存在打回", code, d, 400, "unknown_service")

ms_mod.hub_model_probe = lambda mid: (200, {"id": "x"})
code, d = ms.whatif({"serviceId": "Qwen/Qwen-Image"})
expect("缺 prompt 打回", code, d, 400, "missing_prompt")

code, d = ms.whatif({"serviceId": "MusePublic/Qwen-Image-Edit", "prompt": "night"})
expect("编辑模型没接图打回", code, d, 400, "missing_input_media")

code, d = ms.whatif(
    {
        "serviceId": "MusePublic/Qwen-Image-Edit",
        "prompt": "night",
        "images": ["https://x/a.jpg"],
    }
)
expect("编辑模型接了图放行", code, d, 200)
check(
    "图落到 image_url",
    (d.get("submittedInput") or {}).get("image_url") == ["https://x/a.jpg"],
    str(d.get("submittedInput")),
)

code, d = ms.whatif(
    {"serviceId": "Qwen/Qwen-Image", "prompt": "a cat", "width": 1024, "height": 1024}
)
expect("t2i 齐全放行", code, d, 200)
check(
    "body 与 generate 同源",
    (d.get("submittedInput") or {}).get("size") == "1024x1024",
    str(d.get("submittedInput")),
)
check(
    "放行带 endpoint",
    "images/generations" in ((d.get("checked") or {}).get("endpoint") or ""),
    str(d.get("checked")),
)

ms._reach_error = lambda: "魔搭 AI 地址连不上"
code, d = ms.whatif({"serviceId": "Qwen/Qwen-Image", "prompt": "a cat"})
expect("连不上要 502 不是假 200", code, d, 502, "unreachable")

ms._reach_error = lambda: None
ms_mod.hub_model_probe = lambda mid: (401, {})
code, d = ms.whatif({"serviceId": "ghost/unknown-model", "prompt": "x"})
check(
    "未知模型 401 不得 200 放行",
    code in (400, 401) and d.get("code") in ("unknown_service", "forbidden"),
    f"{code} {d.get('code')} {d.get('error')}",
)

print("nanogpt")
FAKE_NANO = [
    {
        "id": "krea-2-turbo",
        "category": "image",
        "task": "text-to-image",
        "capabilities": {"image_generation": True},
        "supported_parameters": {"resolutions": ["1K", "2K"]},
        "pricing": {"per_image": {"1K": 0.01}},
    },
    {
        "id": "edit-model",
        "category": "image",
        "task": "image-to-image",
        "needsSource": True,
        "capabilities": {"image_to_image": True, "image_generation": False},
        "supported_parameters": {"resolutions": ["1K"]},
        "pricing": {},
    },
]
nano_mod.nano_key = lambda: "test-key"
nano_mod.json_call = _boom
nano_mod.fetch_catalog = lambda force=False: list(FAKE_NANO)
nano_mod.fetch_text_catalog = lambda force=False: []
np = nano_mod.NanoGptProvider()
code, d = np.whatif({})
expect("空 serviceId 打回", code, d, 400, "missing_service")
code, d = np.whatif({"serviceId": "image/convertImage", "prompt": "x"})
expect("civitai 服务打回", code, d, 400, "wrong_backend")
code, d = np.whatif({"serviceId": "ghost/not-in-catalog", "prompt": "x"})
expect("目录外 id 打回", code, d, 400, "unknown_service")
code, d = np.whatif({"serviceId": "krea-2-turbo"})
expect("t2i 缺 prompt 打回", code, d, 400, "missing_prompt")
code, d = np.whatif({"serviceId": "edit-model", "prompt": "night"})
expect("i2i 没接图打回", code, d, 400, "missing_input_media")
code, d = np.whatif({"serviceId": "krea-2-turbo", "prompt": "a cat"})
expect("t2i 齐全放行", code, d, 200)
check("whatif 不提交", True)

print("nano H5 失败不覆盖缓存")
nano_mod.fetch_text_catalog = _ORIG_NANO_TEXT
nano_mod._CACHE["text"] = {"at": 0.0, "items": [{"id": "keep-me", "category": "text"}]}


def _fail_json(*a, **k):
    return 500, {"error": "down"}


nano_mod.json_call = _fail_json
kept = nano_mod.fetch_text_catalog(force=True)
check("失败保留旧文本目录", kept and kept[0].get("id") == "keep-me", str(kept))
nano_mod._CACHE["text"] = {"at": 0.0, "items": None}
raised = False
try:
    nano_mod.fetch_text_catalog(force=True)
except nano_mod.CatalogFetchError:
    raised = True
check("空失败抛错而不是 []", raised)
nano_mod.json_call = _ORIG_NANO_JSON

# --- 反空壳: whatif 不许再是常量返回 -------------------------------
print("anti-stub")
import inspect

for mod, name in (
    (fal_mod, "fal"),
    (hf_mod, "huggingface"),
    (ms_mod, "modelscope"),
    (nano_mod, "nanogpt"),
):
    prov_cls = [
        obj
        for n, obj in vars(mod).items()
        if isinstance(obj, type) and n.endswith("Provider") and obj is not mod.Provider
    ][0]
    src_txt = inspect.getsource(prov_cls.whatif)
    if name == "fal":
        src_txt += inspect.getsource(mod.whatif_check)
    check(
        f"{name} whatif 不是常量 return",
        "return 200, {" not in src_txt.replace("\n", ""),
        name,
    )
    check(f"{name} whatif 有拒绝分支", src_txt.count("400") >= 3, name)

print(
    "PASS whatif-contract"
    if not fails
    else f"FAIL whatif-contract {len(fails)}: {fails}"
)
sys.exit(1 if fails else 0)
