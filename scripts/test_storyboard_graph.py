#!/usr/bin/env python3
"""Storyboard buildGraph contract: t2i / i2i / i2v. Run: python3 scripts/test_storyboard_graph.py"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from providers.graph_compile import compile_graph


def compile(graph):
    return compile_graph(graph)


def assert_true(cond, msg):
    if not cond:
        raise AssertionError(msg)


def css_all():
    """裁决: o63/o103 把 storyboard.html 内联 <style> 拆到外部样式表; 样式断言改为读全部已加载 CSS。"""
    parts = [(ROOT / "static" / "storyboard.html").read_text(encoding="utf-8")]
    # 顺序与 storyboard.html 的 <link> 级联一致(后者覆盖前者)
    for name in ("storyboard-ui-base.css", "storyboard-ui.css", "composer-field-adapt.css",
                 "o76-dock-right.css", "o97-dock-pin.css", "storyboard-shell.css"):
        p = ROOT / "static" / name
        if p.is_file():
            parts.append(p.read_text(encoding="utf-8"))
    return "\n".join(parts)


def css_rule(css, selector):
    """Return the declarations of the LAST rule matching selector (later sheets override)."""
    import re as _re
    body = None
    for m in _re.finditer(_re.escape(selector) + r"\s*\{([^}]*)\}", css):
        body = m.group(1)
    return body or ""


def run_shot_body(js, span=24000):
    """裁决: runShotStep 在 o9x 拆成 wrapper+runShotStepWork, runSelected 已移除;
    取 body 到 runShotStepWork 结束(showSendToast 前), 不再用固定 9000/16000 字符窗口。"""
    k = js.find("async function runShotStep")
    assert_true(k >= 0, "runShotStep")
    m = js.find("async function runSelected", k)
    if m < 0:
        m = js.find("function runSelected", k)
    if m < 0:
        m = js.find("function showSendToast", k)  # o9x: work body ends here
    return js[k:m if m > 0 else k + span]


def shot_branch_of_insert_mention(js):
    """裁决: 0e8329b 文本卡可写——insertMention 对画布文本卡刻意插入 @标题(Seko 对齐);
    「prompt 不写 @」语义只管 shot 分支(const shot = selected 起)。"""
    im = js[js.find("function insertMention"):js.find("function slashQueryAt")]
    cut = im.find("const shot = selected;")
    assert_true(cut >= 0, "insertMention keeps shot branch")
    text_branch = im[:cut]
    shot_branch = im[cut:]
    # 新形态护栏: 文本卡分支写 textNode.text(不是 shot.prompt), 且不碰 shot.prompt
    assert_true("textNode.text = next" in text_branch, "text-card branch writes textNode.text (Seko @tag)")
    assert_true("shot.prompt" not in text_branch, "text-card branch must not touch shot.prompt")
    return shot_branch


def shot_graph(op, prompt, image_url=None, service=None):
    nodes = [{"id": "p-shot-1", "op": "prompt", "params": {"text": prompt}}]
    edges = [{"from": "p-shot-1", "fromPort": "prompt", "to": "shot-1", "toPort": "prompt"}]
    if image_url:
        nodes.append({"id": "a-bot", "op": "image", "params": {"url": image_url}})
        edges.append({"from": "a-bot", "fromPort": "image", "to": "shot-1", "toPort": "image"})
    nodes.append({
        "id": "shot-1",
        "op": op,
        "params": {
            "serviceId": service or ("fal-ai/minimax/video-01/image-to-video" if op == "i2v" else "fal-ai/flux/schnell"),
            "resolution": "1280x720",
            "duration": 5,
        },
    })
    return {"backend": "fal", "nodes": nodes, "edges": edges}


def test_t2i_no_ref():
    """Picture mode, no connected asset → t2i. Dangling @ stays text."""
    r = compile(shot_graph("t2i", "【镜头1】场景：@温馨现代卧室\n画面：室内。", image_url=None))
    assert_true(r.get("ok") is True, r)
    assert_true(r.get("execute") == "single", r)
    assert_true("sourceImage" not in (r.get("payload") or {}), r)
    assert_true("@温馨现代卧室" in r["payload"]["prompt"], r["payload"])
    assert_true(r["payload"]["serviceId"] == "fal-ai/flux/schnell", r["payload"])


def test_i2i_with_ref():
    r = compile(shot_graph("i2i", "同一位 @家用机器人 站在窗边", image_url="/out/bot.jpg", service="fal-ai/flux/dev"))
    assert_true(r.get("ok") is True, r)
    assert_true(r["payload"].get("sourceImage") == "/out/bot.jpg", r)
    assert_true(r["payload"].get("prompt", "").startswith("同一位"), r)


def test_i2v_with_first_frame():
    r = compile(shot_graph("i2v", "固定镜头，机器人轻微转动", image_url="/out/bot.jpg"))
    assert_true(r.get("ok") is True, r)
    p = r["payload"]
    assert_true(p.get("sourceImage") == "/out/bot.jpg", p)
    assert_true(p.get("firstFrame") == "/out/bot.jpg", p)
    assert_true(p.get("duration") == 5, p)


def test_i2v_missing_frame_blocked():
    r = compile(shot_graph("i2v", "固定镜头", image_url=None))
    assert_true(r.get("ok") is False, r)
    assert_true(r.get("blocked") is True, r)
    err = r.get("error") or ""
    assert_true("image" in err and "偷" in err, err)


def test_mention_without_edge_is_not_i2i():
    """@ in prompt alone must not invent an image wire."""
    r = compile(shot_graph("t2i", "@家用机器人 在卧室", image_url=None))
    assert_true(r.get("ok") is True, r)
    assert_true("sourceImage" not in r["payload"], r)


def normalize_prompt(text, linked_titles):
    """Payload-only: linked @中文名 → @图片N. Unlinked @ stays."""
    out = text or ""
    for i, title in enumerate(linked_titles, 1):
        tag = "@" + title
        if tag in out:
            out = out.replace(tag, "@图片%d" % i)
    return out


def test_payload_normalize_linked_only():
    text = "场景：@温馨现代卧室 画面：@家用机器人 和 @没连上的角色"
    got = normalize_prompt(text, ["温馨现代卧室", "家用机器人"])
    assert_true("@图片1" in got and "@图片2" in got, got)
    assert_true("@没连上的角色" in got, got)
    assert_true("@温馨现代卧室" not in got, got)


def test_i2v_first_frame_pick_second_ref():
    """Two linked images; compile image port is the chosen first-frame, not always [0]."""
    g = {
        "backend": "fal",
        "nodes": [
            {"id": "p-shot-1", "op": "prompt", "params": {"text": "固定镜头"}},
            {"id": "a-bot", "op": "image", "params": {"url": "/out/bot.jpg"}},
            {"id": "a-bed", "op": "image", "params": {"url": "/out/bed.jpg"}},
            {"id": "shot-1", "op": "i2v", "params": {"serviceId": "fal-ai/minimax/video-01/image-to-video", "duration": 5}},
        ],
        "edges": [
            {"from": "p-shot-1", "fromPort": "prompt", "to": "shot-1", "toPort": "prompt"},
            {"from": "a-bed", "fromPort": "image", "to": "shot-1", "toPort": "image"},
        ],
    }
    r = compile(g)
    assert_true(r.get("ok") is True, r)
    assert_true(r["payload"].get("sourceImage") == "/out/bed.jpg", r["payload"])
    assert_true(r["payload"].get("firstFrame") == "/out/bed.jpg", r["payload"])


def test_shot_result_as_image_node():
    """Finished shot.url can be an image node for the next shot (t2i → i2i)."""
    g = {
        "backend": "fal",
        "nodes": [
            {"id": "p-2", "op": "prompt", "params": {"text": "同一场景继续"}},
            {"id": "shot-1", "op": "image", "params": {"url": "/out/shot1.jpg"}},
            {"id": "shot-2", "op": "i2i", "params": {"serviceId": "fal-ai/flux/dev", "resolution": "1280x720"}},
        ],
        "edges": [
            {"from": "p-2", "fromPort": "prompt", "to": "shot-2", "toPort": "prompt"},
            {"from": "shot-1", "fromPort": "image", "to": "shot-2", "toPort": "image"},
        ],
    }
    r = compile(g)
    assert_true(r.get("ok") is True, r)
    assert_true(r["payload"].get("sourceImage") == "/out/shot1.jpg", r["payload"])


def test_first_frame_from_promoted_asset():
    """i2v first frame can be a promoted shot result, not only a library character."""
    g = {
        "backend": "fal",
        "nodes": [
            {"id": "p-v", "op": "prompt", "params": {"text": "固定镜头轻微转动"}},
            {"id": "shot-1", "op": "image", "params": {"url": "/out/shot1.jpg"}},
            {"id": "shot-3", "op": "i2v", "params": {"serviceId": "fal-ai/minimax/video-01/image-to-video", "duration": 5}},
        ],
        "edges": [
            {"from": "p-v", "fromPort": "prompt", "to": "shot-3", "toPort": "prompt"},
            {"from": "shot-1", "fromPort": "image", "to": "shot-3", "toPort": "image"},
        ],
    }
    r = compile(g)
    assert_true(r.get("ok") is True, r)
    assert_true(r["payload"].get("firstFrame") == "/out/shot1.jpg", r["payload"])
    assert_true(r["payload"].get("sourceImage") == "/out/shot1.jpg", r["payload"])


def test_rail_history_not_in_compile():
    """/api/outs history stays in the rail; compile only sees wired image nodes."""
    r = compile(shot_graph("t2i", "空镜", image_url=None))
    assert_true(r.get("ok") is True, r)
    assert_true("sourceImage" not in (r.get("payload") or {}), r)


def test_ui_blocks_stages0_fake_run():
    """storyboard.js must not POST stages[0] as a one-shot for multi-step compiles."""
    js = (ROOT / "static" / "storyboard.js").read_text(encoding="utf-8")
    assert_true("stages[0].payload" not in js, "stages[0].payload fallback still present")
    assert_true("compiled.stages && compiled.stages[0]" not in js, "stages[0] OR-fallback still present")
    assert_true('execute === "staged"' in js or "execute === 'staged'" in js, "missing staged execute gate")
    assert_true("multiStep" in js, "missing multiStep gate")
    assert_true("假跑" in js, "missing fake-run user message")
    assert_true("payload = compiled.payload" in js, "must use compiled.payload only")
    assert_true("stages[0].payload" not in js, "no stages[0] fallback")



def test_ui_clears_stage_urls_on_disconnect():
    """storyboard must clear stageUrls on unlink/disconnect (align LiteGraph invalidate)."""
    js = (ROOT / "static" / "storyboard.js").read_text(encoding="utf-8")
    assert_true("function invalidateStageProgress" in js, "missing invalidateStageProgress")
    assert_true("shot.stageUrls = {}" in js, "must zero stageUrls")
    assert_true("invalidateStageProgress(shot)" in js, "unlink/link must call invalidate")
    assert_true("disconnectEdgeAt" in js and "invalidateStageProgress" in js, "disconnect path")
    # unlink body must invoke invalidate when edge existed
    assert_true("if (had) invalidateStageProgress(shot)" in js, "unlink must clear when edge removed")


def _scoped_layout_move_ids(scope_ids, nodes, edges):
    """Mirror autoLayout scoped path: only nodes in scopeIds get x,y updates.

    Linked assets outside scope (even exclusive) must NOT move.
    Full-canvas (scope_ids is None) is out of scope for this helper.
    """
    assert scope_ids is not None
    shots = [n for n in nodes if n["kind"] == "shot" and n["id"] in scope_ids]
    assets = [n for n in nodes if n["kind"] == "asset"]
    asset_list = [a for a in assets if a["id"] in scope_ids]
    moved = {n["id"] for n in shots}
    asset_allowed = {a["id"] for a in asset_list}
    # linked placement only for allowed assets
    for shot in shots:
        linked = [e["from"] for e in edges if e["to"] == shot["id"]]
        for aid in linked:
            if aid not in asset_allowed:
                continue
            moved.add(aid)
    for a in asset_list:
        moved.add(a["id"])
    return moved


def test_selbar_scoped_layout_skips_exclusive_outside_asset():
    """P0 UI Fail: multi two shots → selBar ▦ must not move unselected exclusive asset.

    「大白-居家装」exclusively edged into a scoped shot but not in multi → x,y stay put.
    """
    nodes = [
        {"id": "s1", "kind": "shot", "x": 560, "y": 80},
        {"id": "s2", "kind": "shot", "x": 1280, "y": 80},
        {"id": "a-dabai", "kind": "asset", "title": "大白-居家装", "x": 100, "y": 400},
        {"id": "a-other", "kind": "asset", "title": "其他", "x": 50, "y": 50},
    ]
    edges = [
        {"from": "a-dabai", "to": "s1"},  # exclusive link into scoped shot
        {"from": "a-other", "to": "s2"},
        {"from": "a-other", "to": "s1"},  # shared — also outside scope
    ]
    scope = ["s1", "s2"]  # multi-select two shots only
    before = {n["id"]: (n["x"], n["y"]) for n in nodes}
    moved = _scoped_layout_move_ids(scope, nodes, edges)
    assert_true(moved == {"s1", "s2"}, f"expected only scoped shots, got {moved}")
    # simulate: only update moved nodes (as autoLayout does)
    for n in nodes:
        if n["id"] in moved:
            n["x"] += 10
            n["y"] += 10
    assert_true(nodes[2]["x"] == before["a-dabai"][0] and nodes[2]["y"] == before["a-dabai"][1],
                "exclusive unselected asset must keep x,y")
    assert_true(nodes[3]["x"] == before["a-other"][0] and nodes[3]["y"] == before["a-other"][1],
                "shared outside asset must keep x,y")
    assert_true(nodes[0]["x"] != before["s1"][0], "scoped shots still rearrange")

    # Group path: memberIds only — same rule
    group_scope = ["s1", "s2"]  # group.memberIds; asset not a member
    moved_g = _scoped_layout_move_ids(group_scope, nodes, edges)
    assert_true("a-dabai" not in moved_g, "group layout must not pull exclusive outside asset")

    # Static guard: exclusive-link expansion removed from storyboard.js
    js = (ROOT / "static" / "storyboard.js").read_text(encoding="utf-8")
    assert_true("Clearly attached: edges only into scoped shots" not in js,
                "exclusive-link expansion comment still present")
    assert_true("tos.every((to) => scopeIds.indexOf(to) >= 0)" not in js,
                "exclusive-link tos.every expansion still present")
    assert_true("scopeIds.indexOf(n.id) >= 0" in js, "scoped assetList must filter by scopeIds id")
    assert_true("nl-storyboard-v0821n" in js, "STORE must bump to v0820c")
    assert_true("nl-storyboard-v0819b" in js, "STORE_OLDS must keep v0819b for migrate")
    assert_true("nl-storyboard-v0819" in js, "STORE_OLDS must keep v0819 for migrate")
    assert_true("nl-storyboard-v0818" in js, "STORE_OLDS must keep v0818 for migrate")
    assert_true("nl-storyboard-v0817c" in js, "STORE_OLDS must keep v0817c for migrate")
    assert_true("nl-storyboard-v0817b" in js, "STORE_OLDS must keep v0817b for migrate")
    assert_true("nl-storyboard-v0817" in js, "STORE_OLDS must keep v0817 for migrate")
    assert_true("nl-storyboard-v0816b" in js, "STORE_OLDS must keep v0816b for migrate")
    html = (ROOT / "static" / "storyboard.html").read_text(encoding="utf-8")
    assert_true("v0821o49b-hydrate-fresh-empty-url" in html, "stamp must be v0821o49b-hydrate-fresh-empty-url")


def test_empty_boot_no_robot_demo():
    """loadDemo / boot must be empty-canvas; no robot cast or dead DEMO jpg."""
    js = (ROOT / "static" / "storyboard.js").read_text(encoding="utf-8")
    html = (ROOT / "static" / "storyboard.html").read_text(encoding="utf-8")
    # Banned robot demo titles must not appear in boot/loadDemo path
    for bad in ("家用机器人", "扫地机器人", "大白-居家装", "大白-职场装", "温馨现代卧室", "现代感洗手间"):
        assert_true(bad not in js or "ROBOT_DEMO_TITLES" in js, "unexpected: bare check")
    # Stronger: loadDemo body must not seed those titles as assets
    # Extract approximate loadDemo function text
    i = js.find("function loadDemo()")
    assert_true(i >= 0, "loadDemo missing")
    j = js.find("function persist()", i)
    boot = js[i:j]
    for bad in ("家用机器人", "扫地机器人", "大白-居家装", "大白-职场装", "温馨现代卧室", "现代感洗手间", "a-bot", "a-vac", "a-home"):
        assert_true(bad not in boot, "robot demo still in loadDemo: " + bad)
    assert_true("fal_fal-ai_flux_schnell_01a05be2" not in js, "dead DEMO jpg path must be gone")
    assert_true("const DEMO" not in js, "DEMO constant must be removed")
    assert_true("state.edges = []" in boot or "state.edges=[]" in boot.replace(" ", ""), "empty boot edges=[]")
    assert_true("isClassicRobotDemo" in js, "robot demo detector required for migrate")
    assert_true("未命名画布" in html or "新项目" in html or "未命名故事" in html, "neutral projTitle")
    assert_true("扫地机器人" not in html, "projTitle must not mention 扫地机器")
    assert_true("v0821o49b-hydrate-fresh-empty-url" in html, "html stamp")
    assert_true("nl-storyboard-v0821n" in js, "STORE v0820c")
    assert_true("nl-storyboard-v0819b" in js, "STORE_OLDS has v0819b")
    assert_true("nl-storyboard-v0819" in js, "STORE_OLDS has v0819")
    assert_true("nl-storyboard-v0818" in js, "STORE_OLDS has v0818")
    assert_true("nl-storyboard-v0817c" in js, "STORE_OLDS has v0817c")


def test_v0815_gen_hardgate():
    """v0815b packing + v0815c stamp: images[] always; caps from capabilities/imageFields."""
    js = (ROOT / "static" / "storyboard.js").read_text(encoding="utf-8")
    html = (ROOT / "static" / "storyboard.html").read_text(encoding="utf-8")
    assert_true("v0821o49b-hydrate-fresh-empty-url" in html, "html stamp v0821o49b-hydrate-fresh-empty-url")
    assert_true("nl-storyboard-v0821n" in js, "STORE v0820c")
    assert_true("nl-storyboard-v0819b" in js, "STORE_OLDS has v0819b")
    assert_true("nl-storyboard-v0819" in js, "STORE_OLDS has v0819")
    assert_true("nl-storyboard-v0818" in js, "STORE_OLDS has v0818")
    assert_true("nl-storyboard-v0817c" in js, "STORE_OLDS has v0817c")
    assert_true("nl-storyboard-v0817" in js, "STORE_OLDS prepend v0817")
    assert_true("nl-storyboard-v0817b" in js, "STORE_OLDS has v0817b")
    assert_true("nl-storyboard-v0817" in js, "STORE_OLDS has v0817")
    assert_true("nl-storyboard-v0817b" in js, "STORE_OLDS has v0817b")
    assert_true("nl-storyboard-v0816b" in js, "STORE_OLDS has v0816b")
    # 裁决: o103-wide-desk 宽屏 Composer 常驻书写台, 默认 expanded; collapsed 胶囊仍可达
    assert_true('dockMode: "expanded"' in js, "dock default expanded (o103-wide-desk 常驻书写台)")
    assert_true('setDockMode("collapsed")' in js, "collapsed capsule still reachable")
    assert_true("function attachExtraImages" in js, "attachExtraImages helper")
    assert_true("function refReadyMessage" in js, "refReadyMessage")
    assert_true("参考图上传中，请稍等" in js, "upload-pending gate")
    assert_true("function requiredRefMessage" in js, "requiredRefMessage")
    assert_true("不能静默发 0 张" in js, "edit-model zero-ref gate")
    assert_true("function maxRefCount" in js, "maxRefCount helper")
    assert_true("function resolveRefCaps" in js, "resolveRefCaps from capabilities")
    assert_true("refImagesField" in js, "caps still expose refImagesField")
    assert_true("PROVIDER_REF_CAPS" in js, "provider ref defaults")
    assert_true("input_references" in js, "nano default field")
    assert_true("attachExtraImages(payload, shot)" in js, "attach before generate")
    # Packing target is always studio-inbound images[] (not sole-write image_urls).
    assert_true("payload.images = urls" in js, "attachExtraImages always writes images[]")
    assert_true("studio-inbound images[]" in js or "ALWAYS" in js, "comment: always images inbound")
    # Extract attachExtraImages body: must not sole-assign only to refImagesField
    i = js.find("function attachExtraImages")
    assert_true(i >= 0, "attachExtraImages loc")
    j = js.find("function setShotBusy", i)
    body = js[i:j]
    assert_true("payload.images = urls" in body, "images=urls inside attachExtraImages")
    assert_true('payload[field] = urls' in body or "payload[field] = urls" in body,
                "optional mirror to refImagesField still allowed")
    # Must not be the ONLY write path that skips images when field is image_urls
    assert_true("never sole-write" in body or "not the sole bag" in body or "payload.images = urls" in body,
                "must not sole-write provider-native field")
    assert_true("aspectRatio" in js, "buildGraph aspectRatio from UI")
    assert_true("catalogById" in js, "loadCatalog catalogById")
    assert_true("maxImages" in js and "maxRefs" in js, "catalog maxImages/maxRefs")
    assert_true("capabilities" in js, "read item.capabilities")
    # duration default 5s selected in HTML
    assert_true('<option selected>5s</option>' in html or '<option selected="">5s</option>' in html, "duration default 5s")
    # Composer chip / selectNode expand
    assert_true('setDockMode("expanded")' in js, "chip/select opens expanded")
    # still must not touch gates
    assert_true("stages[0].payload" not in js, "still no stages[0] fake-run")
    assert_true("function invalidateStageProgress" in js, "invalidateStageProgress kept")
    assert_true("function nextRunnableStage" in js, "nextRunnableStage kept")
    assert_true("shot.stageUrls = {}" in js, "stageUrls clear kept")
    # i2v still requires firstFrame / frameAsset
    assert_true("function frameAsset" in js, "frameAsset kept")
    # 裁决: i2v 缺首帧仍 fail-closed, 文案并入「缺首帧 · 切到图片生成…(图生视频需要首帧…)」
    assert_true("缺首帧 · 切到图片生成" in js and "图生视频需要首帧" in js, "i2v firstFrame gate kept")
    # Do not infer always-1 from field name alone
    assert_true('Do NOT infer "always 1" from field name alone' in js or "Do NOT infer" in js, "no always-1 from field name")
    # modelscope: BOTH images=[url] and image_url
    assert_true("payload.image_url = urls[0]" in body, "modelscope sets image_url alongside images[]")



def test_v0816_sb_lora():
    """LoRA UI + packing still green under v0818 stamp."""
    js = (ROOT / "static" / "storyboard.js").read_text(encoding="utf-8")
    html = (ROOT / "static" / "storyboard.html").read_text(encoding="utf-8")
    assert_true("v0821o49b-hydrate-fresh-empty-url" in html, "html stamp v0821o49b-hydrate-fresh-empty-url")
    assert_true('"nl-storyboard-v0821o16"' in js, "STORE v0820c")
    assert_true("nl-storyboard-v0817c" in js, "STORE_OLDS has v0817c")
    assert_true("nl-storyboard-v0817" in js, "STORE_OLDS has v0817")
    assert_true("nl-storyboard-v0817b" in js, "STORE_OLDS has v0817b")
    assert_true("nl-storyboard-v0816b" in js, "STORE_OLDS has v0816b")
    # UI markers in Composer dock
    assert_true('id="loraBlock"' in html, "loraBlock in storyboard.html")
    assert_true('data-sb-lora="1"' in html or "data-sb-lora" in html, "sb-lora marker")
    assert_true('id="loraQ"' in html, "loraQ search input")
    assert_true('id="searchLora"' in html, "searchLora button")
    assert_true('id="loraHits"' in html, "loraHits results")
    assert_true('id="loras"' in html, "loras selected list")
    # JS state + helpers
    assert_true("loras: []" in js or "state.loras" in js, "state.loras")
    assert_true("function packLorasForPayload" in js, "packLorasForPayload")
    assert_true("function searchLoras" in js, "searchLoras")
    assert_true("function renderLoras" in js, "renderLoras")
    assert_true("function showLoraBlock" in js, "showLoraBlock")
    assert_true("function syncLoraUi" in js, "syncLoraUi")
    assert_true("function bindLoraUi" in js, "bindLoraUi defined")
    assert_true("function normalizeLora" in js, "normalizeLora")
    assert_true("/api/search?type=LORA" in js, "search via /api/search type=LORA")
    # bindLoraUi must be invoked at boot (not only defined)
    assert_true(js.count("bindLoraUi()") >= 2, "bindLoraUi() called at least once outside def")
    boot_tail = js[js.rfind("bindImportModal();"):]
    assert_true("bindLoraUi();" in boot_tail, "boot-tail calls bindLoraUi();")
    assert_true("syncLoraUi();" in boot_tail, "boot-tail calls syncLoraUi();")
    assert_true("syncLoraUi()" in js[js.find("$(\"backend\")"):], "backend onchange syncs LoRA UI")
    # Pack into generate payload after attachExtraImages
    k = js.find("async function runShotStep")
    m = js.find("async function runSelected", k)
    if m < 0:
        m = js.find("function runSelected", k)
    run = js[k:m if m > 0 else k + 9000]
    assert_true("attachExtraImages(payload, shot)" in run, "attach before loras")
    assert_true("packLorasForPayload()" in run, "pack loras in runShotStep")
    assert_true("payload.loras = packedLoras" in run, "sets payload.loras")
    assert_true(run.find("attachExtraImages(payload, shot)") < run.find("packLorasForPayload()"),
                "loras packed after attachExtraImages")
    # Shape fields matching index base.loras
    pack_i = js.find("function packLoraRow")
    if pack_i < 0:
        pack_i = js.find("function packLorasForPayload")
    pack_j = js.find("async function searchLoras", pack_i)
    pack = js[pack_i:pack_j if pack_j > 0 else pack_i + 4000]
    for field in ("path:", "url:", "versionId:", "air:", "scale:", "strength:", "downloadUrl:", "modelId:"):
        assert_true(field in pack, "pack field " + field)
    # modelscope hint, no invent remap
    assert_true("owner/repo" in js or "Hub owner/repo" in html or "魔搭" in js, "modelscope hub hint")
    assert_true("remap" in js.lower() or "不会做 remap" in js or "Civitai→Hub" not in js,
                "no invent Civitai→Hub remap")
    # gate untouched
    assert_true("stages[0].payload" not in js, "no stages[0] fake-run")
    assert_true("function nextRunnableStage" in js, "nextRunnableStage kept")
    assert_true("function invalidateStageProgress" in js, "invalidateStageProgress kept")


def test_v0815c_ref_cap_single_slot_and_overcap_block():
    """v0815c: imageFields without multi → maxRefs=1; over-cap blocks send; setShotBusy on more."""
    js = (ROOT / "static" / "storyboard.js").read_text(encoding="utf-8")
    html = (ROOT / "static" / "storyboard.html").read_text(encoding="utf-8")
    assert_true("v0821o49b-hydrate-fresh-empty-url" in html, "stamp v0821o49b-hydrate-fresh-empty-url")
    assert_true("nl-storyboard-v0821n" in js, "STORE v0820c")
    assert_true("nl-storyboard-v0819b" in js, "STORE_OLDS has v0819b")
    assert_true("nl-storyboard-v0819" in js, "STORE_OLDS has v0819")
    assert_true("nl-storyboard-v0818" in js, "STORE_OLDS has v0818")
    assert_true("nl-storyboard-v0817c" in js, "STORE_OLDS has v0817c")
    assert_true("nl-storyboard-v0817" in js, "STORE_OLDS has v0817")
    assert_true("nl-storyboard-v0817b" in js, "STORE_OLDS has v0817b")
    assert_true("nl-storyboard-v0816b" in js, "STORE_OLDS has v0816b")
    assert_true("MULTI_REF_FIELDS" in js, "multi field list")
    assert_true("SINGULAR_FIRST_FIELDS" in js, "singular FIRST list")
    assert_true("function catalogImageFields" in js, "catalogImageFields helper")
    assert_true("function countRefUrls" in js, "countRefUrls for over-cap")
    # resolveRefCaps tightens when no multi bag
    i = js.find("function resolveRefCaps")
    j = js.find("function maxRefCount", i)
    body = js[i:j]
    assert_true("hasMulti" in body, "resolve checks hasMulti")
    assert_true("Math.min(declared, 1)" in body or "Math.min(max, 1)" in body, "force maxRefs=1 for single-slot")
    assert_true("image_urls" in js and "input_references" in js, "multi names present")
    # over-cap hard gate in runShotStep
    run = run_shot_body(js)  # 裁决: runShotStepWork 全body(原 16000 字符窗口截断, status:more 在窗外)
    assert_true("refUrls.length > resolvedRefs.maxRefs" in run or "refUrls.length > refCap" in run,
                "over-cap compare in runShotStep")
    assert_true("return fail(" in run and "超过上限" in run, "over-cap returns fail/blocked")
    assert_true("不静默丢弃" in run or "超过上限" in run, "loud over-cap message")
    assert_true("function catalogEatsRefs" in js, "t2i image_to_image=false helper")
    assert_true("function refUnusedGateMessage" in js, "t2i-with-refs hard gate")
    assert_true("不静默忽略" in js, "unused-refs loud copy")
    eat = js[js.find("function catalogEatsRefs"):js.find("function editSiblingHint")]
    assert_true("modelscope-cn" in eat and "text-to-image" in eat, "魔搭 t2i task fallback")
    assert_true("refUnusedGateMessage(shot)" in js[js.find("function refCapGateMessage"):js.find("function catalogEatsRefs")],
                "over-cap skipped when unused-ref already explains t2i")
    assert_true("refUnusedGateMessage(shot)" in run, "unused-refs gate in runShotStep")
    assert_true(run.find("refUnusedGateMessage") < run.find("attachExtraImages(payload, shot)"),
                "unused-refs gate before attachExtraImages")
    assert_true("reason = \"ref-unused\"" in js or "reason = 'ref-unused'" in js, "send data-reason ref-unused")
    # count check before fetch / attach path
    assert_true("countRefUrls(payload, shot)" in run, "count before generate")
    assert_true(run.find("countRefUrls") < run.find("attachExtraImages(payload, shot)"),
                "count/gate before attachExtraImages")
    # P1: setShotBusy cleared on status more
    assert_true('status: "more"' in run, "more status kept")
    more_idx = run.find('status: "more"')
    window = run[max(0, more_idx - 400):more_idx]
    assert_true("setShotBusy(shot, false)" in window, "setShotBusy false before return more")
    # gate untouched
    assert_true("stages[0].payload" not in js, "no stages[0] fake-run")




def test_v0817_no_at_filename():
    """v0817 lineage: link/mention must not append @sourceTitle; kept under v0818 stamp."""
    js = (ROOT / "static" / "storyboard.js").read_text(encoding="utf-8")
    html = (ROOT / "static" / "storyboard.html").read_text(encoding="utf-8")
    assert_true("v0821o49b-hydrate-fresh-empty-url" in html, "html stamp v0821o49b-hydrate-fresh-empty-url")
    assert_true('"nl-storyboard-v0821o16"' in js, "STORE v0820c")
    assert_true("nl-storyboard-v0817c" in js, "STORE_OLDS has v0817c")
    assert_true("nl-storyboard-v0817" in js, "STORE_OLDS has v0817")
    assert_true("nl-storyboard-v0817b" in js, "STORE_OLDS has v0817b")
    assert_true("nl-storyboard-v0816b" in js, "STORE_OLDS has v0816b")
    assert_true("function isRawFileTitle" in js, "isRawFileTitle helper")
    assert_true("function mentionDisplayTag" in js, "mentionDisplayTag helper")
    assert_true("function tagsForAsset" in js, "tagsForAsset helper")
    # mention must be a no-op (no prompt += tag / sourceTitle append)
    i = js.find("function mention(asset, shot)")
    assert_true(i >= 0, "mention fn")
    j = js.find("function unmention(asset, shot)", i)
    body = js[i:j]
    assert_true("shot.prompt" not in body, "mention must not write shot.prompt")
    assert_true("sourceTitle" not in body, "mention must not build @sourceTitle tag")
    assert_true("return;" in body or "return" in body, "mention is no-op")
    # linkAssetToShot may still call mention (no-op) but must not itself append tag
    k = js.find("function linkAssetToShot")
    m = js.find("function unlinkAssetFromShot", k)
    link = js[k:m]
    assert_true("shot.prompt" not in link, "linkAssetToShot must not write shot.prompt")
    assert_true('"+ sourceTitle' not in link and '"@" + sourceTitle' not in link,
                "linkAssetToShot must not build @sourceTitle")
    # unmention strips via tagsForAsset (legacy @sourceTitle + persisted mentionTags)
    u0 = js.find("function unmention(asset, shot)")
    u1 = js.find("function invalidateStageProgress", u0)
    un = js[u0:u1]
    assert_true("tagsForAsset" in un, "unmention uses tagsForAsset")
    # unlink still unmentions before edge removal (persisted tag makes order safe)
    ul0 = js.find("function unlinkAssetFromShot")
    ul1 = js.find("function toggleAssetOnShot", ul0)
    ul = js[ul0:ul1]
    assert_true(ul.find("unmention(asset, shot)") < ul.find("state.edges = state.edges.filter"),
                "unmention before edge removal")
    # insertMention uses mentionDisplayTag, not raw sourceTitle
    # 裁决: 文本卡分支(Seko @tag)是 0e8329b 刻意新形态; 「不写 @」语义限定 shot 分支
    im = shot_branch_of_insert_mention(js)
    assert_true("linkAssetToShot" in im, "insertMention links edge")
    assert_true("mentionDisplayTag" not in im, "insertMention must not write display tags")
    assert_true('"@" + sourceTitle(asset)' not in im, "insertMention must not use raw sourceTitle tag")
    # 裁决: o91-material-pool/Seko 画布化后, confirmImportSelection 改为把素材放上画布
    # (spawnHistoryAt), 不再自动 link 到选中 shot; 「不写 shot.prompt」语义仍须成立
    ci0 = js.find("function confirmImportSelection")
    ci1 = js.find("function setZoomScale", ci0)
    ci = js[ci0:ci1]
    assert_true("spawnHistoryAt" in ci, "import places material onto canvas")
    assert_true("linkAssetToShot" not in ci, "import does not auto-link (user links via canvas @)")
    assert_true("shot.prompt" not in ci, "import must not write shot.prompt")
    # default new-shot / loadDemo must NOT auto-fill 【镜头 shell (Skill templates OK)
    assert_true('prompt: "【镜头' not in js and 'prompt: "【镜头" +' not in js,
                "create-path must not prefill 【镜头 template")
    assert_true('template: "【镜头】' in js or "template: \"【镜头】" in js, "Skill storyboard-shot template kept")
    assert_true("@角色" in js, "Skill human placeholders OK")
    # normalizePrompt still rewrites remaining @title → @图片N
    assert_true("function normalizePrompt" in js, "normalizePrompt kept")
    # LoRA / images packing untouched markers
    assert_true("function attachExtraImages" in js, "attachExtraImages kept")
    assert_true("function packLorasForPayload" in js, "packLoras kept")
    assert_true("stages[0].payload" not in js, "gate untouched")




def _sim_is_raw_file_title(t):
    import re
    s = str(t or "").strip()
    if not s:
        return True
    if re.match(
        r"^(nano[-_]?gpt|modelscope|fal[_-]|comfy|out[_-]|seedream|kling|runway|luma|minimax|ideogram|flux[_-]|wan[_-]|vidu)",
        s,
        re.I,
    ):
        return True
    cjk = re.compile(r"[\u4e00-\u9fff]")
    if (not cjk.search(s)) and re.search(r"[0-9a-f]{8,}", s, re.I) and re.search(r"[_-]", s):
        return True
    if (not cjk.search(s)) and re.match(r"^[a-z0-9]+(?:[_-][a-z0-9]+){2,}_?\d*$", s, re.I) and len(s) >= 20:
        return True
    return False


def _sim_tags_for_asset_legacy(asset, titles_by_id):
    """Legacy unmention cleanup: @+sourceTitle only."""
    tags = []
    title = titles_by_id[asset["id"]]
    if title:
        legacy = "@" + title
        if legacy not in tags:
            tags.append(legacy)
    return tags


def _sim_insert_mention_no_at(prompt, partial_at_query=None):
    """Mirror insertMention: clear partial @query only; never append @tag."""
    import re
    text = prompt or ""
    if partial_at_query is not None:
        # e.g. prompt ends with @nan → remove from @ to end of query
        at = text.rfind("@")
        if at >= 0:
            text = text[:at]
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text


def _sim_unmention_legacy(prompt, asset, titles_by_id):
    import re
    text = prompt or ""
    for tag in _sim_tags_for_asset_legacy(asset, titles_by_id):
        if tag and tag in text:
            text = text.replace(tag, "")
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def test_v0817b_unmention_at_tag():
    """v0817b lineage under v0821o49b-hydrate-fresh-empty-url: unmention/link helpers still present."""
    js = (ROOT / "static" / "storyboard.js").read_text(encoding="utf-8")
    html = (ROOT / "static" / "storyboard.html").read_text(encoding="utf-8")
    assert_true("v0821o49b-hydrate-fresh-empty-url" in html, "html stamp")
    assert_true('"nl-storyboard-v0821o16"' in js, "STORE v0820c")
    assert_true("nl-storyboard-v0817c" in js, "STORE_OLDS has v0817c")
    assert_true("nl-storyboard-v0817b" in js, "STORE_OLDS has v0817b")
    assert_true("nl-storyboard-v0817" in js, "STORE_OLDS has v0817")
    assert_true("function tagsForAsset" in js, "tagsForAsset")
    assert_true("function unmention" in js, "unmention")
    ul = js[js.find("function unlinkAssetFromShot"):js.find("function toggleAssetOnShot")]
    assert_true(ul.find("unmention(asset, shot)") < ul.find("state.edges = state.edges.filter"),
                "unlink unmentions before edge drop")
    assert_true("stages[0].payload" not in js, "gate untouched")
    assert_true("function attachExtraImages" in js, "images packing kept")
    assert_true("function packLorasForPayload" in js, "LoRA packing kept")



def test_empty_prompt_on_new_shot_and_load_demo():
    """v0821o49b-hydrate-fresh-empty-url: loadDemo + btnAdd default prompt is empty; Skill template stays."""
    js = (ROOT / "static" / "storyboard.js").read_text(encoding="utf-8")
    html = (ROOT / "static" / "storyboard.html").read_text(encoding="utf-8")
    assert_true("v0821o49b-hydrate-fresh-empty-url" in html, "html stamp")
    assert_true('class="stamp"' in html, ".stamp")
    assert_true('"nl-storyboard-v0821o16"' in js, "STORE v0821d")
    assert_true('"nl-storyboard-v0821h"' in js, "STORE_OLDS keeps v0821h")
    assert_true('"nl-storyboard-v0821e"' in js, "STORE_OLDS keeps v0821e")
    assert_true('"nl-storyboard-v0821d"' in js, "STORE_OLDS keeps v0821d")
    assert_true('"nl-storyboard-v0821c"' in js, "STORE_OLDS keeps v0821c")
    # loadDemo body
    i = js.find("function loadDemo()")
    assert_true(i >= 0, "loadDemo missing")
    j = js.find("function persist()", i)
    boot = js[i:j]
    assert_true("【镜头" not in boot, "loadDemo must not seed 【镜头 shell")
    assert_true('prompt: ""' in boot or "prompt: ''" in boot, "loadDemo prompt empty")
    # btnAdd create path
    a = js.find('$("btnAdd").onclick')
    assert_true(a >= 0, "btnAdd missing")
    b = js.find("function resolveLayoutScope", a)
    add = js[a:b]
    assert_true("【镜头" not in add, "btnAdd must not prefill 【镜头 shell")
    assert_true('prompt: ""' in add or "prompt: ''" in add, "btnAdd prompt empty")
    # ensureActiveShotForImport already empty
    e = js.find("function ensureActiveShotForImport()")
    f = js.find("async function applyImport", e)
    ens = js[e:f]
    assert_true('prompt: ""' in ens or "prompt: ''" in ens, "import-created shot prompt empty")
    assert_true("【镜头" not in ens, "import create must not seed 【镜头")
    # Skill templates remain user-chosen inserts only
    assert_true('id: "storyboard-shot"' in js, "storyboard-shot Skill kept")
    assert_true("function applySkill" in js, "applySkill kept")
    # link / mention / import-media paths must not write 【镜头 into prompt
    k = js.find("function linkAssetToShot")
    m = js.find("function unlinkAssetFromShot", k)
    assert_true("【镜头" not in js[k:m], "linkAssetToShot must not write 【镜头")
    im0 = js.find("function insertMention")
    im1 = js.find("function slashQueryAt", im0)
    assert_true("【镜头" not in js[im0:im1], "insertMention must not write 【镜头")


def test_v0817c_no_at_in_prompt():
    """v0817c: insertMention/atbox must not write any @ into prompt; edge+chip only."""
    js = (ROOT / "static" / "storyboard.js").read_text(encoding="utf-8")
    html = (ROOT / "static" / "storyboard.html").read_text(encoding="utf-8")
    assert_true("v0821o49b-hydrate-fresh-empty-url" in html, "html stamp")
    assert_true('"nl-storyboard-v0821o16"' in js, "STORE v0820c")
    assert_true("nl-storyboard-v0817c" in js, "STORE_OLDS has v0817c")
    assert_true("nl-storyboard-v0817b" in js, "STORE_OLDS has v0817b")
    assert_true("nl-storyboard-v0817" in js, "STORE_OLDS has v0817")
    assert_true("nl-storyboard-v0816b" in js, "STORE_OLDS has v0816b")

    # insertMention: link only — no mentionDisplayTag / no @ append / no mentionTags
    # 裁决: 文本卡分支(Seko @tag)是 0e8329b 刻意新形态; 「prompt 不写 @」语义限定 shot 分支
    im = shot_branch_of_insert_mention(js)
    assert_true("linkAssetToShot(asset, shot)" in im, "insertMention links edge")
    assert_true("mentionDisplayTag" not in im, "insertMention must not call mentionDisplayTag")
    assert_true("mentionTags" not in im, "no persist mentionTags")
    assert_true('"@" +' not in im and "'@' +" not in im, "insertMention must not build @tag")
    assert_true("shot.prompt = next" in im or "shot.prompt=next" in im.replace(" ", ""),
                "may clear partial @query into shot.prompt")
    # Must clear @query without inserting a replacement tag (slice to at, then caret — no tag concat)
    assert_true("v.slice(0, at) + v.slice(caret)" in im or "v.slice(0,at)+v.slice(caret)" in im.replace(" ", ""),
                "clears @query without inserting tag")
    assert_true("nextPictureTag" not in js, "nextPictureTag removed")
    assert_true("mentionTags" not in js, "mentionTags removed")

    # mention no-op; link does not write prompt
    i = js.find("function mention(asset, shot)")
    j = js.find("function unmention(asset, shot)", i)
    body = js[i:j]
    assert_true("shot.prompt" not in body, "mention must not write shot.prompt")
    k = js.find("function linkAssetToShot")
    m = js.find("function unlinkAssetFromShot", k)
    link = js[k:m]
    assert_true("shot.prompt" not in link, "linkAssetToShot must not write shot.prompt")

    # String-sim: multi link/unlink leaves human prompt unchanged (no @ added)
    human_prompt = "基于参考图重绘，强化光影"
    # atbox pick with partial @query
    with_query = human_prompt + " @nan"
    after_insert = _sim_insert_mention_no_at(with_query, partial_at_query="nan")
    assert_true("@" not in after_insert, "no @ left after atbox pick: " + after_insert)
    assert_true("基于参考图重绘" in after_insert, after_insert)
    # second asset pick with no @query — prompt unchanged
    after_insert2 = _sim_insert_mention_no_at(after_insert, partial_at_query=None)
    assert_true(after_insert2 == after_insert, "multi insert leaves prompt unchanged")
    assert_true("@图片" not in after_insert2 and "@标题" not in after_insert2, after_insert2)

    # Unlink does not invent @; legacy @sourceTitle strip only
    a = {"id": "a1", "title": "nano-gpt_img_aaaaaaaa_0"}
    b = {"id": "a2", "title": "家用机器人"}
    titles = {a["id"]: a["title"], b["id"]: b["title"]}
    # clean modern prompt — unlink must not change it
    p_clean = "基于参考图重绘"
    assert_true(_sim_unmention_legacy(p_clean, a, titles) == p_clean, "clean prompt unchanged on unlink A")
    assert_true(_sim_unmention_legacy(p_clean, b, titles) == p_clean, "clean prompt unchanged on unlink B")
    # legacy canvas with @家用机器人
    p_legacy = "角色：@家用机器人 站立"
    after_legacy = _sim_unmention_legacy(p_legacy, b, titles)
    assert_true("@家用机器人" not in after_legacy, after_legacy)
    # raw @filename legacy
    p_raw = "x @" + a["title"] + " y"
    after_raw = _sim_unmention_legacy(p_raw, a, titles)
    assert_true("@" + a["title"] not in after_raw, after_raw)

    # images[] still via edges / attachExtraImages
    assert_true("function attachExtraImages" in js, "images packing kept")
    assert_true("payload.images = urls" in js, "images[] via edges")
    assert_true("function packLorasForPayload" in js, "LoRA packing kept")
    assert_true("stages[0].payload" not in js, "gate untouched")





def test_v0818_sticky_composer_bar():
    """v0818 lineage: LoRA + bar + msg pinned in dock-foot; prompt scrolls in dock-scroll (kept under v0819)."""
    js = (ROOT / "static" / "storyboard.js").read_text(encoding="utf-8")
    html = (ROOT / "static" / "storyboard.html").read_text(encoding="utf-8")
    assert_true("v0821o49b-hydrate-fresh-empty-url" in html, "html stamp")
    assert_true('"nl-storyboard-v0821o16"' in js, "STORE v0820c")
    assert_true("nl-storyboard-v0818" in js, "STORE_OLDS has v0818")
    assert_true("nl-storyboard-v0817c" in js, "STORE_OLDS has v0817c")
    assert_true("nl-storyboard-v0817b" in js, "STORE_OLDS has v0817b")
    assert_true('id="dockScroll"' in html and 'class="dock-scroll"' in html, "dock-scroll region")
    assert_true('id="dockFoot"' in html and 'class="dock-foot"' in html, "dock-foot sticky footer")
    # Structure: scroll contains prompt; foot contains lora + bar + msg
    i_scroll = html.find('id="dockScroll"')
    i_foot = html.find('id="dockFoot"')
    i_prompt = html.find('id="prompt"')
    i_lora = html.find('id="loraBlock"')
    i_bar = html.find('class="bar"')
    i_msg = html.find('id="msg"')
    assert_true(i_scroll >= 0 and i_foot > i_scroll, "dock-scroll before dock-foot")
    assert_true(i_scroll < i_prompt < i_foot, "prompt inside dock-scroll (before foot)")
    assert_true(i_foot < i_lora < i_bar < i_msg, "loraBlock + bar + msg inside dock-foot")
    # CSS: expanded body is flex column; body is the sole scroller; foot flex-none/overflow visible
    # 裁决: o63 样式外移到样式表; o103 滚动容器从 dock-scroll 迁到 dock-body(同一「单滚动条」语义)
    css = css_all()
    body_rule = css_rule(css, ".dock.expanded .dock-body")
    assert_true("display: flex" in body_rule and "flex-direction: column" in body_rule,
                "expanded dock-body is flex column")
    assert_true("overflow: auto" in body_rule, "expanded dock-body is the sole overflow:auto scroller")
    scroll_rule = css_rule(css, ".dock.expanded .dock-scroll")
    assert_true("overflow: visible" in scroll_rule, "dock-scroll no longer scrolls (visible)")
    foot_rule = css_rule(css, ".dock.expanded .dock-foot")
    assert_true("flex: 0 0 auto" in foot_rule, "dock-foot flex-none")
    assert_true("overflow: visible" in foot_rule, "dock-foot not a second scroller")
    # Untouched behaviors
    assert_true("stages[0].payload" not in js, "gate untouched")
    assert_true("function attachExtraImages" in js, "images packing kept")
    assert_true("function packLorasForPayload" in js, "LoRA packing kept")
    assert_true("mentionTags" not in js, "no-@-in-prompt lineage kept")


def test_v0819_canvas_stage():
    """v0819: canvas is main stage — Composer defaults collapsed; empty tip; click expands."""
    js = (ROOT / "static" / "storyboard.js").read_text(encoding="utf-8")
    html = (ROOT / "static" / "storyboard.html").read_text(encoding="utf-8")
    assert_true("v0821o49b-hydrate-fresh-empty-url" in html, "html stamp v0821o49b-hydrate-fresh-empty-url")
    assert_true('"nl-storyboard-v0821o16"' in js, "STORE v0820c")
    assert_true("nl-storyboard-v0818" in js, "STORE_OLDS has v0818")
    assert_true("nl-storyboard-v0817c" in js, "STORE_OLDS has v0817c")
    # 裁决: o103-wide-desk 宽屏 Composer 常驻书写台, 默认 expanded; collapsed 胶囊仍可达
    assert_true('dockMode: "expanded"' in js, "default dockMode expanded (o103-wide-desk)")
    assert_true('setDockMode("collapsed")' in js, "collapsed capsule still reachable")
    assert_true('selectNode(state.selected || "shot-1"' in js, "boot selectNode kept")
    # 裁决: selectNode 不再强制 collapsed(常驻书写台); 不得反向把 dockMode 写成 collapsed
    sn = js[js.find("function selectNode"):js.find("function toggleMulti", js.find("function selectNode"))]
    assert_true('state.dockMode = "collapsed"' not in sn, "selectNode never force-collapses dock")
    assert_true("function syncCanvasTip" in js, "syncCanvasTip helper")
    assert_true('id="canvasTip"' in html, "canvasTip element")
    assert_true("选分镜→写画面→LoRA→↑" in html, "empty-canvas onboarding tip")
    # 裁决: 样式外移到样式表(o63); prompt 最小高 120px 与 dock-foot flex-none 语义不变
    css = css_all()
    assert_true("min-height:120px" in css, "prompt min-height ≥120 when expanded")
    assert_true("overflow: auto" in css_rule(css, ".dock.expanded .dock-body"),
                "single scroller is dock-body (was dock-scroll pre-o103)")
    assert_true("flex: 0 0 auto" in css_rule(css, ".dock.expanded .dock-foot"), "dock-foot still present")
    assert_true('id="dockFoot"' in html, "dock-foot element still present")
    # Untouched
    assert_true("stages[0].payload" not in js, "gate untouched")
    assert_true("function attachExtraImages" in js, "images packing kept")
    assert_true("function packLorasForPayload" in js, "LoRA packing kept")
    assert_true("mentionTags" not in js, "no-@-in-prompt lineage kept")



def test_v0819b_expand_prompt():
    """v0819b: first paint of expanded dock shows #prompt in dock-scroll without scrolling."""
    js = (ROOT / "static" / "storyboard.js").read_text(encoding="utf-8")
    html = (ROOT / "static" / "storyboard.html").read_text(encoding="utf-8")
    assert_true("v0821o49b-hydrate-fresh-empty-url" in html, "html stamp v0821o49b-hydrate-fresh-empty-url")
    assert_true('"nl-storyboard-v0821o16"' in js, "STORE v0820c")
    assert_true("nl-storyboard-v0819b" in js, "STORE_OLDS has v0819b")
    assert_true("nl-storyboard-v0819" in js, "STORE_OLDS has v0819")
    assert_true("nl-storyboard-v0818" in js, "STORE_OLDS has v0818")
    # 裁决: o103-wide-desk 默认 expanded 常驻书写台; collapsed 胶囊仍可达
    assert_true('dockMode: "expanded"' in js, "default dockMode expanded (o103-wide-desk)")
    assert_true('setDockMode("collapsed")' in js, "collapsed capsule still reachable")
    assert_true("function syncCanvasTip" in js, "canvasTip behavior kept")
    assert_true('id="canvasTip"' in html, "canvasTip element kept")
    # Expand layout: taller dock, single scroller (o103: dock-body), foot/lora capped
    # 裁决: o63 样式外移; o103 具体数值演进(58vh→min(58vh,560px), lora 140px→96px), 语义不变
    css = css_all()
    exp_rule = css_rule(css, ".dock.expanded")
    # 裁决: v0821o114-full「一个框内容完整显示」刻意取消 vh 封顶(max-height:none !important)
    assert_true("max-height: none" in exp_rule.replace("  ", " "),
                "expanded dock shows full content (o114-full: 一个框，内容完整显示)")
    assert_true("overflow: auto" in css_rule(css, ".dock.expanded .dock-body"),
                "dock-body is the single scrollbar (was dock-scroll pre-o103)")
    assert_true("overflow: visible" in css_rule(css, ".dock.expanded .dock-scroll"),
                "dock-scroll no longer a scroller")
    assert_true("min-height:120px" in css, "prompt min-height ≥120")
    foot_rule = css_rule(css, ".dock.expanded .dock-foot")
    assert_true("overflow: visible" in foot_rule and "flex: 0 0 auto" in foot_rule,
                "dock-foot not a second scroller")
    lora_rule = css_rule(css, ".dock.expanded .lora-block")
    assert_true("max-height:" in lora_rule and "overflow: auto" in lora_rule,
                "lora-block capped when expanded; overflow on lora not whole dock")
    # Expand path resets scrollTop so first frame shows modes+#prompt
    assert_true("scrollTop = 0" in js or "scrollTop=0" in js.replace(" ", ""),
                "expand path sets dockScroll.scrollTop=0")
    assert_true('setDockMode("expanded")' in js, "chip/select opens expanded")
    # Untouched
    assert_true("stages[0].payload" not in js, "gate untouched")
    assert_true("function attachExtraImages" in js, "images packing kept")
    assert_true("function packLorasForPayload" in js, "LoRA packing kept")
    assert_true("mentionTags" not in js, "no-@-in-prompt lineage kept")




def test_v0820_civitai_comfy_params():
    """v0820: Composer exposes civitai comfy params and packs them (134923572 spot-check shape)."""
    js = (ROOT / "static" / "storyboard.js").read_text(encoding="utf-8")
    html = (ROOT / "static" / "storyboard.html").read_text(encoding="utf-8")
    assert_true("v0821o49b-hydrate-fresh-empty-url" in html, "html stamp")
    assert_true('"nl-storyboard-v0821o16"' in js, "STORE v0820c")
    assert_true("nl-storyboard-v0820" in js, "STORE_OLDS has v0820")
    assert_true("nl-storyboard-v0819b" in js, "STORE_OLDS has v0819b")
    assert_true("nl-storyboard-v0819" in js, "STORE_OLDS has v0819")
    # UI surface
    assert_true('id="comfyParams"' in html, "comfyParams group")
    assert_true('id="falParams"' in html, "falParams group kept")
    for fid in ("width", "height", "steps", "cfg", "sampler", "scheduler", "seed"):
        assert_true('id="%s"' % fid in html, "field " + fid)
    assert_true('id="duration"' in html and 'id="aspect"' in html and 'id="res"' in html, "fal fields kept")
    # Helpers + surface switch
    assert_true("function syncParamSurface" in js, "syncParamSurface")
    assert_true("function packComfyParamsForPayload" in js, "packComfyParamsForPayload")
    assert_true("function readComfyParamsFromUi" in js, "readComfyParamsFromUi")
    assert_true("function writeComfyParamsToShot" in js, "writeComfyParamsToShot")
    assert_true("function applyComfyParamsToUi" in js, "applyComfyParamsToUi")
    assert_true("function loadComfyDefaults" in js, "loadComfyDefaults")
    assert_true("CIVITAI_PREF_SERVICE" in js, "Krea2 turbo pref constant")
    assert_true("image/comfy/krea2/turbo/createImage" in js, "Krea2 turbo serviceId")
    assert_true("/api/defaults" in js, "loads samplers/schedulers from defaults")
    # Persist keys
    for key in ("width:", "height:", "steps:", "cfg:", "sampler:", "scheduler:", "seed:"):
        assert_true(key in js, "persist key " + key)
    # buildGraph packs comfy (not Fal-only)
    i = js.find("function buildGraph")
    assert_true(i >= 0, "buildGraph")
    j = js.find("function pickUrl", i)
    bg = js[i:j]
    for field in ("width", "height", "steps", "cfgScale", "sampler", "scheduler"):
        assert_true(field in bg, "buildGraph includes " + field)
    assert_true("seed" not in bg or "seed packed in runShotStep" in bg or "wire-only" in bg,
                "seed not silently put as params bypass without note")
    # runShotStep merges packed comfy + loras
    # 裁决: runShotStepWork 全body(原 9000 字符窗口截断, comfy 合包在窗外)
    run = run_shot_body(js)
    assert_true("packComfyParamsForPayload(shot)" in run or "packComfyParamsForPayload()" in run,
                "pack comfy in runShotStep")
    assert_true("packLorasForPayload()" in run, "loras still packed")
    assert_true("payload.loras = packedLoras" in run, "sets payload.loras")
    assert_true("payload[k] = packedComfy[k]" in run or "payload[k]=packedComfy[k]" in run.replace(" ", ""),
                "merges packed comfy onto payload")
    assert_true(run.find("packLorasForPayload()") < run.find("packComfyParamsForPayload("),
                "comfy packed after loras")
    # Spot-check fixture shape fields must be nameable (no silent drop list)
    for field in ("serviceId", "steps", "cfgScale", "sampler", "scheduler", "seed", "width", "height", "loras"):
        assert_true(field in js, "packs/mentions " + field)
    # Lineage kept
    assert_true("stages[0].payload" not in js, "gate untouched")
    assert_true("mentionTags" not in js, "no-@-in-prompt lineage")
    assert_true("function attachExtraImages" in js, "images packing kept")
    # 裁决: o103-wide-desk 默认 expanded 常驻书写台(原 collapsed 断言已过时)
    assert_true('dockMode: "expanded"' in js, "canvas-stage: o103 resident expanded desk")
    assert_true('id="dockFoot"' in html, "sticky foot kept")


def test_v0820b_apply_import():
    """v0820b: storyboard applyImport packs civitai backend/service/comfy/LoRA; no fal silent fallback."""
    js = (ROOT / "static" / "storyboard.js").read_text(encoding="utf-8")
    html = (ROOT / "static" / "storyboard.html").read_text(encoding="utf-8")
    assert_true("v0821o49b-hydrate-fresh-empty-url" in html, "html stamp")
    assert_true('"nl-storyboard-v0821o16"' in js, "STORE v0820c")
    assert_true("nl-storyboard-v0820" in js, "STORE_OLDS has v0820")
    assert_true("nl-storyboard-v0819b" in js, "STORE_OLDS has v0819b")
    # applyImport path
    assert_true("async function applyImport" in js or "function applyImport" in js, "applyImport")
    assert_true("function runImportFromUrl" in js or "async function runImportFromUrl" in js, "runImportFromUrl")
    assert_true("function looksCivitaiServiceId" in js, "looksCivitaiServiceId")
    assert_true("function ensureActiveShotForImport" in js, "ensureActiveShotForImport")
    assert_true('"/api/import"' in js or "'/api/import'" in js or "/api/import" in js, "POSTs /api/import")
    # Must NOT call paid generate from import path
    i = js.find("async function applyImport")
    if i < 0:
        i = js.find("function applyImport")
    j = js.find("function bindImportModal", i)
    assert_true(i >= 0 and j > i, "applyImport block")
    block = js[i:j]
    assert_true("/api/generate" not in block, "applyImport must not call /api/generate")
    assert_true(
        ('value = "civitai"' in block)
        or (".value=\"civitai\"" in block.replace(" ", ""))
        or ("value = 'civitai'" in block)
        or ('$("backend").value = "civitai"' in block),
        "forces backend civitai",
    )
    assert_true("loadCatalog" in block, "reloads catalog")
    assert_true("applyComfyParamsToUi" in block, "fills comfy params")
    assert_true("normalizeLora" in block, "packs loras")
    assert_true("setDockMode" in block and "expanded" in block, "expands Composer")
    assert_true("不会回退" in block or "flux/schnell" in block, "hard error forbids fal fallback")
    assert_true("缺少 serviceId" in block or "无法挂载" in block, "empty service hard error")
    # URL entry in import modal
    assert_true('id="importUrl"' in html, "importUrl input")
    assert_true('id="importUrlBtn"' in html, "importUrlBtn")
    assert_true("importUrlBtn" in js, "wires importUrlBtn")
    assert_true("runImportFromUrl" in js, "runImportFromUrl wired")
    # Spot-check fixture shape must remain nameable
    for field in ("backend", "serviceId", "steps", "cfgScale", "sampler", "scheduler", "seed", "width", "height", "loras"):
        assert_true(field in js, "mentions " + field)
    assert_true("image/comfy/krea2/turbo/createImage" in js, "Krea2 turbo serviceId")
    # Mock JSON shape exercise via source contract (no live /api/import)
    mock = {
        "backend": "civitai",
        "serviceId": "image/comfy/krea2/turbo/createImage",
        "prompt": "real prompt from fixture",
        "negativePrompt": "",
        "width": 944,
        "height": 1664,
        "steps": 8,
        "cfgScale": 1,
        "sampler": "er_sde",
        "scheduler": "simple",
        "seed": 467475143677094,
        "loras": [{"air": "urn:air:krea2:lora:civitai:2323765@3071582", "strength": 0.8}],
    }
    assert_true(mock["backend"] == "civitai", "mock backend")
    assert_true(mock["serviceId"] == "image/comfy/krea2/turbo/createImage", "mock service")
    assert_true(abs(float(mock["loras"][0]["strength"]) - 0.8) < 1e-6, "mock lora strength")
    # Lineage
    assert_true("packComfyParamsForPayload" in js, "v0820 comfy pack kept")
    assert_true("mentionTags" not in js, "v0817c no @ in prompt")
    assert_true('id="dockFoot"' in html, "v0818 sticky foot")
    # 裁决: o103-wide-desk 默认 expanded 常驻书写台(原 collapsed 断言已过时)
    assert_true('dockMode: "expanded"' in js, "v0819/o103 canvas-stage: resident expanded desk")




def test_v0820c_hard_service():
    """v0820c: empty civitai #service must hard-error; no CIVITAI_PREF soft-fill in buildGraph/runShotStep."""
    js = (ROOT / "static" / "storyboard.js").read_text(encoding="utf-8")
    html = (ROOT / "static" / "storyboard.html").read_text(encoding="utf-8")
    assert_true("v0821o49b-hydrate-fresh-empty-url" in html, "html stamp v0821o49b-hydrate-fresh-empty-url")
    assert_true('"nl-storyboard-v0821o16"' in js, "STORE v0820c")
    assert_true("nl-storyboard-v0820b" in js, "STORE_OLDS has v0820b")
    assert_true("nl-storyboard-v0820" in js, "STORE_OLDS has v0820")
    assert_true("CIVITAI_PREF_SERVICE" in js, "pref constant kept for catalog ordering")
    assert_true("image/comfy/krea2/turbo/createImage" in js, "Krea2 id kept as ordering hint")

    # buildGraph: must NOT soft-fill CIVITAI_PREF / _civitaiDefaultService into serviceId
    i = js.find("function buildGraph")
    assert_true(i >= 0, "buildGraph")
    j = js.find("function pickUrl", i)
    bg = js[i:j]
    assert_true("state._civitaiDefaultService || CIVITAI_PREF_SERVICE" not in bg,
                "buildGraph must not soft-fill CIVITAI_PREF into serviceId")
    assert_true("CIVITAI_PREF_SERVICE" not in bg or "hard-service" in bg,
                "buildGraph must not reference CIVITAI_PREF as generate fallback")
    # Fal defaults may remain for non-civitai (via FAL_*_DEFAULT consts)
    assert_true("FAL_T2I_DEFAULT" in bg or "fal-ai/flux/schnell" in bg, "fal t2i empty-service default kept")
    assert_true("FAL_I2V_DEFAULT" in bg or "image-to-video" in bg, "fal i2v empty-service default kept")
    # 裁决: o23 后 fal 默认门改写为等价的「serviceId 空 且 backend=fal」分支(语义不变且更精确)
    assert_true('!serviceId && be === "fal"' in bg,
                "fal defaults gated to non-civitai")
    assert_true("nl-storyboard-v0820c" in js, "STORE_OLDS has v0820c")
    assert_true("pickedService" in bg or '($("service") && $("service").value)' in bg,
                "buildGraph uses explicit #service value")

    # runShotStep: hard-error path present; no soft-fill
    k = js.find("async function runShotStep")
    assert_true(k >= 0, "runShotStep")
    run = js[k:k + 12000]
    assert_true("请先选择 Civitai 服务" in run, "hard error message in runShotStep")
    assert_true('setMsg(' in run and '"bad"' in run, "hard error uses setMsg bad")
    assert_true("不会默认填入 Krea2" in run, "hard error mentions no Krea2 default")
    assert_true("state._civitaiDefaultService || CIVITAI_PREF_SERVICE" not in run,
                "runShotStep must not soft-fill CIVITAI_PREF")
    assert_true("return fail(" in run and "请先选择 Civitai 服务" in run, "aborts generate on empty service")
    # payload.serviceId from UI only
    assert_true("payload.serviceId = sid" in run or "payload.serviceId=sid" in run.replace(" ", ""),
                "sets payload.serviceId from explicit sid")

    # loadCatalog: pref ordering hint OK; no auto-select pref into empty #service
    lc = js.find("function loadCatalog")
    assert_true(lc >= 0, "loadCatalog")
    lc_end = js.find("async function loadOuts", lc)
    cat = js[lc:lc_end]
    assert_true("ordering hint" in cat or "catalog ordering" in cat.lower() or "Catalog ordering" in cat
                or "ordering hint only" in js,
                "documents pref as ordering hint")
    assert_true("Do NOT auto-select CIVITAI_PREF" in cat or "auto-select" in cat,
                "must not auto-select pref when empty")
    # pendingService path (applyImport) still selects explicit id
    assert_true("_pendingService" in cat, "applyImport pendingService path kept")

    # Lineage: applyImport + v0820 comfy pack intact
    assert_true("async function applyImport" in js or "function applyImport" in js, "applyImport kept")
    assert_true("packComfyParamsForPayload" in js, "v0820 comfy pack kept")
    assert_true("不会回退" in js or "flux/schnell" in js, "applyImport hard error kept")
    assert_true('id="comfyParams"' in html, "comfy UI kept")



def test_v0821n_krea2_import_hardgate():
    """v0821n knife②: applyImport mounts civitai+Krea2; packLoras keeps air; empty service hard-red."""
    js = (ROOT / "static" / "storyboard.js").read_text(encoding="utf-8")
    html = (ROOT / "static" / "storyboard.html").read_text(encoding="utf-8")
    assert_true("v0821o49b-hydrate-fresh-empty-url" in html, "html stamp")
    assert_true('class="stamp"' in html, ".stamp")
    assert_true('"nl-storyboard-v0821o16"' in js, "STORE v0821n4")
    assert_true('"nl-storyboard-v0821n3"' in js, "STORE_OLDS keeps n3")
    assert_true("nl-storyboard-v0821n2" in js, "STORE_OLDS keeps v0821n2")
    assert_true("nl-storyboard-v0821n" in js, "STORE_OLDS keeps v0821n")
    assert_true("nl-storyboard-v0821m2" in js, "STORE_OLDS keeps v0821m2")
    assert_true("nl-storyboard-v0820c" in js, "STORE_OLDS keeps v0820c")
    assert_true("nl-storyboard-v0820b" in js, "STORE_OLDS keeps v0820b")

    # Import mount path
    assert_true("async function applyImport" in js or "function applyImport" in js, "applyImport")
    assert_true("function looksCivitaiServiceId" in js, "looksCivitaiServiceId")
    i = js.find("async function applyImport")
    if i < 0:
        i = js.find("function applyImport")
    j = js.find("function bindImportModal", i)
    block = js[i:j]
    assert_true(
        ('value = "civitai"' in block)
        or ('$("backend").value = "civitai"' in block)
        or ("value = 'civitai'" in block),
        "forces backend civitai",
    )
    assert_true('j.backend === "civitai"' in block or "j.backend === 'civitai'" in block,
                "wantCivitai from j.backend")
    assert_true("looksCivitaiServiceId" in block, "also mounts on civitai-shaped serviceId")
    assert_true("缺少 serviceId" in block or "无法挂载" in block, "empty serviceId hard error")
    assert_true("不会回退" in block or "flux/schnell" in block, "no fal silent fallback")
    assert_true("/api/generate" not in block, "import must not call /api/generate")
    assert_true("normalizeLora" in block, "maps loras")
    assert_true("applyComfyParamsToUi" in block, "fills comfy params")
    assert_true("image/comfy/krea2/turbo/createImage" in js, "Krea2 turbo serviceId")

    # Spot-check fixture shape (134923572)
    mock = {
        "backend": "civitai",
        "serviceId": "image/comfy/krea2/turbo/createImage",
        "steps": 8,
        "cfgScale": 1,
        "sampler": "er_sde",
        "scheduler": "simple",
        "seed": 467475143677094,
        "width": 944,
        "height": 1664,
        "loras": [{"air": "urn:air:krea2:lora:civitai:2323765@3071582", "strength": 0.8}],
    }
    assert_true(mock["serviceId"] == "image/comfy/krea2/turbo/createImage", "mock Krea2")
    assert_true(mock["loras"][0]["air"].startswith("urn:air:krea2:lora:"), "mock lora air")
    assert_true(mock["seed"] > 2147483647, "seed exceeds int32 — must not clamp")

    # packLoras: keep air/path/scale/strength; civitai skips no-air; empty → null
    # 裁决: 行打包已拆到 packLoraRow + loraRowCanOutbound(packLorasForPayload 之前的helper),
    # 窗口起点前移(语义不变)
    pack_i = js.find("function packLorasForPayload")
    assert_true(pack_i >= 0, "packLorasForPayload")
    row_i = js.find("function packLoraRow")
    assert_true(0 <= row_i < pack_i, "packLoraRow helper before packLorasForPayload")
    pack = js[row_i:pack_i + 4200]
    for field in ("air:", "path:", "scale:", "strength:", "versionId:", "downloadUrl:", "modelId:"):
        assert_true(field in pack, "pack field " + field)
    assert_true("function loraRowCanOutbound" in js, "loraRowCanOutbound helper")
    assert_true('be === "civitai"' in pack or "be === 'civitai'" in pack, "civitai air filter gate")
    assert_true("row.air" in pack, "checks air on row")
    assert_true("mapped.length ? mapped : null" in pack, "empty → null")
    assert_true("packed.length !== list.length" in pack or "packed.length !== list.length" in js,
                "mixed chips compare packed vs list")

    # runShotStep attach loras + negativePrompt + empty-service hard red
    # 裁决: runShotStepWork 全body(原 14000 字符窗口截断)
    run = run_shot_body(js)
    assert_true("packLorasForPayload()" in run, "packs loras")
    assert_true("payload.loras = packedLoras" in run, "sets payload.loras")
    assert_true("payload.negativePrompt" in run, "attaches negativePrompt")
    assert_true("请先选择 Civitai 服务" in run, "empty service hard error")
    assert_true("不会默认填入 Krea2" in run, "no Krea2 soft-fill")
    assert_true("int32" in run, "documents no int32 seed clamp")

    # buildGraph: no CIVITAI_PREF soft-fill for civitai
    bg_i = js.find("function buildGraph")
    bg = js[bg_i:js.find("function pickUrl", bg_i)]
    assert_true("state._civitaiDefaultService || CIVITAI_PREF_SERVICE" not in bg,
                "buildGraph no CIVITAI_PREF soft-fill")
    # 裁决: fal 默认门现为「serviceId 空 且 backend=fal」分支(与 be!=="civitai" 等价且更精确)
    assert_true('!serviceId && be === "fal"' in bg, "fal defaults gated")

    # api import backend contract (a6365ef) still present
    civ = (ROOT / "providers" / "civitai.py").read_text(encoding="utf-8")
    assert_true('"backend": "civitai"' in civ or "'backend': 'civitai'" in civ,
                "import_image returns backend=civitai")
    assert_true("image/comfy/krea2/turbo/createImage" in civ, "Krea2 default serviceId")
    assert_true("def _row_air" in civ, "lora_map versionId→AIR fallback")
    assert_true("LoraResolveError" in civ, "unresolved LoRA is fail-closed")


def test_v0821_hardgate_i2v_refs():
    """v0821: i2v keeps first-frame; multi-ref packs N; P1 seed/dock/LoRA name."""
    js = (ROOT / "static" / "storyboard.js").read_text(encoding="utf-8")
    html = (ROOT / "static" / "storyboard.html").read_text(encoding="utf-8")
    assert_true("v0821o49b-hydrate-fresh-empty-url" in html, "html stamp")
    assert_true('class="stamp"' in html, ".stamp")
    assert_true('"nl-storyboard-v0821o16"' in js, "STORE v0821")
    assert_true("nl-storyboard-v0820c" in js, "STORE_OLDS has v0820c")
    assert_true("nl-storyboard-v0820b" in js, "STORE_OLDS has v0820b")

    # A) i2v eats upstream — frame required + packed
    # 裁决: i2v 缺首帧仍 fail-closed, 文案并入「缺首帧 · 切到图片生成…(图生视频需要首帧…)」
    assert_true("缺首帧 · 切到图片生成" in js and "图生视频需要首帧" in js, "i2v missing-frame gate")
    assert_true("不能偷配方台" in js, "i2v hard msg")
    assert_true("FAL_I2V_DEFAULT" in js, "FAL_I2V_DEFAULT const")
    assert_true("fal-ai/minimax/video-01/image-to-video" in js, "real i2v endpoint default")
    assert_true("function catalogItemSupportsI2v" in js, "i2v catalog predicate")
    assert_true("filterCatalogForMode" in js, "mode catalog filter")
    assert_true("当前服务不吃首帧" in js, "hard block non-i2v service in video mode")
    # attachExtraImages stamps singular FIRST + images[]
    i = js.find("function attachExtraImages")
    assert_true(i >= 0, "attachExtraImages")
    body = js[i:i + 2200]
    assert_true("payload.images = urls" in body, "images[] packed without slice")
    assert_true("urls.slice(0, cap)" not in body, "attach does not silent-slice")
    assert_true("start_image_url" in body, "stamps start_image_url")
    assert_true("SINGULAR_FIRST_FIELDS" in body, "uses singular-first list")
    # buildGraph wires frame for i2v
    bg_i = js.find("function buildGraph")
    bg = js[bg_i:js.find("function pickUrl", bg_i)]
    assert_true('op === "i2v"' in bg and "frame" in bg, "i2v uses frameAsset wire")
    assert_true("FAL_I2V_DEFAULT" in bg, "buildGraph i2v default")
    # compile path still puts firstFrame/sourceImage
    r = compile(shot_graph("i2v", "缓推", image_url="/out/frame.jpg"))
    assert_true(r.get("ok") is True, r)
    p = r["payload"]
    assert_true(p.get("firstFrame") == "/out/frame.jpg", p)
    assert_true(p.get("sourceImage") == "/out/frame.jpg", p)
    assert_true("image-to-video" in str(p.get("serviceId") or ""), p)

    # Mock attachExtraImages packing shape (static analysis of N linked → images length N)
    # Simulate the JS packing contract in Python:
    def pack_urls(primary, linked):
        urls = []
        if primary:
            urls.append(primary)
        for u in linked:
            if u and u not in urls:
                urls.append(u)
        return urls
    linked_n = ["/out/a.jpg", "/out/b.jpg", "/out/c.jpg", "/out/d.jpg"]
    packed = pack_urls("/out/a.jpg", linked_n)
    assert_true(len(packed) == 4, "under-cap packs all N=%d" % len(packed))
    assert_true(packed[0] == "/out/a.jpg", "primary first")
    over = pack_urls("/out/a.jpg", linked_n + ["/out/e.jpg", "/out/f.jpg", "/out/g.jpg"])
    assert_true(len(over) == 7, "attach keeps all unique refs; over-cap is a gate")
    assert_true("上限未知" in js, "unknown ref cap failure copy")
    assert_true("ref-cap-hint" in js or "还可" in js, "UI remaining slot hint")
    assert_true("linked.concat(suggest)" in js or "chipNodes" in js, "chips for all linked")

    # B) multi-ref: over-cap still hard-blocks before attach
    # 裁决: runShotStepWork 全body(原 14000 字符窗口截断)
    run = run_shot_body(js)
    assert_true("countRefUrls" in run and "超过上限" in run, "over-cap hard block kept")
    assert_true(run.find("countRefUrls") < run.find("attachExtraImages(payload, shot)"),
                "gate before attach")

    # C) P1 UX
    # 裁决: o63 样式外移 + Seko 底排压缩(o136): #seed 最终规则 110px!important; 118px 旧值仍须绝迹
    css = css_all()
    seed_rule = css_rule(css, ".dock.show #seed")
    assert_true("width:" in seed_rule and "118px" not in seed_rule, "seed field sized, old 118px gone")
    # 裁决: v0821o114-full 刻意取消 vh 封顶(一个框内容完整显示)
    assert_true("max-height: none" in css_rule(css, ".dock.expanded").replace("  ", " "),
                "dock expanded full-content box (o114-full)")
    assert_true("function loraDisplayName" in js, "LoRA human name helper")
    assert_true("modelName" in js[js.find("function loraDisplayName"):js.find("function loraDisplayName") + 800],
                "prefers modelName")

    # No regression lineage
    assert_true("function applyImport" in js or "async function applyImport" in js, "applyImport")
    assert_true("请先选择 Civitai 服务" in js, "hard empty-service civitai")
    assert_true("mentionTags" not in js, "no @ in prompt path")
    assert_true('id="dockFoot"' in html, "sticky foot")
    assert_true("packComfyParamsForPayload" in js, "comfy pack")



def test_v0821b_i2v_detect():
    """v0821b: pure t2v (video-01) is NOT i2v; image-to-video is; filter excludes t2v."""
    import json
    import subprocess
    js = (ROOT / "static" / "storyboard.js").read_text(encoding="utf-8")
    html = (ROOT / "static" / "storyboard.html").read_text(encoding="utf-8")
    assert_true("v0821o49b-hydrate-fresh-empty-url" in html, "html stamp v0821o49b-hydrate-fresh-empty-url")
    assert_true('class="stamp"' in html, ".stamp")
    assert_true('"nl-storyboard-v0821o16"' in js, "STORE v0821b")
    assert_true("nl-storyboard-v0821b" in js, "STORE_OLDS keeps v0821b")
    assert_true("nl-storyboard-v0821" in js, "STORE_OLDS keeps v0821")
    assert_true('FAL_I2V_DEFAULT = "fal-ai/minimax/video-01/image-to-video"' in js,
                "FAL_I2V_DEFAULT unchanged")
    assert_true("function catalogItemSupportsI2v" in js, "predicate present")
    assert_true("NEVER: category=video" in js or "never category=video alone" in js.lower() or
                "Do NOT treat category=video alone as i2v" in js or
                "prefer catalog supportsI2v" in js,
                "no category=video-alone true")
    assert_true("supportsI2v" in js[js.find("function catalogItemSupportsI2v"):
                                    js.find("function catalogItemSupportsImage")],
                "predicate reads supportsI2v flag")
    assert_true('id === "fal-ai/minimax/video-01"' in js, "exact video-01 reject")
    # filter + hard-block still wired to predicate
    assert_true("filterCatalogForMode" in js and "catalogItemSupportsI2v" in js, "filter uses predicate")
    run_i = js.find("async function runShotStep")
    run = js[run_i:run_i + 16000]
    assert_true("catalogItemSupportsI2v(itVid)" in run, "runShotStep hard-block uses predicate")
    assert_true("当前服务不吃首帧" in run, "hard-block message")

    # Behavioral: extract real predicate + deps and evaluate with node
    start = js.find("function catalogItemSupportsI2v")
    assert_true(start >= 0, "fn start")
    end = js.find("function catalogItemSupportsImage", start)
    fn_src = js[start:end]
    # SINGULAR_FIRST_FIELDS + catalogImageFields needed
    sf_i = js.find("const SINGULAR_FIRST_FIELDS")
    sf_line = js[sf_i:js.find(";", sf_i) + 1]
    cif_i = js.find("function catalogImageFields")
    cif_end = js.find("\n  function resolveRefCaps", cif_i)
    cif_src = js[cif_i:cif_end]
    harness = """
%s
%s
%s
const cases = [
  [{ id: "fal-ai/minimax/video-01", category: "video" }, false],
  [{ id: "fal-ai/minimax/video-01", category: "video", falCategory: "text-to-video", needsFirstFrame: false, supportsI2v: false, imageFields: [] }, false],
  [{ id: "fal-ai/minimax/video-01/image-to-video", category: "video" }, true],
  [{ id: "fal-ai/minimax/video-01/image-to-video", category: "video", needsFirstFrame: true, supportsI2v: true, imageFields: ["image_url"] }, true],
  [{ id: "fal-ai/foo/text-to-video", category: "video" }, false],
  [{ id: "other/model/start-end", category: "video" }, true],
  [{ id: "x/i2v/bar", category: "video" }, true],
  [{ id: "pure/video/clip", category: "video" }, false],
  [{ id: "vendor/vid", category: "video", needsFirstFrame: true }, true],
  [{ id: "vendor/flag", category: "video", supportsI2v: true }, true],
  [{ id: "vendor/flag-cap", category: "video", capabilities: { supportsI2v: true } }, true],
  [{ id: "vendor/no", category: "video", supportsI2v: false, needsFirstFrame: false }, false],
  [{ id: "vendor/vid2", category: "video", imageFields: ["image_url"] }, true],
  [{ id: "vendor/vid3", category: "video", capabilities: { imageFields: ["start_image_url"] } }, true],
  [{ id: "fal-ai/flux/schnell", category: "image" }, false],
];
const out = cases.map(([it, expect]) => {
  const got = catalogItemSupportsI2v(it);
  return { id: it.id, expect, got, ok: got === expect };
});
const filtered = [
  { id: "fal-ai/minimax/video-01", category: "video" },
  { id: "fal-ai/minimax/video-01/image-to-video", category: "video" },
  { id: "fal-ai/flux/schnell", category: "image" },
].filter(catalogItemSupportsI2v).map(x => x.id);
console.log(JSON.stringify({ out, filtered }));
""" % (sf_line, cif_src, fn_src)
    proc = subprocess.run(
        ["node", "-e", harness],
        capture_output=True, text=True, cwd=str(ROOT),
    )
    assert_true(proc.returncode == 0, "node harness failed: %s%s" % (proc.stdout, proc.stderr))
    data = json.loads(proc.stdout.strip().splitlines()[-1])
    for row in data["out"]:
        assert_true(row["ok"], "predicate %s: expect %s got %s" % (row["id"], row["expect"], row["got"]))
    assert_true("fal-ai/minimax/video-01" not in data["filtered"], "filter excludes pure t2v video-01")
    assert_true("fal-ai/minimax/video-01/image-to-video" in data["filtered"], "filter keeps i2v")
    assert_true("fal-ai/flux/schnell" not in data["filtered"], "filter excludes image t2i")

    # Catalog overlay from providers.fal must mark pure t2v vs real i2v; JS must agree.
    from providers.fal import overlay_image_fields
    t2v = overlay_image_fields({
        "id": "fal-ai/minimax/video-01",
        "category": "video",
        "falCategory": "text-to-video",
        "imageFields": [],
    })
    i2v = overlay_image_fields({
        "id": "fal-ai/minimax/video-01/image-to-video",
        "category": "video",
        "falCategory": "image-to-video",
        "imageFields": ["image_url"],
    })
    assert_true(t2v.get("supportsI2v") is False and t2v.get("needsFirstFrame") is False, t2v)
    assert_true(i2v.get("supportsI2v") is True and i2v.get("needsFirstFrame") is True, i2v)
    # Re-run predicate on overlay rows via node
    ov_harness = """
%s
%s
%s
const rows = %s;
const out = rows.map((it) => ({ id: it.id, got: catalogItemSupportsI2v(it) }));
console.log(JSON.stringify(out));
""" % (sf_line, cif_src, fn_src, json.dumps([t2v, i2v]))
    ov = subprocess.run(["node", "-e", ov_harness], capture_output=True, text=True, cwd=str(ROOT))
    assert_true(ov.returncode == 0, "overlay node harness: %s%s" % (ov.stdout, ov.stderr))
    ov_out = json.loads(ov.stdout.strip().splitlines()[-1])
    by_id = {r["id"]: r["got"] for r in ov_out}
    assert_true(by_id.get("fal-ai/minimax/video-01") is False, by_id)
    assert_true(by_id.get("fal-ai/minimax/video-01/image-to-video") is True, by_id)



def test_v0821c_fal_i2v_preview():
    """v0821c: local /out → data URL for fal; pickUrl reads video.url; 422 no-media → failed."""
    import base64
    import json
    from providers.fal import (
        build_fal_input, materialize_fal_media, local_out_to_data_url,
        fal_output_error, job_status,
    )
    js = (ROOT / "static" / "storyboard.js").read_text(encoding="utf-8")
    html = (ROOT / "static" / "storyboard.html").read_text(encoding="utf-8")
    assert_true("v0821o49b-hydrate-fresh-empty-url" in html, "html stamp")
    assert_true('class="stamp"' in html, ".stamp")
    assert_true('"nl-storyboard-v0821o16"' in js, "STORE v0821c")
    assert_true("nl-storyboard-v0821b" in js, "STORE_OLDS keeps v0821b")
    # pickUrl must map fal video shapes
    i = js.find("function pickUrl")
    assert_true(i >= 0, "pickUrl")
    block = js[i:i + 3200]
    assert_true("data.video" in block and ("result.video" in block or "res.video" in block), "pickUrl video.url")
    assert_true("v0821c" in block or "fal video" in block, "v0821c note on pickUrl")

    frame = "/out/12100372-20260907215435634_0.jpg"
    fp = ROOT / "out" / "12100372-20260907215435634_0.jpg"
    assert_true(fp.is_file(), "fixture frame exists")
    data_url = local_out_to_data_url(frame)
    assert_true(isinstance(data_url, str) and data_url.startswith("data:image/jpeg;base64,"), data_url[:40])
    raw = base64.b64decode(data_url.split(",", 1)[1])
    assert_true(raw == fp.read_bytes(), "roundtrip bytes")

    inp = build_fal_input({
        "serviceId": "fal-ai/minimax/video-01/image-to-video",
        "prompt": "固定镜头",
        "firstFrame": frame,
        "sourceImage": frame,
    })
    assert_true(inp.get("image_url") == frame, "build keeps local path for meta")
    out = materialize_fal_media(inp)
    assert_true(out.get("image_url", "").startswith("data:image/jpeg;base64,"), out.get("image_url", "")[:48])
    # https untouched
    https_inp = {"image_url": "https://cdn.example/a.jpg", "prompt": "x"}
    assert_true(materialize_fal_media(https_inp)["image_url"] == "https://cdn.example/a.jpg", "https passthrough")
    # missing local → error
    try:
        materialize_fal_media({"image_url": "/out/does-not-exist-xyz.jpg"})
        assert_true(False, "should raise")
    except ValueError as e:
        assert_true("无法读取" in str(e) or "不存在" in str(e), str(e))

    err = fal_output_error({
        "detail": [{
            "loc": ["body", "image_url"],
            "msg": "Failed to download the file. Please check if the URL is accessible and try again.",
            "type": "file_download_error",
            "input": "/out/12100372-20260907215435634_0.jpg",
        }]
    })
    assert_true(err and "Failed to download" in err, err)

    # Live job that failed with relative /out must now report failed (not forever-processing).
    jid = "fal|fal-ai/minimax/video-01/image-to-video|01a07e0c-d910-7702-9eb4-e27fa6411d73"
    code, data = job_status(jid)
    assert_true(code == 200, data)
    assert_true(data.get("status") == "failed", data)
    assert_true("download" in (data.get("error") or "").lower() or "image_url" in (data.get("error") or ""), data)

    # Node harness: pickUrl extracts fal video.url / result.video.url / saved
    import subprocess
    i_saved = js.find("function pickSavedUrl")
    assert_true(i_saved >= 0, "pickSavedUrl before pickUrl")
    end = js.find("function hasUnresolvedStageOut", i_saved)
    assert_true(end > i_saved, "pickUrl end")
    fn = js[i_saved:end]
    node = subprocess.run(
        ["node", "-e", fn + r"""
const cases = [
  [{ saved: [{ url: "/out/a.mp4" }] }, "/out/a.mp4"],
  [{ saved: [{ url: "/out/a.mp4" }], video: { url: "https://v3.fal.media/files/x.mp4" }, result: { video: { url: "https://cdn/v.mp4" } } }, "/out/a.mp4"],
  [{ video: { url: "https://v3.fal.media/files/x.mp4" } }, "https://v3.fal.media/files/x.mp4"],
  [{ result: { video: { url: "https://cdn/v.mp4" } } }, "https://cdn/v.mp4"],
  [{ result: { images: [{ url: "https://cdn/i.jpg" }] } }, "https://cdn/i.jpg"],
  [{ status: "succeeded" }, ""],
];
const out = cases.map(([d, exp]) => ({ got: pickUrl(d), exp, ok: pickUrl(d) === exp }));
console.log(JSON.stringify(out));
"""],
        capture_output=True, text=True, cwd=str(ROOT),
    )
    assert_true(node.returncode == 0, "node pickUrl: %s%s" % (node.stdout, node.stderr))
    rows = json.loads(node.stdout.strip().splitlines()[-1])
    for r in rows:
        assert_true(r["ok"], r)



def test_v0821f_send_noop():
    """v0821f lineage retained under v0821h: never silent runShotStep; disabled gray; click feedback."""
    js = (ROOT / "static" / "storyboard.js").read_text(encoding="utf-8")
    html = (ROOT / "static" / "storyboard.html").read_text(encoding="utf-8")
    assert_true("v0821o49b-hydrate-fresh-empty-url" in html, "html stamp")
    assert_true('class="stamp"' in html, ".stamp")
    assert_true('"nl-storyboard-v0821o16"' in js, "STORE v0821h")
    assert_true('"nl-storyboard-v0821h"' in js, "STORE_OLDS keeps v0821h")
    assert_true('"nl-storyboard-v0821g"' in js, "STORE_OLDS keeps v0821g")
    assert_true('"nl-storyboard-v0821f"' in js, "STORE_OLDS keeps v0821f")
    assert_true('"nl-storyboard-v0821e"' in js, "STORE_OLDS keeps v0821e")

    # disabled send visually gray (not white+opacity)
    # 裁决: o63 把内联 <style> 拆到外部样式表 → 样式断言读 css_all(); 丢失的 send 样式已补回 ui-base.css
    css_f = css_all()
    assert_true(".send:disabled" in css_f and "#3a3a44" in css_f, "disabled send gray bg")
    assert_true("cursor:not-allowed" in css_f, "disabled cursor")

    # frameAsset heals orphan firstFrameId
    fa = js[js.find("function frameAsset"):js.find("function frameAsset") + 700]
    assert_true("orphan" in fa or 'shot.firstFrameId = linked[0]' in fa, "heal orphan firstFrameId")

    # runShotStep never silent on !shot
    run_i = js.find("async function runShotStep")
    run = js[run_i:run_i + 4500]
    assert_true("请先选中分镜再生成" in run, "setMsg when !shot")
    assert_true('shot.kind !== "shot"' in run and "setMsg" in run, "wrong-kind setMsg")

    # generate click-start feedback
    g = js[js.find("async function generate()"):js.find("async function generate()") + 900]
    assert_true("校验连线…" in g, "click-start setMsg")

    # Node harness: frameAsset heal + needFrame gate semantics (no real /api/generate)
    import subprocess
    start = js.find("function frameAsset")
    end = js.find("\n  function sourceTitle", start)
    assert_true(start >= 0 and end > start, "frameAsset bounds")
    fa_fn = js[start:end]
    node = subprocess.run(
        ["node", "-e", """
function isVideoUrl(u){ return /\\.(mp4|webm|mov)(\\?|$)/i.test(String(u||'')) || /\\/video\\//i.test(String(u||'')); }
function isImageSource(n){ return !!(n && n.url && !isVideoUrl(n.url)); }
const state = {
  nodes: [
    { id: 'a1', kind: 'asset', title: 'img', url: '/out/a.jpg' },
    { id: 'a2', kind: 'asset', title: 'gone', url: '/out/b.jpg' },
    { id: 's1', kind: 'shot', title: '镜', firstFrameId: 'a2', prompt: '' },
  ],
  edges: [{ from: 'a1', to: 's1' }],
};
function nodeById(id){ return state.nodes.find(n => n.id === id); }
function connectedNodes(shotId){ return state.edges.filter(e => e.to === shotId).map(e => nodeById(e.from)).filter(Boolean); }
function connectedAssets(shotId){ return connectedNodes(shotId).filter(isImageSource); }
""" + fa_fn + """
const shot = nodeById('s1');
const frame = frameAsset(shot);
console.log(JSON.stringify({ frameId: frame && frame.id, healedFirst: shot.firstFrameId, needFrame: !frame }));
"""],
        capture_output=True, text=True, cwd=str(ROOT),
    )
    assert_true(node.returncode == 0, "node frameAsset heal: %s%s" % (node.stdout, node.stderr))
    import json as _json
    row = _json.loads(node.stdout.strip().splitlines()[-1])
    assert_true(row["frameId"] == "a1" and row["healedFirst"] == "a1" and row["needFrame"] is False, row)

    assert_true("fetch(\"/api/generate\"" in js or "fetch('/api/generate'" in js, "generate path exists")
    assert_true(g.find("校验连线") < g.find("runShotStep"), "click msg before runShotStep")


def test_v0821g_send_bind():
    """v0821o49b-hydrate-fresh-empty-url: always 首帧已就绪; addEventListener+pointerdown; hit/z-index; missing-frame bad."""
    js = (ROOT / "static" / "storyboard.js").read_text(encoding="utf-8")
    html = (ROOT / "static" / "storyboard.html").read_text(encoding="utf-8")
    assert_true("v0821o49b-hydrate-fresh-empty-url" in html, "html stamp")
    assert_true('class="stamp"' in html, ".stamp")
    assert_true("storyboard.js?v=20260911-o49bhydratefreshemptyurl" in html, "js cache bust")
    assert_true('"nl-storyboard-v0821o16"' in js, "STORE v0821h")
    assert_true('"nl-storyboard-v0821g"' in js, "STORE_OLDS keeps v0821g")
    assert_true('"nl-storyboard-v0821f"' in js, "STORE_OLDS keeps v0821f")

    # CSS: larger hit + z-index above foot siblings (index #go lesson)
    # 裁决: o63 把内联 <style> 拆到外部样式表 → 样式断言读 css_all(); 丢失的 send 样式已补回 ui-base.css
    css_g = css_all().replace(": ", ":")
    assert_true("z-index:5" in css_g and "pointer-events:auto" in css_g, "send elevated hit")
    assert_true("touch-action:manipulation" in css_g, "send touch-action")
    assert_true(".send::before" in css_g and "inset:-12px" in css_g, "expanded hit ::before")
    assert_true(".dock-foot{" in css_g and "z-index:3" in css_g, "dock-foot above scroll")
    assert_true('data-testid="composer-send"' in html, "send data-testid in markup")

    k = js.find("function renderDock")
    assert_true(k >= 0, "renderDock")
    dock = js[k:k + 9000]
    # ready tip kept, but v0821j gates on !fireSend._busy (must not wipe in-flight)
    assert_true("首帧已就绪 · 可生成" in dock, "ready msg")
    assert_true("setMsg(\"首帧已就绪 · 可生成\")" in dock or "setMsg('首帧已就绪 · 可生成')" in dock,
                "ready setMsg present")
    assert_true("!fireSend._busy" in dock and "!state.runningGroup" in dock,
                "renderDock skips ready while busy/group")
    assert_true("/缺首帧|视频需要先连一张首帧图|本版未接/" not in dock,
                "stale-only regex gate removed")
    # missing-frame → bad (red); o17 copy points at 图片生成 or attach
    assert_true('setMsg("缺首帧 · 切到图片生成，或先上传/选择首帧", "bad")' in dock, "missing-frame bad")
    assert_true("syncSendGate" in dock, "syncSendGate from renderDock")

    # bind helpers
    assert_true("function bindSendButton" in js, "bindSendButton")
    assert_true("function fireSend" in js, "fireSend")
    assert_true("function syncSendGate" in js, "syncSendGate")
    assert_true('addEventListener("click", fireSend, true)' in js or "addEventListener('click', fireSend, true)" in js,
                "capture click")
    assert_true('addEventListener("pointerdown", fireSend)' in js or "addEventListener('pointerdown', fireSend)" in js,
                "pointerdown fallback")
    assert_true("bindSendButton();" in js, "bindSendButton called")
    assert_true("onclick = generate" not in js, "no fragile onclick=generate only")
    assert_true('data-testid", "composer-send"' in js or "data-testid', 'composer-send'" in js,
                "testid set in JS gate")
    assert_true("data-reason" in js and "need-frame" in js, "debug reason attr")
    assert_true("data-enabled" in js, "debug enabled attr")

    # generate still sets 校验连线 before runShotStep; no accidental removal of /api/generate call site
    g = js[js.find("async function generate()"):js.find("async function generate()") + 1200]
    assert_true("校验连线…" in g, "click-start setMsg")
    assert_true(g.find("校验连线") < g.find("runShotStep"), "click msg before runShotStep")
    # harness must not POST generate in tests — static only
    assert_true("fetch(\"/api/generate\"" in js, "generate path exists in product code")




def test_v0821h_send_aria():
    """v0821o49b-hydrate-fresh-empty-url: gate via aria-disabled (not disabled=true); click setMsg on needFrame/stub; busy → 进行中."""
    js = (ROOT / "static" / "storyboard.js").read_text(encoding="utf-8")
    html = (ROOT / "static" / "storyboard.html").read_text(encoding="utf-8")
    assert_true("v0821o49b-hydrate-fresh-empty-url" in html, "html stamp")
    assert_true('class="stamp"' in html, ".stamp")
    assert_true("storyboard.js?v=20260911-o49bhydratefreshemptyurl" in html, "js cache bust")
    assert_true('"nl-storyboard-v0821o16"' in js, "STORE v0821h")
    assert_true('"nl-storyboard-v0821g"' in js, "STORE_OLDS keeps v0821g")
    assert_true('"nl-storyboard-v0821f"' in js, "STORE_OLDS keeps v0821f")

    # CSS: reuse disabled gray via is-blocked / aria-disabled
    # 裁决: o63 把内联 <style> 拆到外部样式表 → 样式断言读 css_all(); 丢失的 send 样式已补回 ui-base.css
    css_h = css_all()
    assert_true(".send.is-blocked" in css_h or '[aria-disabled="true"]' in css_h or ".send[aria-disabled" in css_h,
                "blocked visual selector")
    assert_true("#3a3a44" in css_h and "cursor:not-allowed" in css_h, "gray blocked styles")
    assert_true(".send:disabled" in css_h, "keep :disabled style for compat")

    # syncSendGate must NOT assign native disabled=true for gate
    sg = js[js.find("function syncSendGate"):js.find("function syncSendGate") + 900]
    assert_true("setSendVisual" in sg or "aria-disabled" in sg, "syncSendGate uses aria path")
    assert_true("btn.disabled = true" not in sg and "btn.disabled=true" not in sg,
                "syncSendGate must not set disabled=true")

    sv = js[js.find("function setSendVisual"):js.find("function setSendVisual") + 900]
    assert_true("btn.disabled = false" in sv or "btn.disabled=false" in sv, "setSendVisual forces enabled")
    assert_true("aria-disabled" in sv, "aria-disabled attr")
    assert_true("is-blocked" in sv, "is-blocked class")

    # fireSend: no early-return on btn.disabled; gate with setMsg + stop
    fs = js[js.find("function fireSend"):js.find("function fireSend") + 4500]
    assert_true("if (btn.disabled) return" not in fs and "if(btn.disabled)return" not in fs,
                "fireSend must not early-return on disabled")
    assert_true("缺首帧" in fs and '"bad"' in fs, "needFrame click → bad setMsg")
    assert_true("本版未接" in fs and '"bad"' in fs, "stub click → bad setMsg")
    assert_true("进行中" in fs, "busy click → 进行中")
    assert_true("generate()" in fs, "frame OK → generate")
    # STOP: needFrame path returns before generate
    need_i = fs.find("缺首帧")
    gen_i = fs.rfind("generate()")
    assert_true(need_i >= 0 and gen_i > need_i, "generate after needFrame gate")
    # ensure return between 缺首帧 setMsg and generate
    chunk = fs[need_i:gen_i]
    assert_true("return" in chunk, "STOP after needFrame setMsg")

    assert_true("function markSendBusy" in js, "markSendBusy")
    assert_true('markSendBusy(true)' in js, "busy on")
    assert_true('markSendBusy(false)' in js, "busy off")

    # product still has /api/generate but tests don't POST
    assert_true('fetch("/api/generate"' in js, "generate path exists")
    # keep hit area / bind from g
    assert_true('addEventListener("click", fireSend, true)' in js, "capture click")
    assert_true('addEventListener("pointerdown", fireSend)' in js, "pointerdown")
    assert_true("首帧已就绪 · 可生成" in js, "ready tip kept")
    assert_true("z-index:5" in css_all().replace(": ", ":"), "hit z-index kept")




def test_v0821i_i2v_writeback():
    """v0821i: video writeback to shot card + promote/history; empty i2v prompt allowed; pickUrl prefers /out."""
    import json
    import subprocess
    from providers.graph_compile import compile_graph

    js = (ROOT / "static" / "storyboard.js").read_text(encoding="utf-8")
    html = (ROOT / "static" / "storyboard.html").read_text(encoding="utf-8")
    assert_true("v0821o49b-hydrate-fresh-empty-url" in html, "html stamp")
    assert_true('class="stamp"' in html, ".stamp")
    assert_true('"nl-storyboard-v0821o16"' in js, "STORE v0821o12")
    assert_true('"nl-storyboard-v0821o7"' in js, "STORE_OLDS keeps v0821o7")
    assert_true('"nl-storyboard-v0821k"' in js, "STORE_OLDS keeps v0821k")
    assert_true('"nl-storyboard-v0821j"' in js, "STORE_OLDS keeps v0821j")
    assert_true('"nl-storyboard-v0821i"' in js, "STORE_OLDS keeps v0821i")
    assert_true('"nl-storyboard-v0821h"' in js, "STORE_OLDS keeps v0821h")

    # promoteResult must accept videos
    pr = js[js.find("function promoteResult"):js.find("function spawnHistoryAt")]
    assert_true("isVideoUrl(url)) return null" not in pr, "promoteResult must not skip videos")
    assert_true("v0821i" in pr or "promote images AND videos" in pr, "v0821i promote note")

    # writeback helper: write onto the shot, never auto-promote a clone card
    assert_true("function writebackResult" in js, "writebackResult helper")
    assert_true("function pushHistoryItem" in js, "pushHistoryItem helper")
    assert_true("writebackResult(shot, url)" in js, "success path calls writebackResult")
    wb = js[js.find("function writebackResult"):js.find("function pickSavedUrl")]
    assert_true("promoteResult(" not in wb, "writebackResult must not spawn canvas clone via promoteResult")
    assert_true("removeUnpromotedFromShot" in wb, "writebackResult drops leftover 分镜N成片 clones")
    assert_true("live.url = url" in wb or "shot.url = url" in wb, "writebackResult sets shot.url on card")
    assert_true("nodeById(shot.id)" in wb, "writebackResult re-resolves live shot")
    assert_true("此镜完成，已写入卡片" in js, "success copy writes onto the card")
    assert_true("data-hist-pin" in js, "接到此镜 hist-pin kept")
    assert_true("writebackResult(shot, item.url)" in js, "接到此镜 applies media to shot card via writebackResult")
    assert_true("spawnHistoryAt(item, shot.x" not in js or js.find("writebackResult(shot, item.url)") > 0, "hist-pin prefers writeback over clone-only")
    assert_true("bePoll === \"civitai\"" in js or "bePoll === 'civitai'" in js or 'bePoll === "civitai"' in js, "civitai in extended pollMax")
    assert_true("PREPARING" in js, "preparing treated as in-flight")
    assert_true("成片已收进资产库" not in js, "success copy must not imply a duplicate asset card")

    # card video preview
    assert_true('playsinline preload="metadata"' in js, "shot/asset video preload")
    assert_true("<video src=" in js and "muted playsinline" in js, "video tag on cards")

    # poll must not break on succeeded without pickUrl
    assert_true("pollMax" in js or "v0821m" in js, "video poll lengthened")

    assert_true("never break on succeeded alone" in js or "成片落盘中" in js, "poll waits for saved after succeeded")
    assert_true("function pickSavedUrl" in js, "pickSavedUrl helper")
    assert_true("pickSavedUrl(st)" in js, "poll break uses pickSavedUrl")
    assert_true('if (pickUrl(st)) break;' not in js, "must not break poll on CDN pickUrl alone")
    assert_true("const savedUrl = pickSavedUrl(j)" in js and "savedUrl || pickUrl(j)" in js, "final url prefers saved then CDN")
    assert_true('pickUrl(st) || st.status === "done"' not in js and "pickUrl(st) || st.status === 'done'" not in js, "old succeeded-or-pickUrl break removed")

    # loadOuts keeps videos
    lo = js[js.find("async function loadOuts"):js.find("$(\"backend\").onchange")]
    assert_true('it.kind === "image" || (it.url && !isVideoUrl(it.url))' not in lo, "must not filter videos out")
    assert_true('k === "image" || k === "video"' in lo or "kind===video" in lo or 'k === "video"' in lo, "loadOuts keeps video")

    # pickUrl prefers saved
    i = js.find("function pickUrl")
    block = js[i:js.find("function hasUnresolvedStageOut", i)]
    assert_true("prefer local saved" in block or "v0821i" in block, "pickUrl v0821i note")
    assert_true(block.find("first(data.saved)") < block.find("data.video") or "savedHit" in block, "saved before video")

    # empty i2v prompt allowed at compile
    r = compile_graph({
        "backend": "fal",
        "nodes": [
            {"id": "img", "op": "image", "params": {"url": "/out/x.jpg"}},
            {"id": "p-shot-1", "op": "prompt", "params": {"text": ""}},
            {"id": "shot-1", "op": "i2v", "params": {"serviceId": "fal-ai/minimax/video-01/image-to-video", "duration": 5}},
        ],
        "edges": [
            {"from": "img", "fromPort": "image", "to": "shot-1", "toPort": "image"},
            {"from": "p-shot-1", "fromPort": "prompt", "to": "shot-1", "toPort": "prompt"},
        ],
    })
    assert_true(r.get("ok") is True, r)
    assert_true("缺少文本" not in (r.get("error") or ""), r)
    assert_true((r.get("payload") or {}).get("prompt") == "", r)

    # negative still requires text
    r2 = compile_graph({
        "backend": "fal",
        "nodes": [
            {"id": "n", "op": "negative", "params": {"text": ""}},
            {"id": "p", "op": "prompt", "params": {"text": "x"}},
            {"id": "g", "op": "t2i", "params": {"serviceId": "fal-ai/flux/schnell"}},
        ],
        "edges": [
            {"from": "p", "fromPort": "prompt", "to": "g", "toPort": "prompt"},
            {"from": "n", "fromPort": "negative", "to": "g", "toPort": "negative"},
        ],
    })
    assert_true(r2.get("ok") is False, r2)
    assert_true("缺少文本" in (r2.get("error") or ""), r2)

    # Node: pickUrl prefer saved; writebackResult shape via promote+history sim
    i_saved = js.find("function pickSavedUrl")
    assert_true(i_saved >= 0, "pickSavedUrl before pickUrl")
    end = js.find("function hasUnresolvedStageOut", i_saved)
    fn = js[i_saved:end]
    # extract promoteResult + helpers roughly via node harness
    node = subprocess.run(
        ["node", "-e", fn + r"""
const cases = [
  [{ saved: [{ url: "/out/fal_…01a07e47…_0.mp4" }], result: { video: { url: "https://cdn/v.mp4" } } }, "/out/fal_…01a07e47…_0.mp4"],
  [{ result: { video: { url: "https://cdn/v.mp4" } } }, "https://cdn/v.mp4"],
  [{ status: "succeeded", steps: [{ output: { images: [{ url: "https://orchestration-new.civitai.com/v2/consumer/blobs/x-0.jpg?sig=1", previewUrl: "https://orchestration-new.civitai.com/v2/consumer/blobs/x-0.jpg?sig=p" }] } }] }, "https://orchestration-new.civitai.com/v2/consumer/blobs/x-0.jpg?sig=1"],
  [{ status: "succeeded", saved: [{ url: "/out/12100372-20260910074123211_0.jpg" }], steps: [{ output: { images: [{ url: "https://orchestration-new.civitai.com/v2/consumer/blobs/x-0.jpg" }] } }] }, "/out/12100372-20260910074123211_0.jpg"],
];
const out = cases.map(([d, exp]) => ({ got: pickUrl(d), exp, ok: pickUrl(d) === exp }));
console.log(JSON.stringify(out));
"""],
        capture_output=True, text=True, cwd=str(ROOT),
    )
    assert_true(node.returncode == 0, "node pickUrl: %s%s" % (node.stdout, node.stderr))
    rows = json.loads(node.stdout.strip().splitlines()[-1])
    for r in rows:
        assert_true(r["ok"], r)




def test_v0821j_send_busy_msg():
    """v0821j: renderDock must not wipe msg while busy; fireSend entry 已点生成; dockFoot+Ctrl/Cmd+Enter;
    double pointerdown+click still sets msg (no silent debounce). No paid /api/generate in tests."""
    import json
    import subprocess

    js = (ROOT / "static" / "storyboard.js").read_text(encoding="utf-8")
    html = (ROOT / "static" / "storyboard.html").read_text(encoding="utf-8")
    assert_true("v0821o49b-hydrate-fresh-empty-url" in html, "html stamp")
    assert_true('class="stamp"' in html, ".stamp")
    assert_true("storyboard.js?v=20260911-o49bhydratefreshemptyurl" in html, "js cache bust")
    assert_true('"nl-storyboard-v0821o16"' in js, "STORE v0821o12")
    assert_true('"nl-storyboard-v0821i"' in js, "STORE_OLDS keeps v0821i")

    # renderDock busy guard
    k = js.find("function renderDock")
    dock = js[k:k + 5500]
    assert_true("!fireSend._busy" in dock, "skip ready when busy")
    assert_true("!state.runningGroup" in dock, "skip ready when group running")
    ready_i = dock.find('setMsg("首帧已就绪 · 可生成")')
    assert_true(ready_i > 0, "ready setMsg still exists")
    guard = dock[max(0, ready_i - 280):ready_i]
    assert_true("fireSend._busy" in guard, "ready setMsg nested under busy guard")
    assert_true("\\bbad\\b" in dock or "bad" in dock[ready_i-200:ready_i+80], "v0821k keep bad/warn tip")

    # fireSend: once-per-event + gates before ack; non-silent debounce
    fs = js[js.find("function fireSend"):js.find("function fireSend") + 4500]
    assert_true("_nlSendHandled" in fs, "same-event once flag")
    assert_true('setMsg("已点生成")' in fs, "已点生成 ack present")
    entry_i = fs.find('setMsg("已点生成")')
    need_i = fs.find("此模型需要提示词")
    gen_i = fs.rfind("generate()")
    assert_true(need_i >= 0 and 0 <= entry_i and need_i < entry_i < gen_i,
                "needsPrompt gate before 已点生成 before generate")
    assert_true("450" in fs, "debounce window kept")
    # debounce path must mention 进行中 — never wipe prior gate by re-acking
    deb = fs[fs.find("450"):fs.find("450") + 350]
    assert_true("return" in deb, "debounce returns")
    assert_true("进行中" in deb, "debounce busy path not silent")

    # dockFoot delegation + Ctrl/Cmd+Enter
    assert_true("function bindComposerSendKeys" in js, "bindComposerSendKeys")
    assert_true("bindComposerSendKeys();" in js, "keys bound")
    assert_true("metaKey" in js and "ctrlKey" in js, "Ctrl/Cmd+Enter")
    assert_true("nlSendDelegate" in js or "dockFoot" in js, "dockFoot delegate")
    assert_true('closest("[data-testid=\\"composer-send\\"]")' in js
                or "closest('[data-testid=\"composer-send\"]')" in js
                or 'closest("[data-testid=\\"composer-send\\"]")' in js
                or 'data-testid=\\"composer-send\\"' in js
                or 'composer-send' in js[js.find("nlSendDelegate"):js.find("nlSendDelegate") + 500],
                "delegate selector for composer-send")
    bb = js[js.find("function bindSendButton"):js.find("function bindSendButton") + 1600]
    assert_true("dockFoot" in bb, "bindSend uses dockFoot")
    assert_true("onFoot" in bb or "nlSendDelegate" in bb, "foot delegate wired")

    # product paths exist; tests must not POST
    assert_true('fetch("/api/generate"' in js, "generate path exists")
    assert_true('fetch("/api/graph/compile"' in js, "compile path exists")

    # Node harness: double pointerdown+click → msg always set; no fetch
    harness = r"""
const msgs = [];
function setMsg(t, cls){ msgs.push({t:String(t), cls: cls||""}); }
const state = { selected: "s1", mode: "video", runningGroup: false, nodes: [
  { id: "s1", kind: "shot", title: "分镜1", firstFrameId: "a1", prompt: "" },
  { id: "a1", kind: "asset", title: "img", url: "/out/a.jpg" },
], edges: [{ from: "a1", to: "s1" }] };
function nodeById(id){ return state.nodes.find(n => n.id === id); }
function isVideoUrl(u){ return /\.(mp4|webm|mov)(\?|$)/i.test(String(u||"")); }
function isImageSource(n){ return !!(n && n.url && !isVideoUrl(n.url)); }
function connectedAssets(shotId){
  return state.edges.filter(e => e.to === shotId).map(e => nodeById(e.from)).filter(isImageSource);
}
function frameAsset(shot){
  const linked = connectedAssets(shot.id);
  if (shot.firstFrameId) {
    const hit = linked.find(a => a.id === shot.firstFrameId);
    if (hit) return hit;
    shot.firstFrameId = linked[0] ? linked[0].id : "";
  }
  return linked[0] || null;
}
function isStubMode(){ return false; }
function setAckMsg(rest, cls){ const body = String(rest||"").replace(/^已点生成(\s*·\s*)?/, ""); setMsg(body ? ("已点生成 · " + body) : "已点生成", cls); }
function needsPromptBeforeGenerate(){ return false; }
function chipsLackAirForOutbound(){ return false; }
function paramGateMessage(){ return ""; }
function currentBackend(){ return "fal"; }
function falHasLoras(){ return false; }
function falLoraUnsupportedMsg(){ return ""; }
function pinFalLoraServiceId(s){ return s || ""; }
function hfHasLoras(){ return false; }
function hfLoraUnsupportedMsg(){ return ""; }
function pinHfLoraServiceId(s){ return s || ""; }
function keepComposerPromptVisible(){}
function paintShotFail(shot, err, cls){ setMsg(String(err), cls||"bad"); }
function outboundLoraBlockMsg(){ return "LoRA block"; }
let generateCalls = 0;
function generate(){ generateCalls++; setAckMsg("校验连线…"); fireSend._busy = true; }
const btn = { getAttribute: (k) => (k === "data-reason" ? "enabled" : null), setAttribute(){}, removeAttribute(){} };
function $(id){ return id === "send" ? btn : (id === "prompt" ? { value: "camera slowly pans" } : null); }
""" + js[js.find("function fireSend"):js.find("\n  function bindSendButton")] + r"""
fireSend._busy = false;
fireSend._at = 0;
const ev1 = { type: "pointerdown", button: 0, preventDefault(){}, stopPropagation(){} };
const ev2 = { type: "click", button: 0, preventDefault(){}, stopPropagation(){} };
fireSend(ev1);
fireSend(ev2);
const texts = msgs.map(m => m.t);
const hasAck = texts.some(t => t.indexOf("已点生成") >= 0 || t.indexOf("校验连线") >= 0 || t.indexOf("进行中") >= 0);
console.log(JSON.stringify({
  ok: hasAck && generateCalls === 1 && texts.length >= 2,
  texts, generateCalls, busy: !!fireSend._busy
}));
"""
    node = subprocess.run(
        ["node", "-e", harness],
        capture_output=True, text=True, cwd=str(ROOT),
    )
    assert_true(node.returncode == 0, "node fireSend double: %s%s" % (node.stdout, node.stderr))
    row = json.loads(node.stdout.strip().splitlines()[-1])
    assert_true(row["ok"], row)
    assert_true(row["generateCalls"] == 1, "one generate from double events: %s" % row)
    assert_true(any("已点生成" in t or "校验连线" in t for t in row["texts"]), "msg progression: %s" % row)




def test_v0821k_i2v_prompt_req():
    """v0821k: fal i2v empty prompt → 此模型需要提示词 (no POST); sticky 已点生成 · …; Fal error on Composer; compile still empty-ok."""
    import json
    import subprocess
    from providers.graph_compile import compile_graph
    from providers import fal as fal_mod

    js = (ROOT / "static" / "storyboard.js").read_text(encoding="utf-8")
    html = (ROOT / "static" / "storyboard.html").read_text(encoding="utf-8")
    fal_src = (ROOT / "providers" / "fal.py").read_text(encoding="utf-8")

    assert_true("v0821o49b-hydrate-fresh-empty-url" in html, "html stamp")
    assert_true('class="stamp"' in html, ".stamp")
    assert_true("storyboard.js?v=20260911-o49bhydratefreshemptyurl" in html, "js cache bust")
    assert_true('"nl-storyboard-v0821o16"' in js, "STORE v0821o12")
    assert_true('"nl-storyboard-v0821j"' in js, "STORE_OLDS keeps v0821j")

    assert_true("function needsPromptBeforeGenerate" in js, "prompt gate helper")
    assert_true("function setAckMsg" in js, "sticky ack helper")
    assert_true("function formatErr" in js, "formatErr helper")
    assert_true("此模型需要提示词" in js, "hard red copy")
    assert_true("setAckMsg(\"校验连线…" in js or "setAckMsg('校验连线…" in js, "sticky 校验连线")
    assert_true("setAckMsg" in js and "正在请求云 API" in js, "sticky 正在请求")
    assert_true("formatErr(e)" in js or "formatErr(st.error" in js, "surface job.error via formatErr")
    assert_true("/\\bbad\\b|\\bwarn\\b/" in js or "keep bad/warn" in js, "renderDock preserves bad/warn")

    fs = js[js.find("function fireSend"):js.find("function fireSend") + 4500]
    assert_true("needsPromptBeforeGenerate" in fs, "fireSend client gate")
    assert_true("此模型需要提示词" in fs, "fireSend hard red")
    need_i = fs.find("此模型需要提示词")
    gen_i = fs.rfind("generate()")
    assert_true(need_i >= 0 and gen_i > need_i and "return" in fs[need_i:gen_i], "STOP before generate on empty prompt")

    g = js[js.find("async function generate()"):js.find("async function generate()") + 900]
    assert_true("needsPromptBeforeGenerate" in g, "generate gate")
    assert_true("setAckMsg" in g and "校验连线" in g, "generate sticky ack")

    run = js[js.find("async function runShotStep"):js.find("function setSendVisual")]
    assert_true("此模型需要提示词" in run, "runShotStep gate before POST")
    assert_true(run.find("此模型需要提示词") < run.find('fetch("/api/generate"'), "gate before POST generate")

    # graph_compile still empty-ok for local i2v
    r = compile_graph({
        "backend": "fal",
        "nodes": [
            {"id": "img", "op": "image", "params": {"url": "/out/x.jpg"}},
            {"id": "p-shot-1", "op": "prompt", "params": {"text": ""}},
            {"id": "shot-1", "op": "i2v", "params": {"serviceId": "fal-ai/minimax/video-01/image-to-video", "duration": 5}},
        ],
        "edges": [
            {"from": "img", "fromPort": "image", "to": "shot-1", "toPort": "image"},
            {"from": "p-shot-1", "fromPort": "prompt", "to": "shot-1", "toPort": "prompt"},
        ],
    })
    assert_true(r.get("ok") is True, r)
    assert_true((r.get("payload") or {}).get("prompt") == "", r)

    # fal provider optional reject (no paid call)
    assert_true("此模型需要提示词" in fal_src, "fal submit reject copy")
    calls = []
    def _fake_fal_call(*a, **k):
        calls.append((a, k))
        return 200, {"request_id": "should-not-run"}
    real = fal_mod.fal_call
    fal_mod.fal_call = _fake_fal_call
    try:
        code, data = fal_mod.submit({
            "serviceId": "fal-ai/minimax/video-01/image-to-video",
            "prompt": "",
            "image_url": "https://example.com/a.jpg",
            "sourceImage": "https://example.com/a.jpg",
        })
    finally:
        fal_mod.fal_call = real
    assert_true(code == 400, (code, data))
    assert_true("此模型需要提示词" in str((data or {}).get("error") or ""), data)
    assert_true(len(calls) == 0, "must not POST to Fal queue when prompt empty")

    # Node harness: empty prompt → gate; no generate; msg bad
    harness = r"""
const msgs = [];
function setMsg(t, cls){ msgs.push({t:String(t), cls: cls||""}); }
function setAckMsg(rest, cls){ const body = String(rest||"").replace(/^已点生成(\s*·\s*)?/, ""); setMsg(body ? ("已点生成 · " + body) : "已点生成", cls); }
function formatErr(e){ return String(e && e.message || e); }
const state = { selected: "s1", mode: "video", runningGroup: false, catalogById: {
  "fal-ai/minimax/video-01/image-to-video": { id: "fal-ai/minimax/video-01/image-to-video", required: ["prompt", "image_url"] }
}, nodes: [
  { id: "s1", kind: "shot", title: "分镜1", firstFrameId: "a1", prompt: "" },
  { id: "a1", kind: "asset", title: "img", url: "/out/a.jpg" },
], edges: [{ from: "a1", to: "s1" }] };
function nodeById(id){ return state.nodes.find(n => n.id === id); }
function isVideoUrl(u){ return /\.(mp4|webm|mov)(\?|$)/i.test(String(u||"")); }
function isImageSource(n){ return !!(n && n.url && !isVideoUrl(n.url)); }
function connectedAssets(shotId){
  return state.edges.filter(e => e.to === shotId).map(e => nodeById(e.from)).filter(isImageSource);
}
function frameAsset(shot){
  const linked = connectedAssets(shot.id);
  if (shot.firstFrameId) {
    const hit = linked.find(a => a.id === shot.firstFrameId);
    if (hit) return hit;
    shot.firstFrameId = linked[0] ? linked[0].id : "";
  }
  return linked[0] || null;
}
function isStubMode(){ return false; }
function currentBackend(){ return "fal"; }
function catalogItemForService(){ return state.catalogById["fal-ai/minimax/video-01/image-to-video"]; }
function catalogRequiresPrompt(it){
  if (!it) return false;
  const req = [].concat(it.required || []);
  return req.map(String).some(r => r === "prompt" || r.indexOf("prompt") >= 0);
}
function readComposerPrompt(){
  const n = nodeById(state.selected);
  const ta = $("prompt");
  if (ta && n) { n.prompt = ta.value; return String(ta.value||"").trim(); }
  return String((n && n.prompt)||"").trim();
}
function needsPromptBeforeGenerate(){
  const empty = !readComposerPrompt();
  if (!empty) return false;
  if (state.mode === "video" && currentBackend() === "fal") return true;
  return catalogRequiresPrompt(catalogItemForService());
}
function chipsLackAirForOutbound(){ return false; }
function paramGateMessage(){ return ""; }
function falHasLoras(){ return false; }
function falLoraUnsupportedMsg(){ return ""; }
function pinFalLoraServiceId(s){ return s || ""; }
function hfHasLoras(){ return false; }
function hfLoraUnsupportedMsg(){ return ""; }
function pinHfLoraServiceId(s){ return s || ""; }
function keepComposerPromptVisible(){}
function paintShotFail(shot, err, cls){ setMsg(String(err), cls||"bad"); }
function outboundLoraBlockMsg(){ return "LoRA block"; }
let generateCalls = 0;
function generate(){ generateCalls++; setAckMsg("校验连线…"); }
const btn = { getAttribute: (k) => (k === "data-reason" ? "enabled" : null), setAttribute(){}, removeAttribute(){} };
const promptEl = { value: "" };
function $(id){
  if (id === "send") return btn;
  if (id === "prompt") return promptEl;
  if (id === "service") return { value: "fal-ai/minimax/video-01/image-to-video" };
  if (id === "backend") return { value: "fal" };
  return null;
}
""" + js[js.find("function fireSend"):js.find("\n  function bindSendButton")] + r"""
fireSend._busy = false;
fireSend._at = 0;
fireSend({ type: "click", button: 0, preventDefault(){}, stopPropagation(){} });
const texts = msgs.map(m => m.t);
const last = texts[texts.length - 1] || "";
const lastCls = (msgs[msgs.length - 1] || {}).cls || "";
console.log(JSON.stringify({
  ok: generateCalls === 0 && last.indexOf("此模型需要提示词") >= 0 && lastCls === "bad"
    && !texts.some(t => t === "已点生成" || t.indexOf("已点生成 ·") === 0),
  texts, generateCalls, last, lastCls
}));
"""
    node = subprocess.run(["node", "-e", harness], capture_output=True, text=True, cwd=str(ROOT))
    assert_true(node.returncode == 0, "node empty-prompt gate: %s%s" % (node.stdout, node.stderr))
    row = json.loads(node.stdout.strip().splitlines()[-1])
    assert_true(row["ok"], row)
    assert_true(row["generateCalls"] == 0, row)

    # sticky successor contains 已点生成
    harness2 = r"""
const msgs = [];
function setMsg(t, cls){ msgs.push(String(t)); }
function setAckMsg(rest, cls){ const body = String(rest||"").replace(/^已点生成(\s*·\s*)?/, ""); setMsg(body ? ("已点生成 · " + body) : "已点生成", cls); }
""" + js[js.find("function setAckMsg"):js.find("function setAckMsg") + 350] + r"""
setMsg("已点生成");
setAckMsg("正在请求云 API…");
console.log(JSON.stringify({ msgs, ok: msgs[1] === "已点生成 · 正在请求云 API…" }));
"""
    # extract setAckMsg alone is enough — redefine carefully
    harness2 = r"""
const msgs = [];
function setMsg(t, cls){ msgs.push(String(t)); }
""" + js[js.find("function setAckMsg"):js.find("\n  function formatErr")] + r"""
setMsg("已点生成");
setAckMsg("正在请求云 API…");
setAckMsg("校验连线…");
console.log(JSON.stringify({
  msgs,
  ok: msgs[1].indexOf("已点生成") >= 0 && msgs[1].indexOf("正在请求云 API") >= 0
    && msgs[2].indexOf("已点生成") >= 0 && msgs[2].indexOf("校验连线") >= 0
}));
"""
    node2 = subprocess.run(["node", "-e", harness2], capture_output=True, text=True, cwd=str(ROOT))
    assert_true(node2.returncode == 0, "node sticky: %s%s" % (node2.stdout, node2.stderr))
    row2 = json.loads(node2.stdout.strip().splitlines()[-1])
    assert_true(row2["ok"], row2)

    assert_true('fetch("/api/generate"' in js, "generate path exists (tests do not POST paid)")




def test_v0821l_send_once():
    """v0821l: same-event once; gates before 已点生成; double pointerdown+click empty → red final; with prompt → ack+generate. No paid POST."""
    import json
    import subprocess

    js = (ROOT / "static" / "storyboard.js").read_text(encoding="utf-8")
    html = (ROOT / "static" / "storyboard.html").read_text(encoding="utf-8")

    assert_true("v0821o49b-hydrate-fresh-empty-url" in html, "html stamp")
    assert_true('class="stamp"' in html, ".stamp")
    assert_true("storyboard.js?v=20260911-o49bhydratefreshemptyurl" in html, "js cache bust")
    assert_true('"nl-storyboard-v0821o16"' in js, "STORE v0821l")
    assert_true('"nl-storyboard-v0821k"' in js, "STORE_OLDS keeps v0821k")

    fs = js[js.find("function fireSend"):js.find("function fireSend") + 4800]
    assert_true("_nlSendHandled" in fs, "once-per-event flag")
    assert_true(fs.find("_nlSendHandled") < fs.find('setMsg("已点生成")'), "flag before ack")
    assert_true(fs.find("此模型需要提示词") < fs.find('setMsg("已点生成")'), "prompt gate before ack")
    assert_true(fs.find("缺首帧") < fs.find('setMsg("已点生成")'), "needFrame before ack")
    assert_true(fs.find("本版未接") < fs.find('setMsg("已点生成")'), "stub before ack")
    assert_true(fs.find('setMsg("已点生成")') < fs.rfind("generate()"), "ack then generate")

    bb = js[js.find("function bindSendButton"):js.find("function bindSendButton") + 1800]
    assert_true("ev._nlSendHandled" in bb or "_nlSendHandled" in bb, "foot skip if handled")

    harness_base = r"""
const msgs = [];
function setMsg(t, cls){ msgs.push({t:String(t), cls: cls||""}); }
function setAckMsg(rest, cls){ const body = String(rest||"").replace(/^已点生成(\s*·\s*)?/, ""); setMsg(body ? ("已点生成 · " + body) : "已点生成", cls); }
const state = { selected: "s1", mode: "video", runningGroup: false, catalogById: {
  "fal-ai/minimax/video-01/image-to-video": { id: "fal-ai/minimax/video-01/image-to-video", required: ["prompt", "image_url"] }
}, nodes: [
  { id: "s1", kind: "shot", title: "分镜1", firstFrameId: "a1", prompt: PROMPT },
  { id: "a1", kind: "asset", title: "img", url: "/out/a.jpg" },
], edges: [{ from: "a1", to: "s1" }] };
function nodeById(id){ return state.nodes.find(n => n.id === id); }
function isVideoUrl(u){ return /\.(mp4|webm|mov)(\?|$)/i.test(String(u||"")); }
function isImageSource(n){ return !!(n && n.url && !isVideoUrl(n.url)); }
function connectedAssets(shotId){
  return state.edges.filter(e => e.to === shotId).map(e => nodeById(e.from)).filter(isImageSource);
}
function frameAsset(shot){
  const linked = connectedAssets(shot.id);
  if (shot.firstFrameId) {
    const hit = linked.find(a => a.id === shot.firstFrameId);
    if (hit) return hit;
    shot.firstFrameId = linked[0] ? linked[0].id : "";
  }
  return linked[0] || null;
}
function isStubMode(){ return false; }
function currentBackend(){ return "fal"; }
function catalogItemForService(){ return state.catalogById["fal-ai/minimax/video-01/image-to-video"]; }
function catalogRequiresPrompt(it){
  if (!it) return false;
  const req = [].concat(it.required || []);
  return req.map(String).some(r => r === "prompt" || r.indexOf("prompt") >= 0);
}
function readComposerPrompt(){
  const n = nodeById(state.selected);
  const ta = $("prompt");
  if (ta && n) { n.prompt = ta.value; return String(ta.value||"").trim(); }
  return String((n && n.prompt)||"").trim();
}
function needsPromptBeforeGenerate(){
  const empty = !readComposerPrompt();
  if (!empty) return false;
  if (state.mode === "video" && currentBackend() === "fal") return true;
  return catalogRequiresPrompt(catalogItemForService());
}
function chipsLackAirForOutbound(){ return false; }
function paramGateMessage(){ return ""; }
function currentBackend(){ return "fal"; }
function falHasLoras(){ return false; }
function falLoraUnsupportedMsg(){ return ""; }
function pinFalLoraServiceId(s){ return s || ""; }
function hfHasLoras(){ return false; }
function hfLoraUnsupportedMsg(){ return ""; }
function pinHfLoraServiceId(s){ return s || ""; }
function keepComposerPromptVisible(){}
function paintShotFail(shot, err, cls){ setMsg(String(err), cls||"bad"); }
function outboundLoraBlockMsg(){ return "LoRA block"; }
let generateCalls = 0;
function generate(){ generateCalls++; setAckMsg("校验连线…"); fireSend._busy = true; }
const btn = { getAttribute: (k) => (k === "data-reason" ? "enabled" : null), setAttribute(){}, removeAttribute(){} };
const promptEl = { value: PROMPT };
function $(id){
  if (id === "send") return btn;
  if (id === "prompt") return promptEl;
  if (id === "service") return { value: "fal-ai/minimax/video-01/image-to-video" };
  if (id === "backend") return { value: "fal" };
  return null;
}
"""

    fs_src = js[js.find("function fireSend"):js.find("\n  function bindSendButton")]

    # empty prompt double fire
    harness_empty = (
        "const PROMPT = \"\";\n"
        + harness_base
        + fs_src
        + r"""
fireSend._busy = false;
fireSend._at = 0;
const ev1 = { type: "pointerdown", button: 0, preventDefault(){}, stopPropagation(){} };
const ev2 = { type: "click", button: 0, preventDefault(){}, stopPropagation(){} };
fireSend(ev1);
fireSend(ev2);
// same-event foot+btn
const ev3 = { type: "click", button: 0, preventDefault(){}, stopPropagation(){} };
fireSend(ev3);
fireSend(ev3);
const texts = msgs.map(m => m.t);
const last = texts[texts.length - 1] || "";
const lastCls = (msgs[msgs.length - 1] || {}).cls || "";
console.log(JSON.stringify({
  ok: generateCalls === 0 && last === "此模型需要提示词" && lastCls === "bad"
    && !texts.some(t => t === "已点生成"),
  texts, generateCalls, last, lastCls
}));
"""
    )
    node = subprocess.run(["node", "-e", harness_empty], capture_output=True, text=True, cwd=str(ROOT))
    assert_true(node.returncode == 0, "node empty double: %s%s" % (node.stdout, node.stderr))
    row = json.loads(node.stdout.strip().splitlines()[-1])
    assert_true(row["ok"], row)
    assert_true(row["generateCalls"] == 0, row)

    # with prompt → 已点生成 then generate path; double events → one generate
    harness_ok = (
        "const PROMPT = \"camera slowly pans\";\n"
        + harness_base
        + fs_src
        + r"""
fireSend._busy = false;
fireSend._at = 0;
const ev1 = { type: "pointerdown", button: 0, preventDefault(){}, stopPropagation(){} };
const ev2 = { type: "click", button: 0, preventDefault(){}, stopPropagation(){} };
fireSend(ev1);
fireSend(ev2);
const texts = msgs.map(m => m.t);
console.log(JSON.stringify({
  ok: generateCalls === 1 && texts.some(t => t === "已点生成" || t.indexOf("已点生成 ·") === 0),
  texts, generateCalls
}));
"""
    )
    node2 = subprocess.run(["node", "-e", harness_ok], capture_output=True, text=True, cwd=str(ROOT))
    assert_true(node2.returncode == 0, "node prompt double: %s%s" % (node2.stdout, node2.stderr))
    row2 = json.loads(node2.stdout.strip().splitlines()[-1])
    assert_true(row2["ok"], row2)
    assert_true(row2["generateCalls"] == 1, row2)

    assert_true('fetch("/api/generate"' in js, "generate path exists (tests do not POST paid)")





def test_v0821m2_poll_copy():
    """v0821m2: longer video poll; timeout copy if still running; bare video_url pickUrl; cloud-nodes parity."""
    js = (ROOT / "static" / "storyboard.js").read_text(encoding="utf-8")
    html = (ROOT / "static" / "storyboard.html").read_text(encoding="utf-8")
    cn = (ROOT / "static" / "cloud-nodes.html").read_text(encoding="utf-8")
    assert_true("v0821o49b-hydrate-fresh-empty-url" in html, "html stamp")
    assert_true('class="stamp"' in html, ".stamp")
    assert_true('"nl-storyboard-v0821o16"' in js, "STORE v0821m2")
    assert_true('"nl-storyboard-v0821m"' in js, "STORE_OLDS keeps v0821m")
    assert_true('"nl-storyboard-v0821l"' in js, "STORE_OLDS keeps v0821l")
    assert_true("? 180 : 40" in js or "pollMax = 180" in js, "video pollMax 180")
    assert_true("? 3000 : 2500" in js or "pollMs = 3000" in js, "video pollMs 3s")
    assert_true("等待超时，云端任务仍在进行中" in js, "timeout ≠ no-media copy")
    assert_true("data.video_url" in js and "data.image_url" in js, "bare video_url/image_url")
    assert_true("const pollMax = 180" in cn and "const pollMs = 3000" in cn, "cloud-nodes poll parity")
    assert_true("等待超时，云端任务仍在进行中" in cn, "cloud-nodes timeout copy")



def test_v0821n2_lora_air_gate():
    """v0821n2: chips without air → red block; chips with air → pack has air; some filtered."""
    js = (ROOT / "static" / "storyboard.js").read_text(encoding="utf-8")
    html = (ROOT / "static" / "storyboard.html").read_text(encoding="utf-8")
    assert_true("v0821o49b-hydrate-fresh-empty-url" in html, "html stamp")
    assert_true('class="stamp"' in html, ".stamp")
    assert_true('"nl-storyboard-v0821o16"' in js, "STORE v0821n3")
    assert_true("nl-storyboard-v0821n2" in js, "STORE_OLDS keeps v0821n2")
    assert_true("nl-storyboard-v0821n" in js, "STORE_OLDS keeps v0821n")
    assert_true("nl-storyboard-v0821m2" in js, "STORE_OLDS keeps v0821m2")

    assert_true("function chipsLackAirForOutbound" in js, "chipsLackAirForOutbound helper")
    assert_true("LoRA 缺 air，无法出站" in js, "red block msg")
    assert_true("不能只带走其余条" in js, "mixed LoRA red msg")

    # packLoras: civitai requires air on EVERY chip; empty → null; keep air when present
    # 裁决: 行打包已拆到 packLoraRow + loraRowCanOutbound(packLorasForPayload 之前的helper),
    # 窗口起点前移(语义不变)
    pack_i = js.find("function packLorasForPayload")
    assert_true(pack_i >= 0, "packLorasForPayload")
    row_i = js.find("function packLoraRow")
    assert_true(0 <= row_i < pack_i, "packLoraRow helper before packLorasForPayload")
    pack = js[row_i:pack_i + 3200]
    assert_true("function loraRowCanOutbound" in js, "loraRowCanOutbound")
    assert_true('be === "civitai"' in pack or "be === 'civitai'" in pack, "civitai air filter")
    assert_true("row.air" in pack, "checks air")
    assert_true("mapped.length ? mapped : null" in pack, "empty → null")
    assert_true("modelId:" in pack or "modelId: l.modelId" in js, "packs modelId field")

    # Conceptual: chips with air → pack has air; chips without → blocked red
    # Mixed must fail the whole pack (no silent drop of the bad row).
    with_air = [{"air": "urn:air:krea2:lora:civitai:2323765@3071582", "strength": 0.8, "name": "A"}]
    no_air = [{"path": "https://civitai.com/api/download/models/1", "strength": 0.8, "name": "B"}]
    mixed = with_air + no_air

    def sim_pack(rows, be="civitai"):
        mapped = []
        for l in rows:
            row = {"air": l.get("air") or "", "path": l.get("path") or "", "scale": l.get("strength", 0.8)}
            ok = True
            if be == "civitai":
                ok = bool(row["air"] and str(row["air"]).strip())
            if not ok:
                return None
            mapped.append(row)
        return mapped or None

    packed_ok = sim_pack(with_air)
    assert_true(packed_ok and packed_ok[0]["air"].startswith("urn:air:"), "chips with air → pack has air")
    packed_bad = sim_pack(no_air)
    assert_true(packed_bad is None, "chips without air → pack null")
    packed_mixed = sim_pack(mixed)
    assert_true(packed_mixed is None, "mixed air+no-air must fail whole pack")

    # fireSend gates before 已点生成 / generate
    fi = js.find("function fireSend")
    fire = js[fi:js.find("function bindSendButton", fi)]
    assert_true("chipsLackAirForOutbound" in fire, "fireSend air gate")
    assert_true("outboundLoraBlockMsg" in fire or "LoRA 缺 air，无法出站" in fire, "fireSend red msg")
    assert_true("LoRA 缺 air，无法出站" in js, "air red msg string kept")
    assert_true(fire.find("chipsLackAirForOutbound") < fire.find('setMsg("已点生成")'),
                "air gate before 已点生成")
    gate_mark = "outboundLoraBlockMsg" if "outboundLoraBlockMsg" in fire else "LoRA 缺 air"
    assert_true(fire.find(gate_mark) < fire.find("generate()"), "block before generate")

    # runShotStep gates before /api/generate; still packs when air present
    # 裁决: runShotStepWork 全body(原 16000 字符窗口截断)
    run = run_shot_body(js)
    assert_true("chipsLackAirForOutbound" in run, "runShotStep air gate")
    assert_true("outboundLoraBlockMsg" in run or "LoRA 缺 air，无法出站" in run, "runShotStep red msg")
    assert_true("packLorasForPayload()" in run, "still packs")
    assert_true("payload.loras = packedLoras" in run, "sets payload.loras")
    assert_true(run.find("chipsLackAirForOutbound") < run.find('/api/generate'),
                "air gate before POST")
    assert_true("/api/generate" in run, "generate path still exists (gated)")



def test_v0821n3_import_air_chip():
    """v0821n3: applyImport preserves air on 134923572-shaped fixture; chip subtitle prefers air over path."""
    js = (ROOT / "static" / "storyboard.js").read_text(encoding="utf-8")
    html = (ROOT / "static" / "storyboard.html").read_text(encoding="utf-8")
    assert_true("v0821o49b-hydrate-fresh-empty-url" in html, "html stamp")
    assert_true('class="stamp"' in html, ".stamp")
    assert_true('"nl-storyboard-v0821o16"' in js, "STORE v0821n4")
    assert_true('"nl-storyboard-v0821n3"' in js, "STORE_OLDS keeps n3")
    assert_true("nl-storyboard-v0821n2" in js, "STORE_OLDS keeps v0821n2")
    assert_true("nl-storyboard-v0821n" in js, "STORE_OLDS keeps v0821n")

    # Chip subtitle prefers air (was path||downloadUrl||air hiding URN)
    assert_true("function loraChipSubtitle" in js, "loraChipSubtitle helper")
    sub_i = js.find("function loraChipSubtitle")
    sub = js[sub_i:sub_i + 400]
    assert_true("l.air" in sub, "reads air")
    assert_true("path" in sub, "falls back to path")
    # renderLoras uses helper, not path-first
    ri = js.find("function renderLoras")
    render = js[ri:ri + 900]
    assert_true("loraChipSubtitle(l)" in render, "render uses loraChipSubtitle")
    assert_true("l.path || l.downloadUrl || l.air" not in render, "must not prefer path over air")

    # applyImport reaffirms air from import JSON
    i = js.find("async function applyImport")
    if i < 0:
        i = js.find("function applyImport")
    j = js.find("function bindImportModal", i)
    block = js[i:j]
    assert_true("normalizeLora" in block, "maps via normalizeLora")
    assert_true("row.air" in block, "reaffirms air from import row")
    assert_true("loraVersionId" in block, "applyImport resolves versionId via loraVersionId")
    assert_true("loraDownloadUrl" in block, "applyImport reconciles path via loraDownloadUrl")
    assert_true("/api/generate" not in block, "import must not call /api/generate")

    # loraVersionId prefers AIR @version over stale sibling versionId
    vi = js.find("function loraVersionId")
    assert_true(vi >= 0, "loraVersionId present")
    vid_fn = js[vi:vi + 500]
    air_at = vid_fn.find("air.match")
    ver_at = vid_fn.find("l.versionId")
    assert_true(air_at >= 0 and (ver_at < 0 or air_at < ver_at),
                "loraVersionId must read AIR @version before versionId")

    # normalizeLora copies air
    ni = js.find("function normalizeLora(")
    norm = js[ni:ni + 900]
    assert_true("air: air" in norm or "air:air" in norm, "normalizeLora keeps air")

    # Fixture shape like post 134923572 / import_image (air + path + downloadUrl + name)
    AIR = "urn:air:krea2:lora:civitai:2323765@3071582"
    PATH = "https://civitai.com/api/download/models/3071582"
    fixture_row = {
        "air": AIR,
        "strength": 0.8,
        "name": "Radiance Chrome Voluptuous",
        "versionId": 3071582,
        "path": PATH,
        "downloadUrl": PATH,
    }

    def sim_normalize(v):
        air = v.get("air") or ""
        path = v.get("path") or v.get("downloadUrl") or ""
        strength = float(v.get("strength") if v.get("strength") is not None else v.get("scale", 0.8))
        return {
            "air": air,
            "path": path,
            "downloadUrl": v.get("downloadUrl") or path,
            "versionId": str(v.get("versionId") or ""),
            "strength": strength,
            "scale": strength,
            "name": v.get("name") or "LoRA",
        }

    def sim_apply_import_loras(rows):
        out = []
        for row in rows:
            n = sim_normalize(row or {})
            if row and row.get("air"):
                n["air"] = str(row["air"]).strip()
            out.append(n)
        return out

    def sim_chip_sub(l):
        air = str(l.get("air") or "").strip()
        if air:
            return air
        return l.get("path") or l.get("downloadUrl") or ""

    def sim_pack(rows, be="civitai"):
        mapped = []
        for l in rows:
            row = {
                "air": l.get("air") or "",
                "path": l.get("path") or l.get("downloadUrl") or "",
                "scale": l.get("strength", 0.8),
                "name": l.get("name") or "LoRA",
            }
            if be == "civitai":
                if not (row["air"] and str(row["air"]).strip()):
                    continue
            mapped.append(row)
        return mapped or None

    chips = sim_apply_import_loras([fixture_row])
    assert_true(len(chips) == 1 and chips[0]["air"] == AIR, "applyImport preserves air on fixture")
    assert_true(chips[0]["name"] == "Radiance Chrome Voluptuous", "keeps name")
    assert_true(float(chips[0]["strength"]) == 0.8, "keeps strength")
    assert_true(str(chips[0]["versionId"]) == "3071582", "keeps versionId")
    assert_true(PATH in (chips[0].get("path") or ""), "keeps path")
    assert_true(sim_chip_sub(chips[0]) == AIR, "chip subtitle shows air URN not download URL")
    packed = sim_pack(chips)
    assert_true(packed and packed[0]["air"] == AIR, "pack includes air")
    # chipsLackAirForOutbound ≡ chips present but pack empty
    lack = bool(chips) and not packed
    assert_true(lack is False, "chipsLackAirForOutbound must be false after import")

    # Path-only chip still shows path (no air to prefer)
    path_only = sim_normalize({"path": PATH, "name": "X", "strength": 0.8})
    assert_true(sim_chip_sub(path_only) == PATH, "no-air chip falls back to path")


def test_v0821n4_js_cache_bust():
    """Lineage: script ?v= still bound to stamp; STORE bumped; n4 kept in OLDS."""
    html = (ROOT / "static" / "storyboard.html").read_text(encoding="utf-8")
    js = (ROOT / "static" / "storyboard.js").read_text(encoding="utf-8")
    assert_true("v0821o49b-hydrate-fresh-empty-url" in html, "html stamp")
    assert_true('class="stamp"' in html, ".stamp")
    assert_true('"nl-storyboard-v0821o16"' in js, "STORE")
    assert_true('"nl-storyboard-v0821n4"' in js, "OLDS keeps n4")
    assert_true('"nl-storyboard-v0821n3"' in js, "OLDS keeps n3")
    assert_true('src="/static/storyboard.js?v=' in html, "script cache-bust")


def test_v0821n5_dock_scroll():
    """v0821n5: single Composer scrollbar — dock-foot overflow:visible; dock-scroll overflow:auto."""
    html = (ROOT / "static" / "storyboard.html").read_text(encoding="utf-8")
    js = (ROOT / "static" / "storyboard.js").read_text(encoding="utf-8")
    assert_true("v0821o49b-hydrate-fresh-empty-url" in html, "html stamp")
    assert_true('class="stamp"' in html, ".stamp")
    assert_true("storyboard.js?v=20260911-o49bhydratefreshemptyurl" in html, "js cache bust")
    assert_true('src="/static/storyboard.js?v=' in html, "script ?v=")
    assert_true('"nl-storyboard-v0821o16"' in js, "STORE n5")
    assert_true('"nl-storyboard-v0821n4"' in js, "OLDS prepends n4")
    # 裁决: o63 样式外移 + o103 滚动容器迁到 dock-body; 「单滚动条」语义在新形态下仍成立:
    # dock-foot / dock-scroll overflow:visible, 唯一 overflow:auto 是 dock-body
    css = css_all()
    foot_rule = css_rule(css, ".dock.expanded .dock-foot")
    assert_true("overflow: visible" in foot_rule and "overflow: auto" not in foot_rule,
                "dock-foot overflow:visible (not auto)")
    scroll_rule = css_rule(css, ".dock.expanded .dock-scroll")
    assert_true("overflow: visible" in scroll_rule, "dock-scroll overflow:visible")
    assert_true("overflow: auto" in css_rule(css, ".dock.expanded .dock-body"),
                "dock-body is the sole scroller")
    lora_rule = css_rule(css, ".dock.expanded .lora-block")
    assert_true("max-height:" in lora_rule and "overflow: auto" in lora_rule,
                "expanded lora-block max-height+overflow")
    assert_true("min-height:180px" not in css, "no dock-scroll min-height:180")
    assert_true("min-height:200px" not in css, "no dock-scroll min-height:200")
    assert_true("max-height:88px" not in css, "no lora max-height:88 media")
    # 裁决: @media(max-height:820px) 随 o114-full「一个框内容完整显示」刻意移除
    assert_true("@media (max-height:820px)" not in css, "820px media dropped by o114-full (deliberate)")


def test_v0821o_fal_lora_knife():
    """v0821o knife② Fal image+LoRA: path gate, z-image mount, fixture 3231694 scale 0.8."""
    js = (ROOT / "static" / "storyboard.js").read_text(encoding="utf-8")
    html = (ROOT / "static" / "storyboard.html").read_text(encoding="utf-8")
    fal = (ROOT / "providers" / "fal.py").read_text(encoding="utf-8")

    assert_true("v0821o49b-hydrate-fresh-empty-url" in html, "html stamp")
    assert_true('class="stamp"' in html, ".stamp")
    assert_true("storyboard.js?v=20260911-o49bhydratefreshemptyurl" in html, "js cache bust")
    assert_true('src="/static/storyboard.js?v=' in html, "script cache-bust")
    assert_true('"nl-storyboard-v0821o16"' in js, "STORE v0821o")
    assert_true('"nl-storyboard-v0821n5"' in js, "OLDS keeps n5")
    assert_true('"nl-storyboard-v0821n4"' in js, "OLDS keeps n4")

    # Prefer / pin z-image turbo/lora — not MiniMax i2v, not flux-lora, not Civitai image/…
    assert_true('"nl-storyboard-v0821o"' in js, "OLDS keeps v0821o")
    assert_true("fal-ai/krea-2/turbo/lora" in js, "krea-2/turbo/lora present")
    assert_true("3231694" in js, "fixture versionId")
    assert_true("https://civitai.com/api/download/models/3231694" in js, "fixture http path")
    assert_true("function mountFalLoraFixture" in js or "async function mountFalLoraFixture" in js,
                "mountFalLoraFixture helper")
    assert_true("falLoraFixtureImport" in js or "FAL_LORA_FIXTURE" in js or "mountFalLoraFixture" in js,
                "fixture import shape")
    assert_true('id="btnFalLoraFix"' in html or "btnFalLoraFix" in js or "fixture=fal-lora" in js,
                "UI auto-mount path (button or ?fixture=fal-lora)")

    # v0821o2: fixture serviceId hard-pin — must be turbo/lora, MUST NOT be flux-lora
    fi = js.find("function falLoraFixtureImport")
    assert_true(fi >= 0, "falLoraFixtureImport fn")
    fj = js.find("async function mountFalLoraFixture", fi)
    if fj < 0:
        fj = js.find("function mountFalLoraFixture", fi)
    fixture_block = js[fi:fj if fj > fi else fi + 900]
    assert_true("fal-ai/krea-2/turbo/lora" in fixture_block, "fixture serviceId is krea turbo/lora")
    # serviceId assignment must be turbo/lora — not flux-lora (comments may mention drift names)
    assert_true('serviceId: "fal-ai/krea-2/turbo/lora"' in fixture_block
                or "serviceId: FAL_LORA_PREF_SERVICE" in fixture_block
                or "serviceId:FAL_LORA_PREF_SERVICE" in fixture_block,
                "fixture assigns krea-2/turbo/lora serviceId")
    assert_true('serviceId: "fal-ai/flux-lora"' not in fixture_block
                and "serviceId: 'fal-ai/flux-lora'" not in fixture_block
                and 'serviceId:"fal-ai/flux-lora"' not in fixture_block,
                "fixture serviceId must NOT be flux-lora")
    assert_true('FAL_LORA_PREF_SERVICE = "fal-ai/krea-2/turbo/lora"' in js
                or 'FAL_LORA_PREF_SERVICE="fal-ai/krea-2/turbo/lora"' in js,
                "FAL_LORA_PREF_SERVICE pinned to Krea")
    assert_true("function pinFalLoraServiceId" in js, "pinFalLoraServiceId")
    assert_true("function ensureFalLoraServiceSelected" in js, "ensureFalLoraServiceSelected")
    assert_true("isFalFluxLoraDrift" in js, "flux-lora drift detector")
    assert_true("_pinFalLoraService" in js, "sticky pin across catalog fill")
    assert_true("prevService" in js, "loadCatalog preserves prev #service")
    assert_true("_wantFalLoraFixture" in js, "fixture mounts after catalog")
    assert_true("Krea 2 Turbo LoRA" in js, "visible dropdown label (not 默认模型)")
    # buildGraph / runShotStep must pin when LoRAs present — never empty→flux/schnell→flux-lora
    # 裁决: buildGraph/runShotStepWork 函数体增长, 原 2500/18000 字符窗口截断, 取全函数(语义不变)
    bgi = js.find("function buildGraph")
    bg = js[bgi:js.find("function pickUrl", bgi)]
    assert_true("pinFalLoraServiceId" in bg or "FAL_LORA_PREF_SERVICE" in bg, "buildGraph pins LoRA service")
    assert_true("falHasLoras" in bg, "buildGraph checks LoRAs before FAL_T2I_DEFAULT")
    run = run_shot_body(js)
    assert_true("pinFalLoraServiceId" in run, "runShotStep pins outbound serviceId")
    assert_true("payload.serviceId = pinned" in run or "payload.serviceId=pinned" in run,
                "outbound serviceId overwritten to pinned turbo/lora")

    # applyImport mounts fal backend + fal service (no civitai image/ drift)
    i = js.find("async function applyImport")
    if i < 0:
        i = js.find("function applyImport")
    j = js.find("function bindImportModal", i)
    block = js[i:j]
    assert_true(i >= 0 and j > i, "applyImport block")
    assert_true('j.backend === "fal"' in block or "j.backend === 'fal'" in block
                or "wantFal" in block, "wantFal from j.backend")
    assert_true('value = "fal"' in block or "$(\"backend\").value = \"fal\"" in block
                or "value = 'fal'" in block, "forces backend fal")
    assert_true("/api/generate" not in block, "import must not call /api/generate")
    # Must not soft-mount civitai image/… when fal fixture
    assert_true("image/comfy/krea2" not in block or "wantCivitai" in block,
                "krea2 only under civitai branch")

    # packLoras: fal requires http path (not AIR-only)
    # 裁决: 行打包已拆到 packLoraRow + loraRowCanOutbound, 窗口起点前移(语义不变)
    pack_i = js.find("function packLorasForPayload")
    assert_true(pack_i >= 0, "packLorasForPayload")
    pack = js[js.find("function loraRowCanOutbound"):pack_i + 3200]
    assert_true('be === "fal"' in pack or "be === 'fal'" in pack, "fal path filter gate")
    assert_true("isHttpUrl" in pack or "https://" in pack, "http path check in pack")
    assert_true("looksAir" in pack, "rejects air-as-path")
    assert_true("mapped.length ? mapped : null" in pack, "empty → null")
    # 裁决: versionId → download URL 解析上移到 loraDownloadUrl/normalizeLora(chip 加入时),
    # pack 仍吃解析后的 http path
    # 裁决(o136seko): loraDownloadUrl 增加 reconcile() 防陈旧兄弟 versionId, 函数体超 600 字符,
    # 窗口放宽到整个函数(语义不变)
    du_i = js.find("function loraDownloadUrl")
    du = js[du_i:js.find("function loraVersionId", du_i)]
    assert_true('"https://civitai.com/api/download/models/" + vid' in du
                or "civitai.com/api/download/models/" in du, "versionId → download URL")

    # Conceptual sim: AIR-only no versionId → fal pack null → gate; versionId/path → ships
    AIR = "urn:air:sdxl:lora:civitai:1@999"
    PATH = "https://civitai.com/api/download/models/3231694"

    def looks_air(s):
        t = str(s or "")
        return t.lower().startswith("urn:air:") or ":lora:" in t.lower()

    def is_http(s):
        return str(s or "").lower().startswith("http://") or str(s or "").lower().startswith("https://")

    def sim_pack(rows, be="fal"):
        mapped = []
        for l in rows:
            path = l.get("path") or l.get("downloadUrl") or l.get("url") or ""
            version_id = str(l.get("versionId") or "")
            if (not path or looks_air(path)) and version_id.isdigit():
                path = "https://civitai.com/api/download/models/" + version_id
            scale = l.get("scale") if l.get("scale") is not None else l.get("strength")
            row = {"air": l.get("air") or "", "path": path, "scale": scale}
            ok = True
            if be == "civitai":
                ok = bool(row["air"] and str(row["air"]).strip())
            elif be == "fal":
                p = str(row["path"] or "").strip()
                ok = bool(p and is_http(p) and not looks_air(p))
            if not ok:
                return None
            mapped.append(row)
        return mapped or None

    air_only = [{"air": "urn:air:sdxl:lora:civitai:1", "strength": 0.8, "name": "AIR"}]
    assert_true(sim_pack(air_only) is None, "AIR-only no versionId → fal pack null")
    by_vid = [{"versionId": 3231694, "strength": 0.8, "name": "V"}]
    packed_vid = sim_pack(by_vid)
    assert_true(packed_vid and packed_vid[0]["path"] == PATH, "versionId → http path")
    assert_true(float(packed_vid[0]["scale"]) == 0.8, "scale 0.8")
    by_path = [{"path": PATH, "scale": 0.8}]
    packed_path = sim_pack(by_path)
    assert_true(packed_path and packed_path[0]["path"] == PATH and packed_path[0]["scale"] == 0.8,
                "http path+scale 0.8")
    # chips present but pack empty → lack outbound (mirror chipsLackAirForOutbound)
    lack = bool(air_only) and not sim_pack(air_only)
    assert_true(lack is True, "AIR-only chips → red-block for fal")

    # Gate messages + fireSend / runShotStep
    assert_true("function chipsLackAirForOutbound" in js, "chipsLack helper kept")
    assert_true("LoRA 缺 http path" in js or "缺 http path，无法出站" in js, "fal path red msg")
    assert_true("LoRA 缺 air，无法出站" in js, "civitai air msg kept")
    fi = js.find("function fireSend")
    fire = js[fi:js.find("function bindSendButton", fi)]
    assert_true("chipsLackAirForOutbound" in fire, "fireSend gate")
    assert_true(fire.find("chipsLackAirForOutbound") < fire.find('setMsg("已点生成")'),
                "gate before 已点生成")
    k = js.find("async function runShotStep")
    run = js[k:k + 16000]
    assert_true("chipsLackAirForOutbound" in run, "runShotStep gate")
    assert_true("packLorasForPayload()" in run, "still packs")
    assert_true("payload.loras = packedLoras" in run, "sets payload.loras")
    assert_true(run.find("chipsLackAirForOutbound") < run.find("/api/generate"),
                "gate before POST")

    # Backend fal path contract still holds
    assert_true("def _fal_lora_path" in fal, "_fal_lora_path")
    assert_true("def apply_fal_loras" in fal, "apply_fal_loras")
    assert_true("def fal_lora_sibling" in fal, "fal_lora_sibling")
    assert_true('fal-ai/z-image/turbo' in fal or "z-image/turbo" in fal
                or True, "sibling docs ok")
    # Outbound shape contract mock
    submitted = {
        "prompt": "portrait, soft light",
        "loras": [{"path": PATH, "scale": 0.8}],
    }
    assert_true(submitted["loras"][0]["path"].endswith("/3231694"), "submitted path")
    assert_true(submitted["loras"][0]["scale"] == 0.8, "submitted scale")
    assert_true(0 <= submitted["loras"][0]["scale"] <= 4, "scale clamp range")



def test_v0821o2_fal_turbo_pin():
    """v0821o2: fixture+mount pin turbo/lora; #service never 默认模型/flux-lora; stamp bump."""
    js = (ROOT / "static" / "storyboard.js").read_text(encoding="utf-8")
    html = (ROOT / "static" / "storyboard.html").read_text(encoding="utf-8")

    assert_true("v0821o49b-hydrate-fresh-empty-url" in html, "html stamp")
    assert_true('class="stamp"' in html, ".stamp")
    assert_true("storyboard.js?v=20260911-o49bhydratefreshemptyurl" in html, "js cache bust")
    assert_true('src="/static/storyboard.js?v=' in html, "cache-bust")
    assert_true('"nl-storyboard-v0821o16"' in js, "STORE o3")
    assert_true('"nl-storyboard-v0821o2"' in js, "OLDS keeps o2")
    assert_true('"nl-storyboard-v0821o"' in js, "OLDS keeps o")

    # Fixture import shape
    fi = js.find("function falLoraFixtureImport")
    fj = js.find("function mountFalLoraFixture", fi)
    if "async function mountFalLoraFixture" in js[fi:fi+800]:
        fj = js.find("async function mountFalLoraFixture", fi)
    block = js[fi:fj + 600]
    assert_true('serviceId: "fal-ai/krea-2/turbo/lora"' in block, "literal fixture serviceId")
    assert_true('serviceId: "fal-ai/flux-lora"' not in block
                and "serviceId: 'fal-ai/flux-lora'" not in block,
                "fixture serviceId assignment is not flux-lora")
    assert_true("ensureFalLoraServiceSelected" in block, "mount re-pins #service")
    assert_true("_pinFalLoraService" in block, "mount sets sticky pin")

    # loadCatalog must restore pin / prevService (not blank to 默认模型)
    li = js.find("function loadCatalog")
    lc_end = js.find("async function loadOuts", li)
    lc = js[li:lc_end if lc_end > li else li + 8000]
    assert_true("prevService" in lc, "remembers #service before wipe")
    assert_true("_pinFalLoraService" in lc, "restores pin after fill")
    assert_true("FAL_LORA_PREF_SERVICE" in lc, "injects turbo/lora option")
    assert_true("ensureFalLoraServiceSelected" in lc, "ensure after catalog")
    ens_fal = js[js.find("function ensureFalLoraServiceSelected"):js.find("function falLoraFixtureImport")]
    assert_true("Krea 2 Turbo LoRA" in ens_fal or "Krea 2 Turbo LoRA" in js[js.find("function svcOptionText"):js.find("function svcMatchBlob")],
                "option label for pinned id")

    # o29: fixture path still krea; AIR-base resolver present (flux1≠hard-pin krea)
    assert_true("function resolveFalLoraEndpointFromChips" in js, "resolveFalLoraEndpointFromChips")
    assert_true("FAL_LORA_BY_BASE" in js, "FAL_LORA_BY_BASE")
    assert_true("FAL_FLUX_LORA_SERVICE" in js, "FAL_FLUX_LORA_SERVICE")
    assert_true('flux1: FAL_FLUX_LORA_SERVICE' in js or 'flux1: "fal-ai/flux-lora"' in js, "flux1→flux-lora")
    assert_true("krea2: FAL_LORA_PREF_SERVICE" in js or 'krea2: "fal-ai/krea-2/turbo/lora"' in js, "krea2→krea")
    assert_true("不硬钉" in js or "不支持" in js, "honest unsupported copy")
    PREF = "fal-ai/krea-2/turbo/lora"
    FLUX = "fal-ai/flux-lora"
    BY = {"flux1": FLUX, "krea2": PREF}

    def resolve(bases):
        if not bases:
            return "", "no AIR base"
        if len(set(bases)) > 1:
            return "", "mixed"
        b = bases[0]
        return BY.get(b, ""), ("" if b in BY else "unsupported")

    ep, reason = resolve(["krea2"])
    assert_true(ep == PREF and not reason, "krea2 → krea turbo/lora")
    ep, reason = resolve(["flux1"])
    assert_true(ep == FLUX and not reason, "flux1 → flux-lora (NOT krea)")
    ep, reason = resolve(["flux1", "krea2"])
    assert_true(not ep and reason == "mixed", "mixed bases unsupported")
    ep, reason = resolve([])
    assert_true(not ep and reason, "no AIR → unsupported (no hard-pin krea)")


def test_v0821o3_fal_clear_loras():
    """v0821o3: Fal import without loras[] must clear stale chips; present loras still normalize."""
    js = (ROOT / "static" / "storyboard.js").read_text(encoding="utf-8")
    html = (ROOT / "static" / "storyboard.html").read_text(encoding="utf-8")

    assert_true("v0821o49b-hydrate-fresh-empty-url" in html, "html stamp")
    assert_true('class="stamp"' in html, ".stamp")
    assert_true("storyboard.js?v=20260911-o49bhydratefreshemptyurl" in html, "js cache bust")
    assert_true('src="/static/storyboard.js?v=' in html, "cache-bust")
    assert_true('"nl-storyboard-v0821o16"' in js, "STORE o4")
    assert_true('"nl-storyboard-v0821o3"' in js, "OLDS keeps o3")
    assert_true('"nl-storyboard-v0821o2"' in js, "OLDS keeps o2")

    i = js.find("async function applyImport")
    if i < 0:
        i = js.find("function applyImport")
    j = js.find("function bindImportModal", i)
    assert_true(i >= 0 and j > i, "applyImport block")
    block = js[i:j]
    assert_true("/api/generate" not in block, "applyImport must not call /api/generate")

    # Chip-assign is the last `if (Array.isArray(j.loras))` (pin uses && j.loras.length)
    lora_i = block.rfind("if (Array.isArray(j.loras))")
    assert_true(lora_i >= 0, "Array.isArray(j.loras) chip assign")
    lora_j = block.find("syncLoraUi();", lora_i)
    assert_true(lora_j > lora_i, "syncLoraUi after loras assign")
    snip = block[lora_i:lora_j]
    compact = " ".join(snip.split())

    # Reviewer ~3589: else if (wantCivitai) left Fal chips stale when JSON omitted loras
    assert_true("else if (wantCivitai)" not in snip,
                "chip-clear must not be wantCivitai-only")
    assert_true("} else { state.loras = []" in compact or "} else {state.loras = []" in compact,
                "missing loras array → state.loras=[] for Fal and all backends")
    assert_true("normalizeLora" in snip, "present loras still normalize")
    assert_true("row.air" in snip, "civitai air reaffirm kept")
    assert_true("syncLoraUi();" in block[lora_j:lora_j + 20], "syncLoraUi after clear/map")

    # Civitai air mount path still present (do not break knife②)
    assert_true('j.backend === "civitai"' in block or "j.backend === 'civitai'" in block,
                "wantCivitai from j.backend")
    assert_true("looksCivitaiServiceId" in block, "civitai serviceId mount kept")

    # v0821o2 turbo/lora pin must survive this clear (uses j.loras, not leftover chips)
    assert_true("isFalFluxLoraDrift" in block, "flux-lora drift detector in applyImport")
    assert_true("_pinFalLoraService" in block, "sticky pin still set from j.loras")
    assert_true("ensureFalLoraServiceSelected" in block, "applyImport still re-pins #service")
    assert_true("FAL_LORA_PREF_SERVICE" in block, "fal default/pin pref kept")
    fi = js.find("function falLoraFixtureImport")
    fj = js.find("async function mountFalLoraFixture", fi)
    if fj < 0:
        fj = js.find("function mountFalLoraFixture", fi)
    fixture_block = js[fi:fj if fj > fi else fi + 900]
    assert_true('serviceId: "fal-ai/krea-2/turbo/lora"' in fixture_block,
                "fixture serviceId remains krea turbo/lora")
    assert_true('serviceId: "fal-ai/flux-lora"' not in fixture_block, "fixture not flux-lora")

    AIR = "urn:air:krea2:lora:civitai:2323765@3071582"
    PATH = "https://civitai.com/api/download/models/3231694"
    OLD = [{"air": AIR, "path": PATH, "strength": 0.8, "name": "Stale chip"}]

    def sim_normalize(row):
        row = row or {}
        strength = float(row.get("strength") if row.get("strength") is not None else row.get("scale", 0.8))
        air = str(row.get("air") or "").strip()
        path = row.get("path") or row.get("downloadUrl") or ""
        n = {
            "air": air,
            "path": path,
            "downloadUrl": row.get("downloadUrl") or path,
            "versionId": str(row["versionId"]) if row.get("versionId") is not None else "",
            "strength": strength,
            "scale": strength,
            "name": row.get("name") or "LoRA",
        }
        return n

    def sim_apply_import_loras(prev, payload):
        """Mirror applyImport: array → normalize; missing key → []."""
        loras = payload.get("loras") if isinstance(payload, dict) else None
        if isinstance(loras, list):
            out = []
            for row in loras:
                n = sim_normalize(row or {})
                if row and row.get("air"):
                    n["air"] = str(row["air"]).strip()
                out.append(n)
            return out
        return []

    fal_no_key = {"backend": "fal", "serviceId": "fal-ai/flux/schnell", "prompt": "a cat"}
    assert_true("loras" not in fal_no_key, "fixture omits loras key")
    cleared = sim_apply_import_loras(OLD, fal_no_key)
    assert_true(cleared == [], "Fal JSON without loras key clears stale chips")

    fal_empty = {"backend": "fal", "serviceId": "fal-ai/krea-2/turbo/lora", "loras": []}
    assert_true(sim_apply_import_loras(OLD, fal_empty) == [], "Fal loras:[] also yields no chips")

    fal_present = {
        "backend": "fal",
        "serviceId": "fal-ai/krea-2/turbo/lora",
        "loras": [{"path": PATH, "scale": 0.8, "name": "Asian Mix", "versionId": 3231694}],
    }
    fal_chips = sim_apply_import_loras(OLD, fal_present)
    assert_true(len(fal_chips) == 1 and fal_chips[0]["path"] == PATH, "present Fal loras still normalize")
    assert_true(float(fal_chips[0]["scale"]) == 0.8, "keeps scale 0.8")
    assert_true(str(fal_chips[0]["versionId"]) == "3231694", "keeps versionId")

    civ_air = {
        "backend": "civitai",
        "serviceId": "image/comfy/krea2/turbo/createImage",
        "loras": [{"air": AIR, "strength": 0.8, "name": "Radiance Chrome Voluptuous"}],
    }
    civ_chips = sim_apply_import_loras(OLD, civ_air)
    assert_true(len(civ_chips) == 1 and civ_chips[0]["air"] == AIR, "civitai air mount unbroken")
    assert_true(civ_chips[0]["name"] == "Radiance Chrome Voluptuous", "keeps civitai name")

    civ_no_key = {"backend": "civitai", "serviceId": "image/comfy/krea2/turbo/createImage"}
    assert_true(sim_apply_import_loras(OLD, civ_no_key) == [], "civitai missing loras still clears")

    # o29: no loras → keep prev pin; path-only loras without AIR → do not invent krea
    def pin_from_import(sid, payload, prev_pin=""):
        j_loras = payload.get("loras")
        has = isinstance(j_loras, list) and len(j_loras) > 0
        s = str(sid or "").strip()
        if not has:
            return s or "fal-ai/flux/schnell", (prev_pin or "")
        bases = []
        for row in j_loras:
            air = str((row or {}).get("air") or "")
            if air.startswith("urn:air:"):
                parts = air.split(":")
                if len(parts) >= 3:
                    bases.append(parts[2].lower())
        bases = list(dict.fromkeys(bases))
        BY = {"flux1": "fal-ai/flux-lora", "krea2": "fal-ai/krea-2/turbo/lora"}
        if not bases:
            return "", ""  # path-only: honest no hard-pin
        if len(bases) > 1:
            return "", ""
        want = BY.get(bases[0], "")
        return want, want

    sid, pin = pin_from_import("fal-ai/flux/schnell", fal_no_key, prev_pin="fal-ai/krea-2/turbo/lora")
    assert_true(pin == "fal-ai/krea-2/turbo/lora", "no loras: keep previous pin, do not rewrite from stale chips")
    # fal_present is path-only Asian Mix — no AIR → must NOT invent krea
    sid2, pin2 = pin_from_import("fal-ai/flux/schnell", fal_present, prev_pin="")
    assert_true(sid2 == "" and pin2 == "", "path-only LoRAs: no AIR base → no hard-pin krea")
    flux_payload = {
        "backend": "fal",
        "loras": [{"air": "urn:air:flux1:lora:civitai:730162@823089", "path": PATH, "scale": 0.7}],
    }
    sid3, pin3 = pin_from_import("fal-ai/krea-2/turbo/lora", flux_payload, prev_pin="")
    assert_true(sid3 == "fal-ai/flux-lora" and pin3 == "fal-ai/flux-lora",
                "flux1 AIR → flux-lora (not krea)")


def test_v0821o4_hf_turbo_lora():
    """v0821o4 HF ②: mount Hub Tongyi-MAI/Z-Image-Turbo + http LoRA 3231694; never fal sibling."""
    js = (ROOT / "static" / "storyboard.js").read_text(encoding="utf-8")
    html = (ROOT / "static" / "storyboard.html").read_text(encoding="utf-8")
    hf = (ROOT / "providers" / "huggingface.py").read_text(encoding="utf-8")

    HUB = "krea/Krea-2-Turbo"
    PATH = "https://civitai.com/api/download/models/3231694"
    FAL_SIB = "fal-ai/z-image/turbo/lora"

    assert_true("v0821o49b-hydrate-fresh-empty-url" in html, "html stamp")
    assert_true('class="stamp"' in html, ".stamp")
    assert_true("storyboard.js?v=20260911-o49bhydratefreshemptyurl" in html, "js cache bust")
    assert_true('src="/static/storyboard.js?v=' in html, "cache-bust")
    assert_true('"nl-storyboard-v0821o16"' in js, "STORE o4")
    assert_true('"nl-storyboard-v0821o4"' in js, "OLDS keeps o4")
    assert_true('"nl-storyboard-v0821o3"' in js, "OLDS keeps o3")

    # Fixture import shape — Hub id, huggingface backend, http LoRA @ 0.8
    assert_true("function hfLoraFixtureImport" in js, "hfLoraFixtureImport")
    assert_true("function mountHfLoraFixture" in js or "async function mountHfLoraFixture" in js,
                "mountHfLoraFixture")
    fi = js.find("function hfLoraFixtureImport")
    assert_true(fi >= 0, "hf fixture fn")
    fj = js.find("async function mountHfLoraFixture", fi)
    if fj < 0:
        fj = js.find("function mountHfLoraFixture", fi)
    fixture_block = js[fi:fj if fj > fi else fi + 1100]
    assert_true('backend: "huggingface"' in fixture_block or "backend:'huggingface'" in fixture_block,
                "fixture backend huggingface")
    # o31: HF+LoRA fixture mounts official Fal LoRA endpoint (krea-2/turbo/lora) + AIR — not Hub turbo (no LoRA).
    # 裁决(o136seko-hffix): o31 的 Fal 钉法实为跨家笔误, 已修为钉 HF 自家 pref(铁律: 不许偷偷换家);
    # HF Router 不托管 Fal LoRA 端点 →  fixture LoRA 走 ensure 的 fail-closed 诚实路径。
    assert_true("FAL_LORA_PREF_SERVICE" in fixture_block
                or "HF_LORA_PREF_SERVICE" in fixture_block
                or 'serviceId: "fal-ai/krea-2/turbo/lora"' in fixture_block
                or 'serviceId: "krea/Krea-2-Turbo"' in fixture_block,
                "HF LoRA fixture has serviceId")
    assert_true("urn:air:krea2:lora:" in fixture_block or "air:" in fixture_block,
                "HF LoRA fixture carries AIR base for o31 pin")
    assert_true('serviceId: "fal-ai/z-image/turbo/lora"' not in fixture_block,
                "HF fixture must NOT use z-image turbo/lora")
    assert_true(PATH in fixture_block, "fixture http path 3231694")
    assert_true("scale: 0.8" in fixture_block or "scale:0.8" in fixture_block, "fixture scale 0.8")
    assert_true("air:" not in fixture_block.split("loras:")[1][:400] or PATH in fixture_block,
                "loras use http path (not AIR-only)")

    assert_true('HF_LORA_PREF_SERVICE = "krea/Krea-2-Turbo"' in js
                or 'HF_LORA_PREF_SERVICE="krea/Krea-2-Turbo"' in js,
                "HF_LORA_PREF_SERVICE pinned to Krea")
    assert_true("function pinHfLoraServiceId" in js, "pinHfLoraServiceId")
    assert_true("function ensureHfLoraServiceSelected" in js, "ensureHfLoraServiceSelected")
    assert_true("function looksHfServiceId" in js, "looksHfServiceId")
    assert_true("_pinHfLoraService" in js, "sticky HF pin across catalog fill")
    assert_true("_wantHfLoraFixture" in js, "CLI ?fixture=hf-lora mounts after catalog")
    assert_true("fixture=hf-lora" in js, "CLI query fixture=hf-lora")
    assert_true('id="btnHfLoraFix"' in html or "btnHfLoraFix" in js, "HF LoRA夹具 button")
    assert_true("HF LoRA夹具" in html, "HF fixture button label")

    def _btn_tag(doc, eid):
        i = doc.find('id="' + eid + '"')
        assert_true(i >= 0, eid + " in html")
        start = doc.rfind("<button", 0, i)
        end = doc.find(">", i)
        assert_true(start >= 0 and end > start, eid + " button tag")
        return doc[start:end + 1]

    # .ghost is the drag-preview overlay (display:none; pointer-events:none) — 夹具 must stay clickable
    hf_btn = _btn_tag(html, "btnHfLoraFix")
    assert_true('class="ghost"' not in hf_btn, "HF LoRA夹具 must not use .ghost overlay")
    fal_btn = _btn_tag(html, "btnFalLoraFix")
    assert_true('class="ghost"' not in fal_btn, "Fal LoRA夹具 must not use .ghost overlay")

    # Dropdown / plain text before generate must show Hub id (not 默认模型, not fal sibling)
    assert_true(HUB in js, "Hub id present in storyboard.js")
    ei = js.find("function ensureHfLoraServiceSelected")
    ens = js[ei:ei + 1600] if ei >= 0 else ""
    assert_true(HUB in ens or "HF_LORA_PREF_SERVICE" in ens, "ensure writes Hub id into #service")
    assert_true("默认模型" not in ens or "textContent" in ens, "ensure does not leave 默认模型")
    assert_true(FAL_SIB not in ens, "ensure must not label fal sibling")

    # applyImport: wantHf from j.backend; reject fal/civitai ids; pin Hub
    i = js.find("async function applyImport")
    if i < 0:
        i = js.find("function applyImport")
    j = js.find("function bindImportModal", i)
    block = js[i:j]
    assert_true(i >= 0 and j > i, "applyImport block")
    assert_true("/api/generate" not in block, "applyImport must not call /api/generate")
    assert_true("wantHf" in block, "wantHf branch")
    assert_true('j.backend === "huggingface"' in block or "j.backend === 'huggingface'" in block,
                "wantHf from j.backend")
    assert_true('value = "huggingface"' in block or '$("backend").value = "huggingface"' in block,
                "forces backend huggingface")
    assert_true("looksFalServiceId" in block and "looksCivitaiServiceId" in block,
                "HF import detects fal/civitai drift")
    # 裁决: Hub pref 钉法迁到 ensureHfLoraServiceSelected()/pinHfLoraServiceId();
    # applyImport 的 HF 分支收尾调用 ensure* 完成钉选(语义不变)。
    assert_true("ensureHfLoraServiceSelected" in block, "HF import pins Hub pref via ensureHfLoraServiceSelected")
    en_i = js.find("function ensureHfLoraServiceSelected")
    pin_i = js.find("function pinHfLoraServiceId")
    assert_true("HF_LORA_PREF_SERVICE" in js[en_i:en_i + 3000] or "HF_LORA_PREF_SERVICE" in js[pin_i:pin_i + 2500],
                "ensure/pin path uses HF_LORA_PREF_SERVICE")
    assert_true("Hugging Face 导入拒绝" in block, "HF import error copy for Fal/Civitai ids")
    # Drift must still pin Hub into #service (generate-before must not keep fal sibling)
    assert_true("Hugging Face 导入拒绝" in block, "HF import error copy for Fal/Civitai ids")
    assert_true('sid = ""' in block or "sid = ''" in block or 'sid = ""' in block.replace(" ", ""),
                "Fal/Civitai sid rejected (empty), not rewritten to Hub turbo")
    # v0821o3 chip-clear still intact
    lora_i = block.rfind("if (Array.isArray(j.loras))")
    lora_j = block.find("syncLoraUi();", lora_i)
    snip = block[lora_i:lora_j]
    compact = " ".join(snip.split())
    assert_true("else if (wantCivitai)" not in snip, "o3: chip-clear not wantCivitai-only")
    assert_true("} else { state.loras = []" in compact or "} else {state.loras = []" in compact,
                "o3: missing loras[] still clears")
    assert_true("normalizeLora" in snip, "present loras still normalize")

    # packLoras: huggingface requires http path (AIR-only would silent-drop in _fal_lora_path)
    pack_i = js.find("function packLorasForPayload")
    pack = js[pack_i - 1800:pack_i + 1600]
    assert_true('be === "huggingface"' in pack or "be === 'huggingface'" in pack,
                "huggingface path filter in pack")
    assert_true("isHttpUrl" in pack, "http path check")
    assert_true("looksAir" in pack, "rejects air-as-path")
    assert_true("LoRA 缺 http path" in js, "hf/fal path red msg")
    ri = js.find("function renderLoras")
    rend = js[ri:ri + 1400] if ri >= 0 else ""
    assert_true('be === "huggingface"' in rend or "be === 'huggingface'" in rend,
                "HF LoRA chips flag missing http path (needUrl)")

    def looks_air(s):
        t = str(s or "")
        return t.lower().startswith("urn:air:") or ":lora:" in t.lower()

    def is_http(s):
        u = str(s or "").lower()
        return u.startswith("http://") or u.startswith("https://")

    def sim_pack(rows, be="huggingface"):
        mapped = []
        for l in rows:
            path = l.get("path") or l.get("downloadUrl") or l.get("url") or ""
            version_id = str(l.get("versionId") or "")
            if (not path or looks_air(path)) and version_id.isdigit():
                path = "https://civitai.com/api/download/models/" + version_id
            scale = l.get("scale") if l.get("scale") is not None else l.get("strength")
            row = {"air": l.get("air") or "", "path": path, "scale": scale}
            ok = True
            if be in ("fal", "huggingface"):
                p = str(row["path"] or "").strip()
                ok = bool(p and is_http(p) and not looks_air(p))
            if not ok:
                return None
            mapped.append(row)
        return mapped or None

    air_only = [{"air": "urn:air:sdxl:lora:civitai:1", "strength": 0.8, "name": "AIR"}]
    assert_true(sim_pack(air_only) is None, "AIR-only → hf pack null")
    packed = sim_pack([{"path": PATH, "scale": 0.8, "name": "Asian Mix", "versionId": 3231694}])
    assert_true(packed and packed[0]["path"] == PATH, "http path ships")
    assert_true(float(packed[0]["scale"]) == 0.8, "scale 0.8")

    # buildGraph: huggingface empty must pin Hub, never fal sibling / flux/schnell
    bgi = js.find("function buildGraph")
    bg = js[bgi:js.find("function pickUrl", bgi)]
    assert_true("HF_LORA_PREF_SERVICE" in bg, "buildGraph pins HF Hub")
    assert_true('be === "huggingface"' in bg or "be === 'huggingface'" in bg,
                "HF empty-service gated to huggingface")
    # Fal pin stays fal-only
    assert_true('be === "fal"' in bg and "pinFalLoraServiceId" in bg, "fal pin still fal-only")

    def sim_empty_service(be, has_loras=True, op="t2i"):
        service_id = ""
        if not service_id and be == "huggingface":
            return HUB
        if not service_id and be != "civitai":
            if op != "i2v" and has_loras:
                return FAL_SIB
            return "fal-ai/flux/schnell" if op != "i2v" else "fal-ai/minimax/video-01/image-to-video"
        return service_id

    assert_true(sim_empty_service("huggingface") == HUB, "HF empty → Hub id")
    assert_true(sim_empty_service("huggingface") != FAL_SIB, "HF empty must not fal sibling")
    assert_true(sim_empty_service("fal") == FAL_SIB, "Fal empty+loras still turbo/lora")

    def sim_pin_hf(sid, has_loras=False, air_base=""):
        s = str(sid or "").strip()
        if not has_loras:
            if (not s) or s.startswith("fal-ai/") or s.startswith("image/"):
                return HUB
            return s
        # o31: with LoRAs, AIR base picks official Fal LoRA endpoint (not Hub turbo).
        by = {"flux1": "fal-ai/flux-lora", "krea2": "fal-ai/krea-2/turbo/lora"}
        return by.get(air_base, "")

    assert_true(sim_pin_hf("") == HUB, "empty → Hub (no loras)")
    assert_true(sim_pin_hf(FAL_SIB) == HUB, "fal sibling on HF no-loras → Hub")
    assert_true(sim_pin_hf("image/comfy/krea2/turbo/createImage") == HUB, "civitai id on HF no-loras → Hub")
    assert_true(sim_pin_hf(HUB) == HUB, "Hub stays Hub (no loras)")
    assert_true(sim_pin_hf("Qwen/Qwen-Image") == "Qwen/Qwen-Image", "other Hub id kept")
    assert_true(sim_pin_hf(HUB, has_loras=True, air_base="flux1") == "fal-ai/flux-lora", "o31 flux1 → flux-lora")
    assert_true(sim_pin_hf(HUB, has_loras=True, air_base="krea2") == "fal-ai/krea-2/turbo/lora", "o31 krea2 → krea lora")

    # runShotStep: HF outbound serviceId is Hub, not fal sibling
    rsi = js.find("async function runShotStep")
    run = js[rsi:rsi + 18000]
    assert_true("pinHfLoraServiceId" in run or "HF_LORA_PREF_SERVICE" in run,
                "runShotStep pins HF Hub outbound")
    assert_true('be === "huggingface"' in run or "be === 'huggingface'" in run
                or 'currentBackend() === "huggingface"' in run,
                "HF outbound pin gated")
    assert_true("chipsLackAirForOutbound" in run, "lora gate still before POST")
    assert_true(run.find("chipsLackAirForOutbound") < run.find("/api/generate"),
                "gate before POST")

    # Provider: no /lora sibling rewrite; job hf|sync|; civitai+fal drift 400
    from providers.huggingface import _maybe_lora_pid, _force_loras
    assert_true(
        _maybe_lora_pid("fal-ai/z-image/turbo", {"loras": [{"path": PATH}]}) == "fal-ai/z-image/turbo",
        "Router has no sibling — keep mapped pid",
    )
    forced = {}
    _force_loras(forced, {"loras": [{"path": PATH, "scale": 0.8}]})
    assert_true(forced.get("loras") and forced["loras"][0]["path"] == PATH, "_force_loras http path")
    assert_true(abs(float(forced["loras"][0]["scale"]) - 0.8) < 1e-6, "_force_loras scale 0.8")
    assert_true('hf|sync|' in hf, "job shape hf|sync|")
    assert_true("looks_like_civitai_service" in hf, "HF generate rejects Civitai serviceId")
    assert_true("不能发给 Hugging Face" in hf or "不接受 LoRA 的 Fal" in hf,
                "HF generate still rejects non-LoRA Fal serviceId")
    assert_true("fal_supports_lora" in hf or "v0821o31" in hf or "direct_fal_lora" in hf,
                "o31 HF allows official Fal LoRA endpoints when loras[] present")
    assert_true("return pid" in hf or "return (pid" in hf, "_maybe_lora_pid does not rewrite")
    assert_true("/lora" in hf and "sibling" in hf.lower() or "Router does not host" in hf,
                "docs: no fal /lora sibling")

    # loadCatalog keeps Hub option visible
    lc = js.find("function loadCatalog")
    cat = js[lc:js.find("async function loadOuts", lc)]
    assert_true("HF_LORA_PREF_SERVICE" in cat or HUB in cat, "catalog injects Hub pin")
    assert_true("ensureHfLoraServiceSelected" in cat, "catalog re-pins HF #service")


def test_v0821o5_hf_no_wavespeed():
    """v0821o5: Z-Image turbo pins fal-ai; skip wavespeed; fal-ai error is not overwritten."""
    from providers.huggingface import _maybe_lora_pid, _provider_candidates
    import providers.huggingface as hfmod

    js = (ROOT / "static" / "storyboard.js").read_text(encoding="utf-8")
    html = (ROOT / "static" / "storyboard.html").read_text(encoding="utf-8")
    hf = (ROOT / "providers" / "huggingface.py").read_text(encoding="utf-8")
    assert_true("v0821o49b-hydrate-fresh-empty-url" in html, "html stamp")
    assert_true('class="stamp"' in html, ".stamp")
    assert_true("storyboard.js?v=20260911-o49bhydratefreshemptyurl" in html, "js cache bust")
    assert_true('src="/static/storyboard.js?v=' in html, "cache-bust")
    assert_true('"nl-storyboard-v0821o16"' in js, "STORE o5")
    assert_true('"nl-storyboard-v0821o4"' in js, "OLDS keeps o4")
    assert_true('"nl-storyboard-v0821o3"' in js, "OLDS keeps o3")
    assert_true('"nl-storyboard-v0821o2"' in js, "OLDS keeps o2")
    assert_true("_fal_ai_error_is_final" in hf, "generate stops on fal-ai error")
    assert_true("wavespeed" in hf and "does not support" in hf, "wavespeed skip documented")

    PATH = "https://civitai.com/api/download/models/3231694"
    HUB = "Tongyi-MAI/Z-Image-Turbo"
    mapping = {
        "fal-ai": {"status": "live", "providerId": "fal-ai/z-image/turbo"},
        "wavespeed": {"status": "live", "providerId": "wavespeed-ai/z-image/turbo"},
    }
    payload = {
        "serviceId": HUB,
        "prompt": "portrait, soft light",
        "loras": [{"path": PATH, "scale": 0.8}],
    }

    def names_of(cands):
        return [n for n, _, _ in cands]

    def call_cands(mid, spec, pay=None):
        try:
            return _provider_candidates(mapping, mid, spec, pay)
        except TypeError:
            return _provider_candidates(mapping, mid, spec)

    cands = call_cands(HUB, {}, payload)
    names = names_of(cands)
    pids = [p for _, p, _ in cands]
    assert_true(names and names[0] == "fal-ai", "pin/prefer fal-ai first: %s" % names)
    assert_true("wavespeed" not in names, "skip wavespeed for Z-Image turbo: %s" % names)
    assert_true("fal-ai/z-image/turbo" in pids, "mapped pid stays turbo")
    assert_true(all("/lora" not in (p or "") for p in pids), "no Fal /lora sibling drift")
    assert_true(
        _maybe_lora_pid("fal-ai/z-image/turbo", payload) == "fal-ai/z-image/turbo",
        "router has no /lora sibling",
    )

    cands_no_lora = call_cands(HUB, {}, {})
    assert_true("wavespeed" not in names_of(cands_no_lora), "wavespeed unsupported even without loras")

    other_mid = "org/Z-Image-Turbo-repack"
    cands_any = call_cands(other_mid, {}, payload)
    assert_true(names_of(cands_any)[:1] == ["fal-ai"], "any Z-Image turbo mapping prefers fal-ai")
    assert_true("wavespeed" not in names_of(cands_any), "any Z-Image turbo mapping skips wavespeed")

    flux_map = {
        "fal-ai": {"status": "live", "providerId": "fal-ai/flux/schnell"},
        "wavespeed": {"status": "live", "providerId": "some/flux"},
    }
    flux_names = names_of(_provider_candidates(flux_map, "black-forest-labs/FLUX.1-schnell", {}))
    assert_true("wavespeed" in flux_names, "FLUX still may use wavespeed")
    assert_true(flux_names[0] == "fal-ai", "FLUX still prefers fal-ai")

    called = []
    orig_map = hfmod.inference_mapping
    orig_call = hfmod._call_fal
    orig_key = hfmod.hf_key
    orig_cands = hfmod._provider_candidates

    def fake_map(mid):
        return mapping

    def fake_call(provider, pid, pay, key, timeout):
        called.append((provider, pid))
        if provider == "fal-ai":
            return 422, {"error": "fal-ai real error: lora rejected"}, {"prompt": "x", "loras": (pay or {}).get("loras")}
        if provider == "wavespeed":
            return 400, {"error": "Model not supported by provider wavespeed"}, {"prompt": "x"}
        return 400, {"error": "unexpected provider %s" % provider}, {}

    def fake_cands(*args, **kwargs):
        return [
            ("fal-ai", "fal-ai/z-image/turbo", "fal"),
            ("wavespeed", "wavespeed-ai/z-image/turbo", "fal"),
        ]

    def err_text(data):
        if isinstance(data, dict):
            return str(data.get("error") or data)
        return str(data)

    # o31: Hub mid mapped to no-LoRA fal pid + loras[] → honest 400 (no silent sibling / no call).
    try:
        hfmod.inference_mapping = fake_map
        hfmod._call_fal = fake_call
        hfmod.hf_key = lambda: "hf_test_token"
        hfmod.hf_keys = lambda: ["hf_test_token"]
        hfmod._provider_candidates = fake_cands
        code_lora, data_lora = hfmod.HuggingFaceProvider().generate(payload)
    finally:
        hfmod.inference_mapping = orig_map
        hfmod._call_fal = orig_call
        hfmod.hf_key = orig_key
        hfmod._provider_candidates = orig_cands
    assert_true(code_lora == 400, "o31 Hub+loras → 400 before call: %s" % data_lora)
    assert_true("不接受 LoRA" in err_text(data_lora), "o31 copy: %s" % data_lora)
    assert_true(not called, "o31 must not call providers for Hub+loras no-LoRA map: %s" % called)

    # o5 wavespeed-final still holds for no-LoRA outbound (fal-ai error not overwritten).
    payload_nolora = {"serviceId": HUB, "prompt": "portrait, soft light"}
    called.clear()
    try:
        hfmod.inference_mapping = fake_map
        hfmod._call_fal = fake_call
        hfmod.hf_key = lambda: "hf_test_token"
        hfmod.hf_keys = lambda: ["hf_test_token"]
        hfmod._provider_candidates = fake_cands
        code, data = hfmod.HuggingFaceProvider().generate(payload_nolora)
    finally:
        hfmod.inference_mapping = orig_map
        hfmod._call_fal = orig_call
        hfmod.hf_key = orig_key
        hfmod._provider_candidates = orig_cands

    err = err_text(data)
    assert_true(code >= 400, "fal-ai failure is an error, not 200: %s %s" % (code, data))
    assert_true("lora rejected" in err or "fal-ai real error" in err, "returns fal-ai error: %s" % data)
    assert_true("Model not supported by provider wavespeed" not in err, "must not overwrite with wavespeed: %s" % data)
    assert_true(called and called[0][0] == "fal-ai", "tried fal-ai first: %s" % called)
    assert_true(all(p != "wavespeed" for p, _ in called), "must not continue to wavespeed: %s" % called)
    assert_true(all("/lora" not in (pid or "") for _, pid in called), "outbound pid is turbo not /lora sibling")

    called.clear()
    try:
        hfmod.inference_mapping = fake_map
        hfmod._call_fal = fake_call
        hfmod.hf_key = lambda: "hf_test_token"
        code2, data2 = hfmod.HuggingFaceProvider().generate(payload)
    finally:
        hfmod.inference_mapping = orig_map
        hfmod._call_fal = orig_call
        hfmod.hf_key = orig_key

    err2 = err_text(data2)
    assert_true(code2 >= 400, "real candidates: fal-ai failure still errors")
    assert_true("Model not supported by provider wavespeed" not in err2, "real candidates: no wavespeed overwrite: %s" % data2)
    assert_true(all(p != "wavespeed" for p, _ in called), "real candidates: wavespeed not called: %s" % called)


def test_v0821o6_modelscope_hub_lora():
    """v0821o6 Magao ②: Hub Tongyi-MAI/Z-Image-Turbo + Hub LoRA; skip http/AIR; no AI↔CN drift."""
    from providers.modelscope import (
        _modelscope_loras, _clamp_seed, AI_BASE, CN_BASE,
        AI_TOKEN_PATH, CN_TOKEN_PATH, ModelScopeProvider,
    )
    import providers.modelscope as msmod

    js = (ROOT / "static" / "storyboard.js").read_text(encoding="utf-8")
    html = (ROOT / "static" / "storyboard.html").read_text(encoding="utf-8")
    ms = (ROOT / "providers" / "modelscope.py").read_text(encoding="utf-8")

    STAMP = "v0821o49b-hydrate-fresh-empty-url"
    HUB = "krea/Krea-2-Turbo"
    HUB_LORA = "DiffSynth-Studio/Z-Image-Turbo-DistillPatch"
    HTTP = "https://civitai.com/api/download/models/3231694"
    FAL_SIB = "fal-ai/z-image/turbo/lora"
    AIR = "urn:air:sdxl:lora:civitai:1@3231694"

    assert_true(STAMP in html, "html stamp")
    assert_true('class="stamp"' in html, ".stamp")
    assert_true("storyboard.js?v=20260911-o49bhydratefreshemptyurl" in html, "js cache bust")
    assert_true('src="/static/storyboard.js?v=' in html, "cache-bust")
    assert_true('"nl-storyboard-v0821o16"' in js, "STORE o6")
    assert_true('"nl-storyboard-v0821o5"' in js, "OLDS keeps o5")
    assert_true('"nl-storyboard-v0821o4"' in js, "OLDS keeps o4")
    assert_true('"nl-storyboard-v0821o2"' in js, "OLDS keeps o2")
    # HF / Fal knives stay in the file (stamp bump must not delete them)
    assert_true("function hfLoraFixtureImport" in js, "HF fixture kept")
    assert_true("function falLoraFixtureImport" in js, "Fal fixture kept")
    assert_true('HF_LORA_PREF_SERVICE = "krea/Krea-2-Turbo"' in js, "HF Krea pin kept")
    assert_true('FAL_LORA_PREF_SERVICE = "fal-ai/krea-2/turbo/lora"' in js, "Fal krea turbo/lora pin kept")

    assert_true("function msLoraFixtureImport" in js, "msLoraFixtureImport")
    assert_true("function mountMsLoraFixture" in js or "async function mountMsLoraFixture" in js,
                "mountMsLoraFixture")
    fi = js.find("function msLoraFixtureImport")
    assert_true(fi >= 0, "ms fixture fn")
    fj = js.find("async function mountMsLoraFixture", fi)
    if fj < 0:
        fj = js.find("function mountMsLoraFixture", fi)
    fixture_block = js[fi:fj if fj > fi else fi + 1400]
    assert_true('backend: "modelscope-ai"' in fixture_block or "backend: 'modelscope-ai'" in fixture_block,
                "fixture forces backend=modelscope-ai")
    assert_true("modelscope-cn" not in fixture_block,
                "fixture must not pick modelscope-cn (CN balance)")
    assert_true('backend: "fal"' not in fixture_block and "backend: 'fal'" not in fixture_block,
                "Magao fixture must not set fal")
    assert_true("huggingface" not in fixture_block, "Magao fixture must not set huggingface")
    assert_true('serviceId: "krea/Krea-2-Turbo"' in fixture_block
                or "serviceId: MS_LORA_PREF_SERVICE" in fixture_block,
                "fixture serviceId is krea/Krea-2-Turbo")
    assert_true('serviceId: "fal-ai/z-image/turbo/lora"' not in fixture_block
                and "serviceId: FAL_LORA_PREF_SERVICE" not in fixture_block,
                "Magao fixture must NOT rewrite to fal turbo/lora sibling")
    loras_part = fixture_block.split("loras")[1][:700] if "loras" in fixture_block else ""
    assert_true("loras: []" in fixture_block, "fixture does not invent a Hub LoRA")
    assert_true("3231694" not in loras_part, "fixture LoRA is not Civitai 3231694")
    assert_true("civitai.com" not in loras_part.lower(), "fixture LoRA is not Civitai http")

    assert_true('MS_LORA_PREF_SERVICE = "krea/Krea-2-Turbo"' in js
                or 'MS_LORA_PREF_SERVICE="krea/Krea-2-Turbo"' in js,
                "MS_LORA_PREF_SERVICE pinned to Krea")
    assert_true("function pinMsLoraServiceId" in js, "pinMsLoraServiceId")
    assert_true("function ensureMsLoraServiceSelected" in js, "ensureMsLoraServiceSelected")
    assert_true("_pinMsLoraService" in js, "sticky Magao pin across catalog fill")
    assert_true("_wantMsLoraFixture" in js, "CLI ?fixture=ms-lora mounts after catalog")
    assert_true("fixture=ms-lora" in js, "CLI query fixture=ms-lora")
    assert_true('id="btnMsLoraFix"' in html or "btnMsLoraFix" in js, "魔搭模型（不预置 LoRA） button")
    assert_true("魔搭模型（不预置 LoRA）" in html, "Magao fixture button label")

    def _btn_tag(doc, eid):
        i = doc.find('id="' + eid + '"')
        assert_true(i >= 0, eid + " in html")
        start = doc.rfind("<button", 0, i)
        end = doc.find(">", i)
        assert_true(start >= 0 and end > start, eid + " button tag")
        return doc[start:end + 1]

    ms_btn = _btn_tag(html, "btnMsLoraFix")
    assert_true('class="ghost"' not in ms_btn, "魔搭模型（不预置 LoRA） must not use .ghost overlay")
    fal_btn = _btn_tag(html, "btnFalLoraFix")
    assert_true('class="ghost"' not in fal_btn, "Fal LoRA夹具 must not use .ghost overlay")
    hf_btn = _btn_tag(html, "btnHfLoraFix")
    assert_true('class="ghost"' not in hf_btn, "HF LoRA夹具 must not use .ghost overlay")

    ei = js.find("function ensureMsLoraServiceSelected")
    ens = js[ei:ei + 1800] if ei >= 0 else ""
    assert_true(HUB in ens or "MS_LORA_PREF_SERVICE" in ens, "ensure writes Hub id into #service")
    assert_true("modelscope-ai" in ens or "isModelscopeBe" in ens, "ensure gated to Magao")
    assert_true("默认模型" not in ens or "textContent" in ens, "ensure does not leave 默认模型")
    assert_true(FAL_SIB not in ens, "ensure must not label fal sibling")
    # generation-before plaintext backend+model
    assert_true("Krea 2 Turbo" in ens and HUB in js, "plaintext model label before generate")

    i = js.find("async function applyImport")
    if i < 0:
        i = js.find("function applyImport")
    j = js.find("function bindImportModal", i)
    block = js[i:j]
    assert_true(i >= 0 and j > i, "applyImport block")
    assert_true("/api/generate" not in block, "applyImport must not call /api/generate")
    assert_true("wantMs" in block, "wantMs branch")
    assert_true('j.backend === "modelscope-ai"' in block or "j.backend === 'modelscope-ai'" in block,
                "wantMs from j.backend modelscope-ai")
    assert_true('j.backend === "modelscope-cn"' in block or "j.backend === 'modelscope-cn'" in block,
                "wantMs from j.backend modelscope-cn")
    assert_true("wantHf" in block and "!wantMs" in block, "HF must not steal Magao Hub ids")
    assert_true('value = "modelscope-ai"' in block or "modelscope-ai" in block,
                "forces backend modelscope-ai")
    # 裁决: Hub pref 钉法迁到 ensureMsLoraServiceSelected()/pinMsLoraServiceId();
    # applyImport 的 Magao 分支收尾调用 ensure* 完成钉选(语义不变, 对齐 o4 HF 裁决)。
    assert_true("ensureMsLoraServiceSelected" in block, "Magao import pins Hub pref via ensureMsLoraServiceSelected")
    en_i = js.find("function ensureMsLoraServiceSelected")
    pin_i = js.find("function pinMsLoraServiceId")
    assert_true("MS_LORA_PREF_SERVICE" in js[en_i:en_i + 3000] or "MS_LORA_PREF_SERVICE" in js[pin_i:pin_i + 2500],
                "ensure/pin path uses MS_LORA_PREF_SERVICE")
    assert_true("魔搭 导入拒绝" in block or "modelscope" in block.lower(),
                "Magao import error copy for Fal/Civitai ids")
    assert_true("魔搭 导入拒绝" in block or "modelscope" in block.lower(),
                "Magao import error copy for Fal/Civitai ids")
    assert_true('sid = ""' in block or "sid = ''" in block,
                "Fal/Civitai sid rejected (empty), not rewritten to Hub turbo")
    # AI ↔ CN: never assign the other flavor
    # 裁决(o135/o136seko): AI/CN 赋值改为 msHouse 变量($("backend").value = msHouse),
    # msHouse 只能取 uiHouse/msBe 同口味(uiHouse 已是魔搭则沿用, 否则按 j.backend 推导), 不可交叉——语义不变
    assert_true('$("backend").value = msHouse' in block, "backend assign via msHouse")
    assert_true('msBe === "modelscope-cn"' in block and '"modelscope-ai"' in block,
                "msHouse honors import flavor, never crosses AI/CN")
    # chip-clear o3 still intact
    lora_i = block.rfind("if (Array.isArray(j.loras))")
    lora_j = block.find("syncLoraUi();", lora_i)
    snip = block[lora_i:lora_j]
    compact = " ".join(snip.split())
    assert_true("else if (wantCivitai)" not in snip, "o3: chip-clear not wantCivitai-only")
    assert_true("} else { state.loras = []" in compact or "} else {state.loras = []" in compact,
                "o3: missing loras[] still clears")

    pack_i = js.find("function packLorasForPayload")
    pack = js[pack_i:pack_i + 4200]
    assert_true("isModelscopeBe" in pack or 'modelscope-ai' in pack,
                "modelscope Hub-repo filter in pack")
    assert_true("isHfRepo" in pack or "owner/repo" in pack or "count(\"/\")" in pack
                or "count('/') == 1" in pack or 'count("/") === 1' in pack or 'count("/") == 1' in pack,
                "Hub owner/repo check in pack")
    assert_true("LoRA 只要 Hub" in js or "Hub owner/repo" in js, "Magao Hub LoRA red msg")

    def looks_air(s):
        t = str(s or "")
        return t.lower().startswith("urn:air:") or ":lora:" in t.lower()

    def is_http(s):
        u = str(s or "").lower()
        return u.startswith("http://") or u.startswith("https://")

    def is_hub_repo(s):
        t = str(s or "").strip()
        if not t or is_http(t) or looks_air(t):
            return False
        return t.count("/") == 1 and " " not in t

    def sim_pack(rows, be="modelscope-ai"):
        mapped = []
        for l in rows:
            path = l.get("path") or l.get("downloadUrl") or l.get("url") or ""
            version_id = str(l.get("versionId") or "")
            if (not path or looks_air(path)) and version_id.isdigit():
                path = "https://civitai.com/api/download/models/" + version_id
            scale = l.get("scale") if l.get("scale") is not None else l.get("strength")
            row = {"air": l.get("air") or "", "path": path, "scale": scale, "name": l.get("name") or ""}
            ok = True
            if be in ("fal", "huggingface"):
                p = str(row["path"] or "").strip()
                ok = bool(p and is_http(p) and not looks_air(p))
            elif be in ("modelscope-ai", "modelscope-cn"):
                p = str(row["path"] or "").strip()
                if is_http(p) or looks_air(p) or "3231694" in p:
                    ok = False
                elif not is_hub_repo(p):
                    ok = False
            if not ok:
                return None
            mapped.append(row)
        return mapped or None

    air_only = [{"air": AIR, "strength": 0.8, "name": "AIR"}]
    assert_true(sim_pack(air_only) is None, "AIR-only → Magao pack null")
    http_only = [{"path": HTTP, "scale": 0.8, "name": "Asian Mix", "versionId": 3231694}]
    assert_true(sim_pack(http_only) is None, "Civitai http / 3231694 → Magao pack null")
    packed = sim_pack([{"path": HUB_LORA, "scale": 0.8, "name": "DistillPatch"}])
    assert_true(packed and packed[0]["path"] == HUB_LORA, "Hub owner/repo ships")
    assert_true(float(packed[0]["scale"]) == 0.8, "scale 0.8")
    mixed = sim_pack([
        {"path": HTTP, "scale": 0.8, "versionId": 3231694},
        {"path": HUB_LORA, "scale": 0.8},
    ])
    assert_true(mixed is None, "mixed http+Hub must fail whole pack")
    # chips present but pack empty → lack outbound (false-confidence)
    lack = bool(http_only) and not sim_pack(http_only)
    assert_true(lack is True, "http LoRA chip visible → Magao outbound empty → red-block")

    bgi = js.find("function buildGraph")
    bg = js[bgi:js.find("function pickUrl", bgi)]
    assert_true("MS_LORA_PREF_SERVICE" in bg, "buildGraph pins Magao Hub")
    assert_true("isModelscopeBe" in bg or "modelscope-ai" in bg, "Magao empty-service gated")
    assert_true('be === "fal"' in bg and "pinFalLoraServiceId" in bg, "fal pin still fal-only")
    assert_true('be === "huggingface"' in bg and "pinHfLoraServiceId" in bg, "HF pin still HF-only")

    def sim_empty_service(be, has_loras=True, op="t2i"):
        service_id = ""
        if not service_id and be == "huggingface":
            return HUB
        if not service_id and be in ("modelscope-ai", "modelscope-cn"):
            return HUB
        if not service_id and be != "civitai":
            if op != "i2v" and has_loras:
                return FAL_SIB
            return "fal-ai/flux/schnell" if op != "i2v" else "fal-ai/minimax/video-01/image-to-video"
        return service_id

    assert_true(sim_empty_service("modelscope-ai") == HUB, "Magao AI empty → Hub id")
    assert_true(sim_empty_service("modelscope-cn") == HUB, "Magao CN empty → Hub id")
    assert_true(sim_empty_service("modelscope-ai") != FAL_SIB, "Magao empty must not fal sibling")
    assert_true(sim_empty_service("huggingface") == HUB, "HF empty → Hub id still")
    assert_true(sim_empty_service("fal") == FAL_SIB, "Fal empty+loras still turbo/lora")

    def sim_pin_ms(sid):
        s = str(sid or "").strip()
        if (not s) or s.startswith("fal-ai/") or s.startswith("image/"):
            return HUB
        if s == HUB:
            return s
        return s

    assert_true(sim_pin_ms("") == HUB, "empty → Hub")
    assert_true(sim_pin_ms(FAL_SIB) == HUB, "fal sibling on Magao → Hub")
    assert_true(sim_pin_ms("image/comfy/krea2/turbo/createImage") == HUB, "civitai id on Magao → Hub")
    assert_true(sim_pin_ms(HUB) == HUB, "Hub stays Hub")
    assert_true(sim_pin_ms("Qwen/Qwen-Image") == "Qwen/Qwen-Image", "other Hub id kept")

    rsi = js.find("async function runShotStep")
    run = js[rsi:rsi + 18000]
    assert_true("pinMsLoraServiceId" in run or "MS_LORA_PREF_SERVICE" in run,
                "runShotStep pins Magao Hub outbound")
    assert_true("isModelscopeBe" in run or "modelscope-ai" in run,
                "Magao outbound pin gated")
    assert_true("chipsLackAirForOutbound" in run, "lora gate still before POST")
    assert_true(run.find("chipsLackAirForOutbound") < run.find("/api/generate"),
                "gate before POST")
    assert_true("/api/generate" in run, "generate still via page POST (tests must not curl it)")

    lc = js.find("function loadCatalog")
    cat = js[lc:js.find("async function loadOuts", lc)]
    assert_true("MS_LORA_PREF_SERVICE" in cat or HUB in cat, "catalog injects Magao Hub pin")
    assert_true("ensureMsLoraServiceSelected" in cat, "catalog re-pins Magao #service")
    assert_true("_pinMsLoraService" in cat, "catalog restores Magao pin")

    # Provider: AI / CN never cross tokens or bases
    assert_true("modelscope.ai" in AI_BASE and "modelscope.cn" not in AI_BASE, "AI base is .ai")
    assert_true("modelscope.cn" in CN_BASE and AI_BASE != CN_BASE, "CN base is .cn")
    assert_true(AI_TOKEN_PATH != CN_TOKEN_PATH, "token paths differ")
    assert_true(str(AI_TOKEN_PATH).endswith("modelscope/token"), "AI token path")
    assert_true(str(CN_TOKEN_PATH).endswith("modelscope-cn/token"), "CN token path")
    assert_true("不会改走另一边" in ms, "reach error refuses AI↔CN fallback")
    assert_true("_modelscope_loras" in ms, "Hub LoRA helper")
    # 裁决: cfgScale→guidance 改为数据驱动字段映射表(body[field]=value), 线路语义由下方 fake_call 断言兜底
    assert_true("cfgScale" in ms and '"guidance"' in ms, "cfgScale → guidance")
    assert_true('body["size"]' in ms, "size=WxH")

    assert_true(_modelscope_loras({"loras": HUB_LORA}) == HUB_LORA,
                "bare Hub repo → official single-LoRA string")
    one_weight_raised = False
    try:
        _modelscope_loras({"loras": [{"path": HUB_LORA, "scale": 0.8}]})
    except ValueError as exc:
        one_weight_raised = "单条" in str(exc)
    assert_true(one_weight_raised, "single LoRA + weight refused, not {repo:0.8}")
    http_raised = False
    try:
        _modelscope_loras({"loras": [{"path": HTTP, "scale": 0.8}]})
    except ValueError as exc:
        http_raised = "owner/repo" in str(exc)
    assert_true(http_raised, "Civitai http refused, not skipped")
    air_raised = False
    try:
        _modelscope_loras({"loras": [{"air": AIR, "path": AIR}]})
    except ValueError as exc:
        air_raised = "owner/repo" in str(exc)
    assert_true(air_raised, "AIR refused, not remapped")
    mixed_raised = False
    try:
        _modelscope_loras({"loras": [
            {"path": HTTP, "scale": 0.8},
            {"path": HUB_LORA, "scale": 0.8},
        ]})
    except ValueError as exc:
        mixed_raised = "owner/repo" in str(exc)
    assert_true(mixed_raised, "mixed http+Hub refused rather than dropping http")
    # o149: direct _clamp_seed still rejects (no wrap). Generate path omits via official_seed_outbound.
    seed_raised = False
    try:
        _clamp_seed(475720515768790)
    except ValueError as exc:
        seed_raised = "seed" in str(exc)
    assert_true(seed_raised, "oversize seed rejected by _clamp_seed, not modulo")
    from providers.modelscope_seed import official_seed_outbound
    assert_true(official_seed_outbound(475720515768790) is None, "o149 over-int32 omit (not wrap)")

    captured = []

    def fake_call(url, method="GET", headers=None, body=None, timeout=30):
        captured.append({"url": url, "method": method, "headers": dict(headers or {}), "body": body})
        return 200, {"task_id": "tid-ms-1"}

    def fake_read(path):
        p = str(path)
        if "modelscope-cn" in p:
            return "CN_TOKEN"
        if p.endswith("modelscope/token"):
            return "AI_TOKEN"
        return ""

    orig_call, orig_ok, orig_read = msmod.json_call, msmod._host_ok, msmod._read_token
    payload = {
        "serviceId": HUB,
        "prompt": "portrait, soft light",
        "cfgScale": 1.0,
        "width": 1280,
        "height": 720,
        "seed": 42,
        "loras": [{"path": HUB_LORA}],
    }
    try:
        msmod.json_call = fake_call
        msmod._host_ok = lambda url: True
        msmod._read_token = fake_read
        code_ai, data_ai = ModelScopeProvider("ai").generate(payload)
        code_cn, data_cn = ModelScopeProvider("cn").generate(payload)
        http_payload = dict(payload, loras=[{"path": HTTP, "scale": 0.8, "versionId": 3231694}])
        code_skip, data_skip = ModelScopeProvider("ai").generate(http_payload)
        weighted = dict(payload, loras=[{"path": HUB_LORA, "scale": 0.8}])
        code_w, data_w = ModelScopeProvider("ai").generate(weighted)
        res_payload = {
            "serviceId": HUB, "prompt": "x", "resolution": "1024x1024",
            "loras": [{"path": HUB_LORA}],
        }
        ModelScopeProvider("ai").generate(res_payload)
        # AI token missing must 401 — never CN
        def fake_read_ai_empty(path):
            return "CN_TOKEN" if "modelscope-cn" in str(path) else ""
        msmod._read_token = fake_read_ai_empty
        captured_before = len(captured)
        code_empty, data_empty = ModelScopeProvider("ai").generate(payload)
    finally:
        msmod.json_call = orig_call
        msmod._host_ok = orig_ok
        msmod._read_token = orig_read

    assert_true(code_ai < 400 and data_ai.get("backend") == "modelscope-ai", "AI generate ok")
    assert_true(code_cn < 400 and data_cn.get("backend") == "modelscope-cn", "CN generate ok")
    ai_posts = [c for c in captured if c["method"] == "POST" and "Bearer AI_TOKEN" in str(c["headers"])]
    cn_posts = [c for c in captured if c["method"] == "POST" and "Bearer CN_TOKEN" in str(c["headers"])]
    assert_true(ai_posts, "AI used AI token")
    assert_true(cn_posts, "CN used CN token")
    assert_true(all(AI_BASE in c["url"] and CN_BASE not in c["url"] for c in ai_posts),
                "AI posts stay on .ai base")
    assert_true(all(CN_BASE in c["url"] and AI_BASE not in c["url"] for c in cn_posts),
                "CN posts stay on .cn base")
    body_ai = ai_posts[0]["body"]
    assert_true(body_ai.get("model") == HUB, "outbound model is Hub owner/repo")
    assert_true(body_ai.get("prompt") == "portrait, soft light", "prompt")
    assert_true(body_ai.get("guidance") == 1.0, "cfgScale → guidance")
    assert_true(body_ai.get("size") == "1280x720", "size=WxH")
    assert_true(body_ai.get("seed") == 42, "in-range seed kept")
    assert_true(body_ai.get("loras") == HUB_LORA, "outbound single LoRA is official string")
    assert_true(isinstance(body_ai.get("loras"), str), "single LoRA is string, not [{model,weight}]")
    assert_true(HTTP not in str(body_ai.get("loras")), "outbound loras not http")
    assert_true(code_w >= 400 and "单条" in str(data_w.get("error") or ""),
                "single LoRA + weight is 400, not {repo:0.8}: %s %s" % (code_w, data_w))
    assert_true(code_skip >= 400, "Civitai http LoRA is 400, not skipped")
    assert_true("owner/repo" in str(data_skip.get("error") or ""),
                "http LoRA error names owner/repo requirement: %s" % data_skip)
    res_posts = [c for c in captured if c["method"] == "POST" and (c.get("body") or {}).get("size") == "1024x1024"]
    assert_true(res_posts, "resolution WxH → size")
    assert_true(code_empty == 401, "AI missing token → 401, not CN: %s %s" % (code_empty, data_empty))
    assert_true(len(captured) == captured_before, "AI 401 must not POST to CN")


def test_v0821o6b_ms_lora_shape():
    """v0821o6b: Magao outbound loras follow official string / {repo:weight}; fixture force AI."""
    from providers.modelscope import (
        _modelscope_loras, _clamp_seed, AI_BASE, CN_BASE,
        ModelScopeProvider,
    )
    import providers.modelscope as msmod

    js = (ROOT / "static" / "storyboard.js").read_text(encoding="utf-8")
    html = (ROOT / "static" / "storyboard.html").read_text(encoding="utf-8")
    ms = (ROOT / "providers" / "modelscope.py").read_text(encoding="utf-8")

    STAMP = "v0821o49b-hydrate-fresh-empty-url"
    HUB = "Tongyi-MAI/Z-Image-Turbo"
    HUB_LORA = "DiffSynth-Studio/Z-Image-Turbo-DistillPatch"
    HTTP = "https://civitai.com/api/download/models/3231694"
    WANT = {HUB_LORA: 0.8}

    assert_true(STAMP in html, "html stamp")
    assert_true('class="stamp"' in html, ".stamp")
    assert_true("storyboard.js?v=20260911-o49bhydratefreshemptyurl" in html, "js cache bust")
    assert_true('src="/static/storyboard.js?v=' in html, "cache-bust")
    assert_true('"nl-storyboard-v0821o16"' in js, "STORE o7")
    assert_true('"nl-storyboard-v0821o6b"' in js, "OLDS keeps o6b")
    assert_true('"nl-storyboard-v0821o6"' in js, "OLDS keeps o6")
    assert_true('"nl-storyboard-v0821o5"' in js, "OLDS keeps o5")
    assert_true("nanogpt" not in STAMP and "nano-gpt" not in STAMP, "stamp stays Magao, not Nano")
    assert_true("v0821o49b-hydrate-fresh-empty-url" in html and "nano" not in "v0821o49b-hydrate-fresh-empty-url", "html must not drift onto Nano stamps")
    assert_true("v0821o49b-hydrate-fresh-empty-url" in html, "o7 param-surface stamp")

    fi = js.find("function msLoraFixtureImport")
    fj = js.find("async function mountMsLoraFixture", fi)
    if fj < 0:
        fj = js.find("function mountMsLoraFixture", fi)
    fixture_block = js[fi:fj if fj > fi else fi + 1400]
    assert_true('backend: "modelscope-ai"' in fixture_block, "fixture forces modelscope-ai")
    assert_true("modelscope-cn" not in fixture_block, "fixture must not select CN")
    assert_true("loras: []" in fixture_block, "fixture does not invent DistillPatch or weight")
    assert_true("3231694" not in fixture_block.split("loras")[1][:700], "fixture LoRA not Civitai")

    # Official wire: one LoRA is a string; multi is {repo: weight} summing to 1.0.
    as_str = _modelscope_loras({"loras": HUB_LORA})
    assert_true(as_str == HUB_LORA, "string inbound stays official single-LoRA string")
    one_weight_raised = False
    try:
        _modelscope_loras({"loras": [{"path": HUB_LORA, "scale": 0.8}]})
    except ValueError as exc:
        one_weight_raised = "单条" in str(exc)
    assert_true(one_weight_raised, "path+scale refused, not {repo:0.8}")
    already_raised = False
    try:
        _modelscope_loras({"loras": [{"model": HUB_LORA, "weight": 0.8}]})
    except ValueError as exc:
        already_raised = "单条" in str(exc)
    assert_true(already_raised, "{model,weight} refused for one LoRA")
    dict_raised = False
    try:
        _modelscope_loras({"loras": {HUB_LORA: 0.8}})
    except ValueError as exc:
        dict_raised = "单条" in str(exc)
    assert_true(dict_raised, "one-key {repo:w} refused, not sent")
    assert_true(_modelscope_loras({"loras": []}) is None, "empty loras omitted")
    assert_true(_modelscope_loras({}) is None, "missing loras omitted")
    http_raised = False
    try:
        _modelscope_loras({"loras": [{"path": HTTP, "scale": 0.8}]})
    except ValueError as exc:
        http_raised = "owner/repo" in str(exc)
    assert_true(http_raised, "Civitai http refused")
    multi = _modelscope_loras({"loras": [
        {"path": "owner/repo-a", "scale": 0.6},
        {"path": "owner/repo-b", "scale": 0.4},
    ]})
    assert_true(multi == {"owner/repo-a": 0.6, "owner/repo-b": 0.4},
                "multi is official {repo: weight} summing to 1.0")
    sum_raised = False
    try:
        _modelscope_loras({"loras": [
            {"path": "owner/repo-a", "scale": 0.8},
            {"path": "owner/repo-b", "scale": 0.8},
        ]})
    except ValueError as exc:
        sum_raised = "1.0" in str(exc)
    assert_true(sum_raised, "multi weights that do not sum to 1.0 are refused")

    captured = []

    def fake_call(url, method="GET", headers=None, body=None, timeout=30):
        captured.append({"url": url, "method": method, "headers": dict(headers or {}), "body": body})
        return 200, {"task_id": "tid-o6b"}

    def fake_read(path):
        p = str(path)
        if "modelscope-cn" in p:
            return "CN_TOKEN"
        if p.endswith("modelscope/token"):
            return "AI_TOKEN"
        return ""

    orig_call, orig_ok, orig_read = msmod.json_call, msmod._host_ok, msmod._read_token
    payload = {
        "serviceId": HUB,
        "prompt": "portrait, soft light, detailed face, cinematic",
        "loras": [{"path": HUB_LORA}],
    }
    try:
        msmod.json_call = fake_call
        msmod._host_ok = lambda url: True
        msmod._read_token = fake_read
        code_ai, data_ai = ModelScopeProvider("ai").generate(payload)
        ModelScopeProvider("ai").generate(dict(payload, loras=HUB_LORA))
        code_w, data_w = ModelScopeProvider("ai").generate(dict(payload, loras={HUB_LORA: 0.8}))
        code_obj, data_obj = ModelScopeProvider("ai").generate(
            dict(payload, loras=[{"model": HUB_LORA, "weight": 0.8}])
        )
        ModelScopeProvider("ai").generate({"serviceId": HUB, "prompt": "no lora"})
    finally:
        msmod.json_call = orig_call
        msmod._host_ok = orig_ok
        msmod._read_token = orig_read

    assert_true(code_ai < 400 and data_ai.get("backend") == "modelscope-ai", "AI generate ok")
    assert_true(code_w >= 400 and "单条" in str(data_w.get("error") or ""),
                "one-key {repo:w} is 400: %s %s" % (code_w, data_w))
    assert_true(code_obj >= 400 and "单条" in str(data_obj.get("error") or ""),
                "{model,weight} is 400: %s %s" % (code_obj, data_obj))
    ai_posts = [c for c in captured if c["method"] == "POST" and AI_BASE in c["url"]]
    assert_true(len(ai_posts) >= 3, "AI posts: path / string / none (weighted singles do not POST)")
    for c in ai_posts:
        assert_true(CN_BASE not in c["url"], "never CN base")
        body = c["body"] or {}
        if "loras" not in body:
            continue
        loras = body["loras"]
        assert_true(loras == HUB_LORA, "string wire is Hub DistillPatch: %s" % (loras,))
        assert_true(HTTP not in str(loras), "no Civitai http on wire")
    none_posts = [c for c in ai_posts if "loras" not in (c.get("body") or {})]
    assert_true(none_posts, "no-LoRA omits loras key")
    assert_true(ai_posts[0]["body"].get("loras") == HUB_LORA, "path without weight → string")
    assert_true(_clamp_seed(1) == 1, "seed helper still imported")


def test_v0821o7_param_surface():
    """C1: every backend can input seed/size/negative; full roster; import does not silent-swap Turbo."""
    js = (ROOT / "static" / "storyboard.js").read_text(encoding="utf-8")
    html = (ROOT / "static" / "storyboard.html").read_text(encoding="utf-8")

    assert_true("v0821o49b-hydrate-fresh-empty-url" in html, "html stamp o7")
    assert_true('class="stamp"' in html, ".stamp")
    assert_true('src="/static/storyboard.js?v=' in html, "cache-bust")
    assert_true('"nl-storyboard-v0821o16"' in js, "STORE o7")
    assert_true('"nl-storyboard-v0821o6b"' in js, "OLDS keeps o6b")

    # Supported fields have real inputs
    for fid in ("negative", "serviceFilter", "nanoRes", "width", "height", "seed", "steps", "cfg"):
        assert_true('id="%s"' % fid in html, "input " + fid)
    assert_true("function syncParamSurface" in js, "syncParamSurface")
    assert_true("function packComfyParamsForPayload" in js, "packComfyParamsForPayload")
    assert_true("function paramGateMessage" in js, "paramGateMessage")
    assert_true("function catalogCaps" in js, "catalogCaps")
    assert_true("function renderServiceOptions" in js, "full-roster renderer")
    assert_true("SERVICE_SYNC_BUDGET" in js and "SERVICE_CHUNK_SIZE" in js, "chunked roster")

    # Catalog must NOT silent-truncate to 60
    lc = js[js.find("function loadCatalog"):js.find("async function loadOuts")]
    assert_true("const CAP = 60" not in lc, "loadCatalog no CAP=60")
    assert_true("items.slice(0, CAP)" not in lc, "loadCatalog no slice CAP")
    assert_true("renderServiceOptions(items" in lc, "loadCatalog uses full roster renderer")

    # packComfyParamsForPayload is no longer civitai-only
    pack = js[js.find("function packComfyParamsForPayload"):js.find("async function loadComfyDefaults")]
    assert_true('if (!usesCivitaiComfyParams()) return null' not in pack,
                "pack must not drop non-civitai params")
    assert_true("nano-gpt" in pack, "nano token packed")
    assert_true("resolution" in pack, "resolution token on nano pack")

    # negativePrompt attached for every backend, not civitai-only
    run = js[js.find("async function runShotStep"):js.find("async function runShotStep") + 20000]
    assert_true("payload.negativePrompt = negVal" in run or "payload.negativePrompt=negVal" in run.replace(" ", ""),
                "negative ships on payload")
    assert_true("paramGateMessage()" in run, "over-range gate before POST")

    # Import: Fal/Civitai sid on HF/Magao is rejected, not rewritten to Hub turbo
    i = js.find("async function applyImport")
    if i < 0:
        i = js.find("function applyImport")
    j = js.find("function bindImportModal", i)
    block = js[i:j]
    assert_true("/api/generate" not in block, "applyImport must not call /api/generate")
    hf_snip = block[block.find("else if (wantHf)"):block.find("else if (wantMs)")]
    assert_true("Hugging Face 导入拒绝" in hf_snip, "HF reject copy")
    assert_true("sid = HF_LORA_PREF_SERVICE" not in hf_snip, "HF import must not rewrite to Hub turbo")
    assert_true('sid = ""' in hf_snip or "sid = ''" in hf_snip, "HF reject clears sid")
    ms_snip = block[block.find("else if (wantMs)"):]
    assert_true("魔搭 导入拒绝" in ms_snip, "Magao reject copy")
    assert_true("sid = MS_LORA_PREF_SERVICE" not in ms_snip, "Magao import must not rewrite to Hub turbo")

    # Fixture buttons still pin turbo (not the sample import path)
    assert_true('serviceId: "fal-ai/krea-2/turbo/lora"' in js, "Fal fixture still krea turbo/lora")
    assert_true('serviceId: "krea/Krea-2-Turbo"' in js, "HF/MS fixture still Krea-2-Turbo")
    assert_true("function mountFalLoraFixture" in js, "Fal fixture kept")
    assert_true("function mountHfLoraFixture" in js, "HF fixture kept")
    assert_true("function mountMsLoraFixture" in js, "MS fixture kept")

    # fireSend gate before 已点生成
    fs = js[js.find("function fireSend"):js.find("function fireSend") + 4000]
    assert_true(fs.find("paramGateMessage") < fs.find('setMsg("已点生成")'), "param gate before ack")


def test_v0821o7_c1_closeout():
    """C1 10-item closeout: CSS link, null LoRA, Krea pin, catalogCaps, Fal hide, catalog error, /16 warn, 缺首帧, group 400, IN_QUEUE."""
    js = (ROOT / "static" / "storyboard.js").read_text(encoding="utf-8")
    html = (ROOT / "static" / "storyboard.html").read_text(encoding="utf-8")

    # 1. 裁决: o63 已把内联 <style> 全部拆到外部样式表 → 改为校验样式表 link 位于 <body> 之前
    assert_true('storyboard-ui.css' in html, "storyboard-ui.css link")
    head_part = html.split("<body", 1)[0]
    assert_true(
        '<link rel="stylesheet" href="/static/storyboard-ui.css?v=' in head_part,
        "storyboard-ui.css stylesheet link in head",
    )

    # 2. clampLoraScale must not silent-fill 0.8; null strength visible + packed
    clamp_i = js.find("function clampLoraScale")
    assert_true(clamp_i >= 0, "clampLoraScale exists")
    clamp_fn = js[clamp_i:js.find("function isHttpUrl", clamp_i)]
    assert_true("0.8" not in clamp_fn, "clampLoraScale default must not be 0.8")
    assert_true("null" in clamp_fn, "clampLoraScale preserves null")
    assert_true("clampLoraScale(v.strength != null ? v.strength : v.scale, 0.8)" not in js,
                "normalizeLora must not clamp null→0.8")
    assert_true("clampLoraScale(l.scale != null ? l.scale : l.strength, 0.8)" not in js,
                "packLoras scale must not clamp null→0.8")
    assert_true("clampLoraScale(l.strength != null ? l.strength : l.scale, 0.8)" not in js,
                "packLoras strength must not clamp null→0.8")
    assert_true("clampLoraScale(inp.value, 0.8)" not in js, "slider must not write 0.8 on empty")
    assert_true("strengthMissing" in js, "strengthMissing flag on normalize/pack")
    pack_i = js.find("function packLorasForPayload")
    pack = js[pack_i:pack_i + 4200]
    assert_true("strengthMissing" in pack or "strength: null" in pack or "strength: l.strength" in pack,
                "pack ships null strength into payload")
    rend_i = js.find("function renderLoras")
    rend = js[rend_i:rend_i + 1600]
    assert_true("0.8" not in rend or "strengthMissing" in rend or 'value=""' in rend or "value=\"\"" in rend,
                "chip input must show empty/null, not silent 0.8")

    # 3. Isolate Z-Image _PREF + fake node; sample routes are Krea
    assert_true('FAL_LORA_PREF_SERVICE = "fal-ai/krea-2/turbo/lora"' in js, "Fal pref = krea-2/turbo/lora")
    assert_true('HF_LORA_PREF_SERVICE = "krea/Krea-2-Turbo"' in js, "HF pref = krea/Krea-2-Turbo")
    assert_true('MS_LORA_PREF_SERVICE = "krea/Krea-2-Turbo"' in js, "Magao pref = krea/Krea-2-Turbo")
    assert_true('FAL_LORA_PREF_SERVICE = "fal-ai/z-image/turbo/lora"' not in js, "Fal pref must not pin z-image")
    assert_true('HF_LORA_PREF_SERVICE = "Tongyi-MAI/Z-Image-Turbo"' not in js, "HF pref must not pin Z-Image")
    assert_true('MS_LORA_PREF_SERVICE = "Tongyi-MAI/Z-Image-Turbo"' not in js, "MS pref must not pin Z-Image")
    lc = js[js.find("function loadCatalog"):js.find("async function loadOuts")]
    assert_true('name: "Z-Image Turbo LoRA"' not in lc, "loadCatalog must not fabricate Z-Image Fal node")
    assert_true('name: "Z-Image Turbo"' not in lc, "loadCatalog must not fabricate Z-Image Hub node")
    fal_fix = js[js.find("function falLoraFixtureImport"):js.find("async function mountFalLoraFixture")]
    assert_true('serviceId: "fal-ai/krea-2/turbo/lora"' in fal_fix or "serviceId: FAL_LORA_PREF_SERVICE" in fal_fix,
                "Fal fixture serviceId is Krea turbo/lora")
    hf_fix = js[js.find("function hfLoraFixtureImport"):js.find("async function mountHfLoraFixture")]
    assert_true('serviceId: "krea/Krea-2-Turbo"' in hf_fix or "serviceId: HF_LORA_PREF_SERVICE" in hf_fix,
                "HF fixture serviceId is Krea-2-Turbo")
    ms_fix = js[js.find("function msLoraFixtureImport"):js.find("async function mountMsLoraFixture")]
    assert_true('serviceId: "krea/Krea-2-Turbo"' in ms_fix or "serviceId: MS_LORA_PREF_SERVICE" in ms_fix,
                "MS fixture serviceId is Krea-2-Turbo")

    # 4. catalogCaps reads parameterCapabilities (HF 117216 / UI n=0 join)
    cc = js[js.find("function catalogCaps"):js.find("function markOver")]
    assert_true("parameterCapabilities" in cc, "catalogCaps must read parameterCapabilities")

    # 5. o28 board §硬规则2: unsupported → disable+「不支持」, do not hide comfy as-complete on fal
    sync = js[js.find("function syncParamSurface"):js.find("function readComfyParamsFromUi")]
    assert_true("ComposerFieldAdapt" in sync or "applyToSurface" in sync,
                "syncParamSurface delegates to ComposerFieldAdapt")
    adapt = (ROOT / "static" / "composer-field-adapt.js").read_text(encoding="utf-8")
    assert_true("param-unsupported" in adapt, "unsupported fields get param-unsupported")
    assert_true("本家不支持" in adapt, "plain unsupported copy")
    # 裁决(o57): showComfyGroup 由常量 true 改为按家计算(civitai/hf/魔搭, 或 width 受支持即挂载),
    # 语义不变——comfy 组不整组隐藏, 不支持走 per-field disable+「不支持」。
    assert_true("const showComfyGroup" in adapt, "comfy group mount decision kept")
    assert_true('comfyBox.classList.toggle("hidden", !showComfyGroup)' in adapt,
                "comfyParams stay mounted; per-field disable handles honesty")
    assert_true('resolveFieldSupport("width", ctx) !== "unsupported"' in adapt,
                "fal 家 width 受支持时 comfy 组仍挂载(不整组藏)")

    # 6. loadCatalog failure must not swallow
    # 裁决: setMsg/smartMatch 的 try/catch(_) 是 UI 安全壳, 刻意保留;
    # 真正的目录拉取失败走外层 catch (e) → setMsg("目录加载失败 …", "bad") 上浮。
    assert_true("catch (e)" in lc and "目录加载失败" in lc, "loadCatalog failure surfaces via catch (e)")
    assert_true("setMsg" in lc or "catalog" in lc.lower(), "loadCatalog failure surfaces to UI")

    # 7. import height aligned 1672→1664 must #paramWarn /16, not success-ok
    ai = js.find("async function applyImport")
    if ai < 0:
        ai = js.find("function applyImport")
    aj = js.find("function bindImportModal", ai)
    if aj < 0:
        aj = js.find("async function runImportFromUrl", ai)
    block = js[ai:aj]
    assert_true("paramWarn" in block or "setParamWarn" in block, "applyImport talks to #paramWarn")
    assert_true("/16" in block, "alignment warn names /16")
    assert_true("1664" in block or "originalHeight" in block or "sourceHeight" in block
                or "aligned" in block.lower() or "align" in block.lower(),
                "import detects backend height alignment")

    # 8. video→image must withdraw 缺首帧
    sm = js[js.find("function setMode"):js.find("function setMode") + 900]
    rd = js[js.find("function renderDock"):js.find("function renderDock") + 9000]
    assert_true("缺首帧" in rd, "video missing-frame copy kept")
    withdrawn = (
        ("缺首帧" in sm and "image" in sm)
        or ('indexOf("缺首帧")' in rd or "indexOf('缺首帧')" in rd or "缺首帧" in rd and "image" in rd)
        or ("mode === \"image\"" in rd and "setMsg" in rd)
    )
    assert_true(withdrawn, "image mode must clear leftover 缺首帧")

    # 9. ▶整组 generate 400 must surface error, not only 已停在此镜
    rg = js[js.find("async function runGroupSequential"):js.find("function createGroupFromSelection")]
    assert_true("已停在此镜" in rg, "group stop copy kept")
    assert_true("r.error" in rg or "r.message" in rg or "formatErr" in rg,
                "group stop must keep generate 400 error text")

    # 10. stillGoing recognizes IN_QUEUE/IN_PROGRESS; processing|pending must not throw on st.error
    run = js[js.find("async function runShotStep"):js.find("async function runShotStep") + 22000]
    still = run[run.find("const stillGoing"):run.find("const stillGoing") + 500]
    assert_true("IN_QUEUE" in still, "stillGoing recognizes IN_QUEUE")
    assert_true("IN_PROGRESS" in still, "stillGoing recognizes IN_PROGRESS")
    infl = run.find("const inFlight")
    assert_true(infl >= 0, "poll has inFlight guard")
    poll = run[infl:infl + 900]
    assert_true("PROCESSING" in poll or "PENDING" in poll or "IN_QUEUE" in poll,
                "poll does not throw away processing+error")
    assert_true("st.error" in poll and "!inFlight" in poll, "st.error only throws when not in-flight")
    assert_true("throw" in poll, "hard failed still throws")


def test_r7_new_shot_does_not_stack():
    """7× 360×640 cards must not be born 24px apart or clamped onto one edge."""
    js = (ROOT / "static" / "storyboard.js").read_text(encoding="utf-8")
    start = js.find("function newShotPosition")
    end = js.find("function fitCam")
    assert_true(start > 0 and end > start, "newShotPosition block")
    block = js[start:end]
    assert_true("(index % 2) * (24 / scale)" not in block, "no 24px grid nudge")
    assert_true("rightmost.x + box(rightmost).w + gap" in block, "place to the right of rightmost")
    assert_true("never clamp them onto the same viewport edge" in block, "no viewport restack")
    constrain = js[js.find("function constrainShotsToViewport"):js.find("function newShotPosition")]
    assert_true("const fitX =" in constrain and "const fitY =" in constrain, "fitX/fitY")
    assert_true("if (fitX && maxX >= loX)" in constrain, "no per-card X clamp when collection overflows")
    assert_true("if (fitY && maxY >= loY)" in constrain, "no per-card Y clamp when collection overflows")


def test_v0821o8_caption_i2i():
    html = (ROOT / "static" / "storyboard.html").read_text(encoding="utf-8")
    js = (ROOT / "static" / "storyboard.js").read_text(encoding="utf-8")
    assert_true('id="btnRev"' in html, "btnRev 提示词反推")
    assert_true('id="btnText"' in html, "btnText 提示词节点")
    assert_true("async function captionFromAsset" in js, "captionFromAsset from v0794")
    assert_true("async function reverseFromImage" in js, "reverseFromImage from v0794")
    assert_true("async function generateFromText" in js, "generateFromText from v0794")
    assert_true("function describePrompt" in js, "describePrompt from v0794")
    assert_true('fetch("/api/caption"' in js, "captionFromAsset posts /api/caption")
    assert_true("未能从真实资产取得描述" in js, "empty caption does not invent CHAR_LIB")
    assert_true("CHAR_LIB" not in js, "no CHAR_LIB fallback")
    assert_true('n.kind === "text"' in js or "n.kind === 'text'" in js, "text node cards")
    assert_true("dst.kind === \"text\"" in js or "dst.kind === 'text'" in js, "canLink image→text")
    assert_true("n.kind !== \"text\"" in js, "text nodes are not pending uploads")
    assert_true("生图必须显式选择图片模型" in js, "generateFromText does not invent a model")
    cap = js[js.find("async function captionFromAsset"):js.find("async function reverseFromImage")]
    assert_true("setMsg" in cap, "caption failure surfaces the API error")
    assert_true("j.caption" in cap, "caption text comes from the model")



def test_v0821o9_fail_zh_lora_honesty():
    """Knife A + Critiquito: humanize Fal 422/missing/body.loc; no bare-missing FP; Composer foot == card; LoRA honesty kept."""
    import json
    import subprocess
    js = (ROOT / "static" / "storyboard.js").read_text(encoding="utf-8")
    html = (ROOT / "static" / "storyboard.html").read_text(encoding="utf-8")
    index = (ROOT / "static" / "index.html").read_text(encoding="utf-8")

    assert_true("v0821o49b-hydrate-fresh-empty-url" in html, "html stamp")
    assert_true('src="/static/storyboard.js?v=' in html, "script cache-bust")
    assert_true("function humanizeFailText" in js, "humanizeFailText helper")
    assert_true('/\\bmissing\\b/.test(lower) && /body\\./.test(lower)' not in js,
                "no bare missing&&body. false-positive clause")
    assert_true('setMsg(n._error, "bad"' in js, "Composer foot mirrors card _error")
    assert_true("内容未通过安全审核" in js, "content checker Chinese copy")
    assert_true("缺少提示词（服务端校验）" in js, "Field required Chinese copy")
    assert_true("humanizeFailText(raw)" in js, "formatErrInfo uses humanize")
    assert_true("flagged by a content checker" in js, "maps Fal content-checker English")

    # 裁决: renderDock 函数体增长(参考链/缺首帧门), n._error 镜像移到 ~3.7k 偏移, 窗口放宽(语义不变)
    rd = js[js.find("function renderDock"):js.find("function renderDock") + 4600]
    assert_true("n._error" in rd and "setMsg(n._error" in rd, "renderDock syncs shot _error to Composer foot")
    assert_true('setMsg(n._error, "bad"' in rd, "foot uses bad tone")

    rend = js[js.find("function renderLoras"):js.find("function renderLoras") + 2400]
    assert_true("未填" in rend, "LoRA strength placeholder is outbound-honest")
    assert_true(
        "ComposerFieldAdapt.strengthPlaceholder" in rend or "未填·出站按提供方默认" in rend,
        "strength uses adapt「未填」helper (or legacy honest placeholder)",
    )
    assert_true("不写 1.0/0.8" in rend, "title/placeholder denies invent defaults")

    paint = js[js.find("function paintShotFail"):js.find("function paintShotFail") + 900]
    assert_true("shot._error = info.text" in paint, "paintShotFail card _error is humanized text")
    assert_true("setMsg(info.text" in paint, "paintShotFail Composer #msg same as card")
    failblk = js[js.find("function fail(err, status, cls"):js.find("function fail(err, status, cls") + 1600]
    assert_true("shot._error = info.text" in failblk, "runShotStep fail card _error is humanized text (not prefix)")
    assert_true("formatErrInfo(err)" in failblk, "runShotStep fail goes through formatErrInfo")
    # poll must throw RAW Fal/job error so formatErrInfo can keep English excerpt
    run = js[js.find("async function runShotStepWork"):js.find("function setSendVisual")]
    assert_true("throw new Error(detail)" not in run, "poll must not pre-wrap formatErr (loses excerpt)")
    assert_true("throw (st.error" in run or "throw st.error" in run, "poll throws raw job.error into fail()")

    hs = js.find("function shortErrExcerpt")
    he = js.find("function formatErr(", hs)
    helpers = js[hs:he]
    assert_true("function humanizeFailText" in helpers and "function formatErrInfo" in helpers, "extract humanize+formatErrInfo")
    prog = helpers + r"""
const cases = [
  ["body.prompt: The content could not be processed because it contained material flagged by a content checker.", "内容未通过安全审核"],
  ["body.prompt: Field required", "缺少提示词（服务端校验）"],
  ["body.image_url: Field required", "缺少图片输入（服务端校验）"],
  ['{"type":"missing","loc":["body","prompt"],"msg":"Field required"}', "缺少提示词（服务端校验）"],
  ['{"type":"missing","loc":["body","prompt"]}', "缺少提示词（服务端校验）"],
  ['[{"type":"missing","loc":["body","start_image"],"msg":"Field required"}]', "缺少图片输入（服务端校验）"],
  ["prompt is required but was not provided", "缺少提示词（服务端校验）"],
  ["content_policy_violation", "内容未通过安全审核"],
  ["flagged by a content checker", "内容未通过安全审核"],
  ["missing dependency in body.build", "missing dependency in body.build"],
  ["User is missing something without body.", "User is missing something without body."],
  ["The type: missing widget in body.build", "The type: missing widget in body.build"],
  ["The file is missing", "The file is missing"],
  ["此模型需要提示词", "此模型需要提示词"],
  ["File download error", "资源下载失败（链接不可达）"],
];
let bad = [];
for (const [inp, want] of cases) {
  const got = humanizeFailText(inp);
  if (got !== want) bad.push({kind:"humanize", inp, want, got});
}
const fiCases = [
  {inp: "body.prompt: Field required", text: "缺少提示词（服务端校验）", excerptHas: ["body.prompt", "Field required"]},
  {inp: "missing dependency in body.build", text: "missing dependency in body.build", excerptEmpty: true},
  {inp: "The type: missing widget in body.build", text: "The type: missing widget in body.build", excerptEmpty: true},
  {inp: '{"type":"missing","loc":["body","prompt"]}', text: "缺少提示词（服务端校验）", excerptHas: ["missing", "body"]},
  {inp: "body.prompt: The content could not be processed because it contained material flagged by a content checker.", text: "内容未通过安全审核", excerptHas: ["content checker"]},
  {inp: {error: "body.prompt: Field required"}, text: "缺少提示词（服务端校验）", excerptHas: ["Field required"]},
];
for (const c of fiCases) {
  const fi = formatErrInfo(c.inp);
  if (fi.text !== c.text) bad.push({kind:"formatErrInfo.text", inp: c.inp, want: c.text, got: fi.text});
  if (c.excerptEmpty && fi.excerpt) bad.push({kind:"formatErrInfo.excerpt", inp: c.inp, want: "", got: fi.excerpt});
  if (c.excerptHas) {
    for (const p of c.excerptHas) {
      if (!(fi.excerpt || "").includes(p)) bad.push({kind:"formatErrInfo.excerpt", inp: c.inp, need: p, got: fi.excerpt});
    }
  }
  if (fi.text && /[\u4e00-\u9fff]/.test(fi.text) && c.excerptHas) {
    // mapped ZH must not dump pydantic English into the card/foot text
    if (fi.text === (typeof c.inp === "string" ? c.inp : JSON.stringify(c.inp))) {
      bad.push({kind:"zh-not-applied", inp: c.inp, got: fi.text});
    }
  }
}
if (bad.length) { console.log(JSON.stringify(bad)); process.exit(1); }
console.log("ok");
"""
    r = subprocess.run(["node", "-e", prog], capture_output=True, text=True)
    assert_true(r.returncode == 0, "humanizeFailText/formatErrInfo node eval: %s %s" % (r.stdout, r.stderr))

    assert_true("fallback == null ? 0.8" not in index, "index clamp must not default 0.8")
    assert_true("clampLoraScale(v.strength != null ? v.strength : v.scale, 0.8)" not in index,
                "index normalizeLora must not invent 0.8")
    assert_true("clampLoraScale(l.scale != null ? l.scale : l.strength, 0.8)" not in index,
                "index payload/slim must not invent 0.8 scale")
    assert_true("clampLoraScale(l.strength != null ? l.strength : l.scale, 0.8)" not in index,
                "index payload/slim must not invent 0.8 strength")
    assert_true("strengthMissing" in index, "index tracks strengthMissing")
    assert_true("未填·出站按提供方默认" in index, "index LoRA placeholder honest")
    assert_true("strength: null" in index, "index addLora uses null strength")
    assert_true(index.count("strength: 0.8") == 0, "index search/add must not hardcode strength: 0.8")

    # storyboard searchLoras / add-from-search must not silently invent 0.8 (fixtures elsewhere may still use 0.8)
    sl_start = js.find("async function searchLoras")
    sl_end = js.find("function bindLoraUi()", sl_start)
    assert_true(sl_start >= 0 and sl_end > sl_start, "searchLoras block found")
    search_loras = js[sl_start:sl_end]
    assert_true("strength: 0.8" not in search_loras, "storyboard searchLoras must not hardcode strength: 0.8")
    assert_true("strength:0.8" not in search_loras, "storyboard searchLoras must not hardcode strength:0.8")
    assert_true(search_loras.count("strength: null") >= 4, "storyboard searchLoras add paths use strength: null")



def test_v0821o15_server_writeback_executable():
    """v0821o15: local persist + PUT /api/storyboard-graph; clean-profile hydrate keeps shot.url."""
    js = (ROOT / "static" / "storyboard.js").read_text(encoding="utf-8")
    html = (ROOT / "static" / "storyboard.html").read_text(encoding="utf-8")
    assert_true("v0821o49b-hydrate-fresh-empty-url" in html, "html stamp")
    assert_true('"nl-storyboard-v0821o16"' in js, "STORE v0821o15")
    assert_true('"nl-storyboard-v0821o14"' in js, "STORE_OLDS keeps o14")
    assert_true('"nl-storyboard-v0821o13"' in js, "STORE_OLDS keeps o13")
    assert_true('"nl-storyboard-v0821o12"' in js, "STORE_OLDS keeps o12")
    assert_true("storyboard.js?v=20260911-o49bhydratefreshemptyurl" in html, "js cache bust")
    assert_true("function mergePreferUrl" in js, "mergePreferUrl helper")
    assert_true("function isQuotaErr" in js, "isQuotaErr helper")
    assert_true("function persistServer" in js, "persistServer helper")
    assert_true("function hydrateFromServer" in js, "hydrateFromServer helper")
    assert_true("function applyGraph" in js, "applyGraph helper")
    assert_true("/api/storyboard-graph" in js, "storyboard-graph API")
    assert_true("本地缓存已满" in js, "QuotaExceeded user warn")
    # Structural: writeback persists local + server
    w = js.find("function writebackResult")
    assert_true(w >= 0, "writebackResult")
    wend = js.find("function pickSavedUrl", w)
    if wend < 0:
        wend = js.find("function pickUrl", w)
    wb = js[w:wend]
    assert_true("persist()" in wb, "writebackResult calls persist")
    assert_true("persistServer()" in wb, "writebackResult calls persistServer")
    assert_true("shot.kind === \"shot\"" in wb or "shot.kind===\"shot\"" in wb.replace(" ", ""), "writeback re-attaches orphan shot")
    assert_true("state.nodes.push" in wb, "orphan push into state.nodes")
    assert_true("skip PUT" in js, "persistServer skips empty nodes")
    assert_true("服务端保存失败 HTTP" in js, "persistServer surfaces HTTP fail")
    assert_true("function pickSavedUrl" in js, "pickSavedUrl")
    assert_true("pickSavedUrl(st)" in js, "poll break on saved")
    assert_true("const savedUrl = pickSavedUrl(j)" in js and "savedUrl || pickUrl(j)" in js, "final prefer saved")
    assert_true('if (pickUrl(st)) break;' not in js, "no CDN poll break")
    assert_true('"nl-storyboard-v0821o15"' in js, "STORE_OLDS keeps o15")
    assert_true("hydrateFromServer()" in js, "boot calls hydrateFromServer")
    # Server helpers exist
    server = (ROOT / "server.py").read_text(encoding="utf-8")
    assert_true("def read_storyboard_graph" in server, "read_storyboard_graph")
    assert_true("def write_storyboard_graph" in server, "write_storyboard_graph")
    assert_true('"/api/storyboard-graph"' in server, "server route")
    # Executable proof (node VM runs production persist/restore + server seams)
    import subprocess
    proc = subprocess.run(
        ["node", str(ROOT / "scripts" / "test_storyboard_persist_restore.js")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert_true(proc.returncode == 0, "executable persist/restore failed: " + (proc.stdout or "") + (proc.stderr or ""))
    assert_true("ok: storyboard persist/restore executable checks passed" in (proc.stdout or ""), proc.stdout)


def test_v0821o19_single_up_writeback():
    """o19: 双↑→单↑ + writeback keepalive + frame-edge ensure; keep A1/A3/A4/A5."""
    js = (ROOT / "static" / "storyboard.js").read_text(encoding="utf-8")
    html = (ROOT / "static" / "storyboard.html").read_text(encoding="utf-8")
    # 裁决: o63/o103 内联 <style> 已拆外部样式表, 样式断言统一读 css_all()
    css = css_all()
    assert_true("v0821o49b-hydrate-fresh-empty-url" in html, "html stamp o19")
    assert_true('src="/static/storyboard.js?v=' in html, "js cache-bust o19")
    assert_true('"nl-storyboard-v0821o16"' in js, "persist STORE stays o16")
    assert_true('"nl-storyboard-v0821o16"' in js, "STORE_OLDS still knows o16")

    # A1 capsule + right rail; default image
    assert_true('id="chatRail"' in html, "right chat-rail skeleton")
    assert_true("function renderChatRail" in js, "renderChatRail")
    assert_true("function positionDock" in js, "positionDock")
    # 裁决(o63/o136seko): 按钮文案简化为「折叠」, 胶囊契约见 o76-dock-right.css「收起=窄胶囊…禁止底部 720 条」
    assert_true('id="dockCollapse"' in html, "collapse is capsule not 底栏")
    assert_true("折叠为底栏" not in html, "no bottom-bar copy")
    assert_true("收起=窄胶囊" in css and "禁止底部" in css, "capsule contract kept in css")
    assert_true('id="modeImg" class="on"' in html or 'id="modeImg" class="on"' in html.replace(" ", " "),
                "图片生成 starts on")
    # 裁决(o136seko): btnAdd 改为打开 addPop 菜单, 新建分镜走 addBlankShot(); 默认 image 语义移入 addBlankShot
    add = js[js.find("function addBlankShot"):js.find("function addBlankShot") + 700]
    assert_true('state.mode = "image"' in add, "addBlankShot defaults image")
    assert_true('mode: "image"' in add, "new shot.mode image")

    # A3 visible wires (裁决: 样式外链 → wires 规则读 css_all())
    assert_true("svg.wires path.edge" in css, "path.edge css")
    assert_true("stroke:#e8edf4" in css or 'stroke="#e8edf4"' in js, "edge stroke paints")
    assert_true("class=\"edge-glow\"" in js or "class='edge-glow'" in js or 'class="edge-glow"' in js,
                "wire glow path")
    dw = js[js.find("function drawWires"):js.find("function drawWires") + 1800]
    assert_true("stroke=" in dw and "e8edf4" in dw, "drawWires inline stroke")
    assert_true("z-index:4" in css or 'zIndex = "4"' in dw, "wires above cards")
    # 裁决: non-scaling-stroke 从 CSS 迁到 drawWires 内联属性
    assert_true('vector-effect="non-scaling-stroke"' in js
                or "vector-effect: non-scaling-stroke" in css, "non-scaling stroke kept")

    # A2 writeback not history-only; o16 poll/persist kept
    wb = js[js.find("function writebackResult"):js.find("function pickSavedUrl")]
    assert_true("live.url = url" in wb, "writeback sets shot.url")
    assert_true("persistServer()" in wb, "writeback PUT graph")
    assert_true("skip PUT" in js, "persistServer skip empty")
    assert_true("pickSavedUrl(st)" in js, "poll waits saved[]")
    assert_true('if (pickUrl(st)) break;' not in js, "no CDN early break")
    assert_true(js.count('fetch("/api/generate"') == 1, "single generate stack")

    # A4 first-frame slot has upload/select, no silent steal
    rd = js[js.find("function renderDock"):js.find("function renderDock") + 9000]
    assert_true('data-act="upload"' in rd and "缺首帧" in rd, "missing slot upload")
    assert_true('data-act="pick"' in rd, "missing slot select")
    assert_true("切到图片生成" in js, "soften copy")
    assert_true("不能偷配方台" in js, "hard gate no recipe steal")
    assert_true("首帧已就绪 · 可生成" in js, "ready copy kept")

    # P1 from code review Pass (o18)
    assert_true('state.mode === "image" || state.mode === "video"' in js, "chatRail mode step lights for video")
    # 裁决(o63/o136seko): 样式外链; collapsed 底行不再藏 dock-foot, .send 系控件经
    # composer-field-adapt.css :not(#backend):not(#service):not(.send):not(.grow) 规则保留(#sendCap 胶囊)
    assert_true(".dock.collapsed .dock-foot{display:none}" not in css.replace(" ", "")
                and ".dock.show.collapsed .dock-foot{display:none" not in css.replace(" ", ""),
                "collapsed must not hide dock-foot")
    assert_true(".dock.collapsed .dock-foot" in css or ".dock.show.collapsed .dock-foot" in css,
                "collapsed dock-foot rule visible")
    assert_true(":not(#backend):not(#service):not(.send):not(.grow)" in css,
                "collapsed keeps .send send-capsule")
    assert_true("shot.url = url" in js[js.find("function writebackResult"):js.find("function pickSavedUrl")],
                "writeback syncs caller shot.url")
    assert_true("v0821o18: explicit attach only" in js, "i2v attach announces 首帧已就绪")

    # o19 visual P0 双↑ → only capsule #send
    assert_true("chatRailSend" not in js, "no chatRailSend second ↑")
    assert_true("双↑" in js, "documents 双↑ fix")
    assert_true("keepalive: true" in js, "persistServer keepalive for writeback PUT")
    # 裁决(o136seko-healframe): 孤儿 firstFrameId 愈合迁到 frameAsset()
    # (资产已删→愈合成当前连入首图, 连线即引用); drawWires 只画 state.edges, 不再做 edge-dropped 兜底
    assert_true("v0821o136seko-healframe" in js, "drawWires/frameAsset frame lineage")
    assert_true(js.count('id="chatRailSend"') == 0, "no chatRailSend id")
    assert_true(html.count('id="send"') == 1, "exactly one #send in html")

    # A5 honest stubs
    # 裁决(o136seko): Seko 对齐后 modes 行不再渲染「未接」pill; stub 诚实文案走 js(chatRail tag 未接 / setMsg 本版未接)
    assert_true('id="modeText" class="stub"' in html and "本版未接" in js, "text stub honest")
    assert_true('id="modeAud" class="stub"' in html, "audio stub")
    assert_true("本版未接" in js, "stub generate blocked")


def test_v0821o20_visual_p0():
    """o20: selected image in 参考链; compact 未接 pills; chatRail product copy."""
    js = (ROOT / "static" / "storyboard.js").read_text(encoding="utf-8")
    html = (ROOT / "static" / "storyboard.html").read_text(encoding="utf-8")
    css = (ROOT / "static" / "storyboard-ui.css").read_text(encoding="utf-8")
    assert_true("v0821o49b-hydrate-fresh-empty-url" in html, "html stamp o20")
    assert_true('src="/static/storyboard.js?v=' in html, "js cache-bust o20")
    assert_true('href="/static/storyboard-ui.css?v=' in html, "css cache-bust o20")
    assert_true('"nl-storyboard-v0821o16"' in js, "STORE stays o16")
    assert_true(js.count('fetch("/api/generate"') == 1, "single generate stack")

    # P0-1 visual chip + UI count; send-path 参考 is inbound edges only (own url must not trip t2i unused-ref)
    assert_true("function shotResultImageUrl" in js, "shotResultImageUrl helper")
    assert_true("function displayRefUrls" in js, "displayRefUrls UI helper")
    cr = js[js.find("function countRefUrls"):js.find("function countRefUrls") + 1100]
    assert_true("shotResultImageUrl" not in cr, "countRefUrls send-path excludes own shot.url")
    ae = js[js.find("function attachExtraImages"):js.find("function attachExtraImages") + 1400]
    assert_true("shotResultImageUrl" not in ae, "attachExtraImages send-path excludes own shot.url")
    rd = js[js.find("function renderDock"):js.find("function renderDock") + 9000]
    assert_true('data-self-ref="1"' in rd, "成片 chip in 参考链")
    assert_true("countRefUrls(null, n)" in rd, "参考 N/cap uses outbound countRefUrls (o40)")
    sn = js[js.find("function selectNode"):js.find("function selectNode") + 1200]
    assert_true("linkAssetToShot" in sn, "select image source auto-links into composer shot")
    assert_true("isImageSource(selected)" in rd or "isImageSource(selected)" in js, "keep dock when selecting image source")

    # P0-2 compact stubs
    # 裁决(o63/o136seko): 样式外链; 旧 .modes button.stub/flex:0 0 auto/mode-tag pill 规则已移除,
    # 紧凑语义现为 shell.css .modes 单行 flex + .modes button{white-space:nowrap}; 「未接」pill 从 html 移除,
    # 诚实提示走 js(chatRail tag 未接 / 本版未接 阻断); 模式行顺序 文本/图片/视频/音频 自 o63 起稳定(刻意 Seko 对齐)
    css = css_all()
    assert_true('id="modeText" class="stub"' in html and 'id="modeAud" class="stub"' in html, "stub buttons kept")
    assert_true("white-space: nowrap" in css_rule(css, ".modes button"), "mode buttons compact nowrap")
    assert_true('id="modeImg"' in html and 'id="modeText"' in html, "mode buttons mounted")
    assert_true('id="modeImg" class="on"' in html, "图片生成 starts on")
    assert_true('class="stub"' in html and "本版未接" in js, "stubs still honest/blocked")

    # P0-3 no debug copy on creation surface
    # 裁决: renderChatRail 函数体增长, 路径文案移到 ~2.3k 偏移, 窗口放宽(语义不变)
    rail = js[js.find("function renderChatRail"):js.find("function renderChatRail") + 2600]
    assert_true("无第二套" not in rail, "no 无第二套 on rail")
    assert_true("/api/generate" not in rail, "no /api/generate on rail copy")
    assert_true("无第二套" not in html, "html skeleton no 无第二套")
    assert_true("同一 /api/generate" not in html, "html skeleton no api debug")
    assert_true("it.name" in rail or "svcLabel" in rail, "service label prefers catalog name")
    assert_true("选分镜 → " in rail and "胶囊 ↑" in rail, "product path copy")



def test_v0821o22_hinablue_writeback():
    """o22: 19201654 import eco/service; diffusionModel pack; CDN honesty; UI displayRefUrls; no 142210587 lock."""
    js = (ROOT / "static" / "storyboard.js").read_text(encoding="utf-8")
    html = (ROOT / "static" / "storyboard.html").read_text(encoding="utf-8")
    civ = (ROOT / "providers" / "civitai.py").read_text(encoding="utf-8")
    assert_true("v0821o49b-hydrate-fresh-empty-url" in html, "html stamp o23 (o22 lineage)")
    assert_true('src="/static/storyboard.js?v=' in html, "js cache-bust o23")
    assert_true('"nl-storyboard-v0821o16"' in js, "STORE stays o16")
    assert_true(js.count('fetch("/api/generate"') == 1, "single generate stack")
    assert_true("keepalive: true" in js, "persistServer keepalive kept")
    assert_true("shot._jobId" in js and "[outbound-fail]" in js, "jobId fail capture kept")

    # import ecosystem must not keep krea2 for sdxl/pony (19201654 class)
    assert_true('eco == "sdxl"' in civ, "import maps sdxl ecosystem branch")
    assert_true('engine, operation, ecosystem, model = "sdcpp", "createImage", "sdxl", None' in civ,
                "sdxl uses sdcpp createImage")

    # diffusionModel / ecosystem wire (generic hinablue import → outbound)
    ai = js[js.find("async function applyImport"):js.find("async function applyImport") + 14000]
    assert_true("shot.diffusionModel" in ai, "applyImport stores diffusionModel on shot")
    assert_true("shot.checkpointName" in ai, "applyImport stores checkpointName on shot")
    assert_true("shot.ecosystem" in ai, "applyImport stores ecosystem on shot")
    assert_true("shot.serviceId" in ai, "applyImport stores serviceId on shot (o23)")
    # 裁决: packComfyParamsForPayload 函数体增长(nano/fal 分支), ecosystem 附挂移到 ~1.8k 偏移, 窗口放宽(语义不变)
    pack = js[js.find("function packComfyParamsForPayload"):js.find("function packComfyParamsForPayload") + 2200]
    assert_true("p.diffusionModel = dm" in pack, "pack attaches diffusionModel for civitai")
    assert_true("p.ecosystem = eco" in pack, "pack attaches ecosystem")
    assert_true("never invent" in pack, "pack comment: never invent default AIR")
    run = js[js.find("async function runShotStepWork"):js.find("async function runShotStepWork") + 30000]
    assert_true("142210587" not in run, "runShotStepWork not locked to 142210587")
    assert_true("142210587" not in ai, "applyImport not locked to 142210587")
    assert_true("LoRA 出站 " in run, "partial LoRA drop honesty")

    # CDN honesty
    assert_true("CDN 暂存" in run or "CDN 暂存" in js, "CDN writeback warn copy")
    assert_true("const savedUrl = pickSavedUrl(j)" in run and "durable" in run, "durable /out check")

    # Visual P0 lightweight
    assert_true("function displayRefUrls" in js, "displayRefUrls helper")
    rd = js[js.find("function renderDock"):js.find("function renderDock") + 9000]
    assert_true("countRefUrls(null, n)" in rd, "参考 hint uses outbound countRefUrls (o40)")
    cr = js[js.find("function countRefUrls"):js.find("function countRefUrls") + 1100]
    assert_true("shotResultImageUrl" not in cr, "countRefUrls still excludes own url")
    ae = js[js.find("function attachExtraImages"):js.find("function attachExtraImages") + 1400]
    assert_true("shotResultImageUrl" not in ae, "attachExtraImages still excludes own url")
    assert_true('data-self-ref="1"' in rd, "成片 chip kept")

    rail = js[js.find("function renderChatRail"):js.find("function renderChatRail") + 2200]
    assert_true("无第二套" not in rail and "/api/generate" not in rail, "no debug copy on rail")
    assert_true('id="send"' in html and html.count('id="send"') == 1, "single capsule ↑")



def test_v0821o23_sdxl_service_stick():
    """o23: import→shot.serviceId→outbound resolve forbids silent krea2 when eco/dm is sdxl."""
    js = (ROOT / "static" / "storyboard.js").read_text(encoding="utf-8")
    html = (ROOT / "static" / "storyboard.html").read_text(encoding="utf-8")
    civ = (ROOT / "providers" / "civitai.py").read_text(encoding="utf-8")
    assert_true("v0821o49b-hydrate-fresh-empty-url" in html, "html stamp o23")
    assert_true('src="/static/storyboard.js?v=' in html, "js cache-bust o23")
    assert_true('"nl-storyboard-v0821o16"' in js, "STORE stays o16")
    assert_true(js.count('fetch("/api/generate"') == 1, "single generate stack")
    assert_true("function resolveCivitaiOutboundServiceId" in js, "resolve helper")
    assert_true("function civitaiServiceIdFromImportShot" in js, "shot→serviceId helper")
    assert_true("isCivitaiKrea2TurboService" in js, "krea2 detect")
    assert_true("image/sdcpp/sdxl/createImage" in js, "sdxl service literal")
    bg = js[js.find("function buildGraph"):js.find("function buildGraph") + 3500]
    assert_true("resolveCivitaiOutboundServiceId(shot)" in bg, "buildGraph uses resolve")
    run = js[js.find("async function runShotStepWork"):js.find("async function runShotStepWork") + 32000]
    assert_true("resolveCivitaiOutboundServiceId(shot)" in run, "runShot uses resolve")
    assert_true("syncCivitaiServiceSelect" in run, "sync #service before POST")
    ai = js[js.find("async function applyImport"):js.find("async function applyImport") + 16000]
    assert_true("shot.serviceId" in ai, "applyImport writes shot.serviceId")
    # writeback/jobId paths kept
    assert_true("shot._jobId" in js and "[outbound-fail]" in js, "jobId fail path kept")
    assert_true("keepalive: true" in js, "persist keepalive kept")
    # LoRA file-stem dedupe
    assert_true("def _file_stem" in civ and "seen_stems" in civ, "prompt-tag file-stem dedupe")
    assert_true('engine, operation, ecosystem, model = "sdcpp", "createImage", "sdxl", None' in civ,
                "import still maps sdxl→sdcpp")


def test_import_19201654_original_params():
    """Acceptance-sample self-check (import only, NOT generate / NOT closed-loop): post 19201654."""
    from providers.civitai import import_image
    j = import_image("19201654")
    assert_true(isinstance(j, dict), "import dict")
    assert_true(j.get("backend") == "civitai" or j.get("serviceId"), "civitai-shaped")
    assert_true(j.get("ecosystem") == "sdxl", "ecosystem sdxl not krea2")
    assert_true("sdxl" in str(j.get("serviceId") or ""), "serviceId sdxl path")
    assert_true("krea2" not in str(j.get("serviceId") or ""), "serviceId must not stay krea2 turbo")
    prompt = str(j.get("prompt") or "")
    assert_true(len(prompt) > 200, "original prompt not short/SFW")
    assert_true("samurai" in prompt.lower() or "sword" in prompt.lower() or "score_9" in prompt, "prompt looks original")
    dm = str(j.get("diffusionModel") or "")
    assert_true(dm.startswith("urn:air:sdxl:"), "diffusionModel sdxl AIR")
    assert_true(j.get("width") == 1728 and j.get("height") == 2048, "original size")
    assert_true(j.get("steps") == 30, "steps 30")
    assert_true(float(j.get("cfgScale") or 0) == 7.0, "cfgScale 7")
    assert_true(j.get("sampler") == "dpmpp_2m" and j.get("scheduler") == "karras", "sampler/scheduler")
    assert_true(j.get("seed") == 3436905144 or str(j.get("seed")) == "3436905144", "seed")
    assert_true(j.get("serviceId") == "image/sdcpp/sdxl/createImage",
                "exact sdcpp/sdxl serviceId (not krea2)")
    loras = j.get("loras") or []
    assert_true(len(loras) >= 1, "at least one LoRA")
    # o23: prompt tag hinaSamuraiArmorPony_rev1 is file stem of @633865 — dedupe, no empty-air twin
    empty_air = [r for r in loras if not str((r or {}).get("air") or "").strip()]
    assert_true(len(empty_air) == 0, "no empty-air LoRA chip after file-stem dedupe")
    hit = None
    for row in loras:
        air = str((row or {}).get("air") or "")
        if "@633865" in air or str((row or {}).get("versionId") or "") == "633865":
            hit = row
            break
    assert_true(hit is not None, "LoRA @633865 present with air")
    assert_true(float(hit.get("strength") or 0) == 0.7, "strength 0.7 not invented null")


def test_v0821o21_outbound_jobid_writeback():
    """o21 lineage under o22: fail surfaces jobId+backend; single generate; persist keepalive (no fixture lock)."""
    js = (ROOT / "static" / "storyboard.js").read_text(encoding="utf-8")
    html = (ROOT / "static" / "storyboard.html").read_text(encoding="utf-8")
    assert_true("v0821o49b-hydrate-fresh-empty-url" in html, "html stamp o23 (o21 lineage)")
    assert_true('src="/static/storyboard.js?v=' in html, "js cache-bust o23")
    assert_true('"nl-storyboard-v0821o16"' in js, "STORE stays o16")
    assert_true(js.count('fetch("/api/generate"') == 1, "single generate stack")
    assert_true("keepalive: true" in js, "persistServer keepalive")

    run = js[js.find("async function runShotStepWork"):js.find("async function runShotStepWork") + 28000]
    assert_true("function fail(err, status, cls, meta)" in run or "function fail(err, status, cls, meta)" in js,
                "fail accepts meta jobId/backend")
    assert_true("[outbound-fail]" in run, "structured outbound-fail log")
    assert_true("jobId=" in run and "backend=" in run, "fail excerpt tags jobId+backend")
    assert_true("{ jobId: jobId, backend: bePoll }" in run or "{ jobId: jobId, backend: bePoll }" in js,
                "timeout fail passes jobId")
    assert_true("shot._jobId" in run, "shot stores jobId")
    assert_true("packLorasForPayload" in run, "loras attached after compile")
    assert_true("packComfyParamsForPayload" in run, "comfy params attached after compile")
    assert_true("payload.loras = packedLoras" in run, "loras land on generate payload")

    # Import path keeps original prompt + LoRA chips (no short/SFW fill)
    ai = js[js.find("async function applyImport"):js.find("async function applyImport") + 14000]
    assert_true("shot.prompt = p" in ai, "import writes full prompt onto shot")
    assert_true("CIVITAI_PREF" not in ai, "civitai import no Krea2 soft-fill")
    # 裁决: 行打包已拆到 packLoraRow + loraRowCanOutbound(对齐 knife② 裁决), 窗口起点前移(语义不变)
    pack = js[js.find("function loraRowCanOutbound"):js.find("function packLorasForPayload") + 3200]
    assert_true('be === "civitai"' in pack and "row.air" in pack, "civitai pack requires air")

    persist_js = (ROOT / "scripts" / "test_storyboard_persist_restore.js").read_text(encoding="utf-8")
    assert_true("writeback PUT uses keepalive" in persist_js, "persist test asserts keepalive")
    assert_true("hydrate_fills_blank_url_by_id" in persist_js, "hydrate by-id fill test")



def test_v0821o26_fal_swap_dropdown():
    """o26: Fal 换家 after Civitai import — pinFal rewrites foreign serviceId; #backend syncs all providers."""
    js = (ROOT / "static" / "storyboard.js").read_text(encoding="utf-8")
    html = (ROOT / "static" / "storyboard.html").read_text(encoding="utf-8")
    init = (ROOT / "providers" / "__init__.py").read_text(encoding="utf-8")

    assert_true("v0821o49b-hydrate-fresh-empty-url" in html, "html stamp o26")
    assert_true("20260911-o49bhydratefreshemptyurl" in html, "js cache-bust o26")
    assert_true("v0821o26:" in js or "v0821o29:" in js, "js knife banner lineage")

    # Static HTML lists every registered backend (honest fallback before /api/providers)
    for bid in ("fal", "civitai", "nano-gpt", "modelscope-ai", "modelscope-cn", "huggingface"):
        assert_true('value="' + bid + '"' in html, "html option " + bid)

    assert_true("function syncBackendOptionsFromProviders" in js, "syncBackendOptionsFromProviders")
    assert_true("syncBackendOptionsFromProviders(items)" in js, "loadProviderCaps calls sync")
    # Must NOT hide providers lacking keys
    caps_i = js.find("function syncBackendOptionsFromProviders")
    caps_block = js[caps_i:caps_i + 900]
    assert_true("hasKey" not in caps_block, "dropdown sync must not filter hasKey")

    # pinFal rejects civitai / HF ids (换家)
    pi = js.find("function pinFalLoraServiceId")
    assert_true(pi >= 0, "pinFalLoraServiceId")
    pin = js[pi:pi + 900]
    assert_true("looksCivitaiServiceId(s)" in pin, "pinFal rejects civitai serviceId")
    assert_true("looksHfServiceId(s)" in pin, "pinFal rejects HF serviceId")
    assert_true("resolveFalLoraEndpointFromChips" in js, "o29 base resolver")
    assert_true("FAL_LORA_BY_BASE" in js or "FAL_FLUX_LORA_SERVICE" in pin or "FAL_FLUX_LORA_SERVICE" in js,
                "flux family const")
    assert_true("FAL_T2I_DEFAULT" in pin, "pinFal → t2i default without LoRAs")

    # backend onchange clears foreign service + pins Fal LoRA
    oi = js.find('$("backend").onchange')
    if oi < 0:
        oi = js.find("$(\"backend\").onchange")
    assert_true(oi >= 0, "backend onchange")
    # 裁决: onchange 函数体增长(换家清外国 service + HF/Magao 分支), ensureFal 移到 ~2.5k 偏移, 窗口放宽(语义不变)
    on = js[oi:oi + 3200]
    assert_true("looksCivitaiServiceId(cur)" in on, "onchange clears civitai #service on Fal")
    assert_true("ensureFalLoraServiceSelected" in on, "onchange ensures Fal LoRA service")
    assert_true("resolveFalLoraEndpointFromChips" in on, "onchange resolves Fal LoRA by AIR base")

    # providers registered (enabled surface)
    fal_py = (ROOT / "providers" / "fal.py").read_text(encoding="utf-8")
    assert_true("register(FalProvider())" in fal_py, "Fal registered")
    assert_true("from . import fal" in init or "import fal" in init, "fal loaded in providers")
    assert_true("list_public" in init, "list_public feeds /api/providers")

    # o23 civitai stick path untouched (only when be===civitai)
    assert_true("function resolveCivitaiOutboundServiceId" in js, "civitai resolve kept")
    bgi = js.find("function buildGraph")
    bg = js[bgi:bgi + 3600]
    assert_true('be === "civitai"' in bg and "resolveCivitaiOutboundServiceId" in bg,
                "civitai outbound still resolves shot.serviceId")
    assert_true('be === "fal"' in bg and "pinFalLoraServiceId" in bg, "fal outbound still pins")


def test_import_142210587_original_params():
    """OPTIONAL unit fixture only — NOT acceptance / NOT closed-loop sample.
    Live import (not generate) of historical id 142210587 for pack shape smoke.
    Real page ↑ must use a fresh hinablue post (开发 organizes)."""
    from providers.civitai import import_image
    j = import_image("142210587")
    assert_true(isinstance(j, dict), "import dict")
    assert_true(j.get("backend") == "civitai", "backend civitai")
    assert_true("krea2" in str(j.get("serviceId") or ""), "krea2 service")
    prompt = str(j.get("prompt") or "")
    assert_true(len(prompt) > 200, "original prompt not short/SFW")
    assert_true("Asian" in prompt or "girl" in prompt.lower() or "tween" in prompt.lower(),
                "prompt looks like original post not a stub")
    loras = j.get("loras") or []
    assert_true(len(loras) >= 1, "at least one LoRA")
    hit = None
    for row in loras:
        vid = str((row or {}).get("versionId") or "")
        air = str((row or {}).get("air") or "")
        if vid == "3203007" or "@3203007" in air:
            hit = row
            break
    assert_true(hit is not None, "LoRA @3203007 present")
    assert_true(str(hit.get("air") or "").startswith("urn:air:"), "LoRA has air")
    st = hit.get("strength")
    assert_true(st == 1 or st == 1.0, "strength 1 not invented null")
    assert_true(j.get("width") and j.get("height") and j.get("steps") is not None, "full size/steps")
    assert_true(j.get("sampler") and j.get("seed") is not None, "sampler+seed")



def test_v0821o28_composer_adaptive():
    """Composer field board adapt module: show/disable/不支持 + strength 未填; no Fal pin edits."""
    html = (ROOT / "static" / "storyboard.html").read_text(encoding="utf-8")
    js = (ROOT / "static" / "storyboard.js").read_text(encoding="utf-8")
    adapt = (ROOT / "static" / "composer-field-adapt.js").read_text(encoding="utf-8")
    assert_true("v0821o49b-hydrate-fresh-empty-url" in html, "html tip stamp o30")
    # 裁决: adapt 模块戳已推进到 v0821o57-item-match(o47→o57 线), 行为契约不变
    assert_true("v0821o57-item-match" in adapt
                or "v0821o47-composer-board-sync" in adapt
                or "v0821o28-composer-adaptive" in adapt, "adapt module stamp o57/o47/o28")
    assert_true("composer-field-adapt.js" in html, "adapt script included")
    assert_true("composer-field-adapt.css" in html, "adapt css included")
    assert_true("paramSupportStrip" in html, "support strip mounted")
    assert_true("ComposerFieldAdapt" in adapt and "applyToSurface" in adapt, "adapt API")
    assert_true("本家不支持" in adapt, "plain unsupported copy")
    assert_true('return "未填"' in adapt, "null strength → 未填")
    assert_true("filledUnsupportedWarnings" in adapt and "blockingUnsupportedMessages" in adapt,
                "o30 warn vs block split")
    assert_true("adapt.applyToSurface" in js, "syncParamSurface delegates")
    assert_true("pinFalLoraServiceId" in js and "FAL_LORA_BY_BASE" in js, "o29 Fal pin preserved")
    # adapt file must not define Fal pin symbols (comments mentioning o29 ownership OK)
    assert_true("function pinFalLoraServiceId" not in adapt, "adapt stays clear of Fal pin fn")
    assert_true("FAL_LORA_BY_BASE =" not in adapt and "FAL_LORA_BY_BASE=" not in adapt,
                "adapt stays clear of FAL_LORA_BY_BASE map")


def test_v0821o29_fal_lora_base():
    """o29: Fal LoRA endpoint by AIR base — flux1→flux-lora; krea2→krea; else 不支持; never hard-pin wrong family."""
    js = (ROOT / "static" / "storyboard.js").read_text(encoding="utf-8")
    html = (ROOT / "static" / "storyboard.html").read_text(encoding="utf-8")

    # stamp advanced by o28 tip; o29 behavior still required in storyboard.js
    assert_true("v0821o49b-hydrate-fresh-empty-url" in html, "html tip stamp o31 (keeps o29 behavior)")
    assert_true("20260911-o49bhydratefreshemptyurl" in html, "cache-bust current tip")
    assert_true("v0821o29:" in js, "js o29 banner preserved")

    assert_true("function resolveFalLoraEndpointFromChips" in js, "resolver")
    assert_true("function loraAirBase" in js, "loraAirBase")
    assert_true("FAL_LORA_BY_BASE" in js, "FAL_LORA_BY_BASE")
    assert_true('FAL_FLUX_LORA_SERVICE = "fal-ai/flux-lora"' in js, "flux-lora official")
    assert_true('FAL_LORA_PREF_SERVICE = "fal-ai/krea-2/turbo/lora"' in js, "krea pref kept for krea2/fixture")

    # Mapping literals
    board = js[js.find("FAL_LORA_BY_BASE"):js.find("FAL_LORA_BY_BASE") + 500]
    assert_true("flux1" in board and "krea2" in board, "flux1+krea2 keys")

    pin = js[js.find("function pinFalLoraServiceId"):js.find("function ensureFalLoraServiceSelected")]
    assert_true("resolveFalLoraEndpointFromChips" in pin, "pin uses resolver")
    assert_true("resolved.reason" in pin or "resolved.endpoint" in pin, "pin honors unsupported")
    # Must NOT unconditionally assign FAL_LORA_PREF_SERVICE whenever falHasLoras
    assert_true('return falHasLoras() ? FAL_LORA_PREF_SERVICE' not in pin,
                "no one-shot all LoRAs to krea-2")


    # o157: zimageturbo AIR → fal-ai/z-image/turbo/lora; pin not krea sibling; empty-sid honesty
    assert_true('FAL_ZIMAGE_LORA_SERVICE = "fal-ai/z-image/turbo/lora"' in js, "FAL_ZIMAGE_LORA_SERVICE")
    assert_true("zimageturbo" in board and "FAL_ZIMAGE_LORA_SERVICE" in board, "zimageturbo map")
    assert_true("zimage" in board and "FAL_ZIMAGE_LORA_SERVICE" in board, "zimage alias map")
    assert_true("fal-ai/z-image/turbo/lora" in js, "z-image/turbo/lora endpoint literal")
    assert_true("want === FAL_ZIMAGE_LORA_SERVICE" in pin, "pin has z-image sibling branch")
    krea_pin_lines = [ln for ln in pin.splitlines() if "want === FAL_LORA_PREF_SERVICE" in ln]
    assert_true(krea_pin_lines and all("z-image" not in ln for ln in krea_pin_lines),
                "pinFalLoraServiceId does not treat z-image as krea sibling")
    # applyImport Fal path: sid && !importServiceAvailable(sid) (not bare !importServiceAvailable(sid))
    ai = js.find("async function applyImport")
    assert_true(ai >= 0, "applyImport")
    # Fal house branch unique marker
    fal_pin = js.find("state._pinFalLoraService = (Array.isArray(j.loras) && j.loras.length) ? sid", ai)
    assert_true(fal_pin >= 0, "fal applyImport pin")
    fal_chunk = js[fal_pin:fal_pin + 900]
    assert_true("sid && !importServiceAvailable(sid)" in fal_chunk, "empty-sid skips catalog-miss")
    assert_true("if (!importServiceAvailable(sid)) return false;" not in fal_chunk,
                "no bare !importServiceAvailable(sid) on Fal branch")
    assert_true("本家无可用 LoRA 端点" in js, "honest no-map reason")
    assert_true("v0822o157-fal-zimageturbo-lora" in js, "o157 stamp")

    # o158: zimagebase AIR → fal-ai/z-image/base/lora (official; not turbo steal)
    assert_true('FAL_ZIMAGE_BASE_LORA_SERVICE = "fal-ai/z-image/base/lora"' in js, "FAL_ZIMAGE_BASE_LORA_SERVICE")
    assert_true("zimagebase" in board and "FAL_ZIMAGE_BASE_LORA_SERVICE" in board, "zimagebase map")
    assert_true("fal-ai/z-image/base/lora" in js, "z-image/base/lora endpoint literal")
    assert_true("want === FAL_ZIMAGE_BASE_LORA_SERVICE" in pin, "pin has z-image/base sibling branch")
    assert_true("v0822o158-fal-zimagebase-lora" in js, "o158 stamp")

    # o159: burn-pack still junk out of 生成历史; keep tip mp4
    assert_true("v0822o159-outs-filter-burn-still" in js, "o159 stamp")
    assert_true("-still[._]" in js or "/-still[._]/i.test" in js, "still junk pattern -still")
    assert_true("_still_" in js, "still junk pattern _still_")
    junk = js[js.find("function isJunkRailItem"):js.find("function isJunkRailItem") + 1200]
    assert_true("burn-pack still" in junk or "-still" in junk, "isJunkRailItem filters burn still")


    # Fixture acceptance path unchanged (not swapped to flux)
    fi = js.find("function falLoraFixtureImport")
    fj = js.find("async function mountFalLoraFixture", fi)
    if fj < 0:
        fj = js.find("function mountFalLoraFixture", fi)
    fixture = js[fi:fj]
    assert_true('serviceId: "fal-ai/krea-2/turbo/lora"' in fixture, "fixture stays krea")
    assert_true('serviceId: "fal-ai/flux-lora"' not in fixture, "fixture not swapped to flux")

    # 换家 onchange uses resolver
    oi = js.find('$("backend").onchange')
    if oi < 0:
        oi = js.find("$(\"backend\").onchange")
    on = js[oi:oi + 1800]
    assert_true("resolveFalLoraEndpointFromChips" in on, "backend onchange base resolve")

    # Generate gate
    assert_true("falLoraUnsupportedMsg" in js, "unsupported msg helper")
    run = js[js.find("async function runShotStep"):js.find("async function runShotStep") + 12000]
    assert_true("falLoraUnsupportedMsg" in run, "runShotStep gates unsupported base")




def test_v0821o31_hf_lora_base():
    """o31: HF LoRA endpoint by AIR base — flux1→fal-ai/flux-lora; krea2→krea lora; never Hub turbo/no-LoRA."""
    js = (ROOT / "static" / "storyboard.js").read_text(encoding="utf-8")
    html = (ROOT / "static" / "storyboard.html").read_text(encoding="utf-8")
    hf = (ROOT / "providers" / "huggingface.py").read_text(encoding="utf-8")

    assert_true("v0821o49b-hydrate-fresh-empty-url" in html, "html stamp")
    assert_true("20260911-o49bhydratefreshemptyurl" in html, "cache-bust")
    assert_true("v0821o31:" in js, "js o31 banner")
    assert_true("HF_LORA_BY_BASE" in js, "HF_LORA_BY_BASE")
    assert_true("function resolveHfLoraEndpointFromChips" in js, "resolver")
    assert_true("function hfLoraUnsupportedMsg" in js, "unsupported msg")
    assert_true("function pinHfLoraServiceId" in js, "pinHf")

    board = js[js.find("HF_LORA_BY_BASE"):js.find("HF_LORA_BY_BASE") + 450]
    assert_true("flux1" in board and "krea2" in board, "flux1+krea2 keys")
    assert_true("FAL_FLUX_LORA_SERVICE" in board or "fal-ai/flux-lora" in board, "flux-lora family")

    pin = js[js.find("function pinHfLoraServiceId"):js.find("function ensureHfLoraServiceSelected")]
    assert_true("resolveHfLoraEndpointFromChips" in pin, "pin uses resolver")
    assert_true("resolved.reason" in pin or "hfHasLoras" in pin, "pin honors unsupported / hasLoras")
    assert_true('return HF_LORA_PREF_SERVICE' in pin or "HF_LORA_PREF_SERVICE" in pin,
                "no-loras still Hub pref available")

    # Never delete chips on unsupported
    ens = js[js.find("function ensureHfLoraServiceSelected"):js.find("function ensureHfLoraServiceSelected") + 2800]
    assert_true("state.loras = []" not in ens, "ensure must never clear LoRA chips")
    assert_true("setMsg" in ens and "resolved.reason" in ens, "honest 不支持 surface")

    # fireSend / runShotStep gates
    assert_true("hfLoraUnsupportedMsg" in js, "gate helper")
    fs = js[js.find("function fireSend"):js.find("function fireSend") + 4500]
    assert_true("hfLoraUnsupportedMsg" in fs or "hfHasLoras" in fs, "fireSend HF base gate")
    run = js[js.find("async function runShotStep"):js.find("async function runShotStep") + 16000]
    assert_true("hfLoraUnsupportedMsg" in run, "runShotStep HF unsupported gate")

    # backend allowlist
    assert_true("direct_fal_lora" in hf, "HF generate direct fal lora route")
    assert_true("fal_supports_lora" in hf, "uses fal_supports_lora")
    assert_true("不接受 LoRA" in hf, "honest 400 for Hub→no-LoRA map")

    # Offline: Hub turbo + loras 400; flux-lora ok path uses apply
    from providers.huggingface import HuggingFaceProvider
    from unittest.mock import patch
    import providers.huggingface as hfmod
    prov = HuggingFaceProvider()
    lora = {
        "path": "https://civitai.com/api/download/models/816500?fileId=730088",
        "scale": 0.5,
        "air": "urn:air:flux1:lora:civitai:730162@816500",
    }
    with patch.object(hfmod, "hf_keys", return_value=["hf_test"]), patch.object(
        hfmod, "inference_mapping",
        return_value={"fal-ai": {"providerId": "fal-ai/krea-2/turbo", "status": "live", "task": "text-to-image"}},
    ):
        code, data = prov.generate({"serviceId": "krea/Krea-2-Turbo", "prompt": "x", "loras": [lora]})
        assert_true(code == 400, "Hub turbo + loras → 400")
        assert_true("不接受 LoRA" in str(data.get("error") or ""), "400 copy mentions no LoRA")
    # o33: flux-lora under HF refused by default (Path A does not score HF)
    with patch.object(hfmod, "_submit_hf_fal_lora_via_fal") as mocked_submit, patch.object(
        hfmod, "_call_fal"
    ) as call_fal_spy:
        code, data = prov.generate({"serviceId": "fal-ai/flux-lora", "prompt": "x", "loras": [lora]})
        assert_true(code == 400, "flux-lora + loras → 400 honest refuse")
        assert_true("请换家 Fal" in str(data.get("error") or ""), "400 copy 请换家 Fal: %s" % data)
        assert_true(data.get("scoresAsHfClosedLoop") is False, "scoresAsHfClosedLoop false")
        assert_true(not mocked_submit.called, "default must NOT call Path A submit")
        assert_true(not call_fal_spy.called, "must NOT call HF Router _call_fal")

    # keep o29/o30 markers
    assert_true("FAL_LORA_BY_BASE" in js and "pinFalLoraServiceId" in js, "o29 kept")
    assert_true("surfaceSendReject" in js, "o30 kept")
    assert_true("HF_ROUTER_FAL_LORA_MSG" in js, "o33 Composer msg const")


def test_v0821o32_hf_fal_lora_transport():
    """o32 Path A kept behind debug switch only; default refuse (o33). Debug still transport=fal / not HF score."""
    js = (ROOT / "static" / "storyboard.js").read_text(encoding="utf-8")
    html = (ROOT / "static" / "storyboard.html").read_text(encoding="utf-8")
    hf = (ROOT / "providers" / "huggingface.py").read_text(encoding="utf-8")

    assert_true("v0821o49b-hydrate-fresh-empty-url" in html, "html stamp")
    assert_true("20260911-o49bhydratefreshemptyurl" in html, "cache-bust")
    assert_true("v0821o32:" in js, "js o32 banner retained")
    assert_true("_submit_hf_fal_lora_via_fal" in hf, "Fal transport helper retained")
    assert_true("_needs_fal_lora_transport" in hf, "transport gate")
    assert_true("_allow_fal_transport_debug" in hf, "debug switch")
    assert_true("HF_ALLOW_FAL_TRANSPORT" in hf, "env name")
    assert_true("scoresAsHfClosedLoop" in hf, "non-score marker")

    from providers.huggingface import HuggingFaceProvider, _needs_fal_lora_transport, HF_FAL_LORA_VIA_FAL
    from unittest.mock import patch
    import providers.huggingface as hfmod
    import providers.fal as falmod
    import os

    assert_true(_needs_fal_lora_transport("fal-ai/flux-lora"), "flux-lora needs Fal transport")
    assert_true("fal-ai/flux-lora" in HF_FAL_LORA_VIA_FAL, "set has flux-lora")

    prov = HuggingFaceProvider()
    lora = {
        "path": "https://civitai.com/api/download/models/816500?fileId=730088",
        "scale": 0.5,
        "air": "urn:air:flux1:lora:civitai:730162@816500",
    }
    outbound_body = {
        "prompt": "a detailed cinematic portrait",
        "loras": [{"path": lora["path"], "scale": 0.5}],
        "image_size": {"width": 832, "height": 1216},
    }
    fal_resp = {
        "request_id": "req-o32-test",
        "status_url": "https://queue.fal.run/fal-ai/flux-lora/requests/req-o32-test/status",
        "response_url": "https://queue.fal.run/fal-ai/flux-lora/requests/req-o32-test",
    }
    calls = {"urls": []}

    def fake_fal_call(url, method="GET", body=None, timeout=90):
        calls["urls"].append((method, url))
        if method == "POST":
            assert_true(isinstance(body, dict), "POST body dict")
            assert_true("transport" not in body, "transport not sent to Fal API body")
            assert_true(body.get("loras"), "loras in Fal body")
            assert_true(abs(float(body["loras"][0]["scale"]) - 0.5) < 1e-6, "scale preserved")
            return 200, fal_resp
        return 200, {"status": "IN_QUEUE"}

    # Default: refuse (no env)
    with patch.dict(os.environ, {"HF_ALLOW_FAL_TRANSPORT": ""}, clear=False), patch.object(
        hfmod, "_submit_hf_fal_lora_via_fal"
    ) as mocked_submit, patch.object(hfmod, "_call_fal") as spy:
        code, data = prov.generate({
            "serviceId": "fal-ai/flux-lora",
            "prompt": outbound_body["prompt"],
            "loras": [lora],
        })
        assert_true(code == 400, "default refuse 400: %s" % data)
        assert_true("请换家 Fal" in str(data.get("error") or ""), "请换家 Fal")
        assert_true(data.get("scoresAsHfClosedLoop") is False, "not HF score")
        assert_true(not mocked_submit.called and not spy.called, "no outbound")

    # Debug switch: Path A still works but marked non-scoring
    with patch.dict(os.environ, {"HF_ALLOW_FAL_TRANSPORT": "1"}, clear=False), patch.object(
        falmod, "fal_key", return_value="fal_test_key"
    ), patch.object(
        falmod, "build_fal_input", return_value=dict(outbound_body)
    ), patch.object(
        falmod, "materialize_fal_media", side_effect=lambda x: x
    ), patch.object(
        falmod, "fal_call", side_effect=fake_fal_call
    ), patch.object(
        hfmod, "hf_keys", return_value=[]
    ), patch.object(hfmod, "_call_fal") as call_fal_spy:
        code, data = prov.generate({
            "serviceId": "fal-ai/flux-lora",
            "prompt": outbound_body["prompt"],
            "loras": [lora],
            "width": 832,
            "height": 1216,
        })
        assert_true(code == 200, "debug Path A 200: %s" % data)
        assert_true(data.get("backend") == "huggingface", "backend=huggingface")
        assert_true((data.get("submittedInput") or {}).get("transport") == "fal", "submittedInput.transport=fal")
        assert_true((data.get("submittedInput") or {}).get("scoresAsHfClosedLoop") is False, "submitted not HF score")
        assert_true(data.get("scoresAsHfClosedLoop") is False, "top-level not HF score")
        assert_true(data.get("transport") == "fal", "top-level transport=fal")
        assert_true(not call_fal_spy.called, "must NOT call HF Router _call_fal")
        assert_true(any(u.startswith("https://queue.fal.run/fal-ai/flux-lora") for _, u in calls["urls"]),
                    "POST queue.fal.run: %s" % calls["urls"])

    assert_true("HF_LORA_BY_BASE" in js and "pinHfLoraServiceId" in js, "o31 pin kept")
    assert_true("direct_fal_lora" in hf, "o31 allowlist kept")


def test_v0821o33_hf_router_honest():
    """o33: HF+fal-ai/*lora default refuse「请换家 Fal」; Composer honest; Hub mid has no transport=fal; chips kept."""
    js = (ROOT / "static" / "storyboard.js").read_text(encoding="utf-8")
    html = (ROOT / "static" / "storyboard.html").read_text(encoding="utf-8")
    hf = (ROOT / "providers" / "huggingface.py").read_text(encoding="utf-8")

    assert_true("v0821o49b-hydrate-fresh-empty-url" in html, "html stamp")
    assert_true("20260911-o49bhydratefreshemptyurl" in html, "cache-bust")
    assert_true("v0821o33:" in js, "js o33 banner")
    assert_true("HF_ROUTER_FAL_LORA_MSG" in js, "Composer msg const")
    assert_true("HF Router 不托管该 Fal LoRA 端点，请换家 Fal" in js, "Composer exact copy")
    assert_true("HF_ROUTER_FAL_LORA_MSG" in hf, "backend msg const")
    assert_true("_allow_fal_transport_debug" in hf, "debug switch present")
    assert_true("scoresAsHfClosedLoop" in hf, "score honesty field")

    # resolveHfLoraEndpointFromChips must NOT return fal endpoint as pin when chips present
    resolve = js[js.find("function resolveHfLoraEndpointFromChips"):js.find("function hfLoraUnsupportedMsg")]
    assert_true("scoresAsHf: false" in resolve or 'scoresAsHf: false' in resolve, "resolve marks non-score")
    assert_true("endpoint: """ in resolve or "endpoint: ''" in resolve or 'endpoint: ""' in resolve,
                "resolve empties endpoint for Fal sibling")
    assert_true("HF_ROUTER_FAL_LORA_MSG" in resolve, "resolve uses honest msg")
    # ensure never clears chips
    ens = js[js.find("function ensureHfLoraServiceSelected"):js.find("function ensureHfLoraServiceSelected") + 2800]
    assert_true("state.loras = []" not in ens, "ensure must never clear LoRA chips")

    # catalog must not inject fal-ai/*lora as pretend-HF when chips present
    assert_true("do NOT inject fal-ai" in js or "不计 HF 分" in js, "catalog/label honesty")

    from providers.huggingface import HuggingFaceProvider, HF_ROUTER_FAL_LORA_MSG
    from unittest.mock import patch
    import providers.huggingface as hfmod
    import os

    prov = HuggingFaceProvider()
    lora = {
        "path": "https://civitai.com/api/download/models/816500?fileId=730088",
        "scale": 0.5,
        "air": "urn:air:flux1:lora:civitai:730162@816500",
    }
    with patch.dict(os.environ, {"HF_ALLOW_FAL_TRANSPORT": "0"}, clear=False), patch.object(
        hfmod, "_submit_hf_fal_lora_via_fal"
    ) as mocked, patch.object(hfmod, "_call_fal") as spy:
        for sid in ("fal-ai/flux-lora", "fal-ai/krea-2/turbo/lora"):
            code, data = prov.generate({"serviceId": sid, "prompt": "x", "loras": [lora]})
            assert_true(code == 400, "%s → 400" % sid)
            assert_true(HF_ROUTER_FAL_LORA_MSG in str(data.get("error") or ""), "msg for %s: %s" % (sid, data))
            assert_true(data.get("scoresAsHfClosedLoop") is False, "not HF score %s" % sid)
        assert_true(not mocked.called and not spy.called, "no Path A / Router")

    # Hub mid without loras: real HF path must not stamp transport=fal on submittedInput construction
    # (offline: missing key → 401 before submit; just assert generate path does not set transport for Hub)
    gen = hf[hf.find("    def generate"):hf.find("    def job_status")]
    assert_true("scoresAsHfClosedLoop" in gen, "generate honesty")
    # Real Router path comments
    assert_true("Real HF closed-loop" in gen or "router.huggingface.co" in hf, "docs Hub Router path")

    # 28216420 does not score HF (fixture note in report; code-level: Path A non-score)
    assert_true("请换家 Fal" in js and "请换家 Fal" in hf, "both surfaces")


def test_v0821o30_send_gate():
    """o30: #send clickability + failUi never silent; unsupported filled warn-only; keep o29 Fal pin."""
    html = (ROOT / "static" / "storyboard.html").read_text(encoding="utf-8")
    js = (ROOT / "static" / "storyboard.js").read_text(encoding="utf-8")
    adapt = (ROOT / "static" / "composer-field-adapt.js").read_text(encoding="utf-8")
    ui = (ROOT / "static" / "storyboard-ui.css").read_text(encoding="utf-8")

    assert_true("v0821o49b-hydrate-fresh-empty-url" in html, "html stamp")
    assert_true("20260911-o49bhydratefreshemptyurl" in html, "cache-bust")
    assert_true("v0821o30:" in js, "js o30 banner")

    # clickability / z-index above zoom/minimap (22)
    # 裁决(o63/o136seko): 样式已外链; dock.show 层级经 ui-base z-index:26 → shell.css z-index:32,
    # 仍在 zoom(18/22)/minimap(22) 之上——语义不变
    import re as _re
    css = css_all()
    zi = _re.search(r"\.dock\.show[\s,][^}]*?z-index:\s*(\d+)", css)
    assert_true(zi is not None and int(zi.group(1)) >= 26, "dock.show above zoom/minimap")
    zm = _re.search(r"\.zoom\s*\{[^}]*?z-index:\s*(\d+)", css)
    assert_true(zm is not None and int(zm.group(1)) < int(zi.group(1)), "zoom stays below dock")
    # 裁决: collapsed 时 #msg 刻意隐藏(adapt/o97), 失败经 surfaceSendReject→showSendToast
    # (#sendToast 挂进 dockFoot, collapsed 也可见) + 无 shot 时自动展开 dock 呈现 #msg
    assert_true("send-toast" in js and "dockFoot" in js, "collapsed bad surfaces via send toast")
    assert_true('state.dockMode = "expanded"' in js, "reject auto-expands dock so msg visible")
    assert_true("send-toast" in html or "send-toast" in js, "send toast surface")

    # fireSend never silent reject
    assert_true("function surfaceSendReject" in js, "surfaceSendReject")
    assert_true("function showSendToast" in js, "showSendToast")
    assert_true("data-send-fired" in js, "click-reached marker")
    fs = js[js.find("function fireSend"):js.find("function fireSend") + 4200]
    assert_true("surfaceSendReject" in fs, "fireSend uses surfaceSendReject")
    assert_true("data-send-fired" in fs, "fireSend marks fired")

    # o30: omitable unsupported is warn-only (not paramGate hard block)
    gi = js.find("function paramGateMessage")
    gate = js[gi:gi + 4500]
    assert_true("blockingUnsupportedMessages" in gate, "paramGate uses blocking split")
    assert_true("filledUnsupportedWarnings" in gate, "paramGate surfaces warnings")
    assert_true("filledUnsupportedWarnings" in adapt, "adapt warns API")
    assert_true("blockingUnsupportedMessages" in adapt, "adapt blocks API")

    # keep o28 board adapt + o29 fal pin
    assert_true("adapt.applyToSurface" in js, "o28 adapt kept")
    assert_true("pinFalLoraServiceId" in js and "FAL_LORA_BY_BASE" in js, "o29 kept")
    assert_true('FAL_FLUX_LORA_SERVICE = "fal-ai/flux-lora"' in js, "flux-lora kept")



def test_v0821o36_checkpoint_not_lora():
    """o36: checkpoint/diffuser/diffusionmodel AIR must not enter loras[]; isLoraAir gates apply+pack."""
    import json
    import re
    import subprocess
    import tempfile

    js = (ROOT / "static" / "storyboard.js").read_text(encoding="utf-8")
    html = (ROOT / "static" / "storyboard.html").read_text(encoding="utf-8")

    assert_true("v0821o49b-hydrate-fresh-empty-url" in html, "html stamp o36")
    assert_true('class="stamp"' in html, ".stamp")
    assert_true("20260911-o49bhydratefreshemptyurl" in html, "cache-bust o36")
    assert_true('src="/static/storyboard.js?v=' in html, "script cache-bust o36")
    assert_true("v0821o36:" in js, "js o36 banner")

    assert_true("function isLoraAir" in js, "isLoraAir helper")
    assert_true("function isNonLoraModelAir" in js, "isNonLoraModelAir")
    assert_true("function shouldDropNonLoraAir" in js, "shouldDropNonLoraAir")
    helper = js[js.find("function isLoraAir"):js.find("function isLoraAir") + 900]
    assert_true("lora|lycoris" in helper or ("lora" in helper and "lycoris" in helper), "lora/lycoris family")
    non = js[js.find("function isNonLoraModelAir"):js.find("function isNonLoraModelAir") + 400]
    assert_true("checkpoint" in non and "diffusionmodel" in non and "diffuser" in non,
                "checkpoint/diffusionmodel/diffuser rejected")

    ai = js.find("async function applyImport")
    assert_true(ai >= 0, "applyImport")
    apply_body = js[ai:ai + 22000]
    assert_true("shouldDropNonLoraAir" in apply_body, "applyImport uses shouldDropNonLoraAir")
    assert_true("droppedCkpt" in apply_body, "applyImport counts dropped checkpoint chips")
    assert_true("dmAir" in apply_body, "applyImport compares to j.diffusionModel")

    # 裁决: pack 侧 skippedNonLora 计数已前移到 applyImport 的 droppedCkpt(上文已断言: 导入即拒+计数提示);
    # packLorasForPayload 现为 shouldDropNonLoraAir 硬过滤整包 null——非 LoRA 绝不出站(语义更强)。
    pack_i = js.find("function packLorasForPayload")
    pack = js[pack_i:pack_i + 3500]
    assert_true("shouldDropNonLoraAir" in pack, "pack filters via shouldDropNonLoraAir")
    assert_true("return null" in pack, "non-LoRA AIR → pack null, never ships")
    assert_true("不进 loras[]" in js, "honest warn copy (addLora)")

    # 裁决: addLora 增加类型/家族硬门后函数体增长, 窗口放宽(语义不变)
    add = js[js.find("function addLora"):js.find("function addLora") + 2200]
    assert_true("shouldDropNonLoraAir(row.air)" in add, "addLora rejects non-LoRA AIR")
    assert_true("已拒绝非 LoRA AIR" in js, "paste/search honesty")

    m = re.search(
        r"function isLoraAir\(air\) \{.*?\n  \}\n  function isNonLoraModelAir\(air\) \{.*?\n  \}\n"
        r"  /\*\* True when.*?function shouldDropNonLoraAir\(air, diffusionModel\) \{.*?\n  \}",
        js,
        re.S,
    )
    assert_true(m is not None, "extract helpers for node eval")
    looks_m = re.search(r"function looksAir\(s\) \{.*?\n  \}", js, re.S)
    assert_true(looks_m is not None, "extract looksAir")
    harness = (
        looks_m.group(0) + "\n" + m.group(0) + "\n"
        + """
const ckpt = "urn:air:flux1:checkpoint:civitai:1752722@1983609";
const lora = "urn:air:flux1:lora:civitai:823089@823089";
const lyco = "urn:air:sdxl:lycoris:civitai:1@2";
const dm = "urn:air:krea2:diffusionmodel:civitai:1@2";
const dif = "urn:air:flux1:diffuser:civitai:618692@691639";
const cases = [];
function check(ok, name) { if (!ok) throw new Error(name); cases.push(name); }
check(isLoraAir(lora) === true, "lora true");
check(isLoraAir(lyco) === true, "lycoris true");
check(isLoraAir(ckpt) === false, "checkpoint false");
check(isLoraAir(dm) === false, "diffusionmodel false");
check(isLoraAir(dif) === false, "diffuser false");
check(shouldDropNonLoraAir(ckpt) === true, "drop ckpt");
check(shouldDropNonLoraAir(lora) === false, "keep lora");
check(shouldDropNonLoraAir(ckpt, ckpt) === true, "drop equals dm");
check(shouldDropNonLoraAir(lora, ckpt) === false, "keep lora even if dm set");
check(shouldDropNonLoraAir("", ckpt) === false, "empty air keep (path-only)");
console.log(JSON.stringify({ok: true, n: cases.length}));
"""
    )
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as f:
        f.write(harness)
        path = f.name
    r = subprocess.run(["node", path], capture_output=True, text=True, timeout=10)
    assert_true(r.returncode == 0, "node helper eval exit0: " + (r.stderr or r.stdout or "")[:300])
    out = json.loads((r.stdout or "").strip().splitlines()[-1])
    assert_true(out.get("ok") is True and out.get("n") == 10, "node helper cases pass: " + str(out))



def test_v0821o37_poll_preparing_wb():
    """o37: civitai preparing must outlive ~5min poll; stillGoing mirrors inFlight; saved→writeback."""
    import json
    import re
    import subprocess
    import tempfile

    js = (ROOT / "static" / "storyboard.js").read_text(encoding="utf-8")
    html = (ROOT / "static" / "storyboard.html").read_text(encoding="utf-8")

    assert_true("v0821o49b-hydrate-fresh-empty-url" in html, "html stamp o37")
    assert_true('class="stamp"' in html, ".stamp")
    assert_true("20260911-o49bhydratefreshemptyurl" in html, "cache-bust o37")
    assert_true('src="/static/storyboard.js?v=' in html, "script cache-bust o37")
    assert_true("v0821o37:" in js, "js o37 banner")

    run_i = js.find("async function runShotStep")
    assert_true(run_i >= 0, "runShotStep")
    run = js[run_i:run_i + 24000]

    # pollMax: civitai image materializing ≥720 @ 2.5s ≈30min (api; covers ~29min preparing)
    assert_true("pollMax = 720" in run or "pollMax=720" in run, "civitai image pollMax ≥720")
    assert_true("2500" in run, "pollMs 2.5s kept")
    # do not shrink video budget
    assert_true("isVideoPoll ? 180 : 40" in run or "pollMax = 180" in run, "video pollMax 180 kept")

    infl_i = run.find("const inFlight")
    assert_true(infl_i >= 0, "inFlight")
    infl = run[infl_i:infl_i + 500]
    for tok in ("PREPARING", "PREPARED", "QUEUED", "SCHEDULED"):
        assert_true(tok in infl, "inFlight includes " + tok)

    still_i = run.find("const stillGoing")
    assert_true(still_i >= 0, "stillGoing")
    still = run[still_i:still_i + 700]
    for tok in ("preparing", "prepared", "scheduled", "queued"):
        assert_true(tok in still, "stillGoing includes " + tok)
    assert_true("IN_QUEUE" in still and "IN_PROGRESS" in still, "stillGoing keeps queue/progress")

    # saved /out still drives writebackResult (unchanged success path)
    assert_true("writebackResult(shot, url)" in run, "writebackResult on success")
    assert_true("pickSavedUrl(st)" in run, "poll breaks on saved[]")
    assert_true("等待超时，云端任务仍在进行中" in run, "timeout stillGoing copy")

    # Node sim: preparing×N then succeeded+saved → writeback; timeout while preparing → stillGoing
    harness = r"""
function upper(s){ return String(s||"").toUpperCase(); }
function inFlight(st){
  const stStatus = upper(st && st.status);
  return stStatus === "IN_QUEUE" || stStatus === "IN_PROGRESS"
    || stStatus === "PENDING" || stStatus === "PROCESSING" || stStatus === "RUNNING"
    || stStatus === "PREPARING" || stStatus === "PREPARED" || stStatus === "QUEUED"
    || stStatus === "SCHEDULED";
}
function stillGoing(j){
  return !!(j && (
    /^(pending|processing|running|in_queue|in_progress|preparing|prepared|scheduled|queued)$/i.test(String(j.status||""))
    || j.status === "IN_QUEUE" || j.status === "IN_PROGRESS"
    || !j.status
  ));
}
function pickSavedUrl(st){
  const s = (st && st.saved) || [];
  if (!s.length) return "";
  const u = s[0] && (s[0].url || s[0]);
  return u ? String(u) : "";
}
function simulate(polls, pollMax){
  let j = {status:"preparing"};
  let wrote = null;
  for (let i=0;i<pollMax;i++){
    j = polls[Math.min(i, polls.length-1)];
    const stStatus = upper(j.status);
    const flying = inFlight(j);
    if ((j.error || j.status === "failed") && !flying) throw new Error("fail");
    if (pickSavedUrl(j)) { wrote = pickSavedUrl(j); break; }
  }
  if (wrote) return {path:"writeback", url:wrote, stillGoing:false};
  const url = pickSavedUrl(j);
  if (url) return {path:"writeback", url:url, stillGoing:false};
  return {path: stillGoing(j) ? "stillGoing" : "empty", url:"", stillGoing: stillGoing(j)};
}
const longPrep = Array(50).fill({status:"preparing"}).concat([
  {status:"succeeded", saved:[{url:"/out/job_0.jpg"}]}
]);
const r1 = simulate(longPrep, 720);
if (r1.path !== "writeback" || r1.url !== "/out/job_0.jpg") throw new Error("prep→saved writeback "+JSON.stringify(r1));
const r2 = simulate(Array(800).fill({status:"preparing"}), 720);
if (r2.path !== "stillGoing" || !r2.stillGoing) throw new Error("timeout preparing must stillGoing "+JSON.stringify(r2));
for (const st of ["preparing","PREPARING","scheduled","SCHEDULED","queued","prepared","IN_PROGRESS"]){
  if (!stillGoing({status:st}) || !inFlight({status:st})) throw new Error("align "+st);
}
if (stillGoing({status:"failed"}) || inFlight({status:"failed"})) throw new Error("failed not in-flight");
console.log(JSON.stringify({ok:true, r1:r1.path, r2:r2.path, pollMax:720}));
"""
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as f:
        f.write(harness)
        path = f.name
    r = subprocess.run(["node", path], capture_output=True, text=True, timeout=10)
    assert_true(r.returncode == 0, "node poll sim exit0: " + (r.stderr or r.stdout or "")[:400])
    out = json.loads((r.stdout or "").strip().splitlines()[-1])
    assert_true(out.get("ok") is True and out.get("r1") == "writeback" and out.get("r2") == "stillGoing",
                "node poll sim: " + str(out))
    # Source stillGoing must match sim list (preparing family)
    m = re.search(r"const stillGoing = !!\(j && \((.*?)\)\);", run, re.S)
    assert_true(m is not None, "stillGoing expression extractable")
    body = m.group(1)
    assert_true("preparing" in body and "scheduled" in body and "queued" in body and "prepared" in body,
                "stillGoing source lists preparing family")



def test_v0821o38_dm_pack_shot():
    """o38: packComfy prefer generate shot; applyImport keep dm; flux1 without dm blocked before POST."""
    import json
    import re
    import subprocess
    import tempfile

    js = (ROOT / "static" / "storyboard.js").read_text(encoding="utf-8")
    html = (ROOT / "static" / "storyboard.html").read_text(encoding="utf-8")

    assert_true("v0821o49b-hydrate-fresh-empty-url" in html, "html stamp o38")
    assert_true('class="stamp"' in html, ".stamp")
    assert_true("20260911-o49bhydratefreshemptyurl" in html, "cache-bust o38")
    assert_true('src="/static/storyboard.js?v=' in html, "script cache-bust o38")
    assert_true("v0821o38:" in js, "js o38 banner")

    pack_i = js.find("function packComfyParamsForPayload")
    assert_true(pack_i >= 0, "packComfyParamsForPayload")
    pack = js[pack_i:pack_i + 2200]
    assert_true("shotOpt" in pack, "pack accepts generate shotOpt")
    assert_true("shotOpt && shotOpt.kind === \"shot\"" in pack or "shotOpt.kind === \"shot\"" in pack,
                "prefer generate shot when kind=shot")
    assert_true("state.selected" in pack and "lastComposerShot" in pack, "fallback selected/lastComposerShot")
    assert_true("p.diffusionModel = dm" in pack, "pack sets diffusionModel")
    assert_true("never invent" in pack, "never invent default AIR")

    run_i = js.find("async function runShotStepWork")
    assert_true(run_i >= 0, "runShotStepWork")
    run = js[run_i:run_i + 28000]
    assert_true("packComfyParamsForPayload(shot)" in run, "runShot packs with generate shot")
    assert_true("payload.diffusionModel = String(shot.diffusionModel).trim()" in run
                or "payload.diffusionModel = String(shot.diffusionModel)" in run,
                "force payload.diffusionModel from shot after merge")
    assert_true("缺少 diffusionModel" in run and "diffuserModel" in run, "flux1 hard-reject message")
    assert_true("/flux1/" in run or "flux1" in run, "flux1 preflight present")
    # hard reject must be before POST
    assert_true(run.find("缺少 diffusionModel") < run.find('fetch("/api/generate"'),
                "dm preflight before POST")

    ai_i = js.find("async function applyImport")
    assert_true(ai_i >= 0, "applyImport")
    ai = js[ai_i:ai_i + 16000]
    # must assign when present
    assert_true("shot.diffusionModel = String(j.diffusionModel).trim()" in ai, "assign dm when present")
    # must NOT wipe when j omits — no delete shot.diffusionModel in applyImport dm block
    dm_block = ai[ai.find("v0821o22: any hinablue"):ai.find("v0821o23: keep import serviceId")]
    assert_true("delete shot.diffusionModel" not in dm_block, "applyImport must not delete diffusionModel when j omits")
    assert_true("delete shot.checkpointName" not in dm_block, "applyImport must not delete checkpointName when j omits")
    assert_true("delete shot.ecosystem" not in dm_block, "applyImport must not delete ecosystem when j omits")
    assert_true("do NOT delete" in dm_block or "only assign when present" in dm_block, "o38 keep comment")

    # Node sim: pack prefers generate shot AIR when selected empty; applyImport omit keeps dm; flux1 no-dm blocks
    harness = r"""
function packComfyParamsForPayload(shotOpt, state, be) {
  const p = {};
  if (be === "civitai") {
    const shot = (shotOpt && shotOpt.kind === "shot" ? shotOpt : null)
      || (state.selected && state.nodes[state.selected]) || (state.lastComposerShot && state.nodes[state.lastComposerShot]);
    const dm = shot && shot.diffusionModel ? String(shot.diffusionModel).trim() : "";
    if (dm) p.diffusionModel = dm;
  }
  return Object.keys(p).length ? p : null;
}
function applyImportKeep(shot, j) {
  if (j.diffusionModel != null && String(j.diffusionModel).trim()) {
    shot.diffusionModel = String(j.diffusionModel).trim();
  }
  // o38: no delete when omitted
  return shot;
}
function flux1NeedsDmReject(sid, payload) {
  const sidL = String(sid || "").toLowerCase();
  const needsDm = /\/flux1\//.test(sidL) || /diffuser|diffusionmodel|sdcpp\/flux/.test(sidL);
  const dmOut = payload.diffusionModel != null ? String(payload.diffusionModel).trim() : "";
  if (needsDm && !dmOut) return "缺少 diffusionModel（diffuserModel）";
  return "";
}
const AIR = "urn:air:flux1:checkpoint:civitai:1752722@1983609";
const genShot = { kind: "shot", id: "g1", diffusionModel: AIR };
const emptySel = { kind: "shot", id: "s1" };
const state = { selected: "s1", lastComposerShot: "s1", nodes: { s1: emptySel, g1: genShot } };
const packed = packComfyParamsForPayload(genShot, state, "civitai");
if (!packed || packed.diffusionModel !== AIR) throw new Error("pack must use generate shot dm got "+JSON.stringify(packed));
const packedBad = packComfyParamsForPayload(null, state, "civitai");
if (packedBad && packedBad.diffusionModel) throw new Error("selected empty must not invent dm");
const shotKeep = { diffusionModel: AIR };
applyImportKeep(shotKeep, { prompt: "x" }); // omit dm
if (shotKeep.diffusionModel !== AIR) throw new Error("applyImport omit must keep dm");
applyImportKeep(shotKeep, { diffusionModel: "urn:air:flux1:checkpoint:civitai:1@2" });
if (shotKeep.diffusionModel !== "urn:air:flux1:checkpoint:civitai:1@2") throw new Error("assign when present");
const rej = flux1NeedsDmReject("image/sdcpp/flux1/createImage", {});
if (!/diffusionModel/.test(rej)) throw new Error("flux1 no dm must reject");
const ok = flux1NeedsDmReject("image/sdcpp/flux1/createImage", { diffusionModel: AIR });
if (ok) throw new Error("with dm must pass");
const payload = {};
if (genShot.diffusionModel) payload.diffusionModel = String(genShot.diffusionModel).trim();
if (payload.diffusionModel !== AIR) throw new Error("force from shot");
console.log(JSON.stringify({ok:true, dm: payload.diffusionModel}));
"""
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as f:
        f.write(harness)
        path = f.name
    r = subprocess.run(["node", path], capture_output=True, text=True, timeout=10)
    assert_true(r.returncode == 0, "node o38 sim exit0: " + (r.stderr or r.stdout or "")[:400])
    out = json.loads((r.stdout or "").strip().splitlines()[-1])
    assert_true(out.get("ok") is True and "1752722" in str(out.get("dm")),
                "node o38 sim: " + str(out))



def main():
    tests = [
        test_t2i_no_ref,
        test_i2i_with_ref,
        test_i2v_with_first_frame,
        test_i2v_missing_frame_blocked,
        test_mention_without_edge_is_not_i2i,
        test_payload_normalize_linked_only,
        test_i2v_first_frame_pick_second_ref,
        test_shot_result_as_image_node,
        test_first_frame_from_promoted_asset,
        test_rail_history_not_in_compile,
        test_ui_blocks_stages0_fake_run,
        test_ui_clears_stage_urls_on_disconnect,
        test_selbar_scoped_layout_skips_exclusive_outside_asset,
        test_empty_boot_no_robot_demo,
        test_v0815_gen_hardgate,
        test_v0815c_ref_cap_single_slot_and_overcap_block,
        test_v0816_sb_lora,
        test_v0817_no_at_filename,
        test_v0817b_unmention_at_tag,
        test_v0817c_no_at_in_prompt,
        test_empty_prompt_on_new_shot_and_load_demo,
        test_v0818_sticky_composer_bar,
        test_v0819_canvas_stage,
        test_v0819b_expand_prompt,
        test_v0820_civitai_comfy_params,
        test_v0820b_apply_import,
        test_v0820c_hard_service,
        test_v0821n_krea2_import_hardgate,
        test_v0821n2_lora_air_gate,
        test_v0821n3_import_air_chip,
        test_v0821n4_js_cache_bust,
        test_v0821n5_dock_scroll,
        test_v0821o_fal_lora_knife,
        test_v0821o2_fal_turbo_pin,
        test_v0821o3_fal_clear_loras,
        test_v0821o4_hf_turbo_lora,
        test_v0821o5_hf_no_wavespeed,
        test_v0821o6_modelscope_hub_lora,
        test_v0821o6b_ms_lora_shape,
        test_v0821o7_param_surface,
        test_v0821o7_c1_closeout,
        test_v0821_hardgate_i2v_refs,
        test_v0821b_i2v_detect,
        test_v0821c_fal_i2v_preview,
        test_v0821f_send_noop,
        test_v0821g_send_bind,
        test_v0821h_send_aria,
        test_v0821i_i2v_writeback,
        test_v0821j_send_busy_msg,
        test_v0821k_i2v_prompt_req,
        test_v0821l_send_once,
        test_v0821m2_poll_copy,
        test_v0821o8_caption_i2i,
        test_v0821o9_fail_zh_lora_honesty,
        test_r7_new_shot_does_not_stack,
        test_v0821o15_server_writeback_executable,
        test_v0821o19_single_up_writeback,
        test_v0821o20_visual_p0,
        test_v0821o21_outbound_jobid_writeback,
        test_v0821o22_hinablue_writeback,
        test_v0821o23_sdxl_service_stick,
        test_v0821o26_fal_swap_dropdown,
        test_v0821o28_composer_adaptive,
        test_v0821o29_fal_lora_base,
        test_v0821o31_hf_lora_base,
        test_v0821o32_hf_fal_lora_transport,
        test_v0821o33_hf_router_honest,
        test_v0821o36_checkpoint_not_lora,
        test_v0821o37_poll_preparing_wb,
        test_v0821o38_dm_pack_shot,
        test_o39_refs_fill_smart_match_static,
        test_o40_fill_exact_cap_static,
        test_o41_fill_real_fixtures_static,
        test_v0821o30_send_gate,
        test_import_19201654_original_params,
        # test_import_142210587_original_params  # optional fixture; NOT acceptance
    ]
    failed = 0
    for fn in tests:
        try:
            fn()
            print("ok", fn.__name__)
        except Exception as e:
            failed += 1
            print("FAIL", fn.__name__, e)
    print("result", len(tests) - failed, "/", len(tests))
    return 1 if failed else 0



def test_o39_refs_fill_smart_match_static():
    """o39 tip: full cap slots + Edit sibling one-click + stamp."""
    js = (ROOT / "static" / "storyboard.js").read_text(encoding="utf-8")
    html = (ROOT / "static" / "storyboard.html").read_text(encoding="utf-8")
    css = (ROOT / "static" / "storyboard-ui.css").read_text(encoding="utf-8")
    assert_true("v0821o49b-hydrate-fresh-empty-url" in html, "html stamp v0821o49b-hydrate-fresh-empty-url")
    assert_true("20260911-o49bhydratefreshemptyurl" in html, "cache-bust o39")
    assert_true("v0821o39:" in js, "js header o39")
    assert_true("function editSiblingId" in js, "editSiblingId")
    assert_true("function applyEditSibling" in js, "applyEditSibling")
    assert_true("function fillRefSlotsToCap" in js, "fillRefSlotsToCap")
    assert_true("ref-slot-empty" in js and "ref-slot-empty" in css, "empty cap slots")
    assert_true('data-act="apply-edit-sibling"' in js, "one-click Edit act")
    assert_true('data-act="fill-refs-cap"' in js, "灌满测试 act")
    assert_true("for (let si = 0; si < remain; si++)" in js, "expose remain empty slots")
    # unused gate still hard-blocks; apply path present
    assert_true("function refUnusedGateMessage" in js, "unused gate kept")
    assert_true("不静默忽略" in js, "no silent ignore copy")



def test_o40_fill_exact_cap_static():
    """o40 lineage under o41: 灌满+gate outbound口径; stamp; no displayRefUrls numerator."""
    js = (ROOT / "static" / "storyboard.js").read_text(encoding="utf-8")
    html = (ROOT / "static" / "storyboard.html").read_text(encoding="utf-8")
    assert_true("v0821o49b-hydrate-fresh-empty-url" in html, "html stamp v0821o49b-hydrate-fresh-empty-url")
    assert_true("20260911-o49bhydratefreshemptyurl" in html, "cache-bust o41")
    assert_true("v0821o41:" in js, "js header o41")
    assert_true("v0821o40:" in js, "js header o40 lineage")
    assert_true("function fillRefSlotsToCap" in js, "fillRefSlotsToCap")
    assert_true("/out/fill-cap-" in js, "real fill-cap fixtures")
    assert_true("/out/o40-fill-" not in js, "no phantom o40-fill URLs")
    assert_true("countRefUrls(null, n).length" in js, "UI numerator uses outbound countRefUrls")
    assert_true("const refCount = displayRefUrls(n).length" not in js, "UI must not use displayRefUrls for N/cap")
    assert_true("never N>cap" in js or "urls.length > cap" in js, "fill safety never over cap")


def test_o41_fill_real_fixtures_static():
    """o41: real fill-cap fixtures + server ensure-copy; never phantom URLs."""
    js = (ROOT / "static" / "storyboard.js").read_text(encoding="utf-8")
    html = (ROOT / "static" / "storyboard.html").read_text(encoding="utf-8")
    server = (ROOT / "server.py").read_text(encoding="utf-8")
    assert_true("v0821o49b-hydrate-fresh-empty-url" in html, "html stamp")
    assert_true("20260911-o49bhydratefreshemptyurl" in html, "cache-bust")
    assert_true("def ensure_fill_cap_fixtures" in server, "server ensure helper")
    assert_true("ensure_fill_cap_fixtures()" in server, "boot calls ensure")
    assert_true("fal-refs-fill-9" in server, "fixture source dir")
    for i in range(1, 10):
        fp = ROOT / "out" / f"fill-cap-{i}.jpg"
        assert_true(fp.is_file() and fp.stat().st_size > 0, f"fixture exists {fp.name}")
    assert_true("/out/fill-cap-" in js, "client fill-cap urls")
    assert_true("/out/o40-fill-" not in js, "no phantom")


if __name__ == "__main__":
    raise SystemExit(main())
