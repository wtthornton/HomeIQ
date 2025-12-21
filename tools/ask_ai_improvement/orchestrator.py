"""
Orchestration logic for Ask AI continuous improvement cycles.

Handles:
- Main improvement cycle loop
- Workflow execution with retry logic
- Cleanup of previous automations
- Service deployment
"""
import asyncio
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any
from dataclasses import asdict

import aiohttp
import httpx

from .config import (
    MAX_CYCLES,
    MAX_RETRIES,
    RETRY_INITIAL_DELAY,
    RETRY_BACKOFF_MULTIPLIER,
    DEPLOYMENT_WAIT_TIME,
    CYCLE_WAIT_TIME,
    HEALTH_CHECK_RETRIES,
    HEALTH_CHECK_INTERVAL,
    HEALTH_URL,
    API_KEY,
    HA_API_TIMEOUT,
    SCORE_EXCELLENT_THRESHOLD,
    SCORE_WARNING_THRESHOLD,
    YAML_VALIDITY_THRESHOLD,
    OUTPUT_DIR,
)
from .api_client import AskAIClient
from .evaluator import Scorer
from .reporter import Reporter
from .clarification_handler import ClarificationHandler
from .models import PromptResult, CycleResult
from .prompts import TARGET_PROMPTS
from .terminal_output import TerminalOutput


class WorkflowOrchestrator:
    """Orchestrates the full workflow execution with retry logic"""
    
    def __init__(self, api_client: AskAIClient, scorer: Scorer):
        self.api_client = api_client
        self.scorer = scorer
    
    async def run_full_workflow(
        self,
        query: str,
        prompt_id: str,
        prompt_name: str,
        prompt_text: str,
        complexity: str
    ) -> tuple[PromptResult, dict[str, Any]]:
        """
        Run complete workflow: query → clarifications → approve → score
        Returns (result, workflow_data) where workflow_data contains all responses
        """
        result = PromptResult(
            prompt_id=prompt_id,
            prompt_name=prompt_name,
            prompt_text=prompt_text,
            complexity=complexity
        )
        workflow_data = {
            'query_response': None,
            'clarification_response': None,
            'approval_response': None,
            'selected_suggestion': None
        }
        
        try:
            workflow_start = time.time()
            
            # Step 1: Submit query
            TerminalOutput.print_step(1, 4, f"Submit Query - {prompt_name}")
            query_response = await self.api_client.submit_query(query)
            workflow_data['query_response'] = query_response
            result.query_id = query_response.get('query_id')
            
            # Track which query_id to use for approval (may change after clarification)
            approval_query_id = result.query_id
            session_id = None
            
            # Check if clarification needed
            if query_response.get('clarification_needed', False):
                session_id = query_response.get('clarification_session_id')
                questions = query_response.get('questions', [])
                
                if questions:
                    # Step 2: Handle clarifications
                    TerminalOutput.print_step(2, 4, "Handle Clarifications")
                    clarification_handler = ClarificationHandler(query)
                    clarification_response, clarification_log = await self.api_client.handle_clarifications(
                        session_id, questions, clarification_handler
                    )
                    workflow_data['clarification_response'] = clarification_response
                    result.clarification_log = clarification_log
                    result.clarification_rounds = len(clarification_log)
                    
                    # After clarification, suggestions may be in a different query record
                    suggestions = clarification_response.get('suggestions', [])
                    
                    # If no suggestions in response, try fetching from query endpoint
                    if not suggestions:
                        try:
                            check_response = await self.api_client.client.get(
                                f"{self.api_client.base_url}/query/{session_id}"
                            )
                            if check_response.status_code == 200:
                                check_data = check_response.json()
                                suggestions = check_data.get('suggestions', [])
                                if suggestions:
                                    clarification_response = check_data
                                    TerminalOutput.print_info(
                                        f"Retrieved {len(suggestions)} suggestion(s) from query endpoint"
                                    )
                        except Exception as e:
                            TerminalOutput.print_warning(
                                f"Could not fetch suggestions from query endpoint: {e}"
                            )
                    
                    if clarification_response.get('clarification_complete', False) or suggestions:
                        # Use session_id as query_id for approval
                        approval_query_id = session_id
                        TerminalOutput.print_info(
                            f"Using clarification_query_id ({session_id}) for approval"
                        )
                else:
                    suggestions = query_response.get('suggestions', [])
            else:
                TerminalOutput.print_info("No clarification needed - proceeding with direct suggestions")
                suggestions = query_response.get('suggestions', [])
            
            if not suggestions:
                raise Exception("No suggestions generated")
            
            # Step 3: Select best suggestion
            TerminalOutput.print_step(3, 4, "Select and Approve Suggestion")
            # Filter out suggestions without suggestion_id
            valid_suggestions = [s for s in suggestions if s.get('suggestion_id')]
            if not valid_suggestions:
                raise Exception("No valid suggestions with suggestion_id found")
            
            TerminalOutput.print_info(f"Evaluating {len(valid_suggestions)} suggestion(s)...")
            best_suggestion = max(valid_suggestions, key=lambda s: s.get('confidence', 0.0))
            workflow_data['selected_suggestion'] = best_suggestion
            result.suggestion_id = best_suggestion.get('suggestion_id')
            
            if not result.suggestion_id:
                raise Exception("Selected suggestion has no suggestion_id")
            
            confidence = best_suggestion.get('confidence', 0.0)
            title = best_suggestion.get('title', 'Untitled')[:50]
            TerminalOutput.print_success(
                f"Selected: {title}... (confidence: {confidence:.1%})"
            )
            
            # Approve suggestion (use correct query_id)
            try:
                approval_response = await self.api_client.approve_suggestion(
                    approval_query_id, result.suggestion_id
                )
            except Exception as e:
                # If approval fails with clarification_query_id, try original query_id as fallback
                if approval_query_id != result.query_id and "not found" in str(e).lower():
                    TerminalOutput.print_warning(
                        "Approval with clarification_query_id failed, trying original query_id"
                    )
                    approval_response = await self.api_client.approve_suggestion(
                        result.query_id, result.suggestion_id
                    )
                else:
                    raise
            workflow_data['approval_response'] = approval_response
            result.automation_id = approval_response.get('automation_id')
            result.automation_yaml = approval_response.get('automation_yaml')
            
            # Validate YAML before scoring
            if not result.automation_yaml:
                raise Exception("No automation YAML generated")
            
            # Step 4: Score results
            TerminalOutput.print_step(4, 4, "Score Results")
            TerminalOutput.print_info("Scoring automation correctness...")
            automation_score = self.scorer.score_automation_correctness(
                result.automation_yaml, query, prompt_id
            )
            TerminalOutput.print_info("Scoring YAML validity...")
            yaml_score = self.scorer.score_yaml_validity(result.automation_yaml)
            
            scores = self.scorer.calculate_total_score(
                automation_score=automation_score,
                yaml_score=yaml_score,
                clarification_count=result.clarification_rounds
            )
            
            result.automation_score = scores['automation_score']
            result.yaml_score = scores['yaml_score']
            result.total_score = scores['total_score']
            result.success = True
            
            workflow_elapsed = time.time() - workflow_start
            TerminalOutput.print_success(
                f"Workflow completed successfully (total time: {workflow_elapsed:.2f}s)"
            )
            TerminalOutput.print_info(f"  Total Score: {result.total_score:.2f}/100", indent=1)
            TerminalOutput.print_info(
                f"  Automation Score: {result.automation_score:.2f}/100", indent=1
            )
            TerminalOutput.print_info(f"  YAML Score: {result.yaml_score:.2f}/100", indent=1)
            TerminalOutput.print_info(
                f"  Clarification Rounds: {result.clarification_rounds}", indent=1
            )
            
        except Exception as e:
            # Store error for potential retry
            result.error = str(e)
            result.success = False
            TerminalOutput.print_error(f"Workflow failed: {result.error}")
        
        return result, workflow_data
    
    async def run_full_workflow_with_retry(
        self,
        query: str,
        prompt_id: str,
        prompt_name: str,
        prompt_text: str,
        complexity: str
    ) -> tuple[PromptResult, dict[str, Any]]:
        """
        Run workflow with retry logic for transient failures.
        Implements exponential backoff retry strategy.
        """
        retryable_errors = [
            "No suggestions generated",
            "Network error",
            "Service disconnected",
            "timeout",
            "Connection",
            "404",
            "502",
            "503",
            "504"
        ]
        
        last_error: Exception | None = None
        delay = RETRY_INITIAL_DELAY
        
        for attempt in range(MAX_RETRIES):
            try:
                result, workflow_data = await self.run_full_workflow(
                    query, prompt_id, prompt_name, prompt_text, complexity
                )
                
                # If successful, return immediately
                if result.success:
                    if attempt > 0:
                        TerminalOutput.print_success(
                            f"Workflow succeeded on retry attempt {attempt + 1}"
                        )
                    return result, workflow_data
                
                # Check if error is retryable
                error_str = result.error or ""
                is_retryable = any(err.lower() in error_str.lower() for err in retryable_errors)
                
                if not is_retryable or attempt == MAX_RETRIES - 1:
                    # Non-retryable error or last attempt
                    return result, workflow_data
                
                # Retryable error - wait and retry
                TerminalOutput.print_warning(
                    f"Retryable error detected (attempt {attempt + 1}/{MAX_RETRIES})"
                )
                TerminalOutput.print_info(f"  Waiting {delay:.1f}s before retry...", indent=1)
                await asyncio.sleep(delay)
                delay *= RETRY_BACKOFF_MULTIPLIER
                
            except Exception as e:
                last_error = e
                error_str = str(e)
                is_retryable = any(err.lower() in error_str.lower() for err in retryable_errors)
                
                if not is_retryable or attempt == MAX_RETRIES - 1:
                    # Create error result
                    result = PromptResult(
                        prompt_id=prompt_id,
                        prompt_name=prompt_name,
                        prompt_text=prompt_text,
                        complexity=complexity,
                        error=error_str,
                        success=False
                    )
                    return result, {}
                
                # Retryable exception - wait and retry
                TerminalOutput.print_warning(
                    f"Retryable exception (attempt {attempt + 1}/{MAX_RETRIES}): {error_str}"
                )
                TerminalOutput.print_info(f"  Waiting {delay:.1f}s before retry...", indent=1)
                await asyncio.sleep(delay)
                delay *= RETRY_BACKOFF_MULTIPLIER
        
        # All retries exhausted
        error_str = str(last_error) if last_error else "Unknown error after retries"
        result = PromptResult(
            prompt_id=prompt_id,
            prompt_name=prompt_name,
            prompt_text=prompt_text,
            complexity=complexity,
            error=f"Failed after {MAX_RETRIES} attempts: {error_str}",
            success=False
        )
        return result, {}


async def cleanup_previous_automations():
    """
    Clean up Home Assistant automations created by previous runs of this script.
    Deletes automations at the beginning of the script run.
    """
    # Load Home Assistant configuration
    ha_url = os.getenv("HA_HTTP_URL") or os.getenv("HOME_ASSISTANT_URL")
    ha_token = os.getenv("HA_TOKEN") or os.getenv("HOME_ASSISTANT_TOKEN")
    
    if not ha_url or not ha_token:
        TerminalOutput.print_warning(
            "Home Assistant URL or token not found. Skipping automation cleanup."
        )
        TerminalOutput.print_info(
            "  Set HA_HTTP_URL and HA_TOKEN environment variables to enable cleanup.",
            indent=1
        )
        return
    
    TerminalOutput.print_header("Cleaning Up Previous Automations")
    TerminalOutput.print_info(f"Connecting to Home Assistant at {ha_url}...")
    
    # Try to use HomeAssistantClient from the project
    ha_client: Any = None
    session: aiohttp.ClientSession | None = None
    delete_headers: dict[str, str] = {}
    use_project_client = False
    
    try:
        # Add the service source to path to import HomeAssistantClient
        service_path = Path(__file__).parent.parent.parent / "services" / "ai-automation-service" / "src"
        if str(service_path) not in sys.path:
            sys.path.insert(0, str(service_path))
        
        from clients.ha_client import HomeAssistantClient  # type: ignore[import-untyped]
        
        # Use the project's HomeAssistantClient
        ha_client = HomeAssistantClient(ha_url=ha_url, access_token=ha_token)
        TerminalOutput.print_info("Using project's HomeAssistantClient")
        use_project_client = True
        
        # Get all automations using the client
        session = await ha_client._get_session()
        delete_headers = ha_client.headers
        
        async with session.get(
            f"{ha_url}/api/states",
            timeout=aiohttp.ClientTimeout(total=HA_API_TIMEOUT)
        ) as resp:
            if resp.status != 200:
                TerminalOutput.print_error(f"Failed to get automations: HTTP {resp.status}")
                if not use_project_client and session and not session.closed:
                    await session.close()
                return
            states = await resp.json()
        
        # Filter for automation entities
        automations = [
            s for s in states
            if s.get('entity_id', '').startswith('automation.')
        ]
    
    except (ImportError, Exception) as e:
        # Fallback to direct API calls if import fails
        TerminalOutput.print_info(
            f"Using direct API calls (could not import HomeAssistantClient: {e})"
        )
        delete_headers = {
            "Authorization": f"Bearer {ha_token}",
            "Content-Type": "application/json"
        }
        session = aiohttp.ClientSession(headers=delete_headers)
        async with session.get(
            f"{ha_url}/api/states",
            timeout=aiohttp.ClientTimeout(total=HA_API_TIMEOUT)
        ) as resp:
            if resp.status != 200:
                TerminalOutput.print_error(f"Failed to get automations: HTTP {resp.status}")
                await session.close()
                return
            states = await resp.json()
        
        # Filter for automation entities
        automations = [
            s for s in states
            if s.get('entity_id', '').startswith('automation.')
        ]
    
    # Check if we have automations (common to both paths)
    if not automations:
        TerminalOutput.print_success("No automations found. Nothing to clean up.")
        if not use_project_client and session and not session.closed:
            await session.close()
        return
    
    TerminalOutput.print_info(f"Found {len(automations)} automation(s) in Home Assistant")
    
    try:
        # Identify automations created by this script
        script_automations = []
        for auto in automations:
            entity_id = auto.get('entity_id', '')
            # Match pattern: automation.name_with_underscores_timestamp_hash
            if re.search(r'automation\.[a-z0-9_]+_\d{10,}_[a-z0-9]+$', entity_id, re.IGNORECASE):
                script_automations.append(auto)
            # Also match simpler patterns that might be from our prompts
            elif any(keyword in entity_id.lower() for keyword in [
                'wled', 'office', 'kitchen', 'living_room', 'bedroom',
                'hallway', 'motion', 'door', 'arrive', 'home'
            ]) and re.search(r'_\d+_[a-z0-9]+$', entity_id, re.IGNORECASE):
                script_automations.append(auto)
        
        if not script_automations:
            TerminalOutput.print_info(
                "No automations matching script pattern found. Skipping cleanup."
            )
            return
        
        TerminalOutput.print_info(
            f"Found {len(script_automations)} automation(s) likely created by this script"
        )
        
        # Delete each automation using the 'id' from attributes
        deleted = 0
        failed = 0
        
        for auto in script_automations:
            entity_id = auto.get('entity_id')
            attrs = auto.get('attributes', {})
            friendly_name = attrs.get('friendly_name', entity_id)
            auto_id = attrs.get('id')  # Use ID from attributes, not entity_id!
            
            if not auto_id:
                TerminalOutput.print_warning(
                    f"Skipping {entity_id}: No ID found in attributes", indent=1
                )
                failed += 1
                continue
            
            try:
                # Use correct endpoint: DELETE /api/config/automation/config/{id-from-attributes}
                async with session.delete(
                    f"{ha_url}/api/config/automation/config/{auto_id}",
                    headers=delete_headers,
                    timeout=aiohttp.ClientTimeout(total=HA_API_TIMEOUT)
                ) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        if result.get('result') == 'ok':
                            deleted += 1
                            TerminalOutput.print_success(
                                f"Deleted: {entity_id} ({friendly_name})", indent=1
                            )
                        else:
                            failed += 1
                            TerminalOutput.print_error(
                                f"Failed: {entity_id} - Unexpected response", indent=1
                            )
                    else:
                        failed += 1
                        text = await resp.text()
                        TerminalOutput.print_error(
                            f"Failed: {entity_id} - HTTP {resp.status}: {text[:100]}",
                            indent=1
                        )
            except Exception as e:
                failed += 1
                TerminalOutput.print_error(f"Failed: {entity_id} - {str(e)}", indent=1)
        
        TerminalOutput.print_info(f"Cleanup complete: {deleted} deleted, {failed} failed")
    
    except aiohttp.ClientError as e:
        TerminalOutput.print_error(f"Network error during cleanup: {e}")
    except Exception as e:
        TerminalOutput.print_error(f"Error during cleanup: {e}")
    finally:
        # Cleanup: Close session if we created it directly
        if not use_project_client and session and not session.closed:
            await session.close()
        elif use_project_client and ha_client and hasattr(ha_client, 'close'):
            await ha_client.close()


async def deploy_service() -> bool:
    """Rebuild and restart the service using async subprocess"""
    TerminalOutput.print_info("Deploying service...")
    try:
        # Build
        TerminalOutput.print_info("Building service...")
        build_process = await asyncio.create_subprocess_exec(
            "docker-compose", "build", "ai-automation-service",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        try:
            stdout, stderr = await asyncio.wait_for(
                build_process.communicate(),
                timeout=600.0
            )
        except asyncio.TimeoutError:
            build_process.kill()
            await build_process.wait()
            TerminalOutput.print_error("Build timed out after 600 seconds")
            return False
        
        if build_process.returncode != 0:
            error_msg = stderr.decode() if stderr else "Unknown error"
            TerminalOutput.print_error(f"Build failed: {error_msg}")
            return False
        
        # Restart
        TerminalOutput.print_info("Restarting service...")
        restart_process = await asyncio.create_subprocess_exec(
            "docker-compose", "restart", "ai-automation-service",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        try:
            stdout, stderr = await asyncio.wait_for(
                restart_process.communicate(),
                timeout=120.0
            )
        except asyncio.TimeoutError:
            restart_process.kill()
            await restart_process.wait()
            TerminalOutput.print_error("Restart timed out after 120 seconds")
            return False
        
        if restart_process.returncode != 0:
            error_msg = stderr.decode() if stderr else "Unknown error"
            TerminalOutput.print_error(f"Restart failed: {error_msg}")
            return False
        
        # Wait for health check
        TerminalOutput.print_info("Waiting for service to be healthy...")
        headers = {}
        if API_KEY:
            headers["X-HomeIQ-API-Key"] = API_KEY
            headers["Authorization"] = f"Bearer {API_KEY}"
        for i in range(HEALTH_CHECK_RETRIES):
            await asyncio.sleep(HEALTH_CHECK_INTERVAL)
            async with httpx.AsyncClient(timeout=5.0, headers=headers) as client:
                try:
                    response = await client.get(HEALTH_URL)
                    if response.status_code == 200:
                        TerminalOutput.print_success("Service is healthy!")
                        return True
                except (httpx.HTTPError, httpx.TimeoutException):
                    pass
            if i % 5 == 0:
                TerminalOutput.print_info(f"Still waiting... ({i}/{HEALTH_CHECK_RETRIES})")
        
        TerminalOutput.print_error(
            f"Service did not become healthy in time (checked {HEALTH_CHECK_RETRIES} times)"
        )
        return False
        
    except Exception as e:
        TerminalOutput.print_error(f"Deployment failed: {e}")
        return False


async def run_improvement_cycles():
    """Main orchestration loop for improvement cycles"""
    TerminalOutput.print_header("Ask AI Continuous Improvement Process")
    
    # Clean up previous automations at the beginning
    await cleanup_previous_automations()
    
    TerminalOutput.print_info(f"Number of Prompts: {len(TARGET_PROMPTS)}")
    for i, prompt_info in enumerate(TARGET_PROMPTS, 1):
        TerminalOutput.print_info(
            f"  {i}. {prompt_info['name']} ({prompt_info['complexity']})", indent=1
        )
    TerminalOutput.print_info(f"Max Cycles: {MAX_CYCLES}")
    TerminalOutput.print_info(f"Output Directory: {OUTPUT_DIR}")
    
    reporter = Reporter(OUTPUT_DIR)
    overall_start = time.time()
    
    for cycle_num in range(1, MAX_CYCLES + 1):
        cycle_start = time.time()
        TerminalOutput.print_header(f"Cycle {cycle_num}/{MAX_CYCLES}", "=")
        
        cycle_result = CycleResult(cycle_number=cycle_num)
        
        async with AskAIClient() as api_client:
            # Check health
            if not await api_client.check_health():
                TerminalOutput.print_error("Service is not healthy. Please start the service first.")
                sys.exit(1)
            
            # Create orchestrator and scorer
            scorer = Scorer()
            orchestrator = WorkflowOrchestrator(api_client, scorer)
            
            # Run all prompts
            for prompt_idx, prompt_info in enumerate(TARGET_PROMPTS, 1):
                prompt_id = prompt_info['id']
                prompt_name = prompt_info['name']
                prompt_text = prompt_info['prompt']
                complexity = prompt_info['complexity']
                
                TerminalOutput.print_header(
                    f"Prompt {prompt_idx}/{len(TARGET_PROMPTS)}: {prompt_name} ({complexity})", "-"
                )
                TerminalOutput.print_info(f"Prompt: {prompt_text[:100]}...")
                
                try:
                    # Run workflow for this prompt with retry logic
                    prompt_result, workflow_data = await orchestrator.run_full_workflow_with_retry(
                        prompt_text, prompt_id, prompt_name, prompt_text, complexity
                    )
                    cycle_result.prompt_results.append(prompt_result)
                    
                    # Save individual prompt data
                    reporter.save_prompt_data(cycle_num, prompt_id, prompt_result, workflow_data)
                    
                    if prompt_result.success:
                        TerminalOutput.print_success(
                            f"Prompt {prompt_idx} completed: {prompt_result.total_score:.2f}/100"
                        )
                    else:
                        TerminalOutput.print_error(
                            f"Prompt {prompt_idx} failed: {prompt_result.error}"
                        )
                    
                except Exception as e:
                    TerminalOutput.print_error(f"Prompt {prompt_idx} exception: {e}")
                    error_result = PromptResult(
                        prompt_id=prompt_id,
                        prompt_name=prompt_name,
                        prompt_text=prompt_text,
                        complexity=complexity,
                        error=str(e),
                        success=False
                    )
                    cycle_result.prompt_results.append(error_result)
            
            # Calculate overall cycle score
            cycle_result.overall_score = cycle_result.calculate_overall_score()
            cycle_result.all_successful = cycle_result.all_prompts_successful()
            
            reporter.cycles.append(cycle_result)
            
            # Save cycle data
            TerminalOutput.print_info("Saving cycle data...")
            reporter.save_cycle_data(cycle_num, cycle_result, {})
            cycle_elapsed = time.time() - cycle_start
            TerminalOutput.print_success(
                f"Cycle {cycle_num} data saved (cycle time: {cycle_elapsed:.2f}s)"
            )
            TerminalOutput.print_info(
                f"  Overall Score: {cycle_result.overall_score:.2f}/100", indent=1
            )
            TerminalOutput.print_info(
                f"  Successful Prompts: {sum(1 for r in cycle_result.prompt_results if r.success)}/{len(cycle_result.prompt_results)}",
                indent=1
            )
            
            # Check if all prompts successful and at 100%
            if not cycle_result.all_successful:
                failed_prompts = [r for r in cycle_result.prompt_results if not r.success]
                TerminalOutput.print_warning(
                    f"Cycle {cycle_num} has {len(failed_prompts)} failed prompt(s)"
                )
                for failed in failed_prompts:
                    TerminalOutput.print_error(
                        f"  - {failed.prompt_name}: {failed.error}", indent=1
                    )
                
                # Stop if critical errors
                all_yaml_failed = all(
                    r.yaml_score < YAML_VALIDITY_THRESHOLD
                    for r in failed_prompts
                    if r.yaml_score > 0
                )
                if all_yaml_failed or len(failed_prompts) == len(cycle_result.prompt_results):
                    TerminalOutput.print_warning("Stopping for manual review and fixes.")
                    break
            
            # Check if all successful prompts have 100% scores
            successful_prompts = [
                r for r in cycle_result.prompt_results if r.success
            ]
            all_at_100 = all(
                r.total_score >= 100.0 for r in successful_prompts
            ) if successful_prompts else False
            
            if cycle_result.all_successful and all_at_100:
                TerminalOutput.print_success("🎉 ALL PROMPTS ACHIEVED 100% ACCURACY!")
                TerminalOutput.print_success(
                    f"Cycle {cycle_num}: All {len(cycle_result.prompt_results)} prompts successful with 100% scores"
                )
                break
            elif successful_prompts:
                not_100 = [r for r in successful_prompts if r.total_score < 100.0]
                if not_100:
                    TerminalOutput.print_info(
                        f"Cycle {cycle_num}: {len(not_100)} prompt(s) below 100% (continuing to improve...)"
                    )
                    for r in not_100:
                        TerminalOutput.print_info(
                            f"  - {r.prompt_name}: {r.total_score:.2f}/100", indent=1
                        )
            
            # Analyze results
            TerminalOutput.print_info("Analyzing results...")
            analysis_result = next(
                (r for r in cycle_result.prompt_results if r.success),
                cycle_result.prompt_results[0] if cycle_result.prompt_results else None
            )
            analysis = None
            if analysis_result:
                analysis = reporter.analyze_cycle(cycle_num, analysis_result, {})
                
                if analysis['issues']:
                    TerminalOutput.print_warning(f"Found {len(analysis['issues'])} issue(s)")
                    for issue in analysis['issues']:
                        TerminalOutput.print_info(f"  - {issue}", indent=1)
                
                # Create improvement plan
                if analysis['improvement_areas'] or cycle_result.overall_score < SCORE_EXCELLENT_THRESHOLD:
                    cycle_dir = OUTPUT_DIR / f"cycle-{cycle_num}"
                    plan_path = cycle_dir / "IMPROVEMENT_PLAN.md"
                    plan = reporter.create_improvement_plan(cycle_num, analysis)
                    with open(plan_path, 'w', encoding='utf-8') as f:
                        f.write(plan)
                    TerminalOutput.print_info(f"Improvement plan saved to {plan_path}")
            
            # Check scores
            if cycle_result.overall_score < SCORE_WARNING_THRESHOLD:
                TerminalOutput.print_warning(
                    f"Cycle {cycle_num} overall score is below threshold: {cycle_result.overall_score:.2f}"
                )
            elif cycle_result.overall_score >= SCORE_EXCELLENT_THRESHOLD and cycle_result.all_successful:
                TerminalOutput.print_success(
                    f"Cycle {cycle_num} score is excellent: {cycle_result.overall_score:.2f} (all prompts successful)"
                )
            
            # If not last cycle, prepare for next iteration
            if cycle_num < MAX_CYCLES:
                TerminalOutput.print_info("\nPreparing for next cycle...")
                
                # If improvements needed, deploy updated service
                if analysis and analysis.get('improvement_areas', []):
                    TerminalOutput.print_info("Improvements identified. Deploying updated service...")
                    deploy_success = await deploy_service()
                    if not deploy_success:
                        TerminalOutput.print_error("Deployment failed. Stopping.")
                        break
                    TerminalOutput.print_success("Service deployed successfully. Waiting before next cycle...")
                    await asyncio.sleep(DEPLOYMENT_WAIT_TIME)
                else:
                    TerminalOutput.print_info("No improvements needed. Continuing to next cycle...")
                    await asyncio.sleep(CYCLE_WAIT_TIME)
    
    # Generate summary
    overall_elapsed = time.time() - overall_start
    TerminalOutput.print_header("Generating Summary")
    summary = reporter.generate_summary()
    summary_path = OUTPUT_DIR / "SUMMARY.md"
    with open(summary_path, 'w', encoding='utf-8') as f:
        f.write(summary)
    
    TerminalOutput.print_success(f"Summary saved to {summary_path}")
    TerminalOutput.print_info(f"Total execution time: {overall_elapsed:.2f}s")

