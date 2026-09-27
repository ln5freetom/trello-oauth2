# Trello REST API Cheat Sheet (OAuth 2.0 Bearer mode)

> 🇨🇳 中文版：[api_reference_zh.md](api_reference_zh.md)

Auth header: `Authorization: Bearer <access_token>` (OAuth2 clients do NOT support the legacy `?key=&token=` query scheme)

Hosts: prefer `https://api.trello.com`; some routes also work on `https://trello.com` (the script falls back automatically).

## Official docs

- Authorization overview (scope list, token generation): https://developer.atlassian.com/cloud/trello/guides/rest-api/authorization/
- OAuth 2.0 confidential client usage (exchange / refresh / Bearer examples): https://developer.atlassian.com/cloud/trello/guides/rest-api/oauth-2-confidential-client-usage/
- REST API reference: https://developer.atlassian.com/cloud/trello/rest/

## OAuth 2.0 endpoints

| Purpose | Method & URL | Key params (JSON body) |
|---|---|---|
| Build authorize URL | open in browser: `https://auth.atlassian.com/authorize` | client_id, redirect_uri, scope, response_type=code, prompt=consent, code_challenge_method=S256, code_challenge, state |
| Exchange code | POST `https://auth.atlassian.com/oauth/token` | client_id, client_secret, code, grant_type=authorization_code, redirect_uri, code_verifier |
| Refresh token | POST `https://auth.atlassian.com/oauth/token` | client_id, client_secret, grant_type=refresh_token, refresh_token |

- access_token ~1h; refresh_token one-time, 90-day validity; the response returns a **new** refresh_token (the old one is invalidated) — always overwrite the stored value
- 400 invalid_grant / invalid code: code expired, already used, or redirect_uri differs from the authorize request

## Common read routes (Bearer)

| Data | Route |
|---|---|
| My boards | GET `/1/members/me/boards?filter=open&fields=name,id,url` |
| Board lists | GET `/1/boards/{boardId}/lists?fields=name,id` |
| Board cards | GET `/1/boards/{boardId}/cards?fields=name,id,idList,url,desc` |
| All board checklists (with checkItems, idCard links to card) | GET `/1/boards/{boardId}/checklists?fields=name,idCard&checkItems=all` |
| Single card checklists | GET `/1/cards/{cardId}/checklists` |

## Common write routes (write scope required)

| Action | Route |
|---|---|
| Check/uncheck a checklist item | PUT `/1/checklists/{idChecklist}/checkItems/{idCheckItem}?state=complete` (or `incomplete`) |
| Rename a card | PUT `/1/cards/{cardId}?name=...` |
| Add a comment | POST `/1/cards/{cardId}/actions/comments?text=...` |
| Create a card | POST `/1/cards?idList={listId}&name=...` |
| Move a card | PUT `/1/cards/{cardId}?idList={targetListId}` |

## Power-Up / workspace restrictions

Power-Up-type OAuth2 clients may be restricted to a single workspace; non-Power-Up 3LO apps are not. For webhooks use the top-level `POST /1/webhooks` (Bearer), not the legacy `/1/tokens/{token}/webhooks`.
