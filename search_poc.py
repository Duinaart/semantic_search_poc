import json
import chromadb
from sentence_transformers import SentenceTransformer

# Initialize ChromaDB and model
chroma_client = chromadb.PersistentClient(path="./chroma_db")
model = SentenceTransformer('all-MiniLM-L6-v2')
collection = None


def safe_get(data, key, default=''):
    """Safely get a value from dictionary, converting None to default"""
    value = data.get(key, default)
    return default if value is None else value

def safe_float(value, default=0.0):
    """Safely convert value to float"""
    try:
        if value is None:
            return default
        return float(value)
    except:
        return default

class LocalEmbeddingFunction:
    def __init__(self, model):
        self.model = model
    
    def __call__(self, input: list[str]) -> list[list[float]]:
        embeddings = self.model.encode(input)
        return embeddings.tolist()

def extract_country(description):
    """Extract country from description"""
    description_lower = description.lower()
    country_markers = {
        'Finland': ['finland-based', 'finnish', 'finland'],
        'Netherlands': ['netherlands-based', 'dutch', 'netherlands'],
        'Belgium': ['belgium-based', 'belgian', 'belgium'],
        'Norway': ['norway-based', 'norwegian', 'norway'],
        'Sweden': ['sweden-based', 'swedish', 'sweden'],
        'Germany': ['germany-based', 'german', 'germany'],
        'France': ['france-based', 'french', 'france'],
        'Denmark': ['denmark-based', 'danish', 'denmark']
    }
    
    for country, markers in country_markers.items():
        if any(marker in description_lower for marker in markers):
            return country
    return 'Unknown'

def process_instrument(instrument_data):
    """Process instrument with comprehensive information"""
    description = safe_get(instrument_data, 'description', '')
    country = extract_country(description)
    size = safe_get(instrument_data, 'size_label', '')
    industry = safe_get(instrument_data, 'equity_industry', '')
    div_yield = safe_float(safe_get(instrument_data, 'div_yield_ttm', 0))
    value_growth = safe_get(instrument_data, 'value_growth_label', '')
    roe = safe_float(safe_get(instrument_data, 'roe_ttm', 0))
    
    searchable_text = f"""
    This is a {size} cap company based in {country}.
    Name: {safe_get(instrument_data, 'name')}
    Country: {country}
    Industry: {industry}
    Sector: {safe_get(instrument_data, 'equity_sector')}
    Investment Style: {value_growth}
    Dividend Yield: {div_yield * 100:.2f}%
    
    Company Details:
    {description}
    
    Financial Metrics:
    - P/E Ratio: {safe_get(instrument_data, 'price_earnings_ex_extra_ttm', '0')}
    - ROE: {roe * 100:.2f}%
    - Net Profit Margin: {safe_float(safe_get(instrument_data, 'net_profit_margin_ttm', 0)) * 100:.2f}%
    """
    
    return searchable_text

def filter_results(results, query):
    """Filter results based on specific criteria"""
    query_lower = query.lower()
    filtered_docs = []
    filtered_metadata = []
    
    # Extract criteria from query
    require_large = "large cap" in query_lower
    require_bank = "bank" in query_lower
    require_tech = "technology" in query_lower
    require_growth = "growth" in query_lower
    require_value = "value" in query_lower
    
    # Dividend threshold
    div_threshold = None
    if "dividend yield above 5%" in query_lower:
        div_threshold = 0.05
    elif "dividend yield above 3%" in query_lower:
        div_threshold = 0.03
    elif "dividend yield above 2%" in query_lower:
        div_threshold = 0.02
    elif "high dividend" in query_lower:
        div_threshold = 0.03
    
    # ROE threshold
    roe_threshold = None
    if "roe above 10%" in query_lower:
        roe_threshold = 0.10
    
    # Country filtering
    target_country = None
    countries = {
        'netherlands': 'Netherlands',
        'finland': 'Finland',
        'belgium': 'Belgium',
        'norway': 'Norway',
        'sweden': 'Sweden',
        'germany': 'Germany',
        'france': 'France',
        'denmark': 'Denmark'
    }
    for country_lower, country_proper in countries.items():
        if country_lower in query_lower:
            target_country = country_proper
            break

    for doc, metadata in zip(results['documents'][0], results['metadatas'][0]):
        meets_criteria = True
        
        # Size filter
        if require_large and metadata['size'] != 'LARGE':
            meets_criteria = False
            continue
            
        # Bank filter
        if require_bank and 'bank' not in metadata['industry'].lower():
            meets_criteria = False
            continue
            
        # Technology filter
        if require_tech and not any(tech in metadata['industry'].lower() 
                                  for tech in ['technology', 'software', 'it services']):
            meets_criteria = False
            continue
            
        # Growth/Value filter
        if require_growth and metadata['value_growth'] != 'GROWTH':
            meets_criteria = False
            continue
        if require_value and metadata['value_growth'] != 'VALUE':
            meets_criteria = False
            continue
            
        # Dividend filter
        if div_threshold and float(metadata['div_yield']) < div_threshold:
            meets_criteria = False
            continue
            
        # ROE filter
        if roe_threshold and safe_float(metadata['roe']) < roe_threshold:
            meets_criteria = False
            continue
            
        # Country filter
        if target_country and metadata['country'] != target_country:
            meets_criteria = False
            continue
        
        if meets_criteria:
            filtered_docs.append(doc)
            filtered_metadata.append(metadata)
    
    # Sort by dividend yield if dividend is mentioned
    if "dividend" in query_lower and filtered_metadata:
        filtered_results = sorted(zip(filtered_docs, filtered_metadata), 
                                key=lambda x: float(x[1]['div_yield']), 
                                reverse=True)
        filtered_docs = [item[0] for item in filtered_results]
        filtered_metadata = [item[1] for item in filtered_results]
    
    return filtered_docs, filtered_metadata

def search_instruments(query, n_results=5):
    """Enhanced search with strict filtering"""
    global collection  # Add this line
    # Get initial results
    results = collection.query(
        query_texts=[query],
        n_results=n_results * 3
    )

    
    # Apply filters
    filtered_docs, filtered_metadata = filter_results(results, query)
    
    if not filtered_metadata:
        print(f"\nNo results found matching all criteria in query: {query}")
        return {'documents': [[]], 'metadatas': [[]]}
    
    return {
        'documents': [filtered_docs[:n_results]],
        'metadatas': [filtered_metadata[:n_results]]
    }

def main():
    global collection  # Add this line
    # First, delete existing collection if it exists
    try:
        chroma_client.delete_collection(name="financial_instruments")
    except:
        pass

    # Create new collection
    embedding_function = LocalEmbeddingFunction(model)
    collection = chroma_client.create_collection(
        name="financial_instruments",
        embedding_function=embedding_function
    )

    # Load and process data
    with open('stock_id_cards.json', 'r') as file:
        data = json.load(file)
    
    # Process and add each instrument
    for ticker, instrument in data['data'].items():
        metadata = {
            'ticker': ticker,
            'name': safe_get(instrument, 'name', ''),
            'country': extract_country(safe_get(instrument, 'description', '')),
            'size': safe_get(instrument, 'size_label', ''),
            'industry': safe_get(instrument, 'equity_industry', ''),
            'div_yield': safe_float(safe_get(instrument, 'div_yield_ttm', 0)),
            'value_growth': safe_get(instrument, 'value_growth_label', ''),
            'pe_ratio': str(safe_float(safe_get(instrument, 'price_earnings_ex_extra_ttm', 0))),
            'roe': str(safe_float(safe_get(instrument, 'roe_ttm', 0)))
        }
        
        collection.add(
            documents=[process_instrument(instrument)],
            metadatas=[metadata],
            ids=[ticker]
        )

    # Test queries
    test_queries = [
        # "large cap banks with dividend yield above 3%",
        # "companies based in the Netherlands with dividend yield above 2%",
        # "value stocks in banking sector with ROE above 10%",
        # "companies with dividend yield above 5%",
        # "large cap consumer companies",
        "growth companies in industrial sector with positive ROE"
    ]
    
    # Perform searches
    for query in test_queries:
        results = search_instruments(query)
        
        print(f"\nQuery: {query}")
        if not results['metadatas'][0]:
            print("No results found matching criteria")
            print("-" * 50)
        else:
            for metadata in results['metadatas'][0]:
                print(f"\nInstrument: {metadata['name']}")
                print(f"Country: {metadata['country']}")
                print(f"Size: {metadata['size']}")
                print(f"Industry: {metadata['industry']}")
                print(f"Dividend Yield: {float(metadata['div_yield']) * 100:.2f}%")
                print(f"Value/Growth: {metadata['value_growth']}")
                if metadata['pe_ratio'] != '0':
                    print(f"P/E Ratio: {metadata['pe_ratio']}")
                if metadata['roe'] != '0':
                    print(f"ROE: {metadata['roe']}")
                print("-" * 50)

if __name__ == "__main__":
    main()
