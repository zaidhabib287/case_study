# Social Support Application – AI Workflow (Prototype)

FastAPI + PostgreSQL backend, Streamlit UI, and a local LLM via **Ollama**.  
Automates intake, validation, eligibility scoring, and decision explanation with an agentic chat.

## ✨ Features
- **API**: Create application, upload docs (PDF/any), run decision pipeline, chat with underwriting agent  
- **DB**: PostgreSQL (applications, documents, decisions)  
- **ML**: Baseline scorer (sklearn placeholder) + validations  
- **Agents**: Deterministic ReAct-style tools; optional LangGraph orchestration  
- **LLM**: Local via **Ollama** (`llama3.2:3b`)  
- **UI**: Streamlit (Create → Upload → Run → Chat)  
- **Auth**: Simple API key (header: `X-API-Key`)

---

## 🔧 Stack
- Python 3.11, FastAPI, SQLAlchemy, Alembic  
- PostgreSQL 16  
- Streamlit  
- Ollama (local LLM)  
- (Optional) LangGraph for orchestration

---

## 📁 Repository Layout
```
.
├─ backend/
│  ├─ app/
│  │  ├─ main.py           # FastAPI endpoints (/health, /applications, /upload, /run, /chat)
│  │  ├─ schemas.py        # Pydantic models
│  │  ├─ models.py         # SQLAlchemy models
│  │  ├─ db.py             # Session + engine
│  │  ├─ security.py       # API key dependency
│  │  ├─ middleware.py     # Request ID middleware
│  │  └─ logging_setup.py  # Request-aware logging
│  └─ services/
│     ├─ parsing.py        # PDF text extraction via pdfplumber
│     ├─ validation.py     # Business validations
│     ├─ ml.py             # Baseline scorer (placeholder)
│     ├─ recommendations.py# Next-step recommendations
│     ├─ agent.py          # Tool functions (docs summary, decision explain)
│     ├─ agent_react.py    # Deterministic ReAct-style output combiner
│     └─ orchestrator.py   # (Optional) LangGraph classify→act graph
├─ alembic/                # DB migrations
├─ frontend/
│  └─ app.py               # Streamlit UI (Create / Upload / Run / Chat)
├─ docs/
│  └─ architecture.md
├─ docker-compose.yml
├─ Dockerfile
└─ README.md
```

---

## 🚀 Quick Start

> If you’re on a remote server, open a local tunnel first (adjust host/port):
>
> ```bash
> ssh -L 18000:localhost:8000 -L 18501:localhost:8501 -L 11434:localhost:11434 -p <PORT> <USER>@<HOST>
> ```
>
> Then browse: **http://localhost:18501** (UI) and hit API via **http://localhost:18000**.

### 1) Build & start
```bash
docker compose up -d --build
```

### 2) Pull the local LLM (first time)
```bash
docker compose exec ollama ollama pull llama3.2:3b
```

### 3) Run DB migrations
```bash
docker compose exec api bash -lc 'alembic upgrade head'
```

### 4) Health checks
```bash
curl -s http://localhost:8000/health
curl -s http://localhost:11434/api/tags | jq .
```

---

## 🔑 Auth

All write endpoints require a simple API key header:
```
X-API-Key: letmein123
```
(Configure via `backend/app/security.py` or env `API_KEY`.)

---

## 🧪 Example Flow (cURL)

### Create an application
```bash
cat >/tmp/app.json <<'JSON'
{
  "application_id": "APP-DEMO-1",
  "full_name": "Demo User",
  "age": 30,
  "address": "DXB",
  "employment_status": "employed",
  "net_monthly_income": 5000
}
JSON

curl -s -X POST http://localhost:8000/applications   -H 'X-API-Key: letmein123' -H 'Content-Type: application/json'   --data @/tmp/app.json
```

### Upload a document (PDF shown; any file type allowed)
```bash
curl -s -X POST http://localhost:8000/applications/APP-DEMO-1/upload   -H 'X-API-Key: letmein123'   -F "files=@/tmp/sample.pdf;type=application/pdf"
```

### Run decision pipeline
```bash
curl -s -X POST http://localhost:8000/applications/APP-DEMO-1/run   -H 'X-API-Key: letmein123' | jq .
```

### Chat with underwriting agent
```bash
curl -s -X POST http://localhost:8000/chat   -H 'X-API-Key: letmein123' -H 'Content-Type: application/json'   -d '{"application_id":"APP-DEMO-1","messages":[{"role":"user","content":"summarize my documents and explain latest decision"}],"use_llm": true}'   | jq .
```

---

## 🖥️ UI
- Streamlit: **http://localhost:8501** (or **http://localhost:18501** via tunnel)  
- Tabs: **Create → Upload → Run → Chat**  
- The Chat tab uses `st.rerun()` (falls back to `experimental_rerun` when needed).

---

## ⚙️ Configuration (env)

Set via `docker-compose.yml` or container env:

```
API_KEY=letmein123         # required for writes
DATABASE_URL=postgresql+psycopg://app:app@db:5432/casestudy
USE_OLLAMA=1               # enable LLM path
OLLAMA_URL=http://ollama:11434
OLLAMA_MODEL=llama3.2:3b
```

---

## 🧩 Design Notes

- **Validations-first**: hard checks (age, income, docs presence) gate the ML scorer.  
- **Baseline ML**: sklearn placeholder returns a probability; label → Approve/Review.  
- **Agents**:
  - Deterministic ReAct-style parser extracts tool calls from LLM output (or routes intent directly) and renders clean markdown (no raw JSON).
  - Tools implemented: **Documents Summary**, **Decision Explanation**. Easily extend with **Policy Validation**, **ML Score**, **Recommendations**.
- **Ollama**: fully local LLM; model is configurable.  
- **LangGraph**: minimal classify→act graph provided; you can expand nodes for extraction, validation, eligibility, recommendation.

---

## 🛠️ Troubleshooting

- **API not responding**: `docker compose ps` → ensure `api` shows *Up*.  
- **Migrations missing**: `docker compose exec api bash -lc 'alembic upgrade head'`.  
- **Ollama model missing**: `docker compose exec ollama ollama pull llama3.2:3b`.  
- **Chat tab error about rerun**: we use `st.rerun()` with fallback.  
- **Uploads parse empty**: `pdfplumber` extracts text; scanned images need OCR (future work).

---

## 🧭 Roadmap / Future Work

- OCR for scanned PDFs (Tesseract or PaddleOCR)  
- Vector store for semantic search over docs  
- Richer sklearn pipeline + model selection & validation  
- Policy rules engine + explainability  
- Agent observability with Langfuse

---

## 📜 License

For assessment/demonstration only.
