import httpx

from app.config import settings


def make_client() -> httpx.AsyncClient:
    cfg = settings()
    return httpx.AsyncClient(
        timeout=httpx.Timeout(cfg.request_timeout_s),
        headers={"User-Agent": cfg.user_agent, "Accept": "application/json"},
        follow_redirects=True,
    )
