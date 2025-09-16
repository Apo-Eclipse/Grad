from agents import Behaviour_Analyst, Explainer_agent
from graphs.database_sub_graph import database_agent_super_agent
from langgraph.graph import StateGraph, END, START
from typing import TypedDict
import ast
import time

class BehaviourAnalystState(TypedDict):
    request: str
    steps: list[str]
    results: list[dict]

def behaviour_analyst(state: BehaviourAnalystState):
    Output = Behaviour_Analyst.invoke({"request": state.get("request", "")})
    if Output.message == "error":
        return {"steps": [], "results": []}

    steps = Output.output
    if isinstance(steps, str):
        try:
            steps = ast.literal_eval(steps)
        except Exception:
            steps = [steps]
            
    for step in steps:
        print("Step to be executed: ", step)
    
    results = []
    for step in steps:
        time.sleep(10)
        db_state = database_agent_super_agent.invoke({"request": step})
        step = db_state.get("result", {}).get("step", "")
        query = db_state.get("result", {}).get("query", "")
        table = db_state.get("result", {}).get("data", [])
        data_to_written = "The request was: " + str(step) \
                            + "\n" + "The result was: " + str(table)
        time.sleep(10)
        explanation = Explainer_agent.invoke({"request": data_to_written}).explanation
        results.append({"explanation": explanation, "table": table, "step": step, "query": query})
    return {"steps": steps, "results": results}

builder = StateGraph(BehaviourAnalystState)
builder.add_node("behaviour_analyst", behaviour_analyst)
builder.add_edge(START, "behaviour_analyst")
builder.add_edge("behaviour_analyst", END)
behaviour_analyst_super_agent = builder.compile()