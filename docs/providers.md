# 供应商插件

每个云厂商一个文件，放在 `providers/`。HTTP 路由只认注册表。

## 会复用
JSON 请求、落盘、任务 id `{provider}|其余`、目录过滤、`GET /api/providers`。

## 不要复用
鉴权头、出图字段、预估费用、Civitai 导入/配方/搜模型。

## 加一家
写 `providers/foo.py` 实现 Provider，token 放 `~/.config/foo/token`，末尾 `register(FooProvider())`，任务 id `foo|{opaque}`，然后重启 `scripts/restart.py` + `run.sh`。
