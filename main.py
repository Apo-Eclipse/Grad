from graphs import behaviour_analyst_super_agent
from graphs.recommendation_sub_graph import parallel_tavily_search
import io
import sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def main():
    # final_state = behaviour_analyst_super_agent.invoke({
    #     "request": "Analyze the spending behavior of user 1"
    # })
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
    
    out_results = parallel_tavily_search("Stocks , artificial intelligence, technology")
    for query, result in out_results.items():
        search_result = result.get('results', [])
        for i in range(len(search_result)):
            print("_______result___________________________"*5)
            print(search_result[i].get("content", ""))
            print("_______result___________________________"*5)

if __name__ == "__main__":
    main()