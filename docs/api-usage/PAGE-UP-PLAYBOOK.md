# 页 ↑ 证据手册（六家）

> 不是 Pass。闭环仍计 0，直到截图验收人只看图说通过。
> 禁止 curl / 代打 `/api/generate`。禁止短 prompt / 旧夹具复用。

作者页（每次换图）：https://civitai.red/user/hinablue/images

## 密钥（只写本机，不进仓）

| backend | 文件 |
| --- | --- |
| civitai | `~/.config/civitai/token` |
| fal | `~/.config/fal/token`（`KEY_ID:KEY_SECRET`） |
| huggingface | `~/.config/huggingface/token` |
| modelscope-ai | `~/.config/modelscope/token` |
| modelscope-cn | `~/.config/modelscope-cn/token` |
| nano-gpt | `~/.config/nano-gpt/token` |

启动一个 `python3 server.py`。端口不钉死，记 PID + HEAD。

## 每家一轮

1. 从 hinablue 点一张**没用过**的图，导入完整参数（原 prompt、底模、LoRA、尺寸、seed）。
2. 切到该 backend，按 catalog item 匹配模型 / LoRA。官方不接 LoRA → 换另一张，不发明 strength。
3. Composer 里官方支持的字段填满。未知能力标未知，不准当低上限预拦。
4. 页面点 ↑。等写回**原卡**。硬刷后再截一张。
5. 截图包只放 `docs/review-shots/`（gitignore）。验收人只看图，不看文字辩解。

## 已核过、可换的 hinablue 帖（2026-09-11，这批无 LoRA）

不要把下面当唯一夹具。有 LoRA 的帖另选。`strength=null` 保持 null。

| id | 底模 | prompt 长度 | seed | LoRA |
| --- | --- | --- | --- | --- |
| 142373903 | Krea2 Asian Utopian v3.3 | 2170 | 243138068893831 | 无 |
| 142373894 | 同上 | 1286 | 933254090841449 | 无 |
| 142373085 | 同上 | 1659 | 447159919688112 | 无 |
| 142337256 | 同上 | 748 | 780465390189923 | 无 |
| 142337258 | 同上 | 1052 | 16701841333952 | 无 |

页：`https://civitai.red/images/<id>`

## 六家官方形（出站对照，不是验收）

见 [OFFICIAL-SOURCES.md](OFFICIAL-SOURCES.md)。

- Civitai：Klein/Comfy/LTX2 = `{air:strength}`；Dev/WAN/Hunyuan = `[{air,strength}]`；Fal-Krea 拒 LoRA。
- Fal：只抄该端点 OpenAPI；禁发明 duration 5/12/16、maxRefs=9。
- HF：无 `loras` 键；seed 不 wrap；hint 禁止 `fal-ai/*`。
- 魔搭：seed -1 省略；Hub `owner/repo`；AI/CN token 不交叉。
- Nano：无 promptMax 1200；无 `loras` 键；分辨率用 catalog token。`z-image-turbo-lora` / `flux-lora` 是启发式 id。

## 验收人

只看成对截图：导入后 Composer 全参 → ↑ 进行中 → 原卡写回 → 硬刷仍在。空画布 / 短 prompt / 历史栏有图卡面空 = 不过。
