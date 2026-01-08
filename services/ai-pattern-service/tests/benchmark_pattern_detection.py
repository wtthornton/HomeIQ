"""
Performance benchmarks for pattern detection.

Measures execution time and memory usage for pattern detection
at various data scales to ensure performance targets are met.

Created: January 2026
Targets:
- 1K events: < 100ms
- 10K events: < 500ms
- 100K events: < 5s
"""

import gc
import logging
import statistics
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable

import numpy as np
import pandas as pd

# Import modules under test
import sys
from pathlib import Path

# Add src directory to path
src_dir = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_dir))

from pattern_analyzer.time_of_day import TimeOfDayPatternDetector

# Configure logging
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)


# ============================================================================
# Benchmark Infrastructure
# ============================================================================

@dataclass
class BenchmarkResult:
    """Result of a single benchmark run."""
    
    name: str
    event_count: int
    device_count: int
    
    # Timing (milliseconds)
    execution_time_ms: float
    min_time_ms: float
    max_time_ms: float
    std_time_ms: float
    
    # Results
    patterns_detected: int
    
    # Memory (bytes)
    memory_before: int = 0
    memory_after: int = 0
    memory_delta: int = 0
    
    # Target
    target_ms: float = 0.0
    meets_target: bool = True
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            'name': self.name,
            'event_count': self.event_count,
            'device_count': self.device_count,
            'execution_time_ms': round(self.execution_time_ms, 2),
            'min_time_ms': round(self.min_time_ms, 2),
            'max_time_ms': round(self.max_time_ms, 2),
            'std_time_ms': round(self.std_time_ms, 2),
            'patterns_detected': self.patterns_detected,
            'memory_delta_mb': round(self.memory_delta / (1024 * 1024), 2),
            'target_ms': self.target_ms,
            'meets_target': self.meets_target,
        }


@dataclass
class BenchmarkSuite:
    """Collection of benchmark results."""
    
    results: list[BenchmarkResult] = field(default_factory=list)
    total_time_ms: float = 0.0
    all_targets_met: bool = True
    
    def add_result(self, result: BenchmarkResult) -> None:
        """Add a benchmark result."""
        self.results.append(result)
        self.total_time_ms += result.execution_time_ms
        if not result.meets_target:
            self.all_targets_met = False
    
    def summary(self) -> dict[str, Any]:
        """Get summary of all benchmarks."""
        return {
            'total_benchmarks': len(self.results),
            'total_time_ms': round(self.total_time_ms, 2),
            'all_targets_met': self.all_targets_met,
            'failed_targets': [
                r.name for r in self.results if not r.meets_target
            ],
            'results': [r.to_dict() for r in self.results],
        }


def get_memory_usage() -> int:
    """Get current memory usage in bytes."""
    try:
        import psutil
        process = psutil.Process()
        return process.memory_info().rss
    except ImportError:
        return 0


def benchmark(
    func: Callable,
    *args,
    iterations: int = 5,
    warmup: int = 1,
    **kwargs
) -> tuple[float, float, float, float, Any]:
    """
    Run benchmark with multiple iterations.
    
    Returns:
        Tuple of (avg_time_ms, min_time_ms, max_time_ms, std_time_ms, result)
    """
    # Warmup runs
    for _ in range(warmup):
        func(*args, **kwargs)
    
    # Timed runs
    times = []
    result = None
    
    for _ in range(iterations):
        gc.collect()  # Clean up before timing
        
        start = time.perf_counter()
        result = func(*args, **kwargs)
        end = time.perf_counter()
        
        times.append((end - start) * 1000)  # Convert to ms
    
    avg_time = statistics.mean(times)
    min_time = min(times)
    max_time = max(times)
    std_time = statistics.stdev(times) if len(times) > 1 else 0.0
    
    return avg_time, min_time, max_time, std_time, result


# ============================================================================
# Data Generation
# ============================================================================

def generate_events(
    n_events: int,
    n_devices: int,
    clustered: bool = True,
    cluster_variance_minutes: int = 15,
) -> pd.DataFrame:
    """
    Generate test event data.
    
    Args:
        n_events: Number of events to generate
        n_devices: Number of unique devices
        clustered: Whether to cluster events by time (more realistic)
        cluster_variance_minutes: Variance in minutes for clustered events
        
    Returns:
        DataFrame with device_id, timestamp, state columns
    """
    np.random.seed(42)  # Reproducibility
    
    # Generate device IDs
    domains = ["light", "switch", "climate", "cover", "sensor"]
    device_ids = [
        f"{domains[i % len(domains)]}.device_{i}"
        for i in range(n_devices)
    ]
    
    events = []
    base_date = datetime(2026, 1, 1)
    
    if clustered:
        # Generate clustered events (more realistic)
        events_per_device = n_events // n_devices
        
        for device_id in device_ids:
            # Each device has 1-3 time clusters
            n_clusters = np.random.randint(1, 4)
            cluster_hours = np.random.choice(24, n_clusters, replace=False)
            
            for _ in range(events_per_device):
                # Pick a cluster
                target_hour = np.random.choice(cluster_hours)
                
                # Add variance
                minute_offset = np.random.randint(
                    -cluster_variance_minutes,
                    cluster_variance_minutes + 1
                )
                day_offset = np.random.randint(0, 30)
                
                hour = target_hour
                minute = 30 + minute_offset
                
                if minute < 0:
                    hour = (hour - 1) % 24
                    minute += 60
                elif minute >= 60:
                    hour = (hour + 1) % 24
                    minute -= 60
                
                timestamp = base_date.replace(hour=hour, minute=minute) + timedelta(days=day_offset)
                
                events.append({
                    "device_id": device_id,
                    "timestamp": timestamp,
                    "state": np.random.choice(["on", "off"]),
                })
    else:
        # Generate random events (worst case for clustering)
        for _ in range(n_events):
            device_id = np.random.choice(device_ids)
            hour = np.random.randint(0, 24)
            minute = np.random.randint(0, 60)
            day_offset = np.random.randint(0, 30)
            
            timestamp = base_date.replace(hour=hour, minute=minute) + timedelta(days=day_offset)
            
            events.append({
                "device_id": device_id,
                "timestamp": timestamp,
                "state": np.random.choice(["on", "off"]),
            })
    
    return pd.DataFrame(events)


# ============================================================================
# Benchmark Tests
# ============================================================================

class PatternDetectionBenchmarks:
    """Benchmark suite for pattern detection."""
    
    # Performance targets (milliseconds)
    TARGETS = {
        1_000: 100,      # 1K events: < 100ms
        5_000: 250,      # 5K events: < 250ms
        10_000: 500,     # 10K events: < 500ms
        50_000: 2_500,   # 50K events: < 2.5s
        100_000: 5_000,  # 100K events: < 5s
    }
    
    def __init__(self):
        """Initialize benchmarks."""
        self.suite = BenchmarkSuite()
        self.detector = TimeOfDayPatternDetector(
            min_occurrences=3,
            min_confidence=0.5
        )
    
    def run_all(self) -> BenchmarkSuite:
        """Run all benchmarks."""
        print("\n" + "=" * 60)
        print("PATTERN DETECTION PERFORMANCE BENCHMARKS")
        print("=" * 60 + "\n")
        
        # Scale benchmarks
        self._benchmark_scale_1k()
        self._benchmark_scale_5k()
        self._benchmark_scale_10k()
        self._benchmark_scale_50k()
        self._benchmark_scale_100k()
        
        # Scenario benchmarks
        self._benchmark_many_devices()
        self._benchmark_few_devices_many_events()
        self._benchmark_random_distribution()
        
        # Print summary
        self._print_summary()
        
        return self.suite
    
    def _run_benchmark(
        self,
        name: str,
        events: pd.DataFrame,
        target_ms: float,
    ) -> BenchmarkResult:
        """Run a single benchmark."""
        n_events = len(events)
        n_devices = events["device_id"].nunique()
        
        # Get memory before
        gc.collect()
        memory_before = get_memory_usage()
        
        # Run benchmark
        avg_time, min_time, max_time, std_time, patterns = benchmark(
            self.detector.detect_patterns,
            events,
            iterations=5,
            warmup=1,
        )
        
        # Get memory after
        memory_after = get_memory_usage()
        
        # Create result
        result = BenchmarkResult(
            name=name,
            event_count=n_events,
            device_count=n_devices,
            execution_time_ms=avg_time,
            min_time_ms=min_time,
            max_time_ms=max_time,
            std_time_ms=std_time,
            patterns_detected=len(patterns),
            memory_before=memory_before,
            memory_after=memory_after,
            memory_delta=memory_after - memory_before,
            target_ms=target_ms,
            meets_target=avg_time <= target_ms,
        )
        
        # Print result
        status = "[OK]" if result.meets_target else "[FAIL]"
        print(f"{status} {name}")
        print(f"    Events: {n_events:,}, Devices: {n_devices}")
        print(f"    Time: {avg_time:.1f}ms (target: {target_ms:.0f}ms)")
        print(f"    Patterns: {len(patterns)}")
        print()
        
        self.suite.add_result(result)
        return result
    
    def _benchmark_scale_1k(self) -> None:
        """Benchmark with 1K events."""
        events = generate_events(1_000, 50, clustered=True)
        self._run_benchmark("Scale: 1K events", events, self.TARGETS[1_000])
    
    def _benchmark_scale_5k(self) -> None:
        """Benchmark with 5K events."""
        events = generate_events(5_000, 100, clustered=True)
        self._run_benchmark("Scale: 5K events", events, self.TARGETS[5_000])
    
    def _benchmark_scale_10k(self) -> None:
        """Benchmark with 10K events."""
        events = generate_events(10_000, 200, clustered=True)
        self._run_benchmark("Scale: 10K events", events, self.TARGETS[10_000])
    
    def _benchmark_scale_50k(self) -> None:
        """Benchmark with 50K events."""
        events = generate_events(50_000, 500, clustered=True)
        self._run_benchmark("Scale: 50K events", events, self.TARGETS[50_000])
    
    def _benchmark_scale_100k(self) -> None:
        """Benchmark with 100K events."""
        events = generate_events(100_000, 1000, clustered=True)
        self._run_benchmark("Scale: 100K events", events, self.TARGETS[100_000])
    
    def _benchmark_many_devices(self) -> None:
        """Benchmark with many devices (few events each)."""
        events = generate_events(10_000, 1000, clustered=True)  # 10 events per device
        self._run_benchmark("Scenario: Many devices (1000)", events, 1000)
    
    def _benchmark_few_devices_many_events(self) -> None:
        """Benchmark with few devices (many events each)."""
        events = generate_events(10_000, 10, clustered=True)  # 1000 events per device
        self._run_benchmark("Scenario: Few devices (10)", events, 500)
    
    def _benchmark_random_distribution(self) -> None:
        """Benchmark with random (non-clustered) events."""
        events = generate_events(10_000, 200, clustered=False)
        self._run_benchmark("Scenario: Random distribution", events, 750)
    
    def _print_summary(self) -> None:
        """Print benchmark summary."""
        print("=" * 60)
        print("BENCHMARK SUMMARY")
        print("=" * 60)
        
        summary = self.suite.summary()
        
        print(f"\nTotal benchmarks: {summary['total_benchmarks']}")
        print(f"Total time: {summary['total_time_ms']:.1f}ms")
        print(f"All targets met: {summary['all_targets_met']}")
        
        if summary['failed_targets']:
            print(f"\nFailed targets:")
            for name in summary['failed_targets']:
                print(f"  - {name}")
        
        print("\n" + "-" * 60)
        print("Detailed Results:")
        print("-" * 60)
        
        for result in summary['results']:
            status = "[OK]" if result['meets_target'] else "[FAIL]"
            print(f"{status} {result['name']}: {result['execution_time_ms']:.1f}ms "
                  f"(target: {result['target_ms']:.0f}ms)")


# ============================================================================
# Memory Benchmarks
# ============================================================================

class MemoryBenchmarks:
    """Memory usage benchmarks."""
    
    def __init__(self):
        """Initialize benchmarks."""
        self.detector = TimeOfDayPatternDetector(
            min_occurrences=3,
            min_confidence=0.5
        )
    
    def run_all(self) -> dict[str, Any]:
        """Run all memory benchmarks."""
        print("\n" + "=" * 60)
        print("MEMORY USAGE BENCHMARKS")
        print("=" * 60 + "\n")
        
        results = {}
        
        for n_events in [1_000, 10_000, 100_000]:
            result = self._benchmark_memory(n_events)
            results[f"{n_events}_events"] = result
            
            print(f"Events: {n_events:,}")
            print(f"  Input size: {result['input_size_mb']:.2f} MB")
            print(f"  Peak memory: {result['peak_memory_mb']:.2f} MB")
            print(f"  Memory per event: {result['memory_per_event_bytes']:.1f} bytes")
            print()
        
        return results
    
    def _benchmark_memory(self, n_events: int) -> dict[str, Any]:
        """Benchmark memory usage for given event count."""
        gc.collect()
        memory_start = get_memory_usage()
        
        # Generate data
        events = generate_events(n_events, n_events // 10, clustered=True)
        memory_after_data = get_memory_usage()
        
        # Run detection
        patterns = self.detector.detect_patterns(events)
        memory_after_detection = get_memory_usage()
        
        # Calculate sizes
        input_size = memory_after_data - memory_start
        peak_memory = memory_after_detection - memory_start
        memory_per_event = peak_memory / n_events if n_events > 0 else 0
        
        return {
            'event_count': n_events,
            'patterns_detected': len(patterns),
            'input_size_mb': input_size / (1024 * 1024),
            'peak_memory_mb': peak_memory / (1024 * 1024),
            'memory_per_event_bytes': memory_per_event,
        }


# ============================================================================
# Throughput Benchmarks
# ============================================================================

class ThroughputBenchmarks:
    """Throughput benchmarks (events per second)."""
    
    def __init__(self):
        """Initialize benchmarks."""
        self.detector = TimeOfDayPatternDetector(
            min_occurrences=3,
            min_confidence=0.5
        )
    
    def run_all(self) -> dict[str, Any]:
        """Run all throughput benchmarks."""
        print("\n" + "=" * 60)
        print("THROUGHPUT BENCHMARKS")
        print("=" * 60 + "\n")
        
        results = {}
        
        for n_events in [1_000, 10_000, 100_000]:
            events = generate_events(n_events, n_events // 10, clustered=True)
            
            # Time the detection
            start = time.perf_counter()
            patterns = self.detector.detect_patterns(events)
            elapsed = time.perf_counter() - start
            
            throughput = n_events / elapsed
            
            results[f"{n_events}_events"] = {
                'event_count': n_events,
                'elapsed_seconds': elapsed,
                'throughput_events_per_second': throughput,
                'patterns_detected': len(patterns),
            }
            
            print(f"Events: {n_events:,}")
            print(f"  Elapsed: {elapsed:.3f}s")
            print(f"  Throughput: {throughput:,.0f} events/second")
            print(f"  Patterns: {len(patterns)}")
            print()
        
        return results


# ============================================================================
# Main
# ============================================================================

def main():
    """Run all benchmarks."""
    # Performance benchmarks
    perf_benchmarks = PatternDetectionBenchmarks()
    perf_suite = perf_benchmarks.run_all()
    
    # Memory benchmarks
    mem_benchmarks = MemoryBenchmarks()
    mem_results = mem_benchmarks.run_all()
    
    # Throughput benchmarks
    throughput_benchmarks = ThroughputBenchmarks()
    throughput_results = throughput_benchmarks.run_all()
    
    # Final summary
    print("\n" + "=" * 60)
    print("FINAL SUMMARY")
    print("=" * 60)
    
    summary = perf_suite.summary()
    if summary['all_targets_met']:
        print("\n[OK] All performance targets met!")
    else:
        print(f"\n[FAIL] {len(summary['failed_targets'])} target(s) failed:")
        for name in summary['failed_targets']:
            print(f"  - {name}")
    
    return 0 if summary['all_targets_met'] else 1


if __name__ == "__main__":
    exit(main())
