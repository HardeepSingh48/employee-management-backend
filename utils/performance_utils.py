"""
Performance monitoring utilities for bulk operations
"""
import time
import gc
from functools import wraps
import logging

logger = logging.getLogger(__name__)

# Optional psutil import for memory monitoring
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False
    logger.warning("psutil not available - memory monitoring disabled")

class PerformanceMonitor:
    """Monitor performance metrics during bulk operations"""

    def __init__(self):
        self.start_time = None
        self.start_memory = None
        self.checkpoints = []

    def start(self):
        """Start performance monitoring"""
        self.start_time = time.time()
        if HAS_PSUTIL:
            self.start_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        else:
            self.start_memory = 0
        self.checkpoints = []
        logger.info(".2f")

    def checkpoint(self, name):
        """Record a performance checkpoint"""
        if self.start_time is None:
            return

        current_time = time.time()
        if HAS_PSUTIL:
            current_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
            memory_delta = current_memory - self.start_memory
        else:
            current_memory = 0
            memory_delta = 0

        elapsed = current_time - self.start_time

        checkpoint_data = {
            'name': name,
            'elapsed_seconds': elapsed,
            'memory_mb': current_memory,
            'memory_delta_mb': memory_delta
        }

        self.checkpoints.append(checkpoint_data)
        logger.info(".2f")

    def get_summary(self):
        """Get performance summary"""
        if self.start_time is None:
            return {}

        total_time = time.time() - self.start_time
        if HAS_PSUTIL:
            end_memory = psutil.Process().memory_info().rss / 1024 / 1024
            memory_delta = end_memory - self.start_memory
        else:
            end_memory = 0
            memory_delta = 0

        return {
            'total_time_seconds': total_time,
            'memory_start_mb': self.start_memory,
            'memory_end_mb': end_memory,
            'memory_delta_mb': memory_delta,
            'checkpoints': self.checkpoints
        }

def performance_monitor(operation_name="operation"):
    """Decorator to monitor performance of functions"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            monitor = PerformanceMonitor()
            monitor.start()

            try:
                result = func(*args, **kwargs)
                monitor.checkpoint("completed")
                return result
            except Exception as e:
                monitor.checkpoint("failed")
                raise e
            finally:
                summary = monitor.get_summary()
                logger.info(f"Performance summary for {operation_name}: {summary}")

        return wrapper
    return decorator

def memory_efficient_gc(memory_threshold_mb=500):
    """Trigger garbage collection if memory usage is high"""
    if not HAS_PSUTIL:
        gc.collect()  # Always collect if psutil not available
        return

    current_memory = psutil.Process().memory_info().rss / 1024 / 1024

    if current_memory > memory_threshold_mb:
        logger.info(".2f")
        gc.collect()
        after_gc = psutil.Process().memory_info().rss / 1024 / 1024
        logger.info(".2f")

def optimize_dataframe_memory(df):
    """Optimize DataFrame memory usage"""
    start_memory = df.memory_usage(deep=True).sum() / 1024 / 1024

    # Convert object columns to category if they have few unique values
    for col in df.select_dtypes(include=['object']):
        if df[col].nunique() / len(df) < 0.5:  # Less than 50% unique values
            df[col] = df[col].astype('category')

    # Downcast numeric types
    for col in df.select_dtypes(include=['int64']):
        df[col] = pd.to_numeric(df[col], downcast='integer')

    for col in df.select_dtypes(include=['float64']):
        df[col] = pd.to_numeric(df[col], downcast='float')

    end_memory = df.memory_usage(deep=True).sum() / 1024 / 1024
    savings = start_memory - end_memory

    if savings > 0:
        logger.info(".2f")

    return df