import json
import logging
from typing import Dict, Optional, List, Union
import os
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from performance_tracer import trace_operation
from llm_config import create_llm
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import PydanticOutputParser

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
    """Settings for QueryTransformer using LangChain configuration."""
    def __init__(self):
        # Use environment variables for LLM configuration
        self.LLM_PROVIDER: str = os.getenv('LLM_PROVIDER', 'openai')
        self.MODEL_NAME: str = os.getenv('LLM_MODEL', 'gpt-4o-mini')
        self.TEMPERATURE: float = float(os.getenv('LLM_TEMPERATURE', '0'))

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
    
    class Config:
        # Exclude None values from serialization
        exclude_none = True

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
        exclude_none = True

class AnswerOrESQuery(BaseModel):

    answer: str | None = None
    es_query: ElasticsearchQuery | None = None


class QueryTransformer:
    def __init__(self, settings: Settings):
        self.settings = settings
        # Create LLM using the LangChain configuration system
        self.llm = create_llm(
            provider=settings.LLM_PROVIDER,
            model=settings.MODEL_NAME,
            temperature=settings.TEMPERATURE
        )
        # Set up the Pydantic output parser
        self.output_parser = PydanticOutputParser(pydantic_object=AnswerOrESQuery)

    def transform(self, natural_query: str) -> Dict:
        """Transform natural language query to Elasticsearch query."""
        with trace_operation("llm_prompt_preparation", 
                           query_length=len(natural_query), 
                           model=self.settings.MODEL_NAME):
            
            # Create system message with the comprehensive schema and instructions
            system_message = SystemMessage(content=f"""
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
    "answer": "Searching for banks in Europe with high dividend yields",
    "es_query": {{
        "query": {{
            "bool": {{
                "filter": [
                    {{"term": {{"currency.keyword": "EUR"}}}},
                    {{"term": {{"equity_industry.keyword": "Banks"}}}},
                    {{"range": {{"div_yield_ttm": {{"gte": 0.03}}}}}}
                ]
            }}
        }}
    }}
}}

2. "Large growth companies in Technology sector" ->
{{
    "answer": "Searching for large technology companies with growth characteristics",
    "es_query": {{
        "query": {{
            "bool": {{
                "filter": [
                    {{"term": {{"size_label.keyword": "LARGE"}}}},
                    {{"term": {{"value_growth_label.keyword": "GROWTH"}}}},
                    {{"term": {{"equity_sector.keyword": "TECHNOLOGY"}}}}
                ]
            }}
        }}
    }}
}}

3. "Companies with upwards potential of 5%, covered by 5 analysts and with debt to equity lower than 40%" ->
{{
    "answer": "Searching for companies with strong analyst coverage, upside potential, and low debt",
    "es_query": {{
        "query": {{
            "bool": {{
                "filter": [
                    {{"range": {{"analyst_upward_potential": {{"gte": 0.05}}}}}},
                    {{"range": {{"analyst_consensus_price_target.nr_analysts": {{"gte": 5}}}}}},
                    {{"range": {{"debt_equity_latest": {{"lte": 0.4}}}}}}
                ]
            }}
        }}
    }}
}}

4. "European banks with upward potential" ->
{{
    "answer": "Searching for European banks with positive upward potential from analysts",
    "es_query": {{
        "query": {{
            "bool": {{
                "filter": [
                    {{"term": {{"currency.keyword": "EUR"}}}},
                    {{"term": {{"equity_industry.keyword": "Banks"}}}},
                    {{"range": {{"analyst_upward_potential": {{"gt": 0}}}}}}
                ]
            }}
        }}
    }}
}}
```

IMPORTANT: 
- For keyword fields (currency, equity_sector, equity_industry, size_label, value_growth_label, isin), always use the .keyword suffix in term queries
- If the prompt is a question, provide an answer instead of creating an Elasticsearch query
- Always add an answer/description explaining how the query was created
- Use proper range queries for numerical fields (gte, lte, gt, lt)
- Use term queries for exact keyword matches
- Use bool/filter queries for combining multiple conditions
- For "upward potential" queries, use range queries with analyst_upward_potential > 0 (e.g., {{"range": {{"analyst_upward_potential": {{"gt": 0}}}}}})
- ONLY use match, term, and range queries - no exists, nested, or other query types

{self.output_parser.get_format_instructions()}
""")

            # Create user message with the query
            user_message = HumanMessage(content=f'Query: "{natural_query}"\n\nTransform this into an appropriate Elasticsearch query or provide an answer if it\'s a question.')

        try:
            with trace_operation("llm_api_call", 
                               model=self.settings.MODEL_NAME,
                               provider=self.settings.LLM_PROVIDER,
                               query_preview=natural_query[:100]):
                
                # First get raw LLM response
                raw_response = self.llm.invoke([system_message, user_message])
                logger.debug(f"Raw LLM response: {raw_response.content}")
                
                # Then parse with output parser
                try:
                    result = self.output_parser.parse(raw_response.content)
                    logger.debug(f"Parsed result: {result}")
                except Exception as parse_error:
                    logger.error(f"Parsing error: {parse_error}")
                    logger.error(f"Raw response was: {raw_response.content}")
                    raise parse_error
            
            with trace_operation("llm_response_parsing", 
                               has_es_query=hasattr(result, 'es_query') and result.es_query is not None):
                # Convert Pydantic model to dictionary and clean up nulls
                result_dict = result.model_dump()
                logger.debug(f"Final result dict: {result_dict}")
                
                # Clean up the elasticsearch query to remove null values
                if result_dict.get('es_query'):
                    def clean_dict(d):
                        if isinstance(d, dict):
                            return {k: clean_dict(v) for k, v in d.items() if v is not None}
                        elif isinstance(d, list):
                            return [clean_dict(item) for item in d if item is not None]
                        return d
                    
                    result_dict['es_query'] = clean_dict(result_dict['es_query'])
                
                return result_dict

        except Exception as e:
            logger.error(f"Error in query transformation: {e}")
            logger.error(f"Error details: {type(e).__name__}: {str(e)}")
            return {"answer": "Sorry, I couldn't process your query.", "es_query": None}
        
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