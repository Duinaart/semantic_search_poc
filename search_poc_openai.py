import json
import chromadb
from sentence_transformers import SentenceTransformer
from openai import OpenAI
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize with in-memory database
chroma_client = chromadb.Client()
model = SentenceTransformer('all-MiniLM-L6-v2')
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
os.environ["TOKENIZERS_PARALLELISM"] = "false"

class LocalEmbeddingFunction:
    def __init__(self, model):
        self.model = model
    
    def __call__(self, input: list[str]) -> list[list[float]]:
        embeddings = self.model.encode(input)
        return embeddings.tolist()

def safe_get(data, key, default=''):
    value = data.get(key, default)
    return default if value is None else str(value)

def create_metadata(instrument):
    # Extract country from description
    description = instrument.get('description', '').lower()
    country = None
    if 'belgium-based' in description or 'belgian' in description:
        country = "Belgium"
    elif 'netherlands-based' in description or 'dutch' in description:
        country = "Netherlands"
    
    return {
        'name': safe_get(instrument, 'name'),
        'industry': safe_get(instrument, 'equity_industry'),
        'sector': safe_get(instrument, 'equity_sector'),
        'size': safe_get(instrument, 'size_label'),
        'value_growth': safe_get(instrument, 'value_growth_label'),
        'dividend_yield': safe_get(instrument, 'div_yield_ttm', '0'),
        'roe': safe_get(instrument, 'roe_ttm', '0'),
        'pe_ratio': safe_get(instrument, 'price_earnings_ex_extra_ttm', '0'),
        'country': country or 'Unknown'
    }

def search_instruments(query: str, collection, n_results=10):
    prompt = f"""
    Analyze this investment query: "{query}"
    Create a JSON with EXACT search criteria. Be extremely precise and literal.

    Key rules:
    1. Banking/Financial:
    - If "banks" mentioned -> industry MUST be "Banks"
    - If "financial" mentioned -> sector MUST be "FINANCIAL_SERVICES"

    2. Geographic:
    - "belgian"/"belgium" -> country MUST be "Belgium"
    - "dutch"/"netherlands" -> country MUST be "Netherlands"

    3. Dividends:
    - "high dividend(s)" -> min_dividend_yield = 0.03
    - If specific percentage mentioned, use that value

    4. Industry/Sector matching:
    - "industrial" -> sector MUST be "INDUSTRIALS"
    - "technology" -> sector MUST be "TECHNOLOGY"
    - "real estate" -> sector MUST be "REAL_ESTATE"

    5. Size/Style:
    - "large cap" -> size MUST be "LARGE"
    - "growth" -> value_growth MUST be "GROWTH"
    - "value" -> value_growth MUST be "VALUE"

    Only include fields that are EXPLICITLY mentioned or directly implied.
    Never use generic values like "ALL" or "ANY".

    Format:
    {{
        "sector": exact sector if mentioned,
        "industry": exact industry if mentioned,
        "country": exact country if mentioned,
        "min_dividend_yield": decimal (e.g., 0.03 for 3%),
        "size": "LARGE"/"MID"/"SMALL" if mentioned,
        "value_growth": "VALUE"/"GROWTH" if mentioned
    }}

    Return only the JSON, no explanation.
    """

    
    response = client.chat.completions.create(
        model="gpt-3",
        messages=[
            {"role": "system", "content": "You are a financial query analyzer. Only include explicitly mentioned criteria."},
            {"role": "user", "content": prompt}
        ]
    )
    
    criteria = json.loads(response.choices[0].message.content)
    print(f"Query analysis: {json.dumps(criteria, indent=2)}")
    
    # Build conditions based on GPT analysis
    conditions = []
    
    if criteria.get('sector'):
        conditions.append({"sector": criteria['sector']})
    if criteria.get('industry'):
        conditions.append({"industry": criteria['industry']})
    if criteria.get('country'):
        conditions.append({"country": criteria['country']})
    if criteria.get('size') and criteria['size'] != 'ALL':
        conditions.append({"size": criteria['size']})
    if criteria.get('value_growth') and criteria['value_growth'] != 'ALL':
        conditions.append({"value_growth": criteria['value_growth']})
    if criteria.get('min_dividend_yield') and float(criteria['min_dividend_yield']) > 0:
        conditions.append({"dividend_yield": {"$gt": float(criteria['min_dividend_yield'])}})
    
    # Combine conditions
    where_clause = None
    if len(conditions) > 1:
        where_clause = {"$and": conditions}
    elif len(conditions) == 1:
        where_clause = conditions[0]
    
    print(f"Search conditions: {json.dumps(where_clause, indent=2)}")
    
    # Get results
    results = collection.query(
        query_texts=[query],
        where=where_clause,
        n_results=n_results
    )
    
    return results


def initialize_search(clear=True):
    """Initialize search functionality and return collection"""
    # Initialize database and model
    chroma_client = chromadb.Client()  # Using in-memory client
    model = SentenceTransformer('all-MiniLM-L6-v2')
    embedding_function = LocalEmbeddingFunction(model)
    
    # Create collection
    collection_name = "financial_instruments"
    if clear:
        try:
            chroma_client.delete_collection(name=collection_name)
        except:
            pass
    
    collection = chroma_client.create_collection(
        name=collection_name,
        embedding_function=embedding_function
    )
    
    # Load data
    with open('stock_id_cards.json', 'r') as file:
        data = json.load(file)
    
    # Add documents to collection
    for ticker, instrument in data['data'].items():
        collection.add(
            documents=[json.dumps(instrument)],
            metadatas=[create_metadata(instrument)],
            ids=[ticker]
        )
    
    return collection


def main():
    # Create collection
    embedding_function = LocalEmbeddingFunction(model)
    collection = chroma_client.create_collection(
        name="financial_instruments",
        embedding_function=embedding_function
    )

    # Load and process data
    with open('stock_id_cards.json', 'r') as file:
        data = json.load(file)
    
    # Add documents to collection
    for ticker, instrument in data['data'].items():
        collection.add(
            documents=[json.dumps(instrument)],
            metadatas=[create_metadata(instrument)],
            ids=[ticker]
        )

    # Example query
    query = "belgian banks that pay a dividend"
    results = search_instruments(query, collection)
    
    print(f"\nQuery: {query}")
    print("=" * 50)
    
    # Print only matching instruments
    for metadata in results['metadatas'][0]:
        print(f"\nInstrument: {metadata['name']}")
        print(f"Sector: {metadata['sector']}")
        print(f"Industry: {metadata['industry']}")
        print(f"Value/Growth: {metadata['value_growth']}")
        print(f"ROE: {float(metadata['roe'])*100:.2f}%")
        print(f"Dividend Yield: {float(metadata['dividend_yield'])*100:.2f}%")
        print(f"Country: {metadata['country']}")
        print("-" * 50)

if __name__ == "__main__":
    main()
