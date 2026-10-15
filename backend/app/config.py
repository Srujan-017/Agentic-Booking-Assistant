from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env", env_file_encoding="utf-8", extra="ignore"
    )

    groq_api_key: str = ""
    llm_model: str = "openai/gpt-oss-120b"
    router_model: str = "openai/gpt-oss-20b"
    embedding_model: str = "BAAI/bge-small-en-v1.5"

    chroma_dir: str = "./chroma_db"
    checkpoint_db: str = "./checkpoints.sqlite"
    app_db: str = "./app.sqlite"

    pdf_url: str = (
        "https://raw.githubusercontent.com/Azure-Samples/"
        "azure-search-openai-demo/main/data/employee_handbook.pdf"
    )
    pdf_path: str = "./data/employee_handbook.pdf"

    cors_origins: str = "http://localhost:5173"
    timezone: str = "Asia/Kolkata"

    def resolve(self, relative: str) -> Path:
        """Paths in .env are relative to the backend folder, not the CWD."""
        p = Path(relative)
        return p if p.is_absolute() else (BACKEND_DIR / p).resolve()

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
