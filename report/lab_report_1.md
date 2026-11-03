# Lab Report 1: Open Banking Sandbox Connection

## 1. Sandbox Config Blueprint

**Aggregator sandbox:** Plaid-style mock Open Banking platform (Flask, runs in Docker
as the `platform` service). Endpoints and field names follow Plaid syntax
(`link_token`, `public_token`, `access_token`, `accounts/balance/get`).

**Sandbox credentials:** `client_id=sandbox_client_id`, `secret=sandbox_secret`
(supplied by environment variables, never hard coded in the client).
Test bank login: `user_good` / `pass_good`.

**Initialization code used** (`client/lab.py`):

```python
    wait_for_platform()
    creds = {"client_id": CLIENT_ID, "secret": SECRET}
    # Step 1: app initiates the connection.
    link_token = post("/link/token/create", **creds)["link_token"]
    log(f"1. link_token created: {link_token}")
    # Steps 2-4: the end user authenticates with their bank on the aggregator's
    # hosted screen. Simulated here with the sandbox test user.
    log(f"2. hosted auth screen: {BASE}/link/{link_token}")
    r = requests.post(f"{BASE}/link/{link_token}/submit", timeout=10, json={
        "institution_id": "ins_1", "username": "user_good", "password": "pass_good"})
    r.raise_for_status()
    public_token = r.json()["public_token"]
    log("3. user selected First Sandbox Bank and logged in (credentials never seen by app)")
    log(f"4. bank issued temporary public_token: {public_token}")
    # Step 5: backend exchanges the public_token for the permanent access_token.
    access_token = post("/item/public_token/exchange", public_token=public_token, **creds)["access_token"]
    log(f"5. exchanged for access_token: {mask(access_token)} (kept server-side)")
    accounts = post("/accounts/balance/get", access_token=access_token, **creds)["accounts"]
    payload = [{
        "account_id": a["account_id"],
        "available_balance": a["balances"]["available"],
        "current_balance": a["balances"]["current"],
        "currency_code": a["balances"]["iso_currency_code"],
    } for a in accounts]
    log("SUCCESS - retrieved sandbox target data array:")
    log(json.dumps(payload, indent=2))
    os.makedirs(REPORT_DIR, exist_ok=True)
    write_report(payload)
    log(f"report written to {REPORT_DIR}/lab_report_1.md")
```

## 2. Output Log Payload

```text
[17:32:35] 1. link_token created: link-sandbox-27c71c4e4d3c0fca
[17:32:35] 2. hosted auth screen: http://localhost:5000/link/link-sandbox-27c71c4e4d3c0fca
[17:32:35] 3. user selected First Sandbox Bank and logged in (credentials never seen by app)
[17:32:35] 4. bank issued temporary public_token: public-sandbox-6b0beeb8316cb7d0
[17:32:35] 5. exchanged for access_token: access-sandbox-...2b3f (kept server-side)
[17:32:35] SUCCESS - retrieved sandbox target data array:
[17:32:35] [
  {
    "account_id": "acc_sandbox_001",
    "available_balance": 100.0,
    "current_balance": 110.0,
    "currency_code": "USD"
  }
]
```

Target data array:

| available_balance | current_balance | currency code |
|---|---|---|
| 100.0 | 110.0 | USD |

## 3. Security Assessment Statement

The access_token is created and stored only inside the backend process: the
browser sees the link_token and a short-lived, single-use public_token, and the
exchange for the access_token happens server to server over the back channel,
authenticated with the client secret. The token is never sent to the client,
and appears masked in logs, so a compromised or inspected browser cannot read
it. A stolen public_token is also useless, since it expires after 30 seconds
and works once.
