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
        try:
            with open(self.log_file, 'w', encoding='utf-8') as f:
                f.write(f"=== Zapret GUI Log - Started {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===\n\n")
        except Exception as e:
            print(f"Error creating log file: {str(e)}")
        
        # Store original stdout and stderr - with safety checks
        try:
            self.orig_stdout = sys.stdout if hasattr(sys.stdout, 'write') else None
            self.orig_stderr = sys.stderr if hasattr(sys.stderr, 'write') else None
        except Exception:
            # In case of any error, set them to None
            self.orig_stdout = None
            self.orig_stderr = None
        
        # Replace stdout and stderr with our custom writers
        try:
            sys.stdout = self
            sys.stderr = self
        except Exception as e:
            print(f"Error redirecting stdout/stderr: {str(e)}")
    
    def write(self, message):
        """Write to the log file and the original stdout"""
        # Write to the original stdout if it exists
        if self.orig_stdout is not None:
            try:
                self.orig_stdout.write(message)
            except Exception:
                # If writing to stdout fails, just ignore it
                pass
        
        # Write to the log file
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                timestamp = datetime.now().strftime('%H:%M:%S')
                f.write(f"[{timestamp}] {message}")
        except Exception as e:
            # If we can't write to the log file and have stderr, try to write there
            if self.orig_stderr is not None:
                try:
                    self.orig_stderr.write(f"Error writing to log: {str(e)}\n")
                except Exception:
                    pass
    
    def flush(self):
        """Flush the output streams"""
        if self.orig_stdout is not None:
            try:
                self.orig_stdout.flush()
            except Exception:
                pass
        
        if self.orig_stderr is not None:
            try:
                self.orig_stderr.flush()
            except Exception:
                pass
    
    def log(self, message, level="INFO"):
        """Log a message with a level prefix"""
        try:
            self.write(f"[{level}] {message}\n")
        except Exception as e:
            # Last resort - attempt direct write to the log file
            try:
                with open(self.log_file, 'a', encoding='utf-8') as f:
                    timestamp = datetime.now().strftime('%H:%M:%S')
                    f.write(f"[{timestamp}] [ERROR] Logger error: {str(e)}\n")
                    f.write(f"[{timestamp}] [{level}] {message}\n")
            except Exception:
                pass
    
    def log_exception(self, e, context=""):
        """Log an exception with its traceback"""
        try:
            tb = traceback.format_exc()
            self.write(f"[ERROR] Exception in {context}: {str(e)}\n{tb}\n")
        except Exception:
            # Last resort - direct write
            try:
                with open(self.log_file, 'a', encoding='utf-8') as f:
                    timestamp = datetime.now().strftime('%H:%M:%S')
                    f.write(f"[{timestamp}] [ERROR] Exception in {context}: {str(e)}\n")
                    f.write(f"[{timestamp}] {traceback.format_exc()}\n")
            except Exception:
                pass
    
    def get_log_content(self):
        """Return the content of the log file"""
        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            return f"Error reading log: {str(e)}"

# Create a global logger instance - with error handling
try:
    global_logger = Logger()
except Exception as setup_error:
    # If logger creation fails, create a minimalist fallback
    class FallbackLogger:
        def log(self, message, level="INFO"):
            pass
        def log_exception(self, e, context=""):
            pass
        def get_log_content(self):
            return "Logging system initialization failed."
    
    global_logger = FallbackLogger()

# Helper functions that can be imported anywhere - with error handling
def log(message, level="INFO"):
    try:
        global_logger.log(message, level)
    except Exception:
        # If all else fails, do nothing
        pass

def log_exception(e, context=""):
    try:
        global_logger.log_exception(e, context)
    except Exception:
        # If all else fails, do nothing
        pass

def get_log_content():
    try:
        return global_logger.get_log_content()
    except Exception as e:
        return f"Error retrieving log content: {str(e)}"