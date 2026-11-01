from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    app_name: str = "Aegis"
    app_env: str = "development"
    log_level: str = "INFO"
    database_url: str = "sqlite:///./aegis.db"
    aegis_api_key: str = ""
    cors_origins: str = "http://localhost:3000,http://localhost:5173"
    max_request_bytes: int = 20_000_000
    upload_dir: str = "./data/uploads"
    max_upload_bytes: int = 15_000_000
    max_csv_rows: int = 100_000
    llm_base_url: str = "http://localhost:11434/v1"
    llm_api_key: str = ""
    llm_model: str = ""
    llm_timeout_seconds: float = 60
    embedding_url: str = "http://localhost:11434/api/embeddings"
    embedding_model: str = "nomic-embed-text"
    retrieval_top_k: int = 6

    @property
    def allowed_origins(self) -> list[str]:
        return [x.strip() for x in self.cors_origins.split(",") if x.strip()]

    @property
    def uploads_path(self) -> Path:
        return Path(self.upload_dir).resolve()

@lru_cache
def get_settings() -> Settings:
    return Settings()
settings = get_settings()
