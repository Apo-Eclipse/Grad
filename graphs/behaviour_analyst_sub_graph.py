from agents import Explainer_agent, Analyser, Behaviour_analyser_orchestrator, Query_planner
from graphs.database_sub_graph import database_agent_super_agent
from langgraph.graph import StateGraph, END, START
from langgraph.types import Command
from typing import TypedDict
import ast
import time
import csv

class BehaviourAnalystState(TypedDict):
    request: str
    analysis: str
    final_output: str
    message: str
    sender: str
    data_acquired: list[str]
    
def add_to_logs(sender, receiver, message):
    with open("./data/logs.csv", mode='a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow([sender, receiver, message])


def analyser(state: BehaviourAnalystState):
    print("===> Analyser Invoked <===")
    print(state)
    data_acquired = state.get("data_acquired", [])
    message = state.get("message", "")
    Output = Analyser.invoke({"data_acquired": data_acquired, "message": message})
    analysis = Output.output
    message = Output.message
    add_to_logs("analyser", "orchestrator", message)
    return {"analysis": analysis, "message": message, "sender": "analyser"}

def orchestrator(state: BehaviourAnalystState):
    print("===> Orchestrator Invoked <===")
    print(state)
    request = state.get("request", "")
    analysis = state.get("analysis", "")
    data_acquired = state.get("data_acquired", [])
    message = state.get("message", "")
    sender = state.get("sender", "")
    Output = Behaviour_analyser_orchestrator.invoke({"request": request,
                                                    "analysis": analysis,
                                                    "message": message,
                                                    "data_acquired": data_acquired,
                                                    "sender": sender})
    message = Output.message
    next_step = Output.next_step
    print("Next step: ", next_step)
    add_to_logs("orchestrator", next_step, message)
    return Command(update = {
            "data_acquired": data_acquired,
            "message": message, 
            "analysis": analysis,
            "analysis": analysis,
            "request": request,
            "sender": "orchestrator"   
            },
            goto = next_step)

def query_planner(state: BehaviourAnalystState):
    print("===> Query Planner Invoked <===")
    print(state)
    request = state.get("request", "")
    message = state.get("message", "")
    data_acquired = state.get("data_acquired", [])
    Output = Query_planner.invoke({"request": request, "message": message, "data_acquired": data_acquired})
    message = Output.message
    steps = Output.output
    if isinstance(steps, str):
        try:
            steps = ast.literal_eval(steps)
        except Exception:
            steps = [steps]
    add_to_logs("query_planner", "orchestrator", message)
    
    for step in steps:
        time.sleep(5)
        db_state = database_agent_super_agent.invoke({"request": step})
        step = db_state.get("result", {}).get("step", "")
        query = db_state.get("result", {}).get("query", "")
        table = db_state.get("result", {}).get("data", [])
        data_to_written = "The request was: " + str(step) \
                            + "\n" + "The result was: " + str(table)
        time.sleep(5)
        explanation = Explainer_agent.invoke({"request": data_to_written}).explanation
        data_acquired.append(explanation)
    return {"data_acquired": data_acquired, "sender": "query_planner", "message": message}


builder = StateGraph(BehaviourAnalystState)
builder.add_node("analyser", analyser)
builder.add_node("orchestrator", orchestrator)
builder.add_node("query_planner", query_planner)

builder.add_edge(START, "orchestrator")
builder.add_edge("orchestrator", END)

builder.add_edge("query_planner", "orchestrator")
builder.add_edge("analyser", "orchestrator")

behaviour_analyst_super_agent = builder.compile()