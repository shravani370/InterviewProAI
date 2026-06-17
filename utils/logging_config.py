"""
Structured logging configuration for production
Logs in JSON format for easy parsing by ELK/Splunk/CloudWatch
"""
import logging
import sys
import json
from pythonjsonlogger import jsonlogger
from io import StringIO
import os

def setup_logging(app=None):
    """
    Setup structured JSON logging for the application
    """
    # Create logs directory if it doesn't exist
    os.makedirs("logs", exist_ok=True)
    
    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    
    # JSON formatter for structured logging
    json_formatter = jsonlogger.JsonFormatter(
        fmt='%(timestamp)s %(level)s %(name)s %(message)s',
        timestamp=True,
    )
    
    # Console handler (for dev/debugging)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(json_formatter)
    root_logger.addHandler(console_handler)
    
    # File handler (for production)
    file_handler = logging.FileHandler("logs/app.log")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(json_formatter)
    root_logger.addHandler(file_handler)
    
    # Database query logging (info level to reduce noise)
    sqlalchemy_logger = logging.getLogger('sqlalchemy.engine')
    sqlalchemy_logger.setLevel(logging.INFO)
    
    # Flask logger
    if app:
        app.logger.setLevel(logging.INFO)
        app.logger.addHandler(console_handler)
        app.logger.addHandler(file_handler)
    
    logging.info("✅ Structured logging initialized")

def get_logger(name):
    """Get a logger instance with the given name"""
    return logging.getLogger(name)
