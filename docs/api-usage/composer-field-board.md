# Composer 字段板（官方支持 / 接线 / 死值）

> 2026-09-10 · api对接助手 · **不报 Pass**  
> 来源：`docs/api-usage/*` + `providers/capabilities.py` + 本轮出站债  
> 用途：Composer 按 backend/service **露槽 / 禁用 / 明示不支持**；禁发明默认 strength。

图例：`supported`=官方有 · `wired`=适配器会出站 · `dead`=UI/代码死值或假齐 · `unsupported`=官方无/适配器硬拒 · `unverified`=发出≠加载

## 总表（六家）

| 字段 | civitai | fal | huggingface | modelscope-ai/cn | nano-gpt |
| --- | --- | --- | --- | --- | --- |
| prompt | supported+wired | supported+wired（空串也保留） | supported+wired | supported+wired | supported+wired（≤1200） |
| negative | supported+wired | schema 允许时 wired | fal通道 wired；OpenAI 通道忽略 | supported+wired | supported+wired |
| width/height | free_wh clamp 16–2048 | →`image_size` | fal→`image_size`；OpenAI→`size` | →`size` WxH | **禁止**自由 WxH；要 catalog `resolution` token |
| steps | wired 1–150 | →`num_inference_steps`（schema） | fal通道 wired | wired→`steps` | dual `steps`+`num_inference_steps` |
| cfg | `cfgScale` | →`guidance_scale` | →`guidance_scale` | →`guidance` | →`guidance_scale` |
| sampler | Comfy 名；**sdcpp 要映射**（`dpmpp_2m`→`dpm++2m`） | 通常无；有则 `scheduler` | fal通道 `scheduler`；OpenAI **unsupported** | unsupported（图片适配器拒 sampler） | unsupported（无独立 sampler 槽） |
| scheduler/schedule | Comfy `scheduler`；sdcpp→`schedule`（karras） | optional | fal optional | unsupported | unsupported |
| seed | no clamp | no clamp | **mod int32** | mod int32 | mod int32 |
| LoRA 形态 | **`{air: float}`** | **`[{path,scale}]`**（AIR 不当 path） | `[{path,scale}]` **unverified** | 单条 **字符串** `owner/repo`；多条 `{repo:w}` 和=1 | `[{path,scale}]`≤3 + 须 `*-lora` 模型 |
| LoRA strength | 必填 float；null 不得发明 | scale clip[0,4]；缺 strength 读 strength | 同 Fal 形 | 单条带 weight→本地 400；多条必填 | 同 path/scale |
| maxRefs | 9 · field=`images` | 默认 9；单图端点 catalog→1 · `image_urls` | 9 · `image_urls` | **1** · `image_url` | **5** · `input_references` |
| i2i | source/images | first_frame / image_urls | 启发式 wants_img；OpenAI 弱 | image_url | input_references（禁混 image_url） |
| i2v | sourceImage 等 frameFields | fal_endpoint 字段族 | i2v=none（能力表） | image_url | image_url / imageDataUrl |
| progress | rate | queue | **none**（禁假动画） | status_only | none |
| cancel | True | True | False | False | False |
| estimate | buzz | pricing_api | none | none | catalog_price |

## 按家：Composer 该怎么露

### civitai
- **必露**：serviceId、prompt、negative、W×H、steps、cfgScale、seed、sampler、scheduler、LoRA(air+strength)、diffusionModel  
- **条件露**：i2v/i2i 帧槽按 recipe `frameFields`；视频 duration/aspect  
- **映射债（已修出站）**：sdcpp `sampleMethod`/`schedule` 名 ≠ Comfy  
- **死值风险**：import 曾静默 krea2（o23 粘 sdxl）；strength 丢（o27 透传中）  
- **出站证据**：`19201654` job `…104743641` — sdcpp + `dpm++2m` + `karras` + `{@633865:0.7}` + 原帖 prompt

### fal
- **必露**：endpoint/serviceId、prompt（可空但 key 在）、seed、steps/cfg（schema）、W×H 或 aspect、duration（视频）  
- **LoRA**：只露 path/downloadUrl+scale；AIR-only → 明示不可作 path（勿静默绿勾）  
- **maxRefs**：跟 catalog `imageFields`（有 `image_urls` 才多图）  
- **死值风险**：sibling 改 endpoint 须 UI 可见；短 prompt 窄成功 ≠ 原帖闭环  
- **出站证据**：窄（旧 Krea2 path@version）；AIImageStudio Fal 本轮待 `28533344`

### huggingface
- **必露**：Hub mid、prompt、seed（显示 clamp）、steps/cfg、size  
- **LoRA**：可露但标 **unverified**（发出≠加载）；OpenAI/bytes 通道 **unsupported** LoRA  
- **i2v**：能力表 none → Composer **禁用并写不支持**  
- **progress/cancel**：none/False → 禁假进度条  
- **出站证据**：本轮无完整页↑证明

### modelscope-ai / modelscope-cn
- **必露**：owner/repo model、prompt、negative、size、seed、steps、guidance  
- **LoRA**：Hub owner/repo；单条无 weight→字符串；有 weight 单条→硬拒；多条 dict 和=1  
- **maxRefs=1**；sampler/scheduler **unsupported**（硬拒丢参）  
- **死值债**：Z-Image + 字符串 LoRA 实测 500 `Model does not exist`；poll 曾翻 FAILED  
- **出站证据**：底模无 LoRA Pass；带 LoRA Fail

### nano-gpt
- **必露**：model、prompt（≤1200）、**resolution token**（禁止自由 WxH 出站）、seed、n、refs≤5  
- **LoRA**：仅 `*-lora` 模型；path 解析失败 **400 fail-closed**（不静默丢）  
- **sampler**：无独立官方槽 → 不露或标 unsupported  
- **出站证据**：本轮无页↑证明

## Composer 自适应硬规则（给 Grok）

1. 读 `GET /api/providers` → `capabilities` + 当前 catalog item 覆盖（只收紧不抬高）。  
2. `unsupported` / `none` → 控件禁用 + 明文「不支持」，**禁止藏掉当已齐**。  
3. strength/scale **null** → UI 明示「未填」，出站不得默认 0.8/1.0。  
4. 分辨率：nano 只给 catalog token；civitai/fal/hf/魔搭按各家。  
5. LoRA 形态按家切换 chip 校验（air vs path vs hub_repo）。  
6. 验收样例源：仅 AIImageStudio 未用图；原帖全文；页面↑。

## 文件锚点

- 能力：`providers/capabilities.py` · `docs/capability-schema.md`  
- 用法：`docs/api-usage/{civitai,fal,huggingface,modelscope,nanogpt}.md`  
- 本板：`docs/api-usage/composer-field-board.md`
