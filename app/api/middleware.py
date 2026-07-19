"""Middleware de segurança: headers de defesa em profundidade e rate
limiting simples por IP, usando o Redis que já existe para o Celery.

Combinados numa única classe para garantir que o rate limit também
devolva os headers de segurança na resposta 429 (a ordem de execução de
múltiplos `BaseHTTPMiddleware` no Starlette não é óbvia o suficiente para
depender dela aqui).
"""

import time

import redis.asyncio as redis
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.config import get_settings

settings = get_settings()

# Caminhos que ficam de fora do rate limit (monitoramento de infraestrutura,
# ex.: healthcheck do Docker, não deve contar como tráfego de cliente)
_EXEMPT_PATHS = {"/health"}


class SecurityMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, limit_per_minute: int) -> None:
        super().__init__(app)
        self._limit = limit_per_minute
        self._redis = redis.from_url(settings.redis_url)

    async def dispatch(self, request: Request, call_next):
        if request.url.path not in _EXEMPT_PATHS:
            blocked = await self._check_rate_limit(request)
            if blocked is not None:
                return self._add_security_headers(blocked)

        response: Response = await call_next(request)
        return self._add_security_headers(response)

    async def _check_rate_limit(self, request: Request) -> Response | None:
        client_ip = request.client.host if request.client else "unknown"
        window = int(time.time() // 60)
        key = f"ratelimit:{client_ip}:{window}"

        try:
            count = await self._redis.incr(key)
            if count == 1:
                await self._redis.expire(key, 60)
        except Exception:  # noqa: BLE001
            # Redis indisponível não deve derrubar a API inteira — deixa passar
            # sem limitar, o que é aceitável para uma rede já restrita.
            return None

        if count > self._limit:
            return JSONResponse(
                status_code=429,
                content={"detail": "Muitas requisições — tente novamente em instantes."},
                headers={"Retry-After": "60"},
            )
        return None

    @staticmethod
    def _add_security_headers(response: Response) -> Response:
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' https://unpkg.com; "
            "style-src 'self' 'unsafe-inline'; "
            "frame-ancestors 'none'"
        )
        return response
