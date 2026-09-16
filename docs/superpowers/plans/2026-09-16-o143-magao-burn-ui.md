# o143 — Magao burn UI P0 (vision reviewer)

> 2026-09-16 · Asia/Shanghai · **不宣称 Pass**

## Before (review shots `docs/review-shots/closed-loop/magao-ai-119689290/`)

1. LoRA：o141 在 `supportsLora` 未知时标「未知」，同时仍渲染具体 LoRA 芯片 → 看起来像不支持却又挂着芯片。
2. 画布：中间空黑壳分镜卡像断链；文生图 Composer 参考槽仍亮着无关花瓶，成片卡是雪地站姿遗留。
3. Magao Hub-only 文案砸在 `#msg` 画布贴纸上，像生成错误。

## After (o143)

1. `o68`：有芯片 + unknown →「未知是否加载」；无芯片仍可「未知」；不因 unknown 假藏芯片。
2. t2i（`!catalogEatsRefs`）：驱动芯片只在 eats；未用连线降级 `ref-unused`（文生图不发送 · 点断开）；空槽仅 eats。
3. `renderCards` 跳过 orphan 空壳分镜（非当前 compose / 无 prompt|url|busy）。
4. `applyImport` → `mountImportStillOnShot`：原图与 prompt 同镜；t2i 清无关连线且不把原图当驱动 ref；i2i/i2v 才 link/firstFrame。
5. o134：Hub owner/repo 警告留在 `#loraHint`，不再写 `#msg`。

## Tests

- `scripts/test_o143_magao_burn_ui.js`
- o141 / o142 / o39 回归对齐 successor stamp

## Anti

- 不宣称 Pass；不拆掉 Magao Hub-only 能力诚实提示（只搬家/澄清）。
