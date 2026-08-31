# 供应商插件

每个云厂商一个文件，放在 `providers/`。HTTP 路由只认注册表 `providers/__init__.py`。

## 会复用

JSON 请求、落盘 `out/`、任务 id `{provider}|其余`、目录过滤、`GET /api/providers`、UI 从 `/api/providers` 画切换条。

## 不要复用

鉴权头、出图字段、预估费用、Civitai 导入 / 配方 / 搜模型 / 工作流 AIR。

## 现有 id

见 [`dev.md`](dev.md) 的供应商表。魔搭是 **两家**：`modelscope-ai` 与 `modelscope-cn`，token 和 base URL 都不共用。

## 加一家

1. 写 `providers/foo.py` 实现 Provider（`id` `label` `has_key` `catalog` `generate` `job`）。
2. token 放 `~/.config/foo/token`。
3. 文件末尾 `register(FooProvider())`。
4. 任务 id `foo|{opaque}`。
5. `python3 scripts/restart.py && ./run.sh`。

不要在新适配器里 fallback 到另一家的 token 或域名。
