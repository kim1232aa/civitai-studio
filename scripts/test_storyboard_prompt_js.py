#!/usr/bin/env python3
"""Static checks that storyboard.js actually implements the prompt contract."""

from pathlib import Path

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
    ok(
        'id: "fisheye", label: "鱼眼镜头", yaw: 0, pitch: 30, zoom: 1' in src,
        "fisheye tab preset",
    )
    ok(
        'id: "reverse", label: "反打镜头", yaw: 180, pitch: 0, zoom: 1' in src,
        "reverse tab preset",
    )
    ok(
        'id: "dutch", label: "荷兰角镜头", yaw: 45, pitch: -30, zoom: 1' in src,
        "dutch tab preset",
    )
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
    ok("LIGHT_PRESET_THUMBS = []" in src, "no remote lighting thumbs")
    ok("光源描述 (选填)" in src, "lighting desc")
    ok("简单描述你想实现的灯光效果，或情绪风格" in src, "lighting placeholder")
    ok('op: "relight"' in src, "relight op")
    ok("category=relight" in src, "relight catalog")
    ok("消除 ◆1" in src, "eraser submit label")
    ok("该方向 fal 不支持" in src, "front/back lighting unsupported")
    ok("btnVideoBar" in src and "合成视频" in src, "compose-video shot-bar entry")
    ok("function classifySelected" in src, "selection classifier")
    ok("SHOTBAR_VIDEO_ITEMS" in src, "video toolbar variant")
    ok(
        "截取帧" in src
        and "视频增强" in src
        and "去字幕" in src
        and "音频分离" in src,
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
    ok("输入你的故事、场景或角色设定" in src, "story placeholder")
    ok("/api/story" in src, "story endpoint")
    ok("skill · 故事导演" in src, "story director skill chip")
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
    print("ok prompt-js-contract")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
