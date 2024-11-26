# elastic_search.py
import requests
from requests.auth import HTTPBasicAuth
from query_transformer import QueryTransformer, Settings
import json
import os
from dotenv import load_dotenv

load_dotenv()

def send_to_elasticsearch(query: dict) -> dict:
    ES_URL = "https://localhost:9200/stocks/_search"
    USERNAME = "elastic"
    PASSWORD = os.getenv('ELASTICSEARCH_PASSWORD')  # Replace or use env var
    
    try:
        response = requests.post(
            ES_URL,
            json=query,
            auth=HTTPBasicAuth(USERNAME, PASSWORD),
            verify=False,
            headers={'Content-Type': 'application/json'}
        )
        response.raise_for_status()
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
            
        es_query = transformer.transform(user_query)
        print("\nElasticsearch Query:")
        print(json.dumps(es_query, indent=2))
        
        print("\nSearching...")
        results = send_to_elasticsearch(es_query)
        
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
