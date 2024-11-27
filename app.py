import dash
from dash import html, dcc, callback, Input, Output, State
import json
from query_transformer import QueryTransformer, Settings
from elastic_query import send_to_elasticsearch
from dotenv import load_dotenv
import dash_bootstrap_components as dbc

load_dotenv()

# Initialize the app with a modern theme
app = dash.Dash(
    __name__,
    external_stylesheets=[
        dbc.themes.BOOTSTRAP,
        'https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap',
        'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css'
    ]
)

# Modern color scheme
COLORS = {
    'primary': '#1A73E8',
    'secondary': '#5F6368',
    'background': '#F8F9FA',
    'card': '#FFFFFF',
    'text': '#202124',
    'border': '#DADCE0',
    'success': '#34A853',
    'warning': '#FBBC04',
    'error': '#EA4335',
}

# Custom CSS
custom_css = {
    'body': {
        'font-family': 'Inter, sans-serif',
        'background-color': COLORS['background'],
    },
    'card': {
        'border-radius': '12px',
        'box-shadow': '0 2px 6px rgba(0,0,0,0.1)',
        'transition': 'all 0.3s ease',
    }
}

app.layout = dbc.Container([
    # Header
    dbc.Row([
        dbc.Col([
            html.Div([
                html.I(className="fas fa-search-dollar", 
                      style={'font-size': '2.5rem', 'color': COLORS['primary'], 'margin-right': '15px'}),
                html.H1("Semantic Stock Search", 
                       style={'color': COLORS['text'], 'font-weight': '600', 'display': 'inline'})
            ], style={'text-align': 'center', 'padding': '2rem'})
        ])
    ]),
    
    # Search Section
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    dbc.Input(
                        id='search-input',
                        placeholder='Try "European banks with high dividends" or "Tech companies with positive momentum"',
                        type='text',
                        size='lg',
                        style={'border-radius': '8px', 'border': f'2px solid {COLORS["border"]}'}
                    ),
                    dbc.Button(
                        [html.I(className="fas fa-search", style={'margin-right': '8px'}), "Search"],
                        id='search-button',
                        color='primary',
                        size='lg',
                        className='mt-3',
                        style={'width': '200px'}
                    )
                ])
            ], style={'border': 'none', 'box-shadow': '0 2px 6px rgba(0,0,0,0.1)'})
        ], width=12)
    ], className='mb-4'),
    
    # Main Content Section - Two Columns
    dbc.Row([
        # Left Column - Description and Query
        dbc.Col([
            # Description Card
            dbc.Card([
                dbc.CardHeader([
                    html.I(className="fas fa-info-circle", style={'margin-right': '8px'}),
                    "Query Description"
                ], style={'background-color': COLORS['primary'], 'color': 'white'}),
                dbc.CardBody(
                    id='description-output',
                    style={'min-height': '100px'}
                )
            ], style=custom_css['card'], className='mb-4'),
            
            # Query Card
            dbc.Card([
                dbc.CardHeader([
                    html.I(className="fas fa-code", style={'margin-right': '8px'}),
                    "Elasticsearch Query"
                ], style={'background-color': COLORS['secondary'], 'color': 'white'}),
                dbc.CardBody([
                    dcc.Markdown(
                        id='query-output',
                        style={'background-color': '#F8F9FA', 'padding': '15px', 'border-radius': '8px'}
                    )
                ])
            ], style=custom_css['card'])
        ], md=12, lg=6),
        
        # Right Column - Results
        dbc.Col([
            dbc.Card([
                dbc.CardHeader([
                    html.I(className="fas fa-list", style={'margin-right': '8px'}),
                    "Search Results"
                ], style={'background-color': COLORS['success'], 'color': 'white'}),
                dbc.CardBody(
                    id='results-output',
                    style={'max-height': '800px', 'overflow-y': 'auto'}
                )
            ], style=custom_css['card'])
        ], md=12, lg=6)
    ])
], fluid=True, style={'max-width': '1400px', 'margin': '0 auto'})

@callback(
    [Output('description-output', 'children'),
     Output('query-output', 'children'),
     Output('results-output', 'children')],
    [Input('search-button', 'n_clicks')],
    [State('search-input', 'value')],
    prevent_initial_call=True
)
def update_output(n_clicks, value):
    if not value:
        return "Please enter a query", "```json\n{}\n```", "No results yet"
    
    settings = Settings()
    transformer = QueryTransformer(settings)
    response = transformer.transform(value)
    
    # Format query with markdown for syntax highlighting
    formatted_query = f"```json\n{json.dumps(response['es_query'], indent=2)}\n```"
    
    results = send_to_elasticsearch(response["es_query"])
    
    if results and 'hits' in results and 'hits' in results['hits']:
        hits = results['hits']['hits']
        results_cards = []
        
        for hit in hits[:5]:
            source = hit['_source']
            
            # Calculate metrics and their styles
            roe = source.get('roe_ttm')
            roe_style = {
                'color': COLORS['success'] if roe and roe > 0 else COLORS['error'],
                'font-weight': '500'
            }
            
            div_yield = source.get('div_yield_ttm')
            div_style = {
                'color': COLORS['success'] if div_yield and div_yield > 0 else COLORS['secondary'],
                'font-weight': '500'
            }
            
            card = dbc.Card([
                dbc.CardBody([
                    # Header row with name and sector
                    dbc.Row([
                        dbc.Col([
                            html.H4(source.get('name', 'N/A'), className='mb-0'),
                            html.Small(source.get('equity_sector', 'N/A'), 
                                     className='text-muted')
                        ], width=8),
                        dbc.Col([
                            html.Div([
                                html.Strong(f"{hit['_score']:.2f}"),
                                html.Small(" relevance", className='text-muted')
                            ], className='text-right')
                        ], width=4, className='text-end')
                    ]),
                    
                    html.Hr(),
                    
                    # Metrics row
                    dbc.Row([
                        dbc.Col([
                            dbc.Row([
                                dbc.Col([
                                    html.Div([
                                        html.I(className="fas fa-chart-line text-primary me-2"),
                                        "ROE: ",
                                        html.Span(f"{roe:.1%}" if roe else "N/A", style=roe_style)
                                    ], className='mb-2'),
                                    html.Div([
                                        html.I(className="fas fa-coins text-warning me-2"),
                                        "Dividend Yield: ",
                                        html.Span(f"{div_yield:.1%}" if div_yield else "N/A", style=div_style)
                                    ]),
                                ], width=6),
                                dbc.Col([
                                    html.Div([
                                        html.I(className="fas fa-building text-success me-2"),
                                        "Industry: ",
                                        html.Span(source.get('equity_industry', 'N/A'))
                                    ], className='mb-2'),
                                    html.Div([
                                        html.I(className="fas fa-tag text-info me-2"),
                                        "ISIN: ",
                                        html.Span(source.get('isin', 'N/A'))
                                    ]),
                                ], width=6)
                            ])
                        ])
                    ])
                ])
            ], className='mb-3', style=custom_css['card'])
            
            results_cards.append(card)
        
        if not results_cards:
            results_cards = dbc.Alert(
                "No matching stocks found",
                color="warning",
                style={'text-align': 'center'}
            )
    else:
        results_cards = dbc.Alert(
            "Error retrieving results",
            color="danger",
            style={'text-align': 'center'}
        )
    
    return response["answer"], formatted_query, results_cards

if __name__ == '__main__':
    app.run_server(debug=True)
