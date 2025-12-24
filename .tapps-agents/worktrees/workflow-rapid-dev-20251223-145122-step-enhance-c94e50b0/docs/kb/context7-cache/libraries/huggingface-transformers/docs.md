# HuggingFace Transformers

**Library**: HuggingFace Transformers
**Context7 ID**: /huggingface/transformers
**Purpose**: State-of-the-art Machine Learning for PyTorch, TensorFlow, and JAX
**Last Updated**: 2025-10-19

## Overview

HuggingFace Transformers provides thousands of pretrained models for Natural Language Processing, Computer Vision, Audio, and Multimodal tasks. It offers a unified API for model loading, inference, and training across PyTorch, TensorFlow, and JAX.

## Installation

```bash
# Base installation
pip install transformers

# With PyTorch
pip install transformers[torch]

# With TensorFlow
pip install transformers[tf]

# With optimizations
pip install transformers accelerate
```

## Model Loading and Inference

### Basic Model Loading

```python
from transformers import AutoModelForCausalLM, AutoTokenizer

# Load model and tokenizer
model = AutoModelForCausalLM.from_pretrained("microsoft/Phi-3.5-mini-instruct")
tokenizer = AutoTokenizer.from_pretrained("microsoft/Phi-3.5-mini-instruct")

# Perform inference
inputs = tokenizer("Hello, how are you?", return_tensors="pt")
outputs = model.generate(**inputs, max_new_tokens=50)
print(tokenizer.decode(outputs[0]))
```

### Memory-Efficient Loading

```python
import torch
from transformers import AutoModelForCausalLM

# Load in half-precision (bfloat16)
model = AutoModelForCausalLM.from_pretrained(
    "mistralai/Mistral-7B-v0.1",
    dtype=torch.bfloat16,
    device_map="auto"  # Automatically distribute across available devices
)

# Load with 8-bit quantization
model = AutoModelForCausalLM.from_pretrained(
    "meta-llama/Llama-2-7b-chat-hf",
    load_in_8bit=True,
    device_map="auto"
)

# Load with 4-bit quantization
from transformers import BitsAndBytesConfig

quant_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_compute_dtype=torch.float16,
    bnb_4bit_quant_type="nf4"
)

model = AutoModelForCausalLM.from_pretrained(
    "meta-llama/Llama-2-7b-chat-hf",
    quantization_config=quant_config,
    device_map="auto"
)
```

### Big Model Inference (Accelerate)

```python
from transformers import AutoModelForCausalLM

# Automatically dispatch model weights across GPU, CPU, and disk
model = AutoModelForCausalLM.from_pretrained(
    "google/gemma-7b",
    device_map="auto"  # Requires Accelerate v0.9.0+ and PyTorch v1.9.0+
)
```

## Optimization for Inference

### Flash Attention 2

```python
import torch
from transformers import AutoModelForCausalLM

model = AutoModelForCausalLM.from_pretrained(
    "MiniMaxAI/MiniMax-Text-01-hf",
    dtype=torch.float16,
    attn_implementation="flash_attention_2",  # Faster attention
    device_map="auto"
)
```

### BetterTransformer

```python
from transformers import AutoModel
from optimum.bettertransformer import BetterTransformer

model = AutoModel.from_pretrained("bert-base-uncased")
bt_model = BetterTransformer.transform(model)

# Benchmark inference speed
import time
inputs = tokenizer("Sample text for benchmarking", return_tensors="pt")

start = time.time()
for _ in range(100):
    with torch.no_grad():
        _ = bt_model(**inputs)
end = time.time()
print(f"Average inference time: {(end - start) / 100 * 1000:.2f}ms")
```

### torch.compile() (PyTorch 2.0+)

```python
import torch
from transformers import AutoModelForImageClassification, AutoImageProcessor

model = AutoModelForImageClassification.from_pretrained(
    "google/vit-base-patch16-224",
    device_map="auto"
)
model = torch.compile(model)  # Compile for faster execution
```

## OpenVINO Integration

### Export and Run with OpenVINO

```python
from optimum.intel.openvino import OVModelForCausalLM
from transformers import AutoTokenizer, pipeline

# Load and export to OpenVINO format
model = OVModelForCausalLM.from_pretrained(
    "microsoft/Phi-3.5-mini-instruct",
    export=True,  # Automatically convert to OpenVINO IR
    load_in_8bit=True  # Apply 8-bit quantization
)

tokenizer = AutoTokenizer.from_pretrained("microsoft/Phi-3.5-mini-instruct")
pipe = pipeline("text-generation", model=model, tokenizer=tokenizer)
results = pipe("The weather is")
```

### INT8 Quantization

```python
from optimum.intel.openvino import OVModelForCausalLM, OVWeightQuantizationConfig

# Load with 8-bit quantization
model = OVModelForCausalLM.from_pretrained(
    "microsoft/Phi-3.5-mini-instruct",
    export=True,
    quantization_config=OVWeightQuantizationConfig(bits=8)
)
```

### INT4 Quantization

```python
from optimum.intel.openvino import OVModelForCausalLM, OVWeightQuantizationConfig

# Load with 4-bit quantization
model = OVModelForCausalLM.from_pretrained(
    "microsoft/Phi-3.5-mini-instruct",
    export=True,
    quantization_config=OVWeightQuantizationConfig(
        bits=4,
        quant_method="awq",
        scale_estimation=True,
        dataset="wikitext2",
        group_size=64,
        ratio=1.0
    )
)
```

## Task-Specific Auto Classes

```python
from transformers import (
    AutoModelForSequenceClassification,  # Text classification
    AutoModelForTokenClassification,     # Token classification (NER)
    AutoModelForQuestionAnswering,       # Question answering
    AutoModelForCausalLM,                # Causal language modeling
    AutoModelForSeq2SeqLM,               # Sequence-to-sequence
    AutoModelForImageClassification,     # Image classification
    AutoModelForObjectDetection,         # Object detection
    AutoModelForImageTextToText,         # Vision-language models
)
```

## Pipelines (High-Level API)

```python
from transformers import pipeline

# Text classification
classifier = pipeline("text-classification", model="distilbert-base-uncased-finetuned-sst-2-english")
result = classifier("I love this movie!")

# Text generation
generator = pipeline("text-generation", model="gpt2")
result = generator("Once upon a time", max_length=50)

# Question answering
qa = pipeline("question-answering")
result = qa(question="What is my name?", context="My name is Clara.")

# Image classification
image_classifier = pipeline("image-classification", model="google/vit-base-patch16-224")
result = image_classifier("path/to/image.jpg")
```

## Best Practices for Production

### 1. Use Appropriate Precision

```python
# For inference, use half-precision (float16/bfloat16)
model = AutoModelForCausalLM.from_pretrained(
    "model_name",
    torch_dtype=torch.float16,  # or torch.bfloat16
    device_map="auto"
)
```

### 2. Quantize for Edge Deployment

```python
# Use INT8 or INT4 quantization for smaller models
model = OVModelForCausalLM.from_pretrained(
    "model_name",
    export=True,
    quantization_config=OVWeightQuantizationConfig(bits=8)
)
```

### 3. Batch Processing

```python
# Process multiple inputs at once
inputs = tokenizer(["Text 1", "Text 2", "Text 3"], return_tensors="pt", padding=True)
outputs = model(**inputs)
```

### 4. Use Device Map for Large Models

```python
# Automatically distribute model across available hardware
model = AutoModelForCausalLM.from_pretrained(
    "large_model",
    device_map="auto"  # Uses GPU, CPU, and disk as needed
)
```

## Integration with Home Assistant Pattern Detection

For the HA Ingestor project's AI pattern detection (Phase 1 MVP):

```python
from optimum.intel.openvino import OVModelForSeq2SeqLM
from transformers import AutoTokenizer

# Classification model (flan-t5-small with INT8 quantization)
model = OVModelForSeq2SeqLM.from_pretrained(
    "google/flan-t5-small",
    export=True,
    quantization_config=OVWeightQuantizationConfig(bits=8)
)

tokenizer = AutoTokenizer.from_pretrained("google/flan-t5-small")

# Pattern categorization prompt
prompt = """You are a smart home pattern classifier.

Pattern: {pattern_description}

Classify into EXACTLY ONE category:
- energy (power saving, electricity, energy efficiency)
- comfort (temperature, lighting comfort, ambiance)
- security (safety, locks, monitoring, alerts)
- convenience (automation, time-saving, routine)

Respond with only the category name (one word).

Category:"""

inputs = tokenizer(prompt, return_tensors="pt")
outputs = model.generate(**inputs, max_new_tokens=10)
category = tokenizer.decode(outputs[0], skip_special_tokens=True).strip().lower()
```

## Resources

- Official Documentation: https://huggingface.co/docs/transformers
- Model Hub: https://huggingface.co/models
- Optimum for Hardware Acceleration: https://huggingface.co/docs/optimum
- Accelerate for Distributed Inference: https://huggingface.co/docs/accelerate

