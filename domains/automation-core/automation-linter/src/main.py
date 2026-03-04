"""
FastAPI service wrapper for HA Automation Linter.
"""

import logging
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from homeiq_ha.ha_automation_lint.constants import (
    ENGINE_VERSION,
    MAX_YAML_SIZE_BYTES,
    RULESET_VERSION,
    FixMode,
)
from homeiq_ha.ha_automation_lint.engine import LintEngine
from homeiq_ha.ha_automation_lint.fixers.auto_fixer import AutoFixer
from homeiq_ha.ha_automation_lint.renderers.yaml_renderer import YAMLRenderer
from pydantic import BaseModel, Field

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(
    title="HomeIQ Automation Linter",
    description="Lint and auto-fix Home Assistant automation YAML",
    version=ENGINE_VERSION
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize engine components
lint_engine = LintEngine()
renderer = YAMLRenderer()


# Request/Response Models
class LintRequest(BaseModel):
    """Request model for lint endpoint."""
    yaml: str = Field(..., description="Automation YAML to lint")
    options: dict | None = Field(default_factory=dict, description="Optional lint options")


class LintResponse(BaseModel):
    """Response model for lint endpoint."""
    engine_version: str
    ruleset_version: str
    automations_detected: int
    findings: list[dict]
    summary: dict[str, int]


class FixRequest(BaseModel):
    """Request model for fix endpoint."""
    yaml: str = Field(..., description="Automation YAML to fix")
    fix_mode: str = Field(default=FixMode.SAFE, description="Fix mode: safe or none")


class FixResponse(BaseModel):
    """Response model for fix endpoint."""
    engine_version: str
    ruleset_version: str
    automations_detected: int
    findings: list[dict]
    summary: dict[str, int]
    fixed_yaml: str | None = None
    applied_fixes: list[str] = Field(default_factory=list)
    diff_summary: str | None = None


# Middleware for request size limit
@app.middleware("http")
async def limit_request_size(request: Request, call_next):
    """Middleware to enforce request size limits."""
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > MAX_YAML_SIZE_BYTES:
        return JSONResponse(
            status_code=413,
            content={"error": f"Request too large. Max size: {MAX_YAML_SIZE_BYTES} bytes"}
        )
    return await call_next(request)


# Endpoints
@app.get("/health")
async def health_check():
    """
    Health check endpoint.

    Returns service health status and version information.
    """
    return {
        "status": "healthy",
        "engine_version": ENGINE_VERSION,
        "ruleset_version": RULESET_VERSION,
        "timestamp": time.time()
    }


@app.get("/rules")
async def list_rules():
    """
    List all available lint rules.

    Returns metadata for all rules including ID, name, severity, and category.
    """
    rules = lint_engine.get_rules()
    return {
        "ruleset_version": RULESET_VERSION,
        "rules": rules
    }


@app.post("/lint", response_model=LintResponse)
async def lint_automation(request: LintRequest):
    """
    Lint automation YAML and return findings.

    Args:
        request: LintRequest with YAML content and options

    Returns:
        LintResponse with findings and summary

    Raises:
        HTTPException: If YAML is too large or linting fails
    """
    try:
        # Validate size
        if len(request.yaml.encode('utf-8')) > MAX_YAML_SIZE_BYTES:
            raise HTTPException(413, "YAML content too large")

        # Run linter
        strict = request.options.get("strict", False) if request.options else False
        logger.info(f"Linting automation YAML (strict={strict})")
        report = lint_engine.lint(request.yaml, strict=strict)

        # Convert findings to dicts
        findings_dicts = [
            {
                "rule_id": f.rule_id,
                "severity": f.severity,
                "message": f.message,
                "why_it_matters": f.why_it_matters,
                "path": f.path,
                "suggested_fix": {
                    "type": f.suggested_fix.type,
                    "summary": f.suggested_fix.summary
                } if f.suggested_fix else None
            }
            for f in report.findings
        ]

        logger.info(f"Lint complete: {report.automations_detected} automations, "
                   f"{report.errors_count} errors, {report.warnings_count} warnings, "
                   f"{report.info_count} info")

        return LintResponse(
            engine_version=report.engine_version,
            ruleset_version=report.ruleset_version,
            automations_detected=report.automations_detected,
            findings=findings_dicts,
            summary={
                "errors_count": report.errors_count,
                "warnings_count": report.warnings_count,
                "info_count": report.info_count
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Lint error: {e}", exc_info=True)
        raise HTTPException(500, f"Linting failed: {str(e)}") from e


@app.post("/fix", response_model=FixResponse)
async def fix_automation(request: FixRequest):
    """
    Lint and auto-fix automation YAML.

    Args:
        request: FixRequest with YAML content and fix mode

    Returns:
        FixResponse with findings, fixed YAML, and applied fixes

    Raises:
        HTTPException: If YAML is too large or fixing fails
    """
    try:
        # Validate size
        if len(request.yaml.encode('utf-8')) > MAX_YAML_SIZE_BYTES:
            raise HTTPException(413, "YAML content too large")

        # Run linter
        logger.info(f"Linting and fixing automation YAML (mode={request.fix_mode})")
        report = lint_engine.lint(request.yaml)

        # Apply fixes if requested
        fixed_yaml = None
        applied_fixes = []
        diff_summary = None

        if request.fix_mode != FixMode.NONE:
            # Parse to get IR
            from homeiq_ha.ha_automation_lint.parsers.yaml_parser import AutomationParser
            parser = AutomationParser()
            automations, _ = parser.parse(request.yaml)

            # Apply fixes
            fixer = AutoFixer(fix_mode=request.fix_mode)
            fixed_automations, applied_fixes = fixer.apply_fixes(automations, report.findings)

            # Render fixed YAML
            fixed_yaml = renderer.render(fixed_automations)
            diff_summary = f"Applied {len(applied_fixes)} fixes"

            logger.info(f"Applied {len(applied_fixes)} fixes: {applied_fixes}")

        # Convert findings to dicts
        findings_dicts = [
            {
                "rule_id": f.rule_id,
                "severity": f.severity,
                "message": f.message,
                "why_it_matters": f.why_it_matters,
                "path": f.path,
                "suggested_fix": {
                    "type": f.suggested_fix.type,
                    "summary": f.suggested_fix.summary
                } if f.suggested_fix else None
            }
            for f in report.findings
        ]

        return FixResponse(
            engine_version=report.engine_version,
            ruleset_version=report.ruleset_version,
            automations_detected=report.automations_detected,
            findings=findings_dicts,
            summary={
                "errors_count": report.errors_count,
                "warnings_count": report.warnings_count,
                "info_count": report.info_count
            },
            fixed_yaml=fixed_yaml,
            applied_fixes=applied_fixes,
            diff_summary=diff_summary
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Fix error: {e}", exc_info=True)
        raise HTTPException(500, f"Auto-fix failed: {str(e)}") from e


# Serve UI
ui_path = Path(__file__).parent.parent / "ui"
if ui_path.exists():
    app.mount("/ui", StaticFiles(directory=str(ui_path)), name="ui")

    @app.get("/")
    async def root():
        """Serve the UI homepage."""
        index_path = ui_path / "index.html"
        if index_path.exists():
            return FileResponse(str(index_path))
        return {"message": "HomeIQ Automation Linter API", "version": ENGINE_VERSION}
else:
    @app.get("/")
    async def root():
        """API root endpoint."""
        return {
            "message": "HomeIQ Automation Linter API",
            "version": ENGINE_VERSION,
            "docs": "/docs",
            "health": "/health"
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8020)  # nosec B104 - Docker container
