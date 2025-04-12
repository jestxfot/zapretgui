import os
import sys
import time
import traceback
from datetime import datetime

class Logger:
    """Simple logging system that captures console output and errors to a file"""
    
    def __init__(self, log_file_path=None):
        """Initialize the logger with optional log file path"""
        if log_file_path is None:
            # Default log file in the same directory as the executable
            base_dir = os.path.dirname(os.path.abspath(sys.executable if getattr(sys, 'frozen', False) else __file__))
            self.log_file = os.path.join(base_dir, "zapret_log.txt")
        else:
            self.log_file = log_file_path
            
        # Ensure the directory exists
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
        
        # Create or truncate the log file with a header
        with open(self.log_file, 'w', encoding='utf-8') as f:
            f.write(f"=== Zapret GUI Log - Started {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===\n\n")
        
        # Store original stdout and stderr
        self.orig_stdout = sys.stdout
        self.orig_stderr = sys.stderr
        
        # Replace stdout and stderr with our custom writers
        sys.stdout = self
        sys.stderr = self
    
    def write(self, message):
        """Write to the log file and the original stdout"""
        # Write to the original stdout
        self.orig_stdout.write(message)
        
        # Write to the log file
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                timestamp = datetime.now().strftime('%H:%M:%S')
                f.write(f"[{timestamp}] {message}")
        except Exception as e:
            # If we can't write to the log file, write to the original stderr
            self.orig_stderr.write(f"Error writing to log: {str(e)}\n")
    
    def flush(self):
        """Flush the output streams"""
        self.orig_stdout.flush()
        self.orig_stderr.flush()
    
    def log(self, message, level="INFO"):
        """Log a message with a level prefix"""
        self.write(f"[{level}] {message}\n")
    
    def log_exception(self, e, context=""):
        """Log an exception with its traceback"""
        tb = traceback.format_exc()
        self.write(f"[ERROR] Exception in {context}: {str(e)}\n{tb}\n")
    
    def get_log_content(self):
        """Return the content of the log file"""
        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            return f"Error reading log: {str(e)}"

# Create a global logger instance
global_logger = Logger()

# Helper functions that can be imported anywhere
def log(message, level="INFO"):
    global_logger.log(message, level)

def log_exception(e, context=""):
    global_logger.log_exception(e, context)

def get_log_content():
    return global_logger.get_log_content()