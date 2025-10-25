from __future__ import annotations
import logging, uuid, time
from typing import Callable
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

log = logging.getLogger("app")

class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable):
        req_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        start = time.time()
        # attach to scope for downstream usage if needed
        request.state.request_id = req_id
        response = await call_next(request)
        duration_ms = int((time.time() - start) * 1000)
        response.headers["X-Request-ID"] = req_id
        log.info(
            "request",
            extra={
                "event": "http_request",
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "duration_ms": duration_ms,
                "request_id": req_id,
                "client": request.client.host if request.client else None,
            },
        )
        return response
