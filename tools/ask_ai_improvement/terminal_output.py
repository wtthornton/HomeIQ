"""
Terminal output helpers for formatted console output.
"""
import logging

# Configure logging with better formatting
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


class TerminalOutput:
    """Helper class for formatted terminal output"""
    
    @staticmethod
    def print_header(text: str, char: str = "="):
        """Print a formatted header"""
        width = 80
        logger.info("")
        logger.info(char * width)
        logger.info(f"  {text}")
        logger.info(char * width)
    
    @staticmethod
    def print_step(step_num: int, total_steps: int, description: str):
        """Print a step indicator"""
        logger.info(f"\n[Step {step_num}/{total_steps}] {description}")
        logger.info("-" * 80)
    
    @staticmethod
    def print_status(status: str, message: str, indent: int = 0):
        """Print a status message"""
        prefix = "  " * indent
        logger.info(f"{prefix}[{status}] {message}")
    
    @staticmethod
    def print_success(message: str, indent: int = 0):
        """Print a success message"""
        TerminalOutput.print_status("✓", message, indent)
    
    @staticmethod
    def print_error(message: str, indent: int = 0):
        """Print an error message"""
        TerminalOutput.print_status("✗", message, indent)
    
    @staticmethod
    def print_warning(message: str, indent: int = 0):
        """Print a warning message"""
        TerminalOutput.print_status("!", message, indent)
    
    @staticmethod
    def print_info(message: str, indent: int = 0):
        """Print an info message"""
        TerminalOutput.print_status("i", message, indent)
    
    @staticmethod
    def print_progress(current: int, total: int, description: str = ""):
        """Print progress indicator"""
        percentage = int((current / total) * 100) if total > 0 else 0
        bar_length = 40
        filled = int(bar_length * current / total) if total > 0 else 0
        bar = "█" * filled + "░" * (bar_length - filled)
        logger.info(f"\r  [{bar}] {percentage:3d}% {description}", end="", flush=True)
        if current >= total:
            logger.info("")  # New line when complete

