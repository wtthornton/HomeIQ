# NLP Fine-Tuning Service

Fine-tuning service for improving HomeIQ's natural language understanding of Home Assistant commands.

## Overview

This service provides tools for fine-tuning language models on the Home Assistant Requests dataset to improve:
- Intent classification accuracy
- Entity extraction (devices, areas, parameters)
- Response generation quality

## Features

### Data Loading
- Load Home Assistant Requests dataset from Hugging Face
- Preprocess and structure data for different fine-tuning approaches
- Export to OpenAI JSONL or PEFT format

### Fine-Tuning Options

#### 1. PEFT/LoRA (Local)
- Parameter-efficient fine-tuning
- Only updates ~0.1% of model parameters
- Works on consumer hardware (16GB RAM)
- Supports Mistral, Llama, Phi, Gemma models

#### 2. OpenAI Fine-Tuning (Cloud)
- Uses OpenAI's infrastructure
- Best for production with OpenAI models
- Supports GPT-4o-mini, GPT-4o, GPT-3.5-turbo

### Evaluation
- Intent classification accuracy
- Entity extraction F1 score
- Exact match accuracy
- BLEU score for response quality
- Per-domain accuracy breakdown

## Usage

### Load and Prepare Data

```python
from src.data.ha_requests_loader import HARequestsLoader

loader = HARequestsLoader()
df = loader.load()

# For OpenAI fine-tuning
openai_examples = loader.to_openai_format(df)
loader.save_openai_jsonl(openai_examples, "data/training.jsonl")

# For PEFT fine-tuning
peft_examples = loader.to_peft_format(df)
```

### PEFT Fine-Tuning

```python
from src.training.fine_tune_peft import HAFineTuner

# Initialize with 8-bit quantization
fine_tuner = HAFineTuner(
    base_model="mistral-7b",
    load_in_8bit=True,
)

# Prepare dataset
train_dataset = fine_tuner.prepare_dataset(peft_examples)

# Train
fine_tuner.train(
    train_dataset,
    output_dir="./models/ha-lora",
    num_epochs=3,
)

# Save adapter
fine_tuner.save_adapter("./models/ha-lora-adapter")
```

### OpenAI Fine-Tuning

```python
from src.training.fine_tune_openai import OpenAIFineTuner

fine_tuner = OpenAIFineTuner()

# Estimate cost
cost = fine_tuner.estimate_cost(openai_examples)
print(f"Estimated cost: ${cost['estimated_training_cost_usd']}")

# Upload and train
file_id = fine_tuner.upload_training_file(openai_examples)
job_id = fine_tuner.create_fine_tuning_job(
    file_id,
    base_model="gpt-4o-mini",
    n_epochs=3,
)

# Wait for completion
model_id = fine_tuner.wait_for_completion(job_id)

# Test
response = fine_tuner.test_model("Turn on the living room lights", model_id)
```

### Evaluation

```python
from src.evaluation.metrics import NLPEvaluator

evaluator = NLPEvaluator()

# Evaluate intent classification
evaluator.evaluate_intent_classification(predictions, ground_truth)

# Evaluate entity extraction
evaluator.evaluate_entity_extraction(pred_entities, true_entities)

# Get summary
summary = evaluator.get_summary()
```

## Dependencies

- `polars>=1.0.0` - Fast data processing
- `datasets>=3.0.0` - Hugging Face datasets
- `transformers>=4.45.0` - Model loading
- `peft>=0.13.0` - Parameter-efficient fine-tuning
- `torch>=2.5.0` - PyTorch
- `openai>=1.0.0` - OpenAI API

## Integration with HomeIQ

After fine-tuning, update the AI Automation Service to use the fine-tuned model:

1. **For PEFT models**: Deploy the adapter alongside the base model
2. **For OpenAI models**: Update `OPENAI_MODEL` environment variable

See `services/ai-automation-service-new/src/clients/openai_client.py` for integration.
