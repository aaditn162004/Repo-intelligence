import os
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Application
    APP_NAME: str = "Repository Intelligence Platform"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"

    # API
    API_V1_PREFIX: str = "/api/v1"
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:3001"]

    # Qdrant — set QDRANT_URL + QDRANT_API_KEY for cloud, leave blank for local
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_URL: str = ""
    QDRANT_API_KEY: str = ""
    QDRANT_COLLECTION_PREFIX: str = "repo_intel"

    # Redis
    REDIS_URL: str = "redis://localhost:6379"
    REDIS_TTL: int = 3600

    # LLM provider — "ollama" for local dev, "groq" for cloud
    LLM_PROVIDER: str = "ollama"

    # Ollama (local)
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    LLM_MODEL: str = "qwen2.5-coder:7b"

    # Groq (cloud)
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.3-70b-versatile"

    LLM_TEMPERATURE: float = 0.1
    LLM_MAX_TOKENS: int = 4096

    # Embeddings
    EMBEDDING_MODEL: str = "BAAI/bge-small-en-v1.5"
    EMBEDDING_DIMENSION: int = 384
    EMBEDDING_BATCH_SIZE: int = 64

    # Repository storage
    REPOS_BASE_DIR: str = "/tmp/repos"
    MAX_REPO_SIZE_MB: int = 500
    MAX_FILE_SIZE_KB: int = 512

    # Indexing
    CHUNK_SIZE: int = 512
    CHUNK_OVERLAP: int = 64
    MAX_WORKERS: int = 4

    # Retrieval
    TOP_K_RESULTS: int = 10
    SIMILARITY_THRESHOLD: float = 0.65

    # GitHub
    GITHUB_TOKEN: str = ""

    @property
    def repos_dir(self) -> str:
        os.makedirs(self.REPOS_BASE_DIR, exist_ok=True)
        return self.REPOS_BASE_DIR


settings = Settings()
