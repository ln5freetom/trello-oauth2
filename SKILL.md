---
name: trello-oauth2
description: Obtain a Trello API access token via Atlassian OAuth 2.0 (3LO + PKCE) and read/write Trello board data (boards/lists/cards/checklists). Use when the user asks to connect to, log in to, read, or update their Trello data, or when the legacy key/token approach returns "invalid key". 通过 Atlassian OAuth 2.0 (3LO + PKCE) 获取 Trello API 访问令牌并读写看板数据；市场 trello skill 旧 key/token 方式报 invalid key 时使用。
agent_created: true
---

# Trello OAuth 2.0 (Atlassian 3LO)

> 🇨🇳 **中文版工作流**：[references/skill_zh.md]([references/skill_zh.md](https://github.com/ln5freetom/trello-oauth2/blob/main/references/api_reference_zh.md)) · 中文 API 速查：[references/api_reference_zh.md](references/api_reference_zh.md)

## Overview

Modern Trello authentication goes through Atlassian OAuth 2.0. The user obtains a `client_id` (32-char string) and a `client_secret` (prefixed with `ATO`) from their OAuth 2.0 (3LO) app on developer.atlassian.com. These credentials are **not** legacy Trello API keys — using them with the legacy `?key=&token=` query scheme returns `invalid key`. The bundled script handles the PKCE authorization-code flow, token refresh, and Bearer calls with zero dependencies.

## Prerequisites (ask the user, never guess)

1. `client_id` — Atlassian OAuth 2.0 client
2. `client_secret` — prefixed with `ATO`; required for confidential-client exchange
3. `redirect_uri` — must match the app registration **character for character**
4. `scope` — e.g. `read:board:trello write:board:trello offline_access`; include `offline_access` to get a refresh token

## Authorization flow (user clicks Allow once)

1. Generate the authorize URL (PKCE S256 + state auto-generated; verifier persisted for the exchange):

```bash
PYTHONIOENCODING=utf-8 python scripts/trello_oauth.py pkce-url <client_id> <redirect_uri> [scope]
# prints AUTH_URL=...; writes <out>/atlassian_auth_url.txt and <out>/pkce_verifier.json
```

2. Have the user open `AUTH_URL` in their own browser (already logged into Trello/Atlassian), approve the consent screen (Allow), then paste back the **full redirect URL** (`redirect_uri?code=...&state=...`). Do not automate the login with agent-browser (daemon startup hangs, Google blocks automated browsers).

3. Exchange immediately — the code is single-use and expires within minutes:

```bash
PYTHONIOENCODING=utf-8 python scripts/trello_oauth.py pkce-exchange <client_id> <client_secret> <redirect_uri> <code> [state]
# success: TOKEN_SAVED=<out>/trello_token.json; failure: ERROR=exchange_failed: <response body>
```

## Token lifecycle & renewal

- `access_token` expires after ~1 hour; `refresh_token` is one-time and valid for 90 days
- On 401, refresh first (refreshing invalidates the old refresh token; the script saves the rotated one automatically):

```bash
PYTHONIOENCODING=utf-8 python scripts/trello_oauth.py refresh <client_id> <client_secret>
# ERROR=refresh_failed (invalid_grant) means the refresh token is dead -> redo the pkce-url flow
```

## Calling the Trello API

Always Bearer, path starts with `/1/`; the script falls back from `api.trello.com` to `trello.com` automatically:

```bash
# Generic call (GET/PUT/POST/DELETE, optional JSON body)
PYTHONIOENCODING=utf-8 python scripts/trello_oauth.py api GET /1/members/me/boards?filter=open <access_token>
PYTHONIOENCODING=utf-8 python scripts/trello_oauth.py api PUT "/1/checklists/<idChecklist>/checkItems/<idCheckItem>?state=complete" <access_token>

# One-shot board dump (default board "freelancer", override via 2nd arg): lists + cards + checklists (with checkItems)
PYTHONIOENCODING=utf-8 python scripts/trello_oauth.py fetch2 <access_token> [board_name]
# prints DATA_SAVED=<out>/trello_data.json: checklists[].idCard links to cards[].id
```

Output directory: `$TRELLO_OAUTH_DIR` or `<cwd>/.workbuddy` (token, pkce_verifier, and data files land there).

## Known pitfalls (tested 2026-09)

- Plugging the `client_id` into legacy endpoints (`?key=` param, `/1/authorize`, OAuth 1.0a routes) returns 404 or `invalid key` — a 32-char client_id + ATO secret means: use this skill's flow
- When a WordPress site is the redirect_uri, the browser may 301 to `www.` (e.g. `nings.eu` → `www.nings.eu`); the exchange `redirect_uri` must still be the exact value used in the authorize request (non-www). Pasted URLs with or without `www` are both fine
- Error response bodies appear on stdout in the `ERROR=` line — check it first (400 invalid_grant / invalid code usually means expired code or redirect_uri mismatch)
- Power-Up-type OAuth2 clients may be restricted to a single workspace
- Set `PYTHONIOENCODING=utf-8` on Windows; sandboxed python/curl have normal network egress, no elevation needed

## Reference docs

- Local cheat sheet (endpoints, common read/write routes, token lifecycle): [api_reference.md](references/api_reference.md)
- Official authorization guide: https://developer.atlassian.com/cloud/trello/guides/rest-api/authorization/
- OAuth 2.0 confidential client: https://developer.atlassian.com/cloud/trello/guides/rest-api/oauth-2-confidential-client-usage/
