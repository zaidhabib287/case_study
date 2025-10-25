FROM python:3.11-slim
WORKDIR /app
RUN pip install --no-cache-dir \
    fastapi uvicorn[standard] pydantic[email] pydantic-settings python-multipart \
    pillow pdfplumber pandas openpyxl scikit-learn joblib \
    streamlit requests python-dotenv \
    sqlalchemy alembic psycopg[binary] \
    langgraph langchain-core httpx

COPY . /app
