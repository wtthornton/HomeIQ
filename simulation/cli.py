#!/usr/bin/env python3
"""
Simulation Framework CLI

Command-line interface for simulation framework.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from engine.simulation_engine import SimulationEngine
from engine.config import SimulationConfig
from batch.batch_processor import BatchProcessor
from reporting.results_aggregator import ResultsAggregator
from reporting.report_generator import ReportGenerator
from metrics.metrics_collector import MetricsCollector

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def run_simulation(
    mode: str = "standard",
    homes_count: int = 100,
    queries_count: int = 50,
    output_dir: str = "simulation_results"
) -> None:
    """
    Run simulation framework.
    
    Args:
        mode: Simulation mode ("quick", "standard", "stress")
        homes_count: Number of homes to simulate
        queries_count: Number of queries per home
        output_dir: Output directory for results
    """
    logger.info(f"Starting simulation: mode={mode}, homes={homes_count}, queries={queries_count}")
    
    # Initialize configuration
    config = SimulationConfig(
        mode=mode,
        synthetic_homes_count=homes_count
    )
    
    # Initialize simulation engine
    engine = SimulationEngine(config)
    
    # Initialize components
    batch_processor = BatchProcessor(
        max_parallel_homes=config.max_parallel_homes,
        max_parallel_queries=20
    )
    
    aggregator = ResultsAggregator()
    
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    report_generator = ReportGenerator(output_path)
    
    metrics_collector = MetricsCollector()
    
    try:
        # Initialize engine
        await engine.initialize()
        
        # Register mock services (simplified - in real implementation would use factories)
        from mocks.influxdb_client import MockInfluxDBClient
        from mocks.openai_client import MockOpenAIClient
        from mocks.mqtt_client import MockMQTTClient
        from mocks.data_api_client import MockDataAPIClient
        from mocks.device_intelligence_client import MockDeviceIntelligenceClient
        from mocks.ha_conversation_api import MockHAConversationAPI
        from mocks.ha_client import MockHAClient
        from mocks.safety_validator import MockSafetyValidator
        
        engine.container.register_instance("influxdb_client", MockInfluxDBClient())
        engine.container.register_instance("openai_client", MockOpenAIClient())
        engine.container.register_instance("mqtt_client", MockMQTTClient())
        engine.container.register_instance("data_api_client", MockDataAPIClient())
        engine.container.register_instance("device_intelligence_client", MockDeviceIntelligenceClient())
        engine.container.register_instance("ha_conversation_api", MockHAConversationAPI())
        engine.container.register_instance("ha_client", MockHAClient())
        engine.container.register_instance("safety_validator", MockSafetyValidator())
        
        # Generate synthetic homes
        logger.info("Generating synthetic homes...")
        homes = []
        for i in range(homes_count):
            homes.append({
                "home_id": f"home_{i:03d}",
                "home_type": "single_family_house"
            })
        
        # Process 3 AM workflows
        logger.info("Processing 3 AM workflows...")
        
        async def process_3am_workflow(home: dict) -> dict:
            """Process 3 AM workflow for a home."""
            simulator = engine.get_workflow_simulator("3am")
            result = await simulator.simulate(home["home_id"])
            aggregator.add_3am_result(result)
            return result
        
        batch_result_3am = await batch_processor.process_homes_batch(
            homes,
            process_3am_workflow,
            workflow_type="3am"
        )
        
        logger.info(f"3 AM workflows completed: {batch_result_3am['successful']}/{batch_result_3am['total_homes']}")
        
        # Process Ask AI queries
        logger.info("Processing Ask AI queries...")
        
        queries = [
            {"query": f"Turn on the lights in room {i}"}
            for i in range(queries_count)
        ]
        
        async def process_ask_ai_query(home_id: str, query: str) -> dict:
            """Process Ask AI query for a home."""
            simulator = engine.get_workflow_simulator("ask_ai")
            result = await simulator.simulate_query(home_id, query)
            aggregator.add_ask_ai_result(result)
            return result
        
        # Process queries for first home as example
        if homes:
            batch_result_ask_ai = await batch_processor.process_queries_batch(
                queries,
                process_ask_ai_query,
                homes[0]["home_id"]
            )
            logger.info(f"Ask AI queries completed: {batch_result_ask_ai['successful']}/{batch_result_ask_ai['total_queries']}")
        
        # Generate reports
        logger.info("Generating reports...")
        summary = aggregator.get_summary()
        summary["metrics"] = metrics_collector.get_summary()
        
        json_report = report_generator.generate_json_report(summary)
        csv_report = report_generator.generate_csv_report(summary)
        html_report = report_generator.generate_html_report(summary)
        
        logger.info(f"Reports generated:")
        logger.info(f"  - JSON: {json_report}")
        logger.info(f"  - CSV: {csv_report}")
        logger.info(f"  - HTML: {html_report}")
        
        logger.info("Simulation completed successfully!")
        
    except Exception as e:
        logger.error(f"Simulation failed: {e}", exc_info=True)
        sys.exit(1)
    
    finally:
        await engine.cleanup()


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Simulation Framework CLI")
    parser.add_argument(
        "--mode",
        choices=["quick", "standard", "stress"],
        default="standard",
        help="Simulation mode"
    )
    parser.add_argument(
        "--homes",
        type=int,
        default=100,
        help="Number of homes to simulate"
    )
    parser.add_argument(
        "--queries",
        type=int,
        default=50,
        help="Number of queries per home"
    )
    parser.add_argument(
        "--output-dir",
        default="simulation_results",
        help="Output directory for results"
    )
    
    args = parser.parse_args()
    
    asyncio.run(run_simulation(
        mode=args.mode,
        homes_count=args.homes,
        queries_count=args.queries,
        output_dir=args.output_dir
    ))


if __name__ == "__main__":
    main()

