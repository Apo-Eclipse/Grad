from typing import Literal,TypedDict, List
from LLMs.azure_models import azure_llm
from langgraph.graph import StateGraph, END
from langchain_core.prompts import ChatPromptTemplate
from pydantic import Field, BaseModel
from LLMs.azure_models import azure_llm


class searchOutput(BaseModel):
    search_queries: List[str] = Field(..., description="The search queries generated based on the insights.")
    # source: List[str] = Field(..., description="The sources of the search results.")

# You are an expert news finder. Your task is to find relevant and recent news articles based on the insights provided.
#     Use the Tavily search tool to gather information. Ensure that the articles you find are credible and relevant to the insights.
#     Provide a summary of each article along with its source.
#     Format the output as a list of articles with their summaries and sources.
#     If no relevant articles are found, respond with "No relevant articles found."
system_prompt = """
    create multiple queries to search with tavily search tool over the internet, make queries based on the insights provided.
"""

user_prompt = """
    insights: {insights}
"""

prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt), 
    ("human", user_prompt)
])


NewsWriter = prompt | azure_llm.with_structured_output(searchOutput)