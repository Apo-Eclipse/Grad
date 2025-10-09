import os
from langchain_tavily import TavilySearch

tavily_search = TavilySearch(
    max_results=2,
    tavily_api_key=os.getenv("TAVILY_API_KEY")
    )