# HF i2v 页面↑ 证据 — AIImageStudio `141669899`

> 时间：2026-09-16 Asia/Shanghai（CST）  
> HEAD 基线：`263415b` + 本轮最小接线修  
> **不宣称闭环 Pass**（铁律：无写回成片 / 无 jobId 出队不得报 Pass）

## 样本

| 项 | 值 |
| --- | --- |
| 作者 | AIImageStudio（未用帖） |
| 图 id | `141669899` |
| 导入 | 页面「导入参数」← `https://civitai.red/images/141669899` |
| promptLen | **978**（原帖全文，未缩短） |
| seed | `79679881871603` |
| 首帧 | 原帖 still → `/out/hf-i2v-141669899-still_*.jpg` |
| LoRA | 原帖有 1 条；**Wan i2v fal schema 无 LoRA 字段** → 页面点「删」清芯片后再发（非发明 strength） |

## 页面操作（禁 curl `/api/generate` 验收）

1. storyboard → 导入原帖参数  
2. backend=`huggingface` · mode=video · service=`Wan-AI/Wan2.2-I2V-A14B`  
3. 清多余参考连线（maxRefs=1）· 挂首帧 · 点 **↑**

## 出站（页面 POST 捕获）

```
sid=Wan-AI/Wan2.2-I2V-A14B
be=huggingface
kind=video
promptLen=978
nLoras=0
nRefs=1
firstFrame=/out/hf-i2v-141669899-still_20260916070036_91581536.jpg
```

generate-audit.jsonl（CST 07:00:42）：

```
backend=huggingface serviceId=Wan-AI/Wan2.2-I2V-A14B promptLen=978 nLoras=0 nRefs=1 code=402 jobId=null
error=You have depleted your monthly included credits. …
```

## 结果

| 项 | 状态 |
| --- | --- |
| 能选 HF 官方 i2v mid | **是**（Wan-AI/Wan2.2-I2V-A14B） |
| 页面 ↑ 真发 | **是**（POST `/api/generate`，非 curl） |
| 路由 | HF Router `fal-ai` × `fal-ai/wan/v2.2-a14b/image-to-video`（映射 live） |
| jobId | **无**（402 额度耗尽，未入队） |
| 成片写回 | **无** |
| 闭环计分 | **仍 0** |

## 本轮最小修（接线洞，非额度）

1. `providers/huggingface.py` `_call_fal`：视频端点未声明 `image_size`/`duration` 时不再自造自拒；refs 已物化后跳过 `image_url` 冲突覆盖  
2. `static/composer-field-adapt.js`：HF field-board `i2v` 由过期 `unsupported` → `supported`；`caps.i2v` 覆盖 board（对齐官方 InferenceClient + `capabilities.i2v=image_url`）  
3. **未改**魔搭视频硬拒

## 截图

- `00-loaded.png` / `01-modal.png` / `01-import.png`  
- `02-composer-i2v.png` / `03-sending.png` / `04-result.png`  
- `report.json`

## 给 api对接助手

- **jobId：无（402）** — 请核 generate-audit 同秒条：`2026-09-16T07:00:42` · `Wan-AI/Wan2.2-I2V-A14B` · promptLen=978 · nRefs=1  
- 额度恢复后再烧同一 mid，应能拿到 `hf|queue|…` / `hf|sync|…`
