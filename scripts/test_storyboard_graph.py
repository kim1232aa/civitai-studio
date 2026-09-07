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
    assert_true("nl-storyboard-v0815b" in js, "STORE must bump to v0815b")
    assert_true("nl-storyboard-v0815" in js, "STORE_OLDS must keep v0815 for migrate")
    html = (ROOT / "static" / "storyboard.html").read_text(encoding="utf-8")
    assert_true("v0815b-ref-images" in html, "stamp must be v0815b-ref-images")


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
    assert_true("v0815b-ref-images" in html, "html stamp")
    assert_true("nl-storyboard-v0815b" in js, "STORE v0815b")


def test_v0815_gen_hardgate():
    """v0815b: multi-ref always packs payload.images[]; caps still from capabilities."""
    js = (ROOT / "static" / "storyboard.js").read_text(encoding="utf-8")
    html = (ROOT / "static" / "storyboard.html").read_text(encoding="utf-8")
    assert_true("v0815b-ref-images" in html, "html stamp v0815b-ref-images")
    assert_true("nl-storyboard-v0815b" in js, "STORE v0815b")
    assert_true("nl-storyboard-v0815" in js, "STORE_OLDS prepend v0815")
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
