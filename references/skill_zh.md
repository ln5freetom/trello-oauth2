# Trello OAuth 2.0 (Atlassian 3LO) — 中文工作流

> 🇬🇧 English: root [SKILL.md](../SKILL.md) · 中文 API 速查：[api_reference_zh.md](api_reference_zh.md)

## 概述

Trello 现代认证走 Atlassian OAuth 2.0：用户在 developer.atlassian.com 的 OAuth 2.0 (3LO) 应用里拿 client_id（32 位字符串）+ client_secret（以 `ATO` 开头）。这类凭证**不是** Trello 旧 API key——用旧 key/token 查询参数方式会报 `invalid key`。本 skill 提供免依赖的 Python 脚本完成 PKCE 授权码流程、token 刷新和 Bearer 调用。

## 前置信息（缺则向用户索要，不要猜）

1. `client_id` — Atlassian OAuth 2.0 client
2. `client_secret` — `ATO` 开头；confidential client 交换时必需
3. `redirect_uri` — app 注册的回调地址（必须与授权请求**逐字符一致**）
4. `scope` — 如 `read:board:trello write:board:trello offline_access`；要 refresh_token 必须含 `offline_access`

## 授权流程（用户只需点一次 Allow）

1. 生成授权链接（PKCE S256 + state 自动生成，verifier 落盘待 exchange 用）：

```bash
PYTHONIOENCODING=utf-8 python scripts/trello_oauth.py pkce-url <client_id> <redirect_uri> [scope]
# 输出 AUTH_URL=...，同时写 <out>/atlassian_auth_url.txt 与 <out>/pkce_verifier.json
```

2. 让用户在自己的浏览器（已登录 Trello/Atlassian 的 Firefox/Chrome）打开 `AUTH_URL`，同意授权（Allow）后跳转到 `redirect_uri?code=...&state=...`，把**地址栏完整 URL** 贴回来。不要用 agent-browser 自动化登录（启动易卡死，Google 登录会被拦截）。

3. 校验 state 后立即换 token（code 一次性、几分钟过期）：

```bash
PYTHONIOENCODING=utf-8 python scripts/trello_oauth.py pkce-exchange <client_id> <client_secret> <redirect_uri> <code> [state]
# 成功输出 TOKEN_SAVED=<out>/trello_token.json；失败输出 ERROR=exchange_failed: <响应体>
```

## Token 生命周期与续期

- `access_token` 约 1 小时过期；`refresh_token` 一次性、90 天有效
- 401 时先刷新（刷新会作废旧 refresh_token，脚本自动保存响应里的新值）：

```bash
PYTHONIOENCODING=utf-8 python scripts/trello_oauth.py refresh <client_id> <client_secret>
# ERROR=refresh_failed (invalid_grant) 说明 refresh_token 已失效 -> 重走 pkce-url 全流程
```

## 调用 Trello API

一律 Bearer，path 以 `/1/` 开头；脚本对 `api.trello.com` 失败自动兜底 `trello.com`：

```bash
# 通用调用（GET/PUT/POST/DELETE，body 可选 JSON 字符串）
PYTHONIOENCODING=utf-8 python scripts/trello_oauth.py api GET /1/members/me/boards?filter=open <access_token>
PYTHONIOENCODING=utf-8 python scripts/trello_oauth.py api PUT "/1/checklists/<idChecklist>/checkItems/<idCheckItem>?state=complete" <access_token>

# 一键导出看板（默认 freelancer，可用第二参数换看板名）：lists + cards + checklists(含 checkItems)
PYTHONIOENCODING=utf-8 python scripts/trello_oauth.py fetch2 <access_token> [board_name]
# 输出 DATA_SAVED=<out>/trello_data.json：checklists[].idCard 关联 cards[].id
```

输出目录：`$TRELLO_OAUTH_DIR` 或 `<当前目录>/.workbuddy`（token、pkce_verifier、数据文件都写这里）。

## 已知坑（2026-09 实测）

- `client_id` 填进旧接口（`?key=` 参数、`/1/authorize`、OAuth 1.0a 端点）全部 404 或 `invalid key`——识别到 32 位 client_id + ATO secret 就直接走本 skill 流程
- WordPress 站点作 redirect_uri 时浏览器可能 301 到 `www.`（如 `nings.eu`→`www.nings.eu`）；exchange 的 `redirect_uri` 必须用授权请求时的原值（非 www），用户贴回的 URL 域名带不带 www 都正常
- `pkce-exchange`/`refresh` 的错误响应体在 stdout 的 `ERROR=` 行里，排错先看它（400 invalid_grant / invalid code 多为过期或 redirect_uri 不匹配）
- Power-Up 类型的 OAuth2 客户端可能被限制在单一 workspace 内
- Windows 下跑脚本设 `PYTHONIOENCODING=utf-8`；沙箱内 python/curl 出网正常，无需提权

## 参考文档

- 本地速查（端点、常用读写接口表、token 生命周期）：[api_reference_zh.md](api_reference_zh.md)
- 官方授权文档：https://developer.atlassian.com/cloud/trello/guides/rest-api/authorization/
- OAuth 2.0 confidential client：https://developer.atlassian.com/cloud/trello/guides/rest-api/oauth-2-confidential-client-usage/
