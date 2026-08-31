# Civitai Studio — UI Spec（Night Lab · Catalog）

产品名 **Civitai Studio**。本地生成台：左配方 / 服务 / 参数，右成片。中文界面，`lang=zh-CN`。不改 `server.py`。

生成**仅**由用户点击 `#go`；预估仅 `#whatif`。加载、切配方、选服务、导入、defaults **不得**代点。

服务列表来自 **`GET /api/catalog`**（orchestration `/v2/services` 的 304 条瘦身项）。**禁止**写死 MiniMax / Wan / Hunyuan 等引擎菜单。`GET /api/defaults` 的 `videoPresets` **忽略**，不得当作引擎下拉数据源。

---

## 1. Layout

全视口 `display: grid; grid-template-columns: 440px 1fr; min-height: 100vh`。

| 区 | 宽/高 | 行为 |
|---|---|---|
| `aside` 左栏 | **440px** 固定，`100vh` | `flex` 列：顶栏 → 配方 → 可滚 `.form` → **sticky dock** |
| `header.brand` | 栏宽 | 字标 + `#mature`；不随表单滚动 |
| `nav.recipes` | 栏宽 | 分段控件：**图片 / 视频 / 超分 / 去背景**。子项 `flex: 1`，可再加同级 `button` |
| `#serviceList.svc-list` | `.form` 内、导入之上 | 当前配方目录项（Runway 密度）；内部滚动 |
| `.form` | `flex: 1; overflow: auto` | 服务列表 → 导入、提示词、动态字段、LoRA、高级参数 |
| `.dock` | 栏底 `flex-shrink: 0` | 贴在左栏底部：`#cost`、`#whatif`、`#go`、`#dockStatus` |
| `main` | `flex: 1` | 顶状态 `#status` + 画廊 `#grid` + 空态 |

Dock **必须在 aside 内**，不要移到 `main` 或 `body` 底。`#dockStatus` 在按钮旁（或紧邻按钮行）。

---

## 2. Color tokens

```css
:root {
  --bg:     #09090b;  /* 页底 */
  --panel:  #111114;  /* 左栏 / 卡片 */
  --elev:   #18181f;  /* 输入、抬升面 */
  --line:   #2a2a33;  /* 分割 */
  --text:   #f4f1ea;  /* 暖白 */
  --muted:  #8b8796;  /* 标签 / 次文 */
  --accent: #ff4d3d;  /* 生成（珊瑚） */
  --buzz:   #f0c36a;  /* 预估 / 费用 / 焦点环 */
  --ok:     #5dcaa0;  /* 成功 / 可用 */
  --nsfw:   #ff5c8a;  /* 成人开 */
}
```

禁止改成泛紫 shadcn。焦点环 **1px `--buzz`**。禁用生成钮 `opacity ~ .55`。

---

## 3. Type

- 字体：Google **Outfit**（拉丁字标）+ **Noto Sans SC**（正文）。
- 字标：Outfit，宽 tracking（约 `.16–.22em`），「Civitai Studio」+ 小金色 buzz 闪电。
- 标签：11px、`--muted`、轻字距。
- 正文 / 输入：13–14px、`--text`。
- 生成钮：16px / 700。费用：12–13px `--buzz`。
- 圆角：钮 8–10px；卡片 / 画廊图 **12px**。
- 服务行：13px 名 + 11px 次文，行高紧凑。

---

## 4. Catalog

`GET /api/catalog` → `{ total, items: [...] }`。

单条 shape（字段来自 `docs/catalog.json` / 服务端 `slim_item`）：

```
{
  id, name, description, category, status, step, tags, modalities,
  engine, operation, ecosystem, model, version, provider,
  parameters: { engine, operation, ecosystem, model, version, provider, ... }
}
```

`status`: `available` | `degraded` | `unknown` | `unavailable`。

Live orchestration 可能 404：UI 必须把列表置空，并在 **`#dockStatus` 写中文错误**（例如「无法加载服务目录（404）」）。不要用硬编码引擎列表填空。

`parameters` 优先于顶层同名键：选中服务时

```
store serviceId
copy engine / operation / ecosystem / model / version / provider
  from item.parameters || item
```

---

## 5. Recipes（`.recipes`，可扩展）

横向分段，激活类名 **`.on`**。切配方**只过滤 `#serviceList`**，改字段显隐，**绝不** `POST /api/generate` 或 `/api/whatif`。

| 按钮 id | 文案 | 过滤 |
|---|---|---|
| `#tabImage` | 图片 | `category === 'image' && step === 'imageGen'` |
| `#tabVideo` | 视频 | `category === 'video' && step === 'videoGen'` |
| `#tabUpscale` | 超分 | `tags` 含 `'upscaling'`，或 `id` / `name` 含 `upscaler`（大小写不敏感） |
| `#tabBg` | 去背景 | `tags` 含 `'background-removal'` |

**渲染目录返回的任何项**，不要写死服务名。新增配方 = 再加一颗同级 button + 一条谓词。

`setKind('image'|'video')` 映射到对应配方（兼容旧调用），同样只过滤、不提交。

---

## 6. Service list（`#serviceList`）

位于 `.form` 内、导入栏之上（配方 nav 正下方）。行 `.svc-row` / 选中 `.svc-row.on`；降级 `.badge-deg`（`--buzz`）；未上线 `.svc-other`。

排序：`available` → `degraded` → `unknown` / `unavailable`。

| 状态 | 展示 |
|---|---|
| `available` | 始终可见 |
| `degraded` | 可见，黄色徽章 **「降级」** |
| `unknown`、`unavailable` | 收进折叠 `<details class="svc-other">`，summary **「其它 / 未上线」** |

点击一行选中。默认选中过滤结果里**第一个 available**；没有 available 则第一个 degraded；再没有则不强选。切配方只过滤，绝不 generate / whatif。

选中后：记下 `serviceId`，从 `item.parameters || item` 拷贝 `engine / operation / ecosystem / model / version / provider`，按第 7 节刷新动态字段。隐藏 `#vPreset` 可同步所选 `id`（**不可见**）。禁止用它或 `defaults.videoPresets` 当「视频引擎」菜单。

---

## 7. Dynamic fields

显隐按所选服务的 `operation` / `step` / `modalities`，不要用写死的引擎名（MiniMax / Wan / Hunyuan）。

**始终可见**

提示词、负面、底模 AIR、LoRA、成人开关（成人在顶栏）。

**`#imageFields`**（宽高、步数、CFG、数量、高级采样）：所选 `step === 'videoGen'` 时隐藏；其它服务显示。

**`#videoFields`**：所选 `step === 'videoGen'`（或当前配方是视频且尚未选中项）时显示。时长、turbo / fast。视频 payload 仍带 `duration, firstFrame, lastFrame, turbo, fast`。

**首帧** `#firstFile` / `#firstFrame`：`operation` 为 `imageToVideo` | `image-to-video` | `firstLastFrameToVideo`。

**尾帧** `#lastFrame`：`firstLastFrameToVideo`（可空）。

**参考图** `#refs`：`operation` 匹配 `referenceToVideo` | `reference-to-video` | `/reference/i`，或 `name` 含「参考」。FileReader dataURL；payload `images` 为 URL 数组。

**源图**（编辑 / 变体 / 超分 / 去背景等）：`operation` 为 `editImage` | `createVariant`，或 `modalities.input` 含 `image` 且不是纯文本（且不是上面的 i2v / 参考）。`#sourceFile`（FileReader dataURL）+ `#sourceImage`（URL）。payload `sourceImage`，并作为 `firstFrame` 别名。

高级参数 `<details>` **无 `open`**：sampler、scheduler、`#model`（turbo|raw）、视频的 `#vSeed #vWidth #vHeight #vSteps #vRes`。

---

## 8. Payload

`POST /api/generate` 与 `POST /api/whatif` 同一 `payload()`：

```
serviceId, kind,          // kind = item.category==='video' ? 'video' : 'image'
engine, operation, ecosystem, model, version, provider,
prompt, negativePrompt, width, height, steps, cfgScale, quantity,
sampler, scheduler, seed, diffusionModel, loras, allowMatureContent
```

视频附加：`duration, firstFrame, lastFrame, turbo, fast, images`（参考图 URL 数组）。

编辑 / i2i：`sourceImage`（及 `firstFrame` 别名）来自源图上传或 URL。

`loras`: `[{ air, strength, name }]`。`seed` 空字符串 → `null`。

---

## 9. Component inventory

### 9.1 Import bar

「导入 Civitai 图/视频」：`#imgId`（ID 或 URL）+ `#importImg`。点导入 → `GET /api/import-image/:id` → `applyImport`。不触发生成。从 URL 抽 `images/(\d+)`。

### 9.2 NSFW switch

`#mature` 在顶栏，**默认 checked**；启动后再被 `GET /api/defaults` 的 `allowMatureContent` 覆盖。开：`--nsfw` 轨道。

### 9.3 Dropzone + FileReader

`#firstFile` / `#sourceFile` / `#refs` 内文件：`FileReader.readAsDataURL` 写入对应 URL 框或参考数组。`#lastFrame` 单独一行。

### 9.4 LoRA chip

`renderLoras` 可改 HTML，但 **strength `<input type="number">` 必须保留**，删钮仍 `loras.splice` + `renderLoras`。`#loraQ` + `#searchLora` → `#hits` → `#loras`。`window.addLora`。

### 9.5 Dock

`#cost`（金）、`#whatif`（ghost「预估」）、`#go`（大珊瑚「生成」）、`#dockStatus`（钮旁，队列/错误）。`setStatus` 同步 `#status` 与 `#dockStatus`，并设 `.ok` / `.bad`。

### 9.6 Gallery + empty

`#grid`：`repeat(auto-fill, minmax(240px, 1fr))`。卡片 12px，图/视频拉满宽，视频 `controls`，`.meta` 说明。

空态（无卡时可见）：**「还没有成片」** + 去点「生成」。`addCard` prepend 后隐藏空态。不要用空态替代 `#grid`（id 必须始终存在）。

---

## 10. Interaction rules

| 规则 | 细节 |
|---|---|
| 禁止自动生成 | `load` / `defaults` / `catalog` / `import` / `whatif` / 切配方 / 选服务 **不得**调用 generate。仅 `#go` click。 |
| 禁止自动预估 | 仅 `#whatif` click → `POST /api/whatif`。 |
| 配方切换 | `setKind` / `setRecipe` 只改 `.on`、过滤列表、字段显隐。 |
| 导入 | 失败写 status，不改队列。若返回 `serviceId` 则选中该服务。 |
| 轮询 | `GET /api/jobs/:id`，3s，最多 120 次；succeeded 则 `addCard`。 |
| 成人 | payload `allowMatureContent: $('#mature').checked`。 |
| 目录失败 | 空列表 + `#dockStatus` 中文错误。 |

可见文案与 placeholder 一律中文。

---

## 11. APIs（保持）

| 方法 | 路径 |
|---|---|
| GET | `/api/catalog` |
| GET | `/api/defaults`（samplers / schedulers / defaults / hasToken；**忽略 videoPresets**） |
| POST | `/api/generate` |
| POST | `/api/whatif` |
| GET | `/api/jobs/:id` |
| GET | `/api/import-image/:id` |
| GET | `/api/search?type=LORA&q=` |
| GET | `/api/model-version/:id` |

---

## 12. JS contract（存活）

`$(id)` = `getElementById`。下列 **id 一字不改**：

`tabImage tabVideo imgId importImg prompt negative imageFields width height steps cfg qty sampler scheduler model seed videoFields duration vSeed vWidth vHeight vSteps vRes firstFrame firstFile lastFrame turbo fast diffusion ckptName loraQ searchLora hits loras mature cost dockStatus whatif go status grid`

**新增**：`serviceList tabUpscale tabBg sourceFile sourceImage refs`。隐藏 `#vPreset` 可选（同步所选 id）。

保留 `payload()`、`poll`、`applyImport`、`loras` 数组、`setKind`、`window.addLora`、`window.onerror`、`addCard`。单文件 vanilla JS，无前端框架。
