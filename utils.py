import logging
import functools
import time
import asyncio
from datetime import date
import os

def setup_logger(name):
    """Configure logger with standard format"""
    logger = logging.getLogger(name)
    
    # Si el logger ya tiene handlers, asumimos que ya está configurado
    if logger.handlers:
        return logger
        
    logger.setLevel(logging.INFO)
    
    # Crear directorio de logs si no existe
    log_file = f"logs/video_generation_{date.today().strftime('%Y%m%d')}.log"
    os.makedirs('logs', exist_ok=True)
    
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_formatter = logging.Formatter('%(message)s')
    
    # File Handler
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setFormatter(formatter)
    
    # Console Handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(console_formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    # Evitar la propagación de logs a loggers padre
    logger.propagate = False
    
    return logger

def retry_on_429(max_retries=3, delay=5):
    """Decorator for retrying functions on 429 errors"""
    def decorator(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            logger = logging.getLogger(func.__module__)
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    if '429' in str(e) and attempt < max_retries - 1:
                        logger.warning(f"Rate limit hit, retrying in {delay} seconds... (attempt {attempt + 1}/{max_retries})")
                        await asyncio.sleep(delay)
                        continue
                    raise
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            logger = logging.getLogger(func.__module__)
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if '429' in str(e) and attempt < max_retries - 1:
                        logger.warning(f"Rate limit hit, retrying in {delay} seconds... (attempt {attempt + 1}/{max_retries})")
                        time.sleep(delay)
                        continue
                    raise
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator
