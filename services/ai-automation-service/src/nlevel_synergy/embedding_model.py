"""
Device Embedding Model

Epic AI-4, Story AI4.1: Device Embedding Generation
OpenVINO-optimized embedding model for device relationship discovery.

Uses: sentence-transformers/all-MiniLM-L6-v2 (INT8 quantized)
Size: ~20MB (INT8) vs ~80MB (FP32)
Speed: ~50ms per batch (32 devices)
"""

import logging
from pathlib import Path

import numpy as np
import torch

logger = logging.getLogger(__name__)


class DeviceEmbeddingModel:
    """
    OpenVINO-optimized embedding model for device descriptions.

    Story AI4.1: Device Embedding Generation
    Context7 Best Practice: OpenVINO INT8 quantization for edge deployment

    Usage:
        >>> model = DeviceEmbeddingModel()
        >>> model.load_model()
        >>> embeddings = model.encode(["motion sensor in kitchen"])
        >>> print(embeddings.shape)
        (1, 384)
    """

    MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
    MODEL_VERSION = "all-MiniLM-L6-v2-int8"
    EMBEDDING_DIM = 384
    MAX_SEQ_LENGTH = 512

    def __init__(
        self,
        model_path: str = "./models/nlevel-synergy/embedding-int8",
        device: str = "CPU",
    ):
        """
        Initialize embedding model.

        Args:
            model_path: Path to quantized OpenVINO model
            device: OpenVINO device (CPU, GPU, etc.)
        """
        self.model_path = Path(model_path)
        self.device = device
        self.model = None
        self.tokenizer = None
        self._model_loaded = False

    def load_model(self):
        """
        Load OpenVINO-optimized model.

        Context7 Best Practice:
        - Use OVModelForFeatureExtraction for sentence transformers
        - INT8 quantization via export=True
        - Supports CPU and GPU devices

        Raises:
            FileNotFoundError: If model not found at model_path
            RuntimeError: If model fails to load
        """
        if self._model_loaded:
            logger.debug("Model already loaded, skipping")
            return

        try:
            logger.info(f"Loading OpenVINO embedding model from {self.model_path}...")

            # Check if model exists
            if not self.model_path.exists():
                msg = (
                    f"Model not found at {self.model_path}. "
                    f"Run: bash scripts/quantize-nlevel-models.sh"
                )
                raise FileNotFoundError(
                    msg,
                )

            # Load OpenVINO model
            from optimum.intel.openvino import OVModelForFeatureExtraction
            from transformers import AutoTokenizer

            self.model = OVModelForFeatureExtraction.from_pretrained(
                str(self.model_path),
                device=self.device,
            )

            # Load tokenizer (from original model)
            self.tokenizer = AutoTokenizer.from_pretrained(self.MODEL_NAME)

            self._model_loaded = True

            logger.info(
                f"✅ Model loaded successfully\n"
                f"   Device: {self.device}\n"
                f"   Embedding dim: {self.EMBEDDING_DIM}\n"
                f"   Max seq length: {self.MAX_SEQ_LENGTH}",
            )

        except Exception as e:
            logger.exception(f"Failed to load OpenVINO model: {e}")
            msg = f"Model loading failed: {e}"
            raise RuntimeError(msg)

    def encode(
        self,
        texts: list[str],
        batch_size: int = 32,
        normalize: bool = True,
        show_progress: bool = False,
        convert_to_numpy: bool = True,
    ) -> np.ndarray:
        """
        Generate embeddings for text descriptions.

        Args:
            texts: List of device descriptors
            batch_size: Batch size for processing (Context7: 32 optimal)
            normalize: Normalize embeddings for dot-product scoring
            show_progress: Show progress bar (requires tqdm)
            convert_to_numpy: Return numpy array (vs torch tensor)

        Returns:
            Numpy array of embeddings (N x 384) or torch tensor

        Context7 Best Practice:
        - Batch processing for efficiency
        - Normalize for dot-product scoring (faster than cosine)
        - Use mean pooling for sentence embeddings

        Example:
            >>> texts = ["motion sensor in kitchen", "light in living room"]
            >>> embeddings = model.encode(texts, normalize=True)
            >>> similarity = np.dot(embeddings[0], embeddings[1])
        """
        if not self._model_loaded:
            msg = "Model not loaded. Call load_model() first."
            raise RuntimeError(msg)

        if not texts:
            return np.array([])

        logger.debug(f"Encoding {len(texts)} texts in batches of {batch_size}")

        all_embeddings = []

        # Batch processing
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i+batch_size]

            # Tokenize batch
            inputs = self.tokenizer(
                batch,
                padding=True,
                truncation=True,
                max_length=self.MAX_SEQ_LENGTH,
                return_tensors="pt",
            )

            # Generate embeddings
            with torch.no_grad():
                outputs = self.model(**inputs)

                # Mean pooling (Context7 best practice for sentence embeddings)
                embeddings = self._mean_pooling(
                    outputs.last_hidden_state,
                    inputs["attention_mask"],
                )

            all_embeddings.append(embeddings)

        # Concatenate batches
        embeddings = torch.cat(all_embeddings, dim=0)

        # Normalize for dot-product scoring (Context7 best practice)
        if normalize:
            from sentence_transformers import util
            embeddings = util.normalize_embeddings(embeddings)

        # Convert to numpy if requested
        if convert_to_numpy:
            embeddings = embeddings.cpu().numpy()

        logger.debug(f"Generated embeddings shape: {embeddings.shape}")

        return embeddings

    def _mean_pooling(
        self,
        token_embeddings: torch.Tensor,
        attention_mask: torch.Tensor,
    ) -> torch.Tensor:
        """
        Mean pooling to get sentence embeddings.

        Context7: Standard practice for sentence transformers

        Args:
            token_embeddings: Token-level embeddings from model
            attention_mask: Attention mask for padding

        Returns:
            Mean-pooled sentence embeddings
        """
        input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
        sum_embeddings = torch.sum(token_embeddings * input_mask_expanded, 1)
        sum_mask = torch.clamp(input_mask_expanded.sum(1), min=1e-9)
        return sum_embeddings / sum_mask

    def get_model_info(self) -> dict:
        """
        Get model metadata.

        Returns:
            Dict with model information
        """
        return {
            "model_name": self.MODEL_NAME,
            "model_version": self.MODEL_VERSION,
            "embedding_dim": self.EMBEDDING_DIM,
            "max_seq_length": self.MAX_SEQ_LENGTH,
            "device": self.device,
            "loaded": self._model_loaded,
        }

    def unload_model(self):
        """
        Unload model to free memory.
        """
        if self._model_loaded:
            self.model = None
            self.tokenizer = None
            self._model_loaded = False
            logger.info("Model unloaded")

