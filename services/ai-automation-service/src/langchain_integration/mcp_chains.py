"""
LangChain LCEL chains for MCP code execution pattern.
Replaces direct OpenAI calls with LangChain chains for better orchestration.
"""

from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.schema import StrOutputParser
from langchain.schema.runnable import RunnableLambda
from langchain.callbacks import get_openai_callback
import httpx
import logging
from typing import Dict, Any
import json
import re

logger = logging.getLogger(__name__)


class MCPCodeExecutionChain:
    """
    LangChain LCEL chain for MCP code execution pattern.

    Flow:
    1. User request → Code generation prompt
    2. LLM generates Python code
    3. Execute code in sandbox (calls MCP tools)
    4. Results → Interpretation prompt
    5. LLM interprets results → Final automation
    """

    def __init__(self, code_executor_url: str = "http://ai-code-executor:8030"):
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.7
        )
        self.code_executor_url = code_executor_url

        # Build LCEL chains
        self.code_generation_chain = self._build_code_generation_chain()
        self.interpretation_chain = self._build_interpretation_chain()

    def _build_code_generation_chain(self):
        """Build chain for generating Python code"""
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a Python code generator for home automation analysis.

Available MCP tools (import as modules):
- import data  # Data API tools
  - await data.get_devices() → Get all devices
  - await data.query_device_history(entity_id, start_time, end_time) → Get history
  - await data.search_events(entity_id, start_time, limit) → Search events

- import automation  # AI Automation tools
  - await automation.detect_patterns(start_time, end_time, pattern_types) → Detect patterns

- import device  # Device Intelligence tools
  - await device.get_device_capabilities(entity_id) → Get device capabilities

Rules:
1. Process data LOCALLY in code (filter, aggregate, analyze)
2. Print progress messages for user visibility
3. Return a SUMMARY dictionary (NOT full data)
4. Use async/await for all tool calls
5. Handle errors gracefully with try/except

Example:
```python
import data

try:
    devices = await data.get_devices()
    lights = [d for d in devices['devices'] if d['entity_id'].startswith('light.')]

    print(f"Found {{len(lights)}} lights out of {{devices['count']}} devices")

    # Return summary, not full data
    {{
        "total_devices": devices['count'],
        "lights_count": len(lights),
        "sample_light_ids": [l['entity_id'] for l in lights[:3]]
    }}
except Exception as e:
    print(f"Error: {{e}}")
    {{"error": str(e)}}
```"""),
            ("user", """Task: {description}

Context: {context}

Generate Python code to accomplish this task:""")
        ])

        return (
            prompt
            | self.llm
            | StrOutputParser()
            | RunnableLambda(self._extract_code_block)
        )

    def _build_interpretation_chain(self):
        """Build chain for interpreting execution results"""
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a Home Assistant automation expert.

Your task is to interpret code execution results and generate the appropriate YAML automation.

Format your response as valid Home Assistant YAML automation configuration."""),
            ("user", """Original request: {description}

Code execution output:
{stdout}

Summary result:
{result}

Generate the Home Assistant automation YAML:""")
        ])

        return (
            prompt
            | self.llm
            | StrOutputParser()
        )

    def _extract_code_block(self, text: str) -> str:
        """Extract Python code from markdown code blocks"""
        # Look for ```python ... ``` blocks
        matches = re.findall(r'```python\n(.*?)\n```', text, re.DOTALL)
        if matches:
            return matches[0].strip()

        # Look for ``` ... ``` blocks (no language specified)
        matches = re.findall(r'```\n(.*?)\n```', text, re.DOTALL)
        if matches:
            return matches[0].strip()

        # No code block, return as-is
        return text.strip()

    async def _execute_code(self, code: str) -> Dict[str, Any]:
        """Execute code in sandbox"""
        logger.info(f"Executing code ({len(code)} chars)")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.code_executor_url}/execute",
                json={"code": code},
                timeout=60.0
            )
            response.raise_for_status()
            return response.json()

    async def generate_automation(
        self,
        description: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate automation using LangChain + MCP code execution.

        Returns:
            {
                "automation_yaml": str,
                "code": str,
                "execution_result": dict,
                "token_usage": dict
            }
        """
        with get_openai_callback() as cb:
            # Step 1: Generate code
            logger.info(f"Step 1: Generating code for '{description}'")

            code = await self.code_generation_chain.ainvoke({
                "description": description,
                "context": json.dumps(context, indent=2)
            })

            logger.info(f"Generated code:\n{code}")
            code_gen_tokens = cb.total_tokens

            # Step 2: Execute code
            logger.info("Step 2: Executing code in sandbox")

            exec_result = await self._execute_code(code)

            if not exec_result['success']:
                error_msg = exec_result.get('error', 'Unknown error')
                logger.error(f"Code execution failed: {error_msg}")

                # Return error result
                return {
                    "automation_yaml": None,
                    "code": code,
                    "execution_result": exec_result,
                    "error": f"Code execution failed: {error_msg}",
                    "token_usage": {
                        "code_generation_tokens": code_gen_tokens,
                        "total_tokens": code_gen_tokens,
                        "prompt_tokens": cb.prompt_tokens,
                        "completion_tokens": cb.completion_tokens,
                        "total_cost": cb.total_cost
                    }
                }

            logger.info(f"Execution successful ({exec_result['execution_time']:.3f}s)")
            logger.info(f"Output:\n{exec_result['stdout']}")

            # Step 3: Interpret results
            logger.info("Step 3: Interpreting results")

            automation_yaml = await self.interpretation_chain.ainvoke({
                "description": description,
                "stdout": exec_result['stdout'],
                "result": json.dumps(exec_result['return_value'], indent=2)
            })

            interpretation_tokens = cb.total_tokens - code_gen_tokens

            logger.info(f"Generated automation:\n{automation_yaml}")

            return {
                "automation_yaml": automation_yaml,
                "code": code,
                "execution_result": exec_result,
                "token_usage": {
                    "code_generation_tokens": code_gen_tokens,
                    "interpretation_tokens": interpretation_tokens,
                    "total_tokens": cb.total_tokens,
                    "prompt_tokens": cb.prompt_tokens,
                    "completion_tokens": cb.completion_tokens,
                    "total_cost": cb.total_cost
                }
            }
