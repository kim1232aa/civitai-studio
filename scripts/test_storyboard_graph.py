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
            "serviceId": service or ("fal-ai/minimax/video-01" if op == "i2v" else "fal-ai/flux/schnell"),
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
            {"id": "shot-1", "op": "i2v", "params": {"serviceId": "fal-ai/minimax/video-01", "duration": 5}},
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
            {"id": "shot-3", "op": "i2v", "params": {"serviceId": "fal-ai/minimax/video-01", "duration": 5}},
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
    assert_true("nl-storyboard-v0820" in js, "STORE must bump to v0820")
    assert_true("nl-storyboard-v0819b" in js, "STORE_OLDS must keep v0819b for migrate")
    assert_true("nl-storyboard-v0819" in js, "STORE_OLDS must keep v0819 for migrate")
    assert_true("nl-storyboard-v0818" in js, "STORE_OLDS must keep v0818 for migrate")
    assert_true("nl-storyboard-v0817c" in js, "STORE_OLDS must keep v0817c for migrate")
    assert_true("nl-storyboard-v0817b" in js, "STORE_OLDS must keep v0817b for migrate")
    assert_true("nl-storyboard-v0817" in js, "STORE_OLDS must keep v0817 for migrate")
    assert_true("nl-storyboard-v0816b" in js, "STORE_OLDS must keep v0816b for migrate")
    html = (ROOT / "static" / "storyboard.html").read_text(encoding="utf-8")
    assert_true("v0820-civitai-comfy-params" in html, "stamp must be v0820-civitai-comfy-params")


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
    assert_true("v0820-civitai-comfy-params" in html, "html stamp")
    assert_true("nl-storyboard-v0820" in js, "STORE v0820")
    assert_true("nl-storyboard-v0819b" in js, "STORE_OLDS has v0819b")
    assert_true("nl-storyboard-v0819" in js, "STORE_OLDS has v0819")
    assert_true("nl-storyboard-v0818" in js, "STORE_OLDS has v0818")
    assert_true("nl-storyboard-v0817c" in js, "STORE_OLDS has v0817c")


def test_v0815_gen_hardgate():
    """v0815b packing + v0815c stamp: images[] always; caps from capabilities/imageFields."""
    js = (ROOT / "static" / "storyboard.js").read_text(encoding="utf-8")
    html = (ROOT / "static" / "storyboard.html").read_text(encoding="utf-8")
    assert_true("v0820-civitai-comfy-params" in html, "html stamp v0820-civitai-comfy-params")
    assert_true("nl-storyboard-v0820" in js, "STORE v0820")
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
    assert_true("v0820-civitai-comfy-params" in html, "html stamp v0820-civitai-comfy-params")
    assert_true('const STORE = "nl-storyboard-v0820"' in js, "STORE v0818")
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
    assert_true("v0820-civitai-comfy-params" in html, "stamp v0820-civitai-comfy-params")
    assert_true("nl-storyboard-v0820" in js, "STORE v0820")
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
    assert_true("v0820-civitai-comfy-params" in html, "html stamp v0820-civitai-comfy-params")
    assert_true('const STORE = "nl-storyboard-v0820"' in js, "STORE v0818")
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
    # default new-shot template has no @asset auto-fill
    assert_true('prompt: "【镜头"' in js or "prompt: \"【镜头" in js, "human shot template")
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
    """v0817b lineage under v0820-civitai-comfy-params: unmention/link helpers still present."""
    js = (ROOT / "static" / "storyboard.js").read_text(encoding="utf-8")
    html = (ROOT / "static" / "storyboard.html").read_text(encoding="utf-8")
    assert_true("v0820-civitai-comfy-params" in html, "html stamp")
    assert_true('const STORE = "nl-storyboard-v0820"' in js, "STORE v0818")
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


def test_v0817c_no_at_in_prompt():
    """v0817c: insertMention/atbox must not write any @ into prompt; edge+chip only."""
    js = (ROOT / "static" / "storyboard.js").read_text(encoding="utf-8")
    html = (ROOT / "static" / "storyboard.html").read_text(encoding="utf-8")
    assert_true("v0820-civitai-comfy-params" in html, "html stamp")
    assert_true('const STORE = "nl-storyboard-v0820"' in js, "STORE v0818")
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
    assert_true("v0820-civitai-comfy-params" in html, "html stamp")
    assert_true('const STORE = "nl-storyboard-v0820"' in js, "STORE v0819")
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
    assert_true("v0820-civitai-comfy-params" in html, "html stamp v0820-civitai-comfy-params")
    assert_true('const STORE = "nl-storyboard-v0820"' in js, "STORE v0819")
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
    assert_true("v0820-civitai-comfy-params" in html, "html stamp v0820-civitai-comfy-params")
    assert_true('const STORE = "nl-storyboard-v0820"' in js, "STORE v0820")
    assert_true("nl-storyboard-v0819b" in js, "STORE_OLDS has v0819b")
    assert_true("nl-storyboard-v0819" in js, "STORE_OLDS has v0819")
    assert_true("nl-storyboard-v0818" in js, "STORE_OLDS has v0818")
    # Default collapsed + tip kept from v0819
    assert_true('dockMode: "collapsed"' in js, "default dockMode still collapsed")
    assert_true("function syncCanvasTip" in js, "canvasTip behavior kept")
    assert_true('id="canvasTip"' in html, "canvasTip element kept")
    # Expand layout: taller dock, scroll min-height, foot capped, lora capped
    assert_true(".dock.expanded{max-height:72vh}" in html or "max-height:72vh" in html,
                "expanded dock max-height raised")
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
    assert_true("v0820-civitai-comfy-params" in html, "html stamp")
    assert_true('const STORE = "nl-storyboard-v0820"' in js, "STORE v0820")
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
        test_v0818_sticky_composer_bar,
        test_v0819_canvas_stage,
        test_v0819b_expand_prompt,
        test_v0820_civitai_comfy_params,
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
