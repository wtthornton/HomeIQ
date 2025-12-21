"""
Ask AI Continuous Improvement Tool

Main entry point for running continuous improvement cycles on the Ask AI service.
This script orchestrates multiple improvement cycles, testing various prompts
and measuring the quality of generated automations.

Usage:
    python tools/ask-ai-continuous-improvement.py
"""
import asyncio
import sys

from ask_ai_improvement.orchestrator import run_improvement_cycles
from ask_ai_improvement.terminal_output import TerminalOutput


async def main():
    """Main entry point"""
    try:
        await run_improvement_cycles()
    except KeyboardInterrupt:
        TerminalOutput.print_warning("\nInterrupted by user. Exiting...")
        sys.exit(1)
                except Exception as e:
        TerminalOutput.print_error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
