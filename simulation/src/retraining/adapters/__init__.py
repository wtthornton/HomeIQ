"""
Training Data Adapters

Adapters to convert simulation JSON data to formats expected by production training scripts.
"""

from .gnn_adapter import GNNDataAdapter
from .soft_prompt_adapter import SoftPromptDataAdapter

__all__ = ["GNNDataAdapter", "SoftPromptDataAdapter"]

