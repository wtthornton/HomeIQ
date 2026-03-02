"""
Transformer-Based Sequence Modeling for Synergy Detection

Uses transformer models to learn device action sequences and predict next actions.
Understands temporal order: "Door opens -> Light turns on -> Music starts" is different
from "Music starts -> Light turns on -> Door opens".

2025 Best Practice: Transformer models excel at sequence modeling and temporal patterns.
Expected improvement: +20-30% accuracy in synergy detection.
Epic 39: Migrated from archived ai-automation-service (optional, framework ready)
Epic 7, Story 3: Fine-tuning implementation
Epic 7, Story 4: Transformer-based prediction implementation
"""

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


class DeviceSequenceTransformer:
    """
    Transformer model for learning device action sequences.

    Architecture:
    - Input: Sequence of device state changes with timestamps
    - Model: Fine-tuned transformer (BERT-style) with classification head
    - Output: Next device action prediction + confidence

    To enable full functionality:
    1. Install dependencies: pip install transformers torch
    2. Provide training data via learn_sequences()
    3. Model checkpoint saved to model_dir for inference
    """

    def __init__(
        self,
        model_name: str = "bert-base-uncased",
        use_pretrained: bool = True,
        model_dir: str = "/app/data/models/sequence_transformer",
    ):
        """
        Initialize sequence transformer.

        Args:
            model_name: Hugging Face model name
            use_pretrained: Whether to use pre-trained model (faster) or train from scratch
            model_dir: Directory to save/load model checkpoints
        """
        self.model_name = model_name
        self.use_pretrained = use_pretrained
        self.model_dir = model_dir
        self.model: Any | None = None
        self.tokenizer: Any | None = None
        self.classification_head: Any | None = None
        self.device_vocab: dict[str, int] = {}  # Device ID to token index
        self.idx_to_device: dict[int, str] = {}  # Reverse mapping
        self._is_initialized = False
        self._has_trained_head = False
        self._torch: Any | None = None

        logger.info(
            "DeviceSequenceTransformer initialized (model=%s, pretrained=%s)",
            model_name, use_pretrained,
        )

    async def initialize(self) -> None:
        """Lazy initialization of transformer model."""
        if self._is_initialized:
            return

        try:
            try:
                import torch
                from transformers import AutoModel, AutoTokenizer
                self._torch = torch
            except ImportError:
                logger.warning("transformers library not available, sequence learning disabled")
                logger.warning("Install with: pip install transformers torch")
                return

            if self.use_pretrained:
                logger.info("Loading pre-trained model: %s", self.model_name)
                self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
                self.model = AutoModel.from_pretrained(self.model_name)
                # Freeze base model parameters for efficient fine-tuning
                for param in self.model.parameters():
                    param.requires_grad = False
                logger.info("Pre-trained model loaded (frozen for fine-tuning)")

            # Try to load existing checkpoint
            self._load_checkpoint()

            self._is_initialized = True
            logger.info("Sequence transformer initialized")

        except Exception as e:
            logger.error("Failed to initialize sequence transformer: %s", e)
            logger.warning("Sequence learning will be disabled")

    def _build_classification_head(self, vocab_size: int) -> None:
        """Build a classification head for next-device prediction.

        Args:
            vocab_size: Number of unique devices in the vocabulary.
        """
        torch = self._torch
        if torch is None or self.model is None:
            return

        hidden_size = self.model.config.hidden_size
        self.classification_head = torch.nn.Sequential(
            torch.nn.Linear(hidden_size, hidden_size // 2),
            torch.nn.ReLU(),
            torch.nn.Dropout(0.1),
            torch.nn.Linear(hidden_size // 2, vocab_size),
        )
        logger.info(
            "Classification head built: hidden=%d -> %d classes", hidden_size, vocab_size,
        )

    def _sequence_to_text(self, sequence: list[dict[str, Any]]) -> str:
        """Convert a device event sequence to a text representation for the tokenizer.

        Args:
            sequence: List of event dicts with entity_id and state keys.

        Returns:
            Space-separated string of "entity_id:state" tokens.
        """
        tokens = []
        for event in sequence:
            entity_id = event.get("entity_id", "unknown")
            state = event.get("state", "unknown")
            tokens.append(f"{entity_id}:{state}")
        return " ".join(tokens)

    async def learn_sequences(self, event_sequences: list[list[dict[str, Any]]]) -> dict[str, Any]:
        """
        Learn from historical device action sequences via fine-tuning.

        Trains a classification head on top of the frozen BERT encoder to predict
        the next device given a sequence of preceding device events.

        Args:
            event_sequences: List of sequences, each sequence is list of events
                Example: [
                    [{"entity_id": "motion.kitchen", "state": "on", "timestamp": "..."}, ...],
                    [{"entity_id": "light.kitchen", "state": "on", "timestamp": "..."}, ...]
                ]

        Returns:
            Training statistics dict.
        """
        if not self._is_initialized:
            await self.initialize()

        if not self._is_initialized or not self.model:
            logger.warning("Model not initialized, skipping sequence learning")
            return {"status": "skipped", "reason": "model_not_initialized"}

        torch = self._torch
        if torch is None:
            return {"status": "skipped", "reason": "torch_not_available"}

        logger.info("Learning from %d event sequences...", len(event_sequences))

        # Build device vocabulary from all sequences
        all_devices: set[str] = set()
        for sequence in event_sequences:
            for event in sequence:
                all_devices.add(event.get("entity_id", ""))
        all_devices.discard("")

        device_list = sorted(all_devices)
        self.device_vocab = {device: idx for idx, device in enumerate(device_list)}
        self.idx_to_device = {idx: device for device, idx in self.device_vocab.items()}
        vocab_size = len(device_list)

        if vocab_size < 2:
            logger.warning("Vocabulary too small (%d devices), skipping training", vocab_size)
            return {"status": "skipped", "reason": "vocabulary_too_small", "vocabulary_size": vocab_size}

        logger.info("Built vocabulary: %d devices", vocab_size)

        # Build classification head
        self._build_classification_head(vocab_size)
        if self.classification_head is None:
            return {"status": "skipped", "reason": "classification_head_failed"}

        # Prepare training pairs: (input_sequence[:-1], target_device_idx)
        input_texts: list[str] = []
        target_indices: list[int] = []

        for sequence in event_sequences:
            if len(sequence) < 2:
                continue
            # Use all-but-last as input, last device as target
            input_seq = sequence[:-1]
            target_device = sequence[-1].get("entity_id", "")
            if target_device in self.device_vocab:
                input_texts.append(self._sequence_to_text(input_seq))
                target_indices.append(self.device_vocab[target_device])

        if len(input_texts) < 2:
            logger.warning("Insufficient training pairs (%d), skipping", len(input_texts))
            return {
                "status": "skipped",
                "reason": "insufficient_training_data",
                "pairs_found": len(input_texts),
            }

        logger.info("Prepared %d training pairs", len(input_texts))

        # Tokenize inputs
        encodings = self.tokenizer(
            input_texts,
            padding=True,
            truncation=True,
            max_length=128,
            return_tensors="pt",
        )
        labels = torch.tensor(target_indices, dtype=torch.long)

        # Training loop
        optimizer = torch.optim.AdamW(self.classification_head.parameters(), lr=2e-4)
        criterion = torch.nn.CrossEntropyLoss()

        self.model.eval()
        self.classification_head.train()

        epochs = min(10, max(3, len(input_texts) // 10))
        best_loss = float("inf")
        patience_counter = 0
        patience = 3

        training_losses: list[float] = []

        for epoch in range(epochs):
            # Get BERT embeddings (frozen)
            with torch.no_grad():
                outputs = self.model(**encodings)
                # Use [CLS] token embedding
                cls_embeddings = outputs.last_hidden_state[:, 0, :]

            # Forward through classification head
            logits = self.classification_head(cls_embeddings)
            loss = criterion(logits, labels)

            # Backward pass
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

            epoch_loss = loss.item()
            training_losses.append(epoch_loss)

            # Calculate accuracy
            with torch.no_grad():
                predictions = torch.argmax(logits, dim=1)
                accuracy = (predictions == labels).float().mean().item()

            logger.info(
                "Epoch %d/%d - loss: %.4f, accuracy: %.4f",
                epoch + 1, epochs, epoch_loss, accuracy,
            )

            # Early stopping
            if epoch_loss < best_loss:
                best_loss = epoch_loss
                patience_counter = 0
            else:
                patience_counter += 1
                if patience_counter >= patience:
                    logger.info("Early stopping at epoch %d", epoch + 1)
                    break

        self._has_trained_head = True
        self.classification_head.eval()

        # Save checkpoint
        self._save_checkpoint()

        final_accuracy = accuracy
        return {
            "status": "complete",
            "sequences_processed": len(event_sequences),
            "training_pairs": len(input_texts),
            "vocabulary_size": vocab_size,
            "epochs_completed": len(training_losses),
            "final_loss": training_losses[-1] if training_losses else None,
            "final_accuracy": round(final_accuracy, 4),
        }

    async def predict_next_action(
        self,
        current_sequence: list[dict[str, Any]],
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """
        Predict next device action given current sequence.

        Uses the fine-tuned classification head when a trained checkpoint exists.
        Falls back to heuristics otherwise.

        Args:
            current_sequence: Current sequence of device events
            top_k: Number of top predictions to return

        Returns:
            List of predicted next actions with confidence scores
        """
        if not self._is_initialized:
            await self.initialize()

        if not self._is_initialized or not self.model:
            logger.debug("Model not initialized, using fallback heuristics")
            return self._predict_with_heuristics(current_sequence, top_k)

        # Use transformer prediction when trained head is available
        if self._has_trained_head and self.classification_head is not None:
            predictions = self._predict_with_transformer(current_sequence, top_k)
            if predictions:
                return predictions
            # Fall through to heuristics if transformer prediction fails

        logger.debug("No trained checkpoint, using fallback heuristics")
        return self._predict_with_heuristics(current_sequence, top_k)

    def _predict_with_transformer(
        self,
        current_sequence: list[dict[str, Any]],
        top_k: int,
    ) -> list[dict[str, Any]]:
        """Predict next action using the fine-tuned transformer head.

        Args:
            current_sequence: Current sequence of device events.
            top_k: Number of top predictions to return.

        Returns:
            List of predicted next actions with confidence scores.
        """
        torch = self._torch
        if torch is None or self.model is None or self.classification_head is None:
            return []

        if not current_sequence:
            return []

        try:
            # Tokenize the input sequence
            input_text = self._sequence_to_text(current_sequence)
            encodings = self.tokenizer(
                [input_text],
                padding=True,
                truncation=True,
                max_length=128,
                return_tensors="pt",
            )

            # Get prediction
            self.model.eval()
            self.classification_head.eval()

            with torch.no_grad():
                outputs = self.model(**encodings)
                cls_embedding = outputs.last_hidden_state[:, 0, :]
                logits = self.classification_head(cls_embedding)
                probabilities = torch.softmax(logits, dim=1)[0]

                # Get top-k predictions
                top_values, top_indices = torch.topk(probabilities, min(top_k, len(probabilities)))

            predictions = []
            for prob, idx in zip(top_values.tolist(), top_indices.tolist()):
                device_id = self.idx_to_device.get(idx, f"unknown_{idx}")
                predictions.append({
                    "entity_id": device_id,
                    "confidence": round(prob, 4),
                    "reason": "Transformer sequence prediction",
                    "method": "transformer",
                })

            return predictions

        except Exception as e:
            logger.warning("Transformer prediction failed: %s, falling back to heuristics", e)
            return []

    def _predict_with_heuristics(
        self,
        current_sequence: list[dict[str, Any]],
        top_k: int,
    ) -> list[dict[str, Any]]:
        """
        Fallback prediction using simple heuristics.

        Args:
            current_sequence: Current sequence of device events
            top_k: Number of predictions to return

        Returns:
            List of predicted next actions
        """
        if not current_sequence:
            return []

        last_event = current_sequence[-1]
        last_entity = last_event.get("entity_id", "")
        last_domain = last_entity.split(".")[0] if "." in last_entity else ""

        predictions = []

        # Motion sensor -> Light
        if last_domain == "binary_sensor" and "motion" in last_entity.lower():
            predictions.append({
                "entity_id": "light.follow_up",
                "confidence": 0.7,
                "reason": "Motion sensors commonly trigger lights",
                "method": "heuristic",
            })

        # Door sensor -> Lock
        if last_domain == "binary_sensor" and "door" in last_entity.lower():
            predictions.append({
                "entity_id": "lock.follow_up",
                "confidence": 0.8,
                "reason": "Door sensors commonly trigger locks",
                "method": "heuristic",
            })

        # Temperature sensor -> Climate
        if last_domain == "sensor" and "temp" in last_entity.lower():
            predictions.append({
                "entity_id": "climate.follow_up",
                "confidence": 0.6,
                "reason": "Temperature sensors commonly trigger climate control",
                "method": "heuristic",
            })

        predictions.sort(key=lambda x: x.get("confidence", 0), reverse=True)
        return predictions[:top_k]

    def _save_checkpoint(self) -> None:
        """Save model checkpoint (classification head, vocabulary)."""
        torch = self._torch
        if torch is None or self.classification_head is None:
            return

        try:
            os.makedirs(self.model_dir, exist_ok=True)
            checkpoint = {
                "classification_head_state": self.classification_head.state_dict(),
                "device_vocab": self.device_vocab,
                "idx_to_device": self.idx_to_device,
            }
            path = os.path.join(self.model_dir, "checkpoint.pt")
            torch.save(checkpoint, path)
            logger.info("Checkpoint saved to %s", path)
        except Exception as e:
            logger.error("Failed to save checkpoint: %s", e)

    def _load_checkpoint(self) -> None:
        """Load model checkpoint if it exists."""
        torch = self._torch
        if torch is None or self.model is None:
            return

        path = os.path.join(self.model_dir, "checkpoint.pt")
        if not os.path.exists(path):
            return

        try:
            checkpoint = torch.load(path, weights_only=False)
            self.device_vocab = checkpoint["device_vocab"]
            self.idx_to_device = checkpoint["idx_to_device"]
            vocab_size = len(self.device_vocab)

            if vocab_size > 0:
                self._build_classification_head(vocab_size)
                if self.classification_head is not None:
                    self.classification_head.load_state_dict(checkpoint["classification_head_state"])
                    self.classification_head.eval()
                    self._has_trained_head = True
                    logger.info("Checkpoint loaded from %s (%d devices)", path, vocab_size)
        except Exception as e:
            logger.warning("Failed to load checkpoint from %s: %s", path, e)
