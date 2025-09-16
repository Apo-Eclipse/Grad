from langchain_tavily import TavilySearch
# from helpers.config import get_setting

# app_settings = get_setting()

# Initialize search tool
tavily_search = TavilySearch(
    max_results=2,
    tavily_api_key="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"
    )