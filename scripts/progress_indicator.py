#!/usr/bin/env python3
"""
Progress Indicator Utility
Provides visual feedback for long-running operations in terminal scripts.
"""

import sys
import time
import threading
from typing import Optional, Callable
from contextlib import contextmanager


class Spinner:
    """Animated spinner for operations without clear progress."""
    
    SPINNER_FRAMES = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
    
    def __init__(self, message: str = "Processing", delay: float = 0.1):
        self.message = message
        self.delay = delay
        self.spinner_thread = None
        self.stop_spinner = False
        self.start_time = None
        
    def _spin(self):
        """Internal spinner animation loop."""
        frame_idx = 0
        while not self.stop_spinner:
            elapsed = time.time() - self.start_time
            elapsed_str = f"{elapsed:.1f}s" if elapsed < 60 else f"{elapsed/60:.1f}m"
            frame = self.SPINNER_FRAMES[frame_idx % len(self.SPINNER_FRAMES)]
            sys.stdout.write(f'\r{frame} {self.message}... ({elapsed_str})')
            sys.stdout.flush()
            frame_idx += 1
            time.sleep(self.delay)
    
    def start(self):
        """Start the spinner."""
        self.start_time = time.time()
        self.stop_spinner = False
        self.spinner_thread = threading.Thread(target=self._spin, daemon=True)
        self.spinner_thread.start()
    
    def stop(self, success: bool = True, message: Optional[str] = None):
        """Stop the spinner and show final message."""
        self.stop_spinner = True
        if self.spinner_thread:
            self.spinner_thread.join(timeout=0.5)
        
        elapsed = time.time() - self.start_time if self.start_time else 0
        elapsed_str = f"{elapsed:.1f}s" if elapsed < 60 else f"{elapsed/60:.1f}m"
        
        icon = "✅" if success else "❌"
        final_message = message or self.message
        sys.stdout.write(f'\r{icon} {final_message} ({elapsed_str})\n')
        sys.stdout.flush()
    
    @contextmanager
    def context(self, message: Optional[str] = None):
        """Context manager for spinner."""
        if message:
            self.message = message
        self.start()
        try:
            yield self
            self.stop(success=True)
        except Exception as e:
            self.stop(success=False, message=f"{self.message} - Error: {str(e)}")
            raise


class ProgressBar:
    """Progress bar for operations with known totals."""
    
    def __init__(self, total: int, message: str = "Progress", width: int = 40):
        self.total = total
        self.current = 0
        self.message = message
        self.width = width
        self.start_time = time.time()
        
    def update(self, value: int = None, increment: int = 1):
        """Update progress bar."""
        if value is not None:
            self.current = min(value, self.total)
        else:
            self.current = min(self.current + increment, self.total)
        
        percentage = (self.current / self.total) * 100
        filled = int(self.width * self.current / self.total)
        bar = '█' * filled + '░' * (self.width - filled)
        
        elapsed = time.time() - self.start_time
        elapsed_str = f"{elapsed:.1f}s" if elapsed < 60 else f"{elapsed/60:.1f}m"
        
        if self.current < self.total:
            # Estimate remaining time
            if self.current > 0:
                rate = elapsed / self.current
                remaining = (self.total - self.current) * rate
                remaining_str = f"{remaining:.1f}s" if remaining < 60 else f"{remaining/60:.1f}m"
                eta = f"ETA: {remaining_str}"
            else:
                eta = "ETA: calculating..."
        else:
            eta = "Complete"
        
        sys.stdout.write(f'\r{self.message}: [{bar}] {self.current}/{self.total} ({percentage:.1f}%) | {elapsed_str} | {eta}')
        sys.stdout.flush()
    
    def finish(self, message: Optional[str] = None):
        """Finish the progress bar."""
        self.current = self.total
        self.update()
        elapsed = time.time() - self.start_time
        elapsed_str = f"{elapsed:.1f}s" if elapsed < 60 else f"{elapsed/60:.1f}m"
        final_message = message or self.message
        sys.stdout.write(f'\r✅ {final_message} ({elapsed_str})\n')
        sys.stdout.flush()


class StatusUpdater:
    """Status updater for operations with status messages."""
    
    def __init__(self, message: str = "Status"):
        self.message = message
        self.start_time = time.time()
        self.last_update = None
        
    def update(self, status: str, show_elapsed: bool = True):
        """Update status message."""
        elapsed = time.time() - self.start_time
        elapsed_str = f" ({elapsed:.1f}s)" if show_elapsed and elapsed > 0 else ""
        sys.stdout.write(f'\r🔄 {self.message}: {status}{elapsed_str}')
        sys.stdout.flush()
        self.last_update = status
    
    def finish(self, success: bool = True, message: Optional[str] = None):
        """Finish status update."""
        elapsed = time.time() - self.start_time
        elapsed_str = f"{elapsed:.1f}s" if elapsed < 60 else f"{elapsed/60:.1f}m"
        icon = "✅" if success else "❌"
        final_message = message or self.last_update or self.message
        sys.stdout.write(f'\r{icon} {final_message} ({elapsed_str})\n')
        sys.stdout.flush()


class StepTracker:
    """Track multi-step operations with visual feedback."""
    
    def __init__(self, total_steps: int, step_name: str = "Step"):
        self.total_steps = total_steps
        self.current_step = 0
        self.step_name = step_name
        self.start_time = time.time()
        
    def start_step(self, step_number: int, step_message: str):
        """Start a new step."""
        self.current_step = step_number
        elapsed = time.time() - self.start_time
        elapsed_str = f"{elapsed:.1f}s" if elapsed < 60 else f"{elapsed/60:.1f}m"
        sys.stdout.write(f'\n[{step_number}/{self.total_steps}] {step_message}...\n')
        sys.stdout.flush()
    
    def update_step(self, message: str):
        """Update current step status."""
        sys.stdout.write(f'  → {message}\n')
        sys.stdout.flush()
    
    def finish_step(self, success: bool = True, message: Optional[str] = None):
        """Finish current step."""
        icon = "✅" if success else "❌"
        step_elapsed = time.time() - self.start_time
        step_elapsed_str = f"{step_elapsed:.1f}s" if step_elapsed < 60 else f"{step_elapsed/60:.1f}m"
        final_message = message or f"{self.step_name} {self.current_step} completed"
        sys.stdout.write(f'  {icon} {final_message} ({step_elapsed_str})\n')
        sys.stdout.flush()
    
    def finish_all(self):
        """Finish all steps."""
        total_elapsed = time.time() - self.start_time
        total_elapsed_str = f"{total_elapsed:.1f}s" if total_elapsed < 60 else f"{total_elapsed/60:.1f}m"
        sys.stdout.write(f'\n🎉 All {self.total_steps} steps completed in {total_elapsed_str}\n')
        sys.stdout.flush()


def print_step_header(step_num: int, total_steps: int, title: str):
    """Print a formatted step header."""
    sys.stdout.write(f'\n{"="*80}\n')
    sys.stdout.write(f'STEP {step_num}/{total_steps}: {title}\n')
    sys.stdout.write(f'{"="*80}\n')
    sys.stdout.flush()

