"""Utility script to fine-tune a lightweight soft prompt model on Ask AI data.

This script is designed for the NUC deployment footprint – CPU friendly defaults,
LoRA-based adaptation, and small batch sizes. It can be run manually or invoked
through a cron/systemd job once labelled conversations accumulate.
"""

from __future__ import annotations

import argparse
import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path

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
        default=Path("data/ask_ai_soft_prompt"),
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
        default=2,
        help="Per-device batch size (kept small for CPU training)",
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


def load_training_examples(db_path: Path, limit: int) -> list[dict[str, str]]:
    if not db_path.exists():
        msg = f"SQLite database not found at {db_path}"
        raise FileNotFoundError(msg)

    query = """
        SELECT original_query, suggestions
        FROM ask_ai_queries
        WHERE suggestions IS NOT NULL
        ORDER BY created_at DESC
        LIMIT ?
    """

    examples: list[dict[str, str]] = []

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
                        },
                    )

    return examples


def ensure_dependencies():
    try:
        import torch  # noqa: F401
        from peft import LoraConfig  # noqa: F401
        from transformers import AutoTokenizer  # noqa: F401
    except ImportError as exc:  # pragma: no cover - runtime dependency check
        msg = "Required dependencies missing. Install transformers[torch], torch (CPU wheel), and peft."
        raise RuntimeError(
            msg,
        ) from exc


def prepare_dataset(
    tokenizer,
    examples: list[dict[str, str]],
    max_source_tokens: int,
    max_target_tokens: int,
):
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

            return {
                "input_ids": source["input_ids"].squeeze(0),
                "attention_mask": source["attention_mask"].squeeze(0),
                "labels": labels,
            }

    return PromptDataset()


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    args = parse_args()

    ensure_dependencies()

    run_identifier = args.run_id or datetime.utcnow().strftime("run_%Y%m%d_%H%M%S")

    examples = load_training_examples(args.db_path, args.max_samples)
    if not examples:
        logger.error("No Ask AI labelled data available. Nothing to train.")
        return

    logger.info("Loaded %s training examples", len(examples))

    from peft import LoraConfig, get_peft_model
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer, Trainer, TrainingArguments

    tokenizer = AutoTokenizer.from_pretrained(args.base_model)

    dataset = prepare_dataset(
        tokenizer,
        examples,
        max_source_tokens=args.source_max_tokens,
        max_target_tokens=args.target_max_tokens,
    )

    model = AutoModelForSeq2SeqLM.from_pretrained(args.base_model)

    lora_config = LoraConfig(
        r=args.lora_r,
        lora_alpha=args.lora_alpha,
        target_modules=["q", "v"],
        lora_dropout=args.lora_dropout,
        bias="none",
        task_type="SEQ_2_SEQ_LM",
    )
    model = get_peft_model(model, lora_config)

    if args.resume_from:
        logger.info("Resuming from adapter at %s", args.resume_from)
        model.load_adapter(str(args.resume_from))

    args.output_dir.mkdir(parents=True, exist_ok=True)
    run_dir = args.run_directory or (args.output_dir / run_identifier)
    run_dir.mkdir(parents=True, exist_ok=True)

    training_args = TrainingArguments(
        output_dir=str(run_dir),
        per_device_train_batch_size=args.batch_size,
        gradient_accumulation_steps=4,
        num_train_epochs=args.epochs,
        learning_rate=args.learning_rate,
        logging_dir=str(run_dir / "logs"),
        logging_steps=10,
        save_strategy="epoch",
        evaluation_strategy="no",
        report_to=["none"],
        dataloader_drop_last=False,
        bf16=False,
        fp16=False,
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=dataset,
        tokenizer=tokenizer,
    )

    train_result = trainer.train()
    trainer.save_model(str(run_dir))
    tokenizer.save_pretrained(run_dir)

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

    with open(run_dir / "training_run.json", "w", encoding="utf-8") as fp:
        json.dump(metadata, fp, indent=2)

    latest_symlink = args.output_dir / "latest"
    if latest_symlink.exists() or latest_symlink.is_symlink():
        latest_symlink.unlink()
    latest_symlink.symlink_to(run_dir, target_is_directory=True)

    logger.info("Training complete. Artifacts written to %s", run_dir)


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    main()

