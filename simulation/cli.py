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
from reporting.summary_generator import SummaryGenerator
from metrics.metrics_collector import MetricsCollector
from training_data.collector import TrainingDataCollector
from training_data.exporters import TrainingDataExporter
from training_data.lineage_tracker import LineageTracker
from utils.logging_config import setup_logging

# Logging will be configured in main() based on CLI parameters
logger = logging.getLogger(__name__)


async def run_simulation(
    mode: str = "standard",
    homes_count: int = 100,
    queries_count: int = 50,
    output_dir: str = "simulation_results",
    log_level: str = "WARNING",
    html_report: bool = False
) -> None:
    """
    Run simulation framework.
    
    Args:
        mode: Simulation mode ("quick", "standard", "stress")
        homes_count: Number of homes to simulate
        queries_count: Number of queries per home
        output_dir: Output directory for results
        log_level: Console log level (DEBUG, INFO, WARNING, ERROR)
        html_report: Whether to generate HTML dashboard report
    """
    # Setup logging
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    logs_dir = output_path / "logs"
    setup_logging(log_level=log_level, log_dir=logs_dir, log_to_file=True)
    
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
    
    # Initialize summary generator
    summary_generator = SummaryGenerator(output_path)
    
    report_generator = ReportGenerator(output_path)
    
    metrics_collector = MetricsCollector()
    
    # Initialize training data collection (Epic AI-18)
    training_data_collector = TrainingDataCollector()
    training_data_dir = Path("simulation/training_data")
    training_data_dir.mkdir(parents=True, exist_ok=True)
    training_data_exporter = TrainingDataExporter(training_data_dir)
    lineage_tracker = LineageTracker(training_data_dir / "lineage.db")
    
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
        
        influxdb_client = MockInfluxDBClient()
        data_api_client = MockDataAPIClient()
        
        engine.container.register_instance("influxdb_client", influxdb_client)
        engine.container.register_instance("openai_client", MockOpenAIClient())
        engine.container.register_instance("mqtt_client", MockMQTTClient())
        engine.container.register_instance("data_api_client", data_api_client)
        engine.container.register_instance("device_intelligence_client", MockDeviceIntelligenceClient())
        engine.container.register_instance("ha_conversation_api", MockHAConversationAPI())
        engine.container.register_instance("ha_client", MockHAClient())
        engine.container.register_instance("safety_validator", MockSafetyValidator())
        
        # Generate synthetic homes with actual data
        logger.info(f"Generating {homes_count} synthetic homes...")
        from data_generation.home_generator import HomeGenerator
        import pandas as pd
        from datetime import datetime, timezone
        import time
        
        data_creation_start = time.time()
        home_generator = HomeGenerator()
        home_types = ["single_family_house", "apartment", "condo", "townhouse"]
        
        homes = []
        all_events = []
        data_creation_errors = []
        
        for i in range(homes_count):
            home_type = home_types[i % len(home_types)]
            try:
                logger.debug(f"Generating home {i+1}/{homes_count} ({home_type})...")
                home = await home_generator.generate_home(
                    home_type=home_type,
                    event_days=90,
                    home_index=i,
                    enable_ground_truth=False
                )
                homes.append(home)
                
                # Convert events to DataFrame format
                if "events" in home and home["events"]:
                    events_list = home["events"]
                    if events_list:
                        # Convert to DataFrame with required columns
                        events_df = pd.DataFrame(events_list)
                        
                        # Ensure required columns exist and convert types
                        if "_time" not in events_df.columns:
                            if "timestamp" in events_df.columns:
                                events_df["_time"] = pd.to_datetime(events_df["timestamp"], utc=True, errors='coerce')
                            elif "time" in events_df.columns:
                                events_df["_time"] = pd.to_datetime(events_df["time"], utc=True, errors='coerce')
                            else:
                                events_df["_time"] = pd.Timestamp.now(tz=timezone.utc)
                        else:
                            # Ensure _time is datetime type (handle multiple formats)
                            events_df["_time"] = pd.to_datetime(events_df["_time"], utc=True, errors='coerce')
                        
                        # Fill any NaT values with current time
                        events_df["_time"] = events_df["_time"].fillna(pd.Timestamp.now(tz=timezone.utc))
                        
                        # Also set timestamp for Data API compatibility
                        if "timestamp" not in events_df.columns:
                            events_df["timestamp"] = events_df["_time"]
                        else:
                            events_df["timestamp"] = pd.to_datetime(events_df["timestamp"], utc=True, errors='coerce').fillna(events_df["_time"])
                        
                        if "entity_id" not in events_df.columns:
                            if "entity" in events_df.columns:
                                events_df["entity_id"] = events_df["entity"]
                            else:
                                events_df["entity_id"] = "unknown"
                        
                        if "domain" not in events_df.columns and "entity_id" in events_df.columns:
                            events_df["domain"] = events_df["entity_id"].str.split(".").str[0]
                        
                        if "device_id" not in events_df.columns and "entity_id" in events_df.columns:
                            events_df["device_id"] = events_df["entity_id"]
                        
                        all_events.append(events_df)
                        
                        logger.debug(f"  Generated {len(events_list)} events for {home['home_id']}")
            except Exception as e:
                error_msg = f"Failed to generate home {i}: {e}"
                logger.warning(error_msg)
                data_creation_errors.append(error_msg)
                homes.append({
                    "home_id": f"home_{i:03d}",
                    "home_type": home_type
                })
        
        # Calculate data creation metrics
        data_creation_time = time.time() - data_creation_start
        total_devices = sum(len(home.get("devices", [])) for home in homes)
        total_events = sum(len(df) for df in all_events) if all_events else 0
        
        # Generate data creation summary
        data_creation_summary_path = summary_generator.generate_data_creation_summary(
            homes_count=len(homes),
            total_devices=total_devices,
            total_events=total_events,
            generation_time_seconds=data_creation_time,
            errors=data_creation_errors if data_creation_errors else None
        )
        logger.info(f"✅ Data creation complete: {len(homes)} homes, {total_devices} devices, {total_events} events")
        
        # Load all events into mock clients
        if all_events:
            logger.info(f"Loading {total_events} total events into mock clients...")
            combined_events = pd.concat(all_events, ignore_index=True)
            
            # Load into Data API client
            data_api_client.load_events(combined_events)
            
            # Load into InfluxDB client (needs _time column)
            if "_time" in combined_events.columns:
                influxdb_client.load_events(combined_events)
            
            logger.info(f"Loaded events for {len(homes)} homes")
        else:
            logger.warning("No events generated - simulation will run with empty data")
        
        # Process 3 AM workflows
        simulation_start = time.time()
        logger.info("Processing 3 AM workflows...")
        
        async def process_3am_workflow(home: dict) -> dict:
            """Process 3 AM workflow for a home."""
            simulator = engine.get_workflow_simulator("3am")
            result = await simulator.simulate(home["home_id"])
            aggregator.add_3am_result(result)
            
            # Collect training data from 3 AM workflow (Epic AI-18)
            if result.get("status") == "success" and "phases" in result:
                phases = result["phases"]
                
                # Collect pattern detection data
                if "phase3_pattern_detection" in phases:
                    pattern_data = phases["phase3_pattern_detection"]
                    if "patterns" in pattern_data:
                        for pattern in pattern_data.get("patterns", []):
                            # Extract embedded ground_truth and metrics from pattern
                            ground_truth = pattern.get("ground_truth")
                            metrics = pattern.get("metrics")
                            # Create pattern dict without embedded fields for collector
                            pattern_dict = {
                                "entity_id": pattern.get("entity_id"),
                                "pattern_type": pattern.get("pattern_type"),
                                "confidence": pattern.get("confidence"),
                                "occurrences": pattern.get("occurrences")
                            }
                            training_data_collector.collect_pattern_data(
                                pattern=pattern_dict,
                                ground_truth=ground_truth,
                                metrics=metrics
                            )
                            lineage_tracker.track_data(
                                data_id=f"pattern_{home['home_id']}_{len(training_data_collector.get_collected_data('pattern_detection'))}",
                                data_type="pattern_detection",
                                source_cycle="simulation_run",
                                source_home_id=home["home_id"]
                            )
                
                # Collect synergy detection data
                if "phase3c_synergy_detection" in phases:
                    synergy_data = phases["phase3c_synergy_detection"]
                    if "synergies" in synergy_data:
                        for synergy in synergy_data.get("synergies", []):
                            # Extract embedded relationship and prediction from synergy
                            relationship = synergy.get("relationship")
                            prediction = synergy.get("prediction")
                            # Create synergy dict without embedded fields for collector
                            synergy_dict = {
                                "device1": synergy.get("device1"),
                                "device2": synergy.get("device2"),
                                "synergy_score": synergy.get("synergy_score")
                            }
                            training_data_collector.collect_synergy_data(
                                synergy=synergy_dict,
                                relationship=relationship,
                                prediction=prediction
                            )
                            lineage_tracker.track_data(
                                data_id=f"synergy_{home['home_id']}_{len(training_data_collector.get_collected_data('synergy_detection'))}",
                                data_type="synergy_detection",
                                source_cycle="simulation_run",
                                source_home_id=home["home_id"]
                            )
                
                # Collect suggestion generation data
                if "phase5_suggestion_generation" in phases:
                    suggestion_data = phases["phase5_suggestion_generation"]
                    if "suggestions" in suggestion_data:
                        for suggestion_item in suggestion_data.get("suggestions", []):
                            # Extract embedded prompt and response from suggestion
                            if isinstance(suggestion_item, dict):
                                suggestion = suggestion_item.get("suggestion", suggestion_item)
                                prompt = suggestion_item.get("prompt")
                                response = suggestion_item.get("response")
                            else:
                                # Backward compatibility for string suggestions
                                suggestion = {"text": suggestion_item}
                                prompt = None
                                response = None
                            training_data_collector.collect_suggestion_data(
                                suggestion=suggestion,
                                prompt=prompt,
                                response=response
                            )
                            lineage_tracker.track_data(
                                data_id=f"suggestion_{home['home_id']}_{len(training_data_collector.get_collected_data('suggestion_generation'))}",
                                data_type="suggestion_generation",
                                source_cycle="simulation_run",
                                source_home_id=home["home_id"]
                            )
            
            return result
        
        batch_result_3am = await batch_processor.process_homes_batch(
            homes,
            process_3am_workflow,
            workflow_type="3am"
        )
        
        logger.info(f"3 AM workflows completed: {batch_result_3am['successful']}/{batch_result_3am['total_homes']}")
        
        # Process Ask AI queries - distribute across all homes
        logger.info(f"Processing Ask AI queries ({queries_count} per home, {len(homes)} homes = {queries_count * len(homes)} total)...")
        
        async def process_ask_ai_query(home_id: str, query: str) -> dict:
            """Process Ask AI query for a home."""
            simulator = engine.get_workflow_simulator("ask_ai")
            result = await simulator.simulate_query(home_id, query)
            aggregator.add_ask_ai_result(result)
            
            # Collect training data from Ask AI workflow (Epic AI-18)
            if result.get("status") == "success" and "steps" in result:
                steps = result["steps"]
                
                # Collect YAML generation data
                if "step4_yaml_generation" in steps:
                    yaml_data = steps["step4_yaml_generation"]
                    # Check if YAML was actually generated (not empty)
                    yaml_content = yaml_data.get("yaml") or yaml_data.get("yaml_content", "")
                    yaml_generated = yaml_data.get("yaml_generated", False)
                    
                    if yaml_generated and yaml_content and yaml_content.strip():
                        yaml_validation = steps.get("step5_yaml_validation", {})
                        # Ensure validation result has is_valid or yaml_valid
                        if "is_valid" not in yaml_validation and "yaml_valid" not in yaml_validation:
                            yaml_validation["yaml_valid"] = True  # Default to valid for simulation
                        
                        # Ensure input exists
                        yaml_input = yaml_data.get("input")
                        if not yaml_input:
                            yaml_input = {"query": query, "suggestion": "Generated automation"}
                        
                        collected = training_data_collector.collect_yaml_data(
                            yaml_pair={
                                "input": yaml_input,
                                "output": yaml_content.strip()
                            },
                            validation_result=yaml_validation,
                            ground_truth=yaml_data.get("ground_truth")
                        )
                        
                        if collected:
                            lineage_tracker.track_data(
                                data_id=f"yaml_{home_id}_{len(training_data_collector.get_collected_data('yaml_generation'))}",
                                data_type="yaml_generation",
                                source_cycle="simulation_run",
                                source_home_id=home_id
                            )
                    else:
                        logger.debug(f"YAML not collected for {home_id}: generated={yaml_generated}, has_content={bool(yaml_content and yaml_content.strip())}")
                
                # Collect Ask AI conversation data
                training_data_collector.collect_ask_ai_data(
                    query=query,
                    response=result,
                    approval=None  # No approval in simulation
                )
                lineage_tracker.track_data(
                    data_id=f"ask_ai_{home_id}_{len(training_data_collector.get_collected_data('ask_ai_conversation'))}",
                    data_type="ask_ai_conversation",
                    source_cycle="simulation_run",
                    source_home_id=home_id
                )
            
            return result
        
        # Process queries for each home
        total_queries_processed = 0
        total_queries_successful = 0
        
        for home in homes:
            home_id = home["home_id"]
            # Generate queries for this home
            queries = [
                {"query": f"Turn on the lights in room {i} for {home_id}"}
                for i in range(queries_count)
            ]
            
            batch_result_ask_ai = await batch_processor.process_queries_batch(
                queries,
                process_ask_ai_query,
                home_id
            )
            
            total_queries_processed += batch_result_ask_ai["total_queries"]
            total_queries_successful += batch_result_ask_ai["successful"]
        
        logger.info(f"Ask AI queries completed: {total_queries_successful}/{total_queries_processed} across {len(homes)} homes")
        
        # Calculate simulation metrics
        simulation_time = time.time() - simulation_start
        summary = aggregator.get_summary()
        
        # Generate simulation summary
        simulation_summary_path = summary_generator.generate_simulation_summary(
            homes_count=len(homes),
            queries_count=queries_count,
            workflow_3am_total=summary["3am_workflows"]["total"],
            workflow_3am_successful=summary["3am_workflows"]["successful"],
            workflow_3am_failed=summary["3am_workflows"]["failed"],
            workflow_3am_avg_duration=summary["3am_workflows"]["avg_duration_seconds"],
            ask_ai_total=total_queries_processed,
            ask_ai_successful=total_queries_successful,
            ask_ai_failed=total_queries_processed - total_queries_successful,
            ask_ai_avg_duration=summary["ask_ai_queries"]["avg_duration_seconds"],
            simulation_time_seconds=simulation_time,
            errors=None  # Could collect errors if needed
        )
        logger.info(f"✅ Simulation complete: {summary['3am_workflows']['successful']}/{summary['3am_workflows']['total']} workflows, {total_queries_successful}/{total_queries_processed} queries")
        
        # Generate reports
        logger.info("Generating reports...")
        summary["metrics"] = metrics_collector.get_summary()
        
        json_report = report_generator.generate_json_report(summary)
        csv_report = report_generator.generate_csv_report(summary)
        
        # Generate HTML report only if requested
        html_report_path = None
        if html_report:
            html_report_path = report_generator.generate_html_report(summary)
            logger.info(f"HTML dashboard report generated: {html_report_path}")
        
        logger.info(f"Reports generated:")
        logger.info(f"  - JSON: {json_report}")
        logger.info(f"  - CSV: {csv_report}")
        if html_report_path:
            logger.info(f"  - HTML: {html_report_path}")
        
        # Export training data (Epic AI-18)
        logger.info("Exporting training data...")
        collection_stats = training_data_collector.get_collection_stats()
        logger.info(f"Training data collected: {collection_stats['total_collected']} items ({collection_stats['total_filtered']} filtered)")
        
        if collection_stats['total_collected'] > 0:
            # Export all collected data by type
            export_results = {}
            collected_data = training_data_collector.get_collected_data()
            
            # Debug: Log what data types we have
            logger.debug(f"Collected data types: {list(collected_data.keys())}")
            for data_type, data_list in collected_data.items():
                logger.debug(f"  {data_type}: {len(data_list)} entries")
            
            # Export each data type if it exists
            if collected_data.get("synergy_detection"):
                try:
                    export_results["synergy_detection"] = [
                        training_data_exporter.export_gnn_synergy_data(collected_data["synergy_detection"], "json")
                    ]
                except Exception as e:
                    logger.error(f"Failed to export synergy_detection: {e}")
            
            if collected_data.get("pattern_detection"):
                try:
                    export_results["pattern_detection"] = [
                        training_data_exporter.export_pattern_detection_data(collected_data["pattern_detection"], "json")
                    ]
                except Exception as e:
                    logger.error(f"Failed to export pattern_detection: {e}")
            
            if collected_data.get("yaml_generation"):
                try:
                    export_results["yaml_generation"] = [
                        training_data_exporter.export_yaml_generation_data(collected_data["yaml_generation"])
                    ]
                except Exception as e:
                    logger.error(f"Failed to export yaml_generation: {e}")
            
            if collected_data.get("suggestion_generation"):
                try:
                    export_results["suggestion_generation"] = [
                        training_data_exporter.export_soft_prompt_data(collected_data["suggestion_generation"], "json")
                    ]
                except Exception as e:
                    logger.error(f"Failed to export suggestion_generation: {e}")
            
            if collected_data.get("ask_ai_conversation"):
                try:
                    export_results["ask_ai_conversation"] = [
                        training_data_exporter.export_device_intelligence_data(collected_data["ask_ai_conversation"], "json")
                    ]
                except Exception as e:
                    logger.error(f"Failed to export ask_ai_conversation: {e}")
            
            logger.info(f"Training data exported:")
            for data_type, export_paths in export_results.items():
                logger.info(f"  - {data_type}: {len(export_paths)} files")
                for path in export_paths:
                    logger.info(f"    - {path}")
            
            # Log what wasn't exported
            exported_types = set(export_results.keys())
            collected_types = set(k for k, v in collected_data.items() if v)
            missing = collected_types - exported_types
            if missing:
                logger.warning(f"Data types collected but not exported: {missing}")
        else:
            logger.warning("No training data collected - simulation may not have generated collectable data")
        
        # Generate pipeline summary combining all phases
        pipeline_summary_path = summary_generator.generate_pipeline_summary(
            data_creation_summary_path=data_creation_summary_path,
            simulation_summary_path=simulation_summary_path,
            training_summaries=None  # Training summaries would be added if training runs
        )
        logger.info(f"✅ Pipeline summary generated: {pipeline_summary_path}")
        
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
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="WARNING",
        help="Console log level (default: WARNING - only warnings and errors shown)"
    )
    parser.add_argument(
        "--html-report",
        action="store_true",
        help="Generate HTML dashboard report (default: disabled)"
    )
    
    args = parser.parse_args()
    
    asyncio.run(run_simulation(
        mode=args.mode,
        homes_count=args.homes,
        queries_count=args.queries,
        output_dir=args.output_dir,
        log_level=args.log_level,
        html_report=args.html_report
    ))


if __name__ == "__main__":
    main()

