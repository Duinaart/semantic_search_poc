# Performance Tracing System

This document explains how to use the performance tracing system to identify bottlenecks in your semantic search application.

## Overview

The performance tracing system has been integrated into your codebase to measure execution time for different components:

- **Flask Request Processing** - Overall request handling
- **Query Transformation** - LLM API calls and response parsing  
- **Elasticsearch Queries** - Database query execution
- **Result Formatting** - JSON response preparation

## Quick Start

### 1. Using the Web Interface

The Flask app now automatically includes performance data in API responses:

```bash
# Start your app
uv run python app.py

# Make a request to http://localhost:8082/api/search
# The response will include a 'performance' field with timing data
```

### 2. Command Line Testing

Use the performance testing script for detailed analysis:

```bash
# Test a single query
uv run python test_performance.py query "European banks with high dividends"

# Test with multiple iterations for averaging
uv run python test_performance.py query "Technology companies" 5

# Test individual components
uv run python test_performance.py components

# Benchmark different models
uv run python test_performance.py benchmark

# Interactive testing mode
uv run python test_performance.py interactive
```

## Understanding the Output

### Console Output Example

```
============================================================
PERFORMANCE TRACE SUMMARY - Request req_1703123456789
============================================================
Total Duration: 2847.32ms

Breakdown by Operation:
Operation                      Duration (ms)   %         
-------------------------------------------------------
llm_api_call                   2654.12         93.2%
elasticsearch_http_request     145.23          5.1%
result_formatting              35.67           1.3%
llm_response_parsing           8.45            0.3%
request_parsing               3.85            0.1%

Detailed Timeline:
  request_parsing: 3.85ms | {"query_length": 42}
  llm_prompt_preparation: 1.23ms | {"query_length": 42, "model": "gpt-4o-mini"}
  llm_api_call: 2654.12ms | {"model": "gpt-4o-mini", "prompt_tokens": 2847, "query_preview": "European banks with high dividends"}
  llm_response_parsing: 8.45ms | {"response_length": 487}
  elasticsearch_request_preparation: 2.34ms | {"query_size": 234, "query_type": "dict_keys(['bool'])"}
  elasticsearch_http_request: 145.23ms | {"url": "http://localhost:9200/stocks/_search", "query_complexity": 298}
  elasticsearch_response_parsing: 12.56ms | {"status_code": 200, "response_size": 15678}
  result_formatting: 35.67ms | {"result_count": 8}
  response_preparation: 2.89ms
============================================================
```

### API Response Example

```json
{
  "description": "Searching for European banks with high dividend yields...",
  "query": { "query": { "bool": { ... } } },
  "results": [...],
  "performance": {
    "request_id": "req_1703123456789",
    "total_duration_ms": 2847.32,
    "breakdown": {
      "llm_api_call": 2654.12,
      "elasticsearch_http_request": 145.23,
      "result_formatting": 35.67,
      "llm_response_parsing": 8.45,
      "request_parsing": 3.85
    }
  }
}
```

## Performance Optimization Tips

### 1. LLM Performance (Usually the biggest bottleneck)

**Switch to faster models:**
```bash
# In your .env file, try different models
LLM_PROVIDER=google
LLM_MODEL=gemini-2.5-flash-lite  # Ultra-fast model

# Or stick with OpenAI but use faster models
LLM_PROVIDER=openai  
LLM_MODEL=gpt-3.5-turbo  # Faster than gpt-4o-mini
```

**Reduce prompt size:**
- The system prompt is quite large (~2000 tokens)
- Consider simplifying the examples or schema description
- Use more concise field descriptions

**Caching (Future Enhancement):**
- Cache LLM responses for identical queries
- Implement query similarity matching

### 2. Elasticsearch Performance

**Check query complexity:**
- Complex boolean queries with many conditions are slower
- Use filters instead of queries when possible
- Consider query optimization

**Network latency:**
- If Elasticsearch is remote, consider local deployment
- Check network connectivity

### 3. Frontend Performance

**Reduce response size:**
- Limit the number of fields returned
- Implement pagination for large result sets
- Compress responses

## Comparing Performance

### Test Different Models

```bash
# Compare model performance
uv run python test_performance.py benchmark
```

### A/B Testing Queries

```bash
# Test multiple iterations to get averages
uv run python test_performance.py query "your test query" 10
```

### Component Analysis

```bash
# Isolate where time is spent
uv run python test_performance.py components
```

## Common Performance Issues

### 1. High LLM API Times (>2 seconds)

**Causes:**
- Using slower models (gpt-4o vs gpt-4o-mini)
- Large prompts with many examples
- API rate limiting or network issues

**Solutions:**
- Switch to `gemini-2.5-flash-lite` (fastest available)
- Reduce system prompt size
- Implement response caching

### 2. High Elasticsearch Times (>500ms)

**Causes:**
- Complex queries with many filters
- Large result sets
- Database performance issues

**Solutions:**
- Optimize Elasticsearch indices
- Add query caching
- Simplify query structure

### 3. High Result Formatting Time (>100ms)

**Causes:**
- Processing many results
- Complex data transformation
- Large response objects

**Solutions:**
- Limit result count
- Optimize data structures
- Stream large responses

## Adding Custom Tracing

You can add tracing to your own functions:

```python
from performance_tracer import trace_operation, trace_function

# Using decorator
@trace_function("my_operation")
def my_slow_function():
    # Your code here
    pass

# Using context manager
def my_function():
    with trace_operation("database_lookup", table="users"):
        # Your database code here
        pass
```

## Performance Monitoring in Production

For production deployment, consider:

1. **Logging Integration:**
   ```python
   from performance_tracer import tracer
   tracer.log_summary(logging.WARNING)  # Log slow requests
   ```

2. **Metrics Collection:**
   - Export timing data to monitoring systems
   - Set up alerts for slow responses
   - Track performance trends over time

3. **Selective Tracing:**
   - Only trace slow requests
   - Sample a percentage of requests
   - Disable tracing for health checks

## Troubleshooting

### Performance Tracer Not Working

1. **Import Errors:**
   ```bash
   # Make sure all files are in the same directory
   ls -la performance_tracer.py
   ```

2. **No Trace Data:**
   - Check that `start_request_trace()` is called
   - Verify trace operations are inside try blocks
   - Look for Python exceptions

3. **Incomplete Traces:**
   - Ensure all trace operations complete
   - Check for early returns or exceptions
   - Verify context managers are used correctly

### Flask App Issues

1. **Response Too Large:**
   - Performance data adds ~1KB to responses
   - Remove performance data in production if needed

2. **CORS Issues:**
   - Performance data doesn't affect CORS
   - Check CORS configuration separately

## Next Steps

Based on your performance analysis:

1. **Identify the biggest bottleneck** (likely LLM API calls)
2. **Try faster models** (gemini-2.5-flash-lite recommended)
3. **Optimize prompts** (reduce system prompt size)
4. **Consider caching** for repeated queries
5. **Monitor trends** over time to catch regressions

The tracing system will help you make data-driven optimization decisions!