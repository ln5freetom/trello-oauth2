# Trello REST API 速查（OAuth 2.0 Bearer 模式）

> 🇬🇧 English: [api_reference.md](api_reference.md)

认证头：`Authorization: Bearer <access_token>`（OAuth2 client 不支持旧 `?key=&token=` 查询参数方式）

Host：首选 `https://api.trello.com`，个别路径可用 `https://trello.com` 兜底（脚本已内置 fallback）。

## 官方文档

- 授权总览（scope 清单、token 生成）：https://developer.atlassian.com/cloud/trello/guides/rest-api/authorization/
- OAuth 2.0 confidential client 用法（exchange / refresh / Bearer 调用示例）：https://developer.atlassian.com/cloud/trello/guides/rest-api/oauth-2-confidential-client-usage/
- REST API 参考：https://developer.atlassian.com/cloud/trello/rest/

## OAuth 2.0 端点

| 用途 | 方法与 URL | 关键参数（JSON body） |
|---|---|---|
| 生成授权链接 | 浏览器打开 `https://auth.atlassian.com/authorize` | client_id, redirect_uri, scope, response_type=code, prompt=consent, code_challenge_method=S256, code_challenge, state |
| 换 token | POST `https://auth.atlassian.com/oauth/token` | client_id, client_secret, code, grant_type=authorization_code, redirect_uri, code_verifier |
| 刷新 token | POST `https://auth.atlassian.com/oauth/token` | client_id, client_secret, grant_type=refresh_token, refresh_token |

- access_token ~1h；refresh_token 一次性、90 天；响应会返回**新** refresh_token（旧值作废），必须覆盖保存
- 400 invalid_grant / invalid code：code 过期、已用、或 redirect_uri 与授权请求不一致

## 常用读接口（Bearer）

| 数据 | 路径 |
|---|---|
| 我的看板 | GET `/1/members/me/boards?filter=open&fields=name,id,url` |
| 看板列表 | GET `/1/boards/{boardId}/lists?fields=name,id` |
| 看板卡片 | GET `/1/boards/{boardId}/cards?fields=name,id,idList,url,desc` |
| 看板全部 checklist（含勾选项，idCard 关联卡片） | GET `/1/boards/{boardId}/checklists?fields=name,idCard&checkItems=all` |
| 单卡片 checklist | GET `/1/cards/{cardId}/checklists` |

## 常用写接口（需 write scope）

| 操作 | 路径 |
|---|---|
| 勾选/取消 checklist 项 | PUT `/1/checklists/{idChecklist}/checkItems/{idCheckItem}?state=complete`（或 incomplete） |
| 改卡片名 | PUT `/1/cards/{cardId}?name=...` |
| 加评论 | POST `/1/cards/{cardId}/actions/comments?text=...` |
| 建卡片 | POST `/1/cards?idList={listId}&name=...` |
| 移动卡片 | PUT `/1/cards/{cardId}?idList={targetListId}` |

## Power-Up / workspace 限制

Power-Up 类型的 OAuth2 客户端可能被限制在单一 workspace；非 Power-Up 的 3LO 应用无此限制。Webhook 用顶层 `POST /1/webhooks`（Bearer），不走旧的 `/1/tokens/{token}/webhooks`。
