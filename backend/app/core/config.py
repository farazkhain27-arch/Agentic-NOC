from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    APP_NAME: str = "NOC Agentic AI"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    API_SECRET_KEY: str = "dev-secret-key-change-in-production"
    BACKEND_CORS_ORIGINS: str = "http://localhost:3000"

    ANTHROPIC_API_KEY: str = ""
    CLAUDE_MODEL: str = "claude-sonnet-4-6"

    LANGCHAIN_TRACING_V2: bool = True
    LANGCHAIN_API_KEY: str = ""
    LANGCHAIN_PROJECT: str = "noc-agentic-ai"

    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "noc_db"
    POSTGRES_USER: str = "noc_user"
    POSTGRES_PASSWORD: str = "changeme"

    REDIS_URL: str = "redis://localhost:6379"

    JIRA_BASE_URL: str = ""
    JIRA_EMAIL: str = ""
    JIRA_API_TOKEN: str = ""
    JIRA_PROJECT_KEY: str = "NOC"

    SENDGRID_API_KEY: str = ""
    EMAIL_FROM: str = "noc-alerts@company.com"
    EMAIL_MANAGEMENT: str = "management@company.com"

    NMS_SIMULATE: bool = True
    NMS_ALARM_INTERVAL_SECONDS: int = 30

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def CORS_ORIGINS(self) -> List[str]:
        return [o.strip() for o in self.BACKEND_CORS_ORIGINS.split(",")]

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
