"""
Parallel Model Testing Service

Runs multiple OpenAI models in parallel for the same task to compare
performance, cost, and quality metrics.

Created: January 2025
"""

import asyncio
import logging
import time
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ..database.models import ModelComparisonMetrics
from ..llm.openai_client import OpenAIClient

logger = logging.getLogger(__name__)


class ParallelModelTester:
    """Service for running multiple models in parallel and tracking comparison metrics"""

    def __init__(self, api_key: str):
        """
        Initialize parallel model tester.

        Args:
            api_key: OpenAI API key for creating model clients
        """
        self.api_key = api_key
        logger.info("ParallelModelTester initialized")

    async def generate_suggestions_parallel(
        self,
        prompt_dict: dict[str, str],
        models: list[str],
        endpoint: str,
        db_session: AsyncSession | None = None,
        query_id: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1200,
    ) -> dict[str, Any]:
        """
        Generate suggestions using multiple models in parallel.

        Args:
            prompt_dict: Prompt dictionary with system_prompt and user_prompt
            models: List of model names to test (e.g., ['gpt-4o', 'gpt-4o-mini'])
            endpoint: Endpoint name for tracking
            db_session: Database session for storing metrics
            query_id: Optional query ID for linking metrics
            temperature: Temperature for generation
            max_tokens: Maximum tokens for generation

        Returns:
            Dictionary with 'primary_result' (first model's result) and 'comparison' (metrics)
        """
        if len(models) < 2:
            msg = "Parallel testing requires at least 2 models"
            raise ValueError(msg)

        # Create clients for each model
        clients = [OpenAIClient(api_key=self.api_key, model=model) for model in models]

        # Create tasks for parallel execution
        tasks = []
        for client in clients:
            task = self._generate_suggestion_task(
                client=client,
                prompt_dict=prompt_dict,
                endpoint=endpoint,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            tasks.append(task)

        # Execute in parallel
        results = await self._execute_parallel(
            tasks=tasks,
            model_names=models,
            task_type="suggestion",
            db_session=db_session,
            query_id=query_id,
        )

        # Return primary model result (first model) for immediate use
        return {
            "primary_result": results["model_results"][0]["result"],
            "comparison": results,
        }

    async def generate_yaml_parallel(
        self,
        suggestion: dict[str, Any],
        prompt_dict: dict[str, str],
        models: list[str],
        db_session: AsyncSession | None = None,
        suggestion_id: str | None = None,
        temperature: float = 0.3,
        max_tokens: int = 2000,
    ) -> dict[str, Any]:
        """
        Generate YAML using multiple models in parallel.

        Args:
            suggestion: Suggestion dictionary
            prompt_dict: Prompt dictionary with system_prompt and user_prompt
            models: List of model names to test
            db_session: Database session for storing metrics
            suggestion_id: Optional suggestion ID for linking metrics
            temperature: Temperature for generation
            max_tokens: Maximum tokens for generation

        Returns:
            Dictionary with 'primary_result' (first model's YAML) and 'comparison' (metrics)
        """
        if len(models) < 2:
            msg = "Parallel testing requires at least 2 models"
            raise ValueError(msg)

        # Create clients for each model
        clients = [OpenAIClient(api_key=self.api_key, model=model) for model in models]

        # Create tasks for parallel execution
        tasks = []
        for client in clients:
            task = self._generate_yaml_task(
                client=client,
                prompt_dict=prompt_dict,
                endpoint="yaml_generation",
                temperature=temperature,
                max_tokens=max_tokens,
            )
            tasks.append(task)

        # Execute in parallel
        results = await self._execute_parallel(
            tasks=tasks,
            model_names=models,
            task_type="yaml",
            db_session=db_session,
            suggestion_id=suggestion_id,
        )

        # Return primary model result (first model) for immediate use
        return {
            "primary_result": results["model_results"][0]["result"],
            "comparison": results,
        }

    async def _generate_suggestion_task(
        self,
        client: OpenAIClient,
        prompt_dict: dict[str, str],
        endpoint: str,
        temperature: float,
        max_tokens: int,
    ) -> dict[str, Any]:
        """Generate suggestion task for a single model"""
        start_time = time.time()
        try:
            result = await client.generate_with_unified_prompt(
                prompt_dict=prompt_dict,
                temperature=temperature,
                max_tokens=max_tokens,
                output_format="json",
                endpoint=endpoint,
            )
            latency_ms = int((time.time() - start_time) * 1000)

            # Get token usage from client
            usage = client.last_usage or {}
            tokens_input = usage.get("prompt_tokens", 0)
            tokens_output = usage.get("completion_tokens", 0)
            cost_usd = usage.get("cost_usd", 0.0)

            return {
                "success": True,
                "result": result,
                "tokens_input": tokens_input,
                "tokens_output": tokens_output,
                "cost_usd": cost_usd,
                "latency_ms": latency_ms,
                "error": None,
            }
        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            logger.error(f"Model {client.model} failed: {e}", exc_info=True)
            return {
                "success": False,
                "result": None,
                "tokens_input": 0,
                "tokens_output": 0,
                "cost_usd": 0.0,
                "latency_ms": latency_ms,
                "error": str(e),
            }

    async def _generate_yaml_task(
        self,
        client: OpenAIClient,
        prompt_dict: dict[str, str],
        endpoint: str,
        temperature: float,
        max_tokens: int,
    ) -> dict[str, Any]:
        """Generate YAML task for a single model"""
        start_time = time.time()
        try:
            result = await client.generate_with_unified_prompt(
                prompt_dict=prompt_dict,
                temperature=temperature,
                max_tokens=max_tokens,
                output_format="yaml",
                endpoint=endpoint,
            )
            latency_ms = int((time.time() - start_time) * 1000)

            # Get token usage from client
            usage = client.last_usage or {}
            tokens_input = usage.get("prompt_tokens", 0)
            tokens_output = usage.get("completion_tokens", 0)
            cost_usd = usage.get("cost_usd", 0.0)

            return {
                "success": True,
                "result": result,
                "tokens_input": tokens_input,
                "tokens_output": tokens_output,
                "cost_usd": cost_usd,
                "latency_ms": latency_ms,
                "error": None,
            }
        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            logger.error(f"Model {client.model} failed: {e}", exc_info=True)
            return {
                "success": False,
                "result": None,
                "tokens_input": 0,
                "tokens_output": 0,
                "cost_usd": 0.0,
                "latency_ms": latency_ms,
                "error": str(e),
            }

    async def _execute_parallel(
        self,
        tasks: list,
        model_names: list[str],
        task_type: str,
        db_session: AsyncSession | None = None,
        query_id: str | None = None,
        suggestion_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Execute tasks in parallel and store metrics.

        Args:
            tasks: List of async tasks to execute
            model_names: List of model names corresponding to tasks
            task_type: 'suggestion' or 'yaml'
            db_session: Database session for storing metrics
            query_id: Optional query ID
            suggestion_id: Optional suggestion ID

        Returns:
            Dictionary with model results and comparison metrics
        """
        # Execute all tasks in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        model_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Task {i} raised exception: {result}", exc_info=True)
                model_results.append({
                    "model": model_names[i],
                    "success": False,
                    "result": None,
                    "tokens_input": 0,
                    "tokens_output": 0,
                    "cost_usd": 0.0,
                    "latency_ms": 0,
                    "error": str(result),
                })
            else:
                model_results.append({
                    "model": model_names[i],
                    **result,
                })

        # Store metrics in database if session provided
        if db_session and len(model_results) >= 2:
            await self._store_metrics(
                task_type=task_type,
                model_results=model_results,
                db_session=db_session,
                query_id=query_id,
                suggestion_id=suggestion_id,
            )

        return {
            "task_type": task_type,
            "model_results": model_results,
            "timestamp": datetime.utcnow().isoformat(),
        }

    async def _store_metrics(
        self,
        task_type: str,
        model_results: list[dict[str, Any]],
        db_session: AsyncSession,
        query_id: str | None = None,
        suggestion_id: str | None = None,
    ):
        """
        Store comparison metrics in database.

        Args:
            task_type: 'suggestion' or 'yaml'
            model_results: List of model result dictionaries
            db_session: Database session
            query_id: Optional query ID
            suggestion_id: Optional suggestion ID
        """
        if len(model_results) < 2:
            logger.warning("Need at least 2 model results to store comparison metrics")
            return

        try:
            # Get first two models for comparison
            model1 = model_results[0]
            model2 = model_results[1]

            # Create metrics record
            metrics = ModelComparisonMetrics(
                task_type=task_type,
                query_id=query_id,
                suggestion_id=suggestion_id,

                # Model 1
                model1_name=model1["model"],
                model1_tokens_input=model1.get("tokens_input", 0),
                model1_tokens_output=model1.get("tokens_output", 0),
                model1_cost_usd=model1.get("cost_usd", 0.0),
                model1_latency_ms=model1.get("latency_ms", 0),
                model1_result=model1.get("result"),
                model1_error=model1.get("error"),

                # Model 2
                model2_name=model2["model"],
                model2_tokens_input=model2.get("tokens_input", 0),
                model2_tokens_output=model2.get("tokens_output", 0),
                model2_cost_usd=model2.get("cost_usd", 0.0),
                model2_latency_ms=model2.get("latency_ms", 0),
                model2_result=model2.get("result"),
                model2_error=model2.get("error"),

                created_at=datetime.utcnow(),
            )

            db_session.add(metrics)
            await db_session.commit()

            logger.info(
                f"Stored comparison metrics: {task_type} - {model1['model']} vs {model2['model']}, "
                f"cost_diff=${abs(model1.get('cost_usd', 0) - model2.get('cost_usd', 0)):.4f}",
            )
        except Exception as e:
            logger.error(f"Failed to store comparison metrics: {e}", exc_info=True)
            await db_session.rollback()

