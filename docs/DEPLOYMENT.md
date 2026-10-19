# Local setup and deployment

## Local run

```sh
cd Multi-Agent-Enterprise-Market-Lead-Intelligence-Engine
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000` or `/docs`. SQLite data is stored at `data/leads.sqlite3` by default; set `LEAD_DB_PATH` to change it.

## Current implementation scope

This MVP validates operator-provided candidate records, deduplicates by domain, applies deterministic ICP rules, persists results, and exposes job lookup. It does not crawl websites, discover contacts, call LLMs, or enrich records through a third-party provider. Add separately reviewed, permissioned adapters before introducing those capabilities. The app has no authentication and is intended for local development only; do not expose it to an untrusted network.

## Example API call

```sh
curl -sS http://127.0.0.1:8000/research \
  -H 'content-type: application/json' \
  -d '{"icp":{"industries":["Manufacturing"],"regions":["US"],"min_employees":100,"required_signals":["hiring"]},"candidates":[{"company":"Example Manufacturing","domain":"example.com","industry":"Manufacturing","region":"US","employees":250,"signals":["hiring"],"source":"operator-provided"}]}'
```
