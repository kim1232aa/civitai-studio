# Plan: 硬闸闭环证据（真同流程 Seko）— 2026-09-17

## Goal
闭环仍 0。开一刀完整证据包：未用 AIImageStudio → 页↑原参 → o154 卡像素=/out → 硬刷仍在 → **真 Seko 同流程成对**（节点 Composer，禁 Agent 聊天页）。Pass 默认 False，不喊验收。

## Why
- `28978239` o154 像素绿已进 `_invalid-…-pass-no-seko`（缺真对照）
- 假 Seko / Agent Composer 包已作废
- eggbot：别停 Fail 包；继续硬闸证据；刀序听 Looper（未回前按默认：Civitai t2i 最稳写回 + 真 Seko）

## Tasks
1. HEAD ≥ beb0688 o154；重启 :8765 若 stamp 不对
2. 未用帖 import 原参；house-first civitai；页 #send
3. 双卡同构图（藏 Composer）；blob/faceUrl/NCC/blobByteMatch 口径
4. **同会话**截 Seko：入口 `https://seko.sensetime.com/my-space?tab=canvas` → 有画面画布 → 节点 Composer
   - seko-01 画布列表/入口
   - seko-02 有内容画布
   - seko-03 节点 Composer（禁「新对话 Beta」Agent 欢迎页）
   - seko-04 生成/结果态（与 03 视觉差够大）
5. local-contrast = 本地全页（非卡图复制）
6. pack `civitai-<id>-t2i-closed-o154-seko/`；MANIFEST Pass=False；交 Looper 肉眼

## Anti
禁 curl generate；禁缩短 prompt；禁假 Pass；禁复用旧 Seko 当同流程；禁 Agent 页冒充 Composer。
