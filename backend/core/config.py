"""
Configuration management for Doclingflow.

Loads settings from YAML file and environment variables.
Environment variables override YAML settings.
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def load_yaml_config(config_path: str = "/app/config/settings.yaml") -> Dict[str, Any]:
    """Load configuration from YAML file."""
    config_file = Path(config_path)

    if not config_file.exists():
        # Fallback to local config for development
        config_file = Path("config/settings.yaml")

    if not config_file.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with open(config_file, "r") as f:
        config = yaml.safe_load(f)

    # Replace environment variable placeholders
    return _resolve_env_vars(config)


def _resolve_env_vars(config: Any) -> Any:
    """Recursively resolve environment variable placeholders in config."""
    if isinstance(config, dict):
        return {key: _resolve_env_vars(value) for key, value in config.items()}
    elif isinstance(config, list):
        return [_resolve_env_vars(item) for item in config]
    elif isinstance(config, str) and config.startswith("${") and config.endswith("}"):
        # Extract env var name and resolve it
        env_var = config[2:-1]
        return os.getenv(env_var, config)
    return config


class AppSettings(BaseSettings):
    """Application settings."""
    name: str = "Doclingflow"
    version: str = "0.1.0"
    debug: bool = True


class ProcessingSettings(BaseSettings):
    """Document processing settings."""
    watch_folders: List[str] = ["/data/inbox"]
    chunk_size: int = 1000
    chunk_overlap: int = 200
    max_concurrent_jobs: int = 2
    auto_process: bool = True
    supported_formats: List[str] = ["pdf", "docx", "xlsx", "pptx", "txt", "html"]


class ClassificationCategory(BaseSettings):
    """Document classification category."""
    name: str
    keywords: List[str] = []


class ClassificationSettings(BaseSettings):
    """Classification settings."""
    categories: List[Dict[str, Any]] = []

    def get_categories(self) -> List[ClassificationCategory]:
        """Get parsed classification categories."""
        return [
            ClassificationCategory(**cat) for cat in self.categories
        ]


class LLMSettings(BaseSettings):
    """LLM configuration."""
    provider: str = "openrouter"
    model: str = "anthropic/claude-3.5-sonnet"
    temperature: float = 0.1
    max_tokens: int = 2000

    # OpenRouter settings
    openrouter_api_key: Optional[str] = None
    openrouter_base_url: str = "https://openrouter.ai/api/v1"

    # Ollama settings (fallback)
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama2"


class EmbeddingSettings(BaseSettings):
    """Embedding configuration."""
    provider: str = "openrouter"
    model: str = "openai/text-embedding-3-small"
    dimensions: int = 1536


class QdrantSettings(BaseSettings):
    """Qdrant vector database settings."""
    host: str = "qdrant"
    port: int = 6333
    collection_name: str = "documents"
    distance_metric: str = "Cosine"


class EntityExtractionSettings(BaseSettings):
    """Entity extraction settings."""
    enabled: bool = True
    extract: List[str] = [
        "equipment_ids",
        "chemical_names",
        "dates",
        "locations",
        "personnel",
        "measurements"
    ]


class StorageSettings(BaseSettings):
    """Storage paths configuration."""
    inbox_path: str = "/data/inbox"
    processed_path: str = "/data/processed"
    failed_path: str = "/data/failed"
    archive_path: str = "/data/archive"
    archive_after_days: int = 30
    delete_after_days: int = 90


class DatabaseSettings(BaseSettings):
    """Database configuration."""
    model_config = SettingsConfigDict(env_prefix="")

    database_url: str = Field(
        default="postgresql://doclingflow:doclingflow_password@postgres:5432/doclingflow",
        alias="DATABASE_URL"
    )


class RedisSettings(BaseSettings):
    """Redis configuration."""
    model_config = SettingsConfigDict(env_prefix="")

    redis_url: str = Field(
        default="redis://redis:6379/0",
        alias="REDIS_URL"
    )


class Settings(BaseSettings):
    """Main settings class combining all configuration."""
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="allow"
    )

    # Core settings
    app: AppSettings
    processing: ProcessingSettings
    classification: ClassificationSettings
    llm: LLMSettings
    embeddings: EmbeddingSettings
    qdrant: QdrantSettings
    entity_extraction: EntityExtractionSettings
    storage: StorageSettings
    database: DatabaseSettings
    redis: RedisSettings

    # Environment variables
    debug: bool = Field(default=True, alias="DEBUG")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    @classmethod
    def load_from_yaml(cls, config_path: str = "/app/config/settings.yaml") -> "Settings":
        """Load settings from YAML file and environment variables."""
        yaml_config = load_yaml_config(config_path)

        # Load database and redis from env vars
        database = DatabaseSettings()
        redis = RedisSettings()

        # Create settings from YAML structure
        return cls(
            app=AppSettings(**yaml_config.get("app", {})),
            processing=ProcessingSettings(**yaml_config.get("processing", {})),
            classification=ClassificationSettings(**yaml_config.get("classification", {})),
            llm=LLMSettings(**yaml_config.get("llm", {})),
            embeddings=EmbeddingSettings(**yaml_config.get("embeddings", {})),
            qdrant=QdrantSettings(**yaml_config.get("qdrant", {})),
            entity_extraction=EntityExtractionSettings(**yaml_config.get("entity_extraction", {})),
            storage=StorageSettings(**yaml_config.get("storage", {})),
            database=database,
            redis=redis,
            debug=os.getenv("DEBUG", "true").lower() == "true",
            log_level=os.getenv("LOG_LEVEL", "INFO")
        )


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get global settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings.load_from_yaml()
    return _settings


def reload_settings() -> Settings:
    """Reload settings from file."""
    global _settings
    _settings = Settings.load_from_yaml()
    return _settings
