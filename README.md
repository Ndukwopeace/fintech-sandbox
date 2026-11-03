# fintech-sandbox

Lab Report 1 (course slides 17-18): connect to an Open Banking sandbox, run the
OAuth loop, retrieve account balances, and produce the report.

## Run with Docker

```bash
docker compose up --build --abort-on-container-exit
```

The `client` service runs the five-step loop, prints the log, and writes
`report/lab_report_1.md`. The mock platform stays reachable on
http://localhost:5000 while it runs.

To try the hosted auth screen by hand:

```bash
docker compose up --build platform
```

Then POST `/link/token/create` with `{"client_id":"sandbox_client_id","secret":"sandbox_secret"}`
and open `/link/<link_token>` in a browser (login `user_good` / `pass_good`).

## Run without Docker

```bash
pip install -r mock_platform/requirements.txt -r client/requirements.txt
python mock_platform/app.py &
python client/lab.py
```

## Layout

- `mock_platform/` Flask mock of a Plaid-style platform
- `client/lab.py` backend that performs the OAuth exchange and writes the report
- `report/` generated report (submit `lab_report_1.md`, or export it to PDF)
