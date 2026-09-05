#!/usr/bin/env python3
"""Static checks that storyboard.js actually implements the prompt contract."""

from pathlib import Path
import re

JS = Path(__file__).resolve().parents[1] / "static" / "storyboard.js"
src = JS.read_text(encoding="utf-8")


def ok(cond, msg):
    if not cond:
        raise AssertionError(msg)


def main():
    ok('STORE = "nl-storyboard-v0794"' in src, "STORE must be v0794")
    ok("async function reverseFromImage" in src, "reverseFromImage must exist")
    ok("function describePrompt" in src, "describePrompt must exist")
    ok("function generateFromText" in src, "generateFromText must exist")
    ok("function promptOf" in src, "promptOf must exist")
    ok("textarea" in src and "data-text" in src, "text card must be a live textarea")
    ok(
        "look:" in src and "outfit:" in src and "negative:" in src,
        "CHAR_LIB bible fields",
    )
    ok("captionFromAsset" in src, "caption path")
    ok("syncPrompt" in src, "text/shot prompt sync")
    ok("moveCardEl" in src, "drag must not wipe textarea")
    ok("fal_fal-ai_flux_schnell_01a05be2" in src, "apple restore reject")
    for title in (
        "家用机器人",
        "大白-居家装",
        "大白-职场装",
        "扫地机器人",
        "温馨现代卧室",
        "现代感洗手间",
    ):
        ok(title in src, title)
    ok(src.count("demo-bot.jpg") >= 1, "distinct demo urls")
    ok("col * 1120" in src, "demo column stride 1120 (text+shot must not overlap)")
    ok(
        "function sekoRelayoutSeedCards" in src,
        "relayout persisted overlapping seed cards",
    )
    ok("demo-bath.jpg" in src and "demo-work.jpg" in src, "all demo thumbs")
    ok('kind === "text"' in src or 'kind === "text"' in src, "text kind")
    ok("function mapSekoYawToFal" in src, "yaw fal remap")
    ok("function mapSekoPitchToFal" in src, "pitch fal clamp")
    ok("function mapSekoZoomToFal" in src, "zoom fal remap")
    ok("(y + 360) % 360" in src, "seko yaw to fal 0-360")
    ok("Math.max(-30, Math.min(30, p))" in src, "pitch pass-through ±30")
    ok(
        "return 10; // 特写" in src
        and "return 0;  // 广角" in src
        and "return 5;" in src,
        "zoom 特写10/中景5/广角0",
    )
    ok("category=cameraAngle" in src, "cameraAngle catalog filter")
    ok('op: "camera-angle"' in src, "camera-angle op")
    for preset in (
        r'id:\s*"fisheye"[\s\S]*?label:\s*"鱼眼镜头"[\s\S]*?yaw:\s*0[\s\S]*?pitch:\s*30[\s\S]*?zoom:\s*1',
        r'id:\s*"reverse"[\s\S]*?label:\s*"反打镜头"[\s\S]*?yaw:\s*180[\s\S]*?pitch:\s*0[\s\S]*?zoom:\s*1',
        r'id:\s*"dutch"[\s\S]*?label:\s*"荷兰角镜头"[\s\S]*?yaw:\s*45[\s\S]*?pitch:\s*-30[\s\S]*?zoom:\s*1',
    ):
        ok(re.search(preset, src), "camera tab preset")
    ok(
        "四宫格" in src
        and "九宫格" in src
        and "十六宫格" in src
        and "二十五宫格" in src,
        "split names",
    )
    ok(
        "2 × 2" in src and "3 × 3" in src and "4 × 4" in src and "5 × 5" in src,
        "split sizes",
    )
    ok("旋转角度 ±90°" in src and "倾斜角度 ±30°" in src, "slider labels")
    ok("鱼眼镜头" in src and "反打镜头" in src and "荷兰角镜头" in src, "angle tabs")
    ok("重置参数" in src, "reset label")
    ok(
        'serviceId = "fal-ai/qwen-image-edit-2511-multiple-angles"' not in src,
        "no hardcoded fal camera id",
    )
    ok("btnCameraAngle" in src and "btnGridSplit" in src, "Claude toolbar ids")
    ok("打光效果" in src, "relight panel title")
    ok(
        "伦勃朗光" in src and "光学焦散" in src and "布达佩斯大饭店" in src,
        "12 lighting preset names",
    )
    ok("function fallbackRealThumb" in src and "LIGHT_PRESET_THUMBS = []" not in src, "lighting thumbnails are real image refs")
    ok("光源描述 (选填)" in src, "lighting desc")
    ok("简单描述你想实现的灯光效果，或情绪风格" in src, "lighting placeholder")
    ok('op: "relight"' in src, "relight op")
    ok(
        "category=text" in src,
        "story catalog must hit text models",
    )
    ok("消除 ◆1" in src, "eraser submit label")
    ok("该方向 fal 不支持" in src, "front/back lighting unsupported")
    ok("btnVideoBar" in src and "合成视频" in src, "compose-video shot-bar entry")
    ok("function classifySelected" in src, "selection classifier")
    ok("SHOTBAR_VIDEO_ITEMS" in src, "video toolbar variant")
    ok(
        "截取帧" in src and "视频增强" in src and "去字幕" in src and "音频分离" in src,
        "video toolbar five labels",
    )
    ok(
        'reason: "本版不做视频增强（无模型、不接商汤）"' in src
        and 'reason: "本版不去做字幕（无模型、不接商汤）"' in src
        and 'reason: "本版不做音频分离（无模型、不接商汤）"' in src,
        "video enhance/unsub/split are skip, not empty clicks",
    )
    ok("function rejectVideoTool" in src, "explicit video refuse")
    ok("SHOTBAR_GROUP_ITEMS" in src, "group toolbar variant")
    ok(
        '"下载"' in src
        and "整组执行" in src
        and "解组" in src
        and "function downloadGroup" in src
        and "function runGroup" in src
        and "function layoutGroup" in src
        and "function ungroup" in src
        and "function ensureGroupWith" in src,
        "group toolbar is real: download/run/layout/ungroup/create",
    )
    ok('kind: "group"' in src, "group kind in classifier")
    ok("局部摘取" in src, "nine-grid toolbar")
    ok("function isNineGridNode" in src, "nine-grid classifier helper")
    ok("n.gridFrom" in src, "split cards keep image toolbar")
    ok("function nineCellRect" in src, "sheet cell geometry")
    ok("NINE_SHEET_GAP" in src, "compose/crop share gap")
    ok("function startNineCrop" in src, "crop enters pick mode")
    ok("function extractNineGridCell" in src, "crop extracts clicked cell")
    ok("data-ninecell" in src, "clickable cell overlay")
    ok("点宫格中的一格摘取" in src, "pick-cell instruction")
    ok("已摘取左上格" not in src, "no always-top-left crop shell")
    ok("nineType: toolUi.nineType" in src, "generated nine-grid tagged")
    ok("编辑文本" in src and "blankPill" in src, "blank-node pill")
    ok("描述你想要生成的图片，或输入 @ 引用角色" in src, "image placeholder")
    ok(
        "结合图片，描述你想生成的角色动作和画面动态" in src,
        "video placeholder",
    )
    ok("发送 (Cmd/Ctrl + Enter)" in src, "send tooltip")
    ok("function applySelectionDefaults" in src, "selection defaults")
    ok('kind: "none"' in src and 'kind: "video"' in src, "state kinds")
    ok("vp._sekoDeselect" in src, "empty-canvas deselect")
    ok(".shot-bar button.skip{" in src, "pano/lip-sync skip is greyed")
    ok(
        '"btnUpscale"' in src and "btnNineGrid" in src,
        "left-rail extras including 超清 stay hidden",
    )
    ok(
        'cls.kind === "group"' in src and 'cls.kind === "nine_grid"' in src,
        "group and nine-grid hide generate dock",
    )
    ok("function exportInpaintMaskPng" in src, "mask png export")
    ok("function sekoCommitMask" in src, "mask upload hook for Claude")
    ok('op: "inpaint"' in src, "inpaint op")
    ok('op: "mask"' not in src, "inpaint is single node, no mask op")
    ok("maskUrl: maskUrl" in src, "inpaint params.maskUrl")
    ok("window.__sekoUploadMask" in src, "mask upload hook name")
    ok("输入你的故事、场景或角色设定" in src and "向后推演" in src and "向前推演" in src, "story placeholder and sliders")
    ok("STORY_PLAN_ENDPOINT" in src and "buildStoryFrameGraph" in src, "story endpoint plans then generates frames")
    ok("skill · 故事导演" in src and "生成 ◆10" in src, "story director controls")
    ok("GMLM" not in src, "do not show GMLM")
    ok("请输入九宫格生成提示词..." in src, "ninegrid placeholder")
    ok(
        "灵感风暴" in src
        and "故事叙述" in src
        and "武打分镜" in src
        and "全景机位" in src,
        "ninegrid types",
    )
    ok("/api/grid/plan" in src, "ninegrid planner endpoint")
    ok("function planNineGridPrompts" in src, "ninegrid planner client")
    ok("function composeNineGridSheet" in src, "ninegrid canvas sheet")
    ok("function buildNineCellGraph" in src, "ninegrid per-cell t2i graph")
    ok(
        'if (state.mode === "text") return "chat"' not in src,
        "text tab does not query chat",
    )
    ok(
        'if (state.mode === "text" || toolUi.story) return "text"' in src,
        "text/story catalog is category=text",
    )
    ok('option value="">默认模型' not in src, "no fake 默认模型 option")
    ok("无可用模型" in src, "empty catalog is explicit")
    ok("不会用默认假值生成" in src, "generate refuses blank serviceId")
    ok("生图必须显式选择图片模型" in src, "text-to-shot requires image catalog")
    ok("keepStory" in src, "story dock survives selecting its text node")
    ok('pickCatalogService(backend, "grid")' not in src, "no catalog grid dead-end")
    ok("category=grid" not in src, "no forged grid catalog filter")
    ok("没有九宫格模型" not in src, "no grid-model dead-end copy")
    ok("不足不静默补空" in src, "planner short list is hard fail")
    ok('serviceId = "fal-ai/iclight-v2"' not in src, "no hardcoded fal relight id")
    ok(
        "btnRelightBar" in src
        and "btnInpaintBar" in src
        and "btnStoryBar" in src
        and "btnNineGridBar" in src
        and "btnVideoBar" in src,
        "shot-bar ids",
    )
    ok("nodeContextMenu" in src, "node context menu exists")
    ok(
        'data-nodeact="copy"' in src
        and 'data-nodeact="paste"' in src
        and 'data-nodeact="delete"' in src,
        "node context menu has copy/paste/delete",
    )
    ok("function deleteNode" in src, "deleteNode exists")
    ok(
        "e.from !== id && e.to !== id" in src,
        "delete removes attached edges",
    )
    ok(
        "n.memberIds.filter((memberId) => memberId !== id)" in src,
        "delete removes group membership",
    )
    ok(
        'e.key !== "Delete" && e.key !== "Backspace"' in src,
        "Delete and Backspace hotkeys",
    )
    ok(
        'e.target.closest("textarea,input,select,[contenteditable]")' in src,
        "delete hotkeys ignore editable controls",
    )
    ok(
        "localStorage.setItem(" in src and "localStorage.getItem(STORE)" in src,
        "graph persists in localStorage",
    )
    print("ok prompt-js-contract")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
