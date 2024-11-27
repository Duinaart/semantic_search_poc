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
            
        es_query = transformer.transform(user_query)
        print(json.dumps(es_query, indent=2))

if __name__ == "__main__":
    main()


# To Do: add the enum values and specifications to the system prompt
# To Do: make the gpt add the description as to why he created the prompt
# To Do: add another message where the last query was returned, so that the user can ask follow-up filtering requests