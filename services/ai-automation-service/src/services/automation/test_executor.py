"""
Automation Test Executor

Executes and validates automation tests using ActionExecutor.
Uses direct action execution instead of creating temporary automations.

Created: Phase 2 - Core Service Refactoring
Updated: Action Execution Engine Implementation
"""

import logging
import time
import asyncio
from typing import Dict, Optional, Any, List
from datetime import datetime
from ...clients.ha_client import HomeAssistantClient
from .action_parser import ActionParser
from .action_executor import ActionExecutor

logger = logging.getLogger(__name__)


class AutomationTestExecutor:
    """
    Executes automation tests before deployment.
    
    Uses ActionExecutor to execute actions directly without creating
    temporary automations. Captures entity states, executes actions,
    and validates expected state changes.
    """
    
    def __init__(
        self,
        ha_client: HomeAssistantClient,
        action_executor: Optional[ActionExecutor] = None
    ):
        """
        Initialize test executor.
        
        Args:
            ha_client: Home Assistant client for test execution
            action_executor: Optional ActionExecutor instance (will create if not provided)
        """
        self.ha_client = ha_client
        self.action_executor = action_executor
        self.action_parser = ActionParser()
        
        logger.info("AutomationTestExecutor initialized")
    
    async def execute_test(
        self,
        automation_yaml: str,
        expected_changes: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute automation test using ActionExecutor.
        
        Args:
            automation_yaml: Automation YAML to test
            expected_changes: Optional expected state changes
            context: Optional test context (query_id, suggestion_id, etc.)
        
        Returns:
            Test result dictionary with execution summary and state validation
        """
        start_time = time.time()
        
        try:
            # Parse actions from YAML
            logger.info("Parsing actions from YAML...")
            actions = self.action_parser.parse_actions_from_yaml(automation_yaml)
            
            if not actions:
                return {
                    "success": False,
                    "message": "No actions found in automation YAML",
                    "state_changes": {},
                    "errors": ["No actions to execute"]
                }
            
            logger.info(f"Parsed {len(actions)} actions from YAML")
            
            # Extract entity IDs from actions for state capture
            entity_ids = self._extract_entity_ids(actions)
            logger.info(f"Extracted {len(entity_ids)} entity IDs from actions")
            
            # Capture entity states before execution
            logger.info("Capturing entity states before execution...")
            before_states = await self._capture_entity_states(entity_ids)
            
            # Execute actions using ActionExecutor
            if not self.action_executor:
                # Create temporary executor if not provided
                from ...template_engine import TemplateEngine
                template_engine = TemplateEngine(ha_client=self.ha_client)
                executor = ActionExecutor(
                    ha_client=self.ha_client,
                    template_engine=template_engine
                )
                await executor.start()
                try:
                    execution_context = context or {}
                    summary = await executor.execute_actions(actions, execution_context)
                finally:
                    await executor.shutdown()
            else:
                execution_context = context or {}
                summary = await self.action_executor.execute_actions(actions, execution_context)
            
            # Wait a bit for state changes to propagate
            await asyncio.sleep(0.5)
            
            # Validate state changes
            logger.info("Validating state changes...")
            state_validation = await self._validate_state_changes(
                before_states,
                entity_ids,
                wait_timeout=5.0
            )
            
            # Calculate execution time
            execution_time_ms = (time.time() - start_time) * 1000
            
            # Build result
            success = summary.successful == summary.total_actions and state_validation.get('summary', {}).get('all_changed', False)
            
            result = {
                "success": success,
                "message": f"Executed {summary.total_actions} actions, {summary.successful} successful",
                "execution_summary": {
                    "total_actions": summary.total_actions,
                    "successful": summary.successful,
                    "failed": summary.failed,
                    "execution_time_ms": summary.total_time_ms
                },
                "state_changes": state_validation.get('results', {}),
                "state_validation": state_validation.get('summary', {}),
                "errors": summary.errors,
                "execution_time_ms": execution_time_ms
            }
            
            logger.info(f"Test execution complete: {summary.successful}/{summary.total_actions} actions successful")
            return result
            
        except Exception as e:
            logger.error(f"❌ Test execution failed: {e}", exc_info=True)
            return {
                "success": False,
                "message": f"Test execution failed: {str(e)}",
                "state_changes": {},
                "errors": [str(e)],
                "execution_time_ms": (time.time() - start_time) * 1000
            }
    
    def _extract_entity_ids(self, actions: List[Dict[str, Any]]) -> List[str]:
        """Extract entity IDs from actions"""
        entity_ids = []
        
        for action in actions:
            if action.get('type') == 'service_call':
                target = action.get('target', {})
                if isinstance(target, dict):
                    entity_id = target.get('entity_id')
                    if entity_id:
                        if isinstance(entity_id, list):
                            entity_ids.extend(entity_id)
                        else:
                            entity_ids.append(entity_id)
            elif action.get('type') == 'sequence':
                entity_ids.extend(self._extract_entity_ids(action.get('actions', [])))
            elif action.get('type') == 'parallel':
                entity_ids.extend(self._extract_entity_ids(action.get('actions', [])))
        
        # Remove duplicates
        return list(set(entity_ids))
    
    async def _capture_entity_states(
        self,
        entity_ids: List[str],
        timeout: float = 5.0
    ) -> Dict[str, Dict[str, Any]]:
        """Capture current state of entities"""
        states = {}
        
        for entity_id in entity_ids:
            try:
                state = await self.ha_client.get_entity_state(entity_id)
                if state:
                    states[entity_id] = state
            except Exception as e:
                logger.warning(f"Failed to capture state for {entity_id}: {e}")
                states[entity_id] = {'state': 'unknown', 'error': str(e)}
        
        return states
    
    async def _validate_state_changes(
        self,
        before_states: Dict[str, Dict[str, Any]],
        entity_ids: List[str],
        wait_timeout: float = 5.0,
        check_interval: float = 0.5
    ) -> Dict[str, Any]:
        """Validate that state changes occurred after execution"""
        validation_results = {}
        start_time = time.time()
        
        # Wait and poll for state changes
        while (time.time() - start_time) < wait_timeout:
            for entity_id in entity_ids:
                if entity_id not in validation_results or validation_results[entity_id].get('pending'):
                    try:
                        after_state = await self.ha_client.get_entity_state(entity_id)
                        before_state_data = before_states.get(entity_id, {})
                        before_state = before_state_data.get('state')
                        
                        if after_state:
                            after_state_value = after_state.get('state')
                            
                            # Check if state changed
                            if before_state != after_state_value:
                                validation_results[entity_id] = {
                                    'success': True,
                                    'before_state': before_state,
                                    'after_state': after_state_value,
                                    'changed': True,
                                    'timestamp': datetime.now().isoformat()
                                }
                            elif before_state == after_state_value:
                                # Check for attribute changes
                                before_attrs = before_state_data.get('attributes', {})
                                after_attrs = after_state.get('attributes', {})
                                
                                changed_attrs = {}
                                for key in ['brightness', 'color_name', 'rgb_color', 'temperature']:
                                    if before_attrs.get(key) != after_attrs.get(key):
                                        changed_attrs[key] = {
                                            'before': before_attrs.get(key),
                                            'after': after_attrs.get(key)
                                        }
                                
                                if changed_attrs:
                                    validation_results[entity_id] = {
                                        'success': True,
                                        'before_state': before_state,
                                        'after_state': after_state_value,
                                        'changed': True,
                                        'attribute_changes': changed_attrs,
                                        'timestamp': datetime.now().isoformat()
                                    }
                                elif entity_id not in validation_results:
                                    validation_results[entity_id] = {
                                        'success': False,
                                        'before_state': before_state,
                                        'after_state': after_state_value,
                                        'changed': False,
                                        'pending': True,
                                        'timestamp': datetime.now().isoformat()
                                    }
                    
                    except Exception as e:
                        logger.warning(f"Error validating state for {entity_id}: {e}")
                        if entity_id not in validation_results:
                            validation_results[entity_id] = {
                                'success': False,
                                'error': str(e),
                                'timestamp': datetime.now().isoformat()
                            }
            
            # Check if all entities have been validated
            all_validated = all(
                entity_id in validation_results and validation_results[entity_id].get('changed', False)
                for entity_id in entity_ids
            )
            
            if all_validated:
                break
            
            await asyncio.sleep(check_interval)
        
        # Final validation
        for entity_id in entity_ids:
            if entity_id not in validation_results:
                before_state_data = before_states.get(entity_id, {})
                validation_results[entity_id] = {
                    'success': False,
                    'before_state': before_state_data.get('state'),
                    'after_state': None,
                    'changed': False,
                    'timestamp': datetime.now().isoformat()
                }
        
        # Calculate summary
        all_changed = all(
            validation_results.get(entity_id, {}).get('changed', False)
            for entity_id in entity_ids
        )
        
        changed_count = sum(
            1 for entity_id in entity_ids
            if validation_results.get(entity_id, {}).get('changed', False)
        )
        
        return {
            'results': validation_results,
            'summary': {
                'all_changed': all_changed,
                'changed_count': changed_count,
                'total_count': len(entity_ids),
                'validation_time_ms': (time.time() - start_time) * 1000
            }
        }

