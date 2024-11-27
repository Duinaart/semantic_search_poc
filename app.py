# app.py
from dash import Dash, html, dcc, Input, Output, State
import dash_bootstrap_components as dbc
from query_transformer import QueryTransformer, Settings
from elastic_search import send_to_elasticsearch
import json

app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

app.layout = dbc.Container([
    html.H1("Semantic Stock Search", className="mb-4"),
    
    dbc.Row([
        dbc.Col([
            dbc.Input(
                id="query-input",
                placeholder="e.g., tech companies with high ROE",
                type="text",
                className="mb-3"
            ),
            dbc.Button("Search", id="search-button", color="primary", className="mb-3"),
            
            # Query display
            html.H4("Elasticsearch Query"),
            dcc.Loading(
                id="query-loading",
                children=[
                    dbc.Card(
                        dbc.CardBody(
                            html.Pre(id="query-display")
                        )
                    )
                ]
            ),
            
            # Results
            html.H4("Results", className="mt-4"),
            dcc.Loading(
                id="results-loading",
                children=[
                    html.Div(id="results-display")
                ]
            )
        ])
    ])
], fluid=True)

@app.callback(
    [Output("query-display", "children"),
     Output("results-display", "children")],
    [Input("search-button", "n_clicks")],
    [State("query-input", "value")],
    prevent_initial_call=True
)
def update_results(n_clicks, query):
    if not query:
        return "", ""
    
    # Initialize components
    settings = Settings()
    transformer = QueryTransformer(settings)
    
    # Transform query
    es_query = transformer.transform(query)
    query_str = json.dumps(es_query, indent=2)
    
    # Get results
    results = send_to_elasticsearch(es_query)
    
    if results:
        hits = results.get('hits', {}).get('hits', [])
        
        # Create results cards
        results_cards = []
        for hit in hits:
            source = hit['_source']
            card = dbc.Card(
                dbc.CardBody([
                    html.H5(source.get('name'), className="card-title"),
                    html.H6(f"Score: {hit['_score']}", className="card-subtitle mb-2 text-muted"),
                    dbc.Row([
                        dbc.Col([
                            html.P([
                                html.Strong("Sector: "), 
                                source.get('equity_sector')
                            ]),
                            html.P([
                                html.Strong("ROE: "), 
                                f"{source.get('roe_ttm', 0):.2%}"
                            ]),
                        ]),
                        dbc.Col([
                            html.P([
                                html.Strong("Dividend Yield: "), 
                                f"{source.get('div_yield_ttm', 0):.2%}"
                            ]),
                            html.P([
                                html.Strong("P/E Ratio: "), 
                                source.get('price_earnings_ex_extra_ttm')
                            ]),
                        ])
                    ]),
                    html.P(source.get('description', '')[:200] + "...")
                ]),
                className="mb-3"
            )
            results_cards.append(card)
        
        return query_str, html.Div(results_cards)
    
    return query_str, "No results found"

if __name__ == '__main__':
    app.run_server(debug=True)
