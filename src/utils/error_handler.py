"""
Enhanced Error Handling for AccessHelp
Provides graceful error recovery and logging
"""

import sys
import traceback
import logging
from datetime import datetime
import os
import json

# Setup logging
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'logs')
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, f'accesshelp_{datetime.now().strftime("%Y%m%d")}.log')),
        logging.StreamHandler()
    ]
)

class ErrorHandler:
    """Centralized error handling with recovery strategies"""
    
    def __init__(self):
        self.error_log = []
        self.recovery_strategies = {}
        self.setup_recovery_strategies()
    
    def setup_recovery_strategies(self):
        """Define recovery strategies for different error types"""
        self.recovery_strategies = {
            'ImportError': self._handle_import_error,
            'ModuleNotFoundError': self._handle_module_error,
            'ConnectionError': self._handle_connection_error,
            'TimeoutError': self._handle_timeout_error,
            'PermissionError': self._handle_permission_error,
            'FileNotFoundError': self._handle_file_error,
            'ValueError': self._handle_value_error,
            'Exception': self._handle_general_error
        }
    
    def handle_error(self, error, context=None):
        """Handle error with appropriate recovery strategy"""
        error_type = type(error).__name__
        error_msg = str(error)
        stack_trace = traceback.format_exc()
        
        # Log error
        self._log_error(error_type, error_msg, stack_trace, context)
        
        # Get recovery strategy
        strategy = self.recovery_strategies.get(error_type, self._handle_general_error)
        
        # Attempt recovery
        try:
            recovery_result = strategy(error, context)
            return recovery_result
        except Exception as recovery_error:
            # If recovery fails, log and return fallback
            logging.error(f"Recovery failed: {recovery_error}")
            return self._get_fallback_response(error_type)
    
    def _log_error(self, error_type, error_msg, stack_trace, context):
        """Log error to file and memory"""
        error_entry = {
            'timestamp': datetime.now().isoformat(),
            'type': error_type,
            'message': error_msg,
            'traceback': stack_trace,
            'context': context
        }
        
        self.error_log.append(error_entry)
        
        # Keep only last 100 errors
        if len(self.error_log) > 100:
            self.error_log = self.error_log[-100:]
        
        # Log to file
        logging.error(f"{error_type}: {error_msg}")
        if context:
            logging.error(f"Context: {context}")
        logging.debug(stack_trace)
    
    def _handle_import_error(self, error, context):
        """Handle missing module errors"""
        module_name = str(error).split("'")[1] if "'" in str(error) else "unknown"
        
        return {
            'status': 'error',
            'message': f"Missing required module: {module_name}",
            'action': 'install_module',
            'module': module_name,
            'fallback': True
        }
    
    def _handle_module_error(self, error, context):
        """Handle module not found errors"""
        return self._handle_import_error(error, context)
    
    def _handle_connection_error(self, error, context):
        """Handle network connection errors"""
        return {
            'status': 'warning',
            'message': "Network connection error",
            'action': 'retry_later',
            'fallback': 'offline_mode'
        }
    
    def _handle_timeout_error(self, error, context):
        """Handle timeout errors"""
        return {
            'status': 'warning',
            'message': "Operation timed out",
            'action': 'retry',
            'fallback': 'skip'
        }
    
    def _handle_permission_error(self, error, context):
        """Handle permission errors"""
        return {
            'status': 'error',
            'message': "Permission denied. Try running with appropriate permissions.",
            'action': 'check_permissions',
            'fallback': True
        }
    
    def _handle_file_error(self, error, context):
        """Handle file not found errors"""
        return {
            'status': 'warning',
            'message': f"File not found: {error}",
            'action': 'create_file',
            'fallback': True
        }
    
    def _handle_value_error(self, error, context):
        """Handle value errors"""
        return {
            'status': 'error',
            'message': f"Invalid value: {error}",
            'action': 'validate_input',
            'fallback': True
        }
    
    def _handle_general_error(self, error, context):
        """Handle any other errors"""
        return {
            'status': 'error',
            'message': f"An error occurred: {error}",
            'action': 'report_bug',
            'fallback': True
        }
    
    def _get_fallback_response(self, error_type):
        """Get fallback response for unrecoverable errors"""
        fallbacks = {
            'ImportError': "Using fallback mode. Please install required modules.",
            'ConnectionError': "Working in offline mode. Some features may be limited.",
            'TimeoutError': "Operation skipped due to timeout.",
            'PermissionError': "Unable to complete operation due to permissions.",
            'FileNotFoundError': "Creating default file.",
            'default': "Operation failed. Please try again or contact support."
        }
        
        return {
            'status': 'fallback',
            'message': fallbacks.get(error_type, fallbacks['default'])
        }
    
    def get_error_report(self):
        """Generate error report for debugging"""
        return {
            'total_errors': len(self.error_log),
            'errors_by_type': self._group_errors_by_type(),
            'recent_errors': self.error_log[-10:],
            'system_info': self._get_system_info()
        }
    
    def _group_errors_by_type(self):
        """Group errors by type"""
        error_counts = {}
        for error in self.error_log:
            error_type = error['type']
            error_counts[error_type] = error_counts.get(error_type, 0) + 1
        return error_counts
    
    def _get_system_info(self):
        """Get system information for debugging"""
        import platform
        
        return {
            'platform': platform.platform(),
            'python_version': platform.python_version(),
            'processor': platform.processor(),
            'architecture': platform.architecture()
        }

# Global error handler instance
error_handler = ErrorHandler()

def safe_execute(func, *args, **kwargs):
    """Decorator for safe function execution with error handling"""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            return error_handler.handle_error(e, {'function': func.__name__})
    return wrapper