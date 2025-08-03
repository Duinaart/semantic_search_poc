"""
Performance Tracing Module

Provides decorators and context managers to trace execution time
of different components in the semantic search application.
"""

import time
import logging
import functools
from contextlib import contextmanager
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from datetime import datetime
import json


@dataclass
class TraceSpan:
    """Represents a traced operation."""
    name: str
    start_time: float
    end_time: Optional[float] = None
    duration: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def finish(self):
        """Mark the span as finished and calculate duration."""
        self.end_time = time.time()
        self.duration = self.end_time - self.start_time
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'name': self.name,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'duration_ms': round(self.duration * 1000, 2) if self.duration else None,
            'metadata': self.metadata
        }


class PerformanceTracer:
    """Central performance tracer for collecting timing information."""
    
    def __init__(self):
        self.spans: List[TraceSpan] = []
        self.current_request_id: Optional[str] = None
        self.logger = logging.getLogger('performance_tracer')
        
    def start_request(self, request_id: str = None) -> str:
        """Start a new request trace."""
        if request_id is None:
            request_id = f"req_{int(time.time() * 1000)}"
        self.current_request_id = request_id
        self.spans = []  # Reset spans for new request
        return request_id
    
    def create_span(self, name: str, metadata: Dict[str, Any] = None) -> TraceSpan:
        """Create a new trace span."""
        span = TraceSpan(
            name=name,
            start_time=time.time(),
            metadata=metadata or {}
        )
        self.spans.append(span)
        return span
    
    @contextmanager
    def trace(self, operation_name: str, **metadata):
        """Context manager for tracing operations."""
        span = self.create_span(operation_name, metadata)
        try:
            yield span
        finally:
            span.finish()
            
    def get_trace_summary(self) -> Dict[str, Any]:
        """Get a summary of all traced operations for the current request."""
        if not self.spans:
            return {}
            
        total_time = sum(span.duration for span in self.spans if span.duration)
        
        summary = {
            'request_id': self.current_request_id,
            'total_duration_ms': round(total_time * 1000, 2),
            'operations': [span.to_dict() for span in self.spans],
            'breakdown': {}
        }
        
        # Create breakdown by operation type
        for span in self.spans:
            if span.duration:
                summary['breakdown'][span.name] = round(span.duration * 1000, 2)
                
        return summary
    
    def log_summary(self, level: int = logging.INFO):
        """Log the trace summary."""
        summary = self.get_trace_summary()
        if summary:
            self.logger.log(level, f"Performance Summary: {json.dumps(summary, indent=2)}")
    
    def print_summary(self):
        """Print a formatted trace summary to console."""
        summary = self.get_trace_summary()
        if not summary:
            print("No performance data available")
            return
            
        print(f"\n{'='*60}")
        print(f"PERFORMANCE TRACE SUMMARY - Request {summary['request_id']}")
        print(f"{'='*60}")
        print(f"Total Duration: {summary['total_duration_ms']:.2f}ms")
        print(f"\nBreakdown by Operation:")
        print(f"{'Operation':<30} {'Duration (ms)':<15} {'%':<10}")
        print(f"{'-'*55}")
        
        total_ms = summary['total_duration_ms']
        for op_name, duration_ms in summary['breakdown'].items():
            percentage = (duration_ms / total_ms * 100) if total_ms > 0 else 0
            print(f"{op_name:<30} {duration_ms:<15.2f} {percentage:<10.1f}%")
            
        print(f"\nDetailed Timeline:")
        for op in summary['operations']:
            metadata_str = ""
            if op['metadata']:
                metadata_str = f" | {json.dumps(op['metadata'])}"
            print(f"  {op['name']}: {op['duration_ms']:.2f}ms{metadata_str}")
        print(f"{'='*60}\n")


# Global tracer instance
tracer = PerformanceTracer()


def trace_function(operation_name: str = None, include_args: bool = False):
    """Decorator to trace function execution time."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            name = operation_name or f"{func.__module__}.{func.__name__}"
            metadata = {}
            
            if include_args:
                # Be careful not to log sensitive data
                safe_args = []
                for arg in args:
                    if isinstance(arg, (str, int, float, bool)):
                        if isinstance(arg, str) and len(arg) > 100:
                            safe_args.append(arg[:100] + "...")
                        else:
                            safe_args.append(arg)
                    else:
                        safe_args.append(type(arg).__name__)
                        
                metadata['args'] = safe_args
                metadata['kwargs'] = {k: v for k, v in kwargs.items() 
                                    if isinstance(v, (str, int, float, bool))}
            
            with tracer.trace(name, **metadata):
                return func(*args, **kwargs)
        return wrapper
    return decorator


@contextmanager
def trace_operation(name: str, **metadata):
    """Standalone context manager for tracing operations."""
    with tracer.trace(name, **metadata) as span:
        yield span


# Convenience functions
def start_request_trace(request_id: str = None) -> str:
    """Start tracing a new request."""
    return tracer.start_request(request_id)


def print_trace_summary():
    """Print the current trace summary."""
    tracer.print_summary()


def get_trace_summary() -> Dict[str, Any]:
    """Get the current trace summary as a dictionary."""
    return tracer.get_trace_summary()


# Example usage and testing
if __name__ == "__main__":
    # Example of how to use the tracer
    start_request_trace("test_request")
    
    @trace_function("test_operation")
    def slow_operation(duration: float):
        time.sleep(duration)
        return "completed"
    
    with trace_operation("manual_trace", operation_type="test"):
        time.sleep(0.1)
        
    slow_operation(0.2)
    
    with trace_operation("another_operation"):
        time.sleep(0.05)
        
    print_trace_summary()