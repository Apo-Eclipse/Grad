from urllib import response
from agents import NewsWriter
from agents import Scrapper
from tools.web_search import tavily_search
from langgraph.graph import StateGraph, END, START
from typing import Dict, Literal,TypedDict, Annotated, List
from langgraph.types import Command
from operator import add
from graphs.presentation_sub_graph import presentation_super_agent
import requests
import ast
from bs4 import BeautifulSoup

class recommendation_graph_state(TypedDict):
    insights: str
    results: Dict[str, List[str]]
    report: str
    

def get_inner_text_from_url(url):
    try:
        response = requests.get(url)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            for script in soup(["script", "style"]):
                script.extract()
            text = soup.get_text(strip=True)
            return text
        else:
            return f"Failed to retrieve content. Status code: {response.status_code}"
    except Exception as e:
        return f"An error occurred: {str(e)}"

def scrapper(state: recommendation_graph_state):
    results = state.get("results","empty")
    # convert string to dict
    if results == "empty":
        return {"report":"No results found"}
    results = state["results"]
    report = ""
    for k in results:
        report += k + ":\n"
        for url in results[k]:
            scrapped = Scrapper.invoke({"inner_html": get_inner_text_from_url(url), "query": k})
            scrapped = scrapped.scrapped_output
            report += url + ": \n"+ scrapped + "\n" + "------------------\n"
        report += "\n********************************\n"
    return {"report":report}

def parallel_tavily_search(state: recommendation_graph_state):    
    # Get search queries from LLM
    insights = state.get("insights", "empty")
    queries_struct = NewsWriter.invoke({"insights": insights})
    queries = queries_struct.search_queries
    # print(queries)
    # print("__________________________"*10)
    # Run parallel searches for each query
    results_list = tavily_search.batch(queries)
    results = dict(zip(queries, results_list))
    d = {}
    for query, result in results.items():
        search_result = result.get('results', [])
        d[query] = [item.get('url', '') for item in search_result]
        # for i in range(len(search_result)):
        #     print("_______result___________________________"*5)
        #     print(search_result[i].get("content", ""))
        #     print("_______result___________________________"*5)
    return {"results":d}

builder = StateGraph(recommendation_graph_state)
builder.add_node("parallel_tavily_search", parallel_tavily_search)
builder.add_node("presentation", presentation_super_agent)
builder.add_node("scrapper",scrapper)

builder.add_edge(START, "parallel_tavily_search")
builder.add_edge("parallel_tavily_search","scrapper")
# builder.add_edge("scrapper", "presentation")
# builder.add_edge("presentation",END)
builder.add_edge("scrapper",END)
recommendation_agent_sub_graph = builder.compile()