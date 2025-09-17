from typing import Literal,TypedDict, List
from LLMs.azure_models import azure_llm
from langgraph.graph import StateGraph, END
from langchain_core.prompts import ChatPromptTemplate
from pydantic import Field, BaseModel
from LLMs.azure_models import azure_llm
from agents.Recommendation_agent.news_finder import searchOutput


class scrapper_out(BaseModel):
    scrapped_output: str = Field(..., description="The scrapped content generated from the inner text of the html page.")
    
    
system_prompt = """
    You are an expert web scrapper. Your task is to extract meaningful information related to the query from the inner text of the html page.
"""

user_prompt = """
    retrieve the inner text from the html page provided.
    {inner_html}
    Extract meaningful information related to the query: {query}
    Try to be as concise as possible while ensuring that the extracted information is relevant to the query.
    use bullet points or numbered lists if necessary to organize the information.
"""

prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt), 
    ("human", user_prompt)
])


Scrapper = prompt | azure_llm.with_structured_output(scrapper_out)