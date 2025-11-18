"""
Action Execution Models

Pydantic models for action execution engine.
"""

from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum


class ActionType(str, Enum):
    """Action type enumeration"""
    SERVICE_CALL = "service_call"
    DELAY = "delay"
    SEQUENCE = "sequence"
    PARALLEL = "parallel"
    REPEAT = "repeat"
    CHOOSE = "choose"


class ActionItem(BaseModel):
    """Action item model for execution queue"""
    
    action: Dict[str, Any] = Field(..., description="Parsed action from YAML")
    context: Dict[str, Any] = Field(default_factory=dict, description="Test context (query_id, suggestion_id, etc.)")
    retry_on_failure: bool = Field(default=True, description="Whether to retry on failure")
    attempts: int = Field(default=0, description="Number of execution attempts")
    queued_at: datetime = Field(default_factory=datetime.now, description="When action was queued")
    execution_id: Optional[str] = Field(default=None, description="Unique execution ID for tracking")
    parent_action_id: Optional[str] = Field(default=None, description="Parent action ID for nested actions")
    
    class Config:
        arbitrary_types_allowed = True


class ActionExecutionResult(BaseModel):
    """Result of action execution"""
    
    success: bool = Field(..., description="Whether execution succeeded")
    action_id: Optional[str] = Field(default=None, description="Action identifier")
    execution_time_ms: float = Field(default=0.0, description="Execution time in milliseconds")
    error: Optional[str] = Field(default=None, description="Error message if failed")
    status_code: Optional[int] = Field(default=None, description="HTTP status code if applicable")
    response_data: Optional[Dict[str, Any]] = Field(default=None, description="Response data from service call")
    attempts: int = Field(default=1, description="Number of attempts made")
    
    class Config:
        arbitrary_types_allowed = True


class ActionExecutionSummary(BaseModel):
    """Summary of action execution batch"""
    
    total_actions: int = Field(..., description="Total number of actions")
    successful: int = Field(default=0, description="Number of successful actions")
    failed: int = Field(default=0, description="Number of failed actions")
    total_time_ms: float = Field(default=0.0, description="Total execution time in milliseconds")
    results: List[ActionExecutionResult] = Field(default_factory=list, description="Individual action results")
    errors: List[str] = Field(default_factory=list, description="Error messages")
    
    class Config:
        arbitrary_types_allowed = True

