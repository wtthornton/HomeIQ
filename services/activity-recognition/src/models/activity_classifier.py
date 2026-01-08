"""
Activity Classification Model using LSTM

LSTM-based neural network for classifying smart home activities
from sensor sequences.

Features:
- Multi-layer LSTM with dropout
- Supports variable sequence lengths
- ONNX export for NUC deployment
- Configurable architecture
"""

import logging
from pathlib import Path
from typing import Any

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset

logger = logging.getLogger(__name__)


# Activity labels
ACTIVITIES = {
    0: "sleeping",
    1: "waking",
    2: "leaving",
    3: "arriving",
    4: "cooking",
    5: "eating",
    6: "working",
    7: "watching_tv",
    8: "relaxing",
    9: "other",
}


class ActivityLSTM(nn.Module):
    """
    LSTM-based activity classifier for sensor sequences.
    
    Architecture:
    - Multi-layer LSTM with dropout
    - Fully connected classifier
    - Softmax output for activity probabilities
    """
    
    def __init__(
        self,
        input_size: int = 10,
        hidden_size: int = 64,
        num_layers: int = 2,
        num_classes: int = 10,
        dropout: float = 0.2,
        bidirectional: bool = False,
    ):
        """
        Initialize the LSTM classifier.
        
        Args:
            input_size: Number of input features per time step
            hidden_size: LSTM hidden state size
            num_layers: Number of LSTM layers
            num_classes: Number of activity classes
            dropout: Dropout probability
            bidirectional: Whether to use bidirectional LSTM
        """
        super().__init__()
        
        self.input_size = input_size
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        self.num_classes = num_classes
        self.bidirectional = bidirectional
        
        # LSTM layers
        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0,
            bidirectional=bidirectional,
        )
        
        # Classifier
        lstm_output_size = hidden_size * 2 if bidirectional else hidden_size
        self.classifier = nn.Sequential(
            nn.Dropout(dropout),
            nn.Linear(lstm_output_size, hidden_size // 2),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_size // 2, num_classes),
        )
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Forward pass.
        
        Args:
            x: Input tensor of shape (batch, seq_len, input_size)
            
        Returns:
            Output tensor of shape (batch, num_classes)
        """
        # LSTM forward pass
        lstm_out, (h_n, c_n) = self.lstm(x)
        
        # Use the last time step output
        if self.bidirectional:
            # Concatenate forward and backward hidden states
            last_output = torch.cat([
                lstm_out[:, -1, :self.hidden_size],
                lstm_out[:, 0, self.hidden_size:]
            ], dim=1)
        else:
            last_output = lstm_out[:, -1, :]
        
        # Classify
        logits = self.classifier(last_output)
        
        return logits
    
    def predict(self, x: torch.Tensor) -> torch.Tensor:
        """
        Predict activity labels.
        
        Args:
            x: Input tensor of shape (batch, seq_len, input_size)
            
        Returns:
            Predicted labels of shape (batch,)
        """
        self.eval()
        with torch.no_grad():
            logits = self.forward(x)
            predictions = torch.argmax(logits, dim=1)
        return predictions
    
    def predict_proba(self, x: torch.Tensor) -> torch.Tensor:
        """
        Predict activity probabilities.
        
        Args:
            x: Input tensor of shape (batch, seq_len, input_size)
            
        Returns:
            Probabilities of shape (batch, num_classes)
        """
        self.eval()
        with torch.no_grad():
            logits = self.forward(x)
            probs = torch.softmax(logits, dim=1)
        return probs


class ActivityTrainer:
    """
    Trainer for ActivityLSTM model.
    
    Features:
    - Training loop with validation
    - Early stopping
    - Learning rate scheduling
    - Model checkpointing
    """
    
    def __init__(
        self,
        model: ActivityLSTM,
        device: str = "cpu",
        learning_rate: float = 1e-3,
        weight_decay: float = 1e-4,
    ):
        """
        Initialize the trainer.
        
        Args:
            model: ActivityLSTM model
            device: Device to train on ('cpu' or 'cuda')
            learning_rate: Initial learning rate
            weight_decay: L2 regularization weight
        """
        self.model = model.to(device)
        self.device = device
        
        self.criterion = nn.CrossEntropyLoss()
        self.optimizer = torch.optim.AdamW(
            model.parameters(),
            lr=learning_rate,
            weight_decay=weight_decay,
        )
        self.scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
            self.optimizer,
            mode="min",
            factor=0.5,
            patience=5,
            verbose=True,
        )
        
        self.train_losses: list[float] = []
        self.val_losses: list[float] = []
        self.best_val_loss = float("inf")
    
    def train_epoch(self, dataloader: DataLoader) -> float:
        """Train for one epoch."""
        self.model.train()
        total_loss = 0.0
        
        for batch_x, batch_y in dataloader:
            batch_x = batch_x.to(self.device)
            batch_y = batch_y.to(self.device)
            
            self.optimizer.zero_grad()
            
            logits = self.model(batch_x)
            loss = self.criterion(logits, batch_y)
            
            loss.backward()
            torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)
            self.optimizer.step()
            
            total_loss += loss.item()
        
        return total_loss / len(dataloader)
    
    def validate(self, dataloader: DataLoader) -> tuple[float, float]:
        """Validate the model."""
        self.model.eval()
        total_loss = 0.0
        correct = 0
        total = 0
        
        with torch.no_grad():
            for batch_x, batch_y in dataloader:
                batch_x = batch_x.to(self.device)
                batch_y = batch_y.to(self.device)
                
                logits = self.model(batch_x)
                loss = self.criterion(logits, batch_y)
                
                total_loss += loss.item()
                
                predictions = torch.argmax(logits, dim=1)
                correct += (predictions == batch_y).sum().item()
                total += batch_y.size(0)
        
        avg_loss = total_loss / len(dataloader)
        accuracy = correct / total
        
        return avg_loss, accuracy
    
    def train(
        self,
        train_loader: DataLoader,
        val_loader: DataLoader,
        num_epochs: int = 50,
        early_stopping_patience: int = 10,
        checkpoint_dir: Path | None = None,
    ) -> dict[str, Any]:
        """
        Train the model.
        
        Args:
            train_loader: Training data loader
            val_loader: Validation data loader
            num_epochs: Maximum number of epochs
            early_stopping_patience: Epochs to wait before early stopping
            checkpoint_dir: Directory to save checkpoints
            
        Returns:
            Training history dictionary
        """
        if checkpoint_dir:
            checkpoint_dir = Path(checkpoint_dir)
            checkpoint_dir.mkdir(parents=True, exist_ok=True)
        
        patience_counter = 0
        
        for epoch in range(num_epochs):
            # Train
            train_loss = self.train_epoch(train_loader)
            self.train_losses.append(train_loss)
            
            # Validate
            val_loss, val_accuracy = self.validate(val_loader)
            self.val_losses.append(val_loss)
            
            # Learning rate scheduling
            self.scheduler.step(val_loss)
            
            logger.info(
                f"Epoch {epoch + 1}/{num_epochs} - "
                f"Train Loss: {train_loss:.4f}, "
                f"Val Loss: {val_loss:.4f}, "
                f"Val Accuracy: {val_accuracy:.2%}"
            )
            
            # Check for improvement
            if val_loss < self.best_val_loss:
                self.best_val_loss = val_loss
                patience_counter = 0
                
                # Save best model
                if checkpoint_dir:
                    self.save_checkpoint(checkpoint_dir / "best_model.pt")
            else:
                patience_counter += 1
            
            # Early stopping
            if patience_counter >= early_stopping_patience:
                logger.info(f"Early stopping at epoch {epoch + 1}")
                break
        
        return {
            "train_losses": self.train_losses,
            "val_losses": self.val_losses,
            "best_val_loss": self.best_val_loss,
            "epochs_trained": len(self.train_losses),
        }
    
    def save_checkpoint(self, path: Path) -> None:
        """Save model checkpoint."""
        torch.save({
            "model_state_dict": self.model.state_dict(),
            "optimizer_state_dict": self.optimizer.state_dict(),
            "scheduler_state_dict": self.scheduler.state_dict(),
            "train_losses": self.train_losses,
            "val_losses": self.val_losses,
            "best_val_loss": self.best_val_loss,
            "model_config": {
                "input_size": self.model.input_size,
                "hidden_size": self.model.hidden_size,
                "num_layers": self.model.num_layers,
                "num_classes": self.model.num_classes,
                "bidirectional": self.model.bidirectional,
            },
        }, path)
        logger.info(f"Saved checkpoint to {path}")
    
    def load_checkpoint(self, path: Path) -> None:
        """Load model checkpoint."""
        checkpoint = torch.load(path, map_location=self.device)
        self.model.load_state_dict(checkpoint["model_state_dict"])
        self.optimizer.load_state_dict(checkpoint["optimizer_state_dict"])
        self.scheduler.load_state_dict(checkpoint["scheduler_state_dict"])
        self.train_losses = checkpoint["train_losses"]
        self.val_losses = checkpoint["val_losses"]
        self.best_val_loss = checkpoint["best_val_loss"]
        logger.info(f"Loaded checkpoint from {path}")


def export_to_onnx(
    model: ActivityLSTM,
    output_path: Path | str,
    sequence_length: int = 30,
    opset_version: int = 14,
) -> None:
    """
    Export PyTorch model to ONNX for NUC deployment.
    
    Args:
        model: Trained ActivityLSTM model
        output_path: Path to save ONNX model
        sequence_length: Expected sequence length
        opset_version: ONNX opset version
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    model.eval()
    
    # Create dummy input
    dummy_input = torch.randn(1, sequence_length, model.input_size)
    
    # Export
    torch.onnx.export(
        model,
        dummy_input,
        str(output_path),
        input_names=["sensor_sequence"],
        output_names=["activity_logits"],
        dynamic_axes={
            "sensor_sequence": {0: "batch_size"},
            "activity_logits": {0: "batch_size"},
        },
        opset_version=opset_version,
        do_constant_folding=True,
    )
    
    logger.info(f"Exported ONNX model to {output_path}")


def load_onnx_model(model_path: Path | str):
    """
    Load ONNX model for inference.
    
    Args:
        model_path: Path to ONNX model
        
    Returns:
        ONNX Runtime inference session
    """
    import onnxruntime as ort
    
    session = ort.InferenceSession(
        str(model_path),
        providers=["CPUExecutionProvider"],
    )
    
    return session


def predict_with_onnx(
    session,
    sensor_sequence: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Run inference with ONNX model.
    
    Args:
        session: ONNX Runtime session
        sensor_sequence: Input array of shape (batch, seq_len, features)
        
    Returns:
        Tuple of (predicted_labels, probabilities)
    """
    # Ensure correct dtype
    sensor_sequence = sensor_sequence.astype(np.float32)
    
    # Run inference
    input_name = session.get_inputs()[0].name
    output_name = session.get_outputs()[0].name
    
    logits = session.run([output_name], {input_name: sensor_sequence})[0]
    
    # Convert to predictions
    probs = np.exp(logits) / np.sum(np.exp(logits), axis=1, keepdims=True)
    predictions = np.argmax(logits, axis=1)
    
    return predictions, probs


def main():
    """Example usage of ActivityLSTM."""
    logging.basicConfig(level=logging.INFO)
    
    # Create model
    model = ActivityLSTM(
        input_size=5,
        hidden_size=64,
        num_layers=2,
        num_classes=10,
    )
    
    logger.info(f"Model architecture:\n{model}")
    
    # Count parameters
    total_params = sum(p.numel() for p in model.parameters())
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    logger.info(f"\nTotal parameters: {total_params:,}")
    logger.info(f"Trainable parameters: {trainable_params:,}")
    
    # Create synthetic data
    n_samples = 1000
    seq_len = 30
    n_features = 5
    
    X = np.random.randn(n_samples, seq_len, n_features).astype(np.float32)
    y = np.random.randint(0, 10, n_samples)
    
    # Create data loaders
    dataset = TensorDataset(
        torch.from_numpy(X),
        torch.from_numpy(y).long(),
    )
    train_loader = DataLoader(dataset, batch_size=32, shuffle=True)
    val_loader = DataLoader(dataset, batch_size=32)
    
    # Train
    trainer = ActivityTrainer(model, device="cpu")
    history = trainer.train(
        train_loader,
        val_loader,
        num_epochs=5,
        checkpoint_dir=Path("./models"),
    )
    
    logger.info(f"\nTraining history: {history}")
    
    # Export to ONNX
    export_to_onnx(model, Path("./models/activity_lstm.onnx"), sequence_length=seq_len)
    
    # Test ONNX inference
    session = load_onnx_model("./models/activity_lstm.onnx")
    test_input = np.random.randn(2, seq_len, n_features).astype(np.float32)
    predictions, probs = predict_with_onnx(session, test_input)
    logger.info(f"\nONNX predictions: {predictions}")
    logger.info(f"Activity names: {[ACTIVITIES[p] for p in predictions]}")


if __name__ == "__main__":
    main()
