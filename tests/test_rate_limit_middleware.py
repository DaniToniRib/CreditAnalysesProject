"""Testa a lógica de rate limit sem depender de um event loop real.

`_check_rate_limit` só faz `await` em chamadas fake que resolvem na hora
(sem I/O de verdade), então a corrotina roda até o fim no primeiro
`send(None)` — não precisamos de `asyncio.run`/pytest-asyncio para
exercitar o código de verdade.
"""

from app.api.middleware import SecurityMiddleware


def run_coro(coro):
    try:
        coro.send(None)
    except StopIteration as exc:
        return exc.value
    raise RuntimeError("corrotina não completou de forma síncrona")


class FakeClient:
    def __init__(self, host: str):
        self.host = host


class FakeRequest:
    def __init__(self, ip: str):
        self.client = FakeClient(ip)
        self.url = type("URL", (), {"path": "/customers"})()


class FakeRedis:
    """Substitui o Redis real: mesma interface async mínima usada pelo middleware."""

    def __init__(self):
        self.counts: dict[str, int] = {}

    async def incr(self, key: str) -> int:
        self.counts[key] = self.counts.get(key, 0) + 1
        return self.counts[key]

    async def expire(self, key: str, seconds: int) -> None:
        pass


class BrokenRedis:
    async def incr(self, key: str) -> int:
        raise ConnectionError("redis indisponível")


def _middleware(limit: int) -> SecurityMiddleware:
    mw = SecurityMiddleware.__new__(SecurityMiddleware)
    mw._limit = limit
    mw._redis = FakeRedis()
    return mw


def test_allows_requests_up_to_the_limit():
    mw = _middleware(limit=3)
    request = FakeRequest("1.2.3.4")

    for _ in range(3):
        assert run_coro(mw._check_rate_limit(request)) is None


def test_blocks_requests_over_the_limit_with_429():
    mw = _middleware(limit=2)
    request = FakeRequest("1.2.3.4")

    run_coro(mw._check_rate_limit(request))
    run_coro(mw._check_rate_limit(request))
    blocked = run_coro(mw._check_rate_limit(request))

    assert blocked is not None
    assert blocked.status_code == 429


def test_different_ips_have_independent_counters():
    mw = _middleware(limit=1)

    result_a = run_coro(mw._check_rate_limit(FakeRequest("1.1.1.1")))
    result_b = run_coro(mw._check_rate_limit(FakeRequest("2.2.2.2")))

    assert result_a is None
    assert result_b is None


def test_redis_failure_fails_open_instead_of_blocking_everyone():
    mw = _middleware(limit=1)
    mw._redis = BrokenRedis()

    result = run_coro(mw._check_rate_limit(FakeRequest("1.2.3.4")))
    assert result is None
