"""
Performance monitoring for enhanced entity extraction
"""

import logging
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

class EnhancedExtractionMetrics:
    """Monitor performance of enhanced entity extraction"""

    def __init__(self):
        self.metrics = {
            'total_queries': 0,
            'enhanced_extractions': 0,
            'fallback_extractions': 0,
            'avg_extraction_time': 0.0,
            'device_intelligence_calls': 0,
            'capabilities_found': 0,
            'health_filtered_devices': 0,
            'areas_discovered': set(),
            'capabilities_used': defaultdict(int),
            'device_types_found': defaultdict(int),
            'error_count': 0,
            'last_reset': datetime.now(timezone.utc)
        }

    async def track_extraction(self, query: str, entities: list[dict[str, Any]], extraction_time: float):
        """Track extraction metrics"""

        self.metrics['total_queries'] += 1
        self.metrics['avg_extraction_time'] = (
            (self.metrics['avg_extraction_time'] * (self.metrics['total_queries'] - 1) + extraction_time)
            / self.metrics['total_queries']
        )

        # Count enhanced vs fallback extractions
        enhanced_count = len([e for e in entities if e.get('extraction_method') == 'device_intelligence'])
        if enhanced_count > 0:
            self.metrics['enhanced_extractions'] += 1
        else:
            self.metrics['fallback_extractions'] += 1

        # Count capabilities found
        total_capabilities = sum(len(e.get('capabilities', [])) for e in entities)
        self.metrics['capabilities_found'] += total_capabilities

        # Track areas discovered
        for entity in entities:
            if entity.get('area'):
                self.metrics['areas_discovered'].add(entity['area'])

            # Track capabilities used
            capabilities = entity.get('capabilities', [])
            for cap in capabilities:
                if cap.get('supported'):
                    self.metrics['capabilities_used'][cap['feature']] += 1

            # Track device types
            if entity.get('integration'):
                self.metrics['device_types_found'][entity['integration']] += 1

        logger.info(f"📊 Extraction metrics: {enhanced_count} enhanced entities, {total_capabilities} capabilities, {extraction_time:.2f}s")

    def track_device_intelligence_call(self, call_type: str, success: bool = True):
        """Track device intelligence service calls"""

        self.metrics['device_intelligence_calls'] += 1

        if not success:
            self.metrics['error_count'] += 1

        logger.debug(f"📡 Device intelligence call: {call_type}, success: {success}")

    def track_health_filtering(self, filtered_count: int):
        """Track devices filtered by health score"""

        self.metrics['health_filtered_devices'] += filtered_count

        if filtered_count > 0:
            logger.info(f"🏥 Health filtering: {filtered_count} devices filtered out")

    def get_metrics(self) -> dict[str, Any]:
        """Get current metrics with computed statistics"""

        # Convert sets to lists for JSON serialization
        metrics_copy = self.metrics.copy()
        metrics_copy['areas_discovered'] = list(metrics_copy['areas_discovered'])
        metrics_copy['capabilities_used'] = dict(metrics_copy['capabilities_used'])
        metrics_copy['device_types_found'] = dict(metrics_copy['device_types_found'])

        # Add computed statistics
        if self.metrics['total_queries'] > 0:
            metrics_copy['enhancement_rate'] = (
                self.metrics['enhanced_extractions'] / self.metrics['total_queries']
            )
            metrics_copy['fallback_rate'] = (
                self.metrics['fallback_extractions'] / self.metrics['total_queries']
            )
            metrics_copy['avg_capabilities_per_query'] = (
                self.metrics['capabilities_found'] / self.metrics['total_queries']
            )
        else:
            metrics_copy['enhancement_rate'] = 0.0
            metrics_copy['fallback_rate'] = 0.0
            metrics_copy['avg_capabilities_per_query'] = 0.0

        # Add error rate
        if self.metrics['device_intelligence_calls'] > 0:
            metrics_copy['error_rate'] = (
                self.metrics['error_count'] / self.metrics['device_intelligence_calls']
            )
        else:
            metrics_copy['error_rate'] = 0.0

        return metrics_copy

    def get_performance_summary(self) -> str:
        """Get human-readable performance summary"""

        metrics = self.get_metrics()

        summary = f"""
📊 Enhanced Entity Extraction Performance Summary
===============================================

📈 Query Statistics:
- Total Queries: {metrics['total_queries']}
- Enhanced Extractions: {metrics['enhanced_extractions']} ({metrics['enhancement_rate']:.1%})
- Fallback Extractions: {metrics['fallback_extractions']} ({metrics['fallback_rate']:.1%})
- Average Extraction Time: {metrics['avg_extraction_time']:.2f}s

🔧 Device Intelligence:
- Service Calls: {metrics['device_intelligence_calls']}
- Error Rate: {metrics['error_rate']:.1%}
- Health Filtered Devices: {metrics['health_filtered_devices']}

💡 Capabilities:
- Total Capabilities Found: {metrics['capabilities_found']}
- Average per Query: {metrics['avg_capabilities_per_query']:.1f}
- Areas Discovered: {len(metrics['areas_discovered'])}
- Device Types: {len(metrics['device_types_found'])}

🏆 Top Capabilities Used:
{self._format_top_capabilities(metrics['capabilities_used'])}

📱 Top Device Types:
{self._format_top_device_types(metrics['device_types_found'])}

🕒 Last Reset: {metrics['last_reset'].strftime('%Y-%m-%d %H:%M:%S UTC')}
"""
        return summary

    def _format_top_capabilities(self, capabilities: dict[str, int], top_n: int = 5) -> str:
        """Format top capabilities for display"""

        if not capabilities:
            return "  None"

        sorted_caps = sorted(capabilities.items(), key=lambda x: x[1], reverse=True)
        top_caps = sorted_caps[:top_n]

        return "\n".join([f"  {cap}: {count} times" for cap, count in top_caps])

    def _format_top_device_types(self, device_types: dict[str, int], top_n: int = 5) -> str:
        """Format top device types for display"""

        if not device_types:
            return "  None"

        sorted_types = sorted(device_types.items(), key=lambda x: x[1], reverse=True)
        top_types = sorted_types[:top_n]

        return "\n".join([f"  {dtype}: {count} devices" for dtype, count in top_types])

    def reset_metrics(self):
        """Reset all metrics"""

        self.metrics = {
            'total_queries': 0,
            'enhanced_extractions': 0,
            'fallback_extractions': 0,
            'avg_extraction_time': 0.0,
            'device_intelligence_calls': 0,
            'capabilities_found': 0,
            'health_filtered_devices': 0,
            'areas_discovered': set(),
            'capabilities_used': defaultdict(int),
            'device_types_found': defaultdict(int),
            'error_count': 0,
            'last_reset': datetime.now(timezone.utc)
        }

        logger.info("📊 Metrics reset")

# Global metrics instance
extraction_metrics = EnhancedExtractionMetrics()
