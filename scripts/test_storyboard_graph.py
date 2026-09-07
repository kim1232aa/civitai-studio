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
    assert_true("nl-storyboard-v0817b" in js, "STORE must bump to v0817b")
    assert_true("nl-storyboard-v0817" in js, "STORE_OLDS must keep v0817 for migrate")
    assert_true("nl-storyboard-v0816b" in js, "STORE_OLDS must keep v0816b for migrate")
    html = (ROOT / "static" / "storyboard.html").read_text(encoding="utf-8")
    assert_true("v0817b-unmention-at-tag" in html, "stamp must be v0817b-unmention-at-tag")


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
    assert_true("v0817b-unmention-at-tag" in html, "html stamp")
    assert_true("nl-storyboard-v0817b" in js, "STORE v0817b")


def test_v0815_gen_hardgate():
    """v0815b packing + v0815c stamp: images[] always; caps from capabilities/imageFields."""
    js = (ROOT / "static" / "storyboard.js").read_text(encoding="utf-8")
    html = (ROOT / "static" / "storyboard.html").read_text(encoding="utf-8")
    assert_true("v0817b-unmention-at-tag" in html, "html stamp v0817b-unmention-at-tag")
    assert_true("nl-storyboard-v0817b" in js, "STORE v0817b")
    assert_true("nl-storyboard-v0817" in js, "STORE_OLDS prepend v0817")
    assert_true("nl-storyboard-v0817" in js, "STORE_OLDS has v0817")
    assert_true("nl-storyboard-v0816b" in js, "STORE_OLDS has v0816b")
    assert_true('dockMode: "expanded"' in js, "dock default expanded")
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
    """LoRA UI + packing still green under v0817b stamp."""
    js = (ROOT / "static" / "storyboard.js").read_text(encoding="utf-8")
    html = (ROOT / "static" / "storyboard.html").read_text(encoding="utf-8")
    assert_true("v0817b-unmention-at-tag" in html, "html stamp v0817b-unmention-at-tag")
    assert_true('const STORE = "nl-storyboard-v0817b"' in js, "STORE v0817b")
    assert_true("nl-storyboard-v0817" in js, "STORE_OLDS has v0817")
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
    assert_true("v0817b-unmention-at-tag" in html, "stamp v0817b-unmention-at-tag")
    assert_true("nl-storyboard-v0817b" in js, "STORE v0817b")
    assert_true("nl-storyboard-v0817" in js, "STORE_OLDS has v0817")
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
    """v0817 lineage: link/mention must not append @sourceTitle; kept under v0817b stamp."""
    js = (ROOT / "static" / "storyboard.js").read_text(encoding="utf-8")
    html = (ROOT / "static" / "storyboard.html").read_text(encoding="utf-8")
    assert_true("v0817b-unmention-at-tag" in html, "html stamp v0817b-unmention-at-tag")
    assert_true('const STORE = "nl-storyboard-v0817b"' in js, "STORE v0817b")
    assert_true("nl-storyboard-v0817" in js, "STORE_OLDS has v0817")
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
    # unmention strips via tagsForAsset (legacy @sourceTitle + display @图片N)
    u0 = js.find("function unmention(asset, shot)")
    u1 = js.find("function invalidateStageProgress", u0)
    un = js[u0:u1]
    assert_true("tagsForAsset" in un, "unmention uses tagsForAsset")
    # unlink must unmention BEFORE filtering edges (index-stable @图片N)
    ul0 = js.find("function unlinkAssetFromShot")
    ul1 = js.find("function toggleAssetOnShot", ul0)
    ul = js[ul0:ul1]
    assert_true(ul.find("unmention(asset, shot)") < ul.find("state.edges = state.edges.filter"),
                "unmention before edge removal")
    # insertMention uses mentionDisplayTag, not raw sourceTitle
    im0 = js.find("function insertMention")
    im1 = js.find("function slashQueryAt", im0)
    im = js[im0:im1]
    assert_true("mentionDisplayTag" in im, "insertMention uses mentionDisplayTag")
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


def _sim_mention_display_tag(asset, linked_ids, titles_by_id):
    """Mirror mentionDisplayTag while asset is still in linked list."""
    try:
        idx = linked_ids.index(asset["id"])
    except ValueError:
        idx = len(linked_ids)
    title = titles_by_id[asset["id"]]
    if title and not _sim_is_raw_file_title(title):
        return "@" + title
    return "@图片" + str(idx + 1)


def _sim_tags_for_asset(asset, linked_ids, titles_by_id):
    tags = []
    title = titles_by_id[asset["id"]]
    if title:
        legacy = "@" + title
        if legacy not in tags:
            tags.append(legacy)
    display = _sim_mention_display_tag(asset, linked_ids, titles_by_id)
    if display not in tags:
        tags.append(display)
    return tags


def _sim_unmention(prompt, asset, linked_ids, titles_by_id):
    import re
    text = prompt or ""
    for tag in _sim_tags_for_asset(asset, linked_ids, titles_by_id):
        if tag and tag in text:
            text = text.replace(tag, "")
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def test_v0817b_unmention_at_tag():
    """v0817b: insertMention @图片N / human tag must be stripped on unmention/unlink."""
    js = (ROOT / "static" / "storyboard.js").read_text(encoding="utf-8")
    html = (ROOT / "static" / "storyboard.html").read_text(encoding="utf-8")
    assert_true("v0817b-unmention-at-tag" in html, "html stamp")
    assert_true('const STORE = "nl-storyboard-v0817b"' in js, "STORE v0817b")
    assert_true("nl-storyboard-v0817" in js, "STORE_OLDS has v0817")
    assert_true("function tagsForAsset" in js, "tagsForAsset")
    assert_true("seedream" in js[js.find("function isRawFileTitle"):js.find("function mentionDisplayTag")],
                "isRawFileTitle covers seedream")
    # Static: unmention ↔ insertMention alignment
    assert_true("tagsForAsset" in js[js.find("function unmention"):js.find("function invalidateStageProgress")],
                "unmention calls tagsForAsset")
    assert_true("mentionDisplayTag" in js[js.find("function insertMention"):js.find("function slashQueryAt")],
                "insertMention uses mentionDisplayTag")
    ul = js[js.find("function unlinkAssetFromShot"):js.find("function toggleAssetOnShot")]
    assert_true(ul.find("unmention(asset, shot)") < ul.find("state.edges = state.edges.filter"),
                "unlink unmentions before edge drop")

    # Simulate atbox insert of raw-title asset → @图片1, then unmention while still linked
    raw = {"id": "a-raw", "title": "nano-gpt_img_ef80f1b1f425_0"}
    human = {"id": "a-human", "title": "家用机器人"}
    titles = {raw["id"]: raw["title"], human["id"]: human["title"]}
    linked = [raw["id"]]  # sole linked image → @图片1
    display = _sim_mention_display_tag(raw, linked, titles)
    assert_true(display == "@图片1", display)
    prompt = "基于 " + display + " 重绘"
    assert_true("@图片1" in prompt, prompt)
    # chip off / unmention while edge still present
    after = _sim_unmention(prompt, raw, linked, titles)
    assert_true("@图片1" not in after, "orphan @图片1 must be stripped: " + after)
    assert_true("@" + raw["title"] not in after, "no leftover @sourceTitle")
    assert_true("基于" in after, after)

    # Human title path: insert @家用机器人, unmention strips it
    linked_h = [human["id"]]
    d2 = _sim_mention_display_tag(human, linked_h, titles)
    assert_true(d2 == "@家用机器人", d2)
    p2 = "角色：" + d2 + " 站立"
    after2 = _sim_unmention(p2, human, linked_h, titles)
    assert_true("@家用机器人" not in after2, after2)

    # Index stability: two linked; unlink middle asset's @图片2 (not shifted post-unlink)
    a1 = {"id": "a1", "title": "seedream_abc123_out_0"}
    a2 = {"id": "a2", "title": "seedream_def456_out_1"}
    a3 = {"id": "a3", "title": "seedream_ghi789_out_2"}
    titles3 = {a1["id"]: a1["title"], a2["id"]: a2["title"], a3["id"]: a3["title"]}
    linked3 = [a1["id"], a2["id"], a3["id"]]
    t1 = _sim_mention_display_tag(a1, linked3, titles3)
    t2 = _sim_mention_display_tag(a2, linked3, titles3)
    t3 = _sim_mention_display_tag(a3, linked3, titles3)
    assert_true((t1, t2, t3) == ("@图片1", "@图片2", "@图片3"), (t1, t2, t3))
    prompt3 = " ".join([t1, t2, t3])
    # unmention a2 while still linked → strip @图片2 only
    after3 = _sim_unmention(prompt3, a2, linked3, titles3)
    assert_true("@图片2" not in after3, after3)
    assert_true("@图片1" in after3 and "@图片3" in after3, after3)
    # Wrong order (post-unlink index) would compute a2 as @图片3 — ensure we document pre-unlink
    linked_after = [a1["id"], a3["id"]]
    wrong = _sim_mention_display_tag(a2, linked_after, titles3)
    assert_true(wrong == "@图片3", "post-unlink index shifts — why unmention must run first")
    assert_true(wrong not in ["@图片2"], "shifted tag differs from insert-time tag")

    assert_true("stages[0].payload" not in js, "gate untouched")
    assert_true("function attachExtraImages" in js, "images packing kept")
    assert_true("function packLorasForPayload" in js, "LoRA packing kept")



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
