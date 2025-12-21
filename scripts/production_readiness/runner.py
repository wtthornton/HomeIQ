"""
Orchestration runner for production readiness pipeline.
Uses dispatch table pattern to execute steps.
"""
import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, Optional

from .config import AI_SERVICE_DIR, IMPLEMENTATION_DIR, TEST_RESULTS_DIR
from .helpers import format_error_message
from .build_deploy import build_system, deploy_system, run_smoke_tests
from .data_generation import generate_test_data
from .models import save_models
from .reporting import generate_report
from .training import train_all_models
from .validation import validate_dependencies

logger = logging.getLogger(__name__)


@dataclass
class PipelineConfig:
    """Configuration for pipeline execution."""
    skip_build: bool = False
    skip_deploy: bool = False
    skip_smoke: bool = False
    skip_generation: bool = False
    skip_training: bool = False
    quick: bool = False
    count: Optional[int] = None
    days: Optional[int] = None
    skip_validation: bool = False
    allow_low_quality: bool = False
    force_regenerate: bool = False
    output_dir: Optional[Path] = None
    dry_run: bool = False


@dataclass
class PipelineResults:
    """Results from pipeline execution."""
    build: bool = False
    deploy: bool = False
    smoke_tests: dict = None
    data_generation: bool = False
    training: dict = None
    model_save: dict = None
    
    def __post_init__(self):
        if self.smoke_tests is None:
            self.smoke_tests = {'success': False, 'results': {}}
        if self.training is None:
            self.training = {}
        if self.model_save is None:
            self.model_save = {'success': False, 'manifest': {}}


class PipelineRunner:
    """Orchestrates production readiness pipeline steps."""
    
    def __init__(self, config: PipelineConfig):
        self.config = config
        self.results = PipelineResults()
        self.output_dir = config.output_dir or IMPLEMENTATION_DIR
        
        # Dispatch table for step execution
        self.step_handlers: Dict[str, Callable] = {
            'validate': self._run_validate,
            'build': self._run_build,
            'deploy': self._run_deploy,
            'smoke_tests': self._run_smoke_tests,
            'generate_data': self._run_generate_data,
            'train_models': self._run_train_models,
            'save_models': self._run_save_models,
            'generate_report': self._run_generate_report,
        }
    
    async def run(self) -> int:
        """Run the complete pipeline."""
        start_time = datetime.now()
        logger.info("=" * 80)
        logger.info("HomeIQ Production Readiness Pipeline")
        logger.info(f"Started: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        if self.config.dry_run:
            logger.info("🔍 DRY RUN MODE - No actual changes will be made")
        logger.info("=" * 80)
        
        # Pre-flight validation
        if not await self.step_handlers['validate']():
            return 1
        
        # Execute steps in order
        steps = ['build', 'deploy', 'smoke_tests', 'generate_data', 'train_models', 'save_models', 'generate_report']
        
        for step_name in steps:
            if not await self.step_handlers[step_name]():
                if step_name in ['build', 'deploy']:
                    logger.error(f"{step_name.capitalize()} failed - stopping pipeline")
                    return 1
        
        # Summary
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        self._print_summary(duration)
        
        # Determine exit code
        critical_passed = self._check_critical_passed()
        return 0 if critical_passed else 1
    
    async def _run_validate(self) -> bool:
        """Run validation step."""
        if self.config.dry_run:
            logger.info("🔍 [DRY RUN] Would validate dependencies")
            return True
        
        validation_passed, missing_items = validate_dependencies(self.config.skip_validation)
        if not validation_passed:
            error_msg = format_error_message(
                what="Pre-flight validation failed",
                why=f"Missing {len(missing_items)} required dependency(ies)",
                how_to_fix="\n".join([f"  - {item}" for item in missing_items]) + "\n\nInstall missing dependencies and set required environment variables, then re-run the script.",
                impact="CRITICAL"
            )
            logger.error(error_msg)
            return False
        return True
    
    async def _run_build(self) -> bool:
        """Run build step."""
        if self.config.skip_build:
            logger.info("Skipping build step")
            self.results.build = True
            return True
        
        if self.config.dry_run:
            logger.info("🔍 [DRY RUN] Would build Docker images")
            self.results.build = True
            return True
        
        self.results.build = build_system()
        return self.results.build
    
    async def _run_deploy(self) -> bool:
        """Run deploy step."""
        if self.config.skip_deploy:
            logger.info("Skipping deployment step")
            self.results.deploy = True
            return True
        
        if self.config.dry_run:
            logger.info("🔍 [DRY RUN] Would deploy services")
            self.results.deploy = True
            return True
        
        self.results.deploy = deploy_system()
        return self.results.deploy
    
    async def _run_smoke_tests(self) -> bool:
        """Run smoke tests step."""
        if self.config.skip_smoke:
            logger.info("Skipping smoke tests")
            self.results.smoke_tests = {'success': True, 'results': {}}
            return True
        
        if self.config.dry_run:
            logger.info("🔍 [DRY RUN] Would run smoke tests")
            self.results.smoke_tests = {'success': True, 'results': {}}
            return True
        
        success, smoke_results = run_smoke_tests(TEST_RESULTS_DIR)
        self.results.smoke_tests = {'success': success, 'results': smoke_results}
        return True  # Don't fail pipeline on smoke test failures
    
    async def _run_generate_data(self) -> bool:
        """Run data generation step."""
        if self.config.skip_generation:
            logger.info("Skipping test data generation")
            self.results.data_generation = True
            return True
        
        if self.config.dry_run:
            logger.info("🔍 [DRY RUN] Would generate test data")
            self.results.data_generation = True
            return True
        
        # Determine count and days
        if self.config.count or self.config.days:
            count = self.config.count if self.config.count else (10 if self.config.quick else 100)
            days = self.config.days if self.config.days else (7 if self.config.quick else 90)
            self.results.data_generation = await generate_test_data(
                count=count, days=days, quick=False, force=self.config.force_regenerate
            )
        elif self.config.quick:
            self.results.data_generation = await generate_test_data(
                count=10, days=7, quick=True, force=self.config.force_regenerate
            )
        else:
            self.results.data_generation = await generate_test_data(
                count=100, days=90, quick=False, force=self.config.force_regenerate
            )
        return self.results.data_generation
    
    async def _run_train_models(self) -> bool:
        """Run model training step."""
        if self.config.skip_training or not self.results.data_generation:
            logger.info("Skipping model training")
            self.results.training = {}
            return True
        
        if self.config.dry_run:
            logger.info("🔍 [DRY RUN] Would train all models")
            self.results.training = {}
            return True
        
        synthetic_homes_dir = AI_SERVICE_DIR / "tests" / "datasets" / "synthetic_homes"
        self.results.training = await train_all_models(
            synthetic_homes_dir, allow_low_quality=self.config.allow_low_quality
        )
        return True  # Don't fail pipeline on optional model failures
    
    async def _run_save_models(self) -> bool:
        """Run save models step."""
        if self.config.dry_run:
            logger.info("🔍 [DRY RUN] Would save models")
            self.results.model_save = {'success': True, 'manifest': {}}
            return True
        
        success, manifest = save_models(TEST_RESULTS_DIR)
        self.results.model_save = {'success': success, 'manifest': manifest}
        return True
    
    async def _run_generate_report(self) -> bool:
        """Run report generation step."""
        if self.config.dry_run:
            logger.info("🔍 [DRY RUN] Would generate report")
            return True
        
        report_path = generate_report(
            self.results.build,
            self.results.deploy,
            self.results.smoke_tests['results'],
            self.results.data_generation,
            self.results.training,
            self.results.model_save['manifest'],
            self.output_dir
        )
        logger.info(f"Report: {report_path}")
        return True
    
    def _print_summary(self, duration: float) -> None:
        """Print pipeline summary."""
        logger.info("=" * 80)
        logger.info("PIPELINE SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Duration: {duration:.1f} seconds ({duration/60:.1f} minutes)")
        logger.info(f"Build: {'✅ PASSED' if self.results.build else '❌ FAILED'}")
        logger.info(f"Deploy: {'✅ PASSED' if self.results.deploy else '❌ FAILED'}")
        logger.info(f"Smoke Tests: {'✅ PASSED' if self.results.smoke_tests['success'] else '❌ FAILED'}")
        logger.info(f"Data Generation: {'✅ PASSED' if self.results.data_generation else '❌ FAILED'}")
        
        # Enhanced training status
        critical_training = [
            self.results.training.get('home_type', {}).get('success', False),
            self.results.training.get('device_intelligence', {}).get('success', False)
        ]
        optional_training = [
            self.results.training.get('gnn_synergy', {}).get('success', False),
            self.results.training.get('soft_prompt', {}).get('success', False)
        ]
        
        critical_all_passed = all(critical_training)
        optional_status = []
        if optional_training[0]:
            optional_status.append("GNN")
        if optional_training[1]:
            optional_status.append("Soft Prompt")
        
        if critical_all_passed:
            training_status = "✅ PASSED (critical)"
            if optional_status:
                training_status += f" | ✨ Optional: {', '.join(optional_status)}"
            elif not all(optional_training):
                training_status += " | ⚠️  Optional: Not configured"
        else:
            training_status = "❌ FAILED (critical)"
        
        logger.info(f"Training: {training_status}")
        logger.info(f"Model Save: {'✅ PASSED' if self.results.model_save['success'] else '❌ FAILED'}")
        logger.info("=" * 80)
    
    def _check_critical_passed(self) -> bool:
        """Check if all critical components passed."""
        return (
            self.results.build and
            self.results.deploy and
            self.results.smoke_tests['success'] and
            self.results.data_generation and
            self.results.training.get('home_type', {}).get('success', False) and
            self.results.training.get('device_intelligence', {}).get('success', False)
        )


async def run_pipeline(config: PipelineConfig) -> int:
    """Run the production readiness pipeline."""
    runner = PipelineRunner(config)
    return await runner.run()

