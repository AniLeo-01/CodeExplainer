import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve .env path relative to this file's location (code-analyst-agent/.env)
ENV_FILE = Path(__file__).resolve().parent.parent / ".env"

# In Docker, use shared.env mounted at /app/shared.env
DOCKER_ENV_FILE = Path("/app/shared.env")
if DOCKER_ENV_FILE.exists():
    ENV_FILE = DOCKER_ENV_FILE

# Detect Docker environment
def _get_neo4j_default():
    if os.path.exists("/.dockerenv") or os.environ.get("DOCKER_ENV"):
        return "bolt://neo4j:7687"
    return "bolt://localhost:7687"


class Settings(BaseSettings):
    REPO_ROOT: str = "/tmp/repo-cache"  # where indexer clones repositories
    OPENAI_API_KEY: str | None = None
    LLM_MODEL_ID: str = "gpt-4o-mini"
    NEO4J_URI: str = _get_neo4j_default()
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "password"

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
