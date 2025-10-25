from fastapi import Header, HTTPException, status
import os

API_KEY = os.getenv("API_KEY", "dev-key-change-me")

async def require_api_key(x_api_key: str | None = Header(None)):
    if not x_api_key or x_api_key != API_KEY:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or missing API key")
