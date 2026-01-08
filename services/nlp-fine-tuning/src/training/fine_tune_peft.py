"""
PEFT/LoRA Fine-Tuning for Home Assistant Commands

Uses Parameter-Efficient Fine-Tuning (PEFT) with LoRA to fine-tune
language models on Home Assistant command understanding with minimal
compute requirements.

This approach:
- Only updates ~0.1% of model parameters
- Enables fine-tuning on consumer hardware
- Produces small adapter weights that can be shared
"""

import logging
import os
from pathlib import Path
from typing import Any

import torch

logger = logging.getLogger(__name__)


class HAFineTuner:
    """
    Fine-tune language models using LoRA for Home Assistant commands.
    
    This class provides:
    1. Model loading with quantization for memory efficiency
    2. LoRA adapter configuration
    3. Training with Hugging Face Trainer
    4. Model saving and export
    """
    
    # Supported base models
    SUPPORTED_MODELS = {
        "mistral-7b": "mistralai/Mistral-7B-Instruct-v0.3",
        "llama-3-8b": "meta-llama/Meta-Llama-3-8B-Instruct",
        "phi-3-mini": "microsoft/Phi-3-mini-4k-instruct",
        "gemma-2b": "google/gemma-2b-it",
    }
    
    def __init__(
        self,
        base_model: str = "mistral-7b",
        load_in_8bit: bool = True,
        load_in_4bit: bool = False,
        device_map: str = "auto",
    ):
        """
        Initialize the fine-tuner.
        
        Args:
            base_model: Model name or path (can be key from SUPPORTED_MODELS)
            load_in_8bit: Use 8-bit quantization (recommended for NUC)
            load_in_4bit: Use 4-bit quantization (more aggressive)
            device_map: Device placement strategy
        """
        try:
            from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
            from peft import LoraConfig, get_peft_model, TaskType, prepare_model_for_kbit_training
        except ImportError:
            raise ImportError(
                "Please install required packages: "
                "pip install transformers>=4.45.0 peft>=0.13.0 bitsandbytes>=0.43.0"
            )
        
        # Resolve model name
        if base_model in self.SUPPORTED_MODELS:
            model_name = self.SUPPORTED_MODELS[base_model]
        else:
            model_name = base_model
        
        self.model_name = model_name
        self.load_in_8bit = load_in_8bit
        self.load_in_4bit = load_in_4bit
        
        logger.info(f"Loading base model: {model_name}")
        
        # Configure quantization
        quantization_config = None
        if load_in_4bit:
            quantization_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_use_double_quant=True,
            )
        elif load_in_8bit:
            quantization_config = BitsAndBytesConfig(
                load_in_8bit=True,
            )
        
        # Load tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(
            model_name,
            trust_remote_code=True,
        )
        
        # Ensure padding token is set
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
        
        # Load model with quantization
        self.model = AutoModelForCausalLM.from_pretrained(
            model_name,
            quantization_config=quantization_config,
            device_map=device_map,
            trust_remote_code=True,
            torch_dtype=torch.float16 if not quantization_config else None,
        )
        
        # Prepare model for k-bit training
        if quantization_config:
            self.model = prepare_model_for_kbit_training(self.model)
        
        # Configure LoRA
        self.lora_config = LoraConfig(
            task_type=TaskType.CAUSAL_LM,
            r=16,  # LoRA rank
            lora_alpha=32,  # LoRA alpha
            lora_dropout=0.1,
            target_modules=self._get_target_modules(model_name),
            bias="none",
        )
        
        # Apply LoRA
        self.model = get_peft_model(self.model, self.lora_config)
        
        # Log trainable parameters
        trainable_params, total_params = self._count_parameters()
        logger.info(
            f"Trainable parameters: {trainable_params:,} / {total_params:,} "
            f"({100 * trainable_params / total_params:.2f}%)"
        )
    
    def _get_target_modules(self, model_name: str) -> list[str]:
        """Get target modules for LoRA based on model architecture."""
        model_lower = model_name.lower()
        
        if "mistral" in model_lower or "llama" in model_lower:
            return ["q_proj", "v_proj", "k_proj", "o_proj"]
        elif "phi" in model_lower:
            return ["q_proj", "v_proj", "k_proj", "dense"]
        elif "gemma" in model_lower:
            return ["q_proj", "v_proj", "k_proj", "o_proj"]
        else:
            # Default for transformer models
            return ["q_proj", "v_proj"]
    
    def _count_parameters(self) -> tuple[int, int]:
        """Count trainable and total parameters."""
        trainable = sum(p.numel() for p in self.model.parameters() if p.requires_grad)
        total = sum(p.numel() for p in self.model.parameters())
        return trainable, total
    
    def prepare_dataset(
        self,
        examples: list[dict[str, str]],
        max_length: int = 512,
    ) -> Any:
        """
        Prepare dataset for training.
        
        Args:
            examples: List of instruction-input-output dicts
            max_length: Maximum sequence length
            
        Returns:
            Tokenized dataset ready for training
        """
        from datasets import Dataset
        
        def format_prompt(example: dict[str, str]) -> str:
            """Format example as instruction-following prompt."""
            instruction = example.get("instruction", "")
            input_text = example.get("input", "")
            output = example.get("output", "")
            
            if input_text:
                prompt = f"### Instruction:\n{instruction}\n\n### Input:\n{input_text}\n\n### Response:\n{output}"
            else:
                prompt = f"### Instruction:\n{instruction}\n\n### Response:\n{output}"
            
            return prompt
        
        def tokenize(example: dict[str, str]) -> dict[str, Any]:
            """Tokenize a single example."""
            prompt = format_prompt(example)
            
            tokenized = self.tokenizer(
                prompt,
                truncation=True,
                max_length=max_length,
                padding="max_length",
                return_tensors=None,
            )
            
            # Set labels (same as input_ids for causal LM)
            tokenized["labels"] = tokenized["input_ids"].copy()
            
            return tokenized
        
        # Create dataset
        dataset = Dataset.from_list(examples)
        
        # Tokenize
        tokenized_dataset = dataset.map(
            tokenize,
            remove_columns=dataset.column_names,
            desc="Tokenizing",
        )
        
        logger.info(f"Prepared {len(tokenized_dataset):,} training examples")
        
        return tokenized_dataset
    
    def train(
        self,
        train_dataset: Any,
        eval_dataset: Any | None = None,
        output_dir: str = "./models/ha-lora",
        num_epochs: int = 3,
        batch_size: int = 4,
        learning_rate: float = 2e-4,
        warmup_steps: int = 100,
        logging_steps: int = 10,
        save_steps: int = 500,
        gradient_accumulation_steps: int = 4,
    ) -> None:
        """
        Train the model with LoRA.
        
        Args:
            train_dataset: Tokenized training dataset
            eval_dataset: Optional tokenized evaluation dataset
            output_dir: Directory to save model checkpoints
            num_epochs: Number of training epochs
            batch_size: Per-device batch size
            learning_rate: Learning rate
            warmup_steps: Number of warmup steps
            logging_steps: Log every N steps
            save_steps: Save checkpoint every N steps
            gradient_accumulation_steps: Gradient accumulation steps
        """
        from transformers import (
            Trainer,
            TrainingArguments,
            DataCollatorForLanguageModeling,
        )
        
        # Training arguments
        training_args = TrainingArguments(
            output_dir=output_dir,
            num_train_epochs=num_epochs,
            per_device_train_batch_size=batch_size,
            per_device_eval_batch_size=batch_size,
            gradient_accumulation_steps=gradient_accumulation_steps,
            learning_rate=learning_rate,
            warmup_steps=warmup_steps,
            logging_steps=logging_steps,
            save_steps=save_steps,
            save_total_limit=3,
            evaluation_strategy="steps" if eval_dataset else "no",
            eval_steps=save_steps if eval_dataset else None,
            fp16=True,
            optim="paged_adamw_8bit",
            report_to="none",  # Disable wandb/tensorboard
            load_best_model_at_end=True if eval_dataset else False,
        )
        
        # Data collator
        data_collator = DataCollatorForLanguageModeling(
            tokenizer=self.tokenizer,
            mlm=False,  # Causal LM, not masked LM
        )
        
        # Create trainer
        trainer = Trainer(
            model=self.model,
            args=training_args,
            train_dataset=train_dataset,
            eval_dataset=eval_dataset,
            data_collator=data_collator,
        )
        
        logger.info("Starting training...")
        trainer.train()
        
        # Save final model
        trainer.save_model(output_dir)
        self.tokenizer.save_pretrained(output_dir)
        
        logger.info(f"Training complete. Model saved to {output_dir}")
    
    def save_adapter(self, output_dir: str | Path) -> None:
        """
        Save only the LoRA adapter weights.
        
        This produces a small file (~10-50MB) that can be loaded
        on top of the base model.
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        self.model.save_pretrained(output_dir)
        self.tokenizer.save_pretrained(output_dir)
        
        logger.info(f"Saved LoRA adapter to {output_dir}")
    
    def merge_and_save(self, output_dir: str | Path) -> None:
        """
        Merge LoRA weights into base model and save.
        
        This creates a standalone model that doesn't require
        the PEFT library to load.
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Merge LoRA weights
        merged_model = self.model.merge_and_unload()
        
        # Save merged model
        merged_model.save_pretrained(output_dir)
        self.tokenizer.save_pretrained(output_dir)
        
        logger.info(f"Saved merged model to {output_dir}")
    
    def generate(
        self,
        prompt: str,
        max_new_tokens: int = 256,
        temperature: float = 0.7,
        top_p: float = 0.9,
    ) -> str:
        """
        Generate response for a prompt.
        
        Args:
            prompt: Input prompt
            max_new_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            top_p: Top-p sampling parameter
            
        Returns:
            Generated text
        """
        # Format prompt
        formatted = f"### Instruction:\nYou are a Home Assistant AI. Parse the user's smart home request and generate the appropriate response.\n\n### Input:\n{prompt}\n\n### Response:\n"
        
        # Tokenize
        inputs = self.tokenizer(
            formatted,
            return_tensors="pt",
            truncation=True,
            max_length=512,
        ).to(self.model.device)
        
        # Generate
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                temperature=temperature,
                top_p=top_p,
                do_sample=True,
                pad_token_id=self.tokenizer.pad_token_id,
            )
        
        # Decode
        generated = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        # Extract response part
        if "### Response:" in generated:
            response = generated.split("### Response:")[-1].strip()
        else:
            response = generated[len(formatted):].strip()
        
        return response


def main():
    """Example usage of HAFineTuner."""
    logging.basicConfig(level=logging.INFO)
    
    # Example training data
    examples = [
        {
            "instruction": "Parse the user's smart home request.",
            "input": "Turn on the living room lights",
            "output": "I'll turn on the living room lights for you.",
        },
        {
            "instruction": "Parse the user's smart home request.",
            "input": "Set the thermostat to 72 degrees",
            "output": "Setting the thermostat to 72°F.",
        },
    ]
    
    # Initialize fine-tuner (use smaller model for testing)
    fine_tuner = HAFineTuner(
        base_model="gemma-2b",  # Smaller model for testing
        load_in_8bit=True,
    )
    
    # Prepare dataset
    train_dataset = fine_tuner.prepare_dataset(examples)
    
    # Train (short run for testing)
    fine_tuner.train(
        train_dataset,
        output_dir="./models/ha-lora-test",
        num_epochs=1,
        batch_size=1,
    )
    
    # Test generation
    response = fine_tuner.generate("Turn off the bedroom fan")
    print(f"\nGenerated response: {response}")


if __name__ == "__main__":
    main()
