# Case Study – Runbook

## Services & Ports
- API (FastAPI): `:8000` (via SSH tunnel: `http://localhost:18000`)
- UI (Streamlit): `:8501` (via tunnel: `http://localhost:18501`)
- Postgres: `:5432` (internal use)

## Start / Stop
```bash
docker compose up -d
docker compose ps
docker compose down    # stop (keeps data)
docker compose down -v # stop + wipe DB volume
