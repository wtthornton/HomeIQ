"""
Logging Configuration

Configure logging with separate console and file handlers.
Console shows only WARNING/ERROR, detailed logs go to files.
"""

import logging
import sys
from pathlib import Path
from typing import Literal


def setup_logging(
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "WARNING",
    log_dir: Path | None = None,
    log_to_file: bool = True
) -> None:
    """
    Setup logging configuration.
    
    Args:
        log_level: Console log level (default: WARNING - only warnings and errors)
        log_dir: Directory for log files (if None, logs go to current directory)
        log_to_file: Whether to write detailed logs to files
    """
    # Remove existing handlers
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    
    # Set root logger level to DEBUG (we'll filter per handler)
    root_logger.setLevel(logging.DEBUG)
    
    # Console handler - only WARNING and ERROR
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level))
    console_formatter = logging.Formatter(
        "%(levelname)s: %(message)s"
    )
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # File handler - all levels (if enabled)
    if log_to_file and log_dir:
        log_dir = Path(log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # Create separate log files for different phases
        file_handlers = {
            "pipeline": log_dir / "pipeline.log",
            "data_creation": log_dir / "data_creation.log",
            "simulation": log_dir / "simulation.log",
            "training": log_dir / "training.log"
        }
        
        for phase, log_file in file_handlers.items():
            file_handler = logging.FileHandler(log_file, mode="a")
            file_handler.setLevel(logging.DEBUG)
            file_formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            file_handler.setFormatter(file_formatter)
            
            # Add filter to only log messages from relevant modules
            if phase == "pipeline":
                # Pipeline log gets everything
                root_logger.addHandler(file_handler)
            else:
                # Phase-specific logs get filtered messages
                phase_handler = logging.FileHandler(log_file, mode="a")
                phase_handler.setLevel(logging.DEBUG)
                phase_handler.setFormatter(file_formatter)
                # We'll use logger names to filter, but for now add to root
                # In practice, you'd create phase-specific loggers
                root_logger.addHandler(phase_handler)
    
    # Create a simple handler for all file logging (simpler approach)
    if log_to_file and log_dir:
        log_dir = Path(log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # Single detailed log file
        detailed_log_file = log_dir / "detailed.log"
        file_handler = logging.FileHandler(detailed_log_file, mode="a")
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)

