import pytest

from app.core.config import Settings, get_settings


def test_settings_loads_from_env(monkeypatch, tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "DATABASE_URL=postgresql+psycopg://test:test@localhost:5432/test\n"
        "ENVIRONMENT=test\n"
    )

    class TestSettings(Settings):
        model_config = Settings.model_config | {"env_file": str(env_file)}

    s = TestSettings()
    assert s.environment == "test"
    assert s.is_test is True
    assert s.is_production is False


def test_settings_requires_database_url(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setattr("app.core.config.Path", lambda *_: type("P", (), {"resolve": lambda self: self, "parents": [None, None, type("F", (), {"__truediv__": lambda *_: "/nonexistent"})()]})())
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_settings_cached():
    s1 = get_settings()
    s2 = get_settings()
    assert s1 is s2

def test_data_cache_dir_resolves_to_absolute():
    from app.core.config import Settings, get_settings
    get_settings.cache_clear()
    s = get_settings()
    assert s.data_cache_dir.is_absolute()
    assert s.data_cache_dir.name == "data"