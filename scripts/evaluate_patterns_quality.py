#!/usr/bin/env python3
"""
Pattern and Synergy Quality Evaluation Tool

Evaluates the accuracy and quality of patterns and synergies detected by
the AI Pattern Service by validating them against actual Home Assistant events.

Usage:
    python scripts/evaluate_patterns_quality.py --time-window 30 --output-format all
"""

import argparse
import asyncio
import json
import logging
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.quality_evaluation.database_accessor import DatabaseAccessor
from scripts.quality_evaluation.data_quality_analyzer import DataQualityAnalyzer
from scripts.quality_evaluation.event_fetcher import EventFetcher
from scripts.quality_evaluation.pattern_validator import PatternValidator
from scripts.quality_evaluation.report_generator import ReportGenerator
from scripts.quality_evaluation.synergy_validator import SynergyValidator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('quality_evaluation.log')
    ]
)
logger = logging.getLogger(__name__)


async def main() -> None:
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description='Evaluate quality and accuracy of patterns and synergies'
    )
    parser.add_argument(
        '--time-window',
        type=int,
        default=30,
        help='Days of events to analyze (default: 30, max: 90)'
    )
    parser.add_argument(
        '--output-format',
        choices=['json', 'markdown', 'html', 'all'],
        default='all',
        help='Output format (default: all)'
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        default='reports/quality',
        help='Output directory (default: reports/quality)'
    )
    parser.add_argument(
        '--min-confidence',
        type=float,
        default=0.0,
        help='Minimum confidence filter (default: 0.0)'
    )
    parser.add_argument(
        '--pattern-type',
        type=str,
        help='Filter by pattern type (time_of_day, co_occurrence)'
    )
    parser.add_argument(
        '--synergy-type',
        type=str,
        help='Filter by synergy type (device_pair, device_chain, etc.)'
    )
    parser.add_argument(
        '--data-api-url',
        type=str,
        default='http://localhost:8006',
        help='Data API URL (default: http://localhost:8006)'
    )
    parser.add_argument(
        '--db-path',
        type=str,
        default='data/ai_automation.db',
        help='Database path (default: data/ai_automation.db)'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Validate time window
    if args.time_window > 90:
        logger.warning(f"Time window {args.time_window} exceeds max 90 days, using 90")
        args.time_window = 90
    
    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info("=" * 80)
    logger.info("Pattern & Synergy Quality Evaluation")
    logger.info("=" * 80)
    logger.info(f"Time window: {args.time_window} days")
    logger.info(f"Output format: {args.output_format}")
    logger.info(f"Output directory: {output_dir}")
    
    # Initialize components
    db_accessor = None
    event_fetcher = None
    
    try:
        # Initialize database accessor
        logger.info("Initializing database accessor...")
        db_accessor = DatabaseAccessor(args.db_path)
        
        # Initialize event fetcher
        logger.info("Initializing event fetcher...")
        event_fetcher = EventFetcher(args.data_api_url)
        
        # Fetch data
        logger.info("Fetching patterns and synergies from database...")
        patterns = await db_accessor.get_all_patterns(
            pattern_type=args.pattern_type,
            min_confidence=args.min_confidence
        )
        synergies = await db_accessor.get_all_synergies(
            synergy_type=args.synergy_type,
            min_confidence=args.min_confidence
        )
        
        logger.info(f"Found {len(patterns)} patterns and {len(synergies)} synergies")
        
        # Fetch events
        logger.info(f"Fetching events from last {args.time_window} days...")
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=args.time_window)
        
        events_df = await event_fetcher.fetch_events(
            start_time=start_time,
            end_time=end_time,
            limit=50000
        )
        
        if events_df.empty:
            logger.warning("No events found for validation")
            logger.info("Skipping validation, generating data quality report only")
            events_df = None
        else:
            logger.info(f"Fetched {len(events_df)} events")
        
        # Initialize validators and analyzers
        pattern_validator = PatternValidator()
        synergy_validator = SynergyValidator()
        quality_analyzer = DataQualityAnalyzer()
        
        # Run evaluations
        results: Dict[str, Any] = {
            'evaluation_date': datetime.now(timezone.utc).isoformat(),
            'time_window_days': args.time_window,
            'total_patterns': len(patterns),
            'total_synergies': len(synergies),
        }
        
        # Data quality analysis
        logger.info("Analyzing data quality...")
        pattern_quality = quality_analyzer.analyze_pattern_quality(patterns)
        synergy_quality = quality_analyzer.analyze_synergy_quality(synergies)
        
        results['data_quality'] = {
            'patterns': pattern_quality,
            'synergies': synergy_quality
        }
        
        # Pattern validation (if events available)
        if events_df is not None and not events_df.empty:
            logger.info("Validating patterns against events...")
            pattern_validation = await pattern_validator.validate_patterns(
                stored_patterns=patterns,
                events_df=events_df
            )
            results['pattern_validation'] = pattern_validation
            
            logger.info("Validating synergies against events...")
            synergy_validation = await synergy_validator.validate_synergies(
                stored_synergies=synergies,
                events_df=events_df
            )
            results['synergy_validation'] = synergy_validation
        else:
            logger.warning("Skipping validation (no events available)")
            results['pattern_validation'] = {
                'status': 'skipped',
                'reason': 'No events available'
            }
            results['synergy_validation'] = {
                'status': 'skipped',
                'reason': 'No events available'
            }
        
        # Calculate overall quality score
        overall_score = _calculate_overall_quality_score(results)
        results['summary'] = {
            'total_patterns': len(patterns),
            'total_synergies': len(synergies),
            'overall_quality_score': overall_score,
            'pattern_quality_score': pattern_quality.get('quality_score', 0.0),
            'synergy_quality_score': synergy_quality.get('quality_score', 0.0),
        }
        
        # Generate recommendations
        results['recommendations'] = _generate_recommendations(results)
        
        # Generate reports
        logger.info("Generating reports...")
        report_generator = ReportGenerator()
        
        if args.output_format in ['json', 'all']:
            json_path = output_dir / 'evaluation_report.json'
            report_generator.generate_json_report(results, json_path)
            logger.info(f"JSON report: {json_path}")
        
        if args.output_format in ['markdown', 'all']:
            md_path = output_dir / 'evaluation_report.md'
            report_generator.generate_markdown_report(results, md_path)
            logger.info(f"Markdown report: {md_path}")
        
        if args.output_format in ['html', 'all']:
            html_path = output_dir / 'evaluation_report.html'
            report_generator.generate_html_report(results, html_path)
            logger.info(f"HTML report: {html_path}")
        
        logger.info("=" * 80)
        logger.info("Evaluation Complete!")
        logger.info(f"Overall Quality Score: {overall_score:.2%}")
        logger.info("=" * 80)
        
    except Exception as e:
        logger.error(f"Evaluation failed: {e}", exc_info=True)
        sys.exit(1)
        
    finally:
        # Cleanup
        if db_accessor:
            await db_accessor.close()
        if event_fetcher:
            await event_fetcher.close()


def _calculate_overall_quality_score(results: Dict[str, Any]) -> float:
    """Calculate overall quality score from results."""
    scores = []
    
    # Pattern quality score
    if 'data_quality' in results and 'patterns' in results['data_quality']:
        pattern_quality = results['data_quality']['patterns']
        if 'quality_score' in pattern_quality:
            scores.append(pattern_quality['quality_score'])
    
    # Synergy quality score
    if 'data_quality' in results and 'synergies' in results['data_quality']:
        synergy_quality = results['data_quality']['synergies']
        if 'quality_score' in synergy_quality:
            scores.append(synergy_quality['quality_score'])
    
    # Pattern validation score
    if 'pattern_validation' in results and isinstance(results['pattern_validation'], dict):
        if 'f1_score' in results['pattern_validation']:
            scores.append(results['pattern_validation']['f1_score'])
    
    # Synergy validation score
    if 'synergy_validation' in results and isinstance(results['synergy_validation'], dict):
        if 'f1_score' in results['synergy_validation']:
            scores.append(results['synergy_validation']['f1_score'])
    
    if not scores:
        return 0.0
    
    return sum(scores) / len(scores)


def _generate_recommendations(results: Dict[str, Any]) -> List[str]:
    """Generate recommendations based on evaluation results."""
    recommendations = []
    
    # Check data quality
    if 'data_quality' in results:
        pattern_quality = results['data_quality'].get('patterns', {})
        synergy_quality = results['data_quality'].get('synergies', {})
        
        # Pattern completeness
        pattern_completeness = pattern_quality.get('completeness', {})
        if pattern_completeness.get('confidence', 1.0) < 0.95:
            recommendations.append("Some patterns are missing confidence scores - review pattern detection logic")
        
        # Synergy completeness
        synergy_completeness = synergy_quality.get('completeness', {})
        if synergy_completeness.get('pattern_support_score', 1.0) < 0.8:
            recommendations.append("Many synergies lack pattern support scores - consider re-running pattern validation")
    
    # Check validation results
    if 'pattern_validation' in results and isinstance(results['pattern_validation'], dict):
        pattern_val = results['pattern_validation']
        if pattern_val.get('precision', 1.0) < 0.7:
            recommendations.append(f"Pattern precision is low ({pattern_val.get('precision', 0):.2%}) - many false positives detected")
        if pattern_val.get('recall', 1.0) < 0.7:
            recommendations.append(f"Pattern recall is low ({pattern_val.get('recall', 0):.2%}) - many patterns missed")
    
    if 'synergy_validation' in results and isinstance(results['synergy_validation'], dict):
        synergy_val = results['synergy_validation']
        if synergy_val.get('precision', 1.0) < 0.7:
            recommendations.append(f"Synergy precision is low ({synergy_val.get('precision', 0):.2%}) - many false positives detected")
        if synergy_val.get('recall', 1.0) < 0.7:
            recommendations.append(f"Synergy recall is low ({synergy_val.get('recall', 0):.2%}) - many synergies missed")
    
    if not recommendations:
        recommendations.append("Overall data quality is good - no immediate action required")
    
    return recommendations


if __name__ == "__main__":
    asyncio.run(main())
