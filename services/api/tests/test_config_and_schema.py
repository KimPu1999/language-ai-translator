from pathlib import Path

import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_database_url_must_be_postgresql():
    with pytest.raises(ValidationError):
        Settings(database_url="sqlite+aiosqlite:///./not-allowed.db")


def test_default_database_url_contains_no_credentials():
    assert "@" not in Settings().database_url


def test_azure_endpoint_is_restricted_to_https_azure_hosts():
    with pytest.raises(ValidationError):
        Settings(azure_translator_endpoint="http://example.com")
    with pytest.raises(ValidationError):
        Settings(azure_translator_endpoint="https://example.com")


def test_azure_timeout_is_bounded():
    with pytest.raises(ValidationError):
        Settings(azure_translator_timeout_seconds=61)


def test_migration_contains_all_tables_and_idempotent_seed():
    migration = Path(__file__).parents[1] / "alembic/versions/0001_phase1a.py"
    content = migration.read_text()
    for table in ("users", "languages", "translations", "favorites"):
        assert f'"{table}"' in content
    assert "ON CONFLICT (code) DO NOTHING" in content
    for code in ("en", "my", "th", "zh-Hans", "ja", "ko"):
        assert f'("{code}"' in content or f'("{code}",' in content
