"""Model manager for handling local embedding models."""

from pathlib import Path
from typing import Dict, Optional
from ..utils.logging_config import get_logger

# Singleton instance
_model_manager = None


class ModelManager:
    """Manages local embedding models to avoid downloading from HuggingFace."""

    def __init__(self) -> None:
        self.logger = get_logger("model_manager")
        self.models_dir = Path.home() / ".cache" / "textual_mcp" / "models"
        self.models_dir.mkdir(parents=True, exist_ok=True)

        # Map of model names to their local paths if available
        self._available_models: Dict[str, Path] = {}
        self._scan_for_models()

    def _scan_for_models(self) -> None:
        """Scan for available local models."""
        # Check common locations for pre-downloaded models
        common_paths = [
            self.models_dir,
            Path.home() / ".cache" / "huggingface" / "hub",
            Path.home() / ".cache" / "sentence_transformers",
        ]

        # Known model identifiers to look for
        model_patterns = [
            "minishlab/potion-base-8M",
            "sentence-transformers/all-MiniLM-L6-v2",
            "sentence-transformers/all-mpnet-base-v2",
            "BAAI/bge-base-en-v1.5",
            "all-MiniLM-L6-v2",
            "all-mpnet-base-v2",
        ]

        for base_path in common_paths:
            if not base_path.exists():
                continue

            for model_pattern in model_patterns:
                # Check various path formats
                possible_paths = [
                    base_path / model_pattern.replace("/", "--"),
                    base_path / model_pattern.replace("/", "_"),
                    base_path / model_pattern.split("/")[-1],
                ]

                for path in possible_paths:
                    if path.exists() and path.is_dir():
                        # Verify it's a valid model directory
                        if (path / "config.json").exists() or (path / "model.safetensors").exists():
                            self._available_models[model_pattern] = path
                            self.logger.info(f"Found local model: {model_pattern} at {path}")
                            break

    def get_model_path(self, model_name: str) -> Optional[Path]:
        """Get the local path for a model if available."""
        return self._available_models.get(model_name)

    def list_available_models(self) -> Dict[str, Path]:
        """List all available local models."""
        return self._available_models.copy()

    def has_model(self, model_name: str) -> bool:
        """Check if a model is available locally."""
        return model_name in self._available_models


def get_model_manager() -> ModelManager:
    """Get or create the singleton model manager instance."""
    global _model_manager
    if _model_manager is None:
        _model_manager = ModelManager()
    return _model_manager
