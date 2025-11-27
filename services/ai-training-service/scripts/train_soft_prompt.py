"""Utility script to fine-tune a lightweight soft prompt model on Ask AI data.

This script is designed for the NUC deployment footprint – CPU friendly defaults,
LoRA-based adaptation, and small batch sizes. It can be run manually or invoked
through a cron/systemd job once labelled conversations accumulate.

Epic 39, Story 39.3: Migrated to ai-training-service
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sqlite3
import sys
import warnings
from datetime import datetime
from pathlib import Path
from typing import List, Dict

# Suppress TRANSFORMERS_CACHE deprecation warnings
warnings.filterwarnings("ignore", category=FutureWarning, message=".*TRANSFORMERS_CACHE.*")

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train soft prompt adapter from Ask AI history")
    parser.add_argument(
        "--db-path",
        type=Path,
        default=Path("data/ai_automation.db"),
        help="Path to the ai_automation SQLite database",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("models/soft_prompts"),
        help="Directory where the tuned model family will be stored",
    )
    parser.add_argument(
        "--run-directory",
        type=Path,
        default=None,
        help="Optional explicit path for this training run's artifacts",
    )
    parser.add_argument(
        "--run-id",
        type=str,
        default=None,
        help="Optional identifier stored alongside training metadata",
    )
    parser.add_argument(
        "--base-model",
        type=str,
        default="google/flan-t5-small",
        help="HF Hub model to use as the base",
    )
    parser.add_argument(
        "--max-samples",
        type=int,
        default=2000,
        help="Maximum number of labelled Ask AI conversations to include",
    )
    parser.add_argument(
        "--epochs",
        type=int,
        default=3,
        help="Number of fine-tuning epochs",
    )
    parser.add_argument(
        "--learning-rate",
        type=float,
        default=5e-5,
        help="Learning rate for the trainer",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=1,
        help="Per-device batch size (NUC-optimized: 1 for minimal memory)",
    )
    parser.add_argument(
        "--target-max-tokens",
        type=int,
        default=384,
        help="Maximum tokens for generated suggestion text",
    )
    parser.add_argument(
        "--source-max-tokens",
        type=int,
        default=384,
        help="Maximum tokens for the user query context",
    )
    parser.add_argument(
        "--lora-r",
        type=int,
        default=16,
        help="Rank parameter for LoRA adapters",
    )
    parser.add_argument(
        "--lora-alpha",
        type=float,
        default=16.0,
        help="Scaling parameter for LoRA adapters",
    )
    parser.add_argument(
        "--lora-dropout",
        type=float,
        default=0.05,
        help="Dropout applied to LoRA adapters",
    )
    parser.add_argument(
        "--resume-from",
        type=Path,
        default=None,
        help="Optional path to resume training from an existing adapter",
    )

    return parser.parse_args()


def load_training_examples(db_path: Path, limit: int) -> List[Dict[str, str]]:
    if not db_path.exists():
        raise FileNotFoundError(f"SQLite database not found at {db_path}")

    query = """
        SELECT original_query, suggestions
        FROM ask_ai_queries
        WHERE suggestions IS NOT NULL
        ORDER BY created_at DESC
        LIMIT ?
    """

    examples: List[Dict[str, str]] = []

    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        for row in conn.execute(query, (limit,)):
            original_query = row["original_query"] or ""
            raw_suggestions = row["suggestions"]

            if not raw_suggestions:
                continue

            try:
                suggestions_payload = json.loads(raw_suggestions)
            except json.JSONDecodeError:
                logger.debug("Skipping malformed suggestion payload")
                continue

            # Use highest confidence suggestion as the target answer
            if isinstance(suggestions_payload, list) and suggestions_payload:
                sorted_payload = sorted(
                    suggestions_payload,
                    key=lambda item: item.get("confidence", 0),
                    reverse=True,
                )
                top_suggestion = sorted_payload[0]
                response_text = top_suggestion.get("description") or ""

                if response_text.strip():
                    examples.append(
                        {
                            "instruction": original_query.strip(),
                            "response": response_text.strip(),
                        }
                    )

    return examples


def ensure_dependencies():
    try:
        import torch  # noqa: F401
        from transformers import AutoTokenizer  # noqa: F401
        from peft import LoraConfig  # noqa: F401
        try:
            import psutil  # noqa: F401
        except ImportError:
            logger.warning("psutil not available, memory logging will be limited")
    except ImportError as exc:  # pragma: no cover - runtime dependency check
        raise RuntimeError(
            "Required dependencies missing. Install transformers[torch], torch (CPU wheel), and peft."
        ) from exc


def prepare_dataset(
    tokenizer,
    examples: List[Dict[str, str]],
    max_source_tokens: int,
    max_target_tokens: int,
):
    import torch
    from torch.utils.data import Dataset

    class PromptDataset(Dataset):
        def __len__(self) -> int:
            return len(examples)

        def __getitem__(self, idx: int):
            sample = examples[idx]

            source = tokenizer(
                sample["instruction"],
                max_length=max_source_tokens,
                truncation=True,
                padding="max_length",
                return_tensors="pt",
            )
            target = tokenizer(
                sample["response"],
                max_length=max_target_tokens,
                truncation=True,
                padding="max_length",
                return_tensors="pt",
            )

            labels = target["input_ids"].squeeze(0)
            labels[labels == tokenizer.pad_token_id] = -100

            # Ensure all tensors are on CPU
            device = torch.device("cpu")
            return {
                "input_ids": source["input_ids"].squeeze(0).to(device),
                "attention_mask": source["attention_mask"].squeeze(0).to(device),
                "labels": labels.to(device),
            }

    return PromptDataset()


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    args = parse_args()

    logger.info("=" * 60)
    logger.info("Starting soft prompt training")
    logger.info("=" * 60)
    logger.info("Run ID: %s", args.run_id or "auto-generated")
    logger.info("Database: %s", args.db_path)
    logger.info("Output directory: %s", args.output_dir)
    logger.info("Base model: %s", args.base_model)
    logger.info("Max samples: %d", args.max_samples)
    logger.info("Epochs: %d", args.epochs)

    try:
        ensure_dependencies()
        logger.info("Dependencies verified successfully")
    except RuntimeError as e:
        logger.error("Dependency check failed: %s", e)
        sys.exit(1)

    run_identifier = args.run_id or datetime.utcnow().strftime("run_%Y%m%d_%H%M%S")

    try:
        logger.info("Loading training examples from database...")
        examples = load_training_examples(args.db_path, args.max_samples)
        if not examples:
            logger.error("No Ask AI labelled data available. Nothing to train.")
            logger.error("Ensure you have approved suggestions in the database.")
            sys.exit(1)  # Exit with error code to indicate failure
        logger.info("Loaded %s training examples", len(examples))
    except FileNotFoundError as e:
        logger.exception("Database file not found: %s", e)
        sys.exit(1)
    except Exception as e:
        logger.exception("Failed to load training examples: %s", e)
        sys.exit(1)

    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer, Trainer, TrainingArguments
    from peft import LoraConfig, get_peft_model

    # Use cached model if available (set via HF_HOME environment variable)
    # Note: TRANSFORMERS_CACHE is deprecated, use HF_HOME only
    cache_dir = os.environ.get('HF_HOME') or None
    if cache_dir is None:
        # Fallback to TRANSFORMERS_CACHE only if HF_HOME not set (for backward compatibility)
        cache_dir = os.environ.get('TRANSFORMERS_CACHE')
    logger.info("Model cache directory: %s", cache_dir if cache_dir else "default location (~/.cache/huggingface/)")

    # Try to load from cache first, fall back to download if needed
    try:
        logger.info(f"Attempting to load tokenizer from cache: {cache_dir if cache_dir else 'default location'}")
        tokenizer = AutoTokenizer.from_pretrained(
            args.base_model,
            cache_dir=cache_dir,
            local_files_only=True  # Use cache only
        )
        logger.info("Tokenizer loaded from cache successfully")
    except (OSError, FileNotFoundError) as e:
        logger.warning(f"Tokenizer not found in cache ({e}), downloading from HuggingFace Hub...")
        try:
            tokenizer = AutoTokenizer.from_pretrained(
                args.base_model,
                cache_dir=cache_dir,
                local_files_only=False
            )
            logger.info("Tokenizer downloaded and loaded successfully")
        except Exception as download_error:
            logger.exception("Failed to download tokenizer: %s", download_error)
            sys.exit(1)
    except Exception as e:
        logger.exception("Unexpected error loading tokenizer: %s", e)
        sys.exit(1)

    try:
        logger.info("Preparing dataset...")
        dataset = prepare_dataset(
            tokenizer,
            examples,
            max_source_tokens=args.source_max_tokens,
            max_target_tokens=args.target_max_tokens,
        )
        logger.info("Dataset prepared successfully")
    except Exception as e:
        logger.exception("Failed to prepare dataset: %s", e)
        sys.exit(1)

    try:
        import torch
        # Explicitly set device to CPU for NUC deployment (no GPU)
        device = torch.device("cpu")
        logger.info("Using device: %s", device)
        
        logger.info("Loading model from cache: %s...", cache_dir if cache_dir else "default location")
        try:
            model = AutoModelForSeq2SeqLM.from_pretrained(
                args.base_model,
                cache_dir=cache_dir,
                local_files_only=True,  # Try cache first
                torch_dtype=torch.float32,  # Explicitly use float32 for CPU
            )
            # Ensure model is on CPU device
            model = model.to(device)
            logger.info("Model loaded from cache successfully and moved to CPU")
        except (OSError, FileNotFoundError) as cache_error:
            logger.warning(f"Model not found in cache ({cache_error}), downloading from HuggingFace Hub...")
            model = AutoModelForSeq2SeqLM.from_pretrained(
                args.base_model,
                cache_dir=cache_dir,
                local_files_only=False,
                torch_dtype=torch.float32,
            )
            model = model.to(device)
            logger.info("Model downloaded and loaded successfully, moved to CPU")
    except Exception as e:
        logger.exception("Failed to load model: %s", e)
        logger.error("Model loading failed. Check network connectivity and HuggingFace Hub access.")
        sys.exit(1)

    try:
        logger.info("Configuring LoRA adapters...")
        lora_config = LoraConfig(
            r=args.lora_r,
            lora_alpha=args.lora_alpha,
            target_modules=["q", "v"],
            lora_dropout=args.lora_dropout,
            bias="none",
            task_type="SEQ_2_SEQ_LM",
        )
        model = get_peft_model(model, lora_config)
        logger.info("LoRA adapters configured successfully")
    except Exception as e:
        logger.exception("Failed to configure LoRA adapters: %s", e)
        sys.exit(1)
    
    # Enable training mode (PEFT automatically marks LoRA parameters as trainable)
    model.train()

    if args.resume_from:
        try:
            logger.info("Resuming from adapter at %s", args.resume_from)
            model.load_adapter(str(args.resume_from))
            logger.info("Adapter loaded successfully")
        except Exception as e:
            logger.exception("Failed to load adapter: %s", e)
            sys.exit(1)

    try:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        run_dir = args.run_directory or (args.output_dir / run_identifier)
        run_dir.mkdir(parents=True, exist_ok=True)
        logger.info("Output directories created: %s", run_dir)
    except Exception as e:
        logger.exception("Failed to create output directories: %s", e)
        sys.exit(1)

    try:
        import torch
        logger.info("Configuring training arguments...")
        training_args = TrainingArguments(
            output_dir=str(run_dir),
            per_device_train_batch_size=args.batch_size,
            gradient_accumulation_steps=2,  # Reduced from 4 for NUC memory constraints
            num_train_epochs=args.epochs,
            learning_rate=args.learning_rate,
            logging_dir=str(run_dir / "logs"),
            logging_steps=10,
            save_strategy="epoch",
            eval_strategy="no",  # Changed from evaluation_strategy in transformers >= 4.21
            report_to=["none"],
            dataloader_drop_last=False,
            bf16=False,
            fp16=False,
            gradient_checkpointing=False,  # Disabled: incompatible with PEFT/LoRA (causes grad_fn errors)
            dataloader_num_workers=0,  # Disable multiprocessing to save memory
            remove_unused_columns=False,  # Keep all columns to avoid extra processing
            disable_tqdm=True,  # Disable progress bars to save memory (NUC optimization - no GUI needed)
            dataloader_pin_memory=False,  # Disable pin_memory (no GPU, saves memory)
        )
        logger.info("Training arguments configured for CPU training")
    except Exception as e:
        logger.exception("Failed to configure training arguments: %s", e)
        sys.exit(1)

    try:
        logger.info("Initializing trainer...")
        trainer = Trainer(
            model=model,
            args=training_args,
            train_dataset=dataset,
            processing_class=tokenizer,  # Updated from tokenizer (deprecated in v5.0)
        )
        logger.info("Trainer initialized successfully")
    except Exception as e:
        logger.exception("Failed to initialize trainer: %s", e)
        sys.exit(1)

    try:
        import torch
        
        # Log memory usage before training (if psutil available)
        process = None
        try:
            import psutil
            process = psutil.Process(os.getpid())
            memory_info = process.memory_info()
            logger.info(f"Memory usage before training: {memory_info.rss / 1024 / 1024:.2f} MB")
            logger.info(f"Available memory: {psutil.virtual_memory().available / 1024 / 1024:.2f} MB")
        except ImportError:
            logger.info("Memory logging unavailable (psutil not installed)")
        
        logger.info(f"PyTorch device: {torch.device('cpu')}")
        logger.info(f"Number of training examples: {len(examples)}")
        logger.info(f"Batch size: {args.batch_size}, Gradient accumulation: 2")
        
        logger.info("Starting training...")
        # Ensure model and all parameters are on CPU
        device = torch.device("cpu")
        trainer.model = trainer.model.to(device)
        
        # Double-check model is on CPU
        if next(trainer.model.parameters()).is_cuda:
            logger.warning("Model parameters detected on CUDA, moving to CPU...")
            trainer.model = trainer.model.to(device)
        
        logger.info(f"Model device confirmed: {next(trainer.model.parameters()).device}")
        train_result = trainer.train()
        logger.info("Training completed successfully. Final loss: %.4f", train_result.training_loss)
        
        # Log memory usage after training (if psutil available)
        if process is not None:
            try:
                memory_info_after = process.memory_info()
                logger.info(f"Memory usage after training: {memory_info_after.rss / 1024 / 1024:.2f} MB")
            except Exception:
                pass  # Ignore errors in post-training memory logging
    except torch.cuda.OutOfMemoryError as e:
        logger.exception("CUDA out of memory error (unexpected on CPU): %s", e)
        sys.exit(1)
    except RuntimeError as e:
        error_msg = str(e)
        if "out of memory" in error_msg.lower() or "OOM" in error_msg:
            logger.exception("Out of memory error during training: %s", e)
            logger.error("Try reducing batch_size (--batch-size) or max_samples (--max-samples)")
        else:
            logger.exception("Runtime error during training: %s", e)
        sys.exit(1)
    except SystemExit:
        # Re-raise system exits (like from sys.exit)
        raise
    except BaseException as e:
        # Catch all other exceptions including OOM kills (SIGKILL)
        error_msg = str(e)
        logger.exception("Training failed with unexpected error: %s", e)
        logger.error("Error type: %s", type(e).__name__)
        
        # Check if this might be an OOM kill (process was killed)
        import signal
        if hasattr(e, 'errno') and e.errno == -9:
            logger.error("Process was killed (likely OOM). Container memory limit may be too low.")
            logger.error("Current container limit: Check docker-compose.yml (ai-training-service)")
            logger.error("Recommendation: Increase memory limit to 2GB or reduce training parameters")
        
        sys.exit(1)
    except Exception as e:
        logger.exception("Training failed with unexpected error: %s", e)
        logger.error("Error type: %s", type(e).__name__)
        sys.exit(1)

    try:
        logger.info("Saving model and tokenizer...")
        trainer.save_model(str(run_dir))
        tokenizer.save_pretrained(run_dir)
        logger.info("Model and tokenizer saved successfully")
    except Exception as e:
        logger.exception("Failed to save model/tokenizer: %s", e)
        sys.exit(1)

    try:
        metadata = {
            "base_model": args.base_model,
            "samples_used": len(examples),
            "epochs": args.epochs,
            "learning_rate": args.learning_rate,
            "run_directory": str(run_dir),
            "trained_at": datetime.utcnow().isoformat(),
            "final_loss": train_result.training_loss,
            "run_id": run_identifier,
        }

        metadata_path = run_dir / "training_run.json"
        with open(metadata_path, "w", encoding="utf-8") as fp:
            json.dump(metadata, fp, indent=2)
        logger.info("Training metadata saved to %s", metadata_path)
    except Exception as e:
        logger.exception("Failed to save training metadata: %s", e)
        sys.exit(1)

    try:
        latest_symlink = args.output_dir / "latest"
        if latest_symlink.exists() or latest_symlink.is_symlink():
            latest_symlink.unlink()
        latest_symlink.symlink_to(run_dir, target_is_directory=True)
        logger.info("Latest symlink created: %s -> %s", latest_symlink, run_dir)
    except Exception as e:
        logger.warning("Failed to create latest symlink: %s (non-fatal)", e)

    logger.info("Training complete. Artifacts written to %s", run_dir)


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    main()

