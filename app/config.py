from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "Diagram Generation API"
    api_key: str

    database_url: str

    redis_url: str = "redis://localhost:6379"
    cache_ttl_seconds: int = 3600

    openai_api_key: str
    openai_model: str = "gpt-4"

    kroki_base_url: str = "https://kroki.io"


settings = Settings()
