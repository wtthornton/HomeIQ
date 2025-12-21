"""
Report generation for production readiness pipeline.
"""
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


def generate_report(
    build_status: bool,
    deploy_status: bool,
    smoke_results: dict,
    data_generation_status: bool,
    training_results: dict,
    model_manifest: dict,
    output_dir: Path
) -> Path:
    """Generate comprehensive production readiness report."""
    logger.info("=" * 80)
    logger.info("STEP 7: Generating Production Readiness Report")
    logger.info("=" * 80)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = output_dir / f"production_readiness_report_{timestamp}.md"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Calculate overall status
    critical_passed = (
        build_status and
        deploy_status and
        smoke_results.get('overall_status') == 'pass' and
        data_generation_status and
        training_results.get('home_type', {}).get('success', False) and
        training_results.get('device_intelligence', {}).get('success', False)
    )
    
    # Check optional components separately
    optional_status = {
        'gnn_synergy': training_results.get('gnn_synergy', {}).get('success', False),
        'soft_prompt': training_results.get('soft_prompt', {}).get('success', False)
    }
    optional_passed = [name for name, status in optional_status.items() if status]
    optional_failed = [name for name, status in optional_status.items() if not status]
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("# Production Readiness Report\n\n")
        f.write(f"**Generated:** {datetime.now().isoformat()}\n\n")
        f.write("---\n\n")
        
        # Overall Status
        f.write("## Overall Status\n\n")
        if critical_passed:
            f.write("✅ **PRODUCTION READY** (Critical components passed)\n\n")
            if optional_failed:
                f.write(f"⚠️  **Optional Components:** {', '.join([name.replace('_', ' ').title() for name in optional_failed])} not configured\n\n")
            if optional_passed:
                f.write(f"✨ **Optional Enhancements:** {', '.join([name.replace('_', ' ').title() for name in optional_passed])} available\n\n")
        else:
            f.write("❌ **NOT PRODUCTION READY** (Critical components failed)\n\n")
        f.write("---\n\n")
        
        # Build Status
        f.write("## 1. Build Status\n\n")
        f.write(f"- **Status:** {'✅ PASSED' if build_status else '❌ FAILED'}\n\n")
        f.write("---\n\n")
        
        # Deployment Status
        f.write("## 2. Deployment Status\n\n")
        f.write(f"- **Status:** {'✅ PASSED' if deploy_status else '❌ FAILED'}\n\n")
        f.write("---\n\n")
        
        # Smoke Tests
        f.write("## 3. Smoke Test Results\n\n")
        if smoke_results:
            f.write(f"- **Overall Status:** {smoke_results.get('overall_status', 'unknown').upper()}\n")
            f.write(f"- **Total Tests:** {smoke_results.get('total_tests', 0)}\n")
            f.write(f"- **Passed:** {smoke_results.get('passed', 0)}\n")
            f.write(f"- **Failed:** {smoke_results.get('failed', 0)}\n")
            f.write(f"- **Critical Passed:** {smoke_results.get('critical_passed', 0)}\n")
            f.write(f"- **Critical Failed:** {smoke_results.get('critical_failed', 0)}\n\n")
            
            f.write("### Service Details\n\n")
            for service in smoke_results.get('services', []):
                status_icon = "✅" if service.get('passed') else "❌"
                f.write(f"- {status_icon} **{service.get('service')}**: {service.get('status')}\n")
                if service.get('error'):
                    f.write(f"  - Error: {service.get('error')}\n")
        else:
            f.write("- **Status:** Not run\n")
        f.write("\n---\n\n")
        
        # Data Generation
        f.write("## 4. Test Data Generation\n\n")
        f.write(f"- **Status:** {'✅ PASSED' if data_generation_status else '❌ FAILED'}\n\n")
        f.write("---\n\n")
        
        # Training Results
        f.write("## 5. Model Training Results\n\n")
        
        # Critical Models Section
        f.write("### Critical Models (Required for Production)\n\n")
        critical_models = ['home_type', 'device_intelligence']
        for model_name in critical_models:
            if model_name in training_results:
                result = training_results[model_name]
                status_icon = "✅" if result.get('success') else "❌"
                f.write(f"#### {model_name.replace('_', ' ').title()}\n\n")
                f.write(f"- **Status:** {status_icon} {'PASSED' if result.get('success') else 'FAILED'}\n")
                f.write(f"- **Type:** 🔴 CRITICAL\n")
                
                # Quality Validation Results
                quality_validation = result.get('results', {}).get('_quality_validation', {})
                if quality_validation:
                    quality_status = quality_validation.get('status', 'unknown')
                    if quality_status == 'passed':
                        f.write("- **Quality:** ✅ All thresholds met\n")
                    elif quality_status == 'failed':
                        f.write("- **Quality:** ❌ Below thresholds\n")
                        failed_metrics = quality_validation.get('metrics_failed', [])
                        for failed in failed_metrics:
                            f.write(f"  - ⚠️  {failed['metric']}: {failed['value']:.2%} (threshold: {failed['threshold']:.2%})\n")
                    elif quality_status == 'warning':
                        f.write("- **Quality:** ⚠️  Below thresholds (allowed with --allow-low-quality)\n")
                
                if result.get('results'):
                    f.write("- **Metrics:**\n")
                    for key, value in result['results'].items():
                        if key == '_quality_validation':
                            continue
                        if isinstance(value, (int, float)):
                            f.write(f"  - {key}: {value}\n")
                        elif isinstance(value, dict) and 'accuracy' in value:
                            for perf_key, perf_value in value.items():
                                if isinstance(perf_value, (int, float)):
                                    f.write(f"  - {perf_key}: {perf_value}\n")
                f.write("\n")
        
        # Optional Models Section
        f.write("### Optional Models (Enhancements)\n\n")
        optional_models = ['gnn_synergy', 'soft_prompt']
        for model_name in optional_models:
            if model_name in training_results:
                result = training_results[model_name]
                status_icon = "✅" if result.get('success') else "⚠️"
                f.write(f"#### {model_name.replace('_', ' ').title()}\n\n")
                f.write(f"- **Status:** {status_icon} {'PASSED' if result.get('success') else 'NOT CONFIGURED'}\n")
                f.write(f"- **Type:** 🟡 OPTIONAL\n")
                if not result.get('success'):
                    f.write("- **Note:** Optional enhancement - not required for production deployment\n")
                if result.get('results'):
                    f.write("- **Metrics:**\n")
                    for key, value in result['results'].items():
                        if isinstance(value, (int, float)):
                            f.write(f"  - {key}: {value}\n")
                f.write("\n")
        f.write("---\n\n")
        
        # Model Manifest
        f.write("## 6. Model Manifest\n\n")
        if model_manifest:
            f.write(f"- **Generated:** {model_manifest.get('timestamp', 'unknown')}\n\n")
            f.write("### Models Saved\n\n")
            for model_name, model_info in model_manifest.get('models', {}).items():
                f.write(f"#### {model_name.replace('_', ' ').title()}\n\n")
                for key, value in model_info.items():
                    if value:
                        f.write(f"- **{key}:** {value}\n")
                f.write("\n")
        f.write("---\n\n")
        
        # Production Readiness Checklist
        f.write("## 7. Production Readiness Checklist\n\n")
        checklist = [
            ("Build completed successfully", build_status),
            ("Services deployed and running", deploy_status),
            ("All critical smoke tests passed", smoke_results.get('critical_failed', 1) == 0),
            ("Test data generated", data_generation_status),
            ("Home type classifier trained", training_results.get('home_type', {}).get('success', False)),
            ("Device intelligence models trained", training_results.get('device_intelligence', {}).get('success', False)),
            ("Models saved and verified", len(model_manifest.get('models', {})) > 0)
        ]
        
        for item, status in checklist:
            icon = "✅" if status else "❌"
            f.write(f"- {icon} {item}\n")
        
        f.write("\n---\n\n")
        f.write("## Next Steps\n\n")
        if critical_passed:
            f.write("1. Review model performance metrics\n")
            f.write("2. Verify model files are in correct locations\n")
            f.write("3. Deploy to production environment\n")
        else:
            f.write("1. Review failed steps above\n")
            f.write("2. Fix critical issues\n")
            f.write("3. Re-run this script\n")
    
    logger.info(f"✅ Report saved to {report_path}")
    return report_path

