from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as async_client:
        yield async_client


@pytest.fixture
def db_check(monkeypatch):
    check = AsyncMock()
    monkeypatch.setattr("app.api.v1.endpoints.health.check_db", check)
    return check
