#!/usr/bin/env python3
"""
Performance Testing Script

Test the semantic search application with performance tracing enabled.
This script can be used to:
1. Test individual components
2. Run performance benchmarks  
3. Compare different models/configurations
"""

import time
import sys
import json
from query_transformer import QueryTransformer, Settings
from elastic_query import send_to_elasticsearch
from performance_tracer import start_request_trace, print_trace_summary, get_trace_summary

def test_query_performance(query: str, iterations: int = 1):
    """Test a single query with performance tracing."""
    print(f"\n{'='*60}")
    print(f"TESTING QUERY: {query}")
    print(f"ITERATIONS: {iterations}")
    print(f"{'='*60}")
    
    total_times = []
    
    for i in range(iterations):
        print(f"\nIteration {i+1}/{iterations}")
        start_request_trace(f"test_iter_{i+1}")
        
        # Initialize transformer
        settings = Settings()
        transformer = QueryTransformer(settings)
        
        # Transform query
        response = transformer.transform(query)
        
        # If we have an Elasticsearch query, execute it
        if response.get('es_query'):
            results = send_to_elasticsearch(response["es_query"])
            result_count = len(results.get('hits', {}).get('hits', [])) if results else 0
        else:
            result_count = 0
        
        # Get performance summary
        summary = get_trace_summary()
        total_time = summary.get('total_duration_ms', 0)
        total_times.append(total_time)
        
        print(f"Total time: {total_time:.2f}ms")
        print(f"Results found: {result_count}")
        
        if iterations == 1:
            print_trace_summary()
    
    if iterations > 1:
        avg_time = sum(total_times) / len(total_times)
        min_time = min(total_times)
        max_time = max(total_times)
        
        print(f"\n{'='*60}")
        print(f"PERFORMANCE SUMMARY ({iterations} iterations)")
        print(f"{'='*60}")
        print(f"Average time: {avg_time:.2f}ms")
        print(f"Min time: {min_time:.2f}ms")
        print(f"Max time: {max_time:.2f}ms")
        print(f"Time range: {max_time - min_time:.2f}ms")

def test_component_isolation():
    """Test individual components in isolation."""
    print(f"\n{'='*60}")
    print("COMPONENT ISOLATION TEST")
    print(f"{'='*60}")
    
    query = "European technology companies with high growth"
    
    # Test query transformation only
    start_request_trace("component_test")
    settings = Settings()
    transformer = QueryTransformer(settings)
    
    response = transformer.transform(query)
    
    print("\nQuery Transformation Performance:")
    print_trace_summary()
    
    # Test Elasticsearch query only (if we have a query)
    if response.get('es_query'):
        start_request_trace("elasticsearch_only")
        results = send_to_elasticsearch(response["es_query"])
        
        print("\nElasticsearch Query Performance:")
        print_trace_summary()

def benchmark_models():
    """Benchmark different model configurations."""
    print(f"\n{'='*60}")
    print("MODEL BENCHMARKING")
    print(f"{'='*60}")
    
    # Test with different models if available
    models_to_test = ["gpt-4o-mini", "gpt-3.5-turbo"]
    test_query = "Large dividend paying stocks in Europe"
    
    for model in models_to_test:
        print(f"\nTesting model: {model}")
        print("-" * 40)
        
        try:
            # Create settings with specific model
            settings = Settings()
            settings.MODEL_NAME = model
            
            start_request_trace(f"model_test_{model}")
            transformer = QueryTransformer(settings)
            response = transformer.transform(test_query)
            
            if response.get('es_query'):
                send_to_elasticsearch(response["es_query"])
            
            summary = get_trace_summary()
            total_time = summary.get('total_duration_ms', 0)
            print(f"Total time with {model}: {total_time:.2f}ms")
            
            # Print breakdown for first model only
            if model == models_to_test[0]:
                print_trace_summary()
                
        except Exception as e:
            print(f"Error testing {model}: {e}")

def main():
    """Main CLI interface for performance testing."""
    if len(sys.argv) < 2:
        print("Usage: python test_performance.py <mode> [options]")
        print("\nModes:")
        print("  query <query_text> [iterations] - Test a specific query")
        print("  components                      - Test individual components")
        print("  benchmark                       - Benchmark different models")
        print("  interactive                     - Interactive testing mode")
        print("\nExamples:")
        print("  python test_performance.py query 'European banks' 3")
        print("  python test_performance.py components")
        print("  python test_performance.py benchmark")
        return
    
    mode = sys.argv[1].lower()
    
    if mode == "query":
        if len(sys.argv) < 3:
            print("Error: Query text required")
            return
        
        query = sys.argv[2]
        iterations = int(sys.argv[3]) if len(sys.argv) > 3 else 1
        test_query_performance(query, iterations)
        
    elif mode == "components":
        test_component_isolation()
        
    elif mode == "benchmark":
        benchmark_models()
        
    elif mode == "interactive":
        print("Interactive Performance Testing Mode")
        print("Enter queries to test (type 'quit' to exit):")
        
        while True:
            query = input("\nQuery> ").strip()
            if query.lower() in ['quit', 'exit', 'q']:
                break
            if query:
                test_query_performance(query, 1)
    
    else:
        print(f"Unknown mode: {mode}")
        print("Use 'python test_performance.py' for usage help")

if __name__ == "__main__":
    main()