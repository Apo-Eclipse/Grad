from agents.Recommendation_agent.news_finder import NewsWriter
from tools.web_search import tavily_search

def parallel_tavily_search(insights: str):    
    # Get search queries from LLM
    queries_struct = NewsWriter.invoke({"insights": insights})
    queries = queries_struct.search_queries
    print(queries)
    print("__________________________"*10)
    # Run parallel searches for each query
    results_list = tavily_search.batch(queries)
    results = dict(zip(queries, results_list))
    return results