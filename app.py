import dash
from dash import html, dcc, callback, Output, Input, State
import dash_bootstrap_components as dbc
from search_poc_openai import (
    initialize_search,
    search_instruments
)

# Initialize search functionality
collection = initialize_search()

# Initialize Dash app
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

# Layout
app.layout = dbc.Container([
    html.H1("Financial Instrument Search", className="my-4"),
    
    # Search Section
    dbc.Row([
        dbc.Col([
            dbc.Input(
                id='search-input',
                placeholder='e.g., growth companies in industrial sector with positive ROE',
                type='text',
                className="mb-2"
            ),
            dbc.Button("Search", id='search-button', color="primary", className="mb-4")
        ])
    ]),
    
    # Results Section
    html.Div(id='search-results')
])

@callback(
    Output('search-results', 'children'),
    Input('search-button', 'n_clicks'),
    State('search-input', 'value'),
    prevent_initial_call=True
)
def update_results(n_clicks, query):
    if not query:
        return html.Div("Please enter a search query")
    
    # Reinitialize collection for each search
    collection = initialize_search(clear=True)
    results = search_instruments(query, collection)
    
    if not results['metadatas'][0]:
        return html.Div("No results found")
    
    return html.Div([
        dbc.Card(
            dbc.CardBody([
                html.H4(metadata['name'], className="card-title"),
                html.H6(f"Sector: {metadata['sector']}", className="card-subtitle mb-2 text-muted"),
                dbc.Row([
                    dbc.Col([
                        html.P(f"Industry: {metadata['industry']}"),
                        html.P(f"Size: {metadata['size']}"),
                        html.P(f"Value/Growth: {metadata['value_growth']}")
                    ], width=6),
                    dbc.Col([
                        html.P(f"ROE: {float(metadata['roe'])*100:.2f}%"),
                        html.P(f"Dividend Yield: {float(metadata['dividend_yield'])*100:.2f}%"),
                        html.P(f"P/E Ratio: {metadata['pe_ratio']}")
                    ], width=6)
                ])
            ]),
            className="mb-3"
        )
        for metadata in results['metadatas'][0]
    ])

if __name__ == '__main__':
    app.run_server(debug=True)
