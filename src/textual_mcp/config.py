"""Configuration management for Textual MCP Server."""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field


class ValidatorConfig(BaseModel):
    """Configuration for CSS validators."""

    strict_mode: bool = False
    cache_enabled: bool = True
    max_file_size: int = 1048576  # 1MB
    timeout: int = 30


class EmbeddingConfig(BaseModel):
    """Configuration for embedding generation."""

    model: str = "all-MiniLM-L6-v2"
    dimension: int = 384
    batch_size: int = 32


class IndexingConfig(BaseModel):
    """Configuration for document indexing."""

    chunk_size: int = 512
    chunk_overlap: int = 50
    doc_types: List[str] = Field(
        default_factory=lambda: ["api", "guide", "example", "css_reference"]
    )


class SearchConfig(BaseModel):
    """Configuration for documentation search functionality."""

    auto_index: bool = True
    embeddings_model: str = "BAAI/bge-base-en-v1.5"
    persist_path: Optional[str] = "./data/textual_docs.db"
    chunk_size: int = 200
    chunk_overlap: int = 20
    github_token: Optional[str] = None
    default_limit: int = 10
    similarity_threshold: float = 0.7


class PerformanceConfig(BaseModel):
    """Configuration for performance settings."""

    cache_size: int = 100
    timeout: int = 30
    max_concurrent_requests: int = 10


class LoggingConfig(BaseModel):
    """Configuration for logging."""

    level: str = "INFO"
    format: str = "json"
    file: Optional[str] = "textual-mcp.log"


class FeaturesConfig(BaseModel):
    """Configuration for feature flags."""

    experimental: bool = False
    plugins_enabled: bool = True


class TextualMCPConfig(BaseModel):
    """Main configuration class for Textual MCP Server."""

    validators: ValidatorConfig = Field(default_factory=ValidatorConfig)
    search: SearchConfig = Field(default_factory=SearchConfig)
    performance: PerformanceConfig = Field(default_factory=PerformanceConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    features: FeaturesConfig = Field(default_factory=FeaturesConfig)


def get_default_config_path() -> Path:
    """Get the default configuration file path."""
    # Check for config in current directory first
    current_dir = Path.cwd()
    config_files = [
        current_dir / "textual-mcp.yaml",
        current_dir / "textual-mcp.yml",
        current_dir / "config" / "textual-mcp.yaml",
    ]

    for config_file in config_files:
        if config_file.exists():
            return config_file

    # Return default path in config directory
    return current_dir / "config" / "textual-mcp.yaml"


def load_config(config_path: Optional[str] = None) -> TextualMCPConfig:
    """Load configuration from file or environment variables."""
    path: Path
    if config_path is None:
        path = get_default_config_path()
    else:
        path = Path(config_path)

    # Start with default configuration
    config_dict = {}

    # Load from file if it exists
    if path.exists():
        try:
            with open(path, "r") as f:
                file_config = yaml.safe_load(f)
                if file_config:
                    config_dict.update(file_config)
        except Exception as e:
            raise ValueError(f"Failed to load config from {path}: {e}")

    # Override with environment variables
    env_overrides = _get_env_overrides()
    _deep_update(config_dict, env_overrides)

    # Create and validate configuration
    try:
        return TextualMCPConfig(**config_dict)
    except Exception as e:
        raise ValueError(f"Invalid configuration: {e}")


def _get_env_overrides() -> Dict[str, Any]:
    """Get configuration overrides from environment variables."""
    overrides: Dict[str, Any] = {}

    # Search configuration
    if os.getenv("TEXTUAL_SEARCH_EMBEDDINGS_MODEL"):
        overrides.setdefault("search", {})["embeddings_model"] = os.getenv(
            "TEXTUAL_SEARCH_EMBEDDINGS_MODEL"
        )

    if os.getenv("TEXTUAL_SEARCH_PERSIST_PATH"):
        overrides.setdefault("search", {})["persist_path"] = os.getenv(
            "TEXTUAL_SEARCH_PERSIST_PATH"
        )

    if os.getenv("GITHUB_TOKEN"):
        overrides.setdefault("search", {})["github_token"] = os.getenv("GITHUB_TOKEN")

    # Search configuration
    if os.getenv("EMBEDDINGS_MODEL"):
        overrides.setdefault("search", {})["embeddings_model"] = os.getenv("EMBEDDINGS_MODEL")

    if os.getenv("EMBEDDINGS_STORE"):
        overrides.setdefault("search", {})["persist_path"] = os.getenv("EMBEDDINGS_STORE")

    # Logging configuration
    if os.getenv("LOG_LEVEL"):
        overrides.setdefault("logging", {})["level"] = os.getenv("LOG_LEVEL")

    if os.getenv("LOG_FILE"):
        overrides.setdefault("logging", {})["file"] = os.getenv("LOG_FILE")

    # Performance configuration
    if os.getenv("CACHE_SIZE"):
        try:
            overrides.setdefault("performance", {})["cache_size"] = int(os.getenv("CACHE_SIZE", ""))
        except ValueError:
            pass

    if os.getenv("MAX_CONCURRENT_REQUESTS"):
        try:
            overrides.setdefault("performance", {})["max_concurrent_requests"] = int(
                os.getenv("MAX_CONCURRENT_REQUESTS", "")
            )
        except ValueError:
            pass

    return overrides


def _deep_update(base_dict: Dict[str, Any], update_dict: Dict[str, Any]) -> None:
    """Deep update a dictionary with another dictionary."""
    for key, value in update_dict.items():
        if key in base_dict and isinstance(base_dict[key], dict) and isinstance(value, dict):
            _deep_update(base_dict[key], value)
        else:
            base_dict[key] = value


def save_config(config: TextualMCPConfig, config_path: Optional[str] = None) -> None:
    """Save configuration to file."""
    path: Path
    if config_path is None:
        path = get_default_config_path()
    else:
        path = Path(config_path)

    # Ensure directory exists
    path.parent.mkdir(parents=True, exist_ok=True)

    # Convert to dictionary and save
    config_dict = config.model_dump()

    with open(path, "w") as f:
        yaml.dump(config_dict, f, default_flow_style=False, indent=2)


# Default configuration instance
DEFAULT_CONFIG = TextualMCPConfig()
