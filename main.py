from graphs import behaviour_analyst_super_agent,recommendation_agent_sub_graph
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
    
    out_results = recommendation_agent_sub_graph.invoke({"insights":"latest news in investing in real estate in Egypt in 2025"})
    print(out_results['report'])
    # for query, result in out_results.items():
    #     search_result = result.get('results', [])
    #     for i in range(len(search_result)):
    #         print("_______result___________________________"*5)
    #         print(search_result[i].get("content", ""))
    #         print("_______result___________________________"*5)

if __name__ == "__main__":
    main()