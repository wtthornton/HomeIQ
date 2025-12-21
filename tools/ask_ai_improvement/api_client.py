"""
API client for Ask AI service.

Handles all HTTP interactions with the Ask AI API including:
- Health checks
- Query submission
- Clarification handling
- Suggestion approval
"""
import time
import httpx
from datetime import datetime
from typing import Any

from .config import BASE_URL, HEALTH_URL, MAX_CLARIFICATION_ROUNDS, API_KEY
from .terminal_output import TerminalOutput
from .clarification_handler import ClarificationHandler


class AskAIClient:
    """Client for interacting with Ask AI API"""
    
    def __init__(self, base_url: str = BASE_URL, health_url: str = HEALTH_URL, 
                 timeout: float = 300.0, api_key: str = API_KEY):
        self.base_url = base_url
        self.health_url = health_url
        self.timeout = timeout
        self.api_key = api_key
        self.client: httpx.AsyncClient | None = None
    
    async def __aenter__(self):
        """Async context manager entry"""
        headers = {}
        if self.api_key:
            headers["X-HomeIQ-API-Key"] = self.api_key
            headers["Authorization"] = f"Bearer {self.api_key}"
        self.client = httpx.AsyncClient(timeout=self.timeout, headers=headers)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.client:
            await self.client.aclose()
    
    async def check_health(self) -> bool:
        """Check if API is healthy"""
        TerminalOutput.print_info("Checking service health...")
        try:
            response = await self.client.get(self.health_url)
            if response.status_code == 200:
                TerminalOutput.print_success(f"Service is healthy (status: {response.status_code})")
                return True
            else:
                TerminalOutput.print_error(f"Service returned status {response.status_code}")
                return False
        except Exception as e:
            TerminalOutput.print_error(f"Health check failed: {e}")
            return False
    
    async def submit_query(self, query: str, user_id: str = "continuous_improvement") -> dict[str, Any]:
        """Submit query to Ask AI API"""
        TerminalOutput.print_info(f"Submitting query: {query[:80]}...")
        start_time = time.time()
        
        try:
            response = await self.client.post(
                f"{self.base_url}/query",
                json={
                    "query": query,
                    "user_id": user_id
                }
            )
            elapsed = time.time() - start_time
            
            if response.status_code not in [200, 201]:
                error_text = response.text
                TerminalOutput.print_error(f"Query failed (status: {response.status_code}, time: {elapsed:.2f}s)")
                try:
                    error_json = response.json()
                    error_detail = error_json.get('detail', error_text)
                    raise Exception(f"Query failed: {error_detail}")
                except (ValueError, KeyError):
                    raise Exception(f"Query failed with status {response.status_code}: {error_text}")
            
            result = response.json()
            query_id = result.get('query_id', 'unknown')
            clarification_needed = result.get('clarification_needed', False)
            suggestions_count = len(result.get('suggestions', []))
            
            TerminalOutput.print_success(f"Query submitted successfully (time: {elapsed:.2f}s)")
            TerminalOutput.print_info(f"  Query ID: {query_id}", indent=1)
            TerminalOutput.print_info(f"  Clarification needed: {clarification_needed}", indent=1)
            TerminalOutput.print_info(f"  Initial suggestions: {suggestions_count}", indent=1)
            
            return result
        except httpx.HTTPError as e:
            elapsed = time.time() - start_time
            TerminalOutput.print_error(f"Network error during query submission (time: {elapsed:.2f}s)")
            raise Exception(f"Network error during query submission: {str(e)}")
        except Exception as e:
            elapsed = time.time() - start_time
            # Re-raise if already formatted
            if "Query failed" in str(e) or "Network error" in str(e):
                raise
            raise Exception(f"Unexpected error during query submission: {str(e)}")
    
    async def handle_clarifications(
        self, 
        session_id: str, 
        initial_questions: list[dict[str, Any]],
        clarification_handler: ClarificationHandler | None = None
    ) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        """
        Handle clarification loop until complete.
        Returns (final_response, clarification_log)
        """
        clarification_log = []
        current_questions = initial_questions
        session_id_current = session_id
        max_rounds = MAX_CLARIFICATION_ROUNDS
        clarification_response = None
        
        while current_questions and len(clarification_log) < max_rounds:
            round_num = len(clarification_log) + 1
            TerminalOutput.print_info(f"Clarification Round {round_num}/{max_rounds}: {len(current_questions)} question(s)")
            
            # Show questions
            for i, q in enumerate(current_questions, 1):
                q_text = q.get('question_text', 'Unknown question')[:60]
                TerminalOutput.print_info(f"  Q{i}: {q_text}...", indent=1)
            
            # Generate answers
            TerminalOutput.print_info("Generating auto-answers...", indent=1)
            answers = []
            handler = clarification_handler or ClarificationHandler("")
            for q in current_questions:
                answer = handler.answer_question(q)
                answers.append(answer)
                answer_text = answer.get('answer_text', '')[:50]
                TerminalOutput.print_info(f"  A: {answer_text}...", indent=2)
            
            # Log Q&A
            qa_round = {
                'round': round_num,
                'questions': current_questions,
                'answers': answers,
                'timestamp': datetime.now().isoformat()
            }
            clarification_log.append(qa_round)
            
            # Submit answers
            TerminalOutput.print_info("Submitting answers to API...", indent=1)
            start_time = time.time()
            try:
                response = await self.client.post(
                    f"{self.base_url}/clarify",
                    json={
                        "session_id": session_id_current,
                        "answers": answers
                    }
                )
                elapsed = time.time() - start_time
                
                if response.status_code != 200:
                    error_text = response.text
                    TerminalOutput.print_error(f"Clarification failed (status: {response.status_code}, time: {elapsed:.2f}s)")
                    try:
                        error_json = response.json()
                        error_detail = error_json.get('detail', error_text)
                        raise Exception(f"Clarification failed: {error_detail}")
                    except (ValueError, KeyError):
                        raise Exception(f"Clarification failed with status {response.status_code}: {error_text}")
                
                clarification_response = response.json()
                TerminalOutput.print_success(f"Answers submitted (time: {elapsed:.2f}s)")
            except httpx.HTTPError as e:
                elapsed = time.time() - start_time
                TerminalOutput.print_error(f"Network error during clarification (time: {elapsed:.2f}s)")
                raise Exception(f"Network error during clarification: {str(e)}")
            
            # Check if complete
            if clarification_response.get('clarification_complete', False):
                confidence = clarification_response.get('confidence', 0.0)
                suggestions_count = len(clarification_response.get('suggestions', []))
                TerminalOutput.print_success(f"Clarification complete! (confidence: {confidence:.1%}, suggestions: {suggestions_count})")
                return clarification_response, clarification_log
            
            # Get next questions
            current_questions = clarification_response.get('questions', [])
            if not current_questions:
                # Check if we have suggestions even though clarification isn't marked complete
                suggestions = clarification_response.get('suggestions', [])
                if suggestions:
                    TerminalOutput.print_info(f"Found {len(suggestions)} suggestion(s) - proceeding despite incomplete clarification")
                    break
                else:
                    # Try fetching from query endpoint
                    try:
                        check_response = await self.client.get(f"{self.base_url}/query/{session_id_current}")
                        if check_response.status_code == 200:
                            check_data = check_response.json()
                            suggestions = check_data.get('suggestions', [])
                            if suggestions:
                                clarification_response = check_data
                                TerminalOutput.print_info(f"Retrieved {len(suggestions)} suggestion(s) from query endpoint")
                                break
                    except Exception as e:
                        TerminalOutput.print_warning(f"Could not check for suggestions: {e}")
                    
                    TerminalOutput.print_warning("No more questions but clarification not marked complete and no suggestions found")
                    break
        
        if len(clarification_log) >= max_rounds:
            raise Exception(f"Clarification exceeded maximum rounds ({max_rounds})")
        
        if not clarification_response:
            raise Exception("Clarification response is missing")
        
        return clarification_response, clarification_log
    
    async def approve_suggestion(self, query_id: str, suggestion_id: str) -> dict[str, Any]:
        """Approve a suggestion and create automation"""
        TerminalOutput.print_info(f"Approving suggestion {suggestion_id}...")
        TerminalOutput.print_info(f"  Query ID: {query_id}", indent=1)
        start_time = time.time()
        
        try:
            response = await self.client.post(
                f"{self.base_url}/query/{query_id}/suggestions/{suggestion_id}/approve",
                json={}
            )
            elapsed = time.time() - start_time
            
            if response.status_code not in [200, 201]:
                error_text = response.text
                TerminalOutput.print_error(f"Approval failed (status: {response.status_code}, time: {elapsed:.2f}s)")
                # Try to parse error message
                try:
                    error_json = response.json()
                    error_detail = error_json.get('detail', error_text)
                    raise Exception(f"Approval failed: {error_detail}")
                except (ValueError, KeyError):
                    raise Exception(f"Approval failed with status {response.status_code}: {error_text}")
            
            result = response.json()
            
            # Check for error status in response body (API may return 200 OK with error status)
            if result.get('status') == 'error':
                error_msg = result.get('message', 'Unknown error')
                error_details = result.get('error_details', {})
                error_type = error_details.get('type', 'unknown')
                error_detail_msg = error_details.get('message', error_msg)
                invalid_entities = error_details.get('invalid_entities', [])
                
                TerminalOutput.print_error(f"Approval failed (time: {elapsed:.2f}s)")
                TerminalOutput.print_error(f"  Error: {error_msg}", indent=1)
                TerminalOutput.print_error(f"  Type: {error_type}", indent=1)
                if invalid_entities:
                    TerminalOutput.print_error(f"  Invalid entities: {', '.join(invalid_entities)}", indent=1)
                
                raise Exception(f"Approval failed: {error_msg} (Type: {error_type}). Details: {error_detail_msg}")
            
            automation_id = result.get('automation_id', 'unknown')
            has_yaml = bool(result.get('automation_yaml'))
            
            TerminalOutput.print_success(f"Suggestion approved (time: {elapsed:.2f}s)")
            TerminalOutput.print_info(f"  Automation ID: {automation_id}", indent=1)
            TerminalOutput.print_info(f"  YAML generated: {has_yaml}", indent=1)
            
            return result
        except httpx.HTTPError as e:
            elapsed = time.time() - start_time
            TerminalOutput.print_error(f"Network error during approval (time: {elapsed:.2f}s)")
            raise Exception(f"Network error during approval: {str(e)}")
        except Exception as e:
            elapsed = time.time() - start_time
            # Re-raise if already formatted
            if "Approval failed" in str(e):
                raise
            raise Exception(f"Unexpected error during approval: {str(e)}")

