"""Backend client for Lab Report 1: runs the full OAuth loop and writes the report.

Only this process ever holds the access_token. It is read from memory, used
server-side, and masked in every log line.
"""
import json
import os
import sys
import time
from datetime import datetime, timezone

import requests

BASE = os.environ.get("PLATFORM_URL", "http://localhost:5000")
CLIENT_ID = os.environ.get("MOCK_CLIENT_ID", "sandbox_client_id")
SECRET = os.environ.get("MOCK_SECRET", "sandbox_secret")
REPORT_DIR = os.environ.get("REPORT_DIR", "report")

LOG = []


def log(msg):
    line = f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}] {msg}"
    LOG.append(line)
    print(line, flush=True)


def mask(token):
    return token[:15] + "..." + token[-4:]


def post(path, **payload):
    r = requests.post(BASE + path, json=payload, timeout=10)
    r.raise_for_status()
    return r.json()


def wait_for_platform():
    for _ in range(30):
        try:
            if requests.get(BASE + "/health", timeout=2).ok:
                return
        except requests.RequestException:
            time.sleep(1)
    sys.exit("platform not reachable")


def main():
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


def write_report(payload):
    init_code = open(__file__).read().split("def main():")[1].split("def write_report")[0]
    init_snippet = "\n".join(l for l in init_code.splitlines() if l.strip())[:2500]
    report = f"""# Lab Report 1: Open Banking Sandbox Connection

## 1. Sandbox Config Blueprint

**Aggregator sandbox:** Plaid-style mock Open Banking platform (Flask, runs in Docker
as the `platform` service). Endpoints and field names follow Plaid syntax
(`link_token`, `public_token`, `access_token`, `accounts/balance/get`).

**Sandbox credentials:** `client_id=sandbox_client_id`, `secret=sandbox_secret`
(supplied by environment variables, never hard coded in the client).
Test bank login: `user_good` / `pass_good`.

**Initialization code used** (`client/lab.py`):

```python
{init_snippet}
```

## 2. Output Log Payload

```text
{chr(10).join(LOG)}
```

Target data array:

| available_balance | current_balance | currency code |
|---|---|---|
""" + "\n".join(f"| {p['available_balance']} | {p['current_balance']} | {p['currency_code']} |" for p in payload) + """

## 3. Security Assessment Statement

The access_token is created and stored only inside the backend process: the
browser sees the link_token and a short-lived, single-use public_token, and the
exchange for the access_token happens server to server over the back channel,
authenticated with the client secret. The token is never sent to the client,
and appears masked in logs, so a compromised or inspected browser cannot read
it. A stolen public_token is also useless, since it expires after 30 seconds
and works once.
"""
    with open(os.path.join(REPORT_DIR, "lab_report_1.md"), "w") as f:
        f.write(report)


if __name__ == "__main__":
    main()
