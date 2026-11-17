from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str
    JWT_SECRET: str
    JWT_ALG: str = "HS256"
    AUTH_SERVICE_URL: str = "http://auth_service:8000"
    AUTH_SERVICE_API_KEY: str
    INVITATION_BASE_URL: str = "http://localhost:8002"

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
