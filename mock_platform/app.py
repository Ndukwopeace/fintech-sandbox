"""Mock Open Banking platform, modeled on Plaid's sandbox syntax.

Endpoints:
  POST /link/token/create          app -> platform   (step 1: start the connection)
  GET  /link/<link_token>          user's browser    (step 2: hosted auth screen)
  POST /link/<link_token>/submit   user's browser    (steps 3-4: bank login -> public_token)
  POST /item/public_token/exchange app -> platform   (step 5: public_token -> access_token)
  POST /accounts/balance/get       app -> platform   (query account data)
"""
import os
import secrets
import time

from flask import Flask, jsonify, request

app = Flask(__name__)

CLIENT_ID = os.environ.get("MOCK_CLIENT_ID", "sandbox_client_id")
SECRET = os.environ.get("MOCK_SECRET", "sandbox_secret")
PUBLIC_TOKEN_TTL = 30  # seconds, per the "<30 seconds" note on slide 17

BANKS = {"ins_1": "First Sandbox Bank", "ins_2": "Mono Test Bank"}
# Sandbox test user, same idea as Plaid's user_good / pass_good.
SANDBOX_USER = ("user_good", "pass_good")
ACCOUNTS = [{
    "account_id": "acc_sandbox_001",
    "name": "Plaid Checking",
    "type": "depository",
    "subtype": "checking",
    "balances": {
        "available": 100.00,
        "current": 110.00,
        "iso_currency_code": "USD",
    },
}]

link_tokens = {}    # link_token -> {"public_token": None}
public_tokens = {}  # public_token -> expires_at
access_tokens = set()


def auth_ok(body):
    return body.get("client_id") == CLIENT_ID and body.get("secret") == SECRET


def err(code, message, status):
    return jsonify({"error_code": code, "error_message": message}), status


@app.get("/health")
def health():
    return jsonify(status="ok")


@app.post("/link/token/create")
def link_token_create():
    body = request.get_json(silent=True) or {}
    if not auth_ok(body):
        return err("INVALID_API_KEYS", "client_id or secret is wrong", 401)
    token = "link-sandbox-" + secrets.token_hex(8)
    link_tokens[token] = {"public_token": None}
    return jsonify(link_token=token, expiration_seconds=1800)


@app.get("/link/<link_token>")
def link_page(link_token):
    if link_token not in link_tokens:
        return err("INVALID_LINK_TOKEN", "unknown link_token", 404)
    banks = "".join(f'<option value="{k}">{v}</option>' for k, v in BANKS.items())
    return f"""<!doctype html><title>Secure bank login</title>
<h2>Select your bank</h2>
<form method="post" action="/link/{link_token}/submit">
<select name="institution_id">{banks}</select><br>
<input name="username" placeholder="username (user_good)"><br>
<input name="password" type="password" placeholder="password (pass_good)"><br>
<button>Connect</button></form>"""


@app.post("/link/<link_token>/submit")
def link_submit(link_token):
    if link_token not in link_tokens:
        return err("INVALID_LINK_TOKEN", "unknown link_token", 404)
    data = request.get_json(silent=True) or request.form
    if (data.get("username"), data.get("password")) != SANDBOX_USER:
        return err("INVALID_CREDENTIALS", "bad bank credentials", 401)
    if data.get("institution_id") not in BANKS:
        return err("INVALID_INSTITUTION", "unknown institution_id", 400)
    pub = "public-sandbox-" + secrets.token_hex(8)
    public_tokens[pub] = time.time() + PUBLIC_TOKEN_TTL
    link_tokens[link_token]["public_token"] = pub
    # In a real flow this goes to the app's redirect/onSuccess handler.
    return jsonify(public_token=pub)


@app.post("/item/public_token/exchange")
def exchange():
    body = request.get_json(silent=True) or {}
    if not auth_ok(body):
        return err("INVALID_API_KEYS", "client_id or secret is wrong", 401)
    pub = body.get("public_token")
    expires = public_tokens.pop(pub, None)  # single use
    if expires is None:
        return err("INVALID_PUBLIC_TOKEN", "unknown or already used", 400)
    if time.time() > expires:
        return err("PUBLIC_TOKEN_EXPIRED", "public_token expired", 400)
    access = "access-sandbox-" + secrets.token_hex(16)
    access_tokens.add(access)
    return jsonify(access_token=access, item_id="item_" + secrets.token_hex(4))


@app.post("/accounts/balance/get")
def balance_get():
    body = request.get_json(silent=True) or {}
    if not auth_ok(body):
        return err("INVALID_API_KEYS", "client_id or secret is wrong", 401)
    if body.get("access_token") not in access_tokens:
        return err("INVALID_ACCESS_TOKEN", "unknown access_token", 401)
    return jsonify(accounts=ACCOUNTS)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
