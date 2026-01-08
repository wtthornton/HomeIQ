"""
OpenAI Fine-Tuning for Home Assistant Commands

Uses OpenAI's fine-tuning API to create custom models optimized
for Home Assistant command understanding.

This approach:
- Uses OpenAI's infrastructure for training
- Produces models accessible via API
- Best for production deployments using OpenAI
"""

import json
import logging
import os
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class OpenAIFineTuner:
    """
    Fine-tune OpenAI models for Home Assistant commands.
    
    This class provides:
    1. Training data preparation and validation
    2. File upload to OpenAI
    3. Fine-tuning job management
    4. Model deployment and testing
    """
    
    # Supported base models for fine-tuning
    SUPPORTED_MODELS = {
        "gpt-4o-mini": "gpt-4o-mini-2024-07-18",
        "gpt-4o": "gpt-4o-2024-08-06",
        "gpt-3.5-turbo": "gpt-3.5-turbo-0125",
    }
    
    def __init__(
        self,
        api_key: str | None = None,
        organization: str | None = None,
    ):
        """
        Initialize the OpenAI fine-tuner.
        
        Args:
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
            organization: OpenAI organization ID (optional)
        """
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError(
                "Please install the openai library: pip install openai>=1.0.0"
            )
        
        self.client = OpenAI(
            api_key=api_key or os.getenv("OPENAI_API_KEY"),
            organization=organization or os.getenv("OPENAI_ORGANIZATION"),
        )
        
        self._uploaded_file_id: str | None = None
        self._fine_tuning_job_id: str | None = None
        self._fine_tuned_model: str | None = None
    
    def validate_training_data(
        self,
        examples: list[dict[str, Any]],
    ) -> tuple[bool, list[str]]:
        """
        Validate training data format for OpenAI fine-tuning.
        
        Args:
            examples: List of conversation dictionaries
            
        Returns:
            Tuple of (is_valid, list of error messages)
        """
        errors = []
        
        if len(examples) < 10:
            errors.append(f"Need at least 10 examples, got {len(examples)}")
        
        for i, example in enumerate(examples):
            if "messages" not in example:
                errors.append(f"Example {i}: missing 'messages' key")
                continue
            
            messages = example["messages"]
            
            if not isinstance(messages, list):
                errors.append(f"Example {i}: 'messages' must be a list")
                continue
            
            if len(messages) < 2:
                errors.append(f"Example {i}: need at least 2 messages")
                continue
            
            # Check message format
            for j, msg in enumerate(messages):
                if "role" not in msg:
                    errors.append(f"Example {i}, message {j}: missing 'role'")
                if "content" not in msg:
                    errors.append(f"Example {i}, message {j}: missing 'content'")
                if msg.get("role") not in ["system", "user", "assistant"]:
                    errors.append(f"Example {i}, message {j}: invalid role '{msg.get('role')}'")
            
            # Check for at least one assistant message
            has_assistant = any(m.get("role") == "assistant" for m in messages)
            if not has_assistant:
                errors.append(f"Example {i}: must have at least one assistant message")
        
        is_valid = len(errors) == 0
        
        if is_valid:
            logger.info(f"Validated {len(examples)} examples successfully")
        else:
            logger.warning(f"Validation failed with {len(errors)} errors")
        
        return is_valid, errors
    
    def estimate_cost(
        self,
        examples: list[dict[str, Any]],
        base_model: str = "gpt-4o-mini",
        n_epochs: int = 3,
    ) -> dict[str, Any]:
        """
        Estimate fine-tuning cost.
        
        Args:
            examples: Training examples
            base_model: Base model to fine-tune
            n_epochs: Number of training epochs
            
        Returns:
            Cost estimate dictionary
        """
        # Approximate token counts
        total_tokens = 0
        for example in examples:
            for msg in example.get("messages", []):
                content = msg.get("content", "")
                # Rough estimate: 1 token per 4 characters
                total_tokens += len(content) // 4
        
        # Training tokens = tokens * epochs
        training_tokens = total_tokens * n_epochs
        
        # Pricing per 1M tokens (as of 2024)
        pricing = {
            "gpt-4o-mini": {"training": 3.00, "input": 0.15, "output": 0.60},
            "gpt-4o": {"training": 25.00, "input": 2.50, "output": 10.00},
            "gpt-3.5-turbo": {"training": 8.00, "input": 0.50, "output": 1.50},
        }
        
        model_pricing = pricing.get(base_model, pricing["gpt-4o-mini"])
        
        training_cost = (training_tokens / 1_000_000) * model_pricing["training"]
        
        return {
            "total_examples": len(examples),
            "estimated_tokens": total_tokens,
            "training_tokens": training_tokens,
            "n_epochs": n_epochs,
            "base_model": base_model,
            "estimated_training_cost_usd": round(training_cost, 2),
            "pricing_per_1m_tokens": model_pricing,
        }
    
    def upload_training_file(
        self,
        examples: list[dict[str, Any]],
        purpose: str = "fine-tune",
    ) -> str:
        """
        Upload training data to OpenAI.
        
        Args:
            examples: Training examples in OpenAI format
            purpose: File purpose (default: fine-tune)
            
        Returns:
            Uploaded file ID
        """
        import tempfile
        
        # Validate first
        is_valid, errors = self.validate_training_data(examples)
        if not is_valid:
            raise ValueError(f"Invalid training data: {errors}")
        
        # Write to temporary JSONL file
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".jsonl",
            delete=False,
            encoding="utf-8",
        ) as f:
            for example in examples:
                f.write(json.dumps(example) + "\n")
            temp_path = f.name
        
        try:
            # Upload file
            with open(temp_path, "rb") as f:
                response = self.client.files.create(
                    file=f,
                    purpose=purpose,
                )
            
            self._uploaded_file_id = response.id
            logger.info(f"Uploaded training file: {response.id}")
            
            return response.id
            
        finally:
            # Clean up temp file
            Path(temp_path).unlink(missing_ok=True)
    
    def create_fine_tuning_job(
        self,
        training_file_id: str | None = None,
        base_model: str = "gpt-4o-mini",
        n_epochs: int = 3,
        batch_size: int | None = None,
        learning_rate_multiplier: float | None = None,
        suffix: str = "homeiq-ha-commands",
    ) -> str:
        """
        Create a fine-tuning job.
        
        Args:
            training_file_id: ID of uploaded training file
            base_model: Base model to fine-tune
            n_epochs: Number of training epochs
            batch_size: Batch size (auto if None)
            learning_rate_multiplier: Learning rate multiplier (auto if None)
            suffix: Suffix for the fine-tuned model name
            
        Returns:
            Fine-tuning job ID
        """
        file_id = training_file_id or self._uploaded_file_id
        if not file_id:
            raise ValueError("No training file ID provided or uploaded")
        
        # Resolve model name
        model_name = self.SUPPORTED_MODELS.get(base_model, base_model)
        
        # Build hyperparameters
        hyperparameters = {"n_epochs": n_epochs}
        if batch_size:
            hyperparameters["batch_size"] = batch_size
        if learning_rate_multiplier:
            hyperparameters["learning_rate_multiplier"] = learning_rate_multiplier
        
        # Create job
        response = self.client.fine_tuning.jobs.create(
            training_file=file_id,
            model=model_name,
            hyperparameters=hyperparameters,
            suffix=suffix,
        )
        
        self._fine_tuning_job_id = response.id
        logger.info(f"Created fine-tuning job: {response.id}")
        
        return response.id
    
    def get_job_status(self, job_id: str | None = None) -> dict[str, Any]:
        """
        Get the status of a fine-tuning job.
        
        Args:
            job_id: Fine-tuning job ID
            
        Returns:
            Job status dictionary
        """
        job_id = job_id or self._fine_tuning_job_id
        if not job_id:
            raise ValueError("No job ID provided")
        
        response = self.client.fine_tuning.jobs.retrieve(job_id)
        
        return {
            "id": response.id,
            "status": response.status,
            "model": response.model,
            "fine_tuned_model": response.fine_tuned_model,
            "created_at": response.created_at,
            "finished_at": response.finished_at,
            "trained_tokens": response.trained_tokens,
            "error": response.error,
        }
    
    def wait_for_completion(
        self,
        job_id: str | None = None,
        poll_interval: int = 60,
        timeout: int = 7200,
    ) -> str:
        """
        Wait for fine-tuning job to complete.
        
        Args:
            job_id: Fine-tuning job ID
            poll_interval: Seconds between status checks
            timeout: Maximum seconds to wait
            
        Returns:
            Fine-tuned model ID
        """
        job_id = job_id or self._fine_tuning_job_id
        if not job_id:
            raise ValueError("No job ID provided")
        
        start_time = time.time()
        
        while True:
            status = self.get_job_status(job_id)
            
            logger.info(f"Job {job_id} status: {status['status']}")
            
            if status["status"] == "succeeded":
                self._fine_tuned_model = status["fine_tuned_model"]
                logger.info(f"Fine-tuning complete! Model: {self._fine_tuned_model}")
                return self._fine_tuned_model
            
            if status["status"] == "failed":
                raise RuntimeError(f"Fine-tuning failed: {status.get('error')}")
            
            if status["status"] == "cancelled":
                raise RuntimeError("Fine-tuning was cancelled")
            
            elapsed = time.time() - start_time
            if elapsed > timeout:
                raise TimeoutError(f"Fine-tuning timed out after {timeout} seconds")
            
            time.sleep(poll_interval)
    
    def list_jobs(self, limit: int = 10) -> list[dict[str, Any]]:
        """List recent fine-tuning jobs."""
        response = self.client.fine_tuning.jobs.list(limit=limit)
        
        return [
            {
                "id": job.id,
                "status": job.status,
                "model": job.model,
                "fine_tuned_model": job.fine_tuned_model,
                "created_at": job.created_at,
            }
            for job in response.data
        ]
    
    def cancel_job(self, job_id: str | None = None) -> None:
        """Cancel a fine-tuning job."""
        job_id = job_id or self._fine_tuning_job_id
        if not job_id:
            raise ValueError("No job ID provided")
        
        self.client.fine_tuning.jobs.cancel(job_id)
        logger.info(f"Cancelled job: {job_id}")
    
    def test_model(
        self,
        prompt: str,
        model_id: str | None = None,
        system_prompt: str | None = None,
    ) -> str:
        """
        Test the fine-tuned model.
        
        Args:
            prompt: User prompt to test
            model_id: Fine-tuned model ID
            system_prompt: Optional system prompt
            
        Returns:
            Model response
        """
        model_id = model_id or self._fine_tuned_model
        if not model_id:
            raise ValueError("No model ID provided")
        
        if system_prompt is None:
            system_prompt = (
                "You are a Home Assistant AI that helps users control their smart home. "
                "Parse user requests and generate appropriate Home Assistant service calls."
            )
        
        response = self.client.chat.completions.create(
            model=model_id,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            max_tokens=256,
        )
        
        return response.choices[0].message.content
    
    def delete_model(self, model_id: str | None = None) -> None:
        """Delete a fine-tuned model."""
        model_id = model_id or self._fine_tuned_model
        if not model_id:
            raise ValueError("No model ID provided")
        
        self.client.models.delete(model_id)
        logger.info(f"Deleted model: {model_id}")
    
    def get_fine_tuned_model_id(self) -> str | None:
        """Get the fine-tuned model ID."""
        return self._fine_tuned_model


def main():
    """Example usage of OpenAIFineTuner."""
    logging.basicConfig(level=logging.INFO)
    
    # Example training data
    examples = [
        {
            "messages": [
                {"role": "system", "content": "You are a Home Assistant AI."},
                {"role": "user", "content": "Turn on the living room lights"},
                {"role": "assistant", "content": "I'll turn on the living room lights for you."},
            ]
        },
        # Add more examples...
    ]
    
    fine_tuner = OpenAIFineTuner()
    
    # Validate data
    is_valid, errors = fine_tuner.validate_training_data(examples)
    print(f"Validation: {'passed' if is_valid else 'failed'}")
    if errors:
        print(f"Errors: {errors}")
    
    # Estimate cost
    cost = fine_tuner.estimate_cost(examples)
    print(f"\nCost estimate: {json.dumps(cost, indent=2)}")
    
    # To actually fine-tune:
    # file_id = fine_tuner.upload_training_file(examples)
    # job_id = fine_tuner.create_fine_tuning_job(file_id)
    # model_id = fine_tuner.wait_for_completion(job_id)
    # response = fine_tuner.test_model("Turn off the bedroom fan", model_id)


if __name__ == "__main__":
    main()
