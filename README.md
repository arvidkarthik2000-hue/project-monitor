# Project Monitor

Live status dashboard for all active projects. Read by AI agents via `raw.githubusercontent.com`.

## Quick Links

- **Master status:** [`status.json`](status.json)
- **Per-project:** [`projects/`](projects/)
- **Daily logs:** [`logs/`](logs/)

## Projects

| Code | Project | Status |
|------|---------|--------|
| CINE | CineVerse | Indian movie quiz app |
| NEET-UG | NEET UG Prep | Medical entrance exam prep (UG) |
| NEET-PG | NEET PG Prep | Medical entrance exam prep (PG) |
| CHOTU | Chotu AI | AI education for kids |
| QCLAW | QuantClaw/Voltzz | AI trading agent |
| STYLE | StyleGenie | AI fashion advisor |
| UPSC | UPSC Sentinel | Civil services exam predictor |
| PHOTO | PhotoBooth AI | PVR Scene Stealer face swap |

## How It Works

1. **Alfred** (AI agent) runs `push_status.py` after every work session
2. Script queries live Supabase databases for real numbers
3. Updates `status.json` + per-project files + daily log
4. Commits and pushes to GitHub
5. **Claude** reads `status.json` via raw.githubusercontent.com for project context

## Setup

```bash
cp .env.example .env
# Fill in Supabase keys
python push_status.py
```

## Architecture

```
status.json          <- Claude reads this (single fetch = full picture)
projects/{CODE}.json <- Detailed per-project state
logs/YYYY-MM-DD.jsonl <- Append-only audit trail
push_status.py       <- Queries live DBs, writes files, git push
```

## Rules

1. Never edit `status.json` manually — always use `push_status.py`
2. If a DB query fails, the error is logged (no stale numbers)
3. Thread status must reflect reality: "unknown" if unchecked
4. Blockers and next_actions updated every push
