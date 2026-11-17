from app.core.config import Settings


def test_settings_ignore_database_container_variables():
    settings = Settings(
        _env_file=None,
        DATABASE_URL="postgresql+asyncpg://user:pass@group_db:5432/groups",
        JWT_SECRET="test-secret",
        AUTH_SERVICE_API_KEY="test-internal-key",
        POSTGRES_DB="groups",
        POSTGRES_USER="user",
        POSTGRES_PASSWORD="pass",
    )

    assert settings.DATABASE_URL.endswith("@group_db:5432/groups")
    assert settings.AUTH_SERVICE_API_KEY == "test-internal-key"
