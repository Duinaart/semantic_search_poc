from elasticsearch import Elasticsearch

# Connect with HTTPS
es = Elasticsearch(
    "https://localhost:9200",  # Note the https
    basic_auth=("elastic", "7XCO9n*87P+1o3MGmMXK"),  # Replace with your password
    verify_certs=False,  # For development only
    ssl_show_warn=False  # Suppress warnings
)

# Test connection
try:
    result = es.search(index='stocks')
    print(result['hits']['hits'])
except Exception as e:
    print(f"Error: {e}")
