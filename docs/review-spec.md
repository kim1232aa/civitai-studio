# 审查规范

常驻规则。一次审查的截图和结论写在 [`review.md`](review.md)，不要把本文件改成流水账。

审查员：质量审查员。**功能没改好不要叫。** 只在页面上声称的行为已经能用（新成片、hash 不漂、工作流规则）之后才叫。纯文档、空提示词弹窗、未过关的 P0 都不要叫。开发约定见 [`dev.md`](dev.md)。

## 谁做什么

| 角色 | 做 | 不做 |
| --- | --- | --- |
| 审查员 | 硬刷新页面、读代码、截图 UI、**自己点** 导入 / 预估 / 生成 | 用 curl / Python / 自己的工具调生成 API；代点；开第二路浏览器或桌面自动化抢 `8765` |
| 开发 | 修完改标题戳、commit、push、告诉审查员当前戳 | 点测进行中改 `static/index.html`、重启 `8765`、对同一端口开 browserUse |

密钥不进页面。审查截图不要带 token 明文。

## 认哪一版

- **只认标题栏** `Civitai Studio v0xxx`。Dock 会被「已加载 N 个模型」盖掉，不能当版本。
- 关掉旧标签，硬刷新。v0721 / v0731 这类旧戳直接打回，不论功能看起来对不对。
- 开发口头「已经修了」不算。截图标题必须等于当时仓库最新戳。
- 文档-only 提交不改戳。改了 UI / 行为必须 +1。

## 点测期间

- 一路标签。不要第二窗口、第二 agent 抢 `http://127.0.0.1:8765`。
- 开发不重启、不热改页面。审查员说点测开始之后，P1 先记账，等点测结束再改。
- 不要代跑 `POST /api/generate`。`GET /api/go` 只证明点击到了前端，**不等于出图**。

## 生成过关（产品标准）

空提示词弹出「先写提示词」**不算过关**。必须成片栏出现**新文件**（`out/` 多一张，画廊能看见）。

步骤：

1. 硬刷新，确认标题戳。
2. 导入 `https://civitai.red/images/139791102`（hinablue，Z Image Turbo）。提示词应被填上。
3. 文生图：`sourceImage` / `firstFrame` **必须空**。不要把导入的 `mediaUrl` 填进去。
4. 底模应对上：
   - Fal：`fal-ai/z-image/turbo`；有 LoRA 用 `fal-ai/z-image/turbo/lora`
   - Hugging Face / 魔搭 AI / 魔搭 CN：`Tongyi-MAI/Z-Image-Turbo`
5. 审查员自己点四家：**Fal、Hugging Face、魔搭 AI、魔搭 CN**。每家都要新成片。
6. 魔搭 AI 若 `api-inference.modelscope.ai` 解析失败：必须报连接错误。**静默切到魔搭 CN 算失败。**
7. 点「魔搭」后 URL 自己漂到 `#fal` / `#huggingface`（没有再点）算失败。
8. 点生成不得因为旧 hash / `persistBackend` 把供应商改走。

Civitai 本家导入文案始终是「导入 Civitai 图/视频」，四家都能导入这张 Civitai 图。

## 工作流过关（代码 + 页面）

- `.yaml`、sidecar `config.json` 不当 Comfy 图。
- zip 优先于 sidecar JSON；解析失败试下一个附件。
- PNG 走 `parse_png_text`（tEXt / iTXt 的 `workflow` / `prompt`），不要对 PNG 直接 `json.loads`。
- `customComfy.comfyImage` 只接受已是 `urn:air:…comfyimage…` 的 AIR，禁止把 `firstFrame` 写进去。
- 工作流 tab 必须藏模型列表（`.hidden` + `[hidden] { display:none !important }`）。
- 刷新：不要单靠 `sessionStorage` 把工作流 tab 打开。hash 已有 `&recipe=workflow` 时，应恢复 `#wfAir`，boot `persistBackend` 不得把 `&recipe=workflow` 抹掉。
- 对照表第一列用 **filename**，不是模型 title。未匹配行不要画两遍。matched nodepacks 要有行。

## 其它禁区

- 不要为了过关删已有能力（五家后端、七个配方 tab、导入 / 预估 / 生成、目录、Night Lab）。
- 不要把魔搭 AI 和魔搭 CN 重新合成一家，不要 token / base URL 交叉。
- 不要用苹果提示词当夹具。夹具就是 `139791102`。
- 选中模型后，目录刷新不得冲掉「已选 …」。橙框 hover 不算选中。
- Fal 目录一次最多画出约 60 条，禁止整页重载跳回 Civitai。

## 怎么交卷

每条结论配：标题戳截图 + 对应证据（hash、已选模型、成片文件名、或代码位置）。没有新成片就写失败，不要把「按钮变提交中」或「dock 先写提示词」写成通过。
