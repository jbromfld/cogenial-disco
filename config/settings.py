from pydantic import computed_field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str
    DB_USER: str
    DB_PASSWORD: str

    # Embedding
    EMBEDDING_PROVIDER: str = "local"  # "local" | "openai"
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    EMBEDDING_DIM: int = 384

    # Memory tuning
    MEMORY_SIMILARITY_THRESHOLD: float = 0.80

    # P-Agent
    P_AGENT_PROVIDER: str = "anthropic"
    P_AGENT_MODEL: str = "claude-sonnet-4-6"

    # Q-Agent
    Q_AGENT_PROVIDER: str = "anthropic"
    Q_AGENT_MODEL: str = "claude-haiku-4-5-20251001"

    # LangSmith — tracing activates automatically when LANGCHAIN_TRACING_V2=true
    # is present before any langchain_core import. Set these in .env to enable.
    LANGCHAIN_TRACING_V2: str = "false"
    LANGCHAIN_API_KEY: str = ""
    LANGCHAIN_PROJECT: str = "memora-cicd"

    LOG_LEVEL: str = "INFO"

    @computed_field
    @property
    def database_url(self) -> str:
        return (
            f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    @model_validator(mode="after")
    def validate_embedding_dim(self) -> "Settings":
        if self.EMBEDDING_PROVIDER == "openai" and self.EMBEDDING_DIM not in (1536, 3072):
            raise ValueError(
                f"EMBEDDING_DIM must be 1536 or 3072 when EMBEDDING_PROVIDER=openai, "
                f"got {self.EMBEDDING_DIM}"
            )
        return self
