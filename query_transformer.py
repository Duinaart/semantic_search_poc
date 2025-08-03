import json
import logging
from typing import Dict, Optional, List, Union
from openai import OpenAI
import os
from dotenv import load_dotenv
from pydantic import BaseModel, Field

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
    MODEL_NAME: str = "gpt-4o-mini"

from pydantic import BaseModel, Field
from typing import List, Union, Optional, Dict, Any
from datetime import date, datetime

ValueType = str | int | float | bool | datetime | date

# Match Query
class MatchQuery(BaseModel):
    match: dict[str, ValueType]

# Term Query
class TermQuery(BaseModel):
    term: dict[str, ValueType]

# Range Query
class RangeQuery(BaseModel):
    range: dict[str, dict[str, ValueType]]

# QueryType = dict[str, ValueType | dict[str, ValueType]]

# Bool Query Components
class BoolClause(BaseModel):
    must: list[MatchQuery | TermQuery | RangeQuery] | None = None
    should: list[MatchQuery | TermQuery | RangeQuery] | None = None
    must_not: list[MatchQuery | TermQuery | RangeQuery] | None = None
    filter: list[MatchQuery | TermQuery | RangeQuery] | None = None

# Bool Query
class BoolQuery(BaseModel):
    bool: BoolClause

# Main Elasticsearch Query
class ElasticsearchQuery(BaseModel):
    query: BoolQuery  # Optional[MatchQuery | TermQuery | RangeQuery | BoolQuery] = None
    sort: list[dict[str, Union[str, dict[str, ValueType]]]] | None = None
    from_: int | None = Field(None, alias="from")
    size: int | None = None
    aggs: dict[str, Any] | None = None

    class Config:
        populate_by_name = True

class AnswerOrESQuery(BaseModel):

    answer: str | None = None
    es_query: ElasticsearchQuery | None = None


class QueryTransformer:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)

    def transform(self, natural_query: str) -> Dict:
        """Transform natural language query to Elasticsearch query."""
        prompt = """
        Query: "{}"
        
        Transform this natural language query into a valid Elasticsearch query using the provided schema.
        If the prompt is a question, don't make a query but answer to the user.
        Add an answer/description in the answer section, so that the user knows why/how the query was created.
        Return only the JSON query structure that matches the Pydantic model.
        """.format(natural_query)

        try:
            response_format = {
                "type": "json_schema",
                "json_schema": {
                    "name": "AnswerOrESQuery",
                    "strict": False,
                    "schema": AnswerOrESQuery.model_json_schema()
                }
            }
            response = self.client.beta.chat.completions.parse(
                model=self.settings.MODEL_NAME,
                messages=[
                    {"role": "system", "content":
                     """
                     Your task is to translate a user prompt into a valid Elasticsearch query.
                     
                     Use only the following attributes in the query:
                     ```
                     {{"mappings": {{
                        "properties": {{
                        "analyst_consensus_price_target": {{
                            "properties": {{
                            "currency": {{ "type": "keyword" }},                    # ISO3 currency code (eg EUR)
                            "price": {{ "type": "float" }},                         # the price target
                            "nr_analysts": {{ "type": "integer" }}                  # the amount of analysts that are linked to the price target
                            }}
                        }},
                    "analyst_recommendation_count": {{ "type": "integer" }},        # the amount of analysts that have provided a recommendation   
                        "analyst_recommendations": {{
                            "properties": {{
                            "BUY": {{ "type": "integer" }},
                            "HOLD": {{ "type": "integer" }},
                            "OUTPERFORM": {{ "type": "integer" }},
                            "UNDERPERFORM": {{ "type": "integer" }}
                            }}
                        }},
                        "analyst_upward_potential": {{ "type": "float" }},          # the upwards potential from the latest price to the price target
                        "currency": {{ "type": "keyword" }},                        # ISO3 currency code (eg EUR)
                        "debt_equity_latest": {{ "type": "float" }},                # the debt to equity ratio
                        "description": {{ "type": "text" }},                        # the company description, describing what the company actually does
                        "div_yield_current": {{ "type": "float" }},                 # the latest dividend divided by the latest stock price
                        "div_yield_current_fy": {{ "type": "float" }},              # the latest annualized dividend, divided by the latest stock price
                        "div_yield_ttm": {{ "type": "float" }},                     # the dividend yield from dividends paid out in the last 12 months
                        "dividend_payout_ratio_ttm": {{ "type": "float" }},         # the ratio of net earnings that has been paid out in the form of dividends
                        "eps_growth_last_5y": {{ "type": "float" }},                # the earnings per share growth of the last 5 years
                        "eps_ttm": {{ "type": "float" }},                           # the earnings per share of the last 12 months
                        "equity_industry": {{ "type": "keyword" }},                 # the industry of the company. This is the equivalent of GICS level 3
                        "equity_sector": {{ "type": "keyword" }},                   # the sector the company. Can be one  of: [BASIC_MATERIALS, CONSUMER_CYCLICAL, FINANCIAL_SERVICES, REAL_ESTATE, COMMUNICATION_SERVICES, ENERGY, INDUSTRIALS, TECHNOLOGY, CONSUMER_DEFENSIVE, HEALTHCARE, UTILITIES, EDUCATION, OTHER]
                        "financial_health_stars": {{ "type": "integer" }},          # Quintile score for financial health relative to the sector. 1 is worst, 5 is best
                        "growth_stars": {{ "type": "integer" }},                    # Quintile score for growth relative to the sector. 1 is worst, 5 is best
                        "isin": {{ "type": "keyword" }},                            # ISIN identifier of the stock
                        "market_cap": {{ "type": "float" }},                        # Market capitalization of the stock, in currency
                        "momentum_stars": {{ "type": "integer" }},                  # Quintile score for momentum relative to the sector. 1 is worst, 5 is best
                        "name": {{ "type": "text" }},                               # Instrument/company name
                        "net_profit_margin_ttm": {{ "type": "float" }},             # Net profit margin of the company, for the last 12 months
                        "number_of_employees": {{ "type": "integer" }},             # Number of employees in the company
                        "price_book_latest": {{ "type": "float" }},                 # Price to book ratio for the last fiscal years
                        "price_earnings_ex_extra_ttm": {{ "type": "float" }},       # Price to earnings ratio for the last twelve months
                        "price_sales_ttm": {{ "type": "float" }},                   # Price to sales ratio for the last twelve months
                        "profitability_stars": {{ "type": "integer" }},             # Quintile score for profitability relative to the sector. 1 is worst, 5 is best
                        "roe_ttm": {{ "type": "float" }},                           # Return on equity number for the last 12 months
                        "size_label": {{ "type": "keyword" }},                      # Label describing the market cap. Can be one of: [SMALL, LARGE]
                        "stability_stars": {{ "type": "integer" }},                 # Quintile score for financial stability relative to the sector. 1 is worst, 5 is best
                        "value_growth_label": {{ "type": "keyword" }},              # Label describing the market cap. Can be one of: [VALUE, GROWTH]
                        "value_stars": {{ "type": "integer" }}                      # Quintile score for value relative to the sector. 1 is worst, 5 is best
                        }}
                    }}
                    ```

                    Examples of user prompts and corresponding Elasticsearch queries:
                    ```
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
                    ```
                    """},
                    {"role": "user", "content": prompt}
                ],
                response_format=response_format
            )
            
            # Validate response using Pydantic model
            # print(response)
            query = json.loads(response.choices[0].message.content)
            return query

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
            
        response = transformer.transform(user_query)
        
        # Print the natural language explanation
        print("\nExplanation:")
        print(response["answer"])
        
        # Print the Elasticsearch query
        print("\nElasticsearch Query:")
        print(json.dumps(response["es_query"], indent=2))

if __name__ == "__main__":
    main()


# To Do: add the enum values and specifications to the system prompt
# To Do: add another message where the last query was returned, so that the user can ask follow-up filtering requests