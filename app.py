from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import json
from query_transformer import QueryTransformer, Settings
from elastic_query import send_to_elasticsearch
from dotenv import load_dotenv
import os

load_dotenv()

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for frontend requests

# Initialize query transformer
settings = Settings()
transformer = QueryTransformer(settings)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/search', methods=['POST'])
def search():
    try:
        data = request.get_json()
        query = data.get('query', '')
        
        if not query:
            return jsonify({'error': 'Query is required'}), 400
        
        # Transform the query
        response = transformer.transform(query)
        
        if not response.get('es_query'):
            # If no ES query, it's just an answer
            return jsonify({
                'description': response.get('answer', ''),
                'query': None,
                'results': []
            })
        
        # Execute the search
        results = send_to_elasticsearch(response["es_query"])
        
        # Format results
        formatted_results = []
        if results and 'hits' in results and 'hits' in results['hits']:
            hits = results['hits']['hits']
            for hit in hits[:8]:
                source = hit['_source']
                formatted_results.append({
                    'score': hit['_score'],
                    'name': source.get('name', 'N/A'),
                    'sector': source.get('equity_sector', 'N/A'),
                    'industry': source.get('equity_industry', 'N/A'),
                    'isin': source.get('isin', 'N/A'),
                    'roe_ttm': source.get('roe_ttm'),
                    'div_yield_ttm': source.get('div_yield_ttm'),
                    'market_cap': source.get('market_cap'),
                    'price_earnings_ex_extra_ttm': source.get('price_earnings_ex_extra_ttm'),
                    'description': source.get('description', ''),
                    'currency': source.get('currency', ''),
                    'eps_ttm': source.get('eps_ttm'),
                    'momentum_stars': source.get('momentum_stars'),
                    'value_stars': source.get('value_stars'),
                    'profitability_stars': source.get('profitability_stars'),
                    'growth_stars': source.get('growth_stars'),
                    'financial_health_stars': source.get('financial_health_stars')
                })
        
        return jsonify({
            'description': response.get('answer', ''),
            'query': response.get('es_query'),
            'results': formatted_results
        })
        
    except Exception as e:
        print(f"Error in search endpoint: {e}")
        return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8082))
    app.run(
        debug=True,
        host='0.0.0.0',
        port=port
    )

