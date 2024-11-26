import json
import logging
from typing import Dict
from openai import OpenAI
import os
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('query_transformer.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class Settings:
    OPENAI_API_KEY: str = os.getenv('OPENAI_API_KEY')
    MODEL_NAME: str = os.getenv('MODEL_NAME', 'gpt-4')

class QueryTransformer:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.functions = [
            {
                "name": "create_elasticsearch_query",
                "description": "Create an Elasticsearch query from natural language",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "object",
                            "properties": {
                                "bool": {
                                    "type": "object",
                                    "properties": {
                                        "must": {
                                            "type": "array",
                                            "items": {
                                                "type": "object",
                                                "additionalProperties": True
                                            }
                                        },
                                        "should": {
                                            "type": "array",
                                            "items": {
                                                "type": "object",
                                                "additionalProperties": True
                                            }
                                        },
                                        "must_not": {
                                            "type": "array",
                                            "items": {
                                                "type": "object",
                                                "additionalProperties": True
                                            }
                                        },
                                        "filter": {
                                            "type": "array",
                                            "items": {
                                                "type": "object",
                                                "additionalProperties": True
                                            }
                                        }
                                    },
                                    "additionalProperties": True
                                }
                            },
                            "required": ["bool"]
                        }
                    },
                    "required": ["query"]
                }
            }
        ]

    def transform(self, natural_query: str) -> Dict:
        """Transform natural language query to Elasticsearch query."""
        prompt = """
        Query: "{}"

        Rules for Elasticsearch field names and values:
        {{"mappings": {{
            "properties": {{
            "analyst_consensus_price_target": {{
                "properties": {{
                "currency": {{ "type": "keyword" }},
                "price": {{ "type": "float" }},
                "nr_analysts": {{ "type": "integer" }}
                }}
            }},
            "analyst_recommendation_count": {{ "type": "integer" }},
            "analyst_recommendations": {{
                "properties": {{
                "BUY": {{ "type": "integer" }},
                "HOLD": {{ "type": "integer" }},
                "OUTPERFORM": {{ "type": "integer" }},
                "UNDERPERFORM": {{ "type": "integer" }}
                }}
            }},
            "analyst_upward_potential": {{ "type": "float" }},
            "currency": {{ "type": "keyword" }},
            "debt_equity_latest": {{ "type": "float" }},
            "description": {{ "type": "text" }},
            "div_yield_current": {{ "type": "float" }},
            "div_yield_current_fy": {{ "type": "float" }},
            "div_yield_ttm": {{ "type": "float" }},
            "dividend_payout_ratio_ttm": {{ "type": "float" }},
            "eps_growth_last_5y": {{ "type": "float" }},
            "eps_ttm": {{ "type": "float" }},
            "equity_industry": {{ "type": "keyword" }},
            "equity_sector": {{ "type": "keyword" }},
            "financial_health_stars": {{ "type": "integer" }},
            "growth_stars": {{ "type": "integer" }},
            "isin": {{ "type": "keyword" }},
            "market_cap": {{ "type": "float" }},
            "momentum_stars": {{ "type": "integer" }},
            "name": {{ "type": "text" }},
            "net_profit_margin_ttm": {{ "type": "float" }},
            "number_of_employees": {{ "type": "integer" }},
            "price_book_latest": {{ "type": "float" }},
            "price_earnings_ex_extra_ttm": {{ "type": "float" }},
            "price_sales_ttm": {{ "type": "float" }},
            "profitability_stars": {{ "type": "integer" }},
            "roe_ttm": {{ "type": "float" }},
            "size_label": {{ "type": "keyword" }},
            "stability_stars": {{ "type": "integer" }},
            "value_growth_label": {{ "type": "keyword" }},
            "value_stars": {{ "type": "integer" }}
            }}
        }}    
        If a user does not specify that the number should be exact, assume that better is also fine. 

        Example queries:
        1. "European banks with high dividends" ->
        {{
            "query": {{
                "bool": {{
                    "must": [
                        {{"term": {{"currency": "EUR"}}}},
                        {{"term": {{"equity_industry": "Banks"}}}},
                        {{"range": {{"div_yield_ttm.float": {{"gt": 0.03}}}}}}
                    ]
                }}
            }}
        }}

        2. "Large growth companies in Technology sector" ->
        {{
            "query": {{
                "bool": {{
                    "must": [
                        {{"term": {{"size_label": "LARGE"}}}}
                        {{"term": {{"value_growth_label": "GROWTH"}}}},
                        {{"term": {{"equity_sector": "TECHNOLOGY"}}}},

                    ]
                }}
            }}
        }}

        3. "Companies with upwards potential of 5%, covered by 5 analysts and with debt to equity lower than 40%" ->
      {{
            "query": {{
                "bool": {{
                    "must": [
                    {{"range": {{"analyst_upward_potential": {{"gte": 0.05}}}}}},
                    {{"range": {{"analyst_consensus_price_target.nr_analysts": {{"gte":5}}}}}},
                    {{"range": {{"debt_equity_latest": {{"lte": 0.4}}}}}}

                    ]
                }}
            }}
        }}
        """.format(natural_query)

        try:
            response = self.client.chat.completions.create(
                model=self.settings.MODEL_NAME,
                messages=[
                    {"role": "system", "content": "You transform natural language queries into Elasticsearch query DSL format."},
                    {"role": "user", "content": prompt}
                ],
                tools=[{
                    "type": "function",
                    "function": {
                        "name": "create_elasticsearch_query",
                        "description": "Create an Elasticsearch query from natural language",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "query": {
                                    "type": "object",
                                    "properties": {
                                        "bool": {
                                            "type": "object",
                                            "properties": {
                                                "must": {
                                                    "type": "array",
                                                    "items": {
                                                        "type": "object",
                                                        "additionalProperties": True
                                                    }
                                                },
                                                "should": {
                                                    "type": "array",
                                                    "items": {
                                                        "type": "object",
                                                        "additionalProperties": True
                                                    }
                                                },
                                                "must_not": {
                                                    "type": "array",
                                                    "items": {
                                                        "type": "object",
                                                        "additionalProperties": True
                                                    }
                                                },
                                                "filter": {
                                                    "type": "array",
                                                    "items": {
                                                        "type": "object",
                                                        "additionalProperties": True
                                                    }
                                                }
                                            },
                                            "additionalProperties": True
                                        }
                                    },
                                    "required": ["bool"]
                                }
                            },
                            "required": ["query"]
                        }
                    }
                }],
                tool_choice={"type": "function", "function": {"name": "create_elasticsearch_query"}}
            )
            
            # Extract the function call arguments from the new response structure
            tool_calls = response.choices[0].message.tool_calls
            if tool_calls:
                query = json.loads(tool_calls[0].function.arguments)
                return query

            return {"query": {"match_all": {}}}

        except Exception as e:
            logger.error(f"Error in query transformation: {e}")
            return {"query": {"match_all": {}}}


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
        print(json.dumps(es_query, indent=2))

if __name__ == "__main__":
    main()

