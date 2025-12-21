"""
Helper functions for production readiness pipeline.
"""
import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Tuple

from .config import PROJECT_ROOT

logger = logging.getLogger(__name__)


def run_command(cmd: list, cwd: Path = None, check: bool = False) -> Tuple[int, str, str]:
    """Run a command and return exit code, stdout, stderr."""
    logger.info(f"Running: {' '.join(cmd)}")
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd or PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=check
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed: {e}")
        return e.returncode, e.stdout, e.stderr


def check_docker_compose() -> bool:
    """Check if docker compose is available."""
    exit_code, _, _ = run_command(["docker", "compose", "version"], check=False)
    if exit_code == 0:
        return True
    
    exit_code, _, _ = run_command(["docker-compose", "--version"], check=False)
    return exit_code == 0


def get_docker_compose_cmd() -> str:
    """Get the docker compose command to use."""
    exit_code, _, _ = run_command(["docker", "compose", "version"], check=False)
    if exit_code == 0:
        return "docker compose"
    return "docker-compose"


def format_error_message(what: str, why: str, how_to_fix: str, impact: str = "OPTIONAL") -> str:
    """Format error message in What/Why/How to Fix format."""
    impact_icon = "🔴" if impact == "CRITICAL" else "🟡"
    return f"""
{impact_icon} {what}

**Why it failed:**
{why}

**How to fix:**
{how_to_fix}

**Impact:** {impact} - {'Blocks production deployment' if impact == 'CRITICAL' else 'Enhancement feature, not required'}
"""


def validate_model_quality(model_name: str, results: dict, allow_low_quality: bool = False) -> Tuple[bool, dict]:
    """Validate model quality against defined thresholds."""
    from .config import MODEL_QUALITY_THRESHOLDS
    
    if model_name not in MODEL_QUALITY_THRESHOLDS:
        return True, {'status': 'no_thresholds', 'message': 'No quality thresholds defined'}
    
    thresholds = MODEL_QUALITY_THRESHOLDS[model_name]
    validation_details = {
        'status': 'checking',
        'metrics_checked': [],
        'metrics_passed': [],
        'metrics_failed': [],
        'warnings': []
    }
    
    # Extract metrics based on model type
    metrics = {}
    if model_name == 'home_type':
        metrics = {
            'accuracy': results.get('accuracy'),
            'precision': results.get('precision'),
            'recall': results.get('recall'),
            'f1_score': results.get('f1_score')
        }
    elif model_name == 'device_intelligence':
        perf = results.get('model_performance', {})
        metrics = {
            'accuracy': perf.get('accuracy'),
            'precision': perf.get('precision'),
            'recall': perf.get('recall'),
            'f1_score': perf.get('f1_score')
        }
    else:
        metrics = {
            'accuracy': results.get('accuracy') or results.get('model_performance', {}).get('accuracy')
        }
    
    # Validate each metric against threshold
    all_passed = True
    for metric_name, threshold in thresholds.items():
        if metric_name not in metrics:
            validation_details['warnings'].append(f"{metric_name} not available in results")
            continue
        
        metric_value = metrics[metric_name]
        if metric_value is None:
            validation_details['warnings'].append(f"{metric_name} is None - cannot validate")
            continue
        
        validation_details['metrics_checked'].append({
            'metric': metric_name,
            'value': metric_value,
            'threshold': threshold,
            'passed': metric_value >= threshold
        })
        
        if metric_value >= threshold:
            validation_details['metrics_passed'].append(metric_name)
        else:
            validation_details['metrics_failed'].append({
                'metric': metric_name,
                'value': metric_value,
                'threshold': threshold,
                'gap': threshold - metric_value
            })
            all_passed = False
    
    # Determine final status
    if all_passed:
        validation_details['status'] = 'passed'
        validation_details['message'] = 'All quality thresholds met'
    else:
        validation_details['status'] = 'failed' if not allow_low_quality else 'warning'
        failed_metrics = ', '.join([f['metric'] for f in validation_details['metrics_failed']])
        validation_details['message'] = f"Quality thresholds not met: {failed_metrics}"
    
    return all_passed or allow_low_quality, validation_details

