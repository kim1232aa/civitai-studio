# Composer 字段板（官方支持 / 接线 / 死值）

> 2026-09-11 · **不报 Pass** · 官方 API 铁律 · 六家同一张板  
> 出处：[OFFICIAL-SOURCES.md](OFFICIAL-SOURCES.md)

缺键=未知，不预拦。strength null 不发明。未页↑不报 Pass。

## 总表（六家）

| 字段 | civitai | fal | huggingface | modelscope-ai/cn | nano-gpt |
| --- | --- | --- | --- | --- |
| prompt | wired | wired（空串也留 key） | wired | wired（官方 <2000） | wired（**无公布 1200**） |
| seed | no clamp | no clamp | **无官方 max，禁止 mod** | 官方 [0, 2³¹−1]；**-1 省略不发** | **无官方 max，禁止 mod** |
| LoRA | Klein/Comfy/LTX2 `{air:s}`；Dev/WAN/Hunyuan `[{air,s}]`；Fal-Krea 无 | schema 有才发 `[{path,scale}]` | 官方表无 loras；fal 通道 unverified | 单条字符串；多条 dict 和=1 最多6 | 官方 Image API **无 loras 键**；`*-lora` heuristic |
| duration | 仅服务 schema enum | 仅该端点 OpenAPI enum（禁发明 5/12/16） | unsupported | videoDuration=false | 仅 catalog enum |
| maxRefs | 9 `images` | 仅 OpenAPI maxItems；无则未知不发明 9 | 9 `image_urls` | 天花板 3；Edit-2509=3；t2i 不吃 | catalog `input_reference_constraints` |
| i2i | source/images | schema 字段 | 能力表 none（不抬） | 仅编辑模型 `image_url` | `input_references` |

## 按家

- **Civitai** 看当前 recipe，禁止全家一张 dict。Fal-Krea 不接 LoRA/负面/自由宽高。
- **Fal** duration / LoRA / 多图只抄该端点 OpenAPI。
- **HF** seed 不 wrap；Router 不托管 `fal-ai/*lora`。
- **魔搭** -1/random/空 省略 seed；AI/CN token 不交叉。
- **Nano** 用 catalog `resolution` token；不写 ≤1200。
