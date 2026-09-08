# 魔搭 Hub LoRA：怎么挂（说明 + 示例）

适用：Studio 画布 Composer，backend=`modelscope-ai` 或 `modelscope-cn`（两套 token / 端点，**不要串台**）。

## 一句话

魔搭只吃 **ModelScope Hub 的 `owner/repo`**。Civitai 下载链 / versionId / AIR **不能用**，也不会自动 remap。

## 页面怎么挂

1. 选后端：**魔搭 AI**（`modelscope-ai`）或 **魔搭 CN**（`modelscope-cn`）。哪家有额度用哪家；连不上也不会自动切另一家。
2. 模型选 Hub 底模，例如明文：`Tongyi-MAI/Z-Image-Turbo`（不要「默认模型」、不要 fal id）。
3. LoRA 区标题应是「LoRA · 魔搭 Hub owner/repo」。
4. 在搜索框输入 **Hub 仓库 id**，例如：
   - `DiffSynth-Studio/Z-Image-Turbo-DistillPatch`
   - 或其它带 `lora` / 适配 Z-Image 的 Hub 仓（搜「lora」「z-image」）
5. 点搜索 → 点选结果 → chip 上应看到 `owner/repo`，权重例如 `0.8`。
6. **不要**贴 `https://civitai.com/api/download/models/…`；贴了会红拦 / 出站跳过（成片可能仍是裸底模 = 假信心）。
7. 自己点 ↑。成功后看 sidecar / 出站：`loras` 必须还在，且是 Hub 形态。

快捷夹具（开发硬闸）：「魔搭 LoRA夹具」或 `?fixture=ms-lora`  
→ **强制** `backend=modelscope-ai`（不跟当前 CN 走）+ `Tongyi-MAI/Z-Image-Turbo` + `DiffSynth-Studio/Z-Image-Turbo-DistillPatch` @0.8。

## 出站字段（2026-09-08 实测）

`POST {ai|cn}/v1/images/generations`，异步头 `X-ModelScope-Async-Mode: true`。

**能过的形状**（单条也要用数组对象）：

```json
{
  "model": "Tongyi-MAI/Z-Image-Turbo",
  "prompt": "portrait, soft light, detailed face, cinematic",
  "size": "1024x576",
  "loras": [
    {
      "model": "DiffSynth-Studio/Z-Image-Turbo-DistillPatch",
      "weight": 0.8
    }
  ]
}
```

**会 500「Model does not exist」的旧形状**（文档曾写、适配器曾发）：

```json
{ "loras": "DiffSynth-Studio/Z-Image-Turbo-DistillPatch" }
```

```json
{ "loras": { "DiffSynth-Studio/Z-Image-Turbo-DistillPatch": 0.8 } }
```

多条时：

```json
{
  "loras": [
    { "model": "owner/repo-a", "weight": 0.6 },
    { "model": "owner/repo-b", "weight": 0.4 }
  ]
}
```

## 验收怎么判

| 看什么 | Pass | Fail |
| --- | --- | --- |
| Composer 明文 | `modelscope-ai`（或 cn）+ Hub 底模 id | 「默认模型」/ fal / 另一家串台 |
| LoRA chip | `owner/repo` @ scale | 仍是 Civitai http，但点了↑ |
| 出站 / sidecar | `loras:[{model,weight}]` | 空 `loras`、字符串、或 `{repo:w}` |
| 余额 | AI/CN 有额度的那家 | `insufficient balance`（换有额度的端点，勿静默互切） |

## 和别家对比（别混）

| 家 | LoRA 填什么 |
| --- | --- |
| Civitai | AIR / versionId |
| Fal | 常 `[{path: http下载链, scale}]`，可切 `/lora` sibling |
| HF | Hub 底模 id；path 常仍是 Civitai http（unverified） |
| **魔搭** | **只要 Hub `owner/repo`，出站 `[{model,weight}]`** |
| Nano | `*-lora` 目录模 + Civitai http path |

## 相关文件

- 适配器：`providers/modelscope.py`（`_modelscope_loras`）
- 画布夹具：`static/storyboard.js` → `mountMsLoraFixture` / `?fixture=ms-lora`
- 总表：[`provider-lora.md`](provider-lora.md)、[`lora-wiring-deep.md`](lora-wiring-deep.md)
