"""
Batch Processor

Batch processing and parallelization for simulation framework.
Supports processing 100+ homes and 50+ queries in parallel.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


class BatchProcessor:
    """
    Batch processor for simulation framework.
    
    Supports:
    - Parallel processing of multiple homes
    - Batch processing of queries
    - Configurable concurrency limits
    """

    def __init__(
        self,
        max_parallel_homes: int = 10,
        max_parallel_queries: int = 20
    ):
        """
        Initialize batch processor.
        
        Args:
            max_parallel_homes: Maximum parallel homes to process
            max_parallel_queries: Maximum parallel queries to process
        """
        self.max_parallel_homes = max_parallel_homes
        self.max_parallel_queries = max_parallel_queries
        
        logger.info(f"BatchProcessor initialized: max_parallel_homes={max_parallel_homes}, max_parallel_queries={max_parallel_queries}")

    async def process_homes_batch(
        self,
        homes: list[dict[str, Any]],
        workflow_func: Any,  # Callable that processes a single home
        workflow_type: str = "3am"
    ) -> dict[str, Any]:
        """
        Process a batch of homes in parallel.
        
        Args:
            homes: List of home dictionaries
            workflow_func: Function to process a single home
            workflow_type: Workflow type ("3am" or "ask_ai")
            
        Returns:
            Batch processing results
        """
        logger.info(f"Processing batch of {len(homes)} homes (workflow: {workflow_type})")
        start_time = datetime.now(timezone.utc)
        
        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(self.max_parallel_homes)
        
        async def process_home_with_semaphore(home: dict[str, Any]) -> dict[str, Any]:
            """Process a single home with semaphore control."""
            async with semaphore:
                try:
                    home_id = home.get("home_id", "unknown")
                    result = await workflow_func(home)
                    return {
                        "home_id": home_id,
                        "status": "success",
                        "result": result
                    }
                except Exception as e:
                    logger.error(f"Error processing home {home.get('home_id', 'unknown')}: {e}", exc_info=True)
                    return {
                        "home_id": home.get("home_id", "unknown"),
                        "status": "error",
                        "error": str(e)
                    }
        
        # Process all homes in parallel
        tasks = [process_home_with_semaphore(home) for home in homes]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process exceptions
        processed_results = []
        for result in results:
            if isinstance(result, Exception):
                processed_results.append({
                    "status": "error",
                    "error": str(result)
                })
            else:
                processed_results.append(result)
        
        end_time = datetime.now(timezone.utc)
        duration = (end_time - start_time).total_seconds()
        
        # Calculate statistics
        successful = sum(1 for r in processed_results if r.get("status") == "success")
        failed = len(processed_results) - successful
        
        logger.info(f"Batch processing completed: {successful} successful, {failed} failed, {duration:.2f}s")
        
        return {
            "total_homes": len(homes),
            "successful": successful,
            "failed": failed,
            "duration_seconds": duration,
            "results": processed_results
        }

    async def process_queries_batch(
        self,
        queries: list[dict[str, Any]],
        query_func: Any,  # Callable that processes a single query
        home_id: str
    ) -> dict[str, Any]:
        """
        Process a batch of queries in parallel.
        
        Args:
            queries: List of query dictionaries
            query_func: Function to process a single query
            home_id: Home identifier
            
        Returns:
            Batch processing results
        """
        logger.info(f"Processing batch of {len(queries)} queries for home {home_id}")
        start_time = datetime.now(timezone.utc)
        
        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(self.max_parallel_queries)
        
        async def process_query_with_semaphore(query: dict[str, Any]) -> dict[str, Any]:
            """Process a single query with semaphore control."""
            async with semaphore:
                try:
                    query_text = query.get("query", "")
                    result = await query_func(home_id, query_text)
                    return {
                        "query": query_text,
                        "status": "success",
                        "result": result
                    }
                except Exception as e:
                    logger.error(f"Error processing query '{query.get('query', '')}': {e}", exc_info=True)
                    return {
                        "query": query.get("query", ""),
                        "status": "error",
                        "error": str(e)
                    }
        
        # Process all queries in parallel
        tasks = [process_query_with_semaphore(query) for query in queries]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process exceptions
        processed_results = []
        for result in results:
            if isinstance(result, Exception):
                processed_results.append({
                    "status": "error",
                    "error": str(result)
                })
            else:
                processed_results.append(result)
        
        end_time = datetime.now(timezone.utc)
        duration = (end_time - start_time).total_seconds()
        
        # Calculate statistics
        successful = sum(1 for r in processed_results if r.get("status") == "success")
        failed = len(processed_results) - successful
        
        logger.info(f"Query batch processing completed: {successful} successful, {failed} failed, {duration:.2f}s")
        
        return {
            "total_queries": len(queries),
            "successful": successful,
            "failed": failed,
            "duration_seconds": duration,
            "results": processed_results
        }

