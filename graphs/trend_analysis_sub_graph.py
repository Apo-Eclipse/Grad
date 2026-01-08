# from agents.Recommendation_agent.news_finder import Writer
# from tools.web_search import tavily_search
# def parallel_tavily_search(insights: str):
    
#     # Get search queries from LLM
#     queries_struct = Writer.invoke({"insights": insights})
#     queries = queries_struct.search_queries
#     print(queries)
#     print("__________________________"*10)
#     # Run parallel searches for each query
#     results_list = tavily_search.batch(queries)
#     results = dict(zip(queries, results_list))
#     return results


from agents.trend_analysis_agent.fetch_keyword_facts import fetch_facts_for_keywords, KeywordFactsResponse
from agents.trend_analysis_agent.keywords_finder import get_keywords_for_categories, KeywordsResponse
from agents.trend_analysis_agent.theme_analysis import analysis_chain, AnalysisResponse
from agents.trend_analysis_agent.user_persona_extractor import persona_chain, CATEGORY_MAP, ProfileNotesResponse
from agents.trend_analysis_agent.final_report import writer_chain, SummaryResponse
from langgraph.graph import StateGraph, END, START
from typing import Literal,TypedDict, Annotated, List, Optional, Dict
from langgraph.types import Command
from operator import add
from pydantic import BaseModel



class TechNews(TypedDict):
    user_info: Dict
    user_persona: Optional[ProfileNotesResponse]
    keywords_info: Optional[KeywordsResponse]
    keywords_facts: Optional[List[KeywordFactsResponse]]
    theme_analysis: Optional[AnalysisResponse]
    final_report: Optional[SummaryResponse]


def extract_user_persona(state: TechNews):
    print("Extracting user persona...")
    user_profile = state["user_info"]
    
    persona = persona_chain.invoke(user_profile)
    
    return{"user_persona" : persona}

def find_keywords(state: TechNews):
    print("Finding keywords...")
    user_profile = state["user_persona"]

    # merge categories
    categories = user_profile.get("major_categories", []) + user_profile.get("minor_categories", [])


    # Start with user-defined keywords
    all_keywords = set(user_profile.get("keywords", []))

    # fetch keywords for mapped categories
    keywords = get_keywords_for_categories(categories)

    # Add keywords extracted from API responses
    for cat, kw_response in keywords.items():
        if kw_response and kw_response["keywords"]:  # kw_response is KeywordsResponse
            for kw_item in kw_response["keywords"]:  # kw_item is KeywordItem
                all_keywords.add(kw_item["keyword"])

    return {"keywords_info": list(all_keywords)}


def retrieve_keywords_facts(state: TechNews):
    print("Retrieving keyword facts...")
    keywords = state["keywords_info"]
    user_persona = state["user_persona"]
    period = user_persona["time_period"]
    facts = fetch_facts_for_keywords(keywords, period)
    # print(facts)
    return{"keywords_facts": facts}

def create_themes(state: TechNews):
    print("Creating themes...")
    facts = state["keywords_facts"]
    user_name = state["user_info"].get("name" , "Unknown")
    user_work_interests = state["user_info"].get("interests" , "Unknown")
    user_perosnality = state["user_persona"].get("personality" , "Unknown")
    user_time_period = state["user_persona"].get("time_period" , "Unknown")
    def format_facts(facts: List[KeywordFactsResponse]) -> str:
        formatted_facts = []
        for fact in facts:
            keyword = fact.get("keyword", "Unknown")
            summary = fact.get("summary", "No summary available")
            interesting_points = "; ".join(fact.get("interesting", []))
            citations = fact.get("citations", [])

            citations_str = ", ".join([f"[{c['n']}] {c.get('url', 'No URL')}" for c in citations])

            formatted_facts.append(
                f"Keyword: {keyword}\n"
                f"Summary: {summary}\n"
                f"Interesting Points: {interesting_points}\n"
                f"Citations: {citations_str}"
            )
        return "\n\n".join(formatted_facts)
        
    formatted_data = format_facts(facts)

    print("Formatted Data:\n")
    print(formatted_data)

    
    input_data = {
        "name": user_name,
        "user_interests": user_work_interests,
        "personality": user_perosnality,
        "time_period": user_time_period,
        "formatted_data": formatted_data
    }
    analysis = analysis_chain.invoke(input_data)
    
    return{"theme_analysis": analysis}

def create_final_report(state: TechNews):
    print("Creating final report...")
    user_name = state["user_info"].get("name" , "Unknown")
    user_work_interests = state["user_info"].get("interests" , "Unknown")
    user_perosnality = state["user_persona"].get("personality" , "Unknown")
    user_time_period = state["user_persona"].get("time_period" , "Unknown")
    concise_summaries = state["user_persona"].get("concise_summaries" , "Unknown")
    
    
    writer_input = {
        "name": user_name,
        "user_interests": user_work_interests,
        "personality": user_perosnality,
        "time_period": user_time_period,
        "concise_summaries": concise_summaries,
        "analysis_output": state["theme_analysis"],
        "formatted_data": state["keywords_facts"]
    }
    
    final_report = writer_chain.invoke(writer_input)
    return{"final_report": final_report}


builder = StateGraph(TechNews)
# Add nodes to the graph
builder.add_node("Extract_Persona", extract_user_persona)
builder.add_node("Find_Keywords", find_keywords)
builder.add_node("Retrieve_Facts", retrieve_keywords_facts)
builder.add_node("Create_Themes", create_themes)
builder.add_node("Create_Report", create_final_report)

# Define the edges to connect the nodes in a sequence
builder.add_edge(START, "Extract_Persona")
builder.add_edge("Extract_Persona", "Find_Keywords")
builder.add_edge("Find_Keywords", "Retrieve_Facts")
builder.add_edge("Retrieve_Facts", "Create_Themes")
builder.add_edge("Create_Themes", "Create_Report")
builder.add_edge("Create_Report", END)

# Compile the graph
news_super_agent = builder.compile()
