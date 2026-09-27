#!/usr/bin/env python3
"""Trello API via Atlassian OAuth 2.0 (3LO) — stdlib only, no dependencies.

Modes:
  pkce-url <client_id> <redirect_uri> [scope]
        Generate authorize URL (PKCE S256 + state). Saves verifier to
        <out>/pkce_verifier.json and URL to <out>/atlassian_auth_url.txt.
  pkce-exchange <client_id> <client_secret> <redirect_uri> <code> [state]
        Exchange authorization code for tokens -> <out>/trello_token.json.
  refresh <client_id> <client_secret>
        Refresh access token using the refresh_token stored in
        <out>/trello_token.json. Saves the NEW refresh_token (old one is
        invalidated, refresh tokens are one-time, 90-day validity).
  fetch2 <access_token> [board_name]
        Dump a board (default "freelancer"): lists, cards, checklists
        (with checkItems) -> <out>/trello_data.json.
  api <METHOD> <path> <access_token> [json_body]
        Generic Trello REST call with Bearer auth. path must start with /1/.
        Example: api PUT /1/checklists/<id>/checkItems/<itemId>?state=complete <token>

Output dir: $TRELLO_OAUTH_DIR or <cwd>/.workbuddy
"""
import base64
import hashlib
import json
import os
import secrets
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

OUT_DIR = os.environ.get("TRELLO_OAUTH_DIR") or os.path.join(os.getcwd(), ".workbuddy")
TOKEN_FILE = os.path.join(OUT_DIR, "trello_token.json")
ATL_AUTH_URL_FILE = os.path.join(OUT_DIR, "atlassian_auth_url.txt")
PKCE_FILE = os.path.join(OUT_DIR, "pkce_verifier.json")
DATA_FILE = os.path.join(OUT_DIR, "trello_data.json")

AUTHORIZE_ENDPOINT = "https://auth.atlassian.com/authorize"
TOKEN_ENDPOINT = "https://auth.atlassian.com/oauth/token"
API_HOSTS = ("https://api.trello.com", "https://trello.com")


def enc(s):
    return urllib.parse.quote(str(s), safe="")


def _save_tokens(tok):
    tok["obtained_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(TOKEN_FILE, "w", encoding="utf-8") as f:
        json.dump(tok, f, indent=2)
    print("TOKEN_SAVED=" + TOKEN_FILE, flush=True)


def mode_pkce_url(client_id, redirect_uri, scope="read:board:trello write:board:trello offline_access"):
    verifier = base64.urlsafe_b64encode(secrets.token_bytes(48)).rstrip(b"=").decode()
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    state = secrets.token_urlsafe(16)
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(PKCE_FILE, "w", encoding="utf-8") as f:
        json.dump({"client_id": client_id, "redirect_uri": redirect_uri,
                   "verifier": verifier, "state": state}, f, indent=2)
    url = (AUTHORIZE_ENDPOINT + "?client_id=" + enc(client_id)
           + "&scope=" + enc(scope)
           + "&redirect_uri=" + enc(redirect_uri)
           + "&response_type=code&prompt=consent"
           + "&code_challenge_method=S256&code_challenge=" + enc(challenge)
           + "&state=" + enc(state))
    with open(ATL_AUTH_URL_FILE, "w", encoding="utf-8") as f:
        f.write(url)
    print("AUTH_URL=" + url, flush=True)


def mode_pkce_exchange(client_id, client_secret, redirect_uri, code, state=None):
    with open(PKCE_FILE, encoding="utf-8") as f:
        pk = json.load(f)
    if state and state != pk.get("state"):
        print("ERROR=state_mismatch", flush=True)
        sys.exit(1)
    body = json.dumps({
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": redirect_uri,
        "code_verifier": pk["verifier"],
    }).encode("utf-8")
    req = urllib.request.Request(TOKEN_ENDPOINT, data=body,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            tok = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print("ERROR=exchange_failed: " + e.read().decode("utf-8", "replace"), flush=True)
        sys.exit(1)
    _save_tokens(tok)


def mode_refresh(client_id, client_secret):
    with open(TOKEN_FILE, encoding="utf-8") as f:
        tok = json.load(f)
    body = json.dumps({
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "refresh_token",
        "refresh_token": tok["refresh_token"],
    }).encode("utf-8")
    req = urllib.request.Request(TOKEN_ENDPOINT, data=body,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            new = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print("ERROR=refresh_failed: " + e.read().decode("utf-8", "replace"), flush=True)
        print("HINT=refresh_token one-time/90d expired -> rerun pkce-url flow", flush=True)
        sys.exit(1)
    if "refresh_token" not in new:
        new["refresh_token"] = tok["refresh_token"]  # keep old only if not rotated
    _save_tokens(new)


def _bearer_request(method, path, token, json_body=None):
    """Send one Bearer request, try api.trello.com then trello.com fallback."""
    url = API_HOSTS[0] + path
    headers = {"Authorization": "Bearer " + token}
    data = None
    if json_body is not None:
        data = json_body.encode("utf-8")
        headers["Content-Type"] = "application/json"
    for i, host in enumerate(API_HOSTS):
        try:
            req = urllib.request.Request(host + path, data=data, headers=headers, method=method)
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.status, r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            text = e.read().decode("utf-8", "replace")
            if e.code in (401, 403):
                print("AUTH_ERROR=HTTP %s: %s" % (e.code, text[:300]), flush=True)
                if e.code == 401:
                    print("HINT=access_token expired -> run: refresh <client_id> <client_secret>", flush=True)
                sys.exit(1)
            if i + 1 < len(API_HOSTS):
                continue
            print("HTTP_ERROR=HTTP %s: %s" % (e.code, text[:500]), flush=True)
            sys.exit(1)


def mode_api(method, path, token, json_body=None):
    status, text = _bearer_request(method.upper(), path, token, json_body)
    print("STATUS=" + str(status), flush=True)
    print(text, flush=True)


def mode_fetch2(token, board_name="freelancer"):
    def get(path):
        _, text = _bearer_request("GET", path, token)
        return json.loads(text)

    boards = get("/1/members/me/boards?filter=open&fields=name,id,url")
    board = next((b for b in boards if b["name"].strip().lower() == board_name.strip().lower()), None)
    if board is None:
        result = {"error": "board_not_found",
                  "boards": [{"id": b["id"], "name": b["name"]} for b in boards]}
    else:
        lists = get("/1/boards/%s/lists?fields=name,id" % board["id"])
        cards = get("/1/boards/%s/cards?fields=name,id,idList,url,desc" % board["id"])
        checklists = get("/1/boards/%s/checklists?fields=name,idCard&checkItems=all" % board["id"])
        result = {"board": board, "lists": lists, "cards": cards, "checklists": checklists}
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print("DATA_SAVED=" + DATA_FILE, flush=True)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    mode = sys.argv[1]
    try:
        if mode == "pkce-url":
            if len(sys.argv) < 4:
                print("usage: pkce-url <client_id> <redirect_uri> [scope]")
                sys.exit(2)
            scope = sys.argv[4] if len(sys.argv) > 4 else "read:board:trello write:board:trello offline_access"
            mode_pkce_url(sys.argv[2].strip(), sys.argv[3].strip(), scope)
        elif mode == "pkce-exchange":
            if len(sys.argv) < 6:
                print("usage: pkce-exchange <client_id> <client_secret> <redirect_uri> <code> [state]")
                sys.exit(2)
            state = sys.argv[6].strip() if len(sys.argv) > 6 else None
            mode_pkce_exchange(sys.argv[2].strip(), sys.argv[3].strip(),
                               sys.argv[4].strip(), sys.argv[5].strip(), state)
        elif mode == "refresh":
            if len(sys.argv) < 4:
                print("usage: refresh <client_id> <client_secret>")
                sys.exit(2)
            mode_refresh(sys.argv[2].strip(), sys.argv[3].strip())
        elif mode == "fetch2":
            if len(sys.argv) < 3:
                print("usage: fetch2 <access_token> [board_name]")
                sys.exit(2)
            board_name = sys.argv[3] if len(sys.argv) > 3 else "freelancer"
            mode_fetch2(sys.argv[2].strip(), board_name)
        elif mode == "api":
            if len(sys.argv) < 5:
                print("usage: api <METHOD> <path> <access_token> [json_body]")
                sys.exit(2)
            json_body = sys.argv[5] if len(sys.argv) > 5 else None
            mode_api(sys.argv[2].strip(), sys.argv[3].strip(), sys.argv[4].strip(), json_body)
        else:
            print("unknown mode: %s" % mode)
            sys.exit(2)
    except FileNotFoundError as e:
        print("ERROR=file_missing: %s (run earlier flow steps first)" % e.filename, flush=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
