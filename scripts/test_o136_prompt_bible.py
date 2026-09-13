#!/usr/bin/env python3
"""o136: 反推提示词是完整可编辑圣经，不是空壳。禁止 CHAR_LIB 编造。"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
fails: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    if cond:
        print(f"  ok   {name}")
    else:
        fails.append(name)
        print(f"  FAIL {name} {detail}")


bible_js = ROOT / "static" / "prompt-bible.js"
html = (ROOT / "static" / "storyboard.html").read_text(encoding="utf-8")
js = (ROOT / "static" / "storyboard.js").read_text(encoding="utf-8")
css = (ROOT / "static" / "storyboard-ui.css").read_text(encoding="utf-8")
nano = (ROOT / "providers" / "nanogpt.py").read_text(encoding="utf-8")
media = (ROOT / "providers" / "media_io.py").read_text(encoding="utf-8")

print("o136 files")
check("prompt-bible.js exists", bible_js.is_file())
check("html loads prompt-bible.js", "prompt-bible.js" in html)
check("o136 stamp comment", "v0821o136-prompt-bible" in html)
check("no CHAR_LIB", "CHAR_LIB" not in js)
check("describePrompt uses PromptBible", "PromptBible.formatReversePrompt" in js)
check("syncTextToShots", "function syncTextToShots" in js)
check("syncShotToText", "function syncShotToText" in js)
check("insertMention text branch", 'kind === "text"' in js and "insertMention" in js)
check("caret restore", "textarea[data-text]" in js and "setSelectionRange" in js)
check("text card @ atbox", "showAtbox(before.slice(at + 1))" in js)
check("text card editor CSS", ".card.text .editor" in css)
check("text card acts CSS", ".card.text .acts" in css)
check("CAPTION_PROMPT structured", "禁止编造" in media and "【反推提示词】" in media)
check("nanogpt uses CAPTION_PROMPT", "CAPTION_PROMPT" in nano)
check(
    "nanogpt dropped English blob prompt",
    "Do not invent a backstory. Output only the description." not in nano,
)

print("o136 PromptBible vm")
if bible_js.is_file():
    probe = (
        bible_js.read_text(encoding="utf-8")
        + r"""
const b = (typeof PromptBible !== "undefined" && PromptBible)
  || (typeof module !== "undefined" && module.exports);
const out = {
  empty: b.formatReversePrompt(""),
  blank: b.formatReversePrompt("   "),
  unstructured: b.formatReversePrompt("银色家用机器人站在现代厨房，暖色窗光，中景平视。"),
  structured: b.formatReversePrompt("【反推提示词】\n主体：家用机器人\n外观：哑光银白壳体\n服装：\n场景：开放式厨房\n光线：窗边暖光"),
  keys: b.KEYS,
};
console.log(JSON.stringify(out));
"""
    )
    r = subprocess.run(
        ["node", "--input-type=commonjs"],
        input=probe,
        text=True,
        capture_output=True,
        cwd=str(ROOT),
    )
    check("vm exit 0", r.returncode == 0, (r.stderr or r.stdout)[-400:])
    data = {}
    if r.returncode == 0:
        try:
            data = json.loads(r.stdout.strip().splitlines()[-1])
        except json.JSONDecodeError as e:
            check("vm json", False, str(e) + " " + r.stdout[-200:])
    if data:
        check("empty → \"\"", data.get("empty") == "" and data.get("blank") == "")
        keys = data.get("keys") or []
        for k in ["主体", "外观", "服装", "姿态", "场景", "光线", "构图", "画面", "运镜", "约束", "负面"]:
            check("KEY " + k, k in keys)
        u = data.get("unstructured") or ""
        check("unstructured head", u.startswith("【反推提示词】"))
        check("unstructured 视觉描述", "视觉描述：银色家用机器人" in u)
        check("unstructured 主体 blank", "主体：" in u and "居家装" not in u)
        check("unstructured no 自然室内光", "自然室内光" not in u)
        s = data.get("structured") or ""
        check("structured 主体", "主体：家用机器人" in s)
        check("structured 外观", "外观：哑光银白壳体" in s)
        check("structured 场景", "场景：开放式厨房" in s)
        check("structured blank 服装", "职场装" not in s)
else:
    check("vm skipped, missing bible", False)

if fails:
    print("FAIL", len(fails), *fails, sep="\n  ")
    sys.exit(1)
print("ok   o136 prompt bible")
