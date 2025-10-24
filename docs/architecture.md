# Architecture — AI/ML Case Study (Phase 1)

## Overview
- **Frontend**: Streamlit single-page app (`frontend/app.py`).
- **Backend**: FastAPI service (`backend/app/main.py`) exposing:
  - `POST /applications` – create case
  - `POST /applications/{id}/upload` – upload documents
  - `POST /applications/{id}/run` – execute pipeline
  - `GET /health` – liveness check
- **Runtime**: Docker Compose, two services (`api`, `streamlit`).
- **State (Phase 1)**: In-memory (will move to Postgres in Phase 2).

## Flow (high-level)
```mermaid
flowchart LR
UI[Streamlit UI] -->|JSON| API[FastAPI]
API -->|Create| Case[(Application store)]
UI -->|Upload files| API
API -->|Parse/Validate/Score (Phase 3+)| Pipeline
Pipeline --> Decision[(Decision + Rationale)]
Decision --> UI
