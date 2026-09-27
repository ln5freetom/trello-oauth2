# trello-oauth2

An [agent skill](#what-is-a-skill) for connecting to the **Trello REST API via Atlassian OAuth 2.0 (3LO + PKCE)** — with a zero-dependency Python script and bilingual (EN / 中文) workflow docs.

> 🇨🇳 中文说明见下方 [中文说明](#中文说明)。

## Why this exists

Trello's modern authentication runs through **Atlassian OAuth 2.0**. A 32-char `client_id` + `ATO`-prefixed secret from [developer.atlassian.com](https://developer.atlassian.com) is **not** a legacy Trello API key — feeding it into the old `?key=&token=` scheme or OAuth 1.0a routes fails with `invalid key` / 404. This skill implements the correct flow end to end:

- **PKCE authorization-code flow** (S256 + state), single user consent click
- **Token refresh** handling (refresh tokens are one-time, 90-day validity, rotated on every refresh)
- **Bearer API calls** with automatic host fallback (`api.trello.com` → `trello.com`)
- Bilingual docs: English default, [中文版](references/skill_zh.md)

## Files

```
trello-oauth2/
├── SKILL.md                        # agent workflow (English, default)
├── scripts/trello_oauth.py         # stdlib-only CLI (Python 3.8+, no pip installs)
└── references/
    ├── api_reference.md            # REST API cheat sheet (EN)
    ├── api_reference_zh.md         # REST API cheat sheet (中文)
    └── skill_zh.md                 # workflow (中文)
```

## Quick start

```bash
# 1. Generate the authorize URL (PKCE + state), print it, let the user click Allow in their browser
python scripts/trello_oauth.py pkce-url <client_id> "https://your-redirect.example/" [scope]
# -> AUTH_URL=...

# 2. User approves; browser lands on <redirect_uri>?code=...&state=... — paste that URL back and exchange immediately
python scripts/trello_oauth.py pkce-exchange <client_id> <client_secret> "https://your-redirect.example/" <code> [state]
# -> TOKEN_SAVED=<out>/trello_token.json

# 3. Call the API (Bearer), e.g. dump a whole board
python scripts/trello_oauth.py fetch2 <access_token> [board_name]
# -> DATA_SAVED=<out>/trello_data.json  (lists + cards + checklists with checkItems)

# 4. Later, when the access token expires (~1h):
python scripts/trello_oauth.py refresh <client_id> <client_secret>
```

Output directory: `$TRELLO_OAUTH_DIR` or `<cwd>/.workbuddy`.

### Script modes

| Mode | Purpose |
|---|---|
| `pkce-url <client_id> <redirect_uri> [scope]` | Build authorize URL (PKCE S256 + state), persist verifier |
| `pkce-exchange <client_id> <client_secret> <redirect_uri> <code> [state]` | Exchange code → tokens |
| `refresh <client_id> <client_secret>` | Refresh access token, save rotated refresh token |
| `fetch2 <access_token> [board_name]` | Dump board lists/cards/checklists to JSON |
| `api <METHOD> <path> <token> [json_body]` | Generic Trello REST call (GET/PUT/POST/DELETE) |

## Prerequisites

1. An Atlassian **OAuth 2.0 (3LO)** app with Trello granular scopes (create/inspect at https://developer.atlassian.com — console → your app). Copy the `client_id` and `client_secret`.
2. A registered `redirect_uri` (must match the authorize request character-for-character).
3. Scopes, e.g. `read:board:trello write:board:trello offline_access` — `offline_access` is required to receive a refresh token.

## Known pitfalls (battle-tested 2026-09)

- 32-char client_id + `ATO` secret in legacy endpoints (`?key=` param, `/1/authorize`, OAuth 1.0a) → `404` / `invalid key`
- The authorization `code` is single-use and expires within minutes — exchange immediately
- WordPress sites often 301 `non-www` → `www`; the exchange `redirect_uri` must still be the original (non-www) value
- OAuth2 errors surface on stdout in the `ERROR=` line — check it first
- Don't automate the Google/Atlassian login with headless browsers; let the user click Allow

## Security

- Tokens are stored locally in `.workbuddy/trello_token.json` — never commit or share it
- Scope is minimal by default (`read/write board:trello`); access tokens live ~1h, refresh tokens 90 days
- Revoke tokens anytime: Trello account settings → Applications, or delete the Atlassian app

## What is a skill?

`SKILL.md` + bundled scripts is the convention used by agent platforms (WorkBuddy / CodeBuddy compatible): the assistant reads `SKILL.md` to learn the workflow and runs `scripts/trello_oauth.py` instead of re-implementing OAuth every session. Copy this folder into your skills directory (`~/.workbuddy/skills/` or `.workbuddy/skills/` in a project), or just use the script standalone.

## 中文说明

一个用于**通过 Atlassian OAuth 2.0 (3LO + PKCE) 连接 Trello REST API** 的 agent skill——零依赖 Python 脚本 + 双语文档。

**为什么需要它**：Trello 现代认证走 Atlassian OAuth 2.0。developer.atlassian.com 上拿到的 32 位 `client_id` + `ATO` 开头的 `client_secret` **不是**旧版 Trello API key——填进旧 `?key=&token=` 方式或 OAuth 1.0a 端点会报 `invalid key` / 404。本 skill 实现正确的完整流程：

- PKCE 授权码流程（S256 + state），用户只需点一次 Allow
- token 刷新（refresh_token 一次性、90 天有效、每次轮换自动保存新值）
- Bearer 调用（`api.trello.com` 失败自动兜底 `trello.com`）
- 双语文档：英文在根目录 [SKILL.md](SKILL.md)，完整中文工作流在 [references/skill_zh.md](references/skill_zh.md)

**快速开始**：

```bash
# 1. 生成授权链接，用户在自己浏览器里点 Allow
python scripts/trello_oauth.py pkce-url <client_id> "https://你的回调地址/" [scope]
# 2. 用户贴回跳转 URL（含 code），立即换 token（code 几分钟内过期）
python scripts/trello_oauth.py pkce-exchange <client_id> <client_secret> "https://你的回调地址/" <code> [state]
# 3. 调用 API / 一键导出看板（lists + cards + checklists）
python scripts/trello_oauth.py fetch2 <access_token> [看板名]
# 4. token 过期（约 1 小时）后刷新
python scripts/trello_oauth.py refresh <client_id> <client_secret>
```

输出目录：`$TRELLO_OAUTH_DIR` 或 `<当前目录>/.workbuddy`。

**前置条件**：

1. [developer.atlassian.com](https://developer.atlassian.com) 的 OAuth 2.0 (3LO) 应用，勾选 Trello granular scopes（如 `read:board:trello write:board:trello offline_access`，要 refresh_token 必须含 `offline_access`）
2. 应用里注册好的 `redirect_uri`（必须与授权请求逐字符一致）
3. Python 3.8+，无任何第三方依赖

**安全**：token 只存在本地 `.workbuddy/trello_token.json`，不要提交或分享；可在 Trello 账号设置 → Applications 随时撤销。

## License

[MIT](LICENSE)
