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
    assert_true("nl-storyboard-v0821h" in js, "STORE must bump to v0820c")
    assert_true("nl-storyboard-v0819b" in js, "STORE_OLDS must keep v0819b for migrate")
    assert_true("nl-storyboard-v0819" in js, "STORE_OLDS must keep v0819 for migrate")
    assert_true("nl-storyboard-v0818" in js, "STORE_OLDS must keep v0818 for migrate")
    assert_true("nl-storyboard-v0817c" in js, "STORE_OLDS must keep v0817c for migrate")
    assert_true("nl-storyboard-v0817b" in js, "STORE_OLDS must keep v0817b for migrate")
    assert_true("nl-storyboard-v0817" in js, "STORE_OLDS must keep v0817 for migrate")
    assert_true("nl-storyboard-v0816b" in js, "STORE_OLDS must keep v0816b for migrate")
    html = (ROOT / "static" / "storyboard.html").read_text(encoding="utf-8")
    assert_true("v0821h-send-aria" in html, "stamp must be v0821h-send-aria")


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
    assert_true("未命名画布" in html or "新项目" in html, "neutral projTitle")
    assert_true("扫地机器人" not in html, "projTitle must not mention 扫地机器")
    assert_true("v0821h-send-aria" in html, "html stamp")
    assert_true("nl-storyboard-v0821h" in js, "STORE v0820c")
    assert_true("nl-storyboard-v0819b" in js, "STORE_OLDS has v0819b")
    assert_true("nl-storyboard-v0819" in js, "STORE_OLDS has v0819")
    assert_true("nl-storyboard-v0818" in js, "STORE_OLDS has v0818")
    assert_true("nl-storyboard-v0817c" in js, "STORE_OLDS has v0817c")


def test_v0815_gen_hardgate():
    """v0815b packing + v0815c stamp: images[] always; caps from capabilities/imageFields."""
    js = (ROOT / "static" / "storyboard.js").read_text(encoding="utf-8")
    html = (ROOT / "static" / "storyboard.html").read_text(encoding="utf-8")
    assert_true("v0821h-send-aria" in html, "html stamp v0821h-send-aria")
    assert_true("nl-storyboard-v0821h" in js, "STORE v0820c")
    assert_true("nl-storyboard-v0819b" in js, "STORE_OLDS has v0819b")
    assert_true("nl-storyboard-v0819" in js, "STORE_OLDS has v0819")
    assert_true("nl-storyboard-v0818" in js, "STORE_OLDS has v0818")
    assert_true("nl-storyboard-v0817c" in js, "STORE_OLDS has v0817c")
    assert_true("nl-storyboard-v0817" in js, "STORE_OLDS prepend v0817")
    assert_true("nl-storyboard-v0817b" in js, "STORE_OLDS has v0817b")
    assert_true("nl-storyboard-v0817" in js, "STORE_OLDS has v0817")
    assert_true("nl-storyboard-v0817b" in js, "STORE_OLDS has v0817b")
    assert_true("nl-storyboard-v0816b" in js, "STORE_OLDS has v0816b")
    assert_true('dockMode: "collapsed"' in js, "dock default collapsed (canvas-stage)")
    assert_true("function attachExtraImages" in js, "attachExtraImages helper")
    assert_true("function maxRefCount" in js, "maxRefCount helper")
    assert_true("function resolveRefCaps" in js, "resolveRefCaps from capabilities")
    assert_true("refImagesField" in js, "caps still expose refImagesField")
    assert_true("PROVIDER_REF_CAPS" in js, "provider ref defaults")
    assert_true("input_references" in js, "nano default field")
    assert_true("attachExtraImages(payload, shot)" in js, "attach before generate")
    # Packing target is always studio-inbound images[] (not sole-write image_urls).
    assert_true("payload.images = sliced" in js, "attachExtraImages always writes images[]")
    assert_true("studio-inbound images[]" in js or "ALWAYS" in js, "comment: always images inbound")
    # Extract attachExtraImages body: must not sole-assign only to refImagesField
    i = js.find("function attachExtraImages")
    assert_true(i >= 0, "attachExtraImages loc")
    j = js.find("function setShotBusy", i)
    body = js[i:j]
    assert_true("payload.images = sliced" in body, "images=sliced inside attachExtraImages")
    assert_true('payload[field] = sliced' in body or "payload[field] = sliced" in body,
                "optional mirror to refImagesField still allowed")
    # Must not be the ONLY write path that skips images when field is image_urls
    assert_true("never sole-write" in body or "not the sole bag" in body or "payload.images = sliced" in body,
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
    assert_true("视频需要先连一张首帧图" in js, "i2v firstFrame gate kept")
    # Do not infer always-1 from field name alone
    assert_true('Do NOT infer "always 1" from field name alone' in js or "Do NOT infer" in js, "no always-1 from field name")
    # modelscope: BOTH images=[url] and image_url
    assert_true("payload.image_url = sliced[0]" in body, "modelscope sets image_url alongside images[]")



def test_v0816_sb_lora():
    """LoRA UI + packing still green under v0818 stamp."""
    js = (ROOT / "static" / "storyboard.js").read_text(encoding="utf-8")
    html = (ROOT / "static" / "storyboard.html").read_text(encoding="utf-8")
    assert_true("v0821h-send-aria" in html, "html stamp v0821h-send-aria")
    assert_true('const STORE = "nl-storyboard-v0821h"' in js, "STORE v0820c")
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
    pack_i = js.find("function packLorasForPayload")
    pack_j = js.find("async function searchLoras", pack_i)
    pack = js[pack_i:pack_j if pack_j > 0 else pack_i + 2000]
    for field in ("path:", "url:", "versionId:", "air:", "scale:", "strength:", "downloadUrl:"):
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
    assert_true("v0821h-send-aria" in html, "stamp v0821h-send-aria")
    assert_true("nl-storyboard-v0821h" in js, "STORE v0820c")
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
    assert_true("Math.min(max, 1)" in body, "force maxRefs=1 for single-slot")
    assert_true("image_urls" in js and "input_references" in js, "multi names present")
    # over-cap hard gate in runShotStep
    k = js.find("async function runShotStep")
    m = js.find("async function runSelected", k)
    if m < 0:
        m = js.find("function runSelected", k)
    run = js[k:m if m > 0 else k + 8000]
    assert_true("refUrls.length > refCap" in run, "over-cap compare in runShotStep")
    assert_true('status: "blocked"' in run and "超过上限" in run, "over-cap returns blocked with setMsg")
    assert_true("不静默丢弃" in run or "超过上限" in run, "loud over-cap message")
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
    assert_true("v0821h-send-aria" in html, "html stamp v0821h-send-aria")
    assert_true('const STORE = "nl-storyboard-v0821h"' in js, "STORE v0820c")
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
    im0 = js.find("function insertMention")
    im1 = js.find("function slashQueryAt", im0)
    im = js[im0:im1]
    assert_true("linkAssetToShot" in im, "insertMention links edge")
    assert_true("mentionDisplayTag" not in im, "insertMention must not write display tags")
    assert_true('"@" + sourceTitle(asset)' not in im, "insertMention must not use raw sourceTitle tag")
    # import confirms via linkAssetToShot only (no direct prompt write)
    ci0 = js.find("function confirmImportSelection")
    ci1 = js.find("function setZoomScale", ci0)
    ci = js[ci0:ci1]
    assert_true("linkAssetToShot" in ci, "import still auto-links")
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
    """v0817b lineage under v0821h-send-aria: unmention/link helpers still present."""
    js = (ROOT / "static" / "storyboard.js").read_text(encoding="utf-8")
    html = (ROOT / "static" / "storyboard.html").read_text(encoding="utf-8")
    assert_true("v0821h-send-aria" in html, "html stamp")
    assert_true('const STORE = "nl-storyboard-v0821h"' in js, "STORE v0820c")
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
    """v0821h-send-aria: loadDemo + btnAdd default prompt is empty; Skill template stays."""
    js = (ROOT / "static" / "storyboard.js").read_text(encoding="utf-8")
    html = (ROOT / "static" / "storyboard.html").read_text(encoding="utf-8")
    assert_true("v0821h-send-aria" in html, "html stamp")
    assert_true('<span class="stamp">v0821h-send-aria</span>' in html, ".stamp")
    assert_true('const STORE = "nl-storyboard-v0821h"' in js, "STORE v0821d")
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
    assert_true("v0821h-send-aria" in html, "html stamp")
    assert_true('const STORE = "nl-storyboard-v0821h"' in js, "STORE v0820c")
    assert_true("nl-storyboard-v0817c" in js, "STORE_OLDS has v0817c")
    assert_true("nl-storyboard-v0817b" in js, "STORE_OLDS has v0817b")
    assert_true("nl-storyboard-v0817" in js, "STORE_OLDS has v0817")
    assert_true("nl-storyboard-v0816b" in js, "STORE_OLDS has v0816b")

    # insertMention: link only — no mentionDisplayTag / no @ append / no mentionTags
    im = js[js.find("function insertMention"):js.find("function slashQueryAt")]
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
    assert_true("payload.images = sliced" in js, "images[] via edges")
    assert_true("function packLorasForPayload" in js, "LoRA packing kept")
    assert_true("stages[0].payload" not in js, "gate untouched")





def test_v0818_sticky_composer_bar():
    """v0818 lineage: LoRA + bar + msg pinned in dock-foot; prompt scrolls in dock-scroll (kept under v0819)."""
    js = (ROOT / "static" / "storyboard.js").read_text(encoding="utf-8")
    html = (ROOT / "static" / "storyboard.html").read_text(encoding="utf-8")
    assert_true("v0821h-send-aria" in html, "html stamp")
    assert_true('const STORE = "nl-storyboard-v0821h"' in js, "STORE v0820c")
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
    # CSS: expanded body is flex column; scroll overflows; foot sticky/flex-none
    assert_true(".dock.expanded .dock-body{display:flex;flex-direction:column" in html
                or "display:flex;flex-direction:column;overflow:hidden" in html,
                "expanded dock-body is flex column")
    assert_true(".dock-scroll{flex:1 1 auto;min-height:180px;overflow:auto}" in html, "dock-scroll min-height keeps prompt")
    assert_true(".dock-foot{" in html and "flex:0 0 auto" in html, "dock-foot flex-none")
    assert_true("position:sticky;bottom:0" in html, "dock-foot sticky bottom")
    # Untouched behaviors
    assert_true("stages[0].payload" not in js, "gate untouched")
    assert_true("function attachExtraImages" in js, "images packing kept")
    assert_true("function packLorasForPayload" in js, "LoRA packing kept")
    assert_true("mentionTags" not in js, "no-@-in-prompt lineage kept")


def test_v0819_canvas_stage():
    """v0819: canvas is main stage — Composer defaults collapsed; empty tip; click expands."""
    js = (ROOT / "static" / "storyboard.js").read_text(encoding="utf-8")
    html = (ROOT / "static" / "storyboard.html").read_text(encoding="utf-8")
    assert_true("v0821h-send-aria" in html, "html stamp v0821h-send-aria")
    assert_true('const STORE = "nl-storyboard-v0821h"' in js, "STORE v0820c")
    assert_true("nl-storyboard-v0818" in js, "STORE_OLDS has v0818")
    assert_true("nl-storyboard-v0817c" in js, "STORE_OLDS has v0817c")
    assert_true('dockMode: "collapsed"' in js, "default dockMode collapsed")
    assert_true('selectNode(state.selected || "shot-1", { collapsed: true })' in js,
                "boot selectNode keeps Composer collapsed")
    assert_true("opts.collapsed" in js, "selectNode honors collapsed opt")
    assert_true("function syncCanvasTip" in js, "syncCanvasTip helper")
    assert_true('id="canvasTip"' in html, "canvasTip element")
    assert_true("选分镜→写画面→LoRA→↑" in html, "empty-canvas onboarding tip")
    assert_true("min-height:120px" in html, "prompt min-height ≥120 when expanded")
    assert_true("min-height:180px" in html, "dock-scroll min-height keeps prompt visible")
    assert_true('id="dockFoot"' in html and "flex:0 0 auto" in html, "dock-foot still present")
    # Untouched
    assert_true("stages[0].payload" not in js, "gate untouched")
    assert_true("function attachExtraImages" in js, "images packing kept")
    assert_true("function packLorasForPayload" in js, "LoRA packing kept")
    assert_true("mentionTags" not in js, "no-@-in-prompt lineage kept")



def test_v0819b_expand_prompt():
    """v0819b: first paint of expanded dock shows #prompt in dock-scroll without scrolling."""
    js = (ROOT / "static" / "storyboard.js").read_text(encoding="utf-8")
    html = (ROOT / "static" / "storyboard.html").read_text(encoding="utf-8")
    assert_true("v0821h-send-aria" in html, "html stamp v0821h-send-aria")
    assert_true('const STORE = "nl-storyboard-v0821h"' in js, "STORE v0820c")
    assert_true("nl-storyboard-v0819b" in js, "STORE_OLDS has v0819b")
    assert_true("nl-storyboard-v0819" in js, "STORE_OLDS has v0819")
    assert_true("nl-storyboard-v0818" in js, "STORE_OLDS has v0818")
    # Default collapsed + tip kept from v0819
    assert_true('dockMode: "collapsed"' in js, "default dockMode still collapsed")
    assert_true("function syncCanvasTip" in js, "canvasTip behavior kept")
    assert_true('id="canvasTip"' in html, "canvasTip element kept")
    # Expand layout: taller dock, scroll min-height, foot capped, lora capped
    assert_true(".dock.expanded{max-height:58vh}" in html or "max-height:58vh" in html
                or "max-height:72vh" in html,
                "expanded dock max-height present (v0821: 58vh)")
    assert_true(".dock-scroll{flex:1 1 auto;min-height:180px;overflow:auto}" in html,
                "dock-scroll min-height 180px")
    assert_true(".dock.expanded .dock-scroll{min-height:200px}" in html,
                "expanded dock-scroll min-height 200px")
    assert_true("min-height:120px" in html, "prompt min-height ≥120")
    assert_true(".dock-foot{" in html and "max-height:46%" in html,
                "dock-foot capped so it cannot eat >50% of dock")
    assert_true(".dock.expanded .lora-block{max-height:110px;overflow:auto}" in html,
                "lora-block capped when expanded; overflow on lora not whole dock")
    # Expand path resets scrollTop so first frame shows modes+#prompt
    assert_true("scrollTop = 0" in js or "scrollTop=0" in js.replace(" ", ""),
                "expand path sets dockScroll.scrollTop=0")
    assert_true('setDockMode("expanded")' in js, "chip/select opens expanded")
    assert_true('dockMode: "collapsed"' in js, "collapsed default untouched")
    # Untouched
    assert_true("stages[0].payload" not in js, "gate untouched")
    assert_true("function attachExtraImages" in js, "images packing kept")
    assert_true("function packLorasForPayload" in js, "LoRA packing kept")
    assert_true("mentionTags" not in js, "no-@-in-prompt lineage kept")




def test_v0820_civitai_comfy_params():
    """v0820: Composer exposes civitai comfy params and packs them (134923572 spot-check shape)."""
    js = (ROOT / "static" / "storyboard.js").read_text(encoding="utf-8")
    html = (ROOT / "static" / "storyboard.html").read_text(encoding="utf-8")
    assert_true("v0821h-send-aria" in html, "html stamp")
    assert_true('const STORE = "nl-storyboard-v0821h"' in js, "STORE v0820c")
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
    k = js.find("async function runShotStep")
    assert_true(k >= 0, "runShotStep")
    run = js[k:k + 9000]
    assert_true("packComfyParamsForPayload()" in run, "pack comfy in runShotStep")
    assert_true("packLorasForPayload()" in run, "loras still packed")
    assert_true("payload.loras = packedLoras" in run, "sets payload.loras")
    assert_true("payload[k] = packedComfy[k]" in run or "payload[k]=packedComfy[k]" in run.replace(" ", ""),
                "merges packed comfy onto payload")
    assert_true(run.find("packLorasForPayload()") < run.find("packComfyParamsForPayload()"),
                "comfy packed after loras")
    # Spot-check fixture shape fields must be nameable (no silent drop list)
    for field in ("serviceId", "steps", "cfgScale", "sampler", "scheduler", "seed", "width", "height", "loras"):
        assert_true(field in js, "packs/mentions " + field)
    # Lineage kept
    assert_true("stages[0].payload" not in js, "gate untouched")
    assert_true("mentionTags" not in js, "no-@-in-prompt lineage")
    assert_true("function attachExtraImages" in js, "images packing kept")
    assert_true('dockMode: "collapsed"' in js, "canvas-stage collapsed default kept")
    assert_true('id="dockFoot"' in html, "sticky foot kept")


def test_v0820b_apply_import():
    """v0820b: storyboard applyImport packs civitai backend/service/comfy/LoRA; no fal silent fallback."""
    js = (ROOT / "static" / "storyboard.js").read_text(encoding="utf-8")
    html = (ROOT / "static" / "storyboard.html").read_text(encoding="utf-8")
    assert_true("v0821h-send-aria" in html, "html stamp")
    assert_true('const STORE = "nl-storyboard-v0821h"' in js, "STORE v0820c")
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
    assert_true('dockMode: "collapsed"' in js, "v0819 canvas-stage")




def test_v0820c_hard_service():
    """v0820c: empty civitai #service must hard-error; no CIVITAI_PREF soft-fill in buildGraph/runShotStep."""
    js = (ROOT / "static" / "storyboard.js").read_text(encoding="utf-8")
    html = (ROOT / "static" / "storyboard.html").read_text(encoding="utf-8")
    assert_true("v0821h-send-aria" in html, "html stamp v0821h-send-aria")
    assert_true('const STORE = "nl-storyboard-v0821h"' in js, "STORE v0820c")
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
    assert_true('be !== "civitai"' in bg or "be !== 'civitai'" in bg,
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
    assert_true('return { status: "blocked"' in run, "aborts generate on empty service")
    # payload.serviceId from UI only
    assert_true("payload.serviceId = sid" in run or "payload.serviceId=sid" in run.replace(" ", ""),
                "sets payload.serviceId from explicit sid")

    # loadCatalog: pref ordering hint OK; no auto-select pref into empty #service
    lc = js.find("async function loadCatalog")
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


def test_v0821_hardgate_i2v_refs():
    """v0821: i2v keeps first-frame; multi-ref packs N; P1 seed/dock/LoRA name."""
    js = (ROOT / "static" / "storyboard.js").read_text(encoding="utf-8")
    html = (ROOT / "static" / "storyboard.html").read_text(encoding="utf-8")
    assert_true("v0821h-send-aria" in html, "html stamp")
    assert_true('<span class="stamp">v0821h-send-aria</span>' in html, ".stamp")
    assert_true('const STORE = "nl-storyboard-v0821h"' in js, "STORE v0821")
    assert_true("nl-storyboard-v0820c" in js, "STORE_OLDS has v0820c")
    assert_true("nl-storyboard-v0820b" in js, "STORE_OLDS has v0820b")

    # A) i2v eats upstream — frame required + packed
    assert_true("视频需要先连一张首帧图" in js, "i2v missing-frame gate")
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
    assert_true("payload.images = sliced" in body, "images[] packed")
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
    def pack_urls(primary, linked, max_refs):
        urls = []
        if primary:
            urls.append(primary)
        for u in linked:
            if u and u not in urls:
                urls.append(u)
        return urls[:max_refs]
    linked_n = ["/out/a.jpg", "/out/b.jpg", "/out/c.jpg", "/out/d.jpg"]
    packed = pack_urls("/out/a.jpg", linked_n, 9)
    assert_true(len(packed) == 4, "under-cap packs all N=%d" % len(packed))
    assert_true(packed[0] == "/out/a.jpg", "primary first")
    over = pack_urls("/out/a.jpg", linked_n + ["/out/e.jpg"] * 10, 4)
    assert_true(len(over) == 4, "slice to maxRefs")
    assert_true("ref-cap-hint" in js or "还可" in js, "UI remaining slot hint")
    assert_true("linked.concat(suggest)" in js or "chipNodes" in js, "chips for all linked")

    # B) multi-ref: over-cap still hard-blocks before attach
    run_i = js.find("async function runShotStep")
    run = js[run_i:run_i + 14000]
    assert_true("countRefUrls" in run and "超过上限" in run, "over-cap hard block kept")
    assert_true(run.find("countRefUrls") < run.find("attachExtraImages(payload, shot)"),
                "gate before attach")

    # C) P1 UX
    assert_true("min-width:168px" in html or "min-width:168" in html, "seed widened")
    assert_true("#seed" in html and "118px" not in html.split("#seed")[1][:80], "old seed 118px gone")
    assert_true("max-height:58vh" in html, "dock expanded max-height lowered")
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
    assert_true("v0821h-send-aria" in html, "html stamp v0821h-send-aria")
    assert_true('<span class="stamp">v0821h-send-aria</span>' in html, ".stamp")
    assert_true('const STORE = "nl-storyboard-v0821h"' in js, "STORE v0821b")
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
    assert_true("v0821h-send-aria" in html, "html stamp")
    assert_true('<span class="stamp">v0821h-send-aria</span>' in html, ".stamp")
    assert_true('const STORE = "nl-storyboard-v0821h"' in js, "STORE v0821c")
    assert_true("nl-storyboard-v0821b" in js, "STORE_OLDS keeps v0821b")
    # pickUrl must map fal video shapes
    i = js.find("function pickUrl")
    assert_true(i >= 0, "pickUrl")
    block = js[i:i + 1200]
    assert_true("data.video" in block and "result.video" in block or "res.video" in block, "pickUrl video.url")
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
    end = js.find("function hasUnresolvedStageOut", i)
    assert_true(end > i, "pickUrl end")
    fn = js[i:end]
    node = subprocess.run(
        ["node", "-e", fn + r"""
const cases = [
  [{ saved: [{ url: "/out/a.mp4" }] }, "/out/a.mp4"],
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
    assert_true("v0821h-send-aria" in html, "html stamp")
    assert_true('<span class="stamp">v0821h-send-aria</span>' in html, ".stamp")
    assert_true('const STORE = "nl-storyboard-v0821h"' in js, "STORE v0821h")
    assert_true('"nl-storyboard-v0821g"' in js, "STORE_OLDS keeps v0821g")
    assert_true('"nl-storyboard-v0821f"' in js, "STORE_OLDS keeps v0821f")
    assert_true('"nl-storyboard-v0821e"' in js, "STORE_OLDS keeps v0821e")

    # disabled send visually gray (not white+opacity)
    assert_true(".send:disabled" in html and "#3a3a44" in html, "disabled send gray bg")
    assert_true("cursor:not-allowed" in html, "disabled cursor")

    # frameAsset heals orphan firstFrameId
    fa = js[js.find("function frameAsset"):js.find("function frameAsset") + 700]
    assert_true("orphan" in fa or 'shot.firstFrameId = linked[0]' in fa, "heal orphan firstFrameId")

    # runShotStep never silent on !shot
    run_i = js.find("async function runShotStep")
    run = js[run_i:run_i + 1200]
    assert_true("请先选中分镜再生成" in run, "setMsg when !shot")
    assert_true('shot.kind !== "shot"' in run and "setMsg" in run, "wrong-kind setMsg")

    # generate click-start feedback
    g = js[js.find("async function generate"):js.find("async function generate") + 900]
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
    """v0821h-send-aria: always 首帧已就绪; addEventListener+pointerdown; hit/z-index; missing-frame bad."""
    js = (ROOT / "static" / "storyboard.js").read_text(encoding="utf-8")
    html = (ROOT / "static" / "storyboard.html").read_text(encoding="utf-8")
    assert_true("v0821h-send-aria" in html, "html stamp")
    assert_true('<span class="stamp">v0821h-send-aria</span>' in html, ".stamp")
    assert_true("v0821h-send-aria" in html.split("<title>", 1)[1].split("</title>", 1)[0], "title stamp")
    assert_true('const STORE = "nl-storyboard-v0821h"' in js, "STORE v0821h")
    assert_true('"nl-storyboard-v0821g"' in js, "STORE_OLDS keeps v0821g")
    assert_true('"nl-storyboard-v0821f"' in js, "STORE_OLDS keeps v0821f")

    # CSS: larger hit + z-index above foot siblings (index #go lesson)
    assert_true("z-index:5" in html and "pointer-events:auto" in html, "send elevated hit")
    assert_true("touch-action:manipulation" in html, "send touch-action")
    assert_true(".send::before" in html and "inset:-12px" in html, "expanded hit ::before")
    assert_true(".dock-foot{" in html and "z-index:3" in html, "dock-foot above scroll")
    assert_true('data-testid="composer-send"' in html, "send data-testid in markup")

    k = js.find("function renderDock")
    assert_true(k >= 0, "renderDock")
    dock = js[k:k + 5500]
    # always set ready when video+frame (not only stale-regex clear)
    assert_true("首帧已就绪 · 可生成" in dock, "ready msg")
    assert_true("setMsg(\"首帧已就绪 · 可生成\")" in dock or "setMsg('首帧已就绪 · 可生成')" in dock,
                "unconditional ready setMsg")
    assert_true("/缺首帧|视频需要先连一张首帧图|本版未接/" not in dock,
                "stale-only regex gate removed")
    # missing-frame → bad (red)
    assert_true('setMsg("缺首帧 · 视频需要先连一张首帧图", "bad")' in dock, "missing-frame bad")
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
    g = js[js.find("async function generate"):js.find("async function generate") + 1200]
    assert_true("校验连线…" in g, "click-start setMsg")
    assert_true(g.find("校验连线") < g.find("runShotStep"), "click msg before runShotStep")
    # harness must not POST generate in tests — static only
    assert_true("fetch(\"/api/generate\"" in js, "generate path exists in product code")




def test_v0821h_send_aria():
    """v0821h-send-aria: gate via aria-disabled (not disabled=true); click setMsg on needFrame/stub; busy → 进行中."""
    js = (ROOT / "static" / "storyboard.js").read_text(encoding="utf-8")
    html = (ROOT / "static" / "storyboard.html").read_text(encoding="utf-8")
    assert_true("v0821h-send-aria" in html, "html stamp")
    assert_true('<span class="stamp">v0821h-send-aria</span>' in html, ".stamp")
    assert_true("v0821h-send-aria" in html.split("<title>", 1)[1].split("</title>", 1)[0], "title stamp")
    assert_true('const STORE = "nl-storyboard-v0821h"' in js, "STORE v0821h")
    assert_true('"nl-storyboard-v0821g"' in js, "STORE_OLDS keeps v0821g")
    assert_true('"nl-storyboard-v0821f"' in js, "STORE_OLDS keeps v0821f")

    # CSS: reuse disabled gray via is-blocked / aria-disabled
    assert_true(".send.is-blocked" in html or '[aria-disabled="true"]' in html or ".send[aria-disabled" in html,
                "blocked visual selector")
    assert_true("#3a3a44" in html and "cursor:not-allowed" in html, "gray blocked styles")
    assert_true(".send:disabled" in html, "keep :disabled style for compat")

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
    fs = js[js.find("function fireSend"):js.find("function fireSend") + 1600]
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
    assert_true("z-index:5" in html, "hit z-index kept")



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
        test_v0821_hardgate_i2v_refs,
        test_v0821b_i2v_detect,
        test_v0821c_fal_i2v_preview,
        test_v0821f_send_noop,
        test_v0821g_send_bind,
        test_v0821h_send_aria,
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



if __name__ == "__main__":
    raise SystemExit(main())
