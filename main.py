from graphs import behaviour_analyst_super_agent,recommendation_agent_sub_graph
from agents import Explainer_agent
import pandas as pd
import sqlite3
import json
import io
import sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


def process_queries():
    queries_to_run = json.load(open('queries_to_run.json', 'r', encoding='utf-8'))
    conn = sqlite3.connect('./data/database.db')
    tables = []
    for query in queries_to_run:
        table = pd.read_sql_query(queries_to_run[query], conn)
        tables.append("Query: " + query + "\nTable:\n" + table.to_string(index=False))
    conn.close()
    return tables

def process_tables(tables):
    explanations = []
    for table in tables:
        explanation = Explainer_agent.invoke({"request": table})
        explanations.append(explanation.explanation)
    return explanations
    
def main():
    # behaviour analyst agent output
    tables = process_queries()
    explanations = process_tables(tables)
    final_state = behaviour_analyst_super_agent.invoke({
        "request": "Analyze the spending behavior of user 1 and try to investigate more the acquired data"
        , "data_acquired": explanations, "analysis": "no analysis done yet"
        , "final_output": "no output yet", "message": "no message yet", "sender": "user"
    })
    print("\n=== Behaviour Analyst Final State ===")
    print(final_state)
    print("\n=== Behaviour Analyst Analysis ===")
    print(final_state['analysis'])
    # print("\n=== Behaviour Analyst Steps ===")
    # for i, step in enumerate(final_state.get("steps", []), 1):
    #     print(f"{i}. {step}")

    # print("\n=== Database Agent Results ===")
    # for i, res in enumerate(final_state.get("results", []), 1):
    #     print(f"{i}. {res['step']}")
    #     print(f"Table: {res['table']}")
    #     print(f"Query: {res['query']}")
    #     print(f"Explanation: {res['explanation']}")
    #     print("-" * 20)
    
    
    
    # # recommendation agent output
    # out_results = recommendation_agent_sub_graph.invoke({"insights":"latest news in investing in real estate in Egypt in 2025"})
    # print(out_results['report'])
    # # for query, result in out_results.items():
    # #     search_result = result.get('results', [])
    # #     for i in range(len(search_result)):
    # #         print("_______result___________________________"*5)
    # #         print(search_result[i].get("content", ""))
    # #         print("_______result___________________________"*5)

if __name__ == "__main__":
    main()