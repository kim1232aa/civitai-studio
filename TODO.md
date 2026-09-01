# Night Lab 代办清单
更新：2026-09-02 · v0753

原则：不造幻觉功能、不删已有功能、只接官方已有字段。

---

## 禁止项（不要做）

- [ ] 不要加 xAI 后端 / xAI 出图
- [ ] 不要用 Civitai 公开 `/api/v1/images` 冒充完整导入（`meta` 经常是 null）
- [ ] 不要给 HF OpenAI 兼容通道发明 `loras`（那条通道忽略）。Fal 路由 mapped turbo 可带 `loras[]`；魔搭只要 Hub `owner/repo`。细则见 `docs/provider-lora.md`
- [ ] 不要删除 Fal LoRA（搜索、导入、payload、发送）。Fal 官方有 `loras` 参数
- [ ] 不要给 Fal / HF / 魔搭做黄 Buzz
- [ ] 不要导入后代点生成
- [ ] 不要给 HF / 魔搭做取消队列（没有 Fal 那种 `cancel_url`）
- [ ] 不要把训练端点当生成：`fal-ai/krea-2-trainer`、`z-image-trainer`
- [ ] 不要删 Tab / 预估 / 工作流 / 成人开关 / 已有 provider
- [ ] 不要在没有官方样例时瞎编 `urn:air:comfy:nodepacklayer:…`

---

## P0 已报错、还要收口

### 1. Civitai 工作流 Tab（customComfy）
现象：`Declare custom nodes as their install-layer AIR (nodepacklayer)，not the bare nodepack URN rgthree/…`
- [ ] 查到官方 `nodepacklayer` 完整 URN 样例再改 `providers/civitai_workflows.py` 的 `_mint_pack_air`
- [ ] 提交前把 `urn:air:comfy:nodepack:…` 换成 `urn:air:comfy:nodepacklayer:…`
- [x] 工作流缺节点包时诚实报「未映射」，不要静默丢掉
- [x] 裸 nodepack URN 提交前拦截，提示走图片 Tab（不编 nodepacklayer）
- [ ] 在未修好前，Krea 这类图走「图片 Tab + imageGen」，不要走工作流

### 2. Civitai 导入参数对不齐
例：https://civitai.red/images/136863587
- [ ] 核对导入后表单：sampler `er_sde`、scheduler `sgm_uniform`、seed、denoise、AIR `@version`
- [x] 导入图/视频时识别 LoRA（AIR + downloadUrl + versionId），不要只认 checkpoint
- [ ] 对不上的 Comfy 节点（SeedVR2、VAE、unmatchedNodes）只展示，不编进 imageGen body
- [ ] 公开 API `meta:null` 时继续走 HTML `__NEXT_DATA__` + 文件块，不要回退成 `scheduler=simple`

### 3. Fal 出图「成功但没拿到文件」
- [x] 队列 `COMPLETED` 但结果 URL 为空时继续轮询，不要标成功
- [x] `queue_bases` 三段路径与官方 `cancel_url` / `response_url` 对齐
- [x] 结果只认真实媒体 URL，空壳不写进画廊

### 4. HuggingFace 400 `provider replicate`
- [x] 提交时跳过 replicate 通道
- [x] 失败信息写官方返回，不包一层假成功

---

## P1 用户点名、接线未完成或待确认

### 5. Fal LoRA（官方支持，调查用法后接上，禁止删除）

官方用法（不是「往基座乱塞」，是 Fal 自己的 LoRA 接口）：

```json
"loras": [{ "path": "https://…/xxx.safetensors 或 owner/repo", "scale": 1.0 }]
```

文档出处：
- `fal-ai/flux-lora`、`fal-ai/flux-krea-lora`：`list<LoraWeight>`，`path` + `scale`（默认 1）
- `fal-ai/z-image/turbo/lora`、`fal-ai/krea-2/turbo/lora`、`fal-ai/flux-2/lora`：`loras` 最多 3 条
- `fal-ai/lora`、`fal-ai/sd-loras`、`fal-ai/fast-sdxl`：主端点就带 `loras`
- Civitai 下载 URL 可直接当 `path`（Fal 文档示例：`https://civitai.com/api/download/models/135931`）

同一模型常拆成两个端点：基座出图 + 带 LoRA 的 sibling。有 LoRA 时走 sibling，这是官方用法，不是删除。

- [x] Fal 图片/视频始终显示 LoRA 栏，禁止 `delete base.loras`
- [x] 发送前按官方 schema 填 `loras[{path,scale}]`，AIR 改成 Civitai 下载 URL
- [x] 当前服务若文档无 `loras`、但目录里有 `/lora` sibling，改打 sibling，LoRA 仍发送
- [x] 目录里本来就带 `loras` 的端点（flux-lora、fast-sdxl、flux-general）直接发，不要先删再问
- [x] 左栏可提示推荐端点，但不得因选了基座就把 LoRA 清掉

### 6. 取消队列
- [x] Civitai workflow：`DELETE /v2/consumer/workflows/{id}`
- [x] Fal：官方 `cancel_url` PUT
- [x] HF / 魔搭：基类返回「没有取消接口」，不要假取消

### 7. Provider 能力表（界面别再用同一套表单骗人）
- [ ] Civitai 图片：prompt / 负向 / 宽高 / steps / CFG / sampler / scheduler / seed / AIR / LoRA / 预估 / 成人
- [ ] Civitai 视频：首帧、视频尺寸、引擎字段；不要继续显示图片采样器
- [ ] Fal：只显示当前端点 schema 有的字段
- [ ] HF / 魔搭：prompt、尺寸、steps、seed；LoRA / sampler 不显示或标明不发送
- [x] 视频 Tab 按 recipe=video 显示视频表单（不再只看 Civitai `step=videoGen`）

---

## P2 原功能保持，回归即可

- [ ] 五家后端切换仍在
- [ ] 七个 Tab 仍在：图片、视频、超分、去背景、3D、音频、工作流
- [ ] Civitai 黄 Buzz「未预估 / 预估」仍走 whatif，失败保持「未预估」
- [ ] 成人开关进搜索和提交
- [ ] 导入只填左栏，不代点生成
- [ ] Fal 本地目录离线可筛服务

---



---

## 越权复盘（v0737→v0753，用户纠正后）

**不算越权**

- NanoGPT：用户明确要加。
- HF / 魔搭 LoRA：官方可用。见 [`docs/provider-lora.md`](docs/provider-lora.md)。不要再写成「发明字段」。
- v0753 已撤：魔搭 Civitai→Hub 自动换 Asian-beauty。

**还算偏歪 / 待收**

1. **`static_patch.py` 旁路**  
   启动时改 HTML。v0753 源文件上已是 no-op，但仍挂在 `providers/__init__.py` / `run.sh`。应收进 `static/index.html` 后删掉旁路，避免再 silently 改 hash / persist。
2. **Nano 宽高静默收成目录 resolution token**  
   接线必须用 token（文档已写）。偏歪点是 UI 没让人看见改成了啥。应在 dock / 表单显示实际提交的 `resolution` / `aspect_ratio`。

## 验收用例

1. 导入 `https://civitai.red/images/136863587` → 图片 Tab 参数与站点 Other metadata 一致，工作流 Tab 不拿去硬跑 rgthree
2. Civitai 图片生成能取消排队中的任务
3. Fal 选目录里支持 `loras` 的端点，请求体有 `loras[].path`（Civitai 下载 URL 或 HF repo）
4. Fal 当前行不支持 LoRA 时：目录有 `{id}/lora` 或同前缀 LoRA sibling 则改打 sibling 并带上 `loras`；没有 sibling 则不编字段、左栏 LoRA 不删
5. HF 不再打 replicate
6. Fal 完成但没 URL 时界面仍是等待，不是「成功没图」
7. 切 xAI / 公开接口导入 / 假出图 全部不存在
