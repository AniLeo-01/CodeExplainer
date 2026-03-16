# indexer-agent/app/config.py
import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve .env path relative to this file's location (indexer-agent/.env)
ENV_FILE = Path(__file__).resolve().parent.parent / ".env"

# Detect Docker environment - check if neo4j hostname resolves or use env hint
def _get_neo4j_default():
    """Get appropriate Neo4j URI based on environment."""
    # Check if we're in Docker by looking for /.dockerenv or checking hostname
    if os.path.exists("/.dockerenv") or os.environ.get("DOCKER_ENV"):
        return "bolt://neo4j:7687"
    return "bolt://localhost:7687"


class Settings(BaseSettings):
    REPO_URL: str = ""
    REPO_DIR: str = "/tmp/repo-cache"
    NEO4J_URI: str = _get_neo4j_default()
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "password"

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
