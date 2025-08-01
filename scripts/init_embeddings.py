#!/usr/bin/env python
"""Initialize embedding models for Textual MCP Server.

This script downloads and converts embedding models to model2vec format
for use with the Chonkie document processor.
"""

import sys
from pathlib import Path
from typing import Optional
import logging

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from model2vec import StaticModel
from sentence_transformers import SentenceTransformer


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def ensure_model_dir() -> Path:
    """Ensure the models directory exists."""
    models_dir = Path(__file__).parent.parent / "models"
    models_dir.mkdir(exist_ok=True)
    return models_dir


def download_and_convert_model(
    model_name: str, output_name: Optional[str] = None, models_dir: Optional[Path] = None
) -> Path:
    """Download a model from Hugging Face and convert it to model2vec format.

    Args:
        model_name: Hugging Face model identifier (e.g., 'sentence-transformers/all-MiniLM-L6-v2')
        output_name: Name for the converted model (defaults to last part of model_name)
        models_dir: Directory to save models (defaults to ./models)

    Returns:
        Path to the converted model
    """
    if models_dir is None:
        models_dir = ensure_model_dir()

    if output_name is None:
        output_name = model_name.split("/")[-1]

    output_path = models_dir / output_name

    # Check if already converted
    if output_path.exists():
        logger.info(f"Model already exists at {output_path}")
        return output_path

    logger.info(f"Downloading model: {model_name}")

    try:
        # Method 1: Try direct model2vec conversion if supported
        logger.info("Attempting direct model2vec conversion...")
        model = StaticModel.from_pretrained(model_name)
        model.save_pretrained(str(output_path))
        logger.info(f"Successfully converted {model_name} to model2vec format")
        return output_path
    except Exception as e:
        logger.warning(f"Direct model2vec conversion failed: {e}")

        # Method 2: Convert via sentence-transformers
        try:
            logger.info("Attempting conversion via sentence-transformers...")

            # Download sentence transformer model
            SentenceTransformer(model_name)

            # Convert to model2vec
            # This creates a static version of the model
            model = StaticModel.from_distiller(
                base_model=model_name,
                pca_dims=256,  # Dimensionality reduction for efficiency
                apply_zipf=True,  # Apply Zipf's law for better performance
                apply_norm=True,  # Normalize embeddings
            )

            # Save the converted model
            model.save_pretrained(str(output_path))
            logger.info(
                f"Successfully converted {model_name} to model2vec format via sentence-transformers"
            )
            return output_path

        except Exception as e2:
            logger.error(f"Sentence-transformers conversion also failed: {e2}")
            raise RuntimeError(f"Failed to convert model {model_name}: {e}, {e2}")


def init_default_models():
    """Initialize the default models used by Textual MCP."""
    models_to_init = [
        # Model used by Chonkie semantic chunker
        ("minishlab/potion-base-8M", "potion-base-8M")
    ]

    models_dir = ensure_model_dir()
    converted_models = []

    for model_name, output_name in models_to_init:
        try:
            logger.info(f"\nProcessing {model_name}...")
            model_path = download_and_convert_model(model_name, output_name, models_dir)
            converted_models.append((model_name, model_path))
            logger.info(f"✓ {model_name} ready at {model_path}")
        except Exception as e:
            logger.error(f"✗ Failed to initialize {model_name}: {e}")

    # Create a simple model registry file
    registry_path = models_dir / "model_registry.txt"
    with open(registry_path, "w") as f:
        f.write("# Model Registry for Textual MCP\n")
        f.write("# Format: original_name -> local_path\n\n")
        for original, local in converted_models:
            f.write(f"{original} -> {local}\n")

    logger.info(f"\nModel registry written to {registry_path}")
    logger.info(f"Successfully initialized {len(converted_models)} models")

    # Test loading a model
    if converted_models:
        test_model_path = converted_models[0][1]
        logger.info(f"\nTesting model loading from {test_model_path}...")
        try:
            StaticModel.from_pretrained(str(test_model_path))
            logger.info("✓ Model loading test successful")
        except Exception as e:
            logger.error(f"✗ Model loading test failed: {e}")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Initialize embedding models for Textual MCP")
    parser.add_argument(
        "--model",
        help="Specific model to download and convert (e.g., 'sentence-transformers/all-MiniLM-L6-v2')",
    )
    parser.add_argument("--output", help="Output name for the converted model")
    parser.add_argument(
        "--models-dir", type=Path, help="Directory to store models (default: ./models)"
    )

    args = parser.parse_args()

    if args.model:
        # Convert specific model
        models_dir = args.models_dir or ensure_model_dir()
        try:
            model_path = download_and_convert_model(args.model, args.output, models_dir)
            logger.info(f"Model ready at: {model_path}")
        except Exception as e:
            logger.error(f"Failed to convert model: {e}")
            sys.exit(1)
    else:
        # Initialize default models
        init_default_models()


if __name__ == "__main__":
    main()
