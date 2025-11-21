"""
Manual entry point for the weekly Ask-AI self-improvement pilot.

Usage:
    python scripts/run_self_improvement_pilot.py

The script collects recent Ask-AI query metrics, generates a recommendation
report using LangChain templating, and writes the result to
`implementation/analysis/self_improvement_pilot_report.md` for manual review.
"""

import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SERVICE_PACKAGE = PROJECT_ROOT / "services" / "ai-automation-service"
SERVICE_SRC = SERVICE_PACKAGE / "src"

sys.path.insert(0, str(SERVICE_PACKAGE))
sys.path.insert(0, str(SERVICE_SRC))

from src.database.models import get_db_session  # type: ignore  # pylint: disable=wrong-import-position
from src.langchain_integration.self_improvement import (  # type: ignore  # pylint: disable=wrong-import-position
    generate_prompt_tuning_report,
    write_report_to_markdown,
)


async def main() -> None:
    report = await generate_prompt_tuning_report(get_db_session)
    report["generated_at"] = datetime.now(timezone.utc).isoformat()

    output_path = Path(__file__).resolve().parent.parent / "implementation" / "analysis" / "self_improvement_pilot_report.md"
    write_report_to_markdown(report, output_path)
    print(f"[self-improvement] Report written to {output_path}")


if __name__ == "__main__":
    asyncio.run(main())


