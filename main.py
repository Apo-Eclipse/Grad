from dotenv import load_dotenv
load_dotenv()
from IPython.display import Image, display, Markdown
from graphs.trend_analysis_sub_graph import news_super_agent
from graphs import behaviour_analyst_super_agent, recommendation_agent_sub_graph, main_orchestrator_graph
from agents import Explainer_agent
import pandas as pd
import asyncio
import json
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)


# def process_queries():
#     queries_to_run = json.load(open('queries_to_run.json', 'r', encoding='utf-8'))
#     conn = sqlite3.connect('./data/database.db')
#     tables = []
#     for query in queries_to_run:
#         table = pd.read_sql_query(queries_to_run[query], conn)
#         tables.append("Query: " + query + "\nTable:\n" + table.to_string(index=False))
#     conn.close()
#     return tables

# def process_tables(tables):
#     explanations = []
#     for table in tables:
#         explanation = Explainer_agent.invoke({"request": table})
#         explanations.append(explanation.explanation)
#     return explanations  
    
def run_trend_analysis():
        # from graphs import presentation_super_agent,behaviour_analyst_super_agent, database_agent_super_agent

    # sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    # out_results = parallel_tavily_search("Stocks , artificial intelligence, technology")
    # for query, result in out_results.items():
    #     search_result = result.get('results', [])
    #     for i in range(len(search_result)):
    #         print("result"*5)
    #         print(search_result[i].get("content", ""))
    #         print("result"*5)


    #-----------------------------------------------------------------------------------------
    input_dict_developer = {
        "user_info": {
            "name": "Karim",
            "interests": "I'm a backend developer working with Python and cloud services. I'm interested in AI, specifically large language models, open-source projects, and new cloud-native technologies.",
            "user_keywords": "LLMs, Kubernetes, Python, OpenAI, Llama",
            "summary_style": "Detailed, technical breakdown. Don't shy away from jargon.",
            "time_period": "daily"
        },
        "user_persona": None,
        "keywords_info": None,
        "keywords_facts": None,
        "theme_analysis": None,
        "final_report": None,
    }

    output = news_super_agent.invoke(input_dict_developer)
    long_summary = output["final_report"].get("long_summary", "")
    concise_summary = output["final_report"].get("concise_summary", "")
    title = output["final_report"].get("title", "No title generated")
    print("-------------------------------------------------------------------------------------")
    print("title: \n", title)
    print("-------------------------------------------------------------------------------------")
    print("\n\nLong Summary:\n", long_summary)
    print("-------------------------------------------------------------------------------------")
    print("\n\nConcise Summary:\n", concise_summary)
    print("-------------------------------------------------------------------------------------")
    
def run_behaviour_analysis():
    # tables = process_queries()
    # explanations = process_tables(tables)
    # print("****************************Tables******************************************") 
    # for table in tables:
    #     print(table)
    # print("****************************Explanations***************************************")
    # for explanation in explanations:
    #     print(explanation)
    final_state = asyncio.run(behaviour_analyst_super_agent.ainvoke({
        "request": "i want analysis for month 10 in 2025"
        , "data_acquired": [], "analysis": "no analysis done yet"
        , "final_output": "no output yet", "message": "no message yet", "sender": "user", "user": "2"
        },
        {"recursion_limit": 500}
    ))
    
    print("\n=== Behaviour Analyst Analysis ===")
    print(final_state['analysis'])
    # print("\n=== Behaviour data ===")
    # print(final_state['data_acquired'])

def run_recommendation_agent():
    
    out_results = recommendation_agent_sub_graph.invoke({"insights":"where did i spend the most in months 8 and 9 in 2025?"})
    print(out_results['report'])
    # for query, result in out_results.items():
    #     search_result = result.get('results', [])
    #     for i in range(len(search_result)):
    #         print("_______result___________________________"*5)
    #         print(search_result[i].get("content", ""))
    #         print("_______result___________________________"*5)

def main():
    """Interactive conversation loop with PersonalAssistant orchestrator."""
    user_id = 3
    user_name = "Mariam"
    
    print("\n" + "="*80)
    print(f"👋 Welcome {user_name}! Chat with PersonalAssistant (type 'exit' to quit)")
    print("="*80 + "\n")
    
    # Conversation state
    state = {
        "user_id": user_id,
        "user_name": user_name,
        "user_message": "",
        "next_step": "",
        "agent_result": {},
        "routing_decision": "",
        "routing_message": "",
        "message": "",
        "has_data": False,
        "data": None,
        "is_awaiting_data": False
    }
    
    while True:
        user_input = input(f"\n{user_name}: ").strip()
        
        if user_input.lower() in ['exit', 'quit', 'bye']:
            print(f"\n👋 Goodbye {user_name}!")
            break
        
        if not user_input:
            continue
        
        # Update state with new message
        state["user_message"] = user_input
        state["agent_result"] = {}
        state["message"] = ""
        state["has_data"] = False
        state["data"] = None
        state["is_awaiting_data"] = False
        
        # Invoke the orchestrator asynchronously
        result = asyncio.run(main_orchestrator_graph.ainvoke(state))
        
        # Display response based on data availability
        if result.get("has_data", False):
            # Tabular data exists - display message and data
            print(f"\n🤖 Assistant: {result.get('message', 'Here are your results:')}")
            
            # Display data as formatted table
            if result.get('data'):
                import pandas as pd
                df = pd.DataFrame(result.get('data'))
                print(f"\n{df.to_string(index=False)}")
        else:
            # No tabular data - just display the message
            print(f"\n🤖 Assistant: {result.get('message', 'No response generated')}")
        
        # Update state for next iteration
        state = result

if __name__ == "__main__":
    main()