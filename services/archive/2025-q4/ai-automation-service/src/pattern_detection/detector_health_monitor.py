"""
Detector Health Monitoring

Tracks detector performance, failures, and pattern yield to provide visibility
into detector health and identify issues.
"""

import logging
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


class DetectorHealthMonitor:
    """
    Track detector performance and failures.
    
    Provides visibility into:
    - Detector success/failure rates
    - Pattern yield per detector
    - Processing time metrics
    - Error tracking
    """
    
    def __init__(self):
        """Initialize detector health monitor."""
        self.detector_stats: dict[str, dict[str, Any]] = defaultdict(lambda: {
            'runs': 0,
            'successful_runs': 0,
            'failed_runs': 0,
            'total_patterns': 0,
            'total_processing_time': 0.0,
            'avg_processing_time': 0.0,
            'last_error': None,
            'last_error_time': None,
            'last_success_time': None,
            'consecutive_failures': 0,
            'max_patterns_per_run': 0,
            'min_patterns_per_run': float('inf')
        })
        logger.info("DetectorHealthMonitor initialized")
    
    def track_detection_run(
        self,
        detector_name: str,
        patterns_found: int,
        processing_time: float,
        error: Exception | None = None
    ) -> None:
        """
        Track detector execution.
        
        Args:
            detector_name: Name of the detector (e.g., 'TimeOfDayPatternDetector')
            patterns_found: Number of patterns detected (0 if failed)
            processing_time: Processing time in seconds
            error: Exception if detection failed, None if successful
        """
        stats = self.detector_stats[detector_name]
        
        stats['runs'] += 1
        
        if error:
            stats['failed_runs'] += 1
            stats['last_error'] = str(error)
            stats['last_error_time'] = datetime.now(timezone.utc).isoformat()
            stats['consecutive_failures'] += 1
            logger.warning(
                f"Detector {detector_name} failed: {error} "
                f"(consecutive failures: {stats['consecutive_failures']})"
            )
        else:
            stats['successful_runs'] += 1
            stats['total_patterns'] += patterns_found
            stats['total_processing_time'] += processing_time
            stats['avg_processing_time'] = (
                stats['total_processing_time'] / stats['successful_runs']
            )
            stats['last_success_time'] = datetime.now(timezone.utc).isoformat()
            stats['consecutive_failures'] = 0  # Reset on success
            
            # Track min/max patterns
            if patterns_found > stats['max_patterns_per_run']:
                stats['max_patterns_per_run'] = patterns_found
            if patterns_found < stats['min_patterns_per_run']:
                stats['min_patterns_per_run'] = patterns_found
            
            logger.debug(
                f"Detector {detector_name}: {patterns_found} patterns in {processing_time:.2f}s"
            )
    
    def get_health_report(self) -> dict[str, Any]:
        """
        Generate health report for all detectors.
        
        Returns:
            Dictionary with health metrics for each detector:
            {
                'detector_name': {
                    'success_rate': float (0.0-1.0),
                    'avg_patterns_per_run': float,
                    'avg_processing_time': float (seconds),
                    'last_error': str | None,
                    'status': 'healthy' | 'degraded' | 'failing',
                    'consecutive_failures': int,
                    'total_runs': int,
                    'total_patterns': int
                }
            }
        """
        report = {}
        
        for detector_name, stats in self.detector_stats.items():
            total_runs = stats['runs']
            if total_runs == 0:
                continue
            
            success_rate = stats['successful_runs'] / total_runs
            avg_patterns = (
                stats['total_patterns'] / stats['successful_runs']
                if stats['successful_runs'] > 0 else 0.0
            )
            
            # Determine status
            if success_rate >= 0.9 and stats['consecutive_failures'] == 0:
                status = 'healthy'
            elif success_rate >= 0.7 and stats['consecutive_failures'] < 3:
                status = 'degraded'
            else:
                status = 'failing'
            
            report[detector_name] = {
                'success_rate': round(success_rate, 3),
                'avg_patterns_per_run': round(avg_patterns, 1),
                'avg_processing_time': round(stats['avg_processing_time'], 3),
                'last_error': stats['last_error'],
                'last_error_time': stats['last_error_time'],
                'last_success_time': stats['last_success_time'],
                'status': status,
                'consecutive_failures': stats['consecutive_failures'],
                'total_runs': total_runs,
                'total_patterns': stats['total_patterns'],
                'max_patterns_per_run': stats['max_patterns_per_run'],
                'min_patterns_per_run': (
                    stats['min_patterns_per_run'] 
                    if stats['min_patterns_per_run'] != float('inf') else 0
                )
            }
        
        return report
    
    def get_detector_status(self, detector_name: str) -> dict[str, Any] | None:
        """
        Get status for a specific detector.
        
        Args:
            detector_name: Name of the detector
            
        Returns:
            Status dictionary or None if detector not tracked
        """
        if detector_name not in self.detector_stats:
            return None
        
        report = self.get_health_report()
        return report.get(detector_name)
    
    def get_unhealthy_detectors(self) -> list[str]:
        """
        Get list of unhealthy detectors (degraded or failing).
        
        Returns:
            List of detector names with status 'degraded' or 'failing'
        """
        report = self.get_health_report()
        return [
            name for name, data in report.items()
            if data['status'] in ('degraded', 'failing')
        ]
    
    def reset_stats(self, detector_name: str | None = None) -> None:
        """
        Reset statistics for a detector or all detectors.
        
        Args:
            detector_name: Name of detector to reset, or None to reset all
        """
        if detector_name:
            if detector_name in self.detector_stats:
                self.detector_stats[detector_name] = defaultdict(lambda: {
                    'runs': 0,
                    'successful_runs': 0,
                    'failed_runs': 0,
                    'total_patterns': 0,
                    'total_processing_time': 0.0,
                    'avg_processing_time': 0.0,
                    'last_error': None,
                    'last_error_time': None,
                    'last_success_time': None,
                    'consecutive_failures': 0,
                    'max_patterns_per_run': 0,
                    'min_patterns_per_run': float('inf')
                })
                logger.info(f"Reset stats for detector {detector_name}")
        else:
            self.detector_stats.clear()
            logger.info("Reset stats for all detectors")

