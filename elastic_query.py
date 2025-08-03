# elastic_search.py
import requests
from requests.auth import HTTPBasicAuth
from query_transformer import QueryTransformer, Settings
import json
import os
from dotenv import load_dotenv
from performance_tracer import trace_operation

load_dotenv()

def send_to_elasticsearch(query: dict) -> dict:
    ES_URL = "http://localhost:9200/stocks/_search"
    USERNAME = "elastic"
    PASSWORD = os.getenv('ELASTICSEARCH_PASSWORD')  # Replace or use env var
    
    with trace_operation("elasticsearch_request_preparation", 
                       query_size=len(json.dumps(query)),
                       query_type=list(query.get('query', {}).keys())):
        # Prepare request components
        auth = HTTPBasicAuth(USERNAME, PASSWORD)
        headers = {'Content-Type': 'application/json'}
    
    try:
        with trace_operation("elasticsearch_http_request",
                           url=ES_URL,
                           query_complexity=len(str(query))):
            response = requests.post(
                ES_URL,
                json=query,
                auth=auth,
                verify=False,
                headers=headers
            )
            response.raise_for_status()
        
        with trace_operation("elasticsearch_response_parsing",
                           status_code=response.status_code,
                           response_size=len(response.content)):
            return response.json()
            
    except Exception as e:
        print(f"Error querying Elasticsearch: {e}")
        return None

def main():
    settings = Settings()
    transformer = QueryTransformer(settings)

    while True:
        print("\nEnter your query (or 'quit' to exit):")
        user_query = input("> ").strip()
        
        if user_query.lower() in ['quit', 'exit', 'q']:
            print("Goodbye!")
            break
            
        if not user_query:
            print("Please enter a valid query")
            continue
            
        # Get transformed query and explanation
        response = transformer.transform(user_query)
        
        # Print description
        print("\nDescription:")
        print(response["answer"])
        
        # Print Elasticsearch query
        print("\nElasticsearch Query:")
        print(json.dumps(response["es_query"], indent=2))
        
        # print("\nSearching...")
        results = send_to_elasticsearch(response["es_query"])
        
        if results:
            hits = results.get('hits', {}).get('hits', [])
            print(f"\nFound {len(hits)} results")
            
            for hit in hits[:3]:
                source = hit['_source']
                print(f"\nScore: {hit['_score']}")
                print(f"Name: {source.get('name')}")
                print(f"Sector: {source.get('equity_sector')}")
                print(f"ROE: {source.get('roe_ttm')}")
                print("-" * 50)

if __name__ == "__main__":
    main()
