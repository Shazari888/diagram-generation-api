from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "Diagram Generation API"
    api_key: str

    database_url: str

    redis_url: str = "redis://localhost:6379"
    cache_ttl_seconds: int = 3600

    openai_api_key: str
    openai_model: str = "gpt-3.5-turbo"

    kroki_base_url: str = "https://kroki.io"
    mermaid_ink_base_url: str = "https://mermaid.ink"

    x402_enabled: bool = False
    x402_facilitator_url: str = "https://x402.org/facilitator"
    x402_network: str = "eip155:84532"
    x402_pay_to: str | None = None
    x402_price: str = "$0.01"
    x402_builder_code: str | None = None


settings = Settings()
